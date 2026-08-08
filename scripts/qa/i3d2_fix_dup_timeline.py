#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix duplicate timeline items introduced by the pre-fix rerun of the D2 import."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d2/data/intelligence/africa")
fp = P / "relation_timelines.json"
tl = json.load(open(fp, encoding="utf-8"))
removed = 0
for rid, items in tl["timelines"].items():
    seen = set()
    clean = []
    for x in items:
        key = (x.get("date"), x.get("event_title"))
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        clean.append(x)
    tl["timelines"][rid] = clean
print("duplicate timeline items removed:", removed)
tl["generated_at"] = "2026-08-08"
fp.write_text(json.dumps(tl, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("rewritten")
