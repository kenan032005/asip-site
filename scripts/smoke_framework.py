#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""framework 冒烟测试。"""
import sys
sys.path.insert(0, "scripts")
sys.path.insert(0, "scripts/collectors")

from registry import SourceRegistry, ArticleDiscoverer, parse_rss_atom
from framework import ContentExtractor, fetch_page, validate_url

# 1) Registry
reg = SourceRegistry()
print(f"注册表: {len(reg.all())} 来源, 启用 {len(reg.enabled())}")
for cn in ("乍得", "尼日尔"):
    print(f"  {cn}: {len(reg.by_country(cn))} 启用")

# 2) RSS 解析测试
rss_xml = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>Attaque au Tchad</title><link>https://example.com/a</link>
<description>Attaque terroriste à N'Djamena</description>
<pubDate>Sat, 01 Aug 2026 10:00:00 GMT</pubDate></item>
<item><title>Dup</title><link>https://example.com/a</link>
<description>dup</description><pubDate>Sat, 01 Aug 2026 11:00:00 GMT</pubDate></item>
</channel></rss>"""
items = parse_rss_atom(rss_xml)
print(f"\nRSS 解析: {len(items)} 条（去重后应为 1）")

# 3) 正文提取测试
html = """<html><head><title>Attaque au Tchad - Tchadinfos</title>
<meta property="og:title" content="Attaque au Tchad">
<meta property="og:image" content="https://example.com/img.jpg">
<meta property="article:published_time" content="2026-08-01T10:00:00Z">
</head><body><nav>Menu Accueil Contact</nav>
<article><p>Une attaque terroriste a eu lieu à N'Djamena ce matin.</p>
<p>Les forces de sécurité ont répondu à l'attaque dans la capitale tchadienne.</p>
<p>Plusieurs soldats ont été blessés lors de l'affrontement avec les assaillants.</p>
<p>La situation est sous contrôle selon les autorités locales.</p>
<p>Cet incident survient dans un contexte de tensions sécuritaires régionales.</p></article>
<footer>Copyright Tchadinfos</footer></body></html>"""
ext = ContentExtractor({}).extract(html, "https://tchadinfos.com/a")
print(f"正文提取: quality={ext['quality']} words={ext['word_count']} method={ext['method']}")
print(f"  标题: {ext['title'][:40]}")
print(f"  正文: {ext['body'][:80]}...")
print(f"  时间: {ext['published_original']}")
print(f"  图片: {ext['lead_image_url'][:40]}")

# 4) URL 安全校验
for u in ("https://127.0.0.1/admin", "file:///etc/passwd", "http://169.254.169.254/latest/meta-data",
          "https://tchadinfos.com/feed/", "https://example.com/article"):
    ok, reason = validate_url(u)
    print(f"URL 校验: {u[:45]:45s} ok={ok} ({reason})")
