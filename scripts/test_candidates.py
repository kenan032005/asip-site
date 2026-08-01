#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""候选新源可用性测试 - 第二批。"""
import sys
sys.path.insert(0, "scripts/collectors")
from base import fetch_text, parse_feed

candidates = [
    # 乍得
    ("chad_ledo", "https://ledo.td/feed/", "Le Droit Tchad"),
    ("chad_tchadinfos2", "https://tchadinfos.com/feed/", "Tchadinfos(fallback)"),
    ("chad_ondjamena", "https://ondjamena.com/feed/", "OnDjamena"),
    ("chad_tchadmatin", "https://tchadmatin.com/feed/", "TchadMatin"),
    # 尼日尔
    ("niger_planeteniger", "https://planeteniger.com/feed/", "PlaneteNiger"),
    ("niger_nigerdiaspora2", "https://www.nigerdiaspora.net/feed/", "NigerDiaspora"),
    ("niger_ledebloir", "https://www.ledebloir.com/feed/", "LeDebloir Niger"),
    ("niger_legerbe", "https://legerbe.com/feed/", "LeGerbe Niger"),
    # 区域/国际
    ("intl_africanews", "https://www.africanews.com/rss/", "AfricaNews"),
    ("intl_voaafrique2", "https://www.voaafrique.com/api/ytqwivteqz", "VOA Afrique"),
    ("intl_france24_afrique", "https://www.france24.com/fr/afrique/rss", "France24 Afrique"),
    ("intl_jeuneafrique", "https://www.jeuneafrique.com/rss/rss-news.xml", "JeuneAfrique"),
    ("intl_humanitarian", "https://www.thenewhumanitarian.org/rss.xml", "TheNewHumanitarian"),
]
for sid, url, name in candidates:
    text, err = fetch_text(url)
    if err:
        print(f"  X {sid:24s} {name:20s} ERR: {type(err).__name__} {str(err)[:40]}")
        continue
    items = parse_feed(text)
    if items:
        print(f"  OK {sid:24s} {name:20s} items={len(items)} first={items[0]['title'][:35]}")
    else:
        print(f"  WARN {sid:24s} {name:20s} no-articles")
