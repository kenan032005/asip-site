# ASIP 开发模式（Development Freeze / Manual Test Mode）

- 生效时间：2026-08-25T20:08（GMT+3）＝ 2026-08-26T01:08（北京时间）
- 适用范围：ASIP（asip-site，本仓库 fc-stage4 / integration 分支）
- 状态：**开发冻结 / 手动测试模式** —— 暂停所有生产自动化更新，保留全部手动执行能力

---

## 一、统一配置状态

`config/runtime.json`：

```json
"asip_mode": "development",
"development_mode": {
  "production_auto_update": false,
  "scheduled_collection": false,
  "scheduled_ai_processing": false,
  "scheduled_publication": false,
  "scheduled_reports": false,
  "automatic_deploy": false,
  "direct_website_api_call": false,
  "manual_collection": true,
  "manual_ai_trial": true,
  "manual_build": true,
  "manual_ci": true,
  "manual_deploy": true
}
```

既有等效开关（未改动）：`cloud_schedule_enabled=false`、`ai_processing_enabled=false`、`allow_paid_fallback=false`、`ai_provider=workbuddy_queue`。

## 二、已暂停的自动执行入口

| 入口 | 暂停方式 | 保留能力 |
|---|---|---|
| WorkBuddy automation「ASIP 每2小时增量运行（pipeline_runner）」 | status=PAUSED | 可随时恢复（不删除） |
| WorkBuddy automation「ASIP 每日22:00日报运行（pipeline_runner，北京）」 | status=PAUSED | 可随时恢复（不删除） |
| WorkBuddy automation「ASIP 每2小时增量采集」「ASIP 每日22:00全量核实与日报」 | 已为 PAUSED（确认） | — |
| GitHub Actions `asip-pages-preview-republish.yml`（push 自动 preview republish） | 注释 push 触发块 | `workflow_dispatch` 手动触发保留 |
| GitHub Actions `asip-pipeline.yml` | 未动（纯手动 CI） | `workflow_dispatch` CI 完整保留 |
| 定时新闻采集 / AI 队列自动消费 / 自动写入 Public / 自动日报周报 | 由上述 automation 驱动，已随其暂停；无独立常驻进程 | 手动命令保留（pipeline_runner --mode incremental/daily --trigger manual） |

说明：Windows 计划任务（schtasks）因本环境安全策略禁用无法核验；WorkBuddy 层调度已全部暂停，GitHub Actions 无 schedule 触发。

## 三、保护线上快照（冻结基线）

| 项 | 值 |
|---|---|
| main SHA | `79fc8af63960d9d34cbbf0febd48edf4c0f3a374` |
| gh-pages SHA | `0c1eaf5be36c193b5d51cc2fc28b84767b1d22ab` |
| Canonical count | 152 |
| Public count | 11 |
| Public orphan | 0 |
| run_id | `20260802T084000+0800_084349` |
| 冻结时间 | 2026-08-25T20:08（GMT+3） |

冻结约束（自动化暂停后）：
- main 不被自动任务改写（automations 已 PAUSED；Actions 无 schedule）；
- Canonical / Public 不被 schedule 改变；
- gh-pages 不自动变化（preview republish push 触发已注释）；
- AI runtime（data/ai/）不公开（.gitignore 覆盖，dist 白名单不含）；
- 当前线上站点保持现有稳定快照可访问。

## 四、Stage 4 状态

```text
stage4_engineering_status = complete
  - Prompt v1.1 完成（version=1.1.0）
  - WorkBuddy Queue 桥接完成（hy3_stage4_provider.py）
  - Stage 4 桥接 / Provider/collect 完成
  - Public enrichment apply 完成（stage4_apply_enrichment.py，默认 dry-run）
  - 前端 title_zh/summary_zh fallback 完成
  - 最新 main 整合完成（stage4-production-integration @ d446623）
  - Stage 4 测试 100/100

stage4_production_ai_activation = deferred
deferred_reason = hy3_rate_limit
```

Hy3 因当前 WorkBuddy 限流，正式生产内容激活暂缓；**不阻塞后续 Stage 5/6/7 开发**。

## 五、开发 / 功能验证测试模型规则（临时）

```text
execution_route   = workbuddy_queue
actual_model      = deepseek-v4-flash
direct_website_api_call = false
usage_purpose     = development_test
```

允许用途（验证链路）：队列 / Prompt / Schema / collect / Public apply / 前端中文展示 / Stage 5-7 工程流程。

禁止：
- 不得标记为 Hy3；
- 不得作为最终 Hy3 生产质量验收依据；
- 不得自动成为正式 production active result；
- 不得因测试结果改变正式模型策略。

## 六、正式生产内容规则（保留）

正式生产内容处理仍计划：

```text
WorkBuddy Queue → Hy3
```

等 Hy3 可稳定使用、或用户重新裁定模型策略后做最终 production activation；届时只需小规模最终验收，不重新执行全部工程开发。

## 七、手动执行入口清单（全部保留）

| 能力 | 入口 |
|---|---|
| 手动采集 | `pipeline_runner.py --mode incremental --trigger manual` |
| 手动日报 | `pipeline_runner.py --mode daily --trigger manual` |
| 手动 CI | GitHub Actions `asip-pipeline.yml`（workflow_dispatch） |
| 手动构建 | `python scripts/build_site.py` |
| 手动 AI 试跑 | produce → 消费者写回 → collect（Hy3Stage4Provider，expected_model 显式传） |
| 手动 Public apply | `python scripts/stage4_apply_enrichment.py --apply` |
| 手动部署 | GitHub Actions `asip-pages-preview-republish.yml`（workflow_dispatch） |

恢复自动化：将对应 automation 置回 ACTIVE；恢复 preview 自动触发则取消 workflow push 注释（代码与配置均未删除）。
