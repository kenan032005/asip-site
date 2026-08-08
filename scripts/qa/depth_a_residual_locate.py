#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Locate exact residual text fragments."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-depth-a/data/intelligence/africa")
rels = json.load(open(P / "relationships.json", encoding="utf-8"))["relationships"]
for r in rels:
    blob = json.dumps(r, ensure_ascii=False)
    if "当前状态存在多种公开说法" in blob:
        print("REL:", r["relationship_id"])
        for k, v in r.items():
            if isinstance(v, str) and "当前状态存在多种公开说法" in v:
                print("  field:", k, "| value:", v[:200])
ep = json.load(open(P / "entity_profiles.json", encoding="utf-8"))["profiles"]
pr = ep.get("person-amadou-koufa", {})
for k, v in pr.get("sections", {}).items():
    if isinstance(v, str) and "已死亡" in v:
        print("KOUFA section:", k)
        print("  value:", v[:300])
