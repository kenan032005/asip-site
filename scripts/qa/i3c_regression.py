import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "qa-artifacts-i3c"
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
]

def rel(path):
    return str(path.relative_to(ROOT)).replace("\\", "/")

def scrub(text):
    text = text or ""
    lines = []
    for line in text.splitlines():
        if "C:/Users/" in line or "C:\\Users\\" in line or "/home/" in line or "/Users/" in line:
            continue
        lines.append(line)
    return "\n".join(lines)[-1600:]

def run(command, timeout=180):
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout)

results = []
for test in TESTS:
    p = run([str(PYTHON), str(test)])
    results.append({
        "path": rel(test),
        "returncode": p.returncode,
        "status": "PASS" if p.returncode == 0 else "FAIL",
        "stdout_tail": scrub(p.stdout),
        "stderr_tail": scrub(p.stderr),
    })

node_results = []
for source in NODE_FILES:
    p = run([str(NODE), "--check", str(source)])
    node_results.append({
        "path": rel(source),
        "returncode": p.returncode,
        "status": "PASS" if p.returncode == 0 else "FAIL",
        "stderr_tail": scrub(p.stderr),
    })

build = run([str(PYTHON), "scripts/build_site.py", "--no-embed"], timeout=180)

metrics = json.loads((ROOT / "data/intelligence/africa/catalog_metrics.json").read_text(encoding="utf-8"))
expected = {
    "country_count": 13,
    "entity_count": 46,
    "relationship_count": 78,
    "source_count": 96,
    "evidence_count": 167,
    "relation_profile_count": 33,
    "relation_timeline_count": 33,
    "route_count": 151,
}
actual = {
    "country_count": metrics.get("country_count"),
    "entity_count": metrics.get("non_country_entity_count"),
    "relationship_count": metrics.get("relationship_count"),
    "source_count": metrics.get("source_count"),
    "evidence_count": metrics.get("evidence_record_count"),
    "relation_profile_count": metrics.get("relation_profile_count"),
    "relation_timeline_count": metrics.get("relation_timeline_count"),
    "route_count": metrics.get("route_count"),
}
metric_gate = actual == expected
fail_total = sum(item["status"] == "FAIL" for item in results) + sum(item["status"] == "FAIL" for item in node_results) + (build.returncode != 0) + (not metric_gate)
record = {
    "artifact": "I3C_PRE_PRODUCTION_REGRESSION",
    "python_test_count": len(results),
    "node_check_count": len(node_results),
    "tests": results,
    "node_checks": node_results,
    "build": {
        "command": "python scripts/build_site.py --no-embed",
        "returncode": build.returncode,
        "status": "PASS" if build.returncode == 0 else "FAIL",
        "stdout_tail": scrub(build.stdout),
        "stderr_tail": scrub(build.stderr),
    },
    "metrics": {"expected": expected, "actual": actual, "gate": "PASS" if metric_gate else "FAIL"},
    "fail_total": fail_total,
    "gate": "PASS" if fail_total == 0 else "OPEN",
}
(OUT / "pre-production-regression.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"python_tests": len(results), "node_checks": len(node_results), "fail_total": fail_total, "build": build.returncode, "metric_gate": record["metrics"]["gate"], "gate": record["gate"]}, ensure_ascii=False))
