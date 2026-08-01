#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTML栏目页发现 + 详情页正文提取冒烟测试。"""
import sys
sys.path.insert(0, "scripts")
sys.path.insert(0, "scripts/collectors")

from registry import ArticleDiscoverer
from framework import ContentExtractor, fetch_page

source = {
    "source_id": "chad_tchadinfos",
    "source_name": "Tchadinfos",
    "source_country": "乍得",
    "source_type": "local_media",
    "language": "fr",
    "discovery_type": "html_listing",
    "feed_url": "",
    "listing_urls": ["https://tchadinfos.com/category/securite/"],
    "base_url": "https://tchadinfos.com/",
    "max_items": 8,
    "extractor_profile": {},
    "enabled": True,
}

discoverer = ArticleDiscoverer(None)
arts, errs = discoverer.discover(source)
print(f"HTML 栏目页发现: {len(arts)} 条, 错误: {errs}")
for d in arts[:6]:
    print(f"  - {d['title'][:50]} | {d['url'][:60]}")
    text, err, status = fetch_page(d["url"])
    if err:
        print(f"    FETCH ERR: {err}")
        continue
    ext = ContentExtractor({}).extract(text, d["url"])
    print(f"    → quality={ext['quality']} words={ext['word_count']} method={ext['method']}")
