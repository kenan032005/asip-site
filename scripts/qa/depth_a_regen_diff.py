#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH A generator regeneration diff (8 zero-regression requirements)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
SCRATCH = ROOT / ".dist_trash" / "deptha-regen"
PACK = Path("C:/Users/kenan/Downloads/ASIP_Depth_A_Sahel_Flagship_Content_Pack.json")
snapshot = SCRATCH / "snapshot"
SCRATCH.mkdir(parents=True, exist_ok=True)
shutil.copytree(DATA, snapshot, dirs_exist_ok=True)

script = ROOT / "scripts" / "gen" / "depth_a_import.py"
r = subprocess.run([sys.executable, str(script), str(PACK)], capture_output=True, text=True, encoding="utf-8")
if r.returncode != 0:
    print("import rerun failed:", r.stderr[-800:])
    sys.exit(1)


def load_tree(base):
    return {f.name: json.loads(f.read_text(encoding="utf-8")) for f in sorted(base.glob("*.json"))}


before = load_tree(snapshot)
after = load_tree(DATA)
report = {
    "artifact": "DEPTHA_GENERATOR_REGEN_DIFF",
    "idempotent_rerun_exit": r.returncode,
    "unexpected_object_deletions": 0,
    "entity_count_change": 0,
    "relationship_count_change": 0,
    "importance_level_change": 0,
    "relation_type_change": 0,
    "profile_depth_regressions": 0,
    "timeline_regressions": 0,
    "evidence_regressions": 0,
}
issues = []

for name in sorted(set(before) | set(after)):
    if name not in before:
        continue
    if name not in after:
        issues.append(f"file deleted: {name}")
        report["unexpected_object_deletions"] += 1
        continue
    s, rj = before[name], after[name]
    if isinstance(s, dict) and isinstance(rj, dict) and "profiles" in s:
        missing = set(s["profiles"].keys()) - set(rj["profiles"].keys())
        if missing:
            issues.append(f"profile objects deleted in {name}: {missing}")
            report["profile_depth_regressions"] += len(missing)
        for k in set(s["profiles"]) & set(rj["profiles"]):
            if s["profiles"][k].get("profile_depth") != rj["profiles"][k].get("profile_depth"):
                issues.append(f"profile_depth changed {k}")
                report["profile_depth_regressions"] += 1
    if isinstance(s, dict) and isinstance(rj, dict) and "timelines" in s:
        missing = set(s["timelines"].keys()) - set(rj["timelines"].keys())
        if missing:
            issues.append(f"timeline objects deleted in {name}: {missing}")
            report["timeline_regressions"] += len(missing)
    if name == "entities.json":
        b_ents = {e["entity_id"]: e for e in s["entities"]}
        a_ents = {e["entity_id"]: e for e in rj["entities"]}
        if set(b_ents) != set(a_ents):
            issues.append("entity set changed")
            report["entity_count_change"] += 1
        for eid in set(b_ents) & set(a_ents):
            if b_ents[eid].get("importance_level") != a_ents[eid].get("importance_level"):
                issues.append(f"importance changed {eid}")
                report["importance_level_change"] += 1
    if name == "relationships.json":
        b_rels = {x["relationship_id"]: x for x in s["relationships"]}
        a_rels = {x["relationship_id"]: x for x in rj["relationships"]}
        if set(b_rels) != set(a_rels):
            issues.append("relationship set changed")
            report["relationship_count_change"] += 1
        for rid in set(b_rels) & set(a_rels):
            if b_rels[rid]["relationship_type"] != a_rels[rid]["relationship_type"]:
                issues.append(f"relation type changed {rid}")
                report["relation_type_change"] += 1
    if name == "evidence_records.json":
        b_ids = {e["evidence_id"] for e in s["evidence"]}
        a_ids = {e["evidence_id"] for e in rj["evidence"]}
        missing_ev = b_ids - a_ids
        if missing_ev:
            issues.append(f"evidence deleted: {missing_ev}")
            report["evidence_regressions"] += len(missing_ev)

report["issues"] = issues
report["gate"] = "PASS" if not issues else "OPEN"
(ROOT / "qa-artifacts-depth-a" / "generator-regen-diff.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in report.items() if k != "issues"} | {"issues": issues}, ensure_ascii=False, indent=1))
if issues:
    sys.exit(1)
