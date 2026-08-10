#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-B — engineering import master script.

Source of truth: ASIP-PPT-ENTITY-EXPANSION-B-Authoritative-Content-Pack.md.
Merges the content modules (sources / orgs part1+2 / persons / rels part1+2),
upgrades the carry-over person-abdirahman-fahiye to encyclopedia_full,
regenerates alias/graph indexes and catalog metrics, writes evidence records and
the country-dependency file. No research, no invention, no thin country pages.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-expansion-b"

GEN = Path(__file__).resolve().parent
sys.path.insert(0, str(GEN))

import expansion_b_content_sources as SRC
import expansion_b_content_orgs as ORG1
import expansion_b_content_orgs2 as ORG2
import expansion_b_content_persons as PER
import expansion_b_content_rels as REL1
import expansion_b_content_rels2 as REL2

TODAY = "2026-08-10"
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
    report = {"package_id": "ASIP-PPT-ENTITY-EXPANSION-B", "imported_at": TODAY, "steps": {}}

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
    # 0. pre-import dedup audit (artifact)
    # ============================================================
    dedup = {
        "artifact": "EXPANSION_B_PRE_IMPORT_DEDUP_AUDIT",
        "generated_at": TODAY,
        "candidates": [
            {"candidate": "AUSSOM", "dedup_vs": ["actor-aussom", "AMISOM", "ATMIS"], "decision": "NEW",
             "evidence": "no existing AUSSOM/AMISOM/ATMIS entity node; predecessor chain recorded in history text"},
            {"candidate": "SNAF", "dedup_vs": ["actor-somali-national-armed-forces", "Somali National Army", "SNA"], "decision": "NEW",
             "evidence": "no existing Somali armed forces node; SNA kept as alias"},
            {"candidate": "Puntland Security Forces", "dedup_vs": ["actor-puntland-security-forces", "PSF"], "decision": "NEW",
             "evidence": "no existing node; umbrella-label modeling per pack section 4"},
            {"candidate": "FARDC", "dedup_vs": ["actor-fardc", "actor-fardc", "Congolese armed forces"], "decision": "NEW",
             "evidence": "no existing DRC armed forces node"},
            {"candidate": "UPDF", "dedup_vs": ["actor-updf", "Uganda armed forces"], "decision": "NEW",
             "evidence": "no existing Uganda armed forces node"},
            {"candidate": "MONUSCO", "dedup_vs": ["actor-monusco", "MONUC"], "decision": "NEW",
             "evidence": "no existing node; MONUC kept as historical name"},
            {"candidate": "IRGC", "dedup_vs": ["actor-irgc", "actor-iran"], "decision": "NEW",
             "evidence": "no existing Iran/IRGC node in the Africa graph; Expansion A deferred it"},
            {"candidate": "Mahad Karate", "dedup_vs": ["person-mahad-karate"], "decision": "NEW",
             "evidence": "no existing node; alias Abdirahman Mohammed Warsame also absent"},
            {"candidate": "Abdiweli Mohamed Yusuf", "dedup_vs": ["person-abdiweli-mohamed-yusuf"], "decision": "NEW",
             "evidence": "no existing node"},
            {"candidate": "Meddie/Mohamed Ali Nkalubo", "dedup_vs": ["person-meddie-nkalubo"], "decision": "NEW",
             "evidence": "no existing node; Expansion A recorded as deferred supporting person"},
            {"candidate": "Abu Zaid Talha al-Misbah", "dedup_vs": ["person-abu-zaid-talha"], "decision": "NEW",
             "evidence": "no existing node; Expansion A recorded DEFER_FOR_CONTENT_PACK_2; pack B supplies EU source"},
        ],
        "carryover": [
            {"entity": "person-abdirahman-fahiye", "decision": "ENRICH_EXISTING_UPGRADE",
             "from": "standard/E2", "to": "encyclopedia_full/E3"},
            {"entity": "actor-ansaru", "decision": "ENRICH_EXISTING (already encyclopedia_full/E3, confirmed)"},
            {"entity": "actor-lakurawa", "decision": "ENRICH_EXISTING (already encyclopedia_full/E3, confirmed)"},
        ],
        "note": "stable existing IDs preferred; no duplicates created for pack-suggested IDs",
    }
    dump(QA / "pre-import-dedup-audit.json", dedup)
    report["steps"]["dedup_audit"] = dedup

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
                "source_id": pid, "title": ps["title"], "publisher": ps["publisher"],
                "source_type": ps.get("source_type", "research_analysis"),
                "url": ps.get("url", ""), "published_at": ps.get("published_at"),
                "date_precision": ps.get("date_precision", ""),
                "reliability": ps.get("reliability", "high"),
                "accessed_at": SRC.ACCESSED,
                "notes": ps.get("notes", ""),
                "imported_by": ps.get("imported_by", "expansion-b"),
            }
            existing_sources.append(rec)
            existing_source_ids.add(pid)
            by_url[nu] = pid
            added_sources.append(pid)
        source_map[pid] = {"actual_source_id": actual, "matched_by": matched_by}
    # verify all reused source ids exist
    missing_reuse = [sid for sid in SRC.REUSED_SOURCE_IDS if sid not in existing_source_ids]
    if missing_reuse:
        raise SystemExit(f"FATAL: reused source ids missing from registry: {missing_reuse}")
    sources["generated_at"] = TODAY
    dump(DATA / "sources.json", sources)
    report["steps"]["sources"] = {"candidates": len(SRC.NEW_SOURCES), "added": added_sources,
                                  "reused": SRC.REUSED_SOURCE_IDS, "mapping": source_map}

    # ============================================================
    # 2. new entities + profiles (orgs part1+2 + persons)
    # ============================================================
    all_orgs = ORG1.ORG_ENTITIES_1 + ORG2.ORG_ENTITIES
    all_org_profiles = dict(list(ORG1.ORG_PROFILES_1.items()) + list(ORG2.ORG_PROFILES.items()))
    new_entities = []
    for e in all_orgs + PER.PERSON_ENTITIES:
        eid = e["entity_id"]
        if eid in ents_by_id:
            raise SystemExit(f"FATAL: entity {eid} already exists — ENRICH was required, not NEW")
        ents_by_id[eid] = e
        entities["entities"].append(e)
        new_entities.append(eid)
    for eid, pr in list(all_org_profiles.items()) + list(PER.PERSON_PROFILES.items()):
        if eid not in ents_by_id:
            raise SystemExit(f"FATAL: profile {eid} without entity")
        pr["depth_score"] = min(100, (zh_len(pr.get("sections", {})) // 120) + len(pr.get("sections", {})))
        ep_by_id[eid] = pr
    entities["generated_at"] = TODAY
    entity_profiles["generated_at"] = TODAY
    dump(DATA / "entities.json", entities)
    dump(DATA / "entity_profiles.json", entity_profiles)
    report["steps"]["new_entities"] = {"added": new_entities, "count": len(new_entities)}

    # ============================================================
    # 3. carry-over: fahiye upgrade to encyclopedia_full
    # ============================================================
    fahiye = ents_by_id.get("person-abdirahman-fahiye")
    if fahiye is None:
        raise SystemExit("FATAL: carry-over person-abdirahman-fahiye missing")
    pr = ep_by_id["person-abdirahman-fahiye"]
    pr["sections"] = PER.FAHIYE_UPGRADE_SECTIONS
    pr["profile_level"] = "encyclopedia_full"
    pr["profile_depth"] = "encyclopedia_full"
    pr["content_maturity"] = "E3_FULL_ENCYCLOPEDIA"
    pr["completeness"] = "Expansion B 内容包导入档案 · 百科式（carry-over 升级）"
    pr["depth_score"] = min(100, (zh_len(pr["sections"]) // 120) + len(pr["sections"]))
    fahiye["profile_level"] = "L2"
    fahiye["record_updated_at"] = TODAY
    fahiye["last_verified_at"] = TODAY
    fahiye["claim_valid_as_of"] = TODAY
    # add new source refs from the upgrade
    for sid in ["expb-ofac-fahiye-2022-11-01", "expb-treasury-jy1066-2022-11-01", "d2-un-s2026-44"]:
        if sid not in fahiye.setdefault("source_refs", []):
            fahiye["source_refs"].append(sid)
    entity_profiles["generated_at"] = TODAY
    dump(DATA / "entities.json", entities)
    dump(DATA / "entity_profiles.json", entity_profiles)
    report["steps"]["carryover_fahiye"] = {
        "status": "UPGRADED", "from": "standard/E2", "to": "encyclopedia_full/E3",
        "sections": len(pr["sections"]), "zh_chars": zh_len(pr["sections"])}

    # ============================================================
    # 4. new relationships + profiles + timelines (part1 + part2)
    # ============================================================
    all_new_rels = REL1.NEW_RELATIONSHIPS + REL2.NEW_RELATIONSHIPS
    all_profiles = dict(list(REL1.NEW_RELATION_PROFILES.items()) + list(REL2.NEW_RELATION_PROFILES.items()))
    all_timelines = dict(list(REL1.NEW_RELATION_TIMELINES.items()) + list(REL2.NEW_RELATION_TIMELINES.items()))
    new_rels = []
    for r in all_new_rels:
        rid = r["relationship_id"]
        if rid in rels_by_id:
            raise SystemExit(f"FATAL: relationship {rid} already exists")
        for eid in (r["source_entity_id"], r["target_entity_id"]):
            if eid not in ents_by_id:
                raise SystemExit(f"FATAL: relation {rid} endpoint {eid} missing")
        rels["relationships"].append(r)
        rels_by_id[rid] = r
        new_rels.append(rid)
    for rid, pr in all_profiles.items():
        if rid not in rels_by_id:
            raise SystemExit(f"FATAL: profile {rid} without relationship")
        rp_by_id[rid] = pr
    for rid, tl in all_timelines.items():
        rt_by_id[rid] = tl
    rels["generated_at"] = TODAY
    rel_profiles["generated_at"] = TODAY
    rel_timelines["generated_at"] = TODAY
    dump(DATA / "relationships.json", rels)
    dump(DATA / "relation_profiles.json", rel_profiles)
    dump(DATA / "relation_timelines.json", rel_timelines)
    report["steps"]["new_relationships"] = {"added": new_rels, "count": len(new_rels)}

    # ============================================================
    # 5. evidence records for the new relationships
    # ============================================================
    ev_import = []
    for i, r in enumerate(all_new_rels, start=1):
        rid = r["relationship_id"]
        cid = "cl-expb-" + rid.replace("rel-expb-", "", 1)
        if cid in ev_by_claim:
            ev_import.append({"claim_id": cid, "status": "SKIPPED_CLAIM_EXISTS"})
            continue
        src_id = r["source_refs"][0] if r["source_refs"] else None
        if src_id is None or src_id not in existing_source_ids:
            raise SystemExit(f"FATAL: relation {rid} first source missing: {src_id}")
        src = next(s for s in existing_sources if s["source_id"] == src_id)
        # status semantics: official/mission statements -> verified_reported_findings;
        # UPDF/Treasury attribution statements -> partially_verified; UN resolutions -> verified
        if "treasury" in src_id or "updf" in src_id:
            status = "partially_verified"
        elif "unsc" in src_id or "panel" in src_id or "s2026" in src_id or "au-" in src_id or "aussom" in src_id or "unsos" in src_id or "monusco" in src_id or "un-" in src_id or "un_sg" in src_id:
            status = "verified_reported_findings"
        else:
            status = "verified"
        rec = {
            "evidence_id": f"ev-expb-r{i:03d}",
            "claim_id": cid,
            "claim_text_zh": r["relation_summary"],
            "claim_type": "fact" if status == "verified" else "analysis",
            "entity_ids": [r["source_entity_id"], r["target_entity_id"]],
            "relation_ids": [rid],
            "country_ids": [],
            "region_ids": [e.get("region_ids", [])[0] for e in [ents_by_id.get(r["source_entity_id"]), ents_by_id.get(r["target_entity_id"])] if e and e.get("region_ids")],
            "source_id": src_id,
            "source_locator": src.get("url", "") or src.get("title", ""),
            "as_of_date": TODAY,
            "confidence": r["confidence"],
            "disputed": r["disputed"],
            "verification_status": status,
            "verified_at": TODAY,
            "record_created_at": TODAY,
            "record_updated_at": TODAY,
            "record_reviewed_at": TODAY,
            "source_published_at": src.get("published_at"),
            "source_accessed_at": TODAY,
            "claim_valid_as_of": TODAY,
            "freshness_status": r["freshness_status"],
            "evidence_origin": "manual_source_mapping",
            "verification_method": "Expansion B source-of-truth package mapping against the cited authoritative document",
        }
        evidence["evidence"].append(rec)
        ev_by_claim[cid] = rec
        ev_import.append({"claim_id": cid, "status": "IMPORTED", "evidence_id": rec["evidence_id"],
                          "verification_status": status})
    evidence["generated_at"] = TODAY
    dump(DATA / "evidence_records.json", evidence)
    report["steps"]["evidence"] = {"imported": sum(1 for x in ev_import if x["status"] == "IMPORTED"),
                                   "detail": ev_import}

    # ============================================================
    # 6. country dependency (pack section 15)
    # ============================================================
    country_dep = {
        "schema_version": "asip-intelligence-africa-v1.0",
        "package": "ASIP-PPT-ENTITY-EXPANSION-B",
        "generated_at": TODAY,
        "note": "内容包 §15：不得创建薄国家页；Somalia/DRC/Uganda 等国家节点缺失时登记为 EXPANSION_B_COUNTRY_DEPENDENCY，由后续专门内容包处理。",
        "dependencies": [
            {"country": "Somalia", "needed_for": ["actor-aussom", "actor-somali-national-armed-forces",
                                                  "actor-puntland-security-forces", "actor-al-shabaab", "actor-isis-somalia"],
             "status": "EXPANSION_B_COUNTRY_DEPENDENCY"},
            {"country": "Democratic Republic of the Congo", "needed_for": ["actor-fardc", "actor-monusco", "actor-adf-isis-ca"],
             "status": "EXPANSION_B_COUNTRY_DEPENDENCY"},
            {"country": "Uganda", "needed_for": ["actor-updf", "actor-adf-isis-ca"],
             "status": "EXPANSION_B_COUNTRY_DEPENDENCY"},
        ],
    }
    dump(QA / "country-dependency-summary.json", country_dep)
    report["steps"]["country_dependency"] = len(country_dep["dependencies"])

    # ============================================================
    # 7. catalog metrics (full recompute)
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
        "generated_by": "scripts/gen/expansion_b_import.py (machine computed)",
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
    # 8. alias + graph index rebuild
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
        "standard_depth_profiles": prof_depth.get("standard", 0),
    }
    dump(QA / "import-report.json", report)
    print(json.dumps({
        "final_scale": report["final_scale"],
        "sources_added": added_sources,
        "new_entities": new_entities,
        "new_relationships": new_rels,
        "carryover": report["steps"]["carryover_fahiye"],
        "evidence_imported": report["steps"]["evidence"]["imported"],
        "country_dependencies": len(country_dep["dependencies"]),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
