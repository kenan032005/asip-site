# Import Validation Command List (existing commands; no execution here)

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
