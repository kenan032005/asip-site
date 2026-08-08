#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check region-endpoint relationships and active_in_region usage."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d1/data/intelligence/africa")
rels = json.load(open(P / "relationships.json", encoding="utf-8"))["relationships"]
regions = {r["region_id"] for r in json.load(open(P / "regions.json", encoding="utf-8"))["regions"]}
eids = {e["entity_id"] for e in json.load(open(P / "entities.json", encoding="utf-8"))["entities"]}
region_ends = []
for r in rels:
    for end in (r["source_entity_id"], r["target_entity_id"]):
        if end in regions and end not in eids:
            region_ends.append((r["relationship_id"], end))
print("rels with region endpoint:", region_ends)
print("active_in_region used by:", [r["relationship_id"] for r in rels if r["relationship_type"] == "active_in_region"])
