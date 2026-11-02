#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1 — 统一 AI 用量账本（覆盖全部付费路径）。

此前只有 enrichment 的 `token_usage` 进入 ops 账本，news_localization /
assessment / homepage_brief / reports 的模型调用**没有任何账本**，
"某个子程序 REAL_AI_CALLS=0" 也不代表整轮没有模型调用。

本模块在 provider 层（`_flash_provider()` 唯一出口）统一记账：
  - 每次调用的组件、阶段、模型（请求/返回）、输入/输出/缓存 token、
    成功/失败/重试次数、HTTP 状态、耗时；
  - 供应商返回的缓存命中 token（DeepSeek `prompt_cache_hit_tokens`）缺失时记 null，
    并置 `cache_tokens_available=false`，绝不臆造 0；
  - **已确认费用**（供应商账单口径）与**估算费用**分列：仅当配置了单价
    （`ASIP_PRICE_INPUT_PER_MTOK` / `ASIP_PRICE_OUTPUT_PER_MTOK`）才计算估算值，
    否则为 null；`confirmed_cost` 恒为 null（DeepSeek 不回传金额），
    账单需与供应商对账后回填。

落盘位置（随 production-state 提交，独立于旧 token_usage，向后兼容）：
  data/runtime/ops/ai_usage.jsonl        每次调用一行（append-only）
  data/runtime/ops/ai_usage_summary.json 最近一次 run 的分组件汇总
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OPS_DIR = ROOT / "data" / "runtime" / "ops"
LEDGER_PATH = OPS_DIR / "ai_usage.jsonl"
SUMMARY_PATH = OPS_DIR / "ai_usage_summary.json"

#: 需要纳入账本的付费路径（与 P0-R1 第二部分 B 一致）
COMPONENTS = (
    "social_ai", "disease_ai", "news_localization", "daily_assessment",
    "homepage_brief", "daily_report", "weekly_report", "other",
)

_COMPONENT = "other"


class LedgerUnavailable(RuntimeError):
    """账本不可写：不得当作"正常可计费"继续（fail-closed）。"""


def ensure_writable(path=None):
    """调用前的账本可写性探针：不可写即拒绝发起付费调用。"""
    p = Path(path) if path else LEDGER_PATH
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write("")
        return True
    except OSError as e:
        raise LedgerUnavailable("ledger not writable: %s (%s)" % (p, e))


def set_component(name):
    """由各付费入口在开始处声明自身组件（provider 层据此记账）。"""
    global _COMPONENT
    _COMPONENT = str(name or "other")


def current_component():
    """组件标签：子进程通过 ASIP_AI_COMPONENT 继承（orchestrator 打标）。"""
    return os.environ.get("ASIP_AI_COMPONENT") or _COMPONENT


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pricing():
    """单价配置（每百万 token，人民币或美元由使用者口径决定）。

    未配置 → configured=False，估算费用为 null；**不得硬编码价格**。
    """
    i = os.environ.get("ASIP_PRICE_INPUT_PER_MTOK")
    o = os.environ.get("ASIP_PRICE_OUTPUT_PER_MTOK")
    try:
        i = float(i) if i not in (None, "") else None
        o = float(o) if o not in (None, "") else None
    except ValueError:
        i = o = None
    return {"input_per_mtok": i, "output_per_mtok": o,
            "configured": i is not None and o is not None,
            "currency": os.environ.get("ASIP_PRICE_CURRENCY", "")}


def _estimate(in_tokens, out_tokens):
    p = pricing()
    if not p["configured"]:
        return None
    i = (in_tokens or 0) / 1_000_000.0 * p["input_per_mtok"]
    o = (out_tokens or 0) / 1_000_000.0 * p["output_per_mtok"]
    return round(i + o, 6)


def record(component=None, phase="", requested_model=None, returned_model=None,
           input_tokens=None, output_tokens=None, total_tokens=None,
           cache_hit_tokens=None, cache_miss_tokens=None,
           status="unknown", error="", http_status=None, attempt_count=None,
           latency_ms=None, run_id=None, path=None, extra=None):
    """记录一次模型调用（无论成功/失败都记，失败也消耗重试请求）。"""
    comp = component or current_component()
    rec = {
        "ts": _now_iso(),
        "run_id": run_id or os.environ.get("ASIP_RUN_ID") or "",
        "component": comp,
        "phase": phase or "",
        "requested_model": requested_model,
        "returned_model": returned_model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cache_hit_tokens": cache_hit_tokens,
        "cache_miss_tokens": cache_miss_tokens,
        "cache_tokens_available": cache_hit_tokens is not None,
        "status": status,
        "error": str(error)[:200],
        "http_status": http_status,
        "attempt_count": attempt_count,
        "retries": (attempt_count - 1) if isinstance(attempt_count, int) and attempt_count > 0 else 0,
        "latency_ms": latency_ms,
        "billing_mode": "paid",
        "estimated_cost": _estimate(input_tokens, output_tokens),
        "confirmed_cost": None,          # 需与供应商账单对账后回填
        "pricing": pricing(),
    }
    if extra:
        rec.update(extra)
    p = Path(path) if path else LEDGER_PATH
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError as e:
        raise LedgerUnavailable("ledger write failed: %s (%s)" % (p, e))
    return rec


def read_ledger(path=None, run_id=None):
    p = Path(path) if path else LEDGER_PATH
    out = []
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if run_id and r.get("run_id") != run_id:
                    continue
                out.append(r)
    except FileNotFoundError:
        return []
    return out


def summarize(records):
    """按组件汇总：调用数、成功/失败、重试、token、缓存命中、估算费用。"""
    agg = {}
    tot = {"calls": 0, "succeeded": 0, "failed": 0, "retries": 0,
           "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
           "cache_hit_tokens": 0, "cache_tokens_available_calls": 0,
           "estimated_cost": 0.0, "estimated_cost_available": False,
           "confirmed_cost": None}
    for r in records:
        c = r.get("component") or "other"
        a = agg.setdefault(c, {"calls": 0, "succeeded": 0, "failed": 0, "retries": 0,
                               "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
                               "cache_hit_tokens": 0, "cache_tokens_available_calls": 0,
                               "estimated_cost": 0.0, "models": {}})
        a["calls"] += 1
        st = str(r.get("status") or "")
        if st in ("succeeded", "ok", "success"):
            a["succeeded"] += 1
        else:
            a["failed"] += 1
        a["retries"] += int(r.get("retries") or 0)
        a["input_tokens"] += int(r.get("input_tokens") or 0)
        a["output_tokens"] += int(r.get("output_tokens") or 0)
        a["total_tokens"] += int(r.get("total_tokens") or 0)
        if r.get("cache_hit_tokens") is not None:
            a["cache_hit_tokens"] += int(r["cache_hit_tokens"])
            a["cache_tokens_available_calls"] += 1
        m = r.get("returned_model") or r.get("requested_model")
        if m:
            a["models"][m] = a["models"].get(m, 0) + 1
        if r.get("estimated_cost") is not None:
            a["estimated_cost"] += float(r["estimated_cost"])
    # 汇总
    for k in ("calls", "succeeded", "failed", "retries", "input_tokens", "output_tokens",
              "total_tokens", "cache_hit_tokens", "cache_tokens_available_calls"):
        tot[k] = sum(a[k] for a in agg.values())
    costs = [a["estimated_cost"] for a in agg.values()]
    tot["estimated_cost"] = round(sum(costs), 6)
    tot["estimated_cost_available"] = any(c > 0 for c in costs)
    return {"by_component": agg, "totals": tot, "pricing": pricing()}


def write_summary(run_id=None, path=None):
    rid = run_id or os.environ.get("ASIP_RUN_ID") or ""
    recs = read_ledger(run_id=rid) if rid else read_ledger()
    s = summarize(recs)
    s["run_id"] = rid
    s["generated_at"] = _now_iso()
    p = Path(path) if path else SUMMARY_PATH
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        pass
    return s


def coverage(legacy_token_usage, records=None):
    """账本覆盖率：统一账本 calls vs 旧 token_usage 记录的 calls（同一 run）。"""
    legacy_calls = 0
    for _pool, v in (legacy_token_usage or {}).items():
        if isinstance(v, dict):
            legacy_calls += int(v.get("calls") or 0)
    recs = records if records is not None else []
    return {"legacy_calls": legacy_calls, "ledger_calls": len(recs),
            "coverage_pct": round(100.0 * len(recs) / legacy_calls, 1) if legacy_calls else None}


# ── 运行级预算（AI 调用上限；HTTP 重试也计入）────────────────────────
class BudgetExceeded(RuntimeError):
    pass


_BUDGET = {"cap": int(os.environ.get("ASIP_AI_RUN_MAX_CALLS", "80")), "used": 0}


def budget_state():
    return dict(_BUDGET)


def budget_remaining():
    return max(0, _BUDGET["cap"] - _BUDGET["used"])


def charge_attempt(component=""):
    """每次**真实 HTTP 尝试**（含内部重试）调用；超出上限即抛错（fail-closed）。

    上限由 ASIP_AI_RUN_MAX_CALLS 控制（默认 80，参考历史 ≈65 次/日）。
    进程级计数 = 单次运行的上限，重启归零。
    """
    _BUDGET["used"] += 1
    if _BUDGET["used"] > _BUDGET["cap"]:
        raise BudgetExceeded("ai run cap exceeded: %d/%d (component=%s)"
                             % (_BUDGET["used"], _BUDGET["cap"], component))
    return _BUDGET["used"]


# ── 账本收尾（可复用；真实账本派生，绝不强制写 0）──────────────────────
def finalize_run_ledger(run_id=None, path=None, summary_path=None):
    """收尾账本并**读回校验**。

    - 数据源是该 run_id 的**真实调用记录**（若实际发生过 AI 调用，汇总如实反映，
      绝不强制写 0 掩盖事实）；
    - 汇总写入后读回比对（run_id / calls / input / output），任一不符即 ok=False；
    - 账本不可写 → ok=False（不得报告 PASS）。
    """
    rid = run_id or os.environ.get("ASIP_RUN_ID") or ""
    try:
        records = read_ledger(path=path, run_id=rid) if rid else read_ledger(path=path)
        s = summarize(records)
        s["run_id"] = rid
        s["generated_at"] = _now_iso()
        s["records_for_run"] = len(records)
        s["zero_calls_confirmed"] = (s["totals"]["calls"] == 0)
        # 写入
        p_ = Path(summary_path) if summary_path else SUMMARY_PATH
        ensure_writable(p_)
        tmp = p_.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, p_)
        # 读回校验
        back = json.loads(p_.read_text(encoding="utf-8"))
        ok = (back.get("run_id") == rid
              and back.get("totals", {}).get("calls") == s["totals"]["calls"]
              and back.get("totals", {}).get("input_tokens") == s["totals"]["input_tokens"]
              and back.get("totals", {}).get("output_tokens") == s["totals"]["output_tokens"])
        s["verified"] = bool(ok)
        s["ok"] = bool(ok)
        # 把 verified 标志写回文件（落盘证据与内存一致），并再次读回确认
        tmp2 = p_.with_suffix(".json.tmp")
        tmp2.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp2, p_)
        back2 = json.loads(p_.read_text(encoding="utf-8"))
        s["verified"] = s["verified"] and (back2.get("verified") is True)
        s["ok"] = s["verified"]
        return s
    except LedgerUnavailable as e:
        return {"ok": False, "verified": False, "run_id": rid,
                "error": "ledger_unwritable:%s" % e}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "verified": False, "run_id": rid, "error": str(e)[:200]}


# ── provider 包装：门禁 + 记账（唯一出口）─────────────────────────────
class MeteredProvider:
    """对任意 provider 的透明包装：调用前门禁、调用后记账，其余属性透传。"""

    def __init__(self, inner, component=None, run_id=None, ledger_path=None, gate=True):
        self._inner = inner
        self._component = component
        self._run_id = run_id
        self._ledger_path = ledger_path
        self._gate = gate

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def submit_task(self, task):
        from scripts.ops import paid_gate
        comp = self._component or current_component()
        if self._gate:
            paid_gate.assert_paid_allowed(comp)     # 暂停时直接抛，不产生任何网络请求
            ensure_writable(self._ledger_path)      # 账本不可写 → 拒绝发起（fail-closed）
            if budget_remaining() <= 0:             # 预算耗尽 → 拒绝发起（重试也在 provider 内计数）
                raise BudgetExceeded("ai run budget exhausted before submit (%s)" % comp)
        t0 = time.time()
        try:
            res = self._inner.submit_task(task)
        except Exception as e:
            try:
                record(component=comp, phase=str(task.get("task_type") or ""),
                       requested_model=getattr(self._inner, "model", None),
                       status="error", error=str(e), latency_ms=int((time.time() - t0) * 1000),
                       run_id=self._run_id, path=self._ledger_path)
            except LedgerUnavailable:
                pass  # 原始异常优先（账本已不可写，由上层 fail-closed 处理）
            raise
        result = (res or {}).get("result") or {}
        record(component=comp,
               phase=str(task.get("task_type") or ""),
               requested_model=result.get("requested_model") or getattr(self._inner, "model", None),
               returned_model=result.get("returned_model"),
               input_tokens=result.get("input_tokens"),
               output_tokens=result.get("output_tokens"),
               total_tokens=result.get("total_tokens"),
               cache_hit_tokens=result.get("cache_hit_tokens"),
               cache_miss_tokens=result.get("cache_miss_tokens"),
               status=str((res or {}).get("status") or result.get("provider_status") or "unknown"),
               error=((result.get("error") or {}).get("code") if isinstance(result.get("error"), dict)
                      else result.get("error")) or "",
               http_status=result.get("http_status"),
               attempt_count=result.get("attempt_count"),
               latency_ms=result.get("latency_ms") or int((time.time() - t0) * 1000),
               run_id=self._run_id, path=self._ledger_path)
        return res


def wrap_provider(inner, component=None, run_id=None, ledger_path=None, gate=True):
    return MeteredProvider(inner, component=component, run_id=run_id,
                           ledger_path=ledger_path, gate=gate)
