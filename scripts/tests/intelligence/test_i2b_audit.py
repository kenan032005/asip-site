#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I2-B: three-region audit records tests.

Verifies >=36 audit records across Lake Chad / Sudan / Mozambique (>=12 each),
every record has required fields, sources are real (in sources.json), and
unsupported/conflicting claims are flagged rather than presented as fact.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "africa"

PASS = FAIL = 0
REQUIRED = ["audit_id", "region_id", "claim_id", "current_claim_text", "entity_ids",
            "relation_ids", "source_ids", "source_locator", "source_published_at",
            "claim_valid_as_of", "support_result", "issue_type", "correction_action",
            "final_claim_text", "verification_status", "reviewed_at", "reviewer_notes"]
VALID_SUPPORT = {"supported", "partially_supported", "unsupported", "conflicting_sources", "stale_source"}


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  ({detail})")


def main():
    audit = json.loads((DATA / "audit_records.json").read_text(encoding="utf-8"))
    records = audit["records"]
    sources = {s["source_id"] for s in json.loads((DATA / "sources.json").read_text(encoding="utf-8"))["sources"]}

    check("audit schema", audit.get("schema_version") == "asip-audit-records-v1")
    check("audit count >= 36", len(records) >= 36, str(len(records)))
    check("audit count >= 40 (real coverage)", len(records) >= 40, str(len(records)))

    from collections import Counter
    by_region = Counter(r["region_id"] for r in records)
    check("Lake Chad >= 12", by_region.get("region-lake-chad-basin", 0) >= 12)
    check("Sudan >= 12", by_region.get("region-sudan-red-sea-horn", 0) >= 12)
    check("Mozambique >= 12", by_region.get("region-southeast-africa-mozambique", 0) >= 12)

    ids = set()
    for r in records:
        check(f"unique audit_id {r['audit_id']}", r["audit_id"] not in ids)
        ids.add(r["audit_id"])
        for f in REQUIRED:
            check(f"{r['audit_id']}.{f}", f in r, "missing " + f)
        check(f"{r['audit_id']} support_result legal", r["support_result"] in VALID_SUPPORT,
              str(r["support_result"]))
        check(f"{r['audit_id']} sources exist", all(s in sources for s in r["source_ids"]),
              str(r["source_ids"]))
        check(f"{r['audit_id']} source_published_at", bool(r.get("source_published_at")))
        check(f"{r['audit_id']} claim_valid_as_of", bool(r.get("claim_valid_as_of")))
        check(f"{r['audit_id']} final text", bool(r.get("final_claim_text")))
        check(f"{r['audit_id']} reviewed_at", bool(r.get("reviewed_at")))
        check(f"{r['audit_id']} reviewer_notes", bool(r.get("reviewer_notes")))
        if r.get("support_result") == "unsupported":
            check(f"{r['audit_id']} unsupported → correction", bool(r.get("correction_action")))

    print(f"\ntest_i2b_audit: PASS={PASS} FAIL={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
