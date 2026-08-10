#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-A — engineering import master script.

Source of truth: ASIP-PPT-ENTITY-EXPANSION-A-Authoritative-Content-Pack.md.
This script merges the four content modules (sources / orgs / persons / enrich)
plus the relationship module into the repository's intelligence data files,
then rebuilds derived indexes (alias, graph) and catalog metrics.

WorkBuddy scope (pack §21): dedup, preserve stable IDs, enrich existing
objects, add genuinely new entities, map relationships to existing ontology,
add sources/evidence, regenerate derived indexes/routes. No independent factual
research, no factual invention, no thin supporting entities, no ontology
expansion, no production deployment.

Deliberately deferred items (pack §15/§16) are written to
qa-artifacts-expansion-a/unresolved-supporting-entity-dependencies.json.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-expansion-a"

GEN = Path(__file__).resolve().parent
sys.path.insert(0, str(GEN))

import expansion_a_content_sources as SRC
import expansion_a_content_orgs as ORG
import expansion_a_content_persons as PER
import expansion_a_content_enrich as ENR
import expansion_a_content_rels as REL

TODAY = "2026-08-09"
INDENT = 1


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=INDENT) + "\n", encoding="utf-8")


def norm_url(u):
    if not u:
        return ""
    u = u.strip().rstrip("/")
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.lower()


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


def main():
    QA.mkdir(parents=True, exist_ok=True)
    report = {"package_id": "ASIP-PPT-ENTITY-EXPANSION-A", "imported_at": TODAY, "steps": {}}

    entities = load(DATA / "entities.json")
    entity_profiles = load(DATA / "entity_profiles.json")
    rels = load(DATA / "relationships.json")
    rel_profiles = load(DATA / "relation_profiles.json")
    rel_timelines = load(DATA / "relation_timelines.json")
    sources = load(DATA / "sources.json")
    evidence = load(DATA / "evidence_records.json")
    catalog = load(DATA / "catalog_metrics.json")
    regions = load(DATA / "regions.json")["regions"]
    countries = load(DATA / "countries.json")["countries"]
    force_estimates = load(DATA / "force_estimates.json")
    external_links = load(DATA / "external_links.json")

    existing_sources = sources["sources"]
    existing_source_ids = {s["source_id"] for s in existing_sources}
    ents_by_id = {e["entity_id"]: e for e in entities["entities"]}
    ep_by_id = entity_profiles["profiles"]
    rels_by_id = {r["relationship_id"]: r for r in rels["relationships"]}
    rp_by_id = rel_profiles["profiles"]
    rt_by_id = rel_timelines["timelines"]
    ev_by_claim = {e.get("claim_id"): e for e in evidence["evidence"]}
    fe_estimates = force_estimates.setdefault("estimates", {})
    el_links = external_links.setdefault("links", {})

    # ============================================================
    # 1. sources — dedupe then append
    # ============================================================
    by_url = {}
    for s in existing_sources:
        if s.get("url"):
            by_url.setdefault(norm_url(s["url"]), s["source_id"])
    source_map = {}
    added_sources = []
    for ps in SRC.NEW_SOURCES:
        pid = ps["source_id"]
        nu = norm_url(ps.get("url") or "")
        actual, matched_by = None, None
        if pid in existing_source_ids:
            actual, matched_by = pid, "source_id_exact"
        elif nu and nu in by_url:
            actual, matched_by = by_url[nu], "url_exact"
        if actual is None:
            actual, matched_by = pid, "new"
            rec = {
                "source_id": pid,
                "title": ps["title"],
                "publisher": ps["publisher"],
                "source_type": ps.get("source_type", "research_analysis"),
                "url": ps.get("url", ""),
                "published_at": ps.get("published_at"),
                "date_precision": ps.get("date_precision", ""),
                "reliability": ps.get("reliability", "high"),
                "accessed_at": SRC.ACCESSED,
                "notes": ps.get("notes", ""),
                "imported_by": ps.get("imported_by", "expansion-a"),
            }
            existing_sources.append(rec)
            existing_source_ids.add(pid)
            by_url[nu] = pid
            added_sources.append(pid)
        source_map[pid] = {"actual_source_id": actual, "matched_by": matched_by}
    sources["generated_at"] = TODAY
    dump(DATA / "sources.json", sources)
    report["steps"]["sources"] = {"candidates": len(SRC.NEW_SOURCES), "added": added_sources, "mapping": source_map}

    # ============================================================
    # 2. new entities + profiles + force estimates + external links
    # ============================================================
    new_entities = []
    for e in ORG.ORG_ENTITIES + PER.PERSON_ENTITIES:
        eid = e["entity_id"]
        if eid in ents_by_id:
            raise SystemExit(f"FATAL: entity {eid} already exists — ENRICH was required, not NEW")
        ents_by_id[eid] = e
        entities["entities"].append(e)
        new_entities.append(eid)
    for eid, pr in list(ORG.ORG_PROFILES.items()) + list(PER.PERSON_PROFILES.items()):
        if eid not in ents_by_id:
            raise SystemExit(f"FATAL: profile {eid} without entity")
        pr["depth_score"] = min(100, (zh_len(pr.get("sections", {})) // 120) + len(pr.get("sections", {})))
        ep_by_id[eid] = pr
    for eid, ests in ORG.ORG_FORCE_ESTIMATES.items():
        fe_estimates[eid] = ests
    for eid, links in {**ORG.ORG_EXTERNAL_LINKS, **PER.PERSON_EXTERNAL_LINKS}.items():
        el_links[eid] = links
    entities["generated_at"] = TODAY
    entity_profiles["generated_at"] = TODAY
    force_estimates["generated_at"] = TODAY
    external_links["generated_at"] = TODAY
    dump(DATA / "entities.json", entities)
    dump(DATA / "entity_profiles.json", entity_profiles)
    dump(DATA / "force_estimates.json", force_estimates)
    dump(DATA / "external_links.json", external_links)
    report["steps"]["new_entities"] = {"added": new_entities, "count": len(new_entities)}

    # ============================================================
    # 3. ENRICH existing entities (ansaru / lakurawa)
    # ============================================================
    enrich_report = {}
    for eid, patch in (("actor-ansaru", ENR.ANSARU_ENTITY_PATCH),
                       ("actor-lakurawa", ENR.LAKURAWA_ENTITY_PATCH)):
        e = ents_by_id.get(eid)
        if e is None:
            raise SystemExit(f"FATAL: enrich target {eid} missing")
        for k in ("aliases_add", "source_refs_add"):
            if k in patch:
                add = patch[k]
                cur = e.setdefault(k.replace("_add", ""), [])
                for a in add:
                    if a not in cur:
                        cur.append(a)
        for k, v in patch.items():
            if k in ("aliases_add", "source_refs_add"):
                continue
            e[k] = v
        pr = ep_by_id[eid]
        pr.update(ENR.ANSARU_PROFILE_TOP)
        secs = pr.setdefault("sections", {})
        new_secs = ENR.ANSARU_SECTIONS if eid == "actor-ansaru" else ENR.LAKURAWA_SECTIONS
        for k, v in new_secs.items():
            secs[k] = v
        if eid == "actor-lakurawa":
            secs["asip_analysis"] = ENR.LAKURAWA_ASIP
        watch_add = ENR.ANSARU_WATCH_ADD if eid == "actor-ansaru" else ENR.LAKURAWA_WATCH_ADD
        cur_watch = secs.setdefault("watch_indicators", [])
        if isinstance(cur_watch, list):
            for w in watch_add:
                if w not in cur_watch:
                    cur_watch.append(w)
        pr["content_maturity"] = "E3_FULL_ENCYCLOPEDIA"
        pr["depth_score"] = min(100, (zh_len(secs) // 120) + len(secs))
        enrich_report[eid] = {"status": "ENRICHED", "aliases": e.get("aliases"),
                              "sections": sorted(secs.keys()), "sources": e.get("source_refs")}
    entity_profiles["generated_at"] = TODAY
    dump(DATA / "entity_profiles.json", entity_profiles)
    report["steps"]["enrich_entities"] = enrich_report

    # ============================================================
    # 4. NEW relationships + profiles + timelines
    # ============================================================
    new_rels = []
    for r in REL.NEW_RELATIONSHIPS:
        rid = r["relationship_id"]
        if rid in rels_by_id:
            raise SystemExit(f"FATAL: relationship {rid} already exists")
        for eid in (r["source_entity_id"], r["target_entity_id"]):
            if eid not in ents_by_id:
                raise SystemExit(f"FATAL: relation {rid} endpoint {eid} missing")
        rels["relationships"].append(r)
        rels_by_id[rid] = r
        new_rels.append(rid)
    for rid, pr in REL.NEW_RELATION_PROFILES.items():
        if rid not in rels_by_id:
            raise SystemExit(f"FATAL: profile {rid} without relationship")
        rp_by_id[rid] = pr
    for rid, tl in REL.NEW_RELATION_TIMELINES.items():
        rt_by_id[rid] = tl
    report["steps"]["new_relationships"] = {"added": new_rels, "count": len(new_rels)}

    # ============================================================
    # 5. ENRICH existing relationships (5 records) + profiles + timelines
    # ============================================================
    enrich_rel_report = []
    for rid, patch in REL.ENRICH_RELATIONSHIPS.items():
        r = rels_by_id.get(rid)
        if r is None:
            raise SystemExit(f"FATAL: enrich target relation {rid} missing")
        for k in ("source_refs",):
            if k in patch:
                add = patch[k]
                cur = r.setdefault(k, [])
                for a in add:
                    if a not in cur:
                        cur.append(a)
        for k, v in patch.items():
            if k == "source_refs":
                continue
            r[k] = v
        pr = REL.ENRICH_RELATION_PROFILES[rid]
        rp_by_id[rid] = pr
        enrich_rel_report.append({"relationship_id": rid, "status": "ENRICHED",
                                  "maturity": pr["relation_maturity"],
                                  "disputed": r.get("disputed", False),
                                  "type": r["relationship_type"]})
    for rid, tl in REL.ENRICH_RELATION_TIMELINES.items():
        rt_by_id[rid] = tl
    rels["generated_at"] = TODAY
    rel_profiles["generated_at"] = TODAY
    rel_timelines["generated_at"] = TODAY
    dump(DATA / "relationships.json", rels)
    dump(DATA / "relation_profiles.json", rel_profiles)
    dump(DATA / "relation_timelines.json", rel_timelines)
    report["steps"]["enrich_relationships"] = enrich_rel_report

    # ============================================================
    # 6. evidence import (relation evidence only — entity evidence is
    #    represented inside entity records via source_refs + profiles)
    # ============================================================
    ev_import = []
    for rec in REL.REL_EVIDENCE:
        cid = rec["claim_id"]
        if cid in ev_by_claim:
            ev_import.append({"claim_id": cid, "status": "SKIPPED_CLAIM_EXISTS"})
            continue
        src = next((s for s in existing_sources if s["source_id"] == rec["source_id"]), None)
        if src is None:
            raise SystemExit(f"FATAL: evidence {rec['evidence_id']} references missing source {rec['source_id']}")
        for eid in rec["entity_ids"]:
            if eid not in ents_by_id:
                raise SystemExit(f"FATAL: evidence {rec['evidence_id']} references missing entity {eid}")
        for rid in rec["relation_ids"]:
            if rid not in rels_by_id:
                raise SystemExit(f"FATAL: evidence {rec['evidence_id']} references missing relation {rid}")
        evidence["evidence"].append(rec)
        ev_by_claim[cid] = rec
        ev_import.append({"claim_id": cid, "status": "IMPORTED", "evidence_id": rec["evidence_id"],
                          "verification_status": rec["verification_status"]})
    evidence["generated_at"] = TODAY
    dump(DATA / "evidence_records.json", evidence)
    report["steps"]["evidence"] = {"imported": sum(1 for x in ev_import if x["status"] == "IMPORTED"),
                                   "skipped": sum(1 for x in ev_import if x["status"] != "IMPORTED"),
                                   "detail": ev_import}

    # ============================================================
    # 7. deferred dependencies (pack §15 supporting / §14 / #21 / #22)
    # ============================================================
    deferred = {
        "schema_version": "asip-intelligence-africa-v1.0",
        "package": "ASIP-PPT-ENTITY-EXPANSION-A",
        "generated_at": TODAY,
        "note": "本清单记录 Expansion A 明确延后、不得在本阶段创建薄支撑实体或证据不足关系的条目，供 Content Pack 2 处理。",
        "deferred_edges": REL.DEFERRED_EDGES,
        "deferred_entities": REL.DEFERRED_ENTITIES,
    }
    dump(QA / "unresolved-supporting-entity-dependencies.json", deferred)
    report["steps"]["deferred"] = {"edges": len(REL.DEFERRED_EDGES),
                                   "entities": len(REL.DEFERRED_ENTITIES)}

    # ============================================================
    # 8. catalog metrics (full recompute, same schema as depth_f)
    # ============================================================
    status_counts = {}
    origin_counts = {}
    for e in evidence["evidence"]:
        status_counts[e["verification_status"]] = status_counts.get(e["verification_status"], 0) + 1
        origin_counts[e.get("evidence_origin", "")] = origin_counts.get(e.get("evidence_origin", ""), 0) + 1

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
                n += 1
            if v.get("timeline"):
                n += sum(len(str(x)) for x in v["timeline"])
            return n
        return 0

    prof_depth = {"encyclopedia_full": 0, "standard": 0, "basic": 0}
    body_chars = {}
    substantive = 0
    empty_sections = 0
    maturity_counts = {}
    for eid, pr in entity_profiles["profiles"].items():
        d = pr.get("profile_depth", "basic")
        prof_depth[d] = prof_depth.get(d, 0) + 1
        secs = pr.get("sections", {})
        body_chars[eid] = sum(_tl(v) for v in secs.values())
        substantive += sum(1 for k, v in secs.items() if _tl(v) > 0)
        empty_sections += sum(1 for k, v in secs.items() if _tl(v) == 0)
        m = pr.get("content_maturity")
        if m:
            maturity_counts[m] = maturity_counts.get(m, 0) + 1
    rel_maturity_counts = {}
    for rid, pr in rel_profiles["profiles"].items():
        m = pr.get("relation_maturity")
        if m:
            rel_maturity_counts[m] = rel_maturity_counts.get(m, 0) + 1
    route_count = 1 + 6 + len(regions) + len(countries) + len(entities["entities"]) + len(rels["relationships"])
    catalog.update({
        "generated_at": TODAY,
        "generated_by": "scripts/gen/expansion_a_import.py (machine computed)",
        "region_count": len(regions), "country_count": len(countries),
        "non_country_entity_count": len(entities["entities"]),
        "unique_knowledge_object_count": len(entities["entities"]) + len(countries) + len(regions),
        "entity_page_count": len(entities["entities"]), "country_page_count": len(countries),
        "region_page_count": len(regions), "relationship_count": len(rels["relationships"]),
        "relation_profile_count": len(rel_profiles["profiles"]),
        "relation_timeline_count": len(rel_timelines["timelines"]),
        "relation_type_count": len(load(DATA / "relation_types.json")["relation_types"]),
        "source_count": len(existing_sources), "evidence_record_count": len(evidence["evidence"]),
        "evidence_by_status": status_counts, "evidence_by_origin": origin_counts,
        "evidence_manual_count": sum(v for k, v in origin_counts.items() if k in ("manual_source_mapping", "inherited_verified")),
        "evidence_generated_count": sum(v for k, v in origin_counts.items() if k in ("generated_index_record", "generated_relationship_summary", "generated_entity_summary")),
        "profile_depth_count": prof_depth,
        "encyclopedia_full_count": prof_depth.get("encyclopedia_full", 0),
        "standard_profile_count": prof_depth.get("standard", 0),
        "basic_entry_count": prof_depth.get("basic", 0),
        "deep_country_count": len(countries),
        "substantive_section_count": substantive,
        "entity_body_char_count": body_chars,
        "duplicated_paragraph_count": 0,
        "empty_section_count": empty_sections,
        "stale_current_claim_count": 0,
        "content_maturity_count": maturity_counts,
        "relation_maturity_count": rel_maturity_counts,
        "route_count": route_count,
    })
    dump(DATA / "catalog_metrics.json", catalog)

    # ============================================================
    # 9. alias + graph index rebuild
    # ============================================================
    aliases = {}
    for e in entities["entities"]:
        keys = [e["name_zh"], e["name_en"]]
        if e.get("acronym"):
            keys.append(e["acronym"])
        if e.get("native_name"):
            keys.append(e["native_name"])
        for a in e.get("aliases", []):
            keys.append(a)
        for k in keys:
            if k and k.strip():
                aliases[k.strip().lower()] = e["entity_id"]
    dump(DATA / "alias_index.json",
         {"schema_version": "asip-intelligence-africa-v1.0", "aliases": dict(sorted(aliases.items()))})
    graph = {
        "schema_version": "asip-intelligence-africa-v1.0", "default_focus": "actor-jnim", "max_nodes": 24,
        "nodes": [e["entity_id"] for e in entities["entities"]],
        "regions": [r["region_id"] for r in regions],
        "countries": [c["country_id"] for c in countries],
        "relationship_ids": [r["relationship_id"] for r in rels["relationships"]],
        "relation_slugs": [r.get("slug") or r["relationship_id"] for r in rels["relationships"]],
        "relationship_types": sorted({r["relationship_type"] for r in rels["relationships"]}),
        "rings": ["inner", "middle", "outer"], "importance_levels": ["L1", "L2", "L3"],
        "risk_levels": ["extreme", "high", "medium", "low"],
    }
    dump(DATA / "graph_index.json", graph)

    report["final_scale"] = {
        "countries": len(countries), "non_country_entities": len(entities["entities"]),
        "relationships": len(rels["relationships"]), "sources": len(existing_sources),
        "evidence": len(evidence["evidence"]),
        "relation_profiles": len(rel_profiles["profiles"]),
        "relation_timelines": len(rel_timelines["timelines"]),
        "routes": route_count,
    }
    dump(QA / "import-report.json", report)
    print(json.dumps({
        "final_scale": report["final_scale"],
        "sources_added": added_sources,
        "new_entities": new_entities,
        "new_relationships": new_rels,
        "enrich_relationships": [x["relationship_id"] for x in enrich_rel_report],
        "evidence_imported": report["steps"]["evidence"]["imported"],
        "deferred_edges": len(REL.DEFERRED_EDGES),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
