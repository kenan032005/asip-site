#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6B §二十三-§二十六 — 真实 Timeline Dry-run + Review Pack。

Social：Stage6A master events（clusters-v2.json）+ detail-enriched candidates
（enriched-v2.json）构造 timeline；不写 Public，不强行制造 update。
Disease：现有 Disease Canonical（outbreak_events.json 20 条）生成 outbreak
timeline（previous/supersedes 链优先）。

输出（仅 internal / docs）：
  data/runtime/timeline/social_timelines.json
  data/runtime/timeline/disease_timelines.json
  data/runtime/timeline/stats.json
  docs/stage6b-update-review-pack.json
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "data" / "runtime" / "timeline"
REVIEW_PACK = ROOT / "docs" / "stage6b-update-review-pack.json"

sys.path.insert(0, str(ROOT))

from scripts.timeline.social import build_social_timelines, new_timeline, apply_update  # noqa: E402
from scripts.timeline.disease import build_outbreak_timelines  # noqa: E402
from scripts.timeline.country_attr import attribute_event_country  # noqa: E402


def _load_clusters():
    p = ROOT / "data" / "runtime" / "clustering" / "clusters-v2.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("clusters", [])


def _load_enriched():
    p = ROOT / "data" / "runtime" / "clustering" / "enriched-v2.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("enriched", d.get("articles", []))
    return {a.get("candidate_id") or a.get("article_id"): a for a in items}


def _load_disease():
    p = ROOT / "data" / "disease" / "canonical" / "outbreak_events.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    return d if isinstance(d, list) else d.get("items", d.get("events", []))


def _to_social_article(cand, attr):
    """enriched candidate → social timeline article（§二 event country 优先）。"""
    pub = cand.get("published_at")
    return {
        "article_id": cand.get("candidate_id") or cand.get("article_id"),
        "candidate_id": cand.get("candidate_id"),
        "source_id": cand.get("source_id"),
        "source_group": cand.get("source_group"),
        "title": cand.get("title") or "",
        "url": cand.get("canonical_url") or cand.get("url") or "",
        "canonical_url": cand.get("canonical_url"),
        "published_at": pub,
        "event_time": cand.get("event_time") or cand.get("event_time_candidate"),
        "location": cand.get("location") or cand.get("location_hints"),
        "event_type": cand.get("event_type") or cand.get("event_type_hint"),
        "deaths": None,
        "injured": None,
        "actor": cand.get("actor"),
        "body": cand.get("body_extracted") or cand.get("body_snippet"),
        "body_extracted": cand.get("body_extracted"),
        "event_primary_country": attr["event_primary_country"] or
            cand.get("primary_country_iso3"),
        "mentioned_countries": cand.get("mentioned_countries") or attr["mentioned_countries"],
        "content_hash": cand.get("content_hash"),
        "primary_country_iso3": attr["event_primary_country"] or
            cand.get("primary_country_iso3"),
    }


def run_social(clusters, enriched):
    """从 Stage6A master events + enriched candidates 构造 timelines。"""
    timelines = []
    stats = {"master_events_processed": 0, "timelines_created": 0,
             "updates_created": 0, "casualty_updates": 0, "actor_updates": 0,
             "official_confirmations": 0, "corrections": 0, "conflicts": 0,
             "closed_timelines": 0, "skipped_no_published_at": 0}
    for me in clusters:
        mids = me.get("member_ids") or []
        arts = []
        for m in mids:
            cand = enriched.get(m)
            if not cand:
                continue
            attr = attribute_event_country(cand, {"source_id": cand.get("source_id")})
            a = _to_social_article(cand, attr)
            if not a.get("published_at"):
                stats["skipped_no_published_at"] += 1
                continue
            arts.append(a)
        if not arts:
            continue
        stats["master_events_processed"] += 1
        arts.sort(key=lambda a: str(a.get("published_at") or ""))
        tl = None
        for i, a in enumerate(arts):
            if tl is None:
                tl = new_timeline(me.get("master_event_id"), a)
                stats["updates_created"] += 1
            else:
                tl, upd, flags = apply_update(tl, a)
                stats["updates_created"] += 1
                stats["casualty_updates"] += upd["update_type"] == "casualty_update"
                stats["actor_updates"] += upd["update_type"] == "actor_attribution_update"
                stats["official_confirmations"] += upd["update_type"] == "official_confirmation"
                stats["corrections"] += upd["update_type"] == "correction"
                stats["conflicts"] += len(flags)
        timelines.append(tl)
    stats["timelines_created"] = len(timelines)
    stats["closed_timelines"] = sum(1 for t in timelines
                                    if t["timeline_status"] == "closed")
    return timelines, stats


def main():
    run_id = time.strftime("TLRUN%Y%m%dT%H%M%S+0800")

    # ── Social ──
    clusters = _load_clusters()
    enriched = _load_enriched()
    social_tls, social_stats = run_social(clusters, enriched)

    # ── Disease ──
    disease_events = _load_disease()
    disease_tls, disease_stats, orphans = build_outbreak_timelines(disease_events)

    # ── 持久化（internal only）──
    RUNTIME.mkdir(parents=True, exist_ok=True)
    (RUNTIME / "social_timelines.json").write_text(
        json.dumps({"run_id": run_id, "timelines": social_tls},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (RUNTIME / "disease_timelines.json").write_text(
        json.dumps({"run_id": run_id, "timelines": disease_tls},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    stats_doc = {"run_id": run_id, "social": social_stats,
                 "disease": disease_stats,
                 "disease_orphans": [o.get("disease_event_id") for o in orphans]}
    (RUNTIME / "stats.json").write_text(
        json.dumps(stats_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── Review Pack（§二十六 ≤15 组）──
    review = _build_review(social_tls, disease_tls)
    REVIEW_PACK.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PACK.write_text(json.dumps(
        {"run_id": run_id, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
         "count": len(review), "pairs": review}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    # ── 报告输出 ──
    print(json.dumps({"run_id": run_id, "social": social_stats,
                      "disease": disease_stats, "review_pack_count": len(review),
                      "disease_orphans": len(orphans)}, ensure_ascii=False, indent=2))
    return 0


def _build_review(social_tls, disease_tls):
    """§二十六 review pack：优先真实 update 链 / numeric conflict /
    actor attribution 变化 / geographic spread。≤15 组。"""
    review = []

    # 1. Social 多 update 真实 timeline（update 链候选）
    for tl in social_tls:
        if len(tl["updates"]) >= 2 and len(review) < 15:
            review.append({
                "type": "social_timeline",
                "timeline_id": tl["timeline_id"],
                "master_event_id": tl["master_event_id"],
                "timeline_status": tl["timeline_status"],
                "source_count": tl["source_count"],
                "independent_source_count": tl["independent_source_count"],
                "conflict_flags": tl["conflict_flags"],
                "updates": [{
                    "update_id": u["update_id"], "update_type": u["update_type"],
                    "source_id": u["source_id"], "published_at": u["published_at"],
                    "title": (u["evidence"] or {}).get("title", "")[:120],
                } for u in tl["updates"]],
            })

    # 2. Disease update 链（真实 supersede 链）
    for tl in disease_tls:
        if len(tl["updates"]) >= 2 and len(review) < 15:
            review.append({
                "type": "disease_timeline",
                "outbreak_id": tl["outbreak_id"],
                "disease_id": tl["disease_id"],
                "country_iso3": tl["country_iso3"],
                "outbreak_status": tl["outbreak_status"],
                "numeric_conflicts": tl["numeric_conflicts"],
                "updates": [{
                    "update_id": u["update_id"], "update_type": u["update_type"],
                    "report_date": u["report_date"],
                    "confirmed_cases": u["confirmed_cases"], "deaths": u["deaths"],
                    "admin1": u["affected_admin1"],
                } for u in tl["updates"]],
            })
    return review[:15]


if __name__ == "__main__":
    sys.exit(main())
