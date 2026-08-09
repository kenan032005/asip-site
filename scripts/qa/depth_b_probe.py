#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH B probe: inspect current state of target entities, relations, sources,
and the malformed rel-jas-islamic-state-hostile record before repair."""
import json
from pathlib import Path

DATA = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-depth-b/data/intelligence/africa")

def load(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)

entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
sources = load("sources.json")["sources"]
ep = load("entity_profiles.json")["profiles"]
rp = load("relation_profiles.json")["profiles"]
tl = load("relation_timelines.json")["timelines"]

eid_set = {e["entity_id"] for e in entities}
rid_set = {r["relationship_id"] for r in rels}

print("== target entities present ==")
for eid in ("actor-jas","actor-iswap","actor-mnjtf","actor-nigeria-army","actor-chad-army","actor-cameroon-army","actor-lakurawa","actor-ansaru"):
    e = next((x for x in entities if x["entity_id"]==eid), None)
    print(f"  {eid}: {'FOUND' if e else 'MISSING'} | type={e.get('entity_type') if e else '-'}")

print("\n== special entities ==")
for eid in ("actor-islamic-state","actor-is-sahel","actor-iswap"):
    print(f"  {eid}: {'EXISTS' if eid in eid_set else 'MISSING'}")

print("\n== target relations present ==")
for rid in ("rel-jas-iswap-conflict","rel-jas-islamic-state-hostile","rel-iswap-islamic-state-affiliation",
            "rel-nigeria-mnjtf-member","rel-chad-mnjtf-member","rel-cameroon-mnjtf-member",
            "rel-cameroon-army-jas","rel-cameroon-army-iswap","rel-d1-ansaru-jas-split",
            "rel-d1-ansaru-aqim-allegiance","rel-d1-ansaru-jnim-affiliation"):
    r = next((x for x in rels if x["relationship_id"]==rid), None)
    if r:
        print(f"  {rid}: src={r.get('source_entity_id')} -> tgt={r.get('target_entity_id')} | type={r.get('relationship_type')} | status={r.get('current_status')} | slug={r.get('slug')}")
    else:
        print(f"  {rid}: MISSING")

print("\n== malformed relation full record ==")
m = next((x for x in rels if x["relationship_id"]=="rel-jas-islamic-state-hostile"), None)
if m:
    print(json.dumps(m, ensure_ascii=False, indent=1))

print("\n== relations with un-jnim-2018 source ==")
for r in rels:
    if "un-jnim-2018" in r.get("source_refs", []):
        print(f"  {r['relationship_id']}: {r.get('source_entity_id')} -> {r.get('target_entity_id')}")

print("\n== relation profiles for targets ==")
for rid in ("rel-jas-iswap-conflict","rel-jas-islamic-state-hostile","rel-iswap-islamic-state-affiliation"):
    pr = rp.get(rid)
    print(f"  {rid}: profile={'YES' if pr else 'NO'} | maturity={pr.get('relation_maturity') if pr else '-'} | tl_items={len(tl.get(rid,[]))}")

print("\n== entity profile maturity for targets ==")
for eid in ("actor-jas","actor-iswap","actor-mnjtf","actor-nigeria-army","actor-chad-army","actor-cameroon-army","actor-lakurawa","actor-ansaru"):
    pr = ep.get(eid)
    print(f"  {eid}: profile={'YES' if pr else 'NO'} | maturity={pr.get('content_maturity') if pr else '-'} | depth={pr.get('depth_score') if pr else '-'} | imported_by={pr.get('imported_by') if pr else '-'}")

print("\n== evidence verification status enum in use ==")
evs = load("evidence_records.json")["evidence"]
from collections import Counter
print(Counter(x.get("verification_status") for x in evs))

print("\n== source id prefixes count ==")
from collections import Counter
print(Counter(s["source_id"].split("-")[0] for s in sources))
