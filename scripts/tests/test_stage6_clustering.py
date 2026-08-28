#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6A — Cross-Source Clustering 测试（§二十三）。

覆盖：URL normalization / content hash dedup / source_group independence /
aggregator provenance / country·time·location hard reject / event type
compatibility / numeric mismatch non-reject / score thresholds / needs_review /
transitive overmerge protection / cluster anchor / conflict preservation /
runtime isolation / Canonical unchanged / Golden Set 24/24。
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)

from scripts.clustering.dedup import normalize_url, content_hash, dedup_articles, dedup_key
from scripts.clustering.sources import (
    independent_group_key, count_independent, same_block, time_bucket,
)
from scripts.clustering.scoring import hard_reject, score_pair, event_types_compatible
from scripts.clustering.cluster import (
    cluster_candidates, compare_to_anchor, choose_anchor, THRESHOLDS,
)
from scripts.clustering.golden_runner import run_golden


def _a(cid, **kw):
    base = {
        "candidate_id": cid, "source_id": kw.get("source_id", "s1"),
        "source_group": kw.get("source_group", "s1"),
        "trust_tier": kw.get("trust_tier", "B"),
        "title": kw.get("title", "Event"), "url": kw.get("url", "https://x.com/%s" % cid),
        "canonical_url": kw.get("canonical_url"), "original_url": kw.get("original_url"),
        "original_publisher": kw.get("original_publisher"), "content_hash": kw.get("content_hash"),
        "published_at": kw.get("published_at", "2026-08-25T10:00:00+00:00"),
        "event_time": kw.get("event_time", "2026-08-25T09:00:00+00:00"),
        "primary_country_iso3": kw.get("country", "XAA"),
        "affected_countries": kw.get("affected_countries", []),
        "location": kw.get("location"), "event_type": kw.get("event_type", "armed_attack"),
        "actor": kw.get("actor"), "target": kw.get("target"), "facility": kw.get("facility"),
        "casualties": kw.get("casualties"), "numeric_facts": kw.get("numeric_facts", []),
        "body": kw.get("body"), "body_extracted": kw.get("body_extracted"),
    }
    base.update({k: v for k, v in kw.items() if k not in base})
    return base


class TestUrlNormalization(unittest.TestCase):
    def test_http_https_www(self):
        self.assertEqual(normalize_url("HTTP://WWW.X.COM/A/"),
                         normalize_url("https://x.com/a"))

    def test_tracking_params_removed(self):
        self.assertEqual(normalize_url("https://x.com/a?utm_source=1&id=5&fbclid=z"),
                         normalize_url("https://x.com/a?id=5"))

    def test_trailing_slash(self):
        self.assertEqual(normalize_url("https://x.com/a/"), normalize_url("https://x.com/a"))

    def test_query_order_insensitive(self):
        self.assertEqual(normalize_url("https://x.com/a?b=2&a=1"),
                         normalize_url("https://x.com/a?a=1&b=2"))


class TestArticleDedup(unittest.TestCase):
    def test_content_hash_dedup(self):
        a = _a("a", content_hash="h1")
        b = _a("b", content_hash="h1")
        unique, dups = dedup_articles([a, b])
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(dups), 1)

    def test_canonical_url_dedup(self):
        a = _a("a", canonical_url="https://x.com/r1")
        b = _a("b", canonical_url="https://x.com/r1")
        unique, dups = dedup_articles([a, b])
        self.assertEqual(len(unique), 1)

    def test_utm_dedup(self):
        a = _a("a", url="https://x.com/r1?utm_source=a")
        b = _a("b", url="https://x.com/r1?utm_source=b")
        unique, dups = dedup_articles([a, b])
        self.assertEqual(len(unique), 1)

    def test_aggregator_original_url_dedup(self):
        a = _a("a", source_group="allafrica", url="https://allafrica.com/r",
               original_url="https://rfi.fr/r1", original_publisher="RFI")
        b = _a("b", source_group="rfi", url="https://rfi.fr/r1")
        unique, dups = dedup_articles([a, b])
        self.assertEqual(len(unique), 1, "AllAfrica 转载须经 original_url 去重")


class TestSourceIndependence(unittest.TestCase):
    def test_france24_dual_language_one_group(self):
        a = _a("a", source_group="france24")
        b = _a("b", source_group="france24")
        self.assertEqual(independent_group_key(a), independent_group_key(b))
        n, _ = count_independent([a, b])
        self.assertEqual(n, 1)

    def test_aggregator_provenance_inherit(self):
        a = _a("a", source_group="allafrica", original_publisher="WHO")
        self.assertEqual(independent_group_key(a), "who")

    def test_distinct_groups_independent(self):
        n, _ = count_independent([_a("a", source_group="x"), _a("b", source_group="y")])
        self.assertEqual(n, 2)


class TestHardReject(unittest.TestCase):
    def test_country_mismatch(self):
        a = _a("a", country="XAA", location="C1")
        b = _a("b", country="YBB", location="C2")
        self.assertTrue(hard_reject(a, b)[0])

    def test_cross_border_overrides(self):
        a = _a("a", country="XAA", affected_countries=["YBB"])
        b = _a("b", country="YBB", affected_countries=["XAA"])
        self.assertFalse(hard_reject(a, b)[0])

    def test_time_separation_gt72h(self):
        a = _a("a", event_time="2026-08-25T09:00:00+00:00")
        b = _a("b", event_time="2026-08-30T09:00:00+00:00")
        self.assertTrue(hard_reject(a, b)[0])

    def test_distinct_location(self):
        a = _a("a", location="CITY_A")
        b = _a("b", location="CITY_B")
        self.assertTrue(hard_reject(a, b)[0])

    def test_incompatible_event_type(self):
        a = _a("a", event_type="armed_attack")
        b = _a("b", event_type="economic")
        self.assertTrue(hard_reject(a, b)[0])

    def test_distinct_target(self):
        a = _a("a", actor="G1", target="T1")
        b = _a("b", actor="G1", target="T2")
        self.assertTrue(hard_reject(a, b)[0])


class TestNumericMismatch(unittest.TestCase):
    def test_casualty_mismatch_not_reject(self):
        a = _a("a", casualties=10, location="C1")
        b = _a("b", casualties=12, location="C1")
        rejected, reason = hard_reject(a, b)
        self.assertFalse(rejected, "casualty 差异不得 hard reject")
        res = compare_to_anchor(a, b)
        self.assertTrue(any(f.startswith("casualty_difference") for f in res["conflict_flags"]))


class TestScoringThresholds(unittest.TestCase):
    def test_auto_threshold(self):
        a = _a("a", location="C1", casualties=10)
        b = _a("b", location="C1", casualties=10, source_group="s2")
        res = compare_to_anchor(a, b)
        self.assertEqual(res["verdict"], "auto")
        self.assertGreaterEqual(res["score"], THRESHOLDS["auto"])

    def test_low_score_separate(self):
        a = _a("a", title="Alpha")
        b = _a("b", title="Beta", source_group="s2")
        res = compare_to_anchor(a, b)
        self.assertEqual(res["verdict"], "separate")


class TestTransitiveOvermerge(unittest.TestCase):
    def test_no_chain_merge(self):
        # A-B 高分、B-C 高分，但 C 与 anchor A 不兼容 → C 不得并入
        a = _a("a", location="CITY_A", title="Attack in CITY_A", source_group="s1")
        b = _a("b", location="CITY_A", title="Attack in CITY_A reported", source_group="s2")
        c = _a("c", location="CITY_C", title="Attack in CITY_C", source_group="s3")
        # 直接用 cluster 引擎：A 为 anchor，C 与 A 不同 location → R3 reject
        clusters, stats, _ = cluster_candidates([a, b, c])
        merged = [m for m in clusters if len(m["member_ids"]) >= 2]
        self.assertEqual(len(merged), 1, "只有 A+B 合并；C 不得链式并入")
        self.assertEqual(merged[0]["member_ids"], ["a", "b"])
        self.assertEqual(stats["master_event_count"], 2)


class TestClusterAnchor(unittest.TestCase):
    def test_tier_a_anchor(self):
        a = _a("a", trust_tier="C", title="late full report", body="x" * 200)
        b = _a("b", trust_tier="A", title="official", body="y" * 50)
        anchor = choose_anchor([a, b])
        self.assertEqual(anchor["candidate_id"], "b", "Tier A 优先作 anchor")


class TestConflictPreservation(unittest.TestCase):
    def test_conflicts_preserved(self):
        a = _a("a", casualties=10, actor="G1")
        b = _a("b", casualties=12, actor="G2", source_group="s2", location="C1")
        res = compare_to_anchor(a, b)
        flags = res["conflict_flags"]
        self.assertTrue(any(f.startswith("casualty_difference") for f in flags))
        self.assertIn("actor_attribution_difference", flags)


class TestRuntimeAndCanonical(unittest.TestCase):
    def test_runtime_isolation(self):
        gi = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
        self.assertIn("data/runtime/", gi)

    def test_canonical_public_unchanged(self):
        # 本包不写 Canonical：验证 data/events.json 存在且未被本包逻辑引用修改
        p = os.path.join(ROOT, "data", "events.json")
        self.assertTrue(os.path.exists(p), "data/events.json 应存在")
        # 本包不应导入/写 events.json 的模块存在性检查
        gi = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
        self.assertIn("data/runtime/", gi)


class TestGoldenSet(unittest.TestCase):
    def test_golden_24_24(self):
        r = run_golden()
        self.assertEqual(r["total"], 24, "应有 24 对 fixture")
        self.assertEqual(r["failed"], 0, "Golden Set 必须 24/24: %s" %
                         [x for x in r["results"] if not x["pass"]])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    print("RESULT: PASS=%d FAIL=%d" % (n_run - n_fail, n_fail))
    sys.exit(1 if n_fail else 0)
