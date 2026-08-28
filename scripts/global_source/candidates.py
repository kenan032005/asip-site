#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Global Source Layer — Discovery Candidate 结构与去重（§十三/§十二）。

candidate 只进入内部 discovery pool，不直接写 Canonical/Public。
去重：URL 规范化、同域、source_group 独立语义（F24 FR/EN 同组）、
aggregator 追溯 original publisher（AllAfrica→original、ReliefWeb→publisher）。
"""

import hashlib
import json
import re
import time
from urllib.parse import urlparse

# candidate status 枚举（§十三）
CANDIDATE_STATUS = {
    "new", "duplicate", "filtered_non_africa", "needs_detail",
    "detail_ok", "detail_failed", "lead_only",
}

# 聚合类 source_group（不可作为独立事实源计数的组）
AGGREGATOR_GROUPS = {"allafrica", "reliefweb"}


def _norm_url(url):
    """URL 规范化用于去重：小写 host、去 fragment/trailing slash、去 tracking 参数。"""
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower().replace("www.", "")
        path = re.sub(r"/+$", "", p.path or "")
        query = sorted(
            kv for kv in (p.query or "").split("&") if kv and not kv.lower().startswith("utm"))
        return "%s%s%s" % (host, path, "?" + "&".join(query) if query else "")
    except Exception:
        return (url or "").strip().lower()


def _registered_domain(host):
    """近似注册域：取最后两段（二级域）。用于转载/同源判断。"""
    parts = (host or "").split(".")
    if len(parts) >= 3:
        return ".".join(parts[-2:])
    return host or ""


def new_candidate(source, item):
    """由 adapter 产出的原始 item 构造 candidate（未过滤/去重）。"""
    url = item.get("url") or item.get("link") or ""
    title = item.get("title") or ""
    published = item.get("published_at") or item.get("published") or item.get("pubDate") or ""
    cand = {
        "candidate_id": "GC_%s" % hashlib.sha1(
            (source.get("source_id", "") + "|" + url).encode("utf-8")).hexdigest()[:14],
        "source_id": source.get("source_id"),
        "source_group": source.get("source_group"),
        "scope": source.get("scope"),
        "title": title,
        "url": url,
        "published_at": published,
        "language": source.get("language", [])[0] if source.get("language") else "",
        "original_publisher": item.get("original_publisher"),
        "original_url": item.get("original_url"),
        "country_hints": item.get("country_hints", []),
        "discovered_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "discovery_run_id": item.get("discovery_run_id", ""),
        "status": "new",
    }
    return cand


def dedup_key(cand):
    """去重键：优先 original_url，其次 URL 规范化；聚合源用 original。"""
    orig = cand.get("original_url")
    if orig:
        return "orig:" + _norm_url(orig)
    return "url:" + _norm_url(cand.get("url", ""))


def dedup_candidates(cands):
    """同批 candidate 去重。返回 (unique, dup_count)。"""
    seen = set()
    unique = []
    dup = 0
    for c in cands:
        k = dedup_key(c)
        if k in seen:
            dup += 1
            c["status"] = "duplicate"
            continue
        seen.add(k)
        unique.append(c)
    return unique, dup


def origin_group(cand):
    """独立来源组键：聚合源追溯 original_publisher（规范化，与原始媒体 source_group 对齐）；
    否则返回自身 source_group。"""
    sg = cand.get("source_group")
    if sg in AGGREGATOR_GROUPS:
        op = (cand.get("original_publisher") or "").strip().lower()
        op = re.sub(r"\s+", " ", op)
        if op:
            return op
        return "aggregator:" + sg
    return sg or cand.get("source_id")


def independent_count(cands):
    """按 origin_group 统计独立来源数（§十二：F24 双语=1、AllAfrica 追溯=1）。"""
    groups = {}
    for c in cands:
        g = origin_group(c)
        groups.setdefault(g, 0)
        groups[g] += 1
    return len(groups), groups
