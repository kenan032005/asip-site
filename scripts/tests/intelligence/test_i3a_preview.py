#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-A: preview & build contract tests — dist routes exist for deep countries,
priority entities, deepened relations and the graph; assets embed latest JS."""
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


def main():
    dist = ROOT / "dist" / "intelligence" / "africa"
    countries = load("countries.json")["countries"]
    entities = load("entities.json")["entities"]
    rels = load("relationships.json")["relationships"]
    by_slug = {e["slug"]: e for e in entities}
    c_by_slug = {c["slug"]: c for c in countries}
    r_by_id = {r["relationship_id"]: r for r in rels}

    deep_cids = {"country-nigeria", "country-libya", "country-south-sudan", "country-niger",
                 "country-benin", "country-chad", "country-sudan", "country-mozambique"}
    missing = []
    for c in countries:
        if c["country_id"] in deep_cids:
            p = dist / "country" / c["slug"] / "index.html"
            if not p.exists():
                missing.append(c["slug"])
    check("dist: deep country pages built", not missing, str(missing))

    prio = ("actor-jas", "actor-iswap", "actor-mnjtf", "actor-nigeria-army", "actor-lna",
            "actor-gnu-forces", "actor-isis-libya", "actor-sspdf", "actor-splm-io", "actor-nas",
            "person-salva-kiir", "person-riek-machar", "actor-benin-forces")
    missing = []
    for eid in prio:
        e = next((x for x in entities if x["entity_id"] == eid), None)
        if e:
            p = dist / "entity" / e["slug"] / "index.html"
            if not p.exists():
                missing.append(e["slug"])
    check("dist: priority entity pages built", not missing, str(missing))

    deep_rels = ("rel-jas-iswap-conflict", "rel-iswap-islamic-state-affiliation",
                 "rel-jnim-niger-operates", "rel-is-niger-operates", "rel-jnim-is-hostile",
                 "rel-lna-gnu-rivalry", "rel-isis-libya-affiliation", "rel-splm-io-sspdf-conflict",
                 "rel-kiir-sspdf-leads", "rel-machar-splm-io-leads", "rel-nas-splm-io-allied",
                 "rel-nigeria-mnjtf-member")
    missing = []
    for rid in deep_rels:
        r = r_by_id.get(rid)
        slug = (r or {}).get("slug", rid)
        p = dist / "relation" / slug / "index.html"
        if not p.exists():
            missing.append(slug)
    check("dist: deepened relation pages built", not missing, str(missing))

    check("dist: network page built", (dist / "network" / "index.html").exists())
    check("dist: data files copied", (dist / "data" / "catalog_metrics.json").exists()
          and (dist / "data" / "relation_types.json").exists())

    # JS bundles contain the new render features (lead/toc/table) and new labels
    js = (ROOT / "assets" / "js" / "intelligence" / "africa.js").read_text(encoding="utf-8")
    for token in ("profile-lead", "intel-toc", "intel-table", "最近三至五年的重要变化", "对人员、企业和项目安全的影响",
                  "pledged_allegiance_to", "core_assessment", "name_and_translation"):
        check(f"africa.js contains {token[:24]}", token in js)

    if FAIL:
        sys.exit(1)
    print(f"\nI3-A preview contract: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
