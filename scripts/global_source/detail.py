#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Country/Global Source Layer — Detail Extraction（§二/§十四，Source Expansion B）。

正文提取（轻量、免费公开页）：
  canonical_url / title / published_at / body_extracted / body_length / language。
不追求完美；单一 source 失败记录 failure_type，不长时间调试。
"""

import hashlib
import html
import re
import time
import urllib.error
import urllib.request

from .adapters import fetch_text, HTTP_TIMEOUT

# 正文容器候选（按优先级）
BODY_CONTAINERS = [
    "article", "div[itemprop=articleBody]", ".entry-content", ".post-content",
    ".article-body", ".article__content", ".story-body", ".content",
    ".field--name-body",
]
OPINION_SECTIONS = ("opinion", "editorial", "chronique", "analyse", "analysis")


def _tag_text(html_text, tag):
    """提取第一个 <tag> 的文本。"""
    m = re.search(r"<%s[^>]*>(.*?)</%s>" % (tag, tag), html_text, re.S | re.I)
    if not m:
        return None
    t = re.sub(r"<[^>]+>", "", m.group(1))
    return html.unescape(t).strip()


def _meta_content(html_text, prop, attr="property"):
    m = re.search(r'<%s[^>]+%s=["\']%s["\'][^>]*content=["\']([^"\']+)' %
                  (re.escape("meta"), attr, re.escape(prop)), html_text, re.I)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+%s=["\']%s["\']' %
                      (attr, re.escape(prop)), html_text, re.I)
    return html.unescape(m.group(1)).strip() if m else None


def extract_body(html_text, max_paras=40):
    """从正文容器提取段落文本。返回 (body, paras)。"""
    # 优先 <article>；否则取最大 <p> 连续块
    article = re.search(r"<article[^>]*>([\s\S]*?)</article>", html_text, re.I)
    scope = article.group(1) if article else html_text
    paras = []
    for m in re.finditer(r"<p[^>]*>([\s\S]*?)</p>", scope, re.I):
        t = re.sub(r"<[^>]+>", "", m.group(1))
        t = html.unescape(t).strip()
        if len(t) >= 30:
            paras.append(t)
        if len(paras) >= max_paras:
            break
    if not paras:
        # fallback：最大文本块
        text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", "", scope)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(re.sub(r"\s+", " ", text)).strip()
        paras = [text[:1500]] if len(text) >= 50 else []
    return "\n\n".join(paras), paras


def detect_language(text):
    """粗略语言检测（fr/en/other）——基于常见停用词。"""
    fr = sum(1 for w in ("le", "la", "les", "des", "une", "du", "et", "pour", "dans", "sur")
             if re.search(r"\b%s\b" % w, text.lower()))
    en = sum(1 for w in ("the", "and", "for", "with", "from", "that", "this", "was", "are")
             if re.search(r"\b%s\b" % w, text.lower()))
    if fr > en:
        return "fr"
    if en > fr:
        return "en"
    return "unknown"


def detail_extract(url, source_id, language_hint=""):
    """对单个 article URL 做 detail extraction。返回 dict（含 failure_type）。"""
    result = {
        "url": url, "source_id": source_id,
        "canonical_url": url, "title": None, "published_at": None,
        "body_extracted": None, "body_length": 0, "language": language_hint or None,
        "detail_success": False, "failure_type": "none",
    }
    try:
        txt = fetch_text(url)
    except urllib.error.HTTPError as e:
        result["failure_type"] = ("access_restricted" if e.code in (401, 403)
                                  else "http_error")
        result["http_status"] = e.code
        return result
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        result["failure_type"] = "timeout"
        return result
    except Exception:
        result["failure_type"] = "parse_error"
        return result

    # canonical
    cm = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', txt)
    if cm:
        result["canonical_url"] = cm.group(1)
    # title
    result["title"] = _tag_text(txt, "title") or _meta_content(txt, "og:title") or \
        _meta_content(txt, "title", attr="name")
    # published_at
    tm = re.search(r'<time[^>]+datetime=["\']([^"\']+)', txt)
    if tm:
        result["published_at"] = tm.group(1)
    else:
        result["published_at"] = (_meta_content(txt, "article:published_time") or
                                  _meta_content(txt, "datePublished") or
                                  _meta_content(txt, "pubdate", attr="name"))
    # body
    body, paras = extract_body(txt)
    if body:
        result["body_extracted"] = body
        result["body_length"] = len(body)
        result["detail_success"] = True
        if not result["language"]:
            result["language"] = detect_language(body)
    else:
        result["failure_type"] = "empty"
    return result


def content_hash(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]
