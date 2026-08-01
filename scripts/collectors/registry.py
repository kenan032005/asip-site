#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
registry.py — SourceRegistry + ArticleDiscoverer。

SourceRegistry：读取 data/sources.json，兼容现有结构，提供统一来源视图。
ArticleDiscoverer：RSS/Atom + HTML 栏目页文章发现，输出统一 discovered 对象。
"""
import os
import re
import json
import sys
import html
import urllib.parse
from xml.etree import ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from framework import fetch_page, strip_tags, validate_url, bj_iso  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCES_PATH = os.path.join(ROOT, "data", "sources.json")

# ── RSS/Atom 命名空间 ──
ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1}"

# 导航/分类/广告链接排除（HTML 栏目页）
SKIP_PATH = ("/tag/", "/author/", "/category/", "/feed", "/wp-content", "/wp-json",
             "/xmlrpc", "/comments", "/cdn-cgi/", "/privacy", "/about", "/contact",
             "/terms", "/login", "/register", "/search", "/page/", "?share=",
             "/facebook", "/twitter", "/youtube", "/whatsapp", "/telegram")
SKIP_DOMAINS = ("facebook.com", "twitter.com", "x.com", "youtube.com", "whatsapp.com",
                "t.me", "telegram", "instagram.com", "linkedin.com", "google.com",
                "gmail.com", "wikipedia.org")


class SourceRegistry:
    """来源注册表：读取 data/sources.json 并扩展。"""

    def __init__(self, path=SOURCES_PATH):
        self.path = path
        self.doc = {"sources": []}
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.doc = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.doc = {"sources": []}
        self.sources = self.doc.get("sources", [])

    def all(self):
        return self.sources

    def enabled(self):
        out = []
        for s in self.sources:
            lp = s.get("legacy_payload", {})
            enabled = lp.get("enabled", s.get("enabled", False))
            if enabled:
                out.append(self._unified(s))
        return out

    def by_country(self, country_cn):
        return [s for s in self.enabled() if s["source_country"] == country_cn]

    def _unified(self, s):
        """将 legacy/新结构统一为 SourceRegistry 视图。"""
        lp = s.get("legacy_payload", {})
        method = lp.get("collection_method", "")
        # 新结构字段优先，listing_urls 同时读顶层和 legacy_payload
        top_listing = s.get("listing_urls", None)
        legacy_listing = lp.get("category_urls", [])
        listing_urls = top_listing if top_listing is not None else legacy_listing
        return {
            "source_id": s.get("source_id", lp.get("source_id", "")),
            "source_name": s.get("source_name", lp.get("name", "")),
            "source_country": s.get("country_scope", [""])[0] if s.get("country_scope") else lp.get("country", ""),
            "source_type": s.get("source_type", lp.get("source_type", "")),
            "language": s.get("language", [lp.get("language", "fr")]) if isinstance(s.get("language"), list) else s.get("language", lp.get("language", "fr")),
            "discovery_type": self._discovery_type(method, lp),
            "feed_url": lp.get("feed_url", ""),
            "listing_urls": listing_urls,
            "base_url": lp.get("url", s.get("url", "")),
            "url": lp.get("url", s.get("url", "")),
            "enabled": lp.get("enabled", s.get("enabled", False)),
            "priority": lp.get("priority", 50),
            "timeout_seconds": lp.get("timeout_seconds", 15),
            "max_items": lp.get("max_items", 20),
            "extractor_profile": lp.get("extractor_profile", {}),
            "health_status": lp.get("status", "unknown"),
            "last_success_at": lp.get("last_success_at", ""),
            "last_failure_at": lp.get("last_failure_at", ""),
            "failure_count": lp.get("failure_count", 0),
        }

    @staticmethod
    def _discovery_type(method, lp):
        if method == "reliefweb_api":
            return "reliefweb_api_or_feed"
        if method == "rss":
            return "rss"
        if method == "html_list":
            return "html_listing"
        if method == "atom":
            return "atom"
        if method == "gdelt_search":
            return "gdelt_search"
        if lp.get("feed_url"):
            return "rss"
        if lp.get("category_urls"):
            return "html_listing"
        return "html_listing"


# ── RSS/Atom 解析 ────────────────────────────────────
def _rss_item_text(el, tag):
    n = el.find(tag)
    if n is None:
        n = el.find(DC + tag)
    return (n.text or "") if n is not None else ""


def _rss_item_link(el):
    link = el.find("link")
    if link is not None:
        if link.get("href"):
            return link.get("href")
        if link.text:
            return link.text.strip()
    link2 = el.find(ATOM + "link")
    if link2 is not None:
        return link2.get("href", "")
    return ""


def _atom_entry_link(en):
    for l in en.findall(ATOM + "link"):
        if l.get("rel") in (None, "alternate"):
            return l.get("href", "")
    return ""


def parse_rss_atom(xml_text, base_url=""):
    """解析 RSS 2.0 与 Atom，返回 discovered 列表。"""
    items = []
    if not xml_text:
        return items
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    # RSS 2.0
    for it in root.iter("item"):
        link = _rss_item_link(it)
        if not link:
            continue
        if base_url and not link.startswith("http"):
            link = urllib.parse.urljoin(base_url, link)
        published = _rss_item_text(it, "pubDate") or _rss_item_text(it, "date")
        guid = _rss_item_text(it, "guid")
        items.append({
            "title": strip_tags(_rss_item_text(it, "title")),
            "url": link,
            "guid": guid or link,
            "summary": strip_tags(_rss_item_text(it, "description"))[:500],
            "published": published,
            "method": "rss",
        })

    # Atom
    for en in root.iter(ATOM + "entry"):
        link = _atom_entry_link(en)
        if not link:
            continue
        if base_url and not link.startswith("http"):
            link = urllib.parse.urljoin(base_url, link)
        title = strip_tags((en.findtext(ATOM + "title") or ""))
        summary = strip_tags((en.findtext(ATOM + "summary") or "") or
                             (en.findtext(ATOM + "content") or ""))[:500]
        published = en.findtext(ATOM + "published") or en.findtext(ATOM + "updated") or ""
        items.append({
            "title": title,
            "url": link,
            "guid": (en.findtext(ATOM + "id") or link),
            "summary": summary,
            "published": published,
            "method": "atom",
        })

    # Feed 内去重
    seen = set()
    out = []
    for it in items:
        key = (it["url"] or "").lower() or (it["guid"] or "")
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


class ArticleDiscoverer:
    """文章发现器：RSS/Atom + HTML 栏目页。"""

    def __init__(self, registry):
        self.registry = registry

    def discover(self, source):
        """返回 (articles, errors)。articles 为统一 discovered dict。"""
        dtype = source["discovery_type"]
        if dtype == "gdelt_search":
            return [], []
        if dtype in ("rss", "atom"):
            return self._discover_rss(source)
        return self._discover_html(source)

    def _discover_rss(self, source):
        feed_url = source["feed_url"]
        if not feed_url:
            return [], [f"{source['source_id']}: no feed_url"]
        text, err, status = fetch_page(feed_url)
        if err:
            return [], [f"{source['source_id']}: fetch {err}"]
        items = parse_rss_atom(text, base_url=source["base_url"])
        # 过滤无效链接
        valid = []
        for it in items:
            if not it.get("url"):
                continue
            ok, reason = validate_url(it["url"])
            if not ok:
                continue
            it["feed_url"] = feed_url
            it["listing_url"] = ""
            it["language"] = source["language"]
            valid.append(it)
        # 限制数量
        return valid[:source["max_items"]], []

    def _discover_html(self, source):
        listing_urls = source["listing_urls"] or [source["base_url"]]
        seen = set()
        out = []
        errors = []
        for lu in listing_urls:
            if not lu:
                continue
            text, err, status = fetch_page(lu)
            if err:
                errors.append(f"{source['source_id']}: {lu} fetch {err}")
                continue
            for link, txt in self._extract_links(text, lu):
                if not link or not txt:
                    continue
                ok, reason = validate_url(link)
                if not ok:
                    continue
                if link in seen:
                    continue
                seen.add(link)
                out.append({
                    "title": txt,
                    "url": link,
                    "guid": link,
                    "summary": "",
                    "published": "",
                    "method": "html_listing",
                    "feed_url": "",
                    "listing_url": lu,
                    "language": source["language"],
                })
        return out[:source["max_items"]], errors

    @staticmethod
    def _extract_links(html_text, base_url):
        out = []
        if not html_text:
            return out
        # 排除导航容器内的链接（header/nav/footer/menu/widget）
        # 先切掉 nav/header/footer 区块
        content = re.sub(r"<nav[^>]*>.*?</nav>", " ", html_text, flags=re.I | re.S)
        content = re.sub(r"<header[^>]*>.*?</header>", " ", content, flags=re.I | re.S)
        content = re.sub(r"<footer[^>]*>.*?</footer>", " ", content, flags=re.I | re.S)
        content = re.sub(r"<aside[^>]*>.*?</aside>", " ", content, flags=re.I | re.S)
        # 排除含 menu/widget 的 div
        content = re.sub(r'<div[^>]*class=["\'][^"\']*(menu|widget|sidebar|related|share)[^"\']*["\'][^>]*>.*?</div>',
                         " ", content, flags=re.I | re.S)

        for href, inner in re.findall(
                r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                content, re.I | re.S):
            abs_url = urllib.parse.urljoin(base_url, href.strip())
            if not abs_url.startswith("http"):
                continue
            # 域名过滤
            host = urllib.parse.urlparse(abs_url).netloc.lower()
            if any(d in host for d in SKIP_DOMAINS):
                continue
            # 路径过滤
            path = urllib.parse.urlparse(abs_url).path.lower()
            if any(sp in path for sp in SKIP_PATH):
                continue
            # 同站内链（排除子域跳转）
            base_host = urllib.parse.urlparse(base_url).netloc.lower()
            if host != base_host:
                continue
            # 排除栏目/分类/标签/作者/归档页（有明确路径段特征），不再误伤纯 slug 文章
            path = urllib.parse.urlparse(abs_url).path.lower().rstrip("/")
            path_seg = [seg for seg in path.split("/") if seg]
            excluded_seg = {"category", "categories", "tag", "tags", "author",
                            "rubrique", "page", "p", "archives", "date", "wp-json"}
            if any(seg in excluded_seg for seg in path_seg[:2]):
                continue
            # 排除首页链接（无路径）
            if not path_seg:
                continue
            txt = strip_tags(inner)
            if len(txt) < 8:
                continue
            out.append((abs_url, txt))
        return out
