#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-D2 schema probe: baseline scale + refresh targets state."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d2/data/intelligence/africa")


def load(name):
    return json.load(open(P / name, encoding="utf-8"))


ents = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
sources = load("sources.json")["sources"]
evidence = load("evidence_records.json")["evidence"]
rp = load("relation_profiles.json")["profiles"]
rt = load("relation_timelines.json")["timelines"]
ep = load("entity_profiles.json")["profiles"]
print("scale:", "entities", len(ents), "rels", len(rels), "sources", len(sources), "evidence", len(evidence), "profiles", len(rp), "timelines", len(rt))

by_id = {r["relationship_id"]: r for r in rels}
for rid in ("rel-jnim-benin-spillover", "rel-jnim-benin-forces-fought", "rel-jnim-is-conflict"):
    r = by_id.get(rid)
    if r:
        print("\n=== REL", rid, "===")
        print("type:", r["relationship_type"], "| status:", r["current_status"], "| claim_valid_as_of:", r.get("claim_valid_as_of"), "| freshness:", r.get("freshness_status"))
        print("summary:", r["relation_summary"][:120])
        print("sources:", r.get("source_refs"))
        print("timeline items:", len(rt.get(rid, [])), "| profile exists:", rid in rp)
    else:
        print("\n=== REL", rid, "MISSING ===")

eb = {e["entity_id"]: e for e in ents}
for eid in ("actor-jnim", "person-abu-hanifa", "actor-ansarul-islam"):
    e = eb.get(eid)
    print("\n=== ENT", eid, "===")
    if e:
        print("status:", e.get("current_status"), "| countries:", e.get("country_ids"), "| regions:", e.get("region_ids"), "| freshness:", e.get("freshness_status"), "| claim_valid_as_of:", e.get("claim_valid_as_of"))
        pr = ep.get(eid, {})
        secs = pr.get("sections", {})
        print("profile depth:", pr.get("profile_depth"), "| sections:", list(secs.keys()))
        if eid == "person-abu-hanifa":
            print("profile current_assessment tail:", str(secs.get("current_assessment", ""))[-150:])
    else:
        print("MISSING")

print("\nactor-benin-forces exists:", "actor-benin-forces" in eb)
print("existing d2 entity ids collision check:")
new_ids = ["person-jafar-dicko", "person-ousmane-dicko", "actor-katiba-hanifa", "person-abou-ghosmane", "actor-katiba-serma", "actor-dana-atem", "person-ibrahim-malam-dicko", "actor-dozos-of-macina", "person-sidi-ongoiba", "person-amadou-nionson-diarra", "person-youssouf-toloba"]
print([x for x in new_ids if x in eb])
