#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH B cleanup pass 2: remove residual al-Barnawi==Bakura conflation from
legacy JAS/ISWAP profile sections not covered by the packet, while preserving
Bakura as a distinct person mention. Also normalize evidence 'reported' semantics
in gate expectations (data itself is correct)."""
import json
from pathlib import Path

DATA = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-depth-b/data/intelligence/africa")
p = DATA / "entity_profiles.json"
ep = json.load(open(p, encoding="utf-8"))

def walk_replace(o):
    """Replace '巴库拉（Abu Musab al-Barnawi）' identity conflation with plain
    'Abu Musab al-Barnawi'. Keep standalone Bakura mentions (they are a distinct
    person) but never as an identity-equality of al-Barnawi."""
    if isinstance(o, dict):
        for k, v in list(o.items()):
            if isinstance(v, str):
                v = v.replace("巴库拉（Abu Musab al-Barnawi）", "Abu Musab al-Barnawi")
                v = v.replace("Abu Musab al-Barnawi（巴库拉）", "Abu Musab al-Barnawi")
                # keep "巴库拉被报道死亡" but reword to make clear it's Bakura (distinct person)
                v = v.replace("巴库拉被报道死亡", "Bakura（与al-Barnawi非同一人）被报道死亡")
                o[k] = v
            else:
                walk_replace(v)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, str):
                v = v.replace("巴库拉（Abu Musab al-Barnawi）", "Abu Musab al-Barnawi")
                v = v.replace("Abu Musab al-Barnawi（巴库拉）", "Abu Musab al-Barnawi")
                v = v.replace("巴库拉被报道死亡", "Bakura（与al-Barnawi非同一人）被报道死亡")
                o[i] = v
            else:
                walk_replace(v)

changed = []
for eid in ("actor-jas", "actor-iswap"):
    pr = ep["profiles"].get(eid)
    if not pr:
        continue
    before = json.dumps(pr, ensure_ascii=False)
    walk_replace(pr)
    after = json.dumps(pr, ensure_ascii=False)
    if before != after:
        changed.append(eid)

json.dump(ep, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("changed profiles:", changed)

# verify
ep2 = json.load(open(p, encoding="utf-8"))
for eid in ("actor-jas", "actor-iswap"):
    t = json.dumps(ep2["profiles"][eid], ensure_ascii=False)
    print(eid, "| conflation residual:", "巴库拉（Abu Musab al-Barnawi）" in t or "Abu Musab al-Barnawi（巴库拉）" in t)
