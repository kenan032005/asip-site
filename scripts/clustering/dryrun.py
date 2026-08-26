#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6A — 真实 Dry Run（§十七-§十九）。

输入：Source Expansion A+B 最近 72h internal candidate pool
（data/runtime/country_discovery_audit.json + global_discovery_audit.json）。
流程：article dedup → same-event clustering → 统计 → review pack。
只写 data/runtime/clustering/ 与 docs/stage6-cluster-review-pack.json。
不写 Canonical/Public；AI calls=0。
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.clustering.dedup import dedup_articles
from scripts.clustering.cluster import cluster_candidates
from scripts.clustering.sources import independent_group_key
from scripts.global_source.registry import load_registry, load_country_registry

RUNTIME = ROOT / "data" / "runtime" / "clustering"
REVIEW_PACK_PATH = ROOT / "docs" / "stage6-cluster-review-pack.json"


def _load_candidates():
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


def to_article(c, tier_map):
    """candidate → clustering article（字段映射）。"""
    pub = c.get("published_at") or None
    country = c.get("country_iso3") or (c.get("country_hints") or [None])[0]
    return {
        "candidate_id": c.get("candidate_id"),
        "article_id": c.get("candidate_id"),
        "source_id": c.get("source_id"),
        "source_group": c.get("source_group"),
        "trust_tier": tier_map.get(c.get("source_id"), "C"),
        "title": c.get("title") or "",
        "url": c.get("url") or "",
        "canonical_url": c.get("url") or "",
        "original_url": c.get("original_url"),
        "original_publisher": c.get("original_publisher"),
        "content_hash": None,
        "published_at": pub,
        "event_time": pub,
        "primary_country_iso3": country,
        "affected_countries": [],
        "location": None,
        "event_type": None,
        "actor": None,
        "target": None,
        "facility": None,
        "casualties": None,
        "numeric_facts": [],
        "body": None,
        "body_extracted": None,
    }


def run_dryrun():
    cands = _load_candidates()
    tier_map = _tier_map()
    articles = [to_article(c, tier_map) for c in cands]
    articles = [a for a in articles if a["title"]]

    unique, dups = dedup_articles([dict(a) for a in articles])
    clusters, stats, decisions = cluster_candidates(unique)

    run_id = time.strftime("CLU%Y%m%dT%H%M%S+0800")
    stats["run_id"] = run_id
    stats["input_candidates"] = len(articles)
    stats["duplicate_articles"] = len(dups)
    stats["unique_articles"] = len(unique)
    stats["candidate_pairs_evaluated"] = stats.get("candidate_pairs_evaluated", 0)
    stats["cross_country_reject_count"] = stats.get("cross_country_reject_count", 0)

    # review pack（§十九）：≤20 组，优先 multi-source cluster；不足用高分边界对补齐
    review = []
    multi = [m for m in clusters if len(m["member_ids"]) >= 2]
    multi.sort(key=lambda m: (-m["cluster_confidence"], m["cluster_status"] == "needs_review"))
    by_id = {a["candidate_id"]: a for a in unique}
    for m in multi[:20]:
        members = [by_id.get(mid) for mid in m["member_ids"] if by_id.get(mid)]
        review.append({
            "master_event_id": m["master_event_id"],
            "cluster_status": m["cluster_status"],
            "cluster_confidence": m["cluster_confidence"],
            "independent_source_count": m["independent_source_count"],
            "source_groups": m["source_groups"],
            "conflict_flags": m["conflict_flags"],
            "member_ids": m["member_ids"],
            "sources": [{"source_id": x["source_id"], "source_group": x["source_group"],
                         "country": x["primary_country_iso3"],
                         "published_at": x["published_at"],
                         "title": (x["title"] or "")[:120],
                         "url": x["url"]} for x in members],
        })
    # 无 cluster 时用 decisions 中最高分（接近 review 阈值）的边界对
    if len(review) < 20 and decisions:
        top = sorted(decisions, key=lambda d: -d.get("score", 0))[:20 - len(review)]
        for d in top:
            if d.get("score", 0) < 20:
                break
            review.append({
                "pair_id": "boundary_%s" % len(review),
                "candidate_a": d.get("anchor"), "candidate_b": d.get("candidate"),
                "score": d.get("score"), "verdict": d.get("verdict"),
                "reason": d.get("reason"), "features": d.get("features", []),
                "conflict_flags": d.get("conflict_flags", []),
            })
    REVIEW_PACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PACK_PATH.write_text(json.dumps({
        "run_id": run_id, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "count": len(review), "clusters": review,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    RUNTIME.mkdir(parents=True, exist_ok=True)
    (RUNTIME / "clusters.json").write_text(
        json.dumps({"run_id": run_id, "clusters": clusters}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (RUNTIME / "decisions.json").write_text(
        json.dumps({"run_id": run_id, "decisions": decisions}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (RUNTIME / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats, clusters, review


def main():
    stats, clusters, review = run_dryrun()
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print("review pack: %d clusters -> docs/stage6-cluster-review-pack.json" % len(review))
    return 0


if __name__ == "__main__":
    sys.exit(main())
