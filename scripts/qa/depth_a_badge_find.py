#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which upgraded pages lack the maturity badge in the public QA run."""
import json
from pathlib import Path

d = json.load(open(Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-depth-a/qa-artifacts-depth-a/public-browser-qa.json"), encoding="utf-8"))
for p in d["pages"]:
    if (p["label"].startswith("entity ") or p["label"].startswith("relation ")) and p["viewport"] == 1366:
        if not p["state"]["maturity_badge"]:
            print("NO BADGE:", p["label"], p["url"], "| analysis:", p["state"]["analysis_partition"], "| watch:", p["state"]["watch_partition"])
