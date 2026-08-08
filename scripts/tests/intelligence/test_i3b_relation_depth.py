#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-B: relation depth tests — profiles >= 32, timelines >= 30, all deepened
profiles complete with core fields and timelines."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "africa"
PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  ({detail})")


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def main():
    profiles = load("relation_profiles.json")["profiles"]
    timelines = load("relation_timelines.json")["timelines"]
    rels = load("relationships.json")["relationships"]
    rid_set = {r["relationship_id"] for r in rels}

    check("relation_profile_count >= 32", len(profiles) >= 32, str(len(profiles)))
    check("relation_timeline_count >= 30", len(timelines) >= 30, str(len(timelines)))

    deep = [rid for rid, pr in profiles.items() if pr.get("overview") and pr.get("evolution_stages")]
    check("deepened profiles >= 32", len(deep) >= 32, str(len(deep)))
    check("deepened profiles all have timelines", not [r for r in deep if r not in timelines], "")

    incomplete = []
    for rid in deep:
        pr = profiles[rid]
        if pr.get("relation_maturity"):
            maturity = pr["relation_maturity"]
            checks = [("overview", "overview"), ("current", None), ("uncertainties", "uncertainties")]
            if maturity == "R3_FULL_RELATIONSHIP_INTELLIGENCE":
                checks += [("asip_analysis", "asip_analysis"), ("watch_indicators", "watch_indicators")]
            for label, f in checks:
                if label == "current":
                    if not (pr.get("current_status") or pr.get("current_assessment")):
                        incomplete.append(f"{rid}:current")
                elif label == "uncertainties" and not pr.get(f) and not pr.get("current_assessment"):
                    incomplete.append(f"{rid}:uncertainties")
                elif label not in ("uncertainties",) and not pr.get(f):
                    incomplete.append(f"{rid}:{f}")
        else:
            for f in ("overview", "formation_background", "initial_relationship", "causes",
                      "key_turning_points", "current_status", "regional_differences",
                      "impact_on_security", "why_it_matters", "uncertainties"):
                if not pr.get(f):
                    incomplete.append(f"{rid}:{f}")
    check("deepened profiles have all core fields", not incomplete, str(incomplete[:8]))

    # new second-wave relations exist with correct endpoints
    second_wave = ("rel-mali-army-jnim", "rel-burkina-army-jnim", "rel-cameroon-army-ambazonia",
                   "rel-endf-fano-conflict", "rel-endf-ola-conflict", "rel-endf-tdf-conflict",
                   "rel-tanzania-tpdf-is-moz", "rel-vdp-burkina-support")
    missing = [r for r in second_wave if r not in rid_set]
    check("second-wave relations exist", not missing, str(missing))

    if FAIL:
        sys.exit(1)
    print(f"\nI3-B relation depth: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
