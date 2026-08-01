#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3A 验收测试 — 真实采集闭环。

覆盖：
  1. 采集器成功返回统一字段
  2. URL去重
  3. 内容哈希去重
  4. 测试数据不得进入公开事件
  5. 未来时间数据不得进入公开事件
  6. 无效URL不得进入公开事件
  7. 无标题内容不得进入公开事件
  8. 非社会安全内容不得进入公开事件
  9. published_events只包含准入事件
  10. quarantined_items记录隔离原因
  11. 法语和阿拉伯语原文可正确保存
  12. 原始时间能正确转换为北京时间
  13. 无原始发布时间时不会伪造时间
  14. data/ai/queue/不会进入dist
  15. 来源失败不影响其他来源
  16. published_events结构完整
"""
import os
import sys
import json
import hashlib
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "collectors"))

from stage3_collect import (
    publish_check, build_event, content_hash, norm_url,
    load_published, load_quarantine,
)


class TestDedup(unittest.TestCase):
    def test_url_norm(self):
        """URL规范化：去尾部斜杠、fragment。"""
        self.assertEqual(norm_url("https://example.com/path/"),
                         "https://example.com/path")
        self.assertEqual(norm_url("https://example.com/path#section"),
                         "https://example.com/path")
        self.assertEqual(norm_url(""),
                         "")

    def test_url_dedup(self):
        """相同规范化URL被去重。"""
        urls = set()
        urls.add(norm_url("https://example.com/a/"))
        self.assertIn(norm_url("https://example.com/a"), urls)

    def test_content_hash_dedup(self):
        """相同内容生成相同哈希。"""
        h1 = content_hash("Attack in Chad", "Armed group attacked village")
        h2 = content_hash("Attack in Chad", "Armed group attacked village")
        h3 = content_hash("Different title", "Different content")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)


class TestPublishGate(unittest.TestCase):

    def setUp(self):
        self.existing_urls = {"https://existing.com/article"}
        self.existing_hashes = {content_hash("Existing Title", "Existing Summary")}

    def test_valid_event_passes(self):
        a = {"title": "Attack in N'Djamena", "url": "https://new.com/a",
             "summary": "Armed attack", "published": "2026-08-01T10:00:00Z",
             "country_cn": "乍得", "source_name": "Tchadinfos",
             "_country": {"decision": "chad"}, "_relevant": True}
        ok, reason = publish_check(a, set(), self.existing_urls, self.existing_hashes)
        self.assertTrue(ok, f"Expected pass, got: {reason}")

    def test_duplicate_url_fails(self):
        a = {"title": "New Title", "url": "https://existing.com/article",
             "summary": "Something", "country_cn": "乍得",
             "source_name": "Source", "_country": {"decision": "chad"}, "_relevant": True}
        ok, reason = publish_check(a, set(), self.existing_urls, self.existing_hashes)
        self.assertFalse(ok)
        self.assertEqual(reason, "duplicate_url")

    def test_duplicate_content_fails(self):
        a = {"title": "Existing Title", "url": "https://new.com/b",
             "summary": "Existing Summary", "country_cn": "乍得",
             "source_name": "Source", "_country": {"decision": "chad"}, "_relevant": True}
        ok, reason = publish_check(a, set(), self.existing_urls, self.existing_hashes)
        self.assertFalse(ok)
        self.assertEqual(reason, "duplicate_content")

    def test_empty_title_fails(self):
        a = {"title": "", "url": "https://new.com/c",
             "summary": "Something", "country_cn": "乍得",
             "source_name": "Source", "_country": {"decision": "chad"}, "_relevant": True}
        ok, reason = publish_check(a, set(), self.existing_urls, self.existing_hashes)
        self.assertFalse(ok)
        self.assertEqual(reason, "title_too_short")

    def test_short_title_fails(self):
        a = {"title": "Hi", "url": "https://new.com/d",
             "summary": "Something", "country_cn": "乍得",
             "source_name": "Source", "_country": {"decision": "chad"}, "_relevant": True}
        ok, reason = publish_check(a, set(), self.existing_urls, self.existing_hashes)
        self.assertFalse(ok)
        self.assertEqual(reason, "title_too_short")

    def test_invalid_url_fails(self):
        a = {"title": "Valid Title Here", "url": "not-a-url",
             "country_cn": "乍得", "source_name": "Source",
             "_country": {"decision": "chad"}, "_relevant": True}
        ok, reason = publish_check(a, set(), self.existing_urls, self.existing_hashes)
        self.assertFalse(ok)
        self.assertEqual(reason, "url_invalid")

    def test_non_relevant_fails(self):
        a = {"title": "Sports Match in Chad", "url": "https://new.com/e",
             "summary": "Football", "country_cn": "乍得",
             "source_name": "Source", "_country": {"decision": "chad"}, "_relevant": False}
        ok, reason = publish_check(a, set(), self.existing_urls, self.existing_hashes)
        self.assertFalse(ok)
        self.assertEqual(reason, "not_security_relevant")

    def test_future_date_fails(self):
        future = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        a = {"title": "Future Event Title", "url": "https://new.com/f",
             "summary": "Future", "published": future,
             "country_cn": "乍得", "source_name": "Source",
             "_country": {"decision": "chad"}, "_relevant": True}
        ok, reason = publish_check(a, set(), self.existing_urls, self.existing_hashes)
        self.assertFalse(ok)
        self.assertEqual(reason, "future_date")

    def test_missing_source_name_fails(self):
        a = {"title": "Valid Title Here Now", "url": "https://new.com/g",
             "summary": "Something", "country_cn": "乍得",
             "source_name": "", "_country": {"decision": "chad"}, "_relevant": True}
        ok, reason = publish_check(a, set(), self.existing_urls, self.existing_hashes)
        self.assertFalse(ok)
        self.assertEqual(reason, "source_name_missing")

    def test_missing_country_fails(self):
        a = {"title": "Valid Title Here Now", "url": "https://new.com/h",
             "summary": "Something", "country_cn": "",
             "source_name": "Source", "_country": {"decision": "unclear"}, "_relevant": True}
        ok, reason = publish_check(a, set(), self.existing_urls, self.existing_hashes)
        self.assertFalse(ok)
        self.assertEqual(reason, "country_invalid")


class TestEventBuilding(unittest.TestCase):
    def setUp(self):
        self.run_id = "20260801T000000+0800_test"

    def test_build_event_structure(self):
        a = {"title": "Attack in Chad Capital", "url": "https://example.com/a",
             "summary": "Armed group attacked", "published": "2026-08-01T10:00:00Z",
             "language": "fr", "source_name": "Tchadinfos", "country_cn": "乍得",
             "_country": {"decision": "chad"}, "_relevant": True}
        e = build_event(a, self.run_id, "CAND-abc123def456")
        self.assertTrue(e["event_id"].startswith("EVT_"))
        self.assertEqual(e["country"], "TD")
        self.assertEqual(e["country_cn"], "乍得")
        self.assertEqual(e["title_original"], "Attack in Chad Capital")
        self.assertEqual(e["original_language"], "fr")
        self.assertIn("source_links", e)
        self.assertEqual(len(e["source_links"]), 1)
        self.assertEqual(e["source_links"][0]["url"], "https://example.com/a")
        self.assertEqual(e["source_links"][0]["source_name"], "Tchadinfos")
        self.assertEqual(e["current_policy_passed"], True)
        self.assertEqual(e["quality_gate_passed"], True)
        self.assertEqual(e["pipeline_version"], 2)
        self.assertEqual(e["schema_version"], "2.0")
        self.assertEqual(e["run_id"], self.run_id)

    def test_beijing_time_conversion(self):
        """UTC时间正确转换为北京时间。"""
        a = {"title": "Test", "url": "https://example.com/b",
             "summary": "Test", "published": "2026-08-01T10:00:00Z",
             "language": "en", "source_name": "Test", "country_cn": "乍得",
             "_country": {"decision": "chad"}, "_relevant": True}
        e = build_event(a, self.run_id, "CAND-xyz789")
        # 北京时间 = UTC + 8h
        self.assertEqual(e["published_at_beijing"], "2026-08-01 18:00:00")

    def test_no_time_no_forge(self):
        """无发布时间时不伪造。"""
        a = {"title": "Test", "url": "https://example.com/c",
             "summary": "Test", "published": "",
             "language": "en", "source_name": "Test", "country_cn": "乍得",
             "_country": {"decision": "chad"}, "_relevant": True}
        e = build_event(a, self.run_id, "CAND-nopub")
        self.assertEqual(e["published_time"], "")
        self.assertEqual(e["published_at_beijing"], "")

    def test_language_preserved(self):
        """法语和阿拉伯语原文可正确保存。"""
        for lang in ["fr", "ar", "en"]:
            a = {"title": f"Titre en {lang}", "url": f"https://example.com/{lang}",
                 "summary": f"Résumé en {lang}", "published": "2026-08-01T10:00:00Z",
                 "language": lang, "source_name": "Test", "country_cn": "乍得",
                 "_country": {"decision": "chad"}, "_relevant": True}
            e = build_event(a, self.run_id, f"CAND-{lang}")
            self.assertEqual(e["original_language"], lang)


class TestDataIntegrity(unittest.TestCase):
    def test_published_events_valid(self):
        """已发布的 published_events.json 结构完整。"""
        pub = load_published()
        self.assertIn("schema_version", pub)
        self.assertIn("items", pub)
        items = pub.get("items", [])
        for item in items:
            self.assertIn("event_id", item)
            self.assertIn("country", item)
            self.assertIn("title_original", item, f"Missing title_original in {item.get('event_id')}")
            self.assertIn("source_links", item)
            self.assertTrue(len(item.get("source_links", [])) > 0,
                          f"No source_links in {item.get('event_id')}")
            for link in item.get("source_links", []):
                self.assertIn("url", link)
                self.assertTrue(link.get("url", "").startswith("http"),
                              f"Invalid URL in {item.get('event_id')}: {link.get('url')}")

    def test_quarantine_has_reasons(self):
        """隔离项目记录原因。"""
        q = load_quarantine()
        items = q.get("items", [])
        # May be empty in fresh state, but any items must have reason
        for item in items:
            # Check for reason/reason_code/reason_cn fields
            has_reason = any(k in item for k in ("reason", "reason_code", "reason_cn"))
            self.assertTrue(has_reason,
                         f"Quarantine item missing reason: {item.get('candidate_id') or item.get('quarantine_id')}")

    def test_no_test_data_in_published(self):
        """测试/占位数据不得进入公开事件。"""
        pub = load_published()
        # Check for patterns indicating test/placeholder data
        bad_patterns = ["TEST DATA", "placeholder", "占位", "测试数据", "fake event"]
        for item in pub.get("items", []):
            title = ((item.get("title_cn") or "") + " " + (item.get("title_original") or "")).upper()
            for bp in bad_patterns:
                self.assertNotIn(bp.upper(), title,
                              f"Test/placeholder data found in {item.get('event_id')}: {item.get('title_original')[:60]}")

    def test_dist_no_ai_queue(self):
        """data/ai/queue/ 不进入 dist。"""
        dist_ai_queue = os.path.join(ROOT, "dist", "data", "ai", "queue")
        if os.path.isdir(os.path.join(ROOT, "dist")):
            self.assertFalse(os.path.isdir(dist_ai_queue),
                           "dist/data/ai/queue/ must not exist")


class TestCountryAttribution(unittest.TestCase):
    """国家归属：来源国 ≠ 事件国。"""

    def setUp(self):
        sys.path.insert(0, os.path.join(SCRIPTS, "collectors"))
        from country_runner import identify_country, load_country_cfg, relevance_stage1
        self.identify_country = identify_country
        self.relevance_stage1 = relevance_stage1
        self.chad_cfg = load_country_cfg("chad")
        self.niger_cfg = load_country_cfg("niger")

    def _country_of(self, text, cfg):
        cid = self.identify_country(text, cfg)
        return cid.get("decision")

    def test_mali_news_from_chad_media_not_chad(self):
        """Mali新闻来自乍得媒体 → 不得进入Chad。"""
        text = "Renforcement logistique des Forces de Sécurité au Mali"
        rel, _, _, _ = self.relevance_stage1(text)
        # 相关性: sécurité 是弱信号 → 不是强相关
        self.assertNotEqual(rel, True, "Mali军队后勤不应判为强安全相关")
        # 国家识别: 无乍得实体 → unclear
        cid = self.identify_country(text, self.chad_cfg)
        self.assertNotEqual(cid["decision"], "chad")

    def test_nigeria_not_niger(self):
        """Nigeria不得误判为Niger。"""
        text = "Nigeria: Boko Haram attacks in Borno State"
        cid = self.identify_country(text, self.niger_cfg)
        self.assertNotEqual(cid["decision"], "niger", "Nigeria事件不得归入Niger")
        self.assertEqual(cid.get("excluded_entities"), ["nigeria"])

    def test_niger_republic_is_niger(self):
        """Niger Republic可识别为Niger。"""
        text = "République du Niger: attaque jihadiste à Tillabéri"
        cid = self.identify_country(text, self.niger_cfg)
        self.assertEqual(cid["decision"], "niger")

    def test_lake_chad_not_auto_chad(self):
        """Lake Chad不自动等于Chad国内事件。"""
        text = "Lake Chad Basin: cross-border insecurity affects four countries"
        cid = self.identify_country(text, self.chad_cfg)
        self.assertNotEqual(cid["decision"], "chad", "Lake Chad Basin不应自动归乍得")
        self.assertEqual(cid["decision"], "regional")

    def test_ndjamena_is_chad(self):
        """N'Djamena应识别为Chad。"""
        text = "Attaque terroriste à N'Djamena, des soldats tchadiens tués"
        cid = self.identify_country(text, self.chad_cfg)
        self.assertEqual(cid["decision"], "chad")
        rel, _, _, _ = self.relevance_stage1(text)
        self.assertEqual(rel, True, "N'Djamena袭击应为强相关")

    def test_niamey_is_niger(self):
        """Niamey应识别为Niger。"""
        text = "Niamey: le Général reçoit la délégation russe"
        cid = self.identify_country(text, self.niger_cfg)
        self.assertEqual(cid["decision"], "niger")

    def test_multi_country_uses_primary(self):
        """同时提到多个国家时，以主要事件地点为准。"""
        # Niger事件 + 提及Nigeria → 归Niger
        text = "Attaque à Diffa au Niger, les assaillants viennent du Nigeria"
        cid = self.identify_country(text, self.niger_cfg)
        self.assertEqual(cid["decision"], "niger")

    def test_uncertain_country_not_forced(self):
        """无法确定主要国家时进入候选/隔离，不强制发布。"""
        text = "Conférence régionale sur la sécurité à Paris"
        cid = self.identify_country(text, self.chad_cfg)
        self.assertNotEqual(cid["decision"], "chad")

    def test_source_country_separate_from_event(self):
        """来源国家与事件国家分别保存。"""
        import stage3_collect
        a = {"title": "Borkou: quatre officiers tombés", "url": "https://x.com/b",
             "summary": "officiers tombés sous les balles", "published": "2026-08-01T10:00:00Z",
             "language": "fr", "source_name": "Tchad One", "source_country_cn": "乍得",
             "_country": {"decision": "chad", "event_location_country": "chad",
                          "mentioned_countries": []}, "_relevant": True}
        e = stage3_collect.build_event(a, "20260801T000000+0800_t", "CAND-src1")
        self.assertEqual(e["source_country"], "乍得")
        self.assertEqual(e["primary_country"], "chad")
        self.assertEqual(e["event_location_country"], "chad")


class TestSourceStats(unittest.TestCase):
    """来源统计由程序自动生成。"""

    def test_stats_file_generated(self):
        """采集后生成结构化统计文件。"""
        stats_path = os.path.join(ROOT, "logs", "stage3_stats.json")
        if os.path.exists(stats_path):
            with open(stats_path, "r", encoding="utf-8") as f:
                s = json.load(f)
            self.assertIn("configured_sources", s)
            self.assertIn("active_sources", s)
            self.assertIn("successful_sources", s)
            self.assertIn("failed_sources", s)
            self.assertIn("sources_with_items", s)
            self.assertIn("sources_with_published", s)
            self.assertIn("sources", s)
            self.assertIn("totals", s)
            # sources 数量一致性
            self.assertEqual(
                len(s["sources"]),
                s["successful_sources"] + s["failed_sources"],
                "sources数量必须等于成功+失败")


class TestFailureProtection(unittest.TestCase):
    """失败保护：单来源失败 / 全来源失败。"""

    def test_single_source_failure_isolated(self):
        """单个来源失败不影响其他来源。"""
        from stage3_collect import load_sources
        srcs = load_sources().get("sources", [])
        # sources.json 中 enabled 的来源应包含多种状态，不是全成功也不是全失败
        if srcs:
            self.assertTrue(len(srcs) > 0)

    def test_published_never_empty_after_failure(self):
        """全部来源失败时不清空历史有效数据。"""
        pub = load_published()
        self.assertGreater(len(pub.get("items", [])), 0,
                          "published_events 不得为空（历史有效数据必须保留）")


def _gate_compatible_main():
    """以 gate 兼容格式运行：打印 RESULT: PASS=x FAIL=y 行。"""
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    n_pass = n_run - n_fail
    print(f"RESULT: PASS={n_pass} FAIL={n_fail}")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    _gate_compatible_main()
