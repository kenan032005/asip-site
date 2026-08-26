#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7A — Report Input Builder（组装 3 类 report input contract）。

- Africa Daily：eligible events + selection + changes + prev-report 比较 →
  africa_daily_report_input（§四 A-I sections）。
- Country Weekly：country events 聚合 + trend metrics → country_weekly_report_input。
- Major Event Brief：trigger candidates → major_event_brief_input 列表。

全部 internal；不写 Public（§二十九）。facts/analysis_inputs/uncertainties/
source_evidence 分层（§十二）。
"""

import hashlib
import time
from pathlib import Path

from scripts.report.selection import select_daily, _norm_vstatus
from scripts.report.changes import (
    changes_from_timeline, disease_changes_from_timeline,
    prev_report_event_ids, split_prev_reported,
)
from scripts.report.weekly import weekly_metrics, enabled_weekly_countries
from scripts.report.brief import evaluate_brief_candidates

ROOT = Path(__file__).resolve().parents[2]
REPORT_RUNTIME = ROOT / "data" / "runtime" / "reports"


def _bj_now():
    return time.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _facts_from_ev(ev):
    """§十二 facts（对象带证据）——只含确定性字段。"""
    facts = []
    for k, label in (("event_type", "event_type"), ("location", "location"),
                     ("country", "country")):
        if ev.get(k):
            facts.append({"fact": "%s=%s" % (label, ev[k]),
                          "evidence": ev.get("source_name") or ev.get("source_id")})
    d = ev.get("deaths") or ev.get("casualties")
    if d is not None:
        facts.append({"fact": "deaths=%s" % d,
                      "evidence": ev.get("source_name") or ev.get("source_id")})
    if ev.get("injured") is not None:
        facts.append({"fact": "injured=%s" % ev["injured"],
                      "evidence": ev.get("source_name") or ev.get("source_id")})
    return facts


def _analysis_inputs(ev):
    """§十二 analysis_inputs（中性，不越界为预测）。"""
    out = []
    vs = _norm_vstatus(ev.get("verification_status"))
    if vs == "single_source":
        out.append("single-source，尚待进一步核实")
    if ev.get("conflicting"):
        out.append("多源数据存在冲突，需谨慎表述")
    if ev.get("timeline_status") in ("developing", "ongoing"):
        out.append("事件仍在发展，后续更新可能改变事实")
    return out


def _disease_importance(d):
    """§十五/§七 disease 确定性分数：重大变化类型给较高分，无变化 0。"""
    ct = d.get("change_type")
    if ct in ("new_outbreak", "geographic_spread", "cross_border"):
        return 55
    if ct in ("case_increase", "mortality_increase", "status_change", "final_update"):
        return 40
    return 0


def build_daily_input(events, disease_items, prev_report=None,
                      quarantine_ids=None, priority_countries=None,
                      report_date=None, iso2to3=None):
    """§二十三 Africa Daily report input。events: social events（含 category/
    verification/timeline 信息）；disease_items: disease timeline 条目。"""
    rid = "DAILY_%s" % (report_date or time.strftime("%Y%m%d"))
    prev_ids = prev_report_event_ids(prev_report)
    selected, stats, suppressed_log = select_daily(
        list(events) + list(disease_items),   # disease items 一并进入选材（§十五）
        quarantine_ids=quarantine_ids,
        priority_countries=priority_countries,
        prev_event_ids=prev_ids, iso2to3=iso2to3)

    sec = {
        "executive_summary": [],
        "major_security_developments": [],
        "political_social_stability": [],
        "terrorism_armed_violence": [],
        "cross_border_regional": [],
        "public_health_disease": [],
        "key_changes": [],
        "watch_items": [],
        "source_notes": [],
    }

    for it in selected["security"]:
        item = {
            "event_id": it.get("event_id"),
            "master_event_id": it.get("master_event_id"),
            "country": it.get("country"),
            "country_iso3": it.get("country_iso3"),
            "category": it.get("category"),
            "importance_score": it["importance_score"],
            "change_type": it.get("change_type"),
            "verification": _norm_vstatus(it.get("verification_status")),
            "verification_confidence": it.get("verification_confidence"),
            "source_count": it.get("source_count") or 1,
            "single_source_warning": bool(it.get("single_source_warning")),
            "conflicting": bool(it.get("conflicting")),
            "latest_update_at": it.get("latest_update_at") or it.get("published_at"),
            "selection_reasons": it["selection_reasons"],
            "facts": _facts_from_ev(it),
            "analysis_inputs": _analysis_inputs(it),
            "uncertainties": it.get("uncertainties") or [],
            "source_evidence": [{"source_id": it.get("source_id")}] if it.get("source_id") else [],
        }
        cat = it.get("category") or "security"
        if cat == "terrorism":
            sec["terrorism_armed_violence"].append(item)
        elif cat == "political":
            sec["political_social_stability"].append(item)
        elif cat == "cross_border":
            sec["cross_border_regional"].append(item)
        else:
            sec["major_security_developments"].append(item)

    # disease items（§十五：数字完全来自确定性层；§九 数量控制 2-5 +
    # §十一 prev 抑制由 select_daily 完成 → 只取被选中的 disease 子集。
    # 匹配按 outbreak_id（§二十：每个 outbreak 独立，同一 disease 多国=多 outbreak））
    sel_dis_keys = {(d.get("outbreak_id") or d.get("disease_id"))
                    for d in selected["disease"]}
    for d in disease_items:
        if (d.get("outbreak_id") or d.get("disease_id")) not in sel_dis_keys:
            continue
        lc = d.get("latest_counts") or {}
        prev_counts = d.get("previous_counts") or {}
        delta = {}
        for k in ("confirmed_cases", "total_cases", "deaths"):
            cur = lc.get(k)
            pre = prev_counts.get(k)
            if cur is not None and pre is not None:
                delta[k] = cur - pre
        sec["public_health_disease"].append({
            "disease_id": d.get("disease_id"),
            "country_iso3": d.get("country_iso3"),
            "outbreak_id": d.get("outbreak_id"),
            "importance_score": _disease_importance(d),
            "latest_counts": lc,
            "previous_counts": prev_counts,
            "delta": delta,
            "as_of_date": lc.get("as_of_date") or d.get("latest_report_at"),
            "outbreak_status": d.get("outbreak_status"),
            "change_type": d.get("change_type"),
            "source": (d.get("updates") or [{}])[-1].get("evidence", {}).get("primary_source"),
            "verification": d.get("verification_status"),
            "uncertainties": d.get("uncertainties") or [],
            "selection_reasons": d.get("selection_reasons") or [],
        })
    stats["selected_disease_events"] = len(sec["public_health_disease"])

    # Executive Summary（§五 5-8 最高价值）
    exec_cand = sorted(sec["major_security_developments"] +
                       sec["terrorism_armed_violence"] +
                       sec["political_social_stability"] +
                       sec["cross_border_regional"] +
                       sec["public_health_disease"],
                       key=lambda x: -x.get("importance_score", 0))
    sec["executive_summary"] = exec_cand[:8]

    # Key Changes / Watch（§十一）
    key_changes, watch = split_prev_reported(
        [dict(it, change_type=it.get("change_type"))
         for it in sec["executive_summary"]], prev_ids)
    for it in key_changes:
        if it.get("change_type"):
            sec["key_changes"].append({
                "event_id": it.get("event_id"),
                "master_event_id": it.get("master_event_id"),
                "change_type": it["change_type"],
                "description": "该事件相对上日报存在变化",
                "importance_score": it.get("importance_score", 0),
                "facts": it.get("facts") or [],
                "analysis_inputs": it.get("analysis_inputs") or [],
            })
    stats["change_items"] = len(sec["key_changes"])
    sec["watch_items"] = watch[:10]
    stats["watch_items"] = len(sec["watch_items"])

    doc = {
        "report_id": rid,
        "report_type": "africa_daily",
        "report_name": "非洲地区社会安全与综合形势日报",
        "generated_at": _bj_now(),
        "report_date": report_date or time.strftime("%Y-%m-%d"),
        "cutoff": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "previous_report_id": (prev_report or {}).get("report_id"),
        "previous_cutoff": (prev_report or {}).get("cutoff"),
        "stats": stats,
        "sections": sec,
    }
    return doc


def build_weekly_input(country_iso3, events, disease_events, week_start, week_end,
                       prev_metrics=None, prev_report_id=None):
    """§二十四 Country Weekly report input。"""
    metrics = weekly_metrics(events, disease_events, week_start, week_end, prev_metrics)
    # §十七 Weekly 不是日报拼接：按 importance 排序的 major events
    evs = sorted(events, key=lambda e: -(e.get("importance_score") or 0))
    major = []
    for ev in evs[:15]:
        major.append({
            "event_id": ev.get("event_id"),
            "master_event_id": ev.get("master_event_id"),
            "event_type": ev.get("event_type"),
            "location": ev.get("location"),
            "importance_score": ev.get("importance_score") or 0,
            "verification": _norm_vstatus(ev.get("verification_status")),
            "source_count": ev.get("source_count") or 1,
            "change_items_count": ev.get("change_items_count") or 0,
            "facts": _facts_from_ev(ev),
            "analysis_inputs": _analysis_inputs(ev),
            "uncertainties": ev.get("uncertainties") or [],
            "source_evidence": [{"source_id": ev.get("source_id")}] if ev.get("source_id") else [],
        })
    disease = []
    for de in disease_events:
        disease.append({
            "disease_id": de.get("disease_id"),
            "country_iso3": de.get("country_iso3"),
            "latest_counts": de.get("latest_counts") or {},
            "as_of_date": (de.get("latest_counts") or {}).get("as_of_date"),
            "outbreak_status": de.get("outbreak_status"),
            "change_types": [u.get("update_type") for u in (de.get("updates") or [])],
            "source": (de.get("updates") or [{}])[-1].get("evidence", {}).get("primary_source"),
        })
    # §十八 changes_from_previous_week（确定性 comparison 摘要）
    comps = []
    for f, direction in (metrics.get("comparison") or {}).items():
        if direction is not None:
            comps.append({"field": f, "direction": direction,
                          "detail": "week comparison"})
    doc = {
        "report_id": "WEEKLY_%s_%s" % (country_iso3, week_end),
        "report_type": "country_weekly",
        "country_iso3": country_iso3,
        "week_start": week_start,
        "week_end": week_end,
        "previous_report_id": prev_report_id,
        "generated_at": _bj_now(),
        "trend_metrics": metrics,
        "sections": {
            "weekly_executive_assessment": _weekly_assessment_input(metrics, events),
            "major_events": major,
            "security_trend": {"metrics": metrics, "assessment_inputs": []},
            "political_social_stability": [],
            "terrorism_armed_violence": [],
            "disease_public_health": disease,
            "changes_from_previous_week": comps,
            "next_week_watch_items": [],
            "sources": sorted({ev.get("source_id") for ev in events if ev.get("source_id")}),
        },
    }
    return doc


def _weekly_assessment_input(metrics, events):
    """§十八 中性评估输入（非 AI 成稿；无数据不编造趋势）。"""
    out = []
    if not events:
        out.append("本周该国内部事件数据不足，未生成趋势判断")
        return out
    comp = metrics.get("comparison") or {}
    ec = comp.get("event_count")
    if ec == "up":
        out.append("本周事件数量较上周上升")
    elif ec == "down":
        out.append("本周事件数量较上周下降")
    else:
        out.append("本周事件数量与上周基本持平")
    if metrics.get("active_outbreak_count"):
        out.append("当前有 %d 起活跃疫情" % metrics["active_outbreak_count"])
    return out


def build_brief_inputs(events, threshold=None):
    """§二十五 Major Event Brief trigger candidates（≤5）。"""
    cands = evaluate_brief_candidates(events, threshold=threshold)
    return [c for c in cands if c["candidate_status"] == "brief_candidate"][:5]
