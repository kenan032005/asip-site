#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH C integrity & semantics gate. Asserts count invariants, the 5 semantic
cleanup groups, freshness locks, entity/relation maturity targets, relation type
locks, evidence rules, and dist consistency."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
DIST = ROOT / "dist" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-c"
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
check("sources=137 (all reused)", len(sources) == 137, f"got {len(sources)}")
check("evidence=245", len(evidence) == 245, f"got {len(evidence)}")

# ---- freshness locks ----
CURRENT = {"actor-dan-na-ambassagou", "person-youssouf-toloba", "person-jafar-dicko", "person-ousmane-dicko", "person-abou-ghosmane"}
AGING = {"actor-dozos-of-macina", "person-amadou-nionson-diarra", "actor-dana-atem", "person-sidi-ongoiba", "actor-katiba-serma"}
for eid in CURRENT:
    e = next((x for x in entities if x["entity_id"] == eid), None)
    check(f"freshness {eid}=current", e is not None and e.get("freshness_status") == "current", f"got {e.get('freshness_status') if e else None}")
for eid in AGING:
    e = next((x for x in entities if x["entity_id"] == eid), None)
    check(f"freshness {eid}=aging (not upgraded)", e is not None and e.get("freshness_status") == "aging", f"got {e.get('freshness_status') if e else None}")

# ---- semantic locks ----
# 1. Dozo networks not unified: three separate entities, no merged text
for eid in ("actor-dan-na-ambassagou", "actor-dozos-of-macina", "actor-dana-atem"):
    check(f"dozo entity {eid} exists", eid in {e["entity_id"] for e in entities})
for eid in ("actor-dan-na-ambassagou", "actor-dozos-of-macina", "actor-dana-atem"):
    t = json.dumps(ep.get(eid, {}).get("sections", {}), ensure_ascii=False)
    for other in ("actor-dozos-of-macina", "actor-dana-atem", "actor-dan-na-ambassagou"):
        if other != eid:
            check(f"{eid} does not collapse into {other}", not t.startswith(other) and other not in t[:40], "merged-actor guard")

# 2. Dana Atem partial integration: not whole-group member_of_force
dana_fama = rel_by_id.get("rel-d2-dana-fama-coop")
check("Dana-FAMa type=cooperates_with", dana_fama and dana_fama["relationship_type"] == "cooperates_with", f"got {dana_fama.get('relationship_type') if dana_fama else None}")
dana_text = json.dumps(ep.get("actor-dana-atem", {}).get("sections", {}), ensure_ascii=False)
check("Dana Atem partial integration wording", "成员" in dana_text and "不等于整个组织" in dana_text)
# no Dana Atem member_of_force relation to FAMa
dana_mof = [r for r in rels if (r["source_entity_id"] == "actor-dana-atem" or r["target_entity_id"] == "actor-dana-atem") and r["relationship_type"] == "member_of_force"]
check("no Dana Atem whole-group member_of_force", len(dana_mof) == 0, str([r["relationship_id"] for r in dana_mof]))

# 3. All Dozo->FAMa cooperates_with + intermittent/ambiguous
for rid, eid in (("rel-d1-dan-na-fama-coop", "actor-dan-na-ambassagou"), ("rel-d2-dozos-macina-fama-coop", "actor-dozos-of-macina"), ("rel-d2-dana-fama-coop", "actor-dana-atem")):
    r = rel_by_id.get(rid)
    pr = rp.get(rid, {})
    check(f"{rid} type=cooperates_with", r and r["relationship_type"] == "cooperates_with", f"got {r.get('relationship_type') if r else None}")
    t = json.dumps(pr, ensure_ascii=False) + json.dumps(ep.get(eid, {}).get("sections", {}), ensure_ascii=False)
    check(f"{rid} intermittent/ambiguous wording", "间歇" in t or "intermittent" in t or "非正式" in t or "ambiguous" in t)

# 4. Regional command scope: Jafar/Ousmane Burkina-only
jafar_text = json.dumps(ep.get("person-jafar-dicko", {}).get("sections", {}), ensure_ascii=False)
ousmane_text = json.dumps(ep.get("person-ousmane-dicko", {}).get("sections", {}), ensure_ascii=False)
check("Jafar Burkina-regional scope", "Burkina" in jafar_text and "区域" in jafar_text)
check("Jafar not whole-JNIM leader", "整个JNIM总领导人" in jafar_text and "不能改写为整个" in jafar_text)
check("Ousmane Burkina deputy scope", "Burkina" in ousmane_text and "区域" in ousmane_text)
check("Ousmane not whole-JNIM deputy", "整个JNIM副领导" in ousmane_text and "不能写成整个" in ousmane_text)
# Jafar->JNIM stays affiliated_with, not led_by
jafar_jnim = rel_by_id.get("rel-d2-jafar-jnim")
check("Jafar-JNIM type=affiliated_with", jafar_jnim and jafar_jnim["relationship_type"] == "affiliated_with", f"got {jafar_jnim.get('relationship_type') if jafar_jnim else None}")
no_whole_led = [r for r in rels if r["source_entity_id"] == "person-jafar-dicko" and r["target_entity_id"] == "actor-jnim" and r["relationship_type"] == "led_by"]
check("no Jafar whole-JNIM led_by", len(no_whole_led) == 0, str([r["relationship_id"] for r in no_whole_led]))

# 5. Ghosmane != Hanifa
gho_text = json.dumps(ep.get("person-abou-ghosmane", {}).get("sections", {}), ensure_ascii=False)
hanifa_text = json.dumps(ep.get("actor-katiba-hanifa", {}).get("sections", {}), ensure_ascii=False) if "actor-katiba-hanifa" in ep else ""
check("Ghosmane distinct from Abu Hanifa", "Abu Hanifa" in gho_text and ("不同人物" in gho_text or "两个不同人物" in gho_text or "strictly separate" in gho_text))

# 6. Katiba Serma constituent_of JNIM
ks_jnim = rel_by_id.get("rel-d2-katiba-serma-jnim")
check("Katiba Serma-JNIM type=constituent_of", ks_jnim and ks_jnim["relationship_type"] == "constituent_of", f"got {ks_jnim.get('relationship_type') if ks_jnim else None}")

# ---- entity maturity ----
E3 = {"actor-dan-na-ambassagou", "actor-dozos-of-macina", "person-jafar-dicko"}
E2 = {"person-youssouf-toloba", "person-amadou-nionson-diarra", "actor-dana-atem", "actor-katiba-serma", "person-ousmane-dicko", "person-abou-ghosmane"}
E1 = {"person-sidi-ongoiba"}
for eid in E3:
    pr = ep.get(eid, {})
    check(f"entity {eid} maturity=E3", pr.get("content_maturity") == "E3_FULL_ENCYCLOPEDIA", f"got {pr.get('content_maturity')}")
for eid in E2:
    pr = ep.get(eid, {})
    check(f"entity {eid} maturity=E2", pr.get("content_maturity") == "E2_DEVELOPED", f"got {pr.get('content_maturity')}")
for eid in E1:
    pr = ep.get(eid, {})
    check(f"entity {eid} maturity=E1", pr.get("content_maturity") == "E1_BASIC", f"got {pr.get('content_maturity')}")

# ---- relation maturity ----
R3 = {"rel-d1-dan-na-jnim-conflict", "rel-d1-dan-na-fama-coop", "rel-d2-dozos-macina-jnim-conflict", "rel-d2-jafar-jnim"}
for rid in R3:
    pr = rp.get(rid, {})
    check(f"relation {rid} maturity=R3", pr.get("relation_maturity") == "R3_FULL_RELATIONSHIP_INTELLIGENCE", f"got {pr.get('relation_maturity')}")
    check(f"relation {rid} asip_analysis", bool(pr.get("asip_analysis")))
    check(f"relation {rid} watch_indicators", bool(pr.get("watch_indicators")) or rel_by_id.get(rid, {}).get("freshness_status") == "historical")
for rid in ("rel-d2-dan-na-toloba-led", "rel-d2-dana-dan-na-split", "rel-d2-dana-sidi-led", "rel-d2-dana-katiba-serma-conflict",
            "rel-d2-dana-ansarul-conflict", "rel-d2-dana-fama-coop", "rel-d2-dozos-macina-amadou-led",
            "rel-d2-dozos-macina-fama-coop", "rel-d2-katiba-serma-jnim", "rel-d2-ansarul-jafar-led",
            "rel-d2-ousmane-jnim", "rel-d2-ghosmane-jnim"):
    pr = rp.get(rid, {})
    check(f"relation {rid} maturity=R2", pr.get("relation_maturity") == "R2_DEVELOPED_RELATIONSHIP", f"got {pr.get('relation_maturity')}")

# ---- relation type locks ----
TYPE_LOCKS = {
    "rel-d1-dan-na-jnim-conflict": "fought_against",
    "rel-d1-dan-na-fama-coop": "cooperates_with",
    "rel-d2-dan-na-toloba-led": "led_by",
    "rel-d2-dana-dan-na-split": "split_from",
    "rel-d2-dana-sidi-led": "led_by",
    "rel-d2-dana-katiba-serma-conflict": "fought_against",
    "rel-d2-dana-ansarul-conflict": "fought_against",
    "rel-d2-dana-fama-coop": "cooperates_with",
    "rel-d2-dozos-macina-amadou-led": "led_by",
    "rel-d2-dozos-macina-jnim-conflict": "fought_against",
    "rel-d2-dozos-macina-fama-coop": "cooperates_with",
    "rel-d2-katiba-serma-jnim": "constituent_of",
    "rel-d2-jafar-jnim": "affiliated_with",
    "rel-d2-ansarul-jafar-led": "led_by",
    "rel-d2-ousmane-jnim": "affiliated_with",
    "rel-d2-ghosmane-jnim": "affiliated_with",
}
for rid, t in TYPE_LOCKS.items():
    r = rel_by_id.get(rid)
    check(f"relation {rid} type={t}", r and r["relationship_type"] == t, f"got {r.get('relationship_type') if r else None}")

# ---- evidence rules ----
db_ev = [e for e in evidence if str(e.get("claim_id", "")).startswith("depthc")]
check("evidence imported = 14", len(db_ev) == 14, f"got {len(db_ev)}")
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
check("all depthc evidence references resolve", not bad_ref, str(bad_ref[:8]))
check("no analytical evidence written as verified", all(
    e["verification_status"] != "verified" for e in db_ev if "analytical" in e.get("verification_method", "")
), "")

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
    "artifact": "DEPTHC_INTEGRITY_SEMANTICS_GATE",
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
print("== DEPTHC_INTEGRITY_SEMANTICS_GATE =", report["gate"], "==")
sys.exit(0 if not issues else 1)
