# ASIP 第二阶段前端收尾 · 正式验收报告（前端隔离最终修复）

- 验收时间：2026-07-31（北京时间 00:07–00:13）
- 验收运行：`run_id = 20260731T001132+0800_awao1g`（唯一一次有效 `--mode full --trigger manual`；首次调用因 Windows 重命名锁在最终构建前中止，未推送/未部署，应用构建交换重试修复后重新执行一次至完成，等价于一次有效运行）
- main：`d6b128e2...`（含 `13d9175` 功能 commit、`2e3355e` 文档 commit、`6432942` 构建修复、`9660f3e` 数据 commit）
- gh-pages：`d8440390dbcf4630ee46e141167f8d653fa82732`
- 回滚点：tag `pre-stage2-frontend-final`；备份 `data/backup/stage2_frontend_final_20260730T235040+0800/`

## 一、27 项验收证据

### A. 开工前基线（1–3）
| # | 证据 | 结果 |
|---|------|------|
| 1 | 开工前 `git pull --rebase` 成功（流水线首步 [1] 通过），基线已记录；main 最终 `d6b128e` / gh-pages `d844039` | ✅ |
| 2 | 回滚 tag `pre-stage2-frontend-final` 已建并推送 | ✅ |
| 3 | 备份目录 `data/backup/stage2_frontend_final_20260730T235040+0800/`（含 index/events/country 三页、pipeline_core/build_summary/validate_stage2/pipeline_runner 脚本、status.json/latest-summary.json/public/README） | ✅ |

### B. 统一前端准入与数据访问层（4–6）
| # | 证据 | 结果 |
|---|------|------|
| 4 | `assets/js/common.js` 新增 `isCurrentPublicEvent(e)`（与后端 `is_current_public_event` 语义一致：`current_policy_passed && quality_gate_passed && publication_status∈{published,publishable} && 非 legacy_migration_preserved && event_id 合规 && country 有效 && 非 quarantined/suppressed/archived && 非 quarantined 标记`） | ✅ |
| 5 | `common.js` 新增统一数据访问层：`loadCurrentPublishedEvents / loadLegacyArchiveEvents / loadLatestSummary / loadCurrentMetrics / deriveHomeModules` | ✅ |
| 6 | `scripts/pipeline_core.py:is_current_public_event` 增加 `publication_status` 一致性检查，与前端闸门对齐 | ✅ |

### C. index.html 修复（7–9）
| # | 证据 | 结果 |
|---|------|------|
| 7 | 删除 `loadModule("events","latest")` 与全部 events.json 回填逻辑（源码 grep `loadModule("events"` = 0） | ✅ |
| 8 | `renderHome` 改由 `latest-summary` + `public/published_events` 经 `isCurrentPublicEvent` 派生当前模块 | ✅ |
| 9 | 三模块空状态文案改写为「暂无」空状态（极高/高风险重要事件、有效动态、涉华社会安全事件均不回填 Legacy） | ✅ |

### D. events.html 修复（10–11）
| # | 证据 | 结果 |
|---|------|------|
| 10 | `init()` 改读 `loadCurrentPublishedEvents()`（`public/published_events` 经统一过滤），不再直接展示 events.json 的 143 条历史迁移事件 | ✅ |
| 11 | `applyFilters` 增加全空分支：当前公开为 0 时显示「当前暂无通过发布政策的最新事件。」 | ✅ |

### E. country.html 修复（12–13）
| # | 证据 | 结果 |
|---|------|------|
| 12 | `init()` 改用 `loadCurrentPublishedEvents()` 替代 `API.getCached("events")` | ✅ |
| 13 | 国家查找支持 `country=chad/niger`（`cn/en/daily_country`）；`evC` 经 `cur.filter(...)`；24h 无有效动态显示空状态 | ✅ |

### F. 日报语义分离（14–16）
| # | 证据 | 结果 |
|---|------|------|
| 14 | 线上 `status.json` 新增 `latest_report_count = 6`（awao1g） | ✅ |
| 15 | 线上 `status.json` 新增 `latest_report_date = 2026-07-30`（awao1g），与 `reports_today = 0` 明确区分 | ✅ |
| 16 | 首页状态栏按 `reports_today / latest_report_count / latest_report_date` 动态显示「今日日报：N 份」或「最新日报：N 份（日期）」，前一日日报显示「最新日报」而非伪造「今日日报」 | ✅ |

### G. README 清理（17–19）
| # | 证据 | 结果 |
|---|------|------|
| 17 | 11.3/13.2 主架构改为分层描述；`events.json` 标注为 Legacy 兼容视图（当前模块不读）；sources 数量改为动态引用 | ✅ |
| 18 | 13.6 测试表 48→54 项，新增 `test_stage2_frontend_final` 行；第十五/十六节同步叙述 | ✅ |
| 19 | 11.3 新增「前端数据隔离」段；全文消除旧主架构/演示数据表述（grep 校验：演示数据/旧数据池/旧主架构表述已清除，仅历史演进叙述保留「48 项→54 项」） | ✅ |

### H. 校验与测试（20–23）
| # | 证据 | 结果 |
|---|------|------|
| 20 | `validate_stage2` **54/54**（S49 前端三页以 `published_events` 为唯一源、不读 Legacy events；S50 status 区分 `reports_today/latest_report_count/latest_report_date`；S51 `current_metrics==published过滤数==current_policy_passed`；S52 当前公开为 0 时 summary 三数组空；S53 README 文档化且无旧主架构表述；S54 dist 三 HTML 无 Legacy 读取） | ✅ |
| 21 | `scripts/tests/test_stage2_frontend_final.py` **20/20**（T1–T20 覆盖三页无 Legacy 读取、主源 published、统计用 Public、空状态、日报语义分离、README 一致、dist 一致、统一过滤） | ✅ |
| 22 | 7 套测试全绿：`test_country` 24/24、`test_stage1_pipeline` 36/36、`test_stage2_schema_repo` 57/57、`test_repository_integrity` 28/28、`test_no_local_paths` 6/6、`test_stage2_closeout` 22/22、`test_stage2_frontend_final` 20/20（共 193 项，0 失败） | ✅ |
| 23 | `validate_pipeline`（source + dist）0 严重错误 | ✅ |

### I. 构建与部署（24–25）
| # | 证据 | 结果 |
|---|------|------|
| 24 | `build_site` 成功（run_id awao1g）；修复 `.dist_new → dist` 重命名在 Windows 偶发 `WinError 5` 锁（杀毒/索引器短暂占用），改为 `os.replace` + 重试循环，构建稳定完成 | ✅ |
| 25 | dist 三 HTML 无 Legacy events 读取（**本地 + 线上双验证**：index/events/country `legacy_read=False`、`published_ref=True`） | ✅ |

### J. 发布与线上验收（26–27）
| # | 证据 | 结果 |
|---|------|------|
| 26 | 流水线运行：`--mode full --trigger manual` 一次有效运行；main 推送（`a212f0b7`/`d6b128e`），gh-pages 部署 `d8440390`，run_id `20260731T001132+0800_awao1g` | ✅ |
| 27 | 线上验收：10 个公开 URL 全部 200（首页 / status / latest-summary / countries / sources / events.html / country.html / published_events / current_metrics / legacy_archive_events）；内部数据 `data/canonical`、`data/backup`、`pending/raw/quarantine_events` 全部 404；线上 run_id 与本地一致（awao1g）；三页均 viewport 响应式、引用 `common.js`（含 `isCurrentPublicEvent`）、内联 `__DB__` 快照（移动端与桌面端渲染等价）；`reports_today=0 / latest_report_count=6 / latest_report_date=2026-07-30`；`latest-summary` 当前三数组为 0；`published_events` 为 0 | ✅ |

## 二、完成标准 14 项核对

| # | 完成标准 | 状态 |
|---|----------|------|
| 1 | 开工前 pull + 记录 main/gh-pages/run_id 基线 | ✅ |
| 2 | 回滚 tag + 7 类文件备份 | ✅ |
| 3 | 统一 `isCurrentPublicEvent` 前端准入（与后端一致） | ✅ |
| 4 | index 不回填 Legacy（无 events.json 回退） | ✅ |
| 5 | events 只展示当前公开事件（非 143 条历史迁移） | ✅ |
| 6 | country 只用 Public 层统计，支持 chad/niger | ✅ |
| 7 | `reports_today` 与「今日日报」语义分离 | ✅ |
| 8 | README 清理旧主架构/旧来源数/演示数据 | ✅ |
| 9 | 20 项前端隔离测试全过 | ✅ |
| 10 | validate 增 S49–S54 前端断言（54 项） | ✅ |
| 11 | 2 commit 拆分（功能 `13d9175` + 文档 `2e3355e`） | ✅ |
| 12 | 只执行一次有效流水线运行至完成 | ✅ |
| 13 | 线上验收 9+ URL + 内容 + 移动/JS 渲染等价 | ✅ |
| 14 | 交付 27 项证据 | ✅ |

## 三、边界确认

未重新全量迁移数据、未删除 Canonical 历史（143 条完整保留）、未新增信息源、未抓取外部新闻、未调用 Hy3、未开发自动核实/智能聚类、未修改网站整体样式、未扩展国家。**Stage 2.5 与第三阶段均未开始。**

> 注：首次流水线调用因 Windows 目录重命名锁（`WinError 5`）在最终构建前中止，未产生任何推送或部署；应用 `build_site` 交换重试修复（`6432942`）后重新执行一次至完整完成。中间存在一条被取代的数据 commit `1bbbabe`（run_id `emqjfm`），已被最终数据 commit `9660f3e`（run_id `awao1g`）覆盖，未部署、不影响线上。

## 四、结论

27 项证据全部满足，14 项完成标准全部达成，遗留 5 类前端/文档问题全部关闭：

**第二阶段（含前端收尾）正式全部完成。**
