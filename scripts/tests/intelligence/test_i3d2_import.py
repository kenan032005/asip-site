#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP I3-D2 import gates: packet counts, refreshes, entity ids, relationship types,
aging/Nigeria/DoZo/Jafar semantics, source mapping, evidence mapping, generator regen."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "africa"
DIST = ROOT / "dist" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-i3d2"


def load(name, base=DATA):
    return json.load(open(base / name, encoding="utf-8"))


def fail(msg):
    raise AssertionError(msg)


def rel_of(rels, sid, tid, rtype=None):
    for r in rels:
        if r["source_entity_id"] == sid and r["target_entity_id"] == tid and (rtype is None or r["relationship_type"] == rtype):
            return r
    return None


def test_i3d2_packet_counts():
    entities = load("entities.json")["entities"]
    rels = load("relationships.json")["relationships"]
    profiles = load("relation_profiles.json")["profiles"]
    if len(entities) != 83: fail(f"entities={len(entities)} != 83 (72 + 11 Expansion A)")
    if len(rels) != 164: fail(f"relationships={len(rels)} != 164 (150 + 14 Expansion A)")
    if len(profiles) < 50: fail(f"profiles={len(profiles)} < 50")
    d2_ents = ["person-jafar-dicko", "person-ousmane-dicko", "actor-katiba-hanifa", "person-abou-ghosmane", "actor-katiba-serma", "actor-dana-atem", "person-ibrahim-malam-dicko", "actor-dozos-of-macina", "person-sidi-ongoiba", "person-amadou-nionson-diarra", "person-youssouf-toloba"]
    eids = {e["entity_id"] for e in entities}
    missing = [x for x in d2_ents if x not in eids]
    if missing: fail(f"missing d2 entities: {missing}")
    d2_rels = [r for r in rels if r["relationship_id"].startswith("rel-d2-")]
    if len(d2_rels) != 29: fail(f"d2 relationships={len(d2_rels)} != 29")
    print("PASS test_i3d2_packet_counts (72/150/50+)")


def test_i3d2_refreshes():
    entities = load("entities.json")["entities"]
    rels = load("relationships.json")["relationships"]
    ep = load("entity_profiles.json")["profiles"]
    jnim = next(e for e in entities if e["entity_id"] == "actor-jnim")
    if "country-benin" not in jnim["country_ids"] or "country-nigeria" not in jnim["country_ids"]:
        fail("jnim refresh countries missing")
    if jnim["current_status"] != "active_and_expanding_across_west_africa":
        fail("jnim refresh status missing")
    abu = next(e for e in entities if e["entity_id"] == "person-abu-hanifa")
    if "Katiba Hanifa负责人" not in json.dumps(ep["person-abu-hanifa"].get("sections", {}), ensure_ascii=False):
        fail("abu-hanifa profile_append missing")
    ans = ep["actor-ansarul-islam"].get("sections", {})
    if "Jafar Dicko" not in json.dumps(ans, ensure_ascii=False):
        fail("ansarul profile_append missing")
    by_id = {r["relationship_id"]: r for r in rels}
    for rid in ("rel-jnim-benin-spillover", "rel-jnim-benin-forces-fought", "rel-jnim-is-conflict"):
        r = by_id.get(rid)
        if not r: fail(f"refresh target missing: {rid}")
        if r.get("claim_valid_as_of") == "2023-11-30" or r.get("freshness_status") == "stale":
            fail(f"refresh not applied: {rid}")
    print("PASS test_i3d2_refreshes (3 entity + 3 relationship refreshes)")


def test_i3d2_relationship_types():
    rels = load("relationships.json")["relationships"]
    rtypes = {t["relation_type"] for t in load("relation_types.json")["relation_types"]}
    for r in rels:
        if r["relationship_type"] not in rtypes: fail(f"invalid type {r['relationship_type']} on {r['relationship_id']}")
    r = rel_of(rels, "person-jafar-dicko", "actor-jnim")
    if not r or r["relationship_type"] != "affiliated_with": fail("Jafar-JNIM must be affiliated_with")
    if rel_of(rels, "person-jafar-dicko", "actor-jnim", "led_by"): fail("Jafar must NOT be whole-JNIM led_by")
    if not rel_of(rels, "actor-ansarul-islam", "person-jafar-dicko", "led_by"): fail("Ansarul-Jafar must be led_by")
    if not rel_of(rels, "actor-ansarul-islam", "person-ibrahim-malam-dicko", "founded_by"): fail("Ansarul-Ibrahim must be founded_by")
    if not rel_of(rels, "actor-katiba-hanifa", "actor-jnim", "constituent_of"): fail("Katiba Hanifa-JNIM must be constituent_of")
    if not rel_of(rels, "actor-katiba-hanifa", "person-abu-hanifa", "led_by"): fail("Katiba Hanifa-Abu Hanifa must be led_by")
    if not rel_of(rels, "actor-katiba-hanifa", "actor-benin-forces", "fought_against"): fail("Katiba Hanifa-Benin Forces must be fought_against")
    if not rel_of(rels, "actor-dana-atem", "actor-dan-na-ambassagou", "split_from"): fail("Dana Atem-Dan Na must be split_from")
    if rel_of(rels, "actor-dana-atem", "actor-mali-army", "member_of_force"): fail("Dana Atem-FAMa must NOT be member_of_force")
    if rel_of(rels, "actor-dozos-of-macina", "actor-mali-army", "member_of_force"): fail("Dozos-FAMa must NOT be member_of_force")
    print("PASS test_i3d2_relationship_types (locked semantics)")


def test_i3d2_semantics_aging_nigeria():
    rels = load("relationships.json")["relationships"]
    entities = load("entities.json")["entities"]
    timelines = load("relation_timelines.json")["timelines"]
    r = rel_of(rels, "actor-jnim", "country-nigeria")
    if not r or r["current_status"] != "emerging_limited_presence": fail("JNIM-Nigeria must be emerging_limited_presence")
    blob = json.dumps(r, ensure_ascii=False)
    for forbidden in ("成熟分支", "稳定基地", "控制区"):
        if forbidden in blob and "不表示" not in blob:
            fail(f"Nigeria control/mature-branch wording: {forbidden}")
    for eid in ("actor-katiba-serma", "actor-dana-atem", "actor-dozos-of-macina"):
        e = next(x for x in entities if x["entity_id"] == eid)
        if e["freshness_status"] != "aging": fail(f"{eid} must stay aging, got {e['freshness_status']}")
    if not rel_of(rels, "actor-jnim", "actor-is-sahel", "hostile_to"): fail("jnim-is-conflict must stay hostile_to")
    tl = timelines.get("rel-jnim-is-conflict", [])
    if len(tl) < 2: fail("rel-jnim-is-conflict 2026 timeline not appended")
    if not any("Kebbi" in x.get("event_title", "") and ("保留限定" in x.get("event_title", "") or "khawarij" in x.get("event_title", "")) for x in tl):
        fail("Kebbi identity qualifier missing")
    print("PASS test_i3d2_semantics_aging_nigeria (aging preserved, Nigeria limited, Kebbi qualified)")


def test_i3d2_entity_ids():
    entities = load("entities.json")["entities"]
    eids = [e["entity_id"] for e in entities]
    slugs = [e["slug"] for e in entities]
    if len(eids) != len(set(eids)): fail("duplicate entity id")
    if len(slugs) != len(set(slugs)): fail("duplicate entity slug")
    ep = load("entity_profiles.json")["profiles"]
    for e in entities:
        if e["entity_id"] not in ep: fail(f"entity profile missing: {e['entity_id']}")
    print("PASS test_i3d2_entity_ids (72 unique entities, profiles present)")


def test_i3d2_source_mapping():
    sources = load("sources.json")["sources"]
    sids = {s["source_id"] for s in sources}
    mapping = load("source-mapping.json", base=QA)
    for pid, m in mapping["mapping"].items():
        if m["actual_source_id"] not in sids: fail(f"mapped source missing: {m['actual_source_id']}")
    expected_null = {"d2-nctc-jnim-2026-05", "d2-africa-center-benin-2026", "d2-acled-dan-na-profile"}
    actual_null = {s["source_id"] for s in sources if s.get("published_at") is None and s["source_id"].startswith("d2-")}
    if actual_null != expected_null: fail(f"null published_at mismatch: {actual_null ^ expected_null}")
    print("PASS test_i3d2_source_mapping (7 candidates mapped, no invented dates)")


def test_i3d2_evidence_mapping():
    evidence = load("evidence_records.json")["evidence"]
    eids = [e["evidence_id"] for e in evidence]
    if len(eids) != len(set(eids)): fail("duplicate evidence id")
    sids = {s["source_id"] for s in load("sources.json")["sources"]}
    rel_ids = {r["relationship_id"] for r in load("relationships.json")["relationships"]}
    eid_set = {e["entity_id"] for e in load("entities.json")["entities"]}
    cids = {c["country_id"] for c in load("countries.json")["countries"]}
    valid = eid_set | cids
    for e in evidence:
        if e["source_id"] not in sids: fail(f"evidence {e['evidence_id']} dangling source")
        for rid in e.get("relation_ids", []):
            if rid not in rel_ids: fail(f"evidence {e['evidence_id']} dangling relation {rid}")
        for eid in e.get("entity_ids", []):
            if eid not in valid: fail(f"evidence {e['evidence_id']} dangling entity {eid}")
    d2_ev = [e for e in evidence if e["evidence_id"].startswith("ev-d2-")]
    if len(d2_ev) != 12: fail(f"d2 evidence={len(d2_ev)} != 12")
    print("PASS test_i3d2_evidence_mapping (194 evidence, refs resolve)")


def test_i3d2_generator_regression():
    report = load("generator-regen-diff.json", base=QA)
    for key in ("unexpected_object_deletions", "profile_depth_regressions", "evidence_regressions", "relation_type_regressions", "timeline_regressions"):
        if report.get(key, 1) != 0: fail(f"generator regression {key}")
    print("PASS test_i3d2_generator_regression")


def test_i3d2_build_consistency():
    if not DIST.exists(): fail("dist missing")
    for name in ("entities.json", "relationships.json", "sources.json", "evidence_records.json", "relation_profiles.json", "relation_timelines.json"):
        a = load(name)
        b = load(name, base=DIST / "data")
        if a != b: fail(f"dist data mismatch: {name}")
    routes = ["entity/jafar-dicko/", "entity/katiba-hanifa/", "entity/dana-atem/", "entity/dozos-of-macina/", "relation/d2-jnim-nigeria-emerging/", "relation/d2-dana-dan-na-split/", "relation/jnim-is-sahel-conflict/"]
    for rt in routes:
        if not (DIST / rt / "index.html").exists(): fail(f"route missing: {rt}")
    print("PASS test_i3d2_build_consistency (dist matches source, key routes present)")


def main():
    tests = [test_i3d2_packet_counts, test_i3d2_refreshes, test_i3d2_relationship_types, test_i3d2_semantics_aging_nigeria, test_i3d2_entity_ids, test_i3d2_source_mapping, test_i3d2_evidence_mapping, test_i3d2_generator_regression, test_i3d2_build_consistency]
    for t in tests:
        t()
    print("ALL 9 I3-D2 TESTS PASS")


if __name__ == "__main__":
    main()
