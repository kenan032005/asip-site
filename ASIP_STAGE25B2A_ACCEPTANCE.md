# ASIP Stage 2.5B-2A 验收补正 — 脱敏验收记录

> 本文件仅记录**非敏感证据**：不含有本机绝对路径、用户名、密钥，也不含任何真实新闻。
> 所有任务均为虚构演练场景（`synthetic=true`），不进入生产 `data/ai`。

## 1. 执行信息

- 执行日期（UTC）：2026-07-30
- 执行日期（北京时间）：2026-07-31
- 阶段：ASIP Stage 2.5B-2A 验收补正（真实社会安全场景 + Hy3 手工交接证据）
- 使用模型：**WorkBuddy 内置 Hy3（免费）**
- 外部 API 调用数：`external_api_calls = 0`
- 是否使用生产 `data/ai`：否（全程隔离运行时根，已 gitignore）
- 是否读取 Canonical 真实文章：否
- 是否使用 DeepSeek / ChatGPT：否

## 2. 批次与任务标识

- `batch_id`：`BATCH_20260730T210452_41a0ec`
- 任务 1：`AIT_e91233fde9107726cb7ec175`（country_iso3=TCD, source_language=fr）
- 任务 2：`AIT_ac673ef92a59933a813e5e39`（country_iso3=NER, source_language=en）

## 3. 两段虚构 source_text（明确标注 FICTIF / SYNTHETIC）

**任务 1（TCD / fr）：**

```
[SCÉNARIO FICTIF]
Des tirs ont été signalés dans la soirée près d'un marché de la localité
fictive de Dar-Salam, au Tchad. Les forces de sécurité ont temporairement
bouclé le secteur. Les autorités n'ont pas encore confirmé s'il y a eu des
morts ou des blessés.
```

**任务 2（NER / en）：**

```
[SYNTHETIC SCENARIO]
Local authorities temporarily closed the main road near the fictional town
of Kori in Niger after an unidentified object was found beside the roadway.
Traffic was diverted while security personnel inspected the area. No
casualties were officially reported.
```

## 4. Hy3（当前会话内置）真实生成的两段中文摘要

**任务 1（TCD，安全事件）：**

> 乍得虚构地点 Dar-Salam 一处市场附近于晚间传出枪声，安全部队已临时封锁该区域。截至本简报，当局尚未确认是否有人员死亡或受伤。

**任务 2（NER，交通中断）：**

> 尼日尔虚构城镇 Kori 附近主干道因路旁发现不明物体被地方当局临时关闭，安保人员现场检查期间交通改道。官方未报告人员伤亡。

## 5. event_type 与 uncertainties

**任务 1：** `event_type = armed_incident`
- uncertainties：
  - 伤亡情况（死亡/受伤）尚未得到官方确认
  - 枪击具体原因与涉事方不明
  - 事件为虚构演练场景，不代表真实事件

**任务 2：** `event_type = transport_disruption`
- uncertainties：
  - 不明物体性质未确定
  - 官方未报告任何人员伤亡
  - 事件为虚构演练场景，不代表真实事件

## 6. 首次 ingest 结果（真实 CLI）

```
accepted=2, rejected=0, failed_tasks=0, batch_complete=true
accepted_task_ids=[AIT_e91233fde9107726cb7ec175, AIT_ac673ef92a59933a813e5e39]
CLI 退出码 = 0
```

## 7. 重复 ingest 结果（幂等）

```
accepted=0
outcome=[idempotent_success, idempotent_success]
CLI 退出码 = 0
completed 数量仍为 2（无重复、无丢失）
```

## 8. verify 完整结果（16 项硬性条件全部通过）

```
ok = true
checks:
  manifest_exists            = true
  task_count                 = 2
  expected_provider          = workbuddy_queue
  expected_model             = hy3
  queue                      = 0
  processing                 = 0
  completed                  = 2
  leases                     = 0
  completed_task_ids_match    = [AIT_ac673ef92a59933a813e5e39, AIT_e91233fde9107726cb7ec175]
  no_duplicate_completed      = true
  schema_<TCD>               = true
  country_<TCD>              = TCD
  synthetic_<TCD>            = true
  summary_zh_<TCD>           = true
  semantics_<TCD>            = true     (保留“伤亡未确认”)
  event_type_<TCD>           = armed_incident
  schema_<NER>               = true
  country_<NER>              = NER
  synthetic_<NER>            = true
  summary_zh_<NER>           = true
  semantics_<NER>            = true     (不虚构伤亡)
  event_type_<NER>           = transport_disruption
errors = []
CLI 退出码 = 0
```

## 9. 最终状态

- `queue = 0`
- `processing = 0`
- `completed = 2`
- `leases = 0`

## 10. cleanup

- 运行时目录已清理：`cleaned = true`

## 11. 生产 data/ai 未变化

- 执行前后 `data/ai/queue`、`processing`、`completed`、`failed` 计数均为 `0`。
- 合成任务（`synthetic=true`）从未进入生产 `data/ai`。

## 12. 自动测试 vs 当前会话 Hy3 手工交接证据（分离说明）

- **自动测试证据**（`scripts/tests/test_stage25b2a_manual_handoff.py`，18 项全绿）：
  证明 Schema、CLI 退出码、ingest、幂等、verify 逻辑，使用确定性模拟结果以保证流水线可重复。
- **当前会话 Hy3 手工交接证据**（本文档第 3–9 节）：
  证明当前 WorkBuddy 会话实际读取了第 3 节的 `source_text`，并由内置 Hy3（免费）生成第 4 节的中文摘要，
  再经真实 CLI ingest → 幂等重 ingest → verify 全绿。未使用任何测试脚本中的硬编码结果。

## 13. 合规边界确认

- 仅使用合成任务，不处理真实新闻 / 真实 API / 真实数据；
- 仅使用 WorkBuddy 内置 Hy3（免费），`provider=workbuddy_queue`、`model=hy3`；
- 禁用 DeepSeek / ChatGPT 等付费或外部模型；
- 用量 `input_tokens / output_tokens / estimated_cost_usd` 一律记 `0`，未伪造；
- 运行时目录位于 `.workbuddy_runtime/`（已 gitignore，绝不入库）；
- 未修改任何网站页面或业务数据；
- 未开始 Stage 2.5B-2B 或 2.5C。
