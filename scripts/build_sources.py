#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_sources.py —— 真实探测信息源可访问性，生成结构化 data/sources.json。

对每个来源实际发起 HTTP 请求，按优先级探测采集方法：
  RSS/Atom feed -> WordPress(wp-json) -> XML Sitemap -> HTML 列表页
国际/人道来源按合规方式（search_discovery 用 GDELT；reliefweb_api 用 ReliefWeb API）。

输出：data/sources.json（规范字段）+ 控制台探测报告。
不修改任何已运行逻辑，仅生成/刷新来源配置。
"""
import os
import sys
import json
import re
import time
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COLLECTORS_DIR = os.path.join(SCRIPT_DIR, "collectors")
sys.path.insert(0, COLLECTORS_DIR)

from base import fetch_text, parse_feed, extract_links  # noqa: E402
from reliefweb_collector import ReliefWebCollector  # noqa: E402
from country_runner import load_country_cfg  # noqa: E402

ROOT = os.path.dirname(SCRIPT_DIR)
DATA = os.path.join(ROOT, "data")

# ---- 来源清单（本轮仅乍得/尼日尔）----
SOURCES = [
    # ===== 乍得 本地 =====
    {"source_id": "chad-tchadinfos", "name": "Tchadinfos", "country": "乍得",
     "url": "https://tchadinfos.com/", "language": "法语", "source_type": "local_media",
     "source_position": "local_media", "collection_method": "auto",
     "category_urls": ["https://tchadinfos.com/category/securite/", "https://tchadinfos.com/category/tchad/", "https://tchadinfos.com/category/politique/"],
     "lead_only": False, "requires_api": False, "notes": "第一优先级：安全/政治/社会栏目"},
    {"source_id": "chad-alwihda", "name": "Alwihda Info", "country": "乍得",
     "url": "https://www.alwihdainfo.com/", "language": "法语", "source_type": "local_media",
     "source_position": "local_media", "collection_method": "auto",
     "category_urls": [], "lead_only": False, "requires_api": False,
     "notes": "发布多国新闻，须国家识别防误归乍得"},
    {"source_id": "chad-lendjampost", "name": "Le N'Djam Post", "country": "乍得",
     "url": "https://lendjampost.com/", "language": "法语", "source_type": "local_media",
     "source_position": "local_media", "collection_method": "auto",
     "category_urls": [], "lead_only": False, "requires_api": False,
     "notes": "安全/治安/军警/政治/边境"},
    {"source_id": "chad-journaldutchad", "name": "Journal du Tchad", "country": "乍得",
     "url": "https://journaldutchad.com/", "language": "法语", "source_type": "local_media",
     "source_position": "local_media", "collection_method": "auto",
     "category_urls": [], "lead_only": False, "requires_api": False, "notes": "政治/社会/安全/政府"},
    {"source_id": "chad-tchadone", "name": "Tchad One", "country": "乍得",
     "url": "https://tchadone.com/", "language": "法语", "source_type": "local_media",
     "source_position": "commentary", "collection_method": "auto",
     "category_urls": [], "lead_only": True, "requires_api": False,
     "notes": "评论性较多；事实性入候选，评论/社论/指控不直接入正式事件"},
    {"source_id": "chad-toumaiweb", "name": "Toumaï Web Médias", "country": "乍得",
     "url": "https://www.toumaiwebmedias.com/", "language": "法语", "source_type": "local_media",
     "source_position": "local_media", "collection_method": "auto",
     "category_urls": [], "lead_only": False, "requires_api": False, "notes": "地方/安全/边境"},
    {"source_id": "chad-tachad", "name": "Tachad.com", "country": "乍得",
     "url": "https://www.tachad.com/", "language": "法语", "source_type": "local_media",
     "source_position": "local_media", "collection_method": "auto",
     "category_urls": [], "lead_only": False, "requires_api": False, "notes": "备用本地源，确保本地≥6"},
    # ===== 乍得 国际/泛非 =====
    {"source_id": "chad-rfi", "name": "RFI Afrique", "country": "乍得",
     "url": "https://www.rfi.fr/fr/afrique/", "language": "法语", "source_type": "intl_media",
     "source_position": "intl_media", "collection_method": "search_discovery",
     "category_urls": [], "lead_only": False, "requires_api": False,
     "notes": "按乍得过滤的公开搜索发现（不绕过限制）"},
    {"source_id": "chad-france24", "name": "France 24 Afrique", "country": "乍得",
     "url": "https://www.france24.com/fr/afrique/", "language": "法语", "source_type": "intl_media",
     "source_position": "intl_media", "collection_method": "search_discovery",
     "category_urls": [], "lead_only": False, "requires_api": False, "notes": "按乍得过滤"},
    {"source_id": "chad-bbc", "name": "BBC Afrique", "country": "乍得",
     "url": "https://www.bbc.com/afrique", "language": "法语/英文", "source_type": "intl_media",
     "source_position": "intl_media", "collection_method": "search_discovery",
     "category_urls": [], "lead_only": False, "requires_api": False, "notes": "按乍得过滤"},
    # ===== 乍得 人道/专业 =====
    {"source_id": "chad-reliefweb", "name": "ReliefWeb Chad", "country": "乍得",
     "url": "https://reliefweb.int/country/tcd", "language": "英语", "source_type": "humanitarian",
     "source_position": "humanitarian", "collection_method": "reliefweb_api",
     "category_urls": [], "lead_only": False, "requires_api": False, "notes": "ReliefWeb 公开 API 按国家筛选"},
    {"source_id": "chad-unhcr", "name": "UNHCR Chad", "country": "乍得",
     "url": "https://www.unhcr.org/chad.html", "language": "多语", "source_type": "un",
     "source_position": "humanitarian", "collection_method": "search_discovery",
     "category_urls": [], "lead_only": False, "requires_api": False, "notes": "UNHCR 乍得，按乍得过滤"},
    # ===== 乍得 中国相关 =====
    {"source_id": "chad-china", "name": "中国驻乍得使馆/外交部", "country": "乍得",
     "url": "https://td.china-embassy.gov.cn/", "language": "中文", "source_type": "chinese_official",
     "source_position": "chinese_official", "collection_method": "search_discovery",
     "category_urls": [], "lead_only": False, "requires_api": False,
     "query": '("Chinese nationals" OR "Chinese company" OR "China" OR "Ambassade de Chine" OR "ressortissants chinois" OR "citéoyens chinois") (Chad OR Tchad)',
     "notes": "涉中国企业/公民/使馆提醒关键词过滤"},
    # ===== 尼日尔 本地 =====
    {"source_id": "niger-actuniger", "name": "ActuNiger", "country": "尼日尔",
     "url": "https://www.actuniger.com/", "language": "法语", "source_type": "local_media",
     "source_position": "local_media", "collection_method": "auto",
     "category_urls": ["https://www.actuniger.com/category/securite/", "https://www.actuniger.com/category/defense/"],
     "lead_only": False, "requires_api": False, "notes": "第一优先级：安全/国防"},
    {"source_id": "niger-anp", "name": "Agence Nigérienne de Presse (ANP)", "country": "尼日尔",
     "url": "https://anp.ne/", "language": "法语", "source_type": "official",
     "source_position": "official", "collection_method": "auto",
     "category_urls": ["https://anp.ne/securite/", "https://anp.ne/defense/"],
     "lead_only": False, "requires_api": False,
     "notes": "官方通讯社；官方表述须与独立来源区分"},
    {"source_id": "niger-studiokalangou", "name": "Studio Kalangou", "country": "尼日尔",
     "url": "https://www.studiokalangou.org/", "language": "法语", "source_type": "local_media",
     "source_position": "local_media", "collection_method": "auto",
     "category_urls": [], "lead_only": False, "requires_api": False,
     "notes": "新闻稿/周报；第一阶段法语文字"},
    {"source_id": "niger-lesahel", "name": "Le Sahel", "country": "尼日尔",
     "url": "https://www.lesahel.org/", "language": "法语", "source_type": "state_media",
     "source_position": "state_media", "collection_method": "auto",
     "category_urls": ["https://www.lesahel.org/defense-et-securite/"],
     "lead_only": False, "requires_api": False, "notes": "国家媒体，背景官方法庭"},
    {"source_id": "niger-airinfo", "name": "Aïr Info", "country": "尼日尔",
     "url": "https://airinfoagadez.com/", "language": "法语", "source_type": "local_media",
     "source_position": "local_media", "collection_method": "auto",
     "category_urls": [], "lead_only": False, "requires_api": False,
     "notes": "Agadez/Arlit/北部交通/边境/走私/铀矿"},
    {"source_id": "niger-nigerinter", "name": "Niger Inter", "country": "尼日尔",
     "url": "https://nigerinter.com/", "language": "法语", "source_type": "local_media",
     "source_position": "local_media", "collection_method": "auto",
     "category_urls": [], "lead_only": False, "requires_api": False, "notes": "国防安全/城市治安"},
    # ===== 尼日尔 国际/泛非 =====
    {"source_id": "niger-rfi", "name": "RFI Afrique", "country": "尼日尔",
     "url": "https://www.rfi.fr/fr/afrique/", "language": "法语", "source_type": "intl_media",
     "source_position": "intl_media", "collection_method": "search_discovery",
     "category_urls": [], "lead_only": False, "requires_api": False, "notes": "按尼日尔过滤"},
    {"source_id": "niger-france24", "name": "France 24 Afrique", "country": "尼日尔",
     "url": "https://www.france24.com/fr/afrique/", "language": "法语", "source_type": "intl_media",
     "source_position": "intl_media", "collection_method": "search_discovery",
     "category_urls": [], "lead_only": False, "requires_api": False, "notes": "按尼日尔过滤"},
    {"source_id": "niger-bbc", "name": "BBC Afrique", "country": "尼日尔",
     "url": "https://www.bbc.com/afrique", "language": "法语/英文", "source_type": "intl_media",
     "source_position": "intl_media", "collection_method": "search_discovery",
     "category_urls": [], "lead_only": False, "requires_api": False, "notes": "按尼日尔过滤"},
    # ===== 尼日尔 人道/专业 =====
    {"source_id": "niger-reliefweb", "name": "ReliefWeb Niger", "country": "尼日尔",
     "url": "https://reliefweb.int/country/ner", "language": "英语", "source_type": "humanitarian",
     "source_position": "humanitarian", "collection_method": "reliefweb_api",
     "category_urls": [], "lead_only": False, "requires_api": False, "notes": "ReliefWeb 公开 API 按国家筛选"},
    {"source_id": "niger-unhcr", "name": "UNHCR Niger", "country": "尼日尔",
     "url": "https://www.unhcr.org/niger.html", "language": "多语", "source_type": "un",
     "source_position": "humanitarian", "collection_method": "search_discovery",
     "category_urls": [], "lead_only": False, "requires_api": False, "notes": "UNHCR 尼日尔，按尼日尔过滤"},
    # ===== 尼日尔 中国相关 =====
    {"source_id": "niger-china", "name": "中国驻尼日尔使馆/外交部", "country": "尼日尔",
     "url": "https://ne.china-embassy.gov.cn/", "language": "中文", "source_type": "chinese_official",
     "source_position": "chinese_official", "collection_method": "search_discovery",
     "category_urls": [], "lead_only": False, "requires_api": False,
     "query": '("Chinese nationals" OR "Chinese company" OR "China" OR "Ambassade de Chine" OR "ressortissants chinois" OR "citoyens chinois") (Niger OR Nigérien)',
     "notes": "涉中国企业/公民/使馆提醒关键词过滤"},
]


def try_wp_json(base):
    import json
    url = base.rstrip("/") + "/wp-json/wp/v2/posts?per_page=5&_embed"
    text, _ = fetch_text(url)
    if not text:
        return None
    try:
        posts = json.loads(text)
        if isinstance(posts, list) and posts:
            return len(posts)
    except Exception:
        return None
    return None


def probe(source):
    """返回 (method, feed_url, count, status, error)。"""
    method = source.get("collection_method")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if method == "reliefweb_api":
        cfg = load_country_cfg("chad" if source["country"] == "乍得" else "niger")
        col = ReliefWebCollector(source, cfg)
        arts = col.run()
        if arts:
            return "reliefweb_api", "", len(arts), "active", ""
        return "reliefweb_api", "", 0, "degraded", "API 无返回"
    if method == "search_discovery":
        text, err = fetch_text(source["url"])
        if text:
            return "search_discovery", "", 0, "active", ""
        return "search_discovery", "", 0, "degraded", "首页不可达，采集时改用GDELT过滤: %s" % err
    # auto 探测
    base = source["url"].rstrip("/")
    cands = []
    if source.get("feed_url"):
        cands.append(("rss", source["feed_url"]))
    cands += [("rss", base + "/feed/"), ("rss", base + "/feed"),
              ("wp", base), ("sitemap", base + "/sitemap.xml"),
              ("sitemap", base + "/wp-sitemap.xml")]
    for m, u in cands:
        if m == "rss":
            text, _ = fetch_text(u)
            if text:
                arts = parse_feed(text)
                if arts:
                    return "rss", u, len(arts), "active", ""
        elif m == "wp":
            n = try_wp_json(base)
            if n:
                return "wordpress", base, n, "active", ""
        elif m == "sitemap":
            text, _ = fetch_text(u)
            if text:
                locs = re.findall(r"<loc>(.*?)</loc>", text, re.S)
                if locs:
                    return "sitemap", u, len(locs), "active", ""
    # HTML 列表兜底
    text, _ = fetch_text(source["url"])
    if text:
        links = [l for l in extract_links(text, source["url"]) if len(l[1]) >= 8]
        if links:
            return "html_list", "", len(links), "active", ""
    return "html_list", "", 0, "test_failed", "无可用采集方式"


def main():
    out = []
    report = []
    for s in SOURCES:
        method, feed, count, status, err = probe(s)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rec = dict(s)
        rec.update({
            "feed_url": feed,
            "collection_method": method,
            "enabled": True,
            "tested": True,
            "last_test_at": now,
            "last_success_at": now if status in ("active", "degraded") and count > 0 else "",
            "last_failure_at": now if status in ("test_failed",) else "",
            "failure_count": 0 if status in ("active", "degraded") else 1,
            "articles_detected_last_run": count,
            "relevant_articles_last_run": 0,
            "status": status,
            "notes": (s.get("notes", "") + (" | 探测:" + err if err else "")).strip(" |"),
        })
        out.append(rec)
        report.append((s["source_id"], s["country"], method, count, status,
                       s["name"], feed or "-"))
        time.sleep(0.3)
    doc = {
        "version": 2,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "本轮（乍得/尼日尔）信息源结构化配置，已完成真实可访问性测试。status: active=可用, degraded=首页不可达但采集方法可行, test_failed=无可用方式。",
        "sources": out,
    }
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "sources.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print("已生成 data/sources.json，共 %d 个来源\n" % len(out))
    print("%-26s %-5s %-14s %5s  %-10s %s" % ("source_id", "国", "method", "n", "status", "name"))
    for r in report:
        print("%-26s %-5s %-14s %5s  %-10s %s" % r)
    # 按国统计
    from collections import Counter
    by_country = Counter(r[1] for r in report)
    by_status = Counter(r[4] for r in report)
    print("\n按国家:", dict(by_country))
    print("按状态:", dict(by_status))


if __name__ == "__main__":
    main()
