#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
base.py —— 采集器基类与通用网络/解析工具（零依赖、合规）。

设计原则（依据需求第十一、十六节）：
- 设置合理 User-Agent；
- 设置超时；控制访问频率（同源最小间隔）；支持重试；
- 单一来源失败不影响其他来源；保存错误日志；不重复请求同一 URL；
- 不抓取图片/视频大文件；不绕过任何访问限制（登录/付费墙/反爬）。

所有具体采集器（rss / sitemap / wordpress / html_list / reliefweb /
search_discovery）均继承 BaseCollector，run() 返回统一结构的文章列表：
    [ {"title": str, "url": str, "summary": str, "published": str(ISO), "language": str}, ... ]
"""
import os
import re
import json
import time
import html
import socket
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

UA = ("Mozilla/5.0 (compatible; ASIP-Collector/1.0; "
      "+https://github.com/kenan032005/asip-site)")
HTTP_TIMEOUT = 20
MAX_RETRIES = 2
MIN_INTERVAL = 1.0  # 同源最小请求间隔（秒）
# GDELT 公共 API 限流严格（429 频发），同主机请求间隔需明显更长
HOST_INTERVALS = {"api.gdeltproject.org": 20.0}
_max_host_hits = {}  # host -> 最近请求时间


def _rate_limit(url):
    host = urllib.parse.urlparse(url).netloc
    interval = HOST_INTERVALS.get(host, MIN_INTERVAL)
    now = time.time()
    if host in _max_host_hits and now - _max_host_hits[host] < interval:
        time.sleep(interval - (now - _max_host_hits[host]))
    _max_host_hits[host] = time.time()


def fetch_text(url, timeout=HTTP_TIMEOUT):
    """抓取文本。返回 (content_or_None, error_or_None)。"""
    _rate_limit(url)
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                enc = r.headers.get_content_charset() or "utf-8"
                try:
                    return raw.decode(enc, "ignore"), None
                except LookupError:
                    return raw.decode("utf-8", "ignore"), None
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429 and attempt < MAX_RETRIES:
                # 限流：长退避（30s/60s）
                time.sleep(30 * (attempt + 1))
                continue
            if attempt < MAX_RETRIES:
                time.sleep(2 * (attempt + 1))
                continue
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(2 * (attempt + 1))
                continue
    return None, last_err


def strip_tags(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(s).strip()


def normalize_time(s):
    """尽量归一为 ISO8601 UTC 字符串；失败返回空串。"""
    if not s:
        return ""
    s = s.strip()
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                "%d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    # ISO8601 含 Z
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        pass
    # 仅日期
    try:
        dt = datetime.strptime(s[:10], "%Y-%m-%d")
        return dt.strftime("%Y-%m-%dT00:00:00Z")
    except ValueError:
        pass
    return ""


def extract_links(html_text, base_url):
    """从 HTML 抽取 (abs_url, link_text)。"""
    out = []
    if not html_text:
        return out
    for href, inner in re.findall(
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            html_text, re.I | re.S):
        abs_url = urllib.parse.urljoin(base_url, href)
        if abs_url.startswith("http"):
            out.append((abs_url, strip_tags(inner)))
    return out


def _text_of(el, tag):
    n = el.find(tag)
    return (n.text or "") if n is not None else ""


def _atom_link(el):
    for l in el.findall("{http://www.w3.org/2005/Atom}link"):
        if l.get("rel") in (None, "alternate"):
            return l.get("href") or ""
    return ""


def parse_feed(xml_text):
    """解析 RSS 2.0 与 Atom，返回文章列表。"""
    items = []
    if not xml_text:
        return items
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for it in root.iter("item"):
        link = _text_of(it, "link") or (it.find("link").get("href") if it.find("link") is not None else "")
        items.append({
            "title": strip_tags(_text_of(it, "title")),
            "url": link,
            "summary": strip_tags(_text_of(it, "description"))[:400],
            "published": normalize_time(_text_of(it, "pubDate")),
        })
    A = "{http://www.w3.org/2005/Atom}"
    for en in root.iter(A + "entry"):
        summary = _text_of(en, A + "summary") or _text_of(en, A + "content")
        items.append({
            "title": strip_tags(_text_of(en, A + "title")),
            "url": _atom_link(en),
            "summary": strip_tags(summary)[:400],
            "published": normalize_time(_text_of(en, A + "published") or _text_of(en, A + "updated")),
        })
    return items


class BaseCollector:
    """采集器基类。子类实现 run()，返回统一文章列表。"""

    def __init__(self, source, country_cfg=None):
        self.source = source or {}
        self.country_cfg = country_cfg
        self.errors = []
        self.language = self.source.get("language") or "法语"

    def fetch(self, url):
        text, err = fetch_text(url)
        if err:
            self.errors.append("%s: %s: %s" % (url, type(err).__name__, err))
        return text

    def article(self, title, url, summary="", published="", language=None):
        return {
            "title": (title or "").strip(),
            "url": (url or "").strip(),
            "summary": (summary or "").strip(),
            "published": published or "",
            "language": language or self.language,
        }

    def run(self):
        raise NotImplementedError("子类必须实现 run()")
