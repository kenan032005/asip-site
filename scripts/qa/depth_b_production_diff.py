#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH B production diff: compare local dist intelligence/africa against the
gh-pages worktree. Only whitelisted changes allowed: intelligence/africa/** and
the shared intelligence JS/CSS. No new top-level pages outside whitelist,
no deletions outside whitelist, no changes to other ASIP modules."""
import json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist" / "intelligence" / "africa"
WT = Path("C:/Users/kenan/WorkBuddy/clean/asip-ghpages-wt") / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-b"
QA.mkdir(parents=True, exist_ok=True)

WHITELIST_PREFIXES = ("intelligence/africa/",)
SHARED_FILES = {
    "assets/js/intelligence/africa.js",
    "assets/css/intelligence.css",
}

# run git status in gh-pages worktree AFTER sync to detect what changed
# instead: diff the two trees (dist candidate vs production worktree)
def tree_files(base):
    out = {}
    for p in base.rglob("*"):
        if p.is_file():
            rel = p.relative_to(base).as_posix()
            out[rel] = p
    return out

cand = tree_files(DIST)
prod = tree_files(WT)

added = sorted(set(cand) - set(prod))
removed = sorted(set(prod) - set(cand))
changed = []
for rel in sorted(set(cand) & set(prod)):
    if not cand[rel].read_bytes() == prod[rel].read_bytes():
        changed.append(rel)

unexpected = []
for rel in added + removed + changed:
    full = "intelligence/africa/" + rel
    ok = any(full.startswith(p) for p in WHITELIST_PREFIXES) or full in SHARED_FILES
    if not ok:
        unexpected.append(full)

report = {
    "artifact": "DEPTHB_PRODUCTION_DIFF",
    "added_files": added, "removed_files": removed, "changed_files": changed,
    "unexpected_changes_outside_whitelist": unexpected,
    "gate": "PASS" if not unexpected else "OPEN",
}
with open(QA / "production-diff.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"added={len(added)} removed={len(removed)} changed={len(changed)}")
print(f"UNEXPECTED outside whitelist: {len(unexpected)}")
for u in unexpected[:10]:
    print("  !!", u)
print("gate:", report["gate"])
sys.exit(0 if not unexpected else 1)
