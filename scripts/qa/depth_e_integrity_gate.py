#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH E integrity & semantics gate. Asserts count invariants, the 7 fact/
semantic cleanup groups, entity/relation maturity targets, type locks,
evidence rules, and dist consistency."""
import json, sys, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
DIST = ROOT / "dist" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-e"
QA.mkdir(parents=True, exist_ok=True)

ok, issues = [], []

def load(name, base=DATA):
    return json.load(open(base / name, encoding="utf-8"))

countries = load("countries.json")["countries"]
entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
sources = load("sources.json")["sources"]
evidence = load("evidence_records.json")["evidence"]
ep = load("entity_profiles.json")["profiles"]
rp = load("relation_profiles.json")["profiles"]
tl = load("relation_timelines.json")["timelines"]
metrics = load("catalog_metrics.json")

non_country = [e for e in entities if e["entity_type"] != "country"]
rel_by_id = {r["relationship_id"]: r for r in rels}

check = lambda label, cond, detail="": (ok.append(f"{label} ({detail})") if cond else issues.append(f"{label}: {detail}"))
check("countries=13", len(countries) == 13, f"got {len(countries)}")
check("non-country entities=72", len(non_country) == 72, f"got {len(non_country)}")
check("relationships=150", len(rels) == 150, f"got {len(rels)}")
check("routes=249", metrics.get("route_count") == 249, f"got {metrics.get('route_count')}")
check("sources=158", len(sources) == 158, f"got {len(sources)}")
check("evidence=273", len(evidence) == 273, f"got {len(evidence)}")

# ---- GROUP 1: source pollution removed ----
for eid in ("actor-endf", "actor-fano", "actor-ola", "actor-tdf"):
    e = next((x for x in entities if x["entity_id"] == eid), {})
    check(f"{eid} no un-jnim-2018", "un-jnim-2018" not in e.get("source_refs", []), str(e.get("source_refs")))
for rid in ("rel-endf-fano-conflict", "rel-ethiopia-sudan-border"):
    r = rel_by_id.get(rid)
    check(f"{rid} no un-jnim-2018", r and "un-jnim-2018" not in r.get("source_refs", []), str(r.get("source_refs")) if r else "missing")

# ---- GROUP 2: OLA primary_category ----
ola = next((x for x in entities if x["entity_id"] == "actor-ola"), {})
check("OLA primary_category=insurgent_group", ola.get("primary_category") == "insurgent_group", f"got {ola.get('primary_category')}")

# ---- GROUP 3: Tigray control semantics ----
tdf_text = json.dumps(ep.get("actor-tdf", {}).get("sections", {}), ensure_ascii=False)
endf_text = json.dumps(ep.get("actor-endf", {}).get("sections", {}), ensure_ascii=False)
# '主权控制' only in negated context '完整主权控制不能混同'; '事实控制提格雷' only as quoted old-page correction
sovereign_pos = [m.start() for m in re.finditer(r"主权控制", tdf_text)]
sovereign_negated = all("不能混同" in tdf_text[m:m+20] or "不能把" in tdf_text[max(0, m-40):m] for m in sovereign_pos)
check("TDF: rival political authority not full sovereign control", "竞争权威" in tdf_text and (not sovereign_pos or sovereign_negated), f"sovereign at {sovereign_pos[:3]}")
fact_pos = [m.start() for m in re.finditer(r"事实控制", tdf_text)]
fact_negated = all("旧页面" in tdf_text[max(0, m-30):m] or "过强" in tdf_text[m:m+30] for m in fact_pos)
check("TDF: no 'factual control of whole Tigray'", not fact_pos or fact_negated, f"fact at {fact_pos[:3]}")
check("TDF: armed capacity stated", "武装能力" in tdf_text or "显著能力" in tdf_text or "显著武装能力" in tdf_text)

# ---- GROUP 4: Pretoria COHA current ----
check("Pretoria: still current AU framework", "Pretoria" in tdf_text and "现行框架" in tdf_text)
check("Pretoria: not dead", "协议已死" not in tdf_text and "已死" not in tdf_text)
au_text = json.dumps(ep.get("actor-tdf", {}).get("sections", {}), ensure_ascii=False)
check("AU still recognizes COHA", "AU" in au_text)

# ---- GROUP 5: fuel claim removed ----
for eid in ("actor-endf", "actor-tdf"):
    t = json.dumps(ep.get(eid, {}).get("sections", {}), ensure_ascii=False)
    # '伊朗战争导致燃料短缺' only appears as quoted old-page reference being removed
    pos = [m.start() for m in re.finditer(r"伊朗战争(致|导致)燃料短缺", t)]
    negated = all("旧页面" in t[max(0, m-30):m] or "应删除" in t[m:m+40] for m in pos)
    check(f"{eid} no Iran-war fuel claim", not pos or negated, f"fuel at {pos[:3]}")
r = rel_by_id.get("rel-endf-tdf-conflict")
if r:
    t = json.dumps(r, ensure_ascii=False)
    check("rel-endf-tdf-conflict no fuel claim", "伊朗战争" not in t or "燃料短缺" not in t)

# ---- GROUP 6: Fano decentralized ----
fano_text = json.dumps(ep.get("actor-fano", {}).get("sections", {}), ensure_ascii=False)
check("Fano: decentralized umbrella", "统称" in fano_text or "伞形" in fano_text or "umbrella" in fano_text or "分散" in fano_text or "decentralized" in fano_text)
# '统一中央指挥' only in negated context ('而不是统一中央指挥的单一组织')
uni_pos = [m.start() for m in re.finditer(r"统一中央指挥", fano_text)]
uni_negated = all("而不是" in fano_text[max(0, m-20):m] for m in uni_pos)
check("Fano: no single unified command", not uni_pos or uni_negated, f"unified at {uni_pos[:3]}")
check("Fano: not unified", "不是统一中央指挥的单一组织" in fano_text or "而非统一" in fano_text or "不代表已经形成覆盖全部Fano的单一指挥" in fano_text)

# ---- GROUP 7: OLA partial peace ----
ola_text = json.dumps(ep.get("actor-ola", {}).get("sections", {}), ensure_ascii=False)
check("OLA: Dec 2024 splinter-only", "分裂派" in ola_text and "2024年12月" in ola_text)
check("OLA: not whole-group peace", "不得写成OLA整体和平" in ola_text or "主流/其他网络继续武装活动" in ola_text)
check("OLA: no historical alliance extension", "不足以把2021关系延伸" in ola_text or "不能延伸" in ola_text or "现有证据不足以" in ola_text)

# ---- entity maturity ----
for eid in ("actor-endf", "actor-fano", "actor-ola", "actor-tdf"):
    pr = ep.get(eid, {})
    check(f"entity {eid} maturity=E3", pr.get("content_maturity") == "E3_FULL_ENCYCLOPEDIA", f"got {pr.get('content_maturity')}")
    check(f"entity {eid} has asip_analysis", bool(pr.get("sections", {}).get("asip_analysis")))
    check(f"entity {eid} has watch_indicators", bool(pr.get("sections", {}).get("watch_indicators")))

# ---- relation maturity ----
R3 = {"rel-endf-fano-conflict", "rel-endf-ola-conflict", "rel-endf-tdf-conflict"}
R2 = {"rel-ethiopia-sudan-border"}
for rid in R3:
    pr = rp.get(rid, {})
    check(f"relation {rid} maturity=R3", pr.get("relation_maturity") == "R3_FULL_RELATIONSHIP_INTELLIGENCE", f"got {pr.get('relation_maturity')}")
    check(f"relation {rid} asip_analysis", bool(pr.get("asip_analysis")))
    check(f"relation {rid} watch_indicators", bool(pr.get("watch_indicators")))
for rid in R2:
    pr = rp.get(rid, {})
    check(f"relation {rid} maturity=R2", pr.get("relation_maturity") == "R2_DEVELOPED_RELATIONSHIP", f"got {pr.get('relation_maturity')}")

# ---- relation type locks ----
TYPE_LOCKS = {
    "rel-endf-fano-conflict": "hostile_to",
    "rel-endf-ola-conflict": "hostile_to",
    "rel-endf-tdf-conflict": "hostile_to",
    "rel-ethiopia-sudan-border": "cross_border_link",
}
for rid, t in TYPE_LOCKS.items():
    r = rel_by_id.get(rid)
    check(f"relation {rid} type={t}", r and r["relationship_type"] == t, f"got {r.get('relationship_type') if r else None}")

# ---- evidence rules ----
db_ev = [e for e in evidence if str(e.get("claim_id", "")).startswith("depthe")]
check("evidence imported = 13", len(db_ev) == 13, f"got {len(db_ev)}")
bad_ref = []
for e in db_ev:
    if e["source_id"] not in {s["source_id"] for s in sources}:
        bad_ref.append(f"{e['claim_id']}:src")
    for eid in e.get("entity_ids", []):
        if eid not in {x["entity_id"] for x in entities}:
            bad_ref.append(f"{e['claim_id']}:ent:{eid}")
    for rid in e.get("relation_ids", []):
        if rid not in rel_by_id:
            bad_ref.append(f"{e['claim_id']}:rel:{rid}")
check("all depthe evidence references resolve", not bad_ref, str(bad_ref[:8]))
analytic = [e for e in db_ev if "analytical_synthesis" in e.get("verification_method", "")]
check("analytical_synthesis not written as verified", all(e["verification_status"] == "partially_verified" for e in analytic) and len(analytic) == 1, str([(e["claim_id"], e["verification_status"]) for e in analytic]))
alleg = [e for e in db_ev if "allegation" in e.get("verification_method", "")]
check("Eritrea allegation attributed", len(alleg) == 1 and alleg[0]["claim_id"] == "depthe-ev-010", str([e["claim_id"] for e in alleg]))
scope = [e for e in db_ev if "scope_limit" in e.get("verification_method", "")]
check("Fano 5129 scope-limited", len(scope) == 1 and "regional total" in scope[0].get("verification_method", ""), "")

# ---- dist consistency ----
if DIST.exists():
    for f in ("countries.json", "entities.json", "relationships.json", "sources.json", "evidence_records.json", "entity_profiles.json", "relation_profiles.json", "relation_timelines.json", "catalog_metrics.json"):
        try:
            a = load(f)
            b = load(f, DIST / "data")
            check(f"dist/data/{f} in sync", a == b)
        except Exception as ex:
            issues.append(f"dist/data/{f} read error: {ex}")

report = {
    "artifact": "DEPTHE_INTEGRITY_SEMANTICS_GATE",
    "ok": ok, "issues": issues,
    "gate": "PASS" if not issues else "OPEN",
    "scale": {"countries": len(countries), "entities": len(non_country), "relationships": len(rels),
              "sources": len(sources), "evidence": len(evidence), "profiles": len(rp), "timelines": len(tl),
              "routes": metrics.get("route_count")},
}
json.dump(report, open(QA / "integrity-gate.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print(f"checks: {len(ok)} ok, {len(issues)} issues")
for line in ok:
    print("  OK", line)
for line in issues:
    print("  !!", line)
print("== DEPTHE_INTEGRITY_SEMANTICS_GATE =", report["gate"], "==")
sys.exit(0 if not issues else 1)
