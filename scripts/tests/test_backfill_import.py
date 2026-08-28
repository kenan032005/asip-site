#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""backfill_import 单元测试：验证确定性 mapping / dedupe / cluster / HOLD 逻辑。
使用合成测试数据（非真实包，不进入任何 preview 数据）。"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ops import backfill_import as bi  # noqa: E402


def _bundle(social=None, disease=None, china=None):
    return {
        "manifest": {"batch_id": bi.BATCH_ID},
        "social": social or [],
        "disease": disease or [],
        "china": china or [],
        "sources": [],
        "package_qa": {},
        "review_notes": "",
    }


def _social(**kw):
    base = {"record_type": "event", "headline_en": "H", "fact_summary_en": "S",
            "country_iso3": "ZMB", "category": "political_social_stability",
            "event_date": "2026-08-20", "verification_status": "multi_source",
            "country_name_zh": "赞比亚", "importance_score_editorial": 70,
            "sources": [{"url": "https://e.com/a", "source_name": "X"}]}
    base.update(kw)
    return base


class TestBackfillImport(unittest.TestCase):

    def test_input_missing(self):
        # 缺 --pkg-file/--pkg-dir 由 main 处理；这里验证空包契约失败路径
        report = bi.run_bundle(_bundle())
        self.assertEqual(report["results"]["social"]["input"], 0)

    def test_social_new_update_duplicate(self):
        rows = [
            _social(record_id="S1", cluster_key="ZMB_2026_ELECTION_POSTELECTION",
                    headline_en="Protest in ZMB",
                    fact_summary_en="Post-election protest in Lusaka."),
            # 同 content → 包内重复（title/country/date/ver 归一化相同）
            _social(record_id="S2", headline_en="Protest in ZMB",
                    fact_summary_en="Post-election protest in Lusaka.",
                    sources=[{"url": "https://e.com/b", "source_name": "Y"}]),
            # cluster event_update → 并入既有 master
            _social(record_id="S3", record_type="event_update",
                    cluster_key="ZMB_2026_ELECTION_POSTELECTION",
                    headline_en="ZMB post-election update",
                    fact_summary_en="Follow-up violence in Kitwe.",
                    event_date="2026-08-21"),
            # disputed → HOLD 不升级
            _social(record_id="S4", verification_status="disputed_claim",
                    country_iso3="TCD", headline_en="Disputed claim",
                    fact_summary_en="Alleged strike.",
                    category="armed_conflict_terrorism"),
            # 缺 source → HOLD
            _social(record_id="S5", country_iso3="MLI", headline_en="No source",
                    fact_summary_en="Missing url.", sources=[]),
        ]
        report = bi.run_bundle(_bundle(social=rows, china=[
            {"record_id": "S1", "china_interest": "indirect"}]))
        s = report["results"]["social"]
        self.assertEqual(s["input"], 5)
        self.assertEqual(s["new"], 1)       # S1 独立事件
        self.assertEqual(s["update"], 1)    # S3 cluster event_update
        self.assertEqual(s["duplicate"], 1)  # S2 content hash 重复
        self.assertEqual(s["held"], 2)       # S4 disputed + S5 缺 source
        self.assertEqual(report["results"]["china_interest"]["indirect"], 1)

    def test_disease_ebola_cluster_single_entity(self):
        rows = [
            {"record_id": "D1", "record_type": "event", "cluster_key": "COD_EBOLA_BUNDIBUGYO_2026",
             "disease": "Ebola", "disease_zh": "埃博拉", "country_iso3": "COD",
             "country_name_zh": "刚果（金）", "event_date": "2026-08-20",
             "verification_status": "official_confirmed",
             "sources": [{"url": "https://e.com/w", "source_name": "WHO"}]},
            {"record_id": "D2", "record_type": "disease_update", "cluster_key": "COD_EBOLA_BUNDIBUGYO_2026",
             "disease": "Ebola", "country_iso3": "COD", "event_date": "2026-08-24",
             "verification_status": "official_confirmed",
             "sources": [{"url": "https://e.com/w2", "source_name": "WHO"}]},
        ]
        report = bi.run_bundle(_bundle(disease=rows))
        d = report["results"]["disease"]
        self.assertEqual(d["input"], 2)
        self.assertEqual(d["new"], 1)    # 1 个 outbreak 实体
        self.assertEqual(d["update"], 1)  # D2 并入 timeline
        self.assertEqual(d["held"], 0)
        self.assertEqual(report["results"]["disease_entities"], 1)

    def test_multi_country_regional_mapping(self):
        row = {"record_id": "D3", "record_type": "event", "cluster_key": "AFR_POLIO_20260819",
               "disease": "Poliovirus type 2", "country_iso3": "MULTI",
               "country_name_en": "Burundi, Ghana, Uganda", "event_date": "2026-08-19",
               "verification_status": "official_confirmed",
               "sources": [{"url": "https://e.com/p", "source_name": "WHO"}]}
        report = bi.run_bundle(_bundle(disease=[row]))
        self.assertEqual(report["results"]["disease"]["held"], 0)
        ent = report["preview"]["disease_entities"][0]
        self.assertEqual(ent["country_iso3"], "AFR")
        self.assertEqual(ent["regional"], True)
        self.assertEqual(len(ent["affected_countries"]), 3)

    def test_missing_required_field_hold(self):
        report = bi.run_bundle(_bundle(social=[_social(record_id="S6", sources=[])]))
        self.assertEqual(report["results"]["social"]["held"], 1)
        self.assertEqual(report["results"]["social"]["new"], 0)


if __name__ == "__main__":
    unittest.main()
