#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH D import gates: 10 focused tests covering count invariants, SAF-RSF
2026 frontline, JEM-SAF repair, RSF-JEM repair, Burhan/Hemedti current,
SPLM-N autonomy, atrocity attribution, territorial scope, and generator
regression guards."""
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

print("== TEST 1: no count expansion ==")
check("countries=13", len(countries) == 13, f"got {len(countries)}")
check("entities=102", len(non_country) == 102, f"got {len(non_country)} (83 + 11 Expansion B)")
check("relationships=192", len(rels) == 192, f"got {len(rels)} (164 + 17 Expansion B)")
check("routes=321", metrics.get("route_count") == 321, f"got {metrics.get('route_count')} (274 + 19 entities + 28 relations)")

print("== TEST 2: SAF-RSF 2026 front ==")
saf = json.dumps(ep.get("actor-saf", {}).get("sections", {}), ensure_ascii=False)
rsf = json.dumps(ep.get("actor-rsf", {}).get("sections", {}), ensure_ascii=False)
war = json.dumps(rp.get("rel-saf-rsf-war", {}), ensure_ascii=False)
check("SAF 2025 Khartoum", "2025" in saf and "Khartoum" in saf)
check("RSF Darfur + al-Fashir", "Darfur" in rsf and "al-Fashir" in rsf)
check("war Kordofan/El Obeid", "Kordofan" in war and "El Obeid" in war)
check("SAF-RSF hostile_to", rel_by_id.get("rel-saf-rsf-war", {}).get("relationship_type") == "hostile_to")

print("== TEST 3: JEM-SAF repair ==")
jem_saf = rel_by_id.get("rel-jem-saf-conflict")
check("JEM-SAF type=cooperates_with", jem_saf and jem_saf["relationship_type"] == "cooperates_with", f"got {jem_saf.get('relationship_type') if jem_saf else None}")
check("JEM-SAF legacy id", jem_saf and jem_saf["relationship_id"] == "rel-jem-saf-conflict")
check("JEM-SAF historical timeline preserved", "2003—2020" in json.dumps(tl.get("rel-jem-saf-conflict", []), ensure_ascii=False))
check("JEM-SAF no residual hostile", not any(
    r["source_entity_id"] == "actor-jem" and r["target_entity_id"] == "actor-saf" and r["relationship_type"] == "hostile_to"
    for r in rels))
check("JEM-SAF total still 181", len(rels) == 192)

print("== TEST 4: RSF-JEM repair ==")
rsf_jem = rel_by_id.get("rel-rsf-darfur-origin")
check("RSF-JEM type=fought_against", rsf_jem and rsf_jem["relationship_type"] == "fought_against", f"got {rsf_jem.get('relationship_type') if rsf_jem else None}")
check("RSF-JEM legacy id", rsf_jem and rsf_jem["relationship_id"] == "rel-rsf-darfur-origin")
check("no common-origin implication", "共同组织起源" not in json.dumps(rp.get("rel-rsf-darfur-origin", {}), ensure_ascii=False))
jem_text = json.dumps(ep.get("actor-jem", {}).get("sections", {}), ensure_ascii=False)
check("JEM not from Janjaweed/RSF", "源自Janjaweed/RSF" not in jem_text and "RSF的分支" not in jem_text)

print("== TEST 5: Burhan current ==")
burhan = json.dumps(ep.get("person-abdel-fattah-al-burhan", {}).get("sections", {}), ensure_ascii=False)
e = next((x for x in entities if x["entity_id"] == "person-abdel-fattah-al-burhan"), {})
check("Burhan leads SAF + TSC", "Transitional Sovereignty Council" in burhan and "领导" in burhan)
check("Burhan freshness=current", e.get("freshness_status") == "current", f"got {e.get('freshness_status')}")
check("Burhan-SAF led_by", rel_by_id.get("rel-burhan-saf-leads", {}).get("relationship_type") == "led_by")

print("== TEST 6: Hemedti current ==")
hemedti = json.dumps(ep.get("person-mohamed-hamdan-dagalo", {}).get("sections", {}), ensure_ascii=False)
e = next((x for x in entities if x["entity_id"] == "person-mohamed-hamdan-dagalo"), {})
check("Hemedti leads RSF", "Hemedti" in hemedti and "领导" in hemedti)
check("Hemedti freshness=current", e.get("freshness_status") == "current", f"got {e.get('freshness_status')}")
check("Hemedti-RSF led_by", rel_by_id.get("rel-dagalo-rsf-leads", {}).get("relationship_type") == "led_by")

print("== TEST 7: SPLM-N autonomy ==")
splmn = json.dumps(ep.get("actor-splm-n-al-hilu", {}).get("sections", {}), ensure_ascii=False)
check("SPLM-N SFA/Tasis alignment", "SFA" in splmn or "Tasis" in splmn)
check("SPLM-N autonomy stated", "保持" in splmn and ("独立" in splmn or "自主" in splmn))
check("SPLM-N hostile to SAF", rel_by_id.get("rel-splm-n-saf-conflict", {}).get("relationship_type") == "hostile_to")
check("no SPLM-N-RSF edge", not any(
    (r["source_entity_id"] == "actor-splm-n-al-hilu" and r["target_entity_id"] == "actor-rsf") or
    (r["source_entity_id"] == "actor-rsf" and r["target_entity_id"] == "actor-splm-n-al-hilu")
    for r in rels))

print("== TEST 8: atrocity attribution ==")
atrocity = json.dumps(ep.get("actor-rsf", {}).get("sections", {}), ensure_ascii=False) + json.dumps(ep.get("person-mohamed-hamdan-dagalo", {}).get("sections", {}), ensure_ascii=False)
check("UN investigation attribution", "联合国调查" in atrocity or "UN investigation" in atrocity or "调查" in atrocity)
check("no final conviction language", "已被定罪" not in atrocity and "司法定罪" not in atrocity and "法庭已定罪" not in atrocity)

print("== TEST 9: territorial scope ==")
check("SAF operates_in Sudan", rel_by_id.get("rel-saf-sudan-operates", {}).get("relationship_type") == "operates_in")
check("RSF operates_in Sudan", rel_by_id.get("rel-rsf-sudan-operates", {}).get("relationship_type") == "operates_in")
check("no SAF whole-Sudan control", "控制整个苏丹" not in saf)
rsf_pos = [m.start() for m in re.finditer(r"控制整个苏丹", rsf)]
rsf_ok = all("写成" in rsf[max(0, m - 60):m] or "不能把" in rsf[max(0, m - 80):m] for m in rsf_pos)
check("no RSF whole-Sudan control (except negated)", not rsf_pos or rsf_ok, f"matches at {rsf_pos[:3]}")

print("== TEST 10: generator regression guards ==")
# old generator must not restore: JEM hostile to SAF / JEM-RSF common origin / 2024-only framing / whole-Sudan / SPLM-N subordinate
all_rels = json.dumps(rels, ensure_ascii=False)
check("no JEM current hostile_to SAF", not any(
    r["source_entity_id"] == "actor-jem" and r["target_entity_id"] == "actor-saf" and r["relationship_type"] == "hostile_to"
    for r in rels))
check("no historically_associated_with RSF-JEM", rel_by_id.get("rel-rsf-darfur-origin", {}).get("relationship_type") != "historically_associated_with")
check("no SPLM-N member/constituent of RSF", "member_of_force" not in json.dumps(ep.get("actor-splm-n-al-hilu", {}), ensure_ascii=False) and "constituent_of" not in json.dumps(ep.get("actor-splm-n-al-hilu", {}), ensure_ascii=False))
# key type locks
for rid, t in (("rel-saf-rsf-war", "hostile_to"), ("rel-burhan-saf-leads", "led_by"), ("rel-dagalo-rsf-leads", "led_by"),
               ("rel-splm-n-saf-conflict", "hostile_to"), ("rel-jem-saf-conflict", "cooperates_with"),
               ("rel-rsf-darfur-origin", "fought_against"), ("rel-saf-sudan-operates", "operates_in"),
               ("rel-rsf-sudan-operates", "operates_in")):
    check(f"type lock {rid}={t}", rel_by_id.get(rid, {}).get("relationship_type") == t, f"got {rel_by_id.get(rid, {}).get('relationship_type')}")

print()
if fails:
    print(f"FAIL_TOTAL={len(fails)}: {fails}")
    sys.exit(1)
print("ALL DEPTH D TESTS PASS")
