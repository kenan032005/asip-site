#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Expansion C scope diff audit.

Verifies ONLY intended files changed vs the Expansion C base (f663949,
UIUX V2 Fix-1 acceptance HEAD). Outputs: OUT_OF_SCOPE_CHANGED_FILES = 0.
"""
import io, os, subprocess, sys, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = "C:/Users/kenan/WorkBuddy/clean/asip-ppt-expansion-a"

ALLOWED_TRACKED_MODIFIED = {
    # knowledge data (Expansion C import writes)
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
    # CSS: party-card wrap fix for long historical statuses (presentation only)
    "assets/css/intelligence.css",
    # test count pins raised to Expansion C scale (102/192/321)
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
    "scripts/tests/intelligence/test_expansion_b_gate.py",
    # QA tooling refreshed in-place (uiux_v2 + expansion_c)
    "scripts/qa/uiux_v2_derive_qa.py",
    "scripts/qa/expansion_c_semantic_audit.py",
    "scripts/qa/expansion_c_scope_audit.py",
    "scripts/qa/expansion_c_closure_audit.py",
    "scripts/qa/uiux_v2_interaction_qa.js",
    "scripts/qa/uiux_v2_scope_audit.py",
    # gitignore addition for the expansion-c Edge QA profile
    ".gitignore",
}

ALLOWED_TRACKED_PREFIX = [
    "qa-artifacts-expansion-c/",
]

ALLOWED_UNTRACKED = {
    "scripts/gen/expansion_c_content_sources.py",
    "scripts/gen/expansion_c_content_orgs_a.py",
    "scripts/gen/expansion_c_content_orgs_b.py",
    "scripts/gen/expansion_c_content_enrich.py",
    "scripts/gen/expansion_c_content_rels.py",
    "scripts/gen/expansion_c_import.py",
    "scripts/tests/intelligence/test_expansion_c_gate.py",
    "scripts/qa/expansion_c_browser_qa.js",
    "scripts/qa/expansion_c_link_qa.js",
    "scripts/qa/expansion_c_semantic_audit.py",
    "scripts/qa/expansion_c_scope_audit.py",
    "scripts/qa/expansion_c_closure_audit.py",
    "qa-artifacts-expansion-c/",
    # Phase 0 (read-only audit) tooling + artifacts, untouched
    "scripts/qa/uiux_v2_static_inventory.py",
    "scripts/qa/uiux_v2_browser_audit.js",
    "scripts/qa/uiux_v2_derive_audits.py",
    "scripts/qa/uiux_v2_finalize.py",
    "scripts/qa/uiux_v2_interaction_probe.js",
    "qa-artifacts-uiux-v2-audit/",
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
    if p in ALLOWED_TRACKED_MODIFIED:
        continue
    if any(p.startswith(pre) for pre in ALLOWED_TRACKED_PREFIX):
        continue
    problems.append("OUT_OF_SCOPE TRACKED MODIFIED: " + p)
for p in untracked:
    if p == "qa-artifacts-expansion-c/" or p.startswith("qa-artifacts-expansion-c/"):
        continue
    if p == "qa-artifacts-uiux-v2-audit/" or p.startswith("qa-artifacts-uiux-v2-audit/"):
        continue
    if p not in ALLOWED_UNTRACKED:
        problems.append("OUT_OF_SCOPE UNTRACKED: " + p)

checks = {}
d = subprocess.run(["git", "diff", "--stat", "--", "qa-artifacts-i3b-fix1c/local-path-scan.json"],
                   cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
checks["local_path_scan_diff"] = "ZERO" if not d.stdout.strip() else "NONZERO"
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
