#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append DEPTH A partition CSS."""
from pathlib import Path

css = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-depth-a/assets/css/intelligence.css")
block = """

/* DEPTH A: Facts vs ASIP Analysis partitions + maturity badges */
.intel-analysis-card,.intel-watch-card{border-radius:10px;padding:15px 17px}
.intel-analysis-card{background:#eef5fb;border:1px solid #cfe0f0;border-left:4px solid #14507e}
.intel-analysis-card h2,.intel-watch-card h2{font-size:15px;color:#0f3a5d;border-left:0;padding-left:0;margin:0 0 8px}
.intel-watch-card{background:#f7f4ec;border:1px solid #ecdfc2;border-left:4px solid #b98a2e}
.intel-watch-card ul{margin:0;padding-left:18px}
.intel-watch-card li{font-size:13px;line-height:1.7;color:#5c5236}
.intel-analysis-card p{color:#274d70;font-size:14px;line-height:1.8;margin:0}
.analysis-partition{margin-top:26px;border-top:2px dashed #c4d7e8;padding-top:14px}
.watch-partition{margin-top:8px}
.intel-badge.m-e0_stub{background:#f1f2f4;color:#7b8794;border-color:#dde1e6}
.intel-badge.m-e1_basic{background:#f2f6f9;color:#54708a;border-color:#d5e0ea}
.intel-badge.m-e2_developed{background:#e8f2ec;color:#3f6f52;border-color:#cde3d4}
.intel-badge.m-e3_full_encyclopedia{background:#e7f0fa;color:#14507e;border-color:#c3d9ee}
.intel-badge.m-r0_edge_only{background:#f1f2f4;color:#7b8794;border-color:#dde1e6}
.intel-badge.m-r1_basic{background:#f2f6f9;color:#54708a;border-color:#d5e0ea}
.intel-badge.m-r2_developed_relationship{background:#e8f2ec;color:#3f6f52;border-color:#cde3d4}
.intel-badge.m-r3_full_relationship_intelligence{background:#e7f0fa;color:#14507e;border-color:#c3d9ee}
"""
text = css.read_text(encoding="utf-8")
if "DEPTH A" not in text:
    css.write_text(text.rstrip() + "\n" + block, encoding="utf-8")
    print("CSS appended")
else:
    print("already present")
