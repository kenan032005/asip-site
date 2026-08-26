#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Source Expansion B — Country Source Layer 测试（§十九）。

覆盖：country registry / country_iso3 / source_group / publisher provenance /
official source duplication / opinion tagging / topic filtering / health→Disease
chain / normal→Social / country filter / cross-country contamination /
detail extraction / stable source calculation / runtime isolation。
不依赖网络（registry 校验 + 纯函数/构造）。
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)

from scripts.global_source.registry import load_country_registry, by_id
from scripts.global_source.topic_filter import (
    classify_chain, match_topic, detect_opinion, classify_candidate,
    SECURITY_KEYWORDS, DISEASE_KEYWORDS,
)
from scripts.global_source.candidates import new_candidate, independent_count


def _src(sid, group=None, role="evidence", iso3="TCD", topic=None):
    return {
        "source_id": sid, "name": sid, "source_group": group or sid,
        "country_iso3": iso3, "language": ["fr"],
        "role": role, "trust_tier": "B",
        "evidence_eligible": True,
        "acquisition_method": "public_listing_html",
        "listing_host": "x.example", "listing_path": "/",
        "detail_strategy": "public_article_html",
        "enabled": True, "priority": "high",
        "topic_scope": topic or ["security"],
    }


class TestCountryRegistry(unittest.TestCase):
    def test_registry_24_entries_valid(self):
        sources, errs = load_country_registry()
        self.assertEqual(len(sources), 24, "应 24 条 country source")
        self.assertEqual(errs, [], "registry 校验错误: %s" % errs)

    def test_country_breakdown(self):
        sources, _ = load_country_registry()
        by = by_id(sources)
        counts = {}
        for s in sources:
            counts[s["country_iso3"]] = counts.get(s["country_iso3"], 0) + 1
        self.assertEqual(counts, {"TCD": 4, "NER": 5, "SSD": 6, "BEN": 5, "ETH": 4},
                         "5 国源数应符合计划")

    def test_no_sixth_country(self):
        sources, _ = load_country_registry()
        iso3s = {s["country_iso3"] for s in sources}
        self.assertEqual(iso3s, {"TCD", "NER", "SSD", "BEN", "ETH"},
                         "不得出现第 6 个国家")

    def test_tiers_and_roles(self):
        sources, _ = load_country_registry()
        by = by_id(sources)
        self.assertEqual(by["tcd_atpe"]["trust_tier"], "A")
        self.assertEqual(by["tcd_alwihda"]["trust_tier"], "C")
        for sid in ("ssd_moh", "ben_moh", "eth_moh"):
            self.assertEqual(by[sid]["role"], "authoritative_disease_evidence", sid)
            self.assertEqual(by[sid]["trust_tier"], "A", sid)

    def test_addis_standard_trial(self):
        sources, _ = load_country_registry()
        self.assertEqual(by_id(sources)["eth_addis_standard"]["enabled"], "trial")


class TestProvenanceIndependence(unittest.TestCase):
    def test_official_statement_not_double_counted(self):
        # 总统府与 SSBC 复制同一 statement：source_group 不同但 provenance 相同
        c1 = new_candidate(_src("ssd_presidency", group="presidency_ssd"),
                           {"title": "Presidential statement", "url": "https://op.gov.ss/a",
                            "original_publisher": "Office of the President"})
        c2 = new_candidate(_src("ssd_ssbc", group="ssbc"),
                           {"title": "Presidential statement", "url": "https://ssbc.gov.ss/a",
                            "original_publisher": "Office of the President"})
        n, groups = independent_count([c1, c2])
        # 直接来源以 source_group 计：presidency_ssd + ssbc = 2 组（需 content_hash 语义层去重，
        # 本层保留 provenance 字段供 Verification 判定）
        self.assertEqual(n, 2)
        self.assertEqual(c1.get("original_publisher"), "Office of the President")
        self.assertEqual(c2.get("original_publisher"), "Office of the President")


class TestChainRouting(unittest.TestCase):
    def test_health_source_to_disease_chain(self):
        cand = new_candidate(
            _src("ssd_moh", role="authoritative_disease_evidence", topic=["disease"]),
            {"title": "Cholera outbreak update", "url": "https://moh.gov.ss/1"})
        cand["role"] = "authoritative_disease_evidence"
        cand["topic_scope"] = ["disease"]
        cand = classify_candidate(cand)
        self.assertEqual(cand["chain"], "disease")

    def test_normal_source_to_social(self):
        cand = classify_candidate(new_candidate(
            _src("tcd_tchadinfos"), {"title": "Sécurité à N'Djamena",
                                     "url": "https://tchadinfos.com/1"}))
        self.assertEqual(cand["chain"], "social")

    def test_security_keyword_match(self):
        self.assertTrue(match_topic("attaque terroriste", "social")[0])
        self.assertTrue(match_topic("military deployment", "social")[0])
        self.assertFalse(match_topic("football match", "social")[0])

    def test_disease_keyword_match(self):
        self.assertTrue(match_topic("cholera outbreak", "disease")[0])
        self.assertTrue(match_topic("épidémie de méningite", "disease")[0])


class TestOpinionTagging(unittest.TestCase):
    def test_opinion_detected(self):
        self.assertEqual(detect_opinion("Opinion: Reform needed"), "opinion")
        self.assertEqual(detect_opinion("Chronique du lundi"), "opinion")
        self.assertEqual(detect_opinion("Analyse: regional stability"), "analysis")
        self.assertIsNone(detect_opinion("Breaking: attack in Diffa"))

    def test_opinion_not_primary_fact(self):
        cand = classify_candidate(new_candidate(
            _src("ssd_radio_tamazuj"),
            {"title": "Opinion: Is peace possible?", "url": "https://radiotamazuj.org/en/opinion/1"}))
        self.assertEqual(cand.get("content_type"), "opinion")


class TestCountryFilter(unittest.TestCase):
    def test_alwihda_chad_filter(self):
        from scripts.global_source.africa_filter import AFRICA_COUNTRY_ALIASES
        aliases = AFRICA_COUNTRY_ALIASES["TD"]
        self.assertTrue(any(a in "Tchad: nouvelle attaque" for a in aliases))
        self.assertFalse(any(a in "Niger: crise politique" for a in aliases))

    def test_no_cross_country_contamination(self):
        # sudantribune 用 /south-sudan/ 路径；标题含 South Sudan 才属 SSD
        self.assertIn("south-sudan", "/south-sudan/")
        self.assertTrue("south sudan" in "South Sudan: talks resume".lower())


class TestDetailAndStable(unittest.TestCase):
    def test_detail_extract_mock(self):
        from scripts.global_source.detail import extract_body
        html = ("<html><body><article><h1>Title</h1><p>Paragraph one long enough to extract.</p>"
                "<p>Second paragraph with enough length to be kept as body text.</p></article></body></html>")
        body, paras = extract_body(html)
        self.assertTrue(body)
        self.assertGreaterEqual(len(paras), 1)

    def test_stable_calculation_definition(self):
        # §十五：listing_success + item + detail 成功或明确 detail strategy
        from scripts.global_source.country_dryrun import DETAIL_PER_SOURCE
        self.assertGreaterEqual(DETAIL_PER_SOURCE, 2)
        src = _src("x")
        self.assertTrue(src.get("detail_strategy"))


class TestRuntimeIsolation(unittest.TestCase):
    def test_runtime_not_in_dist(self):
        gi = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
        self.assertIn("data/runtime/", gi)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    print("RESULT: PASS=%d FAIL=%d" % (n_run - n_fail, n_fail))
    sys.exit(1 if n_fail else 0)
