#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check rel-jnim-aqim-constituent timeline + upgraded profile fields."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-depth-a/data/intelligence/africa")
tl = json.load(open(P / "relation_timelines.json", encoding="utf-8"))["timelines"]
rp = json.load(open(P / "relation_profiles.json", encoding="utf-8"))["profiles"]
print("aqim-constituent timeline:", len(tl.get("rel-jnim-aqim-constituent", [])))
for rid in ("rel-jnim-aqim-constituent", "rel-d1-fla-jnim-cooperation", "rel-d1-ansarul-jnim-constituent", "rel-d1-africa-corps-fama-coop", "rel-d1-africa-corps-wagner-history", "rel-jnim-is-conflict", "rel-jnim-alqaida-affiliate", "rel-koufa-jnim-senior", "rel-jnim-iyad-led", "rel-jnim-katiba-constituent", "rel-koufa-katiba-founder"):
    pr = rp.get(rid, {})
    print(rid, "| maturity:", pr.get("relation_maturity"), "| current_status:", bool(pr.get("current_status")), "| current_assessment:", bool(pr.get("current_assessment")), "| uncertainties:", bool(pr.get("uncertainties")), "| analysis:", bool(pr.get("asip_analysis")), "| watch:", bool(pr.get("watch_indicators")), "| tl:", len(tl.get(rid, [])))
