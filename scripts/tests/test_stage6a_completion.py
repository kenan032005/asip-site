#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6A Completion — Blocking & Detail-Enrichment 测试（§十八）。

覆盖：true pre-pair blocking / adjacent time buckets / cross-border block /
published_at fallback / detail-enriched candidate / location·event_type·numeric
hints / blocking 不漏 Golden Set expected same_event / 旧 24 Golden 仍 PASS。
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)

from scripts.clustering.blocking import build_blocks, day_bucket
from scripts.clustering.enrich import (
    enrich_candidate, extract_event_type, extract_location_hints,
    extract_numeric_facts, extract_casualty_hints, retrieval_priority,
)
from scripts.clustering.dedup import dedup_articles
from scripts.clustering.cluster import cluster_candidates
from scripts.clustering.golden_runner import run_golden


def _art(cid, **kw):
    base = {
        "candidate_id": cid, "source_id": kw.get("source_id", "s1"),
        "source_group": kw.get("source_group", "s1"), "trust_tier": "B",
        "title": kw.get("title", "Event"), "url": kw.get("url", "https://x.com/%s" % cid),
        "published_at": kw.get("published_at", "2026-08-25T10:00:00+00:00"),
        "event_time": kw.get("event_time"),
        "primary_country_iso3": kw.get("country", "TCD"),
        "affected_countries": kw.get("affected_countries", []),
        "cross_border": kw.get("cross_border", False),
        "location": kw.get("location"), "event_type": kw.get("event_type"),
        "body": kw.get("body"), "body_extracted": kw.get("body_extracted"),
    }
    base.update({k: v for k, v in kw.items() if k not in base})
    return base


class TestTrueBlocking(unittest.TestCase):
    def test_pre_pair_reduction(self):
        arts = [_art("a%d" % i, country="TCD",
                     published_at="2026-08-2%dT09:00:00+00:00" % (4 + i % 6))
                for i in range(20)]
        blocks, st = build_blocks(arts)
        self.assertLess(st["blocked_candidate_pairs"], st["all_possible_pairs"])
        self.assertGreater(st["reduction_ratio"], 0.5)

    def test_adjacent_day_buckets(self):
        # D 与 D+1 同 block；D 与 D+3 不同 block
        a = _art("a", published_at="2026-08-25T09:00:00+00:00")
        b = _art("b", published_at="2026-08-26T09:00:00+00:00")
        c = _art("c", published_at="2026-08-28T09:00:00+00:00")
        blocks, _ = build_blocks([a, b, c])
        ab_same = any({"a", "b"} <= {m.get("candidate_id") for m in blk} for blk in blocks)
        ac_same = any({"a", "c"} <= {m.get("candidate_id") for m in blk} for blk in blocks)
        self.assertTrue(ab_same, "相邻天应同 block")
        self.assertFalse(ac_same, "隔 3 天不应同 block")

    def test_cross_border_block(self):
        a = _art("a", country="TCD", affected_countries=["NER"])
        b = _art("b", country="NER", affected_countries=["TCD"])
        blocks, _ = build_blocks([a, b])
        self.assertTrue(any({"a", "b"} <= {m.get("candidate_id") for m in blk}
                            for blk in blocks))

    def test_published_at_fallback(self):
        arts = [_art("a", published_at="2026-08-25T09:00:00+00:00")]
        _, st = build_blocks(arts)
        self.assertEqual(st["time_basis_counts"]["published_at"], 1)


class TestDayBucket(unittest.TestCase):
    def test_iso_parse(self):
        self.assertEqual(day_bucket("2026-08-25T09:00:00+00:00").isoformat(), "2026-08-25")
        self.assertIsNone(day_bucket(None))
        self.assertIsNone(day_bucket("not-a-date"))


class TestEnrichment(unittest.TestCase):
    def _listing(self, **kw):
        base = {"candidate_id": "GC_x", "source_id": "tcd_tchadinfos",
                "source_group": "tchadinfos", "title": "Attaque à N'Djamena",
                "url": "https://tchadinfos.com/a", "published_at":
                "2026-08-25T10:00:00+00:00", "country_iso3": "TCD"}
        base.update(kw)
        return base

    def test_enriched_fields(self):
        cand = self._listing()
        detail = {"title": "Attaque meurtrière à N'Djamena, 12 morts",
                  "published_at": "2026-08-25T10:00:00+00:00",
                  "canonical_url": "https://tchadinfos.com/a",
                  "body_extracted": ("Une attaque meurtrière a frappé N'Djamena "
                                     "ce matin. 12 morts et 30 blessés ont été "
                                     "rapportés."),
                  "detail_success": True}
        e = enrich_candidate(cand, detail)
        self.assertEqual(e["event_time_basis"], "published_at")
        self.assertIsNone(e["event_time"])
        self.assertIn("TCD", e["primary_country_iso3"] or "")
        self.assertTrue(e["body_length"] > 0)
        self.assertTrue(e["content_hash"])

    def test_event_type_hints(self):
        self.assertEqual(extract_event_type("Deadly attack in capital"), "armed_attack")
        self.assertEqual(extract_event_type("Manifestation à Niamey"), "civil_unrest")
        self.assertEqual(extract_event_type("Inondations au Tchad"), "natural_disaster")

    def test_location_hints(self):
        hints = extract_location_hints("Attaque à N'Djamena, Tchad",
                                       "Incident in the capital of Chad.")
        joined = " ".join(hints)
        self.assertTrue(any(h.startswith("country:") for h in hints))

    def test_numeric_and_casualty(self):
        nums = extract_numeric_facts("12 morts et 30 blessés, plus de 500 déplacés.")
        self.assertIn(12, nums)
        self.assertIn(500, nums)
        cas = extract_casualty_hints("12 morts", "12 morts signalés")
        self.assertTrue(any(c["value"] == 12 for c in cas))

    def test_retrieval_priority_multi_source_first(self):
        arts = [
            _art("a", country="TCD", published_at="2026-08-25T09:00:00+00:00"),
            _art("b", country="TCD", published_at="2026-08-25T10:00:00+00:00"),
            _art("c", country="NER", published_at="2026-08-25T09:00:00+00:00"),
        ]
        order = retrieval_priority(arts)
        self.assertEqual(order[0]["primary_country_iso3"], "TCD",
                         "多源组应优先")


class TestBlockingKeepsGoldenSameEvent(unittest.TestCase):
    def test_same_event_pair_same_block_and_auto(self):
        # golden s1 fixture：同国同日同城同伤亡同类型 → blocking 同 block → auto
        a = _art("s1a", source_group="src_a", title="Attack in CITY_ALPHA kills 10",
                 location="CITY_ALPHA", casualties=10, event_type="armed_attack",
                 published_at="2026-08-25T09:00:00+00:00")
        b = _art("s1b", source_group="src_b", title="Deadly attack in CITY_ALPHA",
                 location="CITY_ALPHA", casualties=10, event_type="armed_attack",
                 published_at="2026-08-25T10:00:00+00:00")
        blocks, _ = build_blocks([a, b])
        self.assertTrue(any({"s1a", "s1b"} <= {m.get("candidate_id") for m in blk}
                            for blk in blocks), "same_event 不得被 blocking 拆散")
        clusters, stats, _ = cluster_candidates([a, b])
        self.assertEqual(stats["auto_clustered_pairs"], 1)

    def test_golden_still_24_24(self):
        r = run_golden()
        self.assertEqual(r["failed"], 0, "Golden Set 必须保持 24/24")


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
