#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH F integrity & semantics gate. Asserts count invariants, the 8 fact/
semantic cleanup groups, entity/relation maturity targets, the count-preserving
repair proof, evidence rules, and dist consistency."""
import json, sys, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
DIST = ROOT / "dist" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-f"
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
ent_by_id = {e["entity_id"]: e for e in entities}

check = lambda label, cond, detail="": (ok.append(f"{label} ({detail})") if cond else issues.append(f"{label}: {detail}"))
check("countries=13", len(countries) == 13, f"got {len(countries)}")
check("non-country entities=72", len(non_country) == 72, f"got {len(non_country)}")
check("relationships=150", len(rels) == 150, f"got {len(rels)}")
check("routes=249", metrics.get("route_count") == 249, f"got {metrics.get('route_count')}")
check("sources=182", len(sources) == 182, f"got {len(sources)}")
check("evidence=297", len(evidence) == 297, f"got {len(evidence)}")

# ---- A. Machar current status ----
machar = json.dumps(ep.get("person-riek-machar", {}).get("sections", {}), ensure_ascii=False)
e_machar = ent_by_id.get("person-riek-machar", {})
check("Machar status=suspended First VP", "被暂停的第一副总统" in machar or "暂停第一副总统" in machar or "suspended First Vice-President" in machar)
check("Machar status=house arrest/detention", "软禁" in machar and ("拘押" in machar or "拘留" in machar or "detained" in machar))
check("Machar status=trial ongoing", "审判" in machar and ("继续" in machar or "2026" in machar))
check("Machar current_status override", "suspended_first_vice_president" in str(e_machar.get("current_status", "")), str(e_machar.get("current_status")))
check("Machar not plain active", "active" not in str(e_machar.get("current_status", "")) or "suspended" in str(e_machar.get("current_status", "")))

# ---- A2. Machar charges != conviction ----
check("Machar no conviction language", "已定罪" not in machar and "司法定罪" not in machar and "被判有罪" not in machar)
check("Machar charges attributed", "指控" in machar and ("否认" in machar or "政府检方" in machar or "检方指控" in machar))

# ---- A3. Machar SPLM/A-IO leadership with fragmented command ----
rel_machar = rel_by_id.get("rel-machar-splm-io-leads")
check("Machar-SPLM-IO led_by", rel_machar and rel_machar["relationship_type"] == "led_by", f"got {rel_machar.get('relationship_type') if rel_machar else None}")
check("Machar-SPLM-IO fragmented command", "fragmented" in str(rel_machar.get("current_status", "")) or "fragmented" in json.dumps(rp.get("rel-machar-splm-io-leads", {}), ensure_ascii=False) or "碎片化" in json.dumps(rp.get("rel-machar-splm-io-leads", {}), ensure_ascii=False))

# ---- B. South Sudan 2026 ----
sspdf = json.dumps(ep.get("actor-sspdf", {}).get("sections", {}), ensure_ascii=False)
splm_io = json.dumps(ep.get("actor-splm-io", {}).get("sections", {}), ensure_ascii=False)
nas = json.dumps(ep.get("actor-nas", {}).get("sections", {}), ensure_ascii=False)
check("SSPDF-SPLM-IO 2026 conflict", "2026" in sspdf and "重新" in sspdf and "Jonglei" in sspdf)
check("SPLM-IO fragmentation", "分裂" in splm_io or "splinter" in splm_io or "fragmentation" in splm_io)
check("NAS cooperation", "MoU" in nas or "2026年3月" in nas or "合作" in nas)
check("NAS-SPLM-IO allied_with", rel_by_id.get("rel-nas-splm-io-allied", {}).get("relationship_type") == "allied_with")
check("NAS no merger", "合并" not in nas or "不合并" in nas)
check("R-ARCSS referenced framework", "R-ARCSS" in sspdf and ("框架" in sspdf or "唯一可行" in sspdf))
check("SPLM-IO-SSPDF hostile_to", rel_by_id.get("rel-splm-io-sspdf-conflict", {}).get("relationship_type") == "hostile_to")

# ---- C. ISM lineage ----
ism = json.dumps(ep.get("actor-is-mozambique", {}).get("sections", {}), ensure_ascii=False)
check("ISM ISCAP lineage", "ISCAP" in ism)
check("ISM not ISWAP branch", "不是ISWAP分支" in ism or "并非ISWAP" in ism or "而不是ISWAP" in ism or "不是ISWAP" in ism)
check("ISM 2022 Mozambique province", "2022" in ism and "province" in ism)
check("no ISM->ISWAP association in rel profiles", "ISWAP" not in json.dumps(rp.get("rel-is-moz-islamic-state", {}), ensure_ascii=False) or "不是" in json.dumps(rp.get("rel-is-moz-islamic-state", {}), ensure_ascii=False))

# ---- D. count-preserving repair ----
ism2 = rel_by_id.get("rel-is-moz-islamic-state2")
check("repair: legacy id retained", ism2 and ism2["relationship_id"] == "rel-is-moz-islamic-state2")
check("repair: src=actor-rdf-mozambique", ism2 and ism2["source_entity_id"] == "actor-rdf-mozambique", f"got {ism2.get('source_entity_id') if ism2 else None}")
check("repair: tgt=actor-is-mozambique", ism2 and ism2["target_entity_id"] == "actor-is-mozambique", f"got {ism2.get('target_entity_id') if ism2 else None}")
check("repair: type=fought_against", ism2 and ism2["relationship_type"] == "fought_against", f"got {ism2.get('relationship_type') if ism2 else None}")
check("repair: time_start=2021", ism2 and ism2.get("time_start") == "2021", f"got {ism2.get('time_start') if ism2 else None}")
check("repair: current_status", ism2 and ism2.get("current_status") == "active_counterinsurgency_conflict", f"got {ism2.get('current_status') if ism2 else None}")
check("repair: total still 150", len(rels) == 150)
# no residual ISM->ISWAP historically_associated_with
residual = [r for r in rels if r["source_entity_id"] == "actor-is-mozambique" and r["target_entity_id"] == "actor-iswap"]
check("no residual ISM->ISWAP edge", len(residual) == 0, str([r["relationship_id"] for r in residual]))

# ---- E. SAMIM / TPDF ----
samim = json.dumps(ep.get("actor-samim", {}).get("sections", {}), ensure_ascii=False)
e_samim = ent_by_id.get("actor-samim", {})
check("SAMIM ended 2024-07-15", "2024年7月15日" in samim or "2024-07-15" in samim or "2024年7月" in samim)
check("SAMIM freshness=historical", e_samim.get("freshness_status") == "historical", f"got {e_samim.get('freshness_status')}")
check("SAMIM status historical", "historical" in str(e_samim.get("current_status", "")), str(e_samim.get("current_status")))
check("TPDF-SAMIM member historical", rel_by_id.get("rel-tanzania-samim-member", {}).get("freshness_status") == "historical", f"got {rel_by_id.get('rel-tanzania-samim-member', {}).get('freshness_status')}")
check("SAMIM-FADM cooperate historical", rel_by_id.get("rel-samim-fadm-cooperate", {}).get("freshness_status") == "historical")
check("TPDF bilateral current", rel_by_id.get("rel-tanzania-mozambique-cooperate", {}).get("freshness_status") == "current")
check("TPDF entity current", ent_by_id.get("actor-tanzania-tpdf", {}).get("freshness_status") == "current")

# ---- F. Tanzania source pollution ----
for rid in ("rel-tanzania-tpdf-is-moz", "rel-tanzania-mozambique-cooperate", "rel-tanzania-samim-member"):
    r = rel_by_id.get(rid)
    check(f"{rid} no un-jnim-2018", r and "un-jnim-2018" not in r.get("source_refs", []), str(r.get("source_refs")) if r else "missing")
e_tpdf = ent_by_id.get("actor-tanzania-tpdf", {})
check("actor-tanzania-tpdf no un-jnim-2018", "un-jnim-2018" not in e_tpdf.get("source_refs", []), str(e_tpdf.get("source_refs")))

# ---- G. Rwanda naming ----
rdf = json.dumps(ep.get("actor-rdf-mozambique", {}).get("sections", {}), ensure_ascii=False)
check("RDF Mozambique naming distinct", "Rwanda" in rdf and ("绝不" in rdf or "不能" in rdf or "不得" in rdf) and ("Sudan Rapid Support" in rdf or "Sudan RSF" in rdf or "苏丹快速支援" in rdf))
check("no RDF-RSF conflation", "Sudan RSF" not in rdf.split("绝不能")[0] if "绝不能" in rdf else True)

# ---- H. Libya ----
lna = json.dumps(ep.get("actor-lna", {}).get("sections", {}), ensure_ascii=False)
gnu = json.dumps(ep.get("actor-gnu-forces", {}).get("sections", {}), ensure_ascii=False)
isis_ly = json.dumps(ep.get("actor-isis-libya", {}).get("sections", {}), ensure_ascii=False)
rel_lna_gnu = rp.get("rel-lna-gnu-rivalry", {})
check("LNA-GNU ceasefire semantics", "2020" in lna and "停火" in lna)
check("LNA-GNU not full-scale war", "全面战争" not in lna or "不是" in lna)
check("LNA-GNU rivalry status", rel_by_id.get("rel-lna-gnu-rivalry", {}).get("current_status") == "political_military_rivalry_under_2020_ceasefire", str(rel_by_id.get("rel-lna-gnu-rivalry", {}).get("current_status")))
check("ISIS-Libya facilitative role", "facilitative" in isis_ly or "facilitation" in isis_ly or "便利" in isis_ly)
check("ISIS-Libya limited territorial control", "limited" in isis_ly.lower() or "有限" in isis_ly)
check("ISIS-Libya-LNA residual hostility", rel_by_id.get("rel-isis-libya-lna-conflict", {}).get("current_status") == "residual_security_hostility_after_historical_combat", str(rel_by_id.get("rel-isis-libya-lna-conflict", {}).get("current_status")))

# ---- entity maturity ----
E3 = {"actor-sspdf","actor-splm-io","person-salva-kiir","person-riek-machar","actor-is-mozambique",
      "actor-fadm","actor-rdf-mozambique","actor-lna","actor-gnu-forces"}
E2 = {"actor-nas","actor-samim","actor-tanzania-tpdf","actor-isis-libya"}
for eid in E3:
    pr = ep.get(eid, {})
    check(f"entity {eid} maturity=E3", pr.get("content_maturity") == "E3_FULL_ENCYCLOPEDIA", f"got {pr.get('content_maturity')}")
    check(f"entity {eid} has asip_analysis", bool(pr.get("sections", {}).get("asip_analysis")))
for eid in E2:
    pr = ep.get(eid, {})
    check(f"entity {eid} maturity=E2", pr.get("content_maturity") == "E2_DEVELOPED", f"got {pr.get('content_maturity')}")

# ---- relation maturity ----
R3 = {"rel-splm-io-sspdf-conflict","rel-machar-splm-io-leads","rel-is-moz-islamic-state","rel-is-moz-islamic-state2",
      "rel-fadm-is-moz-hostile","rel-lna-gnu-rivalry"}
R2 = {"rel-kiir-sspdf-leads","rel-nas-splm-io-allied","rel-rdf-mozambique-fadm-cooperate","rel-samim-fadm-cooperate",
      "rel-is-moz-tanzania-link","rel-fadm-mozambique-operates","rel-is-moz-mozambique-operates",
      "rel-tanzania-tpdf-is-moz","rel-tanzania-mozambique-cooperate","rel-tanzania-samim-member",
      "rel-isis-libya-affiliation","rel-isis-libya-lna-conflict"}
for rid in R3:
    pr = rp.get(rid, {})
    check(f"relation {rid} maturity=R3", pr.get("relation_maturity") == "R3_FULL_RELATIONSHIP_INTELLIGENCE", f"got {pr.get('relation_maturity')}")
for rid in R2:
    pr = rp.get(rid, {})
    check(f"relation {rid} maturity=R2", pr.get("relation_maturity") == "R2_DEVELOPED_RELATIONSHIP", f"got {pr.get('relation_maturity')}")

# ---- evidence rules ----
db_ev = [e for e in evidence if str(e.get("claim_id", "")).startswith("depthf")]
check("evidence imported = 24", len(db_ev) == 24, f"got {len(db_ev)}")
bad_ref = []
for e in db_ev:
    if e["source_id"] not in {s["source_id"] for s in sources}:
        bad_ref.append(f"{e['claim_id']}:src")
    for eid in e.get("entity_ids", []):
        if eid not in ent_by_id:
            bad_ref.append(f"{e['claim_id']}:ent:{eid}")
    for rid in e.get("relation_ids", []):
        if rid not in rel_by_id:
            bad_ref.append(f"{e['claim_id']}:rel:{rid}")
check("all depthf evidence references resolve", not bad_ref, str(bad_ref[:8]))
legal = [e for e in db_ev if "legal_status" in e.get("verification_method", "")]
check("legal status evidence attributed (ev-005)", len(legal) == 1 and legal[0]["claim_id"] == "depthf-ev-005", str([e["claim_id"] for e in legal]))
selfsrc = [e for e in db_ev if "self-publication" in e.get("verification_method", "")]
check("self-source MoU limited (ev-007)", len(selfsrc) == 1 and selfsrc[0]["claim_id"] == "depthf-ev-007", str([e["claim_id"] for e in selfsrc]))
dc = [e for e in db_ev if "analytical_data_correction" in e.get("verification_method", "")]
check("data correction not verified fact (ev-024)", len(dc) == 1 and dc[0]["verification_status"] == "partially_verified", str([(e["claim_id"], e["verification_status"]) for e in dc]))
est = [e for e in db_ev if "verified_estimate" in e.get("verification_method", "")]
check("estimate retained (ev-008)", len(est) == 1 and est[0]["claim_id"] == "depthf-ev-008", str([e["claim_id"] for e in est]))

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
    "artifact": "DEPTHF_INTEGRITY_SEMANTICS_GATE",
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
print("== DEPTHF_INTEGRITY_SEMANTICS_GATE =", report["gate"], "==")
sys.exit(0 if not issues else 1)
