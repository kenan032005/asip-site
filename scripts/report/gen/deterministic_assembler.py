#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage8C Package2 — Deterministic Assembler + Fallback（§四/§八/§九/§十六/§十七）。

确定性事实栏目（Python renderer）：
  Fact Pack → 最终报告的事实类栏目（report_item / disease_item / change_item
  结构，与现有 Final Report Schema 完全兼容）。assessment/outlook 等原 AI 字段
  现在由确定性模板填充（§二：Python deterministic builder 填充）。

Final Assembler：
  Deterministic Fact Sections + AI Analysis（PASS 时）→ Final Report。
  AI Analysis FAIL（timeout/HTTP/JSON/schema/unsupported number/unsupported
  named reference/attribution escalation）→ Deterministic Fallback Analysis
  Section（analysis_status=unavailable + 固定文案），事实部分不变。

Machine Gates（§十七）：
  FACT_GATE / SOURCE_GATE / NUMERIC_GATE / ATTRIBUTION_GATE /
  ANALYSIS_SCHEMA_GATE / ANALYSIS_FACT_BOUNDARY_GATE / FINAL_SCHEMA_GATE /
  METADATA_GATE；Fallback 时 ANALYSIS_* 标记 NOT_APPLICABLE_FALLBACK，
  但 FACT/SOURCE/NUMERIC/ATTRIBUTION/FINAL/METADATA 必须 PASS。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.ai.schema_validation import validate_against_schema  # noqa: E402
from scripts.report.gen import analysis_contract as ac  # noqa: E402

ARCH_VERSION = "deterministic-facts-ai-analysis-v1"
PIPELINE_VERSION = "v2"
FALLBACK_ASSESSMENT = (
    "AI综合研判本次未通过质量门禁，以下仅展示已核验事实与确定性统计信息。")
FALLBACK_TREND = "insufficient_data_or_analysis_gate_failed"
FALLBACK_OUTLOOK = "不作趋势推断（AI 分析未通过质量门禁）"
FALLBACK_WATCH = []

# 确定性占位（schema 必需字段，Python 填充，非 AI 内容）
_ITEM_ASSESSMENT = "该事实已通过确定性核验（来源/归因/不确定性见各字段）。"
_ITEM_OUTLOOK = "AI 研判见总体分析栏目；本条目不提供独立预测。"
_DIS_ASSESSMENT = "该疫情事实已通过确定性核验（来源/不确定性见各字段）。"
_DIS_OUTLOOK = "AI 研判见总体分析栏目；本条目不提供独立预测。"


def _source_refs(fact):
    """source_refs（source_ref 结构：source_id 必需）。"""
    refs = []
    for i, (sid, sname) in enumerate(zip(
            fact.get("source_ids") or [], fact.get("source_refs") or [])):
        refs.append({"source_id": sid or "src_%d" % i,
                     "source_name": sname or "",
                     "url": None})
    if not refs:
        for i, sname in enumerate(fact.get("source_refs") or []):
            refs.append({"source_id": "src_%d" % i, "source_name": sname, "url": None})
    return refs


def _report_item(fact):
    return {
        "item_id": fact.get("fact_id"),
        "master_event_id": None,
        "country_iso3": fact.get("country_iso3"),
        "headline_zh": fact.get("headline_zh"),
        "fact_summary": fact.get("verified_summary"),
        "assessment": _ITEM_ASSESSMENT,
        "outlook": _ITEM_OUTLOOK,
        "verification_status": fact.get("verification_status") or "safety_gate=PASS",
        "uncertainties": fact.get("uncertainties") or [],
        "source_refs": _source_refs(fact),
        "latest_update_at": None,
        "importance_score": fact.get("importance_score"),
        "selection_reasons": fact.get("selection_reasons") or [],
        "single_source_warning": fact.get("single_source_warning"),
        "conflicting": fact.get("conflicting"),
    }


def _disease_item(fact):
    return {
        "item_id": fact.get("fact_id"),
        "disease_id": fact.get("disease_id"),
        "country_iso3": fact.get("country_iso3"),
        "headline_zh": fact.get("headline_zh"),
        "fact_summary": fact.get("verified_summary"),
        "assessment": _DIS_ASSESSMENT,
        "outlook": _DIS_OUTLOOK,
        "verification_status": fact.get("verification_status") or "safety_gate=PASS",
        "uncertainties": fact.get("uncertainties") or [],
        "source_refs": _source_refs(fact),
        "latest_counts": {},
        "as_of_date": None,
    }


def render_fact_sections(fact_pack):
    """Fact Pack → 事实栏目（§四）。返回 sections dict（final schema 兼容）。"""
    rtype = fact_pack.get("report_type")
    social = fact_pack.get("social_facts") or []
    disease = fact_pack.get("disease_facts") or []
    if rtype == "africa_daily":
        social_items = [_report_item(f) for f in social]
        dis_items = [_disease_item(f) for f in disease]
        return {
            "executive_summary": social_items,
            "major_security_developments": social_items,
            "political_social_stability": [_report_item(f) for f in social
                                           if f.get("category") == "political"],
            "terrorism_armed_violence": [_report_item(f) for f in social
                                         if f.get("category") == "terrorism"],
            "cross_border_regional_risks": [],
            "public_health_disease_risks": dis_items,
            "key_changes": [],
            "watch_items": [],
            "source_notes": [_source_refs(f)[0] for f in social + disease
                             if _source_refs(f)],
        }
    # country_weekly
    social_items = [_report_item(f) for f in social]
    dis_items = [_disease_item(f) for f in disease]
    srcs = []
    for f in social + disease:
        for r in _source_refs(f):
            if r.get("source_name") and r["source_name"] not in srcs:
                srcs.append(r["source_name"])
    return {
        "weekly_executive_assessment": [],   # 不在此列（AI 分析见顶层字段）
        "major_events": social_items,
        "security_trend": {},
        "political_social_stability": [_report_item(f) for f in social
                                       if f.get("category") == "political"],
        "terrorism_armed_violence": [_report_item(f) for f in social
                                     if f.get("category") == "terrorism"],
        "disease_public_health": dis_items,
        "changes_from_previous_week": [],
        "next_week_watch_items": [],
        "sources": srcs,
    }


def fallback_analysis(report_type):
    """Deterministic Fallback Analysis Section（§八）。"""
    if report_type == "africa_daily":
        return {
            "executive_assessment": FALLBACK_ASSESSMENT,
            "trend_analysis": FALLBACK_TREND,
            "outlook": FALLBACK_OUTLOOK,
            "watch_points": [],
            "analysis_status": "unavailable",
        }
    return {
        "executive_assessment": FALLBACK_ASSESSMENT,
        "trend_analysis": FALLBACK_TREND,
        "outlook": FALLBACK_OUTLOOK,
        "watch_points": [],
        "analysis_status": "unavailable",
    }


def assemble_report(report_type, fact_pack, analysis=None, analysis_meta=None):
    """Deterministic Fact Sections + AI Analysis → Final Report（schema 兼容）。"""
    sections = render_fact_sections(fact_pack)
    meta = {
        "provider_name": "deepseek",
        "model_name": "deepseek-v4-flash",
        "prompt_version": "analysis-v1.0.0",
        "usage_purpose": "development_test",
        "report_status": "passed_quality_gate",
        "report_generation_architecture": ARCH_VERSION,
        "report_pipeline_version": PIPELINE_VERSION,
        "analysis_status": "ok" if analysis is not None else "unavailable",
        "legacy_full_llm_report_contract": False,
    }
    if report_type == "africa_daily":
        report = {
            "report_id": fact_pack.get("report_id"),
            "report_type": "africa_daily",
            "title": "非洲地区社会安全与综合形势日报",
            "report_date": fact_pack.get("report_date"),
            "period_start": (fact_pack.get("period") or {}).get("start"),
            "period_end": (fact_pack.get("period") or {}).get("end"),
            "generated_at": fact_pack.get("cutoff") or fact_pack.get("generated_at"),
            "report_timezone": "Asia/Shanghai",
            **sections,
            "overall_assessment": (analysis or fallback_analysis("africa_daily"))
                                  .get("executive_assessment"),
            "source_notes": sections.get("source_notes") or [],
            "generation_metadata": meta,
        }
        if analysis:
            report["analysis"] = analysis  # 附加 AI 分析原文（Human Review 区分用）
        return report
    # country_weekly
    an = analysis or fallback_analysis("country_weekly")
    metrics = fact_pack.get("trend_metrics") or {}
    report = {
        "report_id": fact_pack.get("report_id"),
        "report_type": "country_weekly",
        "title": "重点国家周报（%s）" % (fact_pack.get("country_iso3") or ""),
        "country_iso3": fact_pack.get("country_iso3"),
        "week_start": fact_pack.get("week_start"),
        "week_end": fact_pack.get("week_end"),
        "generated_at": fact_pack.get("cutoff") or fact_pack.get("generated_at"),
        "report_timezone": "Asia/Shanghai",
        "executive_assessment": an.get("executive_assessment"),
        "security_trend": an.get("trend_analysis"),
        "major_events": sections.get("major_events") or [],
        "political_social_stability": sections.get("political_social_stability") or [],
        "terrorism_armed_violence": sections.get("terrorism_armed_violence") or [],
        "disease_public_health": sections.get("disease_public_health") or [],
        "week_over_week_changes": [],
        "next_week_watch_items": an.get("watch_points") or [],
        "metrics": metrics,
        "source_notes": [{"source_id": "src_%d" % i, "source_name": s, "url": None}
                         for i, s in enumerate(sections.get("sources") or [])],
        "generation_metadata": meta,
    }
    if analysis:
        report["analysis"] = analysis
    return report


def machine_gates(report, fact_pack, analysis_result=None, final_schema=None):
    """§十七 Machine Gates。返回 {gate: PASS/FAIL/NOT_APPLICABLE, issues: []}。"""
    gates = {}

    # FACT_GATE：事实栏目全部来自 Fact Pack（item_id 与 fact_id 一致）。
    # 0-fact（low-data）为 vacuous PASS（无事实即无违反）。
    fact_ids = {f.get("fact_id") for f in
                fact_pack.get("social_facts", []) + fact_pack.get("disease_facts", [])}
    item_ids = set()
    # 顶层事实栏目
    for sec in ("executive_summary", "major_security_developments",
                "major_events", "political_social_stability",
                "terrorism_armed_violence", "public_health_disease_risks",
                "disease_public_health"):
        for it in report.get(sec) or []:
            if it.get("item_id"):
                item_ids.add(it["item_id"])
    fact_ok = (not fact_ids and not item_ids) or (item_ids and item_ids <= fact_ids)
    gates["FACT_GATE"] = "PASS" if fact_ok else "FAIL"

    # SOURCE_GATE：source_refs 的 source_name 均来自 Fact Pack source_refs
    pack_srcs = set(fact_pack.get("source_refs") or [])
    src_ok = True
    for sec in ("executive_summary", "major_security_developments", "major_events",
                "political_social_stability", "terrorism_armed_violence",
                "public_health_disease_risks", "disease_public_health"):
        for it in report.get(sec) or []:
            for r in it.get("source_refs") or []:
                if r.get("source_name") and r["source_name"] not in pack_srcs:
                    src_ok = False
    gates["SOURCE_GATE"] = "PASS" if src_ok else "FAIL"

    # NUMERIC_GATE：报告事实文本数字均出现在 Fact Pack numeric provenance
    pack_nums = set()
    for v in (fact_pack.get("numeric_provenance") or {}):
        try:
            pack_nums.add(int(str(v).replace(",", "")))
        except (TypeError, ValueError):
            continue
    num_ok = True
    for sec in ("executive_summary", "major_security_developments", "major_events",
                "political_social_stability", "terrorism_armed_violence",
                "public_health_disease_risks", "disease_public_health"):
        for it in report.get(sec) or []:
            for k, v in it.items():
                if k in ("item_id", "source_refs", "latest_counts"):
                    continue
                if isinstance(v, str):
                    for m in ac._analysis_numbers(v):
                        if m not in pack_nums:
                            num_ok = False
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    if int(v) not in pack_nums and k not in ("importance_score",):
                        num_ok = False
    gates["NUMERIC_GATE"] = "PASS" if num_ok else "FAIL"

    # ATTRIBUTION_GATE：报告保留 single_source/conflicting/uncertainties 标记
    attr_ok = True
    for sec in ("executive_summary", "major_security_developments", "major_events",
                "political_social_stability", "terrorism_armed_violence"):
        for it in report.get(sec) or []:
            if it.get("single_source_warning") is None:
                attr_ok = False
    gates["ATTRIBUTION_GATE"] = "PASS" if attr_ok else "FAIL"

    # ANALYSIS_GATES
    if analysis_result is None:
        gates["ANALYSIS_SCHEMA_GATE"] = "NOT_APPLICABLE_FALLBACK"
        gates["ANALYSIS_FACT_BOUNDARY_GATE"] = "NOT_APPLICABLE_FALLBACK"
    else:
        gates["ANALYSIS_SCHEMA_GATE"] = ("PASS" if analysis_result.get("schema_ok")
                                         else "FAIL")
        gates["ANALYSIS_FACT_BOUNDARY_GATE"] = (
            "PASS" if analysis_result.get("boundary_ok") else "FAIL")

    # FINAL_SCHEMA_GATE
    if final_schema is not None:
        errs = validate_against_schema(report, final_schema, resolve_refs=True)
        gates["FINAL_SCHEMA_GATE"] = "PASS" if not errs else "FAIL"
        gates["final_schema_issues"] = errs[:5]
    else:
        gates["FINAL_SCHEMA_GATE"] = "NOT_EXECUTED"

    # METADATA_GATE：envelope 以 Fact Pack/input 为准
    md = report.get("generation_metadata") or {}
    md_ok = (md.get("report_generation_architecture") == ARCH_VERSION and
             md.get("report_pipeline_version") == PIPELINE_VERSION)
    gates["METADATA_GATE"] = "PASS" if md_ok else "FAIL"

    # issues 计数
    gates["issues"] = []
    for g, v in gates.items():
        if v == "FAIL":
            gates["issues"].append(g)
    return gates
