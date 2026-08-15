# Entity Schema Notes (mechanical, program structure only)

Source: `scripts/build_intelligence_africa.py::validate()` + `data/intelligence/africa/entities.json`
+ `entity_profiles.json`. No factual-content interpretation.

## entities.json record — fields actually present (union of all records)
`acronym`, `aliases`, `claim_valid_as_of`, `confidence`, `country_ids`, `current_status`, `current_status_verified_at`, `disputed`, `entity_id`, `entity_type`, `evidence_ids`, `freshness_reviewed_by`, `freshness_status`, `full_description`, `historical_names`, `importance_level`, `importance_reasons`, `importance_review_status`, `importance_reviewed_at`, `importance_score`, `last_verified_at`, `name_en`, `name_zh`, `native_name`, `primary_category`, `primary_type`, `profile_level`, `record_created_at`, `record_reviewed_at`, `record_updated_at`, `region_ids`, `secondary_types`, `short_description`, `slug`, `source_refs`, `tags`, `temporal_sensitive`, `verification_status`

## Validator constraints on entities.json
- `entity_id` : unique (fail on duplicate)
- `slug` : unique (fail on duplicate)
- `importance_level` ∈ {L1, L2, L3} (fail otherwise)
- `freshness_status` ∈ {current, aging, stale, historical, unknown, current_as_structural_history}
- `region_ids[]` : each must exist in regions.json region_id set
- `country_ids[]` : each must exist in countries.json country_id set
- `source_refs[]` : each must exist in sources.json source_id set
- `acronym` : MUST be a string (None is a fail) — use "" for absent
- No country objects duplicated inside entities.json (countries.json is canonical)
- No empty/placeholder text ("暂无信息", "待补充", "TBD", "placeholder") in profiles

## entity_profiles.json — fields actually present
`completeness`, `content_maturity`, `depth_score`, `importance_level`, `importance_statement`, `imported_by`, `profile_depth`, `profile_level`, `sections`, `source_refs`

### sections content model (from validator `_tl`/`_secs`/`_paras`)
A section value may be:
- a string, or
- a list of strings, or
- a dict with keys `p` (list of para strings), `list` (list of items), `table` ({headers, rows})

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
