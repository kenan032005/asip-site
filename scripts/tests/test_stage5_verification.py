#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 事件自动核实核心 V1 测试（§十五）。

覆盖：
- Schema：record 通过 event_verification.schema.json；status 枚举合法/非法；
- trust tier：A/B/C/D 分层判定（官方域名/国际媒体/本地/聚合）；
- 独立来源判断：不同域独立、同域转载、同 hash、聚合不计；
- 确定性规则：verified / probable / single_source / conflicting / rejected /
  NewsNow lead-only / 官方确认 / 转载去重；
- 边界：Canonical 不被修改、Public 不被修改、development mode 不变、
  direct website API 关闭。
"""

import hashlib
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from scripts.verification.engine import verify_event, is_article_url
from scripts.verification.source_tiers import classify_tier
from scripts.verification.independence import count_independent, is_duplicate
from scripts.verification.constants import (
    STATUS_ENUM, STATUS_VERIFIED, STATUS_PROBABLE, STATUS_SINGLE_SOURCE,
    STATUS_CONFLICTING, STATUS_UNVERIFIED, STATUS_REJECTED,
)
from scripts.verification.fixtures import FIXTURES
from scripts.ai.schema_validation import validate_against_schema

SCHEMA_PATH = os.path.join(ROOT, "schemas", "event_verification.schema.json")


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def schema_valid(record):
    return validate_against_schema(record, load_schema())


def file_sha256(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestVerificationSchema(unittest.TestCase):
    def test_record_passes_schema(self):
        rec = verify_event(FIXTURES[0]["event"], FIXTURES[0]["articles"])
        self.assertEqual(schema_valid(rec), [], "record 必须通过 schema")

    def test_status_enum_legal(self):
        self.assertEqual(STATUS_ENUM,
                         {"verified", "probable", "single_source", "conflicting",
                          "unverified", "rejected"})

    def test_status_enum_invalid_rejected(self):
        rec = dict(verify_event(FIXTURES[0]["event"], FIXTURES[0]["articles"]))
        rec["verification_status"] = "not_a_status"
        self.assertNotEqual(schema_valid(rec), [])

    def test_confidence_range(self):
        for fx in FIXTURES:
            rec = verify_event(fx["event"], fx["articles"],
                               quarantine_ids=fx.get("quarantine_ids"))
            self.assertTrue(0 <= rec["verification_confidence"] <= 100, fx["name"])

    def test_support_type_enum(self):
        for fx in FIXTURES:
            rec = verify_event(fx["event"], fx["articles"],
                               quarantine_ids=fx.get("quarantine_ids"))
            for s in rec["supporting_sources"]:
                self.assertIn(s["support_type"],
                              ("primary", "supporting", "official_confirmation",
                               "secondary_report", "lead_only"))


class TestTrustTier(unittest.TestCase):
    def test_tier_a_official(self):
        t, r = classify_tier("世界卫生组织", "https://www.who.int/2026/x",
                             "official")
        self.assertEqual(t, "A")
        t, r = classify_tier("", "https://reuters.com/2026/x", "other")
        self.assertEqual(t, "A")

    def test_tier_b_international(self):
        t, r = classify_tier("BBC", "https://www.bbc.com/news/x", "international_media")
        self.assertEqual(t, "B")

    def test_tier_c_local(self):
        t, r = classify_tier("Tchadinfos", "https://tchadinfos.com/x", "local_media")
        self.assertEqual(t, "C")

    def test_tier_d_aggregator(self):
        t, r = classify_tier("NewsNow", "https://newsnow.co.uk/x", "aggregation_platform")
        self.assertEqual(t, "D")
        t, r = classify_tier("Mirage News", "https://miragenews.com/x", "other")
        self.assertEqual(t, "D")

    def test_reliefweb_official_domain_wins_over_type(self):
        # ReliefWeb 域名（OCHA 官方）优先于 aggregation_platform 标记
        t, r = classify_tier("ReliefWeb（乍得）", "https://reliefweb.int/report/x",
                             "aggregation_platform")
        self.assertEqual(t, "A")


class TestIndependence(unittest.TestCase):
    def test_different_domains_independent(self):
        a = {"article_url": "https://alpha-news.com/x", "content_hash": ""}
        b = {"article_url": "https://beta-news.com/x", "content_hash": ""}
        self.assertFalse(is_duplicate(a, b))

    def test_same_domain_republish(self):
        a = {"article_url": "https://www.alpha-news.com/x", "content_hash": ""}
        b = {"article_url": "https://alpha-news.com/y", "content_hash": ""}
        self.assertTrue(is_duplicate(a, b))

    def test_same_hash_original_copy(self):
        a = {"article_url": "https://a.com/x", "content_hash": "abc123"}
        b = {"article_url": "https://b.com/y", "content_hash": "abc123"}
        self.assertTrue(is_duplicate(a, b))

    def test_aggregator_not_independent(self):
        arts = [
            {"article_url": "https://newsnow.co.uk/x", "source_name": "NewsNow",
             "_tier": "D"},
            {"article_url": "https://alpha-news.com/y", "source_name": "Alpha",
             "_tier": "C"},
        ]
        n, groups = count_independent(arts)
        self.assertEqual(n, 1)


class TestDeterministicRules(unittest.TestCase):
    def _run(self, name):
        fx = next(f for f in FIXTURES if f["name"] == name)
        return verify_event(fx["event"], fx["articles"],
                            quarantine_ids=fx.get("quarantine_ids"))

    def test_fixtures_match_expectations(self):
        for fx in FIXTURES:
            rec = verify_event(fx["event"], fx["articles"],
                               quarantine_ids=fx.get("quarantine_ids"))
            self.assertEqual(rec["verification_status"], fx["expect"],
                             "%s: got %s" % (fx["name"], rec["verification_status"]))

    def test_verified_two_independent(self):
        rec = self._run("two_independent_media_consistent")
        self.assertEqual(rec["verification_status"], STATUS_VERIFIED)
        self.assertGreaterEqual(rec["independent_source_count"], 2)

    def test_official_confirmation_verified(self):
        rec = self._run("official_confirmation")
        self.assertEqual(rec["verification_status"], STATUS_VERIFIED)
        self.assertTrue(rec["source_trust_summary"]["has_official"])

    def test_single_source(self):
        rec = self._run("single_local_source")
        self.assertEqual(rec["verification_status"], STATUS_SINGLE_SOURCE)
        self.assertEqual(rec["independent_source_count"], 1)

    def test_conflicting_deaths(self):
        rec = self._run("deaths_conflict")
        self.assertEqual(rec["verification_status"], STATUS_CONFLICTING)
        self.assertTrue(rec["conflicting_sources"])

    def test_rejected_category_page(self):
        rec = self._run("category_page_rejected")
        self.assertEqual(rec["verification_status"], STATUS_REJECTED)

    def test_rejected_quarantined(self):
        rec = self._run("quarantined_event")
        self.assertEqual(rec["verification_status"], STATUS_REJECTED)

    def test_newsnow_lead_only(self):
        rec = self._run("newsnow_lead_to_original")
        # 聚合不计独立来源；lead_only 不进入 supporting
        self.assertEqual(rec["verification_status"], STATUS_SINGLE_SOURCE)
        for s in rec["supporting_sources"]:
            self.assertNotEqual(s["support_type"], "lead_only")
            self.assertNotEqual(s["source_tier"], "D")

    def test_republish_dedup(self):
        rec = self._run("republish_same_original")
        self.assertEqual(rec["verification_status"], STATUS_SINGLE_SOURCE)
        self.assertEqual(rec["independent_source_count"], 1)
        self.assertEqual(rec["source_count"], 2)  # 原始 2 篇，独立 1

    def test_no_sources_unverified(self):
        rec = verify_event({"event_id": "EVT_00000000000000ff",
                            "country_code": "TD"},
                           [])
        self.assertEqual(rec["verification_status"], STATUS_UNVERIFIED)


class TestBoundaries(unittest.TestCase):
    def test_canonical_not_modified(self):
        before = file_sha256("data/canonical/event_clusters.json")
        for fx in FIXTURES:
            verify_event(fx["event"], fx["articles"],
                         quarantine_ids=fx.get("quarantine_ids"))
        after = file_sha256("data/canonical/event_clusters.json")
        self.assertEqual(before, after, "Canonical 不得被核实修改")

    def test_public_not_modified(self):
        before = file_sha256("data/public/published_events.json")
        for fx in FIXTURES:
            verify_event(fx["event"], fx["articles"],
                         quarantine_ids=fx.get("quarantine_ids"))
        after = file_sha256("data/public/published_events.json")
        self.assertEqual(before, after, "Public 不得被核实修改")

    def test_development_mode_unchanged(self):
        cfg = json.load(open(os.path.join(ROOT, "config", "runtime.json"),
                             encoding="utf-8"))
        self.assertEqual(cfg.get("asip_mode"), "development")
        dm = cfg.get("development_mode") or {}
        self.assertFalse(dm.get("production_auto_update"))
        self.assertTrue(dm.get("manual_ai_trial"))

    def test_direct_website_api_closed(self):
        cfg = json.load(open(os.path.join(ROOT, "config", "runtime.json"),
                             encoding="utf-8"))
        self.assertEqual(cfg.get("ai_provider"), "workbuddy_queue")
        dm = cfg.get("development_mode") or {}
        self.assertFalse(dm.get("direct_website_api_call"))
        self.assertNotIn("openai_api", (cfg.get("ai_provider") or ""))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    print("RESULT: PASS=%d FAIL=%d" % (n_run - n_fail, n_fail))
    sys.exit(1 if n_fail else 0)
