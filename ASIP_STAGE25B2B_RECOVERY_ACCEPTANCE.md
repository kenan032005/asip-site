# ASIP Stage 2.5B-2B-R 验收记录

## Ingest 中断恢复与状态自动对账

- 执行日期：2026-07-31
- 阶段：Stage 2.5B-2B-R（Interrupted Ingest Recovery）
- 回滚标签：`pre-stage25b2b-recovery`（指向修改前 main HEAD `9960bd7`）

---

## 1. 真实验收暴露的问题

在 Stage 2.5B-2B 跨 WorkBuddy 会话接力验收中，Bash 工具的沙箱提升重试机制导致 ingest
命令实际被执行两次：

- 第一次（沙箱内）：`move_task` 写入 `completed/task_id.json` 成功，
  删除 `processing/task_id.json` 失败并中断；
- 第二次（提升权限后）：`completed` 文件已存在 → `idempotent_success` →
  ingest 直接 `continue`，不清理孤儿 processing 文件和孤儿 lease。

最终状态：`completed=2 / processing=1 / leases=1`，需人工删除孤儿文件才能通过 verify。

**根本原因**：`move_task` 的源文件删除位于目标写入之后，文件系统无法保证跨进程强制终止
的绝对原子性；旧幂等分支仅检查目标文件存在即判定幂等，不做任何清理。

---

## 2. 本次恢复规则

| 场景 | 规则 |
|---|---|
| 唯一状态文件 | 不修改 |
| completed + processing（身份校验通过） | completed 权威，自动清理孤儿 processing + 匹配 lease |
| failed + processing（身份校验通过） | failed 权威，自动清理孤儿 processing + 匹配 lease |
| completed + failed 并存 | 硬冲突，失败关闭（CLI 非零） |
| task_id / cache_key 不一致 | state_identity_conflict，失败关闭 |
| 权威文件损坏 | invalid_authoritative_file，失败关闭 |
| 不匹配 batch/worker 的 lease | 保留并报告冲突 |

**身份校验**：task_id 一致、cache_key 一致、status 与目录对应、completed 包含有效
`ai_result` 且 `ai_result.task_id` 一致。

---

## 3. 修改文件清单

| 文件 | 修改内容 |
|---|---|
| `scripts/ai/workbuddy_queue_provider.py` | 新增 `reconcile_task_state()` 对账函数 |
| `scripts/ai/workbuddy_worker.py` | ingest 幂等分支集成对账；新增 `reconcile_batch()` 与 CLI `reconcile` 命令；`status_summary` 增加 4 个中断恢复字段 |
| `scripts/ai/cross_session_handoff_demo.py` | `verify` 增加残留状态检查 |
| `scripts/tests/test_stage25b2b_recovery.py` | 新增 15 项测试（含中断注入、reconcile 幂等、不匹配 lease 保护） |
| `scripts/pipeline_runner.py` | 加入新测试到固定闸门 |
| `WORKBUDDY_AI_WORKER.md` | 新增第 14 节文档 |

未修改：`README.md`（可选更新）。

---

## 4. 中断注入过程与结果

使用临时目录模拟 KeyboardInterrupt：

1. 创建 completed（含有效 ai_result）+ processing（原始任务）+ lease；
2. 调用 `reconcile_task_state()` / 重新运行 ingest；
3. 验证自动清理与结果保留。

### 测试结果（15/0 全部通过）

| 编号 | 测试 | 结果 |
|---|---|---|
| R1 | completed + processing → 自动清理 processing | PASS |
| R2 | completed + lease → 自动清理匹配 lease | PASS |
| R3 | ingest 返回 reconciled=true + actions | PASS |
| R4 | 孤儿 lease 不存在 | PASS |
| R5 | task_id 不一致 → rejected_state_conflict | PASS |
| R6 | cache_key 不一致 → 冲突报告 | PASS |
| R7 | 损坏 completed → rejected_state_conflict | PASS |
| R8 | completed + failed → state_conflict_count=1 | PASS |
| R9 | status 含 duplicate/orphan 字段 | PASS |
| R10 | status 含 orphan_lease_count | PASS |
| CI-1 | KeyboardInterrupt 模拟 + 完整自动恢复 | PASS |
| CI-2 | reconcile --dry-run 不修改文件 | PASS |
| CI-3 | reconcile_batch 检测并修复 | PASS |
| CI-4 | reconcile 重复运行幂等 | PASS |
| CI-5 | 不匹配 lease 不被删除 | PASS |

---

## 5. 无人工清理证明

- 所有 15 项测试在**不进行任何人工文件删除**的前提下全部通过；
- 中断状态（双文件 + 孤儿 lease）由 ingest 幂等分支自动对账并清理；
- 冲突场景（身份不一致 / 损坏文件 / 双权威状态）正确失败关闭且不删除任何文件。

---

## 6. 回归确认

全部现有测试通过：
- Stage 2.5B-2B 跨会话测试：23/0
- Stage 2.5B-2A 手工交接测试：18/0
- Stage 2.5B-1 协议测试：26/0
- Stage 2.5B-1H 加固测试：15/0
- Stage 2.5A 测试：20/0 + 21/0
- Stage 1 + Stage 2 测试：全部通过

---

## 7. 声明

- 所有数据为 synthetic（不涉及真实新闻/用户）；
- `external_api_calls=0`（本次修复仅限文件状态管理，不调用 AI 模型或网络）；
- 生产 `data/ai` 在测试全程保持为空（仅 `.gitkeep` 占位）；
- 未删除原 `ASIP_STAGE25B2B_ACCEPTANCE.md` 历史记录。
