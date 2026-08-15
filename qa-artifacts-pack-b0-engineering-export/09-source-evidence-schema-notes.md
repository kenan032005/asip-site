# Source / Evidence Schema Notes (mechanical, program structure only)

Source: `sources.json`, `evidence_records.json`, validator in `build_intelligence_africa.py`.

## sources.json — fields actually present
`accessed_at`, `date_precision`, `imported_by`, `notes`, `published_at`, `publisher`, `reliability`, `source_id`, `source_type`, `title`, `url`

Validator constraints on sources: referenced by entities/relations/profiles/timelines/evidence —
every source_ref / source_id must resolve to a source_id in sources.json (fail on bad ref).

## evidence_records.json — fields actually present
`as_of_date`, `claim_id`, `claim_text_zh`, `claim_type`, `claim_valid_as_of`, `confidence`, `country_ids`, `current_status_verified_at`, `disputed`, `entity_ids`, `evidence_id`, `evidence_origin`, `freshness_status`, `notes`, `record_created_at`, `record_reviewed_at`, `record_updated_at`, `region_ids`, `relation_ids`, `review_note`, `source_accessed_at`, `source_id`, `source_locator`, `source_published_at`, `time_sensitive`, `verification_method`, `verification_status`, `verified_at`

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
