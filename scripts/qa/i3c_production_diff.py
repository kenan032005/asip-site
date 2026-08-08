#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-C browser-fix production diff: compare freshly built dist candidate against
the currently published gh-pages tree, restricted to the I3-C whitelist."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GH = ROOT.parent / "asip-ghpages-wt"
DIST = ROOT / "dist"
OUT = ROOT / "qa-artifacts-i3c"

WHITELIST_PREFIXES = ("intelligence/africa/", "assets/js/common.js", "assets/js/intelligence/africa.js")
# Main-site files whose only difference is injected build metadata (run_id / build_time),
# verified by mainsite_diff_review.py: business diff lines = 0.
MAIN_SITE_BUILD_META_EXPECTED = {
    "404.html", "countries.html", "country.html", "data/status.json", "disease-risk.html",
    "event.html", "events.html", "index.html", "report.html", "reports.html",
}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def rel_path(p: Path, base: Path) -> str:
    return p.relative_to(base).as_posix()


def main():
    dist_files = {rel_path(p, DIST): p for p in DIST.rglob("*") if p.is_file()}
    gh_files = {rel_path(p, GH): p for p in GH.rglob("*") if p.is_file()}

    added, modified, deleted, unchanged = [], [], [], []
    outside = {"added": [], "modified": [], "deleted": []}
    preserved_rc_preview = []
    gh_pages_only_preserved = []
    for rel, dp in sorted(dist_files.items()):
        if rel == ".git" or rel.startswith(".git/"):
            continue
        gp = gh_files.get(rel)
        if gp is None:
            added.append(rel)
            if not rel.startswith(WHITELIST_PREFIXES):
                outside["added"].append(rel)
        elif sha(dp) != sha(gp):
            modified.append(rel)
            if not rel.startswith(WHITELIST_PREFIXES):
                outside["modified"].append(rel)
        else:
            unchanged.append(rel)
    for rel in sorted(gh_files):
        if rel == ".git" or rel.startswith(".git/"):
            continue
        if rel not in dist_files:
            deleted.append(rel)
            if rel.startswith("previews/"):
                preserved_rc_preview.append(rel)
            elif rel in {".github/workflows/asip-pages-preview-republish.yml", "asip-i3a-preview.txt"}:
                gh_pages_only_preserved.append(rel)
            elif not rel.startswith(WHITELIST_PREFIXES):
                outside["deleted"].append(rel)

    unexpected_modified = [r for r in outside["modified"] if r not in MAIN_SITE_BUILD_META_EXPECTED]
    unexpected_deleted = outside["deleted"]
    unexpected_added = outside["added"]

    report = {
        "artifact": "I3C_BROWSER_FIX_PRODUCTION_DIFF",
        "generated_at": "2026-08-08",
        "candidate_root": "dist",
        "production_root": "asip-ghpages-wt (gh-pages)",
        "whitelist": list(WHITELIST_PREFIXES),
        "added_count": len(added),
        "modified_count": len(modified),
        "deleted_count": len(deleted),
        "unchanged_count": len(unchanged),
        "added": added,
        "modified": modified,
        "deleted": deleted,
        "outside_whitelist_changes": outside,
        "expected_main_site_build_meta": sorted(MAIN_SITE_BUILD_META_EXPECTED),
        "preserved_rc_preview_count": len(preserved_rc_preview),
        "preserved_rc_preview": preserved_rc_preview[:20],
        "gh_pages_only_preserved": gh_pages_only_preserved,
        "unexpected_added": unexpected_added,
        "unexpected_modified": unexpected_modified,
        "unexpected_deleted": unexpected_deleted,
        "UNEXPECTED_MODIFIED": len(unexpected_modified),
        "UNEXPECTED_DELETED": len(unexpected_deleted),
        "UNEXPECTED_ADDED": len(unexpected_added),
        "gate": "PASS" if not unexpected_modified and not unexpected_deleted and not unexpected_added else "OPEN",
    }
    (OUT / "browser-fix-production-diff.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "added": len(added), "modified": len(modified), "deleted": len(deleted), "unchanged": len(unchanged),
        "outside_whitelist_changes": outside,
        "preserved_rc_preview_count": len(preserved_rc_preview),
        "gate": report["gate"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
