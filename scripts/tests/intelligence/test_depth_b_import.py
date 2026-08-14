#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH B import gates: 11 focused tests covering count invariants, the 5 fact
cleanups, Ansaru semantics, Lakurawa disputed lock and generator regression
guards. Mirrors the test list in the sync instruction."""
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

rel_by_id = {r["relationship_id"]: r for r in rels}
non_country = [e for e in entities if e["entity_type"] != "country"]

print("== TEST 1: no count expansion ==")
check("countries=13", len(countries) == 13, f"got {len(countries)}")
check("entities=108", len(non_country) == 108, f"got {len(non_country)} (104 + 4 Expansion E)")
check("relationships=205", len(rels) == 205, f"got {len(rels)} (195 + 10 Expansion E)")

print("== TEST 2: JAS-ISIS pledge history ==")
jas_text = json.dumps(ep.get("actor-jas", {}).get("sections", {}), ensure_ascii=False)
check("JAS 2015 pledge present", "2015" in jas_text and ("宣誓效忠" in jas_text or "效忠" in jas_text))
check("JAS never-joined-ISIS residual=0", "JAS 未加入伊斯兰国体系" not in jas_text and "JAS从未加入伊斯兰国体系" not in jas_text)
check("JAS current unaffiliated", "不隶属于" in jas_text)
iswap_text = json.dumps(ep.get("actor-iswap", {}).get("sections", {}), ensure_ascii=False)
check("ISWAP remains formal ISIS branch", "正式" in iswap_text and "branch" in iswap_text)

print("== TEST 3: malformed relation repair ==")
mal = rel_by_id.get("rel-jas-islamic-state-hostile")
check("rel-jas-islamic-state-hostile exists", mal is not None)
if mal:
    check("target=actor-islamic-state", mal["target_entity_id"] == "actor-islamic-state", mal["target_entity_id"])
    check("type=pledged_allegiance_to", mal["relationship_type"] == "pledged_allegiance_to", mal["relationship_type"])
    check("time=2015-03-07..2016-08-03", mal.get("time_start") == "2015-03-07" and mal.get("time_end") == "2016-08-03")
    check("current_status=historical_pledge...", mal.get("current_status") == "historical_pledge_recognition_shifted_to_iswap")
check("total relationships still 205", len(rels) == 205)

print("== TEST 4: ISWAP leadership uncertainty ==")
check("no uncontested 2021 death", "没有支持" in iswap_text and "2021年确认死亡" in iswap_text or "2021年确认死亡" not in iswap_text)
check("Ba'a Shuwa reported current leader", "Ba'a Shuwa" in iswap_text)
check("member-state divergence", "分歧" in iswap_text)

print("== TEST 5: Bakura != al-Barnawi ==")
all_text = json.dumps({"jas": ep.get("actor-jas", {}), "iswap": ep.get("actor-iswap", {})}, ensure_ascii=False)
check("no identity conflation", "巴库拉（Abu Musab al-Barnawi）" not in all_text and "Abu Musab al-Barnawi（巴库拉）" not in all_text)

print("== TEST 6: MNJTF sector mapping ==")
mnjtf_text = json.dumps(ep.get("actor-mnjtf", {}).get("sections", {}), ensure_ascii=False)
check("Sector1=Cameroon/Mora", "Sector 1" in mnjtf_text and "Cameroon" in mnjtf_text and "Mora" in mnjtf_text)
check("Sector2=Chad/Bagasola", "Sector 2" in mnjtf_text and "Bagasola" in mnjtf_text and "Chad" in mnjtf_text)
check("Sector3=Nigeria/Monguno", "Sector 3" in mnjtf_text and "Monguno" in mnjtf_text and "Nigeria" in mnjtf_text)
check("Sector4=Niger/Diffa", "Sector 4" in mnjtf_text and "Diffa" in mnjtf_text and "Niger" in mnjtf_text)

print("== TEST 7: Niger withdrawal semantics ==")
check("Niger withdrawal reflected", "退出" in mnjtf_text and "troop-contributing" in mnjtf_text)
check("Sector 4 disrupted", "Sector 4" in mnjtf_text and ("冲击" in mnjtf_text or "削弱" in mnjtf_text))

print("== TEST 8: Cameroon source cleanup ==")
for rid in ("rel-cameroon-army-jas", "rel-cameroon-army-iswap"):
    r = rel_by_id.get(rid)
    check(f"{rid} no un-jnim-2018", r is not None and "un-jnim-2018" not in r.get("source_refs", []), str(r.get("source_refs")) if r else "missing")

print("== TEST 9: Ansaru semantics ==")
ansaru_jnim = rel_by_id.get("rel-d1-ansaru-jnim-affiliation")
check("Ansaru->JNIM affiliated_with", ansaru_jnim and ansaru_jnim["relationship_type"] == "affiliated_with")
ansaru_aqim = rel_by_id.get("rel-d1-ansaru-aqim-allegiance")
check("Ansaru->AQIM pledged_allegiance_to", ansaru_aqim and ansaru_aqim["relationship_type"] == "pledged_allegiance_to")
ansaru_jas = rel_by_id.get("rel-d1-ansaru-jas-split")
check("Ansaru split_from JAS", ansaru_jas and ansaru_jas["relationship_type"] == "split_from")

print("== TEST 10: Lakurawa disputed lock ==")
lak_iss = [r for r in rels if r["source_entity_id"] == "actor-lakurawa" and r["target_entity_id"] == "actor-is-sahel"]
check("Lakurawa->IS Sahel part_of_network", len(lak_iss) == 1 and lak_iss[0]["relationship_type"] == "part_of_network")
check("Lakurawa disputed=true", len(lak_iss) == 1 and lak_iss[0].get("disputed") is True)

print("== TEST 11: generator regression guards ==")
# old generator must NOT restore these wrong states
for ph in ("JAS 未加入伊斯兰国体系", "Nigeria Sector 1", "Cameroon Sector 3"):
    found = []
    for eid, pr in ep.items():
        if ph in json.dumps(pr, ensure_ascii=False):
            found.append(eid)
    check(f"old-generator phrase not restored: {ph}", not found, str(found))
malformed_dup = [r for r in rels if r["source_entity_id"] == "actor-jas" and r["target_entity_id"] == "actor-iswap" and r["relationship_type"] == "hostile_to"]
check("no malformed JAS->ISWAP duplicate", len(malformed_dup) == 1, f"got {len(malformed_dup)}")
# per-relation type locks from instruction
check("rel-jas-iswap-conflict=hostile_to", rel_by_id.get("rel-jas-iswap-conflict", {}).get("relationship_type") == "hostile_to")
check("rel-jas-islamic-state-hostile target=actor-islamic-state", rel_by_id.get("rel-jas-islamic-state-hostile", {}).get("target_entity_id") == "actor-islamic-state")
check("rel-jas-islamic-state-hostile type=pledged_allegiance_to", rel_by_id.get("rel-jas-islamic-state-hostile", {}).get("relationship_type") == "pledged_allegiance_to")
check("rel-iswap-islamic-state-affiliation=pledged_allegiance_to", rel_by_id.get("rel-iswap-islamic-state-affiliation", {}).get("relationship_type") == "pledged_allegiance_to")

print()
if fails:
    print(f"FAIL_TOTAL={len(fails)}: {fails}")
    sys.exit(1)
print("ALL DEPTH B TESTS PASS")
