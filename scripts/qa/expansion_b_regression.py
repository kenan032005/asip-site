#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-B full regression runner.

Runs every intelligence test (including the new test_expansion_b_gate.py) plus
the local-path guard and repository integrity checks, writes
qa-artifacts-expansion-b/test-results.json, and restores the historical
qa-artifacts-i3b-fix1c/local-path-scan.json artifact that test_no_local_paths.py
rewrites on every run.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TESTS = os.path.join(ROOT, "scripts", "tests", "intelligence")
EXTRA = [
    os.path.join(ROOT, "scripts", "tests", "test_no_local_paths.py"),
    os.path.join(ROOT, "scripts", "tests", "test_repository_integrity.py"),
]
OUT = os.path.join(ROOT, "qa-artifacts-expansion-b", "test-results.json")
PY = sys.executable


def bj_now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


FAIL_COUNT_RE = re.compile(r"FAIL\s*=\s*(\d+)")
FAIL_MARK_RE = re.compile(r"\[FAIL\]")


def run_one(path):
    p = subprocess.run([PY, path], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    counts = [int(x) for x in FAIL_COUNT_RE.findall(out)]
    fails = max(counts) if counts else len(FAIL_MARK_RE.findall(out))
    return {
        "test": os.path.relpath(path, ROOT).replace("\\", "/"),
        "rc": p.returncode,
        "fail": fails,
        "ok": p.returncode == 0 and fails == 0,
        "tail": out.strip().splitlines()[-4:] if out.strip() else [],
    }


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "EXPANSION_B_FULL_REGRESSION"
    files = sorted(os.path.join(TESTS, f) for f in os.listdir(TESTS)
                   if f.startswith("test_") and f.endswith(".py"))
    files += [p for p in EXTRA if os.path.exists(p)]
    results = [run_one(f) for f in files]
    failed = [r for r in results if not r["ok"]]
    payload = {
        "artifact": label,
        "generated_at": bj_now(),
        "python": sys.version.split()[0],
        "tests_run": len(results),
        "passed": len(results) - len(failed),
        "fail_total": len(failed),
        "failed": [r["test"] for r in failed],
        "results": results,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    # restore the historical QA artifact rewritten by test_no_local_paths.py
    scan = Path(ROOT) / "qa-artifacts-i3b-fix1c" / "local-path-scan.json"
    if scan.exists():
        subprocess.run(["git", "checkout", "--", str(scan)], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(f"tests_run={len(results)} passed={payload['passed']} FAIL_TOTAL={payload['fail_total']}")
    for r in failed:
        print("  FAILED:", r["test"], "rc=", r["rc"], r["tail"])
    return 0 if payload["fail_total"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
