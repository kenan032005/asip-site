#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH G full regression runner: all ASIP Intelligence Python/Node/build/
local-path/source/evidence/network/deep-route tests. FAIL_TOTAL must be 0."""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "scripts" / "tests" / "intelligence"
PY = sys.executable

test_files = sorted(TESTS.glob("test_*.py"))
print(f"found {len(test_files)} python test files")

fail_total = 0
results = []
for t in test_files:
    r = subprocess.run([PY, str(t)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    fail_line = [l for l in out.splitlines() if "FAIL_TOTAL" in l or "PASS" in l and "ALL" in l.upper()]
    nfail = 0
    for l in out.splitlines():
        if "FAIL_TOTAL=" in l:
            try:
                nfail = int(l.split("FAIL_TOTAL=")[1].split(":")[0])
            except Exception:
                nfail = -1
    # fallback: count explicit FAIL markers
    if nfail == 0 and "FAIL" in out and "FAIL_TOTAL" not in out:
        nfail = out.count("[FAIL]")
    ok = r.returncode == 0 and nfail == 0
    fail_total += nfail if nfail > 0 else (0 if ok else 1)
    results.append({"test": t.name, "rc": r.returncode, "fail": nfail, "ok": ok})
    print(f"  {'PASS' if ok else 'FAIL'} {t.name} (rc={r.returncode}, fail={nfail})")

# node tests
node_tests = sorted((ROOT / "scripts" / "tests").glob("**/*.test.js")) + sorted((ROOT / "scripts" / "tests").glob("**/*.mjs"))
if node_tests:
    NODE = r"C:/Users/kenan/.workbuddy/binaries/node/versions/22.22.2/node.exe"
    NODE_PATH = r"C:/Users/kenan/.workbuddy/binaries/node/workspace/node_modules"
    env = {"NODE_PATH": NODE_PATH}
    for nt in node_tests:
        r = subprocess.run([NODE, str(nt)], capture_output=True, text=True, encoding="utf-8", errors="replace", env={**dict(__import__("os").environ), **env})
        out = (r.stdout or "") + (r.stderr or "")
        ok = r.returncode == 0 and "FAIL" not in out
        if not ok:
            fail_total += 1
        results.append({"test": nt.name, "rc": r.returncode, "fail": 0, "ok": ok, "node": True})
        print(f"  {'PASS' if ok else 'FAIL'} {nt.name} (node, rc={r.returncode})")

# build-local-path check: run source/evidence/network/deep-route test scripts if present
extra = [f for f in (ROOT / "scripts" / "tests").rglob("*") if f.suffix == ".py" and "intelligence" not in str(f)]
for f in extra:
    if f.name.startswith("test_"):
        r = subprocess.run([PY, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        ok = r.returncode == 0
        if not ok:
            fail_total += 1
        results.append({"test": f.name, "rc": r.returncode, "fail": 0, "ok": ok})
        print(f"  {'PASS' if ok else 'FAIL'} {f.name} (rc={r.returncode})")

QA = ROOT / "qa-artifacts-depth-g"
QA.mkdir(parents=True, exist_ok=True)
(QA / "regression-report.json").write_text(json.dumps({
    "artifact": "DEPTHG_FULL_REGRESSION",
    "fail_total": fail_total,
    "tests_run": len(results),
    "passed": sum(1 for r in results if r["ok"]),
    "failed": [r for r in results if not r["ok"]],
    "results": results,
}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

print("tests run: %d  passed: %d" % (len(results), sum(1 for r in results if r["ok"])))
print(f"\nFAIL_TOTAL={fail_total}")
sys.exit(0 if fail_total == 0 else 1)
