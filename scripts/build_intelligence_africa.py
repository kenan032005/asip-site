#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the ASIP Africa security intelligence production site (I2-A).
Generates home, regions, countries, entities, relations, network, sources routes
with base-path-relative links and data quality validation.
"""
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "intelligence" / "africa"
TEMPLATES = ROOT / "intelligence" / "africa" / "_templates"

def read(name):
    with (DATA / name).open(encoding="utf-8") as f:
        return json.load(f)

def fail(msg):
    raise SystemExit("AFRICA DATA FAIL: " + msg)

def validate():
    regions = read("regions.json")["regions"]
    countries = read("countries.json")["countries"]
    entities = read("entities.json")["entities"]
    rels = read("relationships.json")["relationships"]
    sources = read("sources.json")["sources"]
    evidence = read("evidence_records.json")["evidence"]
    profiles = read("relation_profiles.json")["profiles"]
    timelines = read("relation_timelines.json")["timelines"]
    estimates = read("force_estimates.json")["estimates"]
    links = read("external_links.json")["links"]
    eids = [e["entity_id"] for e in entities]
    cids = [c["country_id"] for c in countries]
    rids = [r["region_id"] for r in regions]
    sids = {s["source_id"] for s in sources}
    evids = {e["evidence_id"] for e in evidence}
    if len(eids) != len(set(eids)): fail("duplicate entity id")
    if len(cids) != len(set(cids)): fail("duplicate country id")
    if len(rids) != len(set(rids)): fail("duplicate region id")
    if len({e["slug"] for e in entities}) != len(entities): fail("duplicate entity slug")
    if len(rels) < 60: fail(f"relations < 60: {len(rels)}")
    if len(rels) > 100: fail(f"relations > 100: {len(rels)}")
    if len({r["relationship_id"] for r in rels}) != len(rels): fail("duplicate relation id")
    if len(evidence) < 60: fail(f"evidence < 60: {len(evidence)}")
    if len(sources) < 25: fail(f"sources < 25: {len(sources)}")
    if len(regions) < 7: fail(f"regions < 7: {len(regions)}")
    if len(countries) < 12: fail(f"countries < 12: {len(countries)}")
    for e in entities:
        if e["importance_level"] not in ("L1", "L2", "L3"): fail(f"bad importance on {e['entity_id']}")
        for rid in e.get("region_ids", []):
            if rid not in rids: fail(f"bad region ref {rid} on {e['entity_id']}")
        for cid in e.get("country_ids", []):
            if cid not in cids: fail(f"bad country ref {cid} on {e['entity_id']}")
        for sid in e.get("source_refs", []):
            if sid not in sids: fail(f"bad source ref {sid} on {e['entity_id']}")
        if e.get("acronym", "") is None: fail(f"acronym must be string on {e['entity_id']}")
    for r in rels:
        valid_ends = set(eids) | set(cids)
        if r["source_entity_id"] not in valid_ends or r["target_entity_id"] not in valid_ends: fail(f"bad entity ref on {r['relationship_id']}")
        if r["display_ring"] not in ("inner", "middle", "outer"): fail(f"bad ring on {r['relationship_id']}")
        for sid in r.get("source_refs", []):
            if sid not in sids: fail(f"bad source ref on {r['relationship_id']}")
    for c in countries:
        if c["risk_level"] not in ("extreme", "high", "medium", "low"): fail(f"bad risk on {c['country_id']}")
        for rid in c.get("region_ids", []):
            if rid not in rids: fail(f"bad region ref {rid} on {c['country_id']}")
        for sid in c.get("source_ids", []):
            if sid not in sids: fail(f"bad source ref on {c['country_id']}")
    for r in regions:
        for cid in r.get("countries", []):
            if cid not in cids: fail(f"bad country ref {cid} on {r['region_id']}")
        for sid in r.get("source_ids", []):
            if sid not in sids: fail(f"bad source ref on {r['region_id']}")
    for pid, p in profiles.items():
        for sid in p.get("source_ids", []):
            if sid not in sids: fail(f"bad source ref in profile {pid}")
    for tid, tl in timelines.items():
        for item in tl:
            for sid in item.get("source_ids", []):
                if sid not in sids: fail(f"bad source ref in timeline {tid}")
    for eid, est in estimates.items():
        for x in est:
            for sid in x.get("source_ids", []):
                if sid not in sids: fail(f"bad source ref in estimate {eid}")
    for eid, lk in links.items():
        for w in lk.get("wikipedia", []):
            if "wikipedia.org" not in w["url"]: fail(f"bad wikipedia url {w['url']}")
    for ev in evidence:
        if ev["source_id"] not in sids: fail(f"bad source ref in evidence {ev['evidence_id']}")
    print(f"  africa data OK: entities={len(entities)} relations={len(rels)} regions={len(regions)} countries={len(countries)} sources={len(sources)} evidence={len(evidence)} profiles={len(profiles)}")

def build(dist_root):
    validate()
    dist_root = Path(dist_root)
    target = dist_root / "intelligence" / "africa"
    if target.exists():
        shutil.rmtree(target)
    for sub in ["regions", "countries", "entities", "relations", "sources", "network", "region", "country", "entity", "relation"]:
        (target / sub).mkdir(parents=True, exist_ok=True)
    def tpl(name):
        return (TEMPLATES / name).read_text(encoding="utf-8")
    (target / "index.html").write_text(tpl("index.html"), encoding="utf-8")
    (target / "regions" / "index.html").write_text(tpl("regions.html"), encoding="utf-8")
    (target / "countries" / "index.html").write_text(tpl("countries.html"), encoding="utf-8")
    (target / "entities" / "index.html").write_text(tpl("entities.html"), encoding="utf-8")
    (target / "relations" / "index.html").write_text(tpl("relations.html"), encoding="utf-8")
    (target / "sources" / "index.html").write_text(tpl("sources.html"), encoding="utf-8")
    (target / "network" / "index.html").write_text(tpl("network.html"), encoding="utf-8")
    regions = read("regions.json")["regions"]
    countries = read("countries.json")["countries"]
    entities = read("entities.json")["entities"]
    rels = read("relationships.json")["relationships"]
    for r in regions:
        d = target / "region" / r["slug"]; d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(tpl("region.html").replace("__REGION_SLUG__", r["slug"]), encoding="utf-8")
    for c in countries:
        d = target / "country" / c["slug"]; d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(tpl("country.html").replace("__COUNTRY_SLUG__", c["slug"]), encoding="utf-8")
    for e in entities:
        d = target / "entity" / e["slug"]; d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(tpl("entity.html").replace("__ENTITY_SLUG__", e["slug"]), encoding="utf-8")
    for r in rels:
        slug = r.get("slug") or r["relationship_id"]
        d = target / "relation" / slug; d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(tpl("relation.html").replace("__RELATION_SLUG__", slug), encoding="utf-8")
    data_target = target / "data"
    data_target.mkdir(parents=True, exist_ok=True)
    for f in sorted(DATA.glob("*.json")):
        shutil.copy2(f, data_target / f.name)
    route_count = 1 + 6 + len(regions) + len(countries) + len(entities) + len(rels)
    print(f"  intelligence africa: {route_count} routes (home + 6 index + {len(regions)} regions + {len(countries)} countries + {len(entities)} entities + {len(rels)} relations) + data")

if __name__ == "__main__":
    build(ROOT / "dist")
