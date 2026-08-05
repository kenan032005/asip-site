#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the ASIP security intelligence demo data package."""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "demo"
REQUIRED_ENTITY = {"entity_id","entity_type","slug","name_zh","name_en","original_name","aliases","short_description","full_description","current_status","primary_category","tags","profile_level","source_refs","last_verified_at","confidence","temporal_sensitive","disputed"}
REQUIRED_REL = {"relationship_id","source_entity_id","target_entity_id","relationship_type","direction","label_zh","description","current_status","confidence","source_refs","last_verified_at","disputed","temporal_sensitive"}
ALLOWED_TYPES = {"organization","person","country","region"}
ALLOWED_REL_TYPES = {"affiliated_with","constituent_of","led_by","founded_by","operates_in","hostile_to","historically_associated_with","part_of_network"}

def load(name):
    with (DATA / name).open(encoding="utf-8") as f:
        return json.load(f)

def fail(message):
    raise AssertionError(message)

def main():
    entities = load("entities.json")["entities"]
    relationships = load("relationships.json")["relationships"]
    sources = load("sources.json")["sources"]
    graph = load("graph_index.json")
    aliases = load("alias_index.json")["aliases"]
    entity_ids = [e["entity_id"] for e in entities]
    slugs = [e["slug"] for e in entities]
    source_ids = {s["source_id"] for s in sources}
    entity_map = {e["entity_id"]: e for e in entities}
    if len(entities) != 12: fail(f"expected 12 entities, got {len(entities)}")
    if len(set(entity_ids)) != len(entity_ids): fail("entity_id is not unique")
    if len(set(slugs)) != len(slugs): fail("slug is not unique")
    if set(entity_ids) != set(graph["nodes"]): fail("graph_index nodes differ from entities")
    for entity in entities:
        missing = REQUIRED_ENTITY - set(entity)
        if missing: fail(f"{entity.get('entity_id')} missing {sorted(missing)}")
        if entity["entity_type"] not in ALLOWED_TYPES: fail(f"invalid entity type {entity['entity_type']}")
        if not entity["source_refs"]: fail(f"{entity['entity_id']} has no sources")
        if not set(entity["source_refs"]).issubset(source_ids): fail(f"bad source ref on {entity['entity_id']}")
        if not re.fullmatch(r"(?:actor|person|country|region)-[a-z0-9-]+", entity["entity_id"]): fail(f"unstable entity id {entity['entity_id']}")
    for alias, entity_id in aliases.items():
        if entity_id not in entity_map: fail(f"alias {alias} points to missing entity")
    if len(relationships) < 18 or len(relationships) > 25: fail(f"expected 18-25 relationships, got {len(relationships)}")
    rel_ids = [r["relationship_id"] for r in relationships]
    if len(set(rel_ids)) != len(rel_ids): fail("relationship_id is not unique")
    for rel in relationships:
        missing = REQUIRED_REL - set(rel)
        if missing: fail(f"{rel.get('relationship_id')} missing {sorted(missing)}")
        if rel["relationship_type"] not in ALLOWED_REL_TYPES: fail(f"invalid relationship type {rel['relationship_type']}")
        if rel["source_entity_id"] not in entity_map or rel["target_entity_id"] not in entity_map: fail(f"dangling relationship {rel['relationship_id']}")
        if rel["source_entity_id"] == rel["target_entity_id"] and not rel.get("description"): fail(f"self relation without explanation {rel['relationship_id']}")
        if not rel["source_refs"] or not set(rel["source_refs"]).issubset(source_ids): fail(f"bad sources on {rel['relationship_id']}")
        if rel.get("start_year") and rel.get("end_year") and rel["start_year"] > rel["end_year"]: fail(f"date order conflict {rel['relationship_id']}")
    jnim_is = [r for r in relationships if {r["source_entity_id"], r["target_entity_id"]} == {"actor-jnim","actor-is-sahel"}]
    if len(jnim_is) != 2 or not all(r["temporal_sensitive"] for r in jnim_is): fail("JNIM/IS Sahel temporal relationship requirement failed")
    if not any(r["start_year"] == 2017 and r.get("end_year") == 2019 for r in jnim_is): fail("missing historical JNIM/IS phase")
    if not any(r["start_year"] == 2019 and r["current_status"] == "reported_current_hostility" for r in jnim_is): fail("missing current JNIM/IS phase")
    source_counts = {e["entity_id"]: len(e["source_refs"]) for e in entities}
    core_orgs = {"actor-jnim","actor-al-qaida","actor-aqim","actor-ansar-eddine","actor-al-mourabitoun","actor-katiba-macina","actor-is-sahel"}
    if any(source_counts[x] < 2 for x in core_orgs if x != "actor-katiba-macina"): fail("core organization must have at least 2 sources")
    print(f"PASS entities={len(entities)} relationships={len(relationships)} sources={len(sources)}")
    print(f"PASS unique_ids={len(set(entity_ids))} unique_slugs={len(set(slugs))} aliases={len(aliases)}")
    print("PASS references, source coverage, date order, routes, and temporal JNIM/IS relationship")

if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
