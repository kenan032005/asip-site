#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the small ASIP intelligence demo as an isolated static subtree."""
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_DATA = ROOT / "data" / "intelligence" / "demo"
DEMO_SOURCE = ROOT / "intelligence" / "demo"

def read_json(name):
    with (DEMO_DATA / name).open(encoding="utf-8") as f:
        return json.load(f)

def build_intelligence_demo(dist_root):
    dist_root = Path(dist_root)
    target = dist_root / "intelligence" / "demo"
    target.mkdir(parents=True, exist_ok=True)
    (target / "network").mkdir(parents=True, exist_ok=True)
    (target / "relation").mkdir(parents=True, exist_ok=True)
    index_source = DEMO_SOURCE / "index.html"
    shutil.copy2(index_source, target / "index.html")
    shutil.copy2(DEMO_SOURCE / "network" / "index.html", target / "network" / "index.html")
    entities = read_json("entities.json")["entities"]
    entity_template = (DEMO_SOURCE / "entity" / "_template.html").read_text(encoding="utf-8")
    for entity in entities:
        entity_dir = target / "entity" / entity["slug"]
        entity_dir.mkdir(parents=True, exist_ok=True)
        (entity_dir / "index.html").write_text(entity_template.replace("__ENTITY_SLUG__", entity["slug"]), encoding="utf-8")
    relationships = read_json("relationships.json")["relationships"]
    relation_template = (DEMO_SOURCE / "relation" / "_template.html").read_text(encoding="utf-8")
    relation_slugs = set()
    for rel in relationships:
        slug = rel.get("slug") or rel["relationship_id"]
        relation_slugs.add(slug)
        relation_dir = target / "relation" / slug
        relation_dir.mkdir(parents=True, exist_ok=True)
        (relation_dir / "index.html").write_text(relation_template.replace("__RELATION_SLUG__", slug), encoding="utf-8")
    data_target = target / "data"
    data_target.mkdir(parents=True, exist_ok=True)
    for data_file in sorted(DEMO_DATA.glob("*.json")):
        shutil.copy2(data_file, data_target / data_file.name)
    print(f"  intelligence demo: {len(entities)} entity routes + {len(relation_slugs)} relation routes + network + data")

if __name__ == "__main__":
    build_intelligence_demo(ROOT / "dist")
