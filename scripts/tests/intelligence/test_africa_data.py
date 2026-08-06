#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate ASIP Africa intelligence production data package (I2-A)."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "africa"

def load(name):
    with (DATA / name).open(encoding="utf-8") as f:
        return json.load(f)

def fail(msg):
    raise AssertionError(msg)

def main():
    regions = load("regions.json")["regions"]
    countries = load("countries.json")["countries"]
    entities = load("entities.json")["entities"]
    rels = load("relationships.json")["relationships"]
    sources = load("sources.json")["sources"]
    evidence = load("evidence_records.json")["evidence"]
    profiles = load("relation_profiles.json")["profiles"]
    timelines = load("relation_timelines.json")["timelines"]
    estimates = load("force_estimates.json")["estimates"]
    links = load("external_links.json")["links"]
    alias = load("alias_index.json")["aliases"]
    graph = load("graph_index.json")

    eids = [e["entity_id"] for e in entities]
    cids = {c["country_id"] for c in countries}
    rids = {r["region_id"] for r in regions}
    sids = {s["source_id"] for s in sources}
    evids = {e["evidence_id"] for e in evidence}
    eid_set = set(eids)

    # counts
    if len(regions) < 7: fail(f"regions<7: {len(regions)}")
    if len(countries) < 12: fail(f"countries<12: {len(countries)}")
    if not (30 <= len(entities) <= 45): fail(f"entities={len(entities)} outside 30-45")
    if not (60 <= len(rels) <= 100): fail(f"relations={len(rels)} outside 60-100")
    if len(sources) < 25: fail(f"sources<25: {len(sources)}")
    if len(evidence) < 60: fail(f"evidence<60: {len(evidence)}")
    if len(profiles) < 8: fail(f"profiles<8: {len(profiles)}")

    # uniqueness
    if len(eids) != len(set(eids)): fail("duplicate entity id")
    if len({e["slug"] for e in entities}) != len(entities): fail("duplicate slug")
    if len({r["relationship_id"] for r in rels}) != len(rels): fail("duplicate relation id")
    if len({s["source_id"] for s in sources}) != len(sources): fail("duplicate source id")
    if len({c["country_id"] for c in countries}) != len(countries): fail("duplicate country id")
    if len({r["region_id"] for r in regions}) != len(regions): fail("duplicate region id")

    # importance & independence
    for e in entities:
        if e["importance_level"] not in ("L1", "L2", "L3"): fail(f"bad importance {e['entity_id']}")
        if "acronym" not in e or not isinstance(e["acronym"], str): fail(f"acronym type {e['entity_id']}")
        for rid in e.get("region_ids", []):
            if rid not in rids: fail(f"bad region ref {e['entity_id']}")
        for cid in e.get("country_ids", []):
            if cid not in cids: fail(f"bad country ref {e['entity_id']}")
        for sid in e.get("source_refs", []):
            if sid not in sids: fail(f"bad source ref {e['entity_id']}")
    # risk level separate from importance
    for c in countries:
        if c["risk_level"] not in ("extreme", "high", "medium", "low"): fail(f"bad risk {c['country_id']}")
        for rid in c.get("region_ids", []):
            if rid not in rids: fail(f"bad region ref {c['country_id']}")

    # multi-region mapping requirements
    chad = next(c for c in countries if c["country_id"] == "country-chad")
    if "region-central-sahel" not in chad["region_ids"] or "region-lake-chad-basin" not in chad["region_ids"]:
        fail("Chad must belong to both central-sahel and lake-chad-basin")
    moz = next(c for c in countries if c["country_id"] == "country-mozambique")
    if "region-central-sahel" in moz["region_ids"]: fail("Mozambique must NOT be in sahel")
    if "region-southeast-africa-mozambique" not in moz["region_ids"]: fail("Mozambique missing its region")
    sudan = next(c for c in countries if c["country_id"] == "country-sudan")
    if "region-sudan-red-sea-horn" not in sudan["region_ids"]: fail("Sudan missing its region")
    libya = next(c for c in countries if c["country_id"] == "country-libya")
    if "region-north-africa-sahara" not in libya["region_ids"]: fail("Libya missing its region")

    # relation integrity
    for r in rels:
        valid = eid_set | cids
        if r["source_entity_id"] not in valid or r["target_entity_id"] not in valid: fail(f"bad entity ref {r['relationship_id']}")
        if r["display_ring"] not in ("inner", "middle", "outer"): fail(f"bad ring {r['relationship_id']}")
        for sid in r.get("source_refs", []):
            if sid not in sids: fail(f"bad source ref {r['relationship_id']}")

    # evidence integrity
    for ev in evidence:
        if ev["source_id"] not in sids: fail(f"bad source {ev['evidence_id']}")
        if ev.get("confidence") not in ("high", "medium_high", "medium", "low"): fail(f"bad confidence {ev['evidence_id']}")
        for cid in ev.get("country_ids", []):
            if cid not in cids: fail(f"bad country ref {ev['evidence_id']}")

    # relation profile/timeline coverage of 4 regions
    covered_regions = {"central-sahel": False, "lake-chad": False, "sudan": False, "mozambique": False}
    for pid in profiles:
        if "jnim-is-sahel" in pid or "jnim-alqaida" in pid: covered_regions["central-sahel"] = True
        if "jas-iswap" in pid or "iswap-islamic" in pid or "chad-mnjtf" in pid: covered_regions["lake-chad"] = True
        if "saf-rsf" in pid: covered_regions["sudan"] = True
        if "is-moz" in pid or "rdf-mozambique" in pid: covered_regions["mozambique"] = True
    for k, v in covered_regions.items():
        if not v: fail(f"relation profile coverage missing: {k}")

    # force estimates have date+source
    for eid, est in estimates.items():
        for x in est:
            if not x.get("estimate_date") or not x.get("source_ids") or not x.get("estimate_text"): fail(f"estimate missing fields {eid}")

    # wikipedia url format
    for eid, lk in links.items():
        for w in lk.get("wikipedia", []):
            if "wikipedia.org" not in w["url"] or not w["url"].startswith("https://"): fail(f"bad wikipedia url {eid}")

    # alias search index
    if "iswap" not in alias or "jnim" not in alias: fail("alias index missing key terms")
    if len(alias) < 100: fail(f"alias index too small: {len(alias)}")

    # graph index
    if set(graph["nodes"]) != eid_set: fail("graph index nodes mismatch")
    if len(graph["relationship_ids"]) != len(rels): fail("graph index relations mismatch")
    if graph["importance_levels"] != ["L1", "L2", "L3"]: fail("importance levels wrong")
    if set(graph["risk_levels"]) != {"extreme", "high", "medium", "low"}: fail("risk levels wrong")

    print(f"PASS africa: entities={len(entities)} relations={len(rels)} regions={len(regions)} countries={len(countries)}")
    print(f"PASS sources={len(sources)} evidence={len(evidence)} profiles={len(profiles)} timelines={len(timelines)}")
    print("PASS uniqueness, importance/risk/confidence independence, multi-region mapping, refs, estimates, wikipedia, indexes")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
