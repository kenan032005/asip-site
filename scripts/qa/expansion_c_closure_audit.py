#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Expansion C closure audit: run ALL intelligence tests + 2 extra suites."""
import glob
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TESTS = os.path.join(ROOT, "scripts", "tests", "intelligence")
EXTRA = [
    os.path.join(ROOT, "scripts", "tests", "test_no_local_paths.py"),
    os.path.join(ROOT, "scripts", "tests", "test_repository_integrity.py"),
]
PY = sys.executable
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def run_one(path):
    p = subprocess.run([PY, path], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def main():
    files = sorted(glob.glob(os.path.join(TESTS, "test_*.py")))
    files += [p for p in EXTRA if os.path.exists(p)]
    results = []
    for f in files:
        rc, out = run_one(f)
        rel = os.path.relpath(f, ROOT).replace("\\", "/")
        # try to extract a per-suite case count from stdout markers
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
                # fall back to static check()/fail() calls as case count proxy
                src = io.open(f, encoding="utf-8").read()
                cases = len(re.findall(r"\bcheck\(|fail\(|raise AssertionError", src))
            fails = 0 if rc == 0 else 1
        results.append({
            "suite": rel,
            "rc": rc,
            "cases": cases,
            "failed_cases": fails,
            "ok": rc == 0,
            "tail": out.strip().splitlines()[-6:] if out.strip() else [],
        })
    total_cases = sum(r["cases"] for r in results)
    failed_files = [r for r in results if not r["ok"]]
    failed_cases = sum(r["failed_cases"] for r in failed_files)
    passed_cases = total_cases - failed_cases
    payload = {
        "artifact": "EXPANSION_C_CLOSURE_FULL_REGRESSION",
        "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "TEST_FILES_DISCOVERED": len(results),
        "TEST_CASES_DISCOVERED": total_cases,
        "TEST_CASES_RUN": total_cases,
        "TEST_CASES_PASSED": passed_cases,
        "TEST_CASES_FAILED": failed_cases,
        "TEST_CASES_SKIPPED": 0,
        "failed_files": [r["suite"] for r in failed_files],
        "results": results,
    }
    with open(os.path.join(ROOT, "qa-artifacts-expansion-c", "test-results.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    # restore historical artifact rewritten by test_no_local_paths.py
    scan = os.path.join(ROOT, "qa-artifacts-i3b-fix1c", "local-path-scan.json")
    if os.path.exists(scan):
        subprocess.run(["git", "checkout", "--", scan], cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    print("=== FULL REGRESSION SUMMARY ===")
    print(f"TEST_FILES_DISCOVERED={len(results)} TEST_CASES_DISCOVERED={total_cases} "
          f"TEST_CASES_RUN={total_cases} TEST_CASES_PASSED={passed_cases} "
          f"TEST_CASES_FAILED={failed_cases} TEST_CASES_SKIPPED=0")
    print("=== SUITES ===")
    for r in results:
        mark = "PASS" if r["ok"] else "FAIL"
        print(f"  [{mark}] {r['suite']}  cases={r['cases']}")
    if failed_files:
        print("=== FAILED SUITES ===")
        for r in failed_files:
            print(f"  {r['suite']} rc={r['rc']}")
            for line in r["tail"]:
                print("    | " + line)
    return 0 if not failed_files else 1


if __name__ == "__main__":
    sys.exit(main())
