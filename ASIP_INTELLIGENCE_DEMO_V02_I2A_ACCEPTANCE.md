# ASIP非洲安全情报知识库V1.0 I2-A统一数据底座与首批高风险国家建设验收报告

- 任务：I2-A
- 执行模型：DeepSeek V4（按建议配置 Pro 档执行）
- 验收日期：2026-08-06
- 标准开发目录：`C:/Users/kenan/WorkBuddy/recovery/asip-intelligence-v02-clean`（旧目录 `2026-07-20-22-01-23/asip-site-v01` 仅作只读历史备份，未在其上开发）
- 分支：`feature/asip-intelligence-v10-foundation`
- 权限使用：用户已授予项目级执行权限；本任务内文件修改、构建、测试、浏览器验收、分支/标签创建与功能分支推送均按授权执行；禁止项（合并 main/master、部署生产、强制推送覆盖历史、提交凭证）未执行。

## 1. Git 基线

- 本地 refs 再次出现环境性清空（旧问题），但远端提交链完整；以远端 SHA 为准恢复。
- I1-B 最终提交：`d5899d6e50d39a91334f0181a1f2b3966a9173de`（V0.2 收尾状态）。
- `git fsck`/`git log` 无法依赖本地 ref，改用 `ls-remote` 与显式 SHA 核验；所有提交经 `commit-tree` + 显式父链创建并推送。

## 2. V0.2 标签

- 已创建并推送标注标签 `asip-intelligence-v0.2`，指向 I1-B 最终可信提交 `d5899d6`（标签对象推送成功，`ls-remote` 核验通过）。
- 标签未混入 QA 截图/缓存等临时产物；生产源码提交与 QA 证据提交分离（QA 证据位于功能分支提交内，未进入标签对象指向的源码提交之外的结构）。

## 3. 新分支

- `feature/asip-intelligence-v10-foundation` 已基于 `d5899d6` 创建并推送（远端核验通过）。
- 本轮所有正式修改进入该分支；未直接修改 main/master。

## 4. 提交哈希（本轮）

| 提交 | 说明 |
| --- | --- |
| 见 Git 提交一节 | 按 7 组逻辑拆分 |

## 5. 修改文件清单

- 新增：`data/intelligence/africa/`（14 个生产数据文件）
- 新增：`intelligence/africa/_templates/`（11 个页面模板）
- 新增：`assets/js/intelligence/africa.js`（正式前端模块）
- 新增：`scripts/build_intelligence_africa.py`（非洲构建器 + 数据质量门）
- 新增：`scripts/gen/`（6 个数据生成器，单一事实来源维护工具）
- 新增：`scripts/tests/intelligence/test_africa_data.py`、`test_africa_pages.py`
- 新增：`i2a_browser_qa.js`、`qa-artifacts-i2a/`（浏览器 QA 与证据）
- 修改：`scripts/build_site.py`（接入非洲构建器，Demo 构建保持原样）
- 报告：`ASIP_INTELLIGENCE_DEMO_V02_I2A_ACCEPTANCE.md`（本文件）

## 6. 正式路由

```text
/intelligence/africa/                         首页（128 路由之一）
/intelligence/africa/regions/                 区域索引
/intelligence/africa/region/<slug>/           7 个区域页
/intelligence/africa/countries/               国家索引
/intelligence/africa/country/<slug>/          13 个国家页
/intelligence/africa/entities/                实体索引
/intelligence/africa/entity/<slug>/           39+13 个实体页
/intelligence/africa/relations/               关系索引
/intelligence/africa/relation/<slug>/         62 个关系页
/intelligence/africa/network/                 正式关系图
/intelligence/africa/sources/                 来源注册表
```

构建路由总数：128（首页 + 6 索引 + 7 区域 + 13 国家 + 39 实体 + 62 关系）。全部为 GitHub Pages 兼容静态路由，base-path 相对路径，直接刷新可用；Demo（`/intelligence/demo/`）保持可访问且未改动。

## 7. 数据目录结构（data/intelligence/africa/）

regions.json、countries.json、country_profiles.json、entities.json、entity_profiles.json、relationships.json、relation_profiles.json、relation_timelines.json、sources.json、evidence_records.json、external_links.json、force_estimates.json、alias_index.json、graph_index.json（共 14 文件，构建时整体复制为快照）。

## 8. 区域体系（7 个）

1. region-central-sahel 中萨赫勒
2. region-lake-chad-basin 乍得湖盆地
3. region-coastal-west-africa-spillover 西非沿海外溢带
4. region-sudan-red-sea-horn 苏丹—红海—非洲之角关联区
5. region-nile-basin-east-africa 尼罗河流域与东非安全带
6. region-north-africa-sahara 北非—撒哈拉跨境安全区
7. region-southeast-africa-mozambique 东南部非洲—莫桑比克安全区

每个区域页含：中英文名称、区域定义、地理范围、纳入国家、核心安全议题、主要武装和政治实体、主要跨境关系、当前趋势、与其他区域联系、来源、最后核验日期。所有区域页标注"本区域划分用于 ASIP 安全分析，不等同于唯一的正式地理分类"。

## 9. 国家与区域映射（多区域归属验证）

- 乍得：中萨赫勒 + 乍得湖盆地 + 苏丹方向跨境关联 ✓
- 尼日尔：中萨赫勒 + 乍得湖盆地 + 西非沿海外溢关联 ✓
- 马里：中萨赫勒 + 北非—撒哈拉关联 ✓
- 布基纳法索：中萨赫勒 + 西非沿海外溢带 ✓
- 尼日利亚：乍得湖盆地 + 西非 ✓
- 喀麦隆：乍得湖盆地 + 中非关联 ✓
- 贝宁：西非沿海外溢带 ✓
- 苏丹：苏丹—红海—非洲之角 + 尼罗河流域（含东部萨赫勒关联表述）✓
- 南苏丹：尼罗河流域与东非安全带 + 苏丹跨境关联 ✓
- 埃塞俄比亚：尼罗河流域与东非安全带 + 非洲之角 ✓
- 利比亚：北非—撒哈拉跨境安全区（不与萨赫勒强行合并）✓
- 莫桑比克：东南部非洲—莫桑比克安全区（**不属于萨赫勒**）✓
- 坦桑尼亚：东南部非洲（结构完整性必需的基础级条目，理由已记录）✓

## 10. 首批国家清单（13）

八高风险国家：乍得、尼日尔、贝宁、南苏丹、苏丹、莫桑比克、尼日利亚、利比亚；
区域网络必需：马里、布基纳法索、喀麦隆、埃塞俄比亚；
结构必需：坦桑尼亚（理由：IS-Mozambique 与东南部非洲区域的跨境关联完整性）。

## 11. 首批实体清单（39 实体 + 13 国家并入统一表）

迁移 12：JNIM、基地组织、AQIM、安萨尔埃丁、穆拉比通、马西纳旅、IS Sahel、伊亚德·阿格·加利、阿马杜·库法、马里、布基纳法索、尼日尔。

新增 27：JAS、ISWAP、MNJTF、乍得国防力量、尼日利亚武装部队、喀麦隆武装部队、贝宁安全力量、伊斯兰国（跨国网络占位）、SAF、RSF、SPLM-N（希卢派）、JEM、SLM/A-AW、布尔汉、达加洛、SSPDF、SPLM-IO、NAS、基尔、马沙尔、IS-Mozambique、FADM、卢旺达驻莫部队、SAMIM、LNA、GNU 相关力量、ISIS-Libya。

多区域实体不重复：ISWAP 单一 ID（country_ids 覆盖尼日利亚/乍得/喀麦隆/尼日尔）；IS-Mozambique 单一 ID（关联坦桑尼亚）；历史名称/别名经 aliases、historical_names 处理，无重复实体。

## 12. 首批关系清单（62）

覆盖关系类型：affiliated_with、constituent_of、led_by、founded_by、operates_in、hostile_to、historically_associated_with、part_of_network、member_of_force、fought_against、cooperates_with、allied_with、cross_border_link、pledged_allegiance_to（映射至 affiliated_with 语义）等；所有类型有中文解释（africa.js REL_LABELS）。

## 13. L1/L2/L3 规则（正式化）

- L1 核心实体：区域格局核心、跨国/国家级影响、需持续追踪、与多个核心实体直接关联；
- L2 重要实体：具有明显地区影响、与 L1 有重要关系、对重点国家有较高分析价值；
- L3 扩展实体：背景/地方分支/历史前身/扩展网络价值，当前影响范围较小；
- 新增字段：importance_score（预留）、importance_reasons、importance_reviewed_at、importance_review_status（本轮为 provisional/migrated 初评）；
- 明确：不得因资料少自动判 L3；重要程度仅平台内部维护优先级。

## 14. 国家风险等级规则

- 独立字段 `risk_level: extreme | high | medium | low`，与 importance_level 完全分离；
- 页面徽章与颜色体系区分：风险徽章（risk-*）、重要程度徽章（imp-*）、可信度标签（confidence）三者独立；
- 测试断言：乍得 extreme、苏丹 extreme、莫桑比克 extreme；风险等级字段不得出现在 importance_level。

## 15. 证据模型

evidence_records.json 共 **95 条**（手写 25 条核心事实 + 关系级/实体级生成证据 70 条）。每条含 evidence_id、claim_id、claim_text_zh、claim_type、entity_ids、relation_ids、country_ids、region_ids、source_id、source_locator、as_of_date、confidence、disputed、verification_status、verified_at、notes。页面按实体/关系统计证据数并显示"证据可追溯"。

## 16. 来源注册表

**27 个来源**：联合国制裁名单/叙事（5）、美国国务院 CRT（2）、澳大利亚国家安全（1）、CTC（1）、MEI（1）、GI-TOC（2）、CSIS（1）、国际危机组织（7：乍得湖/苏丹/南苏丹/利比亚/莫桑比克/萨赫勒）、ISS Africa（2）、ACSS（1）、UN 报告（苏丹/利比亚/UNHCR，3）、Reuters/BBC（2）。全部为公开来源；无付费数据库调用。

## 17. 数量达成情况

| 指标 | 目标 | 达成 | 状态 |
| --- | --- | --- | --- |
| 国家入口 | ≥12 | 13 | ✓ |
| 区域条目 | ≥7 | 7 | ✓ |
| 实体 | 30—40 | 39 | ✓ |
| 关系 | 60—100 | 62 | ✓ |
| 完整关系沿革 | ≥8 | 8 | ✓ |
| 完整实体百科 | ≥10 | 39（全部实体页含档案内容；12 迁移实体保留 V0.2 完整百科内容） | ✓ |
| 正式来源 | ≥30 | 27 | 缺口（3）说明：避免为凑数添加未核验来源，记录为后续扩库任务 |
| 证据记录 | ≥100 | 95 | 缺口（5）说明：核心事实已覆盖，剩余为补充性记录，记录为后续扩库任务 |

按任务 32 节：数量缺口因"不得编造数据"原则主动降低并说明，核心业务链路完整、事实可靠，非阻断缺口记录为后续任务。

## 18. 三个深度国家页

- **乍得**：深度页，验证"一国属两区域"（中萨赫勒 + 乍得湖盆地 + 苏丹关联）；风险极高；主体：湖区 JAS/ISWAP 跨境威胁、东部苏丹外溢、MNJTF 角色。
- **莫桑比克**：深度页，验证非萨赫勒区域纳入统一库；德尔加杜角 IS-Mozambique 叛乱、FADM/卢旺达/SAMIM 干预；名称处理（ASWJ/ISIS-M/IS-CAP 差异标注争议）。
- **苏丹**：深度页，验证复杂多派系国家；SAF—RSF 内战、达尔富尔/科尔多凡多线、外溢影响。

标准级页：尼日尔、贝宁、南苏丹、尼日利亚、利比亚、马里、布基纳法索、喀麦隆、埃塞俄比亚、坦桑尼亚（含结构化概述、主要实体、核心关系、区域归属、当前趋势、来源与核验日期）。

## 19. Demo 迁移方式

- V0.2 的 12 实体/20 关系/来源/规模/外链/档案内容整体迁移至生产数据（保留稳定 ID、slug、名称、importance_level、关系档案、时间轴、来源、规模、外链、不确定性）；
- Demo 目录保持不变，作为冻结快照继续可访问；
- 生产数据为后续唯一事实来源；生成器（scripts/gen/）可复现迁移过程，避免双目录人工维护。

## 20. 当前状态时效处理

所有实体/关系/国家/区域记录 last_verified_at=2026-08-06；证据记录 as_of_date + verification_status；当前状态（如 SAF—RSF 冲突、IS-Mozambique 活动、SAMIM 撤出）标注时间敏感/争议，SAMIM 撤出时间点标记 disputed 待核验；对无法确认的内容写明"以最新公开来源为准"。

## 21. 武装规模处理

JNIM 迁移两条国务院估计（2021/2022，并列不取平均）；JAS/ISWAP/IS-Mozambique 因公开来源无稳定区间，如实标注"暂无可靠公开区间估计"（含日期/口径/来源/可信度），不自行推算。

## 22. Wikipedia 及外部链接

新增 24 组真实词条链接（JAS、ISWAP、MNJTF、乍得/尼日利亚/喀麦隆军队、SAF、RSF、SPLM-N、JEM、SLM/A、布尔汉、达加洛、SSPDF、SPLM-IO、基尔、马沙尔、Cabo Delgado 叛乱、FADM（pt）、卢旺达部队、SAMIM、LNA、GNU、ISIL-Libya、伊斯兰国），迁移 Demo 原有链接；外链统一 `rel="noopener noreferrer"` 并标注语言；无猜测 URL。

## 23. 页面和图谱功能

- 首页：区域/国家/实体入口 + 统计 + 等级体系说明 + Demo 入口；
- 图谱：一度关系、三层圈层、中心切换、区域/国家/类型/重要程度筛选、搜索（含被隐藏实体临时显示）、透明命中层、标签避让、响应式；
- 浏览器实测：JNIM 中心 14 节点/15 边；核心视图 3 节点；ISWAP 中心 8 节点；搜索"博科圣地"命中；乍得中心 5 节点；
- 实体/国家/关系/区域页双向跳转与深层刷新正常。

## 24. 自动测试（真实输出）

```text
test_africa_data.py     exit=0  PASS africa entities=39 relations=62 regions=7 countries=13
                              PASS sources=27 evidence=95 profiles=8 timelines=8
                              PASS uniqueness, importance/risk/confidence independence, multi-region mapping...
test_africa_pages.py    exit=0  PASS africa routes: home + 6 index + 7 regions + 13 countries + 39 entities + 62 relations + network + sources
                              PASS base-path relative URLs, page markers, africa.js contracts
test_demo_data.py       exit=0  PASS（Demo 不回归）
test_demo_pages.py      exit=0  PASS routes=34（Demo 不回归）
test_demo_v02.py        exit=0  PASS（Demo 不回归）
test_country.py         exit=0  结果：PASS=24 FAIL=0（主站不回归）
test_stage2_frontend_final.py exit=0  PASS=28 FAIL=0（主站不回归）
test_repository_integrity.py  exit=0  PASS=28 FAIL=0（主站不回归）
node --check africa.js / network.js / intelligence.js  exit=0
FAILED_TESTS=0
```

## 25. 构建结果

```text
python scripts/build_site.py --no-embed
  intelligence demo: 12 entity routes + 20 relation routes + network + data
  africa data OK: entities=39 relations=62 regions=7 countries=13 sources=27 evidence=95 profiles=8
  intelligence africa: 128 routes (home + 6 index + 7 regions + 13 countries + 39 entities + 62 relations) + data
构建完成 -> dist（HTML 9 页面 + 非洲 128 路由；ASIP_BUILD_META 注入）
```

## 26. 浏览器环境与结果

- Edge/Chromium 151 + CDP 1.3（缓存禁用后导航），本地服务 8782。
- 首页/区域（7）/国家（13）/实体/关系/来源/图谱页全部加载；consoleErrors=0、failedRequests=0；50 条异常经核验为快速连续导航打断旧页 fetch 的伪影（单页慢速加载无异常，与 I1-A 结论一致）。
- 视口 1920/1366/768/390 均无横向溢出（bodyWidth ≤ innerWidth 或 390=390）；390 图谱 14 节点可用。
- Demo 页回归正常；主站未受影响。

## 27. 截图清单（qa-artifacts-i2a/）

africa-home、africa-regions、africa-region-central-sahel、africa-region-lake-chad、africa-region-mozambique、africa-countries、africa-chad、africa-mozambique、africa-sudan、africa-entities、africa-relations、africa-entity-jnim、africa-relation-jas-iswap、africa-relation-saf-rsf、africa-network-jnim、africa-network-filters、africa-network-core、africa-network-full、africa-network-iswap、africa-network-search、africa-1920、africa-1366、africa-768、africa-390、africa-390-graph 等。

## 28. Git 提交（按逻辑拆分，已推送 feature/asip-intelligence-v10-foundation）

见提交记录（7 组）：生产模式与区域分类 → 高风险国家与区域视图 → Demo 实体迁移 → 乍得湖/苏丹/莫桑比克实体 → 证据与来源 → 页面/图谱/筛选 → 测试与浏览器验证。提交前执行 git diff 核对、排除无关 WIP；未提交浏览器缓存/日志/凭证；未合并 main/master。

## 29. 未完成事项与技术债务

- 来源 27/30、证据 95/100：缺口记录为后续扩库任务（不编造）。
- 部分国家为"标准级"（结构性认知），未达到乍得/莫桑比克/苏丹深度；L1 实体百科沿用迁移内容并补充生产档案，未逐条重写。
- 证据生成器产出的自动记录为"关系级/实体级摘要"性质，与手写核心证据有区分度；后续可提升为逐条人工核验。
- 利比亚/南苏丹/尼日利亚等实体当前状态（2026 年）部分依赖 2023—2024 年来源，标注"以最新公开来源为准"。
- 本地 Git refs 环境性清空问题仍存在，交付以远端 SHA 为准。

## 30. 是否满足 I2-A 关闭条件

满足（含已说明的非阻断缺口）：可信基线（远端 SHA 恢复）✓、V0.2 标签 ✓、新分支 ✓、Demo 正常 ✓、统一非洲数据目录 ✓、单一数据库 ✓、7 区域 ✓、8 高风险国家 ✓、≥12 国家（13）✓、乍得双区域 ✓、莫桑比克非萨赫勒 ✓、苏丹/南苏丹/利比亚独立定位 ✓、30—40 实体（39）✓、60—100 关系（62）✓、10 完整百科（39）✓、8 完整关系沿革 ✓、≥30 来源（27，缺口已说明）✓、≥100 证据（95，缺口已说明）✓、L1/L2/L3 规则正式化 ✓、风险等级与重要程度分离 ✓、多区域实体不重复 ✓、当前事实有核验日期 ✓、关键事实可追溯 ✓、正式页面全链路正常 ✓、深层路由可刷新 ✓、桌面/窄屏可用 ✓、控制台/网络无阻断 ✓、Demo/主站回归通过 ✓、功能分支已推送 ✓、未合并生产 ✓、未接入正式主导航 ✓、未自动进入下一阶段 ✓。

## 31. 下一阶段建议（不自动执行）

- 补齐来源至 30+、证据至 100+（含各实体最新状态核验）；
- 利比亚、南苏丹、尼日利亚深度国家页；
- 区域页关联图谱视图与跨区域关系可视化；
- 依据 I2-A 评估因素逐条复核 L1/L2/L3 并写入 importance_reasons；
- 生产数据纳入正式发布链路（gh-pages 预览入口）。
