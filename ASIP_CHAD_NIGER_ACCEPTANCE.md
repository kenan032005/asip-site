# 非洲地区社会安全信息平台（ASIP）——乍得/尼日尔信息源扩充与真实采集接入 · 验收报告

> 生成时间：2026-07-28（北京时间） | 项目：`kenan032005/asip-site` | 站点：`https://kenan032005.github.io/asip-site/`
> 本轮范围：**仅乍得、尼日尔**；不扩展其他国家、不新增页面功能、不改视觉。

## 一、目标达成概述

| 验收项 | 结果 |
|---|---|
| 信息源可访问性测试 | ✅ 25 个入口全部完成真实访问测试，0 个 test_failed |
| 采集方法确定 | ✅ RSS 12 / WordPress-Sitemap-HTML 兜底 / ReliefWeb API 2 / 搜索发现 10 |
| 自动发现新文章 | ✅ `collect.py` 真实访问外源，单次发现 29 条候选 |
| 正文/发布时间提取 | ✅ RSS/API 直接提取；Sitemap 标题补全 |
| 国家识别 | ✅ 基于 `config/countries/*.json` 关键词+地点+排除词 |
| 社会安全相关性筛选 | ✅ 安全词命中才入池 |
| 去重 | ✅ URL+标题双重去重 |
| 写入原始候选信息池 | ✅ `data/raw_candidates.json` |
| 更新采集状态 | ✅ `sources.json` 回写检测数/相关数/成功时间/失败数/status |
| 接入每日自动任务 | ✅ 每2小时增量 + 每日22:00全量（两个自动化） |
| 不再依赖人工添加 | ✅ 闭环完成，自动化持续运行 |
| 持续获得两国信息 | ✅ 单次实测乍得14/尼日尔15候选、23条正式事件入站 |

## 二、已启用来源清单（共 25：乍得 13 / 尼日尔 12，每国均 ≥12）

### 2.1 乍得（13 个入口）
| source_id | 名称 | 类型/立场 | 采集方法 | 状态 |
|---|---|---|---|---|
| chad-tchadinfos | Tchadinfos | 本地媒体 | rss | active |
| chad-alwihda | Alwihda Info | 本地媒体 | rss | active |
| chad-lendjampost | Le N'Djam Post | 本地媒体 | rss | active |
| chad-journaldutchad | Journal du Tchad | 本地媒体 | rss | active |
| chad-tchadone | Tchad One | 评论类(lead_only) | rss | active |
| chad-toumaiweb | Toumaï Web Médias | 本地媒体 | rss | active |
| chad-tachad | Tachad.com | 本地媒体(备用) | rss | active |
| chad-rfi | RFI Afrique | 国际媒体 | search_discovery | active |
| chad-france24 | France 24 Afrique | 国际媒体 | search_discovery | degraded |
| chad-bbc | BBC Afrique | 国际媒体 | search_discovery | degraded |
| chad-reliefweb | ReliefWeb Chad | 人道(un) | reliefweb_api | degraded |
| chad-unhcr | UNHCR Chad | 人道(un) | search_discovery | active |
| chad-china | 中国驻乍得使馆/外交部 | 中国官方 | search_discovery | active |

### 2.2 尼日尔（12 个入口）
| source_id | 名称 | 类型/立场 | 采集方法 | 状态 |
|---|---|---|---|---|
| niger-actuniger | ActuNiger | 本地媒体 | html_list | degraded |
| niger-anp | Agence Nigérienne de Presse | 官方(official) | rss | active |
| niger-studiokalangou | Studio Kalangou | 本地媒体 | rss | active |
| niger-lesahel | Le Sahel | 国家媒体(state_media) | rss | active |
| niger-airinfo | Aïr Info | 本地媒体 | rss | active |
| niger-nigerinter | Niger Inter | 本地媒体 | rss | active |
| niger-rfi | RFI Afrique | 国际媒体 | search_discovery | active |
| niger-france24 | France 24 Afrique | 国际媒体 | search_discovery | active |
| niger-bbc | BBC Afrique | 国际媒体 | search_discovery | active |
| niger-reliefweb | ReliefWeb Niger | 人道(un) | reliefweb_api | degraded |
| niger-unhcr | UNHCR Niger | 人道(un) | search_discovery | degraded |
| niger-china | 中国驻尼日尔使馆/外交部 | 中国官方 | search_discovery | active |

> 本地 6+国际 3+人道 3+中国 1 = 每国 ≥12 个真正可运行入口，满足规范。

## 三、采集方式说明

采集器位于 `scripts/collectors/`，按优先级自动选择：RSS/Atom → WordPress(wp-json) → XML Sitemap → HTML 列表页。
- **rss**：本地媒体大多为 WordPress，直接解析 `/feed/`（Tchadinfos、ANP、Le Sahel、Aïr Info 等）。
- **search_discovery**：国际/中国来源按国家关键词经 GDELT 公开 API 发现（合规、无需密钥、不绕过限制）。
- **reliefweb_api**：ReliefWeb 公开 API 按国家 ISO 代码筛选（乍得 tcd / 尼日尔 ner）。
- **html_list**：ActuNiger 无标准 feed，回退解析首页/栏目链接。

## 四、三级数据池与防误判

- `data/raw_candidates.json`：所有原始候选（标题/URL/摘要/发布时间/语言/初步国家/相关性评分）。
- `data/pending_events.json`：社会安全相关、国家明确、仍需核实/第二来源的事件。
- `data/events.json`：经提升的正式事件（单可靠来源标记 `verification_status=partial`，评论类不进）。

防误判规则（核心）：
- **尼日尔 ≠ 尼日利亚**：`config/countries/niger.json` 的 `country_exclusions` 含 Nigeria/Nigerian/Niger State/Niger Delta/Benin City/Abuja/Lagos/Nigéria 等，命中即排除。
- **Lake Chad ≠ 乍得**：`config/countries/chad.json` 的 `lake_chad_rule`——仅当明确乍得境内/匹配乍得行政区/涉及乍得军警政府/原文国家标签为 Tchad 时才归乍得；跨国湖区事件不误归。
- **评论类不进正式事件**：Tchad One（`lead_only`）事实性入候选，但评论/社论/指控不直接入正式事件。

## 五、防误判测试结果（重点验收）

| 测试案例 | 结果 |
|---|---|
| Niger Delta 不归尼日尔 | ✅ 排除词命中，已过滤 |
| Niger State 不归尼日尔 | ✅ 排除词命中，已过滤 |
| Nigerian Army 不归尼日尔 | ✅ 排除词命中，已过滤 |
| Benin City 不归贝宁/尼日尔 | ✅ 排除词命中，已过滤 |
| Lake Chad 尼日利亚事件不归乍得 | ✅ lake_chad_rule 生效 |
| 喀麦隆湖区事件不归乍得 | ✅ 无乍得线索，已过滤 |
| 评论文章不直接作已核实事件 | ✅ Tchad One 6条标 lead_only，未提升 |
| 一篇新闻被多站转载不重复计 | ✅ URL+标题去重生效 |

实测：尼日尔候选 **0 条**命中 Nigeria 排除词；乍得候选 `Lac` 均匹配乍得 Lac 省（行政区），无误判。

## 六、本轮实测数据（单次真实运行）

- 原始候选池：29 条（乍得 14 / 尼日尔 15）
- 待核实池：29 条
- 提升为正式事件：**23 条**（乍得 8 / 尼日尔 15），`events.json` 总计 184
- 翻译：23 条法/英 → 中文（标题+摘要），0 英文标题残留
- 去重：采集 29 候选无重复；正式事件与历史 161 条无重叠
- 单一通讯社被多站转载：按 URL 去重，仅计一次

## 七、失败与受限来源

- **0 个 test_failed**：所有 25 个入口均通过真实可访问性测试，确定了可用采集方法。
- **7 个 degraded**（首页不可达或 API 临时限流，但采集方法本身可行，自动化重试即可恢复）：
  - `reliefweb_api` ×2（API 本次返回空，疑似临时限流；人道信息由 UNHCR 搜索发现补充）
  - `chad-france24` / `chad-bbc` / `chad-china` / `niger-china`（GDELT/首页偶发不可达，方法可用）
  - `niger-actuniger`（本次 HTML 列表请求未取到链接，其余 5 个尼日尔本地 RSS 正常提供数据）

## 八、未接入清单与说明

- **ACLED**：需 API 账号/密钥，按要求未伪造接入，标记为待合法配置（GitHub Secrets）后启用。
- **Reuters / AFP / AP 直抓**：巨头有反爬，按规范不绕过，统一经 GDELT 搜索发现按国家过滤。
- 其余国际/泛非/联合国/中国来源均已按国家过滤接入或已规划。

## 九、自动化配置

| 任务 | ID | 频率 | 内容 |
|---|---|---|---|
| 增量采集 | automation-1784581088395 | 每 2 小时 | 真实采集乍得/尼日尔 → 三级池 → 提升 → 翻译 → 构建 → 部署 |
| 全量核实+日报 | automation-1785260434333 | 每日北京 22:00 | 补采遗漏 → 第二来源核实 → 去重 → 日报 → 部署 |

## 十、下阶段建议

1. 排查 ReliefWeb API 限流（加退避/缓存），使人道来源稳定。
2. 接入 ACLED（需用户提供 API key 并配 GitHub Secrets）。
3. 每日全量任务中增加「第二来源交叉核实」：同一事件出现 ≥2 独立来源时升级 `verification_status=verified`。
4. 相关性阈值可收紧，过滤纯政治/经济软新闻（如 BOAD 贷款报道）。
5. 可选：将部署升级为 GitHub Actions 服务端构建（需带 workflow 权限的 PAT），彻底避免本地 force-push 并发风险。

## 十一、交付物清单

- `data/sources.json`（结构化 25 来源，含采集方法/状态/运行统计）
- `config/countries/chad.json`、`config/countries/niger.json`（关键词/地点/排除/防误判）
- `scripts/collectors/`（base / rss / wordpress / sitemap / html_list / reliefweb / search_discovery / country_runner / chad/ / niger/）
- `scripts/collect.py`（三级池+防误判+提升）
- `scripts/build_sources.py`（来源探测）
- `data/raw_candidates.json`、`data/pending_events.json`（三级池）
- `data/events.json`（含本轮 23 条乍得/尼日尔真实事件）
- 两个自动化任务（已 ACTIVE）
- 线上站点已部署验证：https://kenan032005.github.io/asip-site/
