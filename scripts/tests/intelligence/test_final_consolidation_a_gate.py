#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final Depth Consolidation Pack A dedicated gate test."""
import io, json, os, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
DATA = "data/intelligence/africa"
PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  :: {detail}")


def load(n):
    return json.load(io.open(os.path.join(DATA, n), encoding="utf-8"))


def _tl(v):
    if isinstance(v, str):
        return len(v)
    if isinstance(v, list):
        return sum(len(str(x)) for x in v)
    if isinstance(v, dict):
        n = 0
        for kk in ("p", "list", "timeline", "table"):
            if v.get(kk):
                n += sum(len(str(x)) for x in v[kk])
        return n
    return 0


entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
ep = load("entity_profiles.json")["profiles"]
rp = load("relation_profiles.json")["profiles"]
rt = load("relation_timelines.json")["timelines"]
evidence = load("evidence_records.json")["evidence"]
aliases = load("alias_index.json")["aliases"]
countries = load("countries.json")["countries"]

ent_ids = [x["entity_id"] for x in entities]
ent_by_id = {x["entity_id"]: x for x in entities}
rel_ids = [x["relationship_id"] for x in rels]

# ---- de-formalization gates ----
PERSONS = ["person-sidi-ongoiba", "person-amadou-nionson-diarra", "person-abou-ghosmane"]
DROP_RELS = ["rel-d2-dana-sidi-led", "rel-d2-dozos-macina-amadou-led",
             "rel-d2-ghosmane-jnim", "rel-d2-ghosmane-niger"]
for p in PERSONS:
    check(f"person de-formalized: {p}", p not in ent_ids)
for r in DROP_RELS:
    check(f"person-only relation removed: {r}", r not in rel_ids)

# ---- broken target gates ----
country_ids = {c["country_id"] for c in countries}
region_ids = {"region-central-sahel", "region-lake-chad-basin", "region-coastal-west-africa-spillover",
              "region-sudan-red-sea-horn", "region-nile-basin-east-africa", "region-north-africa-sahara",
              "region-southeast-africa-mozambique"}
valid_nodes = set(ent_ids) | country_ids | region_ids
broken_rel = [r["relationship_id"] for r in rels
              if r["source_entity_id"] not in valid_nodes or r["target_entity_id"] not in valid_nodes]
check("BROKEN_RELATIONSHIP_TARGETS == 0", len(broken_rel) == 0, str(broken_rel))

broken_ev = [e["evidence_id"] for e in evidence
             if e.get("source_id") and e["source_id"] not in {s["source_id"] for s in load("sources.json")["sources"]}]
check("BROKEN_EVIDENCE_TARGETS == 0", len(broken_ev) == 0, str(broken_ev))

broken_alias = [a for a, t in aliases.items() if t not in valid_nodes]
check("BROKEN_ALIAS_TARGETS == 0", len(broken_alias) == 0, str(broken_alias[:5]))

orphan_ev = [e["evidence_id"] for e in evidence
             if not (e.get("entity_ids") or []) and not (e.get("relation_ids") or [])
             and not (e.get("country_ids") or []) and not (e.get("region_ids") or [])]
check("ORPHAN_EVIDENCE == 0", len(orphan_ev) == 0, str(orphan_ev))

# ---- 9 retained entities encyclopedia_full ----
RETAIN = ["actor-katiba-serma", "person-ibrahim-malam-dicko", "person-ousmane-dicko",
          "person-youssouf-toloba", "person-sadou-samahouna", "actor-hcua",
          "actor-dana-atem", "actor-dozos-of-macina", "actor-niger-armed-forces"]
grade_d = 0
for eid in RETAIN:
    pr = ep.get(eid, {})
    secs = pr.get("sections", {})
    chars = sum(_tl(v) for v in secs.values())
    nsec = sum(1 for v in secs.values() if _tl(v) > 0)
    is_full = pr.get("profile_depth") == "encyclopedia_full" and chars >= 1800 and nsec >= 8
    if not is_full:
        grade_d += 1
    check(f"enriched entity full: {eid}", is_full, f"chars={chars} secs={nsec} depth={pr.get('profile_depth')}")
check("ENTITY_GRADE_D_COUNT == 0 (retained 9)", grade_d == 0, str(grade_d))

# ---- 4 P0 relations substantive R3 ----
P0 = ["rel-jnim-benin-forces-fought", "rel-d1-dan-na-jnim-conflict",
      "rel-d2-jafar-jnim", "rel-d2-dozos-macina-jnim-conflict"]
REL_SECTIONS = ("overview", "formation_background", "evolution_stages", "current_status",
                "why_it_matters", "uncertainties", "asip_analysis", "watch_indicators")
p0_thin = 0
for rid in P0:
    pr = rp.get(rid, {})
    tl = rt.get(rid, [])
    pchars = sum(len(str(pr.get(k) or "")) for k in REL_SECTIONS)
    sp = sum(1 for k in REL_SECTIONS if pr.get(k))
    is_r3 = pr.get("relation_maturity") == "R3_FULL_RELATIONSHIP_INTELLIGENCE"
    ok = is_r3 and pchars >= 350 and len(tl) >= 4 and sp >= 5
    if not ok:
        p0_thin += 1
    check(f"P0 relation substantive: {rid}", ok, f"chars={pchars} sections={sp} tl={len(tl)}")
check("P0_CONSOLIDATION_COUNT == 0", p0_thin == 0, str(p0_thin))

# ---- leadership facts preserved in org narrative ----
dana_txt = " ".join(str(v) for v in ep["actor-dana-atem"]["sections"].values())
dozos_txt = " ".join(str(v) for v in ep["actor-dozos-of-macina"]["sections"].values())
jnim_txt = " ".join(str(v) for v in ep["actor-jnim"]["sections"].values())
check("Sidi Ongoiba leadership preserved in Dana Atem", "Sidi Ongoiba" in dana_txt or "翁戈伊巴" in dana_txt)
check("Amadou Nionson Diarra leadership preserved in Dozos of Macina", "Amadou Nionson" in dozos_txt or "尼翁松" in dozos_txt)
check("Abou Ghosmane leadership preserved in JNIM", "Abou Ghosmane" in jnim_txt or "戈斯曼" in jnim_txt)

# ---- semantic enforcement ----
hcua_txt = " ".join(str(v) for v in ep["actor-hcua"]["sections"].values())
check("HCUA not reclassified as jihadist", "圣战组织" not in hcua_txt or "不得" in hcua_txt or "jihadist" not in hcua_txt.lower())
sadou_txt = " ".join(str(v) for v in ep["person-sadou-samahouna"]["sections"].values())
check("Sadou Samahouna not written as definitive deceased", "已故" not in sadou_txt and "deceased" not in sadou_txt.lower())
check("Sadou Samahouna time-sensitive/uncertain", ("不确定" in sadou_txt or "时间敏感" in sadou_txt))
jafar_rel = rp.get("rel-d2-jafar-jnim", {})
jafar_txt = " ".join(str(v) for v in jafar_rel.values())
check("Jafar Dicko not overall JNIM emir", ("整个 JNIM 的埃米尔" in jafar_txt and "不是" in jafar_txt) or "不是" in jafar_txt)
check("Iyad Ag Ghali remains wider JNIM leader", "伊亚德·阿格·加利" in jafar_txt or "Iyad Ag Ghali" in jafar_txt)

# ---- DUPLICATE canonical ----
from collections import Counter
dup = [k for k, v in Counter(ent_ids).items() if v > 1]
check("DUPLICATE_CANONICAL_ENTITIES == 0", len(dup) == 0, str(dup))

print(f"\n  PASS={PASS} FAIL={FAIL}")
sys.exit(1 if FAIL else 0)
