#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Source Expansion A — Global Source Layer 测试（§十九）。

覆盖：Registry schema / source_group / France24 双语不算双独立来源 /
AllAfrica provenance / AllAfrica 不作为默认 evidence / ReliefWeb publisher
inheritance / WHO·Africa CDC Tier A / global Africa filter / duplicate URL /
origin publisher dedup / source health / runtime 不进 dist。
不依赖网络（纯本地 + 小样本构造）。
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)

from scripts.global_source.registry import load_registry, by_id
from scripts.global_source.candidates import (
    new_candidate, dedup_candidates, origin_group, independent_count,
)
from scripts.global_source.africa_filter import (
    is_africa_text, country_hints, filter_candidates,
)
from scripts.global_source.health import load_health, record_health


def _src(sid, group=None, role="evidence", tier="B", scope="africa",
         evidence_eligible=True):
    return {
        "source_id": sid, "name": sid, "source_group": group or sid,
        "scope": scope, "country_scope": ["africa"], "language": ["en"],
        "role": role, "trust_tier": tier,
        "evidence_eligible": evidence_eligible,
        "acquisition_method": "rss", "listing_host": "x.example",
        "listing_path": "/rss.xml", "detail_strategy": "public_article_html",
        "enabled": True, "priority": 1,
    }


class TestRegistry(unittest.TestCase):
    def test_registry_12_entries_valid(self):
        sources, errs = load_registry()
        self.assertEqual(len(sources), 12, "应有 12 个 registry entry")
        self.assertEqual(errs, [], "registry 校验错误: %s" % errs)
        ids = [s["source_id"] for s in sources]
        self.assertEqual(len(set(ids)), len(ids), "source_id 不得重复")

    def test_required_sources_present(self):
        sources, _ = load_registry()
        by = by_id(sources)
        for sid in ("global_reuters_africa", "global_ap_africa",
                    "global_bbc_africa", "global_rfi_afrique",
                    "global_france24_afrique_fr", "global_france24_africa_en",
                    "global_aljazeera", "global_allafrica", "global_reliefweb",
                    "disease_who_don", "disease_who_afro",
                    "disease_africa_cdc"):
            self.assertIn(sid, by, "缺少 source: %s" % sid)

    def test_who_cdc_tier_a(self):
        sources, _ = load_registry()
        by = by_id(sources)
        for sid in ("disease_who_don", "disease_who_afro", "disease_africa_cdc"):
            self.assertEqual(by[sid]["trust_tier"], "A", sid)
            self.assertEqual(by[sid]["role"], "authoritative_disease_evidence", sid)

    def test_aggregator_not_evidence_eligible(self):
        sources, _ = load_registry()
        by = by_id(sources)
        self.assertFalse(by["global_allafrica"]["evidence_eligible"])
        self.assertEqual(by["global_allafrica"]["role"], "discovery")
        self.assertEqual(by["global_allafrica"]["trust_tier"], "D")
        self.assertFalse(by["global_reliefweb"]["evidence_eligible"])
        self.assertEqual(by["global_reliefweb"]["trust_tier"], "NONE")


class TestSourceGroupIndependence(unittest.TestCase):
    def test_france24_dual_language_same_group(self):
        sources, _ = load_registry()
        by = by_id(sources)
        self.assertEqual(by["global_france24_afrique_fr"]["source_group"],
                         by["global_france24_africa_en"]["source_group"],
                         "FR/EN 必须同属 france24 组")

    def test_france24_not_double_independent(self):
        f24 = _src("f24_fr", group="france24")
        c1 = new_candidate(f24, {"title": "A", "url": "https://france24.com/a"})
        c2 = new_candidate(f24, {"title": "B", "url": "https://france24.com/b"})
        n, groups = independent_count([c1, c2])
        self.assertEqual(n, 1, "同一 source_group 只算 1 个独立来源")

    def test_distinct_groups_independent(self):
        c1 = new_candidate(_src("bbc"), {"title": "A", "url": "https://bbc.com/a"})
        c2 = new_candidate(_src("rfi"), {"title": "B", "url": "https://rfi.fr/b"})
        n, _ = independent_count([c1, c2])
        self.assertEqual(n, 2)


class TestAllAfricaProvenance(unittest.TestCase):
    def test_aggregator_publisher_provenance(self):
        # AllAfrica item 含 original_publisher（WHO）→ origin 追溯为 who，非 allafrica
        src = _src("allafrica", group="allafrica", role="discovery", tier="D",
                   evidence_eligible=False)
        cand = new_candidate(src, {"title": "X", "url": "https://allafrica.com/x",
                                   "original_publisher": "WHO"})
        self.assertEqual(origin_group(cand), "who",
                         "AllAfrica 必须追溯 original publisher")

    def test_allafrica_not_counted_independent_from_original(self):
        src = _src("allafrica", group="allafrica", role="discovery", tier="D",
                   evidence_eligible=False)
        c_agg = new_candidate(src, {"title": "X", "url": "https://allafrica.com/x",
                                    "original_publisher": "RFI"})
        c_rfi = new_candidate(_src("rfi", group="rfi"),
                              {"title": "X", "url": "https://rfi.fr/x"})
        n, _ = independent_count([c_agg, c_rfi])
        self.assertEqual(n, 1, "allafrica 转载 + rfi 原始不得算 2 个独立来源")

    def test_unknown_publisher_stays_aggregator(self):
        src = _src("allafrica", group="allafrica", role="discovery", tier="D",
                   evidence_eligible=False)
        cand = new_candidate(src, {"title": "X", "url": "https://allafrica.com/x",
                                   "original_publisher": None})
        self.assertEqual(origin_group(cand), "aggregator:allafrica")


class TestReliefWebInheritance(unittest.TestCase):
    def test_reliefweb_origin_group_by_publisher(self):
        src = _src("reliefweb", group="reliefweb", role="distribution_platform",
                   tier="NONE", evidence_eligible=False)
        cand = new_candidate(src, {"title": "Y", "url": "https://reliefweb.int/y",
                                   "original_publisher": "World Health Organization"})
        self.assertEqual(origin_group(cand), "world health organization")


class TestAfricaFilter(unittest.TestCase):
    def test_africa_region_keywords(self):
        self.assertTrue(is_africa_text("Sahel security situation"))
        self.assertTrue(is_africa_text("Afrique de l'Ouest"))
        self.assertFalse(is_africa_text("Stock market in Tokyo"))

    def test_country_aliases(self):
        self.assertTrue(is_africa_text("Tchad: attaques"))
        self.assertTrue(is_africa_text("Nigeria economy"))
        self.assertEqual(country_hints("Chad and Niger"), ["NE", "TD"])

    def test_filter_splits_global_feed(self):
        items = [
            {"title": "Niger coup update", "url": "https://aj.com/1"},
            {"title": "US election", "url": "https://aj.com/2"},
            {"title": "Ethiopia drought", "url": "https://aj.com/3"},
        ]
        africa, filtered = filter_candidates(items)
        self.assertEqual(len(africa), 2)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["africa_filter"], "filtered_non_africa")


class TestDedup(unittest.TestCase):
    def test_duplicate_url_dedup(self):
        src = _src("bbc")
        c1 = new_candidate(src, {"title": "A", "url": "https://bbc.com/news/a"})
        c2 = new_candidate(src, {"title": "A2", "url": "https://bbc.com/news/a?utm=1"})
        uniq, dup = dedup_candidates([c1, c2])
        self.assertEqual(len(uniq), 1, "规范化 URL 去重应只留 1 条")
        self.assertEqual(dup, 1)

    def test_original_url_dedup_across_aggregators(self):
        src1 = _src("allafrica", group="allafrica", role="discovery", tier="D",
                    evidence_eligible=False)
        src2 = _src("reliefweb", group="reliefweb", role="distribution_platform",
                    tier="NONE", evidence_eligible=False)
        c1 = new_candidate(src1, {"title": "A", "url": "https://allafrica.com/agg",
                                  "original_publisher": "WHO",
                                  "original_url": "https://who.int/report/x"})
        c2 = new_candidate(src2, {"title": "A", "url": "https://reliefweb.int/rep",
                                  "original_publisher": "WHO",
                                  "original_url": "https://who.int/report/x"})
        uniq, dup = dedup_candidates([c1, c2])
        self.assertEqual(len(uniq), 1, "同一 original_url 跨聚合器应去重")


class TestSourceHealth(unittest.TestCase):
    def test_health_record_and_runtime_gitignore(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "health.json")
            record_health([{"source_id": "s1", "listing_status": "success",
                            "http_status": 200, "items_discovered": 5,
                            "failure_type": "none"}], path=p,
                          latest_items={"s1": "2026-08-26T00:00:00+08:00"})
            doc = load_health(p)
            self.assertEqual(len(doc["entries"]), 1)
            self.assertEqual(doc["entries"][0]["latest_item_at"],
                             "2026-08-26T00:00:00+08:00")
        gi = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
        self.assertIn("data/runtime/", gi, "runtime 必须 gitignore 不进 dist")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    print("RESULT: PASS=%d FAIL=%d" % (n_run - n_fail, n_fail))
    sys.exit(1 if n_fail else 0)
