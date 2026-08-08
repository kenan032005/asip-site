#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check actual source records for d1/d2 dozo sources."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d2/data/intelligence/africa")
sources = json.load(open(P / "sources.json", encoding="utf-8"))["sources"]
for s in sources:
    if "dozo" in s["source_id"] or "acled" in s["source_id"]:
        print(s["source_id"], "|", s.get("url"), "|", s.get("published_at"))
