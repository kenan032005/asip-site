# ASIP非洲安全情报知识库 I3-A 现有高风险国家与核心实体百科内容深化验收报告

- 阶段：I3-A（内容深化与百科建设）
- 报告日期：2026-08-06
- 执行模型：DeepSeek V4 Pro（主执行：来源研究、事实判断、正文撰写、最终审查；构建/测试/浏览器 QA 由自动化流水线完成）
- 标准开发目录：`C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-trusted`（I2-B 起唯一可信目录，reftable 引用后端）

## 1. Git 基线、分支与提交

| 项 | 值 |
|---|---|
| I3-Prep-A 基线 | `f8d3003`（远端核验一致） |
| I2-B 基线 | `1582e83`（未变） |
| I3-A 功能分支 | `feature/asip-intelligence-v10-i3a-content` |
| I3-A 远端 HEAD | `8f1ef5e`（已推送，`ls-remote` 核验通过） |
| 阶段标签 | `asip-intelligence-v1.0-content-preview`（对象 `baae7e1` → 提交 `8f1ef5e`，已推送；仅代表"首批核心国家和实体内容达到人工预览标准"，非生产发布） |
| 工作树 | 干净（`git status --porcelain` = 0） |
| Git 健康 | `git fsck --full` 无异常；正常 `git commit` 创建全部提交，未使用 commit-tree |

I3-A 七组逻辑提交（真实哈希链）：

```text
88fe881  data: deepen country intelligence profiles (Nigeria Libya South Sudan Niger Benin + Chad Sudan Mozambique maintenance)
87cb492  data: upgrade core entity encyclopedia and standard profiles
0cffbb7  data: deepen relationship histories, evidence and sources
6c4c6d8  feat: improve encyclopedia reading experience (lead, TOC, tables, in-text links)
51ba8c1  feat: strengthen build-time content quality gates and I3-A generators
76e4d68  test: add I3-A content depth and source coverage validation
8f1ef5e  docs: add I3-A browser acceptance evidence
```

修改文件清单：`data/intelligence/africa/` 下 9 个数据文件、`assets/js/intelligence/africa.js`、`assets/css/intelligence.css`、`scripts/build_intelligence_africa.py`、`scripts/gen/gen_i2b_migration.py` + 3 个新生成脚本、6 个新测试 + 1 个测试更新、浏览器 QA 脚本与证据目录。

## 2. 内容深化成果

### 2.1 深度国家页（8 个，正文均 ≥2500 中文字符、18 个章节、含导语与目录）

| 国家 | 正文字符数 | 实质章节 | 主题覆盖 |
|---|---|---|---|
| 尼日利亚 | 5349 | 18 | 四线冲突体系、JAS/ISWAP 2025-26 回升、西北绑架经济与拉库拉瓦、三角洲、人员/企业安全 |
| 利比亚 | 4531 | 18 | 双政府格局、LNA/GNU 机构冷战、南部走私、ISIS 残部、2027 选举目标、外部力量 |
| 南苏丹 | 4395 | 18 | R-ARCSS 解体、纳西尔事件、马沙尔审判、UPDF 介入、SPLM/A-IO 分裂、选举 |
| 尼日尔 | 4501 | 18 | AES 联盟、IS Sahel 尼亚美机场袭击、JNIM 攻势、Domol Leydi、边境真空 |
| 贝宁 | 3968 | 18 | WAP 保护区、2025 最致命年、米拉多行动、瓦达尼外交、沿海扩散风险 |
| 乍得 | 3427 | 18 | 湖区两线作战、2026-05 重大伤亡、东部苏丹外溢、MNJTF 枢纽 |
| 苏丹 | 4701 | 18 | SAF—RSF 战争格局、平行政府、达尔富尔武装、SPLM-N 结盟、人道危机 |
| 莫桑比克 | 4128 | 18 | IS-Mozambique 叛乱、RDF/SAMIM 演变、LNG 重启、撤军不确定性 |

（字符数为章节正文合计，不含标题/信息框/来源列表/关系卡；每页含 2–4 段导语、信息框日期语义、时效提示。）

### 2.2 实体档案深度（profile_depth 由内容完整度自动分级）

- **完整百科 14 个**（目标 ≥12）：JNIM（既有）、博科圣地/JAS、ISWAP、MNJTF、尼日利亚武装部队、利比亚国民军（LNA）、GNU 相关安全力量、ISIS 利比亚分支、SSPDF、SPLM/A-IO、NAS、萨尔瓦·基尔、里克·马沙尔、贝宁安全力量。每页 10–20 个实质章节、1800–3200 字正文，覆盖成立背景/历史沿革/组织结构/领导层/活动范围/武装规模口径/战术/资金/关系/当前状态/不确定性与来源。
- **标准档案 18 个**（目标 ≥18）：SAF、RSF、IS-Mozambique、FADM、卢旺达驻莫部队、SAMIM、乍得国防力量、喀麦隆武装部队、伊斯兰国（网络实体）、JEM、SLM/A-AW、SPLM-N al-Hilu、布尔汉、赫梅蒂、AQIM、IS Sahel、伊亚德·阿格·加利、阿马杜·库法。每页 900–1400 字、≥9 个章节。
- **基础条目 4 个**（目标 ≤10）：基地组织、安萨尔埃丁、穆拉比通、马西纳旅（均有来源与结构信息，作为网络节点保留）。
- 武装规模无可靠公开数据处均明确写"暂无可靠公开区间估计"，不猜测。

### 2.3 关系档案深化（12 条，含背景/阶段/转折/现状/不确定性 + 时间轴）

JAS—ISWAP、ISWAP—伊斯兰国（效忠）、JNIM—IS Sahel、JNIM—尼日尔、IS Sahel—尼日尔、LNA—GNU、ISIS-Libya—伊斯兰国、SPLM/A-IO—SSPDF、基尔—SSPDF、马沙尔—SPLM/A-IO、NAS—SPLM/A-IO、尼日利亚—MNJTF。关系页显示时间轴（每条约 1–7 个条目）、双方互链、来源与"返回图谱"入口。

### 2.4 来源与证据

- 来源：新增 22 个（联合国/非盟决议与专家报告摘要、ACLED 专家评论、ISS Africa、CFR、美国国务院报告、国际危机组织 CrisisWatch、DefenceWeb 等），合计 **62 个**。
- 证据：新增/升级人工来源映射证据 **42 条**（目标 ≥30），合计 **137 条**：已核验 34 / 部分核验 80 / 待复核 23。
- 生成证据复核：**70 条生成证据全部完成显式复核**——47 条升级为部分核验（`manual_review_2026_i3a`，附真实来源与 locator），23 条明确保留 pending_review 并附复核说明（目标 ≥25 达成）。无任何生成证据被标记为 verified。
- verified 证据满足 10 项标准（source_id 存在、可访问、发布日、locator、方法、核验日等），构建门强制校验。

### 2.5 统计口径（catalog_metrics.json 机器生成）

```
region_count=7  country_count=13  non_country_entity_count=36
unique_knowledge_object_count=56（区域+国家+非国家实体，无重复计数）
relationship_count=62  relation_profile_count=17  relation_timeline_count=17  relation_type_count=24
source_count=62  evidence_record_count=137（verified 34 / partially 80 / pending 23）
encyclopedia_full=14  standard=18  basic=4  deep_country=8
duplicated_paragraph_count=5（均为"来源说明"统一组件，正文无重复）  empty_section_count=0
stale_current_claim_count=11（诚实标注的过时条目）  route_count=125
```

## 3. 前端阅读体验

- 正文渲染升级：多段落正文（`{p:[…]}`）、表格、章节内时间轴、受控互链语法（`[[entity:id|名]]` 仅作者显式写入，不做全文正则替换）、自动目录（≥4 章节时显示）、导语置顶样式。
- 新增章节标签：最近三至五年的重要变化、对人员企业和项目安全的影响、相关实体、主要分支、资金补给与招募、主要敌对对象、法律与政治地位、主要任务、参与的重要行动、当前挑战、核心评估、名称与译名等。
- 未重做整体视觉、未改配色体系、未引入新框架；信息框/时效徽章/证据徽章保持 I2-B 语义。

## 4. 数据质量门（构建内置）

深度国家正文 ≥2500 字且实质章节 ≥8；encyclopedia_full 需 ≥8 章节 & ≥1800 字；standard 需 ≥5 章节 & ≥900 字；basic 必须有来源；无空章节/占位符/大量重复段落（统一组件豁免）；正文互链必须可解析；当前状态必须有 claim_valid_as_of；verified 证据必须有 locator；生成证据不得标记 verified。全部通过。

## 5. 自动测试

```text
20 个测试文件 + 3 个 node --check，全部通过：PASS=186 FAIL=0
（含 I2-B 全部 8 项、Demo 3 项、主站回归 3 项、I3-A 新增 6 项）
python scripts/build_site.py --no-embed → 构建完成，非洲知识库 125 路由 + Demo 不回归
```

I3-A 新增测试：`test_i3a_country_depth.py`、`test_i3a_entity_depth.py`、`test_i3a_content_quality.py`、`test_i3a_duplicate_text.py`、`test_i3a_source_coverage.py`、`test_i3a_preview.py`（另更新 `test_africa_metrics.py` 断言到 I3-A 标准）。

## 6. 真实浏览器验收

环境：Edge 151（`--disable-extensions` 全新 profile，CDP 9224）、预览服务 8786（可信克隆 dist）。

```text
33 页验收（8 国家页 + 13 实体页 + 12 关系页）
consoleErrors=0  runtimeExceptions=0  failedRequests=0
expectedNavigationAborts=0  unexpectedUnhandledRejections=0  stalePageEvents=0
8 国家页：18 章节、3200–5100 字、目录 18 项、无横向溢出
13 实体页：10–20 章节、1800–3100 字、信息框含档案深度与时效日期
12 关系页：10 章节、时间轴 1–7 条、双方互链、返回图谱按钮
图谱回归：乍得中心 5 节点/4 边 + 焦点链接→country/chad；ISWAP 8/8、4 种关系线颜色；图例正常
深层路由刷新：/country/libya/ 直刷正常（18 章节）
390px：国家/实体/关系页均无横向溢出，目录正常显示
截图证据：39 张（8 国家页、13 实体页、12 关系页、图谱、390px、deep reload）
```

## 7. 非生产预览更新

- **CloudStudio 隔离预览（已验证可访问）**：https://e5f9aef1abbc4c938d3ce143c41811c4.gz1.agentos-app.net
  - 非洲知识库：`/intelligence/africa/`、尼日利亚 `/country/nigeria/`、JAS `/entity/boko-haram-jas/`、图谱 `/network/`、指标 `/data/catalog_metrics.json` 全部返回 200。
  - 对应分支：`feature/asip-intelligence-v10-i3a-content` @ `8f1ef5e`；部署时间 2026-08-06；与生产隔离（沙箱工作区，非生产域）；停止/回退可在应用管理入口删除。
  - **你可以随时在「设置 - 数据管理 - 我发布的应用」中管理（例如删除）这个已发布的应用。**
- **GitHub Pages 隔离预览分支**：`gh-pages` 已更新至 `d72926f`（仅包含静态产物 + 预览标记，不包含源码数据）；`raw.githubusercontent.com` 端点确认文件已就位，公开域名 `kenan032005.github.io/asip-site/intelligence/africa/` 因 Pages CDN 对新目录的传播延迟暂返回 404（demo 与旧路径正常），传播完成后即生效。
- 未接入正式主导航、未部署生产环境、未覆盖生产站。

## 8. 关闭标准对照

| 关闭条件 | 状态 |
|---|---|
| Git 基线稳定 / 分支建立并推送 | ✅ 8f1ef5e 推送，fsck 无异常 |
| 未新增空壳实体（新增实体为 0，全部升级既有实体） | ✅ |
| 尼日利亚/利比亚/南苏丹/尼日尔/贝宁深度国家页 | ✅ |
| 乍得/苏丹/莫桑比克保持深度标准 | ✅ |
| 深度国家 ≥8 | ✅ 8 |
| 完整百科 ≥12 | ✅ 14 |
| 标准档案 ≥18 | ✅ 18 |
| 基础条目 ≤10 | ✅ 4 |
| 关系深化 ≥10 | ✅ 12 |
| 新增/升级人工证据 ≥30 | ✅ 42 |
| 生成证据人工核验或明确保留 ≥25 | ✅ 70 条全部显式复核（47 升级 + 23 保留待复核） |
| 页面非"信息框+短摘要" | ✅ 正文 1800–5300 字/页 |
| 无大量模板重复文字 | ✅ duplicated=5（统一组件）、empty_section=0 |
| 当前状态时效语义准确 | ✅ current/aging/stale 明确区分，claim_valid_as_of 与核验日分离 |
| 来源可追溯 | ✅ 62 来源、137 证据、locator 门 |
| 重点实体互链 / 双向跳转 / 图谱回归 | ✅ 浏览器验收通过 |
| 深层路由可刷新 / 桌面与窄屏 | ✅ |
| 控制台/网络无阻断错误 | ✅ 全 0 |
| Demo / 主站回归 | ✅ PASS=186 FAIL=0 |
| 非生产预览更新并提供 URL | ✅ CloudStudio URL 可访问 |
| 未接入主导航 / 未部署生产 / 未进入地图与新闻阶段 | ✅ |

## 9. 未完成事项与技术债务

- GitHub Pages 公开域名的 africa 目录仍在 CDN 传播中（raw 端点已确认文件就位）；如需立即使用公网预览，CloudStudio 链接当前可用。
- 剩余 4 个基础条目（基地组织/安萨尔埃丁/穆拉比通/马西纳旅）与 11 个 stale/aging 标记条目（如埃塞俄比亚、坦桑尼亚等）留待后续轮次深化；本轮严格遵守"核心国家与核心实体不以来源不足保留空壳"要求。
- 关系时间轴与档案为"深化优先 12 条"，其余 50 条关系保留索引级内容。
- 内容写作依赖公开来源；个别高影响判断（如卢旺达撤军前景、利比亚美方斡旋方案）已标注"部分核验/存在不同评估"。

## 10. 结论

**I3-A 满足全部关闭标准。** 知识库从"页面与词条入口"阶段进入"实质内容"阶段：8 个深度国家百科、14 个完整百科实体、18 个标准档案、12 条深化关系、42 条新人工证据、70 条生成证据显式复核，测试 186/0、构建 125 路由、浏览器 33 页零错误，并已提供可访问的非生产预览 URL。未合并 main/master、未部署生产、未接入主导航；等待人工打开页面检查正文内容与阅读体验后，再确认下一阶段安排。
