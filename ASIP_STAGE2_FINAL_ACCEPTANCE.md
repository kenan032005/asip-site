# 非洲地区社会安全信息平台（ASIP）——第二阶段最终收尾整改 · 验收报告

> 生成时间：2026-07-30（北京时间） | 项目：`kenan032005/asip-site` | 站点：`https://kenan032005.github.io/asip-site/`
> 本轮范围：**仅关闭第二阶段遗留问题**，形成 canonical-first 完整闭环；不进入第三阶段、不新增信息源、不改视觉、不等待定时任务。
> 本次运行 run_id：`20260730T035933+0800_8psi3h`（pipeline_version=2）

## 一、全链路运行结果（单次 `pipeline_runner.py --mode full --trigger manual`）

| 步骤 | 结果 | 关键产出 |
|---|---|---|
| [1] git pull --rebase | ✅ success | main 已最新（PULL_FAILURE_BLOCKS 生效，失败即中止） |
| [2] 单元测试 ×5 | ✅ success | 24 / 36 / 57 / 28 / 6（详见第三节） |
| [2.5] apply_publication_semantics | ✅ success | clusters=143，历史保留=143，published=143 |
| [3] build_summary | ✅ success | public events=143；24h=0/7d=0；当前政策通过=0；sources=93 |
| [4] generate_reports | ✅ success | 6 国日报生成（窗口内无新增，符合实时采集未接入现状） |
| [4.5] build_site（pre-validate） | ✅ success | 注入 run_id，供 S42 校验 |
| [4.6] validate_stage2（42 项） | ✅ success | **PASS=42 FAIL=0 WARN=0** |
| [5] validate_pipeline（source） | ✅ success | 0 严重错误（1 非严重：legacy 报告窗口跳过） |
| [6] git commit main（data） | ✅ success | 9418de846a9ad3100c771a1aa34f19ed5f6d5743 |
| [7] source_commit 提交 | ✅ success | c9c0d91a2319bdded1c5ff9c81be5e396ea98fd3 |
| [8] build_site（final） | ✅ success | HTML 9 页，ASIP_BUILD_META.run_id 注入 |
| [9] validate_pipeline（dist） | ✅ success | dist.run_id 与 data 一致，事件数 143，0 严重错误 |
| [10] git push origin main | ✅ success | remote main = 6f0daae…（含全部提交 + 日志提交） |
| [11] deploy gh-pages | ✅ success | gh-pages = 3c86e484026c3f0a96c2a8e0820ad26d076b4113 |
| [12] online verify（轮询） | ✅ success | online_run_id=`20260730T035933+0800_8psi3h`，HTTP 200 |
| 退出码 | **0** | `final_status=success` |

运行日志：`logs/pipeline_20260730T035933+0800_8psi3h.json`

## 二、线上验收（9 个关键 URL，全部 HTTP 200）

| URL | 状态 | run_id / 校验 |
|---|---|---|
| `/`（首页） | 200 | 内联 `ASIP_BUILD_META.run_id` ✅ |
| `/data/status.json` | 200 | `20260730T035933+0800_8psi3h` ✅ |
| `/data/public/published_events.json` | 200 | `20260730T035933+0800_8psi3h` ✅ |
| `/data/public/current_metrics.json` | 200 | `20260730T035933+0800_8psi3h` ✅ |
| `/data/latest-summary.json` | 200 | `20260730T035933+0800_8psi3h` ✅ |
| `/data/canonical/event_clusters.json` | 200 | `20260730T035933+0800_8psi3h` ✅ |
| `/data/sources.json` | 200 | 配置型（93 源）；run_id 反映上次信源配置更新，不纳入每轮事件流水线（与项目 S42 口径一致） |
| `/reports/sudan/index.json` | 200 | JSON 合法 |
| `/reports/benin/index.json` | 200 | JSON 合法 |

> 事件数据端点（status/published_events/current_metrics/latest-summary/canonical）run_id **全链路一致**；`sources.json` 为信源配置文件，按设计不参与每轮 run_id 重写（见 S42 口径）。

## 三、23 项证据清单

1. **全链路运行成功**：run_id=`20260730T035933+0800_8psi3h`，exit code 0，`final_status=success`（运行日志）。
2. **git pull --rebase 成功**：`PULL_FAILURE_BLOCKS=True`，失败即中止机制生效；本次 main 已最新。
3. **单元测试 test_country**：PASS=24 FAIL=0。
4. **单元测试 test_stage1_pipeline**：PASS=36 FAIL=0（run_id/时区/窗口/统计/锁/校验退出码）。
5. **单元测试 test_stage2_schema_repo**：PASS=57 FAIL=0（仓储/ID/归一化/发布闸门/导出）。
6. **单元测试 test_repository_integrity**：PASS=28 FAIL=0（强制 Schema / 事务双向关联 / source_rules）。
7. **单元测试 test_no_local_paths**：PASS=6 FAIL=0（扫描 main/dist/public/migration_state/logs）。
8. **canonical→public→legacy 单向导出**：`apply_publication_semantics` clusters=143，历史保留=143，published=143。
9. **build_summary 读 public**：public events=143；24h=0/7d=0；当前政策通过=0（历史迁移保留不计入统计）；sources=93。
10. **generate_reports 读 public**：日报生成（6 国持续跟踪），仅读 `public/published_events.json`。
11. **validate_stage2 42 项全过**：PASS=42 FAIL=0 WARN=0（S01–S42）。
12. **S42 run_id 全链路一致**：main / dist / public 均为 `20260730T035933+0800_8psi3h`（S42 + V12-dist-rid 双重确认）。
13. **validate_pipeline（source）0 严重错误**：1 非严重问题（legacy 报告窗口跳过），可继续部署。
14. **git commit main 成功**：data commit `9418de8` + source_commit 提交 `c9c0d91`。
15. **build_site 注入 run_id**：HTML 9 页，`ASIP_BUILD_META.run_id` 一致。
16. **validate_pipeline（dist）0 严重错误**：dist.run_id 与 data 一致，事件数 143。
17. **git push origin main 成功**：remote `main=6f0daae…`。
18. **deploy gh-pages 成功**：`gh-pages=3c86e48`（remote 一致）。
19. **线上轮询验证成功**：`online_run_id=20260730T035933+0800_8psi3h`，HTTP 200，`verified_at=2026-07-30T04:00:41`。
20. **22 国风险统一（S32）**：cluster 顶层与 legacy_payload 风险等级/标签与 `countries.json` 全部一致。
21. **路径卫生（S35/S36）**：`data/public/`、`migration_state.json`、`logs/`、`dist/` 无本机绝对路径（日志已脱敏）。
22. **来源业务规则（S33）**：`sources.json` 全部通过（Reuters/新华社单源转载≠官方直接来源；ReliefWeb=转载平台）。
23. **文档闭环**：README 第十三/十四节记录第二阶段整改与最终收尾（canonical-first 链路、42 项校验、范围边界"不进入第三阶段"）；运行日志已提交 main。

## 四、范围边界确认（严格遵守 spec）

- ✅ 未新增信息源、未改 Reuters/新华社/GDELT 采集策略。
- ✅ 未引入 Hy3 翻译/摘要、未做自动二次核实引擎。
- ✅ 未改首页/国家页视觉、未新增国家、未改日报正文。
- ✅ 未等待定时任务、未批量重新抓取。
- ✅ 达到校验指标即停止，**未进入第三阶段**。

## 结论

**第二阶段完成。** 全部 23 项证据齐备，线上 9 URL 验收通过，run_id 全链路一致可追溯，gh-pages 已部署且线上验证通过。
