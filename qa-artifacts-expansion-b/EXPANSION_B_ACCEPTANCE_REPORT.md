# ASIP-PPT-ENTITY-EXPANSION-B — Local Candidate Acceptance Report

**Branch:** `feature/asip-ppt-entity-expansion-b`
**Base HEAD:** `ae36014` (Expansion A accepted candidate, as instructed)
**Imported:** 2026-08-10
**Result:** `EXPANSION_B_LOCAL_CANDIDATE = PASS`

---

## 0. Gate summary

| Gate | Value | Status |
|---|---|---|
| OUT_OF_SCOPE_CHANGED_FILES | 0 | ✅ |
| FACT_SEMANTIC_ERRORS | 0 | ✅ |
| STANDARD_FINAL_ENTITY_COUNT (Expansion B scope) | 0 | ✅ |
| FAIL_TOTAL (37 tests incl. new gate test) | 0 | ✅ |
| BUILD | PASS (302 routes) | ✅ |
| BROWSER_QA | PASS (31 pages, 0 console / 0 failed requests) | ✅ |
| NETWORK_QA | PASS (337 pages / 1956 links / 0 dead) | ✅ |
| production changed | NO | ✅ |
| gh-pages changed | NO | ✅ |
| Depth G started / UI-V2 started | NO | ✅ |
| force push | NO | ✅ |

---

## 1. Expansion A carry-over (first priority)

| Entity | Ruling | Result |
|---|---|---|
| person-abdirahman-fahiye | ENRICH_EXISTING upgrade | standard/E2 → **encyclopedia_full/E3**; 15 sections, 2233 chars; new sections biography/sanctions_legal/events/influence; sources added (OFAC 2022-11-01, Treasury jy1066, UN S/2026/44); 1985 Bosaso birth, 2017 Bosaso suicide bombing coordination, 2021 emir reporting to Mu'min, 2026 UN operational-leadership role all recorded with attribution |
| actor-ansaru | ENRICH_EXISTING (confirmed) | already encyclopedia_full/E3 (23 secs / 2501 chars) — no depth gap |
| actor-lakurawa | ENRICH_EXISTING (confirmed) | already encyclopedia_full/E3 (18 secs / 2157 chars) — no depth gap |

`STANDARD_FINAL_ENTITY_COUNT = 0` for every Expansion-B-touched entity (11 new + 3 carry-over).

## 2. New entities — dedup rulings (all NEW, stable-ID verified)

| Candidate | Ruling | Evidence |
|---|---|---|
| AUSSOM | NEW | no AMISOM/ATMIS/AUSSOM node; predecessor chain in history text |
| Somali National Armed Forces / SNAF | NEW | no Somali army node; SNA kept as alias |
| Puntland Security Forces | NEW | umbrella-label modeling (UN reporting), not a unified legal force |
| FARDC | NEW | no DRC armed forces node |
| UPDF | NEW | no Uganda armed forces node |
| MONUSCO | NEW | MONUC kept as historical name |
| IRGC | NEW | no Iran/IRGC node in Africa graph (Expansion A deferred) |
| Mahad Karate | NEW | finance+Amniyat chief; State SDGT 2015-04-10 (attributed) |
| Abdiweli Mohamed Yusuf | NEW | ISS finance office head; OFAC SDGT 2023-07-27 |
| Meddie/Mohamed Ali Nkalubo | NEW | UN-listed ADF senior leader (2024-02-20), attributed narrative |
| Abu Zaid Talha al-Misbah | NEW | EU 2026/251 commander listing (Expansion A DEFER resolved with EU source) |

All 11 new entities are `encyclopedia_full` with thickness floors met (orgs ≥14 sections / ≥1800 chars; persons ≥12 / ≥1500; all verified above the floors: orgs 2125–3573 chars, persons 1721–1837).

## 3. Relationships (17 new)

- 8 core R3 dossiers with ≥3 timeline nodes each and full field sets: Al-Shabaab↔AUSSOM, Al-Shabaab↔SNAF, AUSSOM↔SNAF (incl. security-transfer), ISIS-Somalia↔Puntland (Operation Hilaac), ADF↔FARDC, ADF↔UPDF, FARDC↔UPDF (Operation Shujaa), BBMB↔IRGC (attributed-support).
- 9 R2 relations: Karate→Al-Shabaab, Yusuf→ISIS-Somalia, Yusuf→Mu'min (reporting, affiliated_with), Yusuf→Fahiye (reporting, affiliated_with), MONUSCO→ADF (hostile_to with civilian-protection framing), MONUSCO↔FARDC (cooperates_with), Nkalubo→ADF (led_by), Talha→BBMB (led_by), Talha↔SAF (allied_with, EU attribution).
- Ontology: **no new relationship types**; all mapped to the existing 18-type registry.
- MONUSCO-ADF explicitly framed as peacekeeping civilian-protection countering, not belligerent hostility; BBMB-IRGC explicitly "U.S. Treasury states", no command/control inferred; UPDF/FARDC operational claims remain attributed to UPDF; Puntland modeled as a multi-component umbrella label per UN reporting.

## 4. Sources / evidence

- Sources: 202 → **221** (+19 `expb-*`; 11 existing IDs reused, no duplicates).
- Evidence: 341 → **358** (+17 `ev-expb-r*` relation evidence; verified ratio 0.64 < 0.80).
- 0 dangling source references across entities/relations/profiles/evidence.
- alias_index rebuilt: **393** entries; graph_index nodes == 94 entity set, relationship_ids == 181.

## 5. Country dependencies (pack §15)

Somalia / DRC / Uganda country nodes deliberately NOT created. Recorded in
`qa-artifacts-expansion-b/country-dependency-summary.json` as
**EXPANSION_B_COUNTRY_DEPENDENCY** for a later dedicated pack.

## 6. Final counts

countries=13, entities=94, relationships=181, relation_profiles=181, relation_timelines=73, sources=221, evidence=358, alias=393, routes=302.

## 7. QA evidence

- `scripts/qa/expansion_b_regression.py` → tests_run=37, passed=37, FAIL_TOTAL=0 (incl. new `test_expansion_b_gate.py`, PASS=113).
- `scripts/build_site.py --no-embed` → PASS; `africa data OK: entities=94 relations=181 …`; 302 routes.
- Browser QA (Edge headless CDP, 1366×900, cache disabled): 31 pages, 0 console errors, 0 runtime exceptions, 0 failed requests, 0 broken anchors, 0 overflow → gate PASS.
- Network QA: 337 pages / 1956 links / 0 dead links → gate PASS.
- Scope audit: OUT_OF_SCOPE_CHANGED_FILES = 0; `qa-artifacts-i3b-fix1c/local-path-scan.json` diff = ZERO; production/gh-pages diff = none.
- Final acceptance audit: PASS=162 / FAIL=0 / FACT_SEMANTIC_ERRORS=0.

## 8. Git / delivery

Branch `feature/asip-ppt-entity-expansion-b` based on `ae36014`, pushed without
force (remote SHA verified). No production deployment, no gh-pages change,
no UI/UX V2 started.

**Verdict:** All gates hold → **EXPANSION_B_LOCAL_CANDIDATE = PASS**. Stopped.
