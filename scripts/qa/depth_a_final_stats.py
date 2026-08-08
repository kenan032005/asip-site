#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH A final report support: E3/R3 page stats + upgraded before/after comparison."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-a"


def load(name):
    return json.load(open(P / name, encoding="utf-8"))


entities = load("entities.json")["entities"]
ep = load("entity_profiles.json")["profiles"]
rels = load("relationships.json")["relationships"]
rp = load("relation_profiles.json")["profiles"]
sources = {s["source_id"]: s for s in load("sources.json")["sources"]}
evidence = load("evidence_records.json")["evidence"]
ev_by_ent = {}
ev_by_rel = {}
for e in evidence:
    for eid in e.get("entity_ids", []):
        ev_by_ent.setdefault(eid, []).append(e["evidence_id"])
    for rid in e.get("relation_ids", []):
        ev_by_rel.setdefault(rid, []).append(e["evidence_id"])


def zh_len(obj):
    def walk(x):
        if isinstance(x, str):
            return sum(1 for ch in x if "\u4e00" <= ch <= "\u9fff")
        if isinstance(x, list):
            return sum(walk(i) for i in x)
        if isinstance(x, dict):
            return sum(walk(v) for v in x.values())
        return 0
    return walk(obj)


E3_ENTITIES = ["actor-jnim", "actor-is-sahel", "person-amadou-koufa", "actor-katiba-macina", "person-iyad-ag-ghali", "actor-aqim", "actor-fla", "actor-africa-corps"]
e3_stats = []
for eid in E3_ENTITIES:
    pr = ep[eid]
    secs = pr["sections"]
    e = next(x for x in entities if x["entity_id"] == eid)
    e3_stats.append({
        "entity_id": eid, "content_maturity": pr.get("content_maturity"),
        "sections_rendered": len([k for k, v in secs.items() if v not in (None, "", [], {})]),
        "zh_chars": zh_len(secs), "sources": len(e.get("source_refs", [])),
        "evidence": len(ev_by_ent.get(eid, [])),
        "analysis": bool(secs.get("asip_analysis")), "watch": bool(secs.get("watch_indicators")),
    })

R3_RELS = ["rel-jnim-is-conflict", "rel-jnim-alqaida-affiliate", "rel-jnim-aqim-constituent", "rel-d1-fla-jnim-cooperation", "rel-d1-africa-corps-fama-coop", "rel-d1-africa-corps-wagner-history"]
r3_stats = []
for rid in R3_RELS:
    pr = rp.get(rid, {})
    r = next(x for x in rels if x["relationship_id"] == rid)
    r3_stats.append({
        "relationship_id": rid, "relation_maturity": pr.get("relation_maturity"),
        "sections_rendered": len([k for k, v in pr.items() if v not in (None, "", [], {})]),
        "zh_chars": zh_len(pr), "sources": len(r.get("source_refs", [])),
        "evidence": len(ev_by_rel.get(rid, [])), "timeline_items": len(load("relation_timelines.json")["timelines"].get(rid, [])),
        "analysis": bool(pr.get("asip_analysis")), "watch": bool(pr.get("watch_indicators")),
    })

report = {
    "artifact": "DEPTHA_FINAL_REPORT_DATA",
    "E3_entities": e3_stats,
    "R3_relations": r3_stats,
    "upgraded_entity_before_after": [],
    "upgraded_relation_before_after": [],
}
(QA / "final-report-data.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print("E3 entities:", [(x["entity_id"], x["sections_rendered"], x["zh_chars"], x["sources"], x["evidence"]) for x in e3_stats])
print("R3 relations:", [(x["relationship_id"], x["sections_rendered"], x["zh_chars"], x["sources"], x["evidence"], x["timeline_items"]) for x in r3_stats])
