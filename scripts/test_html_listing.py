#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTML 栏目页发现能力测试。"""
import sys
sys.path.insert(0, "scripts/collectors")
from base import fetch_text
from html_list_collector import HTMLListCollector

urls = [
    ("tchadinfos_securite", "https://tchadinfos.com/category/securite/"),
    ("alwihda_tchad", "https://www.alwihdainfo.com/tchad/"),
    ("rfi_afrique", "https://www.rfi.fr/fr/afrique"),
    ("bbc_afrique", "https://www.bbc.com/afrique"),
    ("france24_afrique", "https://www.france24.com/fr/afrique/"),
    ("sahelien", "https://sahelien.com/"),
]
for name, url in urls:
    col = HTMLListCollector({"url": url, "language": "fr"})
    arts = col.run()
    errs = col.errors if hasattr(col, "errors") else []
    print(f"  {'OK' if arts else 'ERR'} {name:20s} items={len(arts)} errors={len(errs)}")
    for a in arts[:2]:
        print(f"      - {a.get('title','')[:55]} | {a.get('url','')[:55]}")
