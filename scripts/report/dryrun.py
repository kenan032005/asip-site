#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7A §二十三-§二十五 — 真实 Report Engine Dry-run。

- Africa Daily input：events.json（public 视图）+ quarantine + Stage6B
  disease timelines；确定性选材，不用 AI。
- Country Weekly input：TCD / NER / SSD 三周聚合（数据不足如实 short）。
- Major Event Brief candidates：≤5（允许 0，不强行降低阈值）。

输出仅 internal（data/runtime/reports/），不写 Public。
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT_RUNTIME = ROOT / "data" / "runtime" / "reports"

sys.path.insert(0, str(ROOT))

from scripts.report.builder import (  # noqa: E402
    build_daily_input, build_weekly_input, build_brief_inputs,
)
from scripts.report.changes import (  # noqa: E402
    changes_from_timeline, disease_changes_from_timeline,
)
from scripts.report.selection import _norm_vstatus, CATEGORY_BY_TYPE  # noqa: E402
from scripts.report.config import PRIORITY_REPORT_COUNTRIES  # noqa: E402
from scripts.timeline.country_attr import _country_from_named  # noqa: E402


def _load_events():
    d = json.loads((ROOT / "data" / "events.json").read_text(encoding="utf-8"))
    return d.get("events", [])


def _load_quarantine_ids():
    d = json.loads((ROOT / "data" / "quarantine_events.json").read_text(encoding="utf-8"))
    items = d.get("events", d.get("items", [])) if isinstance(d, dict) else d
    return {str(x.get("event_id") or x.get("disease_event_id")) for x in items}


def _load_disease_timelines():
    p = ROOT / "data" / "runtime" / "timeline" / "disease_timelines.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("timelines", [])


def _load_social_timelines():
    p = ROOT / "data" / "runtime" / "timeline" / "social_timelines.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("timelines", [])


def _enrich_social_event(ev, timelines_by_key):
    """补 country_iso3 / category / verification / timeline change 关联。"""
    iso3 = _country_from_named(ev.get("country_iso3") or ev.get("country"))
    ev["country_iso3"] = iso3
    et = (ev.get("event_type") or "").lower()
    ev["category"] = CATEGORY_BY_TYPE.get(et, "security")
    ev["verification_status"] = _norm_vstatus(ev.get("verification_status"))
    ev["published_at"] = ev.get("published_time") or ev.get("event_time")
    # timeline 关联（§十）：按 country_iso3 + event_type 近似匹配变化
    for tl in timelines_by_key.get((iso3, et), []):
        changes, latest_type, has_conflict, closed = changes_from_timeline(tl)
        if changes:
            ev["change_type"] = latest_type
            ev["change_items_count"] = len(changes)
            ev["timeline_status"] = tl.get("timeline_status")
            ev["latest_update_at"] = tl.get("latest_update_at")
            if has_conflict:
                ev["conflicting"] = True
            if closed:
                ev["timeline_status"] = "closed"
        break
    return ev


def _disease_timeline_item(tl, since=None):
    """disease timeline → report disease item（§十五 数字来自确定性层）。"""
    changes, latest_type, prev_counts = disease_changes_from_timeline(tl, since)
    return {
        "is_disease": True,
        "outbreak_id": tl.get("outbreak_id"),
        "disease_id": tl.get("disease_id"),
        "country_iso3": tl.get("country_iso3"),
        "source_id": "disease_canonical",
        "source_name": "Disease Canonical",
        "latest_counts": tl.get("latest_counts") or {},
        "previous_counts": prev_counts,
        "latest_report_at": tl.get("latest_report_at"),
        "outbreak_status": tl.get("outbreak_status"),
        "change_type": latest_type,
        "verification_status": tl.get("verification_status"),
        "uncertainties": tl.get("uncertainties") or [],
        "updates": tl.get("updates") or [],
        "selection_reasons": ["%s" % latest_type] if latest_type else [],
    }


def main():
    run_id = time.strftime("RPTRUN%Y%m%dT%H%M%S+0800")
    events = _load_events()
    qids = _load_quarantine_ids()
    dis_tls = _load_disease_timelines()
    soc_tls = _load_social_timelines()

    # timeline 关联索引
    tl_key = {}
    for tl in soc_tls:
        cs = tl.get("current_state") or {}
        k = (cs.get("country"), cs.get("event_type"))
        tl_key.setdefault(k, []).append(tl)

    social_events = [_enrich_social_event(dict(e), tl_key) for e in events]
    disease_items = [_disease_timeline_item(t) for t in dis_tls]
    priority = [c for c, on in PRIORITY_REPORT_COUNTRIES.items() if on]

    # ── §二十三 Africa Daily input ──
    daily = build_daily_input(social_events, disease_items,
                              quarantine_ids=qids,
                              priority_countries=priority)
    (REPORT_RUNTIME / "daily_input").mkdir(parents=True, exist_ok=True)
    (REPORT_RUNTIME / "daily_input" / "latest.json").write_text(
        json.dumps(daily, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── §二十四 3 国 Weekly input（TCD/NER/SSD）──
    week_start, week_end = "2026-08-24", "2026-08-30"
    (REPORT_RUNTIME / "weekly_input").mkdir(parents=True, exist_ok=True)
    weekly_out = {}
    for iso3 in priority:
        c_events = [e for e in social_events
                    if e.get("country_iso3") == iso3]
        c_disease = [d for d in disease_items
                     if d.get("country_iso3") == iso3]
        weekly = build_weekly_input(iso3, c_events, c_disease,
                                    week_start, week_end)
        weekly_out[iso3] = weekly
        (REPORT_RUNTIME / "weekly_input" / ("%s.json" % iso3)).write_text(
            json.dumps(weekly, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── §二十五 Major Brief candidates（≤5，允许 0）──
    briefs = build_brief_inputs(social_events + disease_items)
    (REPORT_RUNTIME / "brief_candidates").mkdir(parents=True, exist_ok=True)
    (REPORT_RUNTIME / "brief_candidates" / "latest.json").write_text(
        json.dumps({"run_id": run_id, "candidates": briefs},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 汇总统计 ──
    stats = {
        "run_id": run_id,
        "daily": daily.get("stats"),
        "weekly": {c: {"country_iso3": w["country_iso3"],
                       "event_count": w["trend_metrics"]["event_count"],
                       "fatalities_known": w["trend_metrics"]["fatalities_known"],
                       "new_outbreak_count": w["trend_metrics"]["new_outbreak_count"],
                       "active_outbreak_count": w["trend_metrics"]["active_outbreak_count"]}
                   for c, w in weekly_out.items()},
        "brief_candidates": len(briefs),
        "brief_scores": [b["trigger_score"] for b in briefs],
    }
    (REPORT_RUNTIME / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
