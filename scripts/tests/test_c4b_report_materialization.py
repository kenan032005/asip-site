#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c4b_report_materialization.py — C4-B 物化 + 来源策略 + UI 契约测试。

覆盖 C4-B §八（来源策略 10 项）、§九（物化/UI 关键契约 12 项）、§十 的 Python 侧代理
（renderer 坏值契约由 scripts/tests/report_ui_contract.js 承担，本文件负责调用它）。
纯本地、确定性、不调用 AI、不写业务 data/。
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts")):
    sys.path.insert(0, p)

from scripts.report import factory as F            # noqa: E402
from scripts.report import materialize as M        # noqa: E402

NODE = os.environ.get("ASIP_NODE") or "node"
WF = ".github/workflows/asip-v11-c3-ai.yml"


def _cpfile(src, dst):
    d = os.path.dirname(dst)
    if d:
        os.makedirs(d, exist_ok=True)
    if os.path.exists(src):
        shutil.copy2(src, dst)


def mktmp_root(with_ai=False):
    """最小可物化根：canonical + views + 可选既有 AI artifacts。"""
    t = tempfile.mkdtemp(prefix="c4b_")
    for rel in ("data/canonical/articles.json", "data/canonical/event_clusters.json",
                "data/status.json", "data/views/report_index.json",
                "data/views/country_snapshots.json"):
        _cpfile(str(ROOT / rel), os.path.join(t, rel.replace("/", os.sep)))
    return t


class SourcePolicyTest(unittest.TestCase):
    """§八：SOURCE_BACKED_ONLY"""

    def setUp(self):
        self.t = mktmp_root()

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    def test_01_unattributed_fact_never_enters_key_events(self):
        ev = [{"event_id": "E1", "country_iso3": "TCD", "event_type": "armed_conflict",
               "event_time": "2026-09-18", "source_count": 1, "title_original": "x"}]
        kept, excluded = M.source_backed_pool(ev, {})
        self.assertEqual(kept, [])
        self.assertEqual(excluded, 1)
        rep, fp = self._materialize_one(ev)
        self.assertEqual(rep["fact_count"], 0)
        self.assertIn("source-backed event coverage is limited", rep["coverage_notes"])

    def test_02_unattributed_fact_never_enters_ai_fact_pack(self):
        ev = [{"event_id": "E1", "country_iso3": "TCD", "event_type": "armed_conflict",
               "event_time": "2026-09-18", "source_count": 1, "title_original": "x"}]
        rep, fp = self._materialize_one(ev)
        self.assertEqual(fp.get("social_facts"), [])
        self.assertEqual(fp.get("disease_facts"), [])

    def test_03_low_source_coverage_produces_low_data(self):
        ev = [{"event_id": "E%d" % i, "country_iso3": "TCD", "event_type": "armed_conflict",
               "event_time": "2026-09-18", "source_count": 1, "source_groups": ["g%d" % i],
               "title_original": "x%d" % i} for i in range(3)]
        rep, _ = self._materialize_one(ev)
        self.assertEqual(rep["status"], M.STATUS_LOW_DATA, "3 < DAILY_SECURITY_MIN(8)")

    def test_04_low_data_report_still_materializes(self):
        ev = [{"event_id": "E1", "country_iso3": "TCD", "event_type": "armed_conflict",
               "event_time": "2026-09-18", "source_count": 1, "source_groups": ["g"],
               "title_original": "x"}]
        rep, _ = self._materialize_one(ev)
        self.assertEqual(rep["status"], M.STATUS_LOW_DATA)
        path = M.write_report_artifact(self.t, "africa_daily", rep)
        self.assertTrue(os.path.exists(path))
        loaded = json.load(io.open(path, encoding="utf-8"))
        self.assertEqual(loaded["report_id"], rep["report_id"])
        self.assertEqual(loaded["status"], M.STATUS_LOW_DATA)

    def test_05_report_source_attribution_rate_is_100_percent(self):
        st = M.materialize_reports(str(ROOT), days=14, write=False)
        self.assertEqual(st["REPORT_FACT_SOURCE_ATTRIBUTION_RATE"], 100.0)
        self.assertEqual(st["REPORT_FACTS_TOTAL"], st["REPORT_FACTS_WITH_SOURCE_REFS"])

    def test_06_canonical_source_gap_does_not_fail_report_factory(self):
        st = M.materialize_reports(str(ROOT), days=14, write=False)
        self.assertGreater(st["CANONICAL_SOURCE_IDENTITY_COVERAGE"], 0)
        self.assertLess(st["CANONICAL_SOURCE_IDENTITY_COVERAGE"], 100)
        self.assertEqual(st["DAILY_FAIL"], 0)
        self.assertEqual(st["STATUS_FAIL"], 0)

    def test_07_coverage_note_counts_excluded_unattributed_facts(self):
        ev = [{"event_id": "E1", "country_iso3": "TCD", "event_type": "armed_conflict",
               "event_time": "2026-09-18", "source_count": 1, "title_original": "x"},
              {"event_id": "E2", "country_iso3": "TCD", "event_type": "armed_conflict",
               "event_time": "2026-09-18", "source_count": 1, "title_original": "y"}]
        rep, _ = self._materialize_one(ev)
        self.assertEqual(rep["unattributed_facts_excluded"], 2)
        self.assertTrue(any("2 candidate events" in c for c in rep["coverage_notes"]))

    def test_08_weekly_excludes_unattributed_facts(self):
        wk = {"report_id": "AFRICA_WEEKLY_20260913", "week_start": "2026-09-06",
              "week_end": "2026-09-13"}
        ev = [{"event_id": "E1", "country_iso3": "TCD", "event_type": "armed_conflict",
               "event_time": "2026-09-10", "source_count": 1, "title_original": "x"}]
        rep, fp = M.materialize_africa_weekly(self.t, wk, ev, [], {})
        self.assertEqual(fp.get("social_facts"), [])

    def test_09_country_weekly_excludes_unattributed_facts(self):
        tgt = {"report_id": "WEEKLY_TCD_20260913", "country_iso3": "TCD",
               "week_start": "2026-09-06", "week_end": "2026-09-13",
               "selection_reason": "CONFIGURED_PRIORITY_COUNTRY"}
        ev = [{"event_id": "E1", "country_iso3": "TCD", "event_type": "armed_conflict",
               "event_time": "2026-09-10", "source_count": 1, "title_original": "x"}]
        rep, fp = M.materialize_country_weekly(self.t, tgt, ev, [], {})
        self.assertEqual(fp.get("social_facts"), [])

    def test_10_no_fake_source_identity_created(self):
        src = (ROOT / "scripts" / "report" / "materialize.py").read_text(encoding="utf-8")
        for bad in ("source_unknown", "UNKNOWN_SOURCE_", "src_unknown", "fake_source"):
            self.assertNotIn(bad, src)
        ev = [{"event_id": "E1", "country_iso3": "TCD", "event_type": "armed_conflict",
               "event_time": "2026-09-18", "source_count": 1, "title_original": "x"}]
        rep, _ = self._materialize_one(ev)
        self.assertEqual(rep.get("source_refs"), [])

    # helper
    def _materialize_one(self, ev):
        tgt = {"report_date": "2026-09-18",
               "report_id": F.build_report_id("africa_daily", report_date="2026-09-18")}
        return M.materialize_daily(self.t, tgt, ev, [], {})


class MaterializationContractTest(unittest.TestCase):
    """§九：物化 / 索引 / UI 关键契约"""

    def setUp(self):
        self.t = mktmp_root()

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    def test_11_storage_created_on_first_materialization(self):
        target = os.path.join(self.t, "data", "reports")
        self.assertFalse(os.path.isdir(target))
        ev = [{"event_id": "E1", "country_iso3": "TCD", "event_type": "armed_conflict",
               "event_time": "2026-09-18", "source_count": 1, "source_groups": ["g"],
               "title_original": "x"}]
        rep, _ = M.materialize_daily(self.t, {
            "report_date": "2026-09-18",
            "report_id": F.build_report_id("africa_daily", report_date="2026-09-18")}, ev, [], {})
        M.write_report_artifact(self.t, "africa_daily", rep)
        self.assertTrue(os.path.isdir(os.path.join(target, "daily")))
        src = (ROOT / "scripts" / "report" / "materialize.py").read_text(encoding="utf-8")
        self.assertIn("os.makedirs(os.path.dirname(path), exist_ok=True)", src)

    def test_12_writer_is_atomic(self):
        src = (ROOT / "scripts" / "report" / "materialize.py").read_text(encoding="utf-8")
        self.assertIn('tmp = path + ".tmp"', src)
        self.assertIn("os.fsync(f.fileno())", src)
        self.assertIn("os.replace(tmp, path)", src)

    def test_13_existing_daily_not_duplicated(self):
        st = M.materialize_reports(str(ROOT), days=14, write=False)
        self.assertEqual(st["DAILY_DUPLICATES"], 0)
        self.assertEqual(st["DAILY_EXISTING_REUSED"] + st["DAILY_NEWLY_MATERIALIZED"]
                         + st["DAILY_DIRTY_REBUILT"], 14)

    def test_14_legacy_daily_timestamp_maps_to_report_date(self):
        self.assertEqual(M.legacy_report_date("DAILY_20260918",
                                              "2026-09-18T20:19:54.123456"), "2026-09-18")
        self.assertEqual(M.legacy_report_date("DAILY_20260905"), "2026-09-05")

    def test_15_legacy_daily_201954_not_duplicate(self):
        """period_end 带 20:19:54 也不算另一个报告日。"""
        self.assertEqual(M.legacy_report_date("DAILY_20260918",
                                              "2026-09-18T20:19:54"), "2026-09-18")
        state, _ = M.classify_existing(str(ROOT), "DAILY_20260918", "africa_daily")
        self.assertIn(state, ("EXISTING_VALID", "MISSING"))

    def test_16_historical_daily_excludes_future_events(self):
        from datetime import datetime
        ev = [{"event_id": "E1", "country_iso3": "TCD", "event_type": "armed_conflict",
               "event_time": "2026-09-17", "source_count": 1, "source_groups": ["g"],
               "title_original": "future"}]
        s, e = F.daily_window("2026-09-05")
        pool = M.window_scoped_pool(ev, e.replace(tzinfo=None))
        self.assertEqual(pool, [], "cutoff 之后的事件必须被排除")

    def test_17_daily_windows_produce_distinct_fact_sets(self):
        st = M.materialize_reports(str(ROOT), days=14, write=False)
        wins = {d["period_start"] for d in st["_plan"]["DAILY_TARGET_DATES"]}
        self.assertEqual(len(wins), 14)

    def test_18_14_daily_targets_unique(self):
        st = M.materialize_reports(str(ROOT), days=14, write=False)
        ids = [d["report_id"] for d in st["_plan"]["DAILY_TARGET_DATES"]]
        self.assertEqual(len(ids), 14)
        self.assertEqual(len(set(ids)), 14)

    def test_19_two_africa_weeklies_materialized(self):
        st = M.materialize_reports(str(ROOT), days=14, write=False)
        self.assertEqual(st["AFRICA_WEEKLY_TARGET"], 2)
        self.assertEqual(st["AFRICA_WEEKLY_MATERIALIZED"], 2)

    def test_20_six_configured_country_weeklies_materialized(self):
        st = M.materialize_reports(str(ROOT), days=14, write=False)
        self.assertEqual(st["COUNTRY_WEEKLY_TARGET"], 6)
        self.assertEqual(st["COUNTRY_WEEKLY_MATERIALIZED"], 6)
        isos = {c["country_iso3"] for c in st["_plan"]["COUNTRY_WEEKLY_TARGETS"]}
        self.assertEqual(isos, {"TCD", "NER", "SSD"})

    def test_21_mock_never_enters_real_index(self):
        legacy = [{"report_id": "DAILY_DEV", "is_mock": True, "period_end": "2026-12-31"},
                  {"report_id": "DAILY_20260918", "is_mock": False, "period_end": "2026-09-18"}]
        idx = M.build_real_report_index(self.t, rows=[], legacy=legacy)
        ids = [r["report_id"] for r in idx["reports"]]
        self.assertNotIn("DAILY_DEV", ids)
        self.assertIn("DAILY_20260918", ids)

    def test_22_report_index_deduplicates_legacy_and_new(self):
        rows = [{"report_id": "DAILY_20260918", "report_type": "africa_daily",
                 "status": "LOW_DATA", "path": "data/reports/daily/DAILY_20260918.json"}]
        legacy = [{"report_id": "DAILY_20260918", "is_mock": False, "status": "DATED"}]
        idx = M.build_real_report_index(self.t, rows=rows, legacy=legacy)
        self.assertEqual(idx["count"], 1)
        r = idx["reports"][0]
        self.assertFalse(r.get("legacy_only"), "new canonical artifact 必须覆盖 legacy")

    def test_23_homepage_uses_real_report_index(self):
        js = (ROOT / "assets" / "js" / "report-views.js").read_text(encoding="utf-8")
        self.assertIn("homepageIntel", js)
        self.assertIn("v11Intel", js)
        self.assertIn('report_type === t', js.replace('r.report_type === t', 'report_type === t')
                      if False else js)
        self.assertIn("data/report_index.json", js)

    def test_24_no_real_ai_calls_in_c4b(self):
        st = M.materialize_reports(str(ROOT), days=14, write=False)
        self.assertEqual(st["REAL_AI_CALLS"], 0)
        src = (ROOT / "scripts" / "report" / "materialize.py").read_text(encoding="utf-8")
        for bad in ("submit_task", "DeepSeekV4FlashProvider", "api_key", "ASIP_DEEPSEEK"):
            self.assertNotIn(bad, src)


class RendererContractTest(unittest.TestCase):
    """§十：调用 node harness 验证 renderer 坏值契约（测真实实现）"""

    def _node(self):
        for cand in (os.environ.get("ASIP_NODE"),
                     r"C:\Users\kenan\.workbuddy\binaries\node\versions\22.22.2-2\node.exe",
                     "node"):
            if not cand:
                continue
            try:
                subprocess.run([cand, "-e", "0"], capture_output=True, timeout=20, check=True)
                return cand
            except Exception:  # noqa: BLE001
                continue
        return None

    def test_25_renderer_bad_value_contract(self):
        node = self._node()
        if not node:
            self.skipTest("node unavailable")
        r = subprocess.run([node, str(ROOT / "scripts" / "tests" / "report_ui_contract.js"),
                            str(ROOT / "assets" / "js" / "report-views.js"),
                            str(ROOT / "data")],
                           capture_output=True, text=True, encoding="utf-8", errors="ignore")
        self.assertEqual(r.returncode, 0, (r.stdout or "") + (r.stderr or ""))
        self.assertIn("5 passed, 0 failed", r.stdout)

    def test_26_renderer_never_uses_String_object(self):
        js = (ROOT / "assets" / "js" / "report-views.js").read_text(encoding="utf-8")
        self.assertIn("function displayValue(", js)
        # 不允许把裸对象直接插进模板 / join
        for bad in ("String(f.", "String(rep.", "String(r.", "(f.source_refs || []).join"):
            self.assertNotIn(bad, js)
        self.assertIn("displayValue(f.source_refs)", js)

    def test_27_no_sentinel_masking(self):
        """§三：不得用字符串遮丑。"""
        js = (ROOT / "assets" / "js" / "report-views.js").read_text(encoding="utf-8")
        for bad in ('replace("[object Object]"', 'replace("null"', 'replace("undefined"',
                    'replace(/null/', 'replace(/undefined/'):
            self.assertNotIn(bad, js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
