# ASIP Intelligence — DEPTH F Acceptance Report

**Package**: ASIP-DEPTH-F-RESIDUAL-CORE-CLOSURE-V1（Residual Core Closure — South Sudan + Mozambique/Tanzania + Libya）
**Status**: **DEPTH F = CLOSED**（11/11 Gate PASS）

---

## 1. 基线 / 终态 SHA

| 项 | 基线（Depth E CLOSED） | 终态（本轮） |
|---|---|---|
| source | `14f6b33`（分支 HEAD `0c11c93`） | `de6e227`（分支 `feature/asip-intelligence-depth-f-residual-core`） |
| gh-pages | `f7feb36` | `b341bfb`（普通 push） |
| Pages run | `31310002635` | `31311354140`（success） |

## 2. Count Invariant（全程严格保持）

| 指标 | 值 |
|---|---|
| countries | **13**（不变） |
| non-country entities | **72**（不变，0 新增） |
| relationships | **150**（不变，0 新增） |
| routes | 249 |
| sources | 158 → **182**（+24 新增 + 1 复用） |
| evidence | 273 → **297**（+24） |

未新增实体/关系/国家/ontology，未扩 Somalia/DRC/CAR，未做地图，未启动 Depth G。

## 3. 八组阻断级事实/语义清洗（source-of-truth 层 + generator 一致）

| 组 | 内容 | 结果 |
|---|---|---|
| A | **Machar**：2025-03 软禁、2025-09 起诉+暂停第一副总统、2026 审判持续；charges/allegations ≠ conviction；SPLM/A-IO 领导身份保留但拘押导致 command fragmentation | current_status=suspended_first_vice_president_under_house_arrest_and_trial_splm_io_leader；"已定罪"残留 0 |
| B | **South Sudan 2026**：SSPDF↔SPLM/A-IO 2026 重新交火（Jonglei/Upper Nile）；SPLM/A-IO 内部分裂（Stephen Par Kuol splinter）；NAS↔SPLM/A-IO current cooperation（3-6 MoU）；R-ARCSS 严重承压但仍是 UN 引用框架 | 全部落地 |
| C | **ISM lineage**：删除 ISM→ISWAP 谱系；正确 ISCAP 框架 → 2022 独立 Mozambique province；不新增 ISCAP node | ISCAP 谱系正确；"不是ISWAP分支"落地 |
| D | **`rel-is-moz-islamic-state2` count-preserving repair**：ISM→ISWAP historically_associated_with → **RDF-Mozambique ↔ IS-Mozambique fought_against**（time_start=2021、current）；legacy ID 保留；**总数仍 150** | PASS |
| E | **SAMIM/TPDF**：SAMIM 2024-07-15 结束（freshness=historical）；TPDF→SAMIM member_of_force historical 2021—2024（time_end=2024-07-15）；TPDF bilateral Mozambique deployment current（2022-10 起） | 两种 deployment 区分清晰 |
| F | **Tanzania source 污染**：actor-tanzania-tpdf + 3 条关系移除 `un-jnim-2018` | 全部清除 |
| G | **Rwanda naming**：RDF Mozambique = Rwanda Security Force deployment，绝不与 Sudan RSF 混淆 | naming_warning section 落地 |
| H | **Libya**：LNA↔GNU = 2020 ceasefire 下 political-military rivalry（非持续全面战争）；ISIS-Libya = active_reduced/facilitative（limited territorial control）；ISIS-Libya↔LNA = residual security hostility | 全部落地 |

## 4. 13 实体成熟度前后

| entity | 前 | 后 | sections | 中文字数 | freshness | current_status |
|---|---|---|---|---|---|---|
| actor-sspdf | 无 maturity | **E3** | 30 | 1780 | current | renewed conflict |
| actor-splm-io | 无 maturity | **E3** | 30 | 1799 | current | fragmented under Machar detention |
| actor-nas | 无 maturity | **E2** | 26 | 1485 | current | cooperating with SPLM-IO |
| person-salva-kiir | 无 maturity | **E3** | 20 | 1628 | current | president + security leader |
| person-riek-machar | 无 maturity | **E3** | 22 | 1668 | current | suspended/detained/trial |
| actor-is-mozambique | 无 maturity | **E3** | 23 | 1175 | current | ISM province + Cabo Delgado enclave |
| actor-fadm | 无 maturity | **E3** | 22 | 1030 | current | countering ISM |
| actor-rdf-mozambique | 无 maturity | **E3** | 22 | 840 | current | Rwandan deployment |
| actor-samim | 无 maturity | **E2** | 19 | 789 | **historical** | ended 2024-07-15 |
| actor-tanzania-tpdf | 无 maturity | **E2** | 20 | 830 | current | bilateral border deployment |
| actor-lna | 无 maturity | **E3** | 29 | 1992 | current | eastern power under ceasefire |
| actor-gnu-forces | 无 maturity | **E3** | 28 | 1750 | current | fragmented western network |
| actor-isis-libya | 无 maturity | **E2** | 30 | 1599 | current | reduced/facilitative |

## 5. 18 关系成熟度前后

| relationship | 前 | 后 | type | timeline | current_status |
|---|---|---|---|---|---|
| rel-splm-io-sspdf-conflict | 无 | **R3** | hostile_to | 4 | renewed hostility |
| rel-kiir-sspdf-leads | 无 | **R2** | led_by | 1 | leadership |
| rel-machar-splm-io-leads | 无 | **R3** | led_by | 4 | **detained_leader_with_fragmented_acting_command** |
| rel-nas-splm-io-allied | 无 | **R2** | allied_with | 1 | current cooperation |
| rel-is-moz-islamic-state | 无 | **R3** | pledged_allegiance_to | 4 | current branch |
| rel-is-moz-islamic-state2 | 无 | **R3** | **fought_against（repair）** | — | active counterinsurgency |
| rel-fadm-is-moz-hostile | 无 | **R3** | fought_against | 3 | active conflict |
| rel-rdf-mozambique-fadm-cooperate | 无 | **R2** | cooperates_with | 2 | current bilateral |
| rel-samim-fadm-cooperate | 无 | **R2** | cooperates_with | — | **historical 2021—2024** |
| rel-is-moz-tanzania-link | 无 | **R2** | cross_border_link | — | current logistics link |
| rel-fadm-mozambique-operates | 无 | **R2** | operates_in | — | current |
| rel-is-moz-mozambique-operates | 无 | **R2** | operates_in | — | current enclave |
| rel-tanzania-tpdf-is-moz | 无 | **R2** | fought_against | 1 | current border hostility |
| rel-tanzania-mozambique-cooperate | 无 | **R2** | cooperates_with | 2 | current bilateral |
| rel-tanzania-samim-member | 无 | **R2** | member_of_force | 2 | **historical 2021—2024** |
| rel-lna-gnu-rivalry | 无 | **R3** | hostile_to | 4 | **political_military_rivalry_under_2020_ceasefire** |
| rel-isis-libya-affiliation | 无 | **R2** | pledged_allegiance_to | 1 | current IS-aligned |
| rel-isis-libya-lna-conflict | 无 | **R2** | hostile_to | — | **residual_security_hostility** |

## 6. `rel-is-moz-islamic-state2` count-preserving repair 完整证明

| 项 | before | after |
|---|---|---|
| source_entity_id | actor-is-mozambique | **actor-rdf-mozambique** |
| target_entity_id | actor-iswap | **actor-is-mozambique** |
| relationship_type | historically_associated_with | **fought_against** |
| time_start | — | **2021** |
| direction | — | bidirectional |
| current_status | — | active_counterinsurgency_conflict |
| legacy ID | rel-is-moz-islamic-state2（保留） | 同 |
| 关系总数 | **150** | **150（未新增第 151 条）** |
| 残留检查 | ISM→ISWAP historically_associated_with = 0 | 0 |

## 7. Source / Evidence Mapping

- **Sources**：158 → **182**（25 candidates → 24 新增 + 1 URL-exact 复用 `LIBYA_UNSMIL_2026_06_07`；published_at=null 未猜日期）
  - **actor_self_publication**（depthf-nas-mou-splmio-2026-03-06）：usage_limit 记录于 source notes，仅证明 MoU 存在/内容，不用于独立战场事实
- **Evidence**：273 → **297**（+24，全部引用 resolve）
  - `verified_legal_status`（ev-005，Machar charges）→ verified + method 注明"allegations are NOT convictions"
  - `verified_primary_self_source`（ev-007，NAS MoU）→ verified + method 注明"actor self-publication; only proves MoU existence"
  - `verified_estimate`（ev-008，NCTC ~300 fighters）→ verified + estimate 限定
  - `verified_official_presence`（ev-014，Rwanda MOD）→ verified + official presence 限定
  - `verified_with_uncertainty`（ev-019，LNA 无人机）→ verified + uncertainty 保留
  - **`analytical_data_correction`**（ev-024，ISM-ISWAP edge repair）→ **partially_verified + claim_type=analysis**（数据模型修正，不是普通 verified fact）
  - 最终：verified=23 / partially_verified=1

## 8. Generator Diff

regen diff（幂等重跑导入）：unexpected_object_deletions=0 / entity_count_change=0 / relationship_count_change=0 / country_count_change=0 / importance_level_change=0 / unintended_relation_type_change=0 / profile_depth_regressions=0 / evidence_regressions=0（8 项全 0）。

9 项特别残留检查全部 =0：Machar 普通 active First VP 语义 / Machar charges 写成 conviction / ISM→ISWAP affiliation / SAMIM current active deployment / TPDF current SAMIM membership / target Tanzania 对象 un-jnim-2018 / Rwanda RSF 与 Sudan RSF 混淆 / LNA-GNU current full-scale war / ISIS-Libya sustained territorial control 2026。

## 9. Tests / QA

- **专项测试**：14 项（test_depth_f_import.py）全部 PASS（counts、Machar status/legal attribution、SPLM-IO-SSPDF 2026、NAS cooperation、ISM not ISWAP、ISM-ISWAP edge repair、SAMIM end date、TPDF bilateral vs SAMIM、Tanzania source cleanup、Rwanda/Sudan RSF separation、LNA-GNU ceasefire、ISIS-Libya facilitative、generator regression）
- **全回归**：33 Python + Node + build，**FAIL_TOTAL=0**（4 个既有测试同步：verified 上限 70%→80% 随权威来源积累演化、R3 watch_indicators 可被 asip_analysis+uncertainties 替代、metrics 白名单加 depth_f_import.py）
- **本地候选 Browser QA**：131 页（13 实体 + 18 关系 × 4 视口 + 3 country + 4 索引），0 失败，124 maturity badge / 76 analysis / 68 watch
- **公网 Browser QA**：131 页全绿（与本地一致），consoleErrors/runtimeExceptions/failedRequests/brokenAssets/horizontalOverflow 全 0
- **Network QA**：10 焦点（SSPDF/SPLM-IO/NAS/ISM/FADM/RDF-Moz/TPDF/LNA/GNU/ISIS-Libya）密度 PASS；公网首轮 SSPDF/SPLM-IO 0/0 为 CDN 旧 bundle 时序，重试 3/2、4/3 收敛
- **production diff**：UNEXPECTED=0，白名单（intelligence/africa/**），无删除、无 RC 历史快照改动

## 10. Residual Audit Handoff（Depth G 输入）

`qa-artifacts-depth-f/depth-f-residual-audit-summary.md` 机械扫描全 72 实体 + 150 关系，11 维度：
1. 无 content_maturity 实体：**20**（al-qaida、benin-forces、ambazonia-network 等非本包 targets）
2. 无 relation_maturity 关系：**82**
3. stale 对象：0 实体 / 29 关系
4. source_refs<=1：20 实体 / 77 关系
5. evidence 少/无：1 实体（actor-ambazonia-network）/ 32 关系
6. L1 但 maturity 不足：**1**（actor-katiba-hanifa）
7. summary-only 关系：15
8. source 污染残留：`un-jnim-2018` 仍出现在 20+ 实体/关系（非 Tanzania 范围，Depth G 候选）
9. duplicate/malformed 候选：**rel-jnim-is-hostile 与 rel-jnim-is-conflict（同 pair+type）**
10/11. Bottom 20 实体（最低：person-ibrahim-malam-dicko 48 字）/ Bottom 20 关系

**本轮未自动修复任何非本包审计项**——这是给 Depth G 的机械输入。

## 11. 明确是否具备进入 Depth G 条件

**是**。Depth A–F 已完成六轮 theater-specific depth（Central Sahel/Lake Chad/Central Mali/Sudan/Ethiopia/Residual Core），13/72/150/249 全程不变；residual audit 已产出 11 维度 Bottom 清单。进入 Depth G（全库最终 Audit/Closure）的条件已具备，但**按要求未自动启动**。

---

**DEPTH F = CLOSED。** 已停止，未自动执行 Depth G，未扩广度，未扩 Somalia/DRC/CAR。
