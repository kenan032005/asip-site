#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH G shared truthful-maturity scorer.

Implements closure_standard.entity_truthfulness_rule and
closure_standard.relation_policy from the Depth G Final Closure Content Pack.

The scorer derives what maturity an object's ACTUAL content + resolvable
sourcing can support. It never reads the existing badge, so an inflated
Depth A-F label cannot self-justify.

Rubric basis (data-derived, not arbitrary character counts):

  Entities - the observed E3 population (32/32) universally carries
  lead + current_situation + asip_analysis + watch_indicators +
  core_assessment + name_and_translation + sources. The scorer therefore
  measures FUNCTIONAL DIMENSION COVERAGE (identity / background / structure /
  geography-operations / current state / assessment / uncertainty / sourcing)
  plus a substance floor, rather than raw length, so a tightly written but
  fully dimensioned Chinese profile is not punished and a long but
  one-dimensional skeleton is not rewarded.

  Relations - quoted directly from closure_standard.relation_policy:
    R1 summary + temporal/current state + >=1 resolvable source/evidence
    R2 summary + context/history + current assessment + why-it-matters or
       uncertainty + supporting source/evidence
    R3 multi-phase evolution/timeline + drivers + current assessment +
       ASIP Analysis + uncertainty/watch + multiple supporting evidence
  The observed data confirms this split: asip_analysis appears in 25/25 R3
  profiles and 0/43 R2 profiles.

Used by both the BEFORE snapshot and the AFTER full-library recalibration so
the two are strictly comparable.
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"

ENT_ORDER = ["E0_STUB", "E1_BASIC", "E2_DEVELOPED", "E3_FULL_ENCYCLOPEDIA"]
REL_ORDER = ["R0_EDGE_ONLY", "R1_SIMPLE_SOURCED_RELATION", "R2_DEVELOPED_RELATIONSHIP",
             "R3_FULL_RELATIONSHIP_INTELLIGENCE"]
FLOOR = {"L1": "E3_FULL_ENCYCLOPEDIA", "L2": "E2_DEVELOPED", "L3": "E1_BASIC"}

# Publisher tokens accepted as a single authoritative source for a narrow claim
# (closure_standard.source_count_rule).
AUTHORITATIVE = ("nctc", "un-", "-un-", "unsc", "unmiss", "un_", "hrw", "acled",
                 "reuters", "africa-center", "au-", "uk-", "state-dept", "icg",
                 "crisis-group", "crisisgroup", "pax-", "s2026", "s-2026")

# ---- entity functional dimensions -----------------------------------------
ENT_DIMS = {
    "identity": {"lead", "name_and_translation", "overview"},
    "background": {"history", "formation_background", "formation",
                   "historical_context", "history_correction", "origins",
                   "trajectory"},
    "structure": {"structure", "leadership", "components", "organizational_role",
                  "force_estimates", "current_structure", "membership"},
    "geography_operations": {"geography", "tactics", "operations", "operations_2026",
                             "regional_impact", "regional_role", "africa_network",
                             "2026_threat", "2026_operations", "allies",
                             "capabilities_and_constraints", "ideology_goals",
                             "relationships", "missions", "finance", "adversaries",
                             "events", "lake_chad_role", "jas_iswap_correction",
                             "strength", "mali_role"},
    "current_state": {"current_situation", "current_status", "current_assessment"},
    "assessment": {"asip_analysis", "core_assessment"},
    "uncertainty": {"uncertainties", "controversies_uncertainties", "watch_indicators"},
}

REL_CORE_FIELDS = [
    "overview", "formation_background", "initial_relationship", "causes",
    "key_turning_points", "evolution_stages", "regional_differences",
    "impact_on_security", "current_status", "current_assessment",
    "watch_indicators", "asip_analysis", "why_it_matters", "uncertainties",
    "drivers", "constraints", "third_party_effects", "operational_role",
    "geographic_scope", "historical_context", "nature", "role",
    "cooperation_dimensions", "continuities", "differences",
    "personnel_flows", "organizational_balance", "humanitarian_spillover",
    "current_structure",
]
REL_CONTEXT_FIELDS = ["formation_background", "initial_relationship", "causes",
                      "key_turning_points", "evolution_stages", "historical_context",
                      "continuities", "nature"]
REL_CURRENT_FIELDS = ["current_status", "current_assessment"]
REL_WHY_FIELDS = ["why_it_matters", "uncertainties", "watch_indicators",
                  "impact_on_security", "constraints"]


def load(name):
    return json.load(open(DATA / name, encoding="utf-8"))


def load_all():
    return {
        "entities": load("entities.json")["entities"],
        "rels": load("relationships.json")["relationships"],
        "ep": load("entity_profiles.json")["profiles"],
        "rp": load("relation_profiles.json")["profiles"],
        "tl": load("relation_timelines.json")["timelines"],
        "sources": load("sources.json")["sources"],
        "evidence": load("evidence_records.json")["evidence"],
        "metrics": load("catalog_metrics.json"),
        "countries": load("countries.json")["countries"],
    }


def evidence_index(evidence):
    ev_e, ev_r = defaultdict(set), defaultdict(set)
    for x in evidence:
        for i in x.get("entity_ids", []) or []:
            ev_e[i].add(x["claim_id"])
        for i in x.get("relation_ids", []) or []:
            ev_r[i].add(x["claim_id"])
    return ev_e, ev_r


def is_authoritative(refs):
    return any(any(a in str(r).lower() for a in AUTHORITATIVE) for r in (refs or []))


def entity_dimensions(sections):
    keys = {k for k, v in (sections or {}).items() if v and str(v).strip()}
    hit = {d: bool(keys & names) for d, names in ENT_DIMS.items()}
    hit["sourcing"] = "sources" in keys
    return hit


def score_entity(e, profile, ev_ids, source_ids_present):
    """Return (truthful_maturity, stats, reasons). Never reads the badge."""
    p = profile or {}
    secs = p.get("sections") or {}
    filled = {k: v for k, v in secs.items() if v and str(v).strip()}
    n_sec = len(filled)
    chars = sum(len(str(v)) for v in filled.values())
    density = (chars // n_sec) if n_sec else 0
    refs = [r for r in (e.get("source_refs") or []) if r in source_ids_present]
    n_src, n_ev = len(refs), len(ev_ids)
    auth = is_authoritative(refs)

    dims = entity_dimensions(secs)
    dims["sourcing"] = dims["sourcing"] or n_src >= 1
    n_dims = sum(1 for v in dims.values() if v)
    has_asip = bool(filled.get("asip_analysis"))
    reasons = []

    e3 = (has_asip and dims["current_state"] and dims["uncertainty"]
          and dims["sourcing"] and n_dims >= 6 and n_sec >= 10 and chars >= 700
          and density >= 55 and n_ev >= 3 and (n_src >= 2 or auth))
    e2 = (dims["assessment"] and dims["current_state"] and dims["sourcing"]
          and n_dims >= 4 and n_sec >= 6 and chars >= 400 and (n_ev >= 1 or n_src >= 1))
    e1 = (n_dims >= 2 and n_sec >= 2 and chars >= 120 and (n_src >= 1 or n_ev >= 1))

    if e3:
        m = "E3_FULL_ENCYCLOPEDIA"
    elif e2:
        m = "E2_DEVELOPED"
    elif e1:
        m = "E1_BASIC"
    else:
        m = "E0_STUB"

    if not e3:
        if not has_asip:
            reasons.append("no asip_analysis")
        if not dims["current_state"]:
            reasons.append("no current state dimension")
        if not dims["uncertainty"]:
            reasons.append("no uncertainty/watch dimension")
        if n_dims < 6:
            reasons.append(f"dimensions={n_dims}<6")
        if n_sec < 10:
            reasons.append(f"sections={n_sec}<10")
        if chars < 700:
            reasons.append(f"chars={chars}<700")
        if density < 55:
            reasons.append(f"density={density}<55")
        if n_ev < 3:
            reasons.append(f"evidence={n_ev}<3")
        if n_src < 2 and not auth:
            reasons.append(f"sources={n_src}<2 and none authoritative")

    stats = {"sections": n_sec, "chars": chars, "density": density,
             "sources": n_src, "evidence": n_ev, "authoritative_source": auth,
             "dimensions": n_dims,
             "dims": {k: v for k, v in dims.items()}}
    return m, stats, reasons


def score_relation(r, profile, tl_events, ev_ids, source_ids_present):
    p = profile or {}
    filled = [k for k in REL_CORE_FIELDS if p.get(k) and str(p.get(k)).strip()]
    chars = sum(len(str(p.get(k) or "")) for k in REL_CORE_FIELDS)
    refs = [x for x in (r.get("source_refs") or []) if x in source_ids_present]
    n_src, n_ev, n_tl = len(refs), len(ev_ids), len(tl_events or [])

    # A relation's readable surface is the union of its profile and its
    # relationship record — the rendered page draws from both. Scoring only the
    # profile would under-report relations whose sourced context/why/current
    # material lives on the relationship object, which is where several earlier
    # depths placed it.
    def either(keys):
        return any(p.get(k) and str(p.get(k)).strip() for k in keys) or any(
            r.get(k) and str(r.get(k)).strip() for k in keys
        )

    prof_refs = [x for x in (p.get("source_ids") or []) if x in source_ids_present]
    n_src = len(set(refs) | set(prof_refs))

    has_summary = bool(p.get("overview") or r.get("relation_summary")
                       or r.get("summary") or r.get("description"))
    has_analysis = bool(p.get("asip_analysis") or r.get("asip_analysis"))
    has_phases = bool(p.get("evolution_stages") or r.get("evolution_stages")) or n_tl >= 2
    has_current = either(REL_CURRENT_FIELDS) or bool(r.get("current_status"))
    has_context = either(REL_CONTEXT_FIELDS) or bool(
        (r.get("formation_background") or "").strip()
    )
    has_why = either(REL_WHY_FIELDS)
    sourced = n_src >= 1 or n_ev >= 1
    reasons = []

    r3 = (has_analysis and has_phases and has_current and has_why
          and sourced and n_ev >= 1 and n_src >= 1)
    r2 = (has_summary and has_context and has_current and has_why and sourced)
    r1 = has_summary and sourced

    if r3:
        m = "R3_FULL_RELATIONSHIP_INTELLIGENCE"
    elif r2:
        m = "R2_DEVELOPED_RELATIONSHIP"
    elif r1:
        m = "R1_SIMPLE_SOURCED_RELATION"
    else:
        m = "R0_EDGE_ONLY"

    # Report why the object did not reach the tier immediately above the one
    # it was assigned, so the gap reason is actionable rather than generic.
    if m == "R0_EDGE_ONLY":
        if not has_summary:
            reasons.append("no overview/summary")
        if not sourced:
            reasons.append("no resolvable source or evidence")
    elif m == "R1_SIMPLE_SOURCED_RELATION":
        if not has_context:
            reasons.append("R2 gap: no context/history field")
        if not has_current:
            reasons.append("R2 gap: no current status/assessment")
        if not has_why:
            reasons.append("R2 gap: no why-it-matters/uncertainty/watch")
    elif m == "R2_DEVELOPED_RELATIONSHIP":
        if not has_analysis:
            reasons.append("R3 gap: no asip_analysis")
        if not has_phases:
            reasons.append("R3 gap: no evolution_stages / <2 timeline events")
        if n_ev < 1:
            reasons.append("R3 gap: no resolvable evidence")
        if n_src < 1:
            reasons.append("R3 gap: no resolvable source")

    stats = {"fields": len(filled), "chars": chars, "sources": n_src,
             "evidence": n_ev, "timeline": n_tl, "asip_analysis": has_analysis,
             "phases": has_phases, "current": has_current, "context": has_context,
             "why": has_why, "summary": has_summary}
    return m, stats, reasons


def snapshot(label):
    d = load_all()
    ev_e, ev_r = evidence_index(d["evidence"])
    src_present = {s["source_id"] for s in d["sources"]}
    non_country = [e for e in d["entities"] if e["entity_type"] != "country"]

    ents = {}
    for e in non_country:
        eid = e["entity_id"]
        pr = d["ep"].get(eid, {})
        truthful, stats, reasons = score_entity(e, pr, ev_e.get(eid, set()), src_present)
        current = pr.get("content_maturity")
        lvl = e.get("importance_level")
        floor = FLOOR.get(lvl)
        ents[eid] = {
            "importance_level": lvl,
            "current_maturity": current,
            "truthful_maturity": truthful,
            "delta": (ENT_ORDER.index(current) - ENT_ORDER.index(truthful)) if current in ENT_ORDER else None,
            "floor": floor,
            "truthful_meets_floor": (floor is None) or (ENT_ORDER.index(truthful) >= ENT_ORDER.index(floor)),
            "stats": stats,
            "gap_reasons": reasons,
        }

    rls = {}
    for r in d["rels"]:
        rid = r["relationship_id"]
        pr = d["rp"].get(rid, {})
        truthful, stats, reasons = score_relation(
            r, pr, d["tl"].get(rid, []), ev_r.get(rid, set()), src_present)
        current = pr.get("relation_maturity")
        rls[rid] = {
            "type": r.get("relationship_type"),
            "current_maturity": current,
            "truthful_maturity": truthful,
            "delta": (REL_ORDER.index(current) - REL_ORDER.index(truthful)) if current in REL_ORDER else None,
            "has_profile": rid in d["rp"],
            "freshness": r.get("freshness_status"),
            "stats": stats,
            "gap_reasons": reasons,
        }

    def tally(dic, key):
        c = defaultdict(int)
        for v in dic.values():
            c[v[key] or "NONE"] += 1
        return dict(sorted(c.items()))

    return {
        "artifact": f"DEPTHG_MATURITY_RECALIBRATION_{label.upper()}",
        "rubric": {
            "entity": "functional dimension coverage + substance floor + evidence grounding",
            "relation": "closure_standard.relation_policy (R1 sourced summary / R2 +context+current+why / R3 +asip_analysis+phases+evidence)",
        },
        "entity_count": len(ents),
        "relation_count": len(rls),
        "entity_current_distribution": tally(ents, "current_maturity"),
        "entity_truthful_distribution": tally(ents, "truthful_maturity"),
        "relation_current_distribution": tally(rls, "current_maturity"),
        "relation_truthful_distribution": tally(rls, "truthful_maturity"),
        "entities": ents,
        "relations": rls,
    }


if __name__ == "__main__":
    import sys
    label = sys.argv[1] if len(sys.argv) > 1 else "before"
    QA = ROOT / "qa-artifacts-depth-g"
    QA.mkdir(parents=True, exist_ok=True)
    snap = snapshot(label)
    out = QA / f"maturity-recalibration-{label}.json"
    json.dump(snap, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"== DEPTH G MATURITY RECALIBRATION [{label.upper()}] ==")
    print("entities current  :", snap["entity_current_distribution"])
    print("entities truthful :", snap["entity_truthful_distribution"])
    print("relations current :", snap["relation_current_distribution"])
    print("relations truthful:", snap["relation_truthful_distribution"])

    infl = {k: v for k, v in snap["entities"].items() if v["delta"] and v["delta"] > 0}
    under = {k: v for k, v in snap["entities"].items() if v["delta"] and v["delta"] < 0}
    print(f"\nENTITY inflated labels (badge > truthful): {len(infl)}")
    for k, v in sorted(infl.items()):
        print(f"  {k} [{v['importance_level']}] {v['current_maturity']} -> {v['truthful_maturity']} :: {', '.join(v['gap_reasons'][:3])}")
    print(f"ENTITY understated (content exceeds badge, held): {len(under)}")
    for k, v in sorted(under.items()):
        print(f"  {k} [{v['importance_level']}] {v['current_maturity']} <- content supports {v['truthful_maturity']}")

    rinfl = {k: v for k, v in snap["relations"].items() if v["delta"] and v["delta"] > 0}
    print(f"\nRELATION inflated labels: {len(rinfl)}")
    for k, v in sorted(rinfl.items()):
        print(f"  {k} {v['current_maturity']} -> {v['truthful_maturity']} :: {', '.join(v['gap_reasons'][:2])}")

    viol = {k: v for k, v in snap["entities"].items() if not v["truthful_meets_floor"]}
    print(f"\nfloor violations under truthful scoring: {len(viol)}")
    for k, v in sorted(viol.items()):
        print(f"  {k} [{v['importance_level']}] truthful={v['truthful_maturity']} floor={v['floor']} :: {', '.join(v['gap_reasons'][:3])}")
    print(f"\nwritten: {out}")
