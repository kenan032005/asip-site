# ASIP Stage 2 最终微修复 — 验收报告

> 范围极小、边界严格：仅修复 4 项前端/文档问题，未重新迁移数据、未抓取新闻、未调用 Hy3 处理文章、未开始 Stage 2.5。
> 执行模型遵循规格「一、先写失败测试，再修改实现」的 TDD 顺序。

## 0. 修复的 4 项

1. **删除 `loadCurrentPublishedEvents()` 对 Legacy `events.json` 的回退** — `assets/js/common.js`。
2. **加强测试** — `scripts/tests/test_stage2_frontend_final.py` 新增 T21–T28 负向断言，确保当前页面在任何情况下都不能读取 Legacy `events.json`。
3. **修正 README 错误描述** — 删除“所有条目 `tested` 均为 `false`”的过期表述。
4. **修正 `latest-summary.json` “今日日报 / 最新日报”语义** — `scripts/build_summary.py` 动态生成标签，`status` / `latest-summary` / 首页三者一致。

## 1. 开工前基线（规格 二）

| 项 | 值 |
|---|---|
| Git 工作区 | 干净 |
| `git pull --rebase` | Already up to date |
| main（修复前） | `23164bf` |
| gh-pages（修复前） | `d844039` |
| 线上 run_id（修复前） | `20260731T001132+0800_awao1g` |
| tag `pre-stage2-microfix` | 已创建 |
| 备份目录 | `data/backup/stage2_microfix_20260731T002823+0800/`（含 common.js / 测试 / validate_stage2 / build_summary / latest-summary / README 共 6 文件） |

## 2. TDD：先写失败测试，再改实现（规格 一、三）

**修改前运行（先加测试、未改业务代码）结果：PASS=21  FAIL=7（共 28 项）。**

失败的 7 项（证明测试有效，非“放水或 skip”）：

- T21 `loadCurrentPublishedEvents` 含 `API.get("events")` → 失败（catch 中仍回退读 events.json）
- T22 `loadCurrentPublishedEvents` 含裸 `"events"` 引用 → 失败
- T24 Public 加载失败时失败分支仍回退 Legacy → 失败
- T25 `latest-summary` 缺 `reports_today`/`latest_report_count`/`latest_report_date` → 失败
- T26 `reports_today=0` 时标签仍为“今日日报” → 失败
- T27 README 仍含“所有条目 tested 均为 false” → 失败
- T28 `build_summary.py` 仍把“今日日报”写死在 metrics 列表 → 失败

（T23 三页面无 Legacy 降级源 → 已通过，作为回归守卫。）

## 3. 修改内容（仅下列文件，未改其他架构）

- `assets/js/common.js`：`loadCurrentPublishedEvents()` 移除 `API.get("events")` 回退；Public 失败返回 `[]`（显示空状态），绝不读 Legacy。`loadLegacyArchiveEvents()` 保留只读 `legacy_archive_events.json`，且不被当前页面自动调用。
- `scripts/build_summary.py`：日报指标改为动态生成 —— `reports_today>0` →“今日日报”；`reports_today=0 且 latest_report_count>0` →“最新日报”+`date`；均 0 →“暂无日报”。`latest-summary.json` 新增 `reports_today`/`latest_report_count`/`latest_report_date` 三字段。
- `scripts/tests/test_stage2_frontend_final.py`：新增 T21–T28 负向测试。
- `README.md`：以动态数据说明替换“所有条目 tested 均为 false”错误表述。
- `data/latest-summary.json`、`data/status.json`、`data/public/legacy_archive_events.json`：由修正后的 `build_summary.py` 重新生成（run_id 随流水线统一刷新）。

**修改后运行结果：PASS=28  FAIL=0（共 28 项）。**

> T28 中途一度因断言过严（禁止出现“今日日报”字符串）而报红；修正为“不得写死在 metrics 列表、须经 `report_metric` 变量动态生成”后通过——属修正测试断言，非放宽标准。

## 4. 其余测试与校验（规格 七）

| 套件 | 结果 |
|---|---|
| test_stage2_frontend_final.py | PASS=28 FAIL=0 |
| test_stage2_closeout.py | PASS=22 FAIL=0 |
| test_stage2_schema_repo.py | PASS=57 FAIL=0 |
| validate_stage2.py | PASS=54 FAIL=0 WARN=0 |
| validate_pipeline.py | 0 严重错误（仅 1 条非关键 V08 闸门告警，预存遗留报告，非本次引入） |

## 5. 最终完整运行（规格 九，仅一次有效运行）

- 命令：`python scripts/pipeline_runner.py --mode full --trigger manual`
- 退出码：0；运行耗时 ≈ 54s
- run_id：`20260731T003431+0800_8htvlm`
- 数据 commit：`0df9aa7`；main HEAD：`7024171`（含 logs commit `f399715`）
- gh-pages 部署 commit：`9ac0a11`
- 线上轮询：`✅ run_id 一致`、`http=200`、`events_24h=0`
- 结构化日志：`logs/pipeline_20260731T003431+0800_8htvlm.json`
- 未抓新闻、未重迁数据、未调 Hy3 处理文章、未开始 Stage 2.5。

## 6. 线上验收（规格 十，7 个 URL 全 200）

1. `common.js` 的 `loadCurrentPublishedEvents` 不读 `events.json`（函数体内 `API.get("events")`=0、裸 `"events"`=0、无 `loadLegacyArchiveEvents()` 调用、catch 返回 `[]`）。
2. Public 加载失败时返回空数组，不触发 Legacy 请求。
3. 首页当前事件为空 → 显示“当前暂无通过发布政策的有效动态”。
4. 最新事件页不显示历史迁移事件（渲染仅经 `loadCurrentPublishedEvents` → 当前公开集=0）。
5. 国家页不显示历史迁移事件（同 4，且 `country=chad` 当前集=0）。
6. `reports_today=0` 时，最新 6 份日报显示“**最新日报**”（带 `date: 2026-07-30`），非“今日日报”。
7. `status` 与 `latest-summary` 日报语义一致（`reports_today=0` / `latest_report_count=6` / `latest_report_date=2026-07-30`）。
8. 线上 run_id = `20260731T003431+0800_8htvlm`（=本次运行 run_id）。
9. 全部检查 URL HTTP 200。
10. `common.js` 解析正常，无可见 JS 语法错误。

> 说明（透明披露）：部署产物（含内联 `__DB__` 快照）会嵌入 Legacy `events` 缓存键，但**任何当前页面代码路径都不请求它**——当前事件渲染严格走 `public/published_events`。该内联缓存为既有架构（前端最终修复阶段已确认），非本次“读取”。源文件中三页面 Legacy 读取语句 = 0。

## 7. 18 项交付证据（规格 十一）

1. tag `pre-stage2-microfix`：✅ 已创建
2. 功能 commit：`e8e0b8b`；文档/指标 commit：`89b4b45`
3. 最终 main commit：`f399715`（logs）/ `7024171`
4. gh-pages commit：`9ac0a11`
5. 最终 run_id：`20260731T003431+0800_8htvlm`
6. 修改前失败测试：PASS=21 FAIL=7（T21/T22/T24/T25/T26/T27/T28 失败）
7. 修改后通过测试：PASS=28 FAIL=0（全部 28 项）
8. `common.js` 中 `API.get("events")` 扫描：函数体内 **0** 次
9. 三个页面 Legacy 读取扫描（源文件）：index/events/country 各 **0** 次
10. `reports_today`：**0**
11. `latest_report_count`：**6**
12. `latest_report_date`：**2026-07-30**
13. `latest-summary` 日报指标实际 JSON：
    `{"label": "最新日报", "value": "6", "date": "2026-07-30", "link": "reports.html"}`
14. README 修正：删除 `> 所有条目 `tested` 均为 `false`…`，改为“信息源配置数量、启用数量、测试数量及最近一轮成功状态属于动态运行数据，以 data/status.json 与最近一次结构化运行日志为准，README 不固定写死这些数量或状态。”
15. `validate_stage2`：PASS=54 FAIL=0
16. `validate_pipeline`：0 严重错误
17. 结构化日志路径：`logs/pipeline_20260731T003431+0800_8htvlm.json`
18. 线上验证：7 URL 全 200、run_id 一致、无逻辑层 Legacy 读取、无 JS 错误。

## 8. 完成声明

以上 18 项全部通过。ASIP 第二阶段（含前端隔离最终修复与本次最终微修复）**正式关闭，可以进入 Stage 2.5**。

按规格要求，本次已完成即停止，**未自动开始 Stage 2.5**。
