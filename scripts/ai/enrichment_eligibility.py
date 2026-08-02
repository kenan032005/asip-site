#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 — 输入资格判定。

Stage 4 只处理满足以下条件的 Canonical 事件：
- 未进入 quarantine
- primary_country 有效
- canonical_url 为文章详情页
- body_status 为 full_body 或 partial_body
- body_extracted 非空
- article_word_count 达到最低要求（默认 30 词）

不得为增加处理数量而降低 Stage 3 正文准入标准。
不满足条件的事件进入 skipped_ineligible，并记录明确原因。
"""

from urllib.parse import urlparse

# 列表页/非文章页路径段（与 Stage 3B CanonicalUrlIntegrity 一致）
NON_ARTICLE_SEGMENTS = {
    "country", "category", "categories", "tag", "tags",
    "rubrique", "search", "feed", "rss", "author",
    "archives", "date", "wp-json", "page", "video",
    "newsfeed", "program", "podcast",
}

# 不可处理正文状态
INELIGIBLE_BODY_STATUSES = {
    "rss_summary_only", "extraction_failed", "title_only",
}

# 最低词数要求（默认）
DEFAULT_MIN_WORD_COUNT = 30

# 隔离原因（quarantine reason_code）
QUARANTINE_REASONS = {
    "homepage_or_listing_page", "article_page_mismatch", "template_noise_unresolved",
}


def is_article_url(url):
    """判断 canonical_url 是否为具体文章详情页（复用 Stage 3B 规则）。"""
    if not url:
        return False
    if not url.startswith(("http://", "https://")):
        return False
    p = urlparse(url)
    segs = [s for s in (p.path or "").strip("/").lower().split("/") if s]
    if not segs:
        return False
    if segs[0] in NON_ARTICLE_SEGMENTS:
        return False
    return True


def eligibility_status(event, quarantine_ids=None, min_word_count=None):
    """判定单个 canonical event 是否可进入 AI 增强处理。

    返回 (status, reason)：
      - status: "eligible" 或 "skipped_ineligible"
      - reason: 字符串原因（eligible 时为空）
    """
    min_wc = min_word_count if min_word_count is not None else DEFAULT_MIN_WORD_COUNT
    quar = quarantine_ids or set()

    eid = event.get("event_id", "")
    if not eid:
        return "skipped_ineligible", "missing_event_id"
    if eid in quar:
        return "skipped_ineligible", "quarantined"
    if not event.get("primary_country") and not event.get("country_code"):
        return "skipped_ineligible", "missing_primary_country"
    url = event.get("canonical_url", "")
    if not is_article_url(url):
        return "skipped_ineligible", "non_article_url"
    bs = event.get("body_status", "")
    if bs in INELIGIBLE_BODY_STATUSES:
        return "skipped_ineligible", "body_status:" + bs
    if bs not in ("full_body", "partial_body"):
        return "skipped_ineligible", "body_status:" + (bs or "missing")
    if not event.get("body_extracted"):
        return "skipped_ineligible", "missing_body"
    wc = int(event.get("article_word_count") or 0)
    if wc < min_wc:
        return "skipped_ineligible", f"insufficient_body:{wc}<{min_wc}"
    return "eligible", ""


def compute_input_hash(event):
    """基于影响 AI 输出的 Canonical 字段生成 input_hash（SHA-256）。

    字段：original_title / body_extracted / primary_country / event_time / canonical_url
    """
    import hashlib
    parts = [
        "title=" + str(event.get("original_title", "")),
        "body=" + str(event.get("body_extracted", "")),
        "country=" + str(event.get("primary_country", "") or event.get("country_code", "")),
        "time=" + str(event.get("event_time", "")),
        "url=" + str(event.get("canonical_url", "")),
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
