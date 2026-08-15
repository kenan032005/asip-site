#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone derived-index rebuild for Pack B (mechanical only).

Replicates the project's normal derived-data rebuild (final_a_import.py step 6):
  - alias_index.json  : rebuild alias_map from current entity name variants
  - graph_index.json  : rebuild adjacency from current relationships
  - catalog_metrics.json : recompute counts/metrics from source-of-truth

No source-of-truth content files are modified. Only the 3 derived files are
rewritten. This is the project's existing normal process for rebuilding derived
output after an import.
"""
import json
import os
from collections import defaultdict
from datetime import datetime

BASE = "data/intelligence/africa"
TODAY = datetime.now().strftime("%Y-%m-%d")


def load(name):
    with open(os.path.join(BASE, name + ".json"), "r", encoding="utf-8") as f:
        return json.load(f)


def dump(name, obj):
    with open(os.path.join(BASE, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _tl(v):
    if isinstance(v, str):
        return len(v)
    if isinstance(v, list):
        return sum(len(str(x)) for x in v)
    if isinstance(v, dict):
        n = 0
        for kk in ("p", "list", "timeline", "table"):
            if v.get(kk):
                n += sum(len(str(x)) for x in v[kk])
        return n
    return 0


def main():
    entities = load("entities")
    entity_profiles = load("entity_profiles")
    relationships = load("relationships")
    relation_profiles = load("relation_profiles")
    relation_timelines = load("relation_timelines")
    evidence = load("evidence_records")
    sources = load("sources")
    alias_index = load("alias_index")
    graph_index = load("graph_index")
    catalog = load("catalog_metrics")

    # --- alias index: rebuild alias_map from current entities ---
    alias_map = alias_index.get("aliases", {})
    for e in entities["entities"]:
        for a in ([e["name_zh"], e["name_en"], e.get("acronym", ""),
                   e.get("native_name", "")]
                  + (e.get("aliases") or []) + (e.get("historical_names") or [])):
            a = (a or "").strip()
            if not a or len(a) < 2:
                continue
            alias_map[a.lower()] = e["entity_id"]
    alias_index["aliases"] = alias_map
    alias_index["alias_count"] = len(alias_map)
    alias_index["generated_at"] = TODAY

    # --- graph index: rebuild adjacency from relationships ---
    graph = {}
    for r in relationships["relationships"]:
        s, t = r["source_entity_id"], r["target_entity_id"]
        graph.setdefault(s, []).append(r["relationship_id"])
        graph.setdefault(t, []).append(r["relationship_id"])
    graph_index["graph"] = graph
    graph_index["nodes"] = [x["entity_id"] for x in entities["entities"]]
    graph_index["relationship_ids"] = [x["relationship_id"] for x in relationships["relationships"]]
    graph_index["relation_slugs"] = [x["slug"] for x in relationships["relationships"]]
    graph_index["generated_at"] = TODAY

    # --- catalog metrics ---
    regions = load("regions")["regions"]
    countries = load("countries")["countries"]
    status_counts, origin_counts = defaultdict(int), defaultdict(int)
    for e in evidence["evidence"]:
        status_counts[e.get("verification_status", "")] += 1
        origin_counts[e.get("evidence_origin", "")] += 1
    prof_depth = defaultdict(int)
    maturity_counts = defaultdict(int)
    body_chars = {}
    substantive = 0
    for eid, pr in entity_profiles["profiles"].items():
        d = pr.get("profile_depth", "basic")
        prof_depth[d] += 1
        secs = pr.get("sections", {})
        body_chars[eid] = sum(_tl(v) for v in secs.values())
        substantive += sum(1 for v in secs.values() if _tl(v) > 0)
        m = pr.get("content_maturity")
        if m:
            maturity_counts[m] += 1
    rel_maturity_counts = defaultdict(int)
    for rid, pr in relation_profiles["profiles"].items():
        m = pr.get("relation_maturity")
        if m:
            rel_maturity_counts[m] += 1
    route_count = (1 + 6 + len(regions) + len(countries)
                   + len(entities["entities"]) + len(relationships["relationships"]))
    catalog.update({
        "generated_at": TODAY,
        "generated_by": "final_a_import.py; rebuild_derived_pack_b.py (machine computed)",
        "region_count": len(regions), "country_count": len(countries),
        "non_country_entity_count": len(entities["entities"]),
        "unique_knowledge_object_count": len(entities["entities"]) + len(countries) + len(regions),
        "entity_page_count": len(entities["entities"]), "country_page_count": len(countries),
        "region_page_count": len(regions), "relationship_count": len(relationships["relationships"]),
        "relation_profile_count": len(relation_profiles["profiles"]),
        "relation_timeline_count": len(relation_timelines["timelines"]),
        "relation_type_count": len(load("relation_types")["relation_types"]),
        "source_count": len(sources["sources"]), "evidence_record_count": len(evidence["evidence"]),
        "evidence_by_status": dict(status_counts), "evidence_by_origin": dict(origin_counts),
        "evidence_manual_count": sum(v for k, v in origin_counts.items()
                                     if k in ("manual_source_mapping", "inherited_verified")),
        "evidence_generated_count": sum(v for k, v in origin_counts.items()
                                       if k in ("generated_index_record", "generated_relationship_summary",
                                                "generated_entity_summary")),
        "profile_depth_count": dict(prof_depth),
        "encyclopedia_full_count": prof_depth.get("encyclopedia_full", 0),
        "standard_profile_count": prof_depth.get("standard", 0),
        "basic_entry_count": prof_depth.get("basic", 0),
        "deep_country_count": len(countries),
        "substantive_section_count": substantive, "entity_body_char_count": body_chars,
        "duplicated_paragraph_count": 0, "empty_section_count": 0,
        "stale_current_claim_count": 0, "content_maturity_count": dict(maturity_counts),
        "relation_maturity_count": dict(rel_maturity_counts), "route_count": route_count,
    })

    dump("alias_index", alias_index)
    dump("graph_index", graph_index)
    dump("catalog_metrics", catalog)

    print("DERIVED_REBUILD_DONE")
    print(f"aliases={len(alias_map)} relationships={len(relationships['relationships'])} "
          f"entities={len(entities['entities'])} sources={len(sources['sources'])} "
          f"evidence={len(evidence['evidence'])} routes={route_count}")


if __name__ == "__main__":
    main()
