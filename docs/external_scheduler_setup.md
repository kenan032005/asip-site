# External Automated Wake-up — 配置说明（Stage8D §十七/§十八）

## 1. 为什么需要外部调度

Observation V2 实测（窗口 2026-08-29T02:40:07Z → 2026-08-30T02:40:07Z）：

```
EXPECTED_HOURLY_TICKS = 24
ACTUAL_NATURAL_RUNS   = 6
MISSED_TICKS          = 18（命中率 25%）
MAX_GAP_BETWEEN_RUNS  = 361 min
```

结论：**GITHUB_NATIVE_SCHEDULE_PRIMARY = REJECTED**。GitHub 原生 cron 只能作为
secondary wake-up，主唤醒改由外部调度器发起。

## 2. 接收端（已完成，本仓库内）

`asip-production-orchestrator.yml` 新增：

```yaml
on:
  repository_dispatch:
    types: [external_scheduler_wakeup]
  schedule:
    - cron: '0 * * * *'      # secondary wake-up，保留
  workflow_dispatch:         # 仅人工 canary
```

安全约束（fail-closed）：

- 只有 `client_payload.trigger_source == "external_scheduler"` 才被认定为
  **automation**；否则 workflow 以 `::error::` 直接失败（Guard 步骤）。
- 代码与 workflow 中**不含任何 token**；凭据由外部调度器的 Secret 管理。
- 幂等由 due-planner + production-state + AI 结果缓存共同保证：
  同一小时内外部调度先跑、GitHub 延迟 schedule 后到时，不会产生
  重复任务 / 重复 AI 调用 / 重复报告 / 重复部署。

## 3. 用户需完成的最少配置步骤

前置条件：一个能按小时发出 HTTPS 请求的外部调度器（任选其一）：

- 云服务器 / NAS / 常开电脑的 `cron` + `curl`
- GitHub Actions（**另一个**仓库，注意：同仓库会与生产 workflow 相互干扰）
- Cloudflare Workers Cron Triggers / cron-job.org / UptimeRobot（仅 GET 场景不适用）
- 任意 CI（GitLab CI、Jenkins、云函数定时触发器）

步骤：

1. 创建 Personal Access Token（**fine-grained**）：
   - Repository access：`kenan032005/asip-site`（Only select repositories）
   - Permissions → **Contents: Read and write**，**Actions: Read and write**
     （只需 `repository_dispatch`，最小集为 Contents: R/W + Metadata: R）
   - 过期时间建议 ≤ 90 天，到期轮换。
2. 把 token 存入外部调度器的 **Secret 管理**（不要写进代码、workflow、gh-pages、
   前端、本仓库任何文件）。例如服务器：`export ASIP_GH_TOKEN=...`（写入
   `~/.bashrc` 以外的 secret store，或 systemd credential / GitHub Actions Secrets）。
3. 在外部调度器上配置每小时执行一次（分钟不限，建议 `:05`）：

```bash
curl -sS -X POST \
  -H "Authorization: Bearer ${ASIP_GH_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/kenan032005/asip-site/dispatches \
  -d '{"event_type":"external_scheduler_wakeup","client_payload":{"trigger_source":"external_scheduler"}}' \
  -o /dev/null -w "WAKEUP_HTTP=%{http_code}\n"
```

   期望返回 `204 No Content`（HTTP 码 204）。

4. 验证：运行本目录下的验证脚本

```bash
python scripts/ops/verify_external_scheduler.py \
  --repo kenan032005/asip-site \
  --token-env ASIP_GH_TOKEN
```

   或只读检查（不发起 dispatch，仅查询最近运行并判定 automation 来源）：

```bash
python scripts/ops/verify_external_scheduler.py --repo kenan032005/asip-site --check-only
```

## 4. 验收判据

外部唤醒成功时，orchestrator 运行应显示：

```
trigger_source = external_scheduler
trigger_type   = automation
automation     = true
human          = false
mode           = production
```

并且 deploy（如触发）的 provenance 为 `scheduled_orchestrator_auto_dispatch`，
携带 `root_orchestrator_run_id`。

## 5. 当前状态

- 接收端：**READY**（已实现并随本次修复进入 main）
- Provider / credential：**未配置** → `EXTERNAL_SCHEDULER_CONFIGURED = false`
  （如实记录，不伪造为 true）
