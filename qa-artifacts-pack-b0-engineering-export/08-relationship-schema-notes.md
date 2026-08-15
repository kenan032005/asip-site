# Relationship Schema Notes (mechanical, program structure only)

Source: `scripts/build_intelligence_africa.py::validate()` + `relationships.json`
+ `relation_profiles.json` + `relation_timelines.json`.

## relationships.json record — fields actually present
`claim_valid_as_of`, `confidence`, `current_status`, `current_status_detail`, `current_status_verified_at`, `direction`, `display_ring`, `disputed`, `formation_background`, `freshness_status`, `geographic_scope`, `last_verified_at`, `record_created_at`, `record_reviewed_at`, `record_updated_at`, `relation_summary`, `relationship_id`, `relationship_semantics_note`, `relationship_type`, `slug`, `source_entity_id`, `source_refs`, `start_year`, `target_entity_id`, `temporal_disclosure`, `temporal_handling`, `temporal_sensitive`, `time_end`, `time_start`, `uncertainties`, `why_it_matters`

## Validator constraints on relationships.json
- `relationship_id` : unique
- `source_entity_id` / `target_entity_id` : MUST be a valid endpoint =
  an existing entity_id OR country_id OR region_id (region endpoints allowed, e.g. active_in_region)
- `display_ring` ∈ {inner, middle, outer}
- `relationship_type` : MUST be registered in `relation_types.json` (>= 20 types required)
- `freshness_status` ∈ {current, aging, stale, historical, unknown}
- `source_refs[]` : each must exist in sources.json source_id set

## relation_profiles.json — fields actually present
`asip_analysis`, `causes`, `constraints`, `continuities`, `cooperation_dimensions`, `current_assessment`, `current_status`, `current_structure`, `differences`, `direction`, `display_ring`, `disputed`, `drivers`, `evolution_stages`, `formation_background`, `geographic_scope`, `historical_context`, `humanitarian_spillover`, `impact_on_security`, `imported_by`, `initial_relationship`, `key_turning_points`, `last_verified_at`, `maturity_assessed_at`, `maturity_basis`, `nature`, `operational_role`, `organizational_balance`, `overview`, `parties`, `personnel_flows`, `regional_differences`, `relation_id`, `relation_maturity`, `relation_title`, `relation_type`, `relationship_id`, `role`, `slug`, `source_entity_id`, `source_ids`, `target_entity_id`, `temporal_disclosure`, `temporal_handling`, `temporal_sensitive`, `third_party_effects`, `uncertainties`, `watch_indicators`, `why_it_matters`

## relation_timelines.json — structure (list of event objects per relationship_id)
Per event object observed keys: date, event_title, event_description, impact_on_relationship,
confidence, disputed, source_ids[]. (Validator: every timeline event source_ids[] must be valid.)

## Where to write
- relationship record -> `data/intelligence/africa/relationships.json` (relationships[])
- relation profile -> `data/intelligence/africa/relation_profiles.json` (profiles[relationship_id])
- relation timeline -> `data/intelligence/africa/relation_timelines.json` (timelines[relationship_id])
