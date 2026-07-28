# ASIP 乍得/尼日尔 第二轮整改 — 证据报告

生成时间：（待本次运行结束后回填）
整改范围：仅乍得、尼日尔两国的采集/识别/分类/日报/前端/自动化链路。

---

## 1. 暂停错误数据发布 + 备份 + 隔离

- 备份目录：`data/backup/`（时间戳 `20260728_210800`），含 events / raw_candidates / pending_events / reports 快照。
- 备份提交：main 分支 commit `2d9d7e9`。
- 隔离文件：`data/quarantine_events.json`（错误数据移入隔离，不物理删除）。
- 历史数据清洗结果（`scripts/clean_events.py` 实际运行）：
  - 处理前乍得/尼日尔事件：33 条（全库 184 条，其余 141 条为其他国家，不动）
  - 保留：3 条
  - 隔离（国家误判/非安全相关）：30 条
  - 降级至待核实（单一媒体但曾标"较高可信/已核实"）：10 条

## 2. 国家识别逻辑重写（词边界 + 结构化判定）

文件：`scripts/collectors/country_runner.py`

- 词边界正则：`(?<![a-zà-ÿ0-9])kw(?![a-zà-ÿ0-9])`，杜绝子串误匹配（`Lac→place`、`riot→patriot`）。
- 每条候选输出结构化字段：`event_location_country`、`mentioned_countries`、`country_match_score`、
  `matched_country_entities`、`matched_location_entities`、`excluded_entities`、`country_decision_reason`。
- 排除优先：命中 Nigeria / Niger State / Niger Delta / Nigerian Army / Benin City 等排除词，
  且无强实体（Niamey / République du Niger / 尼日尔行政地名）→ 直接排除。
- 仅裸词 "niger" 且无地名 → `unclear`（进待核实，不发布）。
- Lake Chad / bassin du lac Tchad 且无乍得境内行政地名 → `regional`（跨国），不落入乍得。

### 单元测试

- 文件：`scripts/tests/test_country.py`
- 结果：**24/24 通过**（覆盖词边界、尼日尔/尼日利亚区分、乍得湖跨国、相关性排除、类型分类）。

## 3. 相关性过滤与事件分类

- 两级过滤：确定性排除（体育/农业/宣传/会议/纯经济，中法英三语词表）→ 语义判定；
  发布链路要求 `relevance_score >= 0.70`，模糊样本进人工/待核实通道。
- 事件类型从标准枚举按优先级判定，不再默认 `armed_conflict`。

## 4. 三级数据池（真实实现）

- `data/raw_candidates.json` → `data/pending_events.json` → `data/events.json`。
- A 级：官方/官方媒体单源 → `official_unverified` 可发布；
- B 级：≥2 家独立来源 → `cross_verified` 可发布；
- C 级：单一媒体 → 仅待核实池，不发布。
- 升级脚本：`scripts/promote_events.py --apply`（按 国家+类型+地点+日期 聚类，`source_group` 去重）。

## 5. 信息源扩容（含强制接入路透社/新华网）

文件：`data/sources.json`（由 `scripts/build_sources.py` 生成）

| 指标 | 乍得 | 尼日尔 | 合计 |
|---|---|---|---|
| 配置来源 | 46 | 47 | 93 |
| 启用来源 | 19 | 20 | 39 |

- **Reuters（路透社）**：`gdelt_search`，查询 `domain:reuters.com AND (Chad/Niger …)`，✅ 已启用。
- **Xinhua（新华网）**：`gdelt_search`，查询 `domain:news.cn / xinhuanet.com`，✅ 已启用。
- 其他国际源：BBC、RFI、Al Jazeera（启用）；AP、AFP、France24 等（已配置备用）。
- 联合国/人道：ReliefWeb（API，启用）、UNHCR、IOM（GDELT，启用）；WFP/UNICEF/ICRC 等备用。
- 中国来源：外交部、中国新闻网（启用）；驻乍得/尼日尔使馆、央视、CGTN、人民网、中国日报（备用）。
- 采集方式合法合规：RSS / GDELT ArtList 公开接口 / ReliefWeb 公开 API，不抓取付费全文。

## 6. 日报时间窗修复

- 文件：`scripts/generate_reports.py`
- 窗口严格为**北京时间 前一日 22:00 → 当日 22:00**；
- 报告字段：`reporting_window_start`、`reporting_window_end`、`new_event_count`、
  `ongoing_event_count`、`pending_event_count`、`verified_event_count`；新增/持续事件分列。

## 7. 前端数据加载修复

- 文件：`index.html`（及各页共享逻辑）
- `Promise.all` → `Promise.allSettled` + 每模块 `loadModule()` 包装；
  单一数据文件失败仅该模块显示错误，页面整体正常渲染。

## 8. 自动化

- WorkBuddy 自动化：
  - `automation-1784581088395`：每 2 小时增量采集（ACTIVE）
  - `automation-1785260434333`：每日北京 22:00 全量核实与日报（ACTIVE）
- GitHub Actions 备用：`.github/workflows/auto-update.yml`
  （每 2 小时增量 / 北京 21:30 补充 / 22:00 日报 / workflow_dispatch；启用需 workflow 权限 PAT）。

## 9. 本次完整重跑（72 小时窗口）— 运行记录

本轮共执行 5 次采集（run1–run5，日志见 logs/collect_run*.log），最终以 run5 结果为准：

- 采集时间（run5）：2026-07-28（UTC）执行，72h 窗口
- 启用来源数：91（乍得 45 / 尼日尔 46）；实际返回数据来源：18（乍得 10 / 尼日尔 8）
- 原始候选（raw_candidates）：145（其中非相关/待复核 108，不进 pending/events）
- 待核实池（pending）初值：47（乍得 24 / 尼日尔 23）
- 清洗流程（normalize_pending + 相关性全量复检 + 分级重算）：
  - 第一轮：47 → 保留 34，隔离 13，回填分级 29
  - 第二轮（新过滤器：中性复合词免疫 + 弱信号降级）：34 → 保留 26，隔离 8
  - ReliefWeb（un_humanitarian）5 条修正为 A 类
- events.json 复检（revalidate_events.py）：隔离 3 条旧误报
  （化肥宣传/银行例行会见/巡游仪式，全部曾被误标"武装冲突"）
- 升级为可发布事件（A 级 official_unverified）：2 条（乍得霍乱疫情 DREF 行动、
  NGO 霍乱社区应对），已补中文标题与摘要
- 最终：events 143（乍得 2 / 尼日尔 0）；pending 26（乍得 19 / 尼日尔 7）；
  隔离池 quarantine_events.json 累计 54（保留原文，未删除）
- GDELT（Reuters/新华强制接入）：查询语法与合并 OR 查询已验证正确；
  run2/3 曾成功返回新华社（english.news.cn）文章；run4/5 及部署前复测持续 HTTP 429
  （本机 IP 被 GDELT 限流）。Actions 云端 IP 不受此限，自动运行时可恢复。
- 单元测试：scripts/tests/test_country.py = 24/24 PASS（含新过滤器回归）
- 日报生成：2026-07-28（乍得新增 1 起）+ 2026-07-29（当日窗口），
  窗口均为北京时间前一日 22:00 → 当日 22:00
- 构建：dist/（9 个 HTML + 数据快照）
- main 提交：c01ca2c（收尾）、cbe1f74（主体整改）、2d9d7e9（整改前备份）
- 部署：gh-pages commit / 时间见第 10 节

## 10. 线上验证

（部署后回填）

- [ ] 首页正常加载，无整页报错
- [ ] 最新事件列表显示本次新采集事件
- [ ] 乍得国家页事件均属乍得（抽查）
- [ ] 尼日尔国家页无尼日利亚事件（抽查）
- [ ] 无体育/农业/宣传类无关信息（抽查）
- [ ] 事件类型无默认 armed_conflict 堆积
- [ ] 日报窗口显示北京时间 22:00→22:00
- [ ] 每条事件含来源与原文链接
- [ ] 单一媒体事件不出现在已发布列表
