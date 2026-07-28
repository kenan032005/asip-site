#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
country_runner.py —— 通用国家采集编排（供 chad/ 与 niger/ 调用）。

职责：
- 按 source["collection_method"] 选择采集器并运行；
- Sitemap 来源的标题补全；
- 国家识别（含尼日尔 country_exclusions、乍得 Lake Chad 防误判规则）；
- 社会安全相关性评分。

统一文章结构：
    {"title","url","summary","published","language",
     "_country_ok","_country_reason","_relevant","_rel_score","_rel_matched"}
"""
import os
import re
import json
from rss_collector import RSSCollector
from wordpress_collector import WordPressCollector
from sitemap_collector import SitemapCollector
from html_list_collector import HTMLListCollector, HTMLListCollector as _HTML
from reliefweb_collector import ReliefWebCollector
from search_discovery_collector import SearchDiscoveryCollector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG_DIR = os.path.join(ROOT, "config", "countries")

COLLECTORS = {
    "rss": RSSCollector,
    "wordpress": WordPressCollector,
    "sitemap": SitemapCollector,
    "html_list": HTMLListCollector,
    "reliefweb_api": ReliefWebCollector,
    "search_discovery": SearchDiscoveryCollector,
}

# 社会安全相关性关键词（法/英/中混合，小写匹配）
SECURITY_POS = [
    "attack", "attaque", "killed", "mort", "morts", "dead", "clash", "conflit",
    "conflict", "terror", "terrorist", "terrorisme", "terrorism", "kidnap",
    "kidnapping", "enlèvement", "abduct", "hostage", "manifest", "manifestation",
    "protest", "sécurité", "securite", "insécurité", "insecurity", "bomb",
    "bombing", "explosion", "raid", "affrontement", "embuscade", "otage",
    "braquage", "robbery", "frontière", "frontier", "couvre-feu", "curfew",
    "crise", "émeute", "riot", "violence", "violences", "armed", "armé",
    "milice", "militia", "rebel", "rebel", "army", "armée", "police", "drone",
    "mine", "séquestration", "exécution", "execution", "massacre", "déplacement",
    "deplacement", "réfugié", "refugie", "refugee", "inondation", "inondations",
    "crue", "flood", "drought", "sécheresse", "epidemic", "épidémie", "cholera",
    "choléra", "earthquake", "séisme", "grève", "greve", "strike", "arrestation",
    "arrest", "fermeture", "banditisme", "banditry", "trafic", "smuggling",
    "orpaillage", "ied", "eei", "insurgent", "insurgé", "jnim", "gsim", "isgs",
    "boko haram", "iswap", "fact", "cico", "état d'urgence", "etat d'urgence",
    "state of emergency", "袭击", "冲突", "恐怖", "绑架", "示威", "安全",
    "爆炸", "边境", "宵禁", "危机", "洪水", "干旱", "霍乱", "疫情", "抢劫",
    "交火", "武装", "军队", "警察", "政变", "战乱", "叛乱", "伏击", "人质",
    "撤离", "遇袭", "中国公民", "中国企业", "使馆提醒", "领事提醒", "安全提醒",
]


def load_country_cfg(name_en):
    p = os.path.join(CFG_DIR, name_en + ".json")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_collector(source, country_cfg):
    method = source.get("collection_method") or "html_list"
    cls = COLLECTORS.get(method, HTMLListCollector)
    return cls(source, country_cfg)


def run_source(source, country_cfg):
    col = get_collector(source, country_cfg)
    arts = col.run()
    if source.get("collection_method") == "sitemap":
        filled = 0
        for a in arts:
            if (not a.get("title")) and filled < 10:
                t = _HTML.fetch_detail_title(a["url"])
                if t:
                    a["title"] = t
                    filled += 1
    return arts, col.errors


def _word_boundary(text, kw):
    return re.search(r"(?<![a-zà-ÿ])" + re.escape(kw.lower()) + r"(?![a-zà-ÿ])",
                     text) is not None


def identify_country(text, country_cfg):
    """返回 (is_chad_or_niger, reason)。True=可归本国；False=被排除/不明确。"""
    t = (text or "").lower()
    for ex in country_cfg.get("country_exclusions", []):
        if _word_boundary(t, ex):
            return False, "excluded:" + ex
    for kw in country_cfg.get("keywords", []) + country_cfg.get("locations", []):
        if kw.lower() in t:
            return True, kw
    # Lake Chad 规则（乍得）
    if ("lake chad" in t) or ("lac tchad" in t):
        if not any(x.lower() in t for x in
                   ["chad", "tchad"] + [l.lower() for l in country_cfg.get("locations", [])]):
            return False, "lake_chad_ambiguous"
    return None, ""


def relevance(text):
    t = (text or "").lower()
    score = 0
    matched = []
    for kw in SECURITY_POS:
        if kw.lower() in t:
            score += 1
            matched.append(kw)
    return (score > 0), score, matched


def run_country(country_cfg, sources):
    """对一个国家的全部来源执行采集与初步识别。"""
    results = []
    for s in sources:
        arts, errs = run_source(s, country_cfg)
        for a in arts:
            blob = (a.get("title") or "") + " " + (a.get("summary") or "")
            ok, reason = identify_country(blob, country_cfg)
            rel, score, matched = relevance(blob)
            a["_country_ok"] = ok
            a["_country_reason"] = reason
            a["_relevant"] = rel
            a["_rel_score"] = score
            a["_rel_matched"] = matched
        results.append({"source": s, "articles": arts, "errors": errs})
    return results
