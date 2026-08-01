#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为现有来源补充 HTML 栏目页 URL（category_urls）。"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "sources.json")

with open(PATH, "r", encoding="utf-8") as f:
    doc = json.load(f)

CATEGORY_URLS = {
    "chad_lepaystchad": ["https://lepaystchad.com/category/actualite/"],
    "chad_journaldutchad": ["https://journaldutchad.com/category/securite/"],
    "niger_anp": ["https://anp.ne/category/actualite/"],
    "niger_studiokalangou": ["https://www.studiokalangou.org/category/actualite/"],
    "niger_journalduniger": ["https://www.journalduniger.com/category/actualite/"],
    "niger_nigerinter": ["https://nigerinter.com/category/actualite/"],
}

updated = 0
for s in doc["sources"]:
    sid = s.get("source_id", "")
    if sid in CATEGORY_URLS:
        lp = s.setdefault("legacy_payload", {})
        lp["category_urls"] = CATEGORY_URLS[sid]
        updated += 1

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)

print(f"更新 {updated} 个来源的 category_urls")
# 统计
chad_html = [s["source_id"] for s in doc["sources"]
             if s.get("legacy_payload", {}).get("category_urls")
             and s.get("legacy_payload", {}).get("country") == "乍得"]
niger_html = [s["source_id"] for s in doc["sources"]
              if s.get("legacy_payload", {}).get("category_urls")
              and s.get("legacy_payload", {}).get("country") == "尼日尔"]
print(f"乍得 HTML 栏目页来源: {len(chad_html)}")
print(f"尼日尔 HTML 栏目页来源: {len(niger_html)}")
