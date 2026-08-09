#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH F residual audit handoff for Depth G. Mechanical scan of ALL 72
entities + 150 relationships across the 11 dimensions, plus Bottom 20."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-f"

def load(name):
    return json.load(open(DATA / name, encoding="utf-8"))

entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
ep = load("entity_profiles.json")["profiles"]
rp = load("relation_profiles.json")["profiles"]
tl = load("relation_timelines.json")["timelines"]
evidence = load("evidence_records.json")["evidence"]
sources = load("sources.json")["sources"]

non_country = [e for e in entities if e["entity_type"] != "country"]
ent_by_id = {e["entity_id"]: e for e in entities}
rel_by_id = {r["relationship_id"]: r for r in rels}
source_ids = {s["source_id"] for s in sources}

def zh_len(o):
    def walk(x):
        if isinstance(x, str):
            return sum(1 for c in x if "\u4e00" <= c <= "\u9fff")
        if isinstance(x, list):
            return sum(walk(i) for i in x)
        if isinstance(x, dict):
            return sum(walk(v) for v in x.values())
        return 0
    return walk(o)

audit = {}

# 1. no content_maturity entities
audit["1_no_content_maturity_entities"] = sorted(
    eid for eid in ent_by_id if not ep.get(eid, {}).get("content_maturity"))
# 2. no relation_maturity relations
audit["2_no_relation_maturity_relations"] = sorted(
    rid for rid in rel_by_id if not rp.get(rid, {}).get("relation_maturity"))
# 3. stale objects
audit["3_stale_entities"] = sorted(
    eid for eid, e in ent_by_id.items() if e.get("freshness_status") == "stale")
audit["3_stale_relations"] = sorted(
    rid for rid, r in rel_by_id.items() if r.get("freshness_status") == "stale")
# 4. source_refs <= 1
audit["4_single_source_entities"] = sorted(
    eid for eid, e in ent_by_id.items() if len(e.get("source_refs", [])) <= 1)
audit["4_single_source_relations"] = sorted(
    rid for rid, r in rel_by_id.items() if len(r.get("source_refs", [])) <= 1)
# 5. evidence few/none
ev_by_entity = {}
ev_by_rel = {}
for e in evidence:
    for eid in e.get("entity_ids", []):
        ev_by_entity.setdefault(eid, []).append(e["claim_id"])
    for rid in e.get("relation_ids", []):
        ev_by_rel.setdefault(rid, []).append(e["claim_id"])
audit["5_no_evidence_entities"] = sorted(eid for eid in ent_by_id if len(ev_by_entity.get(eid, [])) == 0)
audit["5_no_evidence_relations"] = sorted(rid for rid in rel_by_id if len(ev_by_rel.get(rid, [])) == 0)
# 6. L1 but maturity insufficient
L1 = [e for e in non_country if e.get("importance_level") == "L1"]
audit["6_L1_maturity_insufficient"] = sorted(
    e["entity_id"] for e in L1
    if ep.get(e["entity_id"], {}).get("content_maturity") not in ("E3_FULL_ENCYCLOPEDIA", "E2_DEVELOPED"))
# 7. summary-only relations
audit["7_summary_only_relations"] = sorted(
    rid for rid, pr in rp.items()
    if pr.get("relation_maturity") in ("R2_DEVELOPED_RELATIONSHIP", "R3_FULL_RELATIONSHIP_INTELLIGENCE")
    and not pr.get("asip_analysis") and not pr.get("evolution_stages") and len(pr.get("overview", "")) < 60)
# 8. obvious source pollution residual
polluted = ["un-jnim-2018"]
audit["8_source_pollution_residual"] = {
    "entities": sorted(eid for eid, e in ent_by_id.items() if any(p in e.get("source_refs", []) for p in polluted)),
    "relations": sorted(rid for rid, r in rel_by_id.items() if any(p in r.get("source_refs", []) for p in polluted)),
}
# 9. duplicate/malformed candidate
rels_by_pair_type = {}
for r in rels:
    key = tuple(sorted([r["source_entity_id"], r["target_entity_id"]])) + (r["relationship_type"],)
    rels_by_pair_type.setdefault(key, []).append(r["relationship_id"])
audit["9_duplicate_pair_type_candidates"] = {
    ".".join(k): v for k, v in rels_by_pair_type.items() if len(v) > 1
}
# 10. Bottom 20 entities by zh content
ent_zh = {eid: zh_len(ep.get(eid, {}).get("sections", {})) for eid in ent_by_id}
audit["10_bottom_20_entities"] = sorted(ent_zh.items(), key=lambda x: x[1])[:20]
# 11. Bottom 20 relations by profile depth
rel_zh = {rid: zh_len(rp.get(rid, {})) for rid in rel_by_id}
audit["11_bottom_20_relations"] = sorted(rel_zh.items(), key=lambda x: x[1])[:20]

report = {
    "artifact": "DEPTHF_RESIDUAL_AUDIT",
    "counts": {"countries": len([c for c in entities if c["entity_type"] == "country"]),
               "entities": len(non_country), "relationships": len(rels),
               "sources": len(source_ids), "evidence": len(evidence)},
    "audit": audit,
    "gate_note": "Mechanical audit for Depth G; do NOT auto-fix non-package targets.",
}
QA.mkdir(parents=True, exist_ok=True)
json.dump(report, open(QA / "depth-f-residual-audit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# markdown summary
lines = ["# ASIP Depth F — Residual Audit Handoff (for Depth G)", "",
         f"**Generated**: 2026-08-09 | counts: {len([c for c in entities if c['entity_type']=='country'])} countries / {len(non_country)} entities / {len(rels)} relationships / {len(source_ids)} sources / {len(evidence)} evidence", "",
         "> Mechanical audit only. Do NOT auto-fix targets outside Depth G package scope.", ""]
sections = [
    ("1. 无 content_maturity 实体", audit["1_no_content_maturity_entities"]),
    ("2. 无 relation_maturity 关系", audit["2_no_relation_maturity_relations"]),
    ("3. stale 对象", audit["3_stale_entities"] + [f"rel:{r}" for r in audit["3_stale_relations"]]),
    ("4. source_refs<=1 对象", [f"ent:{e}" for e in audit["4_single_source_entities"]] + [f"rel:{r}" for r in audit["4_single_source_relations"]]),
    ("5. evidence 少/无 对象", [f"ent:{e}" for e in audit["5_no_evidence_entities"]] + [f"rel:{r}" for r in audit["5_no_evidence_relations"]]),
    ("6. L1 但 maturity 不足", audit["6_L1_maturity_insufficient"]),
    ("7. summary-only 关系", audit["7_summary_only_relations"]),
    ("8. 明显 source 污染残留", [f"ent:{e}" for e in audit["8_source_pollution_residual"]["entities"]] + [f"rel:{r}" for r in audit["8_source_pollution_residual"]["relations"]] or ["无"]),
    ("9. duplicate/malformed 候选", [f"{k}: {v}" for k, v in audit["9_duplicate_pair_type_candidates"].items()] or ["无"]),
]
for title, items in sections:
    lines.append(f"## {title}")
    if not items:
        lines.append("- 无")
    else:
        for it in items[:25]:
            lines.append(f"- {it}")
        if len(items) > 25:
            lines.append(f"- ...（共 {len(items)} 项）")
    lines.append("")
lines.append("## 10. Bottom 20 实体（按中文字数）")
for eid, n in audit["10_bottom_20_entities"]:
    lines.append(f"- {eid}: {n} 字")
lines.append("")
lines.append("## 11. Bottom 20 关系（按 profile 深度）")
for rid, n in audit["11_bottom_20_relations"]:
    lines.append(f"- {rid}: {n} 字符")
lines.append("")
lines.append("---")
lines.append("**DEPTH F residual audit complete. Depth F = CLOSED; Depth G audit may now proceed when directed.**")
open(QA / "depth-f-residual-audit-summary.md", "w", encoding="utf-8").write("\n".join(lines))

print("== audit ==")
for k, v in audit.items():
    if isinstance(v, dict):
        print(f"{k}: {sum(len(x) if isinstance(x, list) else 1 for x in v.values())} entries")
    elif isinstance(v, list):
        print(f"{k}: {len(v)} items")
    else:
        print(f"{k}: {v}")
print("summary written:", QA / "depth-f-residual-audit-summary.md")
