# ASIP Intelligence — DEPTH D Acceptance Report

**Package**: ASIP-DEPTH-D-SUDAN-CIVIL-WAR-CORE-V1（Sudan Civil War Core 深度升级）
**Status**: **DEPTH D = CLOSED**（10/10 Gate PASS）

---

## 1. 基线 / 终态 SHA

| 项 | 基线（Depth C CLOSED） | 终态（本轮） |
|---|---|---|
| source | `46abaed`（分支 HEAD `6f80a15`） | `1d48d2c`（分支 `feature/asip-intelligence-depth-d-sudan-core`） |
| gh-pages | `012b931` | `398aba3`（普通 push） |
| Pages run | `31300822992` | `31302123532`（success） |

## 2. Count Invariant（全程严格保持）

| 指标 | 值 |
|---|---|
| countries | **13**（不变） |
| non-country entities | **72**（不变，0 新增） |
| relationships | **150**（不变，0 新增） |
| routes | 249 |
| sources | 137 → **150**（+13 新增 + 2 复用） |
| evidence | 245 → **260**（+15） |

未新增实体/关系/国家/ontology，未做地图，未开始 Ethiopia/Horn 扩展，未启动 Depth E。

## 3. 六组事实/语义清洗（source-of-truth 层 + generator 一致）

| 组 | 内容 | 结果 |
|---|---|---|
| A | SAF-RSF 2026 战场现实：SAF 2025 恢复 Khartoum；RSF 控制 Darfur 大部；2026 Kordofan/El Obeid 关键接触带；**任一方不得写成控制全国** | "控制整个苏丹" 仅在否定语境出现（"不能把'控制Darfur大部'写成控制整个苏丹西部"） |
| B | **`rel-jem-saf-conflict` count-preserving repair**：type `hostile_to`→`cooperates_with`；current_status=current_operational_cooperation_after_historical_conflict；**2003—2020 历史敌对保留于 timeline**（4 items：2003—2020/2020—2023/2023-11 以后/2025—2026）；legacy ID 保留；总数仍 150 | PASS |
| C | **`rel-rsf-darfur-origin` count-preserving repair**：type `historically_associated_with`→`fought_against`；current_status=current_hostility_after_historical_darfur_association；**不再暗示 JEM 与 RSF/Janjaweed 共同组织起源**；legacy ID 保留；总数仍 150 | PASS |
| D | Leadership：Burhan 当前 SAF 领导人 + Transitional Sovereignty Council 主席（2026-07 卡塔尔官方外交记录）；Hemedti 当前 RSF 领导人；旧 stale 2024 表述清除 | PASS |
| E | SPLM-N al-Hilu：当前 hostile_to SAF；2025 加入 RSF-led SFA/Tasis；**组织保持独立**；不写 member_of_force/constituent_of RSF；**未新增 SPLM-N↔RSF edge**（depth-only） | PASS |
| F | Atrocity language：UN 调查/genocide findings 明确标注来源归因（"联合国调查认为...呈现genocide hallmarks"），**不写成对 Hemedti 个人已司法定罪** | PASS |

## 4. 6 实体成熟度前后

| entity | 前 | 后 | sections | 中文字数 | freshness |
|---|---|---|---|---|---|
| actor-saf | 无 maturity | **E3_FULL_ENCYCLOPEDIA** | 23 | 1379 | current |
| actor-rsf | 无 maturity | **E3_FULL_ENCYCLOPEDIA** | 24 | 1502 | current |
| person-abdel-fattah-al-burhan | 无 maturity | **E3_FULL_ENCYCLOPEDIA** | 17 | 851 | current |
| person-mohamed-hamdan-dagalo | 无 maturity | **E3_FULL_ENCYCLOPEDIA** | 18 | 814 | current |
| actor-splm-n-al-hilu | 无 maturity | **E3_FULL_ENCYCLOPEDIA** | 20 | 871 | current |
| actor-jem | 无 maturity | **E2_DEVELOPED** | 19 | 772 | current |

## 5. 8 关系成熟度前后

| relationship | 前 | 后 | type（锁定/修复） | timeline |
|---|---|---|---|---|
| rel-saf-rsf-war | 无 maturity | **R3** | hostile_to | 4 |
| rel-burhan-saf-leads | 无 maturity | **R2** | led_by | — |
| rel-dagalo-rsf-leads | 无 maturity | **R2** | led_by | — |
| rel-splm-n-saf-conflict | 无 maturity | **R3** | hostile_to | 4 |
| rel-jem-saf-conflict | 无 maturity | **R3** | **cooperates_with（repair）** | 4（含 2003—2020 历史） |
| rel-rsf-darfur-origin | 无 maturity | **R2** | **fought_against（repair）** | — |
| rel-saf-sudan-operates | 无 maturity | **R2** | operates_in | — |
| rel-rsf-sudan-operates | 无 maturity | **R2** | operates_in | — |

## 6. 两个 count-preserving repair 完整证明

| 项 | rel-jem-saf-conflict | rel-rsf-darfur-origin |
|---|---|---|
| legacy ID 保留 | `rel-jem-saf-conflict`（slug `jem-saf-conflict` 不变） | `rel-rsf-darfur-origin`（slug 不变） |
| before type | hostile_to | historically_associated_with |
| after type | cooperates_with | fought_against |
| current_status | current_operational_cooperation_after_historical_conflict | current_hostility_after_historical_darfur_association |
| 历史保留 | 2003—2020 敌对 timeline 4 items | Darfur 历史背景在 profile historical_context |
| 关系总数 | **150（未新增第 151 条）** | **150（未新增第 151 条）** |
| 残留检查 | JEM current hostile_to SAF = 0 | JEM/RSF 共同组织 origin = 0 |

## 7. Source / Evidence Mapping

- **Sources**：137 → **150**（15 candidates → 13 新增 + 2 URL-exact 复用；published_at=null 未猜日期）
  - 复用：`depthd-acled-sudan-july-2026`→`deptha-acled-july-2026`、`depthd-acled-saf-allies-2025`→`acled-sudan-2025`
- **Evidence**：245 → **260**（+15，全部引用 resolve）
  - verification_status **不自动提升**：`analytical_synthesis`（depthd-ev-015）→ partially_verified + claim_type=analysis；`verified_reported_finding`（depthd-ev-005，UN genocide finding）→ verified + method 注明 attribution；`verified_reported_draft_findings`（depthd-ev-006，Reuters 报道的 UN 专家草案）→ verified + method 注明 reported/draft
  - 最终：verified=14 / partially_verified=1

## 8. Generator Diff

regen diff（幂等重跑导入）：unexpected_object_deletions=0 / entity_count_change=0 / relationship_count_change=0 / country_count_change=0 / importance_level_change=0 / unintended_relation_type_change=0 / profile_depth_regressions=0 / evidence_regressions=0（8 项全 0）。

6 项特别残留检查：JEM current hostile_to SAF=0、JEM/RSF common organizational origin=0、SAF-RSF current framing stuck at 2024=0、SAF controls whole Sudan=0（仅否定语境）、RSF controls whole Sudan=0（仅否定语境）、SPLM-N subordinate/member of RSF=0。

## 9. Tests / QA

- **专项测试**：10 项（test_depth_d_import.py）全部 PASS（counts、SAF-RSF 2026 front、JEM-SAF repair、RSF-JEM repair、Burhan current、Hemedti current、SPLM-N autonomy、atrocity attribution、territorial scope、generator regression）
- **全回归**：31 Python + Node + build，**FAIL_TOTAL=0**（1 个既有测试同步：metrics generated_by 白名单加 depth_d_import.py）
- **本地候选 Browser QA**：60 页（6 实体 + 8 关系 × 4 视口 + 4 索引），0 失败，56 maturity badge / 36 analysis / 36 watch
- **公网 Browser QA**：60 页全绿（与本地一致），consoleErrors/runtimeExceptions/failedRequests/brokenAssets/horizontalOverflow 全 0
- **Network QA**：6 焦点（SAF/RSF/JEM/SPLM-N/Burhan/Hemedti）密度 PASS；公网首轮 SAF/RSF 0/0 为 CDN 旧 bundle 时序，重试 7/6、6/5 收敛
- **production diff**：UNEXPECTED=0，白名单（intelligence/africa/** + 共享 CSS），无删除、无 RC 历史快照改动

## 10. 期间发现并修复的真实问题

1. **前端渲染缺陷（产品 CSS）**：Depth D 的 `current_status` 值较长（如 `active_state_force_controlling_khartoum_east_and_contesting_kordofan_darfur`）在 390px 视口撑开 `.intel-badges` 容器（401px>390）；关系页 `.intel-title-en` 拼接过长也无断行点（JEM-SAF 415px）→ 给 `.intel-badge` 与 `.intel-title-en` 加 `overflow-wrap:anywhere + max-width:100%`（本地候选 QA 抓到并修复后复跑归零）。
2. **QA 产物误提交**：regen diff 的 scratch 快照被 git add 误提交 → 已移除并加入 .gitignore（`qa-artifacts-depth-d/scratch/`）。

## 11. Depth A/B/C 审计剩余 Bottom 项在本轮后的变化

Depth A 审计的 Bottom 20 中，Sudan 相关项本轮全部受益：
- **actor-saf / actor-rsf**（Depth A 时仅基础卡，L1 却极薄）→ E3（1379/1502 字）
- **person-abdel-fattah-al-burhan / person-mohamed-hamdan-dagalo** → E3（851/814 字）
- **actor-splm-n-al-hilu** → E3（871 字）
- **actor-jem** → E2（772 字）
- 对应 8 条关系（含最核心 rel-saf-rsf-war 从 2024 stale framing → 2026 R3）→ R3/R2

Depth A 审计中剩余非 Sudan 项（如 wagner、amadou-nionson-diarra 已覆盖等）留待后续候选，本轮未触碰。

---

**DEPTH D = CLOSED。** 已停止，未自动执行 Depth E，未扩广度，未开始 Ethiopia/Horn 扩展。
