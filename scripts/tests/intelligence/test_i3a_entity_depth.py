#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-A: entity profile depth tests.

Verifies encyclopedia_full >= 12, standard >= 18, basic <= 10; and that depth
fields are backed by real content (sections/chars thresholds).
"""
import json
import sys
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


def text_len(v):
    if isinstance(v, str):
        return len(v)
    if isinstance(v, list):
        return sum(len(str(x)) for x in v)
    if isinstance(v, dict):
        n = 0
        if v.get("p"):
            n += sum(len(str(x)) for x in v["p"])
        if v.get("list"):
            n += sum(len(str(x)) for x in v["list"])
        if v.get("table"):
            for row in v["table"].get("rows", []):
                n += sum(len(str(x)) for x in row)
        return n
    return 0


def sec_count(sections):
    return sum(1 for k, v in sections.items() if text_len(v) > 0)


def main():
    profiles = load("entity_profiles.json")["profiles"]
    entities = load("entities.json")["entities"]
    eids = {e["entity_id"] for e in entities}
    depths = {}
    for eid, pr in profiles.items():
        if eid not in eids:
            continue
        d = pr.get("profile_depth")
        secs = pr.get("sections", {})
        body = sum(text_len(v) for v in secs.values())
        n = sec_count(secs)
        depths[eid] = (d, n, body)
    cnt = {}
    for d, _, _ in depths.values():
        cnt[d] = cnt.get(d, 0) + 1
    check("encyclopedia_full >= 12", cnt.get("encyclopedia_full", 0) >= 12, str(cnt))
    check("standard >= 18", cnt.get("standard", 0) >= 18, str(cnt))
    check("basic <= 10", cnt.get("basic", 0) <= 10, str(cnt))
    check("depth counts cover all entities", sum(cnt.values()) == len(eids), f"{sum(cnt.values())} vs {len(eids)}")

    # depth must be backed by content (I3-D1/D2 packet-imported profiles carry externally
    # confirmed content; their depth target comes from the pack, so the char-count gate
    # is not applied to imported_by=i3d*, matching the build generator)
    for eid, (d, n, body) in depths.items():
        imported = str(profiles.get(eid, {}).get("imported_by", "")).startswith("i3d")
        if d == "encyclopedia_full":
            check(f"{eid}: encyclopedia content (>=8 secs, >=1800 chars)", imported or (n >= 8 and body >= 1800), f"secs={n}, chars={body}")
        elif d == "standard":
            check(f"{eid}: standard content (>=5 secs, >=900 chars)", imported or (n >= 5 and body >= 900), f"secs={n}, chars={body}")
        elif d == "basic":
            e = next((x for x in entities if x["entity_id"] == eid), None)
            check(f"{eid}: basic has sources", bool(e and e.get("source_refs")))

    # no empty sections anywhere
    empty = []
    for eid, pr in profiles.items():
        for k, v in pr.get("sections", {}).items():
            if not text_len(v):
                empty.append(f"{eid}:{k}")
    check("no empty sections in entity profiles", not empty, str(empty[:5]))

    if FAIL:
        sys.exit(1)
    print(f"\nI3-A entity depth: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
