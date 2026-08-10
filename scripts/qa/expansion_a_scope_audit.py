# -*- coding: utf-8 -*-
"""Scope diff audit for Expansion A:
Verify that ONLY the intended file set changed vs HEAD, and that no historical
QA artifacts or other out-of-scope files are modified. Outputs:
OUT_OF_SCOPE_CHANGED_FILES = 0  (requirement for PASS)
"""
import io, os, subprocess, sys, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = "C:/Users/kenan/WorkBuddy/clean/asip-ppt-expansion-a"

ALLOWED_TRACKED_MODIFIED = {
    # knowledge data (Expansion A import writes)
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
    # frontend render config (BLOCKER C fix + network_links key + duplicate-causes fix)
    "assets/js/intelligence/africa.js",
    # gitignore addition: Edge headless QA browser profile under qa-artifacts-expansion-a
    ".gitignore",
    # generator derived file (relation-count gate)
    "scripts/build_intelligence_africa.py",
    # targeted test pins (BLOCKER B scale updates)
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
}

ALLOWED_UNTRACKED = {
    # Expansion A content modules
    "scripts/gen/expansion_a_content_sources.py",
    "scripts/gen/expansion_a_content_orgs.py",
    "scripts/gen/expansion_a_content_persons.py",
    "scripts/gen/expansion_a_content_enrich.py",
    "scripts/gen/expansion_a_content_rels.py",
    "scripts/gen/expansion_a_import.py",
    "scripts/gen/expansion_a_dedup_audit.py",
    # QA tooling
    "scripts/qa/expansion_a_regression.py",
    "scripts/qa/expansion_a_browser_qa.js",
    "scripts/qa/expansion_a_link_qa.js",
    "scripts/qa/exp_a_static_server.js",
    "scripts/qa/expansion_a_scope_audit.py",
    "scripts/qa/expansion_a_final_acceptance.py",
    # QA artifacts directory
    "qa-artifacts-expansion-a/",
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
        tracked_modified.append(path)  # anything else that changed (D, R, C)

for p in tracked_modified:
    if p not in ALLOWED_TRACKED_MODIFIED:
        problems.append("OUT_OF_SCOPE TRACKED MODIFIED: " + p)
for p in untracked:
    if p == "qa-artifacts-expansion-a/":
        continue
    if p.startswith("qa-artifacts-expansion-a/"):
        continue
    if p not in ALLOWED_UNTRACKED:
        problems.append("OUT_OF_SCOPE UNTRACKED: " + p)

# extra checks
checks = {}

# 1. local-path-scan.json must have zero diff
d = subprocess.run(["git", "diff", "--stat", "--", "qa-artifacts-i3b-fix1c/local-path-scan.json"],
                   cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
checks["local_path_scan_diff"] = "ZERO" if not d.stdout.strip() else "NONZERO: " + d.stdout.strip()[:120]

# 2. no staged-but-uncommitted leftovers that would enter the diff outside our files
staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
checks["staged_files"] = staged.stdout.strip() or "(none)"

# 3. production / gh-pages unchanged
prod = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", "gh-pages", "docs"],
                      cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
checks["production_gh_pages_diff"] = prod.stdout.strip() or "(none)"

# 4. branch / HEAD sanity
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
