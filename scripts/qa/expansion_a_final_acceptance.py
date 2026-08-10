# -*- coding: utf-8 -*-
"""EXPANSION_A_LOCAL_CANDIDATE final acceptance audit.

Verifies, against the authoritative content pack (§0-§21), the final state of
the imported data. Every check is data-driven; no re-research, no Expansion B.
Gate criteria (all must hold for PASS):
  OUT_OF_SCOPE_CHANGED_FILES = 0   (separate script)
  FACT_SEMANTIC_ERRORS         = 0
  FAIL_TOTAL                   = 0   (separate regression runner)
  BUILD                        = PASS
  BROWSER_QA                   = PASS
  production changed           = NO
  gh-pages changed             = NO
  Depth G started              = NO
  force push                   = NO
"""
import io, json, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DATA = "data/intelligence/africa/"
QA = "qa-artifacts-expansion-a/"

def load(p):
    return json.load(open(p, encoding="utf-8"))

ents = load(DATA + "entities.json")["entities"]
ep = load(DATA + "entity_profiles.json")["profiles"]
rels = load(DATA + "relationships.json")["relationships"]
rp = load(DATA + "relation_profiles.json")["profiles"]
rt = load(DATA + "relation_timelines.json")["timelines"]
srcs = load(DATA + "sources.json")["sources"]
ev = load(DATA + "evidence_records.json")["evidence"]
alias = load(DATA + "alias_index.json")["aliases"]
graph = load(DATA + "graph_index.json")
fe = load(DATA + "force_estimates.json")["estimates"]
lk = load(DATA + "external_links.json")["links"]

eids = {e["entity_id"] for e in ents}
sids = {s["source_id"] for s in srcs}
rids = {r["relationship_id"] for r in rels}
PASS, FAIL, SKIP = [], [], []

def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
    else:
        FAIL.append(name + (" :: " + str(detail) if detail else ""))

# =============================================================================
# 1. NEW / ENRICH_EXISTING / ALIAS_ONLY / DEFERRED final rulings
# =============================================================================
NEW_EXPECT = ["actor-al-shabaab", "actor-isis-somalia", "actor-al-karrar-office",
              "actor-adf-isis-ca", "actor-sim", "actor-bbmb",
              "person-ahmed-diriye", "person-abd-al-qadir-mumin",
              "person-abdirahman-fahiye", "person-seka-musa-baluku",
              "person-ali-ahmed-karti"]
for eid in NEW_EXPECT:
    check("NEW entity present: " + eid, eid in eids)

check("ENRICH existing ansaru present", "actor-ansaru" in eids)
check("ENRICH existing lakurawa present", "actor-lakurawa" in eids)

# ALIAS_ONLY: ADF / ISIS-CA / ISIS-DRC / ISCAP must be one canonical entity
adf = next(e for e in ents if e["entity_id"] == "actor-adf-isis-ca")
adf_all = set(adf.get("aliases", [])) | set(adf.get("historical_names", []))
for a in ["ADF", "ISIS-CA", "ISIS-DRC", "ISCAP", "Allied Democratic Forces"]:
    check("ADF canonical alias covers " + a, a.lower() in {x.lower() for x in adf_all})
check("NO separate actor-isis-drc entity", "actor-isis-drc" not in eids)
check("NO separate actor-adf entity", "actor-adf" not in eids)
check("NO separate actor-iscap entity", "actor-iscap" not in eids)

# DEFERRED rulings
check("DEFER person-abu-zaid-talha (not created)", "person-abu-zaid-talha" not in eids)
check("DEFER IRGC (not created)", "actor-irgc" not in eids and "irgc" not in " ".join(eids).lower())
deferred = json.load(open(QA + "unresolved-supporting-entity-dependencies.json", encoding="utf-8"))
defer_edges = deferred["deferred_edges"]
defer_labels = [d["edge"] for d in defer_edges]
for need in ["BBMB ↔ IRGC", "Abu Zaid Talha al-Misbah → BBMB", "Al-Shabaab ↔ AUSSOM",
             "Al-Shabaab ↔ Somali Security Forces", "ISIS-Somalia ↔ Puntland Security Forces",
             "ADF/ISIS-CA ↔ FARDC", "ADF/ISIS-CA ↔ UPDF", "ADF/ISIS-CA ↔ MONUSCO",
             "Ansaru ↔ Katiba Hanifa"]:
    check("deferred edge recorded: " + need, any(need in x for x in defer_labels))
check("deferred entities recorded", len(deferred.get("deferred_entities", [])) >= 4)

# =============================================================================
# 2. Wikipedia-level content thickness per formal entity
# =============================================================================
def text_len(v):
    if isinstance(v, str):
        return len(v)
    if isinstance(v, list):
        return sum(len(str(x)) for x in v)
    if isinstance(v, dict):
        n = 0
        for k in ("p", "list", "timeline"):
            if v.get(k):
                n += sum(len(str(x)) for x in v[k])
        if v.get("table"):
            n += 2
        return n
    return 0

thickness = {}
for eid in NEW_EXPECT:
    pr = ep.get(eid)
    if not pr:
        check("profile exists: " + eid, False)
        continue
    secs = pr.get("sections", {})
    n = sum(1 for k, v in secs.items() if text_len(v) > 0)
    body = sum(text_len(v) for v in secs.values())
    thickness[eid] = {"sections": n, "chars": body, "depth": pr.get("profile_depth")}
    # threshold matches the test contract: encyclopedia_full >= 1800 chars / 8 secs,
    # standard >= 900 chars / 5 secs (person-abdirahman-fahiye is a standard-depth page)
    need = 1800 if pr.get("profile_depth") == "encyclopedia_full" else 900
    need_n = 8 if pr.get("profile_depth") == "encyclopedia_full" else 5
    check("thickness " + eid, n >= need_n and body >= need, f"secs={n} chars={body} (depth={pr.get('profile_depth')})")

# =============================================================================
# 3. Five deep relation dossiers + #4 branch dossier
# =============================================================================
R3 = "R3_FULL_RELATIONSHIP_INTELLIGENCE"
dossier_rels = {
    "A_shabaab_iss": "rel-expa-shabaab-isis-somalia-rivalry",
    "B_adf_isis": "rel-expa-adf-isis-branch",
    "C_ansaru_jas": "rel-d1-ansaru-jas-split",
    "D1_lakurawa_iss": "rel-d1-lakurawa-is-sahel-network",
    "D2_lakurawa_jnim": "rel-d1-lakurawa-jnim-cooperation",
    "E_sim_bbmb": "rel-expa-sim-bbmb-linked",
    "iss_isis_branch": "rel-expa-isis-somalia-isis-branch",
}
for label, rid in dossier_rels.items():
    pr = rp.get(rid)
    check("dossier profile " + label, pr is not None)
    if pr:
        check("dossier maturity R3 " + label, pr.get("relation_maturity") == R3, pr.get("relation_maturity"))
        tl = rt.get(rid, [])
        check("dossier timeline " + label, len(tl) >= 3, f"{len(tl)} items")
        for field in ("formation_background", "initial_relationship", "evolution_stages",
                      "causes", "key_turning_points", "impact_on_security", "why_it_matters",
                      "uncertainties", "asip_analysis", "watch_indicators"):
            v = pr.get(field)
            ok = bool(v) and not (isinstance(v, (list, dict)) and len(v) == 0)
            check(f"dossier field {label}.{field}", ok)

# D: two records mutually aware through uncertainty notes
d1 = rp.get("rel-d1-lakurawa-is-sahel-network", {}).get("uncertainties", "")
d2 = rp.get("rel-d1-lakurawa-jnim-cooperation", {}).get("uncertainties", "")
check("D records mutually aware (d1 mentions jnim record)", "rel-d1-lakurawa-jnim-cooperation" in d1)
check("D records mutually aware (d2 mentions is-sahel record)", "rel-d1-lakurawa-is-sahel-network" in d2)
check("D contested flags", rp["rel-d1-lakurawa-is-sahel-network"].get("disputed") is True
      and rp["rel-d1-lakurawa-jnim-cooperation"].get("disputed") is True)

# #4: both dates preserved
iss_prof = rp.get("rel-expa-isis-somalia-isis-branch", {})
check("#4 both dates in profile", "2015" in str(iss_prof.get("formation_background", "")) and "2018" in str(iss_prof.get("overview", "")))
check("#4 time_start=2015", any(r["relationship_id"] == "rel-expa-isis-somalia-isis-branch" and r.get("time_start") == "2015" for r in rels))

# =============================================================================
# 4. Factual semantics checks (pack §17 / §19)
# =============================================================================
def all_profile_text(eid):
    pr = ep.get(eid, {})
    return json.dumps(pr.get("sections", {}), ensure_ascii=False)

FACT_SEMANTIC_ERRORS = []
# §19 prohibited imports
if "20,000" in all_profile_text("actor-sim") or "2 万" in all_profile_text("actor-sim") or "两万" in all_profile_text("actor-sim"):
    FACT_SEMANTIC_ERRORS.append("SIM profile carries BBMB 20,000 figure (prohibited transfer)")
if "20,000" in all_profile_text("actor-bbmb") and "美国财政部" not in all_profile_text("actor-bbmb"):
    FACT_SEMANTIC_ERRORS.append("BBMB 20,000 figure without attribution")
if "2,000—3,000" in all_profile_text("actor-ansaru") or "2000-3000" in all_profile_text("actor-ansaru"):
    FACT_SEMANTIC_ERRORS.append("Ansaru unsupported fixed strength retained")
if "无条件" in all_profile_text("actor-lakurawa") and "分支" in all_profile_text("actor-lakurawa"):
    # allowed only if negated / disputed context
    pass
laku_sections = ep.get("actor-lakurawa", {}).get("sections", {})
laku_txt = json.dumps(laku_sections, ensure_ascii=False)
if "作为 JNIM 的一部分运作" in laku_txt and "ACLED" in laku_txt and "保留" in laku_txt:
    check("Lakurawa dual positions preserved", True)
else:
    check("Lakurawa dual positions preserved", False)
# no uncontested branch_of edge
branch_edges = [r for r in rels if r["relationship_type"] == "branch_of"]
check("no branch_of edges created", len(branch_edges) == 0, str(branch_edges))
# no ISGS/EIGS/ISSP as separate entities
for forbidden in ["actor-isgs", "actor-eigs", "actor-issp", "actor-isgs-eigs", "actor-is-sahel-province"]:
    check("prohibited entity absent " + forbidden, forbidden not in eids)
# ADF not split into two current orgs
check("no ADF<->ISIS-CA affiliation edge", not any(r["source_entity_id"] == "actor-adf" and r["target_entity_id"] == "actor-isis-ca" for r in rels))
# Boko Haram subordinate to ISIS not imported
bh_secs = json.dumps(ep.get("actor-boko-haram-jas", {}).get("sections", {}), ensure_ascii=False) if "actor-boko-haram-jas" in ep else ""
if "subordinate" in bh_secs.lower() or "从属" in bh_secs and "伊斯兰国" in bh_secs:
    FACT_SEMANTIC_ERRORS.append("Boko Haram subordinate-to-ISIS claim imported")
# attribution preserved: Karti influence statements attributed to EU
karti_txt = json.dumps(ep.get("person-ali-ahmed-karti", {}).get("sections", {}), ensure_ascii=False)
check("Karti EU attribution preserved", "欧盟" in karti_txt)
# BBMB 20,000 stays attributed
bbmb_txt = json.dumps(ep.get("actor-bbmb", {}).get("sections", {}), ensure_ascii=False)
check("BBMB 20,000 attributed to U.S. Treasury", "财政部" in bbmb_txt or "Treasury" in bbmb_txt)
# ISIS-Somalia 700-1500 is a dated estimate, not timeless
iss_txt = json.dumps(ep.get("actor-isis-somalia", {}).get("sections", {}), ensure_ascii=False)
check("ISS estimate dated", "2025 年 2 月" in iss_txt or "2025-02" in iss_txt or "2025年2月" in iss_txt)
# force estimates for the 6 orgs carry date+source
for eid in ["actor-al-shabaab", "actor-isis-somalia", "actor-al-karrar-office",
            "actor-adf-isis-ca", "actor-sim", "actor-bbmb"]:
    ests = fe.get(eid, [])
    ok = all(x.get("estimate_date") and x.get("source_ids") and x.get("estimate_text") for x in ests)
    check("force estimate fields " + eid, ok, f"{len(ests)} entries")

# =============================================================================
# 5. Source / evidence integrity
# =============================================================================
check("sources count >= 200", len(srcs) >= 200, len(srcs))
check("evidence count >= 330", len(ev) >= 330, len(ev))
new_src_prefix = [s for s in srcs if s["source_id"].startswith("expa-")]
check("expa- sources registered", len(new_src_prefix) == 12, len(new_src_prefix))
dangling_src = []
for e in ents:
    for s in e.get("source_refs", []):
        if s not in sids:
            dangling_src.append((e["entity_id"], s))
for r in rels:
    for s in r.get("source_refs", []):
        if s not in sids:
            dangling_src.append((r["relationship_id"], s))
for rec in ev:
    if rec["source_id"] not in sids:
        dangling_src.append((rec["evidence_id"], rec["source_id"]))
check("no dangling source refs", not dangling_src, dangling_src[:5])
# evidence verified ratio < 80%
v = sum(1 for x in ev if x["verification_status"] == "verified")
check("verified ratio < 0.80", v / len(ev) < 0.80, round(v / len(ev), 4))
# new relation evidence present
rel_ev = [x for x in ev if x["evidence_id"].startswith("ev-expa-r")]
check("expansion relation evidence imported", len(rel_ev) == 26, len(rel_ev))

# =============================================================================
# 6. Final counts
# =============================================================================
check("entities = 83", len(ents) == 83, len(ents))
check("relationships = 164", len(rels) == 164, len(rels))
check("relation_profiles = 164", len(rp) == 164, len(rp))
check("relation_timelines >= 60", len(rt) >= 60, len(rt))
check("graph nodes match entities", set(graph["nodes"]) == eids)
check("graph relationship_ids match", len(graph["relationship_ids"]) == len(rels))
check("alias index >= 100", len(alias) >= 100, len(alias))
check("countries = 13", len(load(DATA + "countries.json")["countries"]) == 13)
# NEW relations count (14) + ENRICH (5)
expa_rels = [r for r in rels if r["relationship_id"].startswith("rel-expa-")]
check("rel-expa- count = 14", len(expa_rels) == 14, len(expa_rels))

# =============================================================================
# 7. Regression / build / QA artifacts presence
# =============================================================================
reg = json.load(open(QA + "test-results.json", encoding="utf-8"))
check("regression FAIL_TOTAL=0", reg.get("fail_total", -1) == 0, reg.get("fail_total"))
bq = json.load(open(QA + "browser-qa.json", encoding="utf-8"))
check("browser QA gate PASS", bq["summary"]["gate"] == "PASS", bq["summary"].get("gate"))
lq = json.load(open(QA + "link-qa.json", encoding="utf-8"))
check("link QA gate PASS", lq["summary"]["gate"] == "PASS", lq["summary"].get("gate"))

print(json.dumps({
    "PASS": len(PASS), "FAIL": len(FAIL), "SKIP": len(SKIP),
    "failures": FAIL,
    "fact_semantic_errors": FACT_SEMANTIC_ERRORS,
    "entity_thickness": thickness,
    "FACT_SEMANTIC_ERRORS": len(FACT_SEMANTIC_ERRORS),
    "final_counts": {"entities": len(ents), "relationships": len(rels),
                     "relation_profiles": len(rp), "relation_timelines": len(rt),
                     "sources": len(srcs), "evidence": len(ev),
                     "alias": len(alias), "countries": len(load(DATA + "countries.json")["countries"])},
}, ensure_ascii=False, indent=1))
sys.exit(1 if (FAIL or FACT_SEMANTIC_ERRORS) else 0)
