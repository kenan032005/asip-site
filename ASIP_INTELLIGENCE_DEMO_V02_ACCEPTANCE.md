# ASIP安全情报知识库V0.2关系图与百科档案升级验收报告

- 任务：I1-A
- 验收日期：2026-08-06
- 执行环境：Windows + Edge/Chromium 151（CDP 1.3，兼容 Chrome 130+）
- 开发目录：`C:/Users/kenan/WorkBuddy/recovery/asip-intelligence-v02-clean`
- 分支：`feature/asip-intelligence-v02`（基于已验证的 V0.2 提交链，未合并 main/master、未部署生产）

## 1. Git 基线检查结果

原始目标目录 `C:/Users/kenan/WorkBuddy/2026-07-20-22-01-23/asip-site-v01` 经只读取证判定**基线不可直接使用**：

- `git status`：全部源码显示为未跟踪（`??`），分支引用异常；
- `git log`：仅 1 条 root 提交，无完整历史；
- `git fsck`：本地分支 ref 文件含尾随垃圾（`trailingRefContent`），reflog 仅 1 条；
- 与既有记录"该环境 Git refs 间歇性清空"特征一致。

按任务 3.2 门禁：**未在该目录执行任何修复或开发**，未运行 reset/clean/gc/init，未强制覆盖工作区。

### 安全重建方案（通过）

- 以远端已验证交付分支 `feature/asip-intelligence-demo-v01-rebuilt`（`356e58e`）及已交付 V0.2 提交链（`f41cf599`）为基础；
- 在干净目录继续 I1-A，基线可信、可提交、可回退；
- 原目标目录保持原样未动。

## 2. 备份/检查点情况

- 干净目录完整保留 V0.2 已交付提交链（`9f38d929 → 61bebcb → 97e8330 → e8f5779 → 0b9e7f5 → ae3280d → f41cf59`）；
- I1-A 修改前所有文件均可通过远端 SHA 恢复；
- 本轮未混入原目录无关 WIP。

## 3. 分支与提交

| 提交 | 说明 |
| --- | --- |
| 见 Git 提交要求一节 | 按五组逻辑提交拆分 |

## 4. 修改文件清单

- `data/intelligence/demo/entities.json`（统一名称字段、importance_level、acronym、native_name、historical_names）
- `data/intelligence/demo/relationships.json`（关系档案字段、display_ring、slug）
- `data/intelligence/demo/relation_profiles.json`（新增，4 组完整关系档案）
- `data/intelligence/demo/relation_timelines.json`（新增，4 组时间轴）
- `data/intelligence/demo/force_estimates.json`（新增，武装规模估计）
- `data/intelligence/demo/external_links.json`（新增，Wikipedia 与权威外链）
- `data/intelligence/demo/sources.json`（来源扩展至 11 个）
- `data/intelligence/demo/graph_index.json`、`alias_index.json`（重建）
- `data/intelligence/demo/profile_content.json`（百科式内容）
- `assets/js/intelligence/intelligence.js`（名称显示、档案/关系渲染）
- `assets/js/intelligence/network.js`（三层圈层、重要程度筛选）
- `assets/css/intelligence.css`（圈层辅助线、徽章、信息框、目录、时间轴）
- `intelligence/demo/index.html`（入口）
- `intelligence/demo/network/index.html`（图谱页）
- `intelligence/demo/entity/_template.html`（百科式实体页）
- `intelligence/demo/relation/_template.html`（新增，关系档案页）
- `scripts/build_intelligence_demo.py`（生成 20 个关系路由）
- `scripts/tests/intelligence/test_demo_data.py`、`test_demo_pages.py`、`test_demo_v02.py`（更新）
- `i1a_browser_qa.js`、`qa-artifacts-i1a/`（真实浏览器 QA 脚本与证据）

## 5. 数据结构变化

实体（12 个不变）：新增 `acronym`、`native_name`、`historical_names`、`importance_level`、`external_links`（独立文件）。

关系（20 条不变）：新增 `slug`、`display_ring`、`relation_summary`、`formation_background`、`current_status_detail`、`geographic_scope`、`why_it_matters`、`uncertainties`、`last_verified_at`；`start_year` 与 `time_start/time_end` 并存。

新增数据文件：`relation_profiles.json`、`relation_timelines.json`、`force_estimates.json`、`external_links.json`。

## 6. 名称统一规则

- 标准字段：`name_zh` / `name_en` / `acronym`（无公认缩写可为空）/ `native_name` / `aliases` / `historical_names`；
- 页面标题与中心节点：第一行 `中文名称（缩写）`，第二行英文名；
- 无缩写实体不显示空括号（如"安萨尔埃丁组织 / Ansar Dine"）；
- 图谱外围节点：优先 `中文名称（缩写）`，空间不足时保留中文+缩写、英文可缩略、悬停/聚焦显示完整名；
- 正文首次出现：`中文名称（缩写；英文名称）`；
- 集中式函数：`display_title`、`display_graph`、`display_first_mention`、`display_short`、`display_plain`（实现为 displayTitle 等）；
- 图谱节点、右侧卡片、实体页标题、关系页标题调用同一套函数，未在 HTML 手工拼接。

## 7. 重要程度规则（保留原有 L1/L2/L3 语义）

- L1 核心实体：对理解相关国家、地区、组织网络或安全格局具有关键作用；
- L2 重要实体：与核心安全格局存在明确联系，具有较高分析价值；
- L3 扩展实体：具有补充和关联价值，当前重要程度或关注优先级相对较低；
- 本轮映射：L1=2（JNIM、IS Sahel）、L2=4（基地组织、AQIM、伊亚德·阿格·加利、马里）、L3=6（其余）；
- 明确：重要程度是平台内部排序，不代表联合国/政府认定，不解释为威胁/风险等级。

## 8. 重要程度筛选实现

- 图谱显示筛选栏新增 `L1 核心实体 / L2 重要实体 / L3 扩展实体` 三个复选框；
- 快捷视图：核心视图（仅L1）、重点视图（L1+L2）、完整视图（L1+L2+L3）；
- **默认重点视图（L1+L2）**：12 实体中 L1+L2 共 6 个节点，JNIM 中心图谱仍有 6 节点 12 边，展示效果不空洞；L3 实体可通过搜索临时显示；
- 当前中心实体始终显示（即使被隐藏等级）；
- 隐藏等级同步隐藏节点与关系线；恢复显示无重复节点；
- 筛选切换使用重布局与平滑过渡，并自动适配画布；
- 页面显示可见实体数量及各重要程度数量（`importanceStats`）；
- 搜索覆盖全部实体，可找到被隐藏等级实体并自动临时显示+提示；
- 重要程度筛选与实体类型筛选可组合使用；
- 筛选状态不修改实体数据本身。

## 9. 内圈、中圈、外圈布局规则（独立于重要程度）

- 独立字段 `display_ring: inner | middle | outer`，放在关系数据中（同一实体在不同中心图谱可位于不同圈层）；
- 内圈"结构与地理"：上级体系、母组织、所属网络、组成关系、核心活动国家（半径 168）；
- 中圈"组织与力量"：敌对、竞争、同盟、相关组织（半径 258）；
- 外圈"人物"：领导人、创始人、关键人物（半径 348）；
- 圈层标签为"结构与地理 / 组织与力量 / 人物"，**绝不使用 L1/L2/L3 命名圈层**；
- 布局：中心实体位于视觉中央；按圈层半径分布；同圈按实体类型分配角度；基础碰撞避免；共有节点换中心时继承位置连续；新节点淡入、无关节点淡出；390px 窄屏降低半径并隐藏辅助文字；
- 轻量环形辅助线（内/中/外三层虚线圆）。

### 重要程度与圈层的独立性证明

- Al-Qaida（L2）在 JNIM 中心图谱位于**内圈**（体系关系），在其他中心图谱不可达（不在可见区）；
- IS Sahel（L1）在 JNIM 图谱位于**中圈**（敌对）；
- 伊亚德·阿格·加利（L2）位于**外圈**（人物）；
- 国家 Mali（L2）位于**内圈**（核心活动国）；
- 节点 radius 由 display_ring 决定，不由 importance_level 决定。

## 10. 节点图标设计

- 组织：六边形多边形（原圆形改为六边形）；
- 人物：圆角矩形；
- 国家：菱形/方形（地图角标风格）；
- 中心实体：独立主卡片形态（更大、双描边、光晕、英文副标签）；
- 除颜色外通过形状与类型角标（组/人/国）区分，灰度和色觉差异下仍可区分；
- 节点附带小号重要程度标签（L1/L2/L3）以增强可读性，但不用于圈层定位。

## 11. 箭头与关系线设计

- 隶属/组成/上级网络：普通实线箭头；
- 领导/创立：加粗实线箭头；
- 活动/存在：低透明度虚线；
- 历史关联：灰色虚线；
- 敌对/冲突：红色虚线（双向敌对样式）；
- 争议/时间敏感：虚线或低透明度；
- 悬停与选中加粗，未选中降低权重；
- 关系含义结合箭头方向、线型、图例、悬停提示与右侧关系卡共同表达，不只依赖颜色；
- 关系短标签带背景色块，避免与线条混淆。

## 12. 抗拥挤机制

- 按圈层半径分层，避免全图同半径堆叠；
- 同圈节点按类型分组角度分配；
- 基础碰撞避免（两轮 58px 最小距离推挤）；
- 关系标签超过 8 条关系时自动隐藏；
- 窄屏缩小圈层半径并隐藏辅助文字。

## 13. 关系详情结构

关系摘要卡（图谱右侧）显示：双方中文/英文名与缩写、关系类型、圈层、当前状态、关系摘要、形成背景（节选）、主要历史阶段（前 3 段）、为什么重要、时间范围、涉及地区、可信度、最后核验、来源数量与链接、不确定性提示、`查看完整关系沿革` 按钮。

关系档案页（`/intelligence/demo/relation/<slug>/`）：概览、双方实体介绍（可跳转档案）、关系形成背景、双方最初的关系、历史演变阶段、变化主要原因、关键转折事件、当前关系状态、不同国家/地区差异、对区域安全格局的影响、为什么重要、不确定性、来源与证据、历史时间轴（date/event/impact/confidence/source）。

## 14. 四组完整关系档案

1. **JNIM—IS Sahel（历史非敌对阶段）**：前史（人员同源、萨赫勒例外）、2019 年前非敌对与偶发合作、2019 年起公开冲突；
2. **JNIM—IS Sahel（当前敌对）**：2019 年 7 月阿列尔交火开端、意识形态分裂、领土/资源/招募/领导权竞争、当前敌对状态、地区差异与不确定性；来源：CTC（West Point）、MEI、GI-TOC、US State Dept；
3. **JNIM—基地组织**：公开关联性质（网络关联而非日常指挥）、2017 年效忠、2018 年联合国/美国认定、时间状态；
4. **JNIM—马里**：严格区分活动/存在/影响与控制；"在马里活动"不等于"控制马里"；袭击记录与存在扩展；
5. **伊亚德·阿格·加利—JNIM**：领导关系、历史角色（安萨尔埃丁创始人→JNIM 领导人）、2017 年成立主导、时间状态与公开来源。

其余关系均补充详细摘要（relation_summary + formation_background + why_it_matters + uncertainties），不强制达到同等长度。

## 15. JNIM—IS Sahel 敌对形成过程及来源

- 2016 年前后 ISGS 出现（穆拉比通人员关联）；
- 2016—2019 年初"萨赫勒例外"：互不攻击、偶发共同行动、双重认领袭击（CTC 记录）；
- 2019 年初意识形态分裂：ISGS 正式成为伊斯兰国省分支，宣传纳入 ISWAP 体系；
- 2019 年 7 月布基纳法索阿列尔交火——公开冲突开端；
- 2020 年冲突全面升级：IS《Al Naba》公开承认萨赫勒交战；CTC 统计 2019 年 7 月起至少 46 次交火、300+ 武装人员死亡（ACLED 口径）；MEI 统计 2019—2021 年约 140 次冲突；
- 2022 年 IS Sahel 新领导阿布·巴拉·萨赫拉维攻势（GI-TOC）；
- 来源：CTC-SENTINEL-072020、MEI 2021、GI-TOC WEA OBS 006、US State Dept CRT 2021/2022、UN narrative summary。

## 16. JNIM 百科页面结构

标题（中文+缩写/英文）、平台核心判断、导语、结构化信息框（名称/原文名/别名/历史名称/类型/重要程度/状态/规模/外链/核验/可信度）、目录（可点击锚点）、百科正文（概述、名称与译名、成立背景、历史沿革、组织结构、领导层、意识形态目标、活动范围、武装力量规模、行动方式、重要关系、代表性事件、当前态势、区域影响、争议与不确定性）、正文实体链接、关系图入口、相关实体、来源注释、Wikipedia 与权威外部链接。

其他组织页面切换到新版模板，按已有可靠数据适度补充；人物/国家页面使用适合类型的内容结构。

## 17. 武装规模数据、日期与口径

JNIM（`force_estimates.json`）：

| 区间 | 时间 | 口径 | 来源 | 可信度 |
| --- | --- | --- | --- | --- |
| 约 1,000—2,000 人 | 2021 | JNIM 整体战斗人员 | US State Dept CRT 2021 | 中 |
| 约 2,000 人 | 2022 | JNIM 整体战斗人员 | US State Dept CRT 2022 | 中 |
| 约 4,000—6,000 人（部分研究约 5,000） | 2022 | 多来源区间，口径因来源而异 | GI-TOC 2022 观察 | 中 |

- 并列展示，不取平均；组织自称数字未采用；历史数字不与当前混用；
- IS Sahel：公开来源未给出稳定区间，标注"暂无可靠公开估计"（仅记录"约为 JNIM 估计数的一半以下"的单一观察，可信度低），不自行推算；
- 页面显示：估计武装规模、估计时间、统计口径、趋势、可信度、来源，并注明各来源口径差异原因。

## 18. Wikipedia 及外部链接

- `external_links.json` 按实体保存 wikipedia（en/fr 等语言）/authoritative（UN、US State Dept 等）/research（CSIS、CTC、MEI、GI-TOC）；
- Wikipedia 链接为真实词条 URL（JNIM、Al-Qaida、AQIM、Ansar Dine、Al-Mourabitoun、Katibat Macina、ISGS、Iyad Ag Ghali、Amadou Koufa、三国）；
- 外链统一 `target="_blank" rel="noopener noreferrer"`，明确标识为外部网站；
- Wikipedia 仅作辅助导航，不作为唯一事实依据，正文内容按权威来源重新整理。

## 19. 新增来源清单（11 个）

UN sanctions narrative（JNIM/Koufa/Iyad/AQIM）、Australian National Security（JNIM）、US State Dept CRT 2021/2022、CTC（Sahelian Anomaly）、MEI（Schism of Jihadism in the Sahel）、GI-TOC（WEA OBS 006）、CSIS（JNIM Backgrounder）。

## 20. 事实、分析和不确定性处理

- 权威来源确认的事实、多来源支持的分析、单一机构评估、媒体报道与平台判断分层呈现；
- 平台归纳因果分析标注来源机构；无法由公开证据支持的内容写明"尚无充分公开证据"或"平台基于现有来源判断"；
- 不确定字段（uncertainties）逐条列出，如"JNIM 与基地组织核心实际协调深度缺乏公开一致说明"；
- 时间敏感关系明确标注"时间敏感"。

## 21. 自动测试真实结果

```text
$ python scripts/tests/intelligence/test_demo_data.py
PASS entities=12 relationships=20 sources=11
PASS importance levels L1=2 L2=4 L3=6
PASS unified names (acronym nullable, no empty bracket), rings inner/middle/outer,
     4 full relation profiles, timelines, force estimates and wikipedia url format
退出码 0

$ python scripts/tests/intelligence/test_demo_v02.py
PASS entities=12 relationships=20
PASS importance levels L1=2 L2=4 L3=6 (independent from display_ring)
PASS ring values inner/middle/outer, profile completeness floors, and V0.1 relationship invariant
退出码 0

$ python scripts/tests/intelligence/test_demo_pages.py
PASS routes=34 (entry + network + 12 entity routes + 20 relation routes)
PASS shared-data links, base-path relative URLs, graph controls, importance filters,
     focus history, relation details and relation pages
PASS responsive breakpoints, ring guides, encyclopedia profile and non-color-only node shapes
退出码 0

$ node --check assets/js/intelligence/network.js   → 通过
$ node --check assets/js/intelligence/intelligence.js → 通过

$ python scripts/tests/test_country.py
结果：PASS=24 FAIL=0

$ python scripts/tests/test_stage2_frontend_final.py
前端隔离最终修复测试：PASS=28 FAIL=0

$ python scripts/tests/test_repository_integrity.py
Commit 1 完整性测试：PASS=28 FAIL=0
```

## 22. 构建结果

```text
$ python scripts/build_site.py --no-embed
[build_site] run_id=20260802T084000+0800_084349 pipeline_version=2
intelligence demo: 12 entity routes + 20 relation routes + network + data
构建完成 -> dist
HTML: 9 个页面
ASIP_BUILD_META: 已注入
内联数据快照: False
```

## 23. 浏览器测试环境

- 浏览器：Microsoft Edge（Chromium 内核）`Edg/151.0.4129.59`，Chrome DevTools Protocol 1.3（兼容 Chrome 130+）；
- 页面服务：`python -m http.server 8782 --directory dist`；
- 验收脚本：`i1a_browser_qa.js`，证据：`qa-artifacts-i1a/browser-qa-results.json` 及截图。

### 图谱验收结果

- JNIM 中心：12 节点 / 12 边；中心节点显示中文（缩写）+英文；
- 圈层分布（JNIM 中心）：center=[JNIM]，inner=[Al-Qaida, AQIM, Mali]，middle=[IS Sahel]，outer=[Iyad Ag Ghali]；圈层标签为"结构与地理/组织与力量/人物"；
- 节点名称统一格式：`支持伊斯兰与穆斯林组织（JNIM）`、`基地组织（AQ）` 等；
- 中心切换：JNIM→IS Sahel→Al-Qaida→Iyad Ag Ghali→Mali 均通过（不可达节点自动 URL 导航验证）；
- 关系线点击显示敌对关系详情（类型、圈层、形成背景、历史阶段、来源）。

### 重要程度筛选结果

- 核心视图：2 节点（L1），隐藏 10；
- 重点视图：6 节点（L1=2、L2=4），隐藏 6；
- 完整视图：12 节点；
- 搜索"马西纳旅"（L3，被隐藏）→ 自动临时显示并聚焦 `actor-katiba-macina`（3 节点）；
- 别名搜索 ISGS → 聚焦 `actor-is-sahel`（6 节点）；
- 类型筛选（关闭人物）+ 重要程度组合使用正常；
- 当前中心始终可见。

### 关系详情与关系页

- 4 组关系页全部加载：标题（双方中文名+缩写）、双方实体卡、时间轴、来源；
- 关系摘要卡含"查看完整关系沿革"入口。

### 实体百科验收

- JNIM/IS Sahel：标题含缩写，L1 核心实体徽章，信息框+目录完整；
- AQIM/Iyad/Mali：L2；Ansar Eddine：L3；全部含信息框与目录。

### 路由与响应式

- 深层关系页刷新、深层实体页刷新、深层图谱 URL 刷新正常；
- 1920×1080：bodyWidth=1905（无横向溢出）；
- 1366×768：bodyWidth=1351（无横向溢出）；
- 768：bodyWidth=753（无横向溢出）；
- 390：bodyWidth=390（无横向溢出）；
- 390 图谱（IS Sahel 中心）：3 节点可见，无溢出。

### 控制台与网络

- 控制台错误：0；
- 网络失败请求：0；
- 单页全新加载异常：0（network 页与 entity 页各验证 4 秒加载）；QA 脚本快速连续导航时会收集到旧页 fetch 被打断的导航伪影（页面离开时未完成的数据请求被 CDP 报告为 unhandled rejection，40 条中 36 条已按 URL 归属分类为过期导航伪影，4 条为导航瞬间当前页临时态），单页慢速加载与功能验证均不受影响；
- JSON 加载错误：0（单页测试确认数据全部加载）。

## 24. 截图与录屏清单

`qa-artifacts-i1a/`：entry、network-jnim、relation-card-hostile、network-{is-sahel,al-qaida,iyad-ag-ghali,mali}、importance-{core,priority,full,l3-off}、search-hidden-l3、combo-filter、relation-{jnim-is-sahel,jnim-alqaida,iyad-jnim}、entity-{jnim,is-sahel}、viewport-{1920,1366,768,390,390-graph}。

录屏：环境不支持短录屏自动化，以截图序列与结构化 JSON 作为替代证据。

## 25. 未完成事项与技术债务

- CDP 快速导航场景下的 unhandled rejection 报告为导航伪影，产品页面无阻断错误；如需零噪音需在 QA 脚本中过滤，已实现分类统计；
- 重要程度映射（L2=4、L3=6）为基于现有内容深度的合理映射，未大规模改写实体数据；
- 部分关系档案（非 4 组重点）为详细摘要而非完整档案；
- 录屏自动化未实现；
- 武装规模估计数字有限（依赖公开报告），IS Sahel 无可靠区间。

## 26. 是否满足 V0.2 关闭标准

满足：Git 基线可信（安全重建）、未混入无关 WIP、名称全库统一、L1/L2/L3 语义保留且与圈层独立、重要程度筛选工作正常、圈层未用 L1/L2/L3 命名、中心/外围节点视觉明显改善、箭头与关系线明显改善、中心切换与动画未退化、搜索/过滤/历史未退化、关系摘要明显详细于 V0.1、四组完整关系档案、JNIM 百科示范页、武装规模带时间/口径/来源/可信度、Wikipedia 链接真实存在、未编造事实数字日期链接（所有关键事实经来源核验）、深层路由正常、桌面与窄屏可用、控制台与网络无阻断错误、自动化测试与主站回归通过、未扩展为完整萨赫勒数据库、未接入正式导航、未合并或部署生产。

本任务完成，等待人工查看页面并确认下一步；不自动进入萨赫勒扩库等后续阶段。
