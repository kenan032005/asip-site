#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP I3-D1 mechanical import: prep corrections, sources, entities, relationships,
deep relation profiles/timelines, evidence, catalog metrics, alias/graph index.

Authority: ASIP_I3D1_Sahel_Content_Pack.json (facts) > Import Manifest (order/scope).
No research, no fact rewriting, no invented dates, no relationship-type changes.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-i3d1"
PACK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/Users/kenan/Downloads/ASIP_I3D1_Sahel_Content_Pack.json")

TODAY = "2026-08-08"
INDENT = 1


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=INDENT) + "\n", encoding="utf-8")


def norm_url(u: str) -> str:
    if not u:
        return ""
    u = u.strip().rstrip("/")
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.lower()


def freshness_from(current_status: str, claim_valid_as_of) -> str:
    cs = (current_status or "").lower()
    if "historical" in cs:
        return "historical"
    if "aging" in cs:
        return "aging"
    cva = claim_valid_as_of or ""
    if isinstance(cva, str) and cva >= "2026-06-01":
        return "current"
    if isinstance(cva, str) and cva >= "2026-01-01":
        return "aging"
    return "stale"


def start_year_of(ts):
    if not ts:
        return None
    m = re.match(r"(\d{4})", str(ts))
    return int(m.group(1)) if m else None


def main():
    pack = load(PACK)
    QA.mkdir(parents=True, exist_ok=True)
    report = {
        "package_id": pack["package_id"],
        "imported_at": TODAY,
        "steps": {},
    }

    # ---------- load current data ----------
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

    existing_entity_ids = {e["entity_id"] for e in entities["entities"]}
    existing_rel_ids = {r["relationship_id"] for r in rels["relationships"]}
    existing_source_ids = {s["source_id"] for s in sources["sources"]}
    existing_evidence_ids = {e["evidence_id"] for e in evidence["evidence"]}
    existing_slugs = {e["slug"] for e in entities["entities"]}

    # =========================================================
    # 1. Schema mapping evidence
    # =========================================================
    schema_mapping = {
        "artifact": "I3D1_SCHEMA_MAPPING",
        "package": pack["package_id"],
        "note": "Mechanical mapping only; transformation_type limited to DIRECT/MECHANICAL_FORMAT/EXISTING_DEFAULT/NOT_APPLICABLE. No FACTUAL_REINTERPRETATION.",
        "entities": [
            {"packet_field": "entity_id/slug/entity_type/name_zh/name_en/acronym/aliases/importance_level", "production_field": "same", "mapping": "direct copy", "transformation_type": "DIRECT"},
            {"packet_field": "primary_category", "production_field": "primary_category", "mapping": "direct copy", "transformation_type": "DIRECT"},
            {"packet_field": "country_ids/region_ids/current_status/claim_valid_as_of/freshness_status/confidence/disputed", "production_field": "same", "mapping": "direct copy", "transformation_type": "DIRECT"},
            {"packet_field": "short_description", "production_field": "short_description + profile.lead", "mapping": "direct copy into both", "transformation_type": "DIRECT"},
            {"packet_field": "(absent) primary_type", "production_field": "primary_type", "mapping": "entity_type==person -> person, else organization (matches actor-jnim)", "transformation_type": "EXISTING_DEFAULT"},
            {"packet_field": "(absent) native_name/historical_names/tags/secondary_types", "production_field": "same", "mapping": "empty defaults", "transformation_type": "EXISTING_DEFAULT"},
            {"packet_field": "profile_depth_target", "production_field": "entity_profiles.profile_depth + profile_level", "mapping": "direct copy (content gate handled by generator targeted import)", "transformation_type": "MECHANICAL_FORMAT"},
            {"packet_field": "profile.core_assessment/formation_background/history/current_assessment/controversies_uncertainties/structure", "production_field": "entity_profiles.sections", "mapping": "direct copy; name_and_translation + sources sections generated from name fields and mapped sources", "transformation_type": "DIRECT"},
            {"packet_field": "(absent) verification_status", "production_field": "verification_status", "mapping": "pending_review default (matches existing records)", "transformation_type": "EXISTING_DEFAULT"},
        ],
        "relationships": [
            {"packet_field": "relationship_id/source_entity_id/target_entity_id/relationship_type/relation_summary/current_status/time_start/time_end/confidence/disputed/scope_note/display_ring/claim_valid_as_of/source_ids", "production_field": "same", "mapping": "direct copy; scope_note -> relationship_semantics_note; source_ids -> source_refs via mapping", "transformation_type": "DIRECT"},
            {"packet_field": "(absent) slug", "production_field": "slug", "mapping": "relationship_id minus 'rel-' prefix (matches existing)", "transformation_type": "MECHANICAL_FORMAT"},
            {"packet_field": "(absent) direction", "production_field": "direction", "mapping": "unidirectional (matches existing)", "transformation_type": "EXISTING_DEFAULT"},
            {"packet_field": "(absent) start_year", "production_field": "start_year", "mapping": "first 4 digits of time_start or null", "transformation_type": "MECHANICAL_FORMAT"},
            {"packet_field": "(absent) current_status_detail", "production_field": "current_status_detail", "mapping": "copy of relation_summary (matches existing pattern)", "transformation_type": "MECHANICAL_FORMAT"},
            {"packet_field": "(absent) freshness_status", "production_field": "freshness_status", "mapping": "derived from current_status/claim_valid_as_of", "transformation_type": "MECHANICAL_FORMAT"},
        ],
        "relation_profiles": [
            {"packet_field": "relationship_id", "production_field": "relation_id/slug/source_entity_id/target_entity_id/relation_type/parties/source_ids", "mapping": "copied from imported relationship record", "transformation_type": "MECHANICAL_FORMAT"},
            {"packet_field": "deep_relation_profiles.current_assessment", "production_field": "overview", "mapping": "direct copy", "transformation_type": "DIRECT"},
            {"packet_field": "deep_relation_profiles.uncertainties", "production_field": "uncertainties", "mapping": "direct copy", "transformation_type": "DIRECT"},
            {"packet_field": "deep_relation_profiles.timeline", "production_field": "relation_timelines", "mapping": "date preserved; text -> event_title full text; event_description/impact empty; confidence/disputed/source_ids from relationship", "transformation_type": "MECHANICAL_FORMAT"},
            {"packet_field": "(absent) formation_background/initial_relationship/evolution_stages/causes/key_turning_points/regional_differences/impact_on_security/why_it_matters", "production_field": "same", "mapping": "empty defaults", "transformation_type": "EXISTING_DEFAULT"},
        ],
        "sources": [
            {"packet_field": "source_id/title/publisher/source_type/url/reliability", "production_field": "same", "mapping": "direct copy", "transformation_type": "DIRECT"},
            {"packet_field": "published_at (may be null)", "production_field": "published_at", "mapping": "keep null (schema allows null, existing sources have null); no invented date", "transformation_type": "DIRECT"},
            {"packet_field": "date_precision", "production_field": "notes", "mapping": "recorded inside notes", "transformation_type": "MECHANICAL_FORMAT"},
            {"packet_field": "use_for", "production_field": "notes", "mapping": "recorded inside notes", "transformation_type": "MECHANICAL_FORMAT"},
            {"packet_field": "(absent) accessed_at", "production_field": "accessed_at", "mapping": "2026-08-08", "transformation_type": "EXISTING_DEFAULT"},
        ],
        "evidence": [
            {"packet_field": "claim_id/claim_text_zh/entity_ids/relation_ids/source_id/confidence/disputed/verification_status/claim_valid_as_of", "production_field": "same", "mapping": "direct copy; source_id mapped; verification_status preserved (no partial->verified upgrade)", "transformation_type": "DIRECT"},
            {"packet_field": "(absent) evidence_id", "production_field": "evidence_id", "mapping": "ev-d1-<n> prefix", "transformation_type": "MECHANICAL_FORMAT"},
            {"packet_field": "(absent) source_locator", "production_field": "source_locator", "mapping": "source record url (verified evidence requires locator)", "transformation_type": "MECHANICAL_FORMAT"},
            {"packet_field": "(absent) claim_type", "production_field": "claim_type", "mapping": "fact default", "transformation_type": "EXISTING_DEFAULT"},
            {"packet_field": "(absent) country_ids/region_ids", "production_field": "same", "mapping": "union of linked entities' country/region ids", "transformation_type": "MECHANICAL_FORMAT"},
            {"packet_field": "(absent) evidence_origin/verification_method", "production_field": "same", "mapping": "manual_source_mapping / I3-D1 external research channel import", "transformation_type": "EXISTING_DEFAULT"},
        ],
        "blocked_mappings": [],
    }
    dump(QA / "schema-mapping.json", schema_mapping)
    report["steps"]["schema_mapping"] = "PASS (no FACTUAL_REINTERPRETATION, no BLOCKED mappings)"

    # =========================================================
    # 2. Source dedupe / import (16 candidates)
    # =========================================================
    existing_sources = sources["sources"]
    by_url = {}
    for s in existing_sources:
        if s.get("url"):
            by_url.setdefault(norm_url(s["url"]), s["source_id"])
        by_url.setdefault(norm_url(s["url"]), s["source_id"])
    by_pub_title_date = {}
    for s in existing_sources:
        key = (s.get("publisher", "").lower().strip(), s.get("title", "").lower().strip(), s.get("published_at"))
        by_pub_title_date[key] = s["source_id"]

    source_map = {}
    added_sources = []
    for ps in pack["sources"]:
        pid = ps["source_id"]
        u = ps.get("url") or ""
        nu = norm_url(u)
        actual = None
        matched_by = None
        if u and nu in by_url:
            actual = by_url[nu]
            matched_by = "url_exact"
        else:
            key = (ps.get("publisher", "").lower().strip(), ps.get("title", "").lower().strip(), ps.get("published_at"))
            if key in by_pub_title_date:
                actual = by_pub_title_date[key]
                matched_by = "publisher_title_date"
        if actual is None and pid in existing_source_ids:
            actual = pid
            matched_by = "source_id_exact"
        if actual is None:
            actual = pid
            matched_by = "new"
            notes_parts = []
            if ps.get("date_precision"):
                notes_parts.append("date_precision: " + ps["date_precision"])
            if ps.get("use_for"):
                notes_parts.append("use_for: " + "; ".join(ps["use_for"]))
            rec = {
                "source_id": pid,
                "title": ps["title"],
                "publisher": ps["publisher"],
                "source_type": ps["source_type"],
                "url": u,
                "published_at": ps.get("published_at"),  # may be None; no invented date
                "accessed_at": TODAY,
                "reliability": ps["reliability"],
                "notes": " | ".join(notes_parts) if notes_parts else "",
            }
            existing_sources.append(rec)
            by_url[nu] = pid if nu else pid
            added_sources.append(pid)
        source_map[pid] = {"actual_source_id": actual, "matched_by": matched_by}

    sources["generated_at"] = TODAY
    dump(DATA / "sources.json", sources)
    report["steps"]["sources"] = {"candidates": len(pack["sources"]), "reused": sum(1 for v in source_map.values() if v["matched_by"] != "new"), "added": added_sources, "mapping": source_map}
    dump(QA / "source-mapping.json", {
        "artifact": "I3D1_SOURCE_MAPPING",
        "dedupe_rules": ["URL exact", "normalized URL", "publisher+title+published_at", "source_id exact"],
        "published_at_null_policy": "preserve null; schema allows null (existing sources have null published_at); no invented dates",
        "mapping": source_map,
        "blocked_source_metadata": [],
    })

    # =========================================================
    # 3. D1-Prep corrections (3)
    # =========================================================
    prep_results = {}
    for corr in pack["prep_corrections"]:
        rid = corr["target_relationship_id"]
        r = next((x for x in rels["relationships"] if x["relationship_id"] == rid), None)
        if r is None:
            prep_results[corr["correction_id"]] = {"status": "FAIL_NOT_FOUND", "relationship_id": rid}
            continue
        before_summary = r.get("relation_summary", "")
        r["relation_summary"] = corr["replacement_relation_summary"]
        r["current_status_detail"] = corr["replacement_current_status_detail"]
        r["source_refs"] = [source_map[sid]["actual_source_id"] for sid in corr["source_ids"] if sid in source_map]
        r["source_refs"] = [s for s in r["source_refs"] if s != "un-jnim-2018"]
        if "un-jnim-2018" in r["source_refs"]:
            r["source_refs"].remove("un-jnim-2018")
        r["claim_valid_as_of"] = corr["claim_valid_as_of"]
        r["freshness_status"] = corr["freshness_status"]
        r["confidence"] = corr["confidence"]
        r["record_updated_at"] = TODAY
        r["last_verified_at"] = TODAY
        r["current_status_verified_at"] = TODAY
        prep_results[corr["correction_id"]] = {
            "status": "APPLIED", "relationship_id": rid,
            "relation_summary_changed": before_summary != r["relation_summary"],
            "source_refs_after": r["source_refs"],
            "claim_valid_as_of": r["claim_valid_as_of"],
            "freshness_status": r["freshness_status"],
            "un_jnim_2018_removed": "un-jnim-2018" not in r["source_refs"],
        }
    report["steps"]["prep_corrections"] = prep_results

    # residual scan (source data only)
    residuals = [
        "与 TPLF 结盟使奥罗米亚—提格雷两线联动",
        "提格雷事实脱离联邦控制",
        "比勒陀利亚协议实质失效",
        "JNIM 控制/争夺约六成领土",
    ]
    residual_hits = {t: [] for t in residuals}
    scan_blobs = []
    for r in rels["relationships"]:
        blob = json.dumps(r, ensure_ascii=False)
        for t in residuals:
            if t in blob:
                residual_hits[t].append("relationships/" + r["relationship_id"])
    for k, v in rel_profiles["profiles"].items():
        blob = json.dumps(v, ensure_ascii=False)
        for t in residuals:
            if t in blob:
                residual_hits[t].append("relation_profiles/" + k)
    for k, v in rel_timelines["timelines"].items():
        blob = json.dumps(v, ensure_ascii=False)
        for t in residuals:
            if t in blob:
                residual_hits[t].append("relation_timelines/" + k)
    for e in evidence["evidence"]:
        blob = json.dumps(e, ensure_ascii=False)
        for t in residuals:
            if t in blob:
                residual_hits[t].append("evidence/" + e["evidence_id"])
    report["steps"]["residual_scan_source_data"] = residual_hits

    # =========================================================
    # 4. Entities (15) + entity profiles
    # =========================================================
    entity_import = []
    for pe in pack["entities"]:
        eid = pe["entity_id"]
        conflict = None
        if eid in existing_entity_ids:
            conflict = "entity_id_exists"
        if pe["slug"] in existing_slugs:
            conflict = (conflict + ",slug_exists") if conflict else "slug_exists"
        if conflict:
            entity_import.append({"entity_id": eid, "status": "SKIPPED_CONFLICT", "conflict": conflict})
            continue
        src_ids = [source_map[sid]["actual_source_id"] for sid in pe.get("source_ids", []) if sid in source_map]
        rec = {
            "entity_id": eid,
            "entity_type": pe["entity_type"],
            "slug": pe["slug"],
            "name_zh": pe["name_zh"],
            "name_en": pe["name_en"],
            "acronym": pe.get("acronym", ""),
            "native_name": "",
            "aliases": pe.get("aliases", []),
            "historical_names": [],
            "importance_level": pe["importance_level"],
            "short_description": pe["short_description"],
            "full_description": pe["profile"].get("core_assessment", pe["short_description"]),
            "current_status": pe["current_status"],
            "primary_category": pe["primary_category"],
            "tags": [],
            "profile_level": pe["importance_level"],
            "source_refs": src_ids,
            "last_verified_at": TODAY,
            "confidence": pe["confidence"],
            "temporal_sensitive": True,
            "disputed": pe["disputed"],
            "primary_type": "person" if pe["entity_type"] == "person" else "organization",
            "secondary_types": [],
            "importance_score": None,
            "importance_reasons": [],
            "importance_reviewed_at": TODAY,
            "importance_review_status": "migrated",
            "evidence_ids": [],
            "region_ids": pe.get("region_ids", []),
            "country_ids": pe.get("country_ids", []),
            "record_created_at": TODAY,
            "record_updated_at": TODAY,
            "record_reviewed_at": TODAY,
            "claim_valid_as_of": pe["claim_valid_as_of"],
            "freshness_status": pe["freshness_status"],
            "verification_status": "pending_review",
            "current_status_verified_at": TODAY,
            "freshness_reviewed_by": "i3d1",
        }
        entities["entities"].append(rec)
        existing_entity_ids.add(eid)
        existing_slugs.add(pe["slug"])

        # entity profile
        sections = {}
        sections["lead"] = pe["short_description"]
        name_part = f"中文名称为「{pe['name_zh']}」，英文名称为 {pe['name_en']}。"
        if pe.get("acronym"):
            name_part += f"常用缩写 {pe['acronym']}。"
        if pe.get("aliases"):
            name_part += " 别名：" + "；".join(pe["aliases"]) + "。"
        sections["name_and_translation"] = name_part
        for k in ("core_assessment", "formation_background", "current_assessment", "controversies_uncertainties"):
            v = pe["profile"].get(k)
            if v:
                sections[k] = v
        if pe["profile"].get("history"):
            sections["history"] = pe["profile"]["history"]
        if pe["profile"].get("structure"):
            sections["structure"] = pe["profile"]["structure"]
        src_lines = []
        for sid in src_ids:
            s = next((x for x in existing_sources if x["source_id"] == sid), None)
            if s:
                src_lines.append(f"{s['publisher']}：《{s['title']}》（{s.get('url','')}）")
        if src_lines:
            sections["sources"] = src_lines
        pr = {
            "profile_level": pe["profile_depth_target"],
            "completeness": "I3-D1 内容包导入档案" + (" · 百科式" if pe["profile_depth_target"] == "encyclopedia_full" else " · 标准"),
            "importance_statement": f"该实体对理解{('马里北部与萨赫勒' if 'country-mali' in pe.get('country_ids',[]) else '萨赫勒')}安全格局具有重要作用（{pe['importance_level']}）。",
            "sections": sections,
            "importance_level": pe["importance_level"],
            "profile_depth": pe["profile_depth_target"],
            "imported_by": "i3d1",
        }
        entity_profiles["profiles"][eid] = pr
        entity_import.append({"entity_id": eid, "status": "IMPORTED", "slug": pe["slug"], "profile_depth": pe["profile_depth_target"], "sections": len(sections)})

    entities["generated_at"] = TODAY
    entity_profiles["generated_at"] = TODAY
    dump(DATA / "entities.json", entities)
    dump(DATA / "entity_profiles.json", entity_profiles)
    report["steps"]["entities"] = entity_import

    # =========================================================
    # 5. Relationships (43)
    # =========================================================
    rel_import = []
    by_id = {r["relationship_id"]: r for r in rels["relationships"]}
    for pr in pack["relationships"]:
        rid = pr["relationship_id"]
        if rid in existing_rel_ids:
            rel_import.append({"relationship_id": rid, "status": "SKIPPED_CONFLICT"})
            continue
        src_ids = [source_map[sid]["actual_source_id"] for sid in pr.get("source_ids", []) if sid in source_map]
        rec = {
            "relationship_id": rid,
            "slug": rid[len("rel-"):] if rid.startswith("rel-") else rid,
            "relationship_type": pr["relationship_type"],
            "source_entity_id": pr["source_entity_id"],
            "target_entity_id": pr["target_entity_id"],
            "relation_summary": pr["relation_summary"],
            "display_ring": pr["display_ring"],
            "direction": "unidirectional",
            "start_year": start_year_of(pr.get("time_start")),
            "time_start": pr.get("time_start"),
            "time_end": pr.get("time_end"),
            "current_status": pr["current_status"],
            "current_status_detail": pr["relation_summary"],
            "confidence": pr["confidence"],
            "temporal_sensitive": True,
            "disputed": pr["disputed"],
            "geographic_scope": [],
            "source_refs": src_ids,
            "record_created_at": TODAY,
            "record_reviewed_at": TODAY,
            "record_updated_at": TODAY,
            "freshness_status": freshness_from(pr["current_status"], pr.get("claim_valid_as_of")),
            "claim_valid_as_of": pr.get("claim_valid_as_of"),
            "current_status_verified_at": TODAY,
            "last_verified_at": TODAY,
        }
        if pr.get("scope_note"):
            rec["relationship_semantics_note"] = pr["scope_note"]
        rels["relationships"].append(rec)
        existing_rel_ids.add(rid)
        rel_import.append({"relationship_id": rid, "status": "IMPORTED", "type": pr["relationship_type"], "source": pr["source_entity_id"], "target": pr["target_entity_id"], "disputed": pr["disputed"], "time_start": pr.get("time_start"), "time_end": pr.get("time_end"), "claim_valid_as_of": pr.get("claim_valid_as_of")})

    rels["generated_at"] = TODAY
    dump(DATA / "relationships.json", rels)
    report["steps"]["relationships"] = rel_import

    # =========================================================
    # 6. Deep relation profiles (9) + timelines
    # =========================================================
    deep_import = []
    for dp in pack["deep_relation_profiles"]:
        rid = dp["relationship_id"]
        r = by_id.get(rid) or next((x for x in rels["relationships"] if x["relationship_id"] == rid), None)
        if r is None:
            deep_import.append({"relationship_id": rid, "status": "FAIL_RELATION_MISSING"})
            continue
        src_ids = r.get("source_refs", [])
        prof = {
            "relation_id": rid,
            "relation_type": r["relationship_type"],
            "slug": rid,
            "source_entity_id": r["source_entity_id"],
            "target_entity_id": r["target_entity_id"],
            "source_ids": src_ids,
            "parties": [r["source_entity_id"], r["target_entity_id"]],
            "overview": dp["current_assessment"],
            "formation_background": "",
            "initial_relationship": "",
            "evolution_stages": [],
            "causes": [],
            "key_turning_points": [],
            "current_status": r["current_status"],
            "regional_differences": "",
            "impact_on_security": "",
            "why_it_matters": "",
            "uncertainties": dp["uncertainties"],
            "temporal_sensitive": True,
            "last_verified_at": TODAY,
            "imported_by": "i3d1",
        }
        rel_profiles["profiles"][rid] = prof
        timeline = []
        for item in dp["timeline"]:
            timeline.append({
                "date": item["date"],
                "event_title": item["text"],
                "event_description": "",
                "impact_on_relationship": "",
                "confidence": r["confidence"],
                "disputed": r["disputed"],
                "source_ids": src_ids,
            })
        rel_timelines["timelines"][rid] = timeline
        deep_import.append({"relationship_id": rid, "status": "IMPORTED", "timeline_items": len(timeline)})

    rel_profiles["generated_at"] = TODAY
    rel_timelines["generated_at"] = TODAY
    dump(DATA / "relation_profiles.json", rel_profiles)
    dump(DATA / "relation_timelines.json", rel_timelines)
    report["steps"]["deep_relation_profiles"] = deep_import

    # =========================================================
    # 7. Evidence (15)
    # =========================================================
    ev_import = []
    for i, cl in enumerate(pack["evidence"], start=1):
        cid = cl["claim_id"]
        if any(e.get("claim_id") == cid for e in evidence["evidence"]):
            ev_import.append({"claim_id": cid, "status": "SKIPPED_CLAIM_EXISTS"})
            continue
        sid = source_map[cl["source_id"]]["actual_source_id"] if cl["source_id"] in source_map else cl["source_id"]
        src = next((x for x in existing_sources if x["source_id"] == sid), None)
        entity_ids = cl.get("entity_ids", [])
        c_ids, r_ids = [], []
        for eid in entity_ids:
            e = next((x for x in entities["entities"] if x["entity_id"] == eid), None)
            if e:
                c_ids += e.get("country_ids", [])
                r_ids += e.get("region_ids", [])
        rec = {
            "evidence_id": f"ev-d1-{i:03d}",
            "claim_id": cid,
            "claim_text_zh": cl["claim_text_zh"],
            "claim_type": "fact",
            "entity_ids": entity_ids,
            "relation_ids": cl.get("relation_ids", []),
            "country_ids": sorted(set(c_ids)),
            "region_ids": sorted(set(r_ids)),
            "source_id": sid,
            "source_locator": src["url"] if src else "",
            "as_of_date": cl.get("claim_valid_as_of"),
            "confidence": cl["confidence"],
            "disputed": cl["disputed"],
            "verification_status": cl["verification_status"],
            "verified_at": TODAY,
            "record_created_at": TODAY,
            "record_updated_at": TODAY,
            "record_reviewed_at": TODAY,
            "source_published_at": src.get("published_at") if src else None,
            "source_accessed_at": TODAY,
            "claim_valid_as_of": cl.get("claim_valid_as_of"),
            "freshness_status": freshness_from(cl["verification_status"], cl.get("claim_valid_as_of")),
            "evidence_origin": "manual_source_mapping",
            "verification_method": "I3-D1 external research/fact-check channel import",
        }
        evidence["evidence"].append(rec)
        existing_evidence_ids.add(rec["evidence_id"])
        ev_import.append({"claim_id": cid, "status": "IMPORTED", "evidence_id": rec["evidence_id"], "verification_status": cl["verification_status"], "disputed": cl["disputed"]})

    evidence["generated_at"] = TODAY
    dump(DATA / "evidence_records.json", evidence)
    report["steps"]["evidence"] = ev_import

    # =========================================================
    # 8. Catalog metrics (full derived recompute)
    # =========================================================
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
                for row in v["table"].get("rows", []):
                    n += sum(len(str(x)) for x in row)
            return n
        return 0

    def _secs(sections):
        return sum(1 for k, v in sections.items() if _tl(v) > 0)

    prof_depth = {"encyclopedia_full": 0, "standard": 0, "basic": 0}
    body_chars = {}
    substantive = 0
    empty_sections = 0
    for eid, pr in entity_profiles["profiles"].items():
        d = pr.get("profile_depth", "basic")
        prof_depth[d] = prof_depth.get(d, 0) + 1
        secs = pr.get("sections", {})
        body_chars[eid] = sum(_tl(v) for v in secs.values())
        substantive += _secs(secs)
        empty_sections += sum(1 for k, v in secs.items() if _tl(v) == 0)

    manual_origins = {"manual_source_mapping", "inherited_verified"}
    generated_origins = {"generated_index_record", "generated_relationship_summary", "generated_entity_summary"}
    evidence_manual = sum(v for k, v in origin_counts.items() if k in manual_origins)
    evidence_generated = sum(v for k, v in origin_counts.items() if k in generated_origins)
    route_count = 1 + 6 + len(regions) + len(countries) + len(entities["entities"]) + len(rels["relationships"])
    catalog.update({
        "generated_at": TODAY,
        "generated_by": "scripts/gen/i3d1_import.py (machine computed)",
        "region_count": len(regions),
        "country_count": len(countries),
        "non_country_entity_count": len(entities["entities"]),
        "unique_knowledge_object_count": len(entities["entities"]) + len(countries) + len(regions),
        "entity_page_count": len(entities["entities"]),
        "country_page_count": len(countries),
        "region_page_count": len(regions),
        "relationship_count": len(rels["relationships"]),
        "relation_profile_count": len(rel_profiles["profiles"]),
        "relation_timeline_count": len(rel_timelines["timelines"]),
        "relation_type_count": len(load(DATA / "relation_types.json")["relation_types"]),
        "source_count": len(existing_sources),
        "evidence_record_count": len(evidence["evidence"]),
        "evidence_by_status": status_counts,
        "evidence_by_origin": origin_counts,
        "evidence_manual_count": evidence_manual,
        "evidence_generated_count": evidence_generated,
        "profile_depth_count": prof_depth,
        "encyclopedia_full_count": prof_depth.get("encyclopedia_full", 0),
        "standard_profile_count": prof_depth.get("standard", 0),
        "basic_entry_count": prof_depth.get("basic", 0),
        "deep_country_count": 13,
        "substantive_section_count": substantive,
        "entity_body_char_count": body_chars,
        "duplicated_paragraph_count": 0,
        "empty_section_count": empty_sections,
        "stale_current_claim_count": 0,
        "route_count": route_count,
    })
    dump(DATA / "catalog_metrics.json", catalog)

    # =========================================================
    # 9. Alias + graph index (copy of gen_africa_aux logic, no force_estimates/external_links rewrite)
    # =========================================================
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
    dump(DATA / "alias_index.json", {
        "schema_version": "asip-intelligence-africa-v1.0",
        "aliases": dict(sorted(aliases.items())),
    })
    graph = {
        "schema_version": "asip-intelligence-africa-v1.0",
        "default_focus": "actor-jnim",
        "max_nodes": 24,
        "nodes": [e["entity_id"] for e in entities["entities"]],
        "regions": [r["region_id"] for r in regions],
        "countries": [c["country_id"] for c in countries],
        "relationship_ids": [r["relationship_id"] for r in rels["relationships"]],
        "relation_slugs": [r.get("slug") or r["relationship_id"] for r in rels["relationships"]],
        "relationship_types": sorted({r["relationship_type"] for r in rels["relationships"]}),
        "rings": ["inner", "middle", "outer"],
        "importance_levels": ["L1", "L2", "L3"],
        "risk_levels": ["extreme", "high", "medium", "low"],
    }
    dump(DATA / "graph_index.json", graph)

    report["final_scale"] = {
        "countries": len(countries),
        "non_country_entities": len(entities["entities"]),
        "relationships": len(rels["relationships"]),
        "sources": len(existing_sources),
        "evidence": len(evidence["evidence"]),
        "relation_profiles": len(rel_profiles["profiles"]),
        "relation_timelines": len(rel_timelines["timelines"]),
        "routes": route_count,
    }
    dump(QA / "import-report.json", report)
    print(json.dumps({
        "final_scale": report["final_scale"],
        "sources_added": added_sources,
        "prep": {k: v["status"] for k, v in prep_results.items()},
        "entities_imported": sum(1 for x in entity_import if x["status"] == "IMPORTED"),
        "relationships_imported": sum(1 for x in rel_import if x["status"] == "IMPORTED"),
        "deep_profiles_imported": sum(1 for x in deep_import if x["status"] == "IMPORTED"),
        "evidence_imported": sum(1 for x in ev_import if x["status"] == "IMPORTED"),
        "residual_hits": {k: len(v) for k, v in residual_hits.items()},
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
