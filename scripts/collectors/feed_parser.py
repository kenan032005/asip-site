#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""feed_parser.py —— C1B §十：健壮 RSS / Atom 解析器（RSS 恢复的核心修复）。

旧解析器（registry.parse_rss_atom + base.parse_feed）的确定性缺陷：
  1. `ET.fromstring(xml_text)` 直接炸在：BOM、XML 声明前的空白/垃圾字节、
     XML 1.0 非法控制字符、未声明的 HTML 实体（&nbsp; &mdash; …）——这几类在
     真实法/英/阿语新闻 feed 里极常见，一旦命中就整份 feed 归零，
     在旧统计里被笼统记成「无产出」。
  2. 命名空间写死 `{http://www.w3.org/2005/Atom}`，Atom 0.3
     (`http://purl.org/atom/ns#`) 与带前缀的 `<atom:entry>` 直接漏读。
  3. 完全不支持 RSS 1.0（RDF）。
  4. `<link>` 只认纯文本或 href 两种形态之一，`rdf:about` / `guid isPermaLink` 漏读。
  5. 日期只认少数格式，RFC822 的**命名时区**（GMT/EST/CET/…）解析失败 →
     published_at 丢失 → 文章无法进入新鲜度分带。

本模块用「命名空间无关（local-name）」的遍历方式重写，并对输入做最小必要修复。
修复只针对**格式兼容性**，绝不臆造内容：解析不出来就返回空，绝不编造条目。
"""
import html as _html
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# 常见 HTML 命名实体 → XML 可用的数字实体（仅做转义兼容，不改变语义）
_NAMED_ENTITIES = {
    "nbsp": "160", "iexcl": "161", "cent": "162", "pound": "163", "curren": "164",
    "yen": "165", "sect": "167", "copy": "169", "laquo": "171", "reg": "174",
    "deg": "176", "plusmn": "177", "sup2": "178", "sup3": "179", "acute": "180",
    "micro": "181", "para": "182", "middot": "183", "raquo": "187", "frac14": "188",
    "frac12": "189", "frac34": "190", "iquest": "191", "times": "215",
    "divide": "247", "ndash": "8211", "mdash": "8212", "lsquo": "8216",
    "rsquo": "8217", "ldquo": "8220", "rdquo": "8221", "bull": "8226",
    "hellip": "8230", "prime": "8242", "euro": "8364", "trade": "8482",
    "larr": "8592", "uarr": "8593", "rarr": "8594", "darr": "8595",
    "agrave": "224", "aacute": "225", "eacute": "233", "egrave": "232",
    "ccedil": "231", "ocirc": "244", "ugrave": "249", "ecirc": "234",
    "acirc": "226", "icirc": "238", "ucirc": "251", "icirc": "238",
    "euml": "235", "iuml": "239", "uuml": "252", "ouml": "246", "auml": "228",
    "szlig": "223", "aring": "229", "oslash": "248", "aelig": "230",
    "sup": "8593", "alpha": "945", "beta": "946", "gamma": "947",
}
_ENTITY_RX = re.compile(r"&([A-Za-z][A-Za-z0-9]{1,31});")
_ILLEGAL_XML_RX = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f\ud800-\udfff\ufdd0-\ufddf\ufffe\uffff]")

# 命名时区（strptime 的 %Z 只认 UTC/GMT，其余必须显式映射）
_TZ_OFFSETS = {
    "UT": 0, "UTC": 0, "GMT": 0, "Z": 0,
    "EST": -5, "EDT": -4, "CST": -6, "CDT": -5, "MST": -7, "MDT": -6,
    "PST": -8, "PDT": -7, "AKST": -9, "HST": -10,
    "CET": 1, "CEST": 2, "EET": 2, "EEST": 3, "WET": 0, "WEST": 1,
    "BST": 1, "MSK": 3, "WAT": 1, "CAT": 2, "EAT": 3, "SAST": 2,
    "IST": 5, "PKT": 5, "WIB": 7, "CST8": 8, "JST": 9, "KST": 9,
}

_DATE_FORMATS = [
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S",
    "%d %b %Y %H:%M:%S %z",
    "%d %b %Y %H:%M:%S",
    "%a, %d %b %y %H:%M:%S %z",
    "%a, %d %b %y %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S %z",
    "%Y-%m-%d %H:%M:%S",
    "%a %b %d %H:%M:%S %z %Y",   # ctime 风格
    "%Y/%m/%d %H:%M:%S",
]


# ── 输入修复 ─────────────────────────────────────────
def sanitize_xml(text):
    """最小必要修复：BOM / 前导垃圾 / 非法控制字符 / 未声明实体。

    只解决"XML 解析器拒绝合法 feed"这一类问题；不修改任何语义内容。
    """
    if not text:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", "ignore")
    text = text.lstrip("\ufeff\ufeff \t\r\n")
    # 去掉 XML 声明之前的任何垃圾前缀（有些 feed 前面有 BOM 残留或空行）
    m = re.search(r"<\?xml|<rss|<feed|<rdf:RDF|<rdf", text, re.I)
    if m and m.start() > 0:
        text = text[m.start():]
    text = _ILLEGAL_XML_RX.sub("", text)
    # 未声明实体 → 数字实体（含 &nbsp; 这类在 HTML 里合法、在 XML 里非法的）
    def _ent(mo):
        name = mo.group(1)
        if name in ("amp", "lt", "gt", "quot", "apos"):
            return mo.group(0)
        if name in _NAMED_ENTITIES:
            return "&#%s;" % _NAMED_ENTITIES[name]
        # 未在映射表里的命名实体：退化为安全字面量，保住整份 feed 可解析
        return "&amp;%s;" % name
    text = _ENTITY_RX.sub(_ent, text)
    return text


def strip_tags(s):
    if not s:
        return ""
    s = re.sub(r"<script.*?</script>", " ", str(s), flags=re.I | re.S)
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


# ── 日期 ─────────────────────────────────────────────
def parse_feed_date(s):
    """返回 (datetime_utc_or_None, tz_label_or_None)。覆盖 RFC822 命名时区。"""
    if not s:
        return None, None
    s = str(s).strip()
    if not s:
        return None, None
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
        except ValueError:
            continue
        if dt.tzinfo:
            return dt.astimezone(timezone.utc), str(dt.tzinfo)
        return dt.replace(tzinfo=timezone.utc), None
    # 命名时区：先摘出时区 token，再按无时区格式解析
    m = re.match(r"^(.*?)\s+([A-Z]{1,5})$", s)
    if m:
        head, tzname = m.group(1).strip(), m.group(2).upper()
        if tzname in _TZ_OFFSETS:
            for fmt in _DATE_FORMATS:
                try:
                    dt = datetime.strptime(head, fmt)
                except ValueError:
                    continue
                dt = dt.replace(tzinfo=timezone(timedelta(hours=_TZ_OFFSETS[tzname])))
                return dt.astimezone(timezone.utc), tzname
    # ISO8601（含 "+08:00"）
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo:
            return dt.astimezone(timezone.utc), str(dt.tzinfo)
        return dt.replace(tzinfo=timezone.utc), None
    except ValueError:
        pass
    # 仅日期
    try:
        dt = datetime.strptime(s[:10], "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc), None
    except ValueError:
        pass
    return None, None


def to_iso_utc(s):
    dt, _ = parse_feed_date(s)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else ""


# ── 命名空间无关遍历 ─────────────────────────────────
def _local(tag):
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else ""


def _iter_local(root, names):
    """按 local-name 迭代（兼容任意/缺失命名空间）。"""
    names = set(n.lower() for n in names)
    for el in root.iter():
        if _local(el.tag) in names:
            yield el


def _child_text(el, names):
    names = set(n.lower() for n in names)
    for c in list(el):
        if _local(c.tag) in names:
            if c.text and c.text.strip():
                return c.text.strip()
            # rdf:Description 这类包装层再下探一层
            for cc in list(c):
                if cc.text and cc.text.strip():
                    return cc.text.strip()
    return ""


def _entry_link(el, base_url=""):
    """RSS/Atom/RDF 各种 link 形态。"""
    # 1) Atom: <link href rel=alternate|None>
    for c in list(el):
        if _local(c.tag) != "link":
            continue
        href = c.get("href")
        rel = (c.get("rel") or "alternate").lower()
        if href and rel in ("alternate", ""):
            return href.strip()
    # 2) RSS: <link>text</link>
    for c in list(el):
        if _local(c.tag) == "link" and c.text and c.text.strip():
            return c.text.strip()
    # 3) RSS: <guid isPermaLink="true">
    for c in list(el):
        if _local(c.tag) == "guid":
            if (c.get("isPermaLink") or "").lower() != "false" and c.text and c.text.strip():
                return c.text.strip()
    # 4) RDF: rdf:about / about
    for k in ("about", "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"):
        v = el.get(k)
        if v:
            return v.strip()
    return ""


def parse_feed_robust(xml_text, base_url=""):
    """解析 RSS 2.0 / RSS 1.0(RDF) / Atom 1.0 / Atom 0.3 → discovered 列表。

    返回条目契约与既有 `parse_rss_atom` 完全一致（title/url/guid/summary/
    published/method），因此可直接替换，不产生第二套语义。
    """
    items = []
    text = sanitize_xml(xml_text)
    if not text:
        return items
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        # 二次尝试：截到最后一个完整闭合条目（应对被截断的响应体），
        # 用文档自身根元素名补一个合法收尾后再解析。
        root = None
        for close_tag in ("</item>", "</entry>"):
            cut = text.rfind(close_tag)
            if cut <= 0:
                continue
            closer = "</channel></rss>"
            if re.search(r"<rdf:RDF", text, re.I):
                closer = "</rdf:RDF>"
            elif re.search(r"<feed[\s>]", text, re.I):
                closer = "</feed>"
            candidate = text[:cut + len(close_tag)] + closer
            try:
                root = ET.fromstring(candidate)
                break
            except ET.ParseError:
                continue
        if root is None:
            return items

    is_atom_doc = _local(root.tag) == "feed" or any(
        _local(e.tag) == "entry" for e in root.iter())

    # ── 条目：item(RSS/RDF) 与 entry(Atom) 都收，按 local-name 判定 ──
    for el in root.iter():
        ln = _local(el.tag)
        if ln not in ("item", "entry"):
            continue
        link = _entry_link(el, base_url)
        if not link:
            continue
        if base_url and not link.startswith("http"):
            link = urllib.parse.urljoin(base_url, link)
        title = strip_tags(_child_text(el, ("title",)))
        summary = strip_tags(_child_text(el, ("description", "summary", "content",
                                              "encoded", "content:encoded", "subtitle")))
        raw_date = (_child_text(el, ("pubdate", "published", "updated", "date",
                                     "dc:date", "created", "modified"))
                    or _child_text(el, ("issued",)))
        guid = _child_text(el, ("guid", "id"))
        method = "atom" if (is_atom_doc and ln == "entry") else "rss"
        items.append({
            "title": title,
            "url": link,
            "guid": guid or link,
            "summary": (summary or "")[:500],
            "published": to_iso_utc(raw_date) or raw_date or "",
            "method": method,
        })

    # feed 内去重（保持既有契约：按 url/guid）
    seen, out = set(), []
    for it in items:
        key = (it["url"] or "").lower() or (it["guid"] or "")
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out
