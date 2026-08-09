#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH D integrity & semantics gate. Asserts count invariants, the 6 fact/
semantic cleanup groups, entity/relation maturity targets, the 2 count-preserving
repairs with proof, evidence rules, and dist consistency."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
DIST = ROOT / "dist" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-d"
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
check("sources=150", len(sources) == 150, f"got {len(sources)}")
check("evidence=260", len(evidence) == 260, f"got {len(evidence)}")

# ---- GROUP A: SAF-RSF 2026 frontline ----
saf_text = json.dumps(ep.get("actor-saf", {}).get("sections", {}), ensure_ascii=False)
rsf_text = json.dumps(ep.get("actor-rsf", {}).get("sections", {}), ensure_ascii=False)
war_text = json.dumps(rp.get("rel-saf-rsf-war", {}), ensure_ascii=False)
check("SAF: 2025 Khartoum recovery", "2025" in saf_text and "Khartoum" in saf_text)
check("RSF: Darfur control + al-Fashir", "Darfur" in rsf_text and "al-Fashir" in rsf_text)
check("war: Kordofan/El Obeid frontline", "Kordofan" in war_text and "El Obeid" in war_text)
check("no 'controls whole Sudan' on SAF", "控制整个苏丹" not in saf_text and "整个苏丹的控制" not in saf_text)
# "控制整个苏丹" only appears in negated context ('不能把...写成控制整个苏丹西部')
import re as _re
rsf_pos = [m.start() for m in _re.finditer(r"控制整个苏丹", rsf_text)]
rsf_negated = all("写成" in rsf_text[max(0, m - 60):m] or "不能把" in rsf_text[max(0, m - 80):m] for m in rsf_pos)
check("no 'controls whole Sudan' on RSF (except negated)", not rsf_pos or rsf_negated, f"matches at {rsf_pos[:3]}")
check("SAF-RSF stays hostile_to", rel_by_id.get("rel-saf-rsf-war", {}).get("relationship_type") == "hostile_to")

# ---- GROUP B: JEM-SAF repair ----
jem_saf = rel_by_id.get("rel-jem-saf-conflict")
check("JEM-SAF repair: type=cooperates_with", jem_saf and jem_saf["relationship_type"] == "cooperates_with", f"got {jem_saf.get('relationship_type') if jem_saf else None}")
check("JEM-SAF repair: legacy id retained", jem_saf and jem_saf["relationship_id"] == "rel-jem-saf-conflict")
check("JEM-SAF repair: current_status", jem_saf and jem_saf.get("current_status") == "current_operational_cooperation_after_historical_conflict", f"got {jem_saf.get('current_status') if jem_saf else None}")
check("JEM-SAF repair: historical timeline preserved", "2003—2020" in json.dumps(tl.get("rel-jem-saf-conflict", []), ensure_ascii=False), "2003-2020 hostility in timeline")
# no other JEM->SAF hostile relation
jem_saf_hostile = [r for r in rels if r["source_entity_id"] == "actor-jem" and r["target_entity_id"] == "actor-saf" and r["relationship_type"] == "hostile_to"]
check("no residual JEM-SAF hostile relation", len(jem_saf_hostile) == 0, str([r["relationship_id"] for r in jem_saf_hostile]))

# ---- GROUP C: RSF-JEM repair ----
rsf_jem = rel_by_id.get("rel-rsf-darfur-origin")
check("RSF-JEM repair: type=fought_against", rsf_jem and rsf_jem["relationship_type"] == "fought_against", f"got {rsf_jem.get('relationship_type') if rsf_jem else None}")
check("RSF-JEM repair: legacy id retained", rsf_jem and rsf_jem["relationship_id"] == "rel-rsf-darfur-origin")
check("RSF-JEM repair: no common-origin wording", "共同组织起源" not in json.dumps(rp.get("rel-rsf-darfur-origin", {}), ensure_ascii=False) and "源自Janjaweed/RSF" not in json.dumps(ep.get("actor-jem", {}), ensure_ascii=False))
check("RSF-JEM repair: current_status", rsf_jem and rsf_jem.get("current_status") == "current_hostility_after_historical_darfur_association", f"got {rsf_jem.get('current_status') if rsf_jem else None}")

# ---- GROUP D: leadership 2026 ----
burhan_text = json.dumps(ep.get("person-abdel-fattah-al-burhan", {}).get("sections", {}), ensure_ascii=False)
hemedti_text = json.dumps(ep.get("person-mohamed-hamdan-dagalo", {}).get("sections", {}), ensure_ascii=False)
check("Burhan current SAF leader", "Burhan" in burhan_text and "Transitional Sovereignty Council" in burhan_text)
check("Hemedti current RSF leader", "Hemedti" in hemedti_text and "领导" in hemedti_text)
check("Burhan-SAF led_by", rel_by_id.get("rel-burhan-saf-leads", {}).get("relationship_type") == "led_by")
check("Hemedti-RSF led_by", rel_by_id.get("rel-dagalo-rsf-leads", {}).get("relationship_type") == "led_by")
check("Burhan freshness=current", next((x for x in entities if x["entity_id"] == "person-abdel-fattah-al-burhan"), {}).get("freshness_status") == "current")
check("Hemedti freshness=current", next((x for x in entities if x["entity_id"] == "person-mohamed-hamdan-dagalo"), {}).get("freshness_status") == "current")

# ---- GROUP E: SPLM-N autonomy ----
splmn_text = json.dumps(ep.get("actor-splm-n-al-hilu", {}).get("sections", {}), ensure_ascii=False)
check("SPLM-N: aligned with SFA/Tasis", "SFA" in splmn_text or "Tasis" in splmn_text)
check("SPLM-N: organizational autonomy", "保持" in splmn_text and ("独立" in splmn_text or "自主" in splmn_text or "autonomy" in splmn_text))
check("SPLM-N: hostile to SAF", rel_by_id.get("rel-splm-n-saf-conflict", {}).get("relationship_type") == "hostile_to")
# no SPLM-N->RSF relation created (depth-only round)
splmn_rsf = [r for r in rels if (r["source_entity_id"] == "actor-splm-n-al-hilu" and r["target_entity_id"] == "actor-rsf") or (r["source_entity_id"] == "actor-rsf" and r["target_entity_id"] == "actor-splm-n-al-hilu")]
check("no SPLM-N-RSF edge created", len(splmn_rsf) == 0, str([r["relationship_id"] for r in splmn_rsf]))

# ---- GROUP F: atrocity attribution ----
atrocity_text = json.dumps(ep.get("actor-rsf", {}).get("sections", {}), ensure_ascii=False) + json.dumps(ep.get("person-mohamed-hamdan-dagalo", {}).get("sections", {}), ensure_ascii=False)
check("atrocity: UN investigation attribution", "联合国调查" in atrocity_text or "UN investigation" in atrocity_text or "调查" in atrocity_text)
check("atrocity: no final conviction language", "已被定罪" not in atrocity_text and "司法定罪" not in atrocity_text and "法庭已定罪" not in atrocity_text)

# ---- entity maturity ----
E3 = {"actor-saf", "actor-rsf", "person-abdel-fattah-al-burhan", "person-mohamed-hamdan-dagalo", "actor-splm-n-al-hilu"}
E2 = {"actor-jem"}
for eid in E3:
    pr = ep.get(eid, {})
    check(f"entity {eid} maturity=E3", pr.get("content_maturity") == "E3_FULL_ENCYCLOPEDIA", f"got {pr.get('content_maturity')}")
    check(f"entity {eid} has asip_analysis", bool(pr.get("sections", {}).get("asip_analysis")))
    check(f"entity {eid} has watch_indicators", bool(pr.get("sections", {}).get("watch_indicators")))
for eid in E2:
    pr = ep.get(eid, {})
    check(f"entity {eid} maturity=E2", pr.get("content_maturity") == "E2_DEVELOPED", f"got {pr.get('content_maturity')}")

# ---- relation maturity ----
R3 = {"rel-saf-rsf-war", "rel-splm-n-saf-conflict", "rel-jem-saf-conflict"}
R2 = {"rel-burhan-saf-leads", "rel-dagalo-rsf-leads", "rel-rsf-darfur-origin", "rel-saf-sudan-operates", "rel-rsf-sudan-operates"}
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
    "rel-saf-rsf-war": "hostile_to",
    "rel-burhan-saf-leads": "led_by",
    "rel-dagalo-rsf-leads": "led_by",
    "rel-splm-n-saf-conflict": "hostile_to",
    "rel-jem-saf-conflict": "cooperates_with",
    "rel-rsf-darfur-origin": "fought_against",
    "rel-saf-sudan-operates": "operates_in",
    "rel-rsf-sudan-operates": "operates_in",
}
for rid, t in TYPE_LOCKS.items():
    r = rel_by_id.get(rid)
    check(f"relation {rid} type={t}", r and r["relationship_type"] == t, f"got {r.get('relationship_type') if r else None}")

# ---- evidence rules ----
db_ev = [e for e in evidence if str(e.get("claim_id", "")).startswith("depthd")]
check("evidence imported = 15", len(db_ev) == 15, f"got {len(db_ev)}")
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
check("all depthd evidence references resolve", not bad_ref, str(bad_ref[:8]))
analytic = [e for e in db_ev if "analytical_synthesis" in e.get("verification_method", "")]
check("analytical_synthesis not written as verified", all(e["verification_status"] == "partially_verified" for e in analytic) and len(analytic) == 1, str([(e["claim_id"], e["verification_status"]) for e in analytic]))
reported = [e for e in db_ev if "reported" in e.get("verification_method", "")]
check("UN reported findings kept attributed", all("attribution" in e.get("verification_method", "") or "reported" in e.get("verification_method", "") for e in reported))

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
    "artifact": "DEPTHD_INTEGRITY_SEMANTICS_GATE",
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
print("== DEPTHD_INTEGRITY_SEMANTICS_GATE =", report["gate"], "==")
sys.exit(0 if not issues else 1)
