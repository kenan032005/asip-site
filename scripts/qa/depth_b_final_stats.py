#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH B final stats: per-page section/char counts for upgraded entities and
relations, plus pre/post maturity comparison reconstructed from packet targets
vs baseline Depth A state (git show). Writes upgrade-comparison.json and
final page stats into qa-artifacts-depth-b."""
import json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-b"

def load(name):
    return json.load(open(DATA / name, encoding="utf-8"))

def zh_len(o):
    def walk(x):
        if isinstance(x, str):
            return sum(1 for c in x if "\u4e00" <= c <= "\u9fff")
        if isinstance(x, list):
            return sum(walk(i) for i in x)
        if isinstance(x, dict):
            return sum(walk(v) for v in x.values())
        return 0
    return walk(o)

entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
ep = load("entity_profiles.json")["profiles"]
rp = load("relation_profiles.json")["profiles"]
tl = load("relation_timelines.json")["timelines"]
sources = load("sources.json")["sources"]
evidence = load("evidence_records.json")["evidence"]

ENT_TARGETS = ["actor-jas","actor-iswap","actor-mnjtf","actor-nigeria-army","actor-chad-army","actor-cameroon-army","actor-lakurawa","actor-ansaru"]
REL_TARGETS = ["rel-jas-iswap-conflict","rel-jas-islamic-state-hostile","rel-iswap-islamic-state-affiliation",
               "rel-nigeria-mnjtf-member","rel-chad-mnjtf-member","rel-cameroon-mnjtf-member",
               "rel-cameroon-army-jas","rel-cameroon-army-iswap","rel-d1-ansaru-jas-split",
               "rel-d1-ansaru-aqim-allegiance","rel-d1-ansaru-jnim-affiliation"]

ent_cmp = []
for eid in ENT_TARGETS:
    pr = ep.get(eid, {})
    secs = pr.get("sections", {})
    ent_cmp.append({
        "entity_id": eid, "maturity": pr.get("content_maturity"), "depth_score": pr.get("depth_score"),
        "sections": len(secs), "zh_chars": zh_len(secs), "asip_analysis": bool(secs.get("asip_analysis")),
        "watch_indicators": bool(secs.get("watch_indicators")),
    })

rel_cmp = []
for rid in REL_TARGETS:
    pr = rp.get(rid, {})
    base = next((r for r in rels if r["relationship_id"] == rid), {})
    rel_cmp.append({
        "relationship_id": rid, "maturity": pr.get("relation_maturity"),
        "type": base.get("relationship_type"), "status": base.get("current_status"),
        "freshness": base.get("freshness_status"), "timeline_items": len(tl.get(rid, [])),
        "asip_analysis": bool(pr.get("asip_analysis")), "watch_indicators": bool(pr.get("watch_indicators")),
        "source_ids": len(pr.get("source_ids", [])),
    })

# pre-upgrade maturity: derive from packet (targets) — pre was None (no maturity) for all 8/11
pre_ent = {eid: "E0_STUB (no Depth A maturity)" for eid in ENT_TARGETS}
pre_rel = {rid: "R0_EDGE_ONLY (no Depth A maturity)" for rid in REL_TARGETS}
# verify pre state via git show of baseline (Depth A closed) for the 8 entities
try:
    out = subprocess.run(["git", "show", "8f0f325:data/intelligence/africa/entity_profiles.json"],
                         capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if out.returncode == 0:
        pre_ep = json.loads(out.stdout)["profiles"]
        pre_ent = {eid: (pre_ep.get(eid, {}).get("content_maturity") or "E0_STUB (no maturity)") for eid in ENT_TARGETS}
    out2 = subprocess.run(["git", "show", "8f0f325:data/intelligence/africa/relation_profiles.json"],
                          capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if out2.returncode == 0:
        pre_rp = json.loads(out2.stdout)["profiles"]
        pre_rel = {rid: (pre_rp.get(rid, {}).get("relation_maturity") or "R0_EDGE_ONLY (no maturity)") for rid in REL_TARGETS}
except Exception as e:
    print("git show fallback skipped:", e)

# page stats for E3/R3 priority pages
page_stats = {}
for eid in ENT_TARGETS:
    pr = ep.get(eid, {})
    secs = pr.get("sections", {})
    page_stats[eid] = {"sections": len(secs), "zh_chars": zh_len(secs), "maturity": pr.get("content_maturity")}
for rid in REL_TARGETS:
    pr = rp.get(rid, {})
    page_stats[rid] = {"profile_fields": len(pr), "timeline_items": len(tl.get(rid, [])), "maturity": pr.get("relation_maturity")}

db_ev = [e for e in evidence if str(e.get("claim_id", "")).startswith("depthb")]
out = {
    "artifact": "DEPTHB_UPGRADE_COMPARISON",
    "pre_entity_maturity": pre_ent,
    "post_entity": ent_cmp,
    "pre_relation_maturity": pre_rel,
    "post_relation": rel_cmp,
    "page_stats": page_stats,
    "evidence": {"depthb_imported": len(db_ev),
                 "by_status": {s: sum(1 for e in db_ev if e["verification_status"] == s) for s in ("verified", "partially_verified")},
                 "by_claim_type": {t: sum(1 for e in db_ev if e["claim_type"] == t) for t in ("fact", "estimate", "analysis")}},
    "sources": {"total": len(sources), "depthb_added": 10, "reused": ["d1-acled-africa-june-2026", "d2-un-s2026-44", "iss-mnjtf-lakechad-2025"]},
}
json.dump(out, open(QA / "upgrade-comparison.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("pre entities:", {k: v for k, v in pre_ent.items() if v != "E0_STUB (no Depth A maturity)"})
print("post entities:")
for x in ent_cmp:
    print(f"  {x['entity_id']}: {x['maturity']} | sections={x['sections']} zh={x['zh_chars']} analysis={x['asip_analysis']} watch={x['watch_indicators']}")
print("post relations:")
for x in rel_cmp:
    print(f"  {x['relationship_id']}: {x['maturity']} | type={x['type']} | tl={x['timeline_items']} | analysis={x['asip_analysis']} watch={x['watch_indicators']}")
print("evidence:", out["evidence"])
