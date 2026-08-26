#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6A Completion — Detail-Enriched Real Clustering Validation（§四-§十三）。

流程：listing candidates（A+B）→ retrieval prioritization → detail fetch →
deterministic feature extraction → article dedup → true pre-pair blocking →
block 内 clustering → review pack v2。
AI calls=0；只写 data/runtime/clustering/ 与 docs/；不写 Canonical/Public。
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.clustering.dedup import dedup_articles
from scripts.clustering.blocking import build_blocks
from scripts.clustering.cluster import cluster_candidates
from scripts.clustering.enrich import enrich_candidate, retrieval_priority
from scripts.global_source.detail import detail_extract
from scripts.global_source.registry import load_registry, load_country_registry

RUNTIME = ROOT / "data" / "runtime" / "clustering"
REVIEW_PACK_V2 = ROOT / "docs" / "stage6-cluster-review-pack-v2.json"
DETAIL_TARGET = 120          # §六 目标 100-150 条
DETAIL_TIMEOUT_SEC = 8


def _load_listing_candidates():
    cands = []
    c = json.load(open(RUNTIME.parent / "country_discovery_audit.json", encoding="utf-8"))
    cands.extend(c.get("candidates", []))
    g = json.load(open(RUNTIME.parent / "global_discovery_audit.json", encoding="utf-8"))
    cands.extend(g.get("candidates", []))
    return cands


def _tier_map():
    m = {}
    for reg in (load_registry(), load_country_registry()):
        sources, _ = reg
        for s in sources:
            m[s["source_id"]] = s.get("trust_tier")
    return m


def _to_listing_article(c, tier_map):
    """listing candidate → enrich 前的基础 article（含 source/时间字段）。
    country 规范化：ISO2（global hints）→ ISO3。"""
    pub = c.get("published_at") or None
    iso2to3 = {"TD": "TCD", "NE": "NER", "SS": "SSD", "BJ": "BEN", "ET": "ETH",
               "SD": "SDN", "ML": "MLI", "BF": "BFA", "NG": "NGA", "CM": "CMR",
               "CD": "COD", "CG": "COG", "KE": "KEN", "UG": "UGA", "TZ": "TZA",
               "ZA": "ZAF", "GH": "GHA", "SN": "SEN", "CI": "CIV", "DZ": "DZA",
               "MA": "MAR", "EG": "EGY", "LY": "LBY", "TN": "TUN", "SO": "SOM",
               "ER": "ERI", "DJ": "DJI", "RW": "RWA", "BI": "BDI", "MG": "MDG",
               "ZM": "ZMB", "ZW": "ZWE", "MZ": "MOZ", "AO": "AGO", "NA": "NAM",
               "BW": "BWA", "MW": "MWI", "GA": "GAB", "GN": "GIN", "SL": "SLE",
               "LR": "LBR", "TG": "TGO", "BJ": "BEN"}
    raw_country = (c.get("country_iso3")
                   or (c.get("country_hints") or [None])[0])
    country = iso2to3.get(str(raw_country).upper(), raw_country) if raw_country else None
    return {
        "candidate_id": c.get("candidate_id"),
        "article_id": c.get("candidate_id"),
        "source_id": c.get("source_id"),
        "source_group": c.get("source_group"),
        "trust_tier": tier_map.get(c.get("source_id"), "C"),
        "title": c.get("title") or "",
        "url": c.get("url") or "",
        "published_at": pub,
        "event_time": pub,
        "primary_country_iso3": country,
        "country_hints": c.get("country_hints") or [],
        "original_url": c.get("original_url"),
        "original_publisher": c.get("original_publisher"),
        "discovery_run_id": c.get("discovery_run_id"),
    }


def run_completion(max_detail=DETAIL_TARGET):
    listing = _load_listing_candidates()
    tier_map = _tier_map()
    base = [_to_listing_article(c, tier_map) for c in listing]
    base = [a for a in base if a["title"]]

    # §七 retrieval prioritization：同国同日多源组优先
    ordered = retrieval_priority(base)

    # §六 detail fetch（目标 max_detail 条；失败记 failure_type）
    detail_attempted = detail_success = detail_failed = 0
    enriched = []
    for a in ordered:
        if detail_attempted >= max_detail:
            break
        detail_attempted += 1
        d = detail_extract(a.get("url") or "", a.get("source_id"),
                           language_hint=None)
        if d["detail_success"]:
            detail_success += 1
        else:
            detail_failed += 1
        e = enrich_candidate(a, d)
        e["failure_type"] = d.get("failure_type")
        enriched.append(e)

    # §八 dedup 重算
    unique, dups = dedup_articles([dict(e) for e in enriched])

    # §二/§三 true blocking
    blocks, block_stats = build_blocks(unique)

    # block 内聚类
    clusters, stats, decisions = cluster_candidates(unique, blocks=blocks)

    # §十一 review pack v2（20 组）
    review = _build_review_v2(clusters, decisions, unique, blocks)

    run_id = time.strftime("CLU2%Y%m%dT%H%M%S+0800")
    stats.update({
        "run_id": run_id,
        "input_listing_candidates": len(base),
        "detail_attempted": detail_attempted,
        "detail_success": detail_success,
        "detail_failed": detail_failed,
        "detail_enriched_candidates": len(enriched),
        "duplicate_articles": len(dups),
        "unique_articles": len(unique),
        "all_possible_pairs": block_stats["all_possible_pairs"],
        "blocked_candidate_pairs": block_stats["blocked_candidate_pairs"],
        "blocking_reduction_ratio": block_stats["reduction_ratio"],
        "pairs_by_country": block_stats["pairs_by_country"],
        "time_basis_counts": block_stats["time_basis_counts"],
        "blocks_with_articles": block_stats["blocks_with_articles"],
        "review_pack_count": len(review),
    })

    RUNTIME.mkdir(parents=True, exist_ok=True)
    (RUNTIME / "clusters-v2.json").write_text(
        json.dumps({"run_id": run_id, "clusters": clusters}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (RUNTIME / "decisions-v2.json").write_text(
        json.dumps({"run_id": run_id, "decisions": decisions}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (RUNTIME / "stats-v2.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    (RUNTIME / "enriched-v2.json").write_text(
        json.dumps({"run_id": run_id, "enriched": enriched}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    REVIEW_PACK_V2.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PACK_V2.write_text(json.dumps({
        "run_id": run_id, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "count": len(review), "pairs": review,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats, clusters, review, enriched


def _build_review_v2(clusters, decisions, unique, blocks):
    """§十一-§十二 Review Pack v2：最多 20 组。
    优先级：auto_clustered 真实 pair → needs_review → score 45-54 边界 →
    高风险 false-merge（hard reject 但标题高度相似）。"""
    by_id = {u.get("candidate_id"): u for u in unique}

    def snip(e):
        b = (e or {}).get("body_snippet") or (e or {}).get("body_extracted") or ""
        return b[:400]

    out = []
    # 1) auto / review 真实 pair（来自 decisions）
    auto_review = [d for d in decisions if d.get("verdict") in ("auto", "review")]
    auto_review.sort(key=lambda d: -d.get("score", 0))
    for d in auto_review:
        a = by_id.get(d.get("anchor"))
        b = by_id.get(d.get("candidate"))
        if not a or not b:
            continue
        out.append(_review_row(d, a, b, snip))
        if len(out) >= 20:
            return out
    # 2) score 45-54 边界
    boundary = [d for d in decisions if 45 <= d.get("score", 0) < 55]
    boundary.sort(key=lambda d: -d.get("score", 0))
    for d in boundary:
        a = by_id.get(d.get("anchor"))
        b = by_id.get(d.get("candidate"))
        if not a or not b:
            continue
        out.append(_review_row(d, a, b, snip))
        if len(out) >= 20:
            return out
    # 3) 高风险 false-merge：hard reject 但标题相似
    risky = [d for d in decisions if d.get("rejected")
             and any(f.startswith("title_similarity") for f in d.get("features", []))]
    for d in risky[:20 - len(out)]:
        a = by_id.get(d.get("anchor"))
        b = by_id.get(d.get("candidate"))
        if not a or not b:
            continue
        out.append(_review_row(d, a, b, snip))
        if len(out) >= 20:
            return out
    return out


def _review_row(d, a, b, snip):
    return {
        "pair_id": "r_%s__%s" % (a["candidate_id"], b["candidate_id"]),
        "candidate_a_id": a["candidate_id"], "candidate_b_id": b["candidate_id"],
        "source_a": a["source_id"], "source_b": b["source_id"],
        "source_group_a": a["source_group"], "source_group_b": b["source_group"],
        "country_a": a["primary_country_iso3"], "country_b": b["primary_country_iso3"],
        "published_at_a": a["published_at"], "published_at_b": b["published_at"],
        "event_time_a": a["event_time"], "event_time_b": b["event_time"],
        "time_basis": "published_at",
        "location_a": a["location"], "location_b": b["location"],
        "location_hints_a": a.get("location_hints") or [], "location_hints_b": b.get("location_hints") or [],
        "event_type_a": a["event_type_hint"], "event_type_b": b["event_type_hint"],
        "title_a": a["title"][:150], "title_b": b["title"][:150],
        "body_snippet_a": snip(a), "body_snippet_b": snip(b),
        "numeric_facts_a": a.get("numeric_facts") or [], "numeric_facts_b": b.get("numeric_facts") or [],
        "actor_hints_a": a.get("named_entity_hints") or [], "actor_hints_b": b.get("named_entity_hints") or [],
        "feature_score": d.get("score"),
        "feature_breakdown": d.get("features"),
        "hard_reject": d.get("rejected"), "hard_reject_reason": d.get("reason"),
        "engine_decision": d.get("verdict"),
        "conflict_flags": d.get("conflict_flags"),
    }


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-detail", type=int, default=DETAIL_TARGET)
    args = ap.parse_args(argv)
    stats, clusters, review, enriched = run_completion(max_detail=args.max_detail)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print("review pack v2: %d pairs -> docs/stage6-cluster-review-pack-v2.json" % len(review))
    return 0


if __name__ == "__main__":
    sys.exit(main())
