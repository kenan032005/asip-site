# WorkBuddy AI Worker 操作手册（Stage 2.5B-1）

> 适用范围：ASIP 项目 `scripts/ai/workbuddy_worker.py`
> 核心约束：**Worker 只做文件与状态管理，绝不调用 Hy3 / OpenAI / 任何外部网络。**
> AI 内容由 WorkBuddy 内置 Hy3 在本机会话内处理，结果按标准契约写回。

---

## 1. 它解决什么问题

Stage 2.5A 只负责"创建标准 AI 任务文件"，不消费队列。2.5B-1 在两者之间建立一套
**符合 WorkBuddy 实际能力的任务交接协议**，让"程序生成任务 → WorkBuddy 领取批次 →
本机 Hy3 处理 → 写标准结果 → Python 校验归档"形成闭环，同时具备：

- **并发安全**（全局 claim 锁）
- **租约与过期恢复**（任务不会因 Worker 崩溃而永久卡在 processing）
- **批次可追溯**（manifest + 规则说明 + 结果模板）
- **幂等与部分成功**（重复 ingest 安全，非法结果不影响同批其他结果）
- **可审计**（JSON Lines 审计日志，无密钥/路径/正文）

---

## 2. 状态目录（均在 `data/ai/`，已 gitignore）

```
data/ai/
  queue/        待领取任务 (*.json)
  processing/   已领取、处理中的任务
  completed/    处理成功
  failed/       处理失败 / 永久失败 (status=permanently_failed)
  cache/        去重缓存 (cache_key)
  usage/        用量占位
  batches/      批次清单 (每个 batch_id 一个子目录)
  leases/       租约 (每个 task_id 一个 *.json)
  audit/        审计日志 (audit_YYYYMMDD.jsonl)
  locks/        全局 claim 锁
```

这些目录默认不入库（见 `.gitignore` 的 `data/ai/**` 段），仅保留 `.gitkeep`。

---

## 3. 命令速查

所有命令支持在子命令**之前或之后**书写 `--ai-root <dir>`（默认 `data/ai`）。

### 3.1 status — 查看队列概览
```bash
python scripts/ai/workbuddy_worker.py status
```
返回 `queue / processing / completed / failed / leases / expired_leases / batches` 计数。

### 3.2 claim — 领取一批任务
```bash
python scripts/ai/workbuddy_worker.py claim \
    --batch-size 3 --worker-id workbuddy-local --lease-minutes 30
```
- 按优先级 `critical > high > normal > low`，同级按 `created_at` 升序选取前 `batch-size` 个。
- 每个任务：`queue → processing` 并写一份 lease。
- 生成 `batches/<batch_id>/{manifest.json, WORKBUDDY_REQUEST.md, results.template.json}`。
- 空队列返回 `{"batch_id": null, "task_count": 0, "tasks": []}`（**不报错**，便于定时脚本判断）。
- **原子回滚**：中途任何失败会把已迁移任务退回 `queue`、删除已建 lease，不留半成品批次。

### 3.3 heartbeat — 续约（仅原 worker）
```bash
python scripts/ai/workbuddy_worker.py heartbeat \
    --batch-id <batch_id> --worker-id <worker_id> --extend-minutes 20
```
- 仅 `batch_id` 归属的 `worker_id` 可续约；他人请求被拒。
- 单次续约 ≤ 30 分钟；非 `processing` 状态拒绝续约。
- 返回 `{"extended": <分钟>, "rejected": [...]}`，`extended=0` 表示无任务被续约。

### 3.4 ingest — 提交结果并归档
```bash
python scripts/ai/workbuddy_worker.py ingest \
    --batch-id <batch_id> --result-file batches/<batch_id>/results.submit.json
```
- 校验：`batch_id` / `worker_id`（取自结果文件）/ 租约 / manifest 归属 / 文件内唯一性 / 契约。
- 每条结果按 `status`：
  - `success` → `processing → completed`（写入 `ai_result`）
  - 其他 → `processing → failed`
  - 非法结果 → **保持 processing**，记录 `reasons`，**不影响同批其他结果**
  - 已完成/已失败任务再次 ingest → `idempotent_success` / `idempotent_failed`（不重复写入）
- 成功后删除该任务 lease。
- 返回报告含 `accepted / failed_tasks / rejected` 及每条 `outcome`。

### 3.5 recover-expired — 过期租约恢复
```bash
python scripts/ai/workbuddy_worker.py recover-expired --dry-run   # 先演练
python scripts/ai/workbuddy_worker.py recover-expired            # 真正执行
```
- 扫描过期 lease：
  - `retry_count + 1 < max_retries` → 任务退回 `queue`，`retry_count++`，**task_id 不变**
  - 否则 → `failed` 且 `status = permanently_failed`
- 删除对应 lease。**不生成新 task_id。**
- `--dry-run` 只返回将被处理的清单，不改动任何状态。

### 3.6 release — 归还整个批次
```bash
python scripts/ai/workbuddy_worker.py release --batch-id <batch_id>
```
- 批次内仍在 `processing` 的任务退回 `queue`，删除该批次所有 lease。
- 返回 `{"released": [...], "skipped": [...]}`，便于中断未完成任务后安全交还队列。

---

## 4. 批次清单（manifest.json）

`claim` 后生成于 `batches/<batch_id>/manifest.json`：

```json
{
  "batch_id": "BATCH_20260730T193653_61b15c",
  "worker_id": "workbuddy-local",
  "created_at": "2026-07-30T19:36:53+00:00",
  "lease_expires_at": "2026-07-30T20:06:53+00:00",
  "task_count": 3,
  "tasks": [ { "task_id": "AIT_...", "priority": "high", "title_cn": "..." }, ... ]
}
```

同一目录还有：
- `WORKBUDDY_REQUEST.md`：本批次处理规则（含 10 条约束，例如"不得伪造 usage、不得外传内容"）。
- `results.template.json`：结果文件骨架，WorkBuddy 处理完后**原地填写** `status/result/error/usage` 等字段，另存为 `results.submit.json` 再 `ingest`。

---

## 5. 结果文件格式（results.template.json）

```json
{
  "batch_id": "BATCH_20260730T193653_61b15c",
  "worker_id": "workbuddy-local",
  "completed_at": "2026-07-30T20:00:00Z",
  "results": [
    {
      "task_id": "AIT_...",
      "schema_version": "1.0",
      "status": "success",
      "provider": "workbuddy_queue",
      "model": "hy3",
      "started_at": "2026-07-30T20:00:00Z",
      "completed_at": "2026-07-30T20:00:05Z",
      "result": { "summary": "…", "confidence": 0.9 },
      "error": null,
      "usage": { "model": "hy3", "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0 }
    }
  ]
}
```

> 内置 Hy3 无可靠 Token 计费接口，故 `input_tokens / output_tokens / estimated_cost_usd`
> 均记 `0`，**不得伪造用量**（W21 静态扫描会拦截伪造/外部调用）。

---

## 6. 审计日志（audit/audit_YYYYMMDD.jsonl）

每行一条 JSON 事件，例如 `task_claimed` / `result_ingested` / `task_completed` / `task_failed`。
- 字段截断为 200 字符。
- **不含**密钥、本地路径、任务正文。
- 可逐行 `json.loads` 解析，便于事后审计与故障回溯。

---

## 7. 典型工作流（模拟，不处理真实新闻）

```bash
# 1) 程序已把任务放进 data/ai/queue/（本阶段用模拟任务演示）
# 2) WorkBuddy 领取
python scripts/ai/workbuddy_worker.py claim --batch-size 3
# 3) 在会话内用内置 Hy3 处理每个 task，填写 results.template.json → results.submit.json
# 4) 续约（若处理耗时接近 30 分钟）
python scripts/ai/workbuddy_worker.py heartbeat --batch-id <B> --worker-id <W> --extend-minutes 20
# 5) 交回结果
python scripts/ai/workbuddy_worker.py ingest --batch-id <B> --result-file batches/<B>/results.submit.json
# 6) 若 Worker 崩溃导致任务过期，恢复：
python scripts/ai/workbuddy_worker.py recover-expired --dry-run
python scripts/ai/workbuddy_worker.py recover-expired
```

---

## 8. 与流水线集成

- `scripts/pipeline_runner.py` 的**构建前单元测试闸门**已加入
  `test_stage25b1_worker_protocol.py`（W1–W25，26 项，须 `FAIL=0`）。
- 运行日志新增 4 个**非敏感**字段（不含密钥/路径/正文）：
  - `ai_worker_protocol_valid`：协议测试是否通过
  - `ai_queue_depth`：`data/ai/queue` 任务数
  - `ai_processing_count`：`processing` 任务数
  - `ai_expired_lease_count`：过期租约数

---

## 9. 安全与隔离边界

- Worker **没有任何** `run-hy3` / `call-model` / `call-openai` 之类的外部网络调用
  （静态扫描 W21 已验证）。
- `data/ai/{batches,leases,audit,locks}` 及其中 `*.md` 不入库，仅保留 `.gitkeep`。
- `dist` 构建白名单与 `validate_pipeline.py` 持续确认不含 `data/ai` 内容。
- 本手册及协议**不处理真实新闻 / 真实 API / 真实数据**；真实执行器属于 Stage 2.5B-2。

---

## 10. 回滚

本阶段回滚基线：**`pre-stage25b1`**（指向 Stage 2.5B-1 开工前 `main` HEAD）。
如需回退，基于该标签重建即可。

---

## 11. Stage 2.5B-1H 协议加固（2026-07-30）

独立审计发现的协议边界问题，已在不重写 Worker 的前提下逐项修复。加固后回滚基线：
**`pre-stage25b1-hardening`**（指向加固前 `main` HEAD `2b9eaa6`）。

### 11.1 租约必须有效且匹配
- `ingest_results` 调用 `validate_active_lease()` 强制校验每条结果持有有效租约。
- 租约缺失/损坏/JSON 不合法/batch_id 不匹配/worker_id 不匹配 → 拒绝并写入脱敏审计。
- `--allow-expired` 仅允许过期不超过 10 分钟（`EXPIRED_GRACE_SECONDS=600`）的租约。
- 已进入 `completed` 或 `failed` 的任务保持幂等返回，不要求租约仍存在。

### 11.2 批次创建事务性
- `claim_batch` 改为临时目录 + `os.rename` 原子创建批次目录。
- `manifest.json` / `WORKBUDDY_REQUEST.md` / `results.template.json` 任一写入失败 → 全部回滚（任务回 `queue`、删 lease、不留半成品目录）。
- 测试用 `_fail_steps={"manifest"|"request_md"|"template"}` 注入故障点验证三种回滚场景。

### 11.3 固定 Provider/Model
- `manifest.json` 新增 `expected_provider` / `expected_model`（当前 `workbuddy_queue` / `hy3`）。
- `results.template.json` 从 manifest 读取这两个值，不再独立写死。
- `ingest` 强制校验 `res.provider == manifest.expected_provider` 与 `res.model == manifest.expected_model`，不一致 → 拒绝。

### 11.4 批次完整性报告
- `ingest_results` 返回新增字段：`manifest_task_count` / `submitted_result_count` / `accepted_task_ids` / `rejected_task_ids` / `missing_task_ids` / `batch_complete`。
- 支持分次 ingest，未提交结果明确记录在 `missing_task_ids`，`batch_complete` 为 `false`。
- `results` 不是数组时整个结果文件被拒。

### 11.5 审计真正脱敏
- `audit()` 先调用 `pipeline_core.sanitize_log_value` 脱敏（Windows/Unix 路径、用户名、疑似密钥、Bearer Token、`sk-` 前缀），再截断为 200 字符。
- `status_summary` 新增 `corrupt_leases` 计数。

### 11.6 参数边界
- `claim`：`batch_size` 1–20、`lease_minutes` 1–30、`worker_id` 1–100 字符 `[a-zA-Z0-9._-]`。
- `heartbeat`：`extend_minutes` 1–30，非法值明确 `ValueError`，不静默 clamp。
- 过期超过宽限期的租约不得续约。

### 11.7 损坏租约处理
- `recover-expired` 发现无法解析的 lease → 标记 `corrupt_lease`（不删除 processing 任务、不自动重新入队），写入脱敏审计，由后续人工 `release` 处理。

---

## 12. Stage 2.5B-2A 单会话 Hy3 手工交接演示（2026-07-30）

目标：在**当前 WorkBuddy 会话内**，用内置 **Hy3（免费）** 模型真实验证「创建任务 → 领取 →
Hy3 处理 → 写标准结果 → 真实 CLI ingest → 完成 → 幂等重 ingest」整条链路，证明 Worker 协议闭环可用。
跨会话接力验证留待 Stage 2.5B-2B。

### 12.1 边界约束
- 仅使用**合成任务**（`synthetic=true`），不处理真实新闻 / 真实 API / 真实数据。
- 仅允许当前 WorkBuddy 内置 **Hy3（免费）**：`provider=workbuddy_queue`、`model=hy3`。
- **禁止** DeepSeek V4 Pro 与 ChatGPT 5.6（付费/外部模型）。
- 用量 `input_tokens / output_tokens / estimated_cost_usd` 一律记 `0`，不得伪造。
- 演示状态全部落在 `.workbuddy_runtime/stage25b2a/`（已 gitignore，绝不入库）。

### 12.2 新增文件
- `scripts/ai/manual_handoff_demo.py`：`prepare`（入队 2 个合成任务 + claim 出批次）/
  `verify`（校验批次清单与字段）/ `cleanup`（删除运行时目录）。
  合成任务为乍得（法语, TCD）+ 尼日尔（英语, NER），均为虚构安全事件。
- `scripts/tests/test_stage25b2a_manual_handoff.py`：**18 项**验收（T1–T18，覆盖
  非空 source_text / 法语·英语语言标记 / 禁用社保·养老金语义 / content_hash 由 source_text
  计算且稳定 / 安全事件与交通中断分类 / 未确认伤亡不得写成已确认 / verify 检查最终状态 /
  verify 失败 CLI 非零 / run 失败 CLI 非零 / 非对象结果 / 全部拒绝 / 部分接受 / 隔离生产等），
  已加入 `pipeline_runner.py` 的单元测试闸门。

### 12.3 CLI 退出码语义（本次新增，2.5B-2A）
`main()` 现在按语义返回退出码，便于定时脚本 / CI 判定：

| 场景 | 退出码 |
|---|---|
| `status` | 0 |
| 空队列 `claim`（返回 `batch_id=null`） | 0 |
| `ingest` 部分接受（accepted>0，含合法 + 被拒混合） | 0 |
| `ingest` 幂等重 ingest（accepted=0 但全部 `idempotent_success`，无错误） | 0 |
| `ingest` **全部被拒**（accepted=0 且 rejected>0） | **≠0** |
| `ingest` 结构性错误（manifest 缺失 / 结果文件不可读 / worker 不匹配） | **≠0** |
| 参数 / 异常错误（如 `claim --batch-size 0`） | **≠0** |

> 不修改任何函数返回结构，仅收敛 `main()` 的退出码；函数级返回（report dict）保持不变。

### 12.4 非对象结果处理（本次新增，2.5B-2A）
- `ingest_results` 在遍历 `results` 时，先判定 `isinstance(res, dict)`。
- 非对象条目（字符串 / 数字 / `null` 等）→ 记为
  `outcome=rejected_invalid_result_type`，计入 `rejected`，**不抛出 AttributeError**，
  继续处理同批其余结果。
- 审计写入脱敏事件 `outcome=invalid_result_type`。

### 12.5 回滚基线
- 本阶段回滚基线：**`pre-stage25b2a`**（指向 2.5B-2A 开工前 `main` HEAD `e10c045`）。
- 与 2.5B-1H 基线 `pre-stage25b1-hardening`（`2b9eaa6`）独立。

### 12.6 验收补正（2026-07-30）：真实社会安全场景 + Hy3 交接证据

独立验收发现原演示将“社会安全”误当成 social security 福利保障、且结果与 source_text
无关、verify 不检查最终状态。补正内容：

- **场景改为真实 ASIP 安全语义**：两个任务均为 `article_analysis` + `synthetic=true`，
  含明确标注虚构的 `source_text`（乍得法语安全事件 / 尼日尔英语交通中断），
  `content_hash` 由 `source_text` 经 SHA-256 计算；`input_ref` 含
  `country_iso3 / source_language / source_text / synthetic / scenario_id`。
  不再出现 `social_security_forum` / `pension_workshop` / `养老金` / `社会保障论坛` 等语义。
- **verify 增强**：`verify()` 现返回 `{ok, checks, errors}`，在 ingest 之后检查 16 项硬性条件
  （manifest 存在、task_count=2、provider/model、queue=0、processing=0、completed=2、
  leases=0、completed 与 manifest 一致、两结果过 Schema、country=TCD/NER、synthetic=true、
  非空 summary_zh、乍得保留“伤亡未确认”、尼日尔不虚构伤亡、无重复 completed）。
  任一失败 `ok=false`。
- **演示 CLI 退出码收敛**：`prepare`/`verify.ok=true`/`cleanup`/`run.ok=true` → 0；
  `verify.ok=false`/`run.ok=false`/参数或异常 → 非 0。不再固定返回 0。
- **测试与真实 Hy3 证据分离**：自动测试用确定性模拟结果证明 Schema/CLI/ingest/幂等/verify
  逻辑；当前会话内置 **Hy3（免费）** 实际读取 `source_text` 并生成中文摘要，经真实 CLI
  ingest → 幂等重 ingest → verify 全绿，证据单独记入
  `ASIP_STAGE25B2A_ACCEPTANCE.md`（仅含非敏感信息）。
- 回滚基线新增：**`pre-stage25b2a-correction`**（指向补正开工前 `main` HEAD）。

## 13. Stage 2.5B-2B-P 跨会话交接准备端（2026-07-31）

> 目标：由当前 WorkBuddy 任务准备一个**隔离的合成 AI 批次**并生成交接文件，
> **不领取、不处理、不生成结果**；随后由一个**全新的 WorkBuddy 任务**接手
> 领取与处理。本阶段验证的是「跨 WorkBuddy 会话交接协议」，不是某一特定模型。

### 13.1 模型与 provider（对应本阶段模型调整）

- `provider` 固定为 **`workbuddy_queue`**。
- `expected_model` 使用 WorkBuddy 内置 **DeepSeek V4 Flash** 的模型标识
  （**`deepseek-v4-flash`**），**不得**将 DeepSeek V4 Flash 伪装成 `hy3`。
- 模型标识只在 `scripts/ai/cross_session_handoff_demo.py` 顶部**单一参数**
  `EXPECTED_MODEL` 定义一次；`HANDOFF_READY.json` / `manifest.expected_model` /
  `results.template.json` / AI Result 的 `model` 字段均以其为唯一来源，
  **不在多个文件中分别写死**。
- 接收端处理时，AI Result 的 `model` 必须与 `manifest.expected_model` **完全一致**。
- `external_api_calls=0`：ASIP Python 程序未直接调用任何外部 API；WorkBuddy 内置
  模型的使用由接收端会话负责，不计入 ASIP 代码 API 调用。

### 13.2 新增文件

| 文件 | 作用 |
|---|---|
| `scripts/ai/cross_session_handoff_demo.py` | 准备端工具：`prepare` / `inspect` / `verify` / `cleanup` |
| `scripts/tests/test_stage25b2b_cross_session.py` | 验收测试（C1–C17，TDD 先红后绿，全部通过） |

### 13.3 命令与职责

```bash
python scripts/ai/cross_session_handoff_demo.py prepare
python scripts/ai/cross_session_handoff_demo.py inspect
python scripts/ai/cross_session_handoff_demo.py verify --consumer-session-id <id>
python scripts/ai/cross_session_handoff_demo.py cleanup
```

- **prepare**：清理旧演示目录 → 建立独立模拟 AI Root
  （`.workbuddy_runtime/stage25b2b/`，已 gitignore）→ 创建 2 个 `synthetic=true`
  的虚构 `article_analysis` 任务写入 `queue` → 生成
  `HANDOFF_READY.json` / `HANDOFF_READY.md`。**不 claim、不建 lease、
  不生成 AI 结果、不 ingest**（`producer_processed_results=false`）。
- **inspect**：检查交接文件存在、`queue=2 / processing=0 / completed=0 / leases=0`、
  无任何 `results*.json`、任务哈希与交接文件一致、`producer_processed_results=false`。
- **verify**（接收端完成后使用）：检查 `queue=0 / processing=0 / completed=2 / leases=0`、
  两个 `task_id` 保持不变、两结果均过 AI Result Schema、`provider=workbuddy_queue`、
  `model=deepseek-v4-flash`、`synthetic=true`、中文摘要非空、
  乍得结果保留“伤亡未确认”、尼日尔结果不虚构伤亡、重复 ingest 无重复结果、
  `consumer_session_id` 与 `producer_session_id` 不同。返回 `{ok, checks, errors}`。
- **cleanup**：删除整个隔离运行时目录。

### 13.4 交接场景（两个新虚构场景，不复用 2.5B-2A 原文）

| country | language | scenario_id | 内容要点 |
|---|---|---|---|
| TCD | fr | `stage25b2b-tcd-curfew` | 虚构城镇短暂骚乱；地方政府临时实施夜间宵禁；主要道路设置检查点；官方未确认伤亡数字（`SCÉNARIO FICTIF` 标注） |
| NER | en | `stage25b2b-ner-roadblock` | 虚构地区道路阻断；安全部门引导车辆绕行；恢复时间尚未公布；官方未报告伤亡（`SYNTHETIC SCENARIO` 标注） |

`source_text` 进入 AI Task；`content_hash = SHA-256(source_text)`。
不使用真实人物 / 真实新闻链接 / 真实事件编号。

### 13.5 HANDOFF_READY 契约

`HANDOFF_READY.json` 至少包含：`handoff_version` / `stage` / `producer_session_id`
（`producer_<8位十六进制>`）/ `created_at` / `repo_commit` / `ai_root_relative`
（`.workbuddy_runtime/stage25b2b`）/ `expected_task_count` / `task_ids` /
`task_content_hashes` / `expected_provider` / `expected_model` /
`consumer_must_claim` / `producer_processed_results`。

`HANDOFF_READY.md` 明确告知新任务 10 条指引：先读本手册；不依赖旧对话；
校验仓库 commit 与任务哈希；自行 claim（以交接文件中的 provider/model 为准）；
用新任务内置 DeepSeek V4 Flash 处理；写标准 results.json；ingest 并幂等重 ingest；
verify（传入自己的 consumer_session_id）；不修改生产 data/ai；不使用外部 API。
交接文件中**不预置**中文摘要或 AI 结果。

### 13.6 边界声明

- 本阶段只做**准备**：不 claim、不调用模型生成结果、不自行完成接收端步骤。
- 准备完成后输出 `READY_FOR_NEW_WORKBUDDY_SESSION` 并停止，等待新会话接手。
- 接收端真实处理证据由新会话单独记录（如实注明 DeepSeek V4 Flash）。
- 回滚基线：**`pre-stage25b2b`**（指向本阶段开工前 `main` HEAD）。

### 13.7 Microfix（2026-07-31）：修复跨会话 Claim 模型传递

独立审计发现：标准 worker CLI 的 `claim` 不支持传入 provider/model，导致接收端
若用 CLI 领取，`manifest.expected_model` 会回落到默认 `hy3`，与
`HANDOFF_READY.expected_model=deepseek-v4-flash` 冲突；同时
`WORKBUDDY_REQUEST.md` 硬编码“使用 Hy3”。

修复内容：

- **claim CLI 新增参数**：
  `--expected-provider`（默认 `workbuddy_queue`）与 `--expected-model`
  （默认 `hy3`），并透传至 `claim_batch`。接收端标准 CLI 领取时显式传
  `--expected-provider workbuddy_queue --expected-model deepseek-v4-flash`，
  manifest / results.template / AI Result 的 model 即与交接契约一致。
- **参数校验**（`_validate_model_ref`）：非空、≤100 字符、仅
  `[A-Za-z0-9._-]`；非法值报错并返回非零，不静默回退；不根据当前模型猜测，
  不伪装模型标识。
- **`WORKBUDDY_REQUEST.md` 动态生成**：从 manifest 读取
  `expected_provider` / `expected_model`，显示“model：`deepseek-v4-flash`
  （DeepSeek V4 Flash）”，并注明“使用当前 WorkBuddy 任务中与上述模型标识
  对应的内置模型；不得更换或伪装模型标识；不调用 ASIP 代码之外的外部 API”。
  计量说明改为通用表述（“当前 WorkBuddy 内置模型未通过 ASIP 代码提供可验证
  Token 计量……不得伪造用量”），不再写死“Hy3 无可靠 Token 接口”。
  旧 `hy3` 批次仍正确显示 Hy3（`_MODEL_DISPLAY_NAMES` 映射）。
- **测试强化**：`test_stage25b2b_cross_session.py` 新增 M1–M6（共 23 项全过）：
  M1 CLI 接受新参数；M2 manifest 携带正确 provider/model；M3 results.template
  与 manifest 一致；M4 REQUEST.md 显示 DeepSeek V4 Flash 且不含硬编码 Hy3；
  M5 未传 `--expected-model` 时保持默认 `hy3`（不破坏旧测试）；M6 空/非法/
  超长模型标识返回非零。M 系列全部通过真实 CLI 执行，不直接调用 `claim_batch`。
- 本 Microfix 未处理任何任务、未生成 AI 结果、未进入接收端。

## 14. Stage 2.5B-2B-R 中断恢复与状态自动对账（2026-07-31）

> 目标：跨 WorkBuddy 会话接力的真实验收中发现——进程在 `move_task` 写入 completed
> 目标文件后删除 processing 源文件前中断，导致同一 task_id 同时存在于两个状态目录
> 且有孤儿 lease 残留。本次修复该缺口，不再依赖人工清理孤儿文件。

### 14.1 问题描述

- 文件系统状态移动无法保证跨进程强制终止的绝对原子性。
- 当 `move_task` 写 completed 成功但 `os.remove(processing)` 中断时，残留双份文件
  及未清理的 lease 会阻碍后续 verify（要求 processing=0 / leases=0）。
- 旧幂等分支仅检查 `os.path.exists(completed/xxx.json)` 即返回
  `idempotent_success`，不做任何清理。

### 14.2 新增核心函数

`reconcile_task_state(task_id, ai_root, batch_id=None, worker_id=None, dry_run=False)`
（位于 `scripts/ai/workbuddy_queue_provider.py`），返回统一报告含
`authoritative_state / states_found / lease_found / actions / conflicts / reconciled`。

#### 权威状态规则

| 场景 | 行为 |
|---|---|
| 唯一状态文件 | 不修改 |
| completed + processing（身份校验通过） | completed 权威，自动清理 processing + 匹配 lease |
| failed + processing（身份校验通过） | failed 权威，自动清理 processing + 匹配 lease |
| completed + failed 并存 | 硬冲突，失败关闭 |
| task_id 或 cache_key 不一致 | state_identity_conflict，失败关闭 |
| 权威文件损坏/不合法 | invalid_authoritative_file，失败关闭 |
| 不匹配 batch/worker 的 lease | 保留并报告冲突 |

身份校验内容：task_id 一致、cache_key 一致、status 与目录对应、
completed 包含有效 `ai_result` 且 `ai_result.task_id` 一致。

### 14.3 Ingest 幂等分支改造

旧逻辑：`os.path.exists(completed)` → `idempotent_success` → `continue`

新逻辑：
- `reconcile_task_state()` → 无冲突 + 有自动清理 → `idempotent_success_reconciled`
- 无冲突 + 无清理 → 原 `idempotent_success/failed`
- 有冲突 → `rejected_state_conflict`（CLI 非零，不自动覆盖）

### 14.4 新增 Reconcile 命令

```bash
# 报告不修改
python scripts/ai/workbuddy_worker.py --ai-root <dir> reconcile --dry-run

# 执行安全清理
python scripts/ai/workbuddy_worker.py --ai-root <dir> reconcile --apply
```

可选 `--batch-id` / `--worker-id` 用于 lease 匹配。存在未解决冲突时 CLI 返回非零。

### 14.5 Status 新字段

`status_summary` 新增：
- `duplicate_state_task_count`：同一 task_id 存在于多个状态目录的数量
- `orphan_processing_count`：completed/failed 任务仍有 processing 残留的数量
- `orphan_lease_count`：completed/failed 任务仍有 lease 的数量
- `state_conflict_count`：completed 和 failed 同时存在的数量

### 14.6 Verify 增强

`cross_session_handoff_demo.py verify` 同时检查上述 4 项新字段均为 0。

### 14.7 审计事件新增

- `task_state_reconciled`
- `orphan_processing_removed`
- `orphan_lease_removed`
- `task_state_conflict`

审计不含本机路径、新闻正文、Prompt、密钥或完整异常堆栈。

### 14.8 新增测试

`scripts/tests/test_stage25b2b_recovery.py`（15 项，含中断注入 + reconcile 幂等 +
不匹配 lease 保护等），已加入 `pipeline_runner.py` 固定闸门。

### 14.9 边界说明

- 硬冲突（completed + failed / 身份不一致）绝不自动处理，需人工审查；
- 不扫描或修改 `ai_root` 以外的路径；
- 所有测试使用临时目录，不操作生产 `data/ai`；
- `external_api_calls=0`：本次修复仅限文件状态管理，不涉及 AI 模型或网络调用。

## 15. Stage 2.5B-RH 状态对账最终失败关闭加固（2026-07-31）

> 独立审计发现 4 类失败关闭缺口：权威文件未使用完整 Schema 校验、
> cache_key 存在性检查不严格、删除操作不验证结果、lease 与 manifest
> 身份未充分验证。本次仅修复这 4 类缺口并加固 CLI 语义。

### 15.1 四类缺口

| 缺口 | 旧行为 | 新行为 |
|---|---|---|
| AI Result Schema | 仅检查键存在 | 调用 `validate_ai_result()` 完整校验；completed 需 status=success；failed 需 status=failed/refused/invalid_output |
| cache_key | `if auth_ck and other_ck and ...` 允许缺失通过 | 必须是非空 str，两边完全相同，否则失败关闭 |
| 删除验证 | `os.remove` 失败静默忽略，仍追加 actions | `remove_with_retry_verified()` 重试 + 确认不存在；仅成功时记录 action |
| Lease 身份 | 仅检查 batch_id/worker_id（若提供） | 十项验证：manifest 存在且合法，batch/worker 一致，task 在 manifest 中，lease 身份一致 |

### 15.2 Terminal + Queue 处理

`completed/failed` 与 `queue` 同时存在时：完成身份和 cache_key 校验后，
terminal 为权威，安全删除残留 queue；不一致则失败关闭。

### 15.3 Reconcile CLI 强身份验证

- `reconcile --dry-run`：可不传 `--batch-id` / `--worker-id`
- `reconcile --apply`：必须同时提供两者，否则参数错误（CLI 非零）

`reconcile_batch` 在指定 `batch_id` 时仅扫描该 manifest 中的任务。

### 15.4 报告语义增强

`reconcile_task_state` 报告新增：
- `cleanup_attempted` / `cleanup_succeeded` / `cleanup_failed`
- `unresolved_paths`（因删除失败残留的文件路径）
- `would_reconcile`（dry_run 使用，与 `reconciled` 区分）
- `planned_actions`（dry_run 时计划执行的操作）
- `actions` 仅记录已成功完成的操作

### 15.5 新增测试

`test_stage25b2b_recovery_hardening.py`（12 项）已加入 `pipeline_runner.py` 固定闸门。

