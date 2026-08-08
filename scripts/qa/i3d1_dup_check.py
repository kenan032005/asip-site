#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find duplicate evidence ids and print prep source_refs."""
import json
from collections import Counter
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d1/data/intelligence/africa")
evidence = json.load(open(P / "evidence_records.json", encoding="utf-8"))["evidence"]
rels = {r["relationship_id"]: r for r in json.load(open(P / "relationships.json", encoding="utf-8"))["relationships"]}

c = Counter(e["evidence_id"] for e in evidence)
print("duplicates:", {k: v for k, v in c.items() if v > 1})
for k, v in c.items():
    if v > 1:
        for e in evidence:
            if e["evidence_id"] == k:
                print("  ", e["claim_id"], e["source_id"], e["claim_text_zh"][:40])

for rid in ("rel-endf-tdf-conflict", "rel-burkina-army-jnim", "rel-endf-ola-conflict"):
    r = rels[rid]
    print(rid, "source_refs:", r["source_refs"])
    print("  summary tail:", r["relation_summary"][-60:])
    print("  status_detail:", r.get("current_status_detail", "")[-60:])
