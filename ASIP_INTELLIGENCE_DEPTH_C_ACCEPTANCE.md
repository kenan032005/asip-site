# ASIP Intelligence — DEPTH C Acceptance Report

**Package**: ASIP-DEPTH-C-CENTRAL-MALI-REGIONAL-COMMAND-V1（Central Mali Dozo 网络 + JNIM 区域指挥链深度升级）
**Status**: **DEPTH C = CLOSED**（10/10 Gate PASS）

---

## 1. 基线 / 终态 SHA

| 项 | 基线（Depth B CLOSED） | 终态（本轮） |
|---|---|---|
| source | `7604c68` | `46abaed`（分支 `feature/asip-intelligence-depth-c-central-mali`） |
| gh-pages | `5aeccd9` | `012b931`（普通 push） |
| Pages run | `31298375711` | `31300822992`（success） |

## 2. Count Invariant（全程严格保持）

| 指标 | 值 |
|---|---|
| countries | **13**（不变） |
| non-country entities | **72**（不变，0 新增） |
| relationships | **150**（不变，0 新增） |
| routes | 249 |
| sources | 137（0 新增，4 全部复用） |
| evidence | 231 → **245**（+14） |

未新增实体/关系/国家/ontology，未做地图，未扩新战区，未启动 Depth D。

## 3. 五组语义清洗（source-of-truth 层 + generator 一致）

| 组 | 内容 | 结果 |
|---|---|---|
| 1 | **Dozo 非统一组织**：三个主要网络（Dan Na Ambassagou / Dozos of Macina / Dana Atem）保持独立，任何一处不得合并 | 3 实体独立存在，无合并表述 |
| 2 | **Dana Atem 部分整合**：2023 年 Mondoro 封锁解除后部分成员进入正规军 ≠ 整体 member_of_force | rel-d2-dana-fama-coop 保持 cooperates_with，无 member_of_force 关系 |
| 3 | **Dozo—FAMa 模糊语义**：全部 Dozo→FAMa 保持 cooperates_with 且 intermittent/ambiguous（合作与缴械/压制并存） | 3 条关系全部 cooperates_with + 间歇/非正式表述 |
| 4 | **区域指挥范围**：Jafar 仅 Burkina regional leader/top commander；Ousmane 仅 Burkina deputy；Abou Ghosmane 仅 Niger 西北行动/后勤 | 无 whole-JNIM led_by/deputy；rel-d2-jafar-jnim 保持 affiliated_with |
| 5 | **Ghosmane ≠ Abu Hanifa**：两独立人物严格分开 | identity 分离表述确认 |

## 4. 10 实体成熟度前后

| entity | 前 | 后 | sections | 中文字数 | freshness |
|---|---|---|---|---|---|
| actor-dan-na-ambassagou | 无 maturity | **E3_FULL_ENCYCLOPEDIA** | 16 | 590 | current |
| person-youssouf-toloba | 无 maturity | **E2_DEVELOPED** | 9 | 200 | current |
| actor-dozos-of-macina | 无 maturity | **E3_FULL_ENCYCLOPEDIA** | 12 | 303 | **aging**（锁定） |
| person-amadou-nionson-diarra | 无 maturity | **E2_DEVELOPED** | 8 | 142 | aging（锁定） |
| actor-dana-atem | 无 maturity | **E2_DEVELOPED** | 11 | 245 | aging（锁定） |
| person-sidi-ongoiba | 无 maturity | **E1_BASIC**（资料有限不强行扩写） | 7 | 116 | aging（锁定） |
| actor-katiba-serma | 无 maturity | **E2_DEVELOPED** | 8 | 160 | aging（锁定） |
| person-jafar-dicko | 无 maturity | **E3_FULL_ENCYCLOPEDIA** | 13 | 289 | current |
| person-ousmane-dicko | 无 maturity | **E2_DEVELOPED** | 9 | 140 | current |
| person-abou-ghosmane | 无 maturity | **E2_DEVELOPED** | 10 | 220 | current |

## 5. 16 关系成熟度前后

| relationship | 前 | 后 | type（锁定） | timeline |
|---|---|---|---|---|
| rel-d1-dan-na-jnim-conflict | 无 maturity | **R3** | fought_against | 3 |
| rel-d1-dan-na-fama-coop | 无 maturity | **R3** | cooperates_with | 2 |
| rel-d2-dan-na-toloba-led | 无 maturity | **R2** | led_by | — |
| rel-d2-dana-dan-na-split | 无 maturity | **R2** | split_from | 2 |
| rel-d2-dana-sidi-led | 无 maturity | **R2** | led_by | — |
| rel-d2-dana-katiba-serma-conflict | 无 maturity | **R2** | fought_against | — |
| rel-d2-dana-ansarul-conflict | 无 maturity | **R2** | fought_against | — |
| rel-d2-dana-fama-coop | 无 maturity | **R2** | cooperates_with | — |
| rel-d2-dozos-macina-amadou-led | 无 maturity | **R2** | led_by | — |
| rel-d2-dozos-macina-jnim-conflict | 无 maturity | **R3** | fought_against | 2 |
| rel-d2-dozos-macina-fama-coop | 无 maturity | **R2** | cooperates_with | — |
| rel-d2-katiba-serma-jnim | 无 maturity | **R2** | **constituent_of**（锁定） | — |
| rel-d2-jafar-jnim | 无 maturity | **R3** | **affiliated_with**（非 led_by） | 2 |
| rel-d2-ansarul-jafar-led | 无 maturity | **R2** | led_by | — |
| rel-d2-ousmane-jnim | 无 maturity | **R2** | affiliated_with | — |
| rel-d2-ghosmane-jnim | 无 maturity | **R2** | affiliated_with | 1 |

## 6. Source / Evidence Mapping

- **Sources**：137 → **137**（4 candidates 全部复用，0 新增，0 编造日期）
  - `depthc-acled-dozos-2025-10-08` → `d1-acled-dozo-2026`（URL exact）
  - `depthc-acled-mali-june-2026` → `d1-acled-africa-june-2026`（URL exact）
  - `depthc-hrw-burkina-2026-04-02` → `d2-hrw-burkina-2026-04-02`（URL exact）
  - `depthc-un-s2026-44` → `d2-un-s2026-44`（UN record 4102624 normalized）
- **Evidence**：231 → **245**（+14，全部引用 resolve，verified=14 / 无自动升级；`verified_with_title_variation` 映射 verified 并在 verification_method 记录标题差异）

## 7. Generator Diff

regen diff（幂等重跑导入）：unexpected deletions=0 / entity count change=0 / relationship count change=0 / country count change=0 / unintended relation type change=0 / profile depth regressions=0 / evidence regressions=0（8 项全 0）。

## 8. Tests / QA

- **专项测试**：11 项（test_depth_c_import.py）全部 PASS（counts、Dozo network separation、Dana partial integration、Dozo-FAMa semantics、Dan Na 2026 refresh、Jafar regional scope、Ousmane regional scope、Ghosmane/Hanifa separation、Katiba Serma constituent lock、freshness locks、generator regression）
- **全回归**：30 Python + Node + build，**FAIL_TOTAL=0**（1 个既有测试同步：metrics generated_by 白名单加 depth_c_import.py）
- **本地候选 Browser QA**：108 页（10 实体 + 16 关系 × 4 视口 + 4 索引），0 失败，100 maturity badge / 56 analysis / 44 watch
- **公网 Browser QA**：108 页全绿（与本地一致），consoleErrors/runtimeExceptions/failedRequests/brokenAssets/horizontalOverflow 全 0
- **Network QA**：8 焦点（Dan Na / Dozos of Macina / Dana Atem / Katiba Serma / Jafar / Ousmane / Ghosmane / Toloba）密度 PASS；公网首轮 Dan Na 0/0 为 CDN 旧 bundle 时序，重试 6/5 收敛
- **production diff**：UNEXPECTED=0，白名单（intelligence/africa/**），无删除、无 RC 历史快照改动

## 9. 期间处理的问题

1. **QA 脚本派生失误**：公网 QA 从 Depth B 派生时 ENTITIES/RELATIONS 列表未完整替换（首轮只跑了 8 实体 + 16 关系 = 100 页），修正后 108 页全绿。
2. **regen diff 派生脚本路径未改**：depth_c_regen_diff.py 曾指向 qa-artifacts-depth-b，误删 Depth B 的 QA 产物 → 已恢复 Depth B 产物并修正路径（本次已确认 Depth B 的 `qa-artifacts-depth-b/` 完好）。
3. **favicon 404**：根页浏览器自动请求 favicon.ico（产品不引用）导致首轮 1 个 4xx → QA 过滤 favicon 后 0 失败。

## 10. Depth A/B 审计剩余 Bottom 项在本轮后的变化

Depth A 审计的 Bottom 20 中，Central Mali 相关项本轮全部受益：
- **actor-dan-na-ambassagou** → E3（590 字，16 sections，freshness=current，2026 JNIM 攻势刷新）
- **actor-dozos-of-macina** → E3（303 字，Souleye 中央层级 + aging 锁定）
- **person-jafar-dicko** → E3（289 字，Burkina 区域领导 + 2026 HRW）
- 其余 7 项（Toloba/Amadou/Dana Atem/Sidi/Katiba Serma/Ousmane/Ghosmane）→ E2/E1
- 对应 16 条关系 → R3/R2

Depth A 审计中剩余非 Central Mali 项（如 amadou-nionson-diarra 已覆盖、wagner 等）留待后续候选，本轮未触碰。

---

**DEPTH C = CLOSED。** 已停止，未自动执行 Depth D，未扩广度。
