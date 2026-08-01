#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精确程序化来源统计（从本轮真实运行记录 + 注册表生成，不手工计算）。"""
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
STATS = os.path.join(ROOT, "logs", "stage3_collection_stats.json")

sources = json.load(open(os.path.join(DATA, "sources.json"), encoding="utf-8"))["sources"]
stats_doc = json.load(open(STATS, encoding="utf-8"))
per_source = stats_doc.get("per_source", [])

# 运行记录索引（按 source_id）
run = {s["source_id"]: s for s in per_source}

# 注册表索引
reg = {}
for s in sources:
    lp = s.get("legacy_payload", {})
    sid = s.get("source_id", "")
    reg[sid] = {
        "source_name": s.get("source_name", lp.get("name", "")),
        "country": lp.get("country", s.get("country_scope", [""])[0] if s.get("country_scope") else ""),
        "source_type": lp.get("source_type", s.get("source_type", "")),
        "collection_method": lp.get("collection_method", ""),
        "enabled": lp.get("enabled", s.get("enabled", False)),
        "url": lp.get("url", s.get("url", "")),
        "feed_url": lp.get("feed_url", ""),
        "category_urls": lp.get("category_urls", []),
    }

# 健康审计结果（离线部分）
try:
    health = json.load(open(os.path.join(ROOT, "logs", "source_health.json"), encoding="utf-8"))
    health_map = {h["source_id"]: h.get("category", "") for h in health.get("sources", [])}
except Exception:
    health_map = {}

VALID_TYPES = {"local_media", "regional_media", "international", "official",
               "state_media", "un_humanitarian", "commentary"}


def country_of(sid):
    return reg.get(sid, {}).get("country", "")


def aggregate(country_cn):
    rows = []
    for sid in reg:
        if country_of(sid) != country_cn:
            continue
        r = reg[sid]
        rs = run.get(sid)
        attempted = rs is not None
        discovered = rs.get("discovered", 0) if rs else 0
        detail_fetch = rs.get("fetched", 0) if rs else 0
        full_body = rs.get("full_body", 0) if rs else 0
        partial_body = rs.get("partial_body", 0) if rs else 0
        summary_only = rs.get("summary_only", 0) if rs else 0
        extraction_failed = rs.get("extraction_failed", 0) if rs else 0
        published = rs.get("published", 0) if rs else 0
        quarantined = rs.get("quarantined", 0) if rs else 0

        method = r["collection_method"]
        # 健康分类
        hc = health_map.get(sid, "")
        if method == "gdelt_search":
            health_status = "not_implemented"
        elif not r["enabled"]:
            health_status = "disabled"
        elif hc == "permanently_broken":
            health_status = "permanently_broken"
        elif hc == "active_and_usable":
            health_status = "active_and_usable"
        elif hc:
            health_status = hc
        else:
            health_status = "unknown"

        # requires_javascript 判定：active 但无法提取正文，或栏目页 0 发现但有启用记录
        requires_js = False
        if method in ("rss", "reliefweb_api_or_feed"):
            if attempted and discovered > 0 and (full_body + partial_body) == 0:
                requires_js = True  # 有 Feed 但详情页无法提取

        rows.append({
            "source_id": sid,
            "source_name": r["source_name"],
            "country": country_cn,
            "source_type": r["source_type"] or "unknown",
            "discovery_method": method,
            "attempted": attempted,
            "articles_discovered": discovered,
            "detail_fetch_success_count": detail_fetch,
            "full_body_count": full_body,
            "partial_body_count": partial_body,
            "rss_summary_only_count": summary_only,
            "extraction_failed_count": extraction_failed,
            "published_count": published,
            "quarantined_count": quarantined,
            "final_health_status": health_status,
            "requires_javascript": requires_js,
        })
    return rows


def summarize(country_cn, rows):
    implemented = [r for r in rows if r["discovery_method"] != "gdelt_search"]
    enabled = [r for r in implemented if r["final_health_status"] != "disabled"]
    attempted = [r for r in enabled if r["attempted"]]
    successful_discovery = [r for r in attempted if r["articles_discovered"] > 0]
    successful_detail = [r for r in successful_discovery if r["detail_fetch_success_count"] > 0]
    successful_body = [r for r in successful_detail if (r["full_body_count"] + r["partial_body_count"]) > 0]
    rss_body = [r for r in successful_body if r["discovery_method"] in ("rss", "reliefweb_api_or_feed")]
    html_body = [r for r in successful_body if r["discovery_method"] == "html_listing"]
    # 正文成功来源（唯一 source_id）—— html+rss 双通道同源计一次
    unique_body = [r for r in successful_body]
    with_pub = [r for r in attempted if r["published_count"] > 0]
    temporarily_failed = [r for r in attempted
                          if r["final_health_status"] == "temporarily_unreachable"]
    perm_broken = [r for r in rows if r["final_health_status"] == "permanently_broken"]
    requires_js = [r for r in attempted if r["requires_javascript"]]
    not_impl = [r for r in rows if r["discovery_method"] == "gdelt_search"]

    # 稳定活跃来源：已实现+启用+本轮尝试+发现≥1+非永久失效+非requires_js
    stable = [r for r in successful_discovery
              if r["final_health_status"] != "permanently_broken"
              and not r["requires_javascript"]]

    # 成功来源类型（有实际内容产出）
    type_counter = Counter(r["source_type"] for r in successful_discovery)
    body_type_counter = Counter(r["source_type"] for r in unique_body)

    return {
        "configured_sources": len(rows),
        "implemented_sources": len(implemented),
        "enabled_sources": len(enabled),
        "attempted_sources": len(attempted),
        "successful_discovery_sources": len(successful_discovery),
        "successful_detail_fetch_sources": len(successful_detail),
        "successful_body_extraction_sources": len(unique_body),
        "rss_body_extraction_sources": len(rss_body),
        "html_listing_body_extraction_sources": len(html_body),
        "sources_with_published_events": len(with_pub),
        "temporarily_failed_sources": len(temporarily_failed),
        "permanently_broken_sources": len(perm_broken),
        "requires_javascript_sources": len(requires_js),
        "not_implemented_sources": len(not_impl),
        "stable_active_source_count": len(stable),
        "successful_source_types": sorted(type_counter),
        "body_source_types": sorted(body_type_counter),
        "body_sources": [{
            "source_id": r["source_id"],
            "source_name": r["source_name"],
            "discovery_method": r["discovery_method"],
            "detail_fetch_success_count": r["detail_fetch_success_count"],
            "full_body_count": r["full_body_count"],
            "partial_body_count": r["partial_body_count"],
            "source_type": r["source_type"],
        } for r in unique_body],
        "rows": rows,
    }


print("=" * 70)
for cn in ("乍得", "尼日尔"):
    rows = aggregate(cn)
    s = summarize(cn, rows)
    print(f"\n===== {cn} =====")
    for k, v in s.items():
        if k in ("rows", "body_sources"):
            continue
        print(f"  {k}: {v}")
    print("\n  --- 逐来源明细 ---")
    for r in rows:
        js = " [JS]" if r["requires_javascript"] else ""
        print(f"  {r['final_health_status'][:18]:18s} {r['source_id']:28s} "
              f"d={r['articles_discovered']:3d} fetch={r['detail_fetch_success_count']:3d} "
              f"fb={r['full_body_count']:3d} pb={r['partial_body_count']:2d} "
              f"pub={r['published_count']} | {r['source_type'][:16]}{js}")
    print("\n  --- 正文成功来源（唯一 source_id）---")
    for b in s["body_sources"]:
        print(f"  {b['source_id']:28s} {b['discovery_method']:10s} "
              f"fetch={b['detail_fetch_success_count']:3d} "
              f"fb={b['full_body_count']:3d} pb={b['partial_body_count']:2d} "
              f"| {b['source_type']}")
