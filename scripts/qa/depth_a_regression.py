#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH A full regression: all intelligence python tests, node checks, build,
local-path scan, metrics, route presence."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "qa-artifacts-depth-a"
PYTHON = Path(sys.executable)
NODE = Path(r"C:/Users/kenan/.workbuddy/binaries/node/versions/22.22.2/node.exe")

TESTS = sorted((ROOT / "scripts/tests/intelligence").glob("test_*.py")) + [
    ROOT / "scripts/tests/test_country.py",
    ROOT / "scripts/tests/test_repository_integrity.py",
    ROOT / "scripts/tests/test_no_local_paths.py",
    ROOT / "scripts/tests/test_i3b_fix1c_postqa_manifest_state.py",
    ROOT / "scripts/tests/test_stage2_frontend_final.py",
]
NODE_FILES = [
    ROOT / "assets/js/intelligence/africa.js",
    ROOT / "assets/js/intelligence/network.js",
    ROOT / "assets/js/intelligence/intelligence.js",
    ROOT / "assets/js/common.js",
]


def rel(p):
    return str(p.relative_to(ROOT)).replace("\\", "/")


def scrub(text):
    text = text or ""
    lines = []
    for line in text.splitlines():
        if "C:/Users/" in line or "C:\\Users\\" in line or "/home/" in line or "/Users/" in line:
            continue
        lines.append(line)
    return "\n".join(lines)[-1200:]


def run(cmd, timeout=240):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)


results = []
fail_total = 0
for test in TESTS:
    p = run([str(PYTHON), str(test)])
    status = "PASS" if p.returncode == 0 else "FAIL"
    if p.returncode != 0:
        fail_total += 1
    results.append({"path": rel(test), "returncode": p.returncode, "status": status, "stdout_tail": scrub(p.stdout), "stderr_tail": scrub(p.stderr)})

node_results = []
for src in NODE_FILES:
    p = run([str(NODE), "--check", str(src)])
    status = "PASS" if p.returncode == 0 else "FAIL"
    if p.returncode != 0:
        fail_total += 1
    node_results.append({"path": rel(src), "returncode": p.returncode, "status": status, "stderr_tail": scrub(p.stderr)})

build = run([str(PYTHON), "scripts/build_site.py", "--no-embed"], timeout=300)
build_status = "PASS" if build.returncode == 0 else "FAIL"
if build.returncode != 0:
    fail_total += 1

metrics = json.loads((ROOT / "data/intelligence/africa/catalog_metrics.json").read_text(encoding="utf-8"))
expected = {"country_count": 13, "non_country_entity_count": 72, "relationship_count": 150, "route_count": 249}
actual = {k: metrics.get(k) for k in expected}
metrics_ok = all(expected[k] == actual[k] for k in expected)
if not metrics_ok:
    fail_total += 1

forbidden = ["C:/Users/", "C:\\Users\\", "/home/", "/Users/", "D:/apps"]
local_hits = []
for base in [ROOT / "data" / "intelligence" / "africa", ROOT / "intelligence" / "africa" / "_templates", ROOT / "assets" / "js" / "intelligence"]:
    if not base.exists():
        continue
    for f in sorted(base.rglob("*")):
        if f.is_file() and f.suffix in (".json", ".html", ".js", ".py"):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for fw in forbidden:
                if fw in text:
                    local_hits.append(f"{rel(f)}:{fw}")
if local_hits:
    fail_total += len(local_hits)

dist = ROOT / "dist" / "intelligence" / "africa"
route_missing = []
for rt in ["entity/jnim/", "entity/is-sahel/", "entity/amadou-koufa/", "relation/jnim-is-sahel-conflict/", "relation/jnim-alqaida-affiliate/", "relation/d1-fla-jnim-cooperation/"]:
    if not (dist / rt / "index.html").exists():
        route_missing.append(rt)
        fail_total += 1

report = {
    "artifact": "DEPTHA_FULL_REGRESSION",
    "python_tests_total": len(results),
    "python_tests_failed": sum(1 for r in results if r["status"] == "FAIL"),
    "node_checks_total": len(node_results),
    "node_checks_failed": sum(1 for r in node_results if r["status"] == "FAIL"),
    "build_status": build_status,
    "metrics": {"expected": expected, "actual": actual, "ok": metrics_ok},
    "local_path_hits": local_hits,
    "route_missing": route_missing,
    "results": results,
    "node_results": node_results,
    "FAIL_TOTAL": fail_total,
    "gate": "PASS" if fail_total == 0 else "OPEN",
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "full-regression.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({
    "python_tests": f"{sum(1 for r in results if r['status']=='PASS')}/{len(results)}",
    "node_checks": f"{sum(1 for r in node_results if r['status']=='PASS')}/{len(node_results)}",
    "build": build_status,
    "metrics_ok": metrics_ok,
    "local_path_hits": len(local_hits),
    "route_missing": route_missing,
    "FAIL_TOTAL": fail_total,
    "gate": report["gate"],
}, ensure_ascii=False, indent=1))
if fail_total:
    for r in results:
        if r["status"] == "FAIL":
            print("FAIL TEST:", r["path"], r["stderr_tail"][-400:])
    sys.exit(1)
