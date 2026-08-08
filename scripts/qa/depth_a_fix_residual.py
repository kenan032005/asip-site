#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Second-pass fact cleanup: relation uncertainties field + Koufa roles section."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-depth-a/data/intelligence/africa")

# 1. relation records: clean all string fields for the koufa phrase
fp = P / "relationships.json"
rels = json.load(open(fp, encoding="utf-8"))
changed = []
for r in rels["relationships"]:
    if r["relationship_id"].startswith("rel-koufa-"):
        for k, v in r.items():
            if isinstance(v, str) and "当前状态存在多种公开说法" in v:
                r[k] = v.replace("库法当前状态存在多种公开说法，以最新权威来源为准。", "Koufa 2025—2026 年被多份权威来源确认为活跃领导层人物。")
                changed.append((r["relationship_id"], k))
print("relation changes:", changed)
rels["generated_at"] = "2026-08-08"
fp.write_text(json.dumps(rels, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

# 2. Koufa roles section
fp2 = P / "entity_profiles.json"
ep = json.load(open(fp2, encoding="utf-8"))
secs = ep["profiles"]["person-amadou-koufa"]["sections"]
if "已死亡" in str(secs.get("roles", "")):
    secs["roles"] = "曾任并现任：马西纳旅领导人、JNIM 核心指挥官（2017 至今）；2026 年多份权威来源确认其仍为活跃领导层人物，2018—2019 年的死亡通报已被证伪。"
    print("roles section corrected")
ep["generated_at"] = "2026-08-08"
fp2.write_text(json.dumps(ep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("done")
