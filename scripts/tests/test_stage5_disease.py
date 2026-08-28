#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 第二执行包 — 传染病风险模块 V1 测试（§二十一）。

覆盖：
- Schema 合法性（disease_event.schema.json）
- 疾病别名归一化（mpox/monkeypox 同一 disease_id）
- 病例类型（source_total 保留；confirmed 不自动相加）
- unknown != 0（未知数字必须 null）
- 日期区分（report_date ≠ case_period）
- 跨境事件（cross_border + affected_countries，不复制事件）
- 官方来源优先（verify_numbers → official）
- 媒体数字不同但报告日期不同 → temporal_update
- 真正核心数字冲突（同日不同）→ data_difference
- Public ⊆ Disease Canonical
- runtime 隔离（内部目录不进 dist 白名单）
- 页面 fallback（disease-risk.html 状态中文映射）
- development mode 不变 / schedule 暂停 / direct website API=false
"""

import hashlib
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from scripts.disease.diseases import resolve_disease_id, load_diseases, disease_name
from scripts.disease.normalizer import (
    build_disease_event, normalize_case_counts, normalize_dates, normalize_geo,
)
from scripts.disease.gate import run_gate
from scripts.disease.canonical import load_canonical, make_event_id, find_previous_for
from scripts.disease.verifier import verify_numbers, classify_event_verification
from scripts.ai.schema_validation import validate_against_schema

SCHEMA_PATH = os.path.join(ROOT, "schemas", "disease_event.schema.json")


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def schema_valid(record):
    return validate_against_schema(record, load_schema())


def _raw(**kw):
    base = {
        "disease_raw": "Cholera", "disease_name_en": "Cholera",
        "disease_name_zh": "霍乱", "country_iso3": "NGA",
        "report_date": "2026-07-31", "primary_source": "WHO",
        "source_tier": "A",
        "source_links": [{"url": "https://example.com/x", "source_id": "t",
                          "source_name": "T", "source_tier": "A"}],
        "outbreak_status": "active", "update_type": "new_outbreak",
    }
    base.update(kw)
    return base


class TestDiseaseSchema(unittest.TestCase):
    def test_record_passes_schema(self):
        fields = build_disease_event(make_event_id("s1"), _raw(total_cases=100, deaths=5))
        # schema 要求的必填字段补全
        fields["disease_name_en"] = "Cholera"
        fields["disease_name_zh"] = "霍乱"
        fields["created_at"] = "2026-08-26T00:00:00+08:00"
        fields["updated_at"] = "2026-08-26T00:00:00+08:00"
        self.assertEqual(schema_valid(fields), [], "disease event 必须通过 schema")

    def test_invalid_status_rejected(self):
        fields = build_disease_event(make_event_id("s2"), _raw(total_cases=1))
        fields["outbreak_status"] = "very_bad"
        errs = schema_valid(fields)
        self.assertTrue(any("outbreak_status" in e for e in errs), errs)


class TestDiseaseDictionary(unittest.TestCase):
    def test_mpox_alias_same_id(self):
        self.assertEqual(resolve_disease_id("mpox"), "mpox")
        self.assertEqual(resolve_disease_id("monkeypox"), "mpox")
        self.assertEqual(resolve_disease_id("猴痘"), "mpox")

    def test_cholera_alias(self):
        self.assertEqual(resolve_disease_id("Cholera"), "cholera")
        self.assertEqual(resolve_disease_id("霍乱"), "cholera")

    def test_unknown_disease_none(self):
        self.assertIsNone(resolve_disease_id("unknown disease xyz"))

    def test_dict_has_required_diseases(self):
        d = load_diseases()
        for did in ("cholera", "mpox", "measles", "yellow_fever", "meningitis",
                    "ebola", "marburg", "lassa_fever", "rift_valley_fever",
                    "polio", "other"):
            self.assertIn(did, d, did)
        self.assertEqual(disease_name("cholera", "zh"), "霍乱")


class TestNumericHandling(unittest.TestCase):
    def test_unknown_is_null_not_zero(self):
        fields, flags = normalize_case_counts({})
        for f in ("confirmed_cases", "probable_cases", "suspected_cases",
                  "total_cases", "deaths", "recoveries"):
            self.assertIsNone(fields.get(f), f)
        self.assertNotIn("0", [str(fields.get(f)) for f in fields])

    def test_confirmed_not_auto_summed(self):
        fields, flags = normalize_case_counts({"confirmed_cases": 20,
                                               "suspected_cases": 15})
        self.assertEqual(fields["confirmed_cases"], 20)
        self.assertEqual(fields["suspected_cases"], 15)
        # 不自动相加为 total
        self.assertIsNone(fields.get("total_cases"))

    def test_source_total_preserved(self):
        fields, flags = normalize_case_counts({"total_cases": 35,
                                               "case_count_type": "source_total"})
        self.assertEqual(fields["total_cases"], 35)
        self.assertEqual(fields["case_count_type"], "source_total")

    def test_negative_number_null(self):
        fields, flags = normalize_case_counts({"deaths": -5})
        self.assertIsNone(fields.get("deaths"))


class TestDateHandling(unittest.TestCase):
    def test_report_date_vs_case_period(self):
        out, flags = normalize_dates({
            "report_date": "2026-08-20",
            "case_period_start": "2026-08-01",
            "case_period_end": "2026-08-18",
        })
        self.assertEqual(out["report_date"], "2026-08-20")
        self.assertEqual(out["case_period_end"], "2026-08-18")
        # report_date 不得被当作事件日期：event_start_date 应独立
        self.assertIsNone(out.get("event_start_date"))

    def test_invalid_date_flagged(self):
        out, flags = normalize_dates({"report_date": "not-a-date"})
        self.assertIsNone(out["report_date"])
        self.assertTrue(any("invalid_date" in f for f in flags))


class TestGeoHandling(unittest.TestCase):
    def test_cross_border_not_duplicated(self):
        out, flags = normalize_geo({
            "country_iso3": "regional", "cross_border": True,
            "affected_countries": ["COD", "COG", "NGA"],
        })
        self.assertTrue(out["cross_border"])
        self.assertEqual(out["affected_countries"], ["COD", "COG", "NGA"])

    def test_regional_iso3(self):
        out, flags = normalize_geo({"country_iso3": "AFRICA"})
        self.assertEqual(out["country_iso3"], "regional")


class TestVerification(unittest.TestCase):
    def test_official_source_priority(self):
        st, reasons, diffs = verify_numbers(
            primary_value=120,
            others=[("media", 118)],
            primary_report_date="2026-08-20",
            other_report_dates={"media": "2026-08-19"})
        self.assertEqual(st, "temporal_update")

    def test_same_date_diff_number_data_difference(self):
        st, reasons, diffs = verify_numbers(
            primary_value=120,
            others=[("media", 118)],
            primary_report_date="2026-08-20",
            other_report_dates={"media": "2026-08-20"})
        self.assertEqual(st, "data_difference")

    def test_official_matching_number(self):
        st, reasons, diffs = verify_numbers(
            primary_value=120,
            others=[("media", 120)],
            primary_report_date="2026-08-20",
            other_report_dates={"media": "2026-08-20"})
        self.assertEqual(st, "official")

    def test_classify_event_official(self):
        st, reasons = classify_event_verification({}, [
            {"source_id": "who", "source_tier": "A", "official": True}])
        self.assertEqual(st, "official")


class TestCanonicalLinking(unittest.TestCase):
    def test_previous_time_direction(self):
        items = [
            {"disease_event_id": "DSEV_a", "disease_id": "cholera",
             "country_iso3": "NGA", "admin1": "Borno", "report_date": "2026-06-01"},
            {"disease_event_id": "DSEV_b", "disease_id": "cholera",
             "country_iso3": "NGA", "admin1": "Borno", "report_date": "2026-07-01"},
        ]
        prev = find_previous_for("cholera", "NGA", "2026-07-15", items, admin1="Borno")
        self.assertIsNotNone(prev)
        self.assertEqual(prev["disease_event_id"], "DSEV_b")

    def test_admin1_granularity_not_linked(self):
        items = [
            {"disease_event_id": "DSEV_nat", "disease_id": "cholera",
             "country_iso3": "NGA", "admin1": "", "report_date": "2026-07-01"},
        ]
        prev = find_previous_for("cholera", "NGA", "2026-08-01", items, admin1="Bauchi")
        self.assertIsNone(prev, "national 与州级不同源，不得关联")


class TestDataIntegrity(unittest.TestCase):
    def test_public_subset_canonical(self):
        canon = load_canonical()
        pub_path = os.path.join(ROOT, "data", "public", "disease_events.json")
        pub = json.load(open(pub_path, encoding="utf-8"))
        cids = {it["disease_event_id"] for it in canon["items"]}
        for p in pub["items"]:
            self.assertIn(p["disease_event_id"], cids,
                          "Public disease ⊆ Disease Canonical 被破坏")

    def test_disease_canonical_separate_from_security(self):
        # 疾病 canonical 独立保存，不得写入社安 event_clusters
        sec = json.load(open(os.path.join(ROOT, "data", "canonical",
                                          "event_clusters.json"), encoding="utf-8"))
        for ev in sec["items"]:
            self.assertNotIn("disease_event_id", ev)
            self.assertNotIn("outbreak_status", ev)

    def test_build_site_allowlist_no_internal_dirs(self):
        bs = open(os.path.join(ROOT, "scripts", "build_site.py"), encoding="utf-8").read()
        m = re.search(r"PUBLIC_DATA_ALLOWLIST\s*=\s*\[([\s\S]*?)\]", bs)
        self.assertIsNotNone(m)
        self.assertIn("public/disease_events.json", m.group(1))
        for bad in ("disease/canonical", "data/disease_sources"):
            self.assertNotIn(bad, m.group(1))

    def test_page_status_mapping(self):
        # Stage 8A：疾病页由「占位 + 硬编码状态词」升级为 view 驱动 Dashboard。
        # 页面展示状态图例；中文状态词由 disease_outbreaks view 的 status_cn 提供。
        html = open(os.path.join(ROOT, "disease-risk.html"), encoding="utf-8").read()
        for cn in ("活跃", "下降", "已控制", "已结束"):
            self.assertIn(cn, html)
        # view 契约：每个 outbreak 必须有 status_cn 中文状态
        view = json.load(open(os.path.join(
            ROOT, "data", "runtime", "frontend_preview_public",
            "disease_outbreaks.json"), encoding="utf-8"))
        self.assertGreaterEqual(len(view["outbreaks"]), 1)
        for o in view["outbreaks"]:
            self.assertTrue(o.get("status_cn"))
        # 公开数据路径：disease_outbreaks 进入 __DB__（前端消费公开视图）
        dist_html = open(os.path.join(ROOT, "dist", "index.html"),
                         encoding="utf-8").read()
        self.assertIn("disease_outbreaks", dist_html)

    def test_development_mode_and_api_closed(self):
        cfg = json.load(open(os.path.join(ROOT, "config", "runtime.json"),
                             encoding="utf-8"))
        self.assertEqual(cfg.get("asip_mode"), "development")
        self.assertFalse(cfg.get("cloud_schedule_enabled"))
        dm = cfg.get("development_mode") or {}
        self.assertFalse(dm.get("direct_website_api_call"))
        self.assertFalse(dm.get("production_auto_update"))

    def test_unknown_disease_flagged_not_guessed(self):
        fields = build_disease_event(make_event_id("s3"),
                                     _raw(disease_raw="Mystery Syndrome",
                                          report_date="bad"))
        ok, errors = run_gate(fields)
        self.assertFalse(ok)
        self.assertTrue(any("invalid_disease_id" in e for e in errors))
        self.assertTrue(any("invalid_report_date" in e for e in errors))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    print("RESULT: PASS=%d FAIL=%d" % (n_run - n_fail, n_fail))
    sys.exit(1 if n_fail else 0)
