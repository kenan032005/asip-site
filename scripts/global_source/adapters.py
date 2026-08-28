#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Global Source Layer — Adapters（§三-§九，Source Expansion A）。

每个 source 一个 adapter：RSS / listing HTML / ReliefWeb API / AllAfrica RDF。
- 只使用免费公开页面/公开 RSS/公开 API；
- 不使用付费 API、不绕过 paywall、不用第三方 mirror；
- 单 source 失败记录 adapter 状态，不阻断整个包；
- 返回统一 item 字典（title/url/published_at/original_publisher/original_url）。
"""

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .registry import load_registry

HTTP_TIMEOUT = 25
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def fetch_text(url, timeout=HTTP_TIMEOUT):
    """GET 文本（带 UA；不重定向处理敏感信息）。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    for enc in ("utf-8", "iso-8859-1", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def _pub_dt(v):
    """RSS/ISO 时间 → ISO 字符串；解析失败返回原文。"""
    if not v:
        return None
    s = str(v).strip()
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(s).astimezone().isoformat(timespec="seconds")
    except Exception:
        pass
    try:
        from datetime import datetime
        return datetime.fromisoformat(s.replace("Z", "+00:00")).isoformat(timespec="seconds")
    except Exception:
        return s


def _parse_rss(xml_text, source):
    """解析 RSS/RDF/Atom → item 列表。"""
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items, "parse_error"
    ns = {
        "": "",
        "content": "http://purl.org/rss/1.0/modules/content/",
        "dc": "http://purl.org/dc/elements/1.1/",
        "atom": "http://www.w3.org/2005/Atom",
    }
    # RSS 2.0
    for it in root.iter("item"):
        t = it.findtext("title") or ""
        link = it.findtext("link") or ""
        pub = it.findtext("pubDate") or it.findtext("dc:date", namespaces=ns) or ""
        desc = it.findtext("description") or ""
        src_el = it.find("dc:source", namespaces=ns)
        original = src_el.text if src_el is not None else None
        items.append({"title": html.unescape(t), "url": link.strip(),
                      "published_at": _pub_dt(pub),
                      "original_publisher": (original or "").strip() or None,
                      "original_url": None, "description": desc})
    # Atom
    for it in root.iter("{http://www.w3.org/2005/Atom}entry"):
        t = it.findtext("{http://www.w3.org/2005/Atom}title") or ""
        link_el = it.find("{http://www.w3.org/2005/Atom}link")
        link = (link_el.get("href") if link_el is not None else "") or ""
        pub = it.findtext("{http://www.w3.org/2005/Atom}updated") or ""
        items.append({"title": html.unescape(t), "url": link.strip(),
                      "published_at": _pub_dt(pub)})
    # RDF (AllAfrica)
    if not items:
        for it in root.iter("{http://purl.org/rss/1.0/}item"):
            t = it.findtext("{http://purl.org/rss/1.0/}title") or ""
            link = it.findtext("{http://purl.org/rss/1.0/}link") or ""
            dc = it.find("{http://purl.org/dc/elements/1.1/}date")
            pub = dc.text if dc is not None else ""
            # AllAfrica: dc:source / dc:publisher
            src_el = it.find("{http://purl.org/dc/elements/1.1/}source")
            pub_el = it.find("{http://purl.org/dc/elements/1.1/}publisher")
            original = (src_el.text if src_el is not None else None) or \
                       (pub_el.text if pub_el is not None else None)
            items.append({
                "title": html.unescape(t), "url": link.strip(),
                "published_at": _pub_dt(pub),
                "original_publisher": (original or "").strip() or None,
                "original_url": None,
            })
    return items, None


def _extract_hub_links(html_text, host, path_prefix, max_items=25):
    """从 listing/hub HTML 提取文章链接（title + url 对）。"""
    out = []
    seen = set()
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html_text, re.S | re.I):
        href, txt = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        txt = html.unescape(txt).strip()
        if not txt or len(txt) < 12:
            continue
        full = urllib.parse.urljoin(host, href) if not href.startswith("http") else href
        if path_prefix and path_prefix not in full:
            continue
        key = full.split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        out.append({"title": txt, "url": full, "published_at": None})
        if len(out) >= max_items:
            break
    return out


def _reliefweb_publisher_from_desc(desc):
    """从 ReliefWeb RSS description HTML 提取原始 publisher 与 Countries。"""
    publisher = None
    countries = []
    m = re.search(r'<div class="tag source">Source:\s*([^<]+)</div>', desc)
    if m:
        publisher = html.unescape(m.group(1)).strip()
    m2 = re.search(r'<div class="tag country">Countries:\s*([^<]+)</div>', desc)
    if m2:
        countries = [c.strip() for c in m2.group(1).split(",") if c.strip()]
    return publisher, countries


def _fetch_reliefweb(source, max_items=25):
    """ReliefWeb 公开 RSS（免审批；API 需预审批 appname，实测 410）。"""
    base = "https://reliefweb.int/updates/rss.xml"
    q = 'primary_country.exact:"Chad" OR primary_country.exact:"Niger" ' \
        'OR primary_country.exact:"Mali" OR primary_country.exact:"Burkina Faso"'
    url = base + "?search=" + urllib.parse.quote(q)
    txt = fetch_text(url)
    items, err = _parse_rss(txt, source)
    for it in items:
        pub, countries = _reliefweb_publisher_from_desc(it.get("description") or "")
        it["original_publisher"] = pub or it.get("original_publisher")
        it["country_hints"] = countries
        it.pop("description", None)
    return items[:max_items], err


def collect_source(source, max_items=25):
    """执行单个 source 的 discovery。返回 (items, health_dict)。"""
    sid = source["source_id"]
    method = source.get("acquisition_method", "")
    host = source.get("listing_host", "")
    path = source.get("listing_path", "")
    health = {
        "source_id": sid, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "listing_status": "unknown", "http_status": None,
        "items_discovered": 0, "failure_type": "none",
    }
    try:
        if method == "rss" or method == "rss_global_filter":
            url = "https://" + host + path
            txt = fetch_text(url)
            items, err = _parse_rss(txt, source)
            health["listing_status"] = "success" if items or err is None else "parse_error"
            health["http_status"] = 200
        elif method == "rss_rdf":  # AllAfrica RDF
            url = "https://" + host + path
            txt = fetch_text(url)
            items, err = _parse_rss(txt, source)
            health["listing_status"] = "success" if items else "parse_error"
            health["http_status"] = 200
        elif method == "api":  # ReliefWeb
            items, err = _fetch_reliefweb(source, max_items)
            health["listing_status"] = "success" if items else "empty"
            health["http_status"] = 200
        elif method in ("public_listing_html", "public_hub_html",
                        "official_listing", "listing_publication_discovery",
                        "publication_discovery"):
            url = "https://" + host + path
            txt = fetch_text(url)
            prefix = None
            if "reuters" in host:
                prefix = "/world/africa"
            elif "apnews" in host:
                prefix = "/hub/africa"
            elif "who.int" in host:
                prefix = None
            items = _extract_hub_links(txt, host, prefix, max_items)
            if not items:
                # 200 但无 href 链接 → 疑似 JS 渲染
                if "<a " in txt.lower() and "href" not in txt.lower():
                    health["failure_type"] = "requires_js"
                elif re.search(r'src="[^"]*\.js"', txt) and len(txt) < 60000:
                    health["failure_type"] = "requires_js"
            health["listing_status"] = "success" if items else "empty"
            health["http_status"] = 200
        else:
            items, err = [], "unsupported_method"
            health["failure_type"] = "unknown"
    except urllib.error.HTTPError as e:
        health["http_status"] = e.code
        health["failure_type"] = "http_error" if e.code < 500 else "http_error"
        if e.code in (403, 401):
            health["failure_type"] = "access_restricted"
        elif e.code == 429:
            health["failure_type"] = "blocked"
        health["listing_status"] = "failed"
        return [], health
    except urllib.error.URLError as e:
        health["http_status"] = None
        health["failure_type"] = "timeout" if isinstance(e.reason, TimeoutError) else "unknown"
        health["listing_status"] = "failed"
        return [], health
    except (TimeoutError, ConnectionError):
        health["failure_type"] = "timeout"
        health["listing_status"] = "failed"
        return [], health
    except Exception as e:
        health["failure_type"] = "parse_error"
        health["listing_status"] = "failed"
        return [], health

    # 时间窗过滤：过去 72h（§十五）
    items = _filter_72h(items)
    health["items_discovered"] = len(items)
    if not items and health["listing_status"] == "success":
        health["listing_status"] = "empty"
        health["failure_type"] = "empty"
    return items, health


def _filter_72h(items, hours=72):
    """按 published_at 过滤过去 N 小时；无时间信息的 item 保留（不误杀）。"""
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out = []
    for it in items:
        p = it.get("published_at")
        if not p:
            out.append(it)
            continue
        try:
            dt = datetime.fromisoformat(p.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                out.append(it)
        except ValueError:
            out.append(it)
    return out


def run_listing(registry_path=None, max_items=25, run_id=None):
    """对所有 enabled source 执行 listing discovery。返回 (results, healths)。"""
    sources, errors = load_registry(registry_path)
    if errors:
        return None, {"registry_errors": errors}
    run_id = run_id or time.strftime("GRUN%Y%m%dT%H%M%S+0800")
    results = {}
    healths = []
    for s in sources:
        if not s.get("enabled", False):
            continue
        items, health = collect_source(s, max_items=max_items)
        for it in items:
            it["discovery_run_id"] = run_id
            it["country_hints"] = it.get("country_hints") or []
        results[s["source_id"]] = items
        healths.append(health)
    return {"run_id": run_id, "results": results}, healths
