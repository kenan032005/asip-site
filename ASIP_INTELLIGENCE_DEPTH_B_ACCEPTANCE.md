# ASIP Intelligence — DEPTH B Acceptance Report

**Package**: ASIP-DEPTH-B-LAKE-CHAD-V1（Lake Chad 旗舰实体百科化 + 关系情报化 + 谱系/机构事实清洗）
**Status**: **DEPTH B = CLOSED**（10/10 Gate PASS）

---

## 1. 基线 / 终态 SHA

| 项 | 基线（Depth A CLOSED） | 终态（本轮） |
|---|---|---|
| source | `8f0f325` | `7604c68`（分支 `feature/asip-intelligence-depth-b-lake-chad`） |
| gh-pages | `54167ed` | `5aeccd9`（普通 push） |
| Pages run | `31277958625` | `31298375711`（success） |

## 2. Count Invariant（全程严格保持）

| 指标 | 值 |
|---|---|
| countries | **13**（不变） |
| non-country entities | **72**（不变，0 新增） |
| relationships | **150**（不变，0 新增） |
| routes | 249 |

未新增实体、未新增关系、未新增国家、未新增 relation ontology、未开发地图、未启动 Depth C。

## 3. 五组阻断级事实清洗（source-of-truth 层 + generator 一致）

| 组 | 内容 | 结果 |
|---|---|---|
| A | ISWAP 领导层：al-Barnawi ≠ Bakura；不写"2021 确认死亡"；Ba'a Shuwa（Abu Musa al-Mangawi）为 reported current leader；保留 UN 成员国状态分歧 | 全库"巴库拉（Abu Musab al-Barnawi）"身份等同残留 **0**；"2021 确认死亡"仅以否定语境出现 |
| B | JAS—ISIS 历史：2015-03-07 Shekau 代表 Boko Haram 向 ISIS 宣誓效忠并被接纳；2016-08-03 正式 West Africa Province 认可转向 al-Barnawi；当前 JAS unaffiliated | "JAS 从未加入 ISIS" 残留 **0**；2015 pledge 语义已恢复 |
| C | `rel-jas-islamic-state-hostile` **count-preserving repair**：target `actor-iswap`→`actor-islamic-state`；type `hostile_to`→`pledged_allegiance_to`；time 2015-03-07~2016-08-03；status=historical_pledge_recognition_shifted_to_iswap；legacy ID/slug 保留；**关系总数仍 = 150**；malformed JAS→ISWAP 重复关系消除（仅剩合法 rel-jas-iswap-conflict 一条） | PASS |
| D | MNJTF sectors：S1=Mora/Cameroon、S2=Bagasola/Chad、S3=Monguno/Nigeria、S4=Diffa/Niger；**Niger 已退出 TCCs**，Sector 4 显示 operationally disrupted；Force Commander 更新为 Major General Saidu Tanko Audu | "Nigeria Sector 1"/"Cameroon Sector 3" 残留 **0** |
| E | Cameroon 关系 source 污染：`rel-cameroon-army-jas` / `rel-cameroon-army-iswap` 移除无关 `un-jnim-2018`，替换为 Lake Chad 专属来源（NCTC/ACLED/ISS） | PASS |

## 4. 8 实体成熟度前后

| entity | 前 | 后 | sections | 中文字数 | ASIP Analysis | Watch |
|---|---|---|---|---|---|---|
| actor-jas | 无 maturity | **E3_FULL_ENCYCLOPEDIA** (94) | 30 | 2375 | ✓ | ✓ |
| actor-iswap | 无 maturity | **E3_FULL_ENCYCLOPEDIA** (95) | 28 | 2065 | ✓ | ✓ |
| actor-mnjtf | 无 maturity | **E3_FULL_ENCYCLOPEDIA** (94) | 27 | 1773 | ✓ | ✓ |
| actor-nigeria-army | 无 maturity | **E2_DEVELOPED** (84) | 25 | 1647 | ✓ | ✓ |
| actor-chad-army | 无 maturity | **E2_DEVELOPED** (82) | 16 | 677 | ✓ | ✓ |
| actor-cameroon-army | 无 maturity | **E2_DEVELOPED** (83) | 16 | 675 | ✓ | ✓ |
| actor-lakurawa | 无 maturity | **E2_DEVELOPED** (82) | 13 | 557 | ✓ | ✓ |
| actor-ansaru | 无 maturity | **E2_DEVELOPED** (84) | 15 | 441 | ✓ | ✓ |

## 5. 11 关系成熟度前后

| relationship | 前 | 后 | type（锁定） | timeline |
|---|---|---|---|---|
| rel-jas-iswap-conflict | 无 maturity | **R3** | hostile_to | 4 |
| rel-jas-islamic-state-hostile | 无 maturity（malformed） | **R3** | pledged_allegiance_to（修复） | 4 |
| rel-iswap-islamic-state-affiliation | 无 maturity | **R3** | pledged_allegiance_to | 2 |
| rel-nigeria-mnjtf-member | 无 maturity | **R2** | member_of_force | 2 |
| rel-chad-mnjtf-member | 无 maturity | **R2** | member_of_force | 2 |
| rel-cameroon-mnjtf-member | 无 maturity | **R2** | member_of_force | — |
| rel-cameroon-army-jas | 无 maturity | **R2** | fought_against | 2 |
| rel-cameroon-army-iswap | 无 maturity | **R2** | fought_against | 2 |
| rel-d1-ansaru-jas-split | 无 maturity | **R2** | split_from | — |
| rel-d1-ansaru-aqim-allegiance | 无 maturity | **R2** | pledged_allegiance_to | 4 |
| rel-d1-ansaru-jnim-affiliation | 无 maturity | **R2** | **affiliated_with（不升级 constituent_of）** | — |

## 6. Source / Evidence Mapping

- **Sources**：127 → **137**（13 candidates → 10 新增 + 3 复用；published_at=null 未猜日期）
  - 复用：`d1-acled-africa-june-2026`（URL exact）、`d2-un-s2026-44`（UN record 4102624 normalized）、`iss-mnjtf-lakechad-2025`（URL exact）
  - 证据文件：`qa-artifacts-depth-b/source-mapping.json`
- **Evidence**：214 → **231**（+17，全部引用 resolve）
  - verification_status **不自动提升**：`analytical_synthesis`（depthb-ev-017）→ partially_verified，claim_type=analysis；`verified_estimate`（depthb-ev-004）→ verified + claim_type=estimate；`verified_reported_with_uncertainty`（depthb-ev-006）→ partially_verified
  - 最终：verified=15 / partially_verified=2；fact=15 / estimate=1 / analysis=1

## 7. Generator Diff

regen diff（幂等重跑导入）：unexpected_object_deletions=0、entity_count_change=0、relationship_count_change=0、country_count_change=0、importance_level_change=0、unintended_relation_type_change=0、profile_depth_regressions=0、evidence_regressions=0（8 项全 0）。

## 8. Tests / QA

- **专项测试**：11 项（test_depth_b_import.py）全部 PASS（counts、JAS-ISIS pledge、malformed repair、ISWAP leadership、Bakura≠al-Barnawi、MNJTF sectors、Niger withdrawal、Cameroon sources、Ansaru、Lakurawa disputed lock、generator regression）
- **全回归**：29 Python + Node + build，**FAIL_TOTAL=0**（3 个既有测试同步：metrics generated_by 白名单 + R2/R3 maturity-aware 判定 + historical R3 不要求 watch_indicators）
- **本地候选 Browser QA**：80 页（8 实体 + 11 关系 × 4 视口 + 4 索引），0 失败，76 maturity badge / 44 analysis / 60 watch
- **公网 Browser QA**：80 页全绿（CDN 缓存收敛后），与本地一致；consoleErrors/runtimeExceptions/failedRequests/brokenAssets/horizontalOverflow 全 0
- **Network QA**：8 焦点（JAS/ISWAP/MNJTF/三国军队/Lakurawa/Ansaru）密度 PASS，公网首轮 2 焦点 0/0 为 CDN 旧 bundle 时序，重试后 9/8 收敛
- **production diff**：UNEXPECTED=0，白名单（intelligence/africa/** + 共享 JS/CSS），无删除、无 RC 历史快照改动

## 9. 发现并修复的真实问题

1. **前端渲染缺陷（产品代码）**：`profile.constraints` 为字符串时前端调用 `.map()` 抛 `profile.constraints.map is not a function` → Nigeria-MNJTF 关系页白屏。修复：字符串按段落渲染、数组按列表渲染（`africa.js`）。
2. **Source 去重增强**：`depthb-un-s2026-44` 与既有 `d2-un-s2026-44` 为同一 UN record（digitallibrary 4102624），首次导入误判为 new；增强 normalized-record 去重规则并原位修复数据引用。
3. **既有测试同步**：3 个测试断言需适配 Depth B 数据（generator 名、R3 historical 无 watch_indicators、R2 核心字段判定）。

## 10. Depth A Audit 中剩余 Bottom 项在本轮后的变化

Depth A 的 Bottom-20 中，Lake Chad 相关项本轮全部受益：
- **actor-jas（Depth A 排名约 41/72）** → E3（2375 中文字，30 sections）
- **actor-iswap** → E3（2065 字）
- **actor-mnjtf** → E3（1773 字）
- **actor-nigeria-army / actor-chad-army / actor-cameroon-army** → E2（1647/677/675 字）
- **actor-lakurawa / actor-ansaru** → E2（557/441 字）
- 对应关系（JAS-ISWAP / JAS-IS / ISWAP-IS / MNJTF-三国 / Cameroon 双线 / Ansaru 三线）→ R3/R2

Depth A 审计文件（`qa-artifacts-depth-a/depth-audit-summary.md`）中的 Bottom 20 实体（如 amadou-nionson-diarra、wagner 等非 Lake Chad 项）未在本轮触碰，留待下一批厚度升级候选。

---

**DEPTH B = CLOSED。** 已停止，未自动执行 Depth C，未扩广度。
