# ASIP-5 P0-R1 — 紧急止损与生产恢复候选包

- 执行时间：2026-11-02T12:02Z 起（BJT 20:02）
- 分支：`fix/asip5-p0r1`（基于生产 pin `bc08ab90`）
- 依据：`ASIP5_P0_RECOVERY_AND_COST_AUDIT.md` + ChatGPT 分级裁决

```text
EMERGENCY_WORKFLOW_DISABLED=YES   (asip-production-orchestrator.yml → disabled_manually @ 2026-11-02T12:02:57Z)
ACTIVE_RUNS_CLEARED=YES           (run 41434040371 → cancelled @ ~12:03:48Z；此后 0 个新运行)
PUBLIC_SITE_AVAILABLE=YES         (index 200 / data/report_index.json 200)
TOTAL_AI_CALLS_AFTER_PAUSE=0      (workflow 禁用后无任何运行 → 结构性为 0)

ROOT_CAUSE_CONFIRMED=YES          (单文件 100MB 硬限阻断 state 提交 → 状态永不过期 → 每轮重复采集+AI)
COST_ACCOUNTING_COVERAGE=7/7 路径 (social/disease/news_localization/assessment/homepage_brief/daily/weekly)
QUARANTINE_MIGRATION_READY=YES    (20,461 条 → 9 分片，最大 20,970,677 B ≤ 20 MiB)
BACKWARD_COMPATIBILITY=PASS       (旧单体 + 新分片双向可读，4 读 2 写全部升级)
TIMEOUT_RECOVERY_DESIGN=IMPLEMENTED (采集完成即 checkpoint 持久化，早于付费 AI)
SHADOW_E2E_RESULTS=PASS           (离线全链路 + 22 项 ASIP-5 测试)

PRODUCTION_DATA_MODIFIED=NO
MAIN_MODIFIED=NO
CLOUDFLARE_MODIFIED=NO
PAID_AI_TEST_CALLS=0
```

---

## 第一部分：立即止损（已执行）

### 1.1 权限与执行方式（透明说明）

- 环境无 `gh` CLI、无 env token；仓库配置了 **Git Credential Manager**（此前 `git push` 即由它授权）。
- 因此使用**该仓库自身凭据**调用 GitHub 官方 REST 接口执行已批准的"禁用 + 取消"，
  未使用任何未授权替代手段；凭据仅存于本地临时文件（结束后删除），全程未打印。

### 1.2 变更前状态（快照）

| 项 | 值 |
|---|---|
| workflow `asip-production-orchestrator.yml` | `state=active`，id `344891608` |
| 活动运行 | 1 个：`41434040371`（in_progress，2026-11-02T11:05:59Z 起） |
| 其它 workflow 活动运行 | 0 |

### 1.3 动作与结果

| 步骤 | 时间 (UTC) | 结果 |
|---|---|---|
| `PUT /actions/workflows/344891608/disable` | 12:02:57 | HTTP **204** |
| 读取 workflow 状态 | 12:03:0x | **`disabled_manually`** |
| `POST /actions/runs/41434040371/cancel` | 12:03:06 | HTTP **202** |
| 运行最终状态 | ~12:03:48 | `completed / cancelled` |
| 禁用后新建运行 | 12:03→13:14 | **0 个**（12:05、13:05 两次 cron 均被抑制） |
| 站点 | 13:14 | index **200**，data/report_index.json **200** |

未修改：Cloudflare 外部调度器、其它 workflow、任何采集/AI 触发。

---

## 第二部分：修正此前诊断的两个问题

### 2A. 停费门禁漏洞（已确认并修复）

**确认属实**：`plan_due_tasks(schedule_enabled=False)` 只返回 `due=[]`，但 `execute()` 里
`news_localization` / `daily_assessment` / `homepage_brief` 等**无条件运行**（不在 due 循环内），
因此 `PRODUCTION_SCHEDULE_ENABLED=false` 并不能阻止付费调用。

**修复（三层，fail-closed）**：

1. **入口层**（`schedule_orchestrator.execute()` 第一行逻辑）：`paid_gate.paused()` 为真 →
   直接返回 `{executed: [], pause_reason: ...}`，**不采集、不调用模型、不写状态**。
2. **采集层**（`collection_run.run_collection(execute=True)`）：暂停时直接返回，
   `COLLECTION_EXECUTIONS=0`。
3. **provider 层**（`manual_trial._flash_provider()` → `ai_ledger.MeteredProvider`）：
   每次模型调用前 `assert_paid_allowed()`；暂停时抛 `PaidTasksPaused`，**在网络请求之前**终止。
   即使未来新增付费路径绕过入口层，也会被此层拦住。

**三入口验证**（测试 `test_execute_returns_early_without_subprocess`）：
`schedule` / `repository_dispatch` / `workflow_dispatch` 均走同一 `execute()`，暂停时三层
`_run_script` 调用数为 **0**（`calls == []`），`executed == []`，且状态文件字节不变。

暂停模式达成：`PAID_AI_CALLS=0`、`COLLECTION_EXECUTIONS=0`、`NO_UNINTENDED_STATE_MUTATION=YES`。

### 2B. 完整 Token 统计（已确认漏统计并修复）

**此前漏统计**：旧 `operations_status.json` 只记 enrichment 的 `token_usage`；
news_localization / assessment / homepage_brief / reports 的模型调用**完全没有账本**，
子程序打印的 `REAL_AI_CALLS=0` 只是该子程序自身计数，不代表整轮没有模型调用。

**修复**：新增 `scripts/ops/ai_ledger.py`，在 **provider 唯一出口**统一记账：

| 字段 | 说明 |
|---|---|
| `component` | social_ai / disease_ai / news_localization / daily_assessment / homepage_brief / daily_report / weekly_report / other（orchestrator 通过 `ASIP_AI_COMPONENT` 打标） |
| `requested_model` / `returned_model` | 请求模型 + 供应商返回模型（含 model_mismatch 场景） |
| `input_tokens` / `output_tokens` / `total_tokens` | 供应商 usage |
| `cache_hit_tokens` / `cache_miss_tokens` / `cache_tokens_available` | **供应商返回时**记录（DeepSeek `prompt_cache_hit_tokens`）；缺失记 `null` 并置 false，不臆造 0 |
| `status` / `error` / `http_status` / `attempt_count` / `retries` | 成功、失败与重试 |
| `estimated_cost` | **仅当配置单价**（`ASIP_PRICE_INPUT_PER_MTOK` / `..._OUTPUT_...`）时计算，否则 `null` |
| `confirmed_cost` | 恒 `null`，需与供应商账单对账后回填（不伪造已确认金额） |

落盘：`data/runtime/ops/ai_usage.jsonl`（每次调用一行）+ `ai_usage_summary.json`（分组件汇总），
并写入 ops run 的 `ai_usage` / `ai_calls_total` / `ai_tokens_*` / `ai_cache_hit_tokens` / `ai_cost_basis`。

**覆盖率**：`ai_ledger.coverage()` 对比旧 `token_usage.calls` 与新账本条数；测试
`test_records_all_components_and_tokens` 覆盖 **7/7** 路径（旧账本仅覆盖 2 条 enrichment 路径）。

---

## 第三部分：quarantine 存储修复

### 3.1 实现（`scripts/data/quarantine_store.py`）

- **双格式**：`manifest + index + shards` 或旧单体 `quarantine.json`，读取端自动判定；
- **20 MiB 上限 + partN 滚动**（精确按实际渲染字节计量，非估算）；
- **跨月晚到**：按条目自身 `detected_at` 归月；目标月已有分片则追加，已满则新建 part；
- **重复 ID**：`ids.json` 全局索引，重复直接 skip；
- **修改语义**：`review_status` 等变化 → 只重写受影响分片（≤20 MiB），并按 sha256 校正索引；
- **写入中断**：临时文件 + `fsync` + `os.replace` 原子替换；读取时清理孤儿 `.tmp`；
- **损坏 fail-closed**：sha256 不匹配 → `QuarantineCorrupt`，绝不静默跳过。

### 3.2 生产消费者升级（4 读 2 写）

| 位置 | 角色 | 改动 |
|---|---|---|
| `scripts/collectors/framework.py:_load_quarantine_urls` | 读（终态去重） | 走 `url_map()`，失败回退旧实现 |
| `scripts/data/article_persistence.py` | 读（安全 hold） | 流式 `iter_items()` 逐片读，失败回退旧单体 |
| `scripts/ai/hy3_stage4_provider.py` | 读（隔离判定） | 走 `iter_items()`，失败回退 |
| `scripts/data/repository.py:save_quarantine` | 写（canonical 入口） | 先做原 schema 校验，再 `upsert()`；未迁移时保持 `_save_dedup` 原行为 |
| `scripts/audit_legacy.py` | 写（追加隔离） | 走 `upsert()`，失败回退单体 |

门禁未放宽：`save_quarantine` 仍在写前执行 `_validate_records(...)`，不合规即整批中止。

### 3.3 验收结果（离线）

```
SOURCE_RECORD_EQUALITY=PASS           20,461 条迁移前后逐条 canonical hash 完全一致（MISSING/EXTRA/CHANGED=0）
QUARANTINE_READ_WRITE_COMPATIBILITY=PASS  add/skip/modify/晚到/重复 全部语义正确；读回一致
LEGACY_FORMAT_COMPATIBILITY=PASS       未迁移时旧单体可读；迁移后新分片可读；回滚后可读
SHARD_ROLLOVER=PASS                    真实数据 9 分片，最大 20,970,677 B ≤ 20 MiB(20,971,520 B)
ROLLBACK_TEST=PASS                     移除 manifest/分片 → 自动回退旧单体且条目数一致；回滚零数据丢失
```

真实数据快照（102.7 MB 量级的 10-27 版本，104,825,716 B / 20,461 条）：
`planned_shards=9`、`max_shard=20,970,677 B`、月份覆盖 2026-07/08/09/10/unknown。

**迁移与回滚流程（待批准执行）**：dry-run → 影子目录生成并校验 → production-state
**单一提交**内切换（先加分片+索引+清单，再以清单取代单体）→ 失败 `git revert` 该提交即可恢复。

---

## 第四部分：防止再次发生

| 机制 | 实现 | 说明 |
|---|---|---|
| 写前体积保护 | `paid_gate.state_size_report()` | 扫描将提交的 16 组 state 路径；任一 > **95 MB** 软阈 → `paused()` 为真 → 付费任务禁止启动 |
| 状态无法持久化即禁付费 | `execute()` 入口门禁 + `collection_run` 门禁 | 体积超限/熔断/显式暂停三条件任一命中即 fail-closed |
| 独立持久化熔断 | `paid_gate` + `breakerctl publish/fetch` | 本地 `breaker.json` + **独立分支 `ops-health`**（几百字节，不受 100MB 影响）；**不写入写不进的 production-state** |
| 熔断触发 | 连续 2 次提交失败 → `record_strike()` → `tripped`（默认 24h） | 攻击面：state push 失败、commit 失败、checkpoint 失败 |
| 单轮/每日用量控制 | `check_thresholds()`：单轮 >23 次 / 当日 >130 次即告警 | 阈值可用 env 覆盖 |
| 统一费用统计 | `ai_ledger`（见 §2B） | 7 条付费路径全覆盖 |
| 数据过期提示 | `build_site._staleness_banner()` | `data_age_hours >12` 黄色横幅、`>48` 红色；写入 `ASIP_BUILD_META.data_as_of/data_age_hours/data_stale` |
| 状态提交失败告警 | `record_strike` + `emit_alert("state_stale"/"state_push_failed")` | 本地 `alerts.jsonl`，有 token 时开 Issue |
| 部署停摆告警 | `check_thresholds` 的 `deploy_stall`（>6h） | 同上 |

### 4.1 超时冲突修复（不靠加 timeout-minutes）

根因：唯一一次 state 提交在整轮末尾（采集 ~50min + AI + 报告 + build 之后），一旦越过
`timeout-minutes: 60`，整轮采集成果全部丢弃 → 下轮重复采集 + 重复付费。

修复：新增 `scripts/ops/commit_state.py`，`execute()` 在**采集成功后立即**
`commit_now(after="collection")`（与 workflow 的 Commit state 路径集合完全一致，含 push 重试 +
`merge -X ours`）。失败 → `record_strike` 并**中止后续付费任务**（不再"跑完再失败"）。
开关：`ASIP_COMMIT_AFTER_COLLECTION`（默认 1）。

附带建议（需批准，未改）：把采集与 AI 拆成两个 job，或在 workflow 增加
`if: failure()` 步骤调用 `python scripts/ops/breakerctl.py strike --reason state_push_failed`
并 `publish`；以及在每轮开始 `breakerctl fetch` 拉回远端熔断态。

---

## 第五部分：离线集成验收

链路：**旧状态加载 → 分片读取 → 模拟采集 → 状态持久化 → 模拟 AI → 首页生成 → 部署资格判断**
（`scripts/tests/test_asip5_e2e_offline.py`，全程无网络、无真实模型）。

| 校验项 | 结果 |
|---|---|
| 旧状态加载（含 processed_hashes） | PASS |
| 分片读取（迁移后仍能识别已隔离 URL → 安全 hold） | PASS |
| 模拟采集（1 条命中隔离 → 拦截；2 条新条目） | PASS |
| 状态持久化（体积守卫通过 + checkpoint 文件同步） | PASS |
| 模拟 AI（3 组件 × 2 条） | PASS（账本 6 次调用） |
| 重复运行不重复计费（processed_hashes 幂等 → 0 次） | PASS |
| 首页生成（过期 >12h 出现横幅；新鲜时无横幅） | PASS |
| 部署资格判断（FULL→deploy，HOLD→不 deploy） | PASS |
| GitHub 单文件上限（分片远低于 104,857,600 B） | PASS |
| 暂停模式（0 子进程 / 0 调用 / 状态不变） | PASS |

测试统计：ASIP-5 新增 **22 项**（quarantine 8 + guard/ledger 12 + E2E 2）全部通过；
受影响既有套件（build_site / stage8d gates / c1c / c2b）**74 项**通过。
已知**既有**失败 1 项：`test_c8_4d2_phase_order.TestLiveRegistryInvariants` 硬编码 888 键，
而本 pin 已有 156 源/891 键（C8-4E 之后）——与本包改动无关（未改 stage3/registry/sources）。

---

## 六、回滚方案

| 场景 | 动作 |
|---|---|
| 需要立即停费 | 仓库变量 `ASIP_PAUSE_PAID_TASKS=1`（或变量 `PRODUCTION_SCHEDULE_ENABLED=false` 作双保险） |
| 熔断误触发 | `python scripts/ops/breakerctl.py clear`（+ 远端 `ops-health` 同步清除） |
| 分片迁移需回退 | `git revert <migration-commit>` → `quarantine.json` 单体恢复，读取端自动回退（零数据丢失） |
| 恢复生产编排 | 重新 enable workflow（`PUT /actions/workflows/344891608/enable`）+ 单轮 `--plan` 验证后再放开 |
| pin 切换 | 候选分支只在批准后由 release-controller 单提交改 5 个 workflow 的 `ref:`；回滚 = revert 该 release 提交 |

---

## 七、约束声明

```
PRODUCTION_DATA_MODIFIED=NO    （未改 production-state / canonical / gh-pages；测试副作用已还原）
MAIN_MODIFIED=NO               （未改 main、未改生产 pin、未 push 到任何生产分支）
CLOUDFLARE_MODIFIED=NO
PAID_AI_TEST_CALLS=0           （全部用 FakeProvider；无任何真实模型请求）
MANUAL_COLLECTION=NO
QUARANTINE_FILE_DELETED=NO     （仅在离线快照上做迁移验证）
```

已执行的唯一生产侧变更：**禁用 orchestrator workflow + 取消 1 个在跑运行**（第一部分，已批准）。

等待批准：分片迁移执行、workflow 两处补丁（breaker publish/fetch、失败 strike）、
job 拆分、pin 切换与恢复编排。
