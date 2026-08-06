#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-A: source coverage tests — deep countries and priority entities have
manual evidence with locators; verified evidence satisfies the 10 conditions;
new manual evidence count >= 30; generated evidence reviewed."""
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
    evidence = load("evidence_records.json")["evidence"]
    sources = load("sources.json")["sources"]
    sids = {s["source_id"] for s in sources}
    entities = load("entities.json")["entities"]
    countries = load("countries.json")["countries"]
    eids = {e["entity_id"] for e in entities}
    cids = {c["country_id"] for c in countries}

    manual = [e for e in evidence if e.get("evidence_origin") == "manual_source_mapping"]
    check(">=30 new/upgraded manual evidence", len(manual) >= 30, str(len(manual)))

    verified = [e for e in evidence if e.get("verification_status") == "verified"]
    bad_verified = []
    for e in verified:
        if not e.get("source_id") or e["source_id"] not in sids:
            bad_verified.append(e["evidence_id"] + ":src")
        if not e.get("source_published_at"):
            bad_verified.append(e["evidence_id"] + ":pub")
        if not e.get("source_locator"):
            bad_verified.append(e["evidence_id"] + ":loc")
        if not e.get("verified_at"):
            bad_verified.append(e["evidence_id"] + ":verified_at")
        if not e.get("verification_method"):
            bad_verified.append(e["evidence_id"] + ":method")
        if not e.get("claim_valid_as_of") and not e.get("as_of_date"):
            bad_verified.append(e["evidence_id"] + ":asof")
    check("verified evidence satisfies locator/source/method requirements", not bad_verified, str(bad_verified[:8]))

    generated = [e for e in evidence if str(e.get("evidence_origin", "")).startswith("generated_")]
    gen_verified = [e for e in generated if e.get("verification_status") == "verified"]
    check("no generated evidence defaulted to verified", not gen_verified)
    reviewed = [e for e in generated if e.get("record_reviewed_at") or e.get("review_note")]
    check(">=25 generated evidence explicitly reviewed (upgrade or keep pending)",
          len(reviewed) >= 25, str(len(reviewed)))
    upgraded = [e for e in generated if e.get("verification_status") == "partially_verified" and e.get("verification_method") in ("manual_review_2026_i3a", "manual_review_2026_i3b")]
    check("generated upgrades carry manual-review method (i3a/i3b)", len(upgraded) >= 25, str(len(upgraded)))

    # deep countries & priority entities have at least one manual evidence
    deep_cids = ("country-nigeria", "country-libya", "country-south-sudan", "country-niger",
                 "country-benin", "country-chad", "country-sudan", "country-mozambique")
    prio_entities = ("actor-jas", "actor-iswap", "actor-mnjtf", "actor-nigeria-army", "actor-lna",
                     "actor-gnu-forces", "actor-isis-libya", "actor-sspdf", "actor-splm-io", "actor-nas",
                     "person-salva-kiir", "person-riek-machar", "actor-benin-forces")
    for cid in deep_cids:
        has = any(cid in e.get("country_ids", []) or cid in e.get("entity_ids", []) for e in manual)
        check(f"deep country {cid} has manual evidence", has)
    for eid in prio_entities:
        has = any(eid in e.get("entity_ids", []) for e in manual)
        check(f"priority entity {eid} has manual evidence", has)

    # evidence entity refs valid (entity_ids may include country ids per graph schema)
    valid_refs = eids | cids
    bad_ref = [e["evidence_id"] for e in evidence if any(x not in valid_refs for x in e.get("entity_ids", []))]
    check("evidence entity references valid", not bad_ref, str(bad_ref[:5]))

    if FAIL:
        sys.exit(1)
    print(f"\nI3-A source coverage: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
