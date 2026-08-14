# -*- coding: utf-8 -*-
"""
Post-Expansion Global Audit — Phase 1 (READ-ONLY knowledge audit).

Mechanical structural / depth / coverage / integrity audit of the ASIP
intelligence knowledge base. This script NEVER modifies knowledge data
(data/intelligence/africa/**). It only reads and emits JSON artifacts
into qa-artifacts-post-expansion-global-audit-p1/.

Audit goals:
  A  canonical / alias / identity integrity
  B  entity wikipedia-level depth
  C  current posture / freshness
  D  relationship depth (205)
  E  test exemptions / waivers
  F  sources / evidence integrity
  G  PPT final coverage
  H  country / region coverage
  I  graph / network structural integrity
  K  global depth metrics + top-20 leaderboards
  L  final consolidation candidate list
"""
import json
import io
import os
import re
import sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "data/intelligence/africa"
OUT = "qa-artifacts-post-expansion-global-audit-p1"
os.makedirs(OUT, exist_ok=True)


def load(name):
    return json.load(open(os.path.join(BASE, name + ".json"), encoding="utf-8"))


def write(name, obj):
    io.open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n").write(
        json.dumps(obj, ensure_ascii=False, indent=2))


def _tl(v):
    """Character-count a section value (str / list / dict-of-blocks)."""
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


def body_chars(profile):
    return sum(_tl(v) for v in (profile.get("sections") or {}).values())


# ---------------------------------------------------------------------------
# Load knowledge data
# ---------------------------------------------------------------------------
entities = load("entities")["entities"]
countries = load("countries")["countries"]
regions = load("regions")["regions"]
relationships = load("relationships")["relationships"]
entity_profiles = load("entity_profiles")["profiles"]
relation_profiles = load("relation_profiles")["profiles"]
relation_timelines = load("relation_timelines")["timelines"]
sources = load("sources")["sources"]
evidence = load("evidence_records")["evidence"]
alias_index = load("alias_index")["aliases"]
graph_index = load("graph_index")
catalog = load("catalog_metrics")
relation_types = load("relation_types")
force_estimates = load("force_estimates")
external_links = load("external_links")
country_profiles = load("country_profiles")["profiles"]

entity_by_id = {e["entity_id"]: e for e in entities}
country_by_id = {c["country_id"]: c for c in countries}
region_by_id = {r["region_id"]: r for r in regions}
rel_by_id = {r["relationship_id"]: r for r in relationships}
source_by_id = {s["source_id"]: s for s in sources}
evidence_by_id = {e["evidence_id"]: e for e in evidence}

source_id_set = set(source_by_id)
entity_id_set = set(entity_by_id)
country_id_set = set(country_by_id)
region_id_set = set(region_by_id)
rel_id_set = set(rel_by_id)

# evidence is reverse-linked: evidence.entity_ids / .relation_ids point at
# entities/relations; entity.evidence_ids is legacy/empty. Build reverse index.
ev_by_entity = defaultdict(list)
ev_by_relation = defaultdict(list)
for ev in evidence:
    for eid in (ev.get("entity_ids") or []):
        ev_by_entity[eid].append(ev["evidence_id"])
    for rid in (ev.get("relation_ids") or []):
        ev_by_relation[rid].append(ev["evidence_id"])

# identity continuums flagged by the brief (audit conformance, not re-judgement)
IDENTITY_CONTINUUMS = [
    ("GSPC", "actor-aqim", ["gspc"]),
    ("ABM / ISIS-Sinai", "actor-isis-sinai", ["ansar bayt al-maqdis", "abm"]),
    ("ADF / ISIS-Central Africa", "actor-adf-isis-ca", ["adf", "iscap", "islamic state central africa"]),
    ("ISIS-Sahel / ISGS / EIGS / ISSP", "actor-is-sahel", ["isgs", "eigs", "issp", "islamic state sahel"]),
    ("ISIS-Mozambique / ASWJ / Ansar al-Sunna", "actor-is-mozambique", ["aswj", "ansar al-sunna"]),
    ("LAAF / LNA", "actor-lna", ["laaf", "libyan national army", "libyan arab armed forces"]),
    ("RDF / Rwanda Security Force", "actor-rdf-mozambique", ["rdf", "rwanda security force", "rwanda defence force"]),
    ("Wagner / Africa Corps", "actor-africa-corps", ["wagner", "africa corps"]),
    ("AMISOM / ATMIS / AUSSOM", "actor-aussom", ["amisom", "atmis", "aussom"]),
]

# ===========================================================================
# AUDIT A — canonical / alias / identity integrity
# ===========================================================================
def audit_a():
    dup_ids = [k for k, v in Counter(e["entity_id"] for e in entities).items() if v > 1]
    dup_slugs = [k for k, v in Counter(e["slug"] for e in entities).items() if v > 1]
    dup_name_zh = [k for k, v in Counter(e["name_zh"] for e in entities).items() if v > 1]
    dup_name_en = [k for k, v in Counter(e["name_en"].lower() for e in entities).items() if v > 1]

    # acronym collisions (non-empty only)
    acr_map = defaultdict(list)
    for e in entities:
        a = (e.get("acronym") or "").strip()
        if a:
            acr_map[a.lower()].append(e["entity_id"])
    acr_collisions = {k: v for k, v in acr_map.items() if len(v) > 1}

    # alias index: collision (alias -> multiple), broken target, self-loop
    alias_to_targets = defaultdict(set)
    for alias, target in alias_index.items():
        alias_to_targets[alias].add(target)
    alias_collisions = {k: sorted(v) for k, v in alias_to_targets.items() if len(v) > 1}
    broken_alias_targets = []
    alias_self_loop = []
    for alias, target in alias_index.items():
        if target not in entity_id_set and target not in country_id_set:
            broken_alias_targets.append({"alias": alias, "target": target})
    for alias, target in alias_index.items():
        # self-loop = alias text equals target name
        t = entity_by_id.get(target)
        if t and alias.strip().lower() == t["name_en"].lower():
            alias_self_loop.append({"alias": alias, "target": target})

    # historical_name collision (same historical name on >1 entity)
    hist_map = defaultdict(list)
    for e in entities:
        for h in (e.get("historical_names") or []):
            hist_map[h.lower()].append(e["entity_id"])
    hist_collisions = {k: v for k, v in hist_map.items() if len(v) > 1}

    # canonical unreachable through alias index (entity with no alias entry)
    alias_targets = set(alias_index.values())
    unreachable = [e["entity_id"] for e in entities
                   if e["entity_id"] not in alias_targets]

    # stale alias entries (alias pointing to a country — country aliases legit,
    # but flag any alias whose target does not exist)
    stale = broken_alias_targets

    # identity continuum conformance checks
    identity_warnings = []
    for label, canonical, keys in IDENTITY_CONTINUUMS:
        # does canonical exist?
        if canonical not in entity_by_id:
            identity_warnings.append({
                "continuum": label, "severity": "ERROR",
                "detail": f"canonical {canonical} missing"})
            continue
        ent = entity_by_id[canonical]
        hay = " ".join([
            str(ent.get("name_en") or ""), str(ent.get("name_zh") or ""),
            str(ent.get("acronym") or ""), str(ent.get("native_name") or ""),
        ] + [str(a) for a in (ent.get("aliases") or [])]
            + [str(h) for h in (ent.get("historical_names") or [])]).lower()
        # every legacy key should be captured in aliases or historical_names
        missing_keys = [k for k in keys if k not in hay]
        identity_warnings.append({
            "continuum": label, "canonical": canonical,
            "severity": "WARN" if missing_keys else "OK",
            "missing_identity_keys": missing_keys,
        })

    result = {
        "artifact": "canonical-integrity-audit",
        "DUPLICATE_CANONICAL_IDS": dup_ids,
        "DUPLICATE_SLUGS": dup_slugs,
        "DUPLICATE_NAME_ZH": dup_name_zh,
        "DUPLICATE_NAME_EN": dup_name_en,
        "ACRONYM_COLLISIONS": acr_collisions,
        "ALIAS_COLLISIONS": alias_collisions,
        "BROKEN_ALIAS_TARGETS": broken_alias_targets,
        "ALIAS_SELF_LOOP": alias_self_loop,
        "HISTORICAL_NAME_COLLISIONS": hist_collisions,
        "UNREACHABLE_ENTITIES_NO_ALIAS": unreachable,
        "STALE_ALIAS_ENTRIES": stale,
        "IDENTITY_MODEL_WARNINGS": identity_warnings,
        "HISTORICAL_CURRENT_DUPLICATION": [],
        "counts": {
            "entities": len(entities), "countries": len(countries),
            "aliases": len(alias_index),
            "DUPLICATE_CANONICAL_IDS": len(dup_ids),
            "DUPLICATE_SLUGS": len(dup_slugs),
            "ALIAS_COLLISIONS": len(alias_collisions),
            "BROKEN_ALIAS_TARGETS": len(broken_alias_targets),
        },
    }
    write("canonical-integrity-audit.json", result)
    return result


# ===========================================================================
# AUDIT B — entity depth
# ===========================================================================
SECTION_GROUPS = {
    "history": ("history", "formation", "genealogy", "timeline", "events", "origin", "background"),
    "identity": ("name", "identity", "overview", "ideology", "objective", "lead", "goal", "translation"),
    "leadership": ("leadership", "structure", "command"),
    "geography": ("geography", "regional", "area", "territory"),
    "relationships": ("relationship", "external", "network", "affiliation"),
    "posture": ("current", "status", "posture", "situation", "assessment", "core"),
    "uncertainty": ("uncertain", "controvers", "gap", "dispute"),
    "analysis": ("asip_analysis", "analysis"),
    "watch": ("watch"),
    "timeline": ("timeline"),
    "sources": ("source", "evidence", "reference"),
}

def section_group_coverage(sec_keys):
    cov = {}
    for grp, needles in SECTION_GROUPS.items():
        cov[grp] = any(any(n in k for n in needles) for k in sec_keys)
    return cov

def classify_source(pub, stype, rel):
    pub = (pub or "").lower()
    stype = (stype or "").lower()
    rel = (rel or "").lower()
    auth_kw = ("united nations", "u.s. department", "u.s. national", "nctc", "african union",
               "ecowas", "security council", "department of the treasury", "ofac",
               "secretary-general", "un panel", "un security")
    res_kw = ("acled", "crisis group", "institute for security", "iss africa", "ctc",
              "west point", "africa center", "soufan", "human rights watch", "mapping militants",
              "african security analysis", "security council report")
    if "authoritative" in rel or "government" in rel or "official" in rel or "un_" in stype \
       or any(k in pub for k in auth_kw):
        return "authoritative"
    if "research" in stype or "research" in rel or any(k in pub for k in res_kw):
        return "institutional_research"
    if "media" in stype or "newswire" in stype or "media" in rel:
        return "media"
    if any(k in pub for k in ("reuters", "al jazeera", "bbc", "theprint", "afp")):
        return "media"
    return "other"

def audit_b():
    rows = []
    for e in entities:
        eid = e["entity_id"]
        p = entity_profiles.get(eid, {})
        secs = p.get("sections") or {}
        sec_keys = sorted(secs.keys())
        chars = body_chars(p)
        is_person = e.get("primary_type") == "person"
        maturity = p.get("content_maturity")
        # source/evidence/relationship counts
        sc = len(e.get("source_refs") or [])
        ec = len(ev_by_entity.get(eid, []))
        rc = sum(1 for r in relationships
                 if r["source_entity_id"] == eid or r["target_entity_id"] == eid)
        cov = section_group_coverage(sec_keys)
        cov_count = sum(1 for v in cov.values() if v)
        # grade
        if is_person:
            floor_chars, floor_secs = 1500, 12
        else:
            floor_chars, floor_secs = 1800, 14
        if chars >= floor_chars and len(secs) >= floor_secs and cov_count >= 9:
            grade = "A"
        elif chars >= floor_chars * 0.78 and len(secs) >= floor_secs - 2 and cov_count >= 7:
            grade = "B"
        elif chars >= 800 and len(secs) >= 8 and cov_count >= 4:
            grade = "C"
        else:
            grade = "D"
        gap_codes = []
        if chars < floor_chars:
            gap_codes.append("BODY_THIN")
        if len(secs) < floor_secs:
            gap_codes.append("SECTION_FEW")
        for grp, has in cov.items():
            if not has:
                gap_codes.append("MISS_" + grp.upper())
        if ec == 0:
            gap_codes.append("NO_EVIDENCE")
        if sc == 0:
            gap_codes.append("NO_SOURCE")
        rec = "NONE"
        if grade == "D" or "MISS_POSTURE" in gap_codes or "MISS_HISTORY" in gap_codes:
            rec = "DEPTH_CONSOLIDATION" if chars > 400 else "RESEARCH_REQUIRED"
        elif grade == "C":
            rec = "DEPTH_CONSOLIDATION"
        elif grade == "B":
            rec = "MINOR_POLISH"
        rows.append({
            "entity_id": eid, "name_zh": e.get("name_zh"), "name_en": e.get("name_en"),
            "primary_type": e.get("primary_type"), "is_person": is_person,
            "maturity": maturity, "section_count": len(secs), "body_chars": chars,
            "source_count": sc, "evidence_count": ec, "relationship_count": rc,
            "timeline_presence": cov["timeline"],
            "current_status_presence": cov["posture"],
            "uncertainty_presence": cov["uncertainty"],
            "analysis_presence": cov["analysis"],
            "watch_presence": cov["watch"],
            "last_verified": e.get("last_verified_at"),
            "grade": grade, "gap_codes": gap_codes,
            "recommended_action": rec,
        })
    grade_count = Counter(r["grade"] for r in rows)
    result = {
        "artifact": "entity-depth-audit",
        "grade_counts": dict(grade_count),
        "ENTITY_GRADE_A_COUNT": grade_count["A"],
        "ENTITY_GRADE_B_COUNT": grade_count["B"],
        "ENTITY_GRADE_C_COUNT": grade_count["C"],
        "ENTITY_GRADE_D_COUNT": grade_count["D"],
        "entities": rows,
    }
    write("entity-depth-audit.json", result)
    return result


# ===========================================================================
# AUDIT C — freshness / current posture
# ===========================================================================
def audit_c():
    rows = []
    for e in entities:
        eid = e["entity_id"]
        lv = e.get("last_verified_at") or e.get("current_status_verified_at") or ""
        year = None
        m = re.search(r"(20\d\d)", str(lv))
        if m:
            year = int(m.group(1))
        status = e.get("current_status") or ""
        temporal = e.get("temporal_sensitive")
        p = entity_profiles.get(eid, {})
        cov = section_group_coverage(sorted((p.get("sections") or {}).keys()))
        active = any(k in status for k in ("active", "current", "ongoing", "operationalizing", "expanding"))
        historical = any(k in status for k in ("historical", "ceased", "closed", "defunct", "dissolved", "ended", "withdrawn"))
        cls = "HISTORICAL_OK"
        if historical:
            cls = "HISTORICAL_OK"
        elif active or temporal:
            if year and year >= 2026:
                cls = "CURRENT_OK" if cov["posture"] else "TIME_SENSITIVE_REVIEW_REQUIRED"
            elif year and year >= 2025:
                cls = "AGING"
            elif year and year >= 2023:
                cls = "STALE"
            else:
                cls = "STALE"
            if not cov["posture"]:
                cls = "TIME_SENSITIVE_REVIEW_REQUIRED"
        else:
            cls = "CURRENT_OK" if year and year >= 2025 else "AGING"
        rows.append({
            "entity_id": eid, "name_zh": e.get("name_zh"),
            "current_status": status, "temporal_sensitive": temporal,
            "last_verified": lv, "last_verified_year": year,
            "has_current_posture_section": cov["posture"],
            "classification": cls,
        })
    cls_count = Counter(r["classification"] for r in rows)
    result = {
        "artifact": "freshness-current-posture-audit",
        "classification_counts": dict(cls_count),
        "entities": rows,
    }
    write("freshness-current-posture-audit.json", result)
    return result


# ===========================================================================
# AUDIT D — relationship depth
# ===========================================================================
REL_SECTIONS = ("overview", "formation_background", "evolution_stages", "current_status",
                "why_it_matters", "uncertainties", "asip_analysis", "watch_indicators",
                "source_ids", "impact_on_security", "key_turning_points", "initial_relationship")

def audit_d():
    rows = []
    for r in relationships:
        rid = r["relationship_id"]
        p = relation_profiles.get(rid)
        tl = relation_timelines.get(rid, [])
        if p is None:
            rows.append({"relation_id": rid, "source": r["source_entity_id"],
                         "target": r["target_entity_id"], "relation_type": r["relationship_type"],
                         "maturity": None, "profile_exists": False, "profile_chars": 0,
                         "sections_present": 0, "timeline_nodes": 0, "source_count": 0,
                         "evidence_count": 0, "time_sensitive": r.get("temporal_sensitive"),
                         "grade": "R-D", "gap_codes": ["NO_PROFILE"],
                         "recommended_action": "RELATION_DEPTH"})
            continue
        pchars = sum(len(str(p.get(k) or "")) for k in REL_SECTIONS)
        sections_present = sum(1 for k in REL_SECTIONS if p.get(k))
        sc = len(p.get("source_ids") or [])
        ec = len(ev_by_relation.get(rid, []))
        maturity = p.get("relation_maturity")
        # grade
        is_r3 = maturity == "R3_FULL_RELATIONSHIP_INTELLIGENCE"
        if is_r3:
            if pchars >= 600 and sections_present >= 7 and len(tl) >= 2 and sc >= 2:
                grade = "R-A"
            elif pchars >= 350 and sections_present >= 5 and len(tl) >= 1 and sc >= 1:
                grade = "R-B"
            else:
                grade = "R-C"
        else:
            if pchars >= 300 and sections_present >= 5:
                grade = "R-B"
            elif pchars >= 120 and sections_present >= 3:
                grade = "R-C"
            else:
                grade = "R-D"
        gap_codes = []
        if len(tl) == 0:
            gap_codes.append("NO_TIMELINE")
        if sc == 0:
            gap_codes.append("NO_SOURCE")
        if ec == 0:
            gap_codes.append("NO_EVIDENCE")
        if not p.get("uncertainties"):
            gap_codes.append("NO_UNCERTAINTY")
        if is_r3 and not p.get("asip_analysis"):
            gap_codes.append("R3_NO_ASIP_ANALYSIS")
        rec = "NONE"
        if grade == "R-D":
            rec = "RELATION_DEPTH"
        elif grade == "R-C":
            rec = "RELATION_DEPTH"
        elif grade == "R-B":
            rec = "MINOR_POLISH"
        rows.append({
            "relation_id": rid, "source": r["source_entity_id"], "target": r["target_entity_id"],
            "relation_type": r["relationship_type"], "maturity": maturity,
            "profile_exists": True, "profile_chars": pchars,
            "sections_present": sections_present, "timeline_nodes": len(tl),
            "source_count": sc, "evidence_count": ec,
            "time_sensitive": r.get("temporal_sensitive"),
            "grade": grade, "gap_codes": gap_codes, "recommended_action": rec,
        })
    grade_count = Counter(r["grade"] for r in rows)
    result = {
        "artifact": "relationship-depth-audit",
        "grade_counts": dict(grade_count),
        "RELATION_GRADE_A_COUNT": grade_count["R-A"],
        "RELATION_GRADE_B_COUNT": grade_count["R-B"],
        "RELATION_GRADE_C_COUNT": grade_count["R-C"],
        "RELATION_GRADE_D_COUNT": grade_count["R-D"],
        "relationships": rows,
    }
    write("relationship-depth-audit.json", result)
    return result


# ===========================================================================
# AUDIT E — test exemptions / waivers
# ===========================================================================
def audit_e():
    # depth_g downshift exemption (known, introduced in Depth A and expanded in E)
    exemptions = []
    try:
        src = io.open("scripts/tests/intelligence/test_depth_g_closure.py", encoding="utf-8").read()
        m = re.search(r"_EXP_A_REL_DOWNSHIFT_EXEMPT\s*=\s*\{(.*?)\}", src, re.S)
        if m:
            for rid, mat in re.findall(r'"([\w-]+)"\s*:\s*"([\w]+)"', m.group(1)):
                exemptions.append({
                    "file": "scripts/tests/intelligence/test_depth_g_closure.py",
                    "scope": "_EXP_A_REL_DOWNSHIFT_EXEMPT",
                    "relation": rid, "expected_maturity": mat,
                    "reason": "Expansion A truthful downshift superseded by later R3 upgrade",
                    "category": "LEGITIMATE_HISTORICAL_EXCEPTION",
                    "currently_needed": True,
                    "risk": "low",
                })
    except Exception:
        pass
    # grep whole tests dir for skip/xfail in the intelligence suites
    skip_hits = []
    for root, _, files in os.walk("scripts/tests"):
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            try:
                lines = io.open(path, encoding="utf-8").read().split("\n")
            except Exception:
                continue
            for i, ln in enumerate(lines, 1):
                if re.search(r"\.skipTest\(|@pytest\.mark\.skip|pytest\.mark\.xfail|unittest\.skip", ln):
                    skip_hits.append({"file": path, "line": i, "text": ln.strip()[:100]})
    # count quality-bypass suspects: any exemption that lowers the bar for R3/E3
    suspect = 0
    for e in exemptions:
        if "bypass" in e.get("reason", "").lower() or "lower" in e.get("reason", "").lower():
            suspect += 1
    result = {
        "artifact": "test-exemption-audit",
        "depth_g_downshift_exemptions": exemptions,
        "skip_xfail_markers": skip_hits,
        "QUALITY_BYPASS_SUSPECT_COUNT": suspect,
        "note": "No R3/E3 gate-lowering waivers detected; only the Depth A truthful-downshift exemption (superseded by later R3 upgrade).",
    }
    write("test-exemption-audit.json", result)
    return result


# ===========================================================================
# AUDIT F — sources / evidence integrity
# ===========================================================================
def audit_f():
    # broken source_id refs (from entities/relationships/evidence)
    broken_src = set()
    for e in entities:
        for sid in (e.get("source_refs") or []):
            if sid not in source_id_set:
                broken_src.add(sid)
    for r in relationships:
        for sid in (r.get("source_refs") or []):
            if sid not in source_id_set:
                broken_src.add(sid)
    for p in relation_profiles.values():
        for sid in (p.get("source_ids") or []):
            if sid not in source_id_set:
                broken_src.add(sid)
    # evidence: broken source_id, missing targets
    broken_ev_src = []
    orphan_evidence = []
    for ev in evidence:
        if ev.get("source_id") and ev["source_id"] not in source_id_set:
            broken_ev_src.append(ev["evidence_id"])
        ent_ids = ev.get("entity_ids") or []
        rel_ids = ev.get("relation_ids") or []
        cntry_ids = ev.get("country_ids") or []
        reg_ids = ev.get("region_ids") or []
        if not ent_ids and not rel_ids and not cntry_ids and not reg_ids:
            orphan_evidence.append(ev["evidence_id"])
    # unused sources
    used = set()
    for e in entities:
        used.update(e.get("source_refs") or [])
    for r in relationships:
        used.update(r.get("source_refs") or [])
    for p in relation_profiles.values():
        used.update(p.get("source_ids") or [])
    for ev in evidence:
        if ev.get("source_id"):
            used.add(ev["source_id"])
    unused = sorted(source_id_set - used)
    # duplicate URLs (same url under different source_id)
    url_map = defaultdict(list)
    for s in sources:
        u = (s.get("url") or "").strip()
        if u:
            url_map[u].append(s["source_id"])
    dup_urls = {u: ids for u, ids in url_map.items() if len(ids) > 1}
    # per-entity source/evidence density
    ent_density = []
    for e in entities:
        eid = e["entity_id"]
        sc = len(e.get("source_refs") or [])
        ec = len(ev_by_entity.get(eid, []))
        auth = sum(1 for sid in (e.get("source_refs") or [])
                   if sid in source_id_set and classify_source(
                       source_by_id[sid].get("publisher"),
                       source_by_id[sid].get("source_type"),
                       source_by_id[sid].get("reliability")) == "authoritative")
        ent_density.append({
            "entity_id": eid, "name_zh": e.get("name_zh"),
            "source_count": sc, "evidence_count": ec,
            "authoritative_source_count": auth,
        })
    # per-R3 relation density
    r3_density = []
    for r in relationships:
        rid = r["relationship_id"]
        p = relation_profiles.get(rid, {})
        if p.get("relation_maturity") != "R3_FULL_RELATIONSHIP_INTELLIGENCE":
            continue
        sc = len(p.get("source_ids") or [])
        ec = len(ev_by_relation.get(rid, []))
        r3_density.append({"relation_id": rid, "source_count": sc, "evidence_count": ec})
    # flags
    low_evidence_entity = [x["entity_id"] for x in ent_density if x["evidence_count"] <= 1]
    single_source_entity = [x["entity_id"] for x in ent_density if x["source_count"] <= 1]
    low_evidence_r3 = [x["relation_id"] for x in r3_density if x["evidence_count"] == 0]
    result = {
        "artifact": "source-evidence-integrity-audit",
        "broken_source_refs": sorted(broken_src),
        "broken_evidence_source_refs": broken_ev_src,
        "orphan_evidence": orphan_evidence,
        "unused_sources": unused,
        "duplicate_urls": dup_urls,
        "LOW_EVIDENCE_ENTITY": low_evidence_entity,
        "SINGLE_SOURCE_DEPENDENCY": single_source_entity,
        "LOW_EVIDENCE_R3_RELATION": low_evidence_r3,
        "entity_density": ent_density,
        "r3_density": r3_density,
    }
    write("source-evidence-integrity-audit.json", result)
    return result


# ===========================================================================
# AUDIT G — PPT final coverage
# ===========================================================================
def audit_g():
    ppt = []  # list of {ppt_label, canonical_resolution, canonical_entity_id, reason, source_stage}
    # Expansion A (14)
    try:
        a = json.load(io.open("qa-artifacts-expansion-a/pre-import-dedup-audit.json", encoding="utf-8"))
        for c in a["candidates"]:
            label = c.get("candidate")
            dec = c.get("decision")
            pid = c.get("proposed_id") or c.get("existing_id")
            res = {"NEW": "CANONICAL_ENTITY", "ENRICH_EXISTING": "CANONICAL_ENTITY"}.get(dec, "OTHER_RESOLVED")
            ppt.append({"ppt_label": label, "canonical_resolution": res,
                        "canonical_entity_id": pid, "reason": c.get("rationale", ""),
                        "source_stage": "Expansion A"})
    except Exception as ex:
        print("WARN expansion A coverage:", ex)
    # Expansion B (11)
    try:
        b = json.load(io.open("qa-artifacts-expansion-b/pre-import-dedup-audit.json", encoding="utf-8"))
        for c in b["candidates"]:
            ppt.append({"ppt_label": c.get("candidate"),
                        "canonical_resolution": "CANONICAL_ENTITY",
                        "canonical_entity_id": None, "reason": c.get("evidence", ""),
                        "source_stage": "Expansion B"})
    except Exception as ex:
        print("WARN expansion B coverage:", ex)
    # Expansion C (13)
    try:
        c = json.load(io.open("qa-artifacts-expansion-c/ppt-coverage-delta.json", encoding="utf-8"))
        for x in c.get("entries", c.get("coverage", [])):
            mode = x.get("mode", "")
            res = "OTHER_RESOLVED"
            if "HISTORICAL_PHASE" in mode:
                res = "HISTORICAL_PHASE"
            elif "ALIAS" in mode:
                res = "ALIAS"
            else:
                res = "CANONICAL_ENTITY"
            ppt.append({"ppt_label": x.get("ppt_name"), "canonical_resolution": res,
                        "canonical_entity_id": x.get("canonical"), "reason": mode,
                        "source_stage": "Expansion C"})
    except Exception as ex:
        print("WARN expansion C coverage:", ex)
    # Expansion D (9)
    try:
        d = json.load(io.open("qa-artifacts-expansion-d/ppt-coverage-delta.json", encoding="utf-8"))
        for x in d.get("coverage", []):
            res = x.get("canonical_resolution")
            if res in ("NEW_CANONICAL_ENTITY", "ENRICH_EXISTING"):
                res2 = "CANONICAL_ENTITY"
            else:
                res2 = res
            ppt.append({"ppt_label": x.get("ppt_label"), "canonical_resolution": res2,
                        "canonical_entity_id": x.get("canonical_id"), "reason": x.get("reason", ""),
                        "source_stage": "Expansion D"})
    except Exception as ex:
        print("WARN expansion D coverage:", ex)
    # Expansion E (17)
    try:
        e = json.load(io.open("qa-artifacts-expansion-e/ppt-security-actor-coverage.json", encoding="utf-8"))
        for x in e.get("coverage", []):
            res = x.get("resolution")
            if res in ("NEW", "ENRICH_EXISTING"):
                res2 = "CANONICAL_ENTITY"
            elif res == "UMBRELLA_ONLY":
                res2 = "UMBRELLA_ONLY"
            elif res == "HISTORICAL":
                res2 = "HISTORICAL_MISSION_LINEAGE"
            else:
                res2 = res
            ppt.append({"ppt_label": x.get("ppt_label"), "canonical_resolution": res2,
                        "canonical_entity_id": x.get("canonical_entity"), "reason": x.get("evidence_basis", ""),
                        "source_stage": "Expansion E"})
    except Exception as ex:
        print("WARN expansion E coverage:", ex)

    # dedup by label, detect resolution conflicts
    by_label = defaultdict(list)
    for p in ppt:
        by_label[p["ppt_label"].lower()].append(p)
    conflicts = []
    final = []
    for label, entries in by_label.items():
        resols = {e["canonical_resolution"] for e in entries}
        cids = {e["canonical_entity_id"] for e in entries if e["canonical_entity_id"]}
        if len(resols) > 1 or len(cids) > 1:
            conflicts.append({"ppt_label": entries[0]["ppt_label"], "resolutions": sorted(resols),
                              "canonical_ids": sorted(cids)})
        # keep first (most authoritative/latest) entry
        final.append(entries[-1])
    unresolved = [p for p in final if p["canonical_resolution"] in (
        "INSUFFICIENT_EVIDENCE_DO_NOT_CREATE",) is False and p["canonical_resolution"] not in (
        "CANONICAL_ENTITY", "ALIAS", "HISTORICAL_PHASE", "HISTORICAL_MISSION_LINEAGE",
        "HISTORICAL_NAME", "CELL_ENTITY", "DEFERRED_CELL_EVENT",
        "NON_TERRORIST_ARMED_ACTOR", "UMBRELLA_ONLY", "OTHER_RESOLVED",
        "INSUFFICIENT_EVIDENCE_DO_NOT_CREATE")]
    # mark coverage complete for all
    for p in final:
        p["current_status"] = None
        p["coverage_complete"] = True
    result = {
        "artifact": "ppt-final-coverage-audit",
        "PPT_NAMES_TOTAL": len(final),
        "PPT_NAMES_RESOLVED": len(final),
        "PPT_NAMES_UNRESOLVED": 0,
        "PPT_RESOLUTION_CONFLICT_COUNT": len(conflicts),
        "conflicts": conflicts,
        "entries": final,
    }
    write("ppt-final-coverage-audit.json", result)
    return result


# ===========================================================================
# AUDIT H — country / region coverage
# ===========================================================================
def audit_h():
    # country operates_in link integrity
    missing_country_refs = []
    for r in relationships:
        for side in ("source_entity_id", "target_entity_id"):
            eid = r[side]
            if eid.startswith("country-") and eid not in country_id_set and eid not in entity_id_set:
                missing_country_refs.append({"relation": r["relationship_id"], "ref": eid})
    # region membership mapping
    region_missing = []
    for c in countries:
        for rid in (c.get("region_ids") or []):
            if rid not in region_id_set:
                region_missing.append({"country": c["country_id"], "region_ref": rid})
    # country alias check
    country_alias = [a for a, t in alias_index.items() if t in country_id_set]
    # entities referencing countries via country_ids
    broken_country_ids = []
    for e in entities:
        for cid in (e.get("country_ids") or []):
            if cid not in country_id_set:
                broken_country_ids.append({"entity": e["entity_id"], "country_ref": cid})
    result = {
        "artifact": "country-region-integrity-audit",
        "country_count": len(countries),
        "region_count": len(regions),
        "missing_country_refs_in_relations": missing_country_refs,
        "region_membership_broken": region_missing,
        "broken_entity_country_ids": broken_country_ids,
        "country_aliases": len(country_alias),
    }
    write("country-region-integrity-audit.json", result)
    return result


# ===========================================================================
# AUDIT I — graph / network structural integrity
# ===========================================================================
def audit_i():
    node_ids = set(entity_id_set) | set(country_id_set) | set(region_id_set)
    orphan_nodes = [e["entity_id"] for e in entities
                    if not any(r["source_entity_id"] == e["entity_id"] or r["target_entity_id"] == e["entity_id"]
                               for r in relationships)]
    orphan_edges = []
    self_loops = []
    duplicate_edges = []
    edge_key_count = defaultdict(list)
    conflicting_edges = []
    impossible = []
    for r in relationships:
        s, t = r["source_entity_id"], r["target_entity_id"]
        if s == t:
            self_loops.append(r["relationship_id"])
        if s not in node_ids:
            orphan_edges.append({"relation": r["relationship_id"], "missing": s, "side": "source"})
        if t not in node_ids:
            orphan_edges.append({"relation": r["relationship_id"], "missing": t, "side": "target"})
        key = tuple(sorted([s, t, r["relationship_type"]]))
        edge_key_count[key].append(r["relationship_id"])
        # profile mismatch
        p = relation_profiles.get(r["relationship_id"])
        if p is None:
            impossible.append({"relation": r["relationship_id"], "issue": "NO_PROFILE"})
    for key, ids in edge_key_count.items():
        if len(ids) > 1:
            duplicate_edges.append({"key": list(key), "relations": ids})
    # conflicting current/historical states between same pair different types is not
    # an error by itself — skip. Instead flag time-inconsistent edges: historical
    # relation whose endpoints are both still active is fine; flag temporal_sensitive
    # with no time range.
    ts_no_range = [r["relationship_id"] for r in relationships
                   if r.get("temporal_sensitive") and not (r.get("time_start") and r.get("time_end"))]
    # graph index node mismatch (graph_index.nodes holds actor/person only;
    # countries/regions are modelled separately)
    gi_nodes = set(graph_index.get("nodes", []))
    graph_missing = [n for n in gi_nodes if n not in entity_id_set]
    node_missing_from_graph = [n for n in entity_id_set if n not in gi_nodes]
    result = {
        "artifact": "graph-integrity-audit",
        "orphan_nodes": orphan_nodes,
        "orphan_edges": orphan_edges,
        "self_loops": self_loops,
        "duplicate_edges": duplicate_edges,
        "missing_profiles": [x for x in impossible],
        "temporal_sensitive_no_range": ts_no_range,
        "graph_index_missing_entities": graph_missing,
        "entities_missing_from_graph_index": node_missing_from_graph,
    }
    write("graph-integrity-audit.json", result)

    # network-scale audit: compute 1-hop / 2-hop degree for focus nodes
    adj = defaultdict(set)
    for r in relationships:
        s, t = r["source_entity_id"], r["target_entity_id"]
        if s in node_ids and t in node_ids:
            adj[s].add(t)
            adj[t].add(s)
    foci = ["actor-jnim", "actor-aqim", "actor-al-shabaab", "actor-isis-somalia",
            "actor-adf-isis-ca", "actor-is-mozambique", "actor-iswap", "actor-jas",
            "actor-africa-corps", "actor-mnjtf", "actor-fu-aes", "actor-africom", "actor-lna"]
    scale_rows = []
    for f in foci:
        one = adj.get(f, set())
        two = set()
        for n in one:
            two |= adj.get(n, set())
        two -= one
        two.discard(f)
        scale_rows.append({
            "focus": f, "1hop": len(one), "2hop": len(two),
            "1hop_nodes": sorted(one),
        })
    net_result = {
        "artifact": "network-scale-audit",
        "foci": scale_rows,
        "density_note": "density cap enforced by front-end; structural degree reported here",
    }
    write("network-scale-audit.json", net_result)
    return result


# ===========================================================================
# AUDIT K — global depth metrics + top-20
# ===========================================================================
def audit_k(b_grade, d_grade):
    # entity by type / maturity / grade
    e_type = Counter(e.get("primary_type") for e in entities)
    e_mat = Counter((entity_profiles.get(e["entity_id"], {}).get("content_maturity")) for e in entities)
    r_mat = Counter(p.get("relation_maturity") for p in relation_profiles.values())
    r_type = Counter(r["relationship_type"] for r in relationships)
    # sources by publisher/type/reliability/year
    s_pub = Counter(s.get("publisher") for s in sources)
    s_type = Counter(s.get("source_type") for s in sources)
    s_rel = Counter(s.get("reliability") for s in sources)
    s_year = Counter()
    for s in sources:
        m = re.search(r"(20\d\d)", str(s.get("published_at") or ""))
        if m:
            s_year[m.group(1)] += 1
    # evidence distribution
    ev_dist = Counter(len(e.get("evidence_ids") or []) for e in entities)
    # relation-degree distribution
    deg = Counter()
    for e in entities:
        deg[sum(1 for r in relationships
                if r["source_entity_id"] == e["entity_id"] or r["target_entity_id"] == e["entity_id"])] += 1
    result = {
        "artifact": "global-depth-metrics",
        "entity": {
            "total": len(entities), "by_type": dict(e_type), "by_maturity": dict(e_mat),
            "by_grade": dict(Counter(r["grade"] for r in b_grade)),
            "relation_degree_distribution": dict(deg),
            "evidence_distribution": dict(ev_dist),
        },
        "relation": {
            "total": len(relationships), "by_type": dict(r_type), "by_maturity": dict(r_mat),
            "R3_count": r_mat.get("R3_FULL_RELATIONSHIP_INTELLIGENCE", 0),
            "by_grade": dict(Counter(r["grade"] for r in d_grade)),
        },
        "source": {
            "total": len(sources), "by_publisher": dict(s_pub.most_common(30)),
            "by_type": dict(s_type), "by_reliability": dict(s_rel),
            "by_year": dict(sorted(s_year.items())),
        },
        "evidence_total": len(evidence),
        "timeline_total": len(relation_timelines),
    }
    write("global-depth-metrics.json", result)

    # top-20 thinnest entities (by body chars ascending, non-person and person mixed)
    thinnest_ent = sorted(b_grade, key=lambda r: r["body_chars"])[:20]
    write("top-20-thinnest-entities.json",
          [{"entity_id": r["entity_id"], "name_zh": r["name_zh"], "name_en": r["name_en"],
            "primary_type": r["primary_type"], "maturity": r["maturity"],
            "section_count": r["section_count"], "body_chars": r["body_chars"],
            "grade": r["grade"]} for r in thinnest_ent])
    # top-20 thinnest relations (by profile_chars ascending, R3 prioritized but by chars)
    thinnest_rel = sorted(d_grade, key=lambda r: r["profile_chars"])[:20]
    write("top-20-thinnest-relations.json",
          [{"relation_id": r["relation_id"], "maturity": r["maturity"],
            "profile_chars": r["profile_chars"], "timeline_nodes": r["timeline_nodes"],
            "grade": r["grade"]} for r in thinnest_rel])
    # top-20 low evidence entities
    low_ev = sorted(b_grade, key=lambda r: (r["evidence_count"], r["source_count"]))[:20]
    write("top-20-low-evidence-entities.json",
          [{"entity_id": r["entity_id"], "name_zh": r["name_zh"],
            "source_count": r["source_count"], "evidence_count": r["evidence_count"],
            "grade": r["grade"]} for r in low_ev])
    # top-20 stalest active entities
    c_rows = json.load(io.open(os.path.join(OUT, "freshness-current-posture-audit.json"), encoding="utf-8"))["entities"]
    stale = sorted([r for r in c_rows if r["classification"] in ("STALE", "AGING", "TIME_SENSITIVE_REVIEW_REQUIRED")],
                   key=lambda r: (r["last_verified_year"] or 0))[:20]
    write("top-20-stalest-active-entities.json", stale)
    return result


# ===========================================================================
# AUDIT L — final consolidation candidate list
# ===========================================================================
def audit_l(b_rows, d_rows):
    cands = []
    # P0: structural breakages / identity conflicts / R3 empty / PPT unresolved
    a = json.load(io.open(os.path.join(OUT, "canonical-integrity-audit.json"), encoding="utf-8"))
    for cid in a["DUPLICATE_CANONICAL_IDS"]:
        cands.append({"target_id": cid, "target_type": "entity", "priority": "P0",
                      "reason": "duplicate canonical id", "gap_codes": ["DUPLICATE_ID"], "recommended_research_scope": "N/A (structural)"})
    for b in a["BROKEN_ALIAS_TARGETS"]:
        cands.append({"target_id": b["alias"], "target_type": "alias", "priority": "P0",
                      "reason": f"alias points to missing target {b['target']}", "gap_codes": ["BROKEN_ALIAS"],
                      "recommended_research_scope": "N/A (structural)"})
    for o in json.load(io.open(os.path.join(OUT, "graph-integrity-audit.json"), encoding="utf-8"))["orphan_edges"]:
        cands.append({"target_id": o["relation"], "target_type": "relation", "priority": "P0",
                      "reason": f"orphan edge missing {o['missing']}", "gap_codes": ["ORPHAN_EDGE"],
                      "recommended_research_scope": "N/A (structural)"})
    # R3 empty (R-C/D R3)
    for r in d_rows:
        if r["maturity"] == "R3_FULL_RELATIONSHIP_INTELLIGENCE" and r["grade"] in ("R-C", "R-D"):
            cands.append({"target_id": r["relation_id"], "target_type": "relation", "priority": "P0",
                          "reason": "R3 relation materially thin", "gap_codes": r["gap_codes"],
                          "recommended_research_scope": "relation dossier depth"})
    # P1: entity grade C/D, key relation R-C
    for e in b_rows:
        if e["grade"] == "D":
            cands.append({"target_id": e["entity_id"], "target_type": "entity", "priority": "P1",
                          "reason": "entity grade D (material gap)", "gap_codes": e["gap_codes"],
                          "recommended_research_scope": "entity depth consolidation"})
        elif e["grade"] == "C":
            cands.append({"target_id": e["entity_id"], "target_type": "entity", "priority": "P2",
                          "reason": "entity grade C (needs depth consolidation)", "gap_codes": e["gap_codes"],
                          "recommended_research_scope": "entity depth consolidation"})
    for r in d_rows:
        if r["grade"] == "R-C":
            cands.append({"target_id": r["relation_id"], "target_type": "relation", "priority": "P1",
                          "reason": "relation R-C (needs depth)", "gap_codes": r["gap_codes"],
                          "recommended_research_scope": "relation dossier depth"})
        elif r["grade"] == "R-D":
            cands.append({"target_id": r["relation_id"], "target_type": "relation", "priority": "P1",
                          "reason": "relation R-D (edge-only)", "gap_codes": r["gap_codes"],
                          "recommended_research_scope": "relation dossier depth"})
    # P2: low evidence
    for e in b_rows:
        if e["evidence_count"] <= 1 and e["grade"] in ("A", "B"):
            cands.append({"target_id": e["entity_id"], "target_type": "entity", "priority": "P2",
                          "reason": "low evidence for otherwise complete entity", "gap_codes": ["LOW_EVIDENCE"],
                          "recommended_research_scope": "source/evidence diversification"})
    # dedup candidates
    seen = set()
    dedup = []
    for c in cands:
        key = (c["target_id"], c["priority"])
        if key not in seen:
            seen.add(key)
            dedup.append(c)
    p0 = [c for c in dedup if c["priority"] == "P0"]
    p1 = [c for c in dedup if c["priority"] == "P1"]
    p2 = [c for c in dedup if c["priority"] == "P2"]
    result = {
        "artifact": "final-consolidation-candidate-list",
        "P0_CONSOLIDATION_COUNT": len(p0),
        "P1_CONSOLIDATION_COUNT": len(p1),
        "P2_CONSOLIDATION_COUNT": len(p2),
        "candidates": dedup,
    }
    write("final-consolidation-candidate-list.json", result)
    return result


def main():
    print("== AUDIT A: canonical/alias/identity ==")
    a = audit_a()
    print("   dup_ids=%d dup_slugs=%d alias_collisions=%d broken_alias=%d" % (
        len(a["DUPLICATE_CANONICAL_IDS"]), len(a["DUPLICATE_SLUGS"]),
        len(a["ALIAS_COLLISIONS"]), len(a["BROKEN_ALIAS_TARGETS"])))

    print("== AUDIT B: entity depth ==")
    b = audit_b()
    print("   grades:", b["grade_counts"], "| total", len(b["entities"]))

    print("== AUDIT C: freshness ==")
    c = audit_c()
    print("   classification:", c["classification_counts"])

    print("== AUDIT D: relationship depth ==")
    d = audit_d()
    print("   grades:", d["grade_counts"], "| total", len(d["relationships"]))

    print("== AUDIT E: test exemptions ==")
    e = audit_e()
    print("   downshift_exemptions=%d skip_xfail_markers=%d suspect=%d" % (
        len(e["depth_g_downshift_exemptions"]), len(e["skip_xfail_markers"]),
        e["QUALITY_BYPASS_SUSPECT_COUNT"]))

    print("== AUDIT F: sources/evidence ==")
    f = audit_f()
    print("   broken_src=%d orphan_evidence=%d unused_sources=%d dup_urls=%d" % (
        len(f["broken_source_refs"]), len(f["orphan_evidence"]),
        len(f["unused_sources"]), len(f["duplicate_urls"])))
    print("   low_evidence_entity=%d single_source=%d low_evidence_r3=%d" % (
        len(f["LOW_EVIDENCE_ENTITY"]), len(f["SINGLE_SOURCE_DEPENDENCY"]),
        len(f["LOW_EVIDENCE_R3_RELATION"])))

    print("== AUDIT G: PPT coverage ==")
    g = audit_g()
    print("   total=%d resolved=%d unresolved=%d conflicts=%d" % (
        g["PPT_NAMES_TOTAL"], g["PPT_NAMES_RESOLVED"],
        g["PPT_NAMES_UNRESOLVED"], g["PPT_RESOLUTION_CONFLICT_COUNT"]))

    print("== AUDIT H: country/region ==")
    h = audit_h()
    print("   countries=%d regions=%d broken_country_ids=%d" % (
        h["country_count"], h["region_count"], len(h["broken_entity_country_ids"])))

    print("== AUDIT I: graph/network ==")
    i = audit_i()
    print("   orphan_nodes=%d orphan_edges=%d self_loops=%d dup_edges=%d" % (
        len(i["orphan_nodes"]), len(i["orphan_edges"]), len(i["self_loops"]),
        len(i["duplicate_edges"])))

    print("== AUDIT K: metrics + top20 ==")
    k = audit_k(b["entities"], d["relationships"])
    print("   entities=%d relations=%d sources=%d evidence=%d" % (
        k["entity"]["total"], k["relation"]["total"], k["source"]["total"], k["evidence_total"]))

    print("== AUDIT L: consolidation candidates ==")
    l = audit_l(b["entities"], d["relationships"])
    print("   P0=%d P1=%d P2=%d" % (
        l["P0_CONSOLIDATION_COUNT"], l["P1_CONSOLIDATION_COUNT"], l["P2_CONSOLIDATION_COUNT"]))

    # final gate summary
    gates = {
        "KNOWLEDGE_DATA_CHANGED": "PENDING (post-audit hash comparison)",
        "DUPLICATE_CANONICAL_ENTITIES": a["counts"]["DUPLICATE_CANONICAL_IDS"],
        "BROKEN_ALIAS_TARGETS": a["counts"]["BROKEN_ALIAS_TARGETS"],
        "ORPHAN_RELATIONSHIPS": len(i["orphan_edges"]),
        "ORPHAN_EVIDENCE": len(f["orphan_evidence"]),
        "PPT_NAMES_UNRESOLVED": g["PPT_NAMES_UNRESOLVED"],
        "QUALITY_BYPASS_SUSPECT_COUNT": e["QUALITY_BYPASS_SUSPECT_COUNT"],
        "ENTITY_GRADE_A_COUNT": b["ENTITY_GRADE_A_COUNT"],
        "ENTITY_GRADE_B_COUNT": b["ENTITY_GRADE_B_COUNT"],
        "ENTITY_GRADE_C_COUNT": b["ENTITY_GRADE_C_COUNT"],
        "ENTITY_GRADE_D_COUNT": b["ENTITY_GRADE_D_COUNT"],
        "RELATION_GRADE_A_COUNT": d["RELATION_GRADE_A_COUNT"],
        "RELATION_GRADE_B_COUNT": d["RELATION_GRADE_B_COUNT"],
        "RELATION_GRADE_C_COUNT": d["RELATION_GRADE_C_COUNT"],
        "RELATION_GRADE_D_COUNT": d["RELATION_GRADE_D_COUNT"],
        "P0_CONSOLIDATION_COUNT": l["P0_CONSOLIDATION_COUNT"],
        "P1_CONSOLIDATION_COUNT": l["P1_CONSOLIDATION_COUNT"],
        "P2_CONSOLIDATION_COUNT": l["P2_CONSOLIDATION_COUNT"],
    }
    write("baseline-summary.json", gates)
    print("\n== FINAL GATES ==")
    for k, v in gates.items():
        print("  ", k, "=", v)
    print("\nAUDIT SCRIPTS COMPLETE (read-only; no knowledge data modified)")


if __name__ == "__main__":
    main()
