#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXPANSION B scope diff audit.

Verifies ONLY intended files changed vs the Expansion B base (ae36014), and
that no historical QA artifacts or other out-of-scope files are modified.
Outputs: OUT_OF_SCOPE_CHANGED_FILES = 0 (requirement for PASS).
"""
import io, os, subprocess, sys, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = "C:/Users/kenan/WorkBuddy/clean/asip-ppt-expansion-a"

ALLOWED_TRACKED_MODIFIED = {
    # knowledge data (Expansion B import writes)
    "data/intelligence/africa/alias_index.json",
    "data/intelligence/africa/catalog_metrics.json",
    "data/intelligence/africa/entities.json",
    "data/intelligence/africa/entity_profiles.json",
    "data/intelligence/africa/evidence_records.json",
    "data/intelligence/africa/external_links.json",
    "data/intelligence/africa/force_estimates.json",
    "data/intelligence/africa/graph_index.json",
    "data/intelligence/africa/relation_profiles.json",
    "data/intelligence/africa/relation_timelines.json",
    "data/intelligence/africa/relationships.json",
    "data/intelligence/africa/sources.json",
    # generator derived file (relation-count gate)
    "scripts/build_intelligence_africa.py",
    # targeted test pins (BLOCKER B scale updates + expansion_b gate test file is new)
    "scripts/tests/intelligence/test_africa_data.py",
    "scripts/tests/intelligence/test_africa_metrics.py",
    "scripts/tests/intelligence/test_depth_a_import.py",
    "scripts/tests/intelligence/test_depth_b_import.py",
    "scripts/tests/intelligence/test_depth_c_import.py",
    "scripts/tests/intelligence/test_depth_d_import.py",
    "scripts/tests/intelligence/test_depth_e_import.py",
    "scripts/tests/intelligence/test_depth_f_import.py",
    "scripts/tests/intelligence/test_depth_g_closure.py",
    "scripts/tests/intelligence/test_i3d1_import.py",
    "scripts/tests/intelligence/test_i3d2_import.py",
    # gitignore addition for the expansion-b Edge QA profile
    ".gitignore",
}

ALLOWED_UNTRACKED = {
    "scripts/gen/expansion_b_content_sources.py",
    "scripts/gen/expansion_b_content_orgs.py",
    "scripts/gen/expansion_b_content_orgs2.py",
    "scripts/gen/expansion_b_content_persons.py",
    "scripts/gen/expansion_b_content_rels.py",
    "scripts/gen/expansion_b_content_rels2.py",
    "scripts/gen/expansion_b_import.py",
    "scripts/tests/intelligence/test_expansion_b_gate.py",
    "scripts/qa/expansion_b_regression.py",
    "scripts/qa/expansion_b_browser_qa.js",
    "scripts/qa/expansion_b_link_qa.js",
    "scripts/qa/expansion_a_link_qa.js",
    "scripts/qa/exp_a_static_server.js",
    "scripts/qa/expansion_a_browser_qa.js",
    "scripts/qa/expansion_a_final_acceptance.py",
    "scripts/qa/expansion_a_scope_audit.py",
    "scripts/qa/expansion_a_regression.py",
    "scripts/qa/expansion_b_scope_audit.py",
    "scripts/qa/expansion_b_semantic_audit.py",
    "scripts/qa/expansion_b_final_acceptance.py",
    "qa-artifacts-expansion-b/",
}

out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
lines = [l for l in out.stdout.splitlines() if l.strip()]

problems = []
tracked_modified = []
untracked = []
for l in lines:
    code = l[:2]
    path = l[3:]
    if code in ("M ", "MM", "AM", "A "):
        tracked_modified.append(path)
    elif code == "??":
        untracked.append(path)
    else:
        tracked_modified.append(path)

for p in tracked_modified:
    if p not in ALLOWED_TRACKED_MODIFIED:
        problems.append("OUT_OF_SCOPE TRACKED MODIFIED: " + p)
for p in untracked:
    if p == "qa-artifacts-expansion-b/" or p.startswith("qa-artifacts-expansion-b/"):
        continue
    if p not in ALLOWED_UNTRACKED:
        problems.append("OUT_OF_SCOPE UNTRACKED: " + p)

checks = {}
d = subprocess.run(["git", "diff", "--stat", "--", "qa-artifacts-i3b-fix1c/local-path-scan.json"],
                   cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
checks["local_path_scan_diff"] = "ZERO" if not d.stdout.strip() else "NONZERO"
staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
checks["staged_files"] = staged.stdout.strip() or "(none)"
prod = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", "gh-pages", "docs"],
                      cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
checks["production_gh_pages_diff"] = prod.stdout.strip() or "(none)"
br = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
head = subprocess.run(["git", "log", "--oneline", "-1"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
checks["branch"] = br.stdout.strip()
checks["head"] = head.stdout.strip()

out_of_scope = len(problems)
print(json.dumps({
    "OUT_OF_SCOPE_CHANGED_FILES": out_of_scope,
    "problems": problems,
    "tracked_modified_count": len(tracked_modified),
    "untracked_count": len(untracked),
    "checks": checks,
}, ensure_ascii=False, indent=1))
sys.exit(1 if out_of_scope else 0)
