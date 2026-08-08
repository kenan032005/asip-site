#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Locate the 3 fact-error phrasings across current source data (profiles/timelines/rels/entities)."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-depth-a/data/intelligence/africa")
patterns = [
    "2019年被法军击毙", "2019年11月被击毙", "已死亡", "2019年后由继任指挥官", "当前状态存在多种公开说法",
    "2023年萨赫拉维死后", "2026年4月首次与JNIM公开交火",
    "伊亚德·阿格·加利的穆拉比通", "Iyad Ag Ghali曾任Al-Mourabitoun副手", "与Iyad Ag Ghali：领导关系",
]
for name in ("entity_profiles.json", "relation_profiles.json", "relation_timelines.json", "relationships.json", "entities.json", "evidence_records.json"):
    obj = json.load(open(P / name, encoding="utf-8"))
    text = json.dumps(obj, ensure_ascii=False)
    for pat in patterns:
        if pat in text:
            # find where
            hits = []
            if name == "entity_profiles.json":
                for eid, pr in obj["profiles"].items():
                    if pat in json.dumps(pr, ensure_ascii=False):
                        hits.append(eid)
            elif name == "relation_profiles.json":
                for rid, pr in obj["profiles"].items():
                    if pat in json.dumps(pr, ensure_ascii=False):
                        hits.append(rid)
            elif name == "relation_timelines.json":
                for rid, tl in obj["timelines"].items():
                    if pat in json.dumps(tl, ensure_ascii=False):
                        hits.append(rid)
            elif name == "relationships.json":
                for r in obj["relationships"]:
                    if pat in json.dumps(r, ensure_ascii=False):
                        hits.append(r["relationship_id"])
            elif name == "entities.json":
                for e in obj["entities"]:
                    if pat in json.dumps(e, ensure_ascii=False):
                        hits.append(e["entity_id"])
            elif name == "evidence_records.json":
                for e in obj["evidence"]:
                    if pat in json.dumps(e, ensure_ascii=False):
                        hits.append(e["evidence_id"])
            print(f"{pat} :: {name} :: {hits}")
