#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find pages failing state checks in the public QA report."""
import json
from pathlib import Path

d = json.load(open(Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3d2/qa-artifacts-i3d2/public-browser-qa.json"), encoding="utf-8"))
found = False
for p in d["pages"]:
    st = p["state"]
    bad = st["ready_state"] != "complete" or not st["header_loaded"] or not st["error_hidden"] or st["overflow"] or any(p["events"].values())
    if bad:
        found = True
        print(p["viewport"], p["label"], p["url"])
        print("  ready:", st["ready_state"], "| header:", st["header_loaded"], "| error_hidden:", st["error_hidden"], "| overflow:", st["overflow"], "| events:", p["events"], "| h1:", st["h1"])
if not found:
    print("no failing pages; all state checks pass")
