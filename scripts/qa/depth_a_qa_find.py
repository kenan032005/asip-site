#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find broken assets and pages without maturity badge in Depth A QA."""
import json
from pathlib import Path

d = json.load(open(Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-depth-a/qa-artifacts-depth-a/candidate-browser-qa.json"), encoding="utf-8"))
print("bad responses:", d["events"]["bad"])
print("failed:", d["events"]["failed"])
for p in d["pages"]:
    if p["label"].startswith(("entity ", "relation ")) and not p["state"]["maturity_badge"]:
        print("NO BADGE:", p["label"], p["url"], "| h1:", p["state"]["h1"])
