#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-D1 schema probe: dump current data scale and field shapes."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d1/data/intelligence/africa")


def load(name):
    return json.load(open(P / name, encoding="utf-8"))


ents = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
srcs = load("sources.json")["sources"]
ev = load("evidence_records.json")["evidence"]
rp = load("relation_profiles.json")["profiles"]
rt = load("relation_timelines.json")["timelines"]
rtypes = load("relation_types.json")["relation_types"]
ep = load("entity_profiles.json")["profiles"]

print("scale:", "entities", len(ents), "rels", len(rels), "sources", len(srcs), "evidence", len(ev), "profiles", len(rp), "timelines", len(rt), "rtypes", len(rtypes), "entity_profiles", len(ep))
print("entity keys:", list(ents[0].keys()))
print("rel keys:", list(rels[0].keys()))
print("source keys:", list(srcs[0].keys()))
print("evidence keys:", list(ev[0].keys()))
print("profile sample:", json.dumps(rp[list(rp.keys())[0]], ensure_ascii=False)[:600])
print("timeline sample:", json.dumps(rt[list(rt.keys())[0]], ensure_ascii=False)[:600])
print("entity_profile sample:", json.dumps(ep[list(ep.keys())[0]], ensure_ascii=False)[:600])
print("rtype ids:", [t["relation_type"] for t in rtypes])
print("existing entity ids:", [e["entity_id"] for e in ents][:80])
