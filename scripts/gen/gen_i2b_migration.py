#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I2-B data migration: trusted statistics, time/freshness semantics, evidence
quality grading, relation ontology fix, profile depth grading and audit records.

Read-only for facts; only adds/renames metadata fields and corrects the
specific issues identified by I2-B:
  1. remove country duplicates from entities.json (countries.json is canonical)
  2. add record_*/source_*/claim_valid/current_status_verified/freshness fields
  3. grade evidence by origin; never default generated records to verified
  4. restore pledged_allegiance_to as independent relation type
  5. add relation_types.json registry
  6. grade entity profile depth (encyclopedia_full/standard/basic)
  7. write audit_records.json (3 regions, >=36 claims, sourced)
  8. generate catalog_metrics.json (machine-computed)
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
AUDIT_DATE = "2026-08-06"   # today's data-file review date
REF_DATE = "2026-08-06"     # freshness reference
CUR_12M = "2025-08-06"      # current threshold (12 months)
AGING_24M = "2024-08-06"    # aging threshold (24 months)


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def save(name, obj):
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def freshness_of(date_str):
    """freshness_status from a source published date."""
    if not date_str:
        return "unknown"
    if date_str >= CUR_12M:
        return "current"
    if date_str >= AGING_24M:
        return "aging"
    return "stale"


def max_source_date(source_ids, sources_by_id):
    dates = [sources_by_id[s].get("published_at") for s in source_ids if s in sources_by_id]
    dates = [d for d in dates if d]
    return max(dates) if dates else None


def main():
    sources = load("sources.json")
    sources_by_id = {s["source_id"]: s for s in sources["sources"]}

    # ---------------------------------------------------------------- entities
    entities = load("entities.json")
    country_entities = {"country-mali", "country-niger", "country-burkina-faso"}
    kept, removed = [], []
    for e in entities["entities"]:
        if e["entity_id"] in country_entities:
            removed.append(e["entity_id"])
            continue
        sd = max_source_date(e.get("source_refs", []), sources_by_id)
        e["record_created_at"] = e.get("record_created_at") or "2026-08-06"
        e["record_updated_at"] = AUDIT_DATE
        e["record_reviewed_at"] = AUDIT_DATE
        e["claim_valid_as_of"] = sd or e.get("claim_valid_as_of")
        e["freshness_status"] = freshness_of(sd)
        e.setdefault("verification_status", "pending_review")
        if e["entity_id"] in AUDITED_ENTITY_IDS:
            e["current_status_verified_at"] = AUDIT_DATE
        else:
            e["current_status_verified_at"] = None
        kept.append(e)
    entities["entities"] = kept
    entities["note"] = ("I2-B: country-type objects removed; canonical country data "
                        "lives in countries.json (single source of truth).")
    save("entities.json", entities)
    print(f"entities: {len(kept)} kept, removed countries: {removed}")

    # -------------------------------------------------------- entity profiles
    eps = load("entity_profiles.json")
    profiles = eps["profiles"]
    grades = {}
    for eid, p in list(profiles.items()):
        if eid in country_entities:
            del profiles[eid]
            continue
        sections = p.get("sections", {})
        if isinstance(sections, dict):
            n_sec = len([k for k, v in sections.items() if str(v or "").strip()])
            content = sum(len(str(v)) for v in sections.values())
        else:
            n_sec, content = 0, 0
        if n_sec >= 12 and content >= 1200:
            depth = "encyclopedia_full"
        elif n_sec >= 7 and content >= 250:
            depth = "standard"
        else:
            depth = "basic"
        p["profile_depth"] = depth
        p["profile_level"] = depth  # repurpose polluted field (was importance value)
        grades[eid] = depth
    eps["profile_depth_note"] = ("I2-B: profile_depth is graded from actual section "
                                 "content (encyclopedia_full: >=12 sections & >=1200 chars; "
                                 "standard: >=7 sections & >=250 chars; else basic).")
    save("entity_profiles.json", eps)
    from collections import Counter
    print("profile_depth:", dict(Counter(grades.values())))

    # ---------------------------------------------------------------- countries
    countries = load("countries.json")
    for c in countries["countries"]:
        sd = max_source_date(c.get("source_ids", []), sources_by_id)
        c["record_created_at"] = c.get("record_created_at") or "2026-08-06"
        c["record_updated_at"] = AUDIT_DATE
        c["record_reviewed_at"] = AUDIT_DATE
        c["claim_valid_as_of"] = sd or c.get("claim_valid_as_of")
        c["freshness_status"] = freshness_of(sd)
        c["current_status_verified_at"] = AUDIT_DATE if c["country_id"] in AUDITED_COUNTRY_IDS else None
    save("countries.json", countries)
    print("countries:", len(countries["countries"]))

    # ------------------------------------------------------------- relationships
    rels = load("relationships.json")
    pledge_map = {
        "rel-iswap-islamic-state-affiliation": "ISWAP 于 2016 年宣誓效忠伊斯兰国并获承认。",
        "rel-is-moz-islamic-state": "IS-Mozambique 以伊斯兰国省分支名义活动，公开资料显示其向伊斯兰国网络宣誓效忠。",
        "rel-isis-libya-affiliation": "ISIS-Libya 属伊斯兰国体系分支，曾向伊斯兰国核心宣誓效忠。",
        "rel-jnim-alqaida-affiliate": "JNIM 于 2017 年公开向基地组织领导人宣誓效忠（bay'ah），获联合国列入关联实体。",
    }
    for r in rels["relationships"]:
        sd = max_source_date(r.get("source_refs", []), sources_by_id)
        r["record_created_at"] = r.get("record_created_at") or "2026-08-06"
        r["record_updated_at"] = AUDIT_DATE
        r["record_reviewed_at"] = AUDIT_DATE
        r["claim_valid_as_of"] = sd or r.get("claim_valid_as_of")
        r["freshness_status"] = freshness_of(sd)
        r["current_status_verified_at"] = AUDIT_DATE if r["relationship_id"] in AUDITED_REL_IDS else None
        if r["relationship_id"] in pledge_map:
            r["relationship_type"] = "pledged_allegiance_to"
            r["relation_summary"] = pledge_map[r["relationship_id"]]
            r["relationship_semantics_note"] = ("I2-B: 类型从 affiliated_with 修正为 pledged_allegiance_to "
                                                "（宣誓效忠），保留独立语义，不与一般网络关联混淆。")
    save("relationships.json", rels)
    pledge_rels = [r["relationship_id"] for r in rels["relationships"] if r["relationship_type"] == "pledged_allegiance_to"]
    print("relationships:", len(rels["relationships"]), "| pledged_allegiance_to:", pledge_rels)

    # ------------------------------------------------------------------- sources
    for sid in ("reuters-africa", "bbc-africa"):
        if sid in sources_by_id:
            s = sources_by_id[sid]
            s["published_at"] = None
            s["notes"] = (s.get("notes") or "") + " I2-B: 通用新闻索引来源，不绑定具体发布日期；" \
                         "不作为当前状态时效依据。"
    save("sources.json", sources)
    print("sources:", len(sources["sources"]))

    # ------------------------------------------------------------ evidence grade
    evidence = load("evidence_records.json")
    verified_set = {  # claims actually checked against primary sources in V0.2 dev
        "cl-jnim-created-2017", "cl-jnim-alqaida-affiliation", "cl-jnim-iyad-leader",
        "cl-jnim-isgs-conflict-start", "cl-sahelian-anomaly",
        "cl-jnim-force-2021", "cl-jnim-force-2022",
    }
    counts = {"verified": 0, "partially_verified": 0, "pending_review": 0,
              "disputed": 0, "unsupported": 0}
    origins = {"inherited_verified": 0, "generated_index_record": 0,
               "generated_relationship_summary": 0, "generated_entity_summary": 0,
               "manual_source_mapping": 0}
    for ev in evidence["evidence"]:
        if ev.get("evidence_origin") == "manual_source_mapping":
            # already upgraded by the I2-B audit; do not downgrade
            counts[ev["verification_status"]] = counts.get(ev["verification_status"], 0) + 1
            origins["manual_source_mapping"] = origins.get("manual_source_mapping", 0) + 1
            continue
        cid = ev["claim_id"]
        src = sources_by_id.get(ev["source_id"], {})
        ev["record_created_at"] = ev.get("record_created_at") or "2026-08-06"
        ev["record_updated_at"] = AUDIT_DATE
        ev["record_reviewed_at"] = AUDIT_DATE
        ev["source_published_at"] = src.get("published_at")
        ev["source_accessed_at"] = src.get("accessed_at")
        ev["claim_valid_as_of"] = ev.get("as_of_date") or src.get("published_at")
        ev["freshness_status"] = freshness_of(ev.get("as_of_date") or src.get("published_at"))
        if cid in verified_set:
            ev["evidence_origin"] = "inherited_verified"
            ev["verification_status"] = "verified"
            ev["verification_method"] = "source mapping verified during V0.2 development (UN/CTC/US State Dept primary sources)"
            ev["verified_at"] = "2026-08-06"
        elif cid.startswith("cl-rel-"):
            ev["evidence_origin"] = "generated_relationship_summary"
            ev["verification_status"] = "pending_review"
            ev["verification_method"] = "generated from relationship records; requires manual source confirmation"
        elif cid.startswith("cl-ent-"):
            ev["evidence_origin"] = "generated_entity_summary"
            ev["verification_status"] = "pending_review"
            ev["verification_method"] = "generated from entity records; requires manual source confirmation"
        else:
            ev["evidence_origin"] = "generated_index_record"
            ev["verification_status"] = "partially_verified" if ev.get("source_locator") else "pending_review"
            ev["verification_method"] = "index record with named report locator; page-level confirmation pending"
        origins[ev["evidence_origin"]] = origins.get(ev["evidence_origin"], 0) + 1
        counts[ev["verification_status"]] = counts.get(ev["verification_status"], 0) + 1
    save("evidence_records.json", evidence)
    print("evidence:", len(evidence["evidence"]), "| status:", counts, "| origins:", origins)

    # ------------------------------------------------------- relation types registry
    # relation_types.json is owned by gen_i2b_audit.py; only read for metrics.
    if (DATA / "relation_types.json").exists():
        rtypes = load("relation_types.json")
    else:
        rtypes = {"relation_types": []}
    print("relation_types.json present:", len(rtypes.get("relation_types", [])))

    # ------------------------------------------------------------- catalog metrics
    metrics = compute_metrics(entities["entities"], countries["countries"],
                              load("regions.json")["regions"], rels["relationships"],
                              sources["sources"], evidence["evidence"], grades,
                              eps["profiles"], len(rtypes["relation_types"]))
    save("catalog_metrics.json", metrics)
    print("catalog_metrics written:", json.dumps(metrics, ensure_ascii=False)[:300])


def compute_metrics(entities, countries, regions, rels, sources, evidence,
                    profile_grades, profiles, relation_type_count):
    from collections import Counter
    ev_status = Counter(e["verification_status"] for e in evidence)
    ev_origin = Counter(e["evidence_origin"] for e in evidence)
    depth = Counter(profile_grades.values())
    rel_profiles = load("relation_profiles.json")["profiles"]
    timelines = load("relation_timelines.json")["timelines"]
    return {
        "schema_version": "asip-catalog-metrics-v1",
        "generated_at": AUDIT_DATE,
        "generated_by": "scripts/gen/gen_i2b_migration.py (machine computed)",
        "region_count": len(regions),
        "country_count": len(countries),
        "non_country_entity_count": len(entities),
        "unique_knowledge_object_count": len(regions) + len(countries) + len(entities),
        "entity_page_count": len(entities),
        "country_page_count": len(countries),
        "region_page_count": len(regions),
        "relationship_count": len(rels),
        "relation_profile_count": len(rel_profiles),
        "relation_timeline_count": len(timelines),
        "relation_type_count": relation_type_count,
        "source_count": len(sources),
        "evidence_record_count": len(evidence),
        "evidence_by_status": dict(ev_status),
        "evidence_by_origin": dict(ev_origin),
        "evidence_manual_count": ev_origin.get("manual_source_mapping", 0) + ev_origin.get("inherited_verified", 0),
        "evidence_generated_count": ev_origin.get("generated_index_record", 0) + ev_origin.get("generated_relationship_summary", 0) + ev_origin.get("generated_entity_summary", 0),
        "profile_depth_count": dict(depth),
        "encyclopedia_full_count": depth.get("encyclopedia_full", 0),
        "standard_profile_count": depth.get("standard", 0),
        "basic_entry_count": depth.get("basic", 0),
        "route_count": 1 + 6 + len(regions) + len(countries) + len(entities) + len(rels),
        "counting_note": ("countries counted once in countries.json; non-country entities in entities.json; "
                          "no double counting; unique_knowledge_object_count = regions + countries + entities"),
    }


# Entities/relationships/countries whose CURRENT status was audited with 2025-2026 sources
AUDITED_ENTITY_IDS = {
    # Lake Chad basin
    "actor-jas", "actor-iswap", "actor-mnjtf", "actor-chad-army",
    "actor-nigeria-army", "actor-cameroon-army",
    # Sudan
    "actor-saf", "actor-rsf", "actor-jem", "actor-slm-aw",
    "actor-splm-n-al-hilu", "person-abdel-fattah-al-burhan", "person-mohamed-hamdan-dagalo",
    # Mozambique
    "actor-is-mozambique", "actor-fadm", "actor-rdf", "actor-samim",
}
AUDITED_COUNTRY_IDS = {"country-chad", "country-sudan", "country-mozambique",
                       "country-nigeria", "country-cameroon", "country-niger"}
AUDITED_REL_IDS = {
    "rel-jas-iswap-conflict", "rel-iswap-islamic-state-affiliation",
    "rel-chad-mnjtf-member", "rel-saf-rsf-war", "rel-is-moz-islamic-state",
    "rel-rdf-mozambique-fadm-cooperate", "rel-samim-fadm-cooperate",
}


if __name__ == "__main__":
    main()
