#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH B integrity & semantics gate. Asserts count invariants (13/72/150),
the 5 fact-cleanup groups (ISWAP leadership, JAS-ISIS pledge history, malformed
relation repair, MNJTF sectors, Cameroon source cleanup), Ansaru semantics,
Lakurawa disputed lock, evidence status rules, and dist consistency."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
DIST = ROOT / "dist" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-b"
QA.mkdir(parents=True, exist_ok=True)

ok, issues = [], []

def load(name, base=DATA):
    with open(base / name, encoding="utf-8") as f:
        return json.load(f)

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

# ---- count invariants ----
check = lambda label, cond, detail="": (ok.append(f"{label} ({detail})") if cond else issues.append(f"{label}: {detail}"))
check("countries=13", len(countries) == 13, f"got {len(countries)}")
check("non-country entities=72", len(non_country) == 72, f"got {len(non_country)}")
check("relationships=150", len(rels) == 150, f"got {len(rels)}")
check("routes=249", metrics.get("route_count") == 249, f"got {metrics.get('route_count')}")

# ---- GROUP A: ISWAP leadership ----
iswap_text = json.dumps(ep.get("actor-iswap", {}).get("sections", {}), ensure_ascii=False)
jas_text = json.dumps(ep.get("actor-jas", {}).get("sections", {}), ensure_ascii=False)
check("ISWAP: no al-Barnawi=Bakura identity", "巴库拉（Abu Musab al-Barnawi）" not in iswap_text and "Abu Musab al-Barnawi（巴库拉）" not in iswap_text and "巴库拉（Abu Musab al-Barnawi）" not in jas_text)
# "2021确认死亡" only allowed in negated context (packet: '没有支持...这一精确结论')
import re as _re
pos_2021 = _re.search(r"2021年确认死亡", iswap_text)
negated_2021 = "没有支持" in iswap_text and "2021年确认死亡" in iswap_text
check("ISWAP: no uncontested '2021 confirmed death'", pos_2021 is None or (negated_2021 and "al-Barnawi" not in iswap_text.split("2021年确认死亡")[0][-80:]) or "没有支持" in iswap_text[:iswap_text.find("2021年确认死亡")+1] if "2021年确认死亡" in iswap_text else True, "2021 death only appears in negated context")
check("ISWAP: Ba'a Shuwa reported current leader", "Ba'a Shuwa" in iswap_text and ("报告" in iswap_text or "reported" in iswap_text), "Ba'a Shuwa mention present")
check("ISWAP: member-state divergence preserved", "分歧" in iswap_text)

# ---- GROUP B: JAS-ISIS pledge history ----
jas_full = json.dumps({"sections": ep.get("actor-jas", {}).get("sections", {}), "rel": rel_by_id.get("rel-jas-islamic-state-hostile")}, ensure_ascii=False)
check("JAS: 'never joined ISIS' residual = 0", "JAS 未加入伊斯兰国体系" not in jas_full and "JAS从未加入伊斯兰国体系" not in jas_full)
check("JAS: 2015 pledge present", "2015" in jas_text and ("宣誓效忠" in jas_text or "效忠" in jas_text))
check("JAS: current unaffiliated stated", "不隶属于" in jas_text)

# ---- GROUP C: malformed relation repair ----
mal = rel_by_id.get("rel-jas-islamic-state-hostile")
check("repair: rel exists with legacy id", mal is not None)
if mal:
    check("repair: target = actor-islamic-state", mal["target_entity_id"] == "actor-islamic-state", mal["target_entity_id"])
    check("repair: type = pledged_allegiance_to", mal["relationship_type"] == "pledged_allegiance_to", mal["relationship_type"])
    check("repair: time 2015-03-07..2016-08-03", mal.get("time_start") == "2015-03-07" and mal.get("time_end") == "2016-08-03", f"{mal.get('time_start')}..{mal.get('time_end')}")
    check("repair: current_status historical_pledge", mal.get("current_status") == "historical_pledge_recognition_shifted_to_iswap", mal.get("current_status"))
    check("repair: freshness historical", mal.get("freshness_status") == "historical", mal.get("freshness_status"))
    check("repair: direction unidirectional", mal.get("direction") == "unidirectional", mal.get("direction"))
# JAS->Islamic State relation count: exactly one JAS->IS pledged_allegiance_to
jas_is = [r for r in rels if r["source_entity_id"] == "actor-jas" and r["target_entity_id"] == "actor-islamic-state" and r["relationship_type"] == "pledged_allegiance_to"]
check("repair: exactly one JAS->IS pledge relation", len(jas_is) == 1, f"got {len(jas_is)}")
# no duplicate JAS->ISWAP hostile (the old malformed duplicate is gone)
jas_iswap_hostile = [r for r in rels if r["source_entity_id"] == "actor-jas" and r["target_entity_id"] == "actor-iswap" and r["relationship_type"] == "hostile_to"]
check("no malformed duplicate JAS->ISWAP hostile relation", len(jas_iswap_hostile) == 1, f"got {len(jas_iswap_hostile)} (should be the single legit rel-jas-iswap-conflict)")

# ---- GROUP D: MNJTF sectors ----
mnjtf_text = json.dumps(ep.get("actor-mnjtf", {}).get("sections", {}), ensure_ascii=False)
check("MNJTF: Sector1 Cameroon/Mora", "Sector 1—Mora, Cameroon" in mnjtf_text or "Sector 1" in mnjtf_text and "Cameroon" in mnjtf_text and "Mora" in mnjtf_text)
check("MNJTF: Sector2 Chad/Bagasola", "Bagasola" in mnjtf_text and "Chad" in mnjtf_text)
check("MNJTF: Sector3 Nigeria/Monguno", "Monguno" in mnjtf_text and "Nigeria" in mnjtf_text)
check("MNJTF: Sector4 Niger/Diffa", "Diffa" in mnjtf_text and "Niger" in mnjtf_text)
check("MNJTF: no Nigeria Sector1", "Nigeria Sector 1" not in mnjtf_text and "尼日利亚 Sector 1" not in mnjtf_text)
check("MNJTF: no Cameroon Sector3", "Cameroon Sector 3" not in mnjtf_text and "喀麦隆 Sector 3" not in mnjtf_text)
check("MNJTF: Niger withdrawal reflected", "退出" in mnjtf_text and "troop-contributing" in mnjtf_text)
check("MNJTF: Sector 4 disrupted", "Sector 4" in mnjtf_text and ("冲击" in mnjtf_text or "削弱" in mnjtf_text or "operationally disrupted" in mnjtf_text))
check("MNJTF: Force Commander Audu", "Saidu Tanko Audu" in mnjtf_text)
# sector mapping on member relations
cam_rel = rel_by_id.get("rel-cameroon-mnjtf-member")
niger_rel = rel_by_id.get("rel-nigeria-mnjtf-member")
if cam_rel and rp.get("rel-cameroon-mnjtf-member"):
    cam_prof = json.dumps(rp["rel-cameroon-mnjtf-member"], ensure_ascii=False)
    check("Cameroon-MNJTF: Sector1 in profile", "Sector 1" in cam_prof and "Mora" in cam_prof)

# ---- GROUP E: Cameroon source cleanup ----
for rid in ("rel-cameroon-army-jas", "rel-cameroon-army-iswap"):
    r = rel_by_id.get(rid)
    if r:
        check(f"{rid}: un-jnim-2018 removed", "un-jnim-2018" not in r.get("source_refs", []), str(r.get("source_refs")))
        check(f"{rid}: Lake Chad sources present", len(r.get("source_refs", [])) >= 2, str(r.get("source_refs")))

# ---- entity maturity ----
E3 = {"actor-jas", "actor-iswap", "actor-mnjtf"}
E2 = {"actor-nigeria-army", "actor-chad-army", "actor-cameroon-army", "actor-lakurawa", "actor-ansaru"}
for eid in sorted(E3 | E2):
    pr = ep.get(eid)
    expect = "E3_FULL_ENCYCLOPEDIA" if eid in E3 else "E2_DEVELOPED"
    check(f"entity {eid} maturity={expect}", pr is not None and pr.get("content_maturity") == expect, f"got {pr.get('content_maturity') if pr else None}")
    if pr:
        secs = pr.get("sections", {})
        check(f"entity {eid} has asip_analysis", bool(secs.get("asip_analysis")))
        check(f"entity {eid} has watch_indicators", bool(secs.get("watch_indicators")))

# ---- relation maturity ----
R3 = {"rel-jas-iswap-conflict", "rel-jas-islamic-state-hostile", "rel-iswap-islamic-state-affiliation"}
for rid in sorted(R3):
    pr = rp.get(rid)
    check(f"relation {rid} maturity=R3", pr is not None and pr.get("relation_maturity") == "R3_FULL_RELATIONSHIP_INTELLIGENCE", f"got {pr.get('relation_maturity') if pr else None}")
for rid in ("rel-nigeria-mnjtf-member", "rel-chad-mnjtf-member", "rel-cameroon-mnjtf-member",
            "rel-cameroon-army-jas", "rel-cameroon-army-iswap", "rel-d1-ansaru-jas-split",
            "rel-d1-ansaru-aqim-allegiance", "rel-d1-ansaru-jnim-affiliation"):
    pr = rp.get(rid)
    check(f"relation {rid} maturity=R2", pr is not None and pr.get("relation_maturity") == "R2_DEVELOPED_RELATIONSHIP", f"got {pr.get('relation_maturity') if pr else None}")

# ---- relation type locks ----
for rid, etype in (("rel-jas-iswap-conflict", "hostile_to"), ("rel-iswap-islamic-state-affiliation", "pledged_allegiance_to")):
    r = rel_by_id.get(rid)
    check(f"relation {rid} type={etype}", r is not None and r["relationship_type"] == etype, f"got {r.get('relationship_type') if r else None}")
check("JAS-ISWAP stays hostile_to", rel_by_id.get("rel-jas-iswap-conflict", {}).get("relationship_type") == "hostile_to")

# ---- Ansaru semantics ----
ansaru_jnim = rel_by_id.get("rel-d1-ansaru-jnim-affiliation")
check("Ansaru->JNIM stays affiliated_with", ansaru_jnim is not None and ansaru_jnim["relationship_type"] == "affiliated_with", f"got {ansaru_jnim.get('relationship_type') if ansaru_jnim else None}")
check("Ansaru->JNIM not constituent_of", "constituent_of" not in json.dumps(rel_by_id.get("rel-d1-ansaru-jnim-affiliation", {}), ensure_ascii=False))

# ---- Lakurawa disputed lock ----
lak = [r for r in rels if r["source_entity_id"] == "actor-lakurawa" or r["target_entity_id"] == "actor-lakurawa"]
lak_iss = [r for r in lak if r["target_entity_id"] == "actor-is-sahel"]
check("Lakurawa->IS Sahel part_of_network+disputed", len(lak_iss) == 1 and lak_iss[0]["relationship_type"] == "part_of_network" and lak_iss[0].get("disputed") is True, str([(r["relationship_type"], r.get("disputed")) for r in lak_iss]))
lak_text = json.dumps(ep.get("actor-lakurawa", {}).get("sections", {}), ensure_ascii=False)
check("Lakurawa: ISSP claim strengthened but scoped", "ISSP" in lak_text and "不能把所有历史" in lak_text)

# ---- evidence status rules ----
db_ev = [e for e in evidence if str(e.get("claim_id", "")).startswith("depthb")]
check("evidence imported = 17", len(db_ev) == 17, f"got {len(db_ev)}")
analytic = [e for e in db_ev if "analytical_synthesis" in e.get("verification_method", "")]
check("analytical_synthesis not written as verified", all(e["verification_status"] == "partially_verified" for e in analytic) and len(analytic) == 1, str([(e["claim_id"], e["verification_status"]) for e in analytic]))
est = [e for e in db_ev if "verified_estimate" in e.get("verification_method", "")]
check("verified_estimate kept as estimate claim_type", all(e["claim_type"] == "estimate" for e in est), str([(e["claim_id"], e["claim_type"]) for e in est]))
# every depthb evidence references resolvable sources/entities/relations
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
check("all depthb evidence references resolve", not bad_ref, str(bad_ref[:8]))

# ---- total evidence/sources scale ----
check("sources = 137", len(sources) == 137, f"got {len(sources)}")
check("evidence = 231", len(evidence) == 231, f"got {len(evidence)}")

# ---- dist consistency (if dist exists) ----
if DIST.exists():
    for f in ("countries.json", "entities.json", "relationships.json", "sources.json", "evidence_records.json", "entity_profiles.json", "relation_profiles.json", "relation_timelines.json", "catalog_metrics.json"):
        try:
            a = load(f)
            b = load(f, DIST / "data")
            same = a == b
            check(f"dist/data/{f} in sync", same)
        except Exception as ex:
            issues.append(f"dist/data/{f} read error: {ex}")

report = {
    "artifact": "DEPTHB_INTEGRITY_SEMANTICS_GATE",
    "ok": ok, "issues": issues,
    "gate": "PASS" if not issues else "OPEN",
    "scale": {"countries": len(countries), "entities": len(non_country), "relationships": len(rels),
              "sources": len(sources), "evidence": len(evidence),
              "profiles": len(rp), "timelines": len(tl), "routes": metrics.get("route_count")},
}
with open(QA / "integrity-gate.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"checks: {len(ok)} ok, {len(issues)} issues")
for line in ok:
    print("  OK", line)
for line in issues:
    print("  !!", line)
print("== DEPTHB_INTEGRITY_SEMANTICS_GATE =", report["gate"], "==")
sys.exit(0 if not issues else 1)
