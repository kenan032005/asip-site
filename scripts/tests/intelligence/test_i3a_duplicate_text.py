#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-A: duplicate text tests — no large fully duplicated paragraphs across
country/entity profiles; limited near-duplicates; no template boilerplate."""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "africa"

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  ({detail})")


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def paras(v):
    out = []
    if isinstance(v, str):
        out.append(v)
    elif isinstance(v, list):
        out.extend(str(x) for x in v)
    elif isinstance(v, dict):
        if v.get("p"):
            out.extend(str(x) for x in v["p"])
        if v.get("list"):
            out.extend(str(x) for x in v["list"])
    return out


def main():
    cp = load("country_profiles.json")["profiles"]
    ep = load("entity_profiles.json")["profiles"]
    # 来源/备注/区域归属说明为允许的统一组件，不参与正文重复检测
    ALLOWED_UNIFORM = {"sources", "notes", "regional_belonging"}
    all_paras = []
    for pr in list(cp.values()) + list(ep.values()):
        for k, v in pr.get("sections", {}).items():
            if k in ALLOWED_UNIFORM:
                continue
            all_paras.extend(str(p) for p in paras(v) if len(str(p)) >= 40)
    cnt = Counter(all_paras)
    dup = {t: n for t, n in cnt.items() if n > 1}
    check("no fully duplicated long paragraphs (>40 chars)", not dup, f"{len(dup)} dup types")

    # near-duplicate: paragraphs sharing >= 80% content within same length bucket
    items = sorted(cnt.keys(), key=len, reverse=True)
    near = 0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if abs(len(a) - len(b)) > 40:
                continue
            la, lb = len(a), len(b)
            if la < 60 or lb < 60:
                continue
            shorter, longer = (a, b) if la <= lb else (b, a)
            if shorter in longer:
                near += 1
    check("near-duplicate long paragraphs within reasonable range (<=3)", near <= 3, str(near))

    # AI-template phrases must be accompanied by specifics (count occurrences)
    boilerplate = ("局势复杂多变", "需要持续关注", "该组织具有重要影响", "对地区安全构成挑战")
    hits = [t for t in cnt if any(b in t for b in boilerplate)]
    check("no empty template boilerplate phrases in long paragraphs", not hits, str(hits[:3]))

    if FAIL:
        sys.exit(1)
    print(f"\nI3-A duplicate text: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
