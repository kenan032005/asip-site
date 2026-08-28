# Stage8D Schedule & Production-Mode Root Cause Report

- 日期：2026-08-28（BJT 至次日凌晨）
- 范围：V1.0 Production Automation 修复（不含 V1.1；V1_1_CHANGED=false）
- 旧 Observation（2026-08-28 01:50 → 2026-08-29 01:50 BJT）：**OBSERVATION_INVALID_FOR_CLOSEOUT=true**
  原因：natural schedule 覆盖不足 + schedule 运行全部进入 Shadow（无真实生产内容）。

---

## 1. 为什么 schedule slots 缺失？

直接读取远端 main（9c4bea0）四个 production workflow：
- 四个 workflow 均 `active`；default branch = `main`。
- 声明的 cron 全部正确（见第 5 节 schedule math，SCHEDULE_MATH=PASS）。
- 但窗口内（17:50Z 8/27 → 17:50Z 8/28）预期 10 个 tick，仅出现 **3 个 schedule 运行**
  （AI 01:34:48Z、Collection 06:10:30Z、AI 06:14:54Z），且全部**严重延迟**
  （相对最近 tick 延迟 1h45m–3h+）；reports（12:00Z）、disease（17:30Z）、
  06:14Z 之后的 collection/AI 槽位全部 MISSED（0 补跑）。
- 72h 复查：provenance 之外无更早 schedule 运行（workflows 于 8/27 18:12Z 才首次上 main，
  此前无 schedule 可能）。
- 结论：非配置错误（cron/workflow state/default branch/Actions 权限均正常）→
  **GITHUB_SCHEDULE_DELAY_OR_DROP；GITHUB_SCHEDULE_RELIABILITY_RISK = true**。

## 2. 为什么触发时间与 cron 不对齐？

- 3 个实际运行创建时间为 01:34Z / 06:10Z / 06:14Z，与任何声明 tick（22:20/22:30、
  04:20/04:30、10:20/10:30、12:00、16:20/16:30、17:30Z）都不对齐；
  且 06:14Z 之后调度完全停止。
- 归因：GitHub Actions 原生 schedule 的高延迟/丢 tick 行为（只读证据无法进一步细分
  平台内部原因），故按证据归因为 `GITHUB_SCHEDULE_DELAY_OR_DROP`。

## 3. 为什么自然运行进入 Shadow？（核心 Blocker，已修复）

- 三个 production workflow 均用 `github.event.inputs.*` 决定 production/shadow：
  - collection：`${{ github.event.inputs.execute }}` → schedule 下为空 → 不传 `--execute`
    → `collection_run.py` 走记账路径（sources_attempted=0）。
  - AI：`${{ github.event.inputs.run_ai }}` → 为空 → `--fake --max-items 0`
    → `ENRICHMENT processed=0 skipped=9/19`。
  - reports：`${{ github.event.inputs.source }}` → 为空 → `source=derived --no-ai`（shadow）。
- 同时四个 workflow 均硬编码 `env: ASIP_MODE: development`。
- 证据：`asip-production-collection.yml` L63-67、`asip-production-ai.yml` L75-93、
  `asip-production-reports.yml` L71-92（release SHA ae582a2 / main 9c4bea0 一致）。
- 修复：新增 hourly orchestrator（`scripts/ops/schedule_orchestrator.py` +
  `asip-production-orchestrator.yml`），schedule 事件由 orchestrator 以
  **production mode** 显式执行（`resolve_mode(schedule)=production`；manual dispatch
  保持默认 shadow、可显式 production）。collection/ai/reports 移除原生 schedule。

## 4. Disease 为什么没有 dedicated tick？

- AI workflow 的 disease step 只是同一 job 里的一个 step，且 schedule 下 `run_ai` 为空
  → 永远 `--fake --max-items 0`；专门的 `30 17 * * *`（BJT 01:30）tick 在窗口内
  **从未触发**（0 次）。
- 修复：orchestrator 依据 `last_disease_run` + BJT 01:30 判定 due，独立执行
  `enrichment_run.py --kind disease`（真实 provider；无 new eligible 则 0 calls）。

## 5. Daily 为什么没有运行？

- `0 12 * * *`（BJT 20:00）tick 在窗口内未触发（0 次）；即便触发，schedule 路径
  也默认 `source=derived --no-ai`（shadow）。
- 修复：orchestrator 依据 `last_daily_report` + BJT 20:00 判定 due，以
  `--source canonical`（production）生成，FULL/FALLBACK/LOW_DATA 为合法，
  Fact Gate FAIL → HOLD（`classify()` fail-closed 既有逻辑）。

## 6. Auto Deploy 为什么没有自然证据？

- reports workflow 的自动 dispatch deploy 步骤存在且正确（`AUTO_DEPLOY_ENABLED` 门禁），
  但 reports workflow 从未由 schedule 运行 → 无自动部署；窗口内仅 2 次
  workflow_dispatch（Stage8D 搭建链，手动，不计 Observation）。
- 修复：orchestrator 生成 daily 报告且分类合法 → 先提交 state、再 dispatch deploy
  （`shadow_only=false`，AUTO_DEPLOY_ENABLED=true 时）；canary 模式 dispatch
  `shadow_only=true`（build/validate/secret-scan，不发布）。

## 7. 最终修复是什么？

- 新增：`scripts/ops/schedule_orchestrator.py`（plan_due_tasks 纯函数 + 生产执行器）、
  `.github/workflows/asip-production-orchestrator.yml`（唯一 schedule 入口，cron
  `0 * * * *` 每小时；workflow_dispatch canary）。
- 修改：collection/ai/reports 移除原生 schedule（仅 dispatch）；4 个 workflow checkout
  ref 统一到新 release（含 orchestrator + 测试）；orchestrator 在 AI 后执行
  `compatibility_export` 再生成 events/public 视图并随 state 提交；deploy 加载 state
  时同步拷贝视图文件；orchestrator 先提交 state 再派发 deploy（防竞态）。
- 测试：`scripts/tests/test_stage8d_orchestrator.py` 18 项全 PASS
  （schedule→production、manual shadow、PRODUCTION_SCHEDULE_ENABLED=false 阻断、
  due planner 各 tick、idempotency、schedule math、export 导入回归）。
- Canary：orchestrator canary#4（cc1ac13 时代）真实 collection（sources_succeeded=1）、
  真实 social AI、disease 0 calls（合法）、timeline、views_export ok、state 提交成功；
  shadow deploy 成功（Build OK、V13 PASS、V17 PASS 152=152、secret_leak_count=0）。
- AUTOMATION_FIX_SHA = **cc1ac13806314e29f0dc8ce3ef15e3652a5ea4ec**（main）。

## 8. 是否采用 Hourly Orchestrator？

**是**。判定依据：cron 正确、workflow active、default branch 正确、Actions 权限正常，
但原生 multi-cron 实测 7/10 tick MISSED、3 个延迟 1h45m–3h
（GITHUB_SCHEDULE_RELIABILITY_RISK=true）→ 符合 §15 采用条件。
实现为**最小** hourly orchestrator（单一 `0 * * * *` + state 判定 due），
未重写 pipeline；幂等由 `processed_hashes` / `last_successful_*` / 报告日期保证；
允许 GitHub 延迟一小时仍可在下一小时补执行 due 任务（`trigger=scheduled_orchestrator`）。
