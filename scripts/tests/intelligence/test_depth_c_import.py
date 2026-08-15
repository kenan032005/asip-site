#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH C import gates: 11 focused tests covering count invariants, Dozo
network separation, Dana partial integration, Dozo-FAMa semantics, Dan Na 2026
refresh, Jafar/Ousmane regional scope, Ghosmane/Hanifa separation, Katiba Serma
constituent lock, freshness locks, and generator regression guards."""
import json, sys
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

print("== TEST 1: no count expansion ==")
check("countries=13", len(countries) == 13, f"got {len(countries)}")
check("entities=105", len(non_country) == 105, f"got {len(non_country)} (105 + 0 Consolidation A)")
check("relationships=203", len(rels) == 203, f"got {len(rels)} (203 + 2 Pack B)")
check("routes=335", metrics.get("route_count") == 335, f"got {metrics.get('route_count')} (335 + 2 Pack B)")

print("== TEST 2: Dozo network separation ==")
dan = json.dumps(ep.get("actor-dan-na-ambassagou", {}).get("sections", {}), ensure_ascii=False)
dozos = json.dumps(ep.get("actor-dozos-of-macina", {}).get("sections", {}), ensure_ascii=False)
dana = json.dumps(ep.get("actor-dana-atem", {}).get("sections", {}), ensure_ascii=False)
check("three Dozo entities exist", all(e in {x["entity_id"] for x in entities} for e in ("actor-dan-na-ambassagou", "actor-dozos-of-macina", "actor-dana-atem")))
check("Dan Na not merged with Dozos of Macina", "Dozos of Macina" not in dan[:60] or "三个主要" in dan)
check("Dana Atem separate from Dan Na", "2018年从" in dana and "Dan Na Ambassagou" in dana)
check("Dozos not unified wording", "不是统一阵营" in dozos or "三大主要" in dozos)

print("== TEST 3: Dana Atem partial integration ==")
check("Dana-FAMa cooperates_with", rel_by_id.get("rel-d2-dana-fama-coop", {}).get("relationship_type") == "cooperates_with")
check("partial member integration wording", "成员" in dana and "不等于整个组织" in dana)
check("no Dana member_of_force", not any(
    (r["source_entity_id"] == "actor-dana-atem" or r["target_entity_id"] == "actor-dana-atem") and r["relationship_type"] == "member_of_force"
    for r in rels))

print("== TEST 4: Dozo-FAMa semantics ==")
for rid in ("rel-d1-dan-na-fama-coop", "rel-d2-dozos-macina-fama-coop", "rel-d2-dana-fama-coop"):
    r = rel_by_id.get(rid)
    check(f"{rid} cooperates_with", r and r["relationship_type"] == "cooperates_with", f"got {r.get('relationship_type') if r else None}")
    t = json.dumps(rp.get(rid, {}), ensure_ascii=False)
    check(f"{rid} intermittent/ambiguous", "间歇" in t or "intermittent" in t or "非正式" in t or "ambiguous" in t)

print("== TEST 5: Dan Na 2026 refresh ==")
e = next((x for x in entities if x["entity_id"] == "actor-dan-na-ambassagou"), None)
check("Dan Na freshness=current", e and e.get("freshness_status") == "current", f"got {e.get('freshness_status') if e else None}")
check("Dan Na 2026 JNIM offensive", "2026" in dan and ("重新集中打击" in dan or "Bandiagara" in dan))
check("Dan Na-JNIM relation current refreshed", "2026" in json.dumps(rp.get("rel-d1-dan-na-jnim-conflict", {}), ensure_ascii=False) or "current" in json.dumps(rel_by_id.get("rel-d1-dan-na-jnim-conflict", {}), ensure_ascii=False))

print("== TEST 6: Jafar regional scope ==")
jafar = json.dumps(ep.get("person-jafar-dicko", {}).get("sections", {}), ensure_ascii=False)
check("Jafar Burkina leader only", "Burkina" in jafar and "整个JNIM" in jafar and ("不" in jafar or "不应" in jafar or "不能" in jafar))
check("Jafar-JNIM affiliated_with", rel_by_id.get("rel-d2-jafar-jnim", {}).get("relationship_type") == "affiliated_with")
check("no Jafar whole-JNIM led_by", not any(
    r["source_entity_id"] == "person-jafar-dicko" and r["target_entity_id"] == "actor-jnim" and r["relationship_type"] == "led_by"
    for r in rels))

print("== TEST 7: Ousmane regional scope ==")
ousmane = json.dumps(ep.get("person-ousmane-dicko", {}).get("sections", {}), ensure_ascii=False)
check("Ousmane Burkina deputy only", "Burkina" in ousmane and "不能写成整个JNIM副领导" in ousmane)
check("Ousmane-JNIM affiliated_with", rel_by_id.get("rel-d2-ousmane-jnim", {}).get("relationship_type") == "affiliated_with")

print("== TEST 8: Ghosmane de-formalized + leadership preserved in JNIM ==")
check("person-abou-ghosmane de-formalized", "person-abou-ghosmane" not in {x["entity_id"] for x in entities})
jnim_txt = json.dumps(ep.get("actor-jnim", {}).get("sections", {}), ensure_ascii=False)
check("Ghosmane leadership preserved in JNIM", "Abou Ghosmane" in jnim_txt or "戈斯曼" in jnim_txt)
check("Ghosmane role Niger northwest ops", "Niger" in jnim_txt and "西北" in jnim_txt)

print("== TEST 9: Katiba Serma constituent lock ==")
check("Katiba Serma-JNIM constituent_of", rel_by_id.get("rel-d2-katiba-serma-jnim", {}).get("relationship_type") == "constituent_of")
ks = json.dumps(ep.get("actor-katiba-serma", {}).get("sections", {}), ensure_ascii=False)
check("Katiba Serma not national org", "constituent_of" in ks or "子单元" in ks)

print("== TEST 10: freshness locks ==")
cur = {"actor-dan-na-ambassagou", "person-youssouf-toloba", "person-jafar-dicko", "person-ousmane-dicko"}
aging = {"actor-dozos-of-macina", "actor-dana-atem", "actor-katiba-serma"}
for eid in cur:
    e = next((x for x in entities if x["entity_id"] == eid), None)
    check(f"freshness {eid}=current", e and e.get("freshness_status") == "current", f"got {e.get('freshness_status') if e else None}")
for eid in aging:
    e = next((x for x in entities if x["entity_id"] == eid), None)
    check(f"freshness {eid}=aging (locked)", e and e.get("freshness_status") == "aging", f"got {e.get('freshness_status') if e else None}")

print("== TEST 11: generator regression guards ==")
# old generator must not restore unified-dozo / whole-JNIM-leader / Hanifa-merge
for eid, ph in (("actor-dan-na-ambassagou", "三个网络合并"), ("actor-dozos-of-macina", "Dozo统一"), ("person-jafar-dicko", "整个JNIM的领导人")):
    t = json.dumps(ep.get(eid, {}), ensure_ascii=False)
    check(f"no restored wrong phrase {ph} in {eid}", ph not in t)
# Ghosmane/Hanifa must not be merged anywhere
merged = [eid for eid, pr in ep.items() if "Abou Ghosmane（Abu Hanifa" in json.dumps(pr, ensure_ascii=False) or "Abou Ghosmane与Abu Hanifa为同一" in json.dumps(pr, ensure_ascii=False)]
check("no Ghosmane/Hanifa merge anywhere", not merged, str(merged))
# per-relation type locks from instruction
for rid, t in (("rel-d1-dan-na-jnim-conflict", "fought_against"), ("rel-d1-dan-na-fama-coop", "cooperates_with"),
               ("rel-d2-dozos-macina-jnim-conflict", "fought_against"), ("rel-d2-jafar-jnim", "affiliated_with"),
               ("rel-d2-katiba-serma-jnim", "constituent_of")):
    check(f"type lock {rid}={t}", rel_by_id.get(rid, {}).get("relationship_type") == t, f"got {rel_by_id.get(rid, {}).get('relationship_type')}")

print()
if fails:
    print(f"FAIL_TOTAL={len(fails)}: {fails}")
    sys.exit(1)
print("ALL DEPTH C TESTS PASS")
