#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Get actual slugs for the three Koufa/Iyad relations."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-depth-a/data/intelligence/africa")
rels = json.load(open(P / "relationships.json", encoding="utf-8"))["relationships"]
for r in rels:
    if r["relationship_id"] in ("rel-jnim-iyad-led", "rel-koufa-jnim-senior", "rel-koufa-katiba-founder"):
        print(r["relationship_id"], "-> slug:", r.get("slug"))
