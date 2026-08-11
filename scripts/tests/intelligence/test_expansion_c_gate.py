#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Expansion C dedicated gate test.

Mechanical checks:
- no duplicate canonical entities (8 new all unique)
- GSPC/AQIM continuity correct (no actor-gspc node; GSPC in AQIM aliases +
  historical_names + profile chapter + alias_index; timeline has 1998/2001/2006/2007)
- no Maitatsine -> Boko Haram lineage edge
- EIJ merge-date conflict preserved (1998 UN + 2001 State both present)
- AIAI relationship qualified as ideological/personnel predecessor
- Al-Murabitun only factional ISIS-Sahel defection (no whole-org succession)
- source/evidence refs resolve; aliases resolve; relation profiles resolve;
  timelines resolve; no orphan entities/relations
"""
import io, json, os, re, sys

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


entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
ep = load("entity_profiles.json")["profiles"]
rp = load("relation_profiles.json")["profiles"]
rt = load("relation_timelines.json")["timelines"]
sources = load("sources.json")["sources"]
evidence = load("evidence_records.json")["evidence"]
aliases = load("alias_index.json")["aliases"]

ent_ids = [x["entity_id"] for x in entities]
rel_ids = [x["relationship_id"] for x in rels]
src_ids = {s["source_id"] for s in sources}

NEW8 = ["actor-egyptian-islamic-jihad", "actor-gia", "actor-aiai",
        "actor-tunisian-combatant-group", "actor-gicm", "actor-al-battar-brigade",
        "actor-maitatsine-movement", "actor-mujao"]

print("== 1. duplicate canonical entities ==")
dups = [x for x in set(ent_ids) if ent_ids.count(x) > 1]
check("no duplicate canonical entities", not dups, str(dups))
check("8 new entities present", all(x in ent_ids for x in NEW8), str([x for x in NEW8 if x not in ent_ids]))
check("no actor-gspc standalone node", "actor-gspc" not in ent_ids)
std_new = [x for x in NEW8 if (ep.get(x) or {}).get("profile_depth") != "encyclopedia_full"]
check("all 8 new entities encyclopedia_full", not std_new, str(std_new))

print("== 2. GSPC/AQIM continuity ==")
aqim = next(x for x in entities if x["entity_id"] == "actor-aqim")
aqim_aliases = " ".join((aqim.get("aliases") or [])).lower()
aqim_hist = " ".join(aqim.get("historical_names") or [])
check("GSPC in AQIM aliases", "gspc" in aqim_aliases)
check("GSPC in AQIM historical_names", "gspc" in aqim_hist.lower() or "萨拉菲宣教与战斗组织" in aqim_hist)
check("alias_index gspc -> actor-aqim", aliases.get("gspc") == "actor-aqim")
aqim_profile_txt = json.dumps(ep.get("actor-aqim", {}).get("sections", {}), ensure_ascii=False)
check("AQIM profile has GIA->GSPC->AQIM chapter", "GIA → GSPC → AQIM" in aqim_profile_txt or "GSPC → AQIM" in aqim_profile_txt)
check("GSPC timeline nodes (1998/2001/2006/2007)", all(k in aqim_profile_txt for k in ["1998", "2001", "2006", "2007"]))
gia_aqim = next((r for r in rels if r["relationship_id"] == "rel-expc-gia-aqim-lineage"), None)
check("GIA->AQIM split_from lineage relation exists", gia_aqim is not None)
check("lineage relation profile mentions GSPC name at formation",
      "GSPC" in json.dumps(rp.get("rel-expc-gia-aqim-lineage", {}), ensure_ascii=False))

print("== 3. Maitatsine no lineage ==")
mat_rels = [r for r in rels if r["source_entity_id"] == "actor-maitatsine-movement" or r["target_entity_id"] == "actor-maitatsine-movement"]
bad_types = [r["relationship_type"] for r in mat_rels if r["relationship_type"] in ("predecessor_of", "split_from", "merged_from", "constituent_of")]
check("no Maitatsine lineage edges (predecessor/split/merged/constituent)", not bad_types, str(bad_types))
check("Maitatsine has no Boko Haram edge", all("actor-jas" not in (r["source_entity_id"], r["target_entity_id"]) for r in mat_rels))
mat_txt = json.dumps(ep.get("actor-maitatsine-movement", {}).get("sections", {}), ensure_ascii=False)
check("Maitatsine profile states no direct lineage", "直接组织传承" in mat_txt or "组织连续性" in mat_txt or "比较≠传承" in mat_txt)

print("== 4. EIJ merge-date conflict preserved ==")
eij_txt = json.dumps(ep.get("actor-egyptian-islamic-jihad", {}).get("sections", {}), ensure_ascii=False)
eij_rel = json.dumps(rp.get("rel-expc-eij-alqaida-integration", {}), ensure_ascii=False)
eij_tl = json.dumps(rt.get("rel-expc-eij-alqaida-integration", []), ensure_ascii=False)
check("EIJ profile keeps 1998 UN date", "1998" in eij_txt and "联合国" in eij_txt)
check("EIJ profile keeps June 2001 State date", ("2001 年 6 月" in eij_txt) or ("2001-06" in eij_txt), "has June 2001 marker")
check("EIJ relation profile staged 1998-2001", "1998—2001" in eij_rel or "1998–2001" in eij_rel)
check("EIJ timeline has both dates", "1998" in eij_tl and "2001" in eij_tl)

print("== 5. AIAI qualified predecessor ==")
aiai_rel = json.dumps(rp.get("rel-expc-aiai-shabaab-predecessor", {}), ensure_ascii=False)
check("AIAI relation qualified ideological/personnel", "意识形态/人事前身" in aiai_rel or "意识形态前驱" in aiai_rel)
check("AIAI relation excludes sole direct succession", "单一" in aiai_rel and ("不支持" in aiai_rel or "排除" in aiai_rel))
check("AIAI relation preserves UN attribution", "联合国" in aiai_rel)

print("== 6. Al-Murabitun faction-only ISIS-Sahel ==")
splinter = json.dumps(rp.get("rel-is-mourabitoun-splinter", {}), ensure_ascii=False)
check("splinter profile faction-qualified", "派别" in splinter or "faction" in splinter.lower())
check("splinter profile excludes whole-org succession", "整个" in splinter and ("不是" in splinter or "并不" in splinter or "而非" in splinter or "不可" in splinter or "并非" in splinter))
mura_txt = json.dumps(ep.get("actor-al-mourabitoun", {}).get("sections", {}), ensure_ascii=False)
check("Al-Murabitun profile 2015 faction-only", "2015" in mura_txt and "派别" in mura_txt)

print("== 7. refs resolve ==")
bad_ev = [e for e in evidence if e.get("source_id") not in src_ids]
check("all evidence source_id resolve", not bad_ev, str([e["evidence_id"] for e in bad_ev[:5]]))
all_src_refs = []
for x in entities:
    all_src_refs += x.get("source_refs", [])
for r in rels:
    all_src_refs += r.get("source_refs", [])
for pr in rp.values():
    all_src_refs += pr.get("source_ids", [])
for tls in rt.values():
    for t in tls:
        all_src_refs += t.get("source_ids", [])
missing = sorted({x for x in all_src_refs if x not in src_ids})
check("all entity/relation/profile/timeline source refs resolve", not missing, str(missing[:8]))

print("== 8. no orphan entities/relations ==")
rel_endpoints = set()
for r in rels:
    rel_endpoints.add(r["source_entity_id"])
    rel_endpoints.add(r["target_entity_id"])
known = set(ent_ids) | {c["country_id"] for c in load("countries.json")["countries"]} | {r["region_id"] for r in load("regions.json")["regions"]}
orphans = sorted({x for x in rel_endpoints if x not in known})
check("no orphan relation endpoints", not orphans, str(orphans))
prof_rel_ids = set(rp.keys())
check("all relation profiles resolve to relationships", not (prof_rel_ids - set(rel_ids)), str(sorted(prof_rel_ids - set(rel_ids))[:5]))
tl_rel_ids = set(rt.keys())
check("all relation timelines resolve to relationships", not (tl_rel_ids - set(rel_ids)), str(sorted(tl_rel_ids - set(rel_ids))[:5]))
missing_prof = [rid for rid in rel_ids if rid not in rp and not rid.startswith("rel-") and False]
check("new 11 relations have profiles", all(r in rp for r in [
    "rel-expc-gia-aqim-lineage", "rel-expc-aqim-alqaida-alignment", "rel-expc-eij-alqaida-integration",
    "rel-expc-aiai-shabaab-predecessor", "rel-expc-battar-isis-libya", "rel-expc-mujao-murabitun",
    "rel-expc-aqim-mujao-split", "rel-expc-aqim-ansar-relation", "rel-expc-gicm-alqaida",
    "rel-expc-tcg-alqaida", "rel-expc-maitatsine-nigeria"]))
check("upgraded relations now R3", all((rp.get(r) or {}).get("relation_maturity") == "R3_FULL_RELATIONSHIP_INTELLIGENCE"
      for r in ["rel-jnim-ansar-constituent", "rel-jnim-mourabitoun-constituent", "rel-is-mourabitoun-splinter"]))
check("katiba timeline has >=4 nodes", len(rt.get("rel-jnim-katiba-constituent", [])) >= 4,
      "nodes=" + str(len(rt.get("rel-jnim-katiba-constituent", []))))
new_r3 = [r for r in ["rel-expc-gia-aqim-lineage", "rel-expc-aqim-alqaida-alignment", "rel-expc-eij-alqaida-integration",
                      "rel-expc-aiai-shabaab-predecessor", "rel-expc-battar-isis-libya", "rel-expc-mujao-murabitun",
                      "rel-expc-aqim-ansar-relation", "rel-expc-gicm-alqaida", "rel-expc-tcg-alqaida"]
          if (rp.get(r) or {}).get("relation_maturity") == "R3_FULL_RELATIONSHIP_INTELLIGENCE"]
check("9 new dossiers reach R3", len(new_r3) >= 9, str(new_r3))

print("== 9. alias resolution ==")
for a, eid in [("gspc", "actor-aqim"), ("egyptian islamic jihad", "actor-egyptian-islamic-jihad"),
               ("maitatsine", "actor-maitatsine-movement"), ("mujao", "actor-mujao"),
               ("al-battar brigade", "actor-al-battar-brigade"), ("aiai", "actor-aiai"),
               ("tunisian combatant group", "actor-tunisian-combatant-group"), ("gicm", "actor-gicm")]:
    check(f"alias '{a}' resolves", aliases.get(a) == eid, f"got {aliases.get(a)}")

print(f"\nEXPANSION_C_GATE: PASS={PASS} FAIL={FAIL}")
sys.exit(1 if FAIL else 0)
