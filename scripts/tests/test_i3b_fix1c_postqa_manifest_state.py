#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立验证 I3-B Fix-1C PostQA 的 18 项最终 source-state 门禁。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts/qa/check_fix1c_postqa_manifest.py"
ARTIFACT = ROOT / "qa-artifacts-i3b-fix1c-postqa/manifest-final-state-check.json"
EXPECTED = {
    "FIX1B-CAM-001", "FIX1B-CAM-002", "FIX1B-MALI-001", "FIX1B-MALI-002",
    "FIX1B-BFA-001", "FIX1B-BFA-002", "FIX1B-NER-001", "FIX1B-NER-002",
    "FIX1B-ETH-001", "FIX1B-ETH-002", "FIX1B-ETH-003", "FIX1B-ETH-004",
    "FIX1B-TZA-001", "FIX1B-TZA-002", "FIX1B-TZA-003", "FIX1B-TCD-001",
    "FIX1B-LBY-001", "FIX1B-MOZ-001",
}

result = subprocess.run([sys.executable, str(CHECKER)], cwd=ROOT, capture_output=True, text=True)
if result.returncode != 0:
    print(result.stdout.strip())
    print(result.stderr.strip(), file=sys.stderr)
    raise SystemExit(result.returncode)

artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
rows = artifact.get("corrections", [])
ids = {row.get("correction_id") for row in rows}
checks = {
    "correction_count_is_18": artifact.get("correction_count") == 18,
    "all_manifest_ids_present": ids == EXPECTED and len(rows) == 18,
    "all_rows_pass": all(row.get("result") == "PASS" for row in rows),
    "all_rows_have_source_match": all(row.get("current_source_match") for row in rows),
    "all_rows_have_old_claim_absent": all(row.get("old_claim_absent") for row in rows),
    "all_rows_have_generator_consistency": all(row.get("generator_consistent") for row in rows),
    "blocking_failures_empty": artifact.get("blocking_failures") == [],
    "gate_pass": artifact.get("gate") == "PASS",
}
failed = [name for name, passed in checks.items() if not passed]
print(json.dumps({"checks": checks, "failed": failed, "gate": "PASS" if not failed else "FAIL"}, ensure_ascii=False))
raise SystemExit(0 if not failed else 1)
