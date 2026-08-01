#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TchadOne 完整判定分析。"""
import sys
sys.path.insert(0, "scripts/collectors")
from registry import SourceRegistry, ArticleDiscoverer
from framework import ContentExtractor, fetch_page
from country_runner import identify_country, load_country_cfg, relevance_stage1

reg = SourceRegistry()
src = [s for s in reg.enabled() if s["source_id"] == "chad_tchadone"][0]
d = ArticleDiscoverer(reg)
arts, errs = d.discover(src)
cfg = load_country_cfg("chad")
print(f"TchadOne 发现 {len(arts)} 条")
for a in arts[:10]:
    text, err, status = fetch_page(a["url"])
    ext = ContentExtractor({}).extract(text, a["url"])
    blob = a["title"] + " " + ext["body"][:800] + " " + a["summary"]
    cid = identify_country(blob, cfg)
    rel, score, m, e = relevance_stage1(blob)
    dec = cid["decision"]
    if dec != "chad":
        why = "country_mismatch"
    elif rel is None:
        why = "weak"
    elif rel is False:
        why = "no"
    else:
        why = "PUBLISH"
    print(f"  [{why:16s}] q={ext['quality'][:12]} {a['title'][:48]}")
