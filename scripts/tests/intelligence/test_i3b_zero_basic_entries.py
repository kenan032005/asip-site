#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-B: zero basic entries; encyclopedia >= 18; every entity at least standard."""
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
        depths[eid] = (d, sec_count(secs), sum(text_len(v) for v in secs.values()))
    cnt = {}
    for d, _, _ in depths.values():
        cnt[d] = cnt.get(d, 0) + 1
    check("basic_entry_count == 0", cnt.get("basic", 0) == 0, str(cnt))
    check("encyclopedia_full >= 18", cnt.get("encyclopedia_full", 0) >= 18, str(cnt))
    check("all entities at least standard", cnt.get("basic", 0) == 0 and sum(cnt.values()) == len(eids))
    check("no new empty shells: new entities standard or above",
          all(d in ("standard", "encyclopedia_full") for eid, (d, _, _) in depths.items() if eid.startswith(("actor-mali-army", "actor-burkina-army", "actor-vdp", "actor-cameroon-bir", "actor-ambazonia-network", "actor-endf", "actor-fano", "actor-ola", "actor-tanzania-tpdf", "actor-tdf"))))
    # depth backed by content (I3-D1/D2 packet-imported profiles exempt, matching generator)
    for eid, (d, n, body) in depths.items():
        imported = str(profiles.get(eid, {}).get("imported_by", "")).startswith("i3d")
        if d == "encyclopedia_full":
            check(f"{eid}: ency content", imported or (n >= 8 and body >= 1800), f"secs={n}, chars={body}")
        elif d == "standard":
            check(f"{eid}: std content", imported or (n >= 5 and body >= 900), f"secs={n}, chars={body}")
    if FAIL:
        sys.exit(1)
    print(f"\nI3-B zero-basic / depth: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
