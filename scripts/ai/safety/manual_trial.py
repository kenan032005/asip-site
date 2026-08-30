#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 8C Package 2 — Manual Human-Review Report Trial.

一次非发布的生产候选链执行（workflow_dispatch manual_trial）：

  Real Social/Disease Input（committed canonical 真实数据）
  → DeepSeek V4 Flash（thinking=disabled，Flash-only 门禁）
  → Deterministic Attribution Safety Layer（Stage8C Package1）
  → attribution_safety_gate → Report Input eligibility
  → Report Engine（Africa Daily / TCD Weekly / SSD Weekly，contract 冻结）
  → Human Review Pack + Artifacts + Telemetry

硬约束（Stage8C Package2 规格 §四-§十八）：
  - provider 仅 deepseek-v4-flash（Flash-only；pro/chat/reasoner 禁止）
  - thinking 全部 disabled；browser_direct_api_call=false
  - 不使用 qualification fixtures / golden set / mock / 编造 case
  - 输入 = 仓库内 committed 真实 canonical 数据（event_clusters /
    outbreak_events），经过 eligibility（current_policy_passed /
    outbreak_status）+ 时间窗口 + 去重
  - 任何 Safety Layer FAIL/HOLD/UNKNOWN 不得进入 Report Input
  - Report path（prompt/schema/envelope/assembler/metadata）零改动
  - 机器 Gate 若 FAIL：保留产物，标记 READY_FOR_HUMAN_REVIEW=false，
    不得自行修复或重跑
  - 不发布 Public、不开 schedule、不 deploy

用法：
  python scripts/ai/safety/manual_trial.py [--out-dir data/runtime/ai_safety/stage8c_trial]
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.ai.safety.attribution_safety import run_attribution_safety
from scripts.ai.schema_validation import validate_against_schema
from scripts.report.gen.assembler import assemble_report

SECRET_NAME = "ASIP_DEEPSEEK_API_KEY"
REPORT_TASK_TYPES = ("africa_daily", "country_weekly")

# §十：每份报告必须检查的机器 Gate 项
MACHINE_GATE_ITEMS = (
    "strict_json", "ai_content_schema", "assembler", "final_schema",
    "metadata", "numeric_evidence", "source_references", "attribution",
    "fact_assessment_outlook_separation")


def _bj_now():
    """当前北京时间 ISO（正确标注 +08:00）。

    旧实现为 `utcnow + 8h` 后仍带 +00:00 后缀，导致自然 Daily 报告的
    generated_at 被误标为 UTC（实际值是 BJT）。
    """
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone.utc).astimezone(
        timezone(timedelta(hours=8))).isoformat()


def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def credential_ok():
    return bool(os.environ.get(SECRET_NAME, "").strip())


# ────────────────────────────────────────────────────────────────────────────
# §五 真实输入构造（committed canonical；eligibility + 窗口 + 去重）
# ────────────────────────────────────────────────────────────────────────────

def _bj_business_date(dt):
    """运行时刻 → BJT 业务日期字符串（naive datetime 视为 BJT）。

    Stage8D P0-4：Africa Daily 运行在 BJT 20:00，报告业务日期必须是
    **当前 BJT business date**，不得读取历史 report date / fixture date /
    development date。
    """
    from datetime import datetime, timezone, timedelta
    if dt is None:
        dt = datetime.now(timezone.utc) + timedelta(hours=8)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)
    return dt.date().isoformat()


def _resolve_run_at(run_at=None):
    """解析报告运行时刻 → naive datetime（语义为北京时间）。"""
    from datetime import datetime, timezone, timedelta
    if run_at is None:
        return (datetime.now(timezone.utc) + timedelta(hours=8)).replace(tzinfo=None)
    if isinstance(run_at, datetime):
        return run_at.replace(tzinfo=None) if run_at.tzinfo else run_at
    try:
        d = datetime.fromisoformat(str(run_at).replace("Z", "+00:00"))
    except Exception:
        return (datetime.now(timezone.utc) + timedelta(hours=8)).replace(tzinfo=None)
    if d.tzinfo is not None:
        d = d.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)
    return d


def build_inputs(run_at=None):
    """从 committed canonical 真实数据构造 trial 输入。

    run_at：本次报告运行时刻（BJT，naive 或带 tz）。用于确定 report_date 与
    fact 时间窗口（§九/§十）。None → 取当前 BJT 时间。

    返回 dict：
      cutoff / social_candidates[] / disease_candidates[] /
      daily_input / weekly_tcd_input / weekly_ssd_input / stats
    """
    evs = load_json(ROOT / "data/canonical/event_clusters.json", {})
    dis = load_json(ROOT / "data/disease/canonical/outbreak_events.json", {})
    events = (evs or {}).get("items", [])
    diseases = (dis or {}).get("items", [])

    # eligibility：Social = current_policy_passed；Disease = active/monitoring/declining
    social_all = [e for e in events if e.get("current_policy_passed")]
    disease_all = [d for d in diseases
                   if d.get("outbreak_status") in ("active", "monitoring", "declining")]

    # 去重（by event_id / disease_event_id）
    seen_s, seen_d = set(), set()
    social = []
    for e in social_all:
        eid = e.get("event_id")
        if eid and eid not in seen_s:
            seen_s.add(eid)
            social.append(e)
    disease = []
    for d in disease_all:
        did = d.get("disease_event_id")
        if did and did not in seen_d:
            seen_d.add(did)
            disease.append(d)

    # cutoff（数据派生统计，仅用于 stats 展示）
    def _sort_key(e, fld):
        return str(e.get(fld) or "")
    social_sorted = sorted(social, key=lambda e: _sort_key(e, "event_time"), reverse=True)
    latest_social_ts = social_sorted[0]["event_time"] if social_sorted else _bj_now()
    disease_sorted = sorted(disease, key=lambda d: _sort_key(d, "report_date"), reverse=True)
    latest_disease_dt = disease_sorted[0]["report_date"] if disease_sorted else None
    cutoff = latest_social_ts

    # §九/§十：报告业务时刻 = 本次运行时刻（BJT）。report_date / period / fact
    # 窗口全部以此为准；cutoff 为数据派生值，不得再用于 report_date 或 period。
    run_dt = _resolve_run_at(run_at)

    # 时间窗口过滤（按 event_time；无时间戳的事件保留为候选——真实数据现状）
    def in_window(ts, win_hours, ref=None):
        if not ts:
            return True  # 无时间戳：如实保留（low-data 场景由 stats 说明）
        try:
            from datetime import datetime
            t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            t = t.replace(tzinfo=None)
            c = ref or run_dt
            delta = (c - t).total_seconds()
            return 0 <= delta <= win_hours * 3600 or delta < 0
        except Exception:
            return True

    # ── Africa Daily：24h 窗口（social + disease 混合）──
    daily_social = [e for e in social if in_window(e.get("event_time"), 24)]
    daily_disease = [d for d in disease if in_window(d.get("report_date") and
                                                     d.get("report_date") + "T00:00:00Z", 24 * 7)]
    # daily disease 窗口放宽到 7 天（通报周期），stats 如实标注
    daily = _build_daily_input(daily_social, daily_disease, run_dt)

    # ── TCD Weekly：7 天窗口（country_iso3=TCD）──
    tcd = [e for e in social if e.get("country_code") == "TD" and
           in_window(e.get("event_time"), 24 * 7)]
    tcd_dis = [d for d in disease if d.get("country_iso3") == "TCD" and
               in_window(d.get("report_date") and d.get("report_date") + "T00:00:00Z",
                         24 * 7)]
    weekly_tcd = _build_weekly_input("TCD", tcd, tcd_dis, run_dt)

    # ── SSD Weekly：7 天窗口（country_iso3=SSD，canonical 无事件 → low-data）──
    ssd = [e for e in social if e.get("country_code") == "SS" and
           in_window(e.get("event_time"), 24 * 7)]
    ssd_dis = [d for d in disease if d.get("country_iso3") == "SSD" and
               in_window(d.get("report_date") and d.get("report_date") + "T00:00:00Z",
                         24 * 7)]
    weekly_ssd = _build_weekly_input("SSD", ssd, ssd_dis, run_dt)

    stats = {
        "cutoff": cutoff,
        "latest_social_event_time": latest_social_ts,
        "latest_disease_report_date": latest_disease_dt,
        "social_eligible_total": len(social),
        "disease_eligible_total": len(disease),
        "daily_social_count": len(daily_social),
        "daily_disease_count": len(daily_disease),
        "weekly_tcd_social_count": len(tcd),
        "weekly_tcd_disease_count": len(tcd_dis),
        "weekly_ssd_social_count": len(ssd),
        "weekly_ssd_disease_count": len(ssd_dis),
        "country_coverage_social": sorted({e.get("country_code") for e in social}),
        "country_coverage_disease": sorted({d.get("country_iso3") for d in disease}),
        "source_coverage_social": _source_coverage(social),
        "source_coverage_disease": _source_coverage(disease),
        "input_source": "committed canonical (event_clusters.json / outbreak_events.json)",
        "fixtures_used": False,
        "golden_set_used": False,
        "mock_used": False,
    }
    return {"cutoff": cutoff, "social_candidates": social, "disease_candidates": disease,
            "daily_input": daily, "weekly_tcd_input": weekly_tcd,
            "weekly_ssd_input": weekly_ssd, "stats": stats}


def _source_coverage(items):
    from collections import Counter
    c = Counter()
    for it in items:
        sl = it.get("source_links") or it.get("sources") or []
        for s in sl if isinstance(sl, list) else []:
            if isinstance(s, dict) and s.get("source_name"):
                c[s["source_name"]] += 1
        if it.get("primary_source"):
            c[str(it["primary_source"])[:40]] += 1
    return dict(sorted(c.items(), key=lambda kv: -kv[1])[:12])


def _fact_item(e, kind):
    """canonical 事件 → report input item 结构（真实字段映射，不编造）。"""
    sl = e.get("source_links") or []
    src_ev = []
    if isinstance(sl, list):
        for s in sl:
            if isinstance(s, dict):
                src_ev.append({"source_id": (s.get("source_name") or "src")[:40],
                               "source_name": s.get("source_name") or "",
                               "url": s.get("url") or ""})
    return {
        "event_id": e.get("event_id") or e.get("disease_event_id"),
        # disease 项需保留 disease_event_id / disease_id（report-input 契约，
        # fact_pack._disease_fact 依赖之；缺失会导致 item_id/disease_id=null）
        "disease_event_id": e.get("disease_event_id"),
        "disease_id": e.get("disease_id"),
        "master_event_id": e.get("legacy_event_id"),
        "country": e.get("country_cn") or e.get("country_code"),
        "country_iso3": e.get("country_iso3") or (e.get("country_code") or "") + "?",
        "category": e.get("event_type") or e.get("disease_name_en"),
        "importance_score": e.get("importance_score") or 50,
        "change_type": e.get("event_status") or "new",
        "verification": e.get("verification_level") or e.get("verification_status"),
        "verification_confidence": e.get("verification_confidence"),
        "source_count": e.get("independent_source_count"),
        "single_source_warning": (e.get("verification_level") == "single_source" or
                                  e.get("independent_source_count") == 1 or
                                  e.get("verification_status") == "single_source"),
        "conflicting": bool(e.get("conflicting_fields")),
        "latest_update_at": e.get("event_time") or e.get("report_date"),
        "title": e.get("title_original") or e.get("title_cn") or e.get("disease_name_en"),
        "title_original": e.get("title_original") or e.get("title_cn"),
        "summary": e.get("summary_cn") or e.get("summary_original") or "",
        "body_extracted": (e.get("body_extracted") or "")[:1200],
        "facts": [{"fact": (e.get("title_cn") or e.get("summary_cn") or
                            e.get("disease_name_zh") or "")[:200],
                   "evidence": (e.get("body_extracted") or e.get("summary_original") or "")[:400]}],
        "uncertainties": [u for u in (e.get("uncertainties") or []) if u] or
                         [("单一来源" if e.get("verification_level") == "single_source"
                           else "信息尚未核实")],
        "source_evidence": src_ev,
        "kind": kind,
    }


def _build_daily_input(social, disease, cutoff):
    """Africa Daily report input（§五：真实事件，sections 契约冻结）。

    Stage8D P0-4：cutoff 为本次运行时刻（BJT，naive）。report_date 与 period
    由此动态推导 —— 不再使用任何 fixture / development 日期或周期。
    """
    from datetime import datetime, timedelta
    try:
        c = datetime.fromisoformat(str(cutoff).replace("Z", "+00:00"))
        c = c.replace(tzinfo=None) if c.tzinfo else c
    except Exception:
        c = _resolve_run_at(None)
    ps = (c - timedelta(hours=24)).isoformat()
    pe = c.isoformat()
    bdate = _bj_business_date(c)
    major = [_fact_item(e, "social") for e in social]
    dis_items = [_fact_item(d, "disease") for d in disease]
    return {
        "report_id": "DAILY_%s" % bdate.replace("-", ""),
        "report_type": "africa_daily",
        "report_name": "非洲地区社会安全与综合形势日报",
        "report_date": bdate,
        "cutoff": pe,
        "previous_cutoff": ps,
        "previous_report_id": None,
        "generated_at": _bj_now(),
        "period_start": ps,
        "period_end": pe,
        "sections": {
            "executive_summary": major,
            "major_security_developments": major,
            "political_social_stability": [],
            "terrorism_armed_violence": [],
            "cross_border_regional": [],
            "public_health_disease": dis_items,
            "key_changes": [],
            "watch_items": [],
            "source_notes": [],
        },
        "stats": {"eligible_events": len(social) + len(disease),
                  "single_source_events": sum(1 for i in major if i["single_source_warning"]),
                  "conflicting_events": sum(1 for i in major if i["conflicting"])},
    }


def _build_weekly_input(country, social, disease, cutoff):
    """country_weekly report input（country_iso3 / week_start / week_end 由 input 决定）。"""
    from datetime import datetime, timedelta
    try:
        c = datetime.fromisoformat(str(cutoff).replace("Z", "+00:00"))
    except Exception:
        c = datetime.utcnow()
    ws = (c - timedelta(days=7)).date().isoformat()
    we = c.date().isoformat()
    items = [_fact_item(e, "social") for e in social] + \
            [_fact_item(d, "disease") for d in disease]
    return {
        "report_id": "WEEKLY_%s_%s" % (country, we.replace("-", "")),
        "report_type": "country_weekly",
        "country_iso3": country,
        "week_start": ws,
        "week_end": we,
        "period_start": ws,
        "period_end": we,
        "generated_at": _bj_now(),
        "sections": {
            "weekly_executive_assessment": items,
            "major_events": items,
            "security_trend": items,
            "political_social_stability": [],
            "terrorism_armed_violence": [],
            "disease_public_health": [_fact_item(d, "disease") for d in disease],
            "changes_from_previous_week": [],
            "next_week_watch_items": [],
            "sources": [],
        },
        "trend_metrics": {},
    }


# ────────────────────────────────────────────────────────────────────────────
# §六 AI enrichment（Flash，thinking disabled）+ §六 Safety Layer
# ────────────────────────────────────────────────────────────────────────────

def _flash_provider():
    from scripts.ai.providers.deepseek_v4_flash import DeepSeekV4FlashProvider
    return DeepSeekV4FlashProvider()


def _enrich_prompt(task_type):
    """Social/Disease enrichment prompt（现有，冻结不修改）。"""
    if task_type == "disease_summary":
        from scripts.ai.glm_golden_set import _disease_glm_system_prompt
        return _disease_glm_system_prompt(), "disease-summary-v1.0.1"
    from scripts.ai.glm_golden_set import _glm_system_prompt
    return _glm_system_prompt(), "stage4-enrichment-v1.0.1"


def _enrich_schema(task_type):
    if task_type == "disease_summary":
        return load_json(ROOT / "schemas/disease_ai_summary.schema.json")
    return load_json(ROOT / "schemas/ai_enrichment_payload.schema.json")


def _strict_json_parse(text):
    if not text or not isinstance(text, str):
        return False, None, "empty"
    t = text.strip()
    if "```" in t:
        return False, None, "markdown_fence"
    try:
        return True, json.loads(t), None
    except Exception as e:
        return False, None, "not_json:%s" % str(e)[:60]


def enrich_and_safe(prov, task_type, payload, label, telemetry, use_cache=True):
    """单条 fact：Flash enrichment → Safety Layer → gate。返回 record dict。

    Stage8D P0-2：接入 scripts/ai/ai_result_cache —— 同一 ai_input_hash
    （fact payload + schema/prompt version + model，剔除 run_id/时间戳等易变字段）
    命中已成功缓存时直接复用 provider 结果，**不调用 API、不计费**。
    """
    sys_text, pv = _enrich_prompt(task_type)
    model = "deepseek-v4-flash"
    out_schema_version = "1.1"
    ai_hash, cache_key = None, None
    if use_cache:
        try:
            from scripts.ai import ai_input_identity as ident
            ai_hash = ident.ai_input_hash(
                payload, task_type=task_type, model=model, prompt_version=pv,
                output_schema_version=out_schema_version)
            cache_key = ident.build_cache_key(ai_hash, task_type, model)
        except Exception:  # noqa: BLE001 — 身份计算失败退化为不缓存（安全侧：宁可重算）
            ai_hash, cache_key = None, None
    task = {
        "task_id": "TRIAL_ENRICH_%s" % label,
        "task_type": task_type,
        "prompt_version": pv,
        "output_schema_version": out_schema_version,
        "content_hash": ai_hash or "",
        "cache_key": cache_key or "",
        "system_text": sys_text,
        "user_text": "INPUT:\n" + json.dumps(payload, ensure_ascii=False)[:6000],
        "usage_purpose": "development_report_trial",
        "max_output_tokens": 2048,
    }
    t = telemetry.setdefault(task_type, {"calls": 0, "input_tokens": 0,
                                         "output_tokens": 0, "total_tokens": 0,
                                         "finish_reasons": [], "thinking": [],
                                         "cache_hits": 0, "cache_misses": 0,
                                         "skipped_same_input": 0})
    t.setdefault("cache_hits", 0)
    t.setdefault("cache_misses", 0)
    t.setdefault("skipped_same_input", 0)

    res, cache_hit = None, False
    if cache_key:
        try:
            from scripts.ai import ai_result_cache
            entry = ai_result_cache.get_cache_entry(cache_key)
            # 显式身份交叉校验（等价 check_cache_hit 的 identity 部分）：
            # 注：check_cache_hit 额外做 business output 契约校验，而
            # stage4_event_enrichment / disease_summary 未注册 prompt package，
            # 该项恒失败；故此处逐项比对身份字段，任一项变化即失效重算。
            if isinstance(entry, dict) and isinstance(entry.get("result"), dict):
                same = (
                    entry.get("task_type") == task.get("task_type")
                    and entry.get("prompt_version") == task.get("prompt_version")
                    and entry.get("output_schema_version") == task.get(
                        "output_schema_version")
                    and entry.get("content_hash") == task.get("content_hash")
                    and (entry.get("result") or {}).get("status") is not None
                )
                if same:
                    # 缓存条目中 result 存的是完整 provider 响应
                    res = entry["result"]
                    cache_hit = True
                    t["cache_hits"] += 1
                    t["skipped_same_input"] += 1
        except Exception:  # noqa: BLE001 — 缓存不可用时退化为真实调用
            res = None

    if res is None:
        res = prov.submit_task(task)
        t["calls"] += 1
        t["cache_misses"] += 1
        rr0 = res.get("result") or {}
        t["input_tokens"] += rr0.get("input_tokens") or 0
        t["output_tokens"] += rr0.get("output_tokens") or 0
        t["total_tokens"] += rr0.get("total_tokens") or 0
        t["finish_reasons"].append(rr0.get("finish_reason"))
        t["thinking"].append(rr0.get("thinking_requested"))
        if cache_key and res.get("status") == "succeeded":
            try:
                import hashlib as _hl
                from scripts.ai import ai_result_cache
                ai_result_cache.write_cache_entry(task, res, {
                    "prompt_checksum": _hl.sha256(
                        sys_text.encode("utf-8")).hexdigest(),
                    "render_hash": _hl.sha256(
                        (task["user_text"] or "").encode("utf-8")).hexdigest(),
                    "prompt_variables_digest": ai_hash or "",
                    "source": "manual_trial.enrich_and_safe",
                }, _bj_now())
            except Exception:  # noqa: BLE001 — 写缓存失败不影响主流程
                pass
    elif cache_hit:
        # 复用缓存：不重复计费，仅记录 finish_reason 用于审计
        t["finish_reasons"].append((res.get("result") or {}).get("finish_reason"))
        t["thinking"].append((res.get("result") or {}).get("thinking_requested"))

    rr = res.get("result") or {}
    rec = {"label": label, "task_type": task_type,
           "requested_model": model,
           "returned_model": rr.get("returned_model"),
           "provider_status": res.get("status"),
           "finish_reason": rr.get("finish_reason"),
           "thinking_requested": rr.get("thinking_requested"),
           "reasoning_tokens": rr.get("reasoning_tokens"),
           "cache_hit": cache_hit,
           "ai_input_hash": ai_hash,
           "tokens": {"input_tokens": rr.get("input_tokens") if not cache_hit else 0,
                      "output_tokens": rr.get("output_tokens") if not cache_hit else 0,
                      "total_tokens": rr.get("total_tokens") if not cache_hit else 0}}
    if res.get("status") != "succeeded":
        rec["status"] = "provider_failed"
        rec["error"] = ((rr.get("error") or {}).get("code") or "unknown")
        return rec
    returned = rr.get("returned_model")
    from scripts.ai.providers.deepseek_v4_flash import ALLOWED_DEEPSEEK_MODELS
    if returned and returned not in ALLOWED_DEEPSEEK_MODELS:
        rec["status"] = "model_mismatch"
        return rec
    raw = rr.get("text") or ""
    ok, parsed, jerr = _strict_json_parse(raw)
    if not ok:
        rec["status"] = "invalid_response_shape"
        rec["error"] = jerr
        return rec
    schema = _enrich_schema(task_type)
    serr = validate_against_schema(parsed, schema) if schema else []
    rec["schema_pass"] = not serr
    if serr:
        rec["status"] = "schema_failure"
        rec["schema_errors"] = serr[:5]
        return rec
    # ── Safety Layer（§六）──
    safe = run_attribution_safety(payload, parsed, task_type)
    rec["status"] = "ok" if safe["attribution_safety_gate"] == "PASS" else "safety_hold"
    rec["safety"] = {
        "gate": safe["attribution_safety_gate"],
        "pre_status": safe["validator_pre_correction"]["status"],
        "corrections": safe["corrections"],
        "post_status": (safe["validator_post_correction"] or {}).get("status"),
        "publication_eligible": safe["publication_eligible"],
        "report_input_eligible": safe["report_input_eligible"],
        "manual_review_required": safe["manual_review_required"],
        "original_ai_output": safe["original_ai_output"],
        "corrected_output": safe["corrected_output"],
    }
    return rec


# ────────────────────────────────────────────────────────────────────────────
# §四/§五（Repair）：Provenance-Aware Numeric Gate
# ────────────────────────────────────────────────────────────────────────────

_METADATA_DATE_FIELDS = ("week_start", "week_end", "report_date", "period_start",
                         "period_end", "cutoff", "previous_cutoff", "generated_at",
                         "event_time", "latest_update_at", "first_seen_at",
                         "created_at", "updated_at", "report_timezone")
_IDENTIFIER_FIELDS = ("event_id", "master_event_id", "disease_event_id",
                      "report_id", "item_id", "brief_id", "source_id",
                      "legacy_event_id", "legacy_report_id", "previous_report_id",
                      "source_refs", "url")
# Machine envelope is validated by metadata/schema gates, not factual numeric
# provenance. Keep semantic report dates in scope for METADATA_DATE_NUMBER.
_MACHINE_METADATA_FIELDS = frozenset((
    "report_id", "brief_id", "model_name", "prompt_version", "prompt_hash",
    "generated_at", "usage_purpose", "provider_name", "provider_metadata",
    "execution_mode", "execution_metadata", "schema_version", "version",
))
_MACHINE_METADATA_SEGMENTS = frozenset((
    "generation_metadata", "provider_metadata", "execution_metadata",
))
_DISEASE_COUNT_FIELDS = ("confirmed_cases", "probable_cases", "suspected_cases",
                         "total_cases", "deaths", "recoveries")
_EVENT_COUNT_FIELDS = ("event_count", "verified_event_count", "armed_attack_count",
                       "civil_unrest_count", "major_crime_count",
                       "natural_disaster_count", "multi_source_event_count",
                       "new_outbreak_count", "active_outbreak_count",
                       "importance_score")
_NUM_RE = re.compile(r"\d[\d,]*")


def _infer_semantic(sec, field):
    """字符串字段数字的语义类型推断（§四）。"""
    if field in _DISEASE_COUNT_FIELDS:
        return "death_count" if field == "deaths" else "case_count"
    if field in _EVENT_COUNT_FIELDS:
        return "event_magnitude"
    if "date" in field or "time" in field or "week" in field or "period" in field:
        return "metadata_date"
    return "event_magnitude"


def _collect_input_provenance(report_input):
    """收集 input 数字 provenance：{value: [ {input_field_path, semantic_type,
    fact_id} ]}。identifier 内数字记 identifier（不作事实证据）。"""
    prov = {}

    def add(val, path, sem, fid=None):
        try:
            n = int(str(val).replace(",", ""))
        except (TypeError, ValueError):
            return
        if not isinstance(n, int):
            return
        prov.setdefault(n, []).append(
            {"input_field_path": path, "semantic_type": sem, "fact_id": fid})

    # top-level metadata 日期字段（§五：metadata/date provenance）
    for f in _METADATA_DATE_FIELDS:
        v = report_input.get(f)
        if isinstance(v, str):
            for m in _NUM_RE.findall(v):
                add(m, f, "metadata_date")
        elif isinstance(v, (int, float)):
            add(v, f, "metadata_date")

    # sections items（事件/疾病事实）
    sections = report_input.get("sections") or {}
    for sec, items in sections.items():
        if not isinstance(items, list):
            continue
        for i, it in enumerate(items):
            if not isinstance(it, dict):
                continue
            fid = (it.get("event_id") or it.get("disease_event_id")
                   or it.get("master_event_id") or it.get("item_id"))
            for k, v in it.items():
                path = "sections.%s[%d].%s" % (sec, i, k)
                if k in _IDENTIFIER_FIELDS:
                    for m in _NUM_RE.findall(str(v)):
                        add(m, path, "identifier", fid)
                elif k in _DISEASE_COUNT_FIELDS:
                    add(v, path, _infer_semantic(sec, k), fid)
                elif k in _EVENT_COUNT_FIELDS:
                    add(v, path, "event_magnitude", fid)
                elif isinstance(v, str):
                    sem = _infer_semantic(sec, k)
                    for m in _NUM_RE.findall(v):
                        add(m, path, sem, fid)

    # trend_metrics / stats
    for f in ("trend_metrics", "stats"):
        v = report_input.get(f) or {}
        if isinstance(v, dict):
            for k, vv in v.items():
                if isinstance(vv, (int, float)) and not isinstance(vv, bool):
                    add(vv, "%s.%s" % (f, k), "event_magnitude")
    return prov


def _numeric_provenance_check(report, report_input):
    """provenance-aware numeric gate（§四/§五）。

    对报告中每个数字判定 provenance：
      - identifier 字段数字（item_id/report_id 等）→ 不检查
      - 匹配 input metadata 日期 → METADATA_DATE_NUMBER
      - 匹配 input 事实数字 → SUPPORTED_INPUT_NUMBER
      - 无匹配 → TRUE_UNSUPPORTED_AI_NUMBER（numeric_evidence=FAIL）
    返回 (ok, entries[], unsupported[])。
    """
    in_prov = _collect_input_provenance(report_input)
    entries, unsupported = [], []

    def classify(n, path):
        parts = [p.split("[", 1)[0] for p in path.split(".") if p]
        leaf = parts[-1] if parts else ""
        if leaf in _MACHINE_METADATA_FIELDS or any(
                segment in _MACHINE_METADATA_SEGMENTS for segment in parts):
            return
        if any(f in leaf for f in ("item_id", "report_id", "brief_id",
                                   "master_event_id", "source_id",
                                   "event_id", "disease_event_id")):
            return
        matches = in_prov.get(n, [])
        best = None
        for m in matches:
            if m["semantic_type"] in ("identifier",):
                continue
            best = m
            if m["semantic_type"] not in ("metadata_date",):
                break
        if best is None:
            unsupported.append({"output_value": n, "output_field": path})
            entries.append({"output_value": n, "output_field": path,
                            "matched_input_value": None,
                            "matched_input_path": None,
                            "semantic_type": "unsupported"})
        else:
            entries.append({"output_value": n, "output_field": path,
                            "matched_input_value": n,
                            "matched_input_path": best["input_field_path"],
                            "semantic_type": best["semantic_type"]})

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, "%s.%s" % (path, k) if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, "%s[%d]" % (path, i) if path else "[%d]" % i)
        elif isinstance(node, str):
            for m in _NUM_RE.findall(node):
                classify(int(m.replace(",", "")), path or "text")
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            classify(int(node), path or "value")

    walk(report, "")
    return (not unsupported, entries, unsupported)


# ────────────────────────────────────────────────────────────────────────────
# §八 Report Engine（contract 冻结）+ §十 机器 Gate
# ────────────────────────────────────────────────────────────────────────────

def generate_report(prov, task_type, report_input, prompt_file, label, telemetry,
                    raw_path=None):
    """单份报告：Flash → AI content → assembler → final schema → quality gate。

    §一（Repair）：usage_purpose 以 final schema const 为 source of truth
    （development_test）；Manual Trial 身份存 execution_mode（不污染 schema）。
    §二（Repair）：Quality Gate 内部异常 → machine_gate=FAIL /
    quality_status=gate_exception，绝不 false PASS。
    §四（Repair）：numeric gate 用 provenance-aware 检查（替代粗粒度比较）。
    """
    from scripts.report.gen.quality import run_quality_gate
    sys_text = Path(prompt_file).read_text(encoding="utf-8")
    pv = "v1.0.3"
    task = {
        "task_id": "TRIAL_REPORT_%s" % label,
        "task_type": task_type,
        "prompt_version": pv,
        "system_text": sys_text,
        "user_text": "INPUT:\n" + json.dumps(report_input, ensure_ascii=False)[:9000],
        "usage_purpose": "development_report_trial",
        "max_output_tokens": 8192 if task_type == "africa_daily" else 6144,
    }
    t = telemetry.setdefault(task_type, {"calls": 0, "input_tokens": 0,
                                         "output_tokens": 0, "total_tokens": 0,
                                         "finish_reasons": [], "thinking": []})
    res = prov.submit_task(task)
    t["calls"] += 1
    rr = res.get("result") or {}
    t["input_tokens"] += rr.get("input_tokens") or 0
    t["output_tokens"] += rr.get("output_tokens") or 0
    t["total_tokens"] += rr.get("total_tokens") or 0
    t["finish_reasons"].append(rr.get("finish_reason"))
    t["thinking"].append(rr.get("thinking_requested"))

    out = {"label": label, "task_type": task_type,
           "requested_model": "deepseek-v4-flash",
           "returned_model": rr.get("returned_model"),
           "finish_reason": rr.get("finish_reason"),
           "thinking_requested": rr.get("thinking_requested"),
           "reasoning_tokens": rr.get("reasoning_tokens"),
           "tokens": {"input_tokens": rr.get("input_tokens"),
                      "output_tokens": rr.get("output_tokens"),
                      "total_tokens": rr.get("total_tokens")},
           "machine_gate": {k: None for k in MACHINE_GATE_ITEMS},
           "machine_gate_status": None}
    if res.get("status") != "succeeded":
        out["status"] = "provider_failed"
        out["error"] = ((rr.get("error") or {}).get("code") or "unknown")
        return out
    from scripts.ai.providers.deepseek_v4_flash import ALLOWED_DEEPSEEK_MODELS
    if rr.get("returned_model") and rr["returned_model"] not in ALLOWED_DEEPSEEK_MODELS:
        out["status"] = "model_mismatch"
        return out
    raw = rr.get("text") or ""
    # Preserve provider evidence before any parse/schema gate can reject it.
    out["raw_content"] = raw
    out["raw_content_length"] = len(raw)
    out["raw_response"] = {
        "raw_content": raw,
        "raw_content_length": len(raw),
        "finish_reason": rr.get("finish_reason"),
        "requested_model": out["requested_model"],
        "returned_model": rr.get("returned_model"),
        "token_usage": out["tokens"],
    }
    if raw_path is not None:
        Path(raw_path).write_text(json.dumps(out["raw_response"],
                                             ensure_ascii=False, indent=1) + "\n",
                                  encoding="utf-8")
    ok, parsed, jerr = _strict_json_parse(raw)
    out["strict_json"] = ok
    out["machine_gate"]["strict_json"] = ok
    if ok:
        out["parsed_ai_content"] = parsed
    if not ok:
        out["status"] = "invalid_response_shape"
        out["error"] = jerr
        out["machine_gate_status"] = "FAIL"
        return out

    # AI content schema（report-specific ai_content schema）
    ai_schema = load_json(ROOT / "schemas" / ("%s_ai_content.schema.json" % task_type))
    aerr = validate_against_schema(parsed, ai_schema, resolve_refs=True) if ai_schema else []
    out["ai_content_schema_pass"] = not aerr
    out["machine_gate"]["ai_content_schema"] = not aerr
    if aerr:
        out["status"] = "ai_content_schema_failure"
        out["schema_errors"] = aerr[:5]
        out["schema_failure_evidence"] = {
            "field_errors": aerr[:20],
            "raw_excerpt": raw[:1200],
            "raw_content_length": len(raw),
        }
        out["machine_gate_status"] = "FAIL"
        return out

    # Assembler（envelope 确定性合并；usage_purpose=development_test 满足 final
    # schema const；Manual Trial 身份存 execution_mode，不污染正式 schema）
    meta = {"provider_name": "deepseek", "model_name": "deepseek-v4-flash",
            "prompt_version": pv, "usage_purpose": "development_test",
            "report_status": "draft"}
    try:
        final = assemble_report(task_type, report_input, parsed, meta)
        out["assembler_pass"] = True
        out["machine_gate"]["assembler"] = True
    except Exception as e:
        out["assembler_pass"] = False
        out["machine_gate"]["assembler"] = False
        out["status"] = "assembler_failure"
        out["error"] = str(e)[:120]
        out["machine_gate_status"] = "FAIL"
        return out
    out["assembled_report"] = final
    out["execution_mode"] = "manual_human_review_trial"

    # Final schema（report output schema）
    ferr = validate_against_schema(final, load_json(
        ROOT / "schemas" / ("%s_report.schema.json" % task_type)), resolve_refs=True)
    out["final_schema_pass"] = not ferr
    out["machine_gate"]["final_schema"] = not ferr
    if ferr:
        out["final_schema_errors"] = ferr[:5]

    # metadata gate：envelope 字段以 input 为准（assembler 已保证；此处回读校验）
    md_ok, md_errs = _metadata_gate(final, report_input, task_type)
    out["metadata_gate"] = md_ok
    out["machine_gate"]["metadata"] = md_ok
    if md_errs:
        out["metadata_errors"] = md_errs[:5]

    # §四（Repair）：provenance-aware numeric gate（替代粗粒度数字比较）
    num_ok, num_entries, num_unsupported = _numeric_provenance_check(final, report_input)
    out["numeric_provenance"] = num_entries
    out["numeric_unsupported"] = num_unsupported
    out["machine_gate"]["numeric_evidence"] = num_ok
    if num_unsupported:
        out["numeric_issues"] = ["unsupported_ai_number: %d (%s)" % (
            e["output_value"], e["output_field"]) for e in num_unsupported[:10]]

    # §二（Repair）：Quality Gate fail-closed——异常 → FAIL + gate_exception
    gate_exc = None
    try:
        qpassed, qstatus, qissues, qwarns = run_quality_gate(final, report_input, task_type)
    except Exception as e:
        qpassed, qstatus, qissues = False, "gate_exception", []
        gate_exc = {"gate_name": "run_quality_gate",
                    "exception_type": type(e).__name__,
                    "exception_message": str(e)[:160]}
    out["quality_status"] = qstatus if qpassed else "failed_quality_gate"
    if gate_exc:
        out["quality_status"] = "gate_exception"
        out["gate_exception"] = gate_exc
        out["quality_issues"] = ["quality gate exception: %s: %s" % (
            gate_exc["exception_type"], gate_exc["exception_message"])]
    else:
        out["quality_issues"] = (qissues or [])[:12]
    if gate_exc:
        out["machine_gate"]["source_references"] = False
        out["machine_gate"]["fact_assessment_outlook_separation"] = False
    else:
        out["machine_gate"]["source_references"] = not any(
            "source" in str(i) for i in (qissues or []))
        out["machine_gate"]["fact_assessment_outlook_separation"] = not any(
            "separat" in str(i) or "malformed" in str(i) for i in (qissues or []))
    # 归因（报告级）：input 含 marker 而报告丢失 → attribution gate 失败
    from scripts.ai.qualification.stage8b import check_attribution
    aok, aerr2 = check_attribution(json.dumps(report_input, ensure_ascii=False),
                                   json.dumps(final, ensure_ascii=False))
    out["attribution_pass"] = aok
    out["machine_gate"]["attribution"] = aok
    if not aok:
        out["attribution_error"] = aerr2

    fails = [k for k, v in out["machine_gate"].items() if v is False]
    out["machine_gate_status"] = "PASS" if not fails else "FAIL"
    out["status"] = "ok" if out["machine_gate_status"] == "PASS" else "machine_gate_fail"
    return out


def _metadata_gate(final, report_input, task_type):
    """envelope 字段必须以 input 为准（metadata cannot be overridden by AI）。"""
    errs = []
    for f in ("report_id", "report_type"):
        if report_input.get(f) and final.get(f) != report_input.get(f):
            errs.append("%s mismatch: %s != %s" % (f, final.get(f), report_input.get(f)))
    if task_type == "africa_daily":
        if report_input.get("period_start") and final.get("period_start") != report_input.get("period_start"):
            errs.append("period_start mismatch")
        if report_input.get("period_end") and final.get("period_end") != report_input.get("period_end"):
            errs.append("period_end mismatch")
        if report_input.get("report_date") and final.get("report_date") != report_input.get("report_date"):
            errs.append("report_date mismatch")
    elif task_type == "country_weekly":
        if report_input.get("week_start") and final.get("week_start") != report_input.get("week_start"):
            errs.append("week_start mismatch")
        if report_input.get("week_end") and final.get("week_end") != report_input.get("week_end"):
            errs.append("week_end mismatch")
        if report_input.get("country_iso3") and final.get("country_iso3") != report_input.get("country_iso3"):
            errs.append("country_iso3 mismatch")
    return (not errs, errs)


# ────────────────────────────────────────────────────────────────────────────
# §十一 Human Review Pack
# ────────────────────────────────────────────────────────────────────────────

def _report_input_unique_count(report_input):
    """Count canonical facts once across repeated report sections."""
    seen = set()
    anonymous = 0
    sections = (report_input or {}).get("sections") or {}
    for items in sections.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            fid = (item.get("event_id") or item.get("disease_event_id")
                   or item.get("master_event_id") or item.get("item_id"))
            if fid:
                seen.add(str(fid))
            else:
                anonymous += 1
    return len(seen) + anonymous


def _eligible_record_count(enrichment):
    """Count distinct Safety-passed records without cross-type double counting."""
    seen = set()
    for rec in enrichment or []:
        safe = rec.get("safety") or {}
        if rec.get("status") != "ok" or safe.get("gate") != "PASS":
            continue
        fid = rec.get("event_id") or rec.get("disease_event_id") or rec.get("label")
        seen.add((rec.get("task_type"), str(fid)))
    return len(seen)


def build_human_review_pack(inputs, enrichment, reports, stats, out_dir,
                            safety_stats=None, schema_held=None):
    safety_stats = safety_stats or {}
    schema_held = schema_held or []
    report_input_accepted = _eligible_record_count(enrichment)
    md = ["# ASIP Stage 8C Package 2 — Manual Human Review Pack",
          "",
          "> 由 ChatGPT + 用户人工裁定内容质量。WorkBuddy 不判定 HUMAN_CONTENT_PASS。",
          "",
          "## REPORT_METADATA",
          "",
          "| 项 | 值 |",
          "| --- | --- |",
          "| trial_type | manual_trial |",
          "| model | deepseek-v4-flash |",
          "| thinking | disabled（全部） |",
          "| cutoff | %s |" % stats.get("cutoff"),
          "| input_record_count | %d" % (stats.get("social_eligible_total", 0) +
                                         stats.get("disease_eligible_total", 0)),
          "| social_count | %d |" % stats.get("social_eligible_total"),
          "| disease_count | %d |" % stats.get("disease_eligible_total"),
          "| country coverage | %s |" % ",".join(stats.get("country_coverage_social") or []),
          "| source coverage | %s |" % ",".join(
              list((stats.get("source_coverage_social") or {}).keys())[:6]),
          "| fixtures/golden/mock | 否 |",
          "",
          "## HUMAN_REVIEW_COMPLETENESS（§十二：区分「模型没写」与「上游被 Gate 拦住」）",
          "",
          "```json",
          json.dumps({
              "input_records_total": (stats.get("social_eligible_total", 0) +
                                      stats.get("disease_eligible_total", 0)),
              "input_records_accepted": report_input_accepted,
              "enrichment_schema_held": len(schema_held),
              "attribution_held": (
                  (safety_stats.get("social") or {}).get("attribution_hold", 0) +
                  (safety_stats.get("disease") or {}).get("attribution_hold", 0)),
              "held_records": schema_held,
          }, ensure_ascii=False, indent=1),
          "```",
          ""]
    for label, r in (("africa_daily", reports.get("africa_daily")),
                     ("tcd_weekly", reports.get("tcd_weekly")),
                     ("ssd_weekly", reports.get("ssd_weekly"))):
        md += ["## %s" % label.upper(), "",
               "### INPUT_FACTS",
               "```json\n%s\n```" % json.dumps(
                   {"report_id": r["report_input"].get("report_id"),
                    "sections_summary": {k: len(v) for k, v in
                                         (r["report_input"].get("sections") or {}).items()}},
                   ensure_ascii=False, indent=1),
               "### SAFETY_LAYER_SUMMARY",
               "```json\n%s\n```" % json.dumps(
                   r.get("safety_summary") or {}, ensure_ascii=False, indent=1),
          "### ORIGINAL_AI_CONTENT",
          "```json\n%s\n```" % json.dumps(
                   r.get("raw_response") or r.get("raw_ai_content") or {},
                   ensure_ascii=False, indent=1)[:20000],
               "### FINAL_ASSEMBLED_REPORT",
               "```json\n%s\n```" % json.dumps(
                   r.get("assembled") or {}, ensure_ascii=False, indent=1)[:20000],
               "### FACT_SUMMARY",
               "```json\n%s\n```" % json.dumps(
                   [{"item_id": i.get("item_id"), "headline_zh": i.get("headline_zh"),
                     "fact_summary": i.get("fact_summary")}
                    for sec in ("executive_summary", "major_security_developments")
                    for i in (r.get("assembled") or {}).get(sec, [])],
                   ensure_ascii=False, indent=1),
               "### ASSESSMENT",
               "```json\n%s\n```" % json.dumps(
                   [{"item_id": i.get("item_id"), "assessment": i.get("assessment")}
                    for sec in ("executive_summary", "major_security_developments")
                    for i in (r.get("assembled") or {}).get(sec, [])],
                   ensure_ascii=False, indent=1),
               "### OUTLOOK",
               "```json\n%s\n```" % json.dumps(
                   [{"item_id": i.get("item_id"), "outlook": i.get("outlook")}
                    for sec in ("executive_summary", "major_security_developments")
                    for i in (r.get("assembled") or {}).get(sec, [])],
                   ensure_ascii=False, indent=1),
               "### VERIFICATION",
               "```json\n%s\n```" % json.dumps(
                   [{"item_id": i.get("item_id"), "verification_status": i.get("verification_status"),
                     "single_source_warning": i.get("single_source_warning"),
                     "conflicting": i.get("conflicting")}
                    for sec in ("executive_summary", "major_security_developments")
                    for i in (r.get("assembled") or {}).get(sec, [])],
                   ensure_ascii=False, indent=1),
               "### UNCERTAINTIES",
               "```json\n%s\n```" % json.dumps(
                   [{"item_id": i.get("item_id"), "uncertainties": i.get("uncertainties")}
                    for sec in ("executive_summary", "major_security_developments")
                    for i in (r.get("assembled") or {}).get(sec, [])],
                   ensure_ascii=False, indent=1),
               "### SOURCE_REFS",
               "```json\n%s\n```" % json.dumps(
                   [{"item_id": i.get("item_id"), "source_refs": i.get("source_refs")}
                    for sec in ("executive_summary", "major_security_developments")
                    for i in (r.get("assembled") or {}).get(sec, [])],
                   ensure_ascii=False, indent=1),
               "### MACHINE_GATE",
               "```json\n%s\n```" % json.dumps(
                   {"machine_gate": r.get("machine_gate"),
                    "machine_gate_status": r.get("machine_gate_status"),
                    "quality_status": r.get("quality_status"),
                    "quality_issues": r.get("quality_issues") or []},
                   ensure_ascii=False, indent=1),
               ""]
    md += ["## 人工审阅重点（§十二）",
           "",
           "A. 事实准确性  B. 事实遗漏  C. 不确定性表达  D. 归因自然性",
           "E. 数字准确  F. 来源与事实匹配  G. 分析与事实分离",
           "H. Assessment 价值  I. Outlook 是否过度推测  J. 可读性",
           "K. 重复内容  L. 对社会安全决策有用性",
           "",
           "WorkBuddy 不判定 HUMAN_CONTENT_PASS；最终由 ChatGPT + 用户裁定。",
           ""]
    out = out_dir / "human_review_pack.md"
    out.write_text("\n".join(md), encoding="utf-8")
    return out


# ────────────────────────────────────────────────────────────────────────────
# main
# ────────────────────────────────────────────────────────────────────────────

# §十（Repair）：三类结果分离——enrichment schema failure / safety correction /
# safety hold 互不混淆（模块级，可测试）。
def _tally(rec, group_key, s, eid, schema_held):
    """统计单条 enrichment 结果。schema_held 为 list（就地追加 held 记录）。"""
    s["checked"] += 1
    if rec.get("status") == "ok":
        safe = rec["safety"]
        s["attribution_pre_pass"] += 1 if safe["pre_status"] == "PASS" else 0
        s["attribution_pre_fail"] += 1 if safe["pre_status"] == "FAIL" else 0
        s["attribution_post_pass"] += 1 if safe["post_status"] == "PASS" else 0
        s["attribution_auto_corrected"] += 1 if safe["corrections"] else 0
    elif rec.get("status") == "safety_hold":
        s["attribution_hold"] += 1
        s["manual_review_required"] += 1
    elif rec.get("status") == "schema_failure":
        s["enrichment_schema_failure"] += 1
        schema_held.append({"event_id": eid, "country": rec.get("country_code"),
                            "reason": "enrichment_schema_failure: %s"
                                      % (rec.get("schema_errors") or [])[:1]})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="data/runtime/ai_safety/stage8c_trial")
    ap.add_argument("--dry-run", action="store_true",
                    help="不调用 API：只构造输入并打印统计（本地验证用）")
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    inputs = build_inputs()
    stats = inputs["stats"]
    (out_dir / "input_summary.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")

    if args.dry_run:
        print("DRY_RUN input stats:", json.dumps(stats, ensure_ascii=False, indent=1))
        return 0

    if not credential_ok():
        print("MANUAL_TRIAL_SKIPPED credential_missing")
        return 0

    prov = _flash_provider()
    telemetry = {}
    safety_stats = {"social": {"checked": 0, "enrichment_schema_failure": 0,
                               "attribution_pre_pass": 0, "attribution_pre_fail": 0,
                               "attribution_auto_corrected": 0,
                               "attribution_post_pass": 0, "attribution_hold": 0,
                               "manual_review_required": 0},
                    "disease": {"checked": 0, "enrichment_schema_failure": 0,
                                "attribution_pre_pass": 0, "attribution_pre_fail": 0,
                                "attribution_auto_corrected": 0,
                                "attribution_post_pass": 0, "attribution_hold": 0,
                                "manual_review_required": 0}}
    enrichment_records = []
    schema_held = []  # §十一：enrichment schema failure 记录（不调 Prompt，fail-closed）

    # §六 1) Social enrichment + safety
    for i, e in enumerate(inputs["social_candidates"]):
        label = "S%02d_%s" % (i + 1, (e.get("event_id") or "x")[-8:])
        rec = enrich_and_safe(prov, "stage4_event_enrichment", e, label, telemetry)
        rec["event_id"] = e.get("event_id")
        rec["country_code"] = e.get("country_code")
        _tally(rec, "social", safety_stats["social"], e.get("event_id"), schema_held)
        enrichment_records.append(rec)
        print("  [enrich] %-16s status=%s gate=%s" % (
            label, rec.get("status"),
            (rec.get("safety") or {}).get("gate") if rec.get("status") == "ok" else "-"))

    # §六 2) Disease enrichment + safety
    for i, d in enumerate(inputs["disease_candidates"]):
        label = "D%02d_%s" % (i + 1, (d.get("disease_event_id") or "x")[-8:])
        rec = enrich_and_safe(prov, "disease_summary", d, label, telemetry)
        rec["disease_event_id"] = d.get("disease_event_id")
        rec["country_code"] = d.get("country_iso3")
        _tally(rec, "disease", safety_stats["disease"], d.get("disease_event_id"), schema_held)
        enrichment_records.append(rec)
        print("  [enrich] %-16s status=%s gate=%s" % (
            label, rec.get("status"),
            (rec.get("safety") or {}).get("gate") if rec.get("status") == "ok" else "-"))

    (out_dir / "safety_layer_trial.json").write_text(
        json.dumps({"safety_stats": safety_stats,
                    "enrichment_schema_held": schema_held,
                    "enrichment_records": [{k: v for k, v in r.items()
                                            if k != "safety" or True} for r in enrichment_records]},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    # §六 3) Report Input eligibility：仅 safety gate=PASS 的 fact 进入
    eligible_social = [r for r in enrichment_records
                       if r.get("task_type") == "stage4_event_enrichment"
                       and r.get("status") == "ok"
                       and r["safety"]["gate"] == "PASS"]
    eligible_disease = [r for r in enrichment_records
                        if r.get("task_type") == "disease_summary"
                        and r.get("status") == "ok"
                        and r["safety"]["gate"] == "PASS"]

    # §八 Report Engine：三份真实报告（输入 = safety-gated 真实事实）
    reports = {}
    jobs = [
        ("africa_daily", "africa_daily",
         ROOT / "config/prompts/africa_daily_report_v1.md",
         inputs["daily_input"], "africa_daily"),
        ("country_weekly", "tcd_weekly",
         ROOT / "config/prompts/country_weekly_report_v1.md",
         inputs["weekly_tcd_input"], "tcd_weekly"),
        ("country_weekly", "ssd_weekly",
         ROOT / "config/prompts/country_weekly_report_v1.md",
         inputs["weekly_ssd_input"], "ssd_weekly"),
    ]
    for tt, label, prompt_file, rinput, key in jobs:
        # 只保留 safety-gated facts 进入 report input（§六）
        gate_ok_items = []
        if key == "africa_daily":
            for sec in ("executive_summary", "major_security_developments",
                        "public_health_disease"):
                rinput["sections"][sec] = [
                    it for it in rinput["sections"].get(sec, [])
                    if _fact_is_gated(it, eligible_social, eligible_disease)]
        else:
            for sec in ("weekly_executive_assessment", "major_events", "security_trend"):
                rinput["sections"][sec] = [
                    it for it in rinput["sections"].get(sec, [])
                    if _fact_is_gated(it, eligible_social, eligible_disease)]
            rinput["sections"]["disease_public_health"] = [
                it for it in rinput["sections"].get("disease_public_health", [])
                if _fact_is_gated(it, eligible_social, eligible_disease)]
        r = generate_report(prov, tt, rinput, prompt_file, label, telemetry,
                             raw_path=out_dir / ("%s_raw_response.json" % key))
        r["report_input"] = rinput
        r["safety_summary"] = {"eligible_social": len(eligible_social),
                               "eligible_disease": len(eligible_disease),
                               "attribution_hold": (safety_stats["social"]["attribution_hold"] +
                                                    safety_stats["disease"]["attribution_hold"]),
                               "enrichment_schema_held": (safety_stats["social"]["enrichment_schema_failure"] +
                                                          safety_stats["disease"]["enrichment_schema_failure"])}
        r["raw_ai_content"] = r.get("parsed_ai_content") or r.get("raw_ai_content")
        r["raw_response"] = r.get("raw_response") or {
            "raw_content": r.get("raw_content") or "",
            "raw_content_length": r.get("raw_content_length", 0),
            "finish_reason": r.get("finish_reason"),
            "requested_model": r.get("requested_model"),
            "returned_model": r.get("returned_model"),
            "token_usage": r.get("tokens") or {},
        }
        reports[key] = r
        print("  [report] %-12s status=%s machine_gate=%s" % (
            label, r.get("status"), r.get("machine_gate_status")))
        (out_dir / ("%s_raw.json" % key)).write_text(
            json.dumps(r.get("raw_ai_content") or {}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        (out_dir / ("%s_assembled.json" % key)).write_text(
            json.dumps(r.get("assembled_report") or {}, ensure_ascii=False, indent=1),
            encoding="utf-8")

    # provider telemetry
    prov_tel = {k: {kk: vv for kk, vv in v.items()} for k, v in telemetry.items()}
    for k, v in prov_tel.items():
        v["finish_reasons"] = list(dict.fromkeys(v.get("finish_reasons") or []))
        v["thinking"] = list(dict.fromkeys(v.get("thinking") or []))
    (out_dir / "provider_telemetry.json").write_text(
        json.dumps({"qualification_version": "stage8c-package2-v1",
                    "providers": {"deepseek": prov_tel},
                    "total_api_calls": sum(v.get("calls", 0) for v in telemetry.values()),
                    "reasoning_tokens_all_null": all(
                        r.get("reasoning_tokens") is None
                        for rec in enrichment_records for r in [rec]),
                    }, ensure_ascii=False, indent=1), encoding="utf-8")

    # Human review pack
    build_human_review_pack(inputs, enrichment_records, reports, stats, out_dir,
                            safety_stats, schema_held)

    # manual_trial_summary.json
    summary = {
        "trial": "ASIP Stage8C Package2 Manual Human Review Trial",
        "model": "deepseek-v4-flash",
        "thinking": "disabled",
        "safety_layer": "stage8c-v1 (commit de8ac2b lineage)",
        "ai_calls": sum(v.get("calls", 0) for v in telemetry.values()),
        "input_stats": stats,
        "safety_stats": safety_stats,
        "enrichment_schema_held": schema_held,
        # §十二（Repair）：Human Review completeness——区分"模型没写"与"上游被 Gate 拦住"
        "review_completeness": {
            "input_records_total": (stats.get("social_eligible_total", 0) +
                                    stats.get("disease_eligible_total", 0)),
            "input_records_accepted": len(eligible_social) + len(eligible_disease),
            "social_schema_accepted": sum(1 for r in enrichment_records
                                           if r.get("task_type") == "stage4_event_enrichment"
                                           and r.get("status") == "ok"),
            "disease_schema_accepted": sum(1 for r in enrichment_records
                                            if r.get("task_type") == "disease_summary"
                                            and r.get("status") == "ok"),
            "enrichment_schema_held": len(schema_held),
            "attribution_held": (safety_stats["social"]["attribution_hold"] +
                                  safety_stats["disease"]["attribution_hold"]),
            "report_input_final_count": {
                "africa_daily": _report_input_unique_count(
                    reports.get("africa_daily", {}).get("report_input")),
                "tcd_weekly": _report_input_unique_count(
                    reports.get("tcd_weekly", {}).get("report_input")),
                "ssd_weekly": _report_input_unique_count(
                    reports.get("ssd_weekly", {}).get("report_input")),
            },
            "report_input_final_unique": _report_input_unique_count(
                reports.get("africa_daily", {}).get("report_input")),
            "held_records": schema_held,
        },
        "reports": {k: {"status": v.get("status"),
                        "machine_gate_status": v.get("machine_gate_status"),
                        "machine_gate": v.get("machine_gate"),
                        "quality_status": v.get("quality_status"),
                        "gate_exception": v.get("gate_exception"),
                        "numeric_unsupported": (v.get("numeric_unsupported") or [])[:5],
                        "reason": v.get("error") or None}
                    for k, v in reports.items()},
        "ready_for_human_review": all(
            v.get("machine_gate_status") == "PASS" for v in reports.values()),
        "public_changed": False,
        "schedule_changed": False,
        "deployed": False,
    }
    (out_dir / "manual_trial_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("MANUAL_TRIAL_SUMMARY_WRITTEN %s" % (out_dir / "manual_trial_summary.json"))
    print("READY_FOR_HUMAN_REVIEW = %s" % summary["ready_for_human_review"])
    print("TOTAL_API_CALLS = %s" % summary["ai_calls"])
    return 0 if summary["ready_for_human_review"] else 2


def _fact_is_gated(item, eligible_social, eligible_disease):
    """report input item 是否通过 safety gate（按 event_id / disease_event_id 匹配）。"""
    eid = item.get("event_id")
    if not eid:
        return False
    for r in eligible_social + eligible_disease:
        if r.get("event_id") == eid or r.get("disease_event_id") == eid:
            return True
    return False


if __name__ == "__main__":
    sys.exit(main())
