#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-D1 detailed schema probe: full record samples and prep targets."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d1/data/intelligence/africa")


def load(name):
    return json.load(open(P / name, encoding="utf-8"))


ents = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
srcs = load("sources.json")["sources"]
ev = load("evidence_records.json")["evidence"]
rp = load("relation_profiles.json")["profiles"]
rt = load("relation_timelines.json")["timelines"]
ep = load("entity_profiles.json")["profiles"]

# full entity sample
e0 = next(e for e in ents if e["entity_id"] == "actor-jnim")
print("=== ENTITY actor-jnim (full) ===")
print(json.dumps(e0, ensure_ascii=False, indent=1)[:2200])
print()
print("=== primary_type values ===")
print(sorted({str(e.get("primary_type")) for e in ents}))
print("=== profile_level values ===")
print(sorted({str(e.get("profile_level")) for e in ents}))
print("=== freshness_status values (entities) ===")
print(sorted({str(e.get("freshness_status")) for e in ents}))
print("=== verification_status values (entities) ===")
print(sorted({str(e.get("verification_status")) for e in ents}))
print()

# prep targets
for rid in ["rel-endf-ola-conflict", "rel-endf-tdf-conflict", "rel-burkina-army-jnim"]:
    r = next((x for x in rels if x["relationship_id"] == rid), None)
    print(f"=== REL {rid} ===")
    if r:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print("NOT FOUND")
    print()

# source un-jnim-2018
s = next((x for x in srcs if x["source_id"] == "un-jnim-2018"), None)
print("=== SOURCE un-jnim-2018 ===")
print(json.dumps(s, ensure_ascii=False, indent=1) if s else "NOT FOUND")
print()

# full source sample
s0 = next(s for s in srcs if s["published_at"])
print("=== SOURCE sample ===")
print(json.dumps(s0, ensure_ascii=False, indent=1))
print()
# any null published_at?
null_pub = [s["source_id"] for s in srcs if not s.get("published_at")]
print("sources with null published_at:", null_pub[:10], "count:", len(null_pub))
print()

# full evidence sample
ev0 = next(x for x in ev if x["verification_status"] == "verified")
print("=== EVIDENCE verified sample ===")
print(json.dumps(ev0, ensure_ascii=False, indent=1)[:1800])
print()
print("evidence_id samples:", [x["evidence_id"] for x in ev[:5]])
print("evidence_origin values:", sorted({x.get("evidence_origin") for x in ev}))
print("claim_type values:", sorted({x.get("claim_type") for x in ev}))
print()

# full relation profile sample
pk = list(rp.keys())[0]
print(f"=== RELATION PROFILE {pk} (all keys) ===")
print(list(rp[pk].keys()))
print(json.dumps(rp[pk], ensure_ascii=False, indent=1)[:2200])
print()

# full timeline sample
tk = list(rt.keys())[0]
print(f"=== TIMELINE {tk} item keys ===")
print(list(rt[tk][0].keys()))
print(json.dumps(rt[tk][:2], ensure_ascii=False, indent=1)[:1600])
print()

# entity profile keys
ek = list(ep.keys())[0]
print(f"=== ENTITY PROFILE {ek} keys ===")
print(list(ep[ek].keys()))
print("sections keys:", list(ep[ek].get("sections", {}).keys())[:30])
print()

# existing relations referencing un-jnim-2018
print("rels referencing un-jnim-2018:", [r["relationship_id"] for r in rels if "un-jnim-2018" in (r.get("source_refs") or [])])
print("profiles referencing un-jnim-2018:", [k for k, v in rp.items() if "un-jnim-2018" in (v.get("source_ids") or [])])
print("timelines referencing un-jnim-2018:", [k for k, v in rt.items() if any("un-jnim-2018" in (i.get("source_ids") or []) for i in v)])
print("evidence referencing un-jnim-2018:", [x["evidence_id"] for x in ev if x.get("source_id") == "un-jnim-2018"])
print()

# relation current_status / freshness values
print("rel current_status values:", sorted({r.get("current_status") for r in rels}))
print("rel freshness_status values:", sorted({r.get("freshness_status") for r in rels}))
print("rel disputed count:", sum(1 for r in rels if r.get("disputed")))
print()

# region ids
regions = load("regions.json")["regions"]
print("region ids:", [r["region_id"] for r in regions])
print("country ids:", [c["country_id"] for c in load("countries.json")["countries"]])
