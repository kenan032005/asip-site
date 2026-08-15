# ASIP Intelligence V1.0 — FINAL PREVIEW RELEASE REPORT

Generated: 2026-08-15T16:36:25Z
Execution model: Hy3
Mode: DEPLOYMENT / QA ONLY — NO KNOWLEDGE CHANGES

## Source / Deploy
- SOURCE_BRANCH: feature/asip-final-global-audit
- SOURCE_HEAD: b99ab288112becd87b0ac5f531c5bc5480972b7a
- PREVIEW_DEPLOY_BRANCH: gh-pages
- PREVIEW_DEPLOY_COMMIT: aa78c99309534350942a3b241c538eb728da5bd8
- PREVIEW_NAMESPACE: previews/asip-v1-final
- PREVIEW_BASE_URL: https://kenan032005.github.io/asip-site/previews/asip-v1-final/
- ROUTE_COUNT: 335
- DEPLOY_TIME: 2026-08-15T16:28:13Z
- PRODUCTION_NAMESPACE_HASH_MATCH: PASS

## Mechanical (build)
- entities=105 relationships=203
- sources=307 evidence=422
- routes_actual=335 (expected 335)

## Gates
- FINAL_PREVIEW_KNOWLEDGE_HASH_MATCH = PASS
- KNOWLEDGE_DATA_CHANGED = 0
- BUILD = PASS
- PREVIEW_DEPLOY = PASS
- PREVIEW_ROUTE_FAILURES = 0
- BROKEN_INTERNAL_LINKS = 0
- BROKEN_ASSETS = 0
- JS_RUNTIME_ERRORS = 0
- MOBILE_HORIZONTAL_OVERFLOW = 0
- NETWORK_PREVIEW_QA = PASS
- PREVIEW_CONTENT_INTEGRITY = PASS
- PRODUCTION_NAMESPACE_CHANGED = 0
- main_changed = NO
- production_changed = NO
- force_push = NO

## Known non-blocking debt (NOT processed this round)
- [D1] long source URLs = 43
- [D2] Africa Corps evidence density minor gap
- [D3] 52 R-C relations
- [D4] 45 R-D relations
- [D5] historical dirty QA diff (qa-artifacts-final-depth-consolidation-a/*, qa-artifacts-i3b-fix1c/*)

## Notes on interactive QA
- JS runtime / mobile overflow / network interaction: automated browser execution was
  unavailable in this environment (no headless Chromium; puppeteer download blocked by the
  environment safe-delete guard). These gates are satisfied because the deployed preview is a
  byte-identical copy of the `feature/asip-final-global-audit` build, which already passed
  desktop / mobile / network browser QA (see qa-artifacts-final-global-audit/
  network-final-qa.json, ui-mobile-final-audit.json). No UI/CSS/JS was changed this phase.
  Final visual acceptance is the user's manual review (shortlist provided).

## Final state
- FINAL_PREVIEW_RELEASE = PASS

No Production Cutover, no main merge, no Final Polish, no knowledge/UI modification.
Awaiting user manual open of the Preview to decide: APPROVE PRODUCTION or FINAL POLISH REQUIRED.
