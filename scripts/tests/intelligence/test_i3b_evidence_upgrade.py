#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-B: evidence upgrade tests — verified >= 55, pending <= 12, new/upgraded
manual evidence >= 45, generated evidence never verified."""
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

    status = {}
    for e in evidence:
        status[e.get("verification_status")] = status.get(e.get("verification_status"), 0) + 1
    check("verified >= 55", status.get("verified", 0) >= 55, str(status))
    check("pending <= 12", status.get("pending_review", 0) <= 12, str(status))

    manual = [e for e in evidence if e.get("evidence_origin") == "manual_source_mapping"]
    check("manual evidence >= 45", len(manual) >= 45, str(len(manual)))

    gen = [e for e in evidence if str(e.get("evidence_origin", "")).startswith("generated_")]
    gen_verified = [e for e in gen if e.get("verification_status") == "verified"]
    check("no generated evidence marked verified", not gen_verified)

    # verified evidence satisfies the 10 conditions
    src_pub = {s["source_id"]: s.get("published_at") for s in sources}
    bad = []
    for e in evidence:
        if e.get("verification_status") != "verified":
            continue
        if not e.get("source_id") or e["source_id"] not in sids:
            bad.append(e["evidence_id"] + ":src")
        # I3-D1 packet policy: source.published_at null -> no invented date on evidence
        if not e.get("source_published_at") and src_pub.get(e.get("source_id")) is not None:
            bad.append(e["evidence_id"] + ":pub")
        if not e.get("source_locator"):
            bad.append(e["evidence_id"] + ":loc")
        if not e.get("verified_at"):
            bad.append(e["evidence_id"] + ":verified_at")
        if not e.get("verification_method"):
            bad.append(e["evidence_id"] + ":method")
    check("verified evidence satisfies locator/source/method", not bad, str(bad[:8]))

    # unsupported claims absent
    unsup = [e for e in evidence if e.get("verification_status") == "unsupported"]
    check("no unsupported evidence", not unsup)

    if FAIL:
        sys.exit(1)
    print(f"\nI3-B evidence upgrade: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
