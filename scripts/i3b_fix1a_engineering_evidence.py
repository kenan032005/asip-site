#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-B-Fix-1A engineering evidence helpers.

This module intentionally records only GitHub Pages, Git, artifact and
production-path metadata. It does not inspect or modify intelligence content.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa-artifacts-i3b-fix1a"


def run(*args: str, cwd: Path = ROOT) -> str:
    p = subprocess.run([*args], cwd=cwd, text=True, capture_output=True, check=False)
    return (p.stdout or "") + (p.stderr or "")


def files_under(root: Path, prefix: str = "") -> dict[str, str]:
    result: dict[str, str] = {}
    if not root.exists():
        return result
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        result[prefix + rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def write_json(name: str, payload: Any) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def git_tree_files(commit: str) -> dict[str, str]:
    result: dict[str, str] = {}
    listing = run("git", "ls-tree", "-r", "--format=%(objectname) %(path)", commit, cwd=Path("C:/Users/kenan/WorkBuddy/clean/asip-ghpages-wt"))
    for line in listing.splitlines():
        if not line.strip():
            continue
        sha, path = line.split(" ", 1)
        if path.startswith("previews/asip-intelligence-v1.0-rc1/"):
            continue
        result[path] = sha
    return result


def main() -> None:
    ghpages = Path("C:/Users/kenan/WorkBuddy/clean/asip-ghpages-wt")
    before_commit = "4703ab80210ba283973a6cb86108e311d4d3b583"
    after_commit = "d8cb693d0d736ae2ab87690bae42478fa2d2c32f"
    before = {
        "schema": "asip-i3b-fix1a-production-isolation-v1",
        "captured_at": "gh-pages-before-fix1a-pages-workflow",
        "commit": before_commit,
        "scope": "gh-pages production root excluding previews/asip-intelligence-v1.0-rc1/",
        "files": git_tree_files(before_commit),
    }
    after = {
        "schema": "asip-i3b-fix1a-production-isolation-v1",
        "captured_at": "gh-pages-after-preview-tree-append-before-fix1a-pages-workflow",
        "commit": after_commit,
        "scope": "gh-pages production root excluding previews/asip-intelligence-v1.0-rc1/",
        "files": git_tree_files(after_commit),
    }
    write_json("production-before.json", before)
    write_json("production-after.json", after)
    before_files = before["files"]
    after_files = after["files"]
    changed = sorted(k for k in set(before_files) | set(after_files) if before_files.get(k) != after_files.get(k))
    write_json("production-diff.json", {
        "schema": "asip-i3b-fix1a-production-diff-v1",
        "before_commit": before_commit,
        "after_commit": after_commit,
        "existing_changed": len([p for p in changed if p in before_files and p in after_files]),
        "existing_deleted": len([p for p in before_files if p not in after_files]),
        "added": sorted(p for p in after_files if p not in before_files),
        "changed_paths": changed,
        "deleted_paths": sorted(p for p in before_files if p not in after_files),
        "production_unchanged": not changed,
        "preview_scope": "previews/asip-intelligence-v1.0-rc1/ is excluded from production comparison",
    })
    write_json("git-state.json", {
        "status_porcelain": run("git", "status", "--porcelain"),
        "branch": run("git", "branch", "--show-current").strip(),
        "head": run("git", "rev-parse", "HEAD").strip(),
        "fsck": run("git", "fsck", "--full"),
        "ls_remote": run("git", "ls-remote", "origin"),
    })


if __name__ == "__main__":
    main()
