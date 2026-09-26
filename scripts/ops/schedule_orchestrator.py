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
import hashlib
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
COLLECTION_MIN_GAP = timedelta(hours=2, minutes=45)  # C7-4 P6：2–3h 滚动 24h 情报面（原 5h45m）；容忍 ≤15min 抖动
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


#: AI 发布内容投影的落点（随 data/runtime/ops 提交进 production-state，跨轮持久）
AI_PUBLICATION_DIGEST = ps.OPS_DIR / "ai_publication_digest.json"


def ai_publication_projection(data_root):
    """公开产物中"AI 本地化/摘要"部分的稳定投影（C6-R5F）。

    背景：`deploy_required` 原先只由 daily / weekly 报告分类驱动，
    因此**仅有 AI 译文/摘要入库时不会触发部署**（实测 16:05 周期
    `deploy_required=false`，canonical title_cn 143→215 却无任何 deploy run）。

    本投影刻意只覆盖"已获得中文/摘要"的公开事件，且按 event_id 排序、剔除
    updated_at/run_id 等易变信封字段：
      - 新获得 title_cn/summary_cn（enrichment bridge 生效）→ 投影变化 → 触发部署；
      - 仅新增"未翻译"事件或重新导出（时间戳变化）→ 投影不变 → 不触发，
        维持原有"日报驱动"的部署节奏，避免每小时无意义部署。

    返回 (digest, localized_count)。文件缺失时返回 ("", 0)。
    """
    p = Path(data_root) / "public" / "published_events.json"
    if not p.exists():
        return "", 0
    try:
        items = json.loads(p.read_text(encoding="utf-8")).get("items", [])
    except Exception:  # noqa: BLE001
        return "", 0
    rows = sorted(
        (str(e.get("event_id") or ""),
         str(e.get("title_cn") or "").strip(),
         str(e.get("summary_cn") or "").strip())
        for e in items
        if str(e.get("title_cn") or "").strip() or str(e.get("summary_cn") or "").strip())
    # C7-3 P10：情报内容变更同样纳入发布触发投影 ——
    #   exec  = executive_summary 的研判内容与计数（排除 generated_time 等易变字段，防部署风暴）
    #   feed  = 情报流中已本地化条目数（新本地化 → 新可见内容）
    exec_sig, feed_loc = None, None
    try:
        ex = json.loads((Path(data_root) / "views" / "executive_summary.json")
                        .read_text(encoding="utf-8"))
        a = ex.get("assessment") or {}
        pt = ex.get("period") or {}
        exec_sig = [a.get("status") or "", str(a.get("overall_assessment") or "")[:400],
                    a.get("risk_direction") or "", pt.get("events_24h"),
                    pt.get("events_7d"), pt.get("active_countries_24h"),
                    pt.get("active_countries_7d")]
    except Exception:  # noqa: BLE001
        exec_sig = None
    try:
        ns = json.loads((Path(data_root) / "views" / "news_stream.json")
                        .read_text(encoding="utf-8"))
        feed_loc = sum(1 for x in (ns.get("items") or []) if x.get("localized"))
    except Exception:  # noqa: BLE001
        feed_loc = None
    # C7-5：首页情报视图的 AI 内容变更同样应触发发布（简报文本 + 关键计数）
    hp_sig = None
    try:
        hp = json.loads((Path(data_root) / "views" / "homepage_intelligence.json")
                        .read_text(encoding="utf-8"))
        # 以**整份视图**的稳定投影做签名（排除 generated_time 等易变字段）：
        # 原先只投影摘要/计数，地图国别、板块领域分析、重点动态、涉华条目、健康条目
        # 的变化都不会触发部署（实测：地图从 3 国修到 22 国后 deploy_required 仍为 false）。
        proj = {k: hp.get(k) for k in ("schema", "overview", "metrics", "sectors",
                                       "top_developments", "china_impact", "map",
                                       "health_security", "latest_intelligence", "reports")}
        if isinstance(proj.get("overview"), dict):
            proj["overview"] = {k: v for k, v in proj["overview"].items() if k != "generated_time"}
        hp_sig = hashlib.sha256(json.dumps(proj, ensure_ascii=False, sort_keys=True)
                                .encode("utf-8")).hexdigest()[:16]
    except Exception:  # noqa: BLE001
        hp_sig = None
    blob = json.dumps({"pub": rows, "exec": exec_sig, "feed_localized": feed_loc,
                       "homepage": hp_sig},
                      ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest(), len(rows)


def publication_change(data_root):
    """比对公开产物投影与上一轮记录；纯读 + 返回决策所需字段。

    返回 {"digest", "localized", "previous", "changed"}。

    首次运行（无历史记录）且**存在已本地化事件**时视为"未发布过"→ changed=True
    （这正是本修复落地的场景：站点上从未发布过这批译文，需要一次部署把它们上线）；
    若无任何已本地化事件则 changed=False，避免空部署。
    记录丢失最多导致一次幂等重复部署，不会造成循环。
    """
    digest, n = ai_publication_projection(data_root)
    prev = None
    try:
        if AI_PUBLICATION_DIGEST.exists():
            prev = json.loads(AI_PUBLICATION_DIGEST.read_text(encoding="utf-8")).get("digest")
    except Exception:  # noqa: BLE001
        prev = None
    if prev:
        changed = digest != prev
    else:
        changed = n > 0
    return {"digest": digest, "localized": n, "previous": prev, "changed": changed}


def record_publication_digest(info, recorded_at, emit=lambda s: print(s)):
    """把本轮投影写入 ops（随 production-state 提交）。

    时间戳由调用方注入（不在函数体内取墙钟）：digest 本身完全由公开内容决定，
    与时间无关 —— 这也让 `scripts/data/hash_audit.py` 的哈希契约审计可静态确认
    本函数产出的 digest 不受时间影响。
    """
    try:
        ps.OPS_DIR.mkdir(parents=True, exist_ok=True)
        AI_PUBLICATION_DIGEST.write_text(json.dumps({
            "digest": info.get("digest"),
            "localized_events": info.get("localized"),
            "previous_digest": info.get("previous"),
            "changed": bool(info.get("changed")),
            "recorded_at": recorded_at,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        emit("publication_digest_write_error=%s" % e)


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
    """读取本次 daily 报告的业务日期 / 分类 / report_id（deploy provenance 用）。"""
    base = Path(root) / "runtime" / "ops" / "reports"
    if not base.exists():
        base = ps.OPS_DIR / "reports"
    summary = _read_json_file(base / "reports_run_summary.json") or {}
    daily = (summary.get("results") or {}).get("daily") or {}
    cls = daily.get("classification")
    report_date, report_id = None, None
    for p in sorted(base.glob("daily_*.json")):
        doc = _read_json_file(p) or {}
        if doc.get("report_date"):
            report_date = doc.get("report_date")
            report_id = doc.get("report_id")
            break
    return {"report_date": report_date, "classification": cls,
            "report_id": report_id, "fact_count": daily.get("fact_count")}


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
    # C6-R5F：本轮是否运行过报告任务。报告分类是**权威可发布性闸门**，
    # 因此发布内容变更检测只在"本轮没有任何报告任务"时兜底触发部署，
    # 绝不覆盖 HOLD 等报告侧的拒绝判定。
    report_ran = False
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
        nonlocal report_ran
        results[label] = {"task": task, "trigger": trigger, "ok": False, "detail": None}
        if task == "collection":
            # C7-3 P1：外层超时 2760s > 采集器内层预算（wall-clock 2400s / 兜底 2700s），
            # 让兜底优雅停机先于外层硬杀生效（修复实测 1858/2631/1817s 三轮被 1800s 硬杀）。
            ok = _run_script(["scripts/ops/collection_run.py", "--execute"], emit,
                             timeout=2760)
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
            report_ran = True
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
                deploy_ctx["report_id"] = meta.get("report_id")
                deploy_ctx["report_classification"] = cls
                deploy_ctx["deploy_requested_at"] = ps._utcnow_iso()
            run["reports_%s" % {"FULL": "full", "FALLBACK": "fallback",
                                "LOW_DATA": "low_data", "HOLD": "hold"}.get(
                cls, "hold")] += 1
            return ok
        if task == "weekly_report":
            report_ran = True
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
    # C6-R5E：AI enrichment → 发布链桥接。
    # 把**已存在**的 AI 产物（data/runtime/ops/enrichment/S<event_id 末8位>_ok.json）中
    # safety.original_ai_output 的 title_zh/summary_zh 等回填进 canonical 事件行；
    # 否则 compatibility_export._published_from_cluster 取到的 title_cn/summary_cn 恒为空，
    # 译文与 AI 摘要永远到不了 public/published_events 与站点（实测 8/8 事件如此）。
    # 幂等（只填空白字段）、不生成 AI、不调外部模型（REAL_AI_CALLS=0）；必须早于 views_export。
    results["apply_enrichment"] = {
        "ok": _run_script(["scripts/ops/enrichment_bridge.py", "--apply"], emit),
        "detail": "enrichment_bridge"}
    # C7-3 P1：采集外层超时必须 > 采集器内层预算（wall-clock 2400s / 兜底 2700s），
    # 否则长采集轮次被外层硬杀（实测 1858/2631/1817s 三轮失败）。2760s 给兜底留出
    # 优雅停机窗口，且 46min + 下游 AI/报告/导出 ≈ 仍在编排 job 的 60min 之内。
    results["news_localization"] = {
        "ok": _run_script(["scripts/ops/news_localization_run.py"], emit,
                          timeout=2760),
        "detail": "news_localization"}
    # C7-5：先重建 C1A 情报流视图（news_stream）。
    # 此前只有站点构建阶段才会重建它，编排器里的 data/views/news_stream.json 长期停在
    # 陈旧快照（生产实测 generated=2026-09-23），导致每日研判与首页「24h 情报信号」恒为 0。
    # 构建器为确定性、无 AI 调用、实测约 1s。
    results["c1a_views"] = {
        "ok": _run_script(["tools/c1a/build_views.py"], emit, timeout=600),
        "detail": "c1a_views"}
    results["daily_assessment"] = {
        "ok": _run_script(["scripts/ops/assessment_run.py"], emit, timeout=900),
        "detail": "assessment_run"}
    # canonical 变更后必须再生成遗留/公开视图（events.json / pending / raw / quarantine /
    # public/published_events / current_metrics），否则 deploy 的 V17 canonical↔legacy 校验失败
    results["views_export"] = {"ok": _export_views(emit), "detail": "compatibility_export"}
    # C7-3 P9：情报板视图刷新（消费 assessment + feed），必须在 views_export 之后发布
    results["executive_view"] = {
        "ok": _run_script(["scripts/ops/executive_view.py", "--apply"], emit),
        "detail": "executive_view"}
    # C7-5：首页情报事实包 → 首页 AI 简报（6h 节奏 + input_hash 缓存；无实质变化则 REAL_AI_CALLS=0）
    #       → 首页公开视图（8 板块 + 风险/活动地图 + 情报流）。必须在 executive_view 之后。
    results["homepage_brief"] = {
        "ok": _run_script(["scripts/ops/homepage_brief_run.py"], emit, timeout=900),
        "detail": "homepage_brief"}
    results["homepage_view"] = {
        "ok": _run_script(["scripts/ops/homepage_view.py", "--apply"], emit),
        "detail": "homepage_view"}

    # C6-R5F：发布内容变更检测 → 让"仅 AI 译文/摘要入库"也能触发现有部署工作流。
    # 原判定只在 daily/weekly 报告分支里设置 deploy_required，因此富集桥接把
    # canonical title_cn 从 143 提到 215 也不会部署（实测 16:05 周期 deploy_required=false）。
    # 这里在导出**之后**比对公开产物的"已本地化投影"，仅在译文/摘要集合真正变化时置位。
    try:
        pub = publication_change(root)
        pub["ok"] = True
    except Exception as e:  # noqa: BLE001
        # 不静默：检测失败即标记 ok=False（main 的退出码聚合会据此失败，fail-closed）
        pub = {"ok": False, "changed": False, "digest": "", "localized": 0,
               "previous": None, "error": "%s: %s" % (type(e).__name__, e)}
    pub["detail"] = "publication_digest"
    results["publication_digest"] = pub
    if pub.get("changed") and not deploy_required and not report_ran:
        deploy_required = True
        deploy_ctx["reason"] = "ai_publication_changed"
        deploy_ctx["publication_localized_events"] = pub.get("localized")
        deploy_ctx["deploy_requested_at"] = ps._utcnow_iso()
    record_publication_digest(pub, ps._utcnow_iso(), emit)

    ops.finish_run(run, status="completed")
    # §K：deploy 请求与 provenance 持久化到 ops run（随 production-state 提交）。
    # dispatch 的 HTTP 结果由 workflow 步骤判定（非 2xx → 该轮 run 失败，不静默）。
    run["deploy_requested"] = bool(deploy_required)
    run["deploy_provenance"] = deploy_ctx
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
        # C6-R5F：Repository 的 root 语义是**仓库根**（canonical_dir = root/"data"/"canonical"）。
        # 原先传 ROOT/"data" 会解析成 data/data/... ⇒ 全部读取为空 ⇒ 导出静默 no-op
        # （实测 VIEWS_EXPORT 五项全 0；这也是 production-state 的 data/public 长期滞后于
        #  deploy 重建产物的原因）。与 build_site / collect / c3_run 等既有调用保持一致。
        repo = Repository(root=ROOT)
        # 信封 run_id 必须符合 ^\d{8}T\d{6}\+0800_[a-z0-9]{6}$：GITHUB_RUN_ID 是纯数字，
        # 直接用它会让 published_events 的保存整批中止（导出修好后才暴露的既有缺陷）。
        # 复用 build_site 的同一判据（canonical 既有 run_id > 按 BJT 生成），保持单一事实源。
        try:
            from scripts.build_site import _compliant_run_id
            export_run_id = _compliant_run_id()
        except Exception:  # noqa: BLE001
            export_run_id = ""
        stats = export_all(repo, run_id=export_run_id)
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
