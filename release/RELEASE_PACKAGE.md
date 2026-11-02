# ASIP-5 发布包（R1C）— 隔离候选 / 迁移与回滚 Runbook

```text
RELEASE_CODE_BRANCH   = release/asip5-code
RELEASE_CODE_SHA      = 见本分支最新提交（parent = 生产代码 pin bc08ab90）
CONTROLLER_BRANCH     = release/asip5-controller
CONTROLLER_BASE       = main @ 3ada28027c0a5f992935d7da3ce4f86496dded61
PIN_IN_WORKFLOWS      = 3dc363ea5c…（5 个生产 workflow 一致切换；无动态 ref）
WORKFLOW_STATE        = disabled_manually（本包未启用）
RUN_MODES             = shadow(默认只读) / collection_only(零付费采集) / production(需授权)
RELEASE_GATES         = ASIP_ALLOW_AUTOMATIC_RUNS=0 / ASIP_ALLOW_MANUAL_PRODUCTION=0（默认全锁）
PRODUCTION_MODIFIED   = NO
```

> 说明（重要）：本仓库的**生产代码谱系**与 `main` 不同：`main` 只承载 workflow + 文档 +
> 部分快照（`scripts/ops/*` 在 main 上基本缺失，`git ls-tree origin/main scripts/ops/` 仅见
> `verify_external_scheduler.py`）。因此"发布候选"被拆成两个互不污染的分支：
> ① **代码 release**（从生产 pin `bc08ab90` 出发，只加 ASIP-5 白名单文件）；
> ② **控制面 release**（从 `main` 出发，只改 5 个 workflow 的 pin 与编排器接线）。
> 禁止把 `fix/asip5-p0r1` 整支合并——它与 main 大幅分叉且带历史数据。

---

## 1. 变更白名单（29 个文件，全部在代码 release 分支）

**新增（8）**
```
scripts/ops/paid_gate.py            scripts/ops/ai_ledger.py
scripts/ops/commit_state.py         scripts/ops/breakerctl.py
scripts/ops/quarantine_migrate.py   scripts/data/quarantine_store.py
scripts/tests/test_asip5_*.py（9 个测试文件）
```
**修改（9 + 1 测试）**
```
scripts/ai/safety/manual_trial.py          （provider 出口：门禁 + 记账，fail-closed）
scripts/ai/providers/deepseek_v4_flash.py  （解析 prompt_cache_hit/miss_tokens）
scripts/ai/hy3_stage4_provider.py          （隔离读取走 store）
scripts/collectors/framework.py            （quarantine 读取走 store）
scripts/data/article_persistence.py        （安全 hold 走 store，fail-closed）
scripts/data/repository.py                 （load/save_quarantine 走 store）
scripts/audit_legacy.py                    （隔离写入走 store）
scripts/ops/collection_run.py              （暂停门禁 + 指标）
scripts/ops/schedule_orchestrator.py       （入口门禁、checkpoint、账本汇总、告警）
scripts/build_site.py                      （数据过期横幅 + meta）
scripts/tests/test_stage8d_daily_deploy_gates.py（stub 签名放宽 component=）
```
**未纳入**：`data/`、站点页面、`sources.json`、任何历史生产数据、C8-4x 分支历史。

## 2. 运行时依赖（导入链，无新增第三方包）

```
scripts.ops.schedule_orchestrator → scripts.ops.{paid_gate, ai_ledger, commit_state, production_state, operations}
scripts.ops.commit_state          → scripts.ops.paid_gate
scripts.ops.breakerctl            → scripts.ops.paid_gate（+ urllib 调 GitHub API）
scripts.ops.ai_ledger             → scripts.ops.paid_gate（provider 包装时）
scripts.data.repository           → scripts.data.quarantine_store
scripts.collectors.framework      → data.quarantine_store（registry 可选，缺则本地 norm_url）
scripts.data.article_persistence  → data.quarantine_store
scripts.ai.hy3_stage4_provider    → scripts.data.quarantine_store
scripts.build_site                → 无新增依赖
```
全部为标准库（json/hashlib/os/pathlib/shutil/subprocess/urllib）——**没有新增 pip 依赖**。

## 3. 生产 workflow 接线（控制面分支）

| 项 | 变更 |
|---|---|
| pin | 5 个 production workflow 的 `ref:` 由 `bc08ab90` → `3dc363ea5c…`（精确 SHA，非分支/非 tag） |
| 新增步骤 | `Fetch breaker state（fail-closed if unverifiable）`：`breakerctl fetch`，失败非零退出 → 本轮不进入付费任务 |
| 替换步骤 | 原"Commit state"整段 shell（`cp` + `git add -A` + `merge \|\| true` + `commit --allow-empty` + 3 次 push 重试）→ **单一** `commit_state.py … --require-expect`（复制校验/add -f/commit/merge/push/远端 SHA/内容校验） |
| 新增步骤 | `Trip breaker on state failure`（`if: failure()`）：`breakerctl strike --repo`（本地已 strike，远端失败只告警，不掩盖原始错误） |
| 顺序 | checkout → load state → guard trigger → **fetch breaker** → orchestrate（采集后内部 checkpoint）→ **guarded final checkpoint** → strike-on-failure → deploy dispatch |
| 三入口 | `schedule` / `repository_dispatch` / `workflow_dispatch` 同走 `execute()` 入口门禁；`PRODUCTION_SCHEDULE_ENABLED` 仍对三者生效 |

YAML 全部 `yaml.safe_load` 通过（5/5）。

## 4. 正式执行顺序（R1D 修订；需批准，本轮未执行任何一步）

```
0) 前置：本包 review 完成；workflow 仍 disabled_manually
1) 代码 release：release/asip5-code（精确 SHA）作为新 pin
2) 控制面：release/asip5-controller 落到 main（仅 5 个 workflow）
3) 离线备份（必须先做，且工作树之外）：
     python scripts/ops/quarantine_migrate.py --root state_src --backup \
       --backup-dir /data/asip-backup --expect 20461
     → 校验 sha256 / 字节数 104825716 / 条目 20461；产出 quarantine.backup.json
4) 迁移（state_src，单一提交；必须提供有效备份清单）：
     --apply --expect 20461 --backup-dir /data/asip-backup     （清单哈希须与当前单体一致）
     --verify --expect 20461                                   （内容级校验）
     --retire --expect 20461                                   （单体 → <4KB 墓碑）
5) 迁移提交（**state-only**，绝不从代码树复制）：
     python scripts/ops/commit_state.py "ops: quarantine sharded + retire" migration \
       --state-only --migration --expect-items 20461
     → 内部：墓碑/manifest/index/ids/分片校验 → commit → 内容校验 → merge → push
       → 远端 SHA == 本地 HEAD → 远端 Git tree 逐文件字节与 expected_tree 完全一致
6) 零付费受控采集（workflow_dispatch，run_mode=collection_only）：
     仅采集 + 采集 checkpoint；AI/localization/assessment/homepage_brief/reports/部署全部禁止
     校验：AI_CALLS=0、state SHA 前进、PHASE_SKIP_RECONCILED=true、deploy_required=false
7) 人工验收：2 个自然周期；核对 ai_calls_total / token 账本 / TRUE_UNACCOUNTED_DROP
8) AI 单轮受控恢复（人工批准；run_mode=production 且仅一轮）
9) 调度恢复：enable workflow（PUT /actions/workflows/344891608/enable）
```

### 只读 plan 验收（不启用 workflow、不采集、不付费）

```bash
PRODUCTION_SCHEDULE_ENABLED=false python scripts/ops/schedule_orchestrator.py --plan --json
# 期望：{"schedule_enabled": false, "plan": {"enabled": false, "due": []}}
ASIP_RUN_MODE=collection_only python scripts/ops/schedule_orchestrator.py --plan --json
python scripts/ops/breakerctl.py status
python scripts/ops/quarantine_migrate.py --root state_src --verify --expect 20461
```

## 5. 迁移/回滚（含"迁移后新增"这一关键差异）

| 操作 | 命令 | 语义 |
|---|---|---|
| 备份 | `--backup --backup-dir <工作树外> --expect 20461` | 复制 + sha256 + 字节数 + 条目数校验，产出 `quarantine.backup.json`；**落在 Git 工作树内会被拒绝（退出码 10）** |
| 迁移提交 | `commit_state.py … --state-only --migration` | **不复制代码树**（避免旧 18MB 单体覆盖新墓碑）；提交前后各校验一次 |
| 迁移 | `--apply --expect 20461 --backup-dir <offline>` | **必须**有有效备份清单且哈希与当前单体一致；已迁移时拒绝重跑（退出码 9） |
| 校验 | `--verify --expect 20461` | 内容级：id 集合/月份归属/ids 映射/index/manifest/分片字节与 sha |
| 退役 | `--retire --expect 20461` | 单体 → <4KB 墓碑（retired=true + 迁移前 bytes/sha/items） |
| 回滚 | `--rollback --expect N` | **先合并全部分片（含迁移后新增）写回单体并校验，再清理分片** → 零丢失 |
| 仅 revert 提交 | `git revert <migration>` | ⚠️ 若迁移后已新增记录，会**丢失增量**；只有"零新增"时可用 |

**关于 >100MB 的回滚单体**：只能用于**离线恢复**（本地校验/离线分析）。它无法再次推入
production-state（单文件硬限），因此"回滚单体"不是可直接恢复生产的方案；生产恢复必须走
"分片 → 合并回单体（离线）→ 再按需重新分片"或直接用分片继续运行。

## 6. 本包测试记录

```
ASIP-5 全量（不含真实快照）          84 passed / 2 skipped
真实快照专项（20,461 条迁移+退役+演练） 2 passed
受影响既有套件                      56 passed / 4 skipped
已知既有失败（与本包无关）            test_c8_4d2_phase_order 硬编码 888 键（本 pin 891）
```


---

## 7. 受控运行方式（workflow 处于 disabled）

**关键事实**：`disabled_manually` 状态下 workflow_dispatch 也会被 GitHub 拒绝。
因此人工受控运行必须"短暂启用 → 立即回禁"，且**必须靠发布闸门而不是靠禁用状态**来防止误跑：

```
# 变量默认（未创建时按 0 处理，即全部锁定）
ASIP_ALLOW_AUTOMATIC_RUNS   = 0     # schedule / repository_dispatch 一律被阻断
ASIP_ALLOW_MANUAL_PRODUCTION= 0     # 人工 production 轮被拒绝（返回码 3）
```

受控采集（零付费）步骤：
1. `gh workflow enable asip-production-orchestrator.yml`（或 API PUT enable）
2. `gh workflow run asip-production-orchestrator.yml -f run_mode=collection_only`
3. 观察：`mode=collection_only`、AI_CALLS=0、`deploy_required=false`、state SHA 前进
4. `gh workflow disable asip-production-orchestrator.yml`（立即回禁）

窗口期风险已由闸门覆盖：即使每小时 cron 在这几分钟内触发，`ASIP_ALLOW_AUTOMATIC_RUNS=0`
会让它**在入口直接返回**（不采集、不写、不付费）；因此"为手动运行而短暂 enable"不会
意外放开定时/外部触发。

**shadow 默认**：`workflow_dispatch` 的 `run_mode` 默认 `shadow` → 即使有人直接点运行，
也只会得到 `mode=shadow, executed=[]`（不采集/AI/报告/写回/部署）。

## 8. 生产切换前置检查清单（执行前逐项打勾）

| # | 检查 | 期望 |
|---|---|---|
| 1 | `git ls-remote origin refs/heads/main` | `3ada28027c`（切换前不变） |
| 2 | `git ls-remote origin refs/heads/production-state` | `1a9cf45267`（切换前不变） |
| 3 | `git ls-remote origin refs/heads/gh-pages` | `60542214e6`（切换前不变） |
| 4 | workflow 状态 | `disabled_manually` |
| 5 | `ops-health` 分支 | 不存在（首次需 `breakerctl bootstrap --repo …`，会建分支+写入+读回校验） |
| 6 | 仓库变量 | 已有 4 个；**需新增** `ASIP_ALLOW_AUTOMATIC_RUNS=0`、`ASIP_ALLOW_MANUAL_PRODUCTION=0` |
| 7 | 备份目录 | 工作树之外（如 `/data/asip-backup`），可写、非仓库路径 |
| 8 | 备份凭据/权限 | 备份只需本地文件权限；state 提交需 `contents:write`（checkout 自带 token） |
| 9 | 熔断读取权限 | `breakerctl fetch/publish` 需 `contents:write`（同一 token） |
| 10 | 回滚 | `--rollback --expect N`（含迁移后新增）；>100MB 单体只可离线恢复 |
| 11 | 只读验收 | `--plan --json` 输出 `due=[]`（或 collection_only 下仅 collection） |
| 12 | 代码 pin | 5 个 workflow 均为同一精确 SHA（无分支/tag 漂移） |
