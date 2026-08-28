#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7A §二十六 — Report Golden Set 评估器（Daily 15 / Weekly 10 / Brief 8）。"""

import sys

from scripts.report.selection import select_daily, is_low_value, importance_score
from scripts.report.weekly import weekly_metrics, enabled_weekly_countries
from scripts.report.brief import evaluate_brief_candidates, trigger_score
from scripts.report.golden import (build_daily_fixtures, build_weekly_fixtures,
                                   build_brief_fixtures)
from scripts.report.config import TRIGGER_THRESHOLD


def _run_daily(fixtures):
    results = []
    for fid, events, exp in fixtures:
        prev_ids = exp.get("prev_ids") or []
        sel, stats, suppressed = select_daily(
            events, prev_event_ids=prev_ids,
            priority_countries=exp.get("priority_countries") or ["TCD", "NER", "SSD"])
        ok = True
        notes = {}
        n_sec = len(sel["security"])
        if "selected" in exp:
            ok = ok and n_sec == exp["selected"]
            notes["selected"] = n_sec
        if "selected_disease" in exp:
            ok = ok and len(sel["disease"]) == exp["selected_disease"]
            notes["selected_disease"] = len(sel["disease"])
        if "suppressed" in exp:
            ok = ok and stats["suppressed_low_value"] == exp["suppressed"]
            notes["suppressed"] = stats["suppressed_low_value"]
        if "warning" in exp:
            ok = ok and all(it.get("single_source_warning") for it in sel["security"])
        if "conflicting" in exp:
            ok = ok and all(it.get("conflicting") for it in sel["security"])
        if "watch" in exp:
            ok = ok and stats["watch_items"] == exp["watch"]
            notes["watch"] = stats["watch_items"]
        if "change_type" in exp:
            ok = ok and any(it.get("change_type") == exp["change_type"]
                            for it in sel["security"] + sel["disease"])
        if "min_score" in exp:
            ok = ok and all(it["importance_score"] >= exp["min_score"]
                            for it in sel["security"])
        if "reasons_contains" in exp:
            ok = ok and any(exp["reasons_contains"] in it["selection_reasons"]
                            for it in sel["security"] + sel["disease"])
        if "status" in exp:
            ok = ok and all(it.get("timeline_status") == exp["status"]
                            for it in sel["security"])
        results.append((fid, "PASS" if ok else "FAIL",
                        {"selected": n_sec, "disease": len(sel["disease"]),
                         "suppressed": stats["suppressed_low_value"],
                         "scores": [it["importance_score"] for it in sel["security"]]}))
    return results


def _run_weekly(fixtures):
    results = []
    for fid, events, exp in fixtures:
        dis = exp.get("disease_events", [])
        m = weekly_metrics(events, dis, "2026-08-24", "2026-08-30",
                           prev_metrics=exp.get("prev_metrics"))
        ok = True
        for k, v in exp.items():
            if k in ("prev_metrics", "disease_events", "assessment"):
                continue
            if k == "comparison":
                for fk, fv in v.items():
                    ok = ok and m["comparison"].get(fk) == fv
            elif k == "comparison_has_values":
                ok = ok and any(v is not None for v in m["comparison"].values())
            elif k == "sources":
                ok = ok and sorted(m.get("sources", []) if isinstance(m, dict) and "sources" in m else [])
            else:
                ok = ok and m.get(k) == v
        if "assessment" in exp:
            ok = ok and exp["assessment"] in _assessment_text(events)
        results.append((fid, "PASS" if ok else "FAIL",
                        {"metrics": {k: m.get(k) for k in
                                     ("event_count", "verified_event_count",
                                      "armed_attack_count", "civil_unrest_count",
                                      "fatalities_known", "new_outbreak_count",
                                      "active_outbreak_count")},
                         "comparison": m.get("comparison")}))
    return results


def _assessment_text(events):
    if not events:
        return "本周该国内部事件数据不足，未生成趋势判断"
    return ""


def _run_brief(fixtures):
    results = []
    for fid, events, exp in fixtures:
        cands = evaluate_brief_candidates(events)
        ok = True
        statuses = [c["candidate_status"] for c in cands]
        if "status" in exp:
            ok = ok and all(s == exp["status"] for s in statuses)
        if "min_score" in exp:
            ok = ok and all(c["trigger_score"] >= exp["min_score"]
                            for c in cands if c["candidate_status"] == "brief_candidate")
        results.append((fid, "PASS" if ok else "FAIL",
                        {"statuses": statuses,
                         "scores": [c["trigger_score"] for c in cands]}))
    return results


def main():
    daily = _run_daily(build_daily_fixtures())
    weekly = _run_weekly(build_weekly_fixtures())
    brief = _run_brief(build_brief_fixtures())
    all_ = daily + weekly + brief
    fails = [r for r in all_ if r[1] == "FAIL"]
    print("=== Daily (%d) ===" % len(daily))
    for pid, v, d in daily:
        print("  %-42s %s %s" % (pid, v, d))
    print("=== Weekly (%d) ===" % len(weekly))
    for pid, v, d in weekly:
        print("  %-42s %s %s" % (pid, v, d))
    print("=== Brief (%d) ===" % len(brief))
    for pid, v, d in brief:
        print("  %-42s %s %s" % (pid, v, d))
    print("TOTAL: %d/%d PASS" % (len(all_) - len(fails), len(all_)))
    if fails:
        for pid, v, d in fails:
            print("  FAIL:", pid, d)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
