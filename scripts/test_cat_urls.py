#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试更多 HTML 栏目页 URL 可用性。"""
import sys
sys.path.insert(0, "scripts/collectors")
from base import fetch_text

urls = [
    ("chad_lepaystchad", "https://lepaystchad.com/category/actualite/", "Le Pays Tchad 栏目"),
    ("chad_tachad", "https://www.tachad.com/category/securite/", "Tachad 栏目"),
    ("chad_lendjampost", "https://lendjampost.com/category/actualite/", "LNDJAM Post 栏目"),
    ("chad_journaldutchad", "https://journaldutchad.com/category/securite/", "Journal du Tchad 栏目"),
    ("chad_tchadone", "https://tchadone.com/category/actualite/", "TchadOne 栏目"),
    ("niger_anp", "https://anp.ne/category/actualite/", "ANP 栏目"),
    ("niger_lesahel", "https://www.lesahel.org/category/actualite/", "Le Sahel 栏目"),
    ("niger_studiokalangou", "https://www.studiokalangou.org/category/actualite/", "Studio Kalangou 栏目"),
    ("niger_journalduniger", "https://www.journalduniger.com/category/actualite/", "Journal du Niger 栏目"),
    ("niger_nigerinter", "https://nigerinter.com/category/actualite/", "Niger Inter 栏目"),
    ("niger_tamtaminfo", "https://tamtaminfo.com/category/actualite/", "Tamtaminfo 栏目"),
    ("niger_airinfo", "https://airinfoagadez.com/category/actualite/", "Aïr Info 栏目"),
]
for sid, url, name in urls:
    text, err = fetch_text(url)
    if err:
        print(f"  X {sid:24s} {name:18s} ERR: {str(err)[:40]}")
    else:
        nlinks = text.count("<a ") if text else 0
        print(f"  OK {sid:24s} {name:18s} links={nlinks}")
