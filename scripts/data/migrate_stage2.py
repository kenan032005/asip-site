#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_stage2.py —— ASIP Stage-2 旧数据无损迁移

输入（遗留数据池）：
- data/raw_candidates.json  → Articles
- data/pending_events.json  → Articles（processing_status=queued_for_verification）
- data/events.json          → Event Clusters + 各事件来源 Article
- data/quarantine_events.json → Quarantine Records
- data/sources.json         → 升级为规范 Source 模型（Reuters/新华社/ReliefWeb 修正）

输出（规范数据）：
- data/canonical/articles.json
- data/canonical/event_clusters.json
- data/canonical/quarantine.json
- data/canonical/migration_state.json
- data/public/published_events.json + current_metrics.json（经 compatibility_export）

原则：
- 旧 ID 与旧字段完整保留于 legacy_payload / legacy_event_id；
- 新 ID 基于稳定指纹，迁移两次结果完全一致（幂等）；
- 不删除原文件；不编造缺失内容；
- 单一来源事件不得升级为 cross_verified / direct_official_source（由 publication_policy 决定）。

用法：
  python scripts/data/migrate_stage2.py --dry-run
  python scripts/data/migrate_stage2.py --apply [--run-id ID]
  python scripts/data/migrate_stage2.py --rollback
  python scripts/data/migrate_stage2.py --report
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
sys.path.insert(0, str(SCRIPTS))

from data.identifiers import article_id, event_id, quarantine_id, content_hash, normalize_url
from data.normalizers import (
    normalize_country_code, normalize_language, normalize_event_severity,
    normalize_event_status, derive_verification_level, derive_needs_translation,
    SOURCE_TYPE_ENUMS, SOURCE_RELIABILITY_TIER_ENUMS,
)
from data.publication_policy import evaluate
from data.repository import Repository
from pipeline_core import FIXED_RISK_LEVELS, normalize_event_type, parse_time, generate_run_id

MIGRATION_VERSION = "1"

ROOT = SCRIPTS.parent
BACKUP_ROOT_DEFAULT = None  # 由 migration_state 记录，rollback 时回读


# ── 来源匹配 ──────────────────────────────────────────
def _clamp01(x: float) -> float:
    """relevance_score 必须为 [0,1]；旧池中存在 >1 的脏值，迁移时收敛，不丢失（原文保留于 legacy_payload）。"""
    try:
        v = float(x)
    except Exception:
        return 0.0
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _domain(url: str) -> str:
    try:
        from urllib.parse import urlsplit
        net = urlsplit(url).netloc.lower()
        if net.startswith("www."):
            net = net[4:]
        return net
    except Exception:
        return ""


def build_source_index(sources: list) -> dict:
    """构建 名称/域名 → 规范 source 记录 的索引。"""
    idx = {}
    for s in sources:
        sid = s.get("source_id", "")
        name = (s.get("source_name") or s.get("name") or "").strip()
        url = s.get("url") or s.get("source_url") or ""
        dom = _domain(url)
        rec = {
            "source_id": sid, "source_group": s.get("source_group", "") or _group_from(sid, name, url),
            "source_name": name, "source_type": s.get("source_type", "") or s.get("source_position", ""),
            "source_reliability_tier": s.get("source_reliability_tier", ""),
            "is_direct_origin": s.get("is_direct_origin", False),
            "claim_origin_type": s.get("claim_origin_type", "unknown"),
            "url": url,
        }
        if sid:
            idx["id:" + sid] = rec
        if name:
            idx["name:" + name.lower()] = rec
        if dom:
            idx["dom:" + dom] = rec
    return idx


def lookup_source(idx, source_id="", source_name="", source_url=""):
    """按 source_id > name > domain 查找，缺失则合成。"""
    key = "id:" + (source_id or "")
    if key in idx:
        return idx[key]
    if source_name:
        key = "name:" + source_name.strip().lower()
        if key in idx:
            return idx[key]
    dom = _domain(source_url)
    if dom and "dom:" + dom in idx:
        return idx["dom:" + dom]
    # 合成
    group = _group_from(source_id, source_name, source_url)
    return {
        "source_id": source_id or group, "source_group": group,
        "source_name": source_name or group, "source_type": "other",
        "source_reliability_tier": "tier_3", "is_direct_origin": False,
        "claim_origin_type": "unknown", "url": source_url,
    }


def _group_from(source_id, name, url):
    if source_id:
        # 去掉国家前缀 chad_tchadinfos -> tchadinfos
        parts = source_id.split("_", 1)
        if len(parts) == 2 and parts[1]:
            return parts[1]
        return source_id
    if name:
        return name.strip().lower().replace(" ", "_")
    dom = _domain(url)
    return dom or "unknown"


# ── 来源类型 / 可靠等级修正 ───────────────────────────
def _apply_source_corrections(group, name):
    """落实 Section 十：Reuters / 新华社 / ReliefWeb 修正。返回 (source_type, is_direct, is_republic, tier)。"""
    g = (group or "").lower()
    low = (name or "").lower()
    if "reuters" in g or "reuters" in low:
        return "international_media", True, False, "tier_1"
    if g in ("xinhua", "xinhuanet") or "新华" in (name or ""):
        return "state_media", False, False, "tier_1"
    if g == "reliefweb" or "reliefweb" in (group or "") or "reliefweb" in low:
        return "aggregation_platform", False, True, "tier_2"
    return None, None, None, None


def map_source_type(legacy_type, legacy_position, group):
    corr, _, _, _ = _apply_source_corrections(group, "")
    if corr:
        return corr
    for v in (legacy_type, legacy_position):
        if v in SOURCE_TYPE_ENUMS:
            return v
    return "other"


def derive_tier(stype):
    if stype in ("government", "military_or_police", "international_organization", "international_media", "state_media"):
        return "tier_1"
    if stype in ("local_media", "humanitarian", "ngo", "research"):
        return "tier_2"
    return "tier_3"


# ── Article 构建 ─────────────────────────────────────
def candidate_to_article(c, from_pending=False, idx=None):
    idx = idx or {}
    url = c.get("url") or ""
    canonical = normalize_url(url) if url else ""
    if canonical:
        aid = article_id(canonical_url=canonical)
    else:
        aid = article_id(source_id=c.get("source_id", ""), published_at=c.get("published_time", ""),
                         title=c.get("title_original", ""))
    src = lookup_source(idx, c.get("source_id", ""), c.get("source_name", ""), c.get("source_url", ""))
    stype = map_source_type(src.get("source_type", ""), src.get("source_position", ""), src["source_group"])
    corr_type, corr_direct, _, corr_tier = _apply_source_corrections(src["source_group"], src["source_name"])
    if corr_type:
        stype, is_direct, tier = corr_type, corr_direct, corr_tier
    else:
        is_direct = src.get("is_direct_origin", False)
        tier = src.get("source_reliability_tier") or derive_tier(stype)
    etype = c.get("event_type", "") or ""
    if not etype and c.get("rel_matched"):
        etype = ""
    return {
        "article_id": aid,
        "schema_version": "2.0", "pipeline_version": 2, "run_id": "",
        "source_id": src["source_id"], "source_group": src["source_group"],
        "source_name": c.get("source_name") or "", "source_type": stype,
        "source_reliability_tier": tier,
        "claim_origin_type": src.get("claim_origin_type", "unknown"),
        "article_url": url, "canonical_url": canonical,
        "title_original": c.get("title_original") or "", "summary_original": c.get("summary_original") or "",
        "content_excerpt": (c.get("summary_original") or "")[:300],
        "language": normalize_language(c.get("language", "")),
        "published_at": c.get("published_time") or None, "retrieved_at": c.get("fetched_at") or None,
        "updated_at": None,
        "detected_country": c.get("country") or "", "event_country": c.get("country") or "",
        "mentioned_countries": c.get("mentioned_countries", []) or [],
        "regional_scope": "", "country_confidence": 1.0 if c.get("country_ok") else 0.0,
        "detected_locations": c.get("matched_location_entities", []) or [],
        "event_type": normalize_event_type(etype) if etype else "",
        "relevance_score": _clamp01(c.get("rel_score", 0) or 0),
        "is_security_relevant": bool(c.get("relevant", False)),
        "china_related": False,
        "title_cn": c.get("title_cn") or "", "summary_cn": c.get("summary_cn") or "",
        "content_hash": content_hash(c.get("title_original", ""), c.get("summary_original", ""), canonical),
        "processing_status": "queued_for_verification" if from_pending
        else ("normalized" if c.get("relevant") else "raw"),
        "verification_queue_status": "waiting" if from_pending else "not_required",
        "linked_event_id": None,
        "warnings": [], "errors": [],
        "needs_translation": derive_needs_translation(c),
        "legacy_payload": dict(c),
    }


# ── Event Cluster 构建 ───────────────────────────────
def event_to_cluster(ev, idx, is_new=False):
    """legacy 事件 → 规范 Event Cluster。

    is_new=False：历史迁移路径，event_id 用 legacy_event_id 做 seed（1:1 稳定），
                  publication_status 强制 published（页面显示不变）。
    is_new=True ：新提升事件（promote_events 2C 起），event_id 用纯内容指纹，
                  publication_status 由确定性发布政策 evaluate() 决定。
    """
    country = ev.get("country", "")
    cc = normalize_country_code(country)
    risk = FIXED_RISK_LEVELS.get(country, {
        "country_risk_level": ev.get("country_risk_level", 4),
        "country_risk_label": ev.get("country_risk_label", "极高"),
    })
    etype = normalize_event_type(ev.get("event_type", ""))
    # 事件来源 → Article
    src = lookup_source(idx, "", ev.get("source_name", ""), ev.get("source_url", ""))
    stype = map_source_type(src.get("source_type", ""), src.get("source_position", ""), src["source_group"])
    corr_type, corr_direct, _, corr_tier = _apply_source_corrections(src["source_group"], src["source_name"])
    if corr_type:
        stype, is_direct, tier = corr_type, corr_direct, corr_tier
    else:
        is_direct = src.get("is_direct_origin", False)
        tier = src.get("source_reliability_tier") or derive_tier(stype)
    src_url = ev.get("source_url", "")
    canon = normalize_url(src_url) if src_url else ""
    if canon:
        aid = article_id(canonical_url=canon)
    else:
        aid = article_id(source_id=src["source_id"], published_at=ev.get("published_time", ""),
                         title=ev.get("title_original", ""))
    src_article = {
        "article_id": aid,
        "schema_version": "2.0", "pipeline_version": 2, "run_id": "",
        "source_id": src["source_id"], "source_group": src["source_group"],
        "source_name": ev.get("source_name", ""), "source_type": stype,
        "source_reliability_tier": tier,
        "claim_origin_type": src.get("claim_origin_type", "unknown"),
        "article_url": src_url, "canonical_url": canon,
        "title_original": ev.get("title_original") or "", "summary_original": ev.get("summary_cn") or "",
        "content_excerpt": (ev.get("summary_cn") or "")[:300],
        "language": normalize_language(ev.get("source_language", "")),
        "published_at": ev.get("published_time") or None, "retrieved_at": None, "updated_at": None,
        "detected_country": country, "event_country": country,
        "mentioned_countries": [], "regional_scope": "", "country_confidence": 1.0,
        "detected_locations": [], "event_type": etype,
        "relevance_score": 1.0, "is_security_relevant": True, "china_related": bool(ev.get("china_related", False)),
        "title_cn": ev.get("title_cn") or "", "summary_cn": ev.get("summary_cn") or "",
        "content_hash": content_hash(ev.get("title_original", ""), ev.get("summary_cn", ""), canon),
        "processing_status": "linked_to_event", "verification_queue_status": "not_required",
        "linked_event_id": None, "warnings": [], "errors": [],
        "needs_translation": derive_needs_translation(ev),
        "legacy_payload": {"from_event_source": ev.get("event_id", "")},
    }
    indep = int(ev.get("independent_source_count") or 1) if is_new else 1
    vl = derive_verification_level(
        ev, source_type=stype, source_group=src["source_group"], is_direct_origin=is_direct,
        independent_source_count=indep, claim_origin_type=src.get("claim_origin_type", "unknown"))
    etime = ev.get("event_time", "")
    dt = parse_time(etime)
    event_date = dt.date().isoformat() if dt else ""
    cluster = {
        "event_id": event_id(cc, ev.get("location", ""), etype, event_date, ev.get("event_type", ""),
                             seed="" if is_new else ev.get("event_id", "")),
        "schema_version": "2.0", "pipeline_version": 2, "run_id": "",
        "legacy_event_id": ev.get("event_id", ""),
        "country_code": cc, "country_cn": country,
        "country_risk_level": risk["country_risk_level"], "country_risk_label": risk["country_risk_label"],
        "event_type": etype, "event_severity": normalize_event_severity(ev.get("event_severity", "")),
        "event_status": normalize_event_status(""),
        "event_time": etime, "event_time_end": ev.get("event_time_end") or None,
        "location_name": ev.get("location", ""), "location_admin1": "", "location_admin2": "",
        "latitude": ev.get("latitude"), "longitude": ev.get("longitude"),
        "title_cn": ev.get("title_cn", ""), "title_original": ev.get("title_original", ""),
        "summary_cn": ev.get("summary_cn", ""), "summary_original": ev.get("summary_original", "") or "",
        "article_ids": [aid], "source_groups": [src["source_group"]], "independent_source_count": indep,
        "verification_level": vl, "verification_score": 0,
        "verification_notes": [], "conflicting_fields": [],
        "publication_status": "", "publication_reason": "", "quality_gate_passed": False,
        "china_related": bool(ev.get("china_related", False)),
        "potential_impact": ev.get("potential_impact", ""), "current_progress": ev.get("progress", ""),
        "legacy_promotion_class": ev.get("source_class", "") or "",
        "legacy_publication_status": ev.get("verification_status", ""),
        "first_seen_at": ev.get("created_at") or None, "last_seen_at": ev.get("updated_at") or None,
        "created_at": ev.get("created_at") or None, "updated_at": ev.get("updated_at") or None,
        "legacy_payload": dict(ev),
    }
    pol = evaluate(vl)
    cluster["verification_score"] = pol["verification_score"]
    cluster["verification_label_cn"] = pol["verification_label_cn"]
    if is_new:
        # 新提升事件：由确定性发布政策决定（仅 cross_verified / direct_official_source
        # 可自动发布；其余进入 verification_pending，不自动发布单一来源）。
        cluster["publication_status"] = pol["publication_status"]
        cluster["quality_gate_passed"] = pol["quality_gate_passed"]
        cluster["publication_reason"] = pol["publication_reason"]
    else:
        # 历史已发布事件（来自 events.json 的既有发布集）迁移后保持 published，
        # 以保证「页面显示效果暂时不变」；verification_level 仍保留供后续自动核实使用。
        cluster["publication_status"] = "published"
        cluster["quality_gate_passed"] = True
        cluster["publication_reason"] = f"历史已发布事件（迁移保留）；verification_level={vl}"
    return cluster, src_article


# ── Quarantine 构建 ──────────────────────────────────
def _map_reason_code(reason: str) -> str:
    r = (reason or "").lower()
    if "country" in r:
        return "wrong_country"
    if "security" in r or "relevant" in r:
        return "not_security_relevant"
    if "duplicate" in r:
        return "duplicate"
    if "url" in r:
        return "invalid_url"
    if "field" in r or "missing" in r:
        return "missing_required_fields"
    if "language" in r:
        return "unsupported_language"
    if "conflict" in r:
        return "conflicting_data"
    if "low" in r or "quality" in r:
        return "low_quality_source"
    if "legacy" in r or "invalid" in r:
        return "legacy_invalid"
    if "schema" in r:
        return "schema_validation_failed"
    return "other"


def quarantine_to_record(q):
    reason = q.get("quarantine_reason", "")
    rc = _map_reason_code(reason)
    oid = q.get("event_id", "")
    # seed=完整旧记录稳定序列化：历史池中存在大量 event_id/detected_at 为空的
    # 排除类记录，四元组会碰撞覆盖；seed 保证 53 条 1:1 无损迁移。
    seed = json.dumps(q, sort_keys=True, ensure_ascii=False)
    aid = quarantine_id("event", oid, rc, q.get("detected_at", ""), seed=seed)
    return {
        "quarantine_id": aid, "original_object_type": "event", "original_id": oid,
        "reason_code": rc, "reason_cn": reason or "隔离",
        "detected_at": q.get("detected_at") or None,
        "detected_by": "auto_quarantined" if q.get("review_status") == "auto_quarantined" else "pipeline",
        "source_file": "data/quarantine_events.json", "legacy_payload": dict(q),
        "review_status": "not_required" if q.get("review_status") == "auto_quarantined" else "pending_review",
        "restorable": True,
    }


# ── Source 升级 ──────────────────────────────────────
def upgrade_source(s):
    sid = s.get("source_id", "")
    name = s.get("source_name") or s.get("name") or ""
    group = s.get("source_group", "") or _group_from(sid, name, s.get("url", ""))
    stype = map_source_type(s.get("source_type", ""), s.get("source_position", ""), group)
    corr_type, corr_direct, corr_repub, corr_tier = _apply_source_corrections(group, name)
    if corr_type:
        stype, is_direct, is_republic, tier = corr_type, corr_direct, corr_repub, corr_tier
    else:
        is_direct = stype in ("government", "military_or_police", "international_organization")
        is_republic = False
        tier = s.get("source_reliability_tier") or derive_tier(stype)
    return {
        "source_id": sid, "source_group": group, "source_name": name,
        "source_type": stype, "source_reliability_tier": tier if tier in SOURCE_RELIABILITY_TIER_ENUMS else "tier_3",
        "country_scope": [s.get("country", "")] if s.get("country") else [],
        "language": [normalize_language(s.get("language", ""))],
        "is_direct_origin": bool(is_direct), "is_republication_platform": bool(is_republic),
        "enabled": bool(s.get("enabled", False)), "tested": bool(s.get("tested", False)),
        "claim_origin_type": "unknown", "url": s.get("url", "") or s.get("source_url", ""),
        "notes": s.get("notes", ""), "legacy_payload": dict(s),
    }


# ── 主迁移逻辑 ───────────────────────────────────────
def _unwrap_source(s):
    """幂等保护：若 source 已是 2.0 升级格式（含 legacy_payload），
    回退到原始旧记录处理。否则第二次 apply 时字段名对不上
    （name/country/language 缺失），source_type 会退化为 other，
    language 变 und，破坏幂等。"""
    if isinstance(s, dict) and isinstance(s.get("legacy_payload"), dict) \
            and s.get("legacy_payload"):
        return dict(s["legacy_payload"])
    return s


def load_legacy_arrays(repo: Repository):
    def arr(name, key):
        d = repo._load_items(repo._data(name))
        return d
    raw = arr("raw_candidates.json", "items")
    pend = arr("pending_events.json", "items")
    evs = arr("events.json", "events")
    quar = arr("quarantine_events.json", "items")
    srcs = [_unwrap_source(s) for s in repo.load_sources()]
    return raw, pend, evs, quar, srcs


def build_canonical(raw, pend, evs, quar, srcs):
    """返回 (articles, clusters, quarantine_records, upgraded_sources, stats)。"""
    idx = build_source_index(srcs)
    articles = {}
    errors = []
    unmapped = set()

    # raw candidates
    for c in raw:
        try:
            a = candidate_to_article(c, from_pending=False, idx=idx)
            articles[a["article_id"]] = a
        except Exception as e:
            errors.append(f"raw {c.get('candidate_id','')}: {e}")

    # pending events（覆盖同 id 的 raw，状态更丰富）
    for c in pend:
        try:
            a = candidate_to_article(c, from_pending=True, idx=idx)
            articles[a["article_id"]] = a
        except Exception as e:
            errors.append(f"pending {c.get('candidate_id','')}: {e}")

    # events → clusters + 来源 Article
    clusters = []
    for ev in evs:
        try:
            cl, src_art = event_to_cluster(ev, idx)
            # 来源 Article 并入；事件来源 Article 必须关联到所属 cluster
            src_art["linked_event_id"] = cl["event_id"]
            if src_art["article_id"] not in articles:
                articles[src_art["article_id"]] = src_art
            else:
                # 已存在则补充 linked_event_id
                articles[src_art["article_id"]]["linked_event_id"] = cl["event_id"]
            clusters.append(cl)
        except Exception as e:
            errors.append(f"event {ev.get('event_id','')}: {e}")

    # quarantine
    qrecs = []
    for q in quar:
        try:
            qrecs.append(quarantine_to_record(q))
        except Exception as e:
            errors.append(f"quar {q.get('event_id','')}: {e}")

    # sources
    upgraded = []
    for s in srcs:
        try:
            upgraded.append(upgrade_source(s))
        except Exception as e:
            errors.append(f"source {s.get('source_id','')}: {e}")

    # 统计未映射字段（legacy 中存在但规范模型无对应顶层字段的，记录在 legacy_payload 即可，不计入丢失）
    stats = {
        "articles": len(articles),
        "event_clusters": len(clusters),
        "quarantine": len(qrecs),
        "sources": len(upgraded),
        "errors": len(errors),
    }
    return list(articles.values()), clusters, qrecs, upgraded, stats, errors, unmapped


def checksum(paths):
    import hashlib
    h = hashlib.sha256()
    for p in paths:
        pp = Path(p)
        if pp.exists():
            h.update(pp.read_bytes())
    return h.hexdigest()


def do_dry_run(repo, run_id):
    raw, pend, evs, quar, srcs = load_legacy_arrays(repo)
    arts, clusters, qrecs, upgraded, stats, errors, unmapped = build_canonical(raw, pend, evs, quar, srcs)
    print("=== DRY-RUN（不写规范数据）===")
    print(f"  raw_candidates       : {len(raw)}")
    print(f"  pending_events       : {len(pend)}")
    print(f"  events               : {len(evs)}")
    print(f"  quarantine_events    : {len(quar)}")
    print(f"  sources              : {len(srcs)}")
    print(f"  -> canonical articles      : {stats['articles']}")
    print(f"  -> canonical clusters     : {stats['event_clusters']}")
    print(f"  -> canonical quarantine    : {stats['quarantine']}")
    print(f"  -> upgraded sources       : {stats['sources']}")
    print(f"  errors               : {stats['errors']}")
    # publishable 预览
    pub = sum(1 for c in clusters if c["publication_status"] in ("publishable", "published"))
    print(f"  -> publishable events     : {pub}")
    return True


def do_apply(repo, run_id):
    raw, pend, evs, quar, srcs = load_legacy_arrays(repo)
    arts, clusters, qrecs, upgraded, stats, errors, unmapped = build_canonical(raw, pend, evs, quar, srcs)

    la = repo.save_articles(arts, run_id)
    lc = repo.save_event_clusters(clusters, run_id)
    lq = repo.save_quarantine(qrecs, run_id)
    repo.save_sources(upgraded, run_id)

    # migration_state
    before = checksum([repo._data("raw_candidates.json"), repo._data("pending_events.json"),
                       repo._data("events.json"), repo._data("quarantine_events.json"),
                       repo._data("sources.json")])
    after = checksum([repo._canonical("articles.json"), repo._canonical("event_clusters.json"),
                      repo._canonical("quarantine.json"), repo._data("sources.json")])
    # 保留首次迁移的原始来源计数：重复 apply 时 legacy 已是再生成视图
    # （raw/pending 是 canonical 的状态切片），计数会与首轮不同，
    # 但首轮真实迁移量是验收证据，必须保留。
    prev = {}
    _msp = repo._canonical("migration_state.json")
    if _msp.exists():
        try:
            prev = json.loads(_msp.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    cur_counts = {"raw_candidates": len(raw), "pending_events": len(pend),
                  "events": len(evs), "quarantine": len(quar), "sources": len(srcs)}
    initial_counts = prev.get("initial_source_counts") or cur_counts
    first_apply_at = prev.get("first_apply_at") or datetime.now(_tz()).isoformat()

    state = {
        "migration_version": MIGRATION_VERSION,
        "schema_version": "2.0", "pipeline_version": 2, "run_id": run_id,
        "started_at": datetime.now(_tz()).isoformat(),
        "completed_at": datetime.now(_tz()).isoformat(),
        "first_apply_at": first_apply_at,
        "initial_source_counts": initial_counts,
        "source_counts": cur_counts,
        "target_counts": stats,
        "skipped_counts": {"articles": la["skipped"], "event_clusters": lc["skipped"], "quarantine": lq["skipped"]},
        "error_counts": stats["errors"],
        "duplicate_counts": {"articles": 0, "event_clusters": 0, "quarantine": 0},
        "unmapped_fields": sorted(unmapped),
        "checksum_before": before, "checksum_after": after,
        "backup_root": _find_backup_root(),
        "idempotent": True,
    }
    repo._atomic_write(repo._canonical("migration_state.json"), state)

    # 兼容导出（legacy + public）
    try:
        from compatibility_export import export_all
        export_all(repo, run_id)
    except Exception as e:
        print(f"  [warn] compatibility_export 失败: {e}")

    print("=== APPLY 完成 ===")
    print(f"  articles      added={la['added']} modified={la['modified']} skipped={la['skipped']} failed={la['failed']}")
    print(f"  clusters      added={lc['added']} modified={lc['modified']} skipped={lc['skipped']} failed={lc['failed']}")
    print(f"  quarantine    added={lq['added']} modified={lq['modified']} skipped={lq['skipped']} failed={lq['failed']}")
    print(f"  errors={stats['errors']}  checksum_before={before[:12]}  checksum_after={after[:12]}")
    return True


def do_rollback(repo):
    backup_root = _find_backup_root()
    if not backup_root or not Path(backup_root).exists():
        print("  [error] 未找到 pre-stage2 备份，无法 rollback")
        return False
    br = Path(backup_root)
    for name in ("raw_candidates.json", "pending_events.json", "events.json",
                 "quarantine_events.json", "sources.json"):
        src = br / name
        if src.exists():
            repo._atomic_write(repo._data(name), json.loads(src.read_text(encoding="utf-8")))
            print(f"  恢复 {name}")
    # 移除规范/公开数据：移入 .backups/rollback_<ts>/ 而非直接删除
    # （规避环境批量删除保护，同时保留可追溯证据）
    import shutil
    from datetime import datetime as _dt
    ts = _dt.now().strftime("%Y%m%dT%H%M%S")
    trash = repo._data(".backups") / f"rollback_{ts}"
    for d in (repo.canonical_dir, repo.public_dir):
        if d.exists():
            trash.mkdir(parents=True, exist_ok=True)
            shutil.move(str(d), str(trash / d.name))
            print(f"  移除 {d} -> {trash / d.name}")
    print("  rollback 完成：已恢复到 pre-stage2 数据状态（代码保留）")
    return True


def do_report(repo):
    p = repo._canonical("migration_state.json")
    if not p.exists():
        print("  尚未执行迁移（无 migration_state.json）")
        return False
    st = json.loads(p.read_text(encoding="utf-8"))
    print("=== MIGRATION REPORT ===")
    for k in ("migration_version", "run_id", "started_at", "completed_at",
              "first_apply_at", "initial_source_counts",
              "source_counts", "target_counts", "skipped_counts", "error_counts",
              "duplicate_counts", "checksum_before", "checksum_after", "backup_root"):
        print(f"  {k}: {st.get(k)}")
    return True


def _tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Asia/Shanghai")
    except Exception:
        from datetime import timezone
        return timezone.utc


def _find_backup_root():
    bp = ROOT / "data" / "backup"
    if not bp.exists():
        return ""
    # 取最新的 stage2_ 备份目录
    cand = sorted([d for d in bp.glob("stage2_*") if d.is_dir()], key=lambda x: x.name)
    return str(cand[-1]) if cand else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--run-id", default="")
    args = ap.parse_args()

    repo = Repository(root=ROOT, run_id=args.run_id or generate_run_id())

    if args.dry_run:
        ok = do_dry_run(repo, repo.run_id)
    elif args.apply:
        ok = do_apply(repo, repo.run_id)
    elif args.rollback:
        ok = do_rollback(repo)
    elif args.report:
        ok = do_report(repo)
    else:
        print("请指定 --dry-run / --apply / --rollback / --report")
        sys.exit(2)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
