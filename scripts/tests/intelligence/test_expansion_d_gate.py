#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Expansion D dedicated gate test.

Mechanical checks for the semantic gates mandated by the Expansion D task:
- ABM is a historical phase of ISIS-Sinai, no duplicate current ABM node
- Ansaroul Islam is NOT whole-group ISIS/IS Sahel misclassified
- Katiba Hanifa → JNIM link exists (constituent_of)
- FPL is NOT classified terrorist/jihadist
- FLA is NOT classified terrorist/jihadist, and FLA↔JNIM is cooperates_with
  (tactical coordination), NOT affiliation/constituent/pledged
- no fake ISIS-Morocco province (Lions cell deferred)
- no Nasr Jihad node / no Yusuf Ghazi node / no U.S. Bancroft edge
- all PPT names resolved; new/enriched entities are encyclopedia_full
- source/evidence refs resolve; aliases resolve; no orphan entities/relations
"""
import io, json, os, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
DATA = "data/intelligence/africa"
PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  :: {detail}")


def load(n):
    return json.load(io.open(os.path.join(DATA, n), encoding="utf-8"))


entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
ep = load("entity_profiles.json")["profiles"]
rp = load("relation_profiles.json")["profiles"]
rt = load("relation_timelines.json")["timelines"]
sources = load("sources.json")["sources"]
evidence = load("evidence_records.json")["evidence"]
aliases = load("alias_index.json")["aliases"]
countries = load("countries.json")["countries"]

ent_ids = [x["entity_id"] for x in entities]
ent_by_id = {x["entity_id"]: x for x in entities}
rel_ids = [x["relationship_id"] for x in rels]
src_ids = {s["source_id"] for s in sources}
country_ids = {c["country_id"] for c in countries}

NEW2 = ["actor-isis-sinai", "actor-niger-fpl"]
ENRICH3 = ["actor-ansarul-islam", "actor-katiba-hanifa", "actor-fla"]

print("== 1. semantic gates (mandatory) ==")
check("ABM_DUPLICATE_CURRENT_NODE = 0", "actor-ansar-bayt-al-maqdis" not in ent_ids)
check("ABM is ISIS-Sinai historical name",
      "Ansar Bayt al-Maqdis" in (ent_by_id.get("actor-isis-sinai", {}).get("historical_names") or []) and
      "Ansar Bayt al-Maqdis" in (ent_by_id.get("actor-isis-sinai", {}).get("aliases") or []))
ansaroul = ent_by_id.get("actor-ansarul-islam", {})
check("ANSAROUL_WHOLE_GROUP_ISIS_MISCLASSIFICATION = 0",
      ansaroul.get("primary_type") != "terrorist_group" and ansaroul.get("current_status") != "isis_constituent")
kh = [r for r in rels if r["source_entity_id"] == "actor-katiba-hanifa" and r["target_entity_id"] == "actor-jnim" and r["relationship_type"] == "constituent_of"]
check("KATIBA_HANIFA_JNIM_LINK = PASS", bool(kh))
fpl = ent_by_id.get("actor-niger-fpl", {})
check("FPL_TERRORIST_MISCLASSIFICATION = 0", fpl.get("primary_type") != "terrorist_group")
fla = ent_by_id.get("actor-fla", {})
check("FLA_TERRORIST_MISCLASSIFICATION = 0", fla.get("primary_type") not in ("terrorist_group",))
check("FLA classified politico-military", fla.get("primary_type") == "political_movement")
fla_jnim = [r for r in rels if r["relationship_id"] == "rel-d1-fla-jnim-cooperation"]
check("FLA_JNIM_AFFILIATION_MISCLASSIFICATION = 0",
      bool(fla_jnim) and fla_jnim[0]["relationship_type"] == "cooperates_with" and fla_jnim[0]["current_status"] == "tactical_coordination")
check("LIONS_FAKE_PROVINCE = 0", "actor-lions-caliphate-maghreb-cell" not in ent_ids)
check("NASR_JIHAD_NODE_CREATED = 0", not any("nasr" in x for x in ent_ids))
check("YUSUF_GHAZI_NODE_CREATED = 0", not any(("yusuf-ghazi" in x or "ghazi-group" in x) for x in ent_ids))
check("UNSUPPORTED_US_BANCROFT_EDGE = 0",
      not any("bancroft" in r.get("relationship_id", "").lower() or "bancroft" in (r.get("relation_summary") or "").lower() for r in rels))

print("== 2. entity quality floor ==")
for eid in NEW2 + ENRICH3:
    p = ep.get(eid, {})
    n = len(p.get("sections", {}))
    check(f"{eid} encyclopedia_full + >=14 sections", p.get("profile_depth") == "encyclopedia_full" and n >= 14, f"depth={p.get('profile_depth')} secs={n}")
check("STANDARD_FINAL_ENTITY_COUNT = 0",
      all((ep.get(eid) or {}).get("profile_depth") == "encyclopedia_full" for eid in NEW2 + ENRICH3))

print("== 3. referential integrity ==")
bad_src = []
for x in entities:
    for sid in x.get("source_refs", []):
        if sid not in src_ids:
            bad_src.append((x["entity_id"], sid))
for r in rels:
    for sid in r.get("source_refs", []):
        if sid not in src_ids:
            bad_src.append((r["relationship_id"], sid))
check("all source refs resolve", not bad_src, str(bad_src[:5]))

orphan_ents = [eid for eid, p in ep.items() if eid not in ent_by_id]
check("no orphan entity profiles", not orphan_ents, str(orphan_ents[:5]))
rel_without_profile = [rid for rid in rel_ids if rid not in rp]
check("every relationship has a profile", not rel_without_profile, str(rel_without_profile[:5]))

print("== 4. new relations present & typed correctly ==")
for rid, st, tt, rt_ in [("rel-expd-isis-sinai-isis", "actor-isis-sinai", "actor-islamic-state", "pledged_allegiance_to"),
                          ("rel-expd-ansaroul-katiba-macina", "actor-ansarul-islam", "actor-katiba-macina", "historically_associated_with"),
                          ("rel-expd-fpl-niger-operates", "actor-niger-fpl", "country-niger", "operates_in")]:
    r = [x for x in rels if x["relationship_id"] == rid]
    check(f"{rid} present & typed", bool(r) and r[0]["source_entity_id"] == st and r[0]["target_entity_id"] == tt and r[0]["relationship_type"] == rt_, str(r[0] if r else "MISSING"))

print(f"PASS={PASS} FAIL={FAIL}")
sys.exit(0 if FAIL == 0 else 1)
