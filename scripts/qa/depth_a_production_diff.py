#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH A production diff: dist candidate vs published gh-pages tree.
Whitelist: intelligence/africa/** + africa.js + intelligence.css (+ common.js unchanged).
Main-site build-meta diffs expected."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GH = ROOT.parent / "asip-ghpages-wt"
DIST = ROOT / "dist"
OUT = ROOT / "qa-artifacts-depth-a"

WHITELIST_PREFIXES = ("intelligence/africa/", "assets/js/common.js", "assets/js/intelligence/africa.js", "assets/css/intelligence.css")
MAIN_SITE_BUILD_META_EXPECTED = {
    "404.html", "countries.html", "country.html", "data/status.json", "disease-risk.html",
    "event.html", "events.html", "index.html", "report.html", "reports.html",
}


def sha(p):
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def main():
    dist_files = {p.relative_to(DIST).as_posix(): p for p in DIST.rglob("*") if p.is_file()}
    gh_files = {p.relative_to(GH).as_posix(): p for p in GH.rglob("*") if p.is_file()}
    added, modified, deleted, unchanged = [], [], [], []
    for rel, dp in sorted(dist_files.items()):
        if rel == ".git" or rel.startswith(".git/"):
            continue
        gp = gh_files.get(rel)
        if gp is None:
            added.append(rel)
        elif sha(dp) != sha(gp):
            modified.append(rel)
        else:
            unchanged.append(rel)
    preserved = []
    for rel in sorted(gh_files):
        if rel == ".git" or rel.startswith(".git/"):
            continue
        if rel not in dist_files:
            deleted.append(rel)
            if rel.startswith("previews/") or rel in {".github/workflows/asip-pages-preview-republish.yml", "asip-i3a-preview.txt"}:
                preserved.append(rel)

    outside_modified = [r for r in modified if not r.startswith(WHITELIST_PREFIXES)]
    expected_meta = [r for r in outside_modified if r in MAIN_SITE_BUILD_META_EXPECTED]
    unexpected_modified = [r for r in outside_modified if r not in MAIN_SITE_BUILD_META_EXPECTED]
    unexpected_deleted = [r for r in deleted if not r.startswith("previews/") and r not in {".github/workflows/asip-pages-preview-republish.yml", "asip-i3a-preview.txt"}]
    unexpected_added = [r for r in added if not r.startswith(WHITELIST_PREFIXES)]
    whitelist_changed = [r for r in modified if r.startswith(WHITELIST_PREFIXES)]

    report = {
        "artifact": "DEPTHA_PRODUCTION_DIFF",
        "generated_at": "2026-08-08",
        "candidate_root": "dist",
        "production_root": "asip-ghpages-wt (gh-pages)",
        "whitelist": list(WHITELIST_PREFIXES),
        "added_count": len(added),
        "modified_count": len(modified),
        "deleted_count": len(deleted),
        "unchanged_count": len(unchanged),
        "preserved_rc_preview_count": len([x for x in preserved if x.startswith("previews/")]),
        "whitelist_changed": whitelist_changed,
        "expected_main_site_build_meta": expected_meta,
        "unexpected_added": unexpected_added,
        "unexpected_modified": unexpected_modified,
        "unexpected_deleted": unexpected_deleted,
        "UNEXPECTED_MODIFIED": len(unexpected_modified),
        "UNEXPECTED_DELETED": len(unexpected_deleted),
        "UNEXPECTED_ADDED": len(unexpected_added),
        "gate": "PASS" if not unexpected_modified and not unexpected_deleted and not unexpected_added else "OPEN",
    }
    (OUT / "production-diff.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"added": len(added), "modified": len(modified), "deleted": len(deleted), "unchanged": len(unchanged), "whitelist_changed": whitelist_changed, "expected_main_site_build_meta": expected_meta, "unexpected_modified": unexpected_modified, "unexpected_deleted": unexpected_deleted, "unexpected_added": unexpected_added, "gate": report["gate"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
