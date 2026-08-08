#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH A: baseline confirmation + full mechanical Depth Audit of 72 entities / 150 relations.
All scores are MECHANICAL_SCORE_NOT_FACT_QUALITY_JUDGMENT."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-a"
QA.mkdir(parents=True, exist_ok=True)


def load(name):
    return json.load(open(P / name, encoding="utf-8"))


entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
sources = load("sources.json")["sources"]
evidence = load("evidence_records.json")["evidence"]
profiles = load("relation_profiles.json")["profiles"]
timelines = load("relation_timelines.json")["timelines"]
ep = load("entity_profiles.json")["profiles"]
countries = load("countries.json")["countries"]

# ---------- baseline gate ----------
baseline = {
    "countries": len(countries),
    "non_country_entities": len(entities),
    "relationships": len(rels),
    "relation_profiles": len(profiles),
    "relation_timelines": len(timelines),
    "sources": len(sources),
    "evidence": len(evidence),
}
expected = {"countries": 13, "non_country_entities": 72, "relationships": 150, "relation_profiles": 50, "relation_timelines": 50, "sources": 115, "evidence": 194}
drift = {k: (baseline[k], expected[k]) for k in expected if baseline[k] != expected[k]}
print("BASELINE:", baseline)
if drift:
    print("BASELINE_KNOWLEDGE_DRIFT:", drift)
    (QA / "baseline-gate.json").write_text(json.dumps({"gate": "DRIFT", "baseline": baseline, "expected": expected, "drift": drift}, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.exit(1)
routes = 1 + 6 + len(load("regions.json")["regions"]) + len(countries) + len(entities) + len(rels)
if routes != 249:
    print("BASELINE_KNOWLEDGE_DRIFT: routes", routes)
    sys.exit(1)
print("BASELINE_GATE: PASS (13/72/150/50/50/115/194/249)")

# ---------- helpers ----------
def _tl(v):
    if isinstance(v, str):
        return len(v)
    if isinstance(v, list):
        return sum(len(str(x)) for x in v)
    if isinstance(v, dict):
        n = 0
        if v.get("p"):
            n += sum(len(str(x)) for x in v["p"])
        if v.get("list"):
            n += sum(len(str(x)) for x in v["list"])
        if v.get("table"):
            for row in v["table"].get("rows", []):
                n += sum(len(str(x)) for x in row)
        return n
    return 0


def _secs(sections):
    return sum(1 for k, v in sections.items() if _tl(v) > 0)


def zh_chars(text):
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


def zh_len(obj):
    def walk(x):
        if isinstance(x, str):
            return zh_chars(x)
        if isinstance(x, list):
            return sum(walk(i) for i in x)
        if isinstance(x, dict):
            return sum(walk(v) for v in x.values())
        return 0
    return walk(obj)


# entity -> direct relation count
rel_degree = {}
for r in rels:
    for end in (r["source_entity_id"], r["target_entity_id"]):
        if end.startswith("actor-") or end.startswith("person-"):
            rel_degree[end] = rel_degree.get(end, 0) + 1

ev_by_entity = {}
for e in evidence:
    for eid in e.get("entity_ids", []):
        ev_by_entity.setdefault(eid, []).append(e["evidence_id"])
ev_by_rel = {}
for e in evidence:
    for rid in e.get("relation_ids", []):
        ev_by_rel.setdefault(rid, []).append(e["evidence_id"])

entity_audit = []
for e in entities:
    eid = e["entity_id"]
    pr = ep.get(eid, {})
    secs = pr.get("sections", {})
    body = sum(_tl(v) for v in secs.values())
    zh = zh_len(secs)
    n_secs = _secs(secs)
    has_current = bool(secs.get("current_assessment") or secs.get("current_situation"))
    has_uncertainty = bool(secs.get("controversies_uncertainties") or secs.get("uncertainties"))
    has_analysis = bool(secs.get("asip_analysis"))
    has_watch = bool(secs.get("watch_indicators"))
    has_history = bool(secs.get("history") or secs.get("major_timeline") or secs.get("formation_background"))
    # mechanical score components (0-100)
    score = 0
    score += min(20, n_secs * 3)
    score += min(25, body // 150)
    score += min(10, len(e.get("source_refs", [])) * 2)
    score += min(10, len(ev_by_entity.get(eid, [])) * 2)
    score += 8 if has_current else 0
    score += 8 if has_uncertainty else 0
    score += 8 if has_history else 0
    score += 6 if has_analysis else 0
    score += 5 if has_watch else 0
    score += min(8, rel_degree.get(eid, 0))
    score = min(100, score)
    entity_audit.append({
        "entity_id": eid, "importance_level": e.get("importance_level"),
        "content_maturity": pr.get("profile_depth") or pr.get("content_maturity") or "basic",
        "mechanical_score": score,
        "zh_chars": zh, "body_chars": body, "substantive_sections": n_secs,
        "source_count": len(e.get("source_refs", [])),
        "evidence_count": len(ev_by_entity.get(eid, [])),
        "relation_count": rel_degree.get(eid, 0),
        "has_current_assessment": has_current, "has_uncertainty": has_uncertainty,
        "has_history": has_history, "has_asip_analysis": has_analysis, "has_watch_indicators": has_watch,
        "empty_entity_fields": sum(1 for k, v in e.items() if v in (None, "", [], {})),
    })

relation_audit = []
for r in rels:
    rid = r["relationship_id"]
    prof = profiles.get(rid, {})
    tl_items = len(timelines.get(rid, []))
    prof_zh = zh_len(prof)
    overview = prof.get("overview") or r.get("relation_summary", "")
    has_evolution = bool(prof.get("evolution_stages"))
    has_drivers = bool(prof.get("drivers"))
    has_uncertainty = bool(prof.get("uncertainties"))
    has_analysis = bool(prof.get("asip_analysis"))
    has_watch = bool(prof.get("watch_indicators"))
    has_current = bool(prof.get("current_status") or prof.get("current_assessment"))
    has_initial = bool(prof.get("initial_relationship"))
    score = 0
    score += min(20, tl_items * 4)
    score += min(20, prof_zh // 120)
    score += min(10, len(r.get("source_refs", [])) * 2)
    score += min(10, len(ev_by_rel.get(rid, [])) * 2)
    score += 8 if has_evolution else 0
    score += 6 if has_drivers else 0
    score += 6 if has_uncertainty else 0
    score += 6 if has_analysis else 0
    score += 6 if has_watch else 0
    score += 5 if has_initial else 0
    score += 3 if has_current else 0
    score = min(100, score)
    relation_audit.append({
        "relationship_id": rid, "relationship_type": r["relationship_type"],
        "maturity": prof.get("relation_maturity") or ("R0_EDGE_ONLY" if not prof else "R1_BASIC"),
        "mechanical_score": score,
        "zh_chars": prof_zh,
        "timeline_items": tl_items,
        "source_count": len(r.get("source_refs", [])),
        "evidence_count": len(ev_by_rel.get(rid, [])),
        "has_overview": bool(overview), "has_evolution_stages": has_evolution,
        "has_drivers": has_drivers, "has_uncertainty": has_uncertainty,
        "has_asip_analysis": has_analysis, "has_watch_indicators": has_watch,
        "has_initial_relationship": has_initial, "has_current_status": has_current,
    })

entity_audit.sort(key=lambda x: (x["mechanical_score"], -x["zh_chars"]))
relation_audit.sort(key=lambda x: (x["mechanical_score"], -x["zh_chars"]))

for i, x in enumerate(entity_audit):
    x["rank"] = i + 1
for i, x in enumerate(relation_audit):
    x["rank"] = i + 1

(QA / "entity-depth-audit.json").write_text(json.dumps({"artifact": "DEPTHA_ENTITY_DEPTH_AUDIT", "note": "MECHANICAL_SCORE_NOT_FACT_QUALITY_JUDGMENT", "entities": entity_audit}, ensure_ascii=False, indent=1), encoding="utf-8")
(QA / "relation-depth-audit.json").write_text(json.dumps({"artifact": "DEPTHA_RELATION_DEPTH_AUDIT", "note": "MECHANICAL_SCORE_NOT_FACT_QUALITY_JUDGMENT", "relations": relation_audit}, ensure_ascii=False, indent=1), encoding="utf-8")

bottom20_entities = entity_audit[:20]
bottom20_relations = relation_audit[:20]

summary_md = [
    "# DEPTH A 全库机械 Depth Audit",
    "",
    "评分口径：MECHANICAL_SCORE_NOT_FACT_QUALITY_JUDGMENT（仅统计内容结构，不评估事实质量）。",
    "",
    f"实体：{len(entity_audit)} | 关系：{len(relation_audit)}",
    "",
    "## Bottom 20 实体（机械分最低）",
    "",
    "| rank | entity | score | zh | secs | src | ev | rel |",
    "|---|---|---|---|---|---|---|---|",
]
for x in bottom20_entities:
    summary_md.append(f"| {x['rank']} | {x['entity_id']} | {x['mechanical_score']} | {x['zh_chars']} | {x['substantive_sections']} | {x['source_count']} | {x['evidence_count']} | {x['relation_count']} |")
summary_md += ["", "## Bottom 20 关系（机械分最低）", "", "| rank | relation | score | zh | tl | src | ev |", "|---|---|---|---|---|---|---|"]
for x in bottom20_relations:
    summary_md.append(f"| {x['rank']} | {x['relationship_id']} | {x['mechanical_score']} | {x['zh_chars']} | {x['timeline_items']} | {x['source_count']} | {x['evidence_count']} |")
summary_md += ["", "## E3/R3 候选（本轮 packet 升级目标）", "", "实体:", ""]
for x in entity_audit:
    if x["entity_id"] in ("actor-jnim", "actor-is-sahel", "person-amadou-koufa", "actor-katiba-macina", "person-iyad-ag-ghali", "actor-aqim", "actor-al-mourabitoun", "actor-ansarul-islam", "actor-fla", "actor-africa-corps", "actor-wagner-group"):
        summary_md.append(f"- {x['entity_id']}: score={x['mechanical_score']} zh={x['zh_chars']} secs={x['substantive_sections']}")
summary_md += ["", "关系:", ""]
for x in relation_audit:
    if x["relationship_id"] in ("rel-jnim-is-conflict", "rel-jnim-alqaida-affiliate", "rel-jnim-aqim-constituent", "rel-jnim-katiba-constituent", "rel-jnim-iyad-led", "rel-koufa-jnim-senior", "rel-d1-ansarul-jnim-constituent", "rel-d1-fla-jnim-cooperation", "rel-d1-africa-corps-fama-coop", "rel-d1-africa-corps-wagner-history", "rel-koufa-katiba-founder"):
        summary_md.append(f"- {x['relationship_id']}: score={x['mechanical_score']} zh={x['zh_chars']} tl={x['timeline_items']}")
(QA / "depth-audit-summary.md").write_text("\n".join(summary_md), encoding="utf-8")

print("entity audit:", len(entity_audit), "| relation audit:", len(relation_audit))
print("Bottom 20 entities:", [x["entity_id"] for x in bottom20_entities])
print("Bottom 20 relations:", [x["relationship_id"] for x in bottom20_relations])
print("DEPTH_AUDIT_GATE: PASS")
