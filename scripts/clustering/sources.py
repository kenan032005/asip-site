#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6A — Source Independence 与 Blocking（§六/§七）。

source_group 独立语义：F24 EN/FR 同组最多贡献 1 独立来源；
聚合转载（AllAfrica/ReliefWeb）经 original_publisher/original_url 追溯；
政府同稿（Presidency→agency→broadcaster）若同 origin/content_hash 不自动计独立。
Blocking：primary_country_iso3 + time bucket（±72h）作为第一层候选生成，
不用于最终判定。
"""

# 聚合类 source_group（转载/分发平台，不作为独立事实源）
AGGREGATOR_GROUPS = {"allafrica", "reliefweb"}


def independent_group_key(article):
    """独立来源组键：
    1) 聚合源 → original_publisher 规范化（与原始媒体 source_group 对齐）；
    2) 否则 → source_group。
    """
    sg = (article.get("source_group") or article.get("source_id") or "?")
    if sg in AGGREGATOR_GROUPS:
        op = (article.get("origin_publisher") or article.get("original_publisher") or "").strip().lower()
        op = " ".join(op.split())
        if op:
            return op
        return "aggregator:" + sg
    return sg


def source_group_of(article):
    return article.get("source_group") or article.get("source_id") or "?"


def count_independent(articles):
    """统计独立来源组数。"""
    groups = {}
    for a in articles:
        g = independent_group_key(a)
        groups.setdefault(g, 0)
        groups[g] += 1
    return len(groups), groups


# ── §七 Blocking：country + time bucket ──
TIME_WINDOW_HOURS = 72


def time_bucket(ts, window_hours=TIME_WINDOW_HOURS):
    """把 ISO 时间映射到 ±window 桶（以小时粒度）。返回 None 若无法解析。"""
    from datetime import datetime, timezone
    if not ts:
        return None
    s = str(ts)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() // (window_hours * 3600))
    except ValueError:
        return None


def time_delta_hours(a_ts, b_ts):
    from datetime import datetime, timezone
    try:
        a = datetime.fromisoformat(str(a_ts).replace("Z", "+00:00"))
        b = datetime.fromisoformat(str(b_ts).replace("Z", "+00:00"))
        if a.tzinfo is None:
            a = a.replace(tzinfo=timezone.utc)
        if b.tzinfo is None:
            b = b.replace(tzinfo=timezone.utc)
        return abs((a - b).total_seconds()) / 3600.0
    except (ValueError, TypeError):
        return None


def cross_border(a, b):
    """明确 cross-border 关系：一方的 affected_countries 含另一方 primary country，
    或显式 cross_border 标记。"""
    ca = a.get("primary_country_iso3")
    cb = b.get("primary_country_iso3")
    ac = set(a.get("affected_countries") or [])
    bc = set(b.get("affected_countries") or [])
    if ca and ca in bc:
        return True
    if cb and cb in ac:
        return True
    if a.get("cross_border") or b.get("cross_border"):
        return True
    return False


def same_block(a, b):
    """第一层 blocking：country + time bucket。
    国家不同且无 cross-border → 不进候选；时间桶不同 → 不进候选（保守）。
    """
    ca, cb = a.get("primary_country_iso3"), b.get("primary_country_iso3")
    if ca and cb and ca != cb and not cross_border(a, b):
        return False
    ba = time_bucket(a.get("event_time") or a.get("published_at"))
    bb = time_bucket(b.get("event_time") or b.get("published_at"))
    if ba is not None and bb is not None and ba != bb:
        return False
    return True
