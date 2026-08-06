#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-B: current-status tests — freshness semantics, stale <= 3, all current
statuses have valid as-of, no unsupported public claims."""
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
    entities = load("entities.json")["entities"]
    countries = load("countries.json")["countries"]
    rels = load("relationships.json")["relationships"]
    evidence = load("evidence_records.json")["evidence"]

    stale = []
    for e in entities + countries:
        if e.get("freshness_status") in ("stale", "aging"):
            stale.append(e.get("entity_id", e.get("country_id")))
    check("stale/aging current-status <= 3", len(stale) <= 3, str(stale))

    no_asof = []
    for e in entities + countries:
        if e.get("freshness_status") in ("current", "aging"):
            if not e.get("claim_valid_as_of"):
                no_asof.append(e.get("entity_id", e.get("country_id")))
    check("current/aging items all have claim_valid_as_of", not no_asof, str(no_asof[:5]))

    no_verified = []
    for e in entities + countries:
        if e.get("freshness_status") == "current" and not e.get("current_status_verified_at"):
            no_verified.append(e.get("entity_id", e.get("country_id")))
    check("current items have current_status_verified_at", not no_verified, str(no_verified[:5]))

    # no unsupported claims in public data
    unsup = [e for e in evidence if e.get("verification_status") == "unsupported"]
    check("no unsupported public claims", not unsup, str([e["evidence_id"] for e in unsup[:5]]))

    # high-impact current-status entities have manual evidence
    manual_entities = set()
    for e in evidence:
        if e.get("evidence_origin") == "manual_source_mapping":
            manual_entities.update(e.get("entity_ids", []))
    prio = ("actor-jnim", "actor-is-sahel", "actor-mali-army", "actor-burkina-army", "actor-vdp",
            "actor-cameroon-army", "actor-endf", "actor-fano", "actor-ola", "actor-tanzania-tpdf",
            "actor-tdf", "actor-ansar-eddine", "actor-al-mourabitoun", "actor-katiba-macina", "actor-aqim")
    missing = [eid for eid in prio if eid not in manual_entities]
    check("priority current-status entities have manual evidence", not missing, str(missing))

    # relation freshness sane
    bad_rel = [r["relationship_id"] for r in rels if r.get("freshness_status") == "unknown"]
    check("relations have defined freshness", not bad_rel, str(bad_rel[:5]))

    if FAIL:
        sys.exit(1)
    print(f"\nI3-B current status: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
