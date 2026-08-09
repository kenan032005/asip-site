#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH E source probe: check existing sources for matches against the 10 packet candidates."""
import json, re
from pathlib import Path

DATA = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-depth-e/data/intelligence/africa")
PACK = Path("C:/Users/kenan/Downloads/ASIP_Depth_E_Ethiopia_Content_Pack.json")

srcs = json.load(open(DATA / "sources.json", encoding="utf-8"))["sources"]
pack = json.load(open(PACK, encoding="utf-8"))

def norm(u):
    if not u:
        return ""
    u = u.strip().rstrip("/")
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.lower()

by_url = {norm(s.get("url", "")): s["source_id"] for s in srcs if s.get("url")}
by_pub = {}
for s in srcs:
    by_pub.setdefault((s.get("publisher", "").lower().strip(), s.get("title", "").lower().strip()), s["source_id"])
by_rec = {}
for s in srcs:
    m = re.search(r"digitallibrary\.un\.org/record/(\d+)", s.get("url", "") or "")
    if m:
        by_rec.setdefault("un-record/" + m.group(1), s["source_id"])

print("candidate -> match")
for ps in pack["sources"]:
    pid = ps["source_id"]
    nu = norm(ps.get("url") or "")
    match, how = None, None
    if nu and nu in by_url:
        match, how = by_url[nu], "url_exact"
    elif nu:
        m = re.search(r"digitallibrary\.un\.org/record/(\d+)", nu)
        if m and ("un-record/" + m.group(1)) in by_rec:
            match, how = by_rec["un-record/" + m.group(1)], "un_record"
    if match is None:
        k = (ps.get("publisher", "").lower().strip(), ps.get("title", "").lower().strip())
        if k in by_pub:
            match, how = by_pub[k], "publisher_title"
    print(f"  {pid} -> {match or 'NEW'} | {how or ''}")
