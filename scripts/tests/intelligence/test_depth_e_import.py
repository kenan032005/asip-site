#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH E import gates: 11 focused tests covering count invariants, source
cleanup, OLA category, Fano decentralized, OLA partial peace, Tigray control
semantics, Pretoria current, no Iran fuel claim, Eritrea attribution, Sudan
border refresh, and generator regression guards."""
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
check("entities=105", len(non_country) == 105, f"got {len(non_country)} (105 + 0 Consolidation A)")
check("relationships=203", len(rels) == 203, f"got {len(rels)} (203 + 2 Pack B)")
check("routes=335", metrics.get("route_count") == 335, f"got {metrics.get('route_count')} (335 + 2 Pack B)")

print("== TEST 2: source cleanup ==")
for eid in ("actor-endf", "actor-fano", "actor-ola", "actor-tdf"):
    e = ent_by_id.get(eid, {})
    check(f"{eid} no un-jnim-2018", "un-jnim-2018" not in e.get("source_refs", []), str(e.get("source_refs")))
for rid in ("rel-endf-fano-conflict", "rel-ethiopia-sudan-border"):
    r = rel_by_id.get(rid, {})
    check(f"{rid} no un-jnim-2018", "un-jnim-2018" not in r.get("source_refs", []), str(r.get("source_refs")))

print("== TEST 3: OLA category ==")
check("OLA primary_category=insurgent_group", ent_by_id.get("actor-ola", {}).get("primary_category") == "insurgent_group",
      f"got {ent_by_id.get('actor-ola', {}).get('primary_category')}")
check("OLA not state_security_force", ent_by_id.get("actor-ola", {}).get("primary_category") != "state_security_force")

print("== TEST 4: Fano decentralized ==")
fano = json.dumps(ep.get("actor-fano", {}).get("sections", {}), ensure_ascii=False)
check("Fano umbrella/decentralized", "统称" in fano or "伞形" in fano or "分散" in fano)
uni = [m.start() for m in re.finditer(r"统一中央指挥", fano)]
check("Fano no single unified command", not uni or all("而不是" in fano[max(0, m - 20):m] for m in uni), f"unified at {uni[:3]}")

print("== TEST 5: OLA partial peace ==")
ola = json.dumps(ep.get("actor-ola", {}).get("sections", {}), ensure_ascii=False)
check("Dec 2024 splinter-only", "2024年12月" in ola and "分裂派" in ola)
check("no whole-OLA peace", "主流/其他网络继续武装活动" in ola or "不得写成OLA整体和平" in ola)
check("no historical alliance extension", "现有证据不足以" in ola or "不能延伸" in ola)

print("== TEST 6: Tigray control semantics ==")
tdf = json.dumps(ep.get("actor-tdf", {}).get("sections", {}), ensure_ascii=False)
sovereign = [m.start() for m in re.finditer(r"主权控制", tdf)]
check("sovereign control only negated", not sovereign or all("不能混同" in tdf[m:m+20] for m in sovereign), f"at {sovereign[:3]}")
factc = [m.start() for m in re.finditer(r"事实控制", tdf)]
check("factual-control only as old-page correction", not factc or all("旧页面" in tdf[max(0, m-30):m] for m in factc), f"at {factc[:3]}")
check("rival political authority + armed capacity", "竞争权威" in tdf and "武装能力" in tdf)

print("== TEST 7: Pretoria current ==")
check("Pretoria current AU framework", "Pretoria" in tdf and "现行框架" in tdf)
check("Pretoria not dead", "协议已死" not in tdf and "已死" not in tdf)

print("== TEST 8: no Iran fuel claim ==")
for eid in ("actor-endf", "actor-tdf"):
    t = json.dumps(ep.get(eid, {}).get("sections", {}), ensure_ascii=False)
    pos = [m.start() for m in re.finditer(r"伊朗战争(致|导致)燃料短缺", t)]
    negated = all("旧页面" in t[max(0, m-30):m] or "应删除" in t[m:m+40] for m in pos)
    check(f"{eid} no Iran-war fuel claim", not pos or negated, f"at {pos[:3]}")
r = rel_by_id.get("rel-endf-tdf-conflict", {})
rt = json.dumps(r, ensure_ascii=False)
check("rel-endf-tdf-conflict no fuel claim", "伊朗战争导致燃料短缺" not in rt or "旧页面" in rt, "")

print("== TEST 9: Eritrea attribution ==")
db_ev = [e for e in evidence if str(e.get("claim_id", "")).startswith("depthe")]
alleg = [e for e in db_ev if "allegation" in e.get("verification_method", "")]
check("Eritrea allegation attributed (ev-010)", len(alleg) == 1 and alleg[0]["claim_id"] == "depthe-ev-010", str([e["claim_id"] for e in alleg]))
rsf_text = json.dumps(ep.get("actor-endf", {}).get("sections", {}), ensure_ascii=False) + json.dumps(ep.get("actor-tdf", {}).get("sections", {}), ensure_ascii=False)
check("Eritrea support as allegation in text", "allegation" in rsf_text or "指责" in rsf_text or "按allegation" in rsf_text)

print("== TEST 10: Sudan border refresh ==")
bord = json.dumps(rp.get("rel-ethiopia-sudan-border", {}), ensure_ascii=False)
check("border cross_border_link", rel_by_id.get("rel-ethiopia-sudan-border", {}).get("relationship_type") == "cross_border_link")
check("border UNHCR dated semantics", "UNHCR" in bord and "2026" in bord)
check("border al-Fashaga context", "al-Fashaga" in bord or "法什卡" in bord)

print("== TEST 11: generator regression guards ==")
# no restored: un-jnim-2018 on targets / state_security_force OLA / fuel claim / dead Pretoria / full Tigray control / unified Fano
check("no un-jnim-2018 restored on targets", all("un-jnim-2018" not in ent_by_id.get(eid, {}).get("source_refs", []) for eid in ("actor-endf", "actor-fano", "actor-ola", "actor-tdf")))
check("OLA category not reverted", ent_by_id.get("actor-ola", {}).get("primary_category") == "insurgent_group")
# type locks
for rid, t in (("rel-endf-fano-conflict", "hostile_to"), ("rel-endf-ola-conflict", "hostile_to"),
               ("rel-endf-tdf-conflict", "hostile_to"), ("rel-ethiopia-sudan-border", "cross_border_link")):
    check(f"type lock {rid}={t}", rel_by_id.get(rid, {}).get("relationship_type") == t, f"got {rel_by_id.get(rid, {}).get('relationship_type')}")

print()
if fails:
    print(f"FAIL_TOTAL={len(fails)}: {fails}")
    sys.exit(1)
print("ALL DEPTH E TESTS PASS")
