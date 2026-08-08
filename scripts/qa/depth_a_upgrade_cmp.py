#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upgraded entity/relation before-vs-after comparison (audit snapshot vs current)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-a"

audit_e = {x["entity_id"]: x for x in json.load(open(QA / "entity-depth-audit.json", encoding="utf-8"))["entities"]}
audit_r = {x["relationship_id"]: x for x in json.load(open(QA / "relation-depth-audit.json", encoding="utf-8"))["relations"]}
ep = json.load(open(P / "entity_profiles.json", encoding="utf-8"))["profiles"]
rp = json.load(open(P / "relation_profiles.json", encoding="utf-8"))["profiles"]
rels = {r["relationship_id"]: r for r in json.load(open(P / "relationships.json", encoding="utf-8"))["relationships"]}


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


ENTITIES = ["actor-jnim", "actor-is-sahel", "person-amadou-koufa", "actor-katiba-macina", "person-iyad-ag-ghali", "actor-aqim", "actor-al-mourabitoun", "actor-ansarul-islam", "actor-fla", "actor-africa-corps", "actor-wagner-group"]
ent_cmp = []
for eid in ENTITIES:
    a = audit_e.get(eid, {})
    secs = ep.get(eid, {}).get("sections", {})
    ent_cmp.append({
        "entity_id": eid,
        "before": {"maturity": a.get("content_maturity") or "basic", "score": a.get("mechanical_score", 0), "zh": a.get("zh_chars", 0), "secs": a.get("substantive_sections", 0)},
        "after": {"maturity": ep.get(eid, {}).get("content_maturity"), "zh": zh_len(secs), "secs": len([k for k, v in secs.items() if v not in (None, "", [], {})]), "analysis": bool(secs.get("asip_analysis")), "watch": bool(secs.get("watch_indicators"))},
    })

RELS = ["rel-jnim-is-conflict", "rel-jnim-alqaida-affiliate", "rel-jnim-aqim-constituent", "rel-jnim-katiba-constituent", "rel-jnim-iyad-led", "rel-koufa-jnim-senior", "rel-d1-ansarul-jnim-constituent", "rel-d1-fla-jnim-cooperation", "rel-d1-africa-corps-fama-coop", "rel-d1-africa-corps-wagner-history", "rel-koufa-katiba-founder"]
rel_cmp = []
for rid in RELS:
    a = audit_r.get(rid, {})
    pr = rp.get(rid, {})
    rel_cmp.append({
        "relationship_id": rid,
        "before": {"maturity": a.get("maturity") or "R0_EDGE_ONLY", "score": a.get("mechanical_score", 0), "zh": a.get("zh_chars", 0), "tl": a.get("timeline_items", 0)},
        "after": {"maturity": pr.get("relation_maturity"), "zh": zh_len(pr), "tl": len(json.load(open(P / "relation_timelines.json", encoding="utf-8"))["timelines"].get(rid, [])), "analysis": bool(pr.get("asip_analysis")), "watch": bool(pr.get("watch_indicators"))},
    })

out = {"entity_upgrade_comparison": ent_cmp, "relation_upgrade_comparison": rel_cmp}
(QA / "upgrade-comparison.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("entity comparison:")
for x in ent_cmp:
    print(f"  {x['entity_id']}: {x['before']['maturity']}({x['before']['score']}) -> {x['after']['maturity']}(zh {x['after']['zh']}, secs {x['after']['secs']})")
print("relation comparison:")
for x in rel_cmp:
    print(f"  {x['relationship_id']}: {x['before']['maturity']}({x['before']['score']}) -> {x['after']['maturity']}(zh {x['after']['zh']}, tl {x['after']['tl']})")
