#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find IS Sahel 2023 Sahrawi phrasing."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-depth-a/data/intelligence/africa")
ep = json.load(open(P / "entity_profiles.json", encoding="utf-8"))["profiles"]
secs = ep["actor-is-sahel"]["sections"]
for k, v in secs.items():
    if isinstance(v, str) and "萨赫拉维" in v:
        print("KEY:", k)
        print("  ", v[:200])
