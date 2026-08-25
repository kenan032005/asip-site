#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 确定性核实 fixtures（§十三）。

10–12 个确定性场景，覆盖全部 status 分支与关键规则。
全部使用中性命名（ORG_TEST_ALPHA / GROUP_TEST_BETA），不使用真实敏感组织文本。
"""

# 中性来源辅助
def _art(sid, url, name, stype="local_media", published=None, **kw):
    a = {
        "article_id": "ART_" + ("0" * 15) + sid[-1:] if sid else "ART_0000000000000000",
        "source_id": sid,
        "source_name": name,
        "article_url": url,
        "source_type": stype,
        "published_at": published or "2026-08-10T10:00:00Z",
        "detected_country": kw.pop("detected_country", "TCD"),
        "event_country": kw.pop("event_country", "TCD"),
        "detected_locations": kw.pop("detected_locations", ["Alpha City"]),
        "event_type": kw.pop("event_type", "other_security"),
        "content_hash": kw.pop("content_hash", ""),
    }
    a.update(kw)
    return a


def _event(eid, country="TCD", event_time="2026-08-10T09:00:00+08:00",
           location="Alpha City", event_type="other_security", url=None, **kw):
    e = {
        "event_id": eid,
        "country_code": country,
        "event_time": event_time,
        "location_name": location,
        "event_type": event_type,
        "canonical_url": url,
        "independent_source_count": 1,
    }
    e.update(kw)
    return e


# 1. 两个独立国际媒体一致（Tier B）→ verified
F1_TWO_INDEPENDENT = {
    "name": "two_independent_media_consistent",
    "event": _event("EVT_0000000000000001"),
    "articles": [
        _art("rfi", "https://www.rfi.fr/fr/2026/08/10/report-a",
             "Radio France Internationale", stype="international_media"),
        _art("ajz", "https://www.aljazeera.com/news/2026/08/10/report-b",
             "Al Jazeera", stype="international_media"),
    ],
    "expect": "verified",
}

# 2. 官方来源 + 媒体 → verified（含 official_confirmation）
F2_OFFICIAL_PLUS_MEDIA = {
    "name": "official_plus_media",
    "event": _event("EVT_0000000000000002"),
    "articles": [
        _art("gov_tcd", "https://gouv.td/2026/08/10/pr", "乍得政府", stype="state_media"),
        _art("tchad_b", "https://beta-news.example.com/2026/08/10/report-b2", "Beta News"),
    ],
    "expect": "verified",
}

# 3. 单一来源 → single_source
F3_SINGLE_SOURCE = {
    "name": "single_local_source",
    "event": _event("EVT_0000000000000003"),
    "articles": [
        _art("local_c", "https://local-news.example.com/2026/08/10/x", "Local News"),
    ],
    "expect": "single_source",
}

# 4. 两个来源死亡数字冲突 → conflicting
F4_DEATHS_CONFLICT = {
    "name": "deaths_conflict",
    "event": _event("EVT_0000000000000004"),
    "articles": [
        _art("tchad_a", "https://alpha-news.example.com/2026/08/10/d1", "Alpha News",
             deaths=5),
        _art("tchad_b", "https://beta-news.example.com/2026/08/10/d2", "Beta News",
             deaths=50),
    ],
    "expect": "conflicting",
}

# 5. 国家冲突 → conflicting
F5_COUNTRY_CONFLICT = {
    "name": "country_conflict",
    "event": _event("EVT_0000000000000005", country="TCD"),
    "articles": [
        _art("tchad_a", "https://alpha-news.example.com/2026/08/10/c1", "Alpha News",
             detected_country="NER", event_country="NER"),
        _art("tchad_b", "https://beta-news.example.com/2026/08/10/c2", "Beta News",
             detected_country="TCD", event_country="TCD"),
    ],
    "expect": "conflicting",
}

# 6. 日期冲突 → conflicting
F6_DATE_CONFLICT = {
    "name": "date_conflict",
    "event": _event("EVT_0000000000000006", event_time="2026-08-10T09:00:00+08:00"),
    "articles": [
        _art("tchad_a", "https://alpha-news.example.com/2026/08/10/t1", "Alpha News",
             published_at="2026-08-10T10:00:00Z"),
        _art("tchad_b", "https://beta-news.example.com/2026/08/10/t2", "Beta News",
             published_at="2026-08-11T10:00:00Z"),
    ],
    "expect": "conflicting",
}

# 7. NewsNow 发现 → 原始媒体（聚合 lead-only + 原始 primary）
F7_NEWSNOW_TO_ORIGINAL = {
    "name": "newsnow_lead_to_original",
    "event": _event("EVT_0000000000000007"),
    "articles": [
        _art("newsnow", "https://newsnow.example.com/2026/08/10/agg", "NewsNow",
             stype="aggregation_platform", detected_country=""),
        _art("tchad_a", "https://alpha-news.example.com/2026/08/10/r7", "Alpha News"),
    ],
    "expect": "single_source",  # 聚合不计独立；仅 1 个原始来源
}

# 8. 两篇转载同一原稿 → 独立去重（1 独立）
F8_REPUBLISH_DEDUP = {
    "name": "republish_same_original",
    "event": _event("EVT_0000000000000008"),
    "articles": [
        _art("tchad_a", "https://alpha-news.example.com/2026/08/10/orig", "Alpha News",
             content_hash="deadbeef"),
        _art("tchad_a2", "https://alpha-news.example.com/2026/08/10/copy", "Alpha News",
             content_hash="deadbeef"),
    ],
    "expect": "single_source",  # 同域 + 同 hash → 1 独立
}

# 9. 错误栏目页 → rejected
F9_CATEGORY_PAGE = {
    "name": "category_page_rejected",
    "event": _event("EVT_0000000000000009",
                    url="https://alpha-news.example.com/category/politics"),
    "articles": [
        _art("tchad_a", "https://alpha-news.example.com/category/politics",
             "Alpha News"),
    ],
    "expect": "rejected",
}

# 10. 已隔离事件 → rejected
F10_QUARANTINED = {
    "name": "quarantined_event",
    "event": _event("EVT_000000000000000a"),
    "articles": [
        _art("tchad_a", "https://alpha-news.example.com/2026/08/10/q", "Alpha News"),
    ],
    "quarantine_ids": {"EVT_000000000000000a"},
    "expect": "rejected",
}

# 11. 官方确认 → verified（official_confirmation）
F11_OFFICIAL_CONFIRM = {
    "name": "official_confirmation",
    "event": _event("EVT_000000000000000b"),
    "articles": [
        _art("gov_tcd", "https://gouv.td/2026/08/10/conf", "乍得政府", stype="state_media"),
        _art("gov_other", "https://interior.gouv.td/2026/08/10/conf2", "内政部",
             stype="state_media"),
    ],
    "expect": "verified",
}

# 12. 低可信单源 → single_source（Tier C 本地）
F12_LOW_TRUST_SINGLE = {
    "name": "low_trust_single",
    "event": _event("EVT_000000000000000c"),
    "articles": [
        _art("forum_x", "https://forum.example.td/2026/08/10/post", "论坛聚合帖",
             stype="other"),
    ],
    "expect": "single_source",
}

FIXTURES = [
    F1_TWO_INDEPENDENT, F2_OFFICIAL_PLUS_MEDIA, F3_SINGLE_SOURCE,
    F4_DEATHS_CONFLICT, F5_COUNTRY_CONFLICT, F6_DATE_CONFLICT,
    F7_NEWSNOW_TO_ORIGINAL, F8_REPUBLISH_DEDUP, F9_CATEGORY_PAGE,
    F10_QUARANTINED, F11_OFFICIAL_CONFIRM, F12_LOW_TRUST_SINGLE,
]
