# ASIP Intelligence I3-D2 JNIM 区域网络扩充验收报告

- 任务：I3-D2 JNIM 区域指挥链、贝宁/尼日利亚跨境网络与中马里基层武装机械同步、构建与发布
- 内容包：`ASIP-I3D2-JNIM-REGIONAL-NETWORK-V1`
- 结论：**I3-D2 = CLOSED · 九项 Gate 全部 PASS**
- 验收日期：2026-08-08

---

## 1. 基线

| 项目 | SHA |
|---|---|
| I3D2_BASELINE_SOURCE_SHA | `d6860f91c36bef00619a77437af1a5e4e455a9ac`（I3-D1 CLOSED 提交） |
| I3D2_BASELINE_GH_PAGES_SHA | `efe71a8e82d566b1eb4b6f5b2b8b66dc51a932eb` |
| 工作分支 | `feature/asip-intelligence-v10-i3d2-regional-network`（clean worktree） |

## 2. 发布记录

| 项目 | 值 |
|---|---|
| 最终源码提交 | `e35ca66`（data `4d2de45`、generator `77321eb`、test `f9ea185`、qa `e35ca66`） |
| gh-pages 发布 | `13847debfa56c6558b016b3f3ebcdf0bc64dbe05`（50 文件，普通 push） |
| Pages deployment | run `31275609742` conclusion **success** |
| 公网路径 | `https://kenan032005.github.io/asip-site/intelligence/africa/` |

## 3. 最终数据规模

| 指标 | 前 | 后 |
|---|---|---|
| countries | 13 | 13 |
| non-country entities | 61 | **72**（+11） |
| relationships | 121 | **150**（+29，另 3 条原位刷新） |
| relation profiles | 42 | **50**（+8） |
| relation timelines | 42 | **50**（+8） |
| sources | 109 | **115**（+6 新增、+1 URL-exact 复用） |
| evidence | 182 | **194**（+12） |
| routes | 209 | **249** |

## 4. 三条 Entity Refreshes

| 刷新 | 目标 | 结果 |
|---|---|---|
| D2REFRESH-JNIM-ENTITY-001 | actor-jnim | +Benin/+Nigeria country、+coastal-west-africa region、status=active_and_expanding_across_west_africa（活动存在，不表示控制）、claim_valid_as_of=2026-05-31 |
| D2REFRESH-ABU-HANIFA-001 | person-abu-hanifa | +Burkina/+Benin country；profile 追加 Katiba Hanifa 负责人语义（HRW/UN） |
| D2REFRESH-ANSARUL-001 | actor-ansarul-islam | profile 追加 Jafar Dicko 接掌与高度整合进 JNIM 语义（HRW） |

## 5. 三条 Relationship Refreshes

| 刷新 | 目标 | 结果 |
|---|---|---|
| D2REFRESH-JNIM-BENIN-001 | rel-jnim-benin-spillover | summary 落到 Katiba Hanifa 在 Alibori/Borgou/Atacora；status=current_activity_presence；freshness=current |
| D2REFRESH-JNIM-BENIN-FORCES-001 | rel-jnim-benin-forces-fought | summary 更新为 Katiba Hanifa 袭击巡逻/据点；status=current_hostility |
| D2REFRESH-JNIM-IS-001 | rel-jnim-is-conflict | **hostile_to 保持**；追加 2026-04-02 Tillabéri 与 2026-04-05 Kebbi 时间线（Kebbi 对象身份保留限定）；status=current_hostility_expanding_geographically |

未创建重复关系（refresh 目标全部原位更新；29 条新关系端点对全部唯一）。

## 6. 11 个新实体（逐条导入）

Jafar Dicko / Ousmane Dicko / Katiba Hanifa / Abou Ghosmane / Katiba Serma / Dana Atem / Ibrahim Malam Dicko / Dozos of Macina / Sidi Ongoiba / Amadou Nionson Diarra / Youssouf Toloba —— 全部 IMPORTED，ID/slug 唯一，profile 72/72 存在。

## 7. 29 条新关系（关键语义锁定）

- Jafar → JNIM = `affiliated_with`（**非整个 JNIM led_by**，role 限定）✓
- Ansarul Islam → Jafar = `led_by`；→ Ibrahim = `founded_by` ✓
- Katiba Hanifa → JNIM = `constituent_of`；→ Abu Hanifa = `led_by`；↔ 贝宁安全力量 = `fought_against` ✓
- **Abou Ghosmane 与 Abu Hanifa 为两个独立实体** ✓
- Dana Atem → Dan Na Ambassagou = `split_from`；Dana/Dozos → FAMa = `cooperates_with`（**非 member_of_force**）✓
- JNIM → Nigeria = `operates_in` + `emerging_limited_presence`（**无成熟分支/稳定基地/控制区语义**）✓
- **三个 Dozo 网络（Dan Na / Dana Atem / Dozos of Macina）保持独立** ✓

## 8. 8 个深度关系档案

Jafar-JNIM / Katiba Hanifa-JNIM / Katiba Hanifa-贝宁力量 / Abou Ghosmane-JNIM / Dana Atem-Dan Na / Dozos of Macina-JNIM / JNIM-Nigeria 新建档案 + rel-jnim-is-conflict 追加 2026 时间线与分析——时间线完整保留日期，未压缩为无日期段落。

## 9. Source 映射

7 个候选：**6 个新增 + 1 个 URL-exact 复用**（`d2-acled-dozo-2025-10-08` → `d1-acled-dozo-2026`，URL 完全一致）。3 个 `published_at=null`（NCTC as_of_2026-05、Africa Center 2026、ACLED dan-na profile）保留 null + date_precision；**未编造任何日期**；SOURCE_DATE_SCHEMA_BLOCKER = 0。

## 10. Evidence 映射

12 条 claims 全部导入（ev-d2-001..012），verification_status 按 packet（全部 verified），source/entity/relation 引用全部 resolve。

## 11. Generator 一致性

- `build_intelligence_africa.py`：packet-profile 放行条件由 `imported_by=="i3d1"` 扩展为 `startswith("i3d")`（覆盖 D2 导入）
- **Regeneration diff：unexpected_object_deletions=0 / profile_depth_regressions=0 / evidence_regressions=0 / relation_type_regressions=0 / timeline_regressions=0**
- 导入脚本幂等（timeline append 按 date+text 去重、profile append 按内容去重）

## 12. 构建与回归

- `build_site.py --no-embed` → **249 routes**（home + 6 index + 7 regions + 13 countries + 72 entities + 150 relations）
- 全回归：**Python 32/32、Node 4/4、build PASS、metrics 一致、local path 0、路由齐全，FAIL_TOTAL=0**
- D2 专项 9 测试全部 PASS（含 aging 保持、Nigeria 限定、Kebbi 限定、Jafar 角色）

## 13. 浏览器 QA

- 本地候选：28 页 PASS（11 新实体 + 3 刷新实体 + 9 代表性关系 + 索引 + Network，0 错误 0 溢出）
- Network 密度：JNIM(32节点/33边)、Katiba Hanifa(7/6)、Dana Atem(7/6)、Abou Ghosmane(3/2)、Jafar Dicko(4/3)、Dozos of Macina(5/4)——无重复节点、焦点切换全部正确
- **公网 68 页 PASS**：11 新实体全部 200、29 新关系全部 200、3 刷新实体全部 200；1920/1366/390 三视口；consoleErrors=0、runtimeExceptions=0、failedRequests=0、brokenAssets=0、horizontalOverflow=0
- 公网 Network 焦点 QA PASS

## 14. Production 隔离

production diff：仅 `intelligence/africa/**` 变化（10 个 data 文件 + 40 个新页面）；主站仅 build 元数据；RC 预览保留；**UNEXPECTED_MODIFIED=0 / UNEXPECTED_DELETED=0 / UNEXPECTED_ADDED=0**。

## 15. 九项 Gate

| Gate | 状态 |
|---|---|
| I3D2_SOURCE_GATE | PASS |
| I3D2_ENTITY_GATE | PASS |
| I3D2_RELATION_GATE | PASS |
| I3D2_REFRESH_GATE | PASS |
| I3D2_EVIDENCE_GATE | PASS |
| I3D2_GENERATOR_GATE | PASS |
| I3D2_BUILD_GATE | PASS |
| I3D2_PUBLIC_QA_GATE | PASS |
| I3D2_PRODUCTION_ISOLATION_GATE | PASS |
| **overall** | **PASS** |

## 16. Blocked / 未完成项

- SOURCE_DATE_SCHEMA_BLOCKER：0
- 其他 BLOCKED：0

## 17. 最终状态

**I3-D2 = CLOSED**。未执行 I3-D3；未新增国家；未开发地图；未新建关系 ontology；未修改与本包无关的知识数据。
