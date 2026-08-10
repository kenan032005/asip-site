# ASIP-PPT-ENTITY-EXPANSION-A — Local Candidate Acceptance Report

**Branch:** `feature/asip-ppt-entity-expansion-a`
**Base HEAD:** `bdf6e4f` (Depth G final acceptance)
**Candidate HEAD:** `ae36014` (pushed; remote SHA verified identical)
**Imported:** 2026-08-09/10
**Model used for import/QA:** DeepSeek V4 Pro (per project rule: one-shot core refactor)
**Result:** `EXPANSION_A_LOCAL_CANDIDATE = PASS`

---

## 0. Gate summary

| Gate | Value | Status |
|---|---|---|
| OUT_OF_SCOPE_CHANGED_FILES | 0 | ✅ |
| FACT_SEMANTIC_ERRORS | 0 | ✅ |
| FAIL_TOTAL (36 tests) | 0 | ✅ |
| BUILD | PASS (274 routes) | ✅ |
| BROWSER_QA | PASS (29 pages, 0 console / 0 failed requests) | ✅ |
| NETWORK_QA | PASS (309 pages / 1788 links / 0 dead) | ✅ |
| production changed | NO | ✅ |
| gh-pages changed | NO (`099fc2f` untouched) | ✅ |
| main changed | NO (`8924416` untouched) | ✅ |
| Depth G started | NO | ✅ |
| force push | NO (plain push, no `-f`) | ✅ |

---

## 1. Final rulings (NEW / ENRICH_EXISTING / ALIAS_ONLY / DEFERRED)

### NEW — 11 formal entities (E3 encyclopedia / standard)
| entity_id | name_zh / name_en | depth | sections | chars |
|---|---|---|---|---|
| actor-al-shabaab | 索马里青年党 / Al-Shabaab | encyclopedia_full | 24 | 3682 |
| actor-isis-somalia | 伊斯兰国索马里省 / ISIS-Somalia | encyclopedia_full | 19 | 2872 |
| actor-al-karrar-office | 卡拉尔办公室 / al-Karrar Office | encyclopedia_full | 17 | 2093 |
| actor-adf-isis-ca | 民主同盟军（伊斯兰国中非省）/ ADF / ISIS-CA | encyclopedia_full | 20 | 2539 |
| actor-sim | 苏丹伊斯兰运动 / Sudanese Islamic Movement | encyclopedia_full | 16 | 2518 |
| actor-bbmb | 巴拉·本·马利克旅 / Al-Baraa Bin Malik Brigade | encyclopedia_full | 17 | 2485 |
| person-ahmed-diriye | 艾哈迈德·迪里耶 / Ahmed Diriye | encyclopedia_full | 15 | 1909 |
| person-abd-al-qadir-mumin | 阿卜杜勒·卡迪尔·穆明 / Abd al-Qadir Mu'min | encyclopedia_full | 15 | 2045 |
| person-abdirahman-fahiye | 阿卜迪拉赫曼·法希耶·伊塞 / Abdirahman Fahiye Isse | standard | 11 | 1163 |
| person-seka-musa-baluku | 塞卡·穆萨·巴卢库 / Seka Musa Baluku | encyclopedia_full | 13 | 2077 |
| person-ali-ahmed-karti | 阿里·艾哈迈德·卡尔提 / Ali Ahmed Karti | encyclopedia_full | 13 | 2101 |

All pages meet the test contract floors (encyclopedia_full ≥ 8 sections / ≥ 1800 chars; standard ≥ 5 / ≥ 900).

### ENRICH_EXISTING — 2 entities
- `actor-ansaru` — name/alias set expanded (Ansarul Muslimina Fi Biladis Sudan, JAMBS, Vanguards…), status → `active_but_leadership_disrupted`, fixed-strength myth (2,000–3,000) removed, 10 sections refreshed, watch indicators extended.
- `actor-lakurawa` — dual positions preserved (NigSAC JNIM designation + ACLED 2026 IS-Sahel reading), status → `active_identity_contested`, `network_links` section rendered (new SECTION_LABELS key), ASIP analysis stored as analysis (non-verified).

### ALIAS_ONLY — 1 modeling case
- ADF / ISIS-CA / ISIS-DRC / ISCAP / Allied Democratic Forces → single canonical `actor-adf-isis-ca`; all historical names kept as aliases + `historical_names`. No `actor-adf`, `actor-isis-drc`, `actor-iscap` nodes exist. Confirmed by audit.

### DEFERRED — to Content Pack 2 (recorded in `unresolved-supporting-entity-dependencies.json`)
- 9 deferred edges: Ansaru↔Katiba Hanifa (§15 #14, no evidence), BBMB↔IRGC (#21, missing entity), Abu Zaid Talha→BBMB (#22 + §14 DEFER), Al-Shabaab↔AUSSOM / ↔Somali SF, ISIS-Somalia↔Puntland SF, ADF↔FARDC / ↔UPDF / ↔MONUSCO (supporting entities out of scope).
- 5 deferred entities: Mahad Karate, Abdiweli Mohamed Yusuf, Meddie Nkalubo, Abu Zaid Talha al-Misbah, IRGC.

---

## 2. Relationships

14 NEW + 5 ENRICHED. Final counts: 164 relationships, 164 relation profiles, 65 timelines.

### Five mandatory deep dossiers (§16) — all R3 with timelines (≥3 items)
| Dossier | relation_id | type | timeline |
|---|---|---|---|
| A. Al-Shabaab ↔ ISIS-Somalia | rel-expa-shabaab-isis-somalia-rivalry | fought_against | 6 |
| B. ADF/ISIS-CA ↔ ISIS | rel-expa-adf-isis-branch | affiliated_with (2019 recognition) | 4 |
| C. Ansaru ↔ JAS | rel-d1-ansaru-jas-split (ENRICH) | split_from (2012-01) | 4 |
| D-1. Lakurawa ↔ IS-Sahel | rel-d1-lakurawa-is-sahel-network (ENRICH) | part_of_network, disputed | 3 |
| D-2. Lakurawa ↔ JNIM | rel-d1-lakurawa-jnim-cooperation (ENRICH) | cooperates_with, disputed | 3 |
| E. SIM ↔ BBMB | rel-expa-sim-bbmb-linked | part_of_network (Linked To) | 4 |

- D records are mutually aware via uncertainty notes; both positions retained, no branch_of asserted (audited: 0 branch_of edges).
- #4 ISIS-Somalia→ISIS (R3) preserves both dates: 2015 pledge (time_start) + 2018 branch recognition (profile/timeline).
- Each R3 dossier carries formation_background / initial_relationship / evolution_stages / causes / key_turning_points / impact_on_security / why_it_matters / uncertainties / asip_analysis / watch_indicators (audited field-by-field).

---

## 3. Factual semantics (§17 / §19) — FACT_SEMANTIC_ERRORS = 0

- BBMB "upwards of 20,000 fighters" kept attributed to U.S. Treasury; NOT transferred to SIM/SMB (audited).
- Ansaru fixed strength 2,000–3,000 removed; current membership marked unknown.
- Boko Haram subordinate-to-ISIS claim NOT imported.
- ISGS / EIGS / ISSP not created as separate current entities.
- ADF and ISIS-CA not split into two parallel current orgs.
- Lakurawa JNIM affiliation kept as Nigerian official position (contested), not as uncontested branch.
- EU/ACLED/NCTC institutional judgments keep attribution (EU for Karti/SIM; ACLED for IS-Sahel; Treasury for financial/fighter figures).
- ISIS-Somalia 700–1,500 stored as dated estimate (2025-02), not timeless.
- No unverified Western-support allegations; no cross-group cooperation claims without independent evidence.
- Force estimates for all 6 new orgs carry estimate_date + source_ids + estimate_text.

## 4. Sources / evidence

- Sources: 190 → 202 (+12 `expa-*` registry entries; dedupe verified 0 collisions).
- Evidence: 315 → 341 (+26 `ev-expa-r*` relation evidence; all reference existing sources/entities/relations — 0 dangling).
- Evidence verified-ratio 220/341 = 0.645 < 0.80 (gate).
- alias_index rebuilt: 353 entries (new aliases incl. ISS, ADF, ISIS-CA, ISCAP, JAMBS, Abu Ubaidah…).
- graph_index rebuilt: nodes == 83 entity set, relationship_ids == 164.

## 5. Final counts

countries=13, entities=83, relationships=164, relation_profiles=164, relation_timelines=65, sources=202, evidence=341, alias=353, routes=274.

## 6. Regression / build / QA evidence

- `scripts/qa/expansion_a_regression.py` → tests_run=36, passed=36, FAIL_TOTAL=0 (`qa-artifacts-expansion-a/test-results.json`).
- `scripts/build_site.py --no-embed` → PASS; `africa data OK: entities=83 relations=164 …`; 274 routes → dist.
- Browser QA (`expansion_a_browser_qa.js`, Edge headless CDP, 1366×900, cache disabled): 29 pages, 0 console errors, 0 runtime exceptions, 0 failed requests, 0 broken anchors, 0 overflow, gate=PASS (`browser-qa.json`).
- Network QA (`expansion_a_link_qa.js`): 309 pages / 1788 links / 0 dead, gate=PASS (`link-qa.json`). The `../` breadcrumb links are **KNOWN_BASELINE_BEHAVIOR / NON_BLOCKING** — pre-existing generator output (entity/ relation/ dirs carry no index.html; served by SPA fallback); not introduced by Expansion A and not modified.

## 7. Git diff / commits (pushed, no force)

```
ae36014 chore(expansion-a): drop stray commit-message temp file from QA artifacts
9669a89 qa(expansion-a): regression runner, browser/link QA tooling, scope audit and acceptance artifacts
0b853a2 test(expansion-a): raise count pins to post-Expansion A scale (83/164/274)
c3522ae data(expansion-a): merge 12 knowledge data files, rebuild alias/graph index and catalog metrics
911a278 feat(expansion-a): source-of-truth content modules and import master script
bdf6e4f (base) docs: DEPTH G final acceptance report
```
- Remote verified via `git ls-remote`: `feature/asip-ppt-entity-expansion-a` = `ae36014797…` == local HEAD.
- Scope audit: OUT_OF_SCOPE_CHANGED_FILES = 0; `qa-artifacts-i3b-fix1c/local-path-scan.json` diff = ZERO (regression runner restores it post-run); production/gh-pages diff = none.

---

**Verdict:** All required gates hold → **EXPANSION_A_LOCAL_CANDIDATE = PASS**. Stopped. Expansion B not started.
