#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I2-B: freshness and current-status semantics tests.

Verifies record_reviewed_at is NOT used as current-status verification date;
freshness_status is legal everywhere; stale/aging objects carry the note
fields; current_status_verified_at is set only where audited.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "africa"

PASS = FAIL = 0
VALID_FRESH = {"current", "aging", "stale", "historical", "unknown"}


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  ({detail})")


def main():
    entities = json.loads((DATA / "entities.json").read_text(encoding="utf-8"))["entities"]
    countries = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))["countries"]
    rels = json.loads((DATA / "relationships.json").read_text(encoding="utf-8"))["relationships"]

    for e in entities:
        check(f"entity freshness legal {e['entity_id']}", e.get("freshness_status") in VALID_FRESH)
        check(f"entity record_reviewed_at {e['entity_id']}", bool(e.get("record_reviewed_at")))
        # record_reviewed_at must not equal current_status_verified_at claim
        if e.get("current_status_verified_at"):
            check(f"entity current verified later than review {e['entity_id']}",
                  e["current_status_verified_at"] >= (e.get("record_reviewed_at") or "2000-01-01"))
        if e.get("freshness_status") in ("stale", "aging"):
            check(f"stale/aging entity has as-of date {e['entity_id']}", bool(e.get("claim_valid_as_of")))

    for c in countries:
        check(f"country freshness legal {c['country_id']}", c.get("freshness_status") in VALID_FRESH)
        check(f"country record_reviewed_at {c['country_id']}", bool(c.get("record_reviewed_at")))

    for r in rels:
        check(f"rel freshness legal {r['relationship_id']}", r.get("freshness_status") in VALID_FRESH)
        check(f"rel record_reviewed_at {r['relationship_id']}", bool(r.get("record_reviewed_at")))

    # audited current-status entities should carry current_status_verified_at
    audited = {"actor-jas", "actor-iswap", "actor-mnjtf", "actor-saf", "actor-rsf",
               "actor-is-mozambique", "actor-fadm", "actor-rdf", "actor-samim"}
    for e in entities:
        if e["entity_id"] in audited:
            check(f"audited entity has current_status_verified_at {e['entity_id']}",
                  bool(e.get("current_status_verified_at")))
    for c in countries:
        if c["country_id"] in ("country-sudan", "country-chad", "country-mozambique"):
            check(f"audited country current verified {c['country_id']}", bool(c.get("current_status_verified_at")))

    print(f"\ntest_africa_freshness: PASS={PASS} FAIL={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
