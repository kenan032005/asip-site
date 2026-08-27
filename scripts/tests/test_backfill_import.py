#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""backfill_import 单元测试：验证确定性 mapping / dedupe / cluster / HOLD 逻辑。
使用合成测试数据（非真实包，不进入任何 preview 数据）。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ops import backfill_import as bi  # noqa: E402


def _pkg_dir(rows):
    td = tempfile.mkdtemp(prefix="wb_bkf_")
    d = Path(td)
    (d / "manifest.json").write_text(json.dumps({
        "batch_id": bi.BATCH_ID, "social_records": len(rows[0]),
        "disease_records": len(rows[1]), "total_structured_records": len(rows[0]) + len(rows[1]),
        "china_interest_records": len(rows[2])}), encoding="utf-8")
    for name, arr in zip(["social_events.jsonl", "disease_events.jsonl", "china_interest.jsonl"], rows):
        (d / name).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in arr) + "\n", encoding="utf-8")
    (d / "sources.jsonl").write_text("", encoding="utf-8")
    return d


class TestBackfillImport(unittest.TestCase):

    def test_input_missing(self):
        report, code = bi.run_import(Path("C:/nonexistent/pkg"))
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "INPUT_MISSING")

    def test_social_new_update_duplicate(self):
        rows = [
            # 2 条相同 content → 1 new + 1 duplicate
            [{"record_type": "event", "cluster_key": None, "headline": "Protest in ZMB",
              "fact_summary": "Post-election protest in Lusaka.", "country": "ZMB",
              "category": "political_social_stability", "date": "2026-08-25",
              "verification_status": "multi_source", "source_url": "https://example.com/a",
              "source_name": "X", "published_date": "2026-08-25"},
             {"record_type": "event", "headline": "Protest in ZMB",
              "fact_summary": "Post-election protest in Lusaka.", "country": "ZMB",
              "category": "political_social_stability", "date": "2026-08-25",
              "verification_status": "multi_source", "source_url": "https://example.com/a"},
             # event_update → cluster 内更新
             {"record_type": "event_update", "cluster_key": "ZMB_2026_ELECTION_POSTELECTION",
              "headline": "ZMB post-election update", "fact_summary": "Follow-up violence in Kitwe.",
              "country": "ZMB", "category": "political_social_stability", "date": "2026-08-26",
              "verification_status": "single_source", "source_url": "https://example.com/b"},
             # disputed → HOLD 不升级
             {"record_type": "event", "headline": "Disputed claim", "fact_summary": "Alleged strike.",
              "country": "TCD", "category": "armed_conflict_terrorism", "date": "2026-08-20",
              "verification_status": "disputed_claim", "source_url": "https://example.com/c"},
             # 缺 source → HOLD
             {"record_type": "event", "headline": "No source", "fact_summary": "Missing url.",
              "country": "MLI", "category": "armed_conflict_terrorism", "date": "2026-08-21",
              "verification_status": "multi_source"}],
            [],
            [{"direct": True, "event_key": "ZMB"}],
        ]
        report, code = bi.run_import(_pkg_dir(rows))
        self.assertEqual(code, 0)
        s = report["results"]["social"]
        self.assertEqual(s["input"], 5)
        self.assertEqual(s["new"], 1)       # 行A 独立事件
        self.assertEqual(s["update"], 1)    # 行C cluster event_update
        self.assertEqual(s["duplicate"], 1)  # 行B content hash 重复
        self.assertEqual(s["held"], 2)       # 行D disputed + 行E 缺 source
        self.assertEqual(report["results"]["china_interest"]["direct"], 1)

    def test_disease_ebola_cluster_single_entity(self):
        rows = [[],
                [
                 {"record_type": "event", "cluster_key": "COD_EBOLA_BUNDIBUGYO_2026",
                  "disease_name": "Ebola", "country": "COD", "report_date": "2026-08-20",
                  "cumulative_confirmed": 10, "outbreak_status": "active",
                  "verification_status": "official_confirmed"},
                 {"record_type": "event_update", "cluster_key": "COD_EBOLA_BUNDIBUGYO_2026",
                  "disease_name": "Ebola", "country": "COD", "report_date": "2026-08-24",
                  "cumulative_confirmed": 14, "outbreak_status": "active",
                  "verification_status": "official_confirmed"},
                ],
                []]
        report, code = bi.run_import(_pkg_dir(rows))
        self.assertEqual(code, 0)
        d = report["results"]["disease"]
        self.assertEqual(d["input"], 2)
        self.assertEqual(d["new"], 1)   # 1 个 outbreak 实体
        self.assertEqual(d["update"], 1)  # 第 2 条 update 并入 timeline
        self.assertEqual(d["held"], 0)

    def test_missing_required_field_hold(self):
        rows = [[{"record_type": "event", "headline": "x", "fact_summary": "y",
                  "country": "NGA", "category": "public_safety_major_incidents",
                  "date": "2026-08-22",
                  "verification_status": "multi_source",
                  "source_url": "https://e.com/x"}], [], []]
        report, code = bi.run_import(_pkg_dir(rows))
        self.assertEqual(code, 0)
        self.assertEqual(report["results"]["social"]["held"], 0)  # 字段齐全 → new
        self.assertEqual(report["results"]["social"]["new"], 1)
        rows2 = [[{"record_type": "event", "headline": "x", "fact_summary": "y",
                   "country": "NGA", "category": "public_safety_major_incidents",
                   "date": "2026-08-22",
                   "verification_status": "multi_source"}], [], []]
        report2, _ = bi.run_import(_pkg_dir(rows2))
        self.assertEqual(report2["results"]["social"]["held"], 1)  # 缺 source_url → HOLD


if __name__ == "__main__":
    unittest.main()
