#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I2-B: relation ontology tests.

Verifies relation_types.json registry completeness and that
pledged_allegiance_to exists as an independent type, is used in the data, and
is not conflated with affiliated_with.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "africa"

PASS = FAIL = 0
REQUIRED_FIELDS = ["relation_type", "label_zh", "label_en", "definition", "direction",
                   "reciprocal", "time_sensitive", "evidence_requirement", "graph_style",
                   "common_confusion", "example"]


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  ({detail})")


def main():
    registry = json.loads((DATA / "relation_types.json").read_text(encoding="utf-8"))
    rtypes = registry["relation_types"]
    by_type = {t["relation_type"]: t for t in rtypes}

    check("registry schema", registry.get("schema_version") == "asip-relation-ontology-v1")
    check("registry count >= 20", len(rtypes) >= 20, str(len(rtypes)))
    check("pledged_allegiance_to present", "pledged_allegiance_to" in by_type)
    check("affiliated_with present", "affiliated_with" in by_type)
    check("constituent_of present", "constituent_of" in by_type)
    check("led_by present", "led_by" in by_type)
    for t in rtypes:
        for f in REQUIRED_FIELDS:
            check(f"{t['relation_type']}.{f}", f in t and t[f] not in (None, ""))
        check(f"{t['relation_type']} label_zh", bool(t["label_zh"]))
        check(f"{t['relation_type']} definition", bool(t["definition"]))

    pledge = by_type["pledged_allegiance_to"]
    affil = by_type["affiliated_with"]
    check("pledge label distinct", pledge["label_zh"] != affil["label_zh"],
          f"{pledge['label_zh']} vs {affil['label_zh']}")
    check("pledge definition distinct", pledge["definition"] != affil["definition"])
    check("pledge directed", pledge["direction"] == "directed")
    check("pledge time_sensitive", pledge["time_sensitive"] is True)

    # data layer usage
    rels = json.loads((DATA / "relationships.json").read_text(encoding="utf-8"))["relationships"]
    used_types = {r["relationship_type"] for r in rels}
    for ut in used_types:
        check(f"used type in registry: {ut}", ut in by_type)
    pledge_rels = [r for r in rels if r["relationship_type"] == "pledged_allegiance_to"]
    check("pledged_allegiance_to used in data", len(pledge_rels) >= 3, str(len(pledge_rels)))
    affil_rels = [r for r in rels if r["relationship_type"] == "affiliated_with"]
    # no relation that is a known pledge still carries affiliated_with
    known_pledges = {"rel-iswap-islamic-state-affiliation", "rel-is-moz-islamic-state",
                     "rel-isis-libya-affiliation", "rel-jnim-alqaida-affiliate"}
    for r in affil_rels:
        check(f"known pledge not conflated: {r['relationship_id']}",
              r["relationship_id"] not in known_pledges)
    for r in pledge_rels:
        check(f"pledge has semantics note {r['relationship_id']}",
              bool(r.get("relationship_semantics_note")) or "宣誓效忠" in r.get("relation_summary", ""))

    print(f"\ntest_relation_ontology: PASS={PASS} FAIL={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
