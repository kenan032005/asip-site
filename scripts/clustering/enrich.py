#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6A Completion — Detail-Enriched Candidate（§四-§七）。

listing candidate → detail fetch（复用 global_source/detail.py）→ 确定性特征
提取（不调用 AI）：
  location_hints / event_type_hint（关键词映射）/ numeric_facts /
  casualty_hints / named_entity_hints / content_hash。
retrieval prioritization：同国家相近时间多源候选优先 detail（不假设 same_event）。
"""

import hashlib
import re

from .blocking import day_bucket, blocking_time

# §五 event_type 关键词映射（确定性）
EVENT_TYPE_RULES = [
    (("attack", "attaque", "armed", "killed", "tué", "tues", "tue", "deadly",
      "assault", "raid", "embuscade", "shooting", "fusillade"), "armed_attack"),
    (("protest", "manifestation", "demonstration", "grève", "greve", "strike",
      "rallies", "sit-in"), "civil_unrest"),
    (("flood", "inondation", "inondations", "floods"), "natural_disaster"),
    (("kidnap", "enlèvement", "enlevement", "hostage", "otage"), "kidnapping"),
    (("explosion", "blast", "bomb", "attentat", "mine"), "explosion"),
    (("border", "frontière", "frontiere", "crossing"), "border_security"),
    (("election", "élection", "election", "vote", "coup"), "political_instability"),
    (("cholera", "mpox", "monkeypox", "measles", "meningitis", "ebola", "marburg",
      "yellow fever", "outbreak", "épidémie", "epidemie"), "public_health"),
]

CASUALTY_KW = ("death", "deaths", "killed", "dead", "died", "morts", "tués",
               "tues", "victimes", "casualties", "died", "décès", "deces",
               "blessés", "blesses", "injured", "wounded")

NUMERIC_PATTERN = re.compile(r"\b(\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?)\b")


def _norm(text):
    return (text or "").lower()


def extract_event_type(title, body=""):
    """确定性 event_type hint（关键词命中返回首个规则）。"""
    blob = _norm(title) + " " + _norm(body)[:2000]
    for kws, etype in EVENT_TYPE_RULES:
        if any(kw in blob for kw in kws):
            return etype
    return None


def extract_location_hints(title, body=""):
    """location hints：国家/城市词典命中（复用 africa_filter 别名与城市表）。"""
    from scripts.global_source.africa_filter import (
        AFRICA_COUNTRY_ALIASES, AFRICA_CITY_KEYWORDS,
    )
    blob = _norm(title) + " " + _norm(body)[:2000]
    hints = []
    for iso2, aliases in AFRICA_COUNTRY_ALIASES.items():
        if any(a in blob for a in aliases):
            hints.append("country:%s" % iso2)
    for city in AFRICA_CITY_KEYWORDS:
        if city in blob:
            hints.append("city:%s" % city)
    # 大写专名（in/à/at + 大写词）
    for m in re.finditer(r"(?:in|à|at|near|près de)\s+([A-Z][A-Za-zÀ-ÿ-]{3,})", title or ""):
        hints.append("place:%s" % m.group(1))
    return sorted(set(hints))[:10]


def extract_numeric_facts(body=""):
    """正文中的显著数字（≥10 或带逗号；去重截断）。"""
    if not body:
        return []
    nums = []
    for m in NUMERIC_PATTERN.finditer(body[:4000]):
        raw = m.group(1).replace(",", "").replace(" ", "")
        try:
            v = int(float(raw))
        except ValueError:
            continue
        if v >= 10 or v in (1, 2, 3, 4, 5, 6, 7, 8, 9):
            nums.append(v)
    # 去重且保留顺序
    seen = []
    for v in nums:
        if v not in seen:
            seen.append(v)
    return seen[:12]


def extract_casualty_hints(title, body=""):
    """casualty hints：死亡/伤亡关键词 + 相邻数字。"""
    blob = _norm(title) + " " + _norm(body)[:4000]
    hints = []
    for kw in CASUALTY_KW:
        for m in re.finditer(r"(\d{1,4}(?:,\d{3})?)\s*%s" % re.escape(kw), blob):
            try:
                v = int(m.group(1).replace(",", ""))
            except ValueError:
                continue
            hints.append({"keyword": kw, "value": v})
    return hints[:8]


def extract_entity_hints(title, body=""):
    """named entity hints：标题中 ≥5 字符非停用词 token（确定性）。"""
    stop = {"the", "and", "for", "with", "from", "that", "this", "was", "are",
            "le", "la", "les", "des", "une", "du", "et", "pour", "dans", "sur",
            "de", "en", "au", "aux", "a", "l", "d", "on", "an", "the", "news",
            "report", "update", "africa", "tchad", "niger", "south", "sudan",
            "benin", "ethiopia", "police", "army", "gouvernement", "government"}
    toks = {w for w in re.split(r"\W+", (title or "").lower())
            if len(w) >= 5 and w not in stop}
    return sorted(toks)[:8]


def enrich_candidate(cand, detail=None):
    """由 listing candidate + detail（可选）构建 enriched candidate。

    detail: global_source.detail.detail_extract 的返回（None 表示抓取失败）。
    """
    body = (detail or {}).get("body_extracted") or ""
    title = (detail or {}).get("title") or cand.get("title") or ""
    pub = (detail or {}).get("published_at") or cand.get("published_at") or None
    canonical = (detail or {}).get("canonical_url") or cand.get("url") or ""
    e = {
        "candidate_id": cand.get("candidate_id"),
        "article_id": cand.get("candidate_id"),
        "source_id": cand.get("source_id"),
        "source_group": cand.get("source_group"),
        "trust_tier": cand.get("trust_tier", "C"),
        "title_original": title,
        "title": title,
        "body_snippet": body[:500],
        "body_extracted": body,
        "body_length": len(body),
        "published_at": pub,
        "canonical_url": canonical,
        "url": canonical or cand.get("url"),
        "original_url": cand.get("original_url"),
        "original_publisher": cand.get("original_publisher"),
        "content_hash": hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
        if body else None,
        "primary_country_iso3": cand.get("primary_country_iso3")
        or cand.get("country_iso3")
        or (cand.get("country_hints") or [None])[0],
        "country_hints": cand.get("country_hints") or [],
        # blocking 时间：只用 published_at（无 event_time），basis 标注 published_at
        "event_time": None,
        "event_time_candidate": pub,
        "event_time_basis": "published_at",
        "location_hints": extract_location_hints(title, body),
        "location": None,
        "named_entity_hints": extract_entity_hints(title, body),
        "event_type_hint": extract_event_type(title, body),
        "event_type": None,
        "numeric_facts": extract_numeric_facts(body),
        "casualty_hints": extract_casualty_hints(title, body),
        "actor": None,
        "target": None,
        "facility": None,
        "affected_countries": [],
        "cross_border": False,
        "detail_success": bool(detail and detail.get("detail_success")),
        "failure_type": (detail or {}).get("failure_type", "not_attempted"),
        "discovery_run_id": cand.get("discovery_run_id"),
    }
    return e


def retrieval_priority(candidates):
    """§七 retrieval prioritization：同国家同 day 多源组优先（不假设 same_event）。
    返回排序后的候选列表（多源组在前）。"""
    from collections import defaultdict
    groups = defaultdict(list)
    for i, c in enumerate(candidates):
        country = c.get("primary_country_iso3") or "UNK"
        d = day_bucket(c.get("event_time") or c.get("published_at")) or "NO_DAY"
        groups[(country, d)].append(i)
    order = []
    for (country, day), idxs in sorted(
            groups.items(), key=lambda kv: (-len(kv[1]), str(kv[0][1]))):
        order.extend(idxs)
    return [candidates[i] for i in order]
