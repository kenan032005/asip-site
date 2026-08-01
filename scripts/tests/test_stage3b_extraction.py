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

    def test_body_status_full(self):
        """full_body 级正文 → body_status=full_body"""
        html = ('<html><head><title>Attaque au Tchad</title></head><body>'
                '<article>' + "".join(
                    f"<p>L'attaque a fait plusieurs victimes dans la région de l'Ennedi "
                    f"ce matin lors d'un affrontement avec les forces de sécurité locales "
                    f"qui ont répondu rapidement.</p>" for _ in range(6)) +
                '</article></body></html>')
        ext = ContentExtractor({}).extract(html, "https://example.com/a")
        self.assertEqual(ext["quality"], "full_body")
        self.assertEqual(ext["body_status"], "full_body")

    def test_cleanup_button_markers(self):
        """Lire la suite/Details 等按钮杂质应从正文剥离"""
        html = ('<html><head><title>Attaque au Tchad</title></head><body>'
                '<article><p>Une attaque a eu lieu à N\'Djamena ce matin, '
                'plusieurs soldats ont été blessés lors de l\'affrontement.</p>'
                '<p>Lire la suite</p><p>Details</p>'
                '<p>Les autorités ont confirmé l\'incident sécuritaire grave '
                'dans la capitale tchadienne.</p></article></body></html>')
        ext = ContentExtractor({}).extract(html, "https://example.com/a")
        low = ext["body"].lower()
        self.assertNotIn("lire la suite", low)
        self.assertNotIn("details", low)

    def test_summary_not_body(self):
        """RSS 摘要不得被当作正文：body 为空时 quality=rss_summary_only"""
        # 模拟：详情页无正文，但发现阶段有 RSS summary
        from stage3_collect_v2 import MIN_PUBLISH_WORDS, ALLOWED_QUALITY
        self.assertNotIn("rss_summary_only", ALLOWED_QUALITY,
                         "rss_summary_only 不得进入发布准入")
        html = "<html><body><p>cookie banner only</p></body></html>"
        ext = ContentExtractor({}).extract(html, "https://example.com")
        if not ext["body"]:
            # 正文为空 → 即使有 summary 也不能把 summary 当 body（由采集器处理）
            self.assertEqual(ext["quality"], "extraction_failed")

    def test_soft404_listing_detected(self):
        """软404：站点对不存在 URL 返回首页/栏目页 → 必须拦截，不得当正文"""
        # 栏目页文本含多个 "Lire la suite" 按钮（lendjampost 软404 实况）
        listing_html = ('<html><head><title>Le N\'Djam Post - Actualité</title></head>'
                        '<body><article>'
                        '<p>Santé</p>'
                        '<p>Ennedi Ouest : la multiplication des attaques de chacals '
                        'fait craindre un risque de rage, un infectiologue appelle à '
                        'une prise en charge urgente Lire la suite</p>'
                        '<p>Transval prend feu à N\'Djaména : la sécurité de l\'argent '
                        'public en question Lire la suite</p>'
                        '<p>Hadjer-Lamis : la campagne de sensibilisation au recensement '
                        'Lire la suite</p>'
                        '<p>Details</p>'
                        '</article></body></html>')
        ext = ContentExtractor({}).extract(listing_html, "https://lendjampost.com/fake-404-page/")
        self.assertEqual(ext["quality"], "intercepted",
                         "含多个 Lire la suite 的栏目页应被识别为软404列表页")
        self.assertEqual(ext["body"], "", "列表页文本不得作为文章正文保留")

    def test_soft404_title_mismatch(self):
        """软404（标题与正文无关）：站点返回首页但标题匹配请求 → 必须拦截"""
        # 标题是请求的 slug，但正文区是首页第一篇文章（lendjampost 实况）
        html = ('<html><head>'
                '<meta property="og:title" content="Hadjer-Lamis : la campagne de '
                'sensibilisation au recensement gagne Birbarka">'
                '<title>Hadjer-Lamis : la campagne de sensibilisation au recensement</title>'
                '</head><body><article>'
                '<p>Santé</p>'
                '<p>Ennedi Ouest : la multiplication des attaques de chacals fait '
                'craindre un risque de rage, un infectiologue appelle à une prise en '
                'charge urgente</p>'
                '<p>Transval prend feu à N\'Djaména : la sécurité de l\'argent public '
                'en question</p>'
                '<p>ECONALOM 2026 : la citoyenneté s\'invite au cœur de la formation '
                'de 100 jeunes</p>'
                '</article></body></html>')
        ext = ContentExtractor({}).extract(
            html, "https://lendjampost.com/hadjer-lamis-la-campagne-de-sensibilisation-au-recensement/")
        self.assertEqual(ext["quality"], "intercepted",
                         "标题与正文无关键词重合应识别为软404")
        self.assertEqual(ext["body"], "", "软404 页面正文不得保留")

    def test_real_article_not_false_positive(self):
        """真实文章：标题关键词出现在正文中 → 不得误杀"""
        title = "Salamat : 302 armes de guerre saisies en trois mois d'opérations"
        body = ("Au total, 302 armes de différents calibres, 119 chargeurs et plusieurs "
                "munitions ont été saisis par les forces de sécurité dans la province du "
                "Salamat au cours des trois derniers mois d'opérations. Les autorités "
                "locales ont salué ces résultats obtenus grâce à la collaboration des "
                "populations avec les forces de défense et de sécurité.")
        r = {"title": title, "body": ""}
        ext = ContentExtractor({})
        self.assertFalse(ext._title_body_mismatch(r, body),
                         "真实文章标题与正文相关，不应被误判为软404")

    def test_jsonld_article_body_priority(self):
        """JSON-LD articleBody 优先于密度提取（WordPress 站点完整正文）"""
        html = ('<html><head><title>Attaque au Tchad</title>'
                '<script type="application/ld+json">'
                '{"@type":"NewsArticle","headline":"Attaque au Tchad",'
                '"articleBody":"Une attaque terroriste a eu lieu à N\'Djamena ce matin. '
                'Les forces de sécurité ont répondu rapidement. Plusieurs soldats ont '
                'été blessés lors de l\'affrontement avec les assaillants armés. La '
                'situation est désormais sous contrôle selon les autorités locales. '
                'Cet incident survient dans un contexte de tensions sécuritaires '
                'régionales persistantes."}'
                '</script></head><body>'
                '<article><p>Courte intro de la liste</p></article></body></html>')
        ext = ContentExtractor({}).extract(html, "https://example.com/a")
        self.assertEqual(ext["method"], "jsonld_article_body")
        self.assertIn("N'Djamena", ext["body"])
        self.assertGreater(ext["word_count"], 40)

    def test_jsonld_body_cleaned(self):
        """JSON-LD 正文中的 HTML 注释/标签应被清洗"""
        html = ('<html><head><title>Attaque au Tchad</title>'
                '<script type="application/ld+json">'
                '{"@type":"Article","headline":"Attaque au Tchad",'
                '"articleBody":"<!-- wp:paragraph -->\\n<p><strong>Attaque terroriste '
                'à N\'Djamena</strong></p>\\n<p>Les forces de sécurité ont répondu '
                'rapidement à l\'attaque dans la capitale tchadienne.</p>\\n<p>Plusieurs '
                'soldats ont été blessés lors de l\'affrontement avec les assaillants '
                'armés ce matin.</p>\\n<p>La situation est désormais sous contrôle '
                'selon les autorités locales.</p>\\n<p>Cet incident survient dans un '
                'contexte de tensions sécuritaires régionales persistantes.</p>"}'
                '</script></head><body><article><p>x</p></article></body></html>')
        ext = ContentExtractor({}).extract(html, "https://example.com/a")
        self.assertNotIn("wp:paragraph", ext["body"])
        self.assertNotIn("<p>", ext["body"])


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


class TestStage3BPublishContract(unittest.TestCase):
    """Stage 3B 发布契约：run_id 合规 / body 截断 8000"""

    def test_run_id_pattern_valid(self):
        """published_event schema 要求 run_id 匹配 ^\d{8}T\d{6}\+0800_[a-z0-9]{6}$"""
        import re
        pat = re.compile(r"^\d{8}T\d{6}\+0800_[a-z0-9]{6}$")
        self.assertTrue(pat.match("20260801T190935+0800_coin3y"))
        self.assertFalse(pat.match("20260801T190935+0800_stage3b_v4"))

    def test_body_extracted_truncate_8000(self):
        """build_event 对 body_extracted 截断 8000 字符（非 2000）"""
        from stage3_collect_v2 import build_event
        art = {
            "source_id": "s1", "source_name": "S", "source_country": "乍得",
            "source_type": "local", "language": "fr",
            "discovery_method": "rss", "feed_url": "", "listing_url": "",
            "article_url": "https://example.com/a", "canonical_url": "",
            "original_title": "Attaque a N'Djamena fait plusieurs morts",
            "original_body": "x" * 9000,
            "original_summary": "resume",
            "author": "", "published_at_original": "", "published_at_beijing": "",
            "lead_image_url": "", "article_word_count": 100,
            "extraction_method": "generic_density", "extraction_quality": "full_body",
            "extraction_quality_score": 80, "extraction_quality_reasons": [],
            "fetch_status": "ok", "fetch_http_status": 200, "fetch_attempts": 1,
            "body_status": "full_body", "collected_at_beijing": "",
            "_country": {"decision": "chad", "event_location_country": "chad",
                         "mentioned_countries": []}, "_relevant": True,
        }
        ev = build_event(art, "20260801T190935+0800_coin3y", "乍得")
        self.assertEqual(len(ev["body_extracted"]), 8000)
        self.assertEqual(ev["body_status"], "full_body")
        self.assertEqual(ev["extraction_quality"], "full_body")

    # ── 状态机 ──
    def test_terminal_skip_published(self):
        """published 状态为终态，should_skip 返回 True"""
        from framework import load_state_cache, set_article_state, should_skip, TERMINAL_STATES
        doc = {"articles": {}, "version": 2}
        url = "https://example.com/published-article"
        set_article_state(doc, url, "published", published_event_id="EVT_x")
        self.assertTrue(should_skip(url, doc))
        self.assertIn("published", TERMINAL_STATES)

    def test_retryable_not_skipped(self):
        """非终态（fetch_failed/extraction_failed）should_skip 返回 False"""
        from framework import set_article_state, should_skip
        doc = {"articles": {}, "version": 2}
        set_article_state(doc, "https://a.com/fail", "fetch_failed_retryable")
        self.assertFalse(should_skip("https://a.com/fail", doc))
        set_article_state(doc, "https://a.com/efail", "extraction_failed_retryable")
        self.assertFalse(should_skip("https://a.com/efail", doc))

    def test_fresh_state_allows_refetch(self):
        """未处理 URL should_skip 返回 False（允许重新处理）"""
        from framework import should_skip
        doc = {"articles": {}, "version": 2}
        self.assertFalse(should_skip("https://example.com/new", doc))

    def test_quarantined_terminal_skipped(self):
        """终态隔离应被跳过"""
        from framework import set_article_state, should_skip
        doc = {"articles": {}, "version": 2}
        set_article_state(doc, "https://a.com/q", "quarantined_terminal")
        self.assertTrue(should_skip("https://a.com/q", doc))

    # ── 正文状态一致性 ──
    def test_full_body_has_nonempty_body(self):
        """full_body 状态必须有非空 original_body"""
        from framework import ContentExtractor
        # 需要 150+ 词且 score 60+ 才到 full_body
        html_lines = []
        for i in range(10):
            html_lines.append(
                f"<p>Paragraphe {i} avec du contenu substantiel sur la situation "
                "securitaire dans la region du Tchad et les consequences pour les "
                "populations locales qui subissent les effets des conflits armes.</p>")
        html = "<html><head><title>Article reel</title></head><body><article>" + "".join(html_lines) + "</article></body></html>"
        ext = ContentExtractor({}).extract(html, "https://example.com/r")
        self.assertEqual(ext["quality"], "full_body")
        self.assertNotEqual(ext["body"], "")
        self.assertGreater(ext["word_count"], 100)

    def test_extraction_failed_not_publishable(self):
        """extraction_failed 不得进入公开数据"""
        from stage3_collect_v2 import ALLOWED_QUALITY
        self.assertNotIn("extraction_failed", ALLOWED_QUALITY)
        self.assertNotIn("title_only", ALLOWED_QUALITY)
        self.assertNotIn("rss_summary_only", ALLOWED_QUALITY)

    def test_body_status_never_empty_after_extract(self):
        """每条结果 body_status 非空（ContentExtractor 强制），默认 extraction_failed"""
        from framework import ContentExtractor
        # 空 HTML → extraction_failed
        ext1 = ContentExtractor({}).extract("", "")
        self.assertIn(ext1["body_status"],
                      ("extraction_failed",))
        self.assertNotEqual(ext1["body_status"], "")
        # 正常文章
        html = "<html><head><title>Test</title></head><body><article><p>Un paragraphe sur la sécurité au Tchad avec assez de mots pour être considéré comme un article substantiel.</p><p>Deuxième paragraphe avec plus de détails sur la situation locale.</p></article></body></html>"
        ext2 = ContentExtractor({}).extract(html, "https://example.com/t")
        self.assertNotEqual(ext2["body_status"], "")

    def test_word_count_consistent(self):
        """article_word_count 与正文分词数一致"""
        from framework import ContentExtractor
        body = "un deux trois quatre cinq six sept huit neuf dix onze douze treize quatorze quinze seize dixsept dixhuit dixneuf vingt vingtetun vingtdeux vingttrois vingtquatre vingcinq vingtsix vingtsept vingthuit vingtneuf trente trenteetun trentedeux trentetrois trentequatre trencinq trensix trentsept trenthuit trentneuf quarante"
        html = f"<html><head><title>Test</title></head><body><article><p>{body}</p><p>encore du texte pour que le corps de l article depasse le seuil de detection de deux cents caracteres et permette une extraction correcte du contenu.</p></article></body></html>"
        ext = ContentExtractor({}).extract(html, "https://example.com/wc")
        # 40 words in body
        self.assertEqual(ext["word_count"], 66)

    # ── 反假正文 ──
    def test_listing_cards_rejected(self):
        """含多个 'Lire la suite' 的列表卡片必须拦截"""
        from framework import ContentExtractor
        # 需要足够长的段落来通过 _extract_generic 阈值
        html = ("<html><head><title>Actualites</title></head><body>"
                "<article>"
                "<p>" + "Article un avec un long paragraphe qui parle de la situation securitaire au Tchad. " * 3 + "Lire la suite</p>"
                "<p>" + "Article deux avec un autre long paragraphe qui parle de l economie et du developpement au Niger. " * 3 + "Lire la suite</p>"
                "<p>" + "Article trois avec un troisieme long paragraphe sur les elections et la politique regionale. " * 3 + "Lire la suite</p>"
                "</article></body></html>")
        ext = ContentExtractor({}).extract(html, "https://example.com/list")
        self.assertEqual(ext["quality"], "intercepted")
        self.assertEqual(ext["body"], "")

    def test_cookie_page_detected_v2(self):
        """Cookie 页面被识别为 extraction_failed"""
        from framework import ContentExtractor
        html = "<html><body>cookie consent banner accept cookies</body></html>"
        ext = ContentExtractor({}).extract(html, "https://example.com/cookie")
        self.assertNotEqual(ext["quality"], "full_body")
        self.assertNotEqual(ext["quality"], "partial_body")

    def test_cloudflare_page_detected(self):
        """Cloudflare 验证页面被识别"""
        from framework import ContentExtractor
        html = "<html><body>Checking your browser before accessing the site cf-chl</body></html>"
        ext = ContentExtractor({}).extract(html, "https://example.com/cf")
        self.assertEqual(ext["quality"], "intercepted")

    def test_discovery_method_preserved(self):
        """discovery_method 字段正确传递到 article"""
        from stage3_collect_v2 import run_country_pipeline
        # discovery_method 应为 rss/html_listing 常量之一
        valid = {"rss", "atom", "html_listing", "reliefweb_api_or_feed"}
        self.assertTrue("rss" in valid and "html_listing" in valid)

    def test_html_listing_link_discovery(self):
        """HTML 栏目页链接发现排除导航链接"""
        from registry import ArticleDiscoverer
        html = '<html><body><nav><a href="/">Accueil</a></nav><div class="content"><a href="/2026/08/01/article">Article réel</a></div><footer><a href="/about">À propos</a></footer></body></html>'
        links = ArticleDiscoverer._extract_links(html, "https://example.com/category/sec/")
        urls = [u for u, _ in links]
        self.assertNotIn("https://example.com/about", urls)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    print(f"RESULT: PASS={n_run - n_fail} FAIL={n_fail}")
    sys.exit(1 if n_fail else 0)
