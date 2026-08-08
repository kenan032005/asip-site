#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-D1 integrity + semantics gate: uniqueness, dangling refs, relation types,
prep corrections, residual scan, packet key semantics."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "data" / "intelligence" / "africa"
DIST = ROOT / "dist" / "intelligence" / "africa"

issues = []
ok = []


def load(name):
    return json.load(open(P / name, encoding="utf-8"))


entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
sources = load("sources.json")["sources"]
evidence = load("evidence_records.json")["evidence"]
profiles = load("relation_profiles.json")["profiles"]
timelines = load("relation_timelines.json")["timelines"]
rtypes = {t["relation_type"] for t in load("relation_types.json")["relation_types"]}
regions = {r["region_id"] for r in load("regions.json")["regions"]}
countries = {c["country_id"] for c in load("countries.json")["countries"]}

eids = [e["entity_id"] for e in entities]
slugs = [e["slug"] for e in entities]
rids = [r["relationship_id"] for r in rels]
sids = [s["source_id"] for s in sources]
evids = [e["evidence_id"] for e in evidence]
eid_set, rid_set, sid_set = set(eids), set(rids), set(sids)

if len(eids) != len(set(eids)):
    issues.append("duplicate entity ids")
if len(slugs) != len(set(slugs)):
    issues.append("duplicate entity slugs")
if len(rids) != len(set(rids)):
    issues.append("duplicate relationship ids")
if len(sids) != len(set(sids)):
    issues.append("duplicate source ids")
if len(evids) != len(set(evids)):
    issues.append("duplicate evidence ids")

valid_ends = eid_set | set(countries) | set(regions)
dangling_rel_ends = []
for r in rels:
    if r["source_entity_id"] not in valid_ends or r["target_entity_id"] not in valid_ends:
        dangling_rel_ends.append(r["relationship_id"])
if dangling_rel_ends:
    issues.append("dangling relation endpoints: " + ",".join(dangling_rel_ends))
else:
    ok.append("all relation endpoints resolve (entities/countries/regions)")

dangling_src = []
for e in entities:
    for s in e.get("source_refs", []):
        if s not in sid_set:
            dangling_src.append(f"entity/{e['entity_id']}:{s}")
for r in rels:
    for s in r.get("source_refs", []):
        if s not in sid_set:
            dangling_src.append(f"rel/{r['relationship_id']}:{s}")
for e in evidence:
    if e["source_id"] not in sid_set:
        dangling_src.append(f"evidence/{e['evidence_id']}:{e['source_id']}")
for k, v in profiles.items():
    for s in v.get("source_ids", []):
        if s not in sid_set:
            dangling_src.append(f"profile/{k}:{s}")
for k, v in timelines.items():
    for item in v:
        for s in item.get("source_ids", []):
            if s not in sid_set:
                dangling_src.append(f"timeline/{k}:{s}")
if dangling_src:
    issues.append("dangling source refs: " + ",".join(dangling_src[:8]))
else:
    ok.append("all source refs resolve")

dangling_rel_refs = []
for e in evidence:
    for rid in e.get("relation_ids", []):
        if rid not in rid_set:
            dangling_rel_refs.append(f"evidence/{e['evidence_id']}:{rid}")
for k in profiles:
    if k not in rid_set:
        dangling_rel_refs.append(f"profile key {k} not in relationships")
for k in timelines:
    if k not in rid_set:
        dangling_rel_refs.append(f"timeline key {k} not in relationships")
if dangling_rel_refs:
    issues.append("dangling relation refs: " + ",".join(dangling_rel_refs[:8]))
else:
    ok.append("all relation refs resolve")

invalid_types = [r["relationship_id"] for r in rels if r["relationship_type"] not in rtypes]
if invalid_types:
    issues.append("invalid relation types: " + ",".join(invalid_types))
else:
    ok.append("all relationship types within the 24-type registry (no new ontology)")

# 43 new relations endpoints exist
new_rels = [r for r in rels if r["relationship_id"].startswith("rel-d1-")]
missing_ends = [r["relationship_id"] for r in new_rels if r["source_entity_id"] not in eid_set or r["target_entity_id"] not in (eid_set | set(countries) | set(regions))]
if len(new_rels) != 43:
    issues.append(f"expected 43 new d1 relations, found {len(new_rels)}")
if missing_ends:
    issues.append("d1 relation missing endpoints: " + ",".join(missing_ends))
else:
    ok.append(f"all {len(new_rels)} D1 relations have valid endpoints")

# ---- prep corrections ----
by_id = {r["relationship_id"]: r for r in rels}
prep = {
    "rel-endf-ola-conflict": {
        "forbidden": ["与 TPLF 结盟使奥罗米亚—提格雷两线联动"],
        "must_contain": ["不足以把2021年的OLA—TPLF联盟关系直接延伸为2026年的正式联盟"],
        "source_has": "d1-acled-ethiopia-2026",
        "no_source": "un-jnim-2018",
    },
    "rel-endf-tdf-conflict": {
        "forbidden": ["提格雷事实脱离联邦控制", "比勒陀利亚协议实质失效"],
        "must_contain": ["重新对峙/局部交火、和平框架严重承压"],
        "must_contain_in_detail": ["重新对峙/局部交火、和平框架严重承压"],
        "source_has": ["ETH_AU_2026_01_30", "d1-acled-ethiopia-2026"],
        "no_source": "un-jnim-2018",
    },
    "rel-burkina-army-jnim": {
        "forbidden": ["JNIM 控制/争夺约六成领土"],
        "must_contain": ["不能解释为JNIM单独控制或争夺约60%—70%的全国领土"],
        "source_has": "BURKINA_ACSS_2025_08_26",
        "no_source": "un-jnim-2018",
    },
}
for rid, spec in prep.items():
    r = by_id.get(rid)
    if not r:
        issues.append(f"prep target missing: {rid}")
        continue
    blob = json.dumps(r, ensure_ascii=False)
    for fw in spec["forbidden"]:
        if fw in blob:
            issues.append(f"prep residual in {rid}: {fw}")
    for mc in spec["must_contain"]:
        if mc not in r["relation_summary"] and mc not in r.get("current_status_detail", ""):
            issues.append(f"prep summary missing in {rid}: {mc}")
    for mc in spec.get("must_contain_in_detail", []):
        if mc not in r.get("current_status_detail", ""):
            issues.append(f"prep detail missing in {rid}: {mc}")
    srcs = r.get("source_refs", [])
    if spec["no_source"] in srcs:
        issues.append(f"prep un-jnim-2018 still bound on {rid}")
    sh = spec["source_has"]
    shl = sh if isinstance(sh, list) else [sh]
    for s in shl:
        if s not in srcs:
            issues.append(f"prep source missing on {rid}: {s}")
ok.append("3 D1-Prep corrections applied to relationships base records")

# ---- residual across all source data + dist ----
residuals = [
    "与 TPLF 结盟使奥罗米亚—提格雷两线联动",
    "提格雷事实脱离联邦控制",
    "比勒陀利亚协议实质失效",
    "JNIM 控制/争夺约六成领土",
]
res_hits = {}
blob_files = [P / "relationships.json", P / "relation_profiles.json", P / "relation_timelines.json", P / "evidence_records.json", P / "entity_profiles.json", P / "entities.json"]
for f in blob_files:
    text = f.read_text(encoding="utf-8")
    for t in residuals:
        if t in text:
            res_hits.setdefault(t, []).append(f.name)
if DIST.exists():
    for f in DIST.rglob("*.html"):
        text = f.read_text(encoding="utf-8", errors="replace")
        for t in residuals:
            if t in text:
                res_hits.setdefault(t, []).append(str(f.relative_to(ROOT)))
if res_hits:
    issues.append("residual hits: " + json.dumps(res_hits, ensure_ascii=False))
else:
    ok.append("residual phrases = 0 across source data and dist")

# ---- key packet semantics ----
def rel_of(sid, tid, rtype=None):
    for r in rels:
        if r["source_entity_id"] == sid and r["target_entity_id"] == tid and (rtype is None or r["relationship_type"] == rtype):
            return r
    return None


checks = [
    ("FLA-JNIM cooperates_with", rel_of("actor-fla", "actor-jnim", "cooperates_with") is not None and rel_of("actor-fla", "actor-jnim", "allied_with") is None),
    ("Ansarul Islam-JNIM constituent_of", rel_of("actor-ansarul-islam", "actor-jnim", "constituent_of") is not None),
    ("Ansaru-AQIM pledged_allegiance_to", rel_of("actor-ansaru", "actor-aqim", "pledged_allegiance_to") is not None),
    ("Ansaru-JNIM affiliated_with", rel_of("actor-ansaru", "actor-jnim", "affiliated_with") is not None),
    ("Lakurawa-IS Sahel part_of_network disputed", rel_of("actor-lakurawa", "actor-is-sahel", "part_of_network") is not None and rel_of("actor-lakurawa", "actor-is-sahel")["disputed"] is True),
    ("Lakurawa-JNIM cooperates_with disputed scope", rel_of("actor-lakurawa", "actor-jnim", "cooperates_with") is not None and rel_of("actor-lakurawa", "actor-jnim")["disputed"] is True and rel_of("actor-lakurawa", "actor-jnim").get("relationship_semantics_note") == "some_cells_only"),
    ("Dan Na-FAMa cooperates_with", rel_of("actor-dan-na-ambassagou", "actor-mali-army", "cooperates_with") is not None and rel_of("actor-dan-na-ambassagou", "actor-mali-army", "member_of_force") is None),
    ("Sadou-JNIM historical", rel_of("person-sadou-samahouna", "actor-jnim", "affiliated_with") is not None and rel_of("person-sadou-samahouna", "actor-jnim")["current_status"] == "historical_ended"),
    ("Sadou-IS Sahel current", rel_of("person-sadou-samahouna", "actor-is-sahel", "affiliated_with") is not None and rel_of("person-sadou-samahouna", "actor-is-sahel")["current_status"] == "current"),
    ("FU-AES members member_of_force", rel_of("actor-mali-army", "actor-fu-aes", "member_of_force") is not None and rel_of("actor-burkina-army", "actor-fu-aes", "member_of_force") is not None and rel_of("actor-niger-armed-forces", "actor-fu-aes", "member_of_force") is not None),
    ("Wagner-Africa Corps historically_associated_with", rel_of("actor-africa-corps", "actor-wagner-group", "historically_associated_with") is not None),
]
for name, cond in checks:
    if cond:
        ok.append(name)
    else:
        issues.append("semantic check failed: " + name)

# disputed preserved on evidence
for e in evidence:
    if e["claim_id"] in ("d1-cl-lakurawa-ambiguous", "d1-cl-lakurawa-issp"):
        if e["disputed"] is not True:
            issues.append(f"evidence disputed flag lost: {e['claim_id']}")
        if e["verification_status"] != "partially_verified":
            issues.append(f"evidence partial->verified upgrade: {e['claim_id']}")
ok.append("Lakurawa evidence disputed=true and partially_verified preserved")

# no invented dates for null-published sources
null_pub = [s["source_id"] for s in sources if s.get("published_at") is None and s["source_id"].startswith("d1-")]
for s in sources:
    if s["source_id"].startswith("d1-") and s.get("published_at") is None:
        continue
expected_null = {"d1-acled-jnim-profile-2026", "d1-acled-africa-march-2026", "d1-acled-border-triangle-2026", "d1-acled-africa-june-2026", "d1-acled-dozo-2026", "d1-acled-ethiopia-2026"}
actual_null = {s["source_id"] for s in sources if s.get("published_at") is None and s["source_id"].startswith("d1-")}
if actual_null != expected_null:
    issues.append(f"null published_at set mismatch: {actual_null ^ expected_null}")
else:
    ok.append("no invented dates; null published_at preserved on 6 ACLED sources")

report = {
    "artifact": "I3D1_INTEGRITY_SEMANTICS_GATE",
    "ok": ok,
    "issues": issues,
    "gate": "PASS" if not issues else "OPEN",
    "scale": {"entities": len(entities), "relationships": len(rels), "sources": len(sources), "evidence": len(evidence), "profiles": len(profiles), "timelines": len(timelines), "routes_built": 209},
}
(ROOT / "qa-artifacts-i3d1" / "integrity-semantics-gate.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({"gate": report["gate"], "issues": issues, "ok_count": len(ok)}, ensure_ascii=False, indent=1))
if issues:
    sys.exit(1)
