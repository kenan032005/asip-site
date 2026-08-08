#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diff timeline keys vs the committed baseline (d6860f9)."""
import json
import subprocess
from pathlib import Path

ROOT = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d2")
P = ROOT / "data/intelligence/africa"

current = json.load(open(P / "relation_timelines.json", encoding="utf-8"))["timelines"]
out = subprocess.run(["git", "show", "d6860f91c36bef00619a77437af1a5e4e455a9ac:data/intelligence/africa/relation_timelines.json"], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
base = json.loads(out.stdout)["timelines"]
new_keys = [k for k in current if k not in base]
missing = [k for k in base if k not in current]
print("new timeline keys:", len(new_keys), new_keys)
print("missing:", missing)

rp_current = json.load(open(P / "relation_profiles.json", encoding="utf-8"))["profiles"]
out2 = subprocess.run(["git", "show", "d6860f91c36bef00619a77437af1a5e4e455a9ac:data/intelligence/africa/relation_profiles.json"], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
rp_base = json.loads(out2.stdout)["profiles"]
new_rp = [k for k in rp_current if k not in rp_base]
print("new profile keys:", len(new_rp), new_rp)
