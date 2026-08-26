#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6A — Article Dedup（§五）。

确定性 Article Dedup：满足任一即 duplicate_article：
  - 相同 canonical_url（归一化后）
  - 相同 original_url
  - 相同 content_hash

URL 归一化：http/https、www、utm_*、fbclid、常见 tracking query、trailing slash。
不删除影响文章身份的 query 参数（如 ?id=、?p=、?page=article）。
"""

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse

# 会被剥离的 tracking query 参数（prefix 匹配）
TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "igshid", "mc_cid", "mc_eid",
                     "ref_src", "ref_url", "spm", "from", "source", "sc_src")
TRACKING_EXACT = {"ref", "cmpid", "cmp", "share", "via", "fbclid"}


def normalize_url(url):
    """URL 归一化。返回规范化字符串；不可解析时返回原样小写。"""
    if not url:
        return ""
    try:
        p = urlparse(url.strip())
        scheme = "https"  # http/https 统一 https
        host = (p.hostname or "").lower().replace("www.", "")
        path = re.sub(r"/+$", "", (p.path or "").lower())
        if not path:
            path = "/"
        kept = []
        for k, v in parse_qsl(p.query, keep_blank_values=True):
            kl = k.lower()
            if kl in TRACKING_EXACT or any(kl.startswith(t) for t in TRACKING_PREFIXES):
                continue
            kept.append((k, v))
        query = urlencode(sorted(kept)) if kept else ""
        return "%s://%s%s%s" % (scheme, host, path, ("?" + query) if query else "")
    except Exception:
        return (url or "").strip().lower()


def content_hash(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def dedup_key(article):
    """article 的 Dedup Key：
    优先显式 content_hash（同稿转载语义），其次归一化 URL
    （original_url 追溯聚合转载 → canonical_url → url）。"""
    h = article.get("content_hash")
    if h:
        return "hash:" + h
    u = article.get("original_url") or article.get("canonical_url") or article.get("url") or ""
    nu = normalize_url(u)
    if nu:
        return "url:" + nu
    return "hash:" + content_hash(str(article.get("title") or ""))


def dedup_articles(articles):
    """输入 article 列表 → (unique_articles, duplicate_articles)。"""
    seen = {}
    unique, dups = [], []
    for a in articles:
        k = dedup_key(a)
        if k in seen:
            a["duplicate_of"] = seen[k]
            dups.append(a)
        else:
            seen[k] = a.get("candidate_id") or a.get("article_id") or a.get("url")
            unique.append(a)
    return unique, dups
