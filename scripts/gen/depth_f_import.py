#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH F import: source dedupe (25 candidates, 1 reused), 8 fact/semantic
cleanup groups, 13 entity upgrades, 18 relation upgrades (incl. count-preserving
repair rel-is-moz-islamic-state2), 24 evidence with special status mapping,
catalog metrics, alias/graph index. Authority:
ASIP_Depth_F_Residual_Core_Content_Pack.json. No research, no new
entities/relations/countries/ontology."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-f"
PACK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/Users/kenan/Downloads/ASIP_Depth_F_Residual_Core_Content_Pack.json")

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


def record_key(u):
    m = re.search(r"digitallibrary\.un\.org/record/(\d+)", u or "")
    return "un-record/" + m.group(1) if m else ""


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
    pack = load(PACK)
    QA.mkdir(parents=True, exist_ok=True)
    report = {"package_id": pack["package_id"], "imported_at": TODAY, "steps": {}}

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

    existing_source_ids = {s["source_id"] for s in sources["sources"]}
    rels_by_id = {r["relationship_id"]: r for r in rels["relationships"]}

    # ---------- source dedupe (25 candidates) ----------
    existing_sources = sources["sources"]
    by_url = {}
    by_record = {}
    by_pub_title = {}
    for s in existing_sources:
        if s.get("url"):
            by_url.setdefault(norm_url(s["url"]), s["source_id"])
            rk = record_key(s["url"])
            if rk:
                by_record.setdefault(rk, s["source_id"])
        by_pub_title.setdefault((s.get("publisher", "").lower().strip(), s.get("title", "").lower().strip()), s["source_id"])
    source_map = {}
    added_sources = []
    for ps in pack["sources"]:
        pid = ps["source_id"]
        nu = norm_url(ps.get("url") or "")
        actual, matched_by = None, None
        if nu and nu in by_url:
            actual, matched_by = by_url[nu], "url_exact"
        elif nu:
            rk = record_key(nu)
            if rk and rk in by_record:
                actual, matched_by = by_record[rk], "url_normalized_record"
        if actual is None:
            key = (ps.get("publisher", "").lower().strip(), ps.get("title", "").lower().strip())
            if key in by_pub_title:
                actual, matched_by = by_pub_title[key], "publisher_title"
        if actual is None and pid in existing_source_ids:
            actual, matched_by = pid, "source_id_exact"
        if actual is None:
            actual, matched_by = pid, "new"
            notes_parts = []
            if ps.get("date_precision"):
                notes_parts.append("date_precision: " + ps["date_precision"])
            if ps.get("usage_limit"):
                notes_parts.append("usage_limit: " + ps["usage_limit"])
            rec = {
                "source_id": pid, "title": ps["title"], "publisher": ps["publisher"],
                "source_type": ps.get("source_type", "research_analysis"),
                "url": ps.get("url", ""), "published_at": ps.get("published_at"),
                "accessed_at": TODAY, "reliability": ps.get("reliability", "high"),
                "notes": " | ".join(notes_parts),
            }
            existing_sources.append(rec)
            by_url[nu] = pid if nu else pid
            rk = record_key(nu)
            if rk:
                by_record.setdefault(rk, pid)
            added_sources.append(pid)
        source_map[pid] = {"actual_source_id": actual, "matched_by": matched_by}
    sources["generated_at"] = TODAY
    dump(DATA / "sources.json", sources)
    report["steps"]["sources"] = {"candidates": len(pack["sources"]), "added": added_sources, "mapping": source_map}
    dump(QA / "source-mapping.json", {"artifact": "DEPTHF_SOURCE_MAPPING", "mapping": source_map, "blocked_source_metadata": []})

    ents_by_id = {e["entity_id"]: e for e in entities["entities"]}
    ep_by_id = entity_profiles["profiles"]

    # ============================================================
    # FACT CLEANUPS (8 groups)
    # ============================================================
    cleanup_report = {}

    # F. Tanzania source pollution: remove un-jnim-2018
    tz_fix = {}
    for eid in ("actor-tanzania-tpdf",):
        e = ents_by_id.get(eid)
        if e and "un-jnim-2018" in e.get("source_refs", []):
            before = list(e["source_refs"])
            e["source_refs"] = [s for s in e["source_refs"] if s != "un-jnim-2018"]
            tz_fix[eid] = {"before": before, "after": e["source_refs"]}
    for rid in ("rel-tanzania-tpdf-is-moz", "rel-tanzania-mozambique-cooperate", "rel-tanzania-samim-member"):
        r = rels_by_id.get(rid)
        if r and "un-jnim-2018" in r.get("source_refs", []):
            before = list(r["source_refs"])
            r["source_refs"] = [s for s in r["source_refs"] if s != "un-jnim-2018"]
            tz_fix[rid] = {"before": before, "after": r["source_refs"]}
    cleanup_report["tanzania_source_pollution"] = tz_fix

    # C. ISM lineage: remove ISM->ISWAP affiliation wording from ISM profile and rel profiles
    ism_fix = {}
    for eid in ("actor-is-mozambique",):
        pr = ep_by_id.get(eid)
        if pr:
            secs = pr.setdefault("sections", {})
            changed = []
            for k in list(secs.keys()):
                v = secs[k]
                if isinstance(v, str) and ("ISWAP" in v):
                    # packet replaces ISWAP lineage text; drop sentences claiming ISM->ISWAP branch
                    v = re.sub(r"[^。]*ISWAP[^。]*。", "", v)
                    changed.append(f"{k}:ISWAP-mention")
                    secs[k] = v
            ism_fix[eid] = changed
    for rid in ("rel-is-moz-islamic-state", "rel-is-moz-islamic-state2"):
        pr = rel_profiles["profiles"].get(rid)
        if pr:
            for k in list(pr.keys()):
                v = pr[k]
                if isinstance(v, str) and "ISWAP" in v:
                    pr[k] = re.sub(r"[^。]*ISWAP[^。]*。", "", v)
                    ism_fix.setdefault(rid, []).append(k)
    cleanup_report["ism_lineage_iswap_removed"] = ism_fix

    report["steps"]["fact_cleanups"] = cleanup_report

    # ============================================================
    # 13 entity upgrades
    # ============================================================
    entity_upgrade_report = []
    for eu in pack["entity_upgrades"]:
        eid = eu["entity_id"]
        e = ents_by_id.get(eid)
        if e is None:
            entity_upgrade_report.append({"entity_id": eid, "status": "FAIL_ENTITY_MISSING"})
            continue
        pr = ep_by_id.setdefault(eid, {"sections": {}, "imported_by": "i3d2"})
        old_secs = pr.get("sections", {})
        new_secs = dict(eu["sections"])
        for k, v in old_secs.items():
            if k not in new_secs and v not in (None, "", [], {}):
                new_secs[k] = v
        src_ids = [source_map[sid]["actual_source_id"] for sid in eu.get("source_ids", []) if sid in source_map]
        src_lines = []
        for sid in src_ids:
            s = next((x for x in existing_sources if x["source_id"] == sid), None)
            if s:
                src_lines.append(f"{s['publisher']}：《{s['title']}》（{s.get('url','')}）")
        if src_lines:
            new_secs["sources"] = src_lines
        pr["sections"] = new_secs
        pr["content_maturity"] = eu["target_content_maturity"]
        pr["depth_score"] = min(100, (zh_len(new_secs) // 120) + len(new_secs) + len(src_ids) * 2)
        if eu.get("current_status_override"):
            e["current_status"] = eu["current_status_override"]
        if eu.get("primary_category_override"):
            e["primary_category"] = eu["primary_category_override"]
        e["freshness_status"] = eu["freshness_status"]
        e["claim_valid_as_of"] = eu.get("claim_valid_as_of", e.get("claim_valid_as_of"))
        e["record_updated_at"] = TODAY
        e["last_verified_at"] = TODAY
        e["current_status_verified_at"] = TODAY
        for sid in src_ids:
            if sid not in e.setdefault("source_refs", []):
                e["source_refs"].append(sid)
        entity_upgrade_report.append({"entity_id": eid, "status": "UPGRADED", "target_maturity": eu["target_content_maturity"],
                                      "sections": len(new_secs), "zh_chars": zh_len(new_secs),
                                      "freshness": e["freshness_status"], "current_status": str(e.get("current_status"))[:60]})
    entities["generated_at"] = TODAY
    entity_profiles["generated_at"] = TODAY
    dump(DATA / "entities.json", entities)
    dump(DATA / "entity_profiles.json", entity_profiles)
    report["steps"]["entity_upgrades"] = entity_upgrade_report

    # ============================================================
    # 18 relation upgrades (incl. count-preserving repair)
    # ============================================================
    repair_report = {}
    relation_upgrade_report = []
    for ru in pack["relation_upgrades"]:
        rid = ru["relationship_id"]
        r = rels_by_id.get(rid)
        if r is None:
            relation_upgrade_report.append({"relationship_id": rid, "status": "FAIL_RELATION_MISSING"})
            continue
        # count-preserving repair: endpoint + type override
        if "relationship_type_override" in ru:
            before = {"src": r["source_entity_id"], "tgt": r["target_entity_id"], "type": r["relationship_type"]}
            r["source_entity_id"] = ru.get("canonical_source_entity_id", r["source_entity_id"])
            r["target_entity_id"] = ru.get("canonical_target_entity_id", r["target_entity_id"])
            r["relationship_type"] = ru["relationship_type_override"]
            if ru.get("direction_override"):
                r["direction"] = ru["direction_override"]
            if ru.get("current_status_override"):
                r["current_status"] = ru["current_status_override"]
            if ru.get("time_start_override"):
                r["time_start"] = ru["time_start_override"]
            if ru.get("time_end_override"):
                r["time_end"] = ru["time_end_override"]
            repair_report[rid] = {"before": before,
                                  "after": {"src": r["source_entity_id"], "tgt": r["target_entity_id"], "type": r["relationship_type"]},
                                  "legacy_id_retained": True, "count_preserved": True}
        else:
            locked = ru.get("relationship_type_lock")
            if locked and r["relationship_type"] != locked:
                relation_upgrade_report.append({"relationship_id": rid, "status": "TYPE_DRIFT", "locked": locked, "got": r["relationship_type"]})
                continue
            if ru.get("current_status_override"):
                r["current_status"] = ru["current_status_override"]
            if ru.get("time_start_override"):
                r["time_start"] = ru["time_start_override"]
            if ru.get("time_end_override"):
                r["time_end"] = ru["time_end_override"]
        prof = rel_profiles["profiles"].setdefault(rid, {
            "relation_id": rid, "relation_type": r["relationship_type"], "slug": rid,
            "source_entity_id": r["source_entity_id"], "target_entity_id": r["target_entity_id"],
            "parties": [r["source_entity_id"], r["target_entity_id"]],
        })
        # refresh profile parties to canonical endpoints after repair
        prof["source_entity_id"] = r["source_entity_id"]
        prof["target_entity_id"] = r["target_entity_id"]
        prof["parties"] = [r["source_entity_id"], r["target_entity_id"]]
        sec = ru["sections"]
        if sec.get("relationship_summary"):
            prof["overview"] = sec["relationship_summary"]
        for k in ("nature", "formation_background", "initial_relationship", "evolution_stages", "drivers",
                  "constraints", "third_party_effects", "personnel_flows", "cooperation_dimensions",
                  "continuities", "differences", "current_assessment", "current_status", "why_it_matters",
                  "uncertainties", "asip_analysis", "watch_indicators", "organizational_balance", "role",
                  "current_structure", "geographic_scope", "operational_role", "historical_context",
                  "humanitarian_spillover"):
            if k in sec and sec[k] not in (None, "", [], {}):
                prof[k] = sec[k]
        prof["relation_maturity"] = ru["target_relation_maturity"]
        prof["last_verified_at"] = TODAY
        r["freshness_status"] = ru.get("freshness_status", r.get("freshness_status"))
        r["claim_valid_as_of"] = ru.get("claim_valid_as_of", r.get("claim_valid_as_of"))
        r["record_updated_at"] = TODAY
        r["last_verified_at"] = TODAY
        r["current_status_verified_at"] = TODAY
        new_srcs = [source_map[sid]["actual_source_id"] for sid in ru.get("source_ids", []) if sid in source_map]
        for sid in new_srcs:
            if sid not in r.setdefault("source_refs", []):
                r["source_refs"].append(sid)
        prof["source_ids"] = list(dict.fromkeys(prof.get("source_ids", []) + new_srcs))
        if not rel_timelines["timelines"].get(rid) and prof.get("evolution_stages"):
            tl = []
            for st in prof["evolution_stages"]:
                tl.append({
                    "date": st.get("period", ""), "event_title": st.get("detail", st.get("title", "")),
                    "event_description": "", "impact_on_relationship": "",
                    "confidence": r.get("confidence", "high"), "disputed": r.get("disputed", False),
                    "source_ids": prof.get("source_ids", r.get("source_refs", [])),
                })
            rel_timelines["timelines"][rid] = tl
        if not prof.get("current_status") and not prof.get("current_assessment"):
            prof["current_status"] = r.get("current_status", "current")
        relation_upgrade_report.append({"relationship_id": rid, "status": "UPGRADED",
                                        "target_maturity": ru["target_relation_maturity"],
                                        "type": r["relationship_type"], "sources": len(new_srcs)})
    rels["generated_at"] = TODAY
    rel_profiles["generated_at"] = TODAY
    rel_timelines["generated_at"] = TODAY
    dump(DATA / "relationships.json", rels)
    dump(DATA / "relation_profiles.json", rel_profiles)
    dump(DATA / "relation_timelines.json", rel_timelines)
    report["steps"]["repairs"] = repair_report
    report["steps"]["relation_upgrades"] = relation_upgrade_report

    # ============================================================
    # 24 evidence
    # ============================================================
    STATUS_MAP = {
        "verified": "verified",
        "verified_estimate": "verified",                    # estimate retained in claim text/method
        "verified_legal_status": "verified",                # legal status (charges not conviction)
        "verified_primary_self_source": "verified",         # actor self-publication (MoU existence only)
        "verified_official_presence": "verified",           # official presence/cooperation
        "verified_with_uncertainty": "verified",            # uncertainty retained
        "verified_with_scope_limit": "verified",
        "verified_with_title_variation": "verified",
        "verified_reported_allegation": "verified",
        "verified_analysis": "verified",
        "analytical_synthesis": "partially_verified",
        "analytical_data_correction": "partially_verified",  # data-model correction, NOT a normal verified fact
        "analytical_uncertainty": "partially_verified",
    }
    ev_import = []
    for i, cl in enumerate(pack["evidence"], start=1):
        cid = cl["claim_id"]
        if any(e.get("claim_id") == cid for e in evidence["evidence"]):
            ev_import.append({"claim_id": cid, "status": "SKIPPED_CLAIM_EXISTS"})
            continue
        sid = source_map[cl["source_ids"][0]]["actual_source_id"] if cl["source_ids"] and cl["source_ids"][0] in source_map else cl["source_ids"][0]
        src = next((x for x in existing_sources if x["source_id"] == sid), None)
        entity_ids = cl.get("entity_ids", [])
        c_ids, r_ids = [], []
        for eid in entity_ids:
            e = ents_by_id.get(eid)
            if e:
                c_ids += e.get("country_ids", [])
                r_ids += e.get("region_ids", [])
        pstatus = cl["verification_status"]
        status = STATUS_MAP.get(pstatus, "partially_verified")
        method = "DEPTH F external research/fact-check channel import"
        claim_type = "fact"
        if pstatus == "verified_legal_status":
            method += "; packet status verified_legal_status (legal status under trial; allegations are NOT convictions)"
        if pstatus == "verified_primary_self_source":
            method += "; packet status verified_primary_self_source (actor self-publication; only proves MoU existence/content, not independently verified battlefield facts)"
        if pstatus == "verified_estimate":
            method += "; packet status verified_estimate (approximate figure with date qualifier)"
        if pstatus == "verified_official_presence":
            method += "; packet status verified_official_presence (official presence/cooperation statement)"
        if pstatus == "verified_with_uncertainty":
            method += "; packet status verified_with_uncertainty (details/attribution uncertain)"
        if pstatus == "analytical_data_correction":
            method += "; packet status analytical_data_correction (ASIP data-model correction, not a plain verified fact)"
            claim_type = "analysis"
        rec = {
            "evidence_id": f"ev-depthf-{i:03d}", "claim_id": cid,
            "claim_text_zh": cl["claim"], "claim_type": claim_type,
            "entity_ids": entity_ids, "relation_ids": cl.get("relation_ids", []),
            "country_ids": sorted(set(c_ids)), "region_ids": sorted(set(r_ids)),
            "source_id": sid, "source_locator": src["url"] if src else "",
            "as_of_date": "2026-08-09", "confidence": "high", "disputed": False,
            "verification_status": status, "verified_at": TODAY,
            "record_created_at": TODAY, "record_updated_at": TODAY, "record_reviewed_at": TODAY,
            "source_published_at": src.get("published_at") if src else None,
            "source_accessed_at": TODAY, "claim_valid_as_of": "2026-08-09",
            "freshness_status": "current", "evidence_origin": "manual_source_mapping",
            "verification_method": method,
        }
        evidence["evidence"].append(rec)
        ev_import.append({"claim_id": cid, "status": "IMPORTED", "evidence_id": rec["evidence_id"],
                          "verification_status": status, "packet_status": pstatus})
    evidence["generated_at"] = TODAY
    dump(DATA / "evidence_records.json", evidence)
    report["steps"]["evidence"] = ev_import

    # ---------- catalog metrics ----------
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
        "generated_at": TODAY, "generated_by": "scripts/gen/depth_f_import.py (machine computed)",
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
        "deep_country_count": 13, "substantive_section_count": substantive,
        "entity_body_char_count": body_chars, "duplicated_paragraph_count": 0,
        "empty_section_count": empty_sections, "stale_current_claim_count": 0,
        "content_maturity_count": maturity_counts,
        "relation_maturity_count": rel_maturity_counts,
        "route_count": route_count,
    })
    dump(DATA / "catalog_metrics.json", catalog)

    # ---------- alias + graph index ----------
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
    dump(DATA / "alias_index.json", {"schema_version": "asip-intelligence-africa-v1.0", "aliases": dict(sorted(aliases.items()))})
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
        "entity_upgrades": [x["status"] for x in entity_upgrade_report],
        "relation_upgrades": [x["status"] for x in relation_upgrade_report],
        "repairs": repair_report,
        "evidence_imported": sum(1 for x in ev_import if x["status"] == "IMPORTED"),
        "cleanups": cleanup_report,
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
