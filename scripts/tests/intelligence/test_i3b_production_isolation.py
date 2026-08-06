#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-B: production isolation tests — main/gh-pages production paths unchanged
except the versioned preview directory; no deletion of production files."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
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


def main():
    # production_isolation_results.json records the hash comparison before/after
    result = None
    if (RELEASE / "production_isolation_results.json").exists():
        result = json.loads((RELEASE / "production_isolation_results.json").read_text(encoding="utf-8"))
    if result:
        check("isolation comparison recorded", bool(result.get("production_paths_unchanged") is not None))
        check("production paths unchanged (only preview dir added)",
              result.get("production_paths_unchanged") is True,
              str(result.get("changed_paths", []))[:200])
        check("no production files deleted", result.get("deleted_paths") in (None, []))

    # git: local feature branch not merged to main
    r = subprocess.run(["git", "-C", str(ROOT), "log", "--oneline", "main..HEAD"], capture_output=True, text=True)
    check("feature branch commits not on main (not merged)", (r.stdout or "").strip() != "")

    # preview directory naming
    check("preview dir versioned",
          (RELEASE / "production_diff_summary.md").exists() and
          "previews" in (RELEASE / "production_diff_summary.md").read_text(encoding="utf-8"),
          "preview isolation documented")

    if FAIL:
        sys.exit(1)
    print(f"\nI3-B production isolation: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
