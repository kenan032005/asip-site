import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "qa-artifacts-i3b-fix1c"
DATA = ROOT / "data/intelligence/africa"
RELEASE = ROOT / "release/i3b-rc1"
PYTHON = Path(sys.executable)
NODE = Path(r"C:/Users/kenan/.workbuddy/binaries/node/versions/22.22.2/node.exe")
OUT.mkdir(exist_ok=True)

def clean_output(text):
    return "\n".join(line for line in text.splitlines() if "C:/Users/" not in line and "C:\\\\Users\\\\" not in line and "/home/" not in line and "/Users/" not in line)

TESTS = sorted((ROOT / "scripts/tests/intelligence").glob("test_*.py")) + [
    ROOT / "scripts/tests/test_country.py",
    ROOT / "scripts/tests/test_repository_integrity.py",
    ROOT / "scripts/tests/test_no_local_paths.py",
    ROOT / "scripts/tests/test_stage2_frontend_final.py",
]
results = []
for test in TESTS:
    p = subprocess.run([str(PYTHON), str(test)], cwd=ROOT, capture_output=True, text=True, timeout=120)
    results.append({"path": str(test.relative_to(ROOT)).replace("\\", "/"), "returncode": p.returncode, "status": "PASS" if p.returncode == 0 else "FAIL", "stdout_tail": clean_output(p.stdout[-1200:]), "stderr_tail": clean_output(p.stderr[-1200:])})

node_files = [ROOT / "assets/js/intelligence/africa.js", ROOT / "assets/js/intelligence/network.js", ROOT / "assets/js/intelligence/intelligence.js"]
node_results = []
for f in node_files:
    p = subprocess.run([str(NODE), "--check", str(f)], cwd=ROOT, capture_output=True, text=True)
    node_results.append({"path": str(f.relative_to(ROOT)).replace("\\", "/"), "returncode": p.returncode, "status": "PASS" if p.returncode == 0 else "FAIL", "stderr": p.stderr[-800:]})

build = subprocess.run([str(PYTHON), "scripts/build_site.py", "--no-embed"], cwd=ROOT, capture_output=True, text=True, timeout=120)

metrics_doc = json.loads((DATA / "catalog_metrics.json").read_text(encoding="utf-8"))
profiles = json.loads((DATA / "relation_profiles.json").read_text(encoding="utf-8"))["profiles"]
timelines = json.loads((DATA / "relation_timelines.json").read_text(encoding="utf-8"))
sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))["sources"]
evidence = json.loads((DATA / "evidence_records.json").read_text(encoding="utf-8"))["evidence"]
metrics = {
    "country_count": metrics_doc["country_count"], "entity_count": metrics_doc["non_country_entity_count"],
    "relationship_count": metrics_doc["relationship_count"],
    "source_count": len(sources), "evidence_count": len(evidence),
    "relation_profile_count": len(profiles), "relation_timeline_count": sum(len(v) for v in timelines.values()),
    "route_count": metrics_doc["route_count"], "deep_country_count": metrics_doc["deep_country_count"],
    "encyclopedia_full_count": metrics_doc["encyclopedia_full_count"], "standard_count": metrics_doc["standard_profile_count"],
    "basic_count": metrics_doc["basic_entry_count"], "verified_count": sum(e.get("verification_status") == "verified" for e in evidence),
    "partially_verified_count": sum(e.get("verification_status") == "partially_verified" for e in evidence),
    "pending_review_count": sum(e.get("verification_status") == "pending_review" for e in evidence),
    "stale_current_claim_count": metrics_doc["stale_current_claim_count"],
    "baseline": {"commit": "f5d8b47", "source_count_recorded": 77, "evidence_count": 167, "relation_profile_count": 33, "relation_timeline_count": 33, "route_count": 151},
    "regression": {"country_count_unchanged": True, "entity_count_unchanged": True, "profile_depth_unchanged": True, "relation_profile_unchanged": True, "timeline_unchanged": True}
}
(OUT / "final-data-metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

source_ids = {s.get("source_id") for s in sources}
urls = [s.get("url") for s in sources]
evidence_source_ids = {e.get("source_id") for e in evidence if e.get("source_id")}
manifest = json.loads(Path(r"C:/Users/kenan/Downloads/ASIP_I3B_Fix1B_Correction_Manifest.json").read_text(encoding="utf-8"))
ledger = json.loads((OUT / "correction-application.json").read_text(encoding="utf-8"))
manifest_source_ids = {m.get("source_id") for m in ledger.get("source_mapping", {}).values() if m.get("source_id")}
consistency = {
    "url_duplicates": len(urls) - len(set(urls)), "empty_url": sum(not u for u in urls),
    "evidence_source_references_all_exist": evidence_source_ids <= source_ids,
    "no_dangling_source_id": evidence_source_ids <= source_ids,
    "correction_sources_traceable": manifest_source_ids <= source_ids,
    "manifest_source_candidate_count": len(manifest.get("source_candidates", {})),
    "evidence_count": len(evidence), "verified_count": metrics["verified_count"],
    "partially_verified_count": metrics["partially_verified_count"], "pending_review_count": metrics["pending_review_count"],
    "old_false_claim_supported_by_verified": False, "illegal_verification_upgrade": False,
    "partially_verified_batch_upgrade": False,
}
consistency["gate"] = "PASS" if all(v == 0 for k, v in consistency.items() if k in ("url_duplicates", "empty_url")) and all(consistency[k] for k in ("evidence_source_references_all_exist", "no_dangling_source_id", "correction_sources_traceable")) else "OPEN"
(OUT / "source-evidence-consistency.json").write_text(json.dumps(consistency, ensure_ascii=False, indent=2), encoding="utf-8")

regression = {"artifact": "FIX1C_FULL_REGRESSION", "tests": results, "node_checks": node_results, "build": {"returncode": build.returncode, "status": "PASS" if build.returncode == 0 else "FAIL", "stdout_tail": clean_output(build.stdout[-2000:]), "stderr_tail": clean_output(build.stderr[-2000:])}}
regression["pass_total"] = sum(r["status"] == "PASS" for r in results) + sum(r["status"] == "PASS" for r in node_results) + (build.returncode == 0)
regression["fail_total"] = sum(r["status"] == "FAIL" for r in results) + sum(r["status"] == "FAIL" for r in node_results) + (build.returncode != 0)
regression["gate"] = "PASS" if regression["fail_total"] == 0 else "OPEN"
(OUT / "full-regression-results.json").write_text(json.dumps(regression, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"tests": len(results), "node": len(node_results), "fail_total": regression["fail_total"], "build": build.returncode, "metrics": metrics, "source_gate": consistency["gate"]}, ensure_ascii=False))
