#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXPANSION_B dedicated gate tests.

Checks the Expansion B package invariants:
- 11 new entities exist, all encyclopedia_full, thickness floors met
- carry-over person-abdirahman-fahiye upgraded to encyclopedia_full
- 17 new relationships exist; 8 core dossiers are R3 with timelines
- special modeling rules (Puntland umbrella label, MONUSCO civilian-protection
  framing, BBMB-IRGC attribution, no branch_of for Lakurawa)
- STANDARD_FINAL_ENTITY_COUNT = 0 for Expansion-B-touched entities
- source/evidence integrity for new records
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


def main():
    entities = load("entities.json")["entities"]
    rels = load("relationships.json")["relationships"]
    ep = load("entity_profiles.json")["profiles"]
    rp = load("relation_profiles.json")["profiles"]
    rt = load("relation_timelines.json")["timelines"]
    sources = load("sources.json")["sources"]
    evidence = load("evidence_records.json")["evidence"]

    eids = {e["entity_id"] for e in entities}
    rids = {r["relationship_id"] for r in rels}
    sids = {s["source_id"] for s in sources}
    R3 = "R3_FULL_RELATIONSHIP_INTELLIGENCE"

    NEW_ENT = ["actor-aussom", "actor-somali-national-armed-forces", "actor-puntland-security-forces",
               "actor-fardc", "actor-updf", "actor-monusco", "actor-irgc",
               "person-mahad-karate", "person-abdiweli-mohamed-yusuf", "person-meddie-nkalubo",
               "person-abu-zaid-talha"]
    NEW_REL = ["rel-expb-shabaab-aussom-conflict", "rel-expb-shabaab-snaf-conflict",
               "rel-expb-aussom-snaf-cooperation", "rel-expb-isis-somalia-puntland-conflict",
               "rel-expb-shabaab-karate-led", "rel-expb-isis-somalia-yusuf-led",
               "rel-expb-mumin-yusuf-reporting", "rel-expb-fahiye-yusuf-reporting",
               "rel-expb-adf-fardc-conflict", "rel-expb-adf-updf-conflict",
               "rel-expb-fardc-updf-shujaa", "rel-expb-monusco-adf-countering",
               "rel-expb-monusco-fardc-cooperation", "rel-expb-adf-nkalubo-led",
               "rel-expb-bbmb-irgc-support", "rel-expb-bbmb-talha-led", "rel-expb-talha-saf-allied"]
    R3_REL = ["rel-expb-shabaab-aussom-conflict", "rel-expb-shabaab-snaf-conflict",
              "rel-expb-aussom-snaf-cooperation", "rel-expb-isis-somalia-puntland-conflict",
              "rel-expb-adf-fardc-conflict", "rel-expb-adf-updf-conflict",
              "rel-expb-fardc-updf-shujaa", "rel-expb-bbmb-irgc-support"]

    # 1. entity presence + depth + thickness
    for eid in NEW_ENT:
        check(f"entity present {eid}", eid in eids)
        pr = ep.get(eid)
        check(f"profile present {eid}", pr is not None)
        if pr:
            secs = pr.get("sections", {})
            n = sum(1 for k, v in secs.items() if text_len(v) > 0)
            body = sum(text_len(v) for v in secs.values())
            need = 1800 if eid.startswith("actor-") else 1500
            need_n = 14 if eid.startswith("actor-") else 12
            check(f"depth encyclopedia {eid}", pr.get("profile_depth") == "encyclopedia_full", pr.get("profile_depth"))
            check(f"thickness {eid}", n >= need_n and body >= need, f"secs={n} chars={body}")

    # 2. carry-over fahiye upgraded
    pr = ep.get("person-abdirahman-fahiye")
    check("fahiye profile exists", pr is not None)
    if pr:
        check("fahiye encyclopedia_full", pr.get("profile_depth") == "encyclopedia_full", pr.get("profile_depth"))
        secs = pr.get("sections", {})
        body = sum(text_len(v) for v in secs.values())
        check("fahiye >=1500 chars", body >= 1500, body)

    # 3. ansaru / lakurawa remain encyclopedia_full (carry-over)
    for eid in ("actor-ansaru", "actor-lakurawa"):
        pr = ep.get(eid)
        check(f"carry-over depth {eid}", pr is not None and pr.get("profile_depth") == "encyclopedia_full")

    # 4. STANDARD_FINAL_ENTITY_COUNT = 0 for Expansion-B-touched entities
    touched = set(NEW_ENT) | {"person-abdirahman-fahiye", "actor-ansaru", "actor-lakurawa"}
    std = [eid for eid in touched if ep.get(eid, {}).get("profile_depth") == "standard"]
    check("STANDARD_FINAL_ENTITY_COUNT = 0", len(std) == 0, str(std))

    # 5. relationships
    for rid in NEW_REL:
        check(f"relation present {rid}", rid in rids)
        pr = rp.get(rid)
        check(f"relation profile {rid}", pr is not None)
        if pr and rid in R3_REL:
            check(f"R3 maturity {rid}", pr.get("relation_maturity") == R3, pr.get("relation_maturity"))
            tl = rt.get(rid, [])
            check(f"R3 timeline {rid}", len(tl) >= 3, f"{len(tl)} items")

    # 6. special modeling rules
    laku = [r for r in rels if r["source_entity_id"] == "actor-lakurawa" and r["relationship_type"] == "branch_of"]
    check("no branch_of edges for lakurawa", len(laku) == 0)
    monadf = rp.get("rel-expb-monusco-adf-countering", {})
    mon_txt = json.dumps(monadf, ensure_ascii=False)
    check("MONUSCO civilian-protection framing", "平民保护" in mon_txt or "保护" in mon_txt)
    check("MONUSCO not belligerent framing", "不是武装冲突方" in mon_txt and "敌对方" not in mon_txt)
    punt = json.dumps(ep.get("actor-puntland-security-forces", {}).get("sections", {}), ensure_ascii=False)
    check("Puntland umbrella-label caveat", "集合标签" in punt or "行动层面集合" in punt)
    irgc = json.dumps(rp.get("rel-expb-bbmb-irgc-support", {}), ensure_ascii=False) + \
           json.dumps(ep.get("actor-irgc", {}).get("sections", {}), ensure_ascii=False)
    check("BBMB-IRGC attribution preserved", "美国财政部" in irgc or "U.S. Treasury" in irgc)
    check("BBMB-IRGC no command/control inferred", "指挥" not in irgc.split("作战指挥")[0] or "不推导" in irgc or "不得推导" in irgc or "不推断" in irgc)
    updf_txt = json.dumps(ep.get("actor-updf", {}).get("sections", {}), ensure_ascii=False)
    check("UPDF claims attributed", "UPDF 官方" in updf_txt or "官方陈述" in updf_txt)

    # 7. source/evidence integrity
    expb_srcs = [s for s in sources if s["source_id"].startswith("expb-")]
    check("expb- sources registered (>=16)", len(expb_srcs) >= 16, len(expb_srcs))
    expb_ev = [e for e in evidence if e["evidence_id"].startswith("ev-expb-")]
    check("expb- evidence imported (>=17)", len(expb_ev) >= 17, len(expb_ev))
    dangling = []
    for r in rels:
        for sid in r.get("source_refs", []):
            if sid not in sids:
                dangling.append((r["relationship_id"], sid))
    for e in evidence:
        if e["source_id"] not in sids:
            dangling.append((e["evidence_id"], e["source_id"]))
    check("no dangling source refs", not dangling, dangling[:5])
    v = sum(1 for e in evidence if e["verification_status"] == "verified")
    check("verified ratio < 0.80", v / len(evidence) < 0.80, round(v / len(evidence), 4))

    # 8. counts
    check("entities=102", len(entities) == 102, len(entities))
    check("relationships=192", len(rels) == 192, len(rels))

    if FAIL:
        sys.exit(1)
    print(f"\nEXPANSION_B_GATE: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
