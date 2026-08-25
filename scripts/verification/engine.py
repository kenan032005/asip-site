#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 事件自动核实核心 V1 规则引擎（§五/§七/§十）。

确定性规则（优先级从高到低）：
  R1 rejected  ：页面非具体文章 / 事件被隔离 / 明确错误国家
  R2 conflicting：高价值字段（国家/日期/地点/伤亡/责任方/类型）存在冲突
  R3 verified  ：≥2 个独立来源支持，且至少一个 Tier A/B
  R4 probable  ：1 个 Tier A 来源直接支持
  R5 single_source：仅 1 个独立来源
  R6 unverified：无独立来源（全部聚合 lead-only / 无来源）

输出为符合 schemas/event_verification.schema.json 的 record，写入
data/verification/（独立目录），不覆盖 Canonical、不写 Public。
"""

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone, timedelta

from .constants import (
    STATUS_VERIFIED, STATUS_PROBABLE, STATUS_SINGLE_SOURCE, STATUS_CONFLICTING,
    STATUS_UNVERIFIED, STATUS_REJECTED, TIER_A, TIER_B, TIER_C, TIER_D,
    SUPPORT_PRIMARY, SUPPORT_SUPPORTING, SUPPORT_OFFICIAL, SUPPORT_SECONDARY,
    SUPPORT_LEAD_ONLY, CONFIDENCE_VERIFIED, CONFIDENCE_PROBABLE,
    CONFIDENCE_SINGLE_SOURCE, CONFIDENCE_CONFLICTING, CONFIDENCE_UNVERIFIED,
    CONFIDENCE_REJECTED, METHOD_DETERMINISTIC, RULES_VERSION,
    CONSISTENT, CONFLICT, UNKNOWN,
)
from .source_tiers import classify_tier
from .independence import count_independent, is_duplicate, _norm_url
from .conflicts import detect_conflicts
from .country_aliases import normalize_country

# 非文章页路径段（与 Stage 3B/Stage 4 一致）
_NON_ARTICLE_SEGMENTS = {
    "country", "category", "categories", "tag", "tags", "rubrique", "search",
    "feed", "rss", "author", "archives", "date", "wp-json", "page", "video",
    "newsfeed", "program", "podcast",
}
_EVENT_ID_RE = re.compile(r"^EVT_[0-9a-f]{16}$")
_ART_ID_RE = re.compile(r"^ART_[0-9a-f]{16}$")


def is_article_url(url):
    if not url:
        return False
    if not url.startswith(("http://", "https://")):
        return False
    from urllib.parse import urlparse
    p = urlparse(url)
    segs = [s for s in (p.path or "").strip("/").lower().split("/") if s]
    if not segs:
        return False
    if segs[0] in _NON_ARTICLE_SEGMENTS:
        return False
    return True


def _bj_now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def _mk_verification_id(event_id):
    seed = "%s|%s" % (event_id, _bj_now())
    return "VER_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _official_flag(article):
    stype = (article.get("source_type") or "").strip().lower()
    tier, reason = classify_tier(
        article.get("source_name"), article.get("article_url") or article.get("url"),
        article.get("source_type"))
    return tier == TIER_A and (stype in ("state_media", "official")
                               or reason in ("domain_a", "name_a"))


def build_evidence_sources(event, articles, quarantine_ids=None):
    """为每个来源文章构造 evidence source（含 tier 与 support_type）。

    返回 (sources, notes)。sources 按独立来源分组整理：
    - 每组取代表作为 supporting（primary/official_confirmation/supporting）；
    - 组内副本 → secondary_report；Tier D 聚合 → lead_only。
    """
    sources = []
    notes = []
    arts = [dict(a) for a in articles if a.get("article_url") or a.get("source_name")]
    for a in arts:
        tier, reason = classify_tier(a.get("source_name"),
                                     a.get("article_url") or a.get("url"),
                                     a.get("source_type"),
                                     publisher=a.get("publisher") or a.get("organization"))
        a["_tier"] = tier
        a["_tier_reason"] = reason

    independent, groups = count_independent(arts)
    lead_only_all = []
    for g in groups:
        tiers = [a["_tier"] for a in g]
        if tiers and all(t == TIER_D for t in tiers):
            # 聚合组：只记录 lead_only，不计独立来源
            for a in g:
                sources.append(_mk_evidence(a, SUPPORT_LEAD_ONLY))
                lead_only_all.append(a)
            continue
        # 独立来源组：第一个为主来源，其余为 secondary（转载）
        primary = g[0]
        official = _official_flag(primary)
        if official:
            st = SUPPORT_OFFICIAL
        elif len(groups) == 1 and tiers and tiers[0] == TIER_A:
            st = SUPPORT_PRIMARY
        else:
            st = SUPPORT_PRIMARY
        sources.append(_mk_evidence(primary, st))
        for a in g[1:]:
            sources.append(_mk_evidence(a, SUPPORT_SECONDARY))
    return sources, notes, arts


def _mk_evidence(article, support_type):
    url = article.get("article_url") or article.get("url") or ""
    return {
        "source_id": article.get("source_id")
                     or (("ART_" + (article.get("article_id") or "")[-16:])
                         if article.get("article_id") else ""),
        "source_name": article.get("source_name") or article.get("source_group") or "unknown",
        "source_tier": article.get("_tier") or TIER_C,
        "url": url,
        "published_at": article.get("published_at") or article.get("retrieved_at"),
        "country": article.get("event_country") or article.get("detected_country"),
        "support_type": support_type,
    }


def _consistency_for(field, conflicts, has_sources):
    if any(c["field"] == field for c in conflicts):
        return CONFLICT
    if has_sources:
        return CONSISTENT
    return UNKNOWN


def verify_event(event, articles, quarantine_ids=None,
                 rules_version=RULES_VERSION, verified_at=None,
                 verification_method=METHOD_DETERMINISTIC):
    """核实单个事件，返回 verification record（符合 schema）。

    event: canonical event dict
    articles: list[dict]，该事件关联的来源文章（linked_event_id 匹配或按 article_id）
    quarantine_ids: set[str]，隔离事件 id 集合（event_id / legacy_event_id）
    """
    event_id = event.get("event_id") or ""
    reasons = []
    uncertainties = []

    # ── R1 rejected 前置判定 ──
    if quarantine_ids and event_id in quarantine_ids:
        return _build_record(event, articles, [], STATUS_REJECTED,
                             CONFIDENCE_REJECTED, [], reasons + ["R1:event_quarantined"],
                             uncertainties, [], rules_version, verified_at,
                             verification_method, independent_count=0)
    c_url = event.get("canonical_url") or ""
    if c_url and not is_article_url(c_url):
        return _build_record(event, articles, [], STATUS_REJECTED,
                             CONFIDENCE_REJECTED, [], reasons + ["R1:non_article_url"],
                             uncertainties, [], rules_version, verified_at,
                             verification_method, independent_count=0)
    # 无任何来源文章 → 无法核实（unverified）
    if not articles:
        return _build_record(event, articles, [], STATUS_UNVERIFIED,
                             CONFIDENCE_UNVERIFIED, [], reasons + ["R6:no_sources"],
                             uncertainties, [], rules_version, verified_at,
                             verification_method, independent_count=0)

    # ── 构造证据来源 + 独立判断（统一使用带 _tier 的文章上下文）──
    sources, _notes, tagged_articles = build_evidence_sources(event, articles,
                                                              quarantine_ids)
    independent, _groups = count_independent(tagged_articles)

    # 独立来源数：排除 lead-only（聚合）
    indep_sources = [s for s in sources if s["support_type"] != SUPPORT_LEAD_ONLY]
    indep_count = independent
    if not indep_sources:
        indep_count = 0

    # ── 冲突检测（§八）──
    baseline = {
        "country": event.get("country_code") or event.get("country_iso3"),
        "date": (event.get("event_time") or "")[:10],
        "location": event.get("location_name"),
        "event_type": event.get("event_type"),
    }
    src_values = []
    for a in articles:
        sv = {"source_id": a.get("source_id") or a.get("article_id") or "?"}
        cntry = normalize_country(a.get("detected_country") or a.get("event_country") or "")
        if cntry:
            sv["country"] = cntry
        if (a.get("published_at") or "").strip():
            sv["date"] = (a.get("published_at") or "")[:10]
        if a.get("detected_locations"):
            locs = a["detected_locations"]
            sv["location"] = locs[0] if isinstance(locs, list) and locs else locs
        if a.get("event_type"):
            sv["event_type"] = a["event_type"]
        # 伤亡/责任方（§八 高价值冲突字段；正文抽取留待后续，fixture 可显式提供）
        for f in ("deaths", "injured", "responsible_party"):
            if a.get(f) is not None:
                sv[f] = a[f]
        src_values.append(sv)
    conflicts, unc_conf = detect_conflicts(baseline, src_values)
    uncertainties.extend(unc_conf)

    # ── R2 conflicting ──
    if conflicts:
        return _build_record(event, articles, sources, STATUS_CONFLICTING,
                             CONFIDENCE_CONFLICTING, conflicts,
                             reasons + ["R2:core_conflict"], uncertainties,
                             [], rules_version, verified_at, verification_method,
                             independent_count=indep_count)

    # ── 计算 tier 分布 ──
    tier_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for s in indep_sources:
        tier_counts[s["source_tier"]] = tier_counts.get(s["source_tier"], 0) + 1
    best_tier = None
    for t in (TIER_A, TIER_B, TIER_C, TIER_D):
        if tier_counts.get(t, 0) > 0:
            best_tier = t
            break
    has_official = any(s["support_type"] == SUPPORT_OFFICIAL for s in indep_sources)

    # ── R3 verified ──
    if indep_count >= 2 and best_tier in (TIER_A, TIER_B):
        status = STATUS_VERIFIED
        conf = CONFIDENCE_VERIFIED
        reasons.append("R3:two_independent_with_ab(%d, best=%s)" % (indep_count, best_tier))
    # ── R4 probable：单个 Tier A 直接支持 ──
    elif indep_count == 1 and best_tier == TIER_A:
        status = STATUS_PROBABLE
        conf = CONFIDENCE_PROBABLE
        reasons.append("R4:single_tier_a")
    # ── R5 single_source ──
    elif indep_count == 1:
        status = STATUS_SINGLE_SOURCE
        conf = CONFIDENCE_SINGLE_SOURCE
        reasons.append("R5:single_source(tier=%s)" % best_tier)
    # ── R6 unverified（聚合 lead-only 或无独立来源）──
    else:
        status = STATUS_UNVERIFIED
        conf = CONFIDENCE_UNVERIFIED
        reasons.append("R6:no_independent(tiers=%s)" % tier_counts)

    return _build_record(event, articles, sources, status, conf, conflicts,
                         reasons, uncertainties, [has_official], rules_version,
                         verified_at, verification_method,
                         independent_count=indep_count)


def _build_record(event, articles, sources, status, confidence, conflicts,
                  reasons, uncertainties, _extra, rules_version, verified_at,
                  verification_method, independent_count=0):
    event_id = event.get("event_id") or ""
    # 官方来源数（Tier A + 官方 support_type）
    official_count = sum(1 for s in sources if s["support_type"] == SUPPORT_OFFICIAL)
    indep_sources = [s for s in sources if s["support_type"] != SUPPORT_LEAD_ONLY]
    indep_count = independent_count if independent_count is not None else 0
    has_sources = bool(indep_sources)

    # 一致性字段
    country_consistency = _consistency_for("country", conflicts, has_sources)
    time_consistency = _consistency_for("date", conflicts, has_sources)
    location_consistency = _consistency_for("location", conflicts, has_sources)

    tier_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for s in indep_sources:
        tier_counts[s["source_tier"]] = tier_counts.get(s["source_tier"], 0) + 1
    best_tier = None
    for t in (TIER_A, TIER_B, TIER_C, TIER_D):
        if tier_counts.get(t, 0) > 0:
            best_tier = t
            break
    has_official = any(s["support_type"] == SUPPORT_OFFICIAL for s in indep_sources)

    record = {
        "event_id": event_id,
        "verification_id": _mk_verification_id(event_id),
        "verification_status": status,
        "verification_confidence": int(confidence),
        "source_count": len(sources),
        "independent_source_count": indep_count,
        "official_source_count": official_count,
        "supporting_sources": [s for s in sources if s["support_type"] != SUPPORT_LEAD_ONLY],
        "conflicting_sources": [],
        "country_consistency": country_consistency,
        "time_consistency": time_consistency,
        "location_consistency": location_consistency,
        "source_trust_summary": {
            "tier_counts": tier_counts,
            "best_tier": best_tier,
            "has_official": has_official,
        },
        "evidence": [],
        "uncertainties": uncertainties,
        "verification_reasons": reasons,
        "verified_at": verified_at or _bj_now(),
        "verification_method": verification_method,
        "rules_version": rules_version,
    }
    if conflicts:
        record["conflicting_sources"] = conflicts
    return record
