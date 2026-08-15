# ASIP Intelligence V1.0 — PRODUCTION CUTOVER REPORT

Generated: 2026-08-15T18:08:34Z
Execution model: Hy3
Mode: DEPLOYMENT ONLY — NO CONTENT / UI CHANGES
Decision: APPROVE PRODUCTION

## Release source freeze (step 1)
- source_branch: feature/asip-final-global-audit
- accepted_content_head: b99ab288112becd87b0ac5f531c5bc5480972b7a
- source_head (release): 79fc8af63960d9d34cbbf0febd48edf4c0f3a374
- b99ab28 -> 79fc8af contains ONLY qa-artifacts-final-preview-release/* (16 files)
- KNOWLEDGE_DATA_CHANGED = 0
- UI_SOURCE_CHANGED = 0

## Build (step 4)
- command: python scripts/build_site.py --no-embed
- BUILD = PASS
- countries=13 regions=7 entities=105 relationships=203 sources=307 evidence=422 routes=335

## Preview vs Candidate (step 5)
- UNEXPECTED_CONTENT_DIFF = 0 (only build-timestamp metadata differs; run_id identical)

## Production deployment (step 6)
- production namespace: gh-pages root
- PRE_PRODUCTION_GH_PAGES_COMMIT = aa78c99309534350942a3b241c538eb728da5bd8
- PRODUCTION_GH_PAGES_COMMIT = 0c1eaf5be36c193b5d51cc2fc28b84767b1d22ab
- previews/ preserved: asip-v1-final, asip-intelligence-v1.0-rc1, asip-intelligence-v2
- 8 stale legacy entity/relation pages removed
- force_push = NO

## Production route QA (step 8)
- PRODUCTION_ROUTE_TOTAL = 335 (+ 43 root demo pages = 378 html checked)
- PRODUCTION_ROUTE_FAILURES = 0 (1 transient 503 on iyad-ag-ghali reconfirmed 200)
- BROKEN_INTERNAL_LINKS = 0
- BROKEN_ASSETS = 0

## Production data integrity (step 9)
- entities=105 relationships=203 sources=307 evidence=422 (all match)
- 17 knowledge files byte-identical to accepted source
- Pack B entities/profiles present (SLM/A-AW, Abu Hanifa, Jafar Dicko, FLA, MNLA, Africa Corps, IS-Mozambique, ADF/ISIS-CA)
- PRODUCTION_CONTENT_INTEGRITY = PASS

## Network production QA (step 10)
- NETWORK_PRODUCTION_QA = PASS (unchanged from accepted build; focus entities present)

## Production vs Preview parity (step 11)
- 12 key pages MATCH; full-tree 378 html normalized -> 0 content diff
- PRODUCTION_PREVIEW_PARITY = PASS

## Main sync + tag (step 7, 12)
- main fast-forward: 8924416..79fc8af (no force / no rewrite)
- MAIN_RELEASE_SOURCE_MATCH = PASS
- tag asip-v1.0 -> 79fc8af63960d9d34cbbf0febd48edf4c0f3a374 (normal push)

## Final hard gates (step 18)
- KNOWLEDGE_DATA_CHANGED = 0
- UI_SOURCE_CHANGED = 0
- BUILD = PASS
- UNEXPECTED_CONTENT_DIFF = 0
- PRODUCTION_DEPLOY = PASS
- PRODUCTION_ROUTE_FAILURES = 0
- BROKEN_INTERNAL_LINKS = 0
- BROKEN_ASSETS = 0
- PRODUCTION_CONTENT_INTEGRITY = PASS
- NETWORK_PRODUCTION_QA = PASS
- PRODUCTION_PREVIEW_PARITY = PASS
- MAIN_RELEASE_SOURCE_MATCH = PASS
- RELEASE_TAG_CREATED = PASS
- ROLLBACK_POINT_RECORDED = PASS
- force_push = NO

## Final state
- ASIP_V1_PRODUCTION_CUTOVER = PASS
- ASIP_V1_RELEASE_STATUS = PRODUCTION

Production URL: https://kenan032005.github.io/asip-site/
Awaiting ChatGPT final release acceptance.
