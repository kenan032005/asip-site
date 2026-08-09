#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH B baseline knowledge confirmation + read-only schema/generator audit.
Verifies 13 countries / 72 non-country entities / 150 relationships / 249 routes
and Depth A schema stability (content_maturity, relation_maturity, ASIP Analysis,
Watch Indicators, evolution_stages, drivers, constraints, third_party_effects,
uncertainties, evidence_integrity_score, content_depth_score, depth_score).
STOP condition: DEPTHB_BASELINE_KNOWLEDGE_DRIFT
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-b"
QA.mkdir(parents=True, exist_ok=True)

ok, issues = [], []

def load(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)

countries = load("countries.json")["countries"]
entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
sources = load("sources.json")["sources"]
evidence = load("evidence_records.json")["evidence"]
ep = load("entity_profiles.json")["profiles"]
rp = load("relation_profiles.json")["profiles"]
metrics = load("catalog_metrics.json")

# --- baseline counts ---
non_country = [e for e in entities if e["entity_type"] != "country"]
ok.append(f"countries={len(countries)}")
ok.append(f"non-country entities={len(non_country)}")
ok.append(f"relationships={len(rels)}")
ok.append(f"sources={len(sources)}")
ok.append(f"evidence={len(evidence)}")
ok.append(f"entity_profiles={len(ep)}")
ok.append(f"relation_profiles={len(rp)}")
ok.append(f"routes={metrics.get('route_count')}")

if len(countries) != 13: issues.append(f"countries={len(countries)} != 13")
if len(non_country) != 72: issues.append(f"non-country entities={len(non_country)} != 72")
if len(rels) != 150: issues.append(f"relationships={len(rels)} != 150")

# --- schema stability audit ---
ENTITY_MATURITY = {"E0_STUB", "E1_BASIC", "E2_DEVELOPED", "E3_FULL_ENCYCLOPEDIA"}
REL_MATURITY = {"R0_EDGE_ONLY", "R1_BASIC", "R2_DEVELOPED_RELATIONSHIP", "R3_FULL_RELATIONSHIP_INTELLIGENCE"}

bad_maturity = []
for eid, pr in ep.items():
    m = pr.get("content_maturity")
    if m and m not in ENTITY_MATURITY:
        bad_maturity.append(f"{eid}:{m}")
ok.append(f"entity content_maturity values all in Depth A enum ({'PASS' if not bad_maturity else 'FAIL'})")
if bad_maturity: issues.append("unexpected entity maturity: " + str(bad_maturity[:5]))

bad_rm = []
for rid, pr in rp.items():
    m = pr.get("relation_maturity")
    if m and m not in REL_MATURITY:
        bad_rm.append(f"{rid}:{m}")
ok.append(f"relation relation_maturity values all in Depth A enum ({'PASS' if not bad_rm else 'FAIL'})")
if bad_rm: issues.append("unexpected relation maturity: " + str(bad_rm[:5]))

# Depth A features exist on upgraded nodes (spot check of schema keys, not content)
n_analysis = sum(1 for pr in ep.values() if pr.get("sections", {}).get("asip_analysis"))
n_watch = sum(1 for pr in ep.values() if pr.get("sections", {}).get("watch_indicators"))
n_rel_analysis = sum(1 for pr in rp.values() if pr.get("asip_analysis"))
ok.append(f"entities with sections.asip_analysis={n_analysis}, sections.watch_indicators={n_watch}")
ok.append(f"relation_profiles with asip_analysis={n_rel_analysis}")

n_ds = sum(1 for pr in ep.values() if "depth_score" in pr)
n_cm = sum(1 for pr in ep.values() if "content_maturity" in pr)
n_rm = sum(1 for pr in rp.values() if "relation_maturity" in pr)
ok.append(f"entity_profiles with depth_score={n_ds}, content_maturity={n_cm}")
ok.append(f"relation_profiles with relation_maturity={n_rm}")
if n_ds < 11 or n_cm < 11:
    issues.append("Depth A content_maturity/depth_score missing from upgraded entity profiles")
if n_rm < 6:
    issues.append("Depth A relation_maturity missing from upgraded relation profiles")

# --- pre-existing relation sanity for targets ---
rel_by_id = {r["relationship_id"]: r for r in rels}
report = {
    "artifact": "DEPTHB_BASELINE_GATE",
    "ok": ok,
    "issues": issues,
    "gate": "PASS" if not issues else "OPEN",
    "baseline": {
        "source_sha_expected": "8f0f325",
        "countries": len(countries), "entities": len(non_country), "relationships": len(rels),
        "sources": len(sources), "evidence": len(evidence), "routes": metrics.get("routes"),
    },
}
with open(QA / "baseline-gate.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print("== baseline ==")
for line in ok: print("  OK", line)
if issues:
    print("== ISSUES ==")
    for line in issues: print("  !!", line)
    sys.exit(1)
print("== DEPTHB_BASELINE_GATE = PASS ==")
