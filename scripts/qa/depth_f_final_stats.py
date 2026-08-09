#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH F final stats: post-upgrade entity/relation page stats + pre/post
maturity comparison via git show of baseline (Depth E closed 0c11c93)."""
import json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-f"

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

ENTS = ["actor-sspdf","actor-splm-io","actor-nas","person-salva-kiir","person-riek-machar",
        "actor-is-mozambique","actor-fadm","actor-rdf-mozambique","actor-samim","actor-tanzania-tpdf",
        "actor-lna","actor-gnu-forces","actor-isis-libya"]
RELS = ["rel-splm-io-sspdf-conflict","rel-kiir-sspdf-leads","rel-machar-splm-io-leads","rel-nas-splm-io-allied",
        "rel-is-moz-islamic-state","rel-is-moz-islamic-state2","rel-fadm-is-moz-hostile","rel-rdf-mozambique-fadm-cooperate",
        "rel-samim-fadm-cooperate","rel-is-moz-tanzania-link","rel-fadm-mozambique-operates","rel-is-moz-mozambique-operates",
        "rel-tanzania-tpdf-is-moz","rel-tanzania-mozambique-cooperate","rel-tanzania-samim-member",
        "rel-lna-gnu-rivalry","rel-isis-libya-affiliation","rel-isis-libya-lna-conflict"]

pre_ent, pre_rel = {}, {}
try:
    out = subprocess.run(["git", "show", "0c11c93:data/intelligence/africa/entity_profiles.json"],
                         capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if out.returncode == 0:
        pre_ep = json.loads(out.stdout)["profiles"]
        pre_ent = {eid: (pre_ep.get(eid, {}).get("content_maturity") or "E0_STUB (no maturity)") for eid in ENTS}
    out2 = subprocess.run(["git", "show", "0c11c93:data/intelligence/africa/relation_profiles.json"],
                          capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if out2.returncode == 0:
        pre_rp = json.loads(out2.stdout)["profiles"]
        pre_rel = {rid: (pre_rp.get(rid, {}).get("relation_maturity") or "R0_EDGE_ONLY (no maturity)") for rid in RELS}
except Exception as e:
    print("git show fallback:", e)

ent_cmp = []
for eid in ENTS:
    pr = ep.get(eid, {})
    secs = pr.get("sections", {})
    e = next((x for x in entities if x["entity_id"] == eid), {})
    ent_cmp.append({"entity_id": eid, "pre_maturity": pre_ent.get(eid, "?"), "maturity": pr.get("content_maturity"),
                    "depth_score": pr.get("depth_score"), "sections": len(secs), "zh_chars": zh_len(secs),
                    "freshness": e.get("freshness_status"), "current_status": str(e.get("current_status", ""))[:60],
                    "asip_analysis": bool(secs.get("asip_analysis"))})

rel_cmp = []
for rid in RELS:
    pr = rp.get(rid, {})
    base = next((r for r in rels if r["relationship_id"] == rid), {})
    rel_cmp.append({"relationship_id": rid, "pre_maturity": pre_rel.get(rid, "?"), "maturity": pr.get("relation_maturity"),
                    "type": base.get("relationship_type"), "freshness": base.get("freshness_status"),
                    "current_status": str(base.get("current_status", ""))[:50],
                    "timeline_items": len(tl.get(rid, [])), "asip_analysis": bool(pr.get("asip_analysis"))})

db_ev = [e for e in evidence if str(e.get("claim_id", "")).startswith("depthf")]
out = {
    "artifact": "DEPTHF_UPGRADE_COMPARISON",
    "entity_upgrades": ent_cmp,
    "relation_upgrades": rel_cmp,
    "evidence": {"depthf_imported": len(db_ev),
                 "by_status": {s: sum(1 for e in db_ev if e["verification_status"] == s) for s in ("verified", "partially_verified")}},
    "sources": {"total": len(sources), "depthf_added": 24, "reused": ["LIBYA_UNSMIL_2026_06_07"]},
}
json.dump(out, open(QA / "upgrade-comparison.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("== entities ==")
for x in ent_cmp:
    print(f"  {x['entity_id']}: {x['pre_maturity']} -> {x['maturity']} | secs={x['sections']} zh={x['zh_chars']} freshness={x['freshness']} | status={x['current_status']}")
print("== relations ==")
for x in rel_cmp:
    print(f"  {x['relationship_id']}: {x['pre_maturity']} -> {x['maturity']} | type={x['type']} tl={x['timeline_items']} | {x['current_status']}")
print("evidence:", out["evidence"])
