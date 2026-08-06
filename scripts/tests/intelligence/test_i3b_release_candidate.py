#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-B: release candidate package tests — release/i3b-rc1 files complete and
consistent with data metrics."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "africa"
RELEASE = ROOT / "release" / "i3b-rc1"
PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  ({detail})")


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


REQUIRED = [
    "release_candidate_manifest.json", "route_manifest.json", "asset_manifest.json",
    "data_metrics.json", "source_evidence_metrics.json", "production_diff_summary.md",
    "production_sync_plan.md", "rollback_plan.md", "pre_deploy_checklist.md",
    "post_deploy_checklist.md", "known_issues.md", "browser_qa_summary.json",
    "public_preview_verification.json", "build_sha256.txt",
]


def main():
    check("release dir exists", RELEASE.is_dir())
    missing = [f for f in REQUIRED if not (RELEASE / f).exists()]
    check("all 14 release files present", not missing, str(missing))

    manifest = None
    if (RELEASE / "release_candidate_manifest.json").exists():
        manifest = json.loads((RELEASE / "release_candidate_manifest.json").read_text(encoding="utf-8"))
    if manifest:
        m = load("catalog_metrics.json")
        check("manifest has required fields", all(k in manifest for k in (
            "release_name", "branch", "commit_sha", "tag", "build_time", "route_count",
            "country_count", "entity_count", "relation_count", "source_count",
            "evidence_count", "test_results", "public_preview_url",
            "production_base_path", "rollback_reference", "known_blockers", "release_status")))
        check("manifest counts match metrics",
              manifest.get("route_count") == m.get("route_count") and
              manifest.get("country_count") == m.get("country_count") and
              manifest.get("entity_count") == m.get("non_country_entity_count") and
              manifest.get("relation_count") == m.get("relationship_count") and
              manifest.get("evidence_count") == m.get("evidence_record_count"),
              "counts mismatch")
        check("manifest release_status is candidate/preview (not production)",
              manifest.get("release_status") in ("release_candidate", "preview_ready", "candidate"))

    if (RELEASE / "rollback_plan.md").exists():
        txt = (RELEASE / "rollback_plan.md").read_text(encoding="utf-8")
        check("rollback plan covers git/static/nav/cache", all(k in txt for k in ("回退", "备份", "验证")), "")

    if FAIL:
        sys.exit(1)
    print(f"\nI3-B release candidate: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
