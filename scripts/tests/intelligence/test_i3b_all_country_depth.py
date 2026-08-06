#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-B: all 13 countries must meet deep-country standard."""
import json
import re
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
    profiles = load("country_profiles.json")["profiles"]
    countries = load("countries.json")["countries"]
    entities = load("entities.json")["entities"]
    eids = {e["entity_id"] for e in entities}
    cids = {c["country_id"] for c in countries}
    deep = {cid: pr for cid, pr in profiles.items() if pr.get("depth") == "deep"}

    check("all 13 countries are deep", len(deep) == 13, str(len(deep)))
    for cid in ("country-mali", "country-burkina-faso", "country-cameroon",
                "country-ethiopia", "country-tanzania"):
        check(f"{cid} is deep", cid in deep)

    for cid, pr in deep.items():
        secs = pr.get("sections", {})
        body = sum(text_len(v) for k, v in secs.items() if k != "lead")
        lead = pr.get("lead")
        substantive = sum(1 for k, v in secs.items()
                          if k not in ("sources", "notes", "regional_belonging", "risk_assessment")
                          and (text_len(v) >= 100 or len(paras(v)) >= 2))
        check(f"{cid}: body >= 2500", body >= 2500, str(body))
        check(f"{cid}: substantive sections >= 10", substantive >= 10, str(substantive))
        check(f"{cid}: lead 2-4 paras", isinstance(lead, list) and 2 <= len(lead) <= 4)
        c = next((x for x in countries if x["country_id"] == cid), None)
        if c:
            check(f"{cid}: claim_valid_as_of", bool(c.get("claim_valid_as_of")))
            check(f"{cid}: freshness not unknown", c.get("freshness_status") not in ("unknown",))
        bad = []
        for k, v in secs.items():
            for p in paras(v):
                for m in re.finditer(r"\[\[(entity|country|region|relation):([^|\]]+)\|", str(p)):
                    kind, ref = m.group(1), m.group(2)
                    ok = {"entity": eids, "country": cids, "region": set(), "relation": set()}.get(kind, set())
                    if ref not in ok:
                        bad.append(f"{kind}:{ref}")
        check(f"{cid}: links resolve", not bad, str(bad[:4]))

    if FAIL:
        sys.exit(1)
    print(f"\nI3-B all-country depth: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
