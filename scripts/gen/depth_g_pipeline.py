#!/usr/bin/env python3
"""Depth G — deterministic closure pipeline runner.

Runs the closure stages in the one order that is actually correct:

  1. source relevance audit   (dedupe + un-jnim-2018 claim-relevance repair)
  2. evidence/source import   (new sources must exist BEFORE anything cites them)
  3. entity closure + repairs (entity sections, factual cleanups, JNIM-IS,
                               core relation overrides)
  4. relation closure         (dynamic maturity, summary-only, staleness)
  5. R3 field-set completion  (asip_analysis/watch_indicators/source wiring)
  6. maturity recalibration   (pre-downgrade scoring pass)
  7. truthful downgrade       (drop inflated badges; keep pack-locked as limitations)
  8. maturity recalibration   (full-library AFTER snapshot)

Running it repeatedly from the same baseline must produce the same result;
that idempotency is what the regeneration diff check depends on.
"""
from __future__ import annotations

import subprocess
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]

STAGES = [
    ("source relevance audit", ["scripts/qa/depth_g_source_audit.py", "--apply"]),
    ("evidence + source import", ["scripts/gen/depth_g_evidence_import.py", "--apply"]),
    ("entity closure + overrides", ["scripts/gen/depth_g_import.py", "--apply"]),
    ("relation closure", ["scripts/gen/depth_g_relation_closure.py", "--apply"]),
    ("R3 field-set completion", ["scripts/gen/depth_g_r3_fieldset.py", "--apply"]),
    ("maturity recalibration (pre-downgrade)", ["scripts/qa/depth_g_maturity.py", "after"]),
    ("truthful downgrade closure", ["scripts/gen/depth_g_truthful_downgrade.py", "--apply"]),
    ("catalog metrics recompute", ["scripts/gen/depth_g_metrics.py", "--apply"]),
    ("maturity recalibration (after)", ["scripts/qa/depth_g_maturity.py", "after"]),
]


def main() -> int:
    for label, cmd in STAGES:
        print(f"\n=== {label} ===", flush=True)
        proc = subprocess.run([sys.executable, *cmd], cwd=ROOT)
        if proc.returncode != 0:
            print(f"STAGE FAILED: {label} (exit {proc.returncode})")
            return proc.returncode
    print("\nAll stages completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
