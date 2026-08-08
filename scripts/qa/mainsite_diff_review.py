#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diff the 10 main-site files between dist and gh-pages, classify the nature of
the difference (build meta vs business content)."""
import difflib
import json
import re
from pathlib import Path

ROOT = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3c")
GH = Path("C:/Users/kenan/WorkBuddy/clean/asip-ghpages-wt")
FILES = ["404.html", "countries.html", "country.html", "data/status.json", "disease-risk.html", "event.html", "events.html", "index.html", "report.html", "reports.html"]
META = re.compile(r"(run_id|build_time|ASIP_BUILD_META|build_run|generated_at|last_updated|data_updated_at|updated_at|timestamp|ts)\s*[:=]")

out = []
for f in FILES:
    dp, gp = ROOT / "dist" / f, GH / f
    dt, gt = dp.read_text(encoding="utf-8"), gp.read_text(encoding="utf-8")
    diff = list(difflib.unified_diff(gt.splitlines(), dt.splitlines(), fromfile="gh:" + f, tofile="dist:" + f, lineterm=""))
    meta_lines = [l for l in diff if l.startswith(("+", "-")) and not l.startswith(("+++", "---")) and META.search(l)]
    business_lines = [l for l in diff if l.startswith(("+", "-")) and not l.startswith(("+++", "---")) and not META.search(l)]
    out.append({
        "file": f,
        "diff_line_count": len(diff),
        "meta_only_lines": len(meta_lines),
        "business_lines": business_lines[:12],
        "classification": "build_meta_or_whitespace" if not business_lines else "BUSINESS_CONTENT",
        "sample": diff[:14],
    })

json.dump(out, open(ROOT / "qa-artifacts-i3c" / "browser-fix-mainsite-diff-review.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
for o in out:
    print(o["file"], "|", o["classification"], "| diff lines:", o["diff_line_count"], "| business:", len(o["business_lines"]))
    if o["business_lines"]:
        print("   ", o["business_lines"][:6])
