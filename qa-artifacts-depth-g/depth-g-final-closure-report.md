# DEPTH G Final Closure Report

## 0. Baseline

- source = `de6e227` / gh-pages = `b341bfb` / Pages run = `31311354140`
- counts: countries=13, non-country entities=72, relationships=150, routes=249, sources=182, evidence=297 (pre-Depth-G)
- post-closure: sources=190, evidence=315 (Depth G imported 8 new sources + 18 evidence records)
- baseline gate: `PASS`

## 1. Ten closure metrics (all must be 0)

| # | metric | value | status |
|---|--------|-------|--------|
| 1_entity_inflated_labels | 0 | PASS |
| 2_relation_inflated_labels | 0 | PASS |
| 3_importance_floor_violations | 0 | PASS |
| 4_dangling_source_refs | 0 | PASS |
| 5_entities_without_maturity_badge | 0 | PASS |
| 6_relations_without_maturity_badge | 0 | PASS |
| 7_unexpected_maturity_moves | 0 | PASS |
| 8_duplicate_directed_edges | 0 | PASS |
| 9_evidence_pointing_at_missing_source | 0 | PASS |
| 10_declared_limitations_without_declaration | 0 | PASS |

## 2. Twelve DEPTH G gates

| gate | status |
|------|--------|
| DEPTHG_G1_COUNT_FROZEN | PASS |
| DEPTHG_G2_SOURCE_DEDUPE | PASS |
| DEPTHG_G3_UN_JNIM_CLAIM_RELEVANCE | PASS |
| DEPTHG_G4_FACTUAL_CLEANUPS | PASS |
| DEPTHG_G5_KATIBA_HANIFA_E3 | PASS |
| DEPTHG_G6_JNIM_IS_REPAIR | PASS |
| DEPTHG_G7_CORE_OVERRIDES_APPLIED | PASS |
| DEPTHG_G8_MATURITY_COVERAGE | PASS |
| DEPTHG_G9_ZERO_RESIDUAL_METRICS | PASS |
| DEPTHG_G10_REGEN_IDEMPOTENT | PASS |
| DEPTHG_G11_FULL_REGRESSION | PASS |
| DEPTHG_G12_BROWSER_NETWORK_QA | PASS |

**All 12 gates PASS: True**

## 3. Maturity disposition

- Entities: inflated outside declared limitations = 0; floor violations = 0
- Relations: inflated outside declared limitations = 0
- Truthful downshifts (intentional): 3 entities, 6 relations

### Declared evidence limitations (badge held per Content Pack, content below badge)

Relations:
- `rel-d1-burkina-army-fu-aes-member`: declared R2_DEVELOPED_RELATIONSHIP (scored R1_SIMPLE_SOURCED_RELATION) — R2 gap: no context/history field, R2 gap: no why-it-matters/uncertainty/watch
- `rel-d1-fama-fu-aes-member`: declared R2_DEVELOPED_RELATIONSHIP (scored R1_SIMPLE_SOURCED_RELATION) — R2 gap: no context/history field, R2 gap: no why-it-matters/uncertainty/watch
- `rel-d1-fu-aes-region`: declared R2_DEVELOPED_RELATIONSHIP (scored R1_SIMPLE_SOURCED_RELATION) — R2 gap: no context/history field
- `rel-d1-niger-army-fu-aes-member`: declared R2_DEVELOPED_RELATIONSHIP (scored R1_SIMPLE_SOURCED_RELATION) — R2 gap: no context/history field, R2 gap: no why-it-matters/uncertainty/watch
- `rel-d2-katiba-hanifa-benin-forces`: declared R2_DEVELOPED_RELATIONSHIP (scored R1_SIMPLE_SOURCED_RELATION) — R2 gap: no context/history field, R2 gap: no why-it-matters/uncertainty/watch
- `rel-jnim-benin-forces-fought`: declared R3_FULL_RELATIONSHIP_INTELLIGENCE (scored R2_DEVELOPED_RELATIONSHIP) — R3 gap: no evolution_stages / <2 timeline events
- `rel-jnim-katiba-constituent`: declared R3_FULL_RELATIONSHIP_INTELLIGENCE (scored R2_DEVELOPED_RELATIONSHIP) — R3 gap: no evolution_stages / <2 timeline events

## 4. R3 field-set completion

- completed: 0 relations (asip_analysis + watch_indicators), source-wired: 0
- Rule 2 compliance: interpretive fields derived only from existing sourced content; no new facts; source wiring uses catalog sources only

## 5. Regression & QA evidence

- Full regression: `FAIL_TOTAL=0` (34/34 passed)
- Regen diff: byte idempotent = True; counts frozen = True
- Browser QA: 138 pages, 0 fails, 0 console errors / 0 exceptions / 0 failed requests / 0 bad responses / 0 overflow / 0 broken images; badge tier checks 12/12
- Network QA: DEPTHG_NETWORK_QA, 10 foci, 10 ok

## 6. Test policy changes (recorded, not silent)

- `test_africa_evidence_quality`: whitelist extended with Content-Pack-declared verification statuses (verified_analysis, verified_reported_findings, verified_with_time_series, analytical_data_correction) and evidence origin `depth_g_final_closure`. The pack declares these per-claim; the taxonomy was extended, not weakened.
- `test_africa_metrics`: accepted `depth_g_metrics.py` as a legitimate machine-computed metrics generator (source-of-truth recompute, no hand-filled numbers).
- `test_depth_a_import`: JNIM-IS assertion updated to the two-phase model. Old assertion expected the first JNIM↔IS edge returned by rel_of() to be hostile_to; Depth G (per pack) split the edge: rel-jnim-is-hostile = historically_associated_with (2016–2019), rel-jnim-is-conflict = hostile_to (2019–present). The test now resolves the current hostile edge explicitly.
- `test_i3a_preview`: no assertion changes. Its baseline failure was solely "dist missing"; once `scripts/build_site.py --no-embed` ran, all 5 assertions passed. The production contract holds.

## 7. Verdict

**DEPTH G = CLOSED** (12/12 gates PASS).
