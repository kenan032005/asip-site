# ASIP V1.0 Production — Release Record

- **Release**: ASIP V1.0 Production
- **Status**: RELEASED
- **Stage**: Stage8D Closed
- **Date (BJT)**: 2026-09-11
- **Repository**: kenan032005/asip-site

## 版本固定（不可歧义）

| 项目 | SHA |
|---|---|
| Production 控制面（main，workflows + 本记录） | `0840c85b842bf6dd5839f1dcf1b83d6ed2ac13e7` |
| **Production 业务代码（release）** | `7e653da88fb45bf67f4c53a7ce356441d4ab9607` |
| release 分支 | `fix/asip-stage8d-release-orchestrator` |
| 最终 gh-pages | `2fbed0247a8733333a4b99087110259b856184dd` |

> 业务代码真实版本以 `production_release_sha` 为准；Production workflow 的 checkout pin 即指向该 SHA。

## 最终自动化证据（自然运行）

| 项目 | 值 |
|---|---|
| 自然根运行 | `34474779375`（2026-09-10T12:05:35Z = BJT 20:05） |
| 触发 | `repository_dispatch` / `external_scheduler_wakeup` |
| provenance | trigger_source=external_scheduler，automation=true，human=false，mode=production |
| 自然 Auto Deploy | `34476141418`（dispatch HTTP 204，shadow_only=false，gh-pages publish EXECUTED） |
| 最终日报 | `DAILY_20260910` / 2026-09-10 / FALLBACK / FACT_GATE=PASS |
| 线上最新日报 | 2026-09-10 |

**Controlled Recovery Deploy（run 34449629776）为人工授权的恢复动作，不计入最终 automation evidence。**

## 线上最终状态

| 数据 | 数量 |
|---|---|
| master_events | 31 |
| disease_outbreaks | 17 |
| event_timelines | 31 |
| report_index | 5 |

## 验证结论

external_scheduler / collection / ai_idempotency / ai_telemetry / disease_automation / daily_freshness /
report_persistence / report_identity / auto_deploy / public_build / v17 / safety / state_integrity /
online_smoke —— **全部 PASS**。

验证阶段历史：Final 24h Observation（completed）→ Post-fix Multi-day Observation（completed）→
Controlled Recovery（PASS，不计入自动化证据）→ **Final Natural Daily Closure（PASS）**。

## Public Build 修复要点

上线版本 `7e653da` 修复了导致站点空化的四个根因：timeline 准入真值未从持久层读取、
compatibility export 因时间格式/run_id 不合规整批中止（V17 随之阻断部署）、
报告路径错配导致 report_index 只剩 DAILY_DEV、report_id 与业务日期脱钩。
新增门禁：`REPORT_ID_DATE_CONSISTENCY_GATE`、`PUBLIC_BUILD_NONEMPTY_SANITY_GATE`、
`PUBLIC_CATASTROPHIC_DROP_GATE`。

## 已知技术债（不在本轮修复）

1. **TD-01** `stage3_collect_v2.py` 900s 超时偶发（最近 `34568487832`）——自动恢复、未污染 state、未突破 Daily SLA，分类 RECOVERED_WARNING。
2. **TD-02** gh-pages 使用 `force_orphan`，发布历史链不适合长期审计；V1.1 评估 history-preserving / atomic publication。
3. **TD-03** 既存非回归测试失败（state-persistence 4 项 + deploy 静态断言 2 项）保持基线。
4. **TD-04** Weekly 部分产物 provenance 的 `report_id` / `report_date` 不完整，不阻断 Daily。
5. **TD-05** `DAILY_DEV` mock 条目仍在兼容 index —— 已显式 `is_mock` 且排末位，不会成为 latest；属清理项。

## V1.0 冻结规则

自本记录起，V1.0 进入 **PRODUCTION MAINTENANCE MODE**：仅允许 P0/P1 生产热修、安全修复、
数据完整性修复与关键可用性修复；新增功能与架构重构一律进入 V1.1。

## V1.1

本 Closeout 未改动 V1.1：`V1_1_CHANGED = false`，状态 `READY_TO_RESUME`（分支 `v11-backfill-v2-full`）。
