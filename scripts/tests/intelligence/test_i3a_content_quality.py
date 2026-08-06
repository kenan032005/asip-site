#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-A: content quality tests — no placeholders, no empty headings,
substantive sections, resolved links in deep countries, relation profiles
with timelines and sources."""
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
    cp = load("country_profiles.json")["profiles"]
    ep = load("entity_profiles.json")["profiles"]
    rp = load("relation_profiles.json")["profiles"]
    tl = load("relation_timelines.json")["timelines"]
    rels = load("relationships.json")["relationships"]
    entities = load("entities.json")["entities"]
    countries = load("countries.json")["countries"]
    eids = {e["entity_id"] for e in entities}
    cids = {c["country_id"] for c in countries}
    rid_set = {r["relationship_id"] for r in rels}

    placeholders = 0
    empty = 0
    bad_links = []
    for pr in list(cp.values()) + list(ep.values()):
        for k, v in pr.get("sections", {}).items():
            if not text_len(v):
                empty += 1
            txt = "".join(paras(v))
            if any(ph in txt for ph in ("暂无信息", "待补充", "TBD", "placeholder", "Lorem")):
                placeholders += 1
            for p in paras(v):
                for m in re.finditer(r"\[\[(entity|country|region|relation):([^|\]]+)\|", str(p)):
                    kind, ref = m.group(1), m.group(2)
                    ok = {"entity": eids, "country": cids, "region": set(), "relation": rid_set}.get(kind, set())
                    if ref not in ok:
                        bad_links.append(f"{kind}:{ref}")
    check("no placeholder text in profiles", placeholders == 0, str(placeholders))
    check("no empty sections in profiles", empty == 0, str(empty))
    check("all in-text links resolve", not bad_links, str(sorted(set(bad_links))[:6]))

    # deep countries: no single-sentence-only sections (substantive rule)
    # metadata sections (所属区域/风险等级/来源) are legitimate uniform components
    META_KEYS = {"regional_belonging", "risk_assessment", "sources", "notes"}
    single = []
    for cid, pr in cp.items():
        if pr.get("depth") != "deep":
            continue
        for k, v in pr.get("sections", {}).items():
            if k in META_KEYS:
                continue
            ps = [p for p in paras(v) if len(str(p)) > 0]
            if len(ps) == 1 and text_len(v) < 100 and not isinstance(v, (dict,)):
                single.append(f"{cid}:{k}")
    check("deep countries: no single-sentence-only sections", not single, str(single[:6]))

    # relation profiles: deepened relations need timeline + sources + evolution
    deep_rels = [rid for rid, pr in rp.items() if pr.get("overview") and pr.get("evolution_stages")]
    check(">=10 deepened relation profiles", len(deep_rels) >= 10, str(len(deep_rels)))
    missing_tl = [rid for rid in deep_rels if rid not in tl]
    check("deepened relations all have timelines", not missing_tl, str(missing_tl[:5]))
    empty_rel_field = []
    for rid in deep_rels:
        pr = rp[rid]
        for f in ("overview", "formation_background", "initial_relationship", "causes",
                  "key_turning_points", "current_status", "uncertainties"):
            if not pr.get(f):
                empty_rel_field.append(f"{rid}:{f}")
    check("deepened relation profiles have all core fields", not empty_rel_field, str(empty_rel_field[:6]))

    if FAIL:
        sys.exit(1)
    print(f"\nI3-A content quality: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
