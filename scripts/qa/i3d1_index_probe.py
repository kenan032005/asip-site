#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-D1: inspect graph_index / alias_index shape and whether generators write them."""
import json
import re
from pathlib import Path

ROOT = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d1")
P = ROOT / "data/intelligence/africa"

g = json.load(open(P / "graph_index.json", encoding="utf-8"))
a = json.load(open(P / "alias_index.json", encoding="utf-8"))
print("graph_index:", type(g).__name__, len(g) if isinstance(g, (list, dict)) else "")
if isinstance(g, dict):
    k = list(g.keys())[0]
    print("  key sample:", k, "->", json.dumps(g[k], ensure_ascii=False)[:400])
elif isinstance(g, list):
    print("  item0:", json.dumps(g[0], ensure_ascii=False)[:400])
print("alias_index:", type(a).__name__, len(a) if isinstance(a, (list, dict)) else "")
if isinstance(a, dict):
    print("  keys sample:", list(a.keys())[:6])
    for k in list(a.keys())[:1]:
        print("  ", k, "->", json.dumps(a[k], ensure_ascii=False)[:300])

# which generators touch these files
print("\ngenerators writing graph_index/alias_index/catalog_metrics:")
for script in sorted((ROOT / "scripts").rglob("*.py")):
    try:
        text = script.read_text(encoding="utf-8")
    except Exception:
        continue
    hits = [name for name in ("graph_index", "alias_index", "catalog_metrics") if name in text]
    if hits:
        print(" ", script.relative_to(ROOT), hits)
