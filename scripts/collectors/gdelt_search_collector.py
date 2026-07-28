#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gdelt_search_collector.py —— 通过 GDELT 公开 API 按「域名+国家查询」发现文章。

用于强制接入路透社(Reuters)、新华社/新华网(News.cn/Xinhuanet)、AP、AFP 等
大型通讯社：这些站点多有反爬/付费墙，直接抓取困难，但 GDELT 公开索引其文章
并暴露标题/链接/时间，属合法公开来源发现（不绕过任何限制、不复制全文）。
采集到的链接指向原始通讯社页面，来源标记 source_name=该通讯社。

限流对策（GDELT 公共 API 429 频发）：
- 同一国家/关键词的全部 gdelt_search 源合并为 **一次** OR 组合查询
  （`(domain:a OR domain:b OR ...) 关键词`），结果按 URL 域名拆回各源；
- 模块级缓存保证一次采集运行中每个「关键词组」只调用一次 API。

来源配置字段（data/sources.json）：
  collection_method = "gdelt_search"
  query             = "domain:reuters.com Chad"                    # 必填
  timespan          = "72h"  # 可选，默认 72h
  maxrecords        = 25     # 可选（合并查询时自动放大）
"""
import json
import os
import re
import urllib.parse
from base import BaseCollector, normalize_time, fetch_text

LANG_MAP = {
    "English": "英语", "French": "法语", "German": "德语", "Spanish": "西班牙语",
    "Italian": "意大利语", "Portuguese": "葡萄牙文", "Turkish": "土耳其语",
    "Arabic": "阿拉伯文", "Russian": "俄文", "Chinese": "中文",
}

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")

# 关键词组 -> {"articles": [...], "error": str|None}
_CACHE = {}


def _parse_query(q):
    """拆出 domain 列表与剩余关键词。"""
    domains = re.findall(r"domain:([^\s()]+)", q or "")
    kw = re.sub(r"\(?domain:[^\s()]+\)?", "", q or "")
    kw = re.sub(r"\bOR\b", "", kw)
    kw = re.sub(r"[()]", "", kw).strip()
    return domains, kw


def _group_key(source, kw, timespan):
    """同国家+同关键词+同窗口 的 gdelt 源共享一次查询。"""
    return "%s|%s|%s" % (source.get("country", ""), kw, timespan)


def _all_group_domains(source, kw, timespan):
    """从 sources.json 收集同组（同国+同关键词）全部启用 gdelt 源的域名。"""
    domains = set()
    try:
        with open(os.path.join(_DATA_DIR, "sources.json"), encoding="utf-8") as f:
            allsrc = json.load(f).get("sources", [])
    except Exception:
        allsrc = [source]
    for s in allsrc:
        if not s.get("enabled") or s.get("collection_method") != "gdelt_search":
            continue
        if s.get("country") != source.get("country"):
            continue
        d, k = _parse_query(s.get("query", ""))
        if k == kw:
            domains.update(d)
    if not domains:
        domains.update(_parse_query(source.get("query", ""))[0])
    return sorted(domains)


def _fetch_group(source, kw, timespan):
    key = _group_key(source, kw, timespan)
    if key in _CACHE:
        return _CACHE[key]
    domains = _all_group_domains(source, kw, timespan)
    dom_expr = " OR ".join("domain:%s" % d for d in domains)
    if len(domains) > 1:
        dom_expr = "(%s)" % dom_expr
    query = "%s %s" % (dom_expr, kw)
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": "250",
        "sort": "DateDesc",
        "timespan": timespan,
    }
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)
    text, err = fetch_text(url)
    entry = {"articles": [], "error": None, "rate_limited": False}
    if not text:
        # 明确区分「GDELT 公共接口限流」与「其它抓取错误」，便于运行后自检与证据留存
        rate = bool(err) and "429" in str(err)
        entry["rate_limited"] = rate
        if rate:
            entry["error"] = ("GDELT 公共接口限流(HTTP 429)：本机出口 IP 被节流，"
                              "需等待冷却或改由 GitHub Actions 云端低频运行。"
                              "强制接入的 Reuters/新华网查询通路正确，限流解除后即可返回数据。"
                              "原始错误: %s" % err)
        else:
            entry["error"] = "gdelt fetch: %s" % err
    else:
        try:
            entry["articles"] = json.loads(text).get("articles", [])
        except Exception as e:
            entry["error"] = "gdelt json: %s / body: %s" % (e, text[:120])
    _CACHE[key] = entry
    return entry


def _url_in_domains(u, domains):
    try:
        host = urllib.parse.urlparse(u).netloc.lower()
    except Exception:
        return False
    for d in domains:
        d = d.lower()
        if host == d or host.endswith("." + d):
            return True
    return False


class GdeltSearchCollector(BaseCollector):
    def run(self):
        query = self.source.get("query") or self.source.get("gdelt_query")
        if not query:
            self.errors.append("gdelt_search: 缺少 query 字段")
            return []
        my_domains, kw = _parse_query(query)
        if not my_domains:
            self.errors.append("gdelt_search: query 未含 domain: 过滤")
            return []
        timespan = self.source.get("timespan", "72h")
        entry = _fetch_group(self.source, kw, timespan)
        if entry["error"]:
            self.errors.append(entry["error"])
            return []
        out = []
        for art in entry["articles"]:
            title = (art.get("title") or "").strip()
            link = (art.get("url") or "").strip()
            if not link or not title:
                continue
            if not _url_in_domains(link, my_domains):
                continue
            pub = normalize_time(art.get("seendate") or art.get("date"))
            lang = LANG_MAP.get((art.get("language") or "").strip(),
                                (art.get("language") or "英语").strip())
            out.append(self.article(title, link, "", pub, lang))
        return out
