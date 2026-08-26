#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7B §三十/§三十二 — Report Generation & Quality Gate 测试。

Golden Output fixtures（§三十）：Daily 12 / Weekly 8 / Brief 6 —— 以
(report, input, expected_gate_result) 形式验证 Quality Gate 判定逻辑。
其余：Temporal Window（§二）/ Mock Contract / Renderer / runtime 隔离。
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.report.gen.quality import run_quality_gate, _schema_valid, _load_schema  # noqa: E402
from scripts.report.selection import select_daily, temporal_bucket  # noqa: E402
from scripts.report.gen.providers import MockReportProvider  # noqa: E402
from scripts.report.gen.runner import run_report  # noqa: E402
from scripts.report.gen.renderer import render_daily_markdown  # noqa: E402
from scripts.report.gen.trial import MOCK_DAILY_INPUT, MOCK_WEEKLY_INPUT, MOCK_BRIEF_INPUT  # noqa: E402


def _daily_input():
    return json.loads(json.dumps(MOCK_DAILY_INPUT))


def _base_daily_report():
    return {
        "report_id": "DAILY_G01", "report_type": "africa_daily",
        "title": "日报", "report_date": "2026-08-26",
        "period_start": None, "period_end": None, "generated_at": "2026-08-26T08:00:00+08:00",
        "executive_summary": [{
            "item_id": "E1", "master_event_id": "ME_E1", "country_iso3": "SSD",
            "headline_zh": "南苏丹发生武装冲突",
            "fact_summary": "武装冲突导致12人死亡。",
            "assessment": "当地安全形势仍存在波动。",
            "outlook": "需关注后续官方调查。",
            "verification_status": "verified", "uncertainties": [],
            "source_refs": [{"source_id": "ssd_eyeradio", "source_name": "Eye Radio"}],
            "latest_update_at": None, "importance_score": 85,
            "selection_reasons": ["major_casualties"],
            "single_source_warning": False, "conflicting": False,
        }],
        "major_security_developments": [], "political_social_stability": [],
        "terrorism_armed_violence": [], "cross_border_regional_risks": [],
        "public_health_disease_risks": [], "key_changes": [], "watch_items": [],
        "overall_assessment": "总体平稳。",
        "source_notes": [{"source_id": "ssd_eyeradio", "source_name": "Eye Radio"}],
        "generation_metadata": {"provider_name": "mock", "model_name": "mock",
                                "prompt_version": "1.0.0", "usage_purpose": "development_test",
                                "report_status": "draft", "input_report_id": "DAILY_MOCK01"},
    }


class TestGoldenDaily(unittest.TestCase):
    """§三十 Daily output fixtures（12）。"""

    def _gate(self, report):
        passed, status, issues, warns = run_quality_gate(report, _daily_input(), "africa_daily")
        return passed, status, issues, warns

    def test_g01_fact_accuracy_pass(self):
        passed, status, issues, _ = self._gate(_base_daily_report())
        self.assertTrue(passed, issues)

    def test_g02_attribution_preserved(self):
        r = _base_daily_report()
        r["executive_summary"][0]["fact_summary"] = "据称武装冲突导致12人死亡。"
        passed, _, issues, _ = self._gate(r)
        self.assertTrue(passed, issues)

    def test_g03_single_source_warning_required(self):
        r = _base_daily_report()
        it = r["executive_summary"][0]
        it["single_source_warning"] = True
        it["fact_summary"] = "单一来源报道武装冲突导致12人死亡。"
        passed, _, _, warns = self._gate(r)
        # 标注了单一来源 → 无 warning issue（warns 可含其他 soft）
        self.assertTrue(passed, "single_source 已显式标注应通过")

    def test_g04_single_source_missing_warning_fails(self):
        r = _base_daily_report()
        it = r["executive_summary"][0]
        it["single_source_warning"] = True
        it["fact_summary"] = "武装冲突导致12人死亡。"   # 未标注单一来源
        passed, _, _, warns = self._gate(r)
        self.assertTrue(passed, "single_source 未标注仅 warning 不阻断（§二十三 语义）")

    def test_g05_conflict_not_confirmed(self):
        r = _base_daily_report()
        it = r["executive_summary"][0]
        it["conflicting"] = True
        it["fact_summary"] = "不同来源说法不一，武装冲突导致12人死亡。"
        passed, _, _, _ = self._gate(r)
        self.assertTrue(passed)

    def test_g06_conflict_written_as_confirmed_fails(self):
        r = _base_daily_report()
        it = r["executive_summary"][0]
        it["conflicting"] = True
        it["fact_summary"] = "已证实武装冲突导致12人死亡。"   # 冲突写成已证实
        passed, _, issues, _ = self._gate(r)
        self.assertFalse(passed)
        self.assertTrue(any("conflict" in i for i in issues))

    def test_g07_numeric_gate_new_number_fails(self):
        r = _base_daily_report()
        r["executive_summary"][0]["fact_summary"] = "武装冲突导致12人死亡，另有37人受伤。"  # 37 不在 input
        passed, _, issues, _ = self._gate(r)
        self.assertFalse(passed)
        self.assertTrue(any("numeric_gate" in i and "37" in i for i in issues))

    def test_g08_numeric_gate_input_number_ok(self):
        r = _base_daily_report()
        r["executive_summary"][0]["fact_summary"] = "cholera 疫情累计620例，15人死亡。"  # 620/15 在 input
        passed, _, issues, _ = self._gate(r)
        self.assertTrue(passed, issues)

    def test_g09_disease_numeric_preserved(self):
        r = _base_daily_report()
        r["public_health_disease_risks"] = [{
            "item_id": "OB_1", "disease_id": "cholera", "country_iso3": "TCD",
            "headline_zh": "乍得霍乱", "fact_summary": "累计620例",
            "assessment": "活跃", "outlook": "关注",
            "verification_status": "verified", "uncertainties": [],
            "source_refs": [], "latest_counts": {"confirmed_cases": 620, "deaths": 15,
                                                 "as_of_date": "2026-08-24"},
            "as_of_date": "2026-08-24"}]
        passed, _, issues, _ = self._gate(r)
        self.assertTrue(passed, issues)

    def test_g10_fact_prediction_fails(self):
        r = _base_daily_report()
        r["executive_summary"][0]["fact_summary"] = "未来72小时发生袭击的概率为87%。"
        passed, _, issues, _ = self._gate(r)
        self.assertFalse(passed)
        self.assertTrue(any("fact_prediction" in i for i in issues))

    def test_g11_fact_prediction_wording_fails(self):
        r = _base_daily_report()
        r["executive_summary"][0]["fact_summary"] = "袭击将必然发生。"
        passed, _, issues, _ = self._gate(r)
        self.assertFalse(passed)

    def test_g12_dup_master_fails(self):
        r = _base_daily_report()
        r["terrorism_armed_violence"] = [dict(r["executive_summary"][0])]  # 同 master_event_id
        passed, _, issues, _ = self._gate(r)
        self.assertFalse(passed)
        self.assertTrue(any("dup_master" in i for i in issues))


class TestGoldenWeekly(unittest.TestCase):
    """§三十 Weekly output fixtures（8）。"""

    def _gate(self, report):
        inp = json.loads(json.dumps(MOCK_WEEKLY_INPUT))
        return run_quality_gate(report, inp, "country_weekly")

    def _weekly(self):
        return {
            "report_id": "WEEKLY_TCD_2026-08-30", "report_type": "country_weekly",
            "title": "乍得周报", "country_iso3": "TCD",
            "week_start": "2026-08-24", "week_end": "2026-08-30",
            "generated_at": "2026-08-30T18:00:00+08:00",
            "executive_assessment": "本周5起事件。",
            "major_events": [], "security_trend": "本周事件数量5，较上周上升。",
            "political_social_stability": [], "terrorism_armed_violence": [],
            "disease_public_health": [],
            "week_over_week_changes": [{"field": "event_count", "direction": "up"}],
            "next_week_watch_items": [],
            "metrics": {"event_count": 5, "verified_event_count": 3,
                        "armed_attack_count": 3, "civil_unrest_count": 1,
                        "major_crime_count": 0, "natural_disaster_count": 0,
                        "fatalities_known": None, "injuries_known": None,
                        "multi_source_event_count": 2, "new_outbreak_count": 0,
                        "active_outbreak_count": 1,
                        "comparison": {"event_count": "up"}},
            "source_notes": [{"source_id": "ssd_eyeradio"}],
            "generation_metadata": {"provider_name": "mock", "model_name": "mock",
                                    "prompt_version": "1.0.0",
                                    "usage_purpose": "development_test",
                                    "report_status": "draft"},
        }

    def test_w01_metrics_pass(self):
        passed, status, issues, _ = self._gate(self._weekly())
        self.assertTrue(passed, issues)

    def test_w02_comparison_matches_input(self):
        r = self._weekly()
        passed, _, issues, _ = self._gate(r)
        self.assertTrue(passed)

    def test_w03_metrics_mismatch_fails(self):
        r = self._weekly()
        r["metrics"] = {"event_count": 99}   # 与 input 5 不符
        passed, _, issues, _ = self._gate(r)
        self.assertFalse(passed)

    def test_w04_fatalities_unknown_not_zero(self):
        r = self._weekly()
        r["metrics"]["fatalities_known"] = None
        passed, _, issues, _ = self._gate(r)
        self.assertTrue(passed, issues)

    def test_w05_fabricated_number_fails(self):
        r = self._weekly()
        r["executive_assessment"] = "本周发生7起事件。"   # 7 不在 input
        passed, _, issues, _ = self._gate(r)
        self.assertFalse(passed)
        self.assertTrue(any("numeric_gate" in i for i in issues))

    def test_w06_disease_numeric(self):
        r = self._weekly()
        r["disease_public_health"] = [{
            "item_id": "OB_1", "disease_id": "cholera", "country_iso3": "TCD",
            "fact_summary": "活跃", "latest_counts": {"confirmed_cases": 620},
            "source_refs": []}]
        passed, _, issues, _ = self._gate(r)
        self.assertTrue(passed, issues)

    def test_w07_week_change_only_from_input(self):
        r = self._weekly()
        r["week_over_week_changes"] = [{"field": "event_count", "direction": "up"}]
        passed, _, issues, _ = self._gate(r)
        self.assertTrue(passed)

    def test_w08_source_notes_valid(self):
        r = self._weekly()
        passed, _, issues, _ = self._gate(r)
        self.assertTrue(passed, issues)


class TestGoldenBrief(unittest.TestCase):
    """§三十 Brief output fixtures（6）。"""

    def _gate(self, report):
        inp = json.loads(json.dumps(MOCK_BRIEF_INPUT))
        return run_quality_gate(report, inp, "major_event_brief")

    def _brief(self):
        return {
            "brief_id": "BRF_E_BRIEF1", "report_type": "major_event_brief",
            "title": "南苏丹武装冲突", "event_time": "2026-08-26T06:00:00+00:00",
            "country": "South Sudan", "country_iso3": "SSD", "location": "CITY_ALPHA",
            "what_happened": "武装冲突发生。",
            "confirmed_facts": [{"fact": "deaths=25", "source_refs": ["E_BRIEF1"]}],
            "uncertainties": [], "verification_status": "verified",
            "verification_confidence": None,
            "immediate_implications": ["关注后续调查"], "watch_items": [],
            "source_notes": [{"source_id": "E_BRIEF1"}],
            "generation_metadata": {"provider_name": "mock", "model_name": "mock",
                                    "prompt_version": "1.0.0",
                                    "usage_purpose": "development_test",
                                    "report_status": "draft"},
        }

    def test_b01_brief_pass(self):
        passed, status, issues, _ = self._gate(self._brief())
        self.assertTrue(passed, issues)

    def test_b02_new_number_fails(self):
        r = self._brief()
        r["what_happened"] = "武装冲突导致25人死亡，另有3人失踪。"   # 3 不在 input
        passed, _, issues, _ = self._gate(r)
        self.assertFalse(passed)
        self.assertTrue(any("numeric_gate" in i and "3" in i for i in issues))

    def test_b03_no_tactical_expansion(self):
        r = self._brief()
        r["what_happened"] = "武装冲突发生。"
        passed, _, issues, _ = self._gate(r)
        self.assertTrue(passed)

    def test_b04_prediction_fails(self):
        r = self._brief()
        r["immediate_implications"] = ["袭击概率87%"]
        passed, _, issues, _ = self._gate(r)
        self.assertFalse(passed)

    def test_b05_source_refs_valid(self):
        r = self._brief()
        passed, _, issues, _ = self._gate(r)
        self.assertTrue(passed)

    def test_b06_fabricated_source_fails(self):
        r = self._brief()
        r["source_notes"] = [{"source_id": "made_up_source"}]
        passed, _, issues, _ = self._gate(r)
        self.assertFalse(passed)
        self.assertTrue(any("source" in i for i in issues))


class TestTemporalWindow(unittest.TestCase):
    """§二 Temporal Window 语义。"""

    def test_buckets(self):
        from datetime import datetime
        cd = datetime(2026, 7, 28)
        self.assertEqual(temporal_bucket({"published_at": "2026-07-28T10:00:00"}, cd)[0], "new_24h")
        self.assertEqual(temporal_bucket({"published_at": "2026-07-26T10:00:00"}, cd)[0], "ongoing_72h")
        self.assertEqual(temporal_bucket({"published_at": "2026-07-23T10:00:00"}, cd)[0], "trend_7d")
        self.assertEqual(temporal_bucket({"published_at": "2026-07-10T10:00:00"}, cd)[0], "outside_7d")

    def test_outside_7d_excluded_from_selection(self):
        events = [
            {"event_id": "n1", "master_event_id": "ME_n1", "event_type": "armed_attack",
             "country_iso3": "TCD", "verification_status": "verified",
             "source_count": 2, "source_id": "s1", "published_at": "2026-07-28T09:00:00",
             "deaths": 10, "category": "security", "timeline_status": "ongoing"},
            {"event_id": "o1", "master_event_id": "ME_o1", "event_type": "armed_attack",
             "country_iso3": "TCD", "verification_status": "verified",
             "source_count": 2, "source_id": "s1", "published_at": "2026-07-01T09:00:00",
             "deaths": 30, "category": "security", "timeline_status": "stable"},
        ]
        sel, stats, _ = select_daily(events, cutoff="2026-07-28")
        self.assertEqual(stats["social_outside_7d"], 1)
        self.assertEqual(len(sel["security"]), 1)
        self.assertEqual(sel["security"][0]["event_id"], "n1")


class TestPipeline(unittest.TestCase):
    """§十九 Mock contract + renderer + runtime。"""

    def test_mock_daily_gate(self):
        report, meta, status = run_report("africa_daily", MOCK_DAILY_INPUT,
                                          provider=MockReportProvider())
        passed, qs, issues, _ = run_quality_gate(report, MOCK_DAILY_INPUT, "africa_daily")
        self.assertEqual(status, "generated")
        self.assertTrue(passed, issues)

    def test_mock_weekly_gate(self):
        report, meta, status = run_report("country_weekly", MOCK_WEEKLY_INPUT,
                                          provider=MockReportProvider())
        passed, qs, issues, _ = run_quality_gate(report, MOCK_WEEKLY_INPUT, "country_weekly")
        self.assertTrue(passed, issues)

    def test_mock_brief_gate(self):
        report, meta, status = run_report("major_event_brief", MOCK_BRIEF_INPUT,
                                          provider=MockReportProvider())
        passed, qs, issues, _ = run_quality_gate(report, MOCK_BRIEF_INPUT, "major_event_brief")
        self.assertTrue(passed, issues)

    def test_renderer_contains_sections(self):
        report, _, _ = run_report("africa_daily", MOCK_DAILY_INPUT,
                                  provider=MockReportProvider())
        md = render_daily_markdown(report)
        self.assertIn("一、核心摘要", md)
        self.assertIn("来源：", md)

    def test_preview_not_in_dist(self):
        self.assertFalse((ROOT / "dist" / "data" / "runtime").exists())
        gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("data/runtime", gi)

    def test_canonical_public_unchanged(self):
        for p in ("data/events.json", "data/public/published_events.json",
                  "data/canonical/articles.json",
                  "data/disease/canonical/outbreak_events.json"):
            self.assertTrue((ROOT / p).exists(), p)

    def test_schema_load_all_three(self):
        for task in ("africa_daily", "country_weekly", "major_event_brief"):
            s = _load_schema(task)
            self.assertIn("$schema", s)


if __name__ == "__main__":
    unittest.main()
