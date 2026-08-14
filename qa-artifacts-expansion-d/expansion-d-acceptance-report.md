# Expansion D — Acceptance Report

> Remaining Current / Contested PPT Entities（Closing Expansion D）

- **Source branch**: `feature/asip-ppt-entity-expansion-d`
- **Baseline**: `feature/asip-ppt-entity-expansion-c @ b8e8c49`（含 Expansion C + UI Polish Pack 1 + UI Hard Fix A；数据与 Expansion C closure 一致，见 pre-import-dedup-audit）
- **Research source**: `ASIP-PPT-ENTITY-EXPANSION-D-Authoritative-Content-Pack.md`（唯一事实底稿，WorkBuddy 未自行联网研究）

---

## 1. 基线确认

- 本地 branch HEAD = `b8e8c49`（feature/asip-ppt-entity-expansion-c）
- remote HEAD = `b8e8c49`（一致）
- `1946c19`（UI Polish Pack 1）之后存在 `b8e8c49`（UI Hard Fix A，已验收）。**采用最新 accepted source HEAD `b8e8c49`** 作为基线建分支，未从旧 HEAD 建分支。
- `data/intelligence/africa/**` 与 Expansion C closure（facff39）一致（导入前 0 改动）。

---

## 2. 候选决议（Candidate Resolution）

| PPT / research candidate | 决议 | canonical id |
|---|---|---|
| ISIS-Sinai / Islamic State-Sinai Province | **NEW_CANONICAL_ENTITY** | `actor-isis-sinai` |
| Ansar Bayt al-Maqdis (ABM) | **HISTORICAL_PHASE**（ISIS-Sinai 历史名） | `actor-isis-sinai` |
| Ansaroul Islam / Ansarul Islam | **ENRICH_EXISTING**（E2→E3） | `actor-ansarul-islam` |
| Katiba Hanifa | **ENRICH_EXISTING**（对齐状态/事实） | `actor-katiba-hanifa` |
| Niger FPL | **NON_TERRORIST_ARMED_ACTOR**（新建，insurgent_group） | `actor-niger-fpl` |
| FLA | **ENRICH_EXISTING**（对齐 political_movement 分类） | `actor-fla` |
| Lions of the Caliphate | **DEFERRED_CELL_EVENT**（无 cell 类型，PPT_NAME_RESOLVED=YES） | — |
| Nasr Jihad Resistance Movement | **INSUFFICIENT_EVIDENCE_DO_NOT_CREATE** | — |
| Yusuf Ghazi group | **INSUFFICIENT_EVIDENCE_DO_NOT_CREATE** | — |

`EXPANSION_D_PPT_NAMES_UNRESOLVED = 0`（9 个名字全部以合格 resolution 处理，明确排除也是合格 resolution）。

---

## 3. 语义门禁（全部通过）

| 门禁 | 值 |
|---|---|
| ABM_DUPLICATE_CURRENT_NODE | **0**（无 actor-ansar-bayt-al-maqdis 节点；ABM 在 ISIS-Sinai aliases + historical_names） |
| ANSAROUL_WHOLE_GROUP_ISIS_MISCLASSIFICATION | **0**（primary_type=organization，constituent_of JNIM，非 ISIS/IS Sahel） |
| KATIBA_HANIFA_JNIM_LINK | **PASS**（constituent_of → actor-jnim） |
| FPL_TERRORIST_MISCLASSIFICATION | **0**（insurgent_group，非 terrorist_group） |
| FLA_TERRORIST_MISCLASSIFICATION | **0**（political_movement，非 terrorist/jihadist） |
| FLA_JNIM_AFFILIATION_MISCLASSIFICATION | **0**（cooperates_with + current_status=tactical_coordination，非 affiliated/constituent/pledged） |
| LIONS_FAKE_PROVINCE | **0**（无 cell/省节点） |
| NASR_JIHAD_NODE_CREATED | **0** |
| YUSUF_GHAZI_NODE_CREATED | **0** |
| UNSUPPORTED_US_BANCROFT_EDGE | **0** |
| EXPANSION_D_PPT_NAMES_UNRESOLVED | **0** |
| FACT_SEMANTIC_ERRORS | **0** |

---

## 4. 实体与关系写入

### 新建实体（2）
- `actor-isis-sinai`（伊斯兰国西奈省，terrorist_group，active_but_severely_degraded，19 章节 / 3184 字）
- `actor-niger-fpl`（尼日尔爱国解放阵线，insurgent_group，active_anti_junta_rebellion，18 章节 / 2180 字）

### ENRICH（3，全部升/保持 encyclopedia_full）
- `actor-ansarul-islam`：E2→E3（17 章节 / 2819 字），补齐 Ibrahim/Jafar Dicko、Soum/Al-Irchad、Nassoumbou、ISGS 少数成员叛变、渐进并入等锁定事实
- `actor-katiba-hanifa`：状态 → `active_and_expanding_cross_border`，补 W-Arly-Pendjari、2025-10 尼日利亚首次行动、IED 等（18 章节 / 2078 字）
- `actor-fla`：primary_type → `political_movement`，补 2026 战术协调框架（15 章节 / 2236 字）

### 新建关系（3）+ 升级/更新
- 新建 `rel-expd-isis-sinai-isis`（pledged_allegiance_to，R3，7 timeline 节点，2218 字）
- 新建 `rel-expd-ansaroul-katiba-macina`（historically_associated_with，R2，4 timeline 节点）
- 新建 `rel-expd-fpl-niger-operates`（operates_in + 富反军政府档案，R3，5 timeline 节点）
- 升级 `rel-d1-ansarul-jnim-constituent` R2→R3（7 timeline 节点）
- 更新 `rel-d1-fla-jnim-cooperation`：current_status → `tactical_coordination`（cooperates_with 保持不变），补 2024-11/2026-04/2026-07 timeline 与独立目标/持久性存疑强调

所有核心 R3 关系正文 ≥800 字、timeline ≥4 节点；新建/ENRICH 实体 ≥14 章节、≥1800 字、encyclopedia_full。**STANDARD_FINAL_ENTITY_COUNT = 0**。

### 无薄依赖
未为 Egypt/Morocco/Togo/Mahamoud Sallah 等创建薄节点；Jafar Dicko、Ibrahim Dicko、Abu Hanifa、Amadou Koufa 等已有 person 节点复用；Egypt/Togo/Morocco 仅在正文叙述。

---

## 5. UI Preservation

- UI 文件零改动，仅 `assets/js/intelligence/africa.js` 的 `STATUS_LABELS` 新增 4 条**状态词汇映射**（active_but_severely_degraded / active_anti_junta_rebellion / active_and_expanding_cross_border / tactical_coordination）——这是数据呈现词汇，非 UI 重设计。
- 未改动 homepage / entity / relation / TOC / key-facts / 语义卡 / 不确定卡 / 正文互链 / 来源顺序 / 时间线 / network / 响应式 / 列表过滤。
- **UI_REGRESSION = 0**（全量回归含全部既有 UI 套件，全部 PASS）。

---

## 6. 质量与机械输出

### 全量回归（禁 partial runner）
```
TEST_FILES_DISCOVERED = 39   （≥38，含新增 test_expansion_d_gate.py）
TEST_CASES_DISCOVERED = 6928
TEST_CASES_RUN        = 6928
TEST_CASES_PASSED     = 6928
TEST_CASES_FAILED     = 0
TEST_CASES_SKIPPED    = 0
```
- 自动 discover 全部 `test_*.py` + 2 EXTRA（test_no_local_paths / test_repository_integrity）
- 未删除/未过滤旧测试；新增 Expansion D 专项 gate（24 检查）
- 同步更新 11 个计数钉测试（102→104、192→195、321→326、181→195）与 metrics 生成器白名单（与 Expansion C closure 修改 12 计数钉测试同理）

### Build
`python scripts/build_site.py --no-embed` → **PASS**，326 routes。

### Browser QA（本地 dist，desktop 1440×900 + mobile 390×844）
**PASS**：10 页 × 2 视口 = 20 页，170/170 gates（console/exceptions/failed/overflow 全 0）；4 个 excluded 对象（ABM / Lions / Nasr / Yusuf）全部 404 无错误路由。

### Network QA
**PASS**：30/30（JNIM / Ansaroul / Katiba Hanifa / ISIS-Sinai / FLA 五焦点均渲染中心标签 + 可见统计）。

### 别名/引用完整性
- 别名解析：ansaroul islam / wilayat sinai / ansar bayt al-maqdis / fpl / front patriotique de libération / hanifa brigade / isis-sinai province 等全部解析到正确 canonical id
- 无 orphan 实体/关系；所有 source/evidence 引用可解析；无重复 canonical 实体（id/slug 唯一）

---

## 7. Counts（机械统计，前后对比）

| 指标 | 前（Expansion C closure） | 后（Expansion D） | Δ |
|---|---|---|---|
| countries | 13 | 13 | 0 |
| entities | 102 | 104 | +2 |
| relationships | 192 | 195 | +3 |
| relation_profiles | 192 | 195 | +3 |
| relation_timelines | 88 | 91 | +3 |
| sources | 246 | 267 | +21 |
| evidence | 380 | 386 | +6 |
| aliases | 443 | 467 | +24 |
| routes | 321 | 326 | +5 |

---

## 8. 最终门禁

| 门禁 | 值 |
|---|---|
| OUT_OF_SCOPE_CHANGED_FILES | 0（仅 data + 4 个 import/content 脚本 + 3 个 QA 脚本 + 1 个测试 gate + 11 计数钉测试 + africa.js 状态词汇 + QA 工件） |
| FACT_SEMANTIC_ERRORS | 0 |
| DUPLICATE_CANONICAL_ENTITIES | 0 |
| STANDARD_FINAL_ENTITY_COUNT | 0 |
| EXPANSION_D_PPT_NAMES_UNRESOLVED | 0 |
| FAIL_TOTAL | 0 |
| BUILD | PASS |
| BROWSER_QA | PASS |
| NETWORK_QA | PASS |
| production / gh-pages / preview changed | NO / NO / NO |
| force push | NO |

```
EXPANSION_D_LOCAL_CANDIDATE = PASS
```

已停止。未启动 Expansion E，未切 production，未部署 gh-pages/preview。

---

## 9. QA 工件（qa-artifacts-expansion-d/）

pre-import-dedup-audit.json / candidate-resolution.json / import-plan.json / entity-import-summary.json / excluded-name-audit.json / relationship-import-summary.json / source-evidence-summary.json / semantic-audit.json / ppt-coverage-delta.json / test-results.json / browser-qa-results.json / network-qa-results.json / final-counts.json / expansion-d-acceptance-report.md
