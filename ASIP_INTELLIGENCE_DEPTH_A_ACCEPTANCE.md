# ASIP Depth A：萨赫勒旗舰实体百科化 + 核心关系情报化 + 事实清洗 · 验收报告

- 任务：DEPTH A 旗舰深度升级（先厚度、后广度战略第一批）
- 内容包：`ASIP-DEPTH-A-SAHEL-FLAGSHIP-V1`
- 结论：**DEPTH A = CLOSED · 十一项 Gate 全部 PASS**
- 验收日期：2026-08-08

---

## 1. 基线 / SHA

| 项目 | 值 |
|---|---|
| DEPTHA_BASELINE_SOURCE_SHA | `05365d8a403174001c7f1b4c339e3a64d88780e4`（I3-D2 CLOSED） |
| DEPTHA_BASELINE_GH_PAGES_SHA | `13847debfa56c6558b016b3f3ebcdf0bc64dbe05` |
| 分支 | `feature/asip-intelligence-depth-a-sahel-flagship`（clean worktree） |
| 最终源码提交 | `1a07a5c`（data `27377f1`、前端 `2a6ce04`、测试 `074d7c0`、QA `1a07a5c`） |
| gh-pages 发布 | `54167edf69311f8380a3a322cdb0c4afcdbc6034`（普通 push，10 文件） |
| Pages deployment | run `31277958625` conclusion **success** |
| 公网路径 | `https://kenan032005.github.io/asip-site/intelligence/africa/` |

## 2. 数据数量保持（无扩展）

| 指标 | 基线 | 最终 | 变化 |
|---|---|---|---|
| countries | 13 | 13 | 0 |
| non-country entities | 72 | 72 | 0 |
| relationships | 150 | 150 | 0 |
| relation profiles | 50 | 55 | +5（R2/R3 新档案） |
| relation timelines | 50 | 51 | +1（aqim-constituent 从 evolution_stages 生成） |
| sources | 115 | 127 | +12 新增（22 候选中 10 复用） |
| evidence | 194 | 214 | +20 |
| routes | 249 | 249 | 0 |

## 3. 全库机械 Depth Audit（72 实体 / 150 关系）

- 产出：`entity-depth-audit.json`（72 条）、`relation-depth-audit.json`（150 条）、`depth-audit-summary.md`
- 口径：**MECHANICAL_SCORE_NOT_FACT_QUALITY_JUDGMENT**（仅统计结构，不评估事实质量）
- 统计维度：中文字符、实质章节、空字段、source/evidence、timeline、current assessment、uncertainty、ASIP Analysis、Watch Indicators、实体关系数
- **Bottom 20 实体**（机械分最低）：person-amadou-nionson-diarra(18)、person-sidi-ongoiba(18)、person-ibrahim-malam-dicko(19)、person-abou-ghosmane(20)、person-ousmane-dicko(20)、actor-katiba-serma(21)、person-youssouf-toloba(21)、actor-dozos-of-macina(22)、actor-dana-atem(26)、actor-katiba-hanifa(32)、person-jafar-dicko(37)、actor-niger-armed-forces(42)、person-abu-hanifa(51)、actor-slm-aw(52)、actor-hcua(53)、person-sadou-samahouna(53)、actor-cameroon-bir(54)、actor-ola(55)、actor-vdp(55)、actor-wagner-group(55)——完整排名见 entity-depth-audit.json
- **Bottom 20 关系**：rel-ssudan-sudan-spillover、rel-is-moz-tanzania-link、rel-fadm-mozambique-operates、rel-d1-fla-mali-operates、rel-d1-fla-fama-conflict、rel-d1-wagner-fama-coop、rel-d1-wagner-jnim-conflict、rel-d1-ansarul-burkina-operates、rel-d1-abu-hanifa-niger、rel-d1-sadou-burkina-history、rel-d1-niger-army-niger、rel-d1-ansaru-jas-split、rel-d1-lakurawa-nigeria-operates、rel-d1-lakurawa-niger-operates、rel-d1-dan-na-mali-operates、rel-d2-ousmane-burkina、rel-d2-katiba-hanifa-niger、rel-d2-katiba-hanifa-burkina、rel-d2-katiba-serma-mali、rel-d2-katiba-serma-burkina——完整排名见 relation-depth-audit.json

## 4. 三组阻断级事实清洗（source-of-truth + generator 安全）

| 纠错 | 目标 | 结果 |
|---|---|---|
| DEPTHA-FIX-KOUFA-001 | person-amadou-koufa + 3 关系 | Koufa **复活**：current_status=active_jnim_deputy_and_katiba_macina_emir、freshness=current、claim_valid_as_of=2026-08-08；profile 的 current_assessment/history/controversies/roles 清除“已死亡/2019被击毙/继任者”表述，改为“曾被错误宣布死亡、后证伪”；rel-koufa-* 的 summary/uncertainties 同步更新 |
| DEPTHA-FIX-ISSAHEL-001 | actor-is-sahel + rel-jnim-is-conflict | Sahrawi 死亡=**2021 年 8 月**（清除 2023 表述）；JNIM—IS 直接冲突=**始于 2019**，2026-04=首次明确扩展进入尼日尔（非“首次交火”） |
| DEPTHA-FIX-MOURABITOUN-001 | actor-al-mourabitoun | 谱系=**MUJAO + Belmokhtar/Al-Mulathameen 体系**；清除“Iyad Ag Ghali 的穆拉比通/副手/领导关系”（数据中本无 Iyad→Mourabitoun 关系，profile 文本亦无残留） |

**Residual 检查**：4 组错误表述在 source data（entity_profiles/relation_profiles/timelines/relationships/entities/evidence）与 dist HTML 中全部 = 0（integrity gate 断言）。

## 5. 11 个实体升级（前后对比，完整见 upgrade-comparison.json）

| 实体 | 前（机械分/深度） | 后（成熟度） |
|---|---|---|
| actor-jnim | encyclopedia_full (85) | **E3** · 33 章节 · 2248 中文字 · 10 sources · 59 evidence |
| actor-is-sahel | encyclopedia_full (80) | **E3** · 23 章节 · 1162 字 · 7 sources · 19 evidence |
| person-amadou-koufa | standard (62) | **E3** · 18 章节 · 834 字 · 6 sources · 6 evidence |
| actor-katiba-macina | encyclopedia_full (70) | **E3** · 23 章节 · 1179 字 · 6 sources · 5 evidence |
| person-iyad-ag-ghali | standard (68) | **E3** · 18 章节 · 643 字 · 6 sources · 7 evidence |
| actor-aqim | encyclopedia_full (70) | **E3** · 21 章节 · 970 字 · 6 sources · 6 evidence |
| actor-al-mourabitoun | encyclopedia_full (68) | **E2** · 19 章节 · 1052 字 · 谱系纠正 |
| actor-ansarul-islam | standard (62) | **E2** · 12 章节 · 431 字 |
| actor-fla | encyclopedia_full (70) | **E3** · 14 章节 · 534 字 · 5 sources · 4 evidence |
| actor-africa-corps | encyclopedia_full (63) | **E3** · 15 章节 · 459 字 · 4 sources · 6 evidence |
| actor-wagner-group | standard (55) | **E2** · 12 章节 · 272 字 |

- 全部保留 entity_id/slug/importance_level；新增 content_maturity + depth_score 元数据
- E3 必备：lead + 时间线 + 当前态势 + 不确定性 + ASIP Analysis + Watch Indicators + 来源

## 6. 11 条关系升级（前后对比）

| 关系 | 前 | 后 |
|---|---|---|
| rel-jnim-is-conflict | R1 (25) | **R3** · zh 308 · tl 2 · hostile_to 保持、start=2019 |
| rel-jnim-alqaida-affiliate | R1 (43) | **R3** · zh 449 · tl 3 |
| rel-jnim-aqim-constituent | R0 (6) | **R3** · zh 92 · tl 4（evolution→timeline） |
| rel-jnim-katiba-constituent | R0 (6) | **R2** |
| rel-jnim-iyad-led | R0 (8) | **R2** |
| rel-koufa-jnim-senior | R0 (4) | **R2**（Koufa 活跃语义） |
| rel-d1-ansarul-jnim-constituent | R1 (21) | **R2** |
| rel-d1-fla-jnim-cooperation | R1 (25) | **R3** · tl 3 · **仍 cooperates_with** |
| rel-d1-africa-corps-fama-coop | R1 (25) | **R3** · tl 3 |
| rel-d1-africa-corps-wagner-history | R1 (21) | **R3** · tl 2 |
| rel-koufa-katiba-founder | R0 (4) | **R2**（Koufa 活跃语义） |

- 未新建重复关系、未改基础 relationship_type

## 7. 三组事实错误在 source / generator / dist / production 清零

- source data residual = 0（integrity gate 断言）
- generator：无 Koufa 死亡等硬编码（regen diff relation_type_change=0 等 8 项全 0）
- dist：build 后 dist HTML residual = 0（integrity gate 扫描）
- production：公网页面（54167ed 部署后）实测无错误表述（公网 QA 全绿 + 内容由新数据渲染）

## 8. E3 / R3 页面实际显示数据

**E3 实体页**（章节数/中文字数/sources/evidence）：
JNIM 33/2248/10/59 · IS Sahel 23/1162/7/19 · Koufa 18/834/6/6 · Katiba Macina 23/1179/6/5 · Iyad 18/643/6/7 · AQIM 21/970/6/6 · FLA 14/534/5/4 · Africa Corps 15/459/4/6

**R3 关系页**（档案字段数/中文字数/sources/evidence/timeline）：
JNIM-IS 24/308/5/5/2 · JNIM-Al-Qaida 30/449/6/3/3 · JNIM-AQIM 14/92/6/4/4 · FLA-JNIM 20/227/4/2/3 · FAMa-Africa Corps 19/161/3/3/3 · Wagner-Africa Corps 19/143/3/3/2

## 9. Facts / ASIP Analysis / Watch Indicators 分区

- **明确分区**：事实章节（facts）先渲染，随后 **ASIP Analysis · 平台分析**（蓝色独立卡）与 **Watch Indicators · 后续观察指标**（琥珀色紧凑卡）独立展示；成熟度徽章 E0-E3 / R0-R3 显示于页面头部
- ASIP Analysis 内容不生成 verified evidence（packet `analytical_uncertainty` → partially_verified，不升级）
- 实测：本地 QA 33 个 analysis 分区、30 个 watch 分区、22/22 升级页徽章；公网 QA 完全一致
- 兵力数字（JNIM 约/至少 6000、IS Sahel 约 2500、Africa Corps 约 2000）保留日期/范围/估计限定词（专项测试 force_estimate_temporality 断言）

## 10. Source / Evidence 映射

- 22 候选 → **12 新增 + 10 复用**（URL exact / normalized / publisher+title；`deptha-nctc-jnim-2026-05` 等复用既有 d2 同 URL source）；null published_at 保留（NCTC/ACLED 等，未猜日期）；SOURCE_DATE_SCHEMA_BLOCKER=0
- 20 claims → ev-deptha-001..020；`analytical_uncertainty`（deptha-ev-013）→ partially_verified；`verified_with_estimate`（deptha-ev-019）→ verified + 估计限定；全部 refs resolve

## 11. Generator 一致性

- regen diff **8 项全 0**：unexpected_object_deletions=0 / entity_count_change=0 / relationship_count_change=0 / importance_level_change=0 / relation_type_change=0 / profile_depth_regressions=0 / timeline_regressions=0 / evidence_regressions=0
- 导入幂等（sections merge、timeline 生成去重、fact cleanup 短语幂等）

## 12. 构建与回归

- `build_site.py --no-embed` → **249 routes**（数量不变）
- 全回归：**Python 33/33、Node 4/4、build PASS、metrics 一致、local path 0、路由齐全，FAIL_TOTAL=0**
- 专项 11 测试全 PASS（no_count_expansion / koufa_alive / is_sahel_dates / mourabitoun_genealogy / jnim_e3_sections / fact_analysis_separation / watch_indicators / relation_r3_completeness / force_estimate_temporality / generator_regression / depth_audit）

## 13. 浏览器 QA

- 本地候选：50 页 PASS（11 升级实体 + 11 升级关系 + 索引 + 四视口代表页，0 错误 0 溢出，22/22 徽章、33/30 分区）
- Network：JNIM / IS Sahel / Koufa / Katiba Macina / Iyad / FLA / Africa Corps 七焦点密度 PASS（无重复节点、焦点切换正确）
- **公网 50 页 PASS**：11 升级实体全部 200、11 升级关系全部 200；1920/1366/768/390 四视口；consoleErrors=0、runtimeExceptions=0、failedRequests=0、brokenAssets=0、horizontalOverflow=0；22/22 徽章、33/30 分区（与本地一致）；公网 Network QA PASS
- 注：首次公网跑因 github.io CDN 边缘缓存传播出现徽章/分区随机缺失，QA 改为“预热浏览器缓存到新 bundle 后全量”后稳定全绿（产品本身经本地 QA 验证无问题）

## 14. Production 隔离

- production diff：仅 `intelligence/africa/**`（8 data 文件）+ `assets/js/intelligence/africa.js` + `assets/css/intelligence.css` 变更；主站仅 build 元数据；RC 预览保留；**UNEXPECTED_MODIFIED=0 / UNEXPECTED_DELETED=0 / UNEXPECTED_ADDED=0**

## 15. 十一项 Gate

DEPTHA_BASELINE_GATE / DEPTHA_AUDIT_GATE / DEPTHA_FACT_CLEANUP_GATE / DEPTHA_ENTITY_DEPTH_GATE / DEPTHA_RELATION_DEPTH_GATE / DEPTHA_SOURCE_EVIDENCE_GATE / DEPTHA_FACT_ANALYSIS_SEPARATION_GATE / DEPTHA_GENERATOR_GATE / DEPTHA_BUILD_GATE / DEPTHA_PUBLIC_QA_GATE / DEPTHA_PRODUCTION_ISOLATION_GATE —— **全部 PASS**

## 16. 下一批厚度升级候选（仅提出，未执行）

依据机械 Audit 的 Bottom 排名，下一批候选（按优先级）：
1. **person-amadou-nionson-diarra / person-sidi-ongoiba / person-ibrahim-malam-dicko**（机械分 18-19，仅 4 章节）→ 升级到 E2
2. **actor-katiba-serma / person-youssouf-toloba / actor-dozos-of-macina / actor-dana-atem**（机械分 21-26）→ 中马里 Dozo 板块整体 E2/E3
3. **actor-katiba-hanifa / person-jafar-dicko / person-abou-ghosmane / person-ousmane-dicko**（机械分 20-37）→ JNIM 区域指挥链补全
4. **actor-niger-armed-forces**（机械分 42，仅 1 source）→ 尼日尔安全力量深度化
5. 关系侧：**rel-d2-katiba-serma-mali/burkina、rel-d2-katiba-hanifa-niger/burkina、rel-d1-lakurawa-nigeria/niger-operates** 等 R0/R1 → 至少 R2

## 17. 最终状态

**DEPTH A = CLOSED**。未新增实体/关系/国家/ontology；未开发地图；未自动执行下一批厚度升级；未开始扩广度。
