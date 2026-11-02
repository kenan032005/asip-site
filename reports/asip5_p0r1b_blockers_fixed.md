# ASIP-5 P0-R1B — 生产发布前定向修复（阻断项）

- 基线分支 `fix/asip5-p0r1`，基线提交 `25bea0396`
- 本次提交：本报告同批（分支 `fix/asip5-p0r1`，未合并 main、未改生产 pin、未恢复 workflow）
- 生产 workflow 仍为 `disabled_manually`（2026-11-02T12:02:57Z 起），期间 **未产生任何新运行**

```text
R1B_BLOCKERS_FIXED=5/5
CHECKPOINT_CORRECT_WORKTREE=PASS
CHECKPOINT_STATE_CONTENT_VERIFIED=PASS
CHECKPOINT_REMOTE_REF_VERIFIED=PASS
CHECKPOINT_FAILURE_FAIL_CLOSED=PASS
CHECKPOINT_FAILURE_AI_CALLS=0
PROVIDER_GATE_BYPASS=0
LEDGER_FAILURE_POLICY=FAIL_CLOSED
PAUSE_GATE_3_TRIGGERS=PASS
ALL_QUARANTINE_READERS_MIGRATED=YES
CORRUPT_SHARD_FAIL_CLOSED=PASS
NO_SILENT_LEGACY_FALLBACK=YES
ATOMIC_RECOVERY_TEST=PASS
RECORD_EQUALITY=PASS
ROLLBACK_WITH_NEW_RECORDS=PASS
BREAKER_BOOTSTRAP=PASS
BREAKER_REMOTE_UNAVAILABLE=FAIL_CLOSED
BREAKER_CROSS_RUN_RECOVERY=PASS
BREAKER_CLEAR_AUDIT=PASS
ZERO_PAID_AI_CALLS=YES
PRODUCTION_MIGRATION_PERFORMED=NO
PRODUCTION_DATA_MODIFIED=NO   MAIN_MODIFIED=NO   CLOUDFLARE_MODIFIED=NO
```

---

## 任务 1：采集后 Git checkpoint（重写）

**问题确认（R1 缺陷）**：`commit_state.py` 用 `cwd=ROOT` 执行 git —— 会在**代码工作树**提交；
`git add -A <path>` 路径相对代码根（与 workflow 的 `cd state_src` + 相对路径不一致）；
`check=False` 吞掉 add/commit/merge 的失败码；无远端 SHA 与内容校验。

**修复**（`scripts/ops/commit_state.py`，+256/-… 行）：

| 项 | 实现 |
|---|---|
| 工作树 | 所有 git 通过 `git -C <state_src>`；`assert_state_worktree()` 校验 toplevel ≠ 代码根，否则抛 `CheckpointError(stage="guard")` |
| 路径集合 | `GIT_PATHS` 与 workflow `git add -f` 完全一致（14 项，相对 state_src） |
| 退出码 | `_git_ok()` 对 add / commit / merge / fetch / push **逐步校验**；`commit` 不用 `--allow-empty`；merge 失败时用 `rev-list --count` 显式判定 |
| 远端校验 | push 后 `ls-remote origin production-state` 与本地 `HEAD` 比对，不一致即抛 `verify_remote` |
| 内容校验 | `expect={"path","field","equals"/"present"}` 从 `HEAD:<path>` 读取断言（默认用于 `last_successful_collection`） |
| 失败语义 | 抛 `CheckpointError` + `paid_gate.record_strike()`；调用方必须中止（见任务 2） |

**证据**（`test_asip5_r1b_checkpoint.py`，5/5，本地裸仓库 `remote.git` + 独立 `state_src` 克隆）：

```
test_commit_in_state_worktree_and_verify_remote   PASS  （提交在 state_src；代码树 0 提交；
                                                        远端 SHA == 本地 HEAD；HEAD 内容含本轮 run_id/processed_hashes）
test_refuses_code_worktree                        PASS  （STATE_DIR 指向代码树 → stage=guard，拒绝提交）
test_push_rejected_fail_closed                    PASS  （bare pre-receive 拒绝 → stage=push + strikes+1）
test_commit_failure_fail_closed                   PASS  （commit rc=1 → stage=commit，未吞）
test_content_mismatch_detected                    PASS  （期望值不符 → stage=verify_content）
```

---

## 任务 2：消除付费门禁绕过

| 绕过点（R1） | 修复 |
|---|---|
| checkpoint 失败只 `return False`，同一轮后续无条件 AI 子任务继续跑 | 改为 `raise CheckpointFailed`，`execute()` 中止，`main()` 捕获返回 **2**；`news_localization` / `assessment` / `homepage_brief` 位于 due 循环之后，因此一律不执行 |
| checkpoint **异常**被 `except Exception: emit(...)` 吞掉 | 异常同样转 `CheckpointFailed` 上抛（不用 try/except/pass） |
| `_flash_provider()` 包装失败时 `return inner`（门禁与账本同时失效） | 改为 `raise RuntimeError("provider_gate_unavailable: ...")`；并在构造前 `paid_gate.assert_paid_allowed("provider_factory")` |
| 账本写失败被忽略（仍视作正常计费） | `ai_ledger.ensure_writable()` 在**网络请求前**探针；`record()` 写失败抛 `LedgerUnavailable`；`MeteredProvider` 先探针后调用 |

**三入口 × 三场景证据**（`test_asip5_r1b_gate.py`，12/12）：

| 场景 | schedule | repository_dispatch | workflow_dispatch |
|---|---|---|---|
| 暂停 | 子进程 0 / AI 0 | 相同 | 相同 |
| checkpoint 失败 | `CheckpointFailed`，子进程 **仅 1 次**（collection），AI 0 | 同 | 同 |
| checkpoint 异常 | `CheckpointFailed`，AI 0 | 同 | 同 |

补充：`ledger unwritable → inner.n == 0`（账本不可写时**不发请求**）；
`wrapper import failed → RuntimeError`（不返回裸 provider）；
`GITHUB_ACTIONS=true` 且远端熔断状态不可验证 → `paused=breaker_remote_unverified`。

---

## 任务 3：quarantine 读写兼容与损坏保护

| 项 | 修复 |
|---|---|
| `Repository.load_quarantine()` 仍读旧单体 | 改为 `QuarantineStore.load_items()`（单体/分片自适应） |
| 4 个读者各自的静默回退 | framework / article_persistence / hy3 / repository **统一走 store**；已迁移但损坏 → 抛 `QuarantineCorrupt`，**不回退、不返回空** |
| manifest 在、index 缺失 | `mode()` 抛 `QuarantineCorrupt("manifest present but index.json missing")`（禁止静默回退） |
| 分片缺失/JSON 非法/sha256 不符 | `load_items(verify_checksums)`、`iter_items()`、`verify_consistency()` 全部抛错 |
| 记录级一致性 | `verify_consistency()`：index.total == Σcounts == 磁盘实际 == ids 数 == manifest.total |
| 中断写入 | 原子替换（tmp+fsync+replace）+ 读取时清理孤儿 `.tmp`；已提交分片不被破坏 |
| 回滚 | 新增 `rollback_to_monolith()`：先把**全部分片（含迁移后新增）**合并写回单体并校验，再清理分片 |

**证据**（`test_asip5_r1b_quarantine.py` 9 项 + checkpoint/E2E 交叉）：

```
readers_migrated(代码级)         PASS  （4 个读者均引用 QuarantineStore，无裸 json.load 单体路径）
readers_use_shards_after_migrate PASS  （repository.load_quarantine / framework._load_quarantine_urls）
manifest_without_index           PASS  （QuarantineCorrupt）
missing_shard                    PASS  （load_items + verify_consistency 均抛）
corrupt_shard_not_empty          PASS  （load_items / iter_items 均抛，不返回空）
atomic_recovery_orphan_tmp       PASS  （孤儿 tmp 清理；已提交分片内容逐条哈希不变）
consistency_check                PASS  （on_disk == 条目数 == ids）
rollback_keeps_new_records       PASS  （迁移+2 新增 → 回滚后 42 条，含跨月新增）
真实快照 20,461 条               PASS  （逐条 canonical hash 一致；≤20MiB；+1 新增后回滚保留）
```

---

## 任务 4：独立熔断持久化（ops-health 自举）

| 项 | 实现 |
|---|---|
| 分支不自假设存在 | `ensure_branch()`：先查 `git/ref/heads/ops-health`，404 → 取默认分支 HEAD 建 ref（`POST /git/refs`） |
| publish 首次初始化 | `publish()` 内部先 `ensure_branch`，返回 `bootstrapped: true` |
| 远端不可验证即停 | `fetch()` 失败/文件缺失 → `paid_gate.save_remote_status(False)`；`paused()` 返回 `breaker_remote_unavailable`；`GITHUB_ACTIONS=true` 时"未知状态"亦暂停 |
| 跨 runner 恢复 | 新 runner 本地无状态 → `fetch` 读到远端 `tripped` 并落本地（测试构造 tripped → clear 本地 → fetch → 恢复 tripped） |
| 解除可审计 | `clear` 必须显式 `--reason`（缺则返回 2）；写 `cleared_by/cleared_reason/cleared_at` + `breaker_audit.jsonl` |

**证据**（`test_asip5_r1b_gate.py::TestBreakerBootstrap`，5/5）：`bootstrap_creates_branch_when_absent`、
`publish_bootstraps_then_writes`、`fetch_unreachable_fail_closed`、`cross_run_recovery`、`clear_requires_reason_and_is_audited`。
全部用内存假 GitHub API（`_FakeGitHub`）模拟，**未接触真实远端**。

---

## 任务 5：离线最终集成 + 故障注入

`test_asip5_r1b_e2e.py`（10/10），真实 10-27 状态文件（`production_state.json`）+ FakeProvider +
本地裸仓库；隔离数据默认合成、可切真实 20,461 条（`ASIP5_E2E_REAL=1`）。

主链路：旧状态读取 → 分片迁移（一致性校验）→ 安全 hold（blocked URL 命中）→ 模拟采集（2 新）→
`state_src` checkpoint（push + 远端 SHA 校验）→ 模拟 AI（3 组件 × 2）→ 账本（6 次调用、缓存 4800）→
首页（过期横幅）→ 部署资格（FULL 通过 / HOLD 拒绝）。

| 注入 | 断言 |
|---|---|
| Git push rejected | `stage=push`，strikes+1，无后续付费调用 |
| commit command failed | `stage=commit`，未吞 |
| provider wrapper import failed | `RuntimeError: provider_gate_unavailable`，不返回裸 provider |
| ledger write failed | `LedgerUnavailable`，`inner.n == 0`（未发请求） |
| manifest/index/shard corrupted | `QuarantineCorrupt`，不返回空、不回退 |
| breaker remote unavailable | `paused`，`executed=[]`，子进程 0 |
| job 中途取消 | collection checkpoint 已在远端，`processed_hashes` 不丢（下轮不重复付费） |
| 同一输入重复运行 | 第二次待处理集合为空 → 0 次付费调用 |
| 迁移后新增再回滚 | 回滚后仍含 `Q_after_migration`，零丢失 |

---

## 测试汇总

| 套件 | 结果 |
|---|---|
| ASIP-5 全量（`test_asip5*.py`，不含真实快照） | **58 passed / 2 skipped** |
| 真实快照专项（20,461 条迁移、回滚含新增） | **2 passed** |
| 受影响既有套件（build_site / stage8d gates / c1c / c2b） | **56 passed / 4 skipped** |
| 已知既有失败（与本包无关） | `test_c8_4d2_phase_order` 硬编码 888 键（本 pin 891 键 / 156 源） |

---

## 生产迁移 Runbook（需批准，本轮未执行）

1. 备份：记录 `production-state` 当前 SHA（`1a9cf452`）；确认 `quarantine.json` 104,825,716 B / 20,461 条。
2. 预演：`ASIP5_REAL_SNAPSHOT=<snapshot> python -m unittest scripts.tests.test_asip5_r1b_quarantine.TestRealSnapshotR1B`
   → 必须 `RECORD_EQUALITY`/`ROLLBACK_WITH_NEW_RECORDS` 通过。
   （本机已用真实快照验证 CLI：dry-run 9 分片 / 20,970,677 B；apply 后 index/ids/manifest 均 20,461；verify `consistent=true`）
3. 切换（**单一提交**，在 state_src）：`python scripts/ops/quarantine_migrate.py --root . --apply` 生成 9 分片 + index + ids + manifest；
   校验 `verify_consistency()`；将单体文件替换为 manifest（历史条目已在分片）。
4. 提交：`commit_now("ops: quarantine sharded storage", expect={...})` → 校验远端 SHA 与内容。
5. 首次恢复执行：`workflow_dispatch` + `--plan`（不付费）确认 `schedule_enabled` 与 due 列表；
   再单轮 `collection`（人工批准）。
6. 观测 2 个自然周期：`PHASE_SKIP_RECONCILED=true`、`TRUE_UNACCOUNTED_DROP=0`、`ai_calls_total` 与基线同量级。
7. 恢复编排：`PUT /actions/workflows/344891608/enable`（并确认 `ASIP_PAUSE_PAID_TASKS` 未设置）。

**Workflow 待批准补丁（2 处，未改）**：
```yaml
# 每轮开始
- name: Fetch breaker (fail-closed if unreachable)
  run: python scripts/ops/breakerctl.py fetch --repo ${{ github.repository }}
# Commit state 步骤失败时
- name: Trip breaker on state failure
  if: failure()
  run: python scripts/ops/breakerctl.py strike --reason state_push_failed --repo ${{ github.repository }}
```

## 安全回滚 Runbook

| 场景 | 动作 | 数据影响 |
|---|---|---|
| 需立即停费 | 仓库变量 `ASIP_PAUSE_PAID_TASKS=1` | 无 |
| 熔断误触发 | `breakerctl clear --by <人> --reason <原因>`（写入审计） | 无 |
| 分片迁移回退 | `python scripts/ops/quarantine_migrate.py --root . --rollback --expect <N>`（内部 `rollback_to_monolith()`）：**先合并全部分片（含迁移后新增）写回单体并校验，再清理分片** | 零丢失（保留增量） |
| 仅需撤销一次提交 | 在 state_src `git revert <migration-commit>` — **注意**：若迁移后已新增记录，单纯 revert 会丢增量，必须改用上一行的合并回滚 | 见左 |
| 恢复编排前 | 确认 `breaker_remote.reachable=true`、`paid_breaker.tripped=false`、`state_size.safe_to_persist=true` | 无 |

---

## 约束声明

```
PRODUCTION_DATA_MODIFIED=NO    （未写 production-state/canonical/gh-pages；测试副作用已还原）
MAIN_MODIFIED=NO               （未改 main、未改生产 pin；仅推候选分支）
CLOUDFLARE_MODIFIED=NO
PAID_AI_TEST_CALLS=0           （全部 FakeProvider / 假 API；无真实模型请求）
WORKFLOW_ENABLED=NO            （asip-production-orchestrator 仍 disabled_manually）
```

停止，等待 ChatGPT 最终生产裁决。
