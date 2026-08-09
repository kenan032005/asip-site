#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH B locate: find where the 5 fact-error phrase groups live in current data."""
import json
from pathlib import Path

DATA = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-depth-b/data/intelligence/africa")

def load(name):
    return json.load(open(DATA / name, encoding="utf-8"))

entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
ep = load("entity_profiles.json")["profiles"]
rp = load("relation_profiles.json")["profiles"]
tl = load("relation_timelines.json")["timelines"]
sources = load("sources.json")["sources"]

PH = {
  "A_BARNAWI_BAKURA": ["Abu Musab al-Barnawi（巴库拉）", "巴库拉（Abu Musab al-Barnawi）", "Abu Musab al-Barnawi 2021年死亡", "al-Barnawi于2021年", "2021年确认死亡", "巴库拉（Bakura）就是al-Barnawi", "al-Barnawi（Bakura）"],
  "B_JAS_NEVER_ISIS": ["JAS 未加入伊斯兰国体系", "JAS从未加入伊斯兰国体系", "从未加入伊斯兰国", "未加入伊斯兰国体系"],
  "D_SECTOR_WRONG": ["Nigeria Sector 1", "尼日利亚 Sector 1", "Cameroon Sector 3", "喀麦隆 Sector 3", "Nigeria承担Sector 1", "Cameroon承担Sector 3", "尼日利亚承担第一战区", "喀麦隆承担第三战区"],
  "KOUFA_DEAD": ["已死亡", "被击毙"],
}

def scan(obj, path, hits):
    if isinstance(obj, dict):
        for k, v in obj.items():
            scan(v, path + "/" + k, hits)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            scan(v, path + f"[{i}]", hits)
    elif isinstance(obj, str):
        for grp, phrases in PH.items():
            for ph in phrases:
                if ph in obj:
                    hits.append((grp, ph, path, obj[max(0, obj.find(ph)-25):obj.find(ph)+45]))

# entity profiles
print("== entity_profiles ==")
hits = []
for eid, pr in ep.items():
    scan(pr, "ep:" + eid, hits)
for grp, ph, path, ctx in hits:
    print(f"  [{grp}] {ph!r} @ {path} ...{ctx}...")

# entity base records
print("\n== entities base ==")
hits = []
for e in entities:
    scan(e, "entity:" + e["entity_id"], hits)
for grp, ph, path, ctx in hits:
    print(f"  [{grp}] {ph!r} @ {path} ...{ctx}...")

# relation records
print("\n== relationships ==")
hits = []
for r in rels:
    scan(r, "rel:" + r["relationship_id"], hits)
for grp, ph, path, ctx in hits:
    print(f"  [{grp}] {ph!r} @ {path} ...{ctx}...")

# relation profiles
print("\n== relation_profiles ==")
hits = []
for rid, pr in rp.items():
    scan(pr, "rp:" + rid, hits)
for grp, ph, path, ctx in hits:
    print(f"  [{grp}] {ph!r} @ {path} ...{ctx}...")

# timelines
print("\n== relation_timelines ==")
hits = []
for rid, items in tl.items():
    scan(items, "tl:" + rid, hits)
for grp, ph, path, ctx in hits:
    print(f"  [{grp}] {ph!r} @ {path} ...{ctx}...")

# Cameroon relations source check
print("\n== cameroon rel source_refs ==")
for r in rels:
    if r["relationship_id"] in ("rel-cameroon-army-jas", "rel-cameroon-army-iswap"):
        print(f"  {r['relationship_id']}: {r.get('source_refs')}")

# ISWAP/JAS current profiles for JAS-ISIS relationship summary
print("\n== jas/iswap/mnjtf relation records (full text fields) ==")
for rid in ("rel-jas-islamic-state-hostile", "rel-jas-iswap-conflict", "rel-iswap-islamic-state-affiliation"):
    r = next((x for x in rels if x["relationship_id"] == rid), None)
    if r:
        for f in ("relation_summary", "formation_background", "current_status_detail", "why_it_matters", "uncertainties"):
            if r.get(f):
                print(f"  {rid}.{f} = {r[f][:120]!r}")
