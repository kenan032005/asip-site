#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""向 data/sources.json 新增来源（幂等）。"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "sources.json")

with open(PATH, "r", encoding="utf-8") as f:
    doc = json.load(f)

existing = {s["source_id"] for s in doc["sources"]}

NEW_SOURCES = [
    # ── 乍得新增 ──
    {
        "source_id": "chad_lepaystchad",
        "source_name": "Le Pays Tchad",
        "source_type": "local_media",
        "source_reliability_tier": "tier_2",
        "country_scope": ["乍得"],
        "language": ["fr"],
        "enabled": True,
        "tested": True,
        "url": "https://lepaystchad.com/",
        "notes": "乍得当地媒体，RSS 可用（已实测 200）",
        "legacy_payload": {
            "source_id": "chad_lepaystchad", "name": "Le Pays Tchad", "country": "乍得",
            "url": "https://lepaystchad.com/", "language": "法语",
            "source_type": "local_media", "source_position": "local_media",
            "collection_method": "rss", "feed_url": "https://lepaystchad.com/feed/",
            "category_urls": [], "query": "", "domain": "", "enabled": True,
            "tested": True, "lead_only": False, "requires_api": False,
            "last_success_at": "2026-08-01T16:00:00+08:00", "last_failure_at": "",
            "failure_count": 0, "status": "active",
            "notes": "乍得当地媒体，RSS 可用（已实测 200）",
        },
    },
    # ── 尼日尔新增 ──
    {
        "source_id": "niger_sahelien",
        "source_name": "Sahelien",
        "source_type": "regional_media",
        "source_reliability_tier": "tier_2",
        "country_scope": ["尼日尔"],
        "language": ["fr"],
        "enabled": True,
        "tested": True,
        "url": "https://sahelien.com/",
        "notes": "萨赫勒区域媒体（含尼日尔），RSS 可用（已实测 200）",
        "legacy_payload": {
            "source_id": "niger_sahelien", "name": "Sahelien", "country": "尼日尔",
            "url": "https://sahelien.com/", "language": "法语",
            "source_type": "regional_media", "source_position": "regional_media",
            "collection_method": "rss", "feed_url": "https://sahelien.com/feed/",
            "category_urls": [], "query": "", "domain": "", "enabled": True,
            "tested": True, "lead_only": False, "requires_api": False,
            "last_success_at": "2026-08-01T16:00:00+08:00", "last_failure_at": "",
            "failure_count": 0, "status": "active",
            "notes": "萨赫勒区域媒体（含尼日尔），RSS 可用（已实测 200）",
        },
    },
    # ── 国际区域来源（乍得 + 尼日尔各一份映射，事件国过滤）──
    {
        "source_id": "intl_rfi_afrique_chad",
        "source_name": "RFI Afrique (Chad)",
        "source_type": "international",
        "source_reliability_tier": "tier_1",
        "country_scope": ["乍得"],
        "language": ["fr"],
        "enabled": True,
        "tested": True,
        "url": "https://www.rfi.fr/fr/afrique",
        "notes": "国际媒体非洲专题，RSS 可用（已实测 200）；事件国识别过滤",
        "legacy_payload": {
            "source_id": "intl_rfi_afrique_chad", "name": "RFI Afrique (Chad)", "country": "乍得",
            "url": "https://www.rfi.fr/fr/afrique", "language": "法语",
            "source_type": "international", "source_position": "international",
            "collection_method": "rss", "feed_url": "https://www.rfi.fr/fr/afrique/rss",
            "category_urls": [], "query": "", "domain": "rfi.fr", "enabled": True,
            "tested": True, "lead_only": False, "requires_api": False,
            "last_success_at": "2026-08-01T16:00:00+08:00", "last_failure_at": "",
            "failure_count": 0, "status": "active",
            "notes": "国际媒体非洲专题，事件国识别过滤",
        },
    },
    {
        "source_id": "intl_rfi_afrique_niger",
        "source_name": "RFI Afrique (Niger)",
        "source_type": "international",
        "source_reliability_tier": "tier_1",
        "country_scope": ["尼日尔"],
        "language": ["fr"],
        "enabled": True,
        "tested": True,
        "url": "https://www.rfi.fr/fr/afrique",
        "notes": "国际媒体非洲专题，RSS 可用（已实测 200）；事件国识别过滤",
        "legacy_payload": {
            "source_id": "intl_rfi_afrique_niger", "name": "RFI Afrique (Niger)", "country": "尼日尔",
            "url": "https://www.rfi.fr/fr/afrique", "language": "法语",
            "source_type": "international", "source_position": "international",
            "collection_method": "rss", "feed_url": "https://www.rfi.fr/fr/afrique/rss",
            "category_urls": [], "query": "", "domain": "rfi.fr", "enabled": True,
            "tested": True, "lead_only": False, "requires_api": False,
            "last_success_at": "2026-08-01T16:00:00+08:00", "last_failure_at": "",
            "failure_count": 0, "status": "active",
            "notes": "国际媒体非洲专题，事件国识别过滤",
        },
    },
    {
        "source_id": "intl_bbc_afrique_chad",
        "source_name": "BBC Afrique (Chad)",
        "source_type": "international",
        "source_reliability_tier": "tier_1",
        "country_scope": ["乍得"],
        "language": ["fr"],
        "enabled": True,
        "tested": True,
        "url": "https://www.bbc.com/afrique",
        "notes": "国际媒体非洲专题，RSS 可用（已实测 200）；事件国识别过滤",
        "legacy_payload": {
            "source_id": "intl_bbc_afrique_chad", "name": "BBC Afrique (Chad)", "country": "乍得",
            "url": "https://www.bbc.com/afrique", "language": "法语",
            "source_type": "international", "source_position": "international",
            "collection_method": "rss", "feed_url": "https://feeds.bbci.co.uk/afrique/rss.xml",
            "category_urls": [], "query": "", "domain": "bbc.com", "enabled": True,
            "tested": True, "lead_only": False, "requires_api": False,
            "last_success_at": "2026-08-01T16:00:00+08:00", "last_failure_at": "",
            "failure_count": 0, "status": "active",
            "notes": "国际媒体非洲专题，事件国识别过滤",
        },
    },
    {
        "source_id": "intl_bbc_afrique_niger",
        "source_name": "BBC Afrique (Niger)",
        "source_type": "international",
        "source_reliability_tier": "tier_1",
        "country_scope": ["尼日尔"],
        "language": ["fr"],
        "enabled": True,
        "tested": True,
        "url": "https://www.bbc.com/afrique",
        "notes": "国际媒体非洲专题，RSS 可用（已实测 200）；事件国识别过滤",
        "legacy_payload": {
            "source_id": "intl_bbc_afrique_niger", "name": "BBC Afrique (Niger)", "country": "尼日尔",
            "url": "https://www.bbc.com/afrique", "language": "法语",
            "source_type": "international", "source_position": "international",
            "collection_method": "rss", "feed_url": "https://feeds.bbci.co.uk/afrique/rss.xml",
            "category_urls": [], "query": "", "domain": "bbc.com", "enabled": True,
            "tested": True, "lead_only": False, "requires_api": False,
            "last_success_at": "2026-08-01T16:00:00+08:00", "last_failure_at": "",
            "failure_count": 0, "status": "active",
            "notes": "国际媒体非洲专题，事件国识别过滤",
        },
    },
    {
        "source_id": "intl_france24_afrique_chad",
        "source_name": "France24 Afrique (Chad)",
        "source_type": "international",
        "source_reliability_tier": "tier_1",
        "country_scope": ["乍得"],
        "language": ["fr"],
        "enabled": True,
        "tested": True,
        "url": "https://www.france24.com/fr/afrique/",
        "notes": "国际媒体非洲专题，RSS 可用（已实测 200）；事件国识别过滤",
        "legacy_payload": {
            "source_id": "intl_france24_afrique_chad", "name": "France24 Afrique (Chad)", "country": "乍得",
            "url": "https://www.france24.com/fr/afrique/", "language": "法语",
            "source_type": "international", "source_position": "international",
            "collection_method": "rss", "feed_url": "https://www.france24.com/fr/afrique/rss",
            "category_urls": [], "query": "", "domain": "france24.com", "enabled": True,
            "tested": True, "lead_only": False, "requires_api": False,
            "last_success_at": "2026-08-01T16:00:00+08:00", "last_failure_at": "",
            "failure_count": 0, "status": "active",
            "notes": "国际媒体非洲专题，事件国识别过滤",
        },
    },
    {
        "source_id": "intl_france24_afrique_niger",
        "source_name": "France24 Afrique (Niger)",
        "source_type": "international",
        "source_reliability_tier": "tier_1",
        "country_scope": ["尼日尔"],
        "language": ["fr"],
        "enabled": True,
        "tested": True,
        "url": "https://www.france24.com/fr/afrique/",
        "notes": "国际媒体非洲专题，RSS 可用（已实测 200）；事件国识别过滤",
        "legacy_payload": {
            "source_id": "intl_france24_afrique_niger", "name": "France24 Afrique (Niger)", "country": "尼日尔",
            "url": "https://www.france24.com/fr/afrique/", "language": "法语",
            "source_type": "international", "source_position": "international",
            "collection_method": "rss", "feed_url": "https://www.france24.com/fr/afrique/rss",
            "category_urls": [], "query": "", "domain": "france24.com", "enabled": True,
            "tested": True, "lead_only": False, "requires_api": False,
            "last_success_at": "2026-08-01T16:00:00+08:00", "last_failure_at": "",
            "failure_count": 0, "status": "active",
            "notes": "国际媒体非洲专题，事件国识别过滤",
        },
    },
]

added = 0
for ns in NEW_SOURCES:
    if ns["source_id"] in existing:
        continue
    doc["sources"].append(ns)
    existing.add(ns["source_id"])
    added += 1

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)

print(f"新增来源: {added}")
print(f"总来源数: {len(doc['sources'])}")
