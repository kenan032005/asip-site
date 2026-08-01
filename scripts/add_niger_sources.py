#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""向 sources.json 补充尼日尔替补来源（Ouestaf / AfricaNews）。"""
import json

path = "data/sources.json"
doc = json.load(open(path, encoding="utf-8"))
existing = {s["source_id"] for s in doc["sources"]}

NEW = [
    {
        "source_id": "niger_ouestaf",
        "source_name": "Ouestaf",
        "source_type": "regional_media",
        "source_reliability_tier": "tier_2",
        "country_scope": ["尼日尔"],
        "language": ["fr"],
        "enabled": True, "tested": True,
        "url": "https://ouestaf.com/",
        "notes": "萨赫勒区域媒体（含尼日尔），RSS 可用",
        "legacy_payload": {
            "source_id": "niger_ouestaf", "name": "Ouestaf", "country": "尼日尔",
            "url": "https://ouestaf.com/", "language": "法语",
            "source_type": "regional_media", "source_position": "regional_media",
            "collection_method": "rss", "feed_url": "https://ouestaf.com/feed/",
            "category_urls": [], "query": "", "domain": "ouestaf.com",
            "enabled": True, "tested": True, "lead_only": False, "requires_api": False,
            "last_success_at": "", "last_failure_at": "", "failure_count": 0,
            "status": "active", "notes": "萨赫勒区域媒体（含尼日尔），RSS 可用",
        },
    },
    {
        "source_id": "niger_africanews",
        "source_name": "AfricaNews (Niger)",
        "source_type": "international",
        "source_reliability_tier": "tier_1",
        "country_scope": ["尼日尔"],
        "language": ["fr"],
        "enabled": True, "tested": True,
        "url": "https://www.africanews.com/",
        "notes": "国际媒体非洲专题，事件国识别过滤",
        "legacy_payload": {
            "source_id": "niger_africanews", "name": "AfricaNews (Niger)", "country": "尼日尔",
            "url": "https://www.africanews.com/", "language": "法语",
            "source_type": "international", "source_position": "international",
            "collection_method": "rss", "feed_url": "https://www.africanews.com/feed/",
            "category_urls": [], "query": "", "domain": "africanews.com",
            "enabled": True, "tested": True, "lead_only": False, "requires_api": False,
            "last_success_at": "", "last_failure_at": "", "failure_count": 0,
            "status": "active", "notes": "国际媒体非洲专题，事件国识别过滤",
        },
    },
]

added = 0
for ns in NEW:
    if ns["source_id"] in existing:
        continue
    doc["sources"].append(ns)
    existing.add(ns["source_id"])
    added += 1
json.dump(doc, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("新增:", added, "| 总来源:", len(doc["sources"]))
