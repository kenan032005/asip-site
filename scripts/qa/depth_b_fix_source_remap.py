#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH B fix: remap depthb-un-s2026-44 (same UN record 4102624 as d2-un-s2026-44)
to the existing source id, drop the wrongly-added duplicate source record,
then re-run import so the enhanced normalized-record dedupe takes effect.
Also fixes source-mapping.json entry."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-b"

def load(name):
    return json.load(open(DATA / name, encoding="utf-8"))

def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

OLD = "depthb-un-s2026-44"
NEW = "d2-un-s2026-44"

# 1. sources: drop duplicate record
srcs = load("sources.json")
before = len(srcs["sources"])
srcs["sources"] = [s for s in srcs["sources"] if s["source_id"] != OLD]
print(f"sources: {before} -> {len(srcs['sources'])} (dropped {OLD})")
dump(DATA / "sources.json", srcs)

# 2. evidence_records: remap source_id
ev = load("evidence_records.json")
n = 0
for e in ev["evidence"]:
    if e.get("source_id") == OLD:
        e["source_id"] = NEW
        n += 1
print(f"evidence remapped: {n}")
dump(DATA / "evidence_records.json", ev)

# 3. entities / relationships: remap in source_refs
ents = load("entities.json")
n = 0
for e in ents["entities"]:
    refs = e.get("source_refs", [])
    if OLD in refs:
        refs.remove(OLD)
        if NEW not in refs:
            refs.append(NEW)
        n += 1
dump(DATA / "entities.json", ents)
print(f"entities source_refs remapped: {n}")

rels = load("relationships.json")
n = 0
for r in rels["relationships"]:
    refs = r.get("source_refs", [])
    if OLD in refs:
        refs.remove(OLD)
        if NEW not in refs:
            refs.append(NEW)
        n += 1
dump(DATA / "relationships.json", rels)
print(f"relationships source_refs remapped: {n}")

# 4. relation_profiles: remap source_ids
rp = load("relation_profiles.json")
n = 0
for rid, pr in rp["profiles"].items():
    refs = pr.get("source_ids", [])
    if OLD in refs:
        refs.remove(OLD)
        if NEW not in refs:
            refs.append(NEW)
        n += 1
dump(DATA / "relation_profiles.json", rp)
print(f"relation_profiles source_ids remapped: {n}")

# 5. relation_timelines: remap source_ids
tl = load("relation_timelines.json")
n = 0
for rid, items in tl["timelines"].items():
    for it in items:
        refs = it.get("source_ids", [])
        if OLD in refs:
            refs.remove(OLD)
            if NEW not in refs:
                refs.append(NEW)
            n += 1
dump(DATA / "relation_timelines.json", tl)
print(f"timeline source_ids remapped: {n}")

# 6. fix source-mapping.json if present
sm_path = QA / "source-mapping.json"
if sm_path.exists():
    sm = json.load(open(sm_path, encoding="utf-8"))
    if OLD in sm["mapping"]:
        sm["mapping"][OLD] = {"actual_source_id": NEW, "matched_by": "url_normalized_record"}
    dump(sm_path, sm)
    print("source-mapping.json fixed")
