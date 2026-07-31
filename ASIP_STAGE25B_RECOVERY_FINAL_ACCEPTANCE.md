# ASIP Stage 2.5B 恢复最终验收记录

## Stage 2.5B-RH 状态对账最终失败关闭加固

- 执行日期：2026-07-31
- 回滚标签：`pre-stage25b-recovery-hardening`（→ `d7c57cc`）
- 前置基线：Stage 2.5B-2B-R（reconcile/interrupted state recovery）
- 最新成功 run_id：`20260731T154041+0800_92b0zj`

---

## 1. 独立审计发现的缺口

| 缺口 | 描述 |
|---|---|
| G1 | 权威 AI Result 仅检查必填键存在，未运行 `validate_ai_result()` 完整 Schema 校验 |
| G2 | cache_key 一致性使用 `if ack and ock and ack != ock` 允许缺失/空值通过 |
| G3 | `os.remove()` 失败被静默忽略，action 仍追加 `removed_*`，`reconciled` 未区分 real vs attempted |
| G4 | Lease 删除仅检查 `batch_id` / `worker_id` 是否匹配（若提供），未验证 manifest 存在性、task 在 manifest 中的存在性 |

---

## 2. 修复措施

- **G1**：在 `_validate_authoritative_file()` 中调用 `validate_ai_result(ai_result)`；completed 额外要求 `ai_result.status == "success"`；failed 要求 status 为 `failed/refused/invalid_output`
- **G2**：`_strict_cache_key_match()` 要求两边 cache_key 均为非空 str 且完全相同
- **G3**：`remove_with_retry_verified()` 重试删除并确认文件不存在；仅成功时记录 `removed_*`；`reconciled` 仅在 `cleanup_succeeded > 0 and cleanup_failed == 0` 时为 true
- **G4**：Lease 删除需通过十项验证（manifest 存在且合法、batch/worker 一致、task 在 manifest.tasks 中等）；`reconcile --apply` 需同时提供 `--batch-id` 和 `--worker-id`

---

## 3. 测试结果

### 加固测试（12/0）

| 编号 | 测试 | 结果 |
|---|---|---|
| H1 | ai_result Schema 违规 → rejected | PASS |
| H2 | completed 缺 cache_key → 冲突 | PASS |
| H3 | processing 缺 cache_key → 冲突 | PASS |
| H4 | cache_key 不一致 → 冲突 | PASS |
| H5 | cleanup_attempted/succeeded/failed 字段存在 | PASS |
| H6 | 仅成功记录 removed_* | PASS |
| H7 | lease 成功清理 + 报告 | PASS |
| H8 | （与 H7 合并）| — |
| H9 | 无 batch/worker 时不删除 lease | PASS |
| H10 | manifest 缺失时不删除 lease | PASS |
| H11 | completed + queue 自动清理 | PASS |
| H12 | dry-run 语义：would_reconcile ≠ reconciled | PASS |

### 原恢复测试回归（15/0）

全部 15 项继续通过。

### 全部回归

- Stage 2.5B-2B Recovery: 15/0
- Stage 2.5B-RH Hardening: 12/0
- Stage 2.5B-2B Cross-Session: 23/0
- Stage 2.5B-2A Manual Handoff: 18/0
- Stage 2.5B-1 Protocol: 26/0
- Stage 2.5B-1H: 15/0
- Stage 2.5A: 20+21/0
- Stage 1+2: 全部通过

---

## 4. 声明

- external_api_calls=0（仅文件状态管理，无模型/网络调用）
- 生产 data/ai 在测试全程保持为空
- 所有测试使用临时目录
- 未处理真实新闻、未修改 Canonic/Public/网页
- 未开始 Stage 2.5C
