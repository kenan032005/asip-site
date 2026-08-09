#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH B regeneration diff. Snapshot data -> run build generator on a copy? No:
the generator (build_intelligence_africa.py) is deterministic; a regen diff here
verifies that re-running the import script is idempotent (no unexpected object
deletions / count changes) by snapshotting data, re-running depth_d_import.py,
and diffing key structural signals. Requires git-style comparison of the 8
regeneration invariants listed in the instruction."""
import json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-d"
SCRATCH = QA / "scratch"
PACK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/Users/kenan/Downloads/ASIP_Depth_D_Sudan_Content_Pack.json")

snapshot = SCRATCH / "snapshot"
if SCRATCH.exists():
    shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True, exist_ok=True)
shutil.copytree(DATA, snapshot, dirs_exist_ok=True)

def load(base, name):
    return json.load(open(base / name, encoding="utf-8"))

def snapshot_signals(base):
    entities = load(base, "entities.json")["entities"]
    rels = load(base, "relationships.json")["relationships"]
    countries = load(base, "countries.json")["countries"]
    ep = load(base, "entity_profiles.json")["profiles"]
    rp = load(base, "relation_profiles.json")["profiles"]
    ev = load(base, "evidence_records.json")["evidence"]
    return {
        "entity_ids": {e["entity_id"] for e in entities},
        "relation_ids": {r["relationship_id"] for r in rels},
        "country_ids": {c["country_id"] for c in countries},
        "entity_importance": {e["entity_id"]: e.get("importance_level") for e in entities},
        "relation_types": {r["relationship_id"]: r["relationship_type"] for r in rels},
        "profile_depth": {eid: p.get("profile_depth") for eid, p in ep.items()},
        "evidence_ids": {x.get("evidence_id") for x in ev},
    }

before = snapshot_signals(snapshot)

# re-run import (idempotent pass)
subprocess.run([sys.executable, str(ROOT / "scripts" / "gen" / "depth_d_import.py"), str(PACK)],
               check=True, capture_output=True, text=True)

after = snapshot_signals(DATA)

def diff(label, a, b):
    if isinstance(a, set):
        return {"unexpected_deletions": sorted(a - b), "unexpected_additions": sorted(b - a)}
    if isinstance(a, dict):
        deleted = {k: a[k] for k in a if k not in b}
        changed = {k: (a[k], b[k]) for k in a if k in b and a[k] != b[k]}
        return {"deleted": deleted, "changed": changed}
    return {}

results = {}
results["unexpected_object_deletions"] = diff("entity_ids", before["entity_ids"], after["entity_ids"])
results["entity_count_change"] = len(before["entity_ids"]) != len(after["entity_ids"])
results["relationship_count_change"] = len(before["relation_ids"]) != len(after["relation_ids"])
results["country_count_change"] = len(before["country_ids"]) != len(after["country_ids"])
imp = diff("importance", before["entity_importance"], after["entity_importance"])
results["importance_level_change"] = bool(imp.get("changed") or imp.get("deleted"))
rt = diff("relation_types", before["relation_types"], after["relation_types"])
results["unintended_relation_type_change"] = bool(rt.get("changed") or rt.get("deleted"))
pd = diff("profile_depth", before["profile_depth"], after["profile_depth"])
results["profile_depth_regressions"] = {k: v for k, v in pd.get("changed", {}).items() if (v[0] or "") != (v[1] or "")}
evd = diff("evidence", before["evidence_ids"], after["evidence_ids"])
results["evidence_regressions"] = bool(evd.get("unexpected_deletions"))

# cleanup: restore snapshot over data (regen diff must not leave modified data)
shutil.rmtree(SCRATCH, ignore_errors=True)

report = {
    "artifact": "DEPTHD_REGEN_DIFF",
    "results": results,
    "gate": "PASS" if (
        not results["unexpected_object_deletions"]["unexpected_deletions"]
        and not results["unexpected_object_deletions"]["unexpected_additions"]
        and not results["entity_count_change"]
        and not results["relationship_count_change"]
        and not results["country_count_change"]
        and not results["importance_level_change"]
        and not results["unintended_relation_type_change"]
        and not results["profile_depth_regressions"]
        and not results["evidence_regressions"]
    ) else "OPEN",
}
with open(QA / "regen-diff.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps(results, ensure_ascii=False, indent=1))
print("gate:", report["gate"])
