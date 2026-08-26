#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7A §三十 — Report Engine 测试。

覆盖：daily selection / importance scoring / low-value suppression / timeline
change handling / previous report suppression / disease selection + numeric
preservation / weekly metrics + comparison / brief triggering / Fact-Analysis
separation / source provenance / Canonical 未改 / runtime 隔离 + Golden 33 组。
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.report.selection import (  # noqa: E402
    select_daily, importance_score, is_low_value, _norm_vstatus,
)
from scripts.report.changes import (  # noqa: E402
    changes_from_timeline, disease_changes_from_timeline,
    prev_report_event_ids, split_prev_reported,
)
from scripts.report.weekly import weekly_metrics, enabled_weekly_countries  # noqa: E402
from scripts.report.brief import evaluate_brief_candidates, trigger_score  # noqa: E402
from scripts.report.builder import build_daily_input, build_weekly_input  # noqa: E402
from scripts.report.golden_runner import (  # noqa: E402
    _run_daily, _run_weekly, _run_brief,
)
from scripts.report.golden import (  # noqa: E402
    build_daily_fixtures, build_weekly_fixtures, build_brief_fixtures,
)


def _ev(eid, **kw):
    base = {"event_id": eid, "master_event_id": "ME_" + eid,
            "event_type": kw.pop("event_type", "armed_attack"),
            "country_iso3": kw.pop("country_iso3", "TCD"),
            "title_original": kw.pop("title_original", "Attack in CITY_ALPHA"),
            "verification_status": kw.pop("verification_status", "verified"),
            "source_count": kw.pop("source_count", 2),
            "source_id": kw.pop("source_id", "s1"),
            "published_at": kw.pop("published_at", "2026-08-25T10:00:00+00:00"),
            "deaths": kw.pop("deaths", None),
            "injured": kw.pop("injured", None),
            "category": kw.pop("category", "security"),
    }
    base.update(kw)
    return base


class TestSelection(unittest.TestCase):
    """§六-§九 daily selection / importance / suppression。"""

    def test_importance_major_casualties(self):
        s, reasons = importance_score(_ev("a", deaths=25, event_severity="高"))
        self.assertIn("major_casualties", reasons)
        self.assertGreaterEqual(s, 20)

    def test_importance_terrorism(self):
        s, reasons = importance_score(_ev("a", event_type="terrorist_attack"))
        self.assertIn("terrorism_armed_conflict", reasons)

    def test_importance_priority_country(self):
        s, reasons = importance_score(_ev("a", country_iso3="NER"),
                                      priority_countries=["TCD", "NER", "SSD"])
        self.assertIn("priority_country", reasons)

    def test_importance_cap_100(self):
        s, _ = importance_score(_ev("a", event_type="terrorist_attack", deaths=50,
                                    event_severity="极高", official_declaration=True,
                                    timeline_status="ongoing"),
                                priority_countries=["TCD", "NER", "SSD"],
                                prev_changed=True)
        self.assertLessEqual(s, 100)

    def test_low_value_suppression(self):
        self.assertTrue(is_low_value("Business meeting on trade cooperation"))
        self.assertTrue(is_low_value("Minister ceremonial visit to REGION"))
        self.assertFalse(is_low_value("Attack in CITY_ALPHA"))
        self.assertFalse(is_low_value("Business meeting sparks security concerns"))

    def test_daily_select_and_suppress(self):
        events = [_ev("a", event_type="terrorist_attack", deaths=25),
                  _ev("b", title_original="Business meeting on trade in CITY")]
        sel, stats, sup = select_daily(events, priority_countries=["TCD"])
        self.assertEqual(len(sel["security"]), 1)
        self.assertEqual(stats["suppressed_low_value"], 1)

    def test_prev_report_suppression(self):
        # 已报告无变化 → watch；新事件 → key change
        events = [_ev("a", event_type="armed_attack", deaths=10),
                  _ev("b", event_type="armed_attack", deaths=12)]
        sel, stats, sup = select_daily(events, prev_event_ids={"ME_a"})
        self.assertEqual(stats["watch_items"], 1)
        self.assertEqual(stats["change_items"], 1)

    def test_duplicate_master_once(self):
        events = [_ev("a", master_event_id="ME_dup", deaths=10),
                  _ev("b", master_event_id="ME_dup", deaths=10)]
        sel, stats, _ = select_daily(events)
        self.assertEqual(len(sel["security"]), 1)

    def test_verification_normalize(self):
        self.assertEqual(_norm_vstatus("partial"), "single_source")
        self.assertEqual(_norm_vstatus("verified"), "verified")
        self.assertEqual(_norm_vstatus("conflicting"), "conflicting")


class TestChanges(unittest.TestCase):
    """§十-§十三 change detection / prev report / fact-analysis。"""

    def test_timeline_changes(self):
        tl = {"master_event_id": "ME_1", "updates": [
            {"update_type": "initial_report", "published_at": "2026-08-25T09:00:00+00:00"},
            {"update_type": "casualty_update", "published_at": "2026-08-25T14:00:00+00:00"},
        ], "conflict_flags": []}
        changes, latest, has_conflict, closed = changes_from_timeline(tl)
        self.assertIn("new_event", [c["change_type"] for c in changes])
        self.assertIn("casualty_increase", [c["change_type"] for c in changes])
        self.assertEqual(latest, "casualty_increase")
        self.assertFalse(closed)

    def test_timeline_conflict_flag(self):
        tl = {"master_event_id": "ME_1", "updates": [
            {"update_type": "initial_report", "published_at": "2026-08-25T09:00:00+00:00"}],
            "conflict_flags": ["casualty_difference"]}
        changes, latest, has_conflict, _ = changes_from_timeline(tl)
        self.assertTrue(has_conflict)
        self.assertIn("conflict_detected", [c["change_type"] for c in changes])

    def test_closure_change(self):
        tl = {"master_event_id": "ME_1", "updates": [
            {"update_type": "closure_update", "published_at": "2026-08-27T09:00:00+00:00"}],
            "conflict_flags": []}
        _, latest, _, closed = changes_from_timeline(tl)
        self.assertTrue(closed)
        self.assertEqual(latest, "closed")

    def test_disease_changes(self):
        tl = {"outbreak_id": "OB_1", "disease_id": "cholera", "updates": [
            {"update_type": "new_outbreak", "report_date": "2026-08-20"},
            {"update_type": "case_update", "report_date": "2026-08-24"}]}
        changes, latest, prev = disease_changes_from_timeline(tl)
        types = [c["change_type"] for c in changes]
        self.assertIn("new_outbreak", types)
        self.assertIn("case_increase", types)

    def test_prev_report_ids_extraction(self):
        prev = {"report_id": "DAILY_x", "sections": {
            "executive_summary": [{"event_id": "E1"}],
            "public_health_disease": [{"disease_id": "cholera"}]}}
        ids = prev_report_event_ids(prev)
        self.assertIn("E1", ids)
        self.assertIn("cholera", ids)

    def test_split_prev_reported(self):
        items = [{"event_id": "E1", "change_type": "casualty_increase"},
                 {"event_id": "E2", "change_type": None}]
        key, watch = split_prev_reported(items, {"E2"})
        self.assertEqual(len(key), 1)
        self.assertEqual(len(watch), 1)


class TestWeekly(unittest.TestCase):
    """§十六-§十八 weekly metrics。"""

    def test_metrics_aggregation(self):
        m = weekly_metrics([_ev("a", event_type="armed_attack", deaths=5),
                            _ev("b", event_type="civil_unrest", injured=3)],
                           [], "2026-08-24", "2026-08-30")
        self.assertEqual(m["event_count"], 2)
        self.assertEqual(m["armed_attack_count"], 1)
        self.assertEqual(m["civil_unrest_count"], 1)
        self.assertEqual(m["fatalities_known"], 5)

    def test_duplicate_not_double_count(self):
        m = weekly_metrics([_ev("a", event_type="armed_attack", deaths=5),
                            _ev("a", event_type="armed_attack", deaths=5)],
                           [], "2026-08-24", "2026-08-30")
        self.assertEqual(m["event_count"], 1)

    def test_unknown_not_zero(self):
        m = weekly_metrics([_ev("a", event_type="civil_unrest", deaths=None)],
                           [], "2026-08-24", "2026-08-30")
        self.assertIsNone(m["fatalities_known"])

    def test_comparison(self):
        m = weekly_metrics([_ev("a")], [], "2026-08-24", "2026-08-30",
                           prev_metrics={"event_count": 0})
        self.assertEqual(m["comparison"]["event_count"], "up")
        m2 = weekly_metrics([], [], "2026-08-24", "2026-08-30")
        self.assertIsNone(m2["comparison"]["event_count"])

    def test_enabled_countries_config(self):
        en = enabled_weekly_countries()
        self.assertIn("TCD", en)
        self.assertNotIn("BEN", en)

    def test_disease_metrics(self):
        dis = [{"outbreak_id": "OB_1", "disease_id": "cholera",
                "report_date": "2026-08-25", "outbreak_status": "active",
                "updates": [{"report_date": "2026-08-25"}]}]
        m = weekly_metrics([], dis, "2026-08-24", "2026-08-30")
        self.assertEqual(m["new_outbreak_count"], 1)
        self.assertEqual(m["active_outbreak_count"], 1)


class TestBrief(unittest.TestCase):
    """§十九-§二十 brief triggering。"""

    def test_major_attack_triggers(self):
        cands = evaluate_brief_candidates(
            [_ev("a", event_type="terrorist_attack", deaths=40,
                 event_severity="极高", official_emergency=True, update_count=3)])
        self.assertEqual(cands[0]["candidate_status"], "brief_candidate")
        self.assertGreaterEqual(cands[0]["trigger_score"], 70)

    def test_ordinary_not_trigger(self):
        cands = evaluate_brief_candidates(
            [_ev("b", event_type="other_security",
                 title_original="Business meeting in CITY")])
        self.assertEqual(cands[0]["candidate_status"], "below_threshold")

    def test_low_casualty_single_not_trigger(self):
        cands = evaluate_brief_candidates(
            [_ev("c", event_type="armed_attack", deaths=2,
                 verification_status="single_source", source_count=1,
                 single_source_warning=True)])
        self.assertEqual(cands[0]["candidate_status"], "below_threshold")

    def test_conflicting_major_still_candidate(self):
        cands = evaluate_brief_candidates(
            [_ev("d", event_type="terrorist_attack", deaths=50,
                 verification_status="conflicting", conflicting=True,
                 event_severity="极高", update_count=3,
                 title_original="Attack in capital of REGION")])
        self.assertEqual(cands[0]["candidate_status"], "brief_candidate")


class TestFactAnalysisSeparation(unittest.TestCase):
    """§十二 facts/analysis 分层。"""

    def test_daily_input_fact_analysis_fields(self):
        events = [_ev("a", event_type="terrorist_attack", deaths=25)]
        dis = []
        daily = build_daily_input(events, dis, priority_countries=["TCD"])
        item = daily["sections"]["major_security_developments"][0]
        self.assertIn("facts", item)
        self.assertIn("analysis_inputs", item)
        self.assertIn("uncertainties", item)
        self.assertIn("source_evidence", item)
        self.assertTrue(any(f["fact"].startswith("deaths=") for f in item["facts"]))

    def test_disease_numeric_preserved(self):
        dis = [{"is_disease": True, "outbreak_id": "OB_1", "disease_id": "cholera",
                "country_iso3": "TCD", "source_id": "disease_canonical",
                "source_name": "Disease Canonical",
                "latest_counts": {"confirmed_cases": 620, "deaths": 15},
                "previous_counts": {"confirmed_cases": 500, "deaths": 12},
                "latest_report_at": "2026-08-24", "outbreak_status": "active",
                "change_type": "case_increase", "verification_status": "verified",
                "uncertainties": [], "updates": [],
                "selection_reasons": ["case_increase"]}]
        daily = build_daily_input([], dis, priority_countries=["TCD"])
        d = daily["sections"]["public_health_disease"][0]
        self.assertEqual(d["latest_counts"]["confirmed_cases"], 620)
        self.assertEqual(d["delta"]["confirmed_cases"], 120)


class TestRuntimeIsolation(unittest.TestCase):
    """§三十 runtime 隔离 / Canonical 未改。"""

    def test_runtime_not_in_dist(self):
        self.assertFalse((ROOT / "dist" / "data" / "runtime").exists())
        gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("data/runtime", gi)

    def test_canonical_public_unchanged(self):
        for p in ("data/events.json", "data/public/published_events.json",
                  "data/canonical/articles.json",
                  "data/disease/canonical/outbreak_events.json"):
            self.assertTrue((ROOT / p).exists(), p)


class TestGoldenSets(unittest.TestCase):
    """§二十六 Golden 33 组。"""

    def test_daily_golden_15(self):
        results = _run_daily(build_daily_fixtures())
        fails = [r for r in results if r[1] != "PASS"]
        self.assertEqual(fails, [])

    def test_weekly_golden_10(self):
        results = _run_weekly(build_weekly_fixtures())
        fails = [r for r in results if r[1] != "PASS"]
        self.assertEqual(fails, [])

    def test_brief_golden_8(self):
        results = _run_brief(build_brief_fixtures())
        fails = [r for r in results if r[1] != "PASS"]
        self.assertEqual(fails, [])


if __name__ == "__main__":
    unittest.main()
