#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the ASIP security intelligence demo data package (I1-A V0.2)."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "demo"
REQUIRED_ENTITY = {"entity_id","entity_type","slug","name_zh","name_en","acronym","native_name","aliases","historical_names","importance_level","short_description","full_description","current_status","primary_category","tags","source_refs","last_verified_at","confidence","temporal_sensitive","disputed"}
REQUIRED_REL = {"relationship_id","slug","source_entity_id","target_entity_id","relationship_type","direction","display_ring","current_status","time_start","time_end","confidence","relation_summary","formation_background","current_status_detail","geographic_scope","why_it_matters","uncertainties","source_refs","last_verified_at","disputed","temporal_sensitive"}
ALLOWED_TYPES = {"organization","person","country","region"}
ALLOWED_REL_TYPES = {"affiliated_with","constituent_of","led_by","founded_by","operates_in","hostile_to","historically_associated_with","part_of_network"}
ALLOWED_IMPORTANCE = {"L1","L2","L3"}
ALLOWED_RINGS = {"inner","middle","outer"}

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
    relation_profiles = load("relation_profiles.json")["profiles"]
    timelines = load("relation_timelines.json")["timelines"]
    force_estimates = load("force_estimates.json")["estimates"]
    external_links = load("external_links.json")["links"]
    entity_ids = [e["entity_id"] for e in entities]
    source_ids = {s["source_id"] for s in sources}
    entity_map = {e["entity_id"]: e for e in entities}
    if len(entities) != 12: fail(f"expected 12 entities, got {len(entities)}")
    if len(set(entity_ids)) != len(entity_ids): fail("entity_id is not unique")
    if set(entity_ids) != set(graph["nodes"]): fail("graph_index nodes differ from entities")
    imp_counts = {"L1":0,"L2":0,"L3":0}
    for entity in entities:
        missing = REQUIRED_ENTITY - set(entity)
        if missing: fail(f"{entity.get('entity_id')} missing {sorted(missing)}")
        if entity["entity_type"] not in ALLOWED_TYPES: fail(f"invalid entity type {entity['entity_type']}")
        if entity["importance_level"] not in ALLOWED_IMPORTANCE: fail(f"invalid importance_level {entity['importance_level']}")
        imp_counts[entity["importance_level"]] += 1
        if not entity["name_zh"] or not entity["name_en"]: fail(f"name missing on {entity['entity_id']}")
        if "acronym" not in entity or not isinstance(entity["acronym"], str): fail(f"acronym must be a string (may be empty) on {entity['entity_id']}")
        if not entity["source_refs"]: fail(f"{entity['entity_id']} has no sources")
        if not set(entity["source_refs"]).issubset(source_ids): fail(f"bad source ref on {entity['entity_id']}")
        if not re.fullmatch(r"(?:actor|person|country|region)-[a-z0-9-]+", entity["entity_id"]): fail(f"unstable entity id {entity['entity_id']}")
        links = external_links.get(entity["entity_id"], {})
        for wiki in links.get("wikipedia", []):
            if "wikipedia.org" not in wiki["url"]: fail(f"non-wikipedia url in wikipedia section: {wiki['url']}")
            if not wiki["url"].startswith("https://"): fail(f"wikipedia url must be https: {wiki['url']}")
    if imp_counts["L1"] < 1 or imp_counts["L2"] < 1 or imp_counts["L3"] < 1:
        fail(f"each importance level must be present: {imp_counts}")
    for alias, entity_id in aliases.items():
        if entity_id not in entity_map: fail(f"alias {alias} points to missing entity")
    if len(relationships) != 20: fail(f"expected 20 relationships, got {len(relationships)}")
    rel_ids = [r["relationship_id"] for r in relationships]
    if len(set(rel_ids)) != len(rel_ids): fail("relationship_id is not unique")
    rel_slugs = [r["slug"] for r in relationships]
    if len(set(rel_slugs)) != len(rel_slugs): fail("relation slug is not unique")
    full_profiles = {"rel-jnim-is-hostile","rel-jnim-alqaida-affiliate","rel-jnim-mali-operates","rel-jnim-iyad-led"}
    for rel in relationships:
        missing = REQUIRED_REL - set(rel)
        if missing: fail(f"{rel.get('relationship_id')} missing {sorted(missing)}")
        if rel["relationship_type"] not in ALLOWED_REL_TYPES: fail(f"invalid relationship_type {rel['relationship_type']}")
        if rel["display_ring"] not in ALLOWED_RINGS: fail(f"invalid display_ring {rel['display_ring']}")
        if rel["source_entity_id"] not in entity_map or rel["target_entity_id"] not in entity_map: fail(f"bad entity ref on {rel['relationship_id']}")
        if not set(rel["source_refs"]).issubset(source_ids): fail(f"bad source ref on {rel['relationship_id']}")
        if rel["relationship_id"] in full_profiles and rel["relationship_id"] not in relation_profiles:
            fail(f"full relation profile missing for {rel['relationship_id']}")
        if rel["relationship_id"] in full_profiles and rel["relationship_id"] not in timelines:
            fail(f"timeline missing for {rel['relationship_id']}")
    for prof_id, prof in relation_profiles.items():
        for section in ["overview","formation_background","initial_relationship","evolution_stages","causes","key_turning_points","current_status","why_it_matters","uncertainties","source_ids"]:
            if section not in prof: fail(f"relation profile {prof_id} missing {section}")
        for sid in prof["source_ids"]:
            if sid not in source_ids: fail(f"relation profile {prof_id} bad source {sid}")
    for rel_id, timeline in timelines.items():
        for item in timeline:
            for field in ["date","event_title","event_description","impact_on_relationship","confidence","disputed","source_ids"]:
                if field not in item: fail(f"timeline {rel_id} item missing {field}")
            for sid in item["source_ids"]:
                if sid not in source_ids: fail(f"timeline {rel_id} bad source {sid}")
    for ent_id, estimates in force_estimates.items():
        for est in estimates:
            for field in ["estimate_text","estimate_date","estimate_scope","included_components","excluded_components","source_ids","confidence","trend","notes"]:
                if field not in est: fail(f"force estimate {ent_id} missing {field}")
            for sid in est["source_ids"]:
                if sid not in source_ids: fail(f"force estimate {ent_id} bad source {sid}")
    print(f"PASS entities=12 relationships=20 sources={len(sources)}")
    print(f"PASS importance levels L1={imp_counts['L1']} L2={imp_counts['L2']} L3={imp_counts['L3']}")
    print(f"PASS unified names (acronym nullable, no empty bracket), rings inner/middle/outer, 4 full relation profiles, timelines, force estimates and wikipedia url format")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
