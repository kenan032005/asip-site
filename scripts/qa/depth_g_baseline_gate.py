#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH G baseline gate. Confirms Depth F closed baseline
(13/72/150/249, sources=182, evidence=297) and re-derives the residual findings
independently so any undocumented knowledge-object drift trips
DEPTHG_BASELINE_KNOWLEDGE_DRIFT before any write happens."""
import json, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-g"
QA.mkdir(parents=True, exist_ok=True)

ok, issues, drift = [], [], []


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
counts = {
    "countries": len(countries),
    "non_country_entities": len(non_country),
    "relationships": len(rels),
    "routes": metrics.get("route_count"),
    "sources": len(sources),
    "evidence": len(evidence),
}
EXPECTED = {"countries": 13, "non_country_entities": 72, "relationships": 150,
            "routes": 249, "sources": 182, "evidence": 297}
for k, v in EXPECTED.items():
    got = counts[k]
    ok.append(f"{k}={got}")
    if got != v:
        drift.append(f"{k}={got} != baseline {v}")

# ---- schema enum stability -------------------------------------------------
ENT_M = {"E0_STUB", "E1_BASIC", "E2_DEVELOPED", "E3_FULL_ENCYCLOPEDIA"}
REL_M = {"R0_EDGE_ONLY", "R1_BASIC", "R2_DEVELOPED_RELATIONSHIP",
         "R3_FULL_RELATIONSHIP_INTELLIGENCE"}
bad_e = [k for k, p in ep.items() if p.get("content_maturity") and p["content_maturity"] not in ENT_M]
bad_r = [k for k, p in rp.items() if p.get("relation_maturity") and p["relation_maturity"] not in REL_M]
ok.append(f"entity maturity enum stable ({'PASS' if not bad_e else bad_e[:3]})")
ok.append(f"relation maturity enum stable ({'PASS' if not bad_r else bad_r[:3]})")
if bad_e or bad_r:
    drift.append("schema drift in maturity enums")

# ---- residual findings re-derivation ---------------------------------------
ent_ids = [e["entity_id"] for e in non_country]
no_ent_mat = sorted(eid for eid in ent_ids if not ep.get(eid, {}).get("content_maturity"))
rel_ids = [r["relationship_id"] for r in rels]
no_rel_mat = sorted(rid for rid in rel_ids if not rp.get(rid, {}).get("relation_maturity"))

# staleness uses the same definition as the Depth F residual audit: the
# object's own freshness_status marker, not a re-derived date heuristic.
stale = sorted(r["relationship_id"] for r in rels if r.get("freshness_status") == "stale")
stale_entities = sorted(e["entity_id"] for e in non_country if e.get("freshness_status") == "stale")

# summary-only relationships (Depth F definition): claims R2/R3 maturity but the
# profile carries no asip_analysis, no evolution_stages and a sub-60-char overview.
summary_only = sorted(
    rid for rid, pr in rp.items()
    if pr.get("relation_maturity") in ("R2_DEVELOPED_RELATIONSHIP", "R3_FULL_RELATIONSHIP_INTELLIGENCE")
    and not pr.get("asip_analysis") and not pr.get("evolution_stages")
    and len(pr.get("overview", "") or "") < 60)

src_le1_e = sorted(e["entity_id"] for e in non_country if len(e.get("source_refs") or []) <= 1)
src_le1_r = sorted(r["relationship_id"] for r in rels if len(r.get("source_refs") or []) <= 1)

# duplicate (src,tgt,type) candidates
pairs = {}
for r in rels:
    key = (r.get("source_entity_id"), r.get("target_entity_id"), r.get("relationship_type"))
    pairs.setdefault(key, []).append(r["relationship_id"])
dups = {".".join(str(x) for x in k): v for k, v in pairs.items() if len(v) > 1}

# L1 entities below E3 floor
L1_below = sorted(e["entity_id"] for e in non_country
                  if e.get("importance_level") == "L1"
                  and ep.get(e["entity_id"], {}).get("content_maturity") != "E3_FULL_ENCYCLOPEDIA")

derived = {
    "entities_without_content_maturity": len(no_ent_mat),
    "relationships_without_relation_maturity": len(no_rel_mat),
    "stale_relationships_mechanical": len(stale),
    "source_refs_le_1_entities": len(src_le1_e),
    "source_refs_le_1_relationships": len(src_le1_r),
    "summary_only_relationships": len(summary_only),
    "L1_below_maturity_floor": L1_below,
    "duplicate_candidate_groups": dups,
}

MANIFEST_EXPECT = {
    "entities_without_content_maturity": 20,
    "relationships_without_relation_maturity": 82,
    "stale_relationships_mechanical": 29,
    "source_refs_le_1_entities": 20,
    "source_refs_le_1_relationships": 77,
    "summary_only_relationships": 15,
}
for k, v in MANIFEST_EXPECT.items():
    got = derived[k]
    if got != v:
        issues.append(f"residual {k}={got} != manifest {v}")
    else:
        ok.append(f"residual {k}={got} (matches manifest)")

if L1_below != ["actor-katiba-hanifa"]:
    issues.append(f"L1_below_maturity_floor={L1_below} != ['actor-katiba-hanifa']")
else:
    ok.append("L1_below_maturity_floor = ['actor-katiba-hanifa'] (matches manifest)")

exp_dup = {"rel-jnim-is-hostile", "rel-jnim-is-conflict"}
dup_sets = [set(v) for v in dups.values()]
if exp_dup not in dup_sets:
    issues.append(f"expected duplicate candidate group missing; groups={dups}")
else:
    ok.append("duplicate candidate group = {rel-jnim-is-hostile, rel-jnim-is-conflict}")
extra_dups = [v for v in dups.values() if set(v) != exp_dup]
if extra_dups:
    issues.append(f"unexpected duplicate groups: {extra_dups}")

# ---- target existence probe (no writes) ------------------------------------
MAN = json.load(open(Path(sys.argv[1]), encoding="utf-8")) if len(sys.argv) > 1 else None
ENT_T = MAN["entity_targets"] if MAN else []
REL_T = MAN["core_relation_targets"] if MAN else []
rel_by_id = {r["relationship_id"]: r for r in rels}
ent_by_id = {e["entity_id"]: e for e in entities}

probe = {"entities": {}, "relations": {}}
for eid in ENT_T:
    e = ent_by_id.get(eid)
    pr = ep.get(eid, {})
    probe["entities"][eid] = {
        "exists": e is not None,
        "importance_level": e.get("importance_level") if e else None,
        "maturity": pr.get("content_maturity"),
        "freshness": e.get("freshness_status") if e else None,
        "source_refs": len(e.get("source_refs") or []) if e else None,
        "sections": len(pr.get("sections") or {}),
    }
    if e is None:
        drift.append(f"entity target missing: {eid}")
for rid in REL_T:
    r = rel_by_id.get(rid)
    pr = rp.get(rid, {})
    probe["relations"][rid] = {
        "exists": r is not None,
        "type": r.get("relationship_type") if r else None,
        "maturity": pr.get("relation_maturity"),
        "src": r.get("source_entity_id") if r else None,
        "tgt": r.get("target_entity_id") if r else None,
        "source_refs": len(r.get("source_refs") or []) if r else None,
        "timeline_events": len(tl.get(rid, []) or []),
        "stale": rid in stale,
        "summary_only": rid in summary_only,
    }
    if r is None:
        drift.append(f"relation target missing: {rid}")

# ---- un-jnim-2018 pollution census (read-only) -----------------------------
pollution = {"entities": [], "relationships": []}
for e in non_country:
    if "un-jnim-2018" in (e.get("source_refs") or []):
        pollution["entities"].append(e["entity_id"])
for r in rels:
    if "un-jnim-2018" in (r.get("source_refs") or []):
        pollution["relationships"].append(r["relationship_id"])
ok.append(f"un-jnim-2018 refs: {len(pollution['entities'])} entities / {len(pollution['relationships'])} relationships")

gate = "PASS" if not issues and not drift else ("DRIFT" if drift else "OPEN")
report = {
    "artifact": "DEPTHG_BASELINE_GATE",
    "gate": gate,
    "stop_condition": "DEPTHG_BASELINE_KNOWLEDGE_DRIFT" if drift else None,
    "baseline_expected": EXPECTED,
    "baseline_actual": counts,
    "derived_residual": derived,
    "manifest_expected_residual": MANIFEST_EXPECT,
    "lists": {
        "entities_without_content_maturity": no_ent_mat,
        "relationships_without_relation_maturity": no_rel_mat,
        "stale_relationships_mechanical": stale,
        "stale_entities": stale_entities,
        "summary_only_relationships": summary_only,
        "source_refs_le_1_entities": src_le1_e,
        "source_refs_le_1_relationships": src_le1_r,
    },
    "un_jnim_2018_pollution": pollution,
    "probe": probe,
    "ok": ok,
    "issues": issues,
    "drift": drift,
}
json.dump(report, open(QA / "baseline-gate.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

for line in ok:
    print("  OK", line)
for line in issues:
    print("  !!", line)
for line in drift:
    print("  XX DRIFT:", line)
print("== DEPTHG_BASELINE_GATE =", gate, "==")
sys.exit(0 if gate == "PASS" else 1)
