#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daily_index.py —— C2 §十六/§十九/§二十：14 日 Daily News Index 与密度门禁。

纯函数模块（无 IO、无网络），供建档工具与正式测试共用。

纪律：
  * 逐日归属一律用 **真实 published_at**（绝不使用 collection time）；
  * VERIFIED_COUNT 只统计 canonical eligible（independent_source_count>=2 AND
    quality_gate_passed）；
  * 门禁阈值照 §二十 实现，不因结果不理想而调整。
"""
from datetime import datetime, timedelta, timezone

BJ = timezone(timedelta(hours=8))

DENSITY_TARGET_PER_DAY = 20
DENSITY_TARGET_TOTAL = 280
CONDITIONAL_MEDIAN = 15
CONDITIONAL_MIN_DAY = 10
CONDITIONAL_TOTAL = 210


def bj_date(ts):
    """把时间戳统一到东八区自然日字符串。"""
    if ts is None:
        return None
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(BJ).date().isoformat()


def window_days(window_start, window_end):
    d0 = datetime.strptime(window_start, "%Y-%m-%d").date()
    d1 = datetime.strptime(window_end, "%Y-%m-%d").date()
    return [(d0 + timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]


def build_day_matrix(days, news_items, eligible_clusters, timeline_events_by_day=None):
    """逐日矩阵。

    news_items: [{published_at/observed_at, country_cn, source_group, event_type,
                  is_update, historical_backfill}]
    eligible_clusters: [{event_time/first_seen_at/created_at}]
    """
    buckets = {d: [] for d in days}
    for it in news_items:
        d = bj_date(it.get("published_at") or it.get("observed_at"))
        if d in buckets:
            buckets[d].append(it)
    verified = {d: 0 for d in days}
    for c in eligible_clusters:
        d = bj_date(c.get("event_time") or c.get("first_seen_at") or c.get("created_at"))
        if d in verified:
            verified[d] += 1
    tl = timeline_events_by_day or {}
    rows = []
    for d in days:
        rows_d = buckets[d]
        pubs = {r.get("source_group") or r.get("source_name") for r in rows_d}
        ctys = {r.get("country_cn") for r in rows_d if r.get("country_cn")}
        cats = {}
        for r in rows_d:
            k = r.get("event_type_cn") or r.get("event_type")
            if k:
                cats[k] = cats.get(k, 0) + 1
        top = [k for k, _ in sorted(cats.items(), key=lambda kv: -kv[1])[:3]]
        rows.append({
            "date": d,
            "NEWS_COUNT": len(rows_d),
            "EVENT_UPDATE_COUNT": sum(1 for r in rows_d if r.get("is_update")),
            "VERIFIED_COUNT": verified[d],
            "TIMELINE_EVENTS": tl.get(d, 0),
            "COUNTRY_COUNT": len(ctys),
            "PUBLISHER_COUNT": len([p for p in pubs if p]),
            "countries": sorted(x for x in ctys if x),
            "BACKFILL_NEWS_COUNT": sum(1 for r in rows_d if r.get("historical_backfill")),
            "top_categories": top,
        })
    return rows


def density_summary(rows):
    counts = [r["NEWS_COUNT"] for r in rows]
    n = len(counts)
    total = sum(counts)
    srt = sorted(counts)
    if n == 0:
        med = 0
    elif n % 2:
        med = srt[n // 2]
    else:
        med = (srt[n // 2 - 1] + srt[n // 2]) / 2
    pub = sorted(r["PUBLISHER_COUNT"] for r in rows)
    cty = sorted(r["COUNTRY_COUNT"] for r in rows)
    return {
        "NEWS_14D_TOTAL": total,
        "DAILY_MIN": min(counts) if counts else 0,
        "DAILY_MAX": max(counts) if counts else 0,
        "DAILY_MEDIAN": med,
        "DAYS_WITH_20_PLUS": sum(1 for c in counts if c >= DENSITY_TARGET_PER_DAY),
        "DAYS_WITH_10_PLUS": sum(1 for c in counts if c >= CONDITIONAL_MIN_DAY),
        "EMPTY_DAYS": sum(1 for c in counts if c == 0),
        "DAYS_TOTAL": n,
        "DAILY_PUBLISHER_MEDIAN": pub[n // 2] if pub else 0,
        "DAILY_COUNTRY_MEDIAN": cty[n // 2] if cty else 0,
    }


def density_gate(rows):
    """§二十 LEADERSHIP_14D_DENSITY_GATE。阈值写死在此，不随结果调整。"""
    if not rows:
        return "FAIL"
    s = density_summary(rows)
    counts = [r["NEWS_COUNT"] for r in rows]
    n = len(counts)
    if (s["DAYS_WITH_20_PLUS"] == n and s["NEWS_14D_TOTAL"] >= DENSITY_TARGET_TOTAL):
        return "PASS"
    if (all(c > 0 for c in counts)
            and s["DAILY_MEDIAN"] >= CONDITIONAL_MEDIAN
            and all(c >= CONDITIONAL_MIN_DAY for c in counts)
            and s["NEWS_14D_TOTAL"] >= CONDITIONAL_TOTAL):
        return "CONDITIONAL_PASS"
    return "FAIL"
