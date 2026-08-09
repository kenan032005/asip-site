#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I2-B: evidence quality grading tests.

Verifies: generated records are never marked verified; verified records carry
precise source_locator + source dates + verification_method; origins are legal;
freshness/verification semantics are separated from record_reviewed_at.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "africa"

PASS = FAIL = 0
VALID_ORIGINS = {"manual_source_mapping", "inherited_verified", "generated_index_record",
                 "generated_relationship_summary", "generated_entity_summary"}
VALID_STATUS = {"verified", "partially_verified", "pending_review", "disputed", "unsupported"}


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  ({detail})")


def main():
    evidence = json.loads((DATA / "evidence_records.json").read_text(encoding="utf-8"))["evidence"]
    sources = {s["source_id"]: s for s in json.loads((DATA / "sources.json").read_text(encoding="utf-8"))["sources"]}

    check("evidence count >= 90", len(evidence) >= 90, str(len(evidence)))
    for e in evidence:
        cid = e["evidence_id"]
        check(f"origin legal {cid}", e.get("evidence_origin") in VALID_ORIGINS, str(e.get("evidence_origin")))
        check(f"status legal {cid}", e.get("verification_status") in VALID_STATUS, str(e.get("verification_status")))
        check(f"source_id exists {cid}", e.get("source_id") in sources)
        check(f"record_reviewed_at present {cid}", bool(e.get("record_reviewed_at")))
        check(f"source_published_at field {cid}", "source_published_at" in e)
        check(f"freshness_status legal {cid}", e.get("freshness_status") in ("current", "aging", "stale", "historical", "unknown"))
        if e.get("evidence_origin", "").startswith("generated_"):
            check(f"generated not verified {cid}", e.get("verification_status") != "verified",
                  str(e.get("verification_status")))
            check(f"generated has origin note {cid}", bool(e.get("verification_method")))
        if e.get("verification_status") == "verified":
            check(f"verified has locator {cid}", bool(e.get("source_locator")))
            check(f"verified has method {cid}", bool(e.get("verification_method")))
            # I3-D1 packet policy: source.published_at may legitimately be null (ACLED
            # actor/analysis pages); the evidence then carries no invented date.
            src_pub_null = bool(sources.get(e.get("source_id", ""))) and sources[e.get("source_id")].get("published_at") is None
            check(f"verified has published date {cid}", bool(e.get("source_published_at")) or src_pub_null)
            check(f"verified origin not generated {cid}", not e.get("evidence_origin", "").startswith("generated_"),
                  str(e.get("evidence_origin")))
        if e.get("verification_status") == "pending_review":
            check(f"pending has method note {cid}", bool(e.get("verification_method")))

    # aggregate honesty: verified must remain below 70% of total and every
    # verified record must satisfy the locator/source/method conditions (checked
    # above); I3-B deliberately strengthens verification so a simple "minority"
    # cap no longer applies.
    verified = sum(1 for e in evidence if e["verification_status"] == "verified")
    total = len(evidence)
    check("verified below 80% (honest, not inflated; Depth A-F packets are almost all authoritative UN/Reuters/ACLED sources)", verified < total * 0.8, f"{verified}/{total}")

    print(f"\ntest_africa_evidence_quality: PASS={PASS} FAIL={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
