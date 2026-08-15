#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pack B Fix-1 full regression runner.

Mirrors the accepted Pack A / Phase 2 official runner
(post_consolidation_audit_p2_regression.py) exactly:
  - discovers ALL scripts/tests/intelligence/test_*.py (sorted),
  - appends the two EXTRA repository-integrity suites
    (test_no_local_paths.py, test_repository_integrity.py),
  - runs each suite with the same Python interpreter via subprocess,
  - classifies a suite as passed iff its process exit code == 0,
  - parses case counts from PASS=/FAIL= (or checks=) markers in stdout/stderr.

This runner accepts an optional --root so the SAME command can be run against
the Fix-1 candidate and the accepted Phase 2 baseline (cca534d) for a like-for-
like A/B comparison.
"""
import glob
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone


def run_regression(root):
    TESTS = os.path.join(root, "scripts", "tests", "intelligence")
    EXTRA = [
        os.path.join(root, "scripts", "tests", "test_no_local_paths.py"),
        os.path.join(root, "scripts", "tests", "test_repository_integrity.py"),
    ]
    PY = sys.executable
    results = []
    files = sorted(glob.glob(os.path.join(TESTS, "test_*.py")))
    files += [p for p in EXTRA if os.path.exists(p)]
    for f in files:
        p = subprocess.run([PY, f], cwd=root, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        rc = p.returncode
        out = (p.stdout or "") + (p.stderr or "")
        rel = os.path.relpath(f, root).replace("\\", "/")
        m = re.search(r"PASS=(\d+).*?FAIL=(\d+)", out)
        if m:
            cases, fails = int(m.group(1)), int(m.group(2))
        else:
            m2 = re.search(r"checks\s*=\s*(\d+)", out)
            m3 = re.search(r"checked\s*=\s*(\d+)", out)
            if m2:
                cases = int(m2.group(1))
            elif m3:
                cases = int(m3.group(1))
            else:
                try:
                    src = io.open(f, encoding="utf-8").read()
                except Exception:
                    src = ""
                cases = len(re.findall(r"\bcheck\(|fail\(|raise AssertionError", src))
            fails = 0 if rc == 0 else 1
        results.append({
            "suite": rel, "rc": rc, "cases": cases, "failed_cases": fails,
            "ok": rc == 0,
            "tail": out.strip().splitlines()[-6:] if out.strip() else [],
        })
    total_cases = sum(r["cases"] for r in results)
    failed_files = [r for r in results if not r["ok"]]
    failed_cases = sum(r["failed_cases"] for r in failed_files)
    passed_cases = total_cases - failed_cases
    payload = {
        "artifact": "PACK_B_FIX1_FULL_REGRESSION",
        "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "root": root,
        "TEST_FILES_DISCOVERED": len(results),
        "TEST_CASES_DISCOVERED": total_cases,
        "TEST_CASES_RUN": total_cases,
        "TEST_CASES_PASSED": passed_cases,
        "TEST_CASES_FAILED": failed_cases,
        "TEST_CASES_SKIPPED": 0,
        "FULL_REGRESSION": "PASS" if not failed_files else "FAIL",
        "failed_files": [r["suite"] for r in failed_files],
        "suites": [r["suite"] for r in results],
        "results": results,
    }
    return payload


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    payload = run_regression(root)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    print("=== FULL REGRESSION SUMMARY ===")
    print(f"TEST_FILES_DISCOVERED={payload['TEST_FILES_DISCOVERED']} "
          f"TEST_CASES_DISCOVERED={payload['TEST_CASES_DISCOVERED']} "
          f"TEST_CASES_RUN={payload['TEST_CASES_RUN']} "
          f"TEST_CASES_PASSED={payload['TEST_CASES_PASSED']} "
          f"TEST_CASES_FAILED={payload['TEST_CASES_FAILED']} "
          f"TEST_CASES_SKIPPED={payload['TEST_CASES_SKIPPED']}")
    print(f"FULL_REGRESSION={payload['FULL_REGRESSION']}")
    for r in payload["results"]:
        mark = "PASS" if r["ok"] else "FAIL"
        print(f"  [{mark}] {r['suite']}  cases={r['cases']} rc={r['rc']}")
    for r in payload["results"]:
        if not r["ok"]:
            print("--- FAILED:", r["suite"], "---")
            for line in r["tail"]:
                print("  | " + line)
    return 0 if not payload["failed_files"] else 1


if __name__ == "__main__":
    sys.exit(main())
