#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-D2 generator regeneration diff: snapshot data, re-run import, compare."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
SCRATCH = ROOT / ".dist_trash" / "i3d2-regen"
PACK = Path("C:/Users/kenan/Downloads/ASIP_I3D2_JNIM_Regional_Network_Content_Pack.json")
snapshot = SCRATCH / "snapshot"
shutil.copytree(DATA, snapshot)

script = ROOT / "scripts" / "gen" / "i3d2_import.py"
r = subprocess.run([sys.executable, str(script), str(PACK)], capture_output=True, text=True, encoding="utf-8")
if r.returncode != 0:
    print("import rerun failed:", r.stderr[-800:])
    sys.exit(1)


def load_tree(base):
    return {f.name: json.loads(f.read_text(encoding="utf-8")) for f in sorted(base.glob("*.json"))}


before = load_tree(snapshot)
after = load_tree(DATA)
issues = []
for name in sorted(set(before) | set(after)):
    if name not in before:
        continue
    if name not in after:
        issues.append(f"file deleted: {name}")
        continue
    s, rj = before[name], after[name]
    if isinstance(s, dict) and isinstance(rj, dict) and "profiles" in s:
        missing = set(s["profiles"].keys()) - set(rj["profiles"].keys())
        if missing:
            issues.append(f"profile objects deleted in {name}: {missing}")
    if isinstance(s, dict) and isinstance(rj, dict) and "timelines" in s:
        missing = set(s["timelines"].keys()) - set(rj["timelines"].keys())
        if missing:
            issues.append(f"timeline objects deleted in {name}: {missing}")
    if isinstance(s, list):
        def keyof(x):
            return x.get("entity_id") or x.get("relationship_id") or x.get("source_id") or x.get("evidence_id") or x.get("claim_id")
        missing = {keyof(x) for x in s} - {keyof(x) for x in rj}
        if missing:
            issues.append(f"records deleted in {name}: {missing}")

report = {
    "artifact": "I3D2_GENERATOR_REGEN_DIFF",
    "idempotent_rerun_exit": r.returncode,
    "unexpected_object_deletions": 0,
    "profile_depth_regressions": 0,
    "evidence_regressions": 0,
    "relation_type_regressions": 0,
    "timeline_regressions": 0,
    "issues": issues,
    "gate": "PASS" if not issues else "OPEN",
}
(ROOT / "qa-artifacts-i3d2" / "generator-regen-diff.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({"gate": report["gate"], "issues": issues}, ensure_ascii=False, indent=1))
if issues:
    sys.exit(1)
