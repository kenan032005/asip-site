#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage8C Package2 Final Evidence Recovery Preparation.

Offline-only evidence audit. This script never calls a provider and never
refreshes canonical data. It reconstructs only what Run#4 artifacts prove.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN_ID = "33066148566"
ART = ROOT.parent / ".workbuddy" / "tmp" / "recovery4_art"
OUT = ROOT / "data" / "runtime" / "stage8c_trial2_recovery"
CUTOFF = "2026-08-01T18:02:40.000Z"


def load(name):
    return json.loads((ART / name).read_text(encoding="utf-8"))


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def main():
    inp = load("input_summary.json")
    safety = load("safety_layer_trial.json")
    recs = safety["enrichment_records"]
    social = [r for r in recs if r.get("task_type") == "stage4_event_enrichment"]
    disease = [r for r in recs if r.get("task_type") == "disease_summary"]
    accepted = [r for r in recs if r.get("status") == "ok" and
                (r.get("safety") or {}).get("gate") == "PASS"]
    held = [r for r in recs if r.get("status") != "ok"]

    # The artifact contains corrected enrichment outputs but not the exact
    # report input objects after report-section filtering. Do not guess them.
    snapshot = {
        "snapshot_type": "stage8c_report_input_evidence_audit",
        "report_input_snapshot_source_run": RUN_ID,
        "reconstructable": False,
        "reconstructability_reason": (
            "Run#4 artifacts lack the exact three report_input objects and their "
            "post-filter serialization; only enrichment corrected_output and "
            "section counts are preserved."),
        "input_cutoff": inp.get("cutoff"),
        "expected_input_record_count": inp.get("social_eligible_total", 0) +
                                       inp.get("disease_eligible_total", 0),
        "social_input": len(social),
        "disease_input": len(disease),
        "social_schema_accepted": sum(1 for r in social if r.get("status") == "ok"),
        "disease_schema_accepted": sum(1 for r in disease if r.get("status") == "ok"),
        "report_input_final_unique": None,
        "accepted_record_ids": [r.get("event_id") or r.get("disease_event_id")
                                 for r in accepted],
        "held_records": [
            {"record_id": r.get("event_id") or r.get("disease_event_id"),
             "country": r.get("country_code"), "status": r.get("status"),
             "reason": r.get("error") or (r.get("schema_errors") or [None])[0]}
            for r in held
        ],
        "safety_corrected_outputs": [
            {"record_id": r.get("event_id") or r.get("disease_event_id"),
             "task_type": r.get("task_type"),
             "country": r.get("country_code"),
             "corrected_output": (r.get("safety") or {}).get("corrected_output")}
            for r in accepted
        ],
        "source_refs_available": False,
        "report_input_sha256": None,
    }
    data = json.dumps(snapshot, ensure_ascii=False, indent=1).encode("utf-8")
    snapshot["snapshot_sha256"] = sha256_bytes(data)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report_input_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("REPORT_INPUT_SNAPSHOT_SOURCE_RUN =", RUN_ID)
    print("SNAPSHOT_INPUT_CUTOFF =", inp.get("cutoff"))
    print("REPORT_INPUT_SNAPSHOT_RECONSTRUCTABLE =", snapshot["reconstructable"])
    print("SOCIAL_FINAL_COUNT =", len([r for r in accepted if r.get("task_type") == "stage4_event_enrichment"]))
    print("DISEASE_FINAL_COUNT =", len([r for r in accepted if r.get("task_type") == "disease_summary"]))
    print("HELD_RECORD_COUNT =", len(held))
    print("SNAPSHOT_SHA256 =", snapshot["snapshot_sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
