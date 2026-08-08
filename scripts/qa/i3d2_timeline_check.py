#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify final D2 timeline state."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d2/data/intelligence/africa")
tl = json.load(open(P / "relation_timelines.json", encoding="utf-8"))["timelines"]
print("timelines count:", len(tl))
items = tl.get("rel-jnim-is-conflict", [])
print("rel-jnim-is-conflict items:", len(items))
for x in items:
    print("  ", x["date"], "|", x["event_title"][:60])
print("d2 profile timeline counts:", {k: len(v) for k, v in tl.items() if k.startswith("rel-d2")})
