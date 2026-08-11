#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI/UX V2 scope diff audit.

Verifies ONLY intended presentation-layer files changed vs the UI/UX V2 base
(525012d, Expansion B acceptance HEAD), and that no knowledge data, historical
QA artifacts or other out-of-scope files are modified.
Outputs: OUT_OF_SCOPE_CHANGED_FILES = 0 (requirement for PASS).
"""
import io, os, subprocess, sys, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = "C:/Users/kenan/WorkBuddy/clean/asip-ppt-expansion-a"

ALLOWED_TRACKED_MODIFIED = {
    # presentation layer only (UI/UX V2 + Fix-1)
    "assets/js/intelligence/africa.js",
    "assets/css/intelligence.css",
    "intelligence/africa/_templates/entity.html",
    "intelligence/africa/_templates/relation.html",
    "intelligence/africa/_templates/network.html",
    "intelligence/africa/_templates/entities.html",
    "intelligence/africa/_templates/relations.html",
    # test contract updated for the reused .profile-toc class (V2 requirement)
    "scripts/tests/intelligence/test_i3a_preview.py",
    # Fix-1: QA tooling updated to verify the auto-linking renderer
    "scripts/qa/uiux_v2_derive_qa.py",
    "scripts/qa/uiux_v2_interaction_qa.js",
    # Fix-1: refreshed QA artifacts inside the V2 artifact tree
    "scripts/qa/uiux_v2_scope_audit.py",
}

ALLOWED_TRACKED_PREFIX = [
    # any refreshed artifact under the V2 QA tree is in-scope for Fix-1
    "qa-artifacts-uiux-v2/",
]

ALLOWED_UNTRACKED = {
    # UI/UX V2 QA tooling + artifacts
    "scripts/qa/uiux_v2_browser_qa.js",
    "scripts/qa/uiux_v2_interaction_qa.js",
    "scripts/qa/uiux_v2_link_qa.js",
    "scripts/qa/uiux_v2_derive_qa.py",
    "scripts/qa/uiux_v2_scope_audit.py",
    "scripts/qa/uiux_v2_fix1_qa.js",
    "qa-artifacts-uiux-v2/",
    # Phase 0 (read-only audit) tooling + artifacts, still untracked from the
    # previous accepted phase; not modified by this phase.
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
    if p == "qa-artifacts-uiux-v2/" or p.startswith("qa-artifacts-uiux-v2/"):
        continue
    if p == "qa-artifacts-uiux-v2-audit/" or p.startswith("qa-artifacts-uiux-v2-audit/"):
        continue
    if p not in ALLOWED_UNTRACKED:
        problems.append("OUT_OF_SCOPE UNTRACKED: " + p)

checks = {}
# knowledge data must be untouched
d = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", "data/intelligence/africa"],
                   cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
checks["knowledge_data_diff"] = d.stdout.strip() or "(none)"
# historical QA artifact must stay zero-diff
d2 = subprocess.run(["git", "diff", "--stat", "--", "qa-artifacts-i3b-fix1c/local-path-scan.json"],
                    cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
checks["local_path_scan_diff"] = "ZERO" if not d2.stdout.strip() else "NONZERO"
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
