#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify dozo-related entities reference the reused source; fix mapping artifact."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d2/data/intelligence/africa")
QA = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d2/qa-artifacts-i3d2")
entities = json.load(open(P / "entities.json", encoding="utf-8"))["entities"]
sids = {s["source_id"] for s in json.load(open(P / "sources.json", encoding="utf-8"))["sources"]}
for e in entities:
    if e["entity_id"] in ("actor-dana-atem", "actor-dozos-of-macina", "actor-katiba-serma", "person-sidi-ongoiba", "person-amadou-nionson-diarra", "person-youssouf-toloba"):
        refs = e.get("source_refs", [])
        dangling = [r for r in refs if r not in sids]
        print(e["entity_id"], "refs:", refs, "| dangling:", dangling)

rels = json.load(open(P / "relationships.json", encoding="utf-8"))["relationships"]
for r in rels:
    if r["relationship_id"].startswith("rel-d2-"):
        dangling = [s for s in r.get("source_refs", []) if s not in sids]
        if dangling:
            print("dangling rel ref:", r["relationship_id"], dangling)

# fix source-mapping artifact: d2-acled-dozo maps to d1-acled-dozo-2026
mp = json.load(open(QA / "source-mapping.json", encoding="utf-8"))
entry = mp["mapping"].get("d2-acled-dozo-2025-10-08")
if entry and entry["actual_source_id"] == "d2-acled-dozo-2025-10-08":
    entry["actual_source_id"] = "d1-acled-dozo-2026"
    entry["matched_by"] = "url_exact"
    (QA / "source-mapping.json").write_text(json.dumps(mp, ensure_ascii=False, indent=1), encoding="utf-8")
    print("source-mapping corrected: d2-acled-dozo-2025-10-08 -> d1-acled-dozo-2026")
print("done")
