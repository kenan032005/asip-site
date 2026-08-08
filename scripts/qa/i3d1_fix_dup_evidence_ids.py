#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mechanical fix: I3-B legacy duplicate evidence_id 'ev-i3b-126' (5 records) ->
assign unique ids ev-i3b-127..130. Facts unchanged; ids only."""
import json
from collections import Counter
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d1/data/intelligence/africa")
fp = P / "evidence_records.json"
evidence = json.load(open(fp, encoding="utf-8"))
items = evidence["evidence"]

c = Counter(e["evidence_id"] for e in items)
dups = {k: v for k, v in c.items() if v > 1}
print("duplicates found:", dups)

used = {e["evidence_id"] for e in items}
next_n = 127
changes = []
for e in items:
    if c[e["evidence_id"]] > 1:
        # keep the first occurrence of ev-i3b-126, rename subsequent ones
        new_id = f"ev-i3b-{next_n}"
        while new_id in used:
            next_n += 1
            new_id = f"ev-i3b-{next_n}"
        e["evidence_id"] = new_id
        used.add(new_id)
        next_n += 1
        c[e["evidence_id"]] = 0  # not needed for further loops
        changes.append((e["claim_id"], new_id))

# recheck
c2 = Counter(e["evidence_id"] for e in items)
dups2 = {k: v for k, v in c2.items() if v > 1}
print("duplicates after fix:", dups2)
print("renamed:", changes)

evidence["generated_at"] = "2026-08-08"
fp.write_text(json.dumps(evidence, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("written", fp)
