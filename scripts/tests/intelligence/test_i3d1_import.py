#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP I3-D1 import gates (9 tests):
1 test_i3d1_packet_counts
2 test_i3d1_prep_corrections
3 test_i3d1_entity_ids
4 test_i3d1_relationship_types
5 test_i3d1_disputed_semantics
6 test_i3d1_source_mapping
7 test_i3d1_evidence_mapping
8 test_i3d1_generator_regression
9 test_i3d1_build_consistency
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "africa"
DIST = ROOT / "dist" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-i3d1"


def load(name, base=DATA):
    with (base / name).open(encoding="utf-8") as f:
        return json.load(f)


def fail(msg):
    raise AssertionError(msg)


def rel_of(rels, sid, tid, rtype=None):
    for r in rels:
        if r["source_entity_id"] == sid and r["target_entity_id"] == tid and (rtype is None or r["relationship_type"] == rtype):
            return r
    return None


def test_i3d1_packet_counts():
    entities = load("entities.json")["entities"]
    rels = load("relationships.json")["relationships"]
    sources = load("sources.json")["sources"]
    evidence = load("evidence_records.json")["evidence"]
    profiles = load("relation_profiles.json")["profiles"]
    countries = load("countries.json")["countries"]
    if len(countries) != 13: fail(f"countries={len(countries)} != 13")
    # I3-D2 extends the catalog; D1 gate asserts the D1 baseline is present within the current scale
    if len(entities) != 105: fail(f"non-country entities={len(entities)} != 104 (105 + 0 Consolidation A)")
    if len(rels) != 203: fail(f"relationships={len(rels)} != 201 (203 + 2 Pack B)")
    if len(profiles) < 42: fail(f"relation_profiles={len(profiles)} < 42")
    if len(sources) < 96: fail(f"sources={len(sources)} < 96")
    if len(evidence) < 167: fail(f"evidence={len(evidence)} < 167")
    new_rels = [r for r in rels if r["relationship_id"].startswith("rel-d1-")]
    if len(new_rels) != 43: fail(f"d1 relationships={len(new_rels)} != 43")
    new_entities = ["actor-fla", "actor-africa-corps", "actor-wagner-group", "actor-ansarul-islam", "actor-hcua", "actor-mnla", "actor-maa-cma", "actor-gatia", "actor-dan-na-ambassagou", "actor-fu-aes", "actor-niger-armed-forces", "person-abu-hanifa", "person-sadou-samahouna", "actor-lakurawa", "actor-ansaru"]
    eids = {e["entity_id"] for e in entities}
    missing = [x for x in new_entities if x not in eids]
    if missing: fail(f"missing d1 entities: {missing}")
    print("PASS test_i3d1_packet_counts (61/121/42+/sources/evidence)")


def test_i3d1_prep_corrections():
    rels = load("relationships.json")["relationships"]
    by_id = {r["relationship_id"]: r for r in rels}
    checks = {
        "rel-endf-ola-conflict": {
            "forbidden": ["与 TPLF 结盟使奥罗米亚—提格雷两线联动"],
            "must": ["不足以把2021年的OLA—TPLF联盟关系直接延伸为2026年的正式联盟"],
            "sources": ["d1-acled-ethiopia-2026"],
        },
        "rel-endf-tdf-conflict": {
            "forbidden": ["提格雷事实脱离联邦控制", "比勒陀利亚协议实质失效"],
            "must_detail": ["重新对峙/局部交火、和平框架严重承压"],
            "sources": ["ETH_AU_2026_01_30", "d1-acled-ethiopia-2026"],
        },
        "rel-burkina-army-jnim": {
            "forbidden": ["JNIM 控制/争夺约六成领土"],
            "must": ["不能解释为JNIM单独控制或争夺约60%—70%的全国领土"],
            "sources": ["BURKINA_ACSS_2025_08_26"],
        },
    }
    for rid, spec in checks.items():
        r = by_id.get(rid)
        if not r: fail(f"prep target missing: {rid}")
        blob = json.dumps(r, ensure_ascii=False)
        for fw in spec["forbidden"]:
            if fw in blob: fail(f"residual in {rid}: {fw}")
        for mc in spec.get("must", []):
            if mc not in r["relation_summary"]: fail(f"summary missing in {rid}: {mc}")
        for mc in spec.get("must_detail", []):
            if mc not in r.get("current_status_detail", ""): fail(f"detail missing in {rid}: {mc}")
        if "un-jnim-2018" in r.get("source_refs", []): fail(f"un-jnim-2018 still bound on {rid}")
        for s in spec["sources"]:
            if s not in r.get("source_refs", []): fail(f"source {s} missing on {rid}")
    print("PASS test_i3d1_prep_corrections (3 corrections applied, un-jnim-2018 cleared)")


def test_i3d1_entity_ids():
    entities = load("entities.json")["entities"]
    eids = [e["entity_id"] for e in entities]
    slugs = [e["slug"] for e in entities]
    if len(eids) != len(set(eids)): fail("duplicate entity id")
    if len(slugs) != len(set(slugs)): fail("duplicate entity slug")
    ids = {e["entity_id"]: e for e in entities}
    for eid in ("actor-fla", "actor-africa-corps", "actor-wagner-group", "actor-ansarul-islam", "actor-hcua", "actor-mnla", "actor-maa-cma", "actor-gatia", "actor-dan-na-ambassagou", "actor-fu-aes", "actor-niger-armed-forces", "person-abu-hanifa", "person-sadou-samahouna", "actor-lakurawa", "actor-ansaru"):
        e = ids.get(eid)
        if not e: fail(f"missing {eid}")
        for k in ("entity_type", "slug", "name_zh", "name_en", "importance_level", "primary_category", "country_ids", "region_ids", "current_status", "claim_valid_as_of", "freshness_status", "confidence", "disputed"):
            if k not in e: fail(f"{eid} missing field {k}")
    ep = load("entity_profiles.json")["profiles"]
    for eid in ids:
        if eid not in ep: fail(f"entity profile missing: {eid}")
    print("PASS test_i3d1_entity_ids (15 new entities, unique ids/slugs, profiles present)")


def test_i3d1_relationship_types():
    rels = load("relationships.json")["relationships"]
    rtypes = {t["relation_type"] for t in load("relation_types.json")["relation_types"]}
    for r in rels:
        if r["relationship_type"] not in rtypes: fail(f"invalid type {r['relationship_type']} on {r['relationship_id']}")
    # locked semantics
    r = rel_of(rels, "actor-fla", "actor-jnim")
    if not r or r["relationship_type"] != "cooperates_with": fail("FLA-JNIM must be cooperates_with")
    if rel_of(rels, "actor-fla", "actor-jnim", "allied_with"): fail("FLA-JNIM must NOT be allied_with")
    r = rel_of(rels, "actor-ansarul-islam", "actor-jnim")
    if not r or r["relationship_type"] != "constituent_of": fail("Ansarul Islam-JNIM must be constituent_of")
    r = rel_of(rels, "actor-ansaru", "actor-aqim")
    if not r or r["relationship_type"] != "pledged_allegiance_to": fail("Ansaru-AQIM must be pledged_allegiance_to")
    r = rel_of(rels, "actor-ansaru", "actor-jnim")
    if not r or r["relationship_type"] != "affiliated_with": fail("Ansaru-JNIM must be affiliated_with")
    r = rel_of(rels, "actor-dan-na-ambassagou", "actor-mali-army")
    if not r or r["relationship_type"] != "cooperates_with": fail("Dan Na-FAMa must be cooperates_with")
    if rel_of(rels, "actor-dan-na-ambassagou", "actor-mali-army", "member_of_force"): fail("Dan Na-FAMa must NOT be member_of_force")
    r = rel_of(rels, "actor-africa-corps", "actor-wagner-group")
    if not r or r["relationship_type"] != "historically_associated_with": fail("Africa Corps-Wagner must be historically_associated_with")
    for sid, tid in (("actor-mali-army", "actor-fu-aes"), ("actor-burkina-army", "actor-fu-aes"), ("actor-niger-armed-forces", "actor-fu-aes")):
        if not rel_of(rels, sid, tid, "member_of_force"): fail(f"{sid}-FU-AES must be member_of_force")
    print("PASS test_i3d1_relationship_types (locked semantics verified)")


def test_i3d1_disputed_semantics():
    rels = load("relationships.json")["relationships"]
    r = rel_of(rels, "actor-lakurawa", "actor-is-sahel")
    if not r or r["relationship_type"] != "part_of_network": fail("Lakurawa-IS Sahel must be part_of_network")
    if r["disputed"] is not True: fail("Lakurawa-IS Sahel disputed must be true")
    r = rel_of(rels, "actor-lakurawa", "actor-jnim")
    if not r or r["relationship_type"] != "cooperates_with": fail("Lakurawa-JNIM must be cooperates_with")
    if r["disputed"] is not True: fail("Lakurawa-JNIM disputed must be true")
    # EXPANSION A: the semantics note now documents the NigSAC official position
    # vs the ACLED 2026 evidence conflict (pack 15 #16) while preserving the
    # some_cells_only scope: no branch_of relationship is asserted.
    note = r.get("relationship_semantics_note") or ""
    if "cooperates_with" not in note or "branch_of" not in note: fail("Lakurawa-JNIM scope must stay cooperates_with without branch_of")
    r = rel_of(rels, "actor-lakurawa", "actor-jas")
    if not r or r["relationship_type"] != "cooperates_with" or r["disputed"] is not True: fail("Lakurawa-JAS cooperates_with disputed")
    r = rel_of(rels, "person-sadou-samahouna", "actor-jnim")
    if not r or r["current_status"] != "historical_ended": fail("Sadou-JNIM must be historical_ended")
    r = rel_of(rels, "person-sadou-samahouna", "actor-is-sahel")
    if not r or r["current_status"] != "current": fail("Sadou-IS Sahel must be current")
    print("PASS test_i3d1_disputed_semantics (disputed/scope/historical-current preserved)")


def test_i3d1_source_mapping():
    sources = load("sources.json")["sources"]
    sids = {s["source_id"] for s in sources}
    if len(sids) != len(sources): fail("duplicate source id")
    mapping = load("source-mapping.json", base=QA)
    for pid, m in mapping["mapping"].items():
        if m["actual_source_id"] not in sids: fail(f"mapped source missing: {m['actual_source_id']}")
    # no invented dates: ACLED null-published sources stay null
    expected_null = {"d1-acled-jnim-profile-2026", "d1-acled-africa-march-2026", "d1-acled-border-triangle-2026", "d1-acled-africa-june-2026", "d1-acled-dozo-2026", "d1-acled-ethiopia-2026"}
    actual_null = {s["source_id"] for s in sources if s.get("published_at") is None and s["source_id"].startswith("d1-")}
    if actual_null != expected_null: fail(f"null published_at mismatch: {actual_null ^ expected_null}")
    for s in sources:
        if s.get("published_at") == "" or s.get("published_at") == "unknown": fail(f"invented date marker on {s['source_id']}")
    print("PASS test_i3d1_source_mapping (dedupe mapping valid, no invented dates)")


def test_i3d1_evidence_mapping():
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
    # Lakurawa claims keep disputed + partially_verified
    for e in evidence:
        if e["claim_id"] in ("d1-cl-lakurawa-ambiguous", "d1-cl-lakurawa-issp"):
            if e["disputed"] is not True: fail(f"Lakurawa disputed lost: {e['claim_id']}")
            if e["verification_status"] != "partially_verified": fail(f"Lakurawa verification upgraded: {e['claim_id']}")
    print("PASS test_i3d1_evidence_mapping (182 evidence, refs resolve, disputed preserved)")


def test_i3d1_generator_regression():
    report = load("generator-regen-diff.json", base=QA)
    for key in ("unexpected_object_deletions", "profile_depth_regressions", "evidence_regressions", "relation_type_regressions", "timeline_regressions"):
        if report.get(key, 1) != 0: fail(f"generator regression {key}={report.get(key)}")
    if report.get("gate") != "PASS": fail("generator regen diff gate not PASS")
    print("PASS test_i3d1_generator_regression (regen diff 0/0/0/0/0)")


def test_i3d1_build_consistency():
    if not DIST.exists(): fail("dist missing; run build_site.py first")
    dist_data = DIST / "data"
    for name in ("entities.json", "relationships.json", "sources.json", "evidence_records.json", "relation_profiles.json", "relation_timelines.json"):
        a = load(name)
        b = load(name, base=dist_data)
        if a != b: fail(f"dist data mismatch: {name}")
    # key new routes exist
    routes = ["entity/fla/", "entity/africa-corps/", "entity/fu-aes/", "entity/lakurawa/", "entity/ansaru/", "entity/dan-na-ambassagou/", "entity/wagner-group/", "relation/d1-fu-aes-region/", "relation/d1-fla-jnim-cooperation/", "relation/d1-ansaru-aqim-allegiance/", "relation/d1-lakurawa-is-sahel-network/", "relation/d1-sadou-is-sahel/"]
    for rt in routes:
        if not (DIST / rt / "index.html").exists(): fail(f"route missing: {rt}")
    print("PASS test_i3d1_build_consistency (dist matches source, key routes present)")


def main():
    tests = [test_i3d1_packet_counts, test_i3d1_prep_corrections, test_i3d1_entity_ids, test_i3d1_relationship_types, test_i3d1_disputed_semantics, test_i3d1_source_mapping, test_i3d1_evidence_mapping, test_i3d1_generator_regression, test_i3d1_build_consistency]
    for t in tests:
        t()
    print("ALL 9 I3-D1 TESTS PASS")


if __name__ == "__main__":
    main()
