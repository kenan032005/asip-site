#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect_live.py —— 每小时自动采集最新非洲安全新闻（零依赖，合规）。

数据来源：GDELT 2.0 DOC API（https://www.gdeltproject.org/，完全公开、无需密钥、
不绕过任何登录/付费墙/反爬，符合第二十节合规要求）。GDELT 聚合全球新闻，
每条结果含标题、原文链接、来源域名、语言与发布时间。

流程：
  1. 拉取最近数小时非洲 10 个重点国家的冲突/恐袭/绑架/抗议类新闻；
  2. 按国家白名单与关键词映射到本平台的 event_type / 风险等级；
  3. 跳过已在 events.json 中存在的 URL（去重），追加新事件；
  4. 写回 data/events.json。

用法：
  python scripts/collect_live.py            # 采集并写回
  python scripts/collect_live.py --dry      # 仅预览，不写回
  python scripts/collect_live.py --hours 12 # 采集最近 N 小时（默认 24）

合规提醒：仅发布公开信息；如某来源无法合法访问则跳过，绝不绕过限制。
"""
import os
import sys
import json
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"

# GDELT 返回的 source_language 为英文代码（English/French…），统一存为中文
LANG_MAP = {
    "English": "英语", "French": "法语", "German": "德语", "Spanish": "西班牙语",
    "Italian": "意大利语", "Portuguese": "葡萄牙文", "Turkish": "土耳其语",
    "Arabic": "阿拉伯文", "Russian": "俄文", "Chinese": "中文",
}


def norm_lang(s):
    return LANG_MAP.get((s or "").strip(), (s or "英语").strip())

# 重点国家（英文匹配关键词 -> (中文名, 风险等级)）
# 注意顺序：含空格/更具体的词（如 south sudan、nigeria）放前面，
# 避免 "niger" 误匹配 "northern nigeria" 等子串问题。
COUNTRIES = {
    "south sudan": ("南苏丹", 4), "s. sudan": ("南苏丹", 4), "nigeria": ("尼日利亚", 4), "sudan": ("苏丹", 4),
    "chad": ("乍得", 4), "niger": ("尼日尔", 4), "benin": ("贝宁", 4),
    "ethiopia": ("埃塞俄比亚", 3), "mozambique": ("莫桑比克", 4),
    "libya": ("利比亚", 4), "kenya": ("肯尼亚", 3),
}
# 事件类型关键词映射
TERROR_KW = ["isis", "isil", "iswap", "boko", "al-qaida", "al-qaeda", "jnim",
             "terror", "jihad", "insurgent", "militant", "attack", "袭击", "恐怖"]
PROTEST_KW = ["protest", "demonstrat", "strike", "riot", "unrest", "示威", "骚乱", "抗议"]
KIDNAP_KW = ["kidnap", "abduct", "hostage", "绑架", "人质"]
DISASTER_KW = ["rainstorm", "flood", "earthquake", "drought", "storm", "landslide",
               "cyclone", "wildfire", "outbreak", "cholera", "epidemic", "洪水", "地震", "干旱"]
CONFLICT_KW = ["clash", "conflict", "fighting", "war", "battle", "offensive",
               "killed", "dead", "kill", "bomb", "explosion", "冲突", "交火", "袭击"]

MAX_NEW = 30  # 单次最多新增条数，避免失控


def load(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def detect_country(text):
    t = (text or "").lower()
    import re
    for kw, info in COUNTRIES.items():
        if re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", t):
            return info
    return None


def detect_type(text):
    t = (text or "").lower()
    if any(k in t for k in PROTEST_KW):
        return "示威、罢工和社会骚乱", "中"
    if any(k in t for k in KIDNAP_KW):
        return "绑架、抢劫和严重犯罪", "高"
    if any(k in t for k in TERROR_KW):
        return "恐怖袭击", "高"
    if any(k in t for k in DISASTER_KW):
        return "自然灾害", "中"
    if any(k in t for k in CONFLICT_KW):
        return "武装冲突", "高"
    return "武装冲突", "中"


def parse_gdelt_time(s):
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    # 仅日期
    try:
        return datetime.strptime(s[:8], "%Y%m%d").strftime("%Y-%m-%dT00:00:00Z")
    except ValueError:
        return None


def fetch_articles(hours):
    # GDELT 查询：重点国家 + 安全类关键词
    query = ('(Sudan OR "South Sudan" OR Chad OR Niger OR Benin OR Ethiopia OR '
             'Mozambique OR Libya OR Nigeria OR Kenya) '
             '(attack OR killed OR clash OR conflict OR bombing OR kidnapping OR '
             'protest OR insurgent OR militia OR "terror")')
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": 75,
        "sort": "DateDesc",
        "timespan": "%dh" % hours,
    }
    url = GDELT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "ASIP-Bot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        print("  [警告] GDELT 请求失败：", e)
        return []
    return data.get("articles", [])


def bj_now():
    return datetime.now(timezone.utc) + timedelta(hours=8)


def main():
    ap = argparse_parse()
    hours = ap.hours
    articles = fetch_articles(hours)
    print("GDELT 返回文章数：", len(articles))

    doc = load(os.path.join(DATA, "events.json"), {"events": []})
    events = [e for e in doc.get("events", []) if not e.get("is_demo")]
    seen_urls = {e.get("source_url") for e in events}
    seen_titles = {e.get("title_original", "").strip().lower() for e in events}

    # 现有最大序号
    max_n = 0
    for e in events:
        try:
            n = int(str(e.get("event_id", "")).split("-")[-1])
            max_n = max(max_n, n)
        except ValueError:
            pass

    now = bj_now()
    date_str = now.strftime("%Y%m%d")
    new_events = []
    for art in articles:
        url = (art.get("url") or "").strip()
        title = (art.get("title") or "").strip()
        if not url or not title:
            continue
        if url in seen_urls:
            continue
        if title.lower() in seen_titles:
            continue
        country_info = detect_country(title + " " + (art.get("domain") or ""))
        if not country_info:
            continue
        cn, risk = country_info
        etype, sev = detect_type(title)
        pub = parse_gdelt_time(art.get("seendate") or art.get("date")) or now.strftime("%Y-%m-%dT%H:%M:%SZ")
        max_n += 1
        ev = {
            "event_id": "EVT-%s-%03d" % (date_str, max_n),
            "country": cn, "country_cn": cn, "country_risk_level": risk,
            "region": "", "location": "",
            "latitude": None, "longitude": None,
            "event_type": etype, "event_severity": sev,
            "title_cn": title, "title_original": title,
            "summary_cn": "（自动采集，待翻译）" + title,
            "event_time": pub, "published_time": pub,
            "source_name": art.get("domain") or art.get("sourcecountry") or "GDELT",
            "source_url": url,
            "source_language": norm_lang(art.get("language")),
            "needs_translation": True,
            "china_related": False,
            "confidence": "较高可信", "verification_status": "partial",
            "impact": "待评估", "progress": "持续关注", "potential_impact": "待评估",
            "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "is_demo": False,
            "auto_collected": True,
        }
        new_events.append(ev)
        seen_urls.add(url)
        seen_titles.add(title.lower())
        if len(new_events) >= MAX_NEW:
            break

    print("本次新增事件：", len(new_events))
    if ap.dry:
        for e in new_events[:5]:
            print("  +", e["country"], "|", e["event_type"], "|", e["title_original"][:60])
        print("（预览模式，未写回）")
        return

    if new_events:
        events.extend(new_events)
        doc["events"] = events
        doc["updated_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        doc["is_demo"] = False
        with open(os.path.join(DATA, "events.json"), "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        print("已写回 data/events.json（总计", len(events), "条）")
    else:
        print("无符合条件的新事件。")


def argparse_parse():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="仅预览")
    ap.add_argument("--hours", type=int, default=24, help="采集最近 N 小时")
    return ap.parse_args()


if __name__ == "__main__":
    main()
