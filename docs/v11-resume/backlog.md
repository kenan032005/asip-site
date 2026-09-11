# ASIP V1.1 Resume — Backlog & Baseline Notes

基线：V1.0 Production Release（业务代码 `7e653da`，控制面 `ec859ad`，tag `asip-v1.0-production`）。
本分支 `v11-resume-after-v1.0` 由 `7e653da` 建立，只迁移仍有效的 V1.1 产品改动。

## 已迁移（本分支）

| 类别 | 内容 |
|---|---|
| V1.1 Homepage | `index.html`（决策驾驶舱）+ `assets/js/home-v11.js`(848 行) + `assets/css/home-v11.css` + `assets/geo/africa-countries.js` |
| V1.1 前端语义 | `assets/js/frontend.js`（NEW/RECENT recencyBadge、riskLevel/diseaseCount 归一、`__ASIP_CUTOFF__`） |
| V1.1 Pipeline | `scripts/ops/backfill_import.py`、`build_backfill_preview.py`、`emit_backfill_report_pages.py`、`homepage_analysis.py`、`v2_preview_semantic_gate.py`、`v2_preview_runtime_verify.js`、`v2_preview_pages_regression.js` |
| V1.1 Map | `scripts/frontend/build_africa_map.py` |
| V1.1 Tests | `scripts/tests/test_backfill_import.py` |
| V1.1 Evidence | `evidence/v11-backfill/preview/**`（views/canonical/disease/reports 08-18..08-27）。
**未迁移** `evidence/stage8d/ASIP_V1_RELEASE_MANIFEST.json`：旧谱系的过期 release manifest，会与 V1.0 正式记录冲突。 |

## 明确未迁移（过时，已由 V1.0 取代）

- 32 个旧 Stage8B/8C/8D bridge / relock / qualification workflow commit（`.github/workflows/*`）——V1.0 已有最终版本。
- 旧版生产管线文件（`timeline_run` / `reports_run` / `collection_run` / `enrichment_run` / `compatibility_export` / `build_site` / `build_frontend_views`）——一律保留 V1.0 版本；`build_site.py` 仅新增一行 `china_interest` 视图拷贝。

## V1.1 待办（承接 V1.0 Closeout 技术债 + 本次发现）

| ID | 项 | 说明 | 来源 |
|---|---|---|---|
| TD-01 | Collection 900s 超时偶发 | 自动恢复、未污染 state、未破 Daily SLA（最近 run `34568487832`） | V1.0 |
| TD-02 | gh-pages `force_orphan` | 发布历史链不适长期审计；评估 history-preserving / atomic publication | V1.0 |
| TD-03 | 既存非回归测试失败 | state-persistence 4 项 + deploy 静态断言 2 项，保持基线 | V1.0 |
| TD-04 | Weekly provenance | 部分产物 `report_id` / `report_date` 不完整 | V1.0 |
| TD-05 | `DAILY_DEV` mock | 仍在兼容 index（已 `is_mock` 且排末位） | V1.0 |
| V11-01 | `china_interest` 视图无生产数据源 | 首页 China Exposure 依赖该视图；冻结期由 backfill preview overlay 提供，生产视图构建器尚不产出 → 首页该区块当前为空态（`API.get` 失败已优雅降级） | 本次迁移 |
| V11-02 | V1.1 semantic gate 不可复跑 | 冻结时未保留原始 V2 bundle 与完整 preview 命名空间（缺 `source_observations.json`、`country_snapshots`），仅有 4 个 preview 视图证据 | 本次迁移 |
| V11-03 | `reports.html` 文案 | V1.1 原文案指向"本地 Preview 验收"，V1.0 已发布真实生产报告，文案需按新语义重写 | 本次迁移 |

## 验证基线（本分支隔离构建，production-state 快照）

master_events 9 / disease_outbreaks 17 / event_timelines 9 / report_index 5（latest `DAILY_20260910`）
——与同期 V1.0 构建逐项一致（数据回归 0）；V1.0 全部生产修复标记保留。
