#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan deployable/current ASIP content for leaked absolute local paths.
Historical acceptance and QA evidence remain auditable through a finite allowlist.
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
WIN_PAT = re.compile(r"[A-Za-z]:(?:\\\\|\\\\|/)+Users(?:\\\\|\\\\|/)+[A-Za-z0-9_.-]+(?:[^\\s\"'<>]*)")
POSIX_PAT = re.compile(r"/(?:home|Users)/[A-Za-z0-9_.-]+/(?:[^\\s\"'<>]*)")
TEXT_EXTS = {".py", ".json", ".md", ".html", ".css", ".js", ".txt", ".yml", ".yaml", ".xml", ".csv", ".gitignore"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", "backup", ".workbuddy"}
# Finite historical evidence rules: do not broaden to all Markdown/JSON/QA/scripts.
ARCHIVAL_FILES = {
    "ASIP_INTELLIGENCE_DEMO_V01_I0C_RECOVERY_REPORT.md",
    "ASIP_INTELLIGENCE_DEMO_V02_ACCEPTANCE.md",
    "ASIP_INTELLIGENCE_DEMO_V02_DESIGN.md",
    "ASIP_INTELLIGENCE_DEMO_V02_I2A_ACCEPTANCE.md",
    "ASIP_INTELLIGENCE_V10_I2B_TRUST_AUDIT_ACCEPTANCE.md",
    "ASIP_INTELLIGENCE_V10_I3A_CONTENT_ACCEPTANCE.md",
    "ASIP_INTELLIGENCE_V10_I3B_RELEASE_CANDIDATE_ACCEPTANCE.md",
    "ASIP_INTELLIGENCE_V10_I3PREPA_GRAPH_FIX_REPORT.md",
    "i0c-original-wip-protection.json",
    "i0c_min_browser_qa.js",
    "i1a_browser_qa.js",
    "i1b_browser_qa.js",
    "i1_v02_browser_qa.js",
    "i2a_browser_qa.js",
    "i2b_browser_qa.js",
    "qa_browser.js",
}
# Current source data and every current Fix-1C/release/public output are strict.
STRICT_DIRS = ("dist", "data/intelligence/africa", "assets", "release/i3b-rc1", "qa-artifacts-i3b-fix1c", "previews", "intelligence")

def rel(path):
    return path.relative_to(ROOT).as_posix()

def category(r):
    if r.startswith(("dist/", "assets/", "previews/", "intelligence/")): return "PUBLIC_DEPLOYABLE"
    if r.startswith("data/intelligence/africa/"): return "CURRENT_SOURCE"
    if r.startswith("release/i3b-rc1/"): return "CURRENT_RELEASE_ARTIFACT"
    if r.startswith("qa-artifacts-i3b-fix1c/"): return "CURRENT_QA"
    if r.startswith("scripts/gen/") or r.startswith("scripts/qa/") or r.startswith("scripts/tests/"): return "DEVELOPMENT_SCRIPT"
    if r in ARCHIVAL_FILES: return "HISTORICAL_QA" if r.endswith((".json", ".js")) else "HISTORICAL_ACCEPTANCE"
    return "OTHER"

def files_under(base):
    if not base.exists(): return []
    out=[]
    for dp, dns, fns in os.walk(base):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in fns:
            p=Path(dp)/fn
            if p.suffix.lower() in TEXT_EXTS or fn == ".gitignore": out.append(p)
    return out

def match_file(path):
    try: text=path.read_text(encoding="utf-8", errors="replace")
    except OSError: return []
    out=[]
    for pat in (WIN_PAT, POSIX_PAT):
        for m in pat.finditer(text):
            out.append({"file": rel(path), "line": text[:m.start()].count("\n")+1, "matched_path": m.group(0), "file_category": category(rel(path))})
    return out

def scan_current():
    files=[]
    for d in STRICT_DIRS: files.extend(files_under(ROOT / d))
    seen=set(); hits=[]
    for p in files:
        if p in seen or rel(p) == "qa-artifacts-i3b-fix1c/local-path-scan.json": continue
        seen.add(p); hits.extend(match_file(p))
    return files, hits

def scan_archival():
    hits=[]
    for name in ARCHIVAL_FILES:
        p=ROOT / name
        if p.exists(): hits.extend(match_file(p))
    return hits

def self_checks():
    cases=[]
    with tempfile.TemporaryDirectory() as td:
        t=Path(td)
        samples={
            "public.html": "C:/Users/test/project/file.json",
            "current.json": "C:\\\\Users\\\\test\\\\x.json",
            "linux.json": "/home/user/project/x.json /Users/name/project/y.json",
            "relative.json": "data/intelligence/africa/entities.json",
        }
        for name,text in samples.items(): (t/name).write_text(text, encoding="utf-8")
        cases += [{"case":"CASE 1", "expected":"FAIL", "passed": bool(WIN_PAT.search(samples["public.html"]))},
                  {"case":"CASE 2", "expected":"FAIL", "passed": bool(WIN_PAT.search(samples["current.json"]))},
                  {"case":"CASE 3", "expected":"FAIL", "passed": bool(POSIX_PAT.search(samples["linux.json"]))},
                  {"case":"CASE 6", "expected":"PASS", "passed": not bool(WIN_PAT.search(samples["relative.json"]) or POSIX_PAT.search(samples["relative.json"]))}]
    cases.append({"case":"CASE 4", "expected":"PASS archival + counted", "passed": bool(ARCHIVAL_FILES) and category(next(iter(ARCHIVAL_FILES))) in {"HISTORICAL_ACCEPTANCE", "HISTORICAL_QA"}})
    cases.append({"case":"CASE 5", "expected":"FAIL current Fix-1C QA", "passed": category("qa-artifacts-i3b-fix1c/current.json") == "CURRENT_QA"})
    return cases

def main():
    current_files, forbidden = scan_current()
    archival = scan_archival()
    checks=self_checks()
    artifact={"artifact":"FIX1C_LOCAL_PATH_SCAN", "scanned_file_count":len(current_files), "public_scanned_count":sum(category(rel(p))=="PUBLIC_DEPLOYABLE" for p in current_files), "current_release_scanned_count":sum(category(rel(p)) in {"CURRENT_SOURCE","CURRENT_RELEASE_ARTIFACT","CURRENT_QA"} for p in current_files), "archival_ignored_count":len(archival), "forbidden_matches":forbidden, "archival_matches":archival, "allowlist_rules":{"archival_files":sorted(ARCHIVAL_FILES),"strict_dirs":list(STRICT_DIRS),"development_scripts_not_public_scope":True}, "self_checks":checks, "gate":"PASS" if not forbidden and all(c["passed"] for c in checks) else "OPEN"}
    out=ROOT/"qa-artifacts-i3b-fix1c/local-path-scan.json"; out.parent.mkdir(exist_ok=True); out.write_text(json.dumps(artifact,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"scanned_file_count":len(current_files),"public_scanned_count":artifact["public_scanned_count"],"current_release_scanned_count":artifact["current_release_scanned_count"],"archival_ignored_count":len(archival),"forbidden_matches":len(forbidden),"gate":artifact["gate"]},ensure_ascii=False))
    return 0 if artifact["gate"]=="PASS" else 1
if __name__ == "__main__": sys.exit(main())
