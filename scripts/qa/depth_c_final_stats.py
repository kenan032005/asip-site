#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH C final stats: post-upgrade entity/relation page stats + pre/post
maturity comparison via git show of baseline (Depth B closed 9cc55fb)."""
import json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-c"

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

ENTS = ["actor-dan-na-ambassagou","person-youssouf-toloba","actor-dozos-of-macina","person-amadou-nionson-diarra",
        "actor-dana-atem","person-sidi-ongoiba","actor-katiba-serma","person-jafar-dicko","person-ousmane-dicko","person-abou-ghosmane"]
RELS = ["rel-d1-dan-na-jnim-conflict","rel-d1-dan-na-fama-coop","rel-d2-dan-na-toloba-led","rel-d2-dana-dan-na-split",
        "rel-d2-dana-sidi-led","rel-d2-dana-katiba-serma-conflict","rel-d2-dana-ansarul-conflict","rel-d2-dana-fama-coop",
        "rel-d2-dozos-macina-amadou-led","rel-d2-dozos-macina-jnim-conflict","rel-d2-dozos-macina-fama-coop",
        "rel-d2-katiba-serma-jnim","rel-d2-jafar-jnim","rel-d2-ansarul-jafar-led","rel-d2-ousmane-jnim","rel-d2-ghosmane-jnim"]

# pre maturity from baseline (Depth B closed = HEAD~3 in this branch, use git show 9cc55fb)
pre_ent, pre_rel = {}, {}
try:
    out = subprocess.run(["git", "show", "9cc55fb:data/intelligence/africa/entity_profiles.json"],
                         capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if out.returncode == 0:
        pre_ep = json.loads(out.stdout)["profiles"]
        pre_ent = {eid: (pre_ep.get(eid, {}).get("content_maturity") or "E0_STUB (no maturity)") for eid in ENTS}
    out2 = subprocess.run(["git", "show", "9cc55fb:data/intelligence/africa/relation_profiles.json"],
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
                    "freshness": e.get("freshness_status"), "asip_analysis": bool(secs.get("asip_analysis")),
                    "watch_indicators": bool(secs.get("watch_indicators"))})

rel_cmp = []
for rid in RELS:
    pr = rp.get(rid, {})
    base = next((r for r in rels if r["relationship_id"] == rid), {})
    rel_cmp.append({"relationship_id": rid, "pre_maturity": pre_rel.get(rid, "?"), "maturity": pr.get("relation_maturity"),
                    "type": base.get("relationship_type"), "freshness": base.get("freshness_status"),
                    "timeline_items": len(tl.get(rid, [])), "asip_analysis": bool(pr.get("asip_analysis")),
                    "watch_indicators": bool(pr.get("watch_indicators"))})

db_ev = [e for e in evidence if str(e.get("claim_id", "")).startswith("depthc")]
out = {
    "artifact": "DEPTHC_UPGRADE_COMPARISON",
    "entity_upgrades": ent_cmp,
    "relation_upgrades": rel_cmp,
    "evidence": {"depthc_imported": len(db_ev), "by_status": {s: sum(1 for e in db_ev if e["verification_status"] == s) for s in ("verified", "partially_verified")}},
    "sources": {"total": len(sources), "depthc_added": 0, "reused": ["d1-acled-dozo-2026", "d1-acled-africa-june-2026", "d2-hrw-burkina-2026-04-02", "d2-un-s2026-44"]},
}
json.dump(out, open(QA / "upgrade-comparison.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("== entities ==")
for x in ent_cmp:
    print(f"  {x['entity_id']}: {x['pre_maturity']} -> {x['maturity']} | secs={x['sections']} zh={x['zh_chars']} freshness={x['freshness']}")
print("== relations ==")
for x in rel_cmp:
    print(f"  {x['relationship_id']}: {x['pre_maturity']} -> {x['maturity']} | type={x['type']} tl={x['timeline_items']}")
print("evidence:", out["evidence"])
