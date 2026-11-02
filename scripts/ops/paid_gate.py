#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1 — 付费任务暂停门禁 / 熔断 / 写前体积保护 / 告警。

设计要点（对应 P0-R1 第二、四部分）：

1) **最外层暂停门禁**：`PRODUCTION_SCHEDULE_ENABLED=false` 只清空 due 列表，
   `execute()` 仍会无条件运行 news_localization / assessment / homepage_brief 等付费子任务。
   本模块提供 `paused()` / `assert_paid_allowed()`，在**任何付费子任务启动之前**判定，
   并在 provider 层再兜一次（见 ai_ledger.MeteredProvider）。

2) **熔断状态独立持久化**：熔断标记**不写入** production-state（那里正写不进）。
   本模块把状态写到 `data/runtime/ops/paid_breaker.json`（本地），并通过
   `publish_breaker()` 推到**独立分支** `ops-health`（小文件，不受 100MB 限制影响）。
   下轮启动时 `_load_remote_breaker()` 从该分支读回。

3) **写前体积保护**：`state_size_report()` 扫描将提交的 state 文件，任一超过软阈
   （默认 95 MB）即视为"不可安全持久化"，付费任务必须禁止启动。

4) **告警**：`emit_alert()` 写本地告警队列（`data/runtime/ops/alerts.jsonl`）并尽力开 GitHub Issue；
   无凭据时只落本地，不阻断主流程。

所有函数均为纯逻辑 + 明确副作用，便于离线测试（无网络、无付费调用）。
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OPS_DIR = ROOT / "data" / "runtime" / "ops"
BREAKER_PATH = OPS_DIR / "paid_breaker.json"
#: 远端熔断状态可达性（由 breakerctl fetch/publish 写入；用于跨 runner 的 fail-closed 判定）
BREAKER_REMOTE_PATH = OPS_DIR / "breaker_remote.json"
BREAKER_AUDIT_PATH = OPS_DIR / "breaker_audit.jsonl"
ALERTS_PATH = OPS_DIR / "alerts.jsonl"

#: 暂停开关（与 PRODUCTION_SCHEDULE_ENABLED 相互独立，语义更强：直接禁止付费任务）
PAUSE_ENV = "ASIP_PAUSE_PAID_TASKS"
#: 单文件软上限（GitHub 硬上限 100 MB = 104,857,600 B）
STATE_FILE_SOFT_LIMIT_MB = int(os.environ.get("ASIP_STATE_FILE_SOFT_LIMIT_MB", "95"))
GITHUB_HARD_LIMIT_BYTES = 100 * 1024 * 1024

#: 需要纳入体积检查的 state 路径（与 orchestrator Commit state 一致）
STATE_PATHS = [
    "data/canonical", "data/disease", "data/public", "data/views", "data/intelligence",
    "data/reports", "data/runtime/ops", "data/runtime/timeline",
    "data/events.json", "data/pending_events.json", "data/raw_candidates.json",
    "data/quarantine_events.json", "logs/collector_cache",
]


class PaidTasksPaused(RuntimeError):
    """付费任务被门禁拦截（fail-closed，调用方必须向上传播，不得吞掉）。"""

    def __init__(self, reason, component=""):
        super().__init__("PAID_TASKS_PAUSED: %s (%s)" % (reason, component or "unknown"))
        self.reason = reason
        self.component = component


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truthy(v):
    return str(v or "").strip().lower() in ("1", "true", "yes", "on")


# ── 熔断状态（独立持久化）────────────────────────────────────────────
def load_breaker(path=None):
    p = Path(path) if path else BREAKER_PATH
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"tripped": False, "reason": "", "tripped_at": None, "until": None, "strikes": 0}
    if not isinstance(doc, dict):
        return {"tripped": False, "reason": "", "tripped_at": None, "until": None, "strikes": 0}
    return doc


def save_breaker(doc, path=None):
    p = Path(path) if path else BREAKER_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, p)
    return p


def record_strike(reason, ttl_hours=24, strikes_to_trip=2, path=None):
    """记录一次失败；连续 N 次 → 触发熔断。返回当前 breaker 文档。"""
    doc = load_breaker(path)
    doc["strikes"] = int(doc.get("strikes") or 0) + 1
    doc["last_failure_at"] = _now_iso()
    doc["last_failure_reason"] = str(reason)[:300]
    if doc["strikes"] >= strikes_to_trip and not doc.get("tripped"):
        doc["tripped"] = True
        doc["reason"] = "consecutive_failures:%s" % str(reason)[:120]
        doc["tripped_at"] = _now_iso()
        doc["until"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime(time.time() + ttl_hours * 3600))
    save_breaker(doc, path)
    return doc


def clear_breaker(path=None, by="", reason=""):
    """解除熔断（必须可审计：记录 who/when/why 到状态文件与审计日志）。"""
    doc = {"tripped": False, "reason": "", "tripped_at": None, "until": None, "strikes": 0,
           "cleared_at": _now_iso(), "cleared_by": str(by or "unknown"),
           "cleared_reason": str(reason or "manual")}
    save_breaker(doc, path)
    try:
        p = (Path(path) if path else BREAKER_PATH).parent / "breaker_audit.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": doc["cleared_at"], "action": "clear",
                                "by": doc["cleared_by"], "reason": doc["cleared_reason"]},
                               ensure_ascii=False) + "\n")
    except OSError:
        pass
    return doc


def save_remote_status(reachable, detail="", path=None):
    """记录远端熔断状态可达性（供下一轮/另一 runner 判定）。"""
    p = Path(path) if path else BREAKER_REMOTE_PATH
    doc = {"reachable": bool(reachable), "detail": str(detail)[:300], "checked_at": _now_iso()}
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        pass
    return doc


def breaker_remote():
    """远端熔断可达性：True / False / None(未知)。"""
    try:
        doc = json.loads(BREAKER_REMOTE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"reachable": None, "detail": "no remote status file", "checked_at": None}
    return doc


def breaker_active(doc=None):
    doc = doc if doc is not None else load_breaker()
    if not doc.get("tripped"):
        return False, ""
    until = doc.get("until")
    if until:
        try:
            if datetime.strptime(until, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) \
                    < datetime.now(timezone.utc):
                return False, "expired"
        except ValueError:
            pass
    return True, doc.get("reason") or "tripped"


# ── 写前体积保护 ────────────────────────────────────────────────────
def state_size_report(root=None, soft_limit_mb=None):
    """扫描将提交的 state 文件，返回 {max_file, max_bytes, oversize[], total_bytes}。"""
    base = Path(root) if root else ROOT
    limit = (soft_limit_mb if soft_limit_mb is not None else STATE_FILE_SOFT_LIMIT_MB) * 1024 * 1024
    biggest = ("", 0)
    oversize = []
    total = 0
    for rel in STATE_PATHS:
        p = base / rel
        if p.is_file():
            sz = p.stat().st_size
            total += sz
            if sz > biggest[1]:
                biggest = (rel, sz)
            if sz > limit:
                oversize.append({"path": rel, "bytes": sz})
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file():
                    sz = f.stat().st_size
                    total += sz
                    relf = str(f.relative_to(base)).replace("\\", "/")
                    if sz > biggest[1]:
                        biggest = (relf, sz)
                    if sz > limit:
                        oversize.append({"path": relf, "bytes": sz})
    return {
        "max_file": biggest[0],
        "max_bytes": biggest[1],
        "max_mb": round(biggest[1] / 1048576, 2),
        "oversize": oversize,
        "total_bytes": total,
        "soft_limit_mb": limit // 1048576,
        "github_hard_limit_bytes": GITHUB_HARD_LIMIT_BYTES,
        "safe_to_persist": not oversize and biggest[1] < GITHUB_HARD_LIMIT_BYTES,
    }


# ── 统一暂停判定 ────────────────────────────────────────────────────
def paused(root=None, breaker=None, size_report=None):
    """返回 (paused: bool, reason: str)。任何一条命中即暂停（fail-closed）。"""
    if _truthy(os.environ.get(PAUSE_ENV)):
        return True, "env:%s" % PAUSE_ENV
    active, why = breaker_active(breaker)
    if active:
        return True, "breaker:%s" % why
    # 远端熔断状态不可验证 → 暂停（生产强制；本地可通过 ASIP_REQUIRE_BREAKER_REMOTE=0 放宽）
    rs = breaker_remote()
    if rs.get("reachable") is False:
        return True, "breaker_remote_unavailable:%s" % (rs.get("detail") or "")
    if rs.get("reachable") is None:
        required = _truthy(os.environ.get("ASIP_REQUIRE_BREAKER_REMOTE")) or \
            os.environ.get("GITHUB_ACTIONS") == "true"
        if required:
            return True, "breaker_remote_unverified"
    rep = size_report if size_report is not None else state_size_report(root)
    if not rep.get("safe_to_persist"):
        return True, "state_oversize:%s(%.2fMB)" % (rep.get("max_file"), rep.get("max_mb") or 0)
    return False, ""


def assert_paid_allowed(component, root=None):
    """付费调用前必须调用；暂停/collection_only 时抛 PaidTasksPaused（不得捕获后继续）。"""
    # R1D：collection_only 是"零付费采集"模式——与全局暂停开关不同，它只禁付费、
    # 不禁采集，因此在这里单独判定（不能用暂停开关实现，否则采集也被禁）。
    if (os.environ.get("ASIP_RUN_MODE") or "").strip().lower() == "collection_only":
        raise PaidTasksPaused("collection_only_mode", component)
    is_paused, reason = paused(root)
    if is_paused:
        raise PaidTasksPaused(reason, component)
    return True


def pause_mode_summary(root=None):
    is_paused, reason = paused(root)
    rep = state_size_report(root)
    return {"paused": is_paused, "reason": reason,
            "env_pause": _truthy(os.environ.get(PAUSE_ENV)),
            "breaker": load_breaker(),
            "breaker_remote": breaker_remote(),
            "state_size": rep}


# ── 告警 ───────────────────────────────────────────────────────────
ALERT_THRESHOLDS = {
    "state_stale_hours": int(os.environ.get("ASIP_ALERT_STATE_STALE_HOURS", "6")),
    "deploy_stall_hours": int(os.environ.get("ASIP_ALERT_DEPLOY_STALL_HOURS", "6")),
    "single_run_ai_calls": int(os.environ.get("ASIP_ALERT_SINGLE_RUN_AI_CALLS", "23")),
    "daily_ai_calls": int(os.environ.get("ASIP_ALERT_DAILY_AI_CALLS", "130")),
    "state_file_mb": int(os.environ.get("ASIP_ALERT_STATE_FILE_MB", "80")),
}


def emit_alert(kind, detail, root=None, gh_token=None, repo=None):
    """写入本地告警队列；有凭据时尝试开 Issue（失败不阻断）。返回记录。"""
    rec = {"ts": _now_iso(), "kind": kind, "detail": detail,
           "thresholds": ALERT_THRESHOLDS}
    base = Path(root) if root else ROOT
    p = base / "data" / "runtime" / "ops" / "alerts.jsonl"
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass
    token = gh_token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    repo = repo or os.environ.get("GITHUB_REPOSITORY")
    if token and repo:
        try:
            import urllib.request
            body = json.dumps({"title": "[ASIP-5][%s] %s" % (kind, detail[:80]),
                               "body": "自动告警（ASIP-5 P0-R1）\n\n```json\n%s\n```" %
                                       json.dumps(rec, ensure_ascii=False, indent=1)}).encode()
            req = urllib.request.Request(
                "https://api.github.com/repos/%s/issues" % repo, data=body, method="POST",
                headers={"Authorization": "Bearer %s" % token,
                         "Accept": "application/vnd.github+json",
                         "Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=15).read()
            rec["issue_created"] = True
        except Exception as e:  # noqa: BLE001
            rec["issue_error"] = str(e)[:160]
    return rec


def check_thresholds(state=None, ai_today_calls=None, ai_last_run_calls=None, root=None):
    """按 §4.5 阈值产生告警列表（纯判定，供 orchestrator 每轮调用）。"""
    out = []
    state = state or {}
    now = datetime.now(timezone.utc)
    for field, kind in (("last_successful_collection", "state_stale"),
                        ("last_successful_deploy", "deploy_stall")):
        raw = state.get(field)
        if not raw:
            out.append({"kind": kind, "detail": "%s missing" % field})
            continue
        try:
            ts = datetime.strptime(str(raw)[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        hours = (now - ts).total_seconds() / 3600
        limit = ALERT_THRESHOLDS["state_stale_hours" if kind == "state_stale"
                                 else "deploy_stall_hours"]
        if hours > limit:
            out.append({"kind": kind, "detail": "%s %.1fh > %dh" % (field, hours, limit)})
    if ai_last_run_calls is not None and ai_last_run_calls > ALERT_THRESHOLDS["single_run_ai_calls"]:
        out.append({"kind": "single_run_ai_spike",
                    "detail": "calls=%d > %d" % (ai_last_run_calls,
                                                 ALERT_THRESHOLDS["single_run_ai_calls"])})
    if ai_today_calls is not None and ai_today_calls > ALERT_THRESHOLDS["daily_ai_calls"]:
        out.append({"kind": "daily_ai_spike",
                    "detail": "calls=%d > %d" % (ai_today_calls,
                                                 ALERT_THRESHOLDS["daily_ai_calls"])})
    rep = state_size_report(root)
    if rep["max_mb"] > ALERT_THRESHOLDS["state_file_mb"]:
        out.append({"kind": "state_file_size",
                    "detail": "%s %.2fMB > %dMB" % (rep["max_file"], rep["max_mb"],
                                                    ALERT_THRESHOLDS["state_file_mb"])})
    return out
