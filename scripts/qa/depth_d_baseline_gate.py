#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH D baseline gate + target probe. Confirms Depth C closed baseline
(13/72/150/249, sources=137, evidence=245) and inspects the 6 entity / 8
relation targets for current maturity, type locks, freshness."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-d"
QA.mkdir(parents=True, exist_ok=True)

ok, issues = [], []

def load(name):
    return json.load(open(DATA / name, encoding="utf-8"))

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
ok.append(f"countries={len(countries)}")
ok.append(f"non-country entities={len(non_country)}")
ok.append(f"relationships={len(rels)}")
ok.append(f"routes={metrics.get('route_count')}")
ok.append(f"sources={len(sources)}")
ok.append(f"evidence={len(evidence)}")

if len(countries) != 13: issues.append(f"countries={len(countries)} != 13")
if len(non_country) != 72: issues.append(f"entities={len(non_country)} != 72")
if len(rels) != 150: issues.append(f"relationships={len(rels)} != 150")
if metrics.get("route_count") != 249: issues.append(f"routes={metrics.get('route_count')} != 249")
if len(sources) != 137: issues.append(f"sources={len(sources)} != 137")
if len(evidence) != 245: issues.append(f"evidence={len(evidence)} != 245")

# schema stability
ENT_M = {"E0_STUB","E1_BASIC","E2_DEVELOPED","E3_FULL_ENCYCLOPEDIA"}
REL_M = {"R0_EDGE_ONLY","R1_BASIC","R2_DEVELOPED_RELATIONSHIP","R3_FULL_RELATIONSHIP_INTELLIGENCE"}
bad = [eid for eid, pr in ep.items() if pr.get("content_maturity") and pr["content_maturity"] not in ENT_M]
bad_r = [rid for rid, pr in rp.items() if pr.get("relation_maturity") and pr["relation_maturity"] not in REL_M]
ok.append(f"entity maturity enum stable ({'PASS' if not bad else bad[:3]})")
ok.append(f"relation maturity enum stable ({'PASS' if not bad_r else bad_r[:3]})")
if bad or bad_r:
    issues.append("schema drift in maturity enums")

ENTS = ["actor-saf","actor-rsf","person-abdel-fattah-al-burhan","person-mohamed-hamdan-dagalo","actor-splm-n-al-hilu","actor-jem"]
RELS = ["rel-saf-rsf-war","rel-burhan-saf-leads","rel-dagalo-rsf-leads","rel-splm-n-saf-conflict",
        "rel-jem-saf-conflict","rel-rsf-darfur-origin","rel-saf-sudan-operates","rel-rsf-sudan-operates"]

probe = {"entities": {}, "relations": {}}
for eid in ENTS:
    e = next((x for x in entities if x["entity_id"] == eid), None)
    pr = ep.get(eid, {})
    probe["entities"][eid] = {"exists": e is not None, "maturity": pr.get("content_maturity"),
                              "freshness": e.get("freshness_status") if e else None,
                              "sections": len(pr.get("sections", {})), "imported_by": pr.get("imported_by")}
    if e is None:
        issues.append(f"entity target missing: {eid}")
rel_by_id = {r["relationship_id"]: r for r in rels}
for rid in RELS:
    r = rel_by_id.get(rid)
    pr = rp.get(rid, {})
    probe["relations"][rid] = {"exists": r is not None, "type": r.get("relationship_type") if r else None,
                               "maturity": pr.get("relation_maturity"),
                               "src": r.get("source_entity_id") if r else None, "tgt": r.get("target_entity_id") if r else None,
                               "tl": len(tl.get(rid, []))}
    if r is None:
        issues.append(f"relation target missing: {rid}")

report = {
    "artifact": "DEPTHD_BASELINE_GATE",
    "ok": ok, "issues": issues,
    "gate": "PASS" if not issues else "OPEN",
    "probe": probe,
    "baseline": {"source_sha": "46abaed", "countries": len(countries), "entities": len(non_country),
                 "relationships": len(rels), "routes": metrics.get("route_count"),
                 "sources": len(sources), "evidence": len(evidence)},
}
json.dump(report, open(QA / "baseline-gate.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

for line in ok: print("  OK", line)
for line in issues: print("  !!", line)
print("== entities ==")
for eid, v in probe["entities"].items():
    print(f"  {eid}: exists={v['exists']} maturity={v['maturity']} freshness={v['freshness']} secs={v['sections']}")
print("== relations ==")
for rid, v in probe["relations"].items():
    print(f"  {rid}: exists={v['exists']} type={v['type']} maturity={v['maturity']} tl={v['tl']}")
print("== DEPTHD_BASELINE_GATE =", report["gate"], "==")
sys.exit(0 if not issues else 1)
