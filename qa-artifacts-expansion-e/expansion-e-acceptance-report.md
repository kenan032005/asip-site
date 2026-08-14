# Expansion E — Acceptance Report

> Regional Security & Counterterrorism Actors

- **Source branch**: `feature/asip-ppt-entity-expansion-e`
- **Baseline**: `feature/asip-ppt-entity-expansion-d @ 0bb8638`（Expansion D 已验收；数据与 Expansion D acceptance 一致）
- **Research source**: `ASIP-PPT-ENTITY-EXPANSION-E-Authoritative-Content-Pack.md`（唯一事实底稿，未自行联网研究）

---

## 1. 基线确认

- local HEAD = `0bb8638`（feature/asip-ppt-entity-expansion-d）
- remote HEAD = `0bb8638`（一致）
- 无 feature/asip-ppt-entity-expansion-e（新建）
- `data/intelligence/africa/**` 与 Expansion D acceptance 一致（导入前 0 改动）

---

## 2. 候选决议（18 个安全行为体）

| 候选 | 决议 | canonical id |
|---|---|---|
| MNJTF | ENRICH_EXISTING（补 Niger 退出 + 授权更新） | actor-mnjtf |
| G5 Sahel Joint Force | **NEW**（historical，ceased_operations） | actor-g5-sahel-joint-force |
| AES Unified Force | ENRICH_EXISTING（E2→E3） | actor-fu-aes |
| ECOWAS Standby Force | **NEW**（active_framework） | actor-ecowas-standby-force |
| SAMIM | ENRICH_EXISTING（closed_2024） | actor-samim |
| FADM | ENRICH_EXISTING（Chapo/Jane 领导） | actor-fadm |
| RDF / RSF Mozambique | ENRICH_EXISTING（RSF≠RDF 联合构成） | actor-rdf-mozambique |
| TPDF | ENRICH_EXISTING（SAMIM/bilateral 双轨） | actor-tanzania-tpdf |
| Russia Africa Corps | ENRICH_EXISTING（≠Wagner） | actor-africa-corps |
| Wagner Group | ENRICH_EXISTING（Africa Corps 区分） | actor-wagner-group |
| LAAF/LNA | ENRICH_EXISTING（保留稳定 ID，补 LAAF 命名） | actor-lna |
| GNU forces | **UMBRELLA_ONLY**（重分类为 fragmented network） | actor-gnu-forces |
| AFRICOM | **NEW**（external_military_command） | actor-africom |
| MINUSMA | **NEW**（closed_2023，历史联合国任务） | actor-minusma |
| AUSSOM | ENRICH_EXISTING（AMISOM→ATMIS→AUSSOM 沿革） | actor-aussom |
| ATMIS | HISTORICAL_LINEAGE（不建薄节点） | — |
| AMISOM | HISTORICAL_LINEAGE（不建薄节点） | — |

`EXPANSION_E_SECURITY_NAMES_UNRESOLVED = 0`。

---

## 3. 语义门禁（13 项全过）

| 门禁 | 值 |
|---|---|
| MNJTF_NIGER_WITHDRAWAL_PRESERVED | **PASS**（Niger 2025-03 退出，Chad 仅威胁） |
| MNJTF_2026_27_MANDATE | **PASS**（2026-02-01 → 2027-01-31） |
| G5_SAHEL_FALSE_CURRENT_STATUS | **0**（ceased_operations，非 active） |
| AES_FORCE_STRENGTH_TIME_CONFLICT_PRESERVED | **PASS**（5000@2025 vs 6000@2026 ISS） |
| AES_RUSSIAN_COMMAND_MISCLASSIFICATION | **0**（supports，非 command） |
| ECOWAS_260K_ACTIVE_FORCE_FALSE_CLAIM | **0**（26 万概念≠现役军） |
| SAMIM_FALSE_CURRENT_STATUS | **0**（closed_2024，非 active） |
| RSF_RDF_ALIAS_COLLAPSE | **0**（RSF=RDF+RNP，非简单别名） |
| TPDF_SAMIM_BILATERAL_COLLAPSE | **0**（双轨区分） |
| AFRICA_CORPS_WAGNER_ALIAS_COLLAPSE | **0**（非洲军团≠瓦格纳别名） |
| GNU_FAKE_UNIFIED_FORCE_NODE | **0**（重分类 fragmented network，非统一军队） |
| AFRICOM_PARTNER_COMMAND_MISCLASSIFICATION | **0**（不指挥 AUSSOM/SNAF/邦特兰） |
| MINUSMA_FALSE_CURRENT_STATUS | **0**（closed_2023，非 active） |

---

## 4. 实体与关系

### 新建实体（4）
- actor-g5-sahel-joint-force（萨赫勒五国联合部队，ceased_operations，17 章节 / 1809 字）
- actor-ecowas-standby-force（西非共同体待命部队，active_framework，19 章节）
- actor-africom（美国非洲司令部，active，external_military_command）
- actor-minusma（联合国马里稳定团，closed_2023，un_peacekeeping_mission）

### ENRICH（11，全部 encyclopedia_full）
MNJTF（Niger 退出/授权）、FU-AES（兵力时间差/俄支持）、SAMIM、FADM（Chapo/Jane）、RDF-Mozambique（RSF 联合构成）、TPDF（双轨）、Africa Corps（≠Wagner）、Wagner（区分）、LNA（LAAF 命名）、GNU（重分类 fragmented network）、AUSSOM（沿革）。

### 新建关系（10）+ 升级（5）
新建：MNJTF↔JAS、MNJTF↔ISWAP、AES↔JNIM、AES↔IS Sahel、Africa Corps↔AES（supports）、SAMIM↔IS-Moz、AFRICOM↔Shabaab、AFRICOM↔ISIS-Somalia、G5↔JNIM、G5↔IS Sahel。
升级 R3：RDF↔FADM、RDF↔IS-Moz、TPDF↔IS-Moz、LAAF↔ISIS-Libya、Africa Corps↔JNIM。

### 无薄依赖
未为 RNP、EUMAM、南非双边部队、ECOWAS 承诺单位、GNU 统一军队等创建薄节点；AMISOM/ATMIS 未建薄节点，沿革记录在 AUSSOM。

---

## 5. UI Preservation
- 仅 `assets/js/intelligence/africa.js` 的 STATUS_LABELS 新增 4 条状态词汇（ceased_operations / closed_2023 / active_framework / active_operationalizing），数据呈现非 UI 重设计。
- **UI_REGRESSION = 0**（全量回归含全部既有 UI 套件，全 PASS）。

---

## 6. 全量回归（禁 partial runner）
```
TEST_FILES_DISCOVERED = 40   （≥40，含 test_expansion_e_gate.py）
TEST_CASES_DISCOVERED = 7192
TEST_CASES_RUN        = 7192
TEST_CASES_PASSED     = 7192
TEST_CASES_FAILED     = 0
TEST_CASES_SKIPPED    = 0
```
- 自动 discover 全部 test_*.py + 2 EXTRA；未删除/过滤/静默跳过旧测试。
- 同步更新 11 个计数钉测试（104/195/326→108/205/340）+ metrics 白名单 + depth_g downshift 豁免（rel-is-moz-islamic-state2 因 Expansion E §7 R3 填补 gap）。

### Build
`python scripts/build_site.py --no-embed` → **PASS**，340 routes。

### Browser QA
**PASS**：21 页 × 2 视口 = 42 页，**336/336 gates**（console/exceptions/failed/overflow 全 0）。

### Network QA
**PASS**：48/48（MNJTF / AES / FADM / RDF / Africa Corps / AFRICOM / JNIM / ISIS-Mozambique 八焦点）。

---

## 7. Counts（机械统计）

| 指标 | 前（Expansion D） | 后（Expansion E） | Δ |
|---|---|---|---|
| countries | 13 | 13 | 0 |
| entities | 104 | 108 | +4 |
| relationships | 195 | 205 | +10 |
| relation_profiles | 195 | 205 | +10 |
| relation_timelines | 91 | 104 | +13 |
| sources | 267 | 291 | +24 |
| evidence | 386 | 405 | +19 |
| aliases | 467 | 495 | +28 |
| routes | 326 | 340 | +14 |

---

## 8. 最终门禁

| 门禁 | 值 |
|---|---|
| OUT_OF_SCOPE_CHANGED_FILES | 0（data + content/import/supplement 脚本 + QA 脚本 + 测试 gate + 11 计数钉测试 + africa.js 状态词汇） |
| FACT_SEMANTIC_ERRORS | 0 |
| DUPLICATE_CANONICAL_ENTITIES | 0 |
| STANDARD_FINAL_ENTITY_COUNT | 0 |
| EXPANSION_E_SECURITY_NAMES_UNRESOLVED | 0 |
| UI_REGRESSION | 0 |
| FAIL_TOTAL | 0 |
| BUILD | PASS |
| BROWSER_QA | PASS |
| NETWORK_QA | PASS |
| production / gh-pages / preview changed | NO / NO / NO |
| force push | NO |

```
EXPANSION_E_LOCAL_CANDIDATE = PASS
```

已停止。未启动 Global Audit，未部署线上。

---

## 9. QA 工件（qa-artifacts-expansion-e/）

pre-import-dedup-audit.json / candidate-resolution.json / import-plan.json / entity-import-summary.json / historical-status-audit.json / umbrella-resolution-audit.json / relationship-import-summary.json / source-evidence-summary.json / semantic-audit.json / ppt-security-actor-coverage.json / test-results.json / browser-qa-results.json / network-qa-results.json / final-counts.json / expansion-e-acceptance-report.md
