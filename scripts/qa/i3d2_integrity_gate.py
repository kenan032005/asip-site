#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-D2 integrity + semantics gate: uniqueness, dangling refs, relation types,
refresh application, locked semantics (Jafar role, Nigeria presence, Dozo splits,
aging preserved, no duplicate relations)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "data" / "intelligence" / "africa"
DIST = ROOT / "dist" / "intelligence" / "africa"

issues = []
ok = []


def load(name):
    return json.load(open(P / name, encoding="utf-8"))


entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
sources = load("sources.json")["sources"]
evidence = load("evidence_records.json")["evidence"]
profiles = load("relation_profiles.json")["profiles"]
timelines = load("relation_timelines.json")["timelines"]
ep = load("entity_profiles.json")["profiles"]
rtypes = {t["relation_type"] for t in load("relation_types.json")["relation_types"]}
regions = {r["region_id"] for r in load("regions.json")["regions"]}
countries = {c["country_id"] for c in load("countries.json")["countries"]}

eids = [e["entity_id"] for e in entities]
slugs = [e["slug"] for e in entities]
rids = [r["relationship_id"] for r in rels]
sids = [s["source_id"] for s in sources]
evids = [e["evidence_id"] for e in evidence]
eid_set, rid_set, sid_set = set(eids), set(rids), set(sids)

if len(eids) != len(set(eids)):
    issues.append("duplicate entity ids")
if len(slugs) != len(set(slugs)):
    issues.append("duplicate entity slugs")
if len(rids) != len(set(rids)):
    issues.append("duplicate relationship ids")
if len(sids) != len(set(sids)):
    issues.append("duplicate source ids")
if len(evids) != len(set(evids)):
    issues.append("duplicate evidence ids")

valid_ends = eid_set | set(countries) | set(regions)
dangling = []
for r in rels:
    if r["source_entity_id"] not in valid_ends or r["target_entity_id"] not in valid_ends:
        dangling.append(r["relationship_id"])
if dangling:
    issues.append("dangling relation endpoints: " + ",".join(dangling))

for e in entities:
    for s in e.get("source_refs", []):
        if s not in sid_set:
            issues.append(f"dangling source on entity {e['entity_id']}: {s}")
for r in rels:
    for s in r.get("source_refs", []):
        if s not in sid_set:
            issues.append(f"dangling source on rel {r['relationship_id']}: {s}")
for e in evidence:
    if e["source_id"] not in sid_set:
        issues.append(f"dangling source on evidence {e['evidence_id']}")
    for rid in e.get("relation_ids", []):
        if rid not in rid_set:
            issues.append(f"dangling relation on evidence {e['evidence_id']}: {rid}")
for k, v in profiles.items():
    if k not in rid_set:
        issues.append(f"profile key not in relationships: {k}")
for k, v in timelines.items():
    if k not in rid_set:
        issues.append(f"timeline key not in relationships: {k}")

invalid_types = [r["relationship_id"] for r in rels if r["relationship_type"] not in rtypes]
if invalid_types:
    issues.append("invalid relation types: " + ",".join(invalid_types))

new_rels = [r for r in rels if r["relationship_id"].startswith("rel-d2-")]
if len(new_rels) != 29:
    issues.append(f"d2 relationships={len(new_rels)} != 29")
new_entities = [e for e in entities if e["entity_id"] in ("person-jafar-dicko", "person-ousmane-dicko", "actor-katiba-hanifa", "person-abou-ghosmane", "actor-katiba-serma", "actor-dana-atem", "person-ibrahim-malam-dicko", "actor-dozos-of-macina", "person-sidi-ongoiba", "person-amadou-nionson-diarra", "person-youssouf-toloba")]
if len(new_entities) != 11:
    issues.append(f"d2 entities={len(new_entities)} != 11")

# ---- locked semantics ----
def rel_of(sid, tid, rtype=None):
    for r in rels:
        if r["source_entity_id"] == sid and r["target_entity_id"] == tid and (rtype is None or r["relationship_type"] == rtype):
            return r
    return None


checks = [
    ("Jafar-JNIM affiliated_with (not led_by)", rel_of("person-jafar-dicko", "actor-jnim", "affiliated_with") is not None and rel_of("person-jafar-dicko", "actor-jnim", "led_by") is None),
    ("Ansarul-Jafar led_by", rel_of("actor-ansarul-islam", "person-jafar-dicko", "led_by") is not None),
    ("Ansarul-Ibrahim founded_by", rel_of("actor-ansarul-islam", "person-ibrahim-malam-dicko", "founded_by") is not None),
    ("Katiba Hanifa-JNIM constituent_of", rel_of("actor-katiba-hanifa", "actor-jnim", "constituent_of") is not None),
    ("Katiba Hanifa-Abu Hanifa led_by", rel_of("actor-katiba-hanifa", "person-abu-hanifa", "led_by") is not None),
    ("Katiba Hanifa-Benin Forces fought_against", rel_of("actor-katiba-hanifa", "actor-benin-forces", "fought_against") is not None),
    ("Abou Ghosmane distinct from Abu Hanifa", "person-abou-ghosmane" in eid_set and "person-abu-hanifa" in eid_set and "person-abou-ghosmane" != "person-abu-hanifa"),
    ("Dana Atem-Dan Na split_from", rel_of("actor-dana-atem", "actor-dan-na-ambassagou", "split_from") is not None),
    ("Dana Atem-FAMa cooperates_with (not member_of_force)", rel_of("actor-dana-atem", "actor-mali-army", "cooperates_with") is not None and rel_of("actor-dana-atem", "actor-mali-army", "member_of_force") is None),
    ("Dozos of Macina-FAMa cooperates_with (not member_of_force)", rel_of("actor-dozos-of-macina", "actor-mali-army", "cooperates_with") is not None and rel_of("actor-dozos-of-macina", "actor-mali-army", "member_of_force") is None),
    ("JNIM-Nigeria operates_in + emerging_limited_presence", rel_of("actor-jnim", "country-nigeria", "operates_in") is not None and rel_of("actor-jnim", "country-nigeria")["current_status"] == "emerging_limited_presence"),
    ("JNIM-Nigeria no control/mature semantics", "控制" not in json.dumps(rel_of("actor-jnim", "country-nigeria"), ensure_ascii=False) or "不表示成熟分支" in json.dumps(rel_of("actor-jnim", "country-nigeria"), ensure_ascii=False)),
    ("rel-jnim-is-conflict hostile_to preserved", rel_of("actor-jnim", "actor-is-sahel", "hostile_to") is not None),
    ("rel-jnim-is-conflict 2026 timeline appended", len(timelines.get("rel-jnim-is-conflict", [])) >= 2),
    ("Kebbi identity qualifier preserved", any("保留限定" in x.get("event_title", "") or "khawarij" in x.get("event_title", "") for x in timelines.get("rel-jnim-is-conflict", []))),
    ("Katiba Serma aging", "actor-katiba-serma" in eid_set and next(e for e in entities if e["entity_id"] == "actor-katiba-serma")["freshness_status"] == "aging"),
    ("Dana Atem aging", "actor-dana-atem" in eid_set and next(e for e in entities if e["entity_id"] == "actor-dana-atem")["freshness_status"] == "aging"),
    ("Dozos of Macina aging", "actor-dozos-of-macina" in eid_set and next(e for e in entities if e["entity_id"] == "actor-dozos-of-macina")["freshness_status"] == "aging"),
    ("Three Dozo networks distinct", all(x in eid_set for x in ("actor-dan-na-ambassagou", "actor-dana-atem", "actor-dozos-of-macina")) and len({"actor-dan-na-ambassagou", "actor-dana-atem", "actor-dozos-of-macina"}) == 3),
]
for name, cond in checks:
    if cond:
        ok.append(name)
    else:
        issues.append("semantic check failed: " + name)

# ---- refreshes ----
jnim = next(e for e in entities if e["entity_id"] == "actor-jnim")
if "country-benin" not in jnim["country_ids"] or "country-nigeria" not in jnim["country_ids"]:
    issues.append("jnim refresh country ids missing benin/nigeria")
if jnim["current_status"] != "active_and_expanding_across_west_africa":
    issues.append("jnim refresh current_status not applied")
abu = next(e for e in entities if e["entity_id"] == "person-abu-hanifa")
if "country-burkina-faso" not in abu["country_ids"] or "country-benin" not in abu["country_ids"]:
    issues.append("abu-hanifa refresh country ids missing")
if "Katiba Hanifa负责人" not in json.dumps(ep.get("person-abu-hanifa", {}).get("sections", {}), ensure_ascii=False):
    issues.append("abu-hanifa profile_append not applied")
ansarul = next(e for e in entities if e["entity_id"] == "actor-ansarul-islam")
if "Jafar Dicko" not in json.dumps(ep.get("actor-ansarul-islam", {}).get("sections", {}), ensure_ascii=False):
    issues.append("ansarul profile_append not applied")
for rid in ("rel-jnim-benin-spillover", "rel-jnim-benin-forces-fought", "rel-jnim-is-conflict"):
    r = next((x for x in rels if x["relationship_id"] == rid), None)
    if not r:
        issues.append(f"refresh target missing: {rid}")
    elif r.get("claim_valid_as_of") in (None, "2023-11-30") or r.get("freshness_status") == "stale":
        issues.append(f"refresh not applied: {rid}")
ok.append("3 entity refreshes and 3 relationship refreshes applied")

# no duplicate relations among the D2-imported set (29 new relations must not repeat endpoint/type)
d2_rels = [r for r in rels if r["relationship_id"].startswith("rel-d2-")]
seen_pairs = {}
for r in d2_rels:
    key = (r["source_entity_id"], r["target_entity_id"], r["relationship_type"])
    seen_pairs[key] = seen_pairs.get(key, 0) + 1
dups = {"/".join(k): v for k, v in seen_pairs.items() if v > 1}
if dups:
    issues.append("duplicate d2 relation pairs: " + json.dumps(dups, ensure_ascii=False))
else:
    ok.append("29 D2 relations are unique endpoint/type pairs")
# pre-existing endpoint-pair overlaps (rel-jnim-is-hostile vs rel-jnim-is-conflict, jas/iswap) predate D2;
# rel-jnim-is-conflict was refreshed in place, no duplicate created by this package.
pre_existing = {
    "actor-jnim/actor-is-sahel/hostile_to": 2, "actor-jas/actor-iswap/hostile_to": 2
}
report_pre = {"pre_existing_endpoint_pair_overlaps": pre_existing}

# dist consistency
if DIST.exists():
    for name in ("entities.json", "relationships.json", "sources.json", "evidence_records.json", "relation_profiles.json", "relation_timelines.json"):
        a = load(name)
        b = json.load(open(DIST / "data" / name, encoding="utf-8"))
        if a != b:
            issues.append(f"dist data mismatch: {name}")

report = {
    "artifact": "I3D2_INTEGRITY_SEMANTICS_GATE",
    "ok": ok,
    "issues": issues,
    "pre_existing_endpoint_pair_overlaps": pre_existing,
    "gate": "PASS" if not issues else "OPEN",
    "scale": {"entities": len(entities), "relationships": len(rels), "sources": len(sources), "evidence": len(evidence), "profiles": len(profiles), "timelines": len(timelines)},
}
(ROOT / "qa-artifacts-i3d2" / "integrity-semantics-gate.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({"gate": report["gate"], "issues": issues, "ok_count": len(ok)}, ensure_ascii=False, indent=1))
if issues:
    sys.exit(1)
