#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""article_url_admission.py —— 确定性「文章页准入」判定（C3R2-PRE §三）。

单一事实源：所有把 URL 当"文章详情页"处理的下游（Article Store 写入、
enrichment 资格、verification 引擎）都应使用本模块，避免同一规则三处各写一遍。

判定只依据**路径结构**，不做语义猜测：
  * 第一段命中 NON_ARTICLE_SEGMENTS → 非文章页（栏目/国家/标签/搜索/Feed/作者…）；
  * 首页（无路径段）→ 非文章页；
  * 非 http(s) → 非文章页；
  * 其余 → 文章页。

**已知边界（务必保留此说明）**：少数发布方把正文放在 /category/ 之下
（例如 New Vision 的 `/category/<section>/<slug>-NV_<id>_<date>`）。
本规则按路径判定会把它们一并拒绝。这是**刻意的确定性取舍**：
宁可漏收，也不把栏目页当正文。若将来需要恢复这类发布方，
应按 publisher 配置单独的 URL 模式，而不是放宽全局规则。
"""
import urllib.parse

#: 明确非文章的首段（栏目/列表/索引/Feed/作者/搜索等）。
#: 与 scripts/tests/test_stage3b_final_repair.py 的独立判定保持一致或更严。
NON_ARTICLE_SEGMENTS = frozenset({
    "country", "countries", "region", "regions", "category", "categories",
    "tag", "tags", "rubrique", "rubriques", "search", "feed", "feeds", "rss",
    "author", "authors", "archives", "archive", "date", "wp-json", "page",
    "video", "videos", "newsfeed", "program", "programme", "podcast",
    "topic", "topics", "section", "sections", "index", "listing", "list",
    "sitemap", "amp", "gallery", "galleries", "photo", "photos", "about",
    "contact", "privacy", "terms", "login", "subscribe",
})

ARTICLE_PAGE = "ARTICLE_PAGE"
NON_ARTICLE_PAGE = "NON_ARTICLE_PAGE"
REASON_HOMEPAGE = "NON_ARTICLE_PAGE_HOMEPAGE"
REASON_SCHEME = "NON_ARTICLE_PAGE_SCHEME"
REASON_LISTING = "NON_ARTICLE_PAGE"


#: 查询串里出现这些参数说明是列表/检索页（而不是 SPIP 风格的文章永久链接）
LISTING_QUERY_KEYS = frozenset({
    "page", "paged", "paging", "s", "q", "search", "cat", "category", "tag",
    "tags", "author", "archive", "archives", "feed", "rss", "offset", "start",
    "index", "orderby", "filter", "k", "keyword",
})


def first_segment(url):
    p = urllib.parse.urlparse(str(url or ""))
    segs = [s for s in (p.path or "").strip("/").split("/") if s]
    return segs[0].lower() if segs else ""


def _listing_query(url):
    """路径为空但查询串带列表参数 → 列表页；查询串是纯 slug（SPIP 的 ?<slug>）→ 文章页。"""
    q = urllib.parse.parse_qsl(urllib.parse.urlparse(str(url or "")).query, keep_blank_values=True)
    keys = {k.lower() for k, _v in q}
    return bool(keys & LISTING_QUERY_KEYS)


def admit_article_url(url):
    """返回 (ok: bool, reason: str)。ok=False 时 reason 说明拒绝类别。

    判定顺序（纯路径/查询结构，不做语义猜测）：
      1. 非 http(s) → 拒绝；
      2. 第一段命中 NON_ARTICLE_SEGMENTS → 列表/栏目页；
      3. 无路径段：若查询串是列表参数（page=/s=/tag=…）→ 首页/列表页；
         若是纯 slug（SPIP 的 `/?<slug>`）→ 视为**文章页**（不得误杀）；
         若连查询串都没有 → 首页；
      4. 其余 → 文章页。
    """
    u = str(url or "").strip()
    if not u.startswith(("http://", "https://")):
        return False, REASON_SCHEME
    seg = first_segment(u)
    if seg in NON_ARTICLE_SEGMENTS:
        return False, REASON_LISTING
    if not seg:
        p = urllib.parse.urlparse(u)
        if not (p.query or "").strip():
            return False, REASON_HOMEPAGE
        if _listing_query(u):
            return False, REASON_LISTING
        return True, ARTICLE_PAGE
    return True, ARTICLE_PAGE


def is_article_url(url):
    return admit_article_url(url)[0]


def rejection_reason(url):
    ok, reason = admit_article_url(url)
    return None if ok else reason
