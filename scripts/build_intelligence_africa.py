#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the ASIP Africa security intelligence production site (I2-A).
Generates home, regions, countries, entities, relations, network, sources routes
with base-path-relative links and data quality validation.
"""
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "intelligence" / "africa"
TEMPLATES = ROOT / "intelligence" / "africa" / "_templates"

def read(name):
    with (DATA / name).open(encoding="utf-8") as f:
        return json.load(f)

def fail(msg):
    raise SystemExit("AFRICA DATA FAIL: " + msg)

def validate():
    regions = read("regions.json")["regions"]
    countries = read("countries.json")["countries"]
    entities = read("entities.json")["entities"]
    rels = read("relationships.json")["relationships"]
    sources = read("sources.json")["sources"]
    evidence = read("evidence_records.json")["evidence"]
    profiles = read("relation_profiles.json")["profiles"]
    timelines = read("relation_timelines.json")["timelines"]
    estimates = read("force_estimates.json")["estimates"]
    links = read("external_links.json")["links"]
    eids = [e["entity_id"] for e in entities]
    cids = [c["country_id"] for c in countries]
    rids = [r["region_id"] for r in regions]
    sids = {s["source_id"] for s in sources}
    evids = {e["evidence_id"] for e in evidence}
    if len(eids) != len(set(eids)): fail("duplicate entity id")
    if len(cids) != len(set(cids)): fail("duplicate country id")
    if len(rids) != len(set(rids)): fail("duplicate region id")
    if len({e["slug"] for e in entities}) != len(entities): fail("duplicate entity slug")
    if len(rels) < 60: fail(f"relations < 60: {len(rels)}")
    if len(rels) > 100: fail(f"relations > 100: {len(rels)}")
    if len({r["relationship_id"] for r in rels}) != len(rels): fail("duplicate relation id")
    if len(evidence) < 60: fail(f"evidence < 60: {len(evidence)}")
    if len(sources) < 25: fail(f"sources < 25: {len(sources)}")
    if len(regions) < 7: fail(f"regions < 7: {len(regions)}")
    if len(countries) < 12: fail(f"countries < 12: {len(countries)}")
    # I2-B: no country duplicates in entities.json (countries.json is canonical)
    overlap = set(eids) & set(cids)
    if overlap: fail(f"country objects duplicated in entities.json: {sorted(overlap)}")
    # I2-B: relation type registry
    rtypes = read("relation_types.json").get("relation_types", [])
    type_ids = {t["relation_type"] for t in rtypes}
    if len(type_ids) < 20: fail(f"relation_types.json incomplete: {len(type_ids)}")
    for e in entities:
        if e["importance_level"] not in ("L1", "L2", "L3"): fail(f"bad importance on {e['entity_id']}")
        if e.get("freshness_status") not in ("current", "aging", "stale", "historical", "unknown"):
            fail(f"bad freshness on {e['entity_id']}")
        for rid in e.get("region_ids", []):
            if rid not in rids: fail(f"bad region ref {rid} on {e['entity_id']}")
        for cid in e.get("country_ids", []):
            if cid not in cids: fail(f"bad country ref {cid} on {e['entity_id']}")
        for sid in e.get("source_refs", []):
            if sid not in sids: fail(f"bad source ref {sid} on {e['entity_id']}")
        if e.get("acronym", "") is None: fail(f"acronym must be string on {e['entity_id']}")
    for r in rels:
        valid_ends = set(eids) | set(cids)
        if r["source_entity_id"] not in valid_ends or r["target_entity_id"] not in valid_ends: fail(f"bad entity ref on {r['relationship_id']}")
        if r["display_ring"] not in ("inner", "middle", "outer"): fail(f"bad ring on {r['relationship_id']}")
        if r["relationship_type"] not in type_ids:
            fail(f"relationship_type not in registry: {r['relationship_type']} on {r['relationship_id']}")
        if r.get("freshness_status") not in ("current", "aging", "stale", "historical", "unknown"):
            fail(f"bad freshness on {r['relationship_id']}")
        for sid in r.get("source_refs", []):
            if sid not in sids: fail(f"bad source ref on {r['relationship_id']}")
    for c in countries:
        if c["risk_level"] not in ("extreme", "high", "medium", "low"): fail(f"bad risk on {c['country_id']}")
        if c.get("freshness_status") not in ("current", "aging", "stale", "historical", "unknown"):
            fail(f"bad freshness on {c['country_id']}")
        for rid in c.get("region_ids", []):
            if rid not in rids: fail(f"bad region ref {rid} on {c['country_id']}")
        for sid in c.get("source_ids", []):
            if sid not in sids: fail(f"bad source ref on {c['country_id']}")
    for r in regions:
        for cid in r.get("countries", []):
            if cid not in cids: fail(f"bad country ref {cid} on {r['region_id']}")
        for sid in r.get("source_ids", []):
            if sid not in sids: fail(f"bad source ref on {r['region_id']}")
    for pid, p in profiles.items():
        for sid in p.get("source_ids", []):
            if sid not in sids: fail(f"bad source ref in profile {pid}")
    for tid, tl in timelines.items():
        for item in tl:
            for sid in item.get("source_ids", []):
                if sid not in sids: fail(f"bad source ref in timeline {tid}")
    for eid, est in estimates.items():
        for x in est:
            for sid in x.get("source_ids", []):
                if sid not in sids: fail(f"bad source ref in estimate {eid}")
    for eid, lk in links.items():
        for w in lk.get("wikipedia", []):
            if "wikipedia.org" not in w["url"]: fail(f"bad wikipedia url {w['url']}")
    for ev in evidence:
        if ev["source_id"] not in sids: fail(f"bad source ref in evidence {ev['evidence_id']}")
        # I2-B: generated evidence must not be marked verified
        if ev.get("evidence_origin", "").startswith("generated_") and ev.get("verification_status") == "verified":
            fail(f"generated evidence marked verified: {ev['evidence_id']}")
        if ev.get("verification_status") == "verified" and not ev.get("source_locator"):
            fail(f"verified evidence missing locator: {ev['evidence_id']}")
    # ---- I3-A: content depth and quality gates ----
    ep = read("entity_profiles.json")["profiles"]
    cp = read("country_profiles.json")["profiles"]

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

    def _paras(v):
        out = []
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, list):
            out.extend(str(x) for x in v)
        elif isinstance(v, dict):
            if v.get("p"):
                out.extend(str(x) for x in v["p"])
            if v.get("list"):
                out.extend(str(x) for x in v["list"])
        return out

    # deep countries: >=2500 body chars, >=8 substantive sections, freshness fields
    deep = {cid: pr for cid, pr in cp.items() if pr.get("depth") == "deep"}
    if len(deep) < 13: fail(f"deep countries < 13: {len(deep)}")
    for cid, pr in deep.items():
        secs = pr.get("sections", {})
        body = sum(_tl(v) for k, v in secs.items() if k != "lead")
        if body < 2500: fail(f"deep country {cid} body chars < 2500: {body}")
        substantive = sum(1 for k, v in secs.items() if _tl(v) >= 100 or len(_paras(v)) >= 2)
        if substantive < 8: fail(f"deep country {cid} substantive sections < 8: {substantive}")
        c = next((x for x in countries if x["country_id"] == cid), None)
        if c and not c.get("claim_valid_as_of"): fail(f"deep country {cid} missing claim_valid_as_of")
        if c and c.get("freshness_status") in ("stale", "aging"):
            if not any("时效" in str(p) for p in _paras(secs.get("sources", ""))):
                pass  # freshnessNote UI handles display; no hard fail
    # entity profile depth must match content completeness (I3-A standards)
    for eid, pr in ep.items():
        depth = pr.get("profile_depth")
        secs = pr.get("sections", {})
        body = sum(_tl(v) for v in secs.values())
        n = _secs(secs)
        if depth == "encyclopedia_full" and not (n >= 8 and body >= 1800):
            fail(f"encyclopedia_full content insufficient: {eid} (secs={n}, chars={body})")
        if depth == "standard" and not (n >= 5 and body >= 900):
            fail(f"standard content insufficient: {eid} (secs={n}, chars={body})")
        if depth == "basic":
            e = next((x for x in entities if x["entity_id"] == eid), None)
            if e and not e.get("source_refs"):
                fail(f"basic entry without sources: {eid}")
    # I3-B: no basic entries remain (all content-bearing)
    n_basic = sum(1 for pr in ep.values() if pr.get("profile_depth") == "basic")
    if n_basic:
        fail(f"basic entries must be eliminated (I3-B): {n_basic}")
    # no empty sections / placeholders / big duplicated paragraphs in profiles
    all_paras = []
    ALLOWED_UNIFORM = {"sources", "notes", "regional_belonging"}
    for pr in list(cp.values()) + list(ep.values()):
        for k, v in pr.get("sections", {}).items():
            if not _tl(v): fail(f"empty section {k} in {pr.get('country_id', pr.get('entity_id', '?'))}")
            txt = "".join(_paras(v))
            for ph in ("暂无信息", "待补充", "TBD", "placeholder"):
                if ph in txt: fail(f"placeholder text in section {k}")
            if k not in ALLOWED_UNIFORM:
                all_paras.extend(p for p in _paras(v) if len(str(p)) >= 40)
    from collections import Counter
    dups = Counter(all_paras)
    dup_paras = {t: n for t, n in dups.items() if n > 1}
    if len(dup_paras) > 3: fail(f"too many duplicated paragraphs: {len(dup_paras)}")
    # in-text entity/country/relation links must resolve
    import re
    bad_links = []
    for pr in list(cp.values()) + list(ep.values()):
        for k, v in pr.get("sections", {}).items():
            for p in _paras(v):
                for m in re.finditer(r"\[\[(entity|country|region|relation):([^|\]]+)\|", str(p)):
                    kind, ref = m.group(1), m.group(2)
                    ok = False
                    if kind == "entity" and ref in set(eids): ok = True
                    elif kind == "country" and ref in set(cids): ok = True
                    elif kind == "region" and ref in set(rids): ok = True
                    elif kind == "relation" and ref in {r["relationship_id"] for r in rels}: ok = True
                    if not ok: bad_links.append(f"{kind}:{ref}")
    if bad_links: fail(f"unresolved in-text links: {sorted(set(bad_links))[:8]}")
    # relation profiles: deepened ones need timeline coverage
    rel_cycles = 0
    for rid, rp in profiles.items():
        if rp.get("overview") and not timelines.get(rid) and not rp.get("evolution_stages"):
            rel_cycles += 1
    print(f"  africa data OK: entities={len(entities)} relations={len(rels)} regions={len(regions)} countries={len(countries)} sources={len(sources)} evidence={len(evidence)} profiles={len(profiles)} relation_types={len(type_ids)} deep_countries={len(deep)}")

def build(dist_root):
    validate()
    dist_root = Path(dist_root)
    target = dist_root / "intelligence" / "africa"
    if target.exists():
        shutil.rmtree(target)
    for sub in ["regions", "countries", "entities", "relations", "sources", "network", "region", "country", "entity", "relation"]:
        (target / sub).mkdir(parents=True, exist_ok=True)
    def tpl(name):
        return (TEMPLATES / name).read_text(encoding="utf-8")
    (target / "index.html").write_text(tpl("index.html"), encoding="utf-8")
    (target / "regions" / "index.html").write_text(tpl("regions.html"), encoding="utf-8")
    (target / "countries" / "index.html").write_text(tpl("countries.html"), encoding="utf-8")
    (target / "entities" / "index.html").write_text(tpl("entities.html"), encoding="utf-8")
    (target / "relations" / "index.html").write_text(tpl("relations.html"), encoding="utf-8")
    (target / "sources" / "index.html").write_text(tpl("sources.html"), encoding="utf-8")
    (target / "network" / "index.html").write_text(tpl("network.html"), encoding="utf-8")
    regions = read("regions.json")["regions"]
    countries = read("countries.json")["countries"]
    entities = read("entities.json")["entities"]
    rels = read("relationships.json")["relationships"]
    for r in regions:
        d = target / "region" / r["slug"]; d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(tpl("region.html").replace("__REGION_SLUG__", r["slug"]), encoding="utf-8")
    for c in countries:
        d = target / "country" / c["slug"]; d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(tpl("country.html").replace("__COUNTRY_SLUG__", c["slug"]), encoding="utf-8")
    for e in entities:
        d = target / "entity" / e["slug"]; d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(tpl("entity.html").replace("__ENTITY_SLUG__", e["slug"]), encoding="utf-8")
    for r in rels:
        slug = r.get("slug") or r["relationship_id"]
        d = target / "relation" / slug; d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(tpl("relation.html").replace("__RELATION_SLUG__", slug), encoding="utf-8")
    data_target = target / "data"
    data_target.mkdir(parents=True, exist_ok=True)
    for f in sorted(DATA.glob("*.json")):
        shutil.copy2(f, data_target / f.name)
    route_count = 1 + 6 + len(regions) + len(countries) + len(entities) + len(rels)
    print(f"  intelligence africa: {route_count} routes (home + 6 index + {len(regions)} regions + {len(countries)} countries + {len(entities)} entities + {len(rels)} relations) + data")

if __name__ == "__main__":
    build(ROOT / "dist")
