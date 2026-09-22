#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c4a_report_factory.py — C4-A Report Factory 契约测试。

对应 C4-A §七/§十二/§二十六/§三十一 的要求（25+ 项）。
纯本地、确定性、不调用 AI、不写 data/reports。
"""
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.report import factory as F  # noqa: E402


class DailyWindowTest(unittest.TestCase):
    """§一/§二/§五：滚动 24h + 20:00 BJT cutoff"""

    def test_01_daily_window_is_rolling_24h(self):
        s, e = F.daily_window("2026-09-18")
        self.assertEqual((e - s), timedelta(hours=24))
        self.assertEqual(F.DAILY_WINDOW_TYPE, "ROLLING_24H")

    def test_02_daily_cutoff_is_20_bjt(self):
        s, e = F.daily_window("2026-09-18")
        self.assertEqual(e.hour, 20)
        self.assertEqual(str(e.utcoffset()), "8:00:00")
        self.assertEqual(F.DAILY_CUTOFF_HOUR_BJT, 20)
        self.assertEqual(F.REPORT_TIMEZONE, "Asia/Shanghai")

    def test_03_daily_generated_at_does_not_shift_period(self):
        # window 只由 report_date 决定，与"现在几点/什么时候生成"无关
        a = F.daily_window("2026-09-18")
        b = F.daily_window(date(2026, 9, 18))
        self.assertEqual(a, b)
        self.assertEqual(a[0].isoformat(), "2026-09-17T20:00:00+08:00")
        self.assertEqual(a[1].isoformat(), "2026-09-18T20:00:00+08:00")

    def test_04_daily_same_report_date_has_stable_window(self):
        for _ in range(3):
            self.assertEqual(F.daily_window("2026-09-10"), F.daily_window("2026-09-10"))

    def test_05_daily_historical_window_not_based_on_current_wall_clock(self):
        hist = F.daily_window("2026-09-05")
        self.assertEqual(hist[1].date(), date(2026, 9, 5))
        now_win = F.daily_window(datetime.now(F.BJT).date())
        self.assertNotEqual(hist, now_win)

    def test_06_daily_id_uses_cutoff_report_date(self):
        self.assertEqual(F.build_report_id("africa_daily", report_date="2026-09-18"),
                         "DAILY_20260918")


class WeekWindowTest(unittest.TestCase):
    """§六：Sunday→Sunday，闭区间"""

    def test_07_weekly_uses_natural_week_boundary(self):
        s, e = F.week_window("2026-09-13")
        self.assertEqual(s.weekday(), 6)
        self.assertEqual(e.weekday(), 6)
        self.assertEqual((e - s).days, 7)
        self.assertEqual(F.WEEK_IDENTITY, "SUNDAY_TO_SUNDAY")
        self.assertEqual(str(s), "2026-09-06")

    def test_08_week_requires_sunday(self):
        with self.assertRaises(ValueError):
            F.week_window("2026-09-12")     # 周六

    def test_09_week_interval_is_closed(self):
        self.assertEqual(F.WEEK_INTERVAL_INCLUSIVITY, "CLOSED")
        s, e = F.week_window("2026-09-13")
        d = s
        incl = []
        while d <= e:
            incl.append(d)
            d += timedelta(days=1)
        self.assertEqual(len(incl), 8)      # 闭区间 → 两端都含 → 8 个日期点（既有语义）

    def test_10_country_weekly_id_matches_existing_convention(self):
        # 既有实例：WEEKLY_TCD_20260913
        self.assertEqual(
            F.build_report_id("country_weekly", week_end="2026-09-13", country_iso3="TCD"),
            "WEEKLY_TCD_20260913")

    def test_11_africa_weekly_id_stable(self):
        a = F.build_report_id("africa_weekly", week_end="2026-09-13")
        b = F.build_report_id("africa_weekly", week_end=date(2026, 9, 13))
        self.assertEqual(a, b)
        self.assertEqual(a, "AFRICA_WEEKLY_20260913")

    def test_12_report_id_is_stable(self):
        args = ("country_weekly", None, "2026-09-13", "NER")
        self.assertEqual(F.build_report_id(*args), F.build_report_id(*args))


class EligibilityFilterTest(unittest.TestCase):
    """§十六：报告层过滤，不改全站 relevance"""

    def test_13_report_filter_excludes_pure_sports(self):
        ok, reason = F.report_eligibility("Nigeria to face FIFA-banned Russia in friendly")
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("PURE_NON_SECURITY"))

    def test_14_report_filter_keeps_security_related_sports_incident(self):
        ok, reason = F.report_eligibility("Stampede at football stadium kills 12 fans")
        self.assertTrue(ok)
        self.assertTrue(reason.startswith("SECURITY_RELATED"))
        ok2, _ = F.report_eligibility("Football match abandoned after violent clashes")
        self.assertTrue(ok2)

    def test_15_filter_report_facts_splits_lists(self):
        items = [{"title_original": "FIFA friendly announced", "event_type": "other_security"},
                 {"title_original": "Explosion kills five in market", "event_type": "armed_conflict"}]
        kept, excluded = F.filter_report_facts(items)
        self.assertEqual(len(kept), 1)
        self.assertEqual(len(excluded), 1)
        self.assertEqual(kept[0]["_eligibility"], "ELIGIBLE")

    def test_16_filter_is_deterministic(self):
        a = F.report_eligibility("Coupe du Monde review")
        b = F.report_eligibility("Coupe du Monde review")
        self.assertEqual(a, b)

    def test_17_filter_does_not_touch_other_layers(self):
        src = (ROOT / "scripts" / "report" / "factory.py").read_text(encoding="utf-8")
        self.assertIn("仅作用于 Report Fact Pack", src)
        # 不得改动 news stream / homepage relevance 的代码
        self.assertNotIn("news_stream.json", src)
        self.assertNotIn("homepage_fact_pack", src)


class HashAndCacheTest(unittest.TestCase):
    """§十八/§十九/§二十/§二十一"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="c4a_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _pack(self, extra=None):
        p = {"report_id": "DAILY_20260918", "facts": [{"n": 3}, {"n": 5}]}
        if extra:
            p.update(extra)
        return p

    def test_18_report_fact_pack_hash_stable(self):
        self.assertEqual(F.fact_pack_hash(self._pack()), F.fact_pack_hash(self._pack()))

    def test_19_fact_pack_hash_ignores_wall_clock_metadata(self):
        a = self._pack({"generated_at": "2026-09-19T00:00:00+08:00", "cutoff": "x"})
        b = self._pack({"generated_at": "2026-09-20T11:11:11+08:00", "cutoff": "y"})
        self.assertEqual(F.fact_pack_hash(a), F.fact_pack_hash(b))

    def test_20_identical_report_input_zero_new_ai_calls(self):
        c = F.ReportCache(os.path.join(self.tmp, "cache.json"))
        fph = F.fact_pack_hash(self._pack())
        ih = F.input_hash("DAILY_20260918", fph, "deepseek-flash", "africa_daily")
        self.assertTrue(c.should_call(ih))
        c.put_full(ih, {"executive_assessment": "x"})
        self.assertFalse(c.should_call(ih), "同输入第二遍不得再调用 provider")

    def test_21_report_negative_cache(self):
        c = F.ReportCache(os.path.join(self.tmp, "cache.json"))
        fph = F.fact_pack_hash(self._pack())
        ih = F.input_hash("DAILY_20260918", fph, "deepseek-flash", "africa_daily")
        c.put_negative(ih, "FACT_GATE_REJECTED")
        self.assertTrue(c.is_negative(ih))
        self.assertFalse(c.should_call(ih), "终态负缓存必须让第二遍 0 调用")

    def test_22_negative_cache_persists_no_rejected_text(self):
        c = F.ReportCache(os.path.join(self.tmp, "cache.json"))
        c.put_negative("IH1", "FACT_GATE_REJECTED")
        raw = open(os.path.join(self.tmp, "cache.json"), encoding="utf-8").read()
        for banned in ("executive_assessment", "trend_analysis", "raw_response", "summary_cn"):
            self.assertNotIn(banned, raw)
        rec = json.load_ish(raw) if hasattr(F, "json_lish") else None
        import json as _j
        rec = _j.loads(raw)["IH1"]
        self.assertEqual(set(rec.keys()) & {"kind", "reason", "input_hash"}, {"kind", "reason", "input_hash"})

    def test_23_changed_fact_pack_hash_allows_retry(self):
        c = F.ReportCache(os.path.join(self.tmp, "cache.json"))
        ih1 = F.input_hash("D", F.fact_pack_hash(self._pack()), "deepseek-flash", "africa_daily")
        ih2 = F.input_hash("D", F.fact_pack_hash(self._pack({"facts": [{"n": 9}]})),
                           "deepseek-flash", "africa_daily")
        c.put_negative(ih1, "FACT_GATE_REJECTED")
        self.assertFalse(c.should_call(ih1))
        self.assertTrue(c.should_call(ih2), "fact pack 变化 → 允许重试")

    def test_24_changed_model_or_prompt_allows_retry(self):
        fph = F.fact_pack_hash(self._pack())
        a = F.input_hash("D", fph, "deepseek-flash", "africa_daily")
        b = F.input_hash("D", fph, "deepseek-v4-flash", "africa_daily")
        c = F.input_hash("D", fph, "deepseek-flash", "africa_daily", prompt_version="analysis-v1.0.1")
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)


class FactGateTest(unittest.TestCase):
    """§二十三：分析层不得引入新数字/新国家"""

    def test_25_fact_gate_rejects_new_numbers(self):
        fp = {"facts": [{"text": "attack kills 3 people"}]}
        ok, why = F.analysis_fact_gate(fp, {"executive_assessment": "袭击造成 99 人死亡"})
        self.assertFalse(ok)
        self.assertTrue(any("NEW_NUMBER" in r for r in why))

    def test_26_fact_gate_rejects_new_country(self):
        fp = {"facts": [{"iso3": "TCD"}]}
        ok, why = F.analysis_fact_gate(fp, {"trend_analysis": "NER 局势升级"})
        self.assertFalse(ok)

    def test_27_fact_gate_accepts_faithful_analysis(self):
        fp = {"facts": [{"text": "attack kills 3 people", "iso3": "TCD"}]}
        ok, why = F.analysis_fact_gate(
            fp, {"executive_assessment": "TCD 发生袭击，3 人死亡", "watch_points": ["持续关注"]})
        self.assertTrue(ok, why)

    def test_28_fact_gate_requires_analysis(self):
        ok, why = F.analysis_fact_gate({"facts": []}, None)
        self.assertFalse(ok)
        self.assertIn("NO_ANALYSIS", why)

    def test_29_ai_allowed_fields_locked(self):
        self.assertEqual(F.AI_ALLOWED_FIELDS,
                         ("executive_assessment", "trend_analysis", "outlook", "watch_points"))
        src = (ROOT / "scripts" / "report" / "factory.py").read_text(encoding="utf-8")
        for banned in ("source_refs", "report period", "priority_country"):
            self.assertNotIn('"%s":' % banned, src.split("AI_ALLOWED_FIELDS = (")[1][:200])


class IndexTest(unittest.TestCase):
    """§二十六/§二十七"""

    def test_30_report_index_stable(self):
        reps = [{"report_id": "DAILY_20260918", "period_end": "2026-09-18", "status": "FALLBACK"},
                {"report_id": "DAILY_20260917", "period_end": "2026-09-17", "status": "FULL"}]
        a = F.build_report_index(reps)
        b = F.build_report_index(list(reversed(reps)))
        self.assertEqual(a, b, "索引必须稳定（与输入顺序无关）")
        self.assertEqual([r["report_id"] for r in a["reports"]],
                         ["DAILY_20260918", "DAILY_20260917"])

    def test_31_mock_reports_excluded_from_real_index(self):
        reps = [{"report_id": "DAILY_DEV", "is_mock": True, "period_end": "2026-09-01"},
                {"report_id": "DAILY_20260918", "is_mock": False, "period_end": "2026-09-18"}]
        idx = F.build_report_index(reps, real_only=True)
        self.assertEqual(idx["count"], 1)
        self.assertNotIn("DAILY_DEV", [r["report_id"] for r in idx["reports"]])
        all_idx = F.build_report_index(reps, real_only=False)
        self.assertEqual(all_idx["count"], 2)

    def test_32_homepage_latest_reports_source_is_real_index(self):
        """首页 latest 只能来自 real-only 索引（防 placeholder/mock）。"""
        reps = [{"report_id": "DAILY_DEV", "is_mock": True, "period_end": "2026-12-31"},
                {"report_id": "DAILY_20260918", "is_mock": False, "period_end": "2026-09-18"}]
        idx = F.build_report_index(reps, real_only=True)
        latest = idx["reports"][0]["report_id"]
        self.assertEqual(latest, "DAILY_20260918")

    def test_33_generated_at_not_used_as_data_as_of(self):
        r = {"report_id": "D", "generated_at": "2026-09-19T21:00:00+08:00",
             "data_as_of": "2026-09-18T12:00:00+00:00"}
        idx = F.build_report_index([r])
        row = idx["reports"][0]
        self.assertEqual(row["data_as_of"], "2026-09-18T12:00:00+00:00")
        self.assertNotEqual(row["data_as_of"], row["generated_at"])


class PlannerTest(unittest.TestCase):
    """§十二/§十三：配置驱动，不用 TOP5"""

    def test_34_priority_country_selection_is_deterministic(self):
        en, dis = F.enabled_priority_countries()
        self.assertEqual(sorted(en), ["NER", "SSD", "TCD"])
        self.assertEqual(sorted(dis), ["BEN", "ETH"])
        self.assertEqual(F.PRIORITY_COUNTRY_POLICY, "CONFIG_DRIVEN")
        en2, _ = F.enabled_priority_countries()
        self.assertEqual(en, en2)

    def test_35_selection_does_not_override_config(self):
        en, dis = F.enabled_priority_countries()
        for iso in ("BEN", "ETH"):
            self.assertNotIn(iso, en)
        # 明确不得出现动态 TOP5 口径
        src = (ROOT / "scripts" / "report" / "factory.py").read_text(encoding="utf-8")
        self.assertNotIn("TOP5", src)
        self.assertNotIn("top_5", src)

    def test_36_one_country_one_weekly_per_week(self):
        plan = F.plan_report_backfill(ROOT, days=14)
        ids = [c["report_id"] for c in plan["COUNTRY_WEEKLY_TARGETS"]]
        self.assertEqual(len(ids), len(set(ids)), "1 country 1 week 最多 1 份")
        for c in plan["COUNTRY_WEEKLY_TARGETS"]:
            self.assertEqual(c["selection_reason"], "CONFIGURED_PRIORITY_COUNTRY")

    def test_37_backfill_targets_and_limits(self):
        plan = F.plan_report_backfill(ROOT, days=14)
        self.assertEqual(plan["DAILY_TARGET"], 14)
        self.assertEqual(plan["DAILY_WINDOW_TYPE"], "ROLLING_24H")
        self.assertEqual(plan["WEEK_IDENTITY"], "SUNDAY_TO_SUNDAY")
        self.assertEqual(plan["COUNTRY_WEEKLY_TARGET"],
                         plan["WEEKLY_TARGET"] * len(plan["ENABLED_PRIORITY_COUNTRIES"]))
        self.assertEqual(plan["TOTAL_REPORT_TARGET"],
                         plan["DAILY_TARGET"] + plan["WEEKLY_TARGET"] + plan["COUNTRY_WEEKLY_TARGET"])
        # 每日 target 的窗口必须互不相同（历史不得同内容）
        wins = {d["period_start"] for d in plan["DAILY_TARGET_DATES"]}
        self.assertEqual(len(wins), 14)

    def test_38_registered_types_include_africa_weekly(self):
        reg = F.registered_report_types()
        for t in F.REPORT_TYPES:
            self.assertIn(t, reg)
        self.assertFalse(reg["major_event_brief"]["auto_publication"])
        self.assertFalse(F.MAJOR_BRIEF_AUTO_PUBLICATION)

    def test_39_statuses_defined(self):
        self.assertEqual(F.REPORT_STATUSES, ("FULL", "FALLBACK", "LOW_DATA", "FAIL"))
        self.assertEqual(F.PUBLISHABLE_STATUSES, ("FULL", "FALLBACK", "LOW_DATA"))
        self.assertNotIn("FAIL", F.PUBLISHABLE_STATUSES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
