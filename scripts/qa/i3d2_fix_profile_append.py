#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix duplicated uncertainties append on rel-jnim-is-conflict profile."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d2/data/intelligence/africa")
fp = P / "relation_profiles.json"
rp = json.load(open(fp, encoding="utf-8"))
APPEND = "截至2026-04，竞争地理范围已超出2023年的马里—布基纳框架。"
prof = rp["profiles"].get("rel-jnim-is-conflict", {})
if prof:
    u = prof.get("uncertainties", "")
    print("uncertainties before:", repr(u))
    # dedupe repeated append blocks
    parts = [p for p in u.split("\n") if p.strip()]
    seen = set()
    clean = []
    for p in parts:
        if p in seen:
            continue
        seen.add(p)
        clean.append(p)
    prof["uncertainties"] = "\n".join(clean)
    print("uncertainties after:", repr(prof["uncertainties"]))
rp["generated_at"] = "2026-08-08"
fp.write_text(json.dumps(rp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
