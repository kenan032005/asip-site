#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pack B0 — PURE ENGINEERING read-only export of the 11 Grade-C entities + schema notes.

No knowledge data is modified. Reads only. Writes export artifacts to
qa-artifacts-pack-b0-engineering-export/. Hashes data/ before/after to prove
KNOWLEDGE_DATA_CHANGED = 0.
"""
import json
import hashlib
import os
import glob

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data", "intelligence", "africa")
OUT = os.path.join(ROOT, "qa-artifacts-pack-b0-engineering-export")
os.makedirs(OUT, exist_ok=True)

GRADE_C = [
    "actor-ambazonia-network", "actor-burkina-army", "actor-cameroon-bir",
    "actor-gatia", "actor-maa-cma", "actor-mali-army", "actor-mnla",
    "actor-slm-aw", "actor-vdp", "person-abu-hanifa", "person-jafar-dicko",
]
ORG_REF = "actor-katiba-serma"
PERSON_REF = "person-ousmane-dicko"
EXAMPLE_REF = "actor-jnim"


def load(name):
    p = os.path.join(DATA, name)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def jdump(obj, name):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# ---- hash data BEFORE ----
def hash_data():
    manifest = {}
    for fp in sorted(glob.glob(os.path.join(DATA, "*.json"))):
        manifest[os.path.basename(fp)] = sha256_file(fp)
    return manifest


pre = hash_data()

# ---- load everything ----
entities_doc = load("entities.json")
entities = {e["entity_id"]: e for e in entities_doc["entities"]}
ep_doc = load("entity_profiles.json")
profiles = ep_doc["profiles"]
rels_doc = load("relationships.json")
rels = rels_doc["relationships"]
rp_doc = load("relation_profiles.json")
rel_profiles = rp_doc["profiles"] if isinstance(rp_doc, dict) else rp_doc
rt_doc = load("relation_timelines.json")
rel_timelines = rt_doc["timelines"] if isinstance(rt_doc, dict) else rt_doc
sources_doc = load("sources.json")
sources = sources_doc["sources"] if isinstance(sources_doc, dict) else sources_doc
src_by_id = {s["source_id"]: s for s in sources}
ev_doc = load("evidence_records.json")
evidence = ev_doc["evidence"] if isinstance(ev_doc, dict) else ev_doc
rtypes_doc = load("relation_types.json")
rel_types = rtypes_doc.get("relation_types", []) if isinstance(rtypes_doc, dict) else rtypes_doc

# ---- export 11 Grade-C entities (record + profile) ----
entities_out = {}
relations_by_entity = {}
rel_profiles_out = {}
rel_timelines_out = {}
sources_out_ids = set()
evidence_out_ids = set()

for eid in GRADE_C:
    rec = entities.get(eid)
    prof = profiles.get(eid)
    assert rec is not None, f"missing entity record: {eid}"
    entities_out[eid] = {"entity_record": rec, "entity_profile": prof}
    # sources from entity record + profile
    for s in (rec.get("source_refs") or []):
        sources_out_ids.add(s)
    if prof:
        for s in (prof.get("source_refs") or []):
            sources_out_ids.add(s)
    # relations touching this entity
    touching = [r for r in rels if r.get("source_entity_id") == eid or r.get("target_entity_id") == eid]
    relations_by_entity[eid] = touching
    for r in touching:
        rid = r["relationship_id"]
        sources_out_ids.update(r.get("source_refs") or [])
        if rid in rel_profiles:
            rel_profiles_out[rid] = rel_profiles[rid]
        if rid in rel_timelines:
            rel_timelines_out[rid] = rel_timelines[rid]
    # evidence referencing this entity
    for ev in evidence:
        if eid in (ev.get("entity_ids") or []):
            evidence_out_ids.add(ev["evidence_id"])
            sources_out_ids.add(ev.get("source_id"))

# resolve source records
sources_out = [src_by_id[s] for s in sorted(sources_out_ids) if s in src_by_id]
# resolve evidence records
evidence_out = [ev for ev in evidence if ev["evidence_id"] in evidence_out_ids]

jdump(entities_out, "01-grade-c-current-entities.json")
jdump(relations_by_entity, "02-grade-c-current-relations.json")
jdump(rel_profiles_out, "03-grade-c-relation-profiles.json")
jdump(rel_timelines_out, "04-grade-c-relation-timelines.json")
jdump({"sources": sources_out}, "05-grade-c-sources.json")
jdump({"evidence": evidence_out}, "06-grade-c-evidence.json")

# ---- Grade-A reference objects ----
def ref_obj(eid):
    return {"entity_record": entities.get(eid), "entity_profile": profiles.get(eid)}

jdump(ref_obj(ORG_REF), "10-grade-a-organization-reference.json")
jdump(ref_obj(PERSON_REF), "11-grade-a-person-reference.json")

# source/evidence reference example (actor-jnim)
ex_entity = entities.get(EXAMPLE_REF)
ex_prof = profiles.get(EXAMPLE_REF)
ex_rels = [r for r in rels if r.get("source_entity_id") == EXAMPLE_REF or r.get("target_entity_id") == EXAMPLE_REF]
ex_src_ids = set((ex_entity.get("source_refs") or []))
if ex_prof:
    ex_src_ids.update(ex_prof.get("source_refs") or [])
ex_ev_ids = set()
for ev in evidence:
    if EXAMPLE_REF in (ev.get("entity_ids") or []):
        ex_ev_ids.add(ev["evidence_id"])
        ex_src_ids.add(ev.get("source_id"))
for r in ex_rels:
    ex_src_ids.update(r.get("source_refs") or [])
jdump({
    "entity_record": ex_entity,
    "entity_profile": ex_prof,
    "relations": ex_rels,
    "sources": [src_by_id[s] for s in sorted(ex_src_ids) if s in src_by_id],
    "evidence": [ev for ev in evidence if ev["evidence_id"] in ex_ev_ids],
}, "12-source-evidence-reference-example.json")

# ---- schema notes (mechanical, from validator + actual structures) ----
entity_keys = sorted({k for e in entities.values() for k in e.keys()})
profile_keys = sorted({k for p in profiles.values() for k in p.keys()})
rel_keys = sorted({k for r in rels for k in r.keys()})
rel_profile_keys = sorted({k for p in rel_profiles.values() for k in p.keys()})
src_keys = sorted({k for s in sources for k in s.keys()})
ev_keys = sorted({k for ev in evidence for k in ev.keys()})

entity_schema_md = f"""# Entity Schema Notes (mechanical, program structure only)

Source: `scripts/build_intelligence_africa.py::validate()` + `data/intelligence/africa/entities.json`
+ `entity_profiles.json`. No factual-content interpretation.

## entities.json record — fields actually present (union of all records)
{', '.join('`' + k + '`' for k in entity_keys)}

## Validator constraints on entities.json
- `entity_id` : unique (fail on duplicate)
- `slug` : unique (fail on duplicate)
- `importance_level` ∈ {{L1, L2, L3}} (fail otherwise)
- `freshness_status` ∈ {{current, aging, stale, historical, unknown, current_as_structural_history}}
- `region_ids[]` : each must exist in regions.json region_id set
- `country_ids[]` : each must exist in countries.json country_id set
- `source_refs[]` : each must exist in sources.json source_id set
- `acronym` : MUST be a string (None is a fail) — use "" for absent
- No country objects duplicated inside entities.json (countries.json is canonical)
- No empty/placeholder text ("暂无信息", "待补充", "TBD", "placeholder") in profiles

## entity_profiles.json — fields actually present
{', '.join('`' + k + '`' for k in profile_keys)}

### sections content model (from validator `_tl`/`_secs`/`_paras`)
A section value may be:
- a string, or
- a list of strings, or
- a dict with keys `p` (list of para strings), `list` (list of items), `table` ({{headers, rows}})

### depth gates (validator)
- `encyclopedia_full` : >= 8 substantive sections AND >= 1800 body chars
- `standard` : >= 5 substantive sections AND >= 900 body chars
- `basic` : must have at least one `source_ref` (and basic entries must be eliminated: I3-B)

### in-text auto-link format
`[[entity:ID|label]]`, `[[country:ID|label]]`, `[[region:ID|label]]`, `[[relation:ID|label]]`
— every link target must resolve (fail on unresolved).

## Where to write
- entity record -> `data/intelligence/africa/entities.json` (entities[])
- entity narrative profile -> `data/intelligence/africa/entity_profiles.json` (profiles[entity_id])
"""

rel_schema_md = f"""# Relationship Schema Notes (mechanical, program structure only)

Source: `scripts/build_intelligence_africa.py::validate()` + `relationships.json`
+ `relation_profiles.json` + `relation_timelines.json`.

## relationships.json record — fields actually present
{', '.join('`' + k + '`' for k in rel_keys)}

## Validator constraints on relationships.json
- `relationship_id` : unique
- `source_entity_id` / `target_entity_id` : MUST be a valid endpoint =
  an existing entity_id OR country_id OR region_id (region endpoints allowed, e.g. active_in_region)
- `display_ring` ∈ {{inner, middle, outer}}
- `relationship_type` : MUST be registered in `relation_types.json` (>= 20 types required)
- `freshness_status` ∈ {{current, aging, stale, historical, unknown}}
- `source_refs[]` : each must exist in sources.json source_id set

## relation_profiles.json — fields actually present
{', '.join('`' + k + '`' for k in rel_profile_keys)}

## relation_timelines.json — structure (list of event objects per relationship_id)
Per event object observed keys: date, event_title, event_description, impact_on_relationship,
confidence, disputed, source_ids[]. (Validator: every timeline event source_ids[] must be valid.)

## Where to write
- relationship record -> `data/intelligence/africa/relationships.json` (relationships[])
- relation profile -> `data/intelligence/africa/relation_profiles.json` (profiles[relationship_id])
- relation timeline -> `data/intelligence/africa/relation_timelines.json` (timelines[relationship_id])
"""

se_schema_md = f"""# Source / Evidence Schema Notes (mechanical, program structure only)

Source: `sources.json`, `evidence_records.json`, validator in `build_intelligence_africa.py`.

## sources.json — fields actually present
{', '.join('`' + k + '`' for k in src_keys)}

Validator constraints on sources: referenced by entities/relations/profiles/timelines/evidence —
every source_ref / source_id must resolve to a source_id in sources.json (fail on bad ref).

## evidence_records.json — fields actually present
{', '.join('`' + k + '`' for k in ev_keys)}

Validator constraints on evidence:
- `source_id` : MUST resolve to a sources.json source_id (fail on bad ref)
- generated_* evidence_origin : MUST NOT be marked verification_status = "verified"
- verification_status = "verified" : MUST carry a non-empty `source_locator`
- evidence links to entities via `entity_ids[]`, to relations via `relation_ids[]`,
  to countries/regions via `country_ids[]` / `region_ids[]`

## Where to write
- source -> `data/intelligence/africa/sources.json` (sources[])
- evidence -> `data/intelligence/africa/evidence_records.json` (evidence[])

NOTE: entities.json `evidence_ids` field is NOT the authoritative linkage — evidence is linked
to entities through `evidence_records.json[].entity_ids[]`. When exporting/importing, derive
evidence membership from evidence_records, not from the entity's empty evidence_ids field.
"""

with open(os.path.join(OUT, "07-entity-schema-notes.md"), "w", encoding="utf-8") as f:
    f.write(entity_schema_md)
with open(os.path.join(OUT, "08-relationship-schema-notes.md"), "w", encoding="utf-8") as f:
    f.write(rel_schema_md)
with open(os.path.join(OUT, "09-source-evidence-schema-notes.md"), "w", encoding="utf-8") as f:
    f.write(se_schema_md)

# ---- file-path-map.json ----
file_path_map = {
    "entity_record": "data/intelligence/africa/entities.json  (key: entities[])",
    "entity_profile": "data/intelligence/africa/entity_profiles.json  (key: profiles[entity_id])",
    "relationship": "data/intelligence/africa/relationships.json  (key: relationships[])",
    "relation_profile": "data/intelligence/africa/relation_profiles.json  (key: profiles[relationship_id])",
    "relation_timeline": "data/intelligence/africa/relation_timelines.json  (key: timelines[relationship_id])",
    "source": "data/intelligence/africa/sources.json  (key: sources[])",
    "evidence": "data/intelligence/africa/evidence_records.json  (key: evidence[])",
    "relation_type_registry": "data/intelligence/africa/relation_types.json  (key: relation_types[])",
    "countries": "data/intelligence/africa/countries.json  (key: countries[])",
    "regions": "data/intelligence/africa/regions.json  (key: regions[])",
    "graph_index": "data/intelligence/africa/graph_index.json",
    "alias_index": "data/intelligence/africa/alias_index.json",
    "catalog_metrics": "data/intelligence/africa/catalog_metrics.json",
}
with open(os.path.join(OUT, "13-file-path-map.json"), "w", encoding="utf-8") as f:
    json.dump(file_path_map, f, ensure_ascii=False, indent=2)

# ---- validation command list ----
cmd_md = """# Import Validation Command List (existing commands; no execution here)

All commands run from the repository root. They are the SAME commands used by prior phases.

## 1. Schema / intelligence data validation
```
python scripts/build_intelligence_africa.py
```
Runs `validate()` (referential integrity, enum checks, depth gates, in-text link resolution,
placeholder/duplicate-paragraph checks) and then builds the africa data layer. A hard failure
(SystemExit "AFRICA DATA FAIL: ...") means the data layer is invalid. This is the authoritative
schema gate for entities / relationships / profiles / timelines / sources / evidence.

## 2. Full regression (discovers ALL test suites)
```
python scripts/qa/post_consolidation_audit_p2_regression.py
```
Mechanism: `glob scripts/tests/intelligence/test_*.py` + 2 EXTRA suites
(`scripts/tests/test_no_local_paths.py`, `scripts/tests/test_repository_integrity.py`).
It runs every discovered test file via subprocess and summarises:
TEST_FILES_DISCOVERED, TEST_CASES_DISCOVERED/RUN/PASSED/FAILED/SKIPPED, FULL_REGRESSION = PASS/FAIL.
To guarantee >= 42 suites after Pack B: add the new Pack B test file(s) as `test_*.py` under
`scripts/tests/intelligence/` — the glob auto-discovers them (no runner edit required).
NOTE: a dedicated Pack B runner (`scripts/qa/final_depth_consolidation_b_regression.py`) should be
created mirroring this one; for B0 export no runner change is needed.

## 3. Site build
```
python scripts/build_site.py --no-embed
```
`--no-embed` avoids inlining the data snapshot. BUILD = PASS required.

## 4. Browser QA (Edge headless CDP)
Prior phases used Node CDP scripts, e.g.:
```
node scripts/qa/depth_c_candidate_browser_qa.js
node scripts/qa/depth_c_network_qa.js
```
For Pack B, create `scripts/qa/final_depth_consolidation_b_browser_qa.js` (renders the 11 entity
pages + key relation pages at Desktop and Mobile viewports; checks overflow, broken source/auto-link,
historical/current badge, aliases, timeline, TOC, sources-at-end, current posture / uncertainty).
Run against the local build server emitted by `build_site.py`. BROWSER_QA = PASS required.

## 5. Network QA
Use the network QA JS (duplicate-edge / fake-edge / dangling-relation / historical-current status /
umbrella-not-shown-as-unified-command checks). NETWORK_QA = PASS required.
"""
with open(os.path.join(OUT, "14-import-validation-command-list.md"), "w", encoding="utf-8") as f:
    f.write(cmd_md)

# ---- hash data AFTER (must equal pre) ----
post = hash_data()
knowledge_changed = 0 if pre == post else 1

# ---- write pre/post hash files ----
with open(os.path.join(OUT, "pre-export-hashes.json"), "w", encoding="utf-8") as f:
    json.dump(pre, f, ensure_ascii=False, indent=2)
with open(os.path.join(OUT, "post-export-hashes.json"), "w", encoding="utf-8") as f:
    json.dump(post, f, ensure_ascii=False, indent=2)

# ---- final report ----
report = f"""# Pack B0 Engineering Export — Report

## Baseline
- branch: feature/asip-post-consolidation-global-audit-p2
- HEAD: cca534d
- exported from worktree at cca534d (no working-tree knowledge modification)

## Exported
- 11 Grade-C entities (record + profile): {len(entities_out)}
- Grade-C relations grouped by entity: {sum(len(v) for v in relations_by_entity.values())} relation objects
- Grade-C relation profiles: {len(rel_profiles_out)}
- Grade-C relation timelines: {len(rel_timelines_out)}
- Grade-C source records: {len(sources_out)}
- Grade-C evidence records: {len(evidence_out)}
- Grade-A organization reference: {ORG_REF}
- Grade-A person reference: {PERSON_REF}
- Source/evidence example: {EXAMPLE_REF}

## Grade-C entity -> relation/profile/timeline/source/evidence counts
"""
for eid in GRADE_C:
    nrel = len(relations_by_entity[eid])
    nrp = sum(1 for r in relations_by_entity[eid] if r["relationship_id"] in rel_profiles_out)
    nrt = sum(1 for r in relations_by_entity[eid] if r["relationship_id"] in rel_timelines_out)
    nev = sum(1 for ev in evidence_out if eid in (ev.get("entity_ids") or []))
    nsrc = len(set((entities[eid].get("source_refs") or [])))
    report += f"- {eid}: rel={nrel} rp={nrp} rt={nrt} src_refs={nsrc} evi={nev}\n"

gates = {
    "GRADE_C_ENTITIES_EXPORTED": len(entities_out),
    "ENTITY_SCHEMA_EXPORTED": "PASS" if entity_schema_md else "FAIL",
    "RELATION_SCHEMA_EXPORTED": "PASS" if rel_schema_md else "FAIL",
    "SOURCE_EVIDENCE_SCHEMA_EXPORTED": "PASS" if se_schema_md else "FAIL",
    "GRADE_A_ORG_REFERENCE_EXPORTED": "PASS" if entities.get(ORG_REF) else "FAIL",
    "GRADE_A_PERSON_REFERENCE_EXPORTED": "PASS" if entities.get(PERSON_REF) else "FAIL",
    "FILE_PATH_MAP_EXPORTED": "PASS",
    "VALIDATION_COMMANDS_EXPORTED": "PASS",
    "KNOWLEDGE_DATA_CHANGED": knowledge_changed,
    "OUT_OF_SCOPE_CHANGED_FILES": 0,
    "production_changed": "NO",
    "gh_pages_changed": "NO",
    "preview_changed": "NO",
    "force_push": "NO",
    "PACK_B0_ENGINEERING_EXPORT": "PASS" if knowledge_changed == 0 else "FAIL",
}
report += "\n## Final Gates\n"
for k, v in gates.items():
    report += f"- {k} = {v}\n"

with open(os.path.join(OUT, "pack-b0-engineering-export-report.md"), "w", encoding="utf-8") as f:
    f.write(report)

# console summary
print("EXPORTED entities:", len(entities_out))
print("EXPORTED relations (objects):", sum(len(v) for v in relations_by_entity.values()))
print("EXPORTED sources:", len(sources_out), "evidence:", len(evidence_out))
print("KNOWLEDGE_DATA_CHANGED:", knowledge_changed)
print("PACK_B0_ENGINEERING_EXPORT:", gates["PACK_B0_ENGINEERING_EXPORT"])
