# ASIP-V1.0-RELEASE-BASELINE

Release name: ASIP Intelligence Knowledge Base V1.0
Release date: 2026-08-15
Generated: 2026-08-15T18:08:34Z

## Source / Release
- source branch: feature/asip-final-global-audit
- accepted content head (Final Global Audit PASS): b99ab288112becd87b0ac5f531c5bc5480972b7a
- source release commit (final QA artifacts): 79fc8af63960d9d34cbbf0febd48edf4c0f3a374
- main commit (fast-forward synced): 79fc8af63960d9d34cbbf0febd48edf4c0f3a374
- release tag: asip-v1.0 (-> 79fc8af63960d9d34cbbf0febd48edf4c0f3a374)

## Deployment
- Final Preview URL: https://kenan032005.github.io/asip-site/previews/asip-v1-final/
- Final Preview deploy commit: aa78c99309534350942a3b241c538eb728da5bd8
- Production URL: https://kenan032005.github.io/asip-site/
- gh-pages pre-production commit: aa78c99309534350942a3b241c538eb728da5bd8
- gh-pages production commit: 0c1eaf5be36c193b5d51cc2fc28b84767b1d22ab
- rollback method: normal git revert of production commit (NO force-reset / force-push)

## Mechanical
- countries = 13
- regions = 7
- entities = 105
- relationships = 203
- sources = 307
- evidence = 422
- routes = 335

## Grades
- Entity: A = 90, B = 15, C = 0, D = 0
- Relation: R-A = 50, R-B = 56, R-C = 52, R-D = 45
- P0 = 0

## Regression
- 41 suites / 7310 cases / 0 failed / 0 skipped

## Gates
- Final Global Audit: PASS
- Final Preview: PASS
- Production Cutover: PASS

## Known V1.0 non-blocking debt (V1.1 backlog, NOT blockers)
1. Network V3 Focused Intelligence Graph (future visual optimization)
2. 43 long source URLs
3. Africa Corps evidence density minor gap
4. 52 R-C relations
5. 45 R-D relations
6. historical dirty QA artifacts (separate repository hygiene; OUT_OF_SCOPE)
7. HIGH_VALUE_DEPTH future candidates
8. DEFER_FUTURE objects

## Historical QA dirty artifacts
- qa-artifacts-final-depth-consolidation-a/* and qa-artifacts-i3b-fix1c/* kept OUT_OF_SCOPE
  for this release; to be handled in a separate repository-hygiene pass.
