# Stage 4 现有 AI 基础设施审计

> 文档目的：记录 Stage 2.5 已建立的 AI 基础设施真实现状，作为 Stage 4 第一执行包（AI 增强数据合同与离线处理框架）的复用基线。只记录实况，不重写既有架构。

**审计时间**：2026-08-02  
**基线**：main@5bad752 / stage4-ai-contract 分支  

---

## 一、Provider 抽象

| 项 | 位置 | 说明 |
|---|---|---|
| 抽象接口 | `scripts/ai/provider.py` → `BaseAIProvider` | 5 个抽象方法：`validate_config / submit_task / get_task_status / load_result / health_check` |
| Provider 注册表 | `scripts/ai/registry.py` → `get_provider()` | **唯一入口**；`register_provider("workbuddy_queue", ...)` 等 4 个内置注册 |
| Provider 实现目录 | `scripts/ai/providers/` | `base.py`（ProviderConfig/BudgetLimit）、`disabled.py`、`generic_api.py`、`openai_api.py`、`workbuddy_queue.py` |
| 队列 Provider | `scripts/ai/workbuddy_queue_provider.py` | 完整队列实现：`count_queued / move_task / reconcile_task_state / WorkbuddyQueueProvider` |

## 二、支持的 API 协议

```text
VALID_PROVIDERS = {"workbuddy_queue", "openai_api", "generic_api", "disabled"}
PAID_PROVIDERS  = {"openai_api", "generic_api"}
```

- `workbuddy_queue`：默认，离线队列（不联网）
- `openai_api` / `generic_api`：付费协议，当前注册为 `DisabledProvider`（不联网），仅显式选择且配置密钥时校验
- `disabled`：安全关闭

## 三、Hy3 / DeepSeek 配置入口

| 项 | 入口 |
|---|---|
| 运行配置 | `config/runtime.json`（`ai_provider` / `ai_model=hy3` / `ai_processing_enabled=false`） |
| 环境变量 | `ASIP_AI_PROVIDER` / `ASIP_AI_MODEL` / `ASIP_AI_PROCESSING_ENABLED` / `ASIP_ALLOW_PAID_FALLBACK` / `ASIP_CLOUD_SCHEDULE_ENABLED` |
| 密钥（绝不入库） | `OPENAI_API_KEY` / `GENERIC_AI_API_KEY`（仅环境读取） |
| 配置加载 | `scripts/ai/config.py` → `load_runtime_config()`（安全默认值 + 环境覆盖 + 校验） |

- **Hy3 入口**：`config/runtime.json` + `ASIP_AI_MODEL=hy3`（WorkBuddy 内部模型）
- **DeepSeek 入口**：无独立 DeepSeek 配置；可通过 `generic_api` 协议 + `ASIP_AI_MODEL=deepseek-*` 表达（本轮不启用）

## 四、Prompt 保存方式

| 项 | 位置 |
|---|---|
| Prompt 包目录 | `prompts/<task_type>/<semver>/system.md` + `user.md` |
| 注册表 | `prompts/registry.json`（active/deprecated/disabled 版本解析） |
| 管理模块 | `scripts/ai/prompt_registry.py`（版本化加载、安全路径解析） |
| 渲染 | `scripts/ai/prompt_renderer.py` |
| Schema 校验 | `scripts/ai/schema_validation.py` |

现有 task_type：`article_analysis / daily_security_brief / disease_risk_analysis / event_synthesis / source_comparison / trend_forecast`

## 五、AI 队列 Schema

| Schema | 位置 | 关键字段 |
|---|---|---|
| AI Task | `schemas/ai_task.schema.json` | `task_id`(^AIT_[0-9a-f]{24}$), `task_type`, `status`(queued/processing/completed/failed/waiting_retry/permanently_failed/cancelled), `content_hash`, `prompt_version`, `provider_requested`, `retry_count` |
| AI Result | `schemas/ai_result.schema.json` | `task_id`, `status`(success/failed/refused/invalid_output), `provider`, `model`, `started_at/completed_at`, `result`, `error`, `usage` |
| AI 缓存 | `schemas/ai_cache_entry.schema.json` | 缓存条目 |
| 运行时配置 | `schemas/runtime_config.schema.json` | runtime 配置 |

## 六、AI 结果写入位置

```text
data/ai/
  queue/      processing/   completed/    failed/
  cache/      usage/        batches/      leases/
  audit/      locks/
```

- 全部由 `.gitignore` 排除（`data/ai/**/*.json` 等），仅保留 `.gitkeep`
- 结果文件按任务状态目录组织，`completed/` 保存最终结果

## 七、runtime 状态保存方式

```text
data/runtime/              ← 运行时状态（被 gitignore）
  article_processing_state.json
.workbuddy_runtime/        ← 备用运行时目录（被 gitignore）
```

## 八、AI 内部文件避免进入 dist

- `.gitignore`：`data/ai/**` 运行时内容全部排除
- `scripts/build_site.py`：只加载白名单 `data/*.json`（`countries/events/latest-summary/public/risk-levels/sources/status`），**不复制 data/ai/ 与 data/runtime/**
- 线上验证：`/data/ai/queue/`、`/data/runtime/`、`/data/canonical/` 均返回 404

## 九、CI 是否已有 Mock Provider

- **无正式 MockProvider 类**。现有测试使用 `unittest.mock` 模拟网络/密钥访问（如 `test_stage25a_runtime_ai_contract.py` 的 `mock.patch("urllib.request.urlopen")`）
- `disabled` provider 可视为安全关闭实现，但不是可返回确定性结果的 Mock
- **结论**：Stage 4 需新建正式 `MockProvider`（不联网、免 Key、可模拟超时/无效 JSON/字段缺失/API 错误）

---

## 十、可复用组件清单（Stage 4 直接复用）

| 组件 | 复用方式 |
|---|---|
| `BaseAIProvider`（provider.py） | 作为 `MockProvider` 与 `WorkbuddyQueueProvider` 的基类 |
| `get_provider()`（registry.py） | MockProvider 注册为 `mock` 后通过统一入口获取 |
| `config.py` 安全默认值 | 扩展 VALID_PROVIDERS 增加 `mock` |
| `prompt_registry.py` | Stage 4 Prompt 注册为新的 task_type 包 |
| `ai_task/ai_result` schema | Stage 4 任务/结果沿用；AI 增强结果单独 `ai_enrichment.schema.json` |
| `data/ai/` 目录体系 + gitignore | 增强结果存 `data/ai/enrichment_results/`（runtime，不入库） |
| `workbuddy_worker.py` 状态机 | 参考其 pending→processing→completed/failed 流转 |
| `test_stage25b1_worker_protocol.py` 队列测试模式 | 参考队列协议测试 |
