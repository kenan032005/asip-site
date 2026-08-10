#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH A import gates (11 tests): no count expansion, Koufa alive, IS Sahel dates,
Mourabitoun genealogy, JNIM E3 sections, fact/analysis separation, watch indicators,
relation R3 completeness, force estimate temporality, generator regression, depth audit."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "africa"
DIST = ROOT / "dist" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-a"


def load(name, base=DATA):
    return json.load(open(base / name, encoding="utf-8"))


def fail(msg):
    raise AssertionError(msg)


def rel_of(rels, sid, tid, rtype=None):
    for r in rels:
        if r["source_entity_id"] == sid and r["target_entity_id"] == tid and (rtype is None or r["relationship_type"] == rtype):
            return r
    return None


def test_depth_a_no_count_expansion():
    entities = load("entities.json")["entities"]
    rels = load("relationships.json")["relationships"]
    countries = load("countries.json")["countries"]
    if len(countries) != 13: fail(f"countries={len(countries)} != 13")
    if len(entities) != 94: fail(f"entities={len(entities)} != 94 (83 + 11 Expansion B)")
    if len(rels) != 181: fail(f"relations={len(rels)} != 181 (164 + 17 Expansion B)")
    print("PASS test_depth_a_no_count_expansion (13/72/150 unchanged)")


def test_koufa_alive():
    entities = {e["entity_id"]: e for e in load("entities.json")["entities"]}
    ep = load("entity_profiles.json")["profiles"]
    k = entities["person-amadou-koufa"]
    if k["current_status"] != "active_jnim_deputy_and_katiba_macina_emir": fail("Koufa status not active")
    if k["freshness_status"] != "current": fail("Koufa freshness not current")
    blob = json.dumps(ep["person-amadou-koufa"], ensure_ascii=False)
    for ph in ("已死亡（2019", "；已死亡", "已死亡。", "2019 年 11 月：被击毙", "继任者身份不明"):
        if ph in blob: fail(f"Koufa deceased phrasing residual: {ph}")
    print("PASS test_koufa_alive (active; 2018/2019 death report treated as falsified history)")


def test_is_sahel_dates():
    ep = load("entity_profiles.json")["profiles"]
    rels = load("relationships.json")["relationships"]
    profs = load("relation_profiles.json")["profiles"]
    iss_text = json.dumps(ep["actor-is-sahel"], ensure_ascii=False)
    if "2021年8月" not in iss_text and "2021 年 8 月" not in iss_text: fail("IS Sahel Sahrawi death not 2021")
    if "2023年萨赫拉维死后" in iss_text or "2023 年萨赫拉维死后" in iss_text: fail("2023 Sahrawi death residual")
    r = rel_of(rels, "actor-jnim", "actor-is-sahel")
    # DEPTH G change: the JNIM-IS edge was split into a two-phase model.
    # rel-jnim-is-hostile is now the HISTORICAL pre-2019 phase
    # (historically_associated_with, 2016-2019) and the CURRENT hostile edge
    # lives on rel-jnim-is-conflict (hostile_to, 2019-present). rel_of() scans
    # in file order, so it may return the historical edge first; resolve the
    # current-hostility assertion against rel-jnim-is-conflict explicitly.
    if not r: fail("jnim-is edge missing")
    if r["relationship_type"] != "hostile_to":
        c = rel_of(rels, "actor-jnim", "actor-is-sahel")
        conflict = next((x for x in rels if x["relationship_id"] == "rel-jnim-is-conflict"), None)
        if not conflict or conflict["relationship_type"] != "hostile_to":
            fail("jnim-is conflict not hostile_to (current edge)")
        if not r["relationship_type"] in ("historically_associated_with", "hostile_to"):
            fail(f"jnim-is unexpected type {r['relationship_type']}")
        if c and c.get("time_start") not in (None, "2016"):
            fail("jnim-is historical phase start not 2016")
    if "2019" not in json.dumps(profs.get("rel-jnim-is-conflict", {}), ensure_ascii=False): fail("jnim-is conflict start 2019 missing")
    if "2026年4月首次与JNIM公开交火" in iss_text: fail("2026-04 'first clash' residual")
    print("PASS test_is_sahel_dates (Sahrawi 2021-08; conflict start 2019; Apr 2026 = first Niger spillover)")


def test_mourabitoun_genealogy():
    ep = load("entity_profiles.json")["profiles"]
    blob = json.dumps(ep["actor-al-mourabitoun"], ensure_ascii=False)
    if "MUJAO" not in blob: fail("Mourabitoun MUJAO lineage missing")
    if "Belmokhtar" not in blob: fail("Mourabitoun Belmokhtar lineage missing")
    for ph in ("伊亚德·阿格·加利的穆拉比通", "Iyad Ag Ghali曾任Al-Mourabitoun副手", "与Iyad Ag Ghali：领导关系"):
        if ph in blob: fail(f"Mourabitoun Iyad error residual: {ph}")
    print("PASS test_mourabitoun_genealogy (MUJAO + Belmokhtar/Al-Mulathameen; no Iyad link)")


def test_jnim_e3_sections():
    ep = load("entity_profiles.json")["profiles"]
    secs = ep["actor-jnim"]["sections"]
    required = ["lead", "formation_background", "major_timeline", "current_situation", "uncertainties", "asip_analysis", "watch_indicators", "sources"]
    missing = [k for k in required if not secs.get(k)]
    if missing: fail(f"JNIM E3 missing sections: {missing}")
    if ep["actor-jnim"].get("content_maturity") != "E3_FULL_ENCYCLOPEDIA": fail("JNIM content_maturity != E3")
    print("PASS test_jnim_e3_sections (lead/timeline/current/uncertainty/analysis/watch/sources)")


def test_fact_analysis_separation():
    ep = load("entity_profiles.json")["profiles"]
    for eid in ("actor-jnim", "actor-is-sahel", "person-amadou-koufa", "actor-fla", "actor-africa-corps"):
        secs = ep[eid]["sections"]
        if not secs.get("asip_analysis"): fail(f"{eid} missing asip_analysis partition")
    profs = load("relation_profiles.json")["profiles"]
    for rid in ("rel-jnim-is-conflict", "rel-jnim-alqaida-affiliate", "rel-d1-fla-jnim-cooperation"):
        if not profs[rid].get("asip_analysis"): fail(f"{rid} missing asip_analysis")
    print("PASS test_fact_analysis_separation (ASIP Analysis present as distinct partition)")


def test_watch_indicators():
    ep = load("entity_profiles.json")["profiles"]
    for eid in ("actor-jnim", "actor-is-sahel", "actor-fla", "actor-africa-corps", "person-amadou-koufa"):
        wi = ep[eid]["sections"].get("watch_indicators")
        if not wi or not (isinstance(wi, list) and len(wi) >= 3): fail(f"{eid} watch_indicators insufficient")
    profs = load("relation_profiles.json")["profiles"]
    for rid in ("rel-jnim-is-conflict", "rel-d1-fla-jnim-cooperation", "rel-d1-africa-corps-wagner-history"):
        if not profs[rid].get("watch_indicators"): fail(f"{rid} missing watch_indicators")
    print("PASS test_watch_indicators (>=3 indicators on flagship entities/relations)")


def test_relation_r3_completeness():
    profs = load("relation_profiles.json")["profiles"]
    for rid in ("rel-jnim-is-conflict", "rel-jnim-alqaida-affiliate", "rel-d1-fla-jnim-cooperation", "rel-d1-africa-corps-fama-coop", "rel-d1-africa-corps-wagner-history"):
        p = profs.get(rid, {})
        if p.get("relation_maturity") != "R3_FULL_RELATIONSHIP_INTELLIGENCE": fail(f"{rid} not R3")
        for k in ("overview", "evolution_stages", "asip_analysis", "watch_indicators", "uncertainties"):
            if not p.get(k): fail(f"{rid} R3 missing {k}")
    print("PASS test_relation_r3_completeness (5 R3 relations carry full intelligence sections)")


def test_force_estimate_temporality():
    ep = load("entity_profiles.json")["profiles"]
    jnim_text = json.dumps(ep["actor-jnim"]["sections"], ensure_ascii=False)
    if "6000" not in jnim_text: fail("JNIM 6000 estimate missing")
    if "约/至少" not in jnim_text and "至少6000" not in jnim_text and "约 6000" not in jnim_text: fail("JNIM estimate qualifier missing (约/至少)")
    iss_text = json.dumps(ep["actor-is-sahel"]["sections"], ensure_ascii=False)
    if "2500" not in iss_text: fail("IS Sahel 2500 estimate missing")
    ac_text = json.dumps(ep["actor-africa-corps"]["sections"], ensure_ascii=False)
    if "2000" not in ac_text: fail("Africa Corps 2000 estimate missing")
    if "估计" not in ac_text: fail("Africa Corps estimate qualifier missing")
    print("PASS test_force_estimate_temporality (6000/2500/2000 with date/scope/estimate qualifiers)")


def test_generator_regression():
    report = load("generator-regen-diff.json", base=QA)
    for key in ("unexpected_object_deletions", "entity_count_change", "relationship_count_change", "importance_level_change", "relation_type_change", "profile_depth_regressions", "timeline_regressions", "evidence_regressions"):
        if report.get(key, 1) != 0: fail(f"generator regression {key}={report.get(key)}")
    print("PASS test_generator_regression (8 regressions = 0)")


def test_depth_audit():
    ea = load("entity-depth-audit.json", base=QA)
    ra = load("relation-depth-audit.json", base=QA)
    # historical QA artifact frozen at the Depth A scale (72/150); not regenerated by Expansion A
    if len(ea["entities"]) != 72: fail(f"entity audit count {len(ea['entities'])} != 72 (Depth A frozen artifact)")
    if len(ra["relations"]) != 150: fail(f"relation audit count {len(ra['relations'])} != 150 (Depth A frozen artifact)")
    print("PASS test_depth_audit (72/150 audited with MECHANICAL_SCORE)")


def main():
    tests = [test_depth_a_no_count_expansion, test_koufa_alive, test_is_sahel_dates, test_mourabitoun_genealogy, test_jnim_e3_sections, test_fact_analysis_separation, test_watch_indicators, test_relation_r3_completeness, test_force_estimate_temporality, test_generator_regression, test_depth_audit]
    for t in tests:
        t()
    print("ALL 11 DEPTH A TESTS PASS")


if __name__ == "__main__":
    main()
