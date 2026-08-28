#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 独立来源判断（§六）。

第一版使用简单确定性规则（不做语义聚类）：
- 规范化 URL 相同 → 同源；
- 注册域相同 → 视为同域转载（同源）；
- content_hash 相同 → 明显复制同一原稿（同源）；
- 聚合平台（Tier D）不增加独立来源数（lead-only）。

独立来源数（independent_source_count）与原始来源数（source_count）分开记录。
"""

from .source_tiers import _host_of
from .constants import TIER_D


def _norm_url(url):
    """URL 规范化：小写、去尾斜杠、去常见追踪参数。"""
    if not url:
        return ""
    from urllib.parse import urlsplit, parse_qsl, urlencode
    try:
        s = urlsplit(url.strip().lower())
        path = (s.path or "").rstrip("/")
        query = ""
        if s.query:
            keep = [(k, v) for k, v in parse_qsl(s.query)
                    if k not in ("utm_source", "utm_medium", "utm_campaign",
                                 "utm_term", "utm_content", "fbclid", "ref")]
            if keep:
                query = "?" + urlencode(keep)
        frag = ("#" + s.fragment) if s.fragment else ""
        return "%s://%s%s%s%s" % (s.scheme, s.netloc.lower(), path, query, frag)
    except Exception:
        return (url or "").strip().lower()


def _norm_host(url):
    """规范化 host（去 www/m 前缀），用于同域转载判断。

    注意：不能使用注册域（xxx.example.com 与 yyy.example.com 共享 example.com，
    但属于不同独立媒体）；规范化 host 保留子域差异。
    """
    host = _host_of(url)
    if host.startswith("www."):
        host = host[4:]
    elif host.startswith("m."):
        host = host[2:]
    return host


def is_duplicate(art_a, art_b):
    """判定两篇文章是否属同一独立来源（转载/同域/同稿）。"""
    if art_a is art_b:
        return True
    ua = _norm_url(art_a.get("article_url") or art_a.get("url") or "")
    ub = _norm_url(art_b.get("article_url") or art_b.get("url") or "")
    if ua and ub and ua == ub:
        return True
    # 同 host（去 www/m 前缀）→ 同域转载
    ha = _norm_host(art_a.get("article_url") or art_a.get("url") or "")
    hb = _norm_host(art_b.get("article_url") or art_b.get("url") or "")
    if ha and hb and ha == hb:
        return True
    # 同一原稿（content_hash）
    ca = art_a.get("content_hash") or ""
    cb = art_b.get("content_hash") or ""
    if ca and cb and ca == cb:
        return True
    # 同源 ID（采集器给定的 source_id）
    sa = art_a.get("source_id") or ""
    sb = art_b.get("source_id") or ""
    if sa and sb and sa == sb:
        return True
    return False


def count_independent(articles):
    """返回 (independent_count, groups)。

    groups: list of list[article]，每个分组是一个独立来源（组内互相同源）。
    聚合平台（Tier D）条目单独分组且不计入独立来源数。
    """
    articles = list(articles)
    groups = []
    for art in articles:
        placed = False
        for g in groups:
            if any(is_duplicate(art, other) for other in g):
                g.append(art)
                placed = True
                break
        if not placed:
            groups.append([art])
    independent = 0
    kept_groups = []
    for g in groups:
        # 组内所有来源均为 Tier D 聚合 → 不计独立来源
        tiers = [a.get("_tier") for a in g if a.get("_tier")]
        if tiers and all(t == TIER_D for t in tiers):
            kept_groups.append(g)  # 保留供 lead 证据，但不计入 independent
            continue
        independent += 1
        kept_groups.append(g)
    return independent, kept_groups
