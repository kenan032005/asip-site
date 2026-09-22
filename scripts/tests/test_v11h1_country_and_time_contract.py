#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V1.1-H1 契约测试：国家联结键（ISO3）归一 + 三时间契约。

锁定两个已确认缺陷（2026-09-11 定位）：
  B03 国家联结：social_timelines 未带国家 → master_events 回退 cluster 元数据得到 ISO2（NE/TD），
      而 country_snapshots 以 ISO3（NER/TCD）为键 → 国家级视图 24h/7d 恒为 0。
  B04 时间契约：视图只有 generated_at / latest_data_time，窗口基准用的是 latest event time，
      导致"无新事件时窗口停住"，且无法区分 processing cutoff / 最新事件 / 构建时间。
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.frontend import build_frontend_views as bfv  # noqa: E402


COUNTRY_REF = bfv.load_country_ref(str(ROOT / "data"))


class TestCountryNormalization(unittest.TestCase):
    def test_iso2_to_iso3_normalization(self):
        for a2, a3 in (("NE", "NER"), ("TD", "TCD"), ("NG", "NGA")):
            r = bfv.normalize_country_iso3(a2, COUNTRY_REF)
            self.assertTrue(r["resolved"], a2)
            self.assertEqual(r["iso3"], a3)
            self.assertEqual(r["normalization_basis"], "iso2_to_iso3_approved_map")

    def test_iso3_pass_through(self):
        r = bfv.normalize_country_iso3("TCD", COUNTRY_REF)
        self.assertEqual(r["iso3"], "TCD")
        self.assertEqual(r["normalization_basis"], "iso3_passthrough")

    def test_unknown_country_not_guessed(self):
        r = bfv.normalize_country_iso3("XX", COUNTRY_REF)
        self.assertFalse(r["resolved"])
        self.assertIsNone(r["iso3"])
        r2 = bfv.normalize_country_iso3("", COUNTRY_REF)
        self.assertFalse(r2["resolved"])


class TestCountryJoin(unittest.TestCase):
    EVENTS = [
        {"event_id": "E1", "event_time": "2026-09-11T02:00:00Z", "country_iso3": "TD"},   # ISO2
        {"event_id": "E2", "event_time": "2026-09-11T03:00:00Z", "country_iso3": "NER"},  # ISO3
        {"event_id": "E3", "event_time": "2026-09-05T03:00:00Z", "country_iso3": "NE"},   # ISO2, 7d 内
        {"event_id": "E4", "event_time": "2026-08-01T03:00:00Z", "country_iso3": "NG"},   # 7d 外
    ]
    COUNTRIES = [{"cn": "乍得", "en": "Chad", "risk_level": 4},
                 {"cn": "尼日尔", "en": "Niger", "risk_level": 4}]
    DATA_AS_OF = "2026-09-11T14:19:43+00:00"

    def _snaps(self):
        cn2iso, iso2cn, iso2en, iso2risk = bfv.build_country_indexes(self.COUNTRIES)
        views = bfv.build_country_snapshots(self.COUNTRIES, self.EVENTS, [], [],
                                            cn2iso, iso2cn, iso2en, iso2risk,
                                            country_ref=COUNTRY_REF,
                                            data_as_of=self.DATA_AS_OF,
                                            generated_at="2026-09-11T23:00:00+08:00")
        return {s["iso3"]: s for s in views["snapshots"]}

    def test_country_snapshot_uses_iso3_join(self):
        s = self._snaps()
        self.assertEqual(s["TCD"]["events_24h"], 1)   # E1（ISO2→ISO3 命中）
        self.assertEqual(s["NER"]["events_7d"], 2)    # E2 + E3

    def test_country_24h_window_uses_data_as_of(self):
        s = self._snaps()
        # E3 在 7d 内但不在 24h 内（窗口相对 data_as_of，而非最新事件时间）
        self.assertEqual(s["NER"]["events_24h"], 1)
        self.assertEqual(s["NER"]["data_as_of"], self.DATA_AS_OF)

    def test_country_7d_window_uses_data_as_of(self):
        s = self._snaps()
        self.assertEqual(s["TCD"]["events_7d"], 1)    # E4（08-01，NG）不属 TCD

    def test_zero_event_country_can_be_current(self):
        """无近期事件的国家 events=0，但 data_as_of 仍跟随当前 processing window → CURRENT。"""
        cn2iso, iso2cn, iso2en, iso2risk = bfv.build_country_indexes([{"cn": "加纳", "en": "Ghana"}])
        v = bfv.build_country_snapshots([{"cn": "加纳", "en": "Ghana"}], self.EVENTS, [], [],
                                        cn2iso, iso2cn, iso2en, iso2risk,
                                        country_ref=COUNTRY_REF, data_as_of=self.DATA_AS_OF,
                                        generated_at="2026-09-11T23:00:00+08:00")
        g = v["snapshots"][0]
        self.assertEqual(g["events_24h"], 0)
        self.assertEqual(g["events_7d"], 0)
        self.assertEqual(g["data_as_of"], self.DATA_AS_OF, "零事件国家仍必须是当前处理窗口")

    def test_map_and_risk_country_sets_match(self):
        snaps = self._snaps()
        geo = (ROOT / "assets" / "geo" / "africa-countries.js").read_text(encoding="utf-8")
        miss = [i for i in snaps if i not in geo]
        self.assertEqual(miss, [], "map geo 与 snapshot 国家集合必须一致（缺失：%s）" % miss)


class TestTimeContract(unittest.TestCase):
    DATA_AS_OF = "2026-09-11T14:19:43+00:00"
    EVENTS = [{"event_id": "E1", "event_time": "2026-09-11T02:15:31Z", "country_iso3": "TCD"}]

    def _ov(self):
        return bfv.build_site_overview(self.EVENTS, [], [{"cn": "乍得", "en": "Chad", "risk_level": 4}],
                                       {}, [], None, {},
                                       data_as_of=self.DATA_AS_OF,
                                       generated_at="2026-09-11T23:00:00+08:00",
                                       data_as_of_source="test")

    def test_data_as_of_not_generated_at(self):
        ov = self._ov()
        self.assertEqual(ov["data_as_of"], self.DATA_AS_OF)
        self.assertNotEqual(ov["data_as_of"], ov["generated_at"],
                            "generated_at 不得冒充 data_as_of")
        self.assertIn("data_as_of_bj", ov)

    def test_latest_event_time_not_data_as_of(self):
        ov = self._ov()
        self.assertNotEqual(ov["latest_verified_event_time"], ov["data_as_of"])
        self.assertEqual(ov["latest_verified_event_time"], "2026-09-11T02:15:31Z")

    def test_header_uses_data_as_of(self):
        src = (ROOT / "assets" / "js" / "home-v11.js").read_text(encoding="utf-8")
        i_asof = src.find("data_as_of_bj")
        i_latest = src.find("latest_data_time_bj")
        self.assertGreater(i_asof, -1, "首页必须读取 data_as_of_bj")
        self.assertTrue(i_latest == -1 or i_asof < i_latest,
                        "首页表头/窗口必须优先使用 data_as_of，而不是 latest_data_time_bj")
        for f in ("assets/js/common.js", "assets/js/frontend.js"):
            t = (ROOT / f).read_text(encoding="utf-8")
            self.assertIn("数据截至", t, "%s 表头标签必须为『数据截至』" % f)


if __name__ == "__main__":
    unittest.main(verbosity=2)
