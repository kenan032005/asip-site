#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8C Package 2 — Manual Human Review Trial 输入构造测试（不调 API）。

覆盖：
  - 真实输入来自 committed canonical（fixtures/golden/mock 均不用）
  - eligibility / 时间窗口 / 去重
  - 统计字段齐全（cutoff / record count / country / source coverage）
  - report input 契约结构（daily / weekly）
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.safety.manual_trial import build_inputs


class TestTrialInputs(unittest.TestCase):
    def test_inputs_constructed(self):
        inp = build_inputs()
        stats = inp["stats"]
        self.assertFalse(stats["fixtures_used"])
        self.assertFalse(stats["golden_set_used"])
        self.assertFalse(stats["mock_used"])
        self.assertEqual(stats["input_source"], "committed canonical (event_clusters.json / outbreak_events.json)")
        self.assertGreaterEqual(stats["social_eligible_total"], 1)
        self.assertGreaterEqual(stats["disease_eligible_total"], 1)
        self.assertIn("cutoff", stats)
        self.assertTrue(stats["country_coverage_social"])
        self.assertTrue(stats["source_coverage_social"])

    def test_dedup(self):
        inp = build_inputs()
        ids = [e.get("event_id") for e in inp["social_candidates"]]
        self.assertEqual(len(ids), len(set(ids)))
        dids = [d.get("disease_event_id") for d in inp["disease_candidates"]]
        self.assertEqual(len(dids), len(set(dids)))

    def test_eligibility_only(self):
        inp = build_inputs()
        evs = json.loads((ROOT / "data/canonical/event_clusters.json").read_text(encoding="utf-8"))["items"]
        elig = {e["event_id"] for e in evs if e.get("current_policy_passed")}
        for e in inp["social_candidates"]:
            self.assertIn(e["event_id"], elig)

    def test_daily_input_contract(self):
        inp = build_inputs()
        d = inp["daily_input"]
        self.assertEqual(d["report_type"], "africa_daily")
        for sec in ("executive_summary", "major_security_developments",
                    "public_health_disease"):
            self.assertIn(sec, d["sections"])
        self.assertIn("cutoff", d)

    def test_weekly_input_contract(self):
        inp = build_inputs()
        for key in ("weekly_tcd_input", "weekly_ssd_input"):
            w = inp[key]
            self.assertEqual(w["report_type"], "country_weekly")
            self.assertIn("week_start", w)
            self.assertIn("week_end", w)
            self.assertIn("country_iso3", w)

    def test_ssd_low_data_honest(self):
        inp = build_inputs()
        # SSD canonical 无事件 → 如实 low-data（不编造）
        self.assertEqual(inp["stats"]["weekly_ssd_social_count"], 0)


if __name__ == "__main__":
    unittest.main()
