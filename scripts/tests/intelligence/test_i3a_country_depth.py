#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-A: deep country content depth tests.

Verifies the 8 deep country profiles have substantive encyclopedia content:
>=2500 body chars, >=8 substantive sections, lead paragraphs, freshness fields,
and resolvable entity links.
"""
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

    # 1. five newly deepened countries are deep
    for cid in ("country-nigeria", "country-libya", "country-south-sudan", "country-niger", "country-benin"):
        check(f"{cid} is deep", cid in deep)
    # 2. chad/sudan/mozambique keep deep standard
    for cid in ("country-chad", "country-sudan", "country-mozambique"):
        check(f"{cid} keeps deep", cid in deep)
    # 3. at least 8 deep countries total
    check("deep countries >= 8", len(deep) >= 8, str(len(deep)))

    for cid, pr in deep.items():
        secs = pr.get("sections", {})
        body = sum(text_len(v) for k, v in secs.items() if k != "lead")
        lead = pr.get("lead") or secs.get("lead")
        substantive = sum(1 for k, v in secs.items() if text_len(v) >= 100 or len(paras(v)) >= 2)
        check(f"{cid}: body >= 2500 chars", body >= 2500, f"body={body}")
        check(f"{cid}: >= 8 substantive sections", substantive >= 8, f"n={substantive}")
        check(f"{cid}: has lead (2-4 paras)", isinstance(lead, list) and 2 <= len(lead) <= 4, str(len(lead) if isinstance(lead, list) else 0))
        # freshness semantics
        c = next((x for x in countries if x["country_id"] == cid), None)
        if c:
            check(f"{cid}: claim_valid_as_of present", bool(c.get("claim_valid_as_of")), str(c.get("claim_valid_as_of")))
            check(f"{cid}: current_status_verified_at present", bool(c.get("current_status_verified_at")))
            check(f"{cid}: freshness valid", c.get("freshness_status") in ("current", "aging", "stale", "historical", "unknown"))
            check(f"{cid}: record_reviewed_at != 事实有效截至 (semantic separation)",
                  str(c.get("record_reviewed_at")) != str(c.get("claim_valid_as_of")))
        # in-text links resolve
        bad = []
        for k, v in secs.items():
            for p in paras(v):
                for m in re.finditer(r"\[\[(entity|country|region|relation):([^|\]]+)\|", str(p)):
                    kind, ref = m.group(1), m.group(2)
                    if kind == "entity" and ref not in eids:
                        bad.append(ref)
                    elif kind == "country" and ref not in cids:
                        bad.append(ref)
        check(f"{cid}: entity links resolve", not bad, str(sorted(set(bad))[:5]))

    if FAIL:
        sys.exit(1)
    print(f"\nI3-A country depth: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
