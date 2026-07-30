# ASIP Stage 2.5A 交付修复与公开仓库验收报告

> 生成时间：2026-07-31 01:22 (UTC+8)
> 仓库：`kenan032005/asip-site`
> 结论：**Stage 2.5A 已完成**（代码 / 测试 / 标签 / commit 全部存在于公开 main 分支）

---

## 一、未交付原因诊断

上一轮对话中，Stage 2.5A 的全部源码已用 Write/Edit 写入本地工作区，但**执行层（Shell）在彼时会话彻底故障**，导致：

- 从未执行 `git add` / `git commit` / `git push`；
- 从未运行测试；
- 从未创建 `pre-stage25a` 标签；
- 从未运行流水线。

因此公开 main 分支确实长期缺少 Stage 2.5A 文件——属于 **"本地已完整编写但未提交、未推送、未打标签"**，而非"实际未完成"。本轮已补齐全部入库与推送动作。

诊断证据（本轮开始时）：

```
git status --short
 M .gitignore
 M scripts/build_summary.py
?? .env.example
?? config/runtime.json
?? data/ai/
?? schemas/ai_result.schema.json
?? schemas/ai_task.schema.json
?? schemas/runtime_config.schema.json
?? scripts/ai/
?? scripts/tests/test_stage25a_runtime_ai_contract.py
```

`git ls-files` / `git ls-tree HEAD` 确认上述文件**均未进入版本库**；`git tag --list` 无 `pre-stage25a`；`git log` 显示 HEAD=`0d13fcc`（上一任务 B 的验收报告 commit，与 `origin/main` 一致）。

确认项：
1. 仓库 = `kenan032005/asip-site` ✓
2. 当前分支 = `main` ✓
3. Stage 2.5A 文件 = **已写入本地、未跟踪、未提交、未推送**（非其他分支 / 非错误仓库 / 非 .gitignore 误排除 / 非实际未创建）✓

---

## 二、修改前 git status（诊断快照）

见上节。关键：所有 Stage 2.5A 文件为 `??` 未跟踪；`.gitignore` 与 `scripts/build_summary.py` 为已修改已跟踪。

---

## 三、当前分支及 remote

- 分支：`main`
- 远程：`origin` = `https://github.com/kenan032005/asip-site.git`（凭据以 git 存储，不入库）
- 推送后本地 HEAD = `origin/main` = `3748df5`（已同步）

---

## 四、pre-stage25a 标签

已创建并推送：

```
git tag -a pre-stage25a -m "Pre-Stage 2.5A: runtime config and AI task contracts isolated, fail-closed, not yet 2.5B"
git push origin pre-stage25a   # -> [new tag] pre-stage25a -> pre-stage25a  (HTTP 200 远程确认)
```

---

## 五、两个功能 commit

1. `545d6ee` — **Stage 2.5A: runtime configuration and AI task contracts**
   （20 files changed, 806 insertions）
   含：`.gitignore`、`config/runtime.json`、`schemas/runtime_config|ai_task|ai_result.schema.json`、`.env.example`、`data/ai/**/.gitkeep`、`scripts/ai/{__init__,exceptions,config,contracts,identifiers,provider,registry}.py`、`scripts/build_summary.py`

2. `0db1d4b` — **Stage 2.5A: WorkBuddy queue provider and safety tests**
   （3 files changed, 562 insertions）
   含：`scripts/ai/workbuddy_queue_provider.py`、`scripts/ai/disabled_provider.py`、`scripts/tests/test_stage25a_runtime_ai_contract.py`

> 注：本地原已存在等价源码，按规范保留原 commit，未制造重复提交。流水线后续追加的 `e1eba69`(data)、`6b906b6`(chore)、`3748df5`(logs) 为回归构建产物 commit，不计入"功能 commit"。

---

## 六、最终 main commit

`3748df5` — `logs: pipeline run_id=20260731T011950+0800_9lyrjq final_status=success`

main 最近 5 条提交：

```
3748df5 logs: pipeline run_id=20260731T011950+0800_9lyrjq final_status=success
6b906b6 chore: set source_commit=e1eba699 for run_id=20260731T011950+0800_9lyrjq
e1eba69 data: Stage-2 run_id=20260731T011950+0800_9lyrjq (canonical->public->legacy+summary)
0db1d4b Stage 2.5A: WorkBuddy queue provider and safety tests
545d6ee Stage 2.5A: runtime configuration and AI task contracts
```

---

## 七、gh-pages commit

`76c8f8f` — `deploy: source 6b906b6`（由 `pipeline_runner.py` 合成并强制推送至 `gh-pages`）

---

## 八、最终 run_id

`20260731T011950+0800_9lyrjq`

线上轮询验证：`http=200`，`online_run_id` 与本地一致，验证时间 `2026-07-31T01:20:57+08:00`。

---

## 九、Stage 2.5A 文件清单（公开 main 可访问，均 HTTP 200）

| 文件 | 状态 |
|---|---|
| `config/runtime.json` | ✅ |
| `schemas/runtime_config.schema.json` | ✅ |
| `schemas/ai_task.schema.json` | ✅ |
| `schemas/ai_result.schema.json` | ✅ |
| `.env.example` | ✅ |
| `scripts/ai/__init__.py` | ✅ |
| `scripts/ai/exceptions.py` | ✅ |
| `scripts/ai/config.py` | ✅ |
| `scripts/ai/contracts.py` | ✅ |
| `scripts/ai/identifiers.py` | ✅ |
| `scripts/ai/provider.py` | ✅ |
| `scripts/ai/registry.py` | ✅ |
| `scripts/ai/workbuddy_queue_provider.py` | ✅ |
| `scripts/ai/disabled_provider.py` | ✅ |
| `scripts/tests/test_stage25a_runtime_ai_contract.py` | ✅ |
| `data/ai/{queue,processing,completed,failed,cache,usage}/.gitkeep` | ✅ |

`scripts/ai` 目录在 main 中真实存在：`__init__.py config.py contracts.py disabled_provider.py exceptions.py identifiers.py provider.py registry.py workbuddy_queue_provider.py`（9 模块齐全）。

---

## 十、修改前失败测试（TDD "先失败"证据）

采用真实"实现缺失"复现：临时移走 `scripts/ai` 后运行测试 →

```
$ mv scripts/ai scripts/_ai_hidden && python scripts/tests/test_stage25a_runtime_ai_contract.py
ModuleNotFoundError: No module named 'ai'   (退出码 1)
$ mv scripts/_ai_hidden scripts/ai   # 恢复
```

证明：缺少实现时测试立即失败（非 skip）。

另：初次运行实现存在版本时，测试在 **T12** 因 `mock.patch.dict(os.environ, ...)` 在 Windows 上恢复超长环境变量（>32767 字符）抛 `ValueError` 而崩溃。此为测试代码的平台兼容缺陷，已在 Commit 2 中改为手动仅操作 `OPENAI_API_KEY`/`GENERIC_AI_API_KEY` 两键修复。修复后全绿。

---

## 十一、修改后通过测试

恢复实现并修复 T12 后运行：

```
RESULT: PASS=21 FAIL=0
ALL STAGE 2.5A CONTRACT TESTS PASSED   (退出码 0)
```

覆盖：T1–T15 + S1–S4（共 21 项断言/扫描）。

---

## 十二、Stage 2 回归结果

流水线 step [2] 单元测试 + T15 子进程回归，全部通过：

| 套件 | 结果 |
|---|---|
| test_stage2_frontend_final.py | PASS=28 FAIL=0 |
| test_stage2_closeout.py | PASS=22 FAIL=0 |
| test_stage2_schema_repo.py | PASS=57 FAIL=0 |
| validate_stage2.py | PASS=54 FAIL=0 WARN=0 |
| validate_pipeline.py | 0 严重错误，"所有关键检查通过" |

---

## 十三、task_id 幂等测试（T8）

`generate_ai_task_id` 基于 SHA-256 内容哈希（不含 Provider 输入），相同输入两次调用一致且格式为 `AIT_<24 hex>`：

```
id_a == id_b == True ; len==28 ; startswith("AIT_")   [PASS]
```

WorkBuddyQueueProvider.submit_task 对相同 `cache_key` 不重复入队（T7）：同一任务提交两次，`data/ai/queue/*.json` 仅 1 个文件，返回同一 `task_id`，`status=queued`。

---

## 十四、cache_key 测试（T9 / T10）

- T9：`generate_ai_cache_key` 相同输入两次一致，前缀 `cache:` `[PASS]`
- T10：`prompt_version` 由 `p1` 变 `p2` 时生成**新** cache_key（不相等）`[PASS]`

---

## 十五、未调用 API 证明（T6 / S2 / S3 / S4）

- **T6**：用 `mock.patch` 对 `urllib.request.urlopen` 与 `socket.create_connection` 打桩为"一旦调用即抛错"，完整跑完队列 Provider 的 `submit_task/health_check/get_task_status/load_result`，断言两个桩均未被调用 `[PASS]`。
- **S2**：扫描 `registry.py`/`config.py`，不存在将 `ai_provider` 自动赋值为 `openai_api`/`generic_api` 的代码；`config.py` 默认值不含付费 Provider `[PASS]`。
- **S3**：`scripts/ai/*.py`（非 tests）不 import 也不调用 `hy3` `[PASS]`。
- **S4**：`scripts/ai/*.py` 不 import 也不调用 `openai` `[PASS]`。
- 运行配置 `ai_processing_enabled=false`，Worker 在 2.5B 才建设。

---

## 十六、密钥扫描结果（S1）

对全仓 `.py/.json/.md/.example/.yaml/.yml` 扫描 `sk-...` / `AKIA...` / 真实 `OPENAI_API_KEY=/GENERIC_AI_API_KEY=` 赋值，结果：**无匹配（key_viol 为空）** `[PASS]`。

`.env` 被 `.gitignore` 忽略且本仓无真实 `.env` 文件；`.env.example` 仅含空值占位，已进入 Git。

---

## 十七、dist 不含 data/ai 证明

- 本地 `find dist -path '*data/ai*'` → 无结果（dist 构建产物不含 AI 内部目录）`[PASS]`
- `build_site.py` 的 `PUBLIC_DATA_ALLOWLIST` 不含 `data/ai` 或 `ai`（T14a）`[PASS]`
- `validate_pipeline(dist)` 通过（流水线 step [9]）`[PASS]`

---

## 十八、公开 GitHub 文件访问结果

通过 GitHub API（`?ref=main`）与线上站点双重验证：

- 9 个核心文件 + 全部 schema + `.env.example` + 测试文件：API 均返回 **HTTP 200**；
- `scripts/ai` 目录 API 列出 9 个模块；
- 线上站点 `https://kenan032005.github.io/asip-site/data/ai/queue/` 返回 **HTTP 404**（公网不暴露内部 AI 目录）；
- gh-pages 分支 `data/ai` 路径 API 返回 **HTTP 404**；
- `pre-stage25a` 标签远程存在（HTTP 200）；
- main 最新提交 `3748df5` 含 Stage 2.5A 提交历史。

即：代码、测试、标签、commit **均真实存在于公开 main 分支**，非仅本地。

---

## 十九、结构化日志路径

`logs/pipeline_20260731T011950+0800_9lyrjq.json`（本地；流水线已提交并推送至 main）

关键字段：`run_id=20260731T011950+0800_9lyrjq`、`final_status=success`、`main_commit=6b906b6`、`gh_pages_commit=76c8f8f`、`online_run_id=20260731T011950+0800_9lyrjq`、`verified_at=2026-07-31T01:20:57+08:00`。

---

## 二十、尚未完成事项（按规范停止，不进 2.5B）

1. **Stage 2.5B 未启动**：AI Worker（消费 `data/ai/queue`、调用 Hy3 真实处理新闻、产出 `completed` 结果）尚未建设——属 2.5B 范围，本次按指令停止。
2. **付费 Provider 仍为禁用占位**：`openai_api`/`generic_api` 在 `registry` 中映射为 `DisabledProvider`，显式选择且缺密钥时失败关闭；未配置任何真实 API Key，未安装 OpenAI SDK。
3. **WorkBuddy 队列自动消费器未建**：当前仅"创建标准任务文件"，不声称任务已被 AI 处理（`ai_processing_enabled=false`）。
4. **未触发任何真实新闻抓取或 Hy3 调用**——全程零外部 AI 网络请求。

---

## 安全与边界复核（第四节硬性要求）

1. 不配置真实 API Key ✅
2. 不调用 OpenAI ✅
3. 不调用通用 API ✅
4. 不调用 Hy3 处理真实新闻 ✅
5. 不自动切换付费 Provider ✅
6. workbuddy_queue 只创建标准任务文件 ✅
7. 不声称队列任务已被 AI 处理 ✅
8. data/ai 不进入 dist / gh-pages ✅
9. `.env` 被忽略 ✅
10. `.env.example` 进入 Git ✅

---

## 最终声明

**Stage 2.5A 完成。**

代码、测试、标签（`pre-stage25a`）与功能 commit（`545d6ee`、`0db1d4b`）现已全部存在于公开 `main` 分支，并经流水线回归构建、部署与线上验收通过。

随后**立即停止**，不进入 Stage 2.5B。
