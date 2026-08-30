#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage8D schedule fix — Hourly Due-Task Orchestrator（§十五/§十六/§十七）。

背景（Stage8D Observation 根因）：
- 原 4 个 production workflow 均以多 cron 直接调度；实测 10 个预期 tick 中 7 个
  MISSED、3 个延迟 1h45m–3h（GITHUB_SCHEDULE_DELAY_OR_DROP，
  GITHUB_SCHEDULE_RELIABILITY_RISK=true）。
- 原 schedule 路径依赖 github.event.inputs.*（schedule 下为空）→ 全部进入 Shadow
  （collection 无 --execute；AI --fake --max-items 0；reports source=derived --no-ai）。

本模块实现最小 Hourly Orchestrator：
- 单一每小时 cron（0 * * * *）触发；
- 依据 production-state（last_successful_* / processed_hashes / report dates）判断
  哪些任务到期（due），只执行 due 任务；
- 所有任务以 production mode 真实执行（collection --execute；AI 真实 provider；
  reports --source canonical）；
- 幂等：AI 仅处理 content hash 未处理条目；daily/weekly 每日/每周至多一份；
  collection 以 5h45m 间隔阈值防重复；
- trigger 标记 = scheduled_orchestrator（自然 Automation）；--canary 标记 = manual_canary。

时间语义：全部使用北京时间（UTC+8）。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ops import operations as ops  # noqa: E402
from scripts.ops import production_state as ps  # noqa: E402

BJT = timezone(timedelta(hours=8))
# 生产时间门（BJT）
COLLECTION_MIN_GAP = timedelta(hours=5, minutes=45)  # 6h 周期，容忍 ≤15min 抖动
DISEASE_TIME = (1, 30)
DAILY_TIME = (20, 0)
WEEKLY_TIME = (6, 45)  # 周日
LEGAL_REPORT = {"FULL", "FALLBACK", "LOW_DATA"}


def deploy_required_for(classification):
    """§二 publishability 契约（纯函数，便于单测）。

    FULL / FALLBACK / LOW_DATA → 可发布 → deploy_required = True
    FACT_GATE_FAIL（分类为 HOLD）或其它异常值 → 不可发布 → False
    """
    return classification in LEGAL_REPORT


def _parse_iso(s):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def resolve_mode(event_name, inputs=None):
    """§九：schedule → production；workflow_dispatch → 显式 inputs（默认 shadow）。"""
    inputs = inputs or {}
    if event_name == "schedule":
        return "production"
    on = str(inputs.get("execute") or inputs.get("run_ai") or "").lower() == "true"
    src = str(inputs.get("source") or "").lower()
    if on or src == "production":
        return "production"
    return "shadow"


def resolve_trigger(event_name, inputs=None, client_payload=None):
    """§三/§十七：明确区分 automation dispatch 与 human manual dispatch。

    Deploy 的 workflow 事件本身是 workflow_dispatch，不能据此判断"是否人工"——
    真正的判据是触发链根的来源：
      - schedule                                  → automation（GitHub native）
      - repository_dispatch + external_scheduler  → automation（外部调度器）
      - workflow_dispatch / 其它                  → human
    返回 dict：mode / trigger_source / trigger_type / automation / human
    """
    inputs = inputs or {}
    payload = client_payload or {}
    if event_name == "schedule":
        return {"mode": "production", "trigger_source": "github_native_schedule",
                "trigger_type": "automation", "automation": True, "human": False}
    if event_name == "repository_dispatch":
        src = str(payload.get("trigger_source") or "").lower()
        if src == "external_scheduler":
            return {"mode": "production", "trigger_source": "external_scheduler",
                    "trigger_type": "automation", "automation": True, "human": False}
        # 未显式声明 external_scheduler 的 repository_dispatch：不承认 automation
        return {"mode": "shadow", "trigger_source": "repository_dispatch_unverified",
                "trigger_type": "human", "automation": False, "human": True}
    if str(inputs.get("canary") or "").lower() == "true":
        return {"mode": "production", "trigger_source": "manual_canary",
                "trigger_type": "human", "automation": False, "human": True}
    on = str(inputs.get("execute") or inputs.get("run_ai") or "").lower() == "true"
    src = str(inputs.get("source") or "").lower()
    if on or src == "production":
        return {"mode": "production", "trigger_source": "manual_dispatch_production",
                "trigger_type": "human", "automation": False, "human": True}
    return {"mode": "shadow", "trigger_source": "manual_dispatch_shadow",
            "trigger_type": "human", "automation": False, "human": True}


def _eligible_fids(kind, data_root):
    root = Path(data_root) if data_root else ROOT / "data"
    if kind == "social":
        p = root / "canonical" / "event_clusters.json"
        doc = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        return [e.get("event_id") for e in doc.get("items", [])
                if e.get("event_id") and e.get("current_policy_passed")]
    p = root / "disease" / "canonical" / "outbreak_events.json"
    doc = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return [d.get("disease_event_id") for d in doc.get("items", [])
            if d.get("disease_event_id")
            and str(d.get("outbreak_status")) in ("active", "monitoring", "declining")]


def new_eligible_exists(state, kind, data_root=None):
    """存在 eligible 且未处理（content hash 幂等）的条目 → AI 需要跑。"""
    pool = "social_enrichment" if kind == "social" else "disease_enrichment"
    processed = (state.get("processed_hashes") or {}).get(pool, {})
    for fid in _eligible_fids(kind, data_root):
        if fid not in processed:
            return True
    return False


def plan_due_tasks(state, now_bjt=None, schedule_enabled=True):
    """纯函数：依据 state + BJT now 计算 due 任务（不执行、不改 state）。"""
    now = now_bjt or datetime.now(BJT)
    if now.tzinfo is None:
        now = now.replace(tzinfo=BJT)
    if not schedule_enabled:
        return {"enabled": False, "due": [], "now_bjt": now.isoformat()}

    due = []

    def last(field):
        return _parse_iso(state.get(field))

    # Collection：距上次成功 ≥5h45m（首跑 None → due）
    lc = last("last_successful_collection")
    if lc is None or (now - lc) >= COLLECTION_MIN_GAP:
        due.append({"task": "collection", "mode": "production",
                    "trigger": "scheduled_orchestrator", "reason": "collection_gap"})

    # Disease：BJT 已过 01:30 且今天（BJT 日期）未跑
    ld = last("last_disease_run")
    ld_bjt = ld.astimezone(BJT) if ld else None
    if (now.hour, now.minute) >= DISEASE_TIME and (
            ld_bjt is None or ld_bjt.date() != now.date()):
        due.append({"task": "disease_ai", "mode": "production",
                    "trigger": "scheduled_orchestrator", "reason": "disease_daily_tick"})

    # Daily：BJT 已过 20:00 且今天（BJT 日期）未出报告
    lr = last("last_daily_report")
    lr_bjt = lr.astimezone(BJT) if lr else None
    if (now.hour, now.minute) >= DAILY_TIME and (
            lr_bjt is None or lr_bjt.date() != now.date()):
        due.append({"task": "daily_report", "mode": "production",
                    "trigger": "scheduled_orchestrator", "reason": "daily_20_00_tick"})

    # Weekly：BJT 周日 ≥06:45 且本周（BJT ISO 周）未出
    lw = last("last_weekly_report")
    lw_bjt = lw.astimezone(BJT) if lw else None
    if now.weekday() == 6 and (now.hour, now.minute) >= WEEKLY_TIME and (
            lw_bjt is None or lw_bjt.isocalendar()[:2] != now.isocalendar()[:2]):
        due.append({"task": "weekly_report", "mode": "production",
                    "trigger": "scheduled_orchestrator", "reason": "weekly_sunday_tick"})
    return {"enabled": True, "due": due, "now_bjt": now.isoformat()}


def _run_script(args, emit, timeout=1800):
    emit("$ python %s" % " ".join(args))
    try:
        r = subprocess.run([sys.executable] + args, cwd=str(ROOT),
                           capture_output=True, text=True, timeout=timeout)
        emit((r.stdout or "")[-2500:])
        if r.returncode != 0:
            emit("stderr: %s" % (r.stderr or "")[-800:])
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        emit("TIMEOUT %s" % args[0])
        return False
    except OSError as e:
        emit("OSError %s" % e)
        return False


def _env_json(name):
    """从环境变量读取 JSON（workflow 以 toJSON() 注入；'null'/空视为 {}）。"""
    raw = os.environ.get(name)
    if not raw or raw in ("null", "None"):
        return {}
    try:
        v = json.loads(raw)
        return v if isinstance(v, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _read_json_file(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _reload_state(state):
    """子进程（collection/enrichment/reports）各自 load→modify→save state。

    父进程若不重载，最终 save_state 会用陈旧内存覆盖子进程写入的
    processed_hashes —— 这正是 Observation V2 中同一 content 被重复送 AI
    （REPROCESSED_UNCHANGED_COUNT=13）的根因。故每个会写 state 的子进程
    返回后必须重载。
    """
    try:
        fresh = ps.load_state()
    except Exception:  # noqa: BLE001
        return state
    return fresh if isinstance(fresh, dict) and fresh else state


def _daily_report_meta(root):
    """读取本次 daily 报告的业务日期与分类（用于 deploy provenance / 新鲜度）。"""
    base = Path(root) / "runtime" / "ops" / "reports"
    if not base.exists():
        base = ps.OPS_DIR / "reports"
    summary = _read_json_file(base / "reports_run_summary.json") or {}
    daily = (summary.get("results") or {}).get("daily") or {}
    cls = daily.get("classification")
    report_date = None
    for p in sorted(base.glob("daily_*.json")):
        doc = _read_json_file(p) or {}
        if doc.get("report_date"):
            report_date = doc.get("report_date")
            break
    return {"report_date": report_date, "classification": cls,
            "fact_count": daily.get("fact_count")}


def execute(plan, state, data_root=None, emit=lambda s: print(s), canary=False,
            trigger_meta=None):
    """执行 due 任务（production mode）。

    返回 {deploy_required, deploy_request, executed, results}。
    §三：deploy_request 记录 provenance（trigger_type / root run id /
    report_date / classification / deploy_requested_at），下游据此区分
    automation dispatch 与 human manual dispatch。
    """
    tm = trigger_meta or resolve_trigger("schedule", {})
    trigger = "manual_canary" if canary else (tm.get("trigger_source")
                                              or "scheduled_orchestrator")
    root = Path(data_root) if data_root else ROOT / "data"
    run = ops.new_run("asip-production-orchestrator",
                      os.environ.get("GITHUB_RUN_ID") or "local")
    run["notes"].append("trigger=%s" % trigger)
    run["notes"].append("trigger_type=%s" % tm.get("trigger_type"))
    run["notes"].append("automation=%s" % str(bool(tm.get("automation"))).lower())
    run["notes"].append("human=%s" % str(bool(tm.get("human"))).lower())
    results = {}
    deploy_required = False
    deploy_ctx = {
        "trigger_type": tm.get("trigger_type"),
        "trigger_source": tm.get("trigger_source"),
        "automation": bool(tm.get("automation")),
        "human": bool(tm.get("human")),
        "mode": tm.get("mode"),
        "root_orchestrator_run_id": os.environ.get("GITHUB_RUN_ID") or None,
        "report_date": None,
        "report_classification": None,
        "deploy_requested_at": None,
    }

    def _do(task, label):
        # P0-1：嵌套函数内赋值外层变量必须声明 nonlocal，否则外层恒为 False，
        # 导致 publishable 报告也永远 deploy_required=false，Auto Deploy 全链路失效。
        nonlocal deploy_required
        nonlocal state
        results[label] = {"task": task, "trigger": trigger, "ok": False, "detail": None}
        if task == "collection":
            ok = _run_script(["scripts/ops/collection_run.py", "--execute"], emit)
            state = _reload_state(state)
            if ok:
                ps.record_run(state, "last_successful_collection", ok=True)
                # §十四：真实采集成功后刷新 source health 快照
                sh_ok = _run_script(["scripts/ops/source_health.py"], emit)
                results["source_health"] = {"ok": sh_ok,
                                            "detail": "source_health refresh"}
            m = _read_json_file(ps.OPS_DIR / "collection_summary.json") or {}
            results[label] = {"ok": ok, "detail": "collection_run --execute",
                              "metrics_source": m.get("metrics_source"),
                              "sources_configured": m.get("sources_configured"),
                              "sources_attempted": m.get("sources_attempted"),
                              "sources_succeeded": m.get("sources_succeeded"),
                              "sources_failed": m.get("sources_failed"),
                              "raw": m.get("articles_discovered"),
                              "new": m.get("published"),
                              "duplicates": m.get("duplicates"),
                              "held": m.get("quarantined")}
            # §十三：真实指标；读不到记 0 并标注 unavailable，绝不猜值
            run["sources_attempted"] = m.get("sources_attempted") or 0
            run["sources_succeeded"] = m.get("sources_succeeded") or 0
            run["sources_failed"] = m.get("sources_failed") or 0
            run["candidates_new"] = m.get("published") or 0
            if not m:
                run["notes"].append("collection_metrics_unavailable")
            elif m.get("metrics_source") == "unavailable":
                run["notes"].append("collection_metrics_unavailable")
            return ok
        if task == "social_ai":
            if not os.environ.get("ASIP_DEEPSEEK_API_KEY", "").strip():
                emit("CREDENTIAL_MISSING: skip social_ai (fail-closed, no fake)")
                results[label] = {"ok": False, "detail": "credential_missing"}
                return False
            if not new_eligible_exists(state, "social", root):
                emit("SOCIAL_AI_NO_NEW_ELIGIBLE -> 0 calls（合法跳过）")
                results[label] = {"ok": True, "detail": "no_new_eligible_zero_calls",
                                  "ai_calls": 0}
                return True
            ok = _run_script(["scripts/ops/enrichment_run.py", "--kind", "social"], emit)
            state = _reload_state(state)
            if ok:
                ps.record_run(state, "last_successful_ai", ok=True)
            s = _read_json_file(ps.OPS_DIR / "enrichment_summary_social.json") or {}
            results[label] = {"ok": ok, "detail": "enrichment_run social (real)",
                              "processed": s.get("processed"),
                              "skipped_unchanged": (s.get("skipped") or 0)
                              + (s.get("cached_same_input") or 0),
                              "skip_reason": "already_processed_same_input"
                              if (s.get("cached_same_input") or 0) else None,
                              "ai_calls": s.get("ai_calls"),
                              "input_tokens": s.get("input_tokens"),
                              "output_tokens": s.get("output_tokens"),
                              "total_tokens": s.get("total_tokens")}
            # §十五：AI 遥测取自真实 enrichment 结果
            run["ai_attempted"] += s.get("ai_calls") or 0
            run["ai_held"] += s.get("held") or 0
            run["safety_checked"] += (s.get("processed") or 0) + (
                s.get("cached_same_input") or 0)
            if s.get("ai_calls") or s.get("total_tokens"):
                tu = run.get("token_usage") or {}
                tu["social_enrichment"] = {
                    "calls": s.get("ai_calls") or 0,
                    "input_tokens": s.get("input_tokens") or 0,
                    "output_tokens": s.get("output_tokens") or 0,
                    "total_tokens": s.get("total_tokens") or 0}
                run["token_usage"] = tu
            return ok
        if task == "disease_ai":
            if not os.environ.get("ASIP_DEEPSEEK_API_KEY", "").strip():
                emit("CREDENTIAL_MISSING: skip disease_ai (fail-closed, no fake)")
                results[label] = {"ok": False, "detail": "credential_missing"}
                return False
            if not new_eligible_exists(state, "disease", root):
                emit("DISEASE_AI_NO_NEW_ELIGIBLE -> 0 calls（合法跳过）")
                results[label] = {"ok": True, "detail": "no_new_eligible_zero_calls",
                                  "ai_calls": 0}
                return True
            ok = _run_script(["scripts/ops/enrichment_run.py", "--kind", "disease"], emit)
            state = _reload_state(state)
            if ok:
                ps.record_run(state, "last_disease_run", ok=True)
            s = _read_json_file(ps.OPS_DIR / "enrichment_summary_disease.json") or {}
            results[label] = {"ok": ok, "detail": "enrichment_run disease (real)",
                              "processed": s.get("processed"),
                              "skipped_unchanged": (s.get("skipped") or 0)
                              + (s.get("cached_same_input") or 0),
                              "ai_calls": s.get("ai_calls"),
                              "total_tokens": s.get("total_tokens")}
            run["ai_attempted"] += s.get("ai_calls") or 0
            run["ai_held"] += s.get("held") or 0
            if s.get("ai_calls") or s.get("total_tokens"):
                tu = run.get("token_usage") or {}
                tu["disease_enrichment"] = {
                    "calls": s.get("ai_calls") or 0,
                    "input_tokens": s.get("input_tokens") or 0,
                    "output_tokens": s.get("output_tokens") or 0,
                    "total_tokens": s.get("total_tokens") or 0}
                run["token_usage"] = tu
            return ok
        if task == "timeline":
            return _run_script(["scripts/ops/timeline_run.py"], emit)
        if task == "daily_report":
            ok = _run_script(["scripts/ops/reports_run.py", "--mode", "daily",
                              "--source", "canonical"], emit)
            state = _reload_state(state)
            meta = _daily_report_meta(root)
            cls = meta.get("classification")
            results[label] = {"ok": ok, "detail": "daily canonical",
                              "classification": cls,
                              "report_date": meta.get("report_date"),
                              "fact_count": meta.get("fact_count")}
            if ok:
                ps.record_run(state, "last_daily_report", ok=True)
                deploy_required = deploy_required_for(cls)
                deploy_ctx["report_date"] = meta.get("report_date")
                deploy_ctx["report_classification"] = cls
                deploy_ctx["deploy_requested_at"] = ps._utcnow_iso()
            run["reports_%s" % {"FULL": "full", "FALLBACK": "fallback",
                                "LOW_DATA": "low_data", "HOLD": "hold"}.get(
                cls, "hold")] += 1
            return ok
        if task == "weekly_report":
            ok = True
            for mode in ("tcd_weekly", "ssd_weekly"):
                ok = _run_script(["scripts/ops/reports_run.py", "--mode", mode,
                                  "--source", "canonical"], emit) and ok
            state = _reload_state(state)
            summary = _read_json_file(ps.OPS_DIR / "reports"
                                      / "reports_run_summary.json") or {}
            wres = summary.get("results") or {}
            wcls = [v.get("classification") for v in wres.values()
                    if isinstance(v, dict)]
            if ok:
                ps.record_run(state, "last_weekly_report", ok=True)
                deploy_required = any(deploy_required_for(c) for c in wcls)
                deploy_ctx["report_classification"] = ",".join(
                    [c for c in wcls if c] or [])
                deploy_ctx["deploy_requested_at"] = ps._utcnow_iso()
            results[label] = {"ok": ok, "detail": "weekly canonical",
                              "classifications": wcls}
            return ok
        return False

    for t in plan["due"]:
        if t["task"] == "collection":
            ok = _do("collection", "collection")
            if ok:
                # 采集后重估 AI（新 eligible 可能出现）
                if new_eligible_exists(state, "social", root):
                    _do("social_ai", "social_ai")
                if new_eligible_exists(state, "disease", root):
                    _do("disease_ai", "disease_ai")
        elif t["task"] in ("social_ai", "disease_ai"):
            _do(t["task"], t["task"])
        elif t["task"] in ("daily_report", "weekly_report"):
            _do(t["task"], t["task"])
    results.setdefault("timeline", {"ok": _run_script(["scripts/ops/timeline_run.py"], emit),
                                    "detail": "timeline_run"})
    # canonical 变更后必须再生成遗留/公开视图（events.json / pending / raw / quarantine /
    # public/published_events / current_metrics），否则 deploy 的 V17 canonical↔legacy 校验失败
    results["views_export"] = {"ok": _export_views(emit), "detail": "compatibility_export"}

    ops.finish_run(run, status="completed")
    prev = []
    if ps.OPS_STATUS_FILE.exists():
        try:
            prev = json.loads(ps.OPS_STATUS_FILE.read_text(encoding="utf-8")).get("runs", [])
        except Exception:
            prev = []
    ops.save_ops(run, previous=prev[-20:])
    ps.save_state(state)
    emit("DEPLOY_REQUIRED = %s" % str(deploy_required).lower())
    emit("DEPLOY_PROVENANCE = %s" % json.dumps(deploy_ctx, ensure_ascii=False))
    return {"deploy_required": deploy_required, "deploy_request": deploy_ctx,
            "executed": [k for k in results], "results": results}


def _export_views(emit):
    """canonical → 遗留/公开视图单向再生成（V17 一致性 + 站点数据更新）。"""
    try:
        # scripts/data 模块按 scripts/ 与 scripts/data 双路径导入（pipeline_core / data.*）
        sys.path.insert(0, str(ROOT / "scripts"))
        sys.path.insert(0, str(ROOT / "scripts" / "data"))
        from scripts.data.repository import Repository
        from scripts.data.compatibility_export import export_all
        repo = Repository(root=ROOT / "data")
        stats = export_all(repo, run_id=os.environ.get("GITHUB_RUN_ID", ""))
        emit("VIEWS_EXPORT=%s" % json.dumps(stats, ensure_ascii=False))
        return True
    except Exception as e:  # noqa: BLE001
        emit("VIEWS_EXPORT_ERROR=%s" % e)
        return False


def _latest_report_class(root):
    """读取最近一次 daily 报告产物分类（从 reports_run_summary / gates 推导）。"""
    import json as _j
    p = Path(root) / "runtime" / "ops" / "reports" / "reports_run_summary.json"
    if not p.exists():
        p = ps.OPS_DIR / "reports" / "reports_run_summary.json"
    try:
        s = _j.loads(p.read_text(encoding="utf-8"))
        daily = (s.get("results") or {}).get("daily", {})
        return daily.get("classification")
    except Exception:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Stage8D hourly due-task orchestrator")
    ap.add_argument("--run", action="store_true", help="执行 due 任务")
    ap.add_argument("--plan", action="store_true", help="只输出计划（不执行）")
    ap.add_argument("--canary", action="store_true", help="manual canary 标记")
    ap.add_argument("--now", default=None, help="测试用 BJT now（ISO）")
    ap.add_argument("--state", default=None, help="state json 路径（默认 production_state）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    now = datetime.fromisoformat(args.now).astimezone(BJT) if args.now else datetime.now(BJT)
    state = ps.load_state()
    if args.state:
        state = json.loads(Path(args.state).read_text(encoding="utf-8"))
        base = dict(ps.EMPTY_STATE)
        base.update(state)
        state = base
    enabled = os.environ.get("PRODUCTION_SCHEDULE_ENABLED", "true").lower() != "false"
    # §三/§十七：触发来源解析（schedule / repository_dispatch+external_scheduler /
    # workflow_dispatch），用于区分 automation 与 human
    event_name = os.environ.get("GITHUB_EVENT_NAME", "schedule")
    client_payload = _env_json("ASIP_CLIENT_PAYLOAD")
    # workflow_dispatch 的 inputs（canary / source / execute …）由 workflow 以
    # ASIP_WORKFLOW_INPUTS 注入；缺失会导致 canary 被误判成 shadow。
    inputs = _env_json("ASIP_WORKFLOW_INPUTS")
    trigger_meta = resolve_trigger(event_name, inputs, client_payload)
    plan = plan_due_tasks(state, now_bjt=now, schedule_enabled=enabled)

    if args.plan or not args.run:
        out = {"trigger_mode": resolve_mode(
            os.environ.get("GITHUB_EVENT_NAME", "schedule"), {}),
            "now_bjt": now.isoformat(), "schedule_enabled": enabled,
            "trigger": trigger_meta, "plan": plan}
        if args.json:
            print(json.dumps(out, ensure_ascii=False, indent=1))
        else:
            print("TRIGGER=%s NOW=%s ENABLED=%s" % (
                out["trigger_mode"], now.isoformat(), enabled))
            for t in plan["due"]:
                print("  DUE %s (%s)" % (t["task"], t["reason"]))
        return 0

    # --run + --json：进度 emit 走 stderr，最终 JSON 只写 stdout（workflow 读取的必须是纯 JSON）
    def _emit(s):
        print(s, file=sys.stderr)

    res = execute(plan, state, emit=_emit, canary=args.canary,
                  trigger_meta=trigger_meta)
    if args.json:
        print(json.dumps({"deploy_required": res["deploy_required"],
                          "deploy_request": res["deploy_request"],
                          "executed": res["executed"], "results": res["results"]},
                         ensure_ascii=False, indent=1))
    return 0 if all(r.get("ok", False) for r in res["results"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
