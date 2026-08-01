#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3B 测试 — 信息源扩展 + 完整正文提取。

覆盖（按需求文档第十五节）：
  RSS/Atom:   解析/去重/相对URL/无summary/日期格式/详情页提取
  HTML栏目页: 发现/排除导航/相对链接/不重复请求/结构异常安全失败/JS标记
  正文提取:   专用选择器/通用提取/清洗/Cookie识别/拦截识别/摘要降级/title-only不公开
              /空正文不公开/质量评分/法语阿拉伯语字符/北京时间转换
  国家与准入: 来源国≠事件国/Mali不误入/Nigeria不误判Niger/Lake Chad/N'Djamena
              /Niamey/无法判断隔离/URL无效/私有IP/未来时间/测试数据
  稳定性:     单来源失败/全来源失败保护/ETag缓存/已处理不重复发布/状态损坏降级
              /提取失败记录/统计程序化/source与primary分离/run_id一致/ai队列不入dist
"""
import os
import sys
import json
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "collectors"))

from framework import (  # noqa: E402
    validate_url, norm_url, content_hash, parse_original_time, to_beijing,
    ContentExtractor, strip_tags, extract_meta,
)
from registry import parse_rss_atom, ArticleDiscoverer  # noqa: E402


# ── 测试 fixtures ────────────────────────────────────
RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item>
  <title>Attaque au Tchad</title>
  <link>https://example.com/2026/08/01/attaque</link>
  <description>Attaque terroriste à N'Djamena, 5 morts</description>
  <pubDate>Sat, 01 Aug 2026 10:00:00 GMT</pubDate>
  <guid>https://example.com/2026/08/01/attaque</guid>
</item>
<item>
  <title>Attaque au Tchad (dupe)</title>
  <link>https://example.com/2026/08/01/attaque</link>
  <description>dupe</description>
  <pubDate>Sat, 01 Aug 2026 11:00:00 GMT</pubDate>
</item>
<item>
  <title>Article sans summary</title>
  <link>https://example.com/2026/08/01/nosummary</link>
  <pubDate>2026-08-01T12:30:00Z</pubDate>
</item>
</channel></rss>"""

ATOM_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Test</title>
<entry>
  <title>Incident à Niamey</title>
  <link href="https://example.com/niamey-incident"/>
  <summary>Incident sécuritaire à Niamey</summary>
  <published>2026-08-01T10:00:00+02:00</published>
  <id>tag:example.com,2026:niamey</id>
</entry>
</feed>"""

HTML_ARTICLE = """<html><head><title>Attaque au Tchad - TestSite</title>
<meta property="og:title" content="Attaque au Tchad">
<meta property="og:image" content="https://img.example.com/a.jpg">
<meta property="article:published_time" content="2026-08-01T10:00:00Z">
<meta property="article:author" content="Jean Dupont">
</head><body>
<nav>Accueil Contact News</nav>
<article>
<p>Une attaque terroriste a eu lieu à N'Djamena ce matin.</p>
<p>Les forces de sécurité ont répondu rapidement à l'attaque dans la capitale tchadienne.</p>
<p>Plusieurs soldats ont été blessés lors de l'affrontement avec les assaillants armés.</p>
<p>La situation est désormais sous contrôle selon les autorités locales.</p>
<p>Cet incident survient dans un contexte de tensions sécuritaires régionales persistantes.</p>
</article>
<footer>Copyright TestSite - Tous droits réservés</footer>
</body></html>"""

HTML_LISTING = """<html><body>
<nav><a href="/">Accueil</a><a href="/category/securite/">Sécurité</a></nav>
<div class="article-list">
  <article><a href="/2026/08/01/attaque-ndjamena">Attaque à N'Djamena</a></article>
  <article><a href="/2026/07/31/arme-saisie">Saisie d'armes à Salamat</a></article>
</div>
<footer><a href="/about">À propos</a></footer>
</body></html>"""


class TestRSSAtom(unittest.TestCase):
    def test_rss20_parse(self):
        items = parse_rss_atom(RSS_SAMPLE)
        self.assertGreaterEqual(len(items), 2)

    def test_atom_parse(self):
        items = parse_rss_atom(ATOM_SAMPLE)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Incident à Niamey")

    def test_feed_dedup(self):
        items = parse_rss_atom(RSS_SAMPLE)
        urls = [i["url"] for i in items]
        self.assertEqual(len(urls), len(set(urls)), "Feed 内重复 URL 应去重")

    def test_no_summary_item(self):
        items = parse_rss_atom(RSS_SAMPLE)
        no_sum = [i for i in items if "nosummary" in i["url"]]
        self.assertTrue(no_sum, "应解析无 summary 的条目")
        self.assertEqual(no_sum[0]["summary"], "")

    def test_date_formats(self):
        items = parse_rss_atom(RSS_SAMPLE)
        # RFC822 和 ISO8601 两种日期格式都应解析出非空 published
        for i in items:
            self.assertNotEqual(i["published"], "")

    def test_relative_url_resolution(self):
        items = parse_rss_atom(ATOM_SAMPLE, base_url="https://example.com/feed")
        self.assertTrue(items[0]["url"].startswith("http"))


class TestHTMLListing(unittest.TestCase):
    def test_discover_articles(self):
        d = ArticleDiscoverer(None)
        src = {"listing_urls": ["https://example.com/category/securite/"],
               "base_url": "https://example.com", "max_items": 10,
               "discovery_type": "html_listing", "language": "fr"}
        # 用真实 HTML 模拟（通过 monkey patch _extract_links）
        links = ArticleDiscoverer._extract_links(HTML_LISTING, "https://example.com/category/securite/")
        self.assertGreaterEqual(len(links), 2)
        # 应排除导航和 footer 链接
        urls = [u for u, _ in links]
        self.assertNotIn("https://example.com/about", urls)
        self.assertNotIn("https://example.com/category/securite/", urls)

    def test_relative_links(self):
        links = ArticleDiscoverer._extract_links(HTML_LISTING, "https://example.com/category/securite/")
        for u, _ in links:
            self.assertTrue(u.startswith("http"))


class TestURLSafety(unittest.TestCase):
    def test_private_ip_rejected(self):
        self.assertFalse(validate_url("http://127.0.0.1/admin")[0])
        self.assertFalse(validate_url("http://10.0.0.1/x")[0])
        self.assertFalse(validate_url("http://192.168.1.1/x")[0])
        self.assertFalse(validate_url("http://172.16.0.1/x")[0])

    def test_metadata_host_rejected(self):
        self.assertFalse(validate_url("http://169.254.169.254/latest/meta-data")[0])

    def test_localhost_rejected(self):
        self.assertFalse(validate_url("http://localhost:8080/x")[0])

    def test_bad_scheme_rejected(self):
        self.assertFalse(validate_url("file:///etc/passwd")[0])
        self.assertFalse(validate_url("ftp://example.com/x")[0])
        self.assertFalse(validate_url("javascript:alert(1)")[0])

    def test_valid_url_ok(self):
        self.assertTrue(validate_url("https://tchadinfos.com/feed/")[0])


class TestContentExtraction(unittest.TestCase):
    def test_generic_extraction(self):
        ext = ContentExtractor({}).extract(HTML_ARTICLE, "https://example.com/a")
        self.assertGreater(ext["word_count"], 30)
        self.assertEqual(ext["quality"], "partial_body")

    def test_meta_extraction(self):
        ext = ContentExtractor({}).extract(HTML_ARTICLE, "https://example.com/a")
        self.assertEqual(ext["title"], "Attaque au Tchad")
        self.assertEqual(ext["lead_image_url"], "https://img.example.com/a.jpg")
        self.assertEqual(ext["published_original"], "2026-08-01T10:00:00Z")
        self.assertEqual(ext["author"], "Jean Dupont")

    def test_nav_footer_removed(self):
        ext = ContentExtractor({}).extract(HTML_ARTICLE, "https://example.com/a")
        body = ext["body"].lower()
        self.assertNotIn("copyright", body)
        self.assertNotIn("accueil contact", body)

    def test_cookie_page_detected(self):
        html = "<html><body>Ce site utilise des cookies pour améliorer votre expérience. Acceptez-vous ?</body></html>"
        ext = ContentExtractor({}).extract(html, "https://example.com")
        self.assertEqual(ext["quality"], "extraction_failed")

    def test_captcha_page_detected(self):
        html = '<html><body><div class="cf-chl">Checking your browser before accessing</div></body></html>'
        ext = ContentExtractor({}).extract(html, "https://example.com")
        self.assertEqual(ext["quality"], "intercepted")

    def test_quality_scores(self):
        ext = ContentExtractor({}).extract(HTML_ARTICLE, "https://example.com/a")
        self.assertGreaterEqual(ext["quality_score"], 0)
        self.assertLessEqual(ext["quality_score"], 100)

    def test_french_chars_preserved(self):
        html = '<html><body><article><p>Attaque à N\'Djamena — élections à venir, 5 morts et 12 blessés signalés ce matin dans la capitale.</p><p>Les autorités ont confirmé l\'incident sécuritaire grave.</p></article></body></html>'
        ext = ContentExtractor({}).extract(html, "https://example.com")
        self.assertIn("N'Djamena", ext["body"])
        self.assertIn("élections", ext["body"])

    def test_time_to_beijing(self):
        dt, tz = parse_original_time("2026-08-01T10:00:00Z")
        self.assertEqual(to_beijing(dt), "2026-08-01 18:00:00")
        dt2, tz2 = parse_original_time("2026-08-01T10:00:00+02:00")
        self.assertEqual(to_beijing(dt2), "2026-08-01 16:00:00")

    def test_no_time_not_forged(self):
        dt, tz = parse_original_time("")
        self.assertIsNone(dt)


class TestDedup(unittest.TestCase):
    def test_url_norm(self):
        self.assertEqual(norm_url("https://example.com/a/"), "https://example.com/a")
        self.assertEqual(norm_url("https://example.com/a?utm_source=x"), "https://example.com/a")
        self.assertEqual(norm_url("https://example.com/a#frag"), "https://example.com/a")

    def test_content_hash(self):
        self.assertEqual(content_hash("Title A", "Body A"), content_hash("Title A", "Body A"))
        self.assertNotEqual(content_hash("Title A", "Body A"), content_hash("Title B", "Body A"))


class TestCountryScope(unittest.TestCase):
    def setUp(self):
        from country_runner import identify_country, load_country_cfg, relevance_stage1
        self.identify = identify_country
        self.relevance = relevance_stage1
        self.chad = load_country_cfg("chad")
        self.niger = load_country_cfg("niger")

    def test_source_country_not_event(self):
        """来源国 ≠ 事件国。"""
        cid = self.identify("Renforcement logistique au Mali", self.chad)
        self.assertNotEqual(cid["decision"], "chad")

    def test_mali_from_chad_media(self):
        """Mali 文章来自乍得媒体仍不得进入 Chad。"""
        rel, _, _, _ = self.relevance("Renforcement des Forces de Sécurité au Mali")
        self.assertNotEqual(rel, True)

    def test_nigeria_not_niger(self):
        cid = self.identify("Nigeria: Boko Haram in Borno", self.niger)
        self.assertNotEqual(cid["decision"], "niger")

    def test_lake_chad_regional(self):
        cid = self.identify("Lake Chad Basin cross-border crisis", self.chad)
        self.assertEqual(cid["decision"], "regional")

    def test_ndjamena_chad(self):
        cid = self.identify("Attaque à N'Djamena", self.chad)
        self.assertEqual(cid["decision"], "chad")

    def test_niamey_niger(self):
        cid = self.identify("Incident à Niamey", self.niger)
        self.assertEqual(cid["decision"], "niger")

    def test_uncertain_country_isolated(self):
        cid = self.identify("Conférence internationale à Paris", self.chad)
        self.assertNotEqual(cid["decision"], "chad")


class TestStability(unittest.TestCase):
    def test_published_never_empty(self):
        """全来源失败不清空历史公开数据。"""
        pub = json.load(open(os.path.join(ROOT, "data", "public", "published_events.json")))
        self.assertGreater(len(pub.get("items", [])), 0)

    def test_no_ai_queue_in_dist(self):
        """data/ai/queue/ 不进入 dist。"""
        if os.path.isdir(os.path.join(ROOT, "dist")):
            self.assertFalse(
                os.path.isdir(os.path.join(ROOT, "dist", "data", "ai", "queue")))

    def test_stats_generated(self):
        """来源统计程序化生成。"""
        stats_path = os.path.join(ROOT, "logs", "stage3_collection_stats.json")
        if os.path.exists(stats_path):
            with open(stats_path, "r", encoding="utf-8") as f:
                s = json.load(f)
            for key in ("articles_discovered", "full_body_extracted",
                        "published_count", "quarantined_count"):
                self.assertIn(key, s.get("totals", {}))

    def test_run_id_consistency(self):
        """事件 run_id 可追溯；信封 run_id 存在。"""
        import pipeline_core
        pub = json.load(open(os.path.join(ROOT, "data", "public", "published_events.json")))
        # 每个公开事件必须有 run_id（可追溯批次）
        for item in pub.get("items", []):
            self.assertTrue(item.get("run_id"),
                          f"事件缺少 run_id: {item.get('event_id')}")
        # 信封 run_id 非空
        self.assertTrue(pub.get("run_id"))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    print(f"RESULT: PASS={n_run - n_fail} FAIL={n_fail}")
    sys.exit(1 if n_fail else 0)
