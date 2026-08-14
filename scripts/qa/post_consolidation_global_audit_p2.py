# -*- coding: utf-8 -*-
"""
Post-Consolidation Global Audit — Phase 2 (READ-ONLY).

Classifies all 95 P1 relations (and checks P2 entities) into
FINAL_MUST_FIX / HIGH_VALUE_DEPTH / ADEQUATE_FOR_ROLE / DEFER_FUTURE,
plus core-actor / core-relationship / theater readiness and a Pack B
scope simulation. Never modifies knowledge data.
"""
import json
import io
import os
import re
import sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "data/intelligence/africa"
OUT = "qa-artifacts-post-consolidation-global-audit-p2"
os.makedirs(OUT, exist_ok=True)


def load(name):
    return json.load(open(os.path.join(BASE, name + ".json"), encoding="utf-8"))


def write(name, obj):
    io.open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n").write(
        json.dumps(obj, ensure_ascii=False, indent=2))


def _tl(v):
    if isinstance(v, str):
        return len(v)
    if isinstance(v, list):
        return sum(len(str(x)) for x in v)
    if isinstance(v, dict):
        n = 0
        for kk in ("p", "list", "timeline", "table"):
            if v.get(kk):
                n += sum(len(str(x)) for x in v[kk])
        return n
    return 0


entities = load("entities")["entities"]
relationships = load("relationships")["relationships"]
entity_profiles = load("entity_profiles")["profiles"]
relation_profiles = load("relation_profiles")["profiles"]
relation_timelines = load("relation_timelines")["timelines"]
sources = load("sources")["sources"]
evidence = load("evidence_records")["evidence"]
alias_index = load("alias_index")["aliases"]
countries = load("countries")["countries"]

entity_by_id = {e["entity_id"]: e for e in entities}
rel_by_id = {r["relationship_id"]: r for r in relationships}
source_id_set = {s["source_id"] for s in sources}
country_id_set = {c["country_id"] for c in countries}

# reverse evidence index
ev_by_relation = defaultdict(list)
ev_by_entity = defaultdict(list)
for ev in evidence:
    for rid in (ev.get("relation_ids") or []):
        ev_by_relation[rid].append(ev["evidence_id"])
    for eid in (ev.get("entity_ids") or []):
        ev_by_entity[eid].append(ev["evidence_id"])

# graph degree
adj = defaultdict(set)
for r in relationships:
    s, t = r["source_entity_id"], r["target_entity_id"]
    adj[s].add(r["relationship_id"])
    adj[t].add(r["relationship_id"])


def degree(eid):
    return len(adj.get(eid, set()))


def r3_degree(eid):
    return sum(1 for rid in adj.get(eid, set())
               if (relation_profiles.get(rid) or {}).get("relation_maturity") == "R3_FULL_RELATIONSHIP_INTELLIGENCE")


# relation role classification
ROLE_MAP = {
    "operates_in": "SIMPLE_STRUCTURAL",
    "active_in_region": "SIMPLE_STRUCTURAL",
    "member_of_force": "SIMPLE_STRUCTURAL",
    "deployed_in": "SIMPLE_STRUCTURAL",
    "political_affiliation": "SIMPLE_STRUCTURAL",
    "cross_border_link": "SIMPLE_STRUCTURAL",
    "criminal_link": "SIMPLE_STRUCTURAL",
    "constituent_of": "STRATEGIC",
    "pledged_allegiance_to": "STRATEGIC",
    "split_from": "STRATEGIC",
    "merged_from": "STRATEGIC",
    "part_of_network": "STRATEGIC",
    "led_by": "STRATEGIC",
    "founded_by": "STRATEGIC",
    "fought_against": "OPERATIONAL",
    "hostile_to": "OPERATIONAL",
    "cooperates_with": "OPERATIONAL",
    "allied_with": "OPERATIONAL",
    "competes_with": "OPERATIONAL",
    "supports": "OPERATIONAL",
    "supported_by": "OPERATIONAL",
    "alleged_support": "OPERATIONAL",
    "historically_associated_with": "HISTORICAL_CONTEXT",
}

REL_SECTIONS = ("overview", "formation_background", "evolution_stages", "current_status",
                "why_it_matters", "uncertainties", "asip_analysis", "watch_indicators")

# Reuse the Global Audit (Phase 1 / Pack A) grading results to guarantee the
# exact same P1 population (95) — do NOT recompute grades here.
_RA = os.path.join("qa-artifacts-final-depth-consolidation-a")
_rel_audit = json.load(open(os.path.join(_RA, "relationship-depth-audit.json"), encoding="utf-8"))
_ent_audit = json.load(open(os.path.join(_RA, "entity-depth-audit.json"), encoding="utf-8"))
rel_grade_map = {r["relation_id"]: r for r in _rel_audit["relationships"]}
ent_grade_map = {e["entity_id"]: e for e in _ent_audit["entities"]}


def relation_grade(rid):
    r = rel_grade_map.get(rid)
    return r["grade"] if r else "R-D"


def entity_grade(eid):
    e = ent_grade_map.get(eid)
    return e["grade"] if e else "D"

# core lists
CORE_ACTORS = [
    "actor-jnim", "actor-aqim", "actor-al-shabaab", "actor-isis-somalia", "actor-is-sahel",
    "actor-iswap", "actor-jas", "actor-is-mozambique", "actor-adf-isis-ca", "actor-ansarul-islam",
    "actor-katiba-macina", "actor-africa-corps", "actor-mnjtf", "actor-fu-aes", "actor-fadm",
    "actor-rdf-mozambique", "actor-africom", "actor-lna",
]

CORE_RELATIONS = [
    ("actor-jnim", "actor-aqim"), ("actor-jnim", "actor-is-sahel"),
    ("actor-jnim", "actor-ansarul-islam"), ("actor-jnim", "actor-katiba-macina"),
    ("actor-isis-somalia", "actor-islamic-state"), ("actor-is-mozambique", "actor-islamic-state"),
    ("actor-adf-isis-ca", "actor-islamic-state"), ("actor-iswap", "actor-islamic-state"),
    ("actor-jas", "actor-iswap"), ("actor-africa-corps", "actor-wagner-group"),
    ("actor-fu-aes", "actor-jnim"), ("actor-fu-aes", "actor-is-sahel"),
    ("actor-mnjtf", "actor-iswap"), ("actor-mnjtf", "actor-jas"),
    ("actor-fadm", "actor-is-mozambique"), ("actor-rdf-mozambique", "actor-is-mozambique"),
    ("actor-africom", "actor-al-shabaab"), ("actor-africom", "actor-isis-somalia"),
    ("actor-fla", "actor-jnim"), ("actor-lna", "actor-isis-libya"),
]

# theater mapping (entity -> theater)
THEATER_ENTITIES = {
    "Sahel": ["actor-jnim", "actor-is-sahel", "actor-ansarul-islam", "actor-katiba-macina",
              "actor-katiba-serma", "actor-dan-na-ambassagou", "actor-dozos-of-macina",
              "actor-dana-atem", "actor-fla", "actor-hcua", "actor-fu-aes", "actor-g5-sahel-joint-force"],
    "Lake Chad": ["actor-mnjtf", "actor-iswap", "actor-jas", "actor-lakurawa", "actor-bbmb"],
    "Somalia/Horn": ["actor-al-shabaab", "actor-isis-somalia", "actor-africom", "actor-aussom",
                     "actor-somali-national-armed-forces", "actor-puntland-security-forces"],
    "Mozambique": ["actor-is-mozambique", "actor-fadm", "actor-rdf-mozambique", "actor-samim",
                   "actor-tanzania-tpdf"],
    "DRC/Uganda": ["actor-adf-isis-ca", "actor-fardc", "actor-updf", "actor-monusco"],
    "Libya/North Africa": ["actor-lna", "actor-isis-libya", "actor-isis-sinai"],
    "Sudan": ["actor-rsf", "actor-saf", "actor-slm-aw", "actor-splm-io", "actor-splm-n-al-hilu"],
    "Coastal West Africa": ["actor-niger-armed-forces", "actor-benin-forces", "actor-nigeria-army",
                            "actor-ecowas-standby-force"],
}


def profile_chars(rid):
    p = relation_profiles.get(rid, {})
    return sum(len(str(p.get(k) or "")) for k in REL_SECTIONS)


def main():
    # =================================================================
    # P1 population (re-generate with same logic)
    # =================================================================
    p1 = []
    for r in relationships:
        rid = r["relationship_id"]
        g = relation_grade(rid)
        if g in ("R-C", "R-D"):
            au = rel_grade_map[rid]
            p1.append({
                "target_id": rid, "target_type": "relation",
                "source": au["source"], "target": au["target"],
                "relation_type": au["relation_type"],
                "relation_tier": au["maturity"],
                "current_grade": g,
                "profile_chars": au["profile_chars"],
                "sections_present": au["sections_present"],
                "timeline_count": au["timeline_nodes"],
                "source_count": au["source_count"],
                "evidence_count": au["evidence_count"],
                "current_status": r.get("current_status"),
                "time_sensitive": r.get("temporal_sensitive"),
                "disputed": r.get("disputed"),
            })
    p1.sort(key=lambda x: x["profile_chars"])
    write("p1-population.json", {"artifact": "p1-population",
                                 "P1_TOTAL": len(p1), "items": p1})
    print("P1_TOTAL =", len(p1))

    # =================================================================
    # Relation-tier consistency audit
    # =================================================================
    tier_audit = {"R3_BUT_SIMPLE_EDGE": [], "R1_BUT_STRATEGIC_RELATION": [],
                  "R2_BUT_STRATEGIC_RELATION": [], "R3_AND_GENUINELY_STRATEGIC": []}
    for r in relationships:
        rid = r["relationship_id"]
        p = relation_profiles.get(rid, {})
        maturity = p.get("relation_maturity")
        role = ROLE_MAP.get(r["relationship_type"], "OPERATIONAL")
        if maturity == "R3_FULL_RELATIONSHIP_INTELLIGENCE" and role == "SIMPLE_STRUCTURAL":
            tier_audit["R3_BUT_SIMPLE_EDGE"].append(rid)
        elif maturity == "R1_SIMPLE_SOURCED_RELATION" and role in ("STRATEGIC", "TIME_SENSITIVE_STRATEGIC"):
            tier_audit["R1_BUT_STRATEGIC_RELATION"].append(rid)
        elif maturity == "R2_DEVELOPED_RELATIONSHIP" and role == "STRATEGIC":
            tier_audit["R2_BUT_STRATEGIC_RELATION"].append(rid)
        elif maturity == "R3_FULL_RELATIONSHIP_INTELLIGENCE" and role in ("STRATEGIC", "OPERATIONAL"):
            tier_audit["R3_AND_GENUINELY_STRATEGIC"].append(rid)
    write("relation-tier-consistency-audit.json",
          {"artifact": "relation-tier-consistency-audit", **tier_audit,
           "counts": {k: len(v) for k, v in tier_audit.items()}})
    print("  R3_BUT_SIMPLE_EDGE =", len(tier_audit["R3_BUT_SIMPLE_EDGE"]),
          "| R1_BUT_STRATEGIC =", len(tier_audit["R1_BUT_STRATEGIC_RELATION"]),
          "| R2_BUT_STRATEGIC =", len(tier_audit["R2_BUT_STRATEGIC_RELATION"]))

    # =================================================================
    # Core actor readiness
    # =================================================================
    def entity_readiness(eid):
        g = entity_grade(eid)
        if g == "A":
            return "READY"
        if g == "B":
            return "READY_MINOR_GAPS"
        return "NOT_READY"
    core_actors = {}
    for eid in CORE_ACTORS:
        e = entity_by_id.get(eid)
        if not e:
            core_actors[eid] = {"status": "MISSING", "readiness": "NOT_READY"}
            continue
        core_actors[eid] = {
            "readiness": entity_readiness(eid),
            "current_status": e.get("current_status"),
            "depth": (entity_profiles.get(eid) or {}).get("profile_depth"),
        }
    write("core-actor-readiness.json", {"artifact": "core-actor-readiness",
                                       "actors": core_actors,
                                       "counts": dict(Counter(v["readiness"] for v in core_actors.values()))})
    print("  core actor READY =", sum(1 for v in core_actors.values() if v["readiness"] == "READY"),
          "| MINOR_GAPS =", sum(1 for v in core_actors.values() if v["readiness"] == "READY_MINOR_GAPS"),
          "| NOT_READY =", sum(1 for v in core_actors.values() if v["readiness"] == "NOT_READY"))

    # =================================================================
    # Core relationship readiness
    # =================================================================
    core_rels = {}
    for s, t in CORE_RELATIONS:
        matches = [r for r in relationships
                   if (r["source_entity_id"] == s and r["target_entity_id"] == t)
                   or (r["source_entity_id"] == t and r["target_entity_id"] == s)]
        if not matches:
            core_rels[f"{s} <-> {t}"] = {"found": False, "readiness": "NOT_READY"}
            continue
        rid = matches[0]["relationship_id"]
        g = relation_grade(rid)
        maturity = (relation_profiles.get(rid) or {}).get("relation_maturity")
        readiness = "READY" if g == "R-A" else ("READY_MINOR_GAPS" if g == "R-B" else "NOT_READY")
        core_rels[f"{s} <-> {t}"] = {"found": True, "relation_id": rid, "grade": g,
                                     "tier": maturity, "readiness": readiness}
    write("core-relationship-readiness.json", {"artifact": "core-relationship-readiness",
                                               "relations": core_rels,
                                               "counts": dict(Counter(v["readiness"] for v in core_rels.values()))})
    print("  core rel READY =", sum(1 for v in core_rels.values() if v["readiness"] == "READY"),
          "| MINOR_GAPS =", sum(1 for v in core_rels.values() if v["readiness"] == "READY_MINOR_GAPS"),
          "| NOT_READY =", sum(1 for v in core_rels.values() if v["readiness"] == "NOT_READY"))

    # =================================================================
    # P1 relation triage
    # =================================================================
    final_must_fix = set()
    high_value = set()
    core_rel_ids = {v["relation_id"] for v in core_rels.values() if v.get("found")}
    core_rel_ids_ready = {v["relation_id"] for v in core_rels.values()
                          if v.get("found") and v["readiness"] in ("READY", "READY_MINOR_GAPS")}
    not_ready_core = {v["relation_id"] for v in core_rels.values()
                      if v.get("found") and v["readiness"] == "NOT_READY"}

    triage = []
    for item in p1:
        rid = item["target_id"]
        role = ROLE_MAP.get(item["relation_type"], "OPERATIONAL")
        r = rel_by_id[rid]
        time_sensitive = r.get("temporal_sensitive")
        historical = any(k in (r.get("current_status") or "") for k in ("historical", "ceased", "closed", "ended"))
        is_core = rid in core_rel_ids
        is_core_not_ready = rid in not_ready_core

        # classification
        cls = "ADEQUATE_FOR_ROLE"
        borderline = False
        reasons = []
        if role == "SIMPLE_STRUCTURAL" and not item["disputed"]:
            cls = "ADEQUATE_FOR_ROLE"
            reasons.append("simple structural edge (operates_in/member_of/deployed_in)")
        elif role == "HISTORICAL_CONTEXT" and historical:
            cls = "ADEQUATE_FOR_ROLE"
            reasons.append("historical-context edge, adequate for lineage")
        elif is_core_not_ready:
            cls = "FINAL_MUST_FIX"
            reasons.append("core relationship NOT_READY")
        elif item["relation_tier"] == "R3_FULL_RELATIONSHIP_INTELLIGENCE" and role == "STRATEGIC" and item["current_grade"] in ("R-C", "R-D"):
            if item["profile_chars"] < 400:
                cls = "FINAL_MUST_FIX"
                reasons.append("R3 strategic with thin profile")
            else:
                cls = "HIGH_VALUE_DEPTH"
                borderline = True
                reasons.append("R3 strategic, borderline depth")
        elif item["relation_tier"] == "R3_FULL_RELATIONSHIP_INTELLIGENCE" and time_sensitive and item["profile_chars"] < 400:
            cls = "FINAL_MUST_FIX"
            reasons.append("R3 time-sensitive thin profile")
        elif role in ("STRATEGIC", "OPERATIONAL") and item["relation_tier"] in ("R2_DEVELOPED_RELATIONSHIP", "R3_FULL_RELATIONSHIP_INTELLIGENCE"):
            cls = "HIGH_VALUE_DEPTH"
            reasons.append("operational/strategic relation with depth upside")
        elif role == "SIMPLE_STRUCTURAL":
            cls = "ADEQUATE_FOR_ROLE"
            reasons.append("structural edge, low information gain from expansion")
        else:
            cls = "DEFER_FUTURE"
            reasons.append("peripheral/historical, low strategic value")

        if cls == "FINAL_MUST_FIX":
            final_must_fix.add(rid)
        elif cls == "HIGH_VALUE_DEPTH":
            high_value.add(rid)

        # borderline: core-actor-involving leadership/allegiance relations at the
        # HIGH_VALUE_DEPTH / ADEQUATE boundary (they are core facts, but simple
        # leadership need not be a full R3 dossier).
        if role == "STRATEGIC" and item["relation_type"] in ("led_by", "pledged_allegiance_to", "founded_by") \
           and (item["source"] in CORE_ACTORS or item["target"] in CORE_ACTORS) \
           and cls in ("HIGH_VALUE_DEPTH", "ADEQUATE_FOR_ROLE"):
            borderline = True

        triage.append({
            "target_id": rid, "target_type": "relation",
            "current_grade": item["current_grade"], "role_class": role,
            "relation_tier": item["relation_tier"],
            "network_importance": "high" if rid in core_rel_ids else "normal",
            "current_relevance": "HISTORICAL" if historical else ("CURRENT" if time_sensitive else "CURRENT"),
            "evidence_sufficiency": ("STRONG" if item["evidence_count"] >= 2 else "ADEQUATE" if item["evidence_count"] >= 1 else "LIMITED"),
            "gap_codes": ["THIN_PROFILE"] if item["profile_chars"] < 300 else [],
            "final_classification": cls,
            "borderline_review": borderline,
            "reason": "; ".join(reasons),
            "recommended_scope": "relation dossier" if cls in ("FINAL_MUST_FIX", "HIGH_VALUE_DEPTH") else "none",
            "requires_new_external_research": item["evidence_count"] == 0,
        })

    # entity P1 triage: P1 has no entities (grade D = 0); but P2 grade-C entities
    # are checked for escalation in p2-escalation-check.
    write("entity-p1-triage.json", {"artifact": "entity-p1-triage",
                                    "ENTITY_P1_COUNT": 0,
                                    "note": "Pack A cleared all grade-D entities; no entity in P1"})
    write("relation-p1-triage.json", {"artifact": "relation-p1-triage",
                                      "RELATION_P1_COUNT": len(triage), "items": triage})
    write("p1-final-triage.json", {"artifact": "p1-final-triage", "items": triage,
                                   "counts": dict(Counter(t["final_classification"] for t in triage))})
    print("  P1 triage:", dict(Counter(t["final_classification"] for t in triage)))

    # =================================================================
    # final-must-fix evidence readiness
    # =================================================================
    fmf = []
    for t in triage:
        if t["final_classification"] == "FINAL_MUST_FIX":
            fmf.append(t)
    fmf_evidence = []
    for t in fmf:
        sufficiency = "EXISTING_EVIDENCE_SUFFICIENT" if t["evidence_sufficiency"] in ("STRONG", "ADEQUATE") else "NEW_RESEARCH_REQUIRED"
        fmf_evidence.append({"target_id": t["target_id"], "evidence_sufficiency": t["evidence_sufficiency"],
                             "readiness": sufficiency})
    write("final-must-fix-evidence-readiness.json", {
        "artifact": "final-must-fix-evidence-readiness",
        "FINAL_MUST_FIX_COUNT": len(fmf),
        "NEW_RESEARCH_REQUIRED_COUNT": sum(1 for e in fmf_evidence if e["readiness"] == "NEW_RESEARCH_REQUIRED"),
        "EXISTING_EVIDENCE_SUFFICIENT_COUNT": sum(1 for e in fmf_evidence if e["readiness"] == "EXISTING_EVIDENCE_SUFFICIENT"),
        "items": fmf_evidence})
    print("  FINAL_MUST_FIX =", len(fmf))

    # =================================================================
    # Pack B simulation
    # =================================================================
    dist = Counter(t["final_classification"] for t in triage)
    fmf_count = len(fmf)
    if fmf_count == 0:
        rec = "SKIP"
    elif fmf_count <= 5:
        rec = "MICRO"
    elif fmf_count <= 15:
        rec = "SMALL"
    elif fmf_count <= 30:
        rec = "MEDIUM"
    else:
        rec = "REVIEW_REQUIRED"
    fmf_relation = fmf_count  # all P1 are relations
    fmf_entity = 0
    pack_b = {
        "artifact": "pack-b-scope-simulation",
        "FINAL_MUST_FIX_COUNT": fmf_count,
        "ENTITY_COUNT": fmf_entity,
        "RELATION_COUNT": fmf_relation,
        "NEW_RESEARCH_REQUIRED_COUNT": sum(1 for e in fmf_evidence if e["readiness"] == "NEW_RESEARCH_REQUIRED"),
        "EXISTING_EVIDENCE_SUFFICIENT_COUNT": sum(1 for e in fmf_evidence if e["readiness"] == "EXISTING_EVIDENCE_SUFFICIENT"),
        "HIGH_VALUE_DEPTH_COUNT": dist["HIGH_VALUE_DEPTH"],
        "ADEQUATE_FOR_ROLE_COUNT": dist["ADEQUATE_FOR_ROLE"],
        "DEFER_FUTURE_COUNT": dist["DEFER_FUTURE"],
        "PACK_B_RECOMMENDATION": rec,
        "final_must_fix_ids": [t["target_id"] for t in fmf],
        "high_value_depth_ids": sorted(high_value),
    }
    write("pack-b-scope-simulation.json", pack_b)
    print("  PACK_B_RECOMMENDATION =", rec)

    # =================================================================
    # P2 escalation check
    # =================================================================
    p2 = json.load(open("qa-artifacts-final-depth-consolidation-a/final-consolidation-candidate-list.json", encoding="utf-8"))
    p2_items = [c for c in p2["candidates"] if c["priority"] == "P2"]
    escalation = []
    for c in p2_items:
        eid = c["target_id"]
        if eid in CORE_ACTORS:
            # a core actor in P2 (grade C or low-evidence) is a potential
            # mis-prioritization — flag for ChatGPT review.
            g = entity_grade(eid)
            ec = len(ev_by_entity.get(eid, []))
            escalation.append({"target_id": eid, "entity_grade": g,
                               "evidence_count": ec,
                               "reason": f"core actor in P2 (grade {g}, evidence {ec})"})
    write("p2-escalation-check.json", {"artifact": "p2-escalation-check",
                                       "P2_TOTAL": len(p2_items),
                                       "P2_ESCALATION_CANDIDATE": escalation,
                                       "note": "escalation candidates listed for ChatGPT review; not auto-modified"})
    print("  P2 escalation candidates =", len(escalation))

    # =================================================================
    # PPT coverage check
    # =================================================================
    ppt = json.load(open("qa-artifacts-final-depth-consolidation-a/ppt-final-coverage-audit.json", encoding="utf-8"))
    write("ppt-coverage-check.json", {
        "artifact": "ppt-coverage-check",
        "PPT_NAMES_UNRESOLVED": ppt.get("PPT_NAMES_UNRESOLVED", 0),
        "PPT_RESOLUTION_CONFLICT_COUNT": ppt.get("PPT_RESOLUTION_CONFLICT_COUNT", 0),
        "note": "de-formalized persons are not PPT entities; coverage unchanged",
    })

    # =================================================================
    # Theater readiness
    # =================================================================
    theater = {}
    for name, eids in THEATER_ENTITIES.items():
        rows = []
        for eid in eids:
            if eid in entity_by_id:
                rows.append({"entity_id": eid, "readiness": entity_readiness(eid)})
        r_counts = Counter(r["readiness"] for r in rows)
        core_rels_count = sum(1 for rid in core_rel_ids_ready
                              if any(entity_by_id.get(eid) and eid in eids
                                     for eid in [rel_by_id[rid]["source_entity_id"], rel_by_id[rid]["target_entity_id"]]))
        if r_counts.get("NOT_READY", 0) > 0:
            readiness = "NEEDS_FINAL_CONSOLIDATION"
        elif r_counts.get("READY_MINOR_GAPS", 0) > 0:
            readiness = "READY_WITH_MINOR_GAPS"
        else:
            readiness = "READY"
        theater[name] = {
            "core_entities": len(rows),
            "readiness": readiness,
            "entity_readiness": dict(r_counts),
            "core_relations_ready": core_rels_count,
        }
    write("theater-readiness.json", {"artifact": "theater-readiness", "theaters": theater})

    # =================================================================
    # baseline summary
    # =================================================================
    summary = {
        "artifact": "baseline-summary",
        "P1_TOTAL": len(p1),
        "P1_CLASSIFIED_COUNT": len(triage),
        "P1_UNCLASSIFIED_COUNT": len(p1) - len(triage),
        "classification_counts": dict(dist),
        "BORDERLINE_REVIEW_COUNT": sum(1 for t in triage if t["borderline_review"]),
        "FINAL_MUST_FIX_COUNT": fmf_count,
        "NEW_RESEARCH_REQUIRED_COUNT": pack_b["NEW_RESEARCH_REQUIRED_COUNT"],
        "core_actor_readiness": dict(Counter(v["readiness"] for v in core_actors.values())),
        "core_relationship_readiness": dict(Counter(v["readiness"] for v in core_rels.values())),
        "PACK_B_RECOMMENDATION": rec,
        "KNOWLEDGE_DATA_CHANGED": "PENDING post-phase2 hash",
    }
    write("baseline-summary.json", summary)

    print("\n== PHASE 2 SUMMARY ==")
    for k, v in summary.items():
        print("  ", k, "=", v)


if __name__ == "__main__":
    main()
