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
