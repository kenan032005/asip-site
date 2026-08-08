#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove empty timeline keys created by the earlier setdefault behavior."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d2/data/intelligence/africa")
fp = P / "relation_timelines.json"
tl = json.load(open(fp, encoding="utf-8"))
empty = [k for k, v in tl["timelines"].items() if not v]
for k in empty:
    del tl["timelines"][k]
print("removed empty timeline keys:", empty)
tl["generated_at"] = "2026-08-08"
fp.write_text(json.dumps(tl, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("timelines now:", len(tl["timelines"]))
