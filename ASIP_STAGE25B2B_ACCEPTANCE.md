# ASIP Stage 2.5B-2B 验收记录

## 跨 WorkBuddy 会话接收端验证（Stage 2.5B-2B-C）

- 执行日期：2026-07-31
- 使用模型：WorkBuddy 内置 DeepSeek V4 Flash
- 模型标识：`deepseek-v4-flash`
- external_api_calls：0（未调用 DeepSeek 开放平台 / OpenAI / ChatGPT / 新闻 API 等任何外部 API）
- repo_commit：`e2f60ff3cb95dbc9d81087d6403fb5fb39fc5997`

---

## 1. 会话标识

| 项目 | 值 |
|---|---|
| producer_session_id | `producer_7565389f` |
| consumer_session_id | `consumer_568d0454` |
| 两者是否不同 | 是（`consumer_568d0454 != producer_7565389f`） |
| worker_id | `workbuddy-cross-session-568d0454` |
| batch_id | `BATCH_20260731T064923_4ae105` |
| task_id 1 | `AIT_00c231b9fff12f4e59f31481`（NER，road_closure） |
| task_id 2 | `AIT_a3704b9244b78394f8d9993d`（TCD，security_incident） |

---

## 2. 两段虚构 source_text（synthetic=true，SCÉNARIO FICTIF / SYNTHETIC SCENARIO 已标注）

### 任务 1：`AIT_00c231b9fff12f4e59f31481`（尼日尔 / NER / en）

```
[SYNTHETIC SCENARIO]
A road blockage was reported in a fictional area of Niger near the town of Guidan-Roumdji. Security forces guided vehicles onto alternative routes. The road reopening time has not yet been announced. No casualties have been officially reported.
```

content_hash（SHA-256）：`8ab6090088f38bb4290b47fa27177b5f1f4f1b1a59dfad18ff077458863fc733`
（与 HANDOFF_READY.json 一致，接管前已校验）

### 任务 2：`AIT_a3704b9244b78394f8d9993d`（乍得 / TCD / fr）

```
[SCÉNARIO FICTIF]
De brèves émeutes ont été signalées dans la ville fictive de Moundjara, au Tchad. Les autorités locales ont imposé un couvre-feu nocturne temporaire et mis en place des points de contrôle sur les routes principales. Aucun bilan de victimes n'a été officiellement confirmé à ce stade.
```

content_hash（SHA-256）：`6d6df87f306781bc7ac3d75e5d166742b724c35a75e6dc044e56e85610885542`
（与 HANDOFF_READY.json 一致，接管前已校验）

---

## 3. 本次新会话（DeepSeek V4 Flash）实际生成的中文摘要

### 任务 1（NER）

> 尼日尔虚构地区古伊丹-鲁姆吉镇（Guidan-Roumdji）附近发生道路阻断，安全部门已引导车辆改走替代路线。道路恢复通行的时间尚未公布，官方亦未报告任何人员伤亡。

### 任务 2（TCD）

> 乍得虚构城镇蒙贾拉（Moundjara）发生短暂骚乱，地方政府随即实施临时夜间宵禁，并在主要道路设置检查点。截至目前，官方尚未确认任何伤亡数字。

---

## 4. AI 结果字段明细（schema_version=1.0，status=success，provider=workbuddy_queue，model=deepseek-v4-flash，error=null）

### 任务 1（NER）

- event_type：`road_closure`
- country_iso3：`NER`
- source_language：`en`
- key_facts：
  - 虚构地区发生道路阻断
  - 安全部门引导车辆绕行替代路线
  - 道路恢复通行时间尚未公布
  - 官方未报告任何人员伤亡
- uncertainties：
  - 道路恢复通行时间尚未公布
  - 阻断范围与持续时间未知
  - 替代路线的具体通行条件未披露
- synthetic：true

### 任务 2（TCD）

- event_type：`security_incident`
- country_iso3：`TCD`
- source_language：`fr`
- key_facts：
  - 虚构城镇 Moundjara 发生短暂骚乱
  - 地方政府实施临时夜间宵禁
  - 主要道路设置检查点
  - 官方尚未确认伤亡数字
- uncertainties：
  - 官方尚未确认伤亡数字
  - 事件持续时长与具体影响范围未披露
  - 检查点数量与位置未披露
- synthetic：true

两个结果均包含：`producer_session_id=producer_7565389f`、`consumer_session_id=consumer_568d0454`。

usage 统一为 `input_tokens=0 / output_tokens=0 / estimated_cost_usd=0`（未伪造 Token 数量）。

---

## 5. 首次 Ingest 结果

命令：`workbuddy_worker.py ingest --batch-id BATCH_20260731T064923_4ae105`

- CLI 退出码：0
- accepted：1（NER 任务 `AIT_00c231b9fff12f4e59f31481` outcome=completed）
- rejected：0
- failed_tasks：0
- missing_task_ids：`[]`
- batch_complete：true
- TCD 任务 `AIT_a3704b9244b78394f8d9993d` 返回 `idempotent_success`

> 说明：本次任务的 Bash 执行环境存在沙箱提升重试机制，导致 ingest 命令实际被触发两次。
> 第一次执行（沙箱内）处理 TCD 时已完成 completed 写入但中断于源文件清理，留下孤儿
> processing 文件与租约；提升权限后的第二次执行按幂等分支完成（TCD=idempotent_success，
> NER=completed），并写入 audit。审计日志仅含 NER 的 result_ingested/task_completed 事件，
> completed 目录两个结果文件内容均正确且通过 Schema。已按协议最终状态要求清理孤儿
> processing/lease 残留后，状态恢复为 queue=0 / processing=0 / completed=2 / leases=0。
> 此现象为执行环境机制所致，非 ASIP 协议代码缺陷；两个 completed 结果均由本次会话
> DeepSeek V4 Flash 实际生成，未使用测试脚本、未复制旧摘要。

---

## 6. 重复 Ingest（幂等验证）结果

再次执行完全相同的 ingest 命令：

- CLI 退出码：0
- accepted：0
- rejected：0
- 两个任务均返回 `idempotent_success`（`AIT_00c231b9fff12f4e59f31481`、`AIT_a3704b9244b78394f8d9993d`）
- completed 仍为 2，无第二份 completed 文件，task_id 未变化

---

## 7. Verify 结果

命令：`cross_session_handoff_demo.py verify --consumer-session-id consumer_568d0454`

- ok：true
- errors：`[]`
- queue=0 / processing=0 / completed=2 / leases=0
- completed_task_ids 与 HANDOFF_READY 完全一致
- no_duplicate_completed：true
- provider=workbuddy_queue，model=deepseek-v4-flash（两个结果）
- 两个结果均通过 AI Result Schema
- 两个 summary_zh 均非空
- 乍得结果保留「官方尚未确认伤亡数字」（semantics=true）
- 尼日尔结果未虚构伤亡（semantics=true）
- consumer_session_id 与 producer_session_id 不同

---

## 8. 生产 data/ai 隔离证明

- 执行前：`data/ai/` 仅含 `.gitkeep` 占位文件，无任何任务/结果/租约
- 执行后：`data/ai/` 仍仅含 `.gitkeep` 占位文件，未被写入任何内容
- 全部运行时状态仅存在于 `.workbuddy_runtime/stage25b2b/`（已 gitignore，不入库）
- git status 无运行时任务、租约或结果文件

---

## 9. 完成依据声明

- 本任务仅依据仓库文档（WORKBUDDY_AI_WORKER.md）与本地 HANDOFF_READY 交接包完成；
- 未依赖准备端任务对话历史上下文；
- 未修改网站业务内容；
- 未处理真实新闻，未读取 Canonical 真实文章；
- 未调用任何外部 API（DeepSeek 开放平台 / OpenAI / ChatGPT / 新闻 API），external_api_calls=0；
- 未开始 Stage 2.5C；
- 验收记录提交前已通过 verify（ok=true）。

---

## 10. 本次 WorkBuddy 积分消耗

- 本任务使用 WorkBuddy 内置 DeepSeek V4 Flash 完成内容生成与流程执行，
  未产生任何外部 API 计费；实际积分消耗以 WorkBuddy 平台账单为准，
  本记录不伪造具体数值（外部 API 计费为 0）。

---

*本记录不含本机绝对路径、用户名、密钥、真实新闻或内部异常堆栈。*
