# ASIP Intelligence I3-D1 萨赫勒核心关系网络扩充验收报告

- 任务：I3-D1 萨赫勒核心关系网络第一批内容包机械同步、构建与发布
- 内容包：`ASIP-I3D1-SAHEL-CONTENT-PACK-V1`
- 结论：**I3-D1 = CLOSED · 八项 Gate 全部 PASS**
- 验收日期：2026-08-08

---

## 1. 基线

| 项目 | SHA |
|---|---|
| I3D1_BASELINE_SOURCE_SHA | `979e2d6dbe9c899dde05b5fa6d89dcea928e577c`（asip-intelligence-v1.0.1） |
| I3D1_BASELINE_GH_PAGES_SHA | `b666fefbd82e68e9d479020d74a4240e35fde199` |
| 工作分支 | `feature/asip-intelligence-v10-i3d1-sahel-import`（clean worktree） |

## 2. 发布记录

| 项目 | 值 |
|---|---|
| 最终源码提交 | `ecf7402`（数据 `c6f7021`、generator `dcc9546`、前端 `1b71a59`、测试 `9944a42`、QA `28da346`、CSS/公网QA `ecf7402`） |
| gh-pages 内容发布 | `acfdb9df374c5d56c8a977180907fe918906954c`（69 文件，普通 push） |
| gh-pages CSS 修复 | `efe71a8e82d566b1eb4b6f5b2b8b66dc51a932eb`（1 文件） |
| Pages deployment | content run `31273299657` success；css run `31273619731` success |
| 公网路径 | `https://kenan032005.github.io/asip-site/intelligence/africa/` |

## 3. 最终数据规模

| 指标 | 前 | 后 |
|---|---|---|
| countries | 13 | 13 |
| non-country entities | 46 | **61**（+15） |
| relationships | 78 | **121**（+43） |
| relation profiles | 33 | **42**（+9） |
| relation timelines | 33 | **42**（+9） |
| sources | 96 | **109**（+13 新增、+3 复用） |
| evidence | 167 | **182**（+15） |
| routes | 151 | **209** |

## 4. 三条 D1-Prep 修正（逐条）

| 修正 | 目标关系 | 结果 |
|---|---|---|
| D1PREP-ETH-OLA-001 | rel-endf-ola-conflict | 删除“与TPLF结盟使奥罗米亚—提格雷两线联动”；summary 改为“不足以把2021年联盟延伸为2026年正式联盟”；移除 `un-jnim-2018`，绑定 `d1-acled-ethiopia-2026`；claim_valid_as_of=2026-08-08 |
| D1PREP-ETH-TDF-001 | rel-endf-tdf-conflict | 删除“提格雷事实脱离联邦控制”“比勒陀利亚协议实质失效”；改为“重新对峙/局部交火、和平框架严重承压”；移除 `un-jnim-2018`，绑定 `ETH_AU_2026_01_30`（复用）+`d1-acled-ethiopia-2026` |
| D1PREP-BFA-JNIM-001 | rel-burkina-army-jnim | 删除“JNIM控制/争夺约六成领土”；改为“政府军自由行动约30%、其余为争议空间，不归因单一组织”；移除 `un-jnim-2018`，绑定 `BURKINA_ACSS_2025_08_26`（复用） |

**Residual 扫描**（source data + dist）：4 句旧表述全部为 0。

## 5. 15 个实体导入（逐条状态）

| 实体 | 状态 |
|---|---|
| actor-fla / actor-africa-corps / actor-wagner-group / actor-ansarul-islam / actor-hcua / actor-mnla / actor-maa-cma / actor-gatia / actor-dan-na-ambassagou / actor-fu-aes / actor-niger-armed-forces / person-abu-hanifa / person-sadou-samahouna / actor-lakurawa / actor-ansaru | 全部 IMPORTED |

- ID/slug 无冲突（现有 46 实体无重叠）；entity_profiles 61/61 全部存在
- 深度目标：encyclopedia_full 6 个、standard 9 个（按内容包 profile_depth_target）

## 6. 43 条关系（语义锁定全部保留）

- FLA ↔ JNIM = `cooperates_with`（非 allied_with）✓
- Ansarul Islam → JNIM = `constituent_of` ✓
- Ansaru → AQIM = `pledged_allegiance_to`；Ansaru ↔ JNIM = `affiliated_with` ✓
- Lakurawa → IS Sahel = `part_of_network` + `disputed=true`；Lakurawa ↔ JNIM = `cooperates_with` + `disputed=true` + scope `some_cells_only` ✓
- Dan Na Ambassagou ↔ FAMa = `cooperates_with`（非 member_of_force）✓
- Sadou Samahouna → JNIM = `historical_ended`；→ IS Sahel = `current` ✓
- FU-AES 三国军队 = `member_of_force` ✓
- 43 条类型全部 ∈ 24 类型注册表（无新增 ontology）；端点全部合法（实体/国家/区域）

## 7. 9 个深度关系档案

FLA-JNIM / FAMa-Africa Corps / Wagner-Africa Corps / Ansarul-JNIM / Sadou-IS Sahel / Ansaru-AQIM / Lakurawa-IS Sahel / FU-AES / Dan Na-FAMa 全部写入 relation_profiles + relation_timelines；时间线完整保留日期与来源，未被压缩为无日期段落。

## 8. Source 映射

- 16 个候选：13 个新增、**3 个 URL-exact 复用**（`d1-reuters-mali-attacks-2026-04-25`→`MALI_REUTERS_2026_04_25`、`d1-africa-center-burkina-2025-08-26`→`BURKINA_ACSS_2025_08_26`、`d1-au-tigray-2026-01-30`→`ETH_AU_2026_01_30`）
- **published_at=null 政策**：6 个 ACLED source 保留 null（schema 允许），**未编造任何日期**；`SOURCE_DATE_SCHEMA_BLOCKER`：0

## 9. Evidence 映射

- 15 条 claims 全部导入；Lakurawa 两条保持 `disputed=true` + `partially_verified`（未升级）
- 引用完整性：source/entity/relation 全部 resolve
- 顺带机械修复：I3-B 遗留 `ev-i3b-126` 重复 ID（5 条 → ev-i3b-127..131），事实未变

## 10. Generator 一致性

- `build_intelligence_africa.py` 同步：relations 上限 100→150；关系端点允许区域；freshness 枚举 + `current_as_structural_history`；D1 导入档案（imported_by=i3d1）保持内容包深度目标
- **Regeneration diff：unexpected_object_deletions=0 / profile_depth_regressions=0 / evidence_regressions=0 / relation_type_regressions=0 / timeline_regressions=0**
- 前端 `africa.js` 定向修复：区域端点 titleFor 回退、Network 邻居去重守卫（修复 `Cannot read properties of undefined`）、新 freshness 标签；`intelligence.css`：长 URL 换行 + grid min-width（修复 390px 溢出）

## 11. 构建与回归

- `python scripts/build_site.py --no-embed` → **209 routes**（home + 6 index + 7 regions + 13 countries + 61 entities + 121 relations）
- 全回归：**Python 31/31、Node 4/4、build PASS、metrics 一致、local path 0、路由齐全，FAIL_TOTAL=0**

## 12. 浏览器 QA

- 本地候选：20 页 PASS（Africa/索引/Network/重点实体与关系页，0 错误 0 溢出）
- Network 密度：JNIM(25节点/26边) FLA(9/8) Africa Corps(6/5) FU-AES(4/3) Lakurawa(6/5) Ansaru(5/4)，无重复节点、焦点切换全部正确
- **公网 80 页 PASS**：15 新实体全部 200、43 新关系全部 200、1920/1366/390 三视口；consoleErrors=0、runtimeExceptions=0、failedRequests=0、brokenAssets=0、horizontalOverflow=0、unhandledRejections=0

## 13. Production 隔离

- production diff：仅 `intelligence/africa/**` + `assets/js/intelligence/africa.js` 变化；主站 10 文件仅 build 元数据；RC 预览 `previews/**` 全部保留；**UNEXPECTED_MODIFIED=0 / UNEXPECTED_DELETED=0 / UNEXPECTED_ADDED=0**

## 14. 八项 Gate

| Gate | 状态 |
|---|---|
| I3D1_PREP_GATE | PASS |
| I3D1_ENTITY_GATE | PASS |
| I3D1_RELATION_GATE | PASS |
| I3D1_SOURCE_EVIDENCE_GATE | PASS |
| I3D1_GENERATOR_GATE | PASS |
| I3D1_BUILD_GATE | PASS |
| I3D1_PUBLIC_QA_GATE | PASS |
| I3D1_PRODUCTION_ISOLATION_GATE | PASS |
| **overall** | **PASS** |

## 15. Blocked / 未完成项

- `SOURCE_DATE_SCHEMA_BLOCKER`：0（schema 允许 null published_at，无编造日期）
- 其他 BLOCKED：0

## 16. 最终状态

**I3-D1 = CLOSED**。未执行 I3-D2；未新增国家；未开发地图；未新建关系 ontology；未修改与本包无关的知识数据。
