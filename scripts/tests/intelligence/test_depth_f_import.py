#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH F import gates: 14 focused tests covering count invariants, Machar
status/legal attribution, SPLM-IO-SSPDF 2026, NAS cooperation, ISM lineage,
ISM-ISWAP edge repair, SAMIM end date, TPDF bilateral vs SAMIM, Tanzania
source cleanup, Rwanda/Sudan RSF separation, LNA-GNU ceasefire semantics,
ISIS-Libya facilitative role, and generator regression guards."""
import json, sys, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "africa"

fails = []
def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print(f"  [{tag}] {name}" + (f" | {detail}" if detail else ""))
    if not cond:
        fails.append(name)

def load(name):
    return json.load(open(DATA / name, encoding="utf-8"))

countries = load("countries.json")["countries"]
entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
ep = load("entity_profiles.json")["profiles"]
rp = load("relation_profiles.json")["profiles"]
sources = load("sources.json")["sources"]
evidence = load("evidence_records.json")["evidence"]
metrics = load("catalog_metrics.json")
tl = load("relation_timelines.json")["timelines"]

rel_by_id = {r["relationship_id"]: r for r in rels}
non_country = [e for e in entities if e["entity_type"] != "country"]
ent_by_id = {e["entity_id"]: e for e in entities}

print("== TEST 1: no count expansion ==")
check("countries=13", len(countries) == 13, f"got {len(countries)}")
check("entities=108", len(non_country) == 108, f"got {len(non_country)} (104 + 4 Expansion E)")
check("relationships=205", len(rels) == 205, f"got {len(rels)} (195 + 10 Expansion E)")
check("routes=340", metrics.get("route_count") == 340, f"got {metrics.get('route_count')} (326 + 14 Expansion E)")

print("== TEST 2: Machar current status ==")
machar = json.dumps(ep.get("person-riek-machar", {}).get("sections", {}), ensure_ascii=False)
e_machar = ent_by_id.get("person-riek-machar", {})
check("suspended First VP", "被暂停的第一副总统" in machar or "暂停第一副总统" in machar)
check("house arrest/detention", "软禁" in machar and "拘押" in machar or "软禁" in machar and "拘留" in machar)
check("trial ongoing", "审判" in machar)
check("current_status override", "suspended_first_vice_president" in str(e_machar.get("current_status", "")), str(e_machar.get("current_status")))

print("== TEST 3: Machar legal attribution ==")
check("no conviction language", "已定罪" not in machar and "被判有罪" not in machar)
check("charges as allegations", "指控" in machar and ("检方" in machar or "否认" in machar or "政府检方" in machar))

print("== TEST 4: SPLM-IO-SSPDF 2026 ==")
sspdf = json.dumps(ep.get("actor-sspdf", {}).get("sections", {}), ensure_ascii=False)
splm = json.dumps(ep.get("actor-splm-io", {}).get("sections", {}), ensure_ascii=False)
check("2026 renewed conflict", "2026" in sspdf and "重新" in sspdf and "Jonglei" in sspdf)
check("SPLM-IO fragmentation", "分裂" in splm or "splinter" in splm)
check("SSPDF-SPLM-IO hostile_to", rel_by_id.get("rel-splm-io-sspdf-conflict", {}).get("relationship_type") == "hostile_to")
check("R-ARCSS referenced", "R-ARCSS" in sspdf and "框架" in sspdf)

print("== TEST 5: NAS-SPLM-IO current ==")
nas = json.dumps(ep.get("actor-nas", {}).get("sections", {}), ensure_ascii=False)
check("NAS cooperation MoU", "MoU" in nas or "2026年3月" in nas or "合作" in nas)
check("NAS-SPLM-IO allied_with", rel_by_id.get("rel-nas-splm-io-allied", {}).get("relationship_type") == "allied_with")
check("NAS no merger", "合并" not in nas or "不合并" in nas)

print("== TEST 6: ISM not ISWAP ==")
ism = json.dumps(ep.get("actor-is-mozambique", {}).get("sections", {}), ensure_ascii=False)
check("ISCAP lineage", "ISCAP" in ism)
check("not ISWAP branch", "不是ISWAP" in ism or "并非ISWAP" in ism)
check("2022 Mozambique province", "2022" in ism and "province" in ism)

print("== TEST 7: ISM-ISWAP edge repair ==")
ism2 = rel_by_id.get("rel-is-moz-islamic-state2")
check("legacy id retained", ism2 and ism2["relationship_id"] == "rel-is-moz-islamic-state2")
check("src=actor-rdf-mozambique", ism2 and ism2["source_entity_id"] == "actor-rdf-mozambique", f"got {ism2.get('source_entity_id') if ism2 else None}")
check("tgt=actor-is-mozambique", ism2 and ism2["target_entity_id"] == "actor-is-mozambique", f"got {ism2.get('target_entity_id') if ism2 else None}")
check("type=fought_against", ism2 and ism2["relationship_type"] == "fought_against", f"got {ism2.get('relationship_type') if ism2 else None}")
check("time_start=2021", ism2 and ism2.get("time_start") == "2021", f"got {ism2.get('time_start') if ism2 else None}")
check("no residual ISM->ISWAP edge", not any(
    r["source_entity_id"] == "actor-is-mozambique" and r["target_entity_id"] == "actor-iswap" for r in rels))
check("total still 205", len(rels) == 205)

print("== TEST 8: SAMIM end date ==")
samim = json.dumps(ep.get("actor-samim", {}).get("sections", {}), ensure_ascii=False)
e_samim = ent_by_id.get("actor-samim", {})
check("SAMIM ended 2024-07-15", "2024年7月15日" in samim or "2024-07-15" in samim or "2024年7月" in samim)
check("SAMIM historical", e_samim.get("freshness_status") == "historical", f"got {e_samim.get('freshness_status')}")
check("SAMIM-FADM historical", rel_by_id.get("rel-samim-fadm-cooperate", {}).get("freshness_status") == "historical")

print("== TEST 9: TPDF bilateral vs SAMIM ==")
check("TPDF-SAMIM member historical", rel_by_id.get("rel-tanzania-samim-member", {}).get("freshness_status") == "historical")
check("TPDF-SAMIM member time_end=2024-07-15", rel_by_id.get("rel-tanzania-samim-member", {}).get("time_end") == "2024-07-15", str(rel_by_id.get("rel-tanzania-samim-member", {}).get("time_end")))
check("TPDF-Mozambique cooperate current", rel_by_id.get("rel-tanzania-mozambique-cooperate", {}).get("freshness_status") == "current")
check("TPDF entity current", ent_by_id.get("actor-tanzania-tpdf", {}).get("freshness_status") == "current")
tpdf = json.dumps(ep.get("actor-tanzania-tpdf", {}).get("sections", {}), ensure_ascii=False)
check("TPDF bilateral distinction", "双边" in tpdf and ("2022" in tpdf))

print("== TEST 10: Tanzania source cleanup ==")
for rid in ("rel-tanzania-tpdf-is-moz", "rel-tanzania-mozambique-cooperate", "rel-tanzania-samim-member"):
    r = rel_by_id.get(rid)
    check(f"{rid} no un-jnim-2018", r and "un-jnim-2018" not in r.get("source_refs", []), str(r.get("source_refs")) if r else "missing")
check("actor-tanzania-tpdf no un-jnim-2018", "un-jnim-2018" not in ent_by_id.get("actor-tanzania-tpdf", {}).get("source_refs", []))

print("== TEST 11: Rwanda/Sudan RSF separation ==")
rdf = json.dumps(ep.get("actor-rdf-mozambique", {}).get("sections", {}), ensure_ascii=False)
check("RDF Mozambique distinct naming", "Rwanda" in rdf and ("绝不能" in rdf or "不能" in rdf or "不得" in rdf) and ("Sudan" in rdf or "苏丹" in rdf))
check("no Sudan RSF conflation", "Rapid Support Forces" in rdf or "苏丹快速支援" in rdf)

print("== TEST 12: LNA-GNU ceasefire semantics ==")
lna = json.dumps(ep.get("actor-lna", {}).get("sections", {}), ensure_ascii=False)
check("LNA 2020 ceasefire", "2020" in lna and "停火" in lna)
check("LNA-GNU not full-scale war", "全面战争" not in lna or "不是" in lna)
check("LNA-GNU rivalry status", rel_by_id.get("rel-lna-gnu-rivalry", {}).get("current_status") == "political_military_rivalry_under_2020_ceasefire", str(rel_by_id.get("rel-lna-gnu-rivalry", {}).get("current_status")))

print("== TEST 13: ISIS-Libya facilitative role ==")
isis_ly = json.dumps(ep.get("actor-isis-libya", {}).get("sections", {}), ensure_ascii=False)
check("facilitative role", "facilitative" in isis_ly or "facilitation" in isis_ly or "便利" in isis_ly or "enabling" in isis_ly)
check("limited territorial control", "limited" in isis_ly.lower() or "有限" in isis_ly)
check("ISIS-Libya-LNA residual hostility", rel_by_id.get("rel-isis-libya-lna-conflict", {}).get("current_status") == "residual_security_hostility_after_historical_combat", str(rel_by_id.get("rel-isis-libya-lna-conflict", {}).get("current_status")))
check("ISIS-Libya affiliation pledged", rel_by_id.get("rel-isis-libya-affiliation", {}).get("relationship_type") == "pledged_allegiance_to")

print("== TEST 14: generator regression guards ==")
# residuals must be 0: Machar active-only / charges-as-conviction / ISM->ISWAP / SAMIM active / TPDF current SAMIM / un-jnim-2018 / Rwanda-RSF conflation / LNA-GNU full war / ISIS-Libya territorial 2026
check("Machar not active-only", "suspended" in str(ent_by_id.get("person-riek-machar", {}).get("current_status", "")) or "被暂停" in machar)
check("no conviction", "已定罪" not in machar)
check("no ISM->ISWAP affiliation anywhere", "ISWAP" not in json.dumps(ep.get("actor-is-mozambique", {}), ensure_ascii=False) or "不是ISWAP" in ism)
check("no SAMIM active", ent_by_id.get("actor-samim", {}).get("freshness_status") == "historical")
check("no TPDF current SAMIM member", rel_by_id.get("rel-tanzania-samim-member", {}).get("freshness_status") == "historical")
check("no un-jnim-2018 on targets", all("un-jnim-2018" not in rel_by_id.get(rid, {}).get("source_refs", []) for rid in ("rel-tanzania-tpdf-is-moz", "rel-tanzania-mozambique-cooperate", "rel-tanzania-samim-member")))
check("no Rwanda/Sudan RSF conflation", "Sudan Rapid Support" in rdf or "绝不" in rdf)
check("no LNA-GNU full-scale war", "全面战争" not in lna or "不是" in lna)
check("no ISIS-Libya territorial 2026", "持续" not in isis_ly or "有限" in isis_ly)
# key type locks
for rid, t in (("rel-splm-io-sspdf-conflict", "hostile_to"), ("rel-kiir-sspdf-leads", "led_by"),
               ("rel-machar-splm-io-leads", "led_by"), ("rel-nas-splm-io-allied", "allied_with"),
               ("rel-is-moz-islamic-state", "pledged_allegiance_to"), ("rel-is-moz-islamic-state2", "fought_against"),
               ("rel-fadm-is-moz-hostile", "fought_against"), ("rel-lna-gnu-rivalry", "hostile_to"),
               ("rel-isis-libya-affiliation", "pledged_allegiance_to"), ("rel-isis-libya-lna-conflict", "hostile_to")):
    check(f"type lock {rid}={t}", rel_by_id.get(rid, {}).get("relationship_type") == t, f"got {rel_by_id.get(rid, {}).get('relationship_type')}")

print()
if fails:
    print(f"FAIL_TOTAL={len(fails)}: {fails}")
    sys.exit(1)
print("ALL DEPTH F TESTS PASS")
