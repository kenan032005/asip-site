# ASIP Stage 4 第二执行包 — WorkBuddy 真实 AI 质量试跑 · 审阅材料

**试跑名称**：WorkBuddy 真实 AI 质量试跑（原「Hy3 质量试跑」更名）
**execution_route**：`workbuddy_queue` ｜ **actual_model**：`deepseek-v4-flash` ｜ **direct_website_api_call**：`false`
**分支**：`stage4-hy3-trial` @ A 包 `ad9c69a` + C 包 `527255b` + 本包
**生成时间**：2026-08-02（北京时间）

---

## 一、样本（§三）

| 指标 | 值 |
|---|---|
| 样本总数 | 20（TCD=10 / NER=10） |
| 选取规则 | 官方 `eligibility_status()` 判定 eligible（未隔离/文章页/full·partial_body/词数≥30/ISO3 合法），按 canonical 文件序每国取前 10；**样本内容未修改** |
| 前轮样本说明 | 前轮 §三 仅完成选择逻辑、manifest 未落盘，本轮按同一规则确定性重生成 |
| manifest | `data/ai/sample_manifest.json` |

## 二、执行链路（§四/§五）

| 环节 | 说明 | 结果 |
|---|---|---|
| produce | C 包 `Hy3Stage4Provider`（`expected_model=deepseek-v4-flash`, `max_retries=1`, mode=produce）入队 20 条 + 写 Prompt 文件/索引/交接说明 | 20/20 入队 |
| 消费者写回 | 消费者会话（WorkBuddy 内置模型 = `deepseek-v4-flash`）逐条基于真实正文生成 10 字段增强分析，写回 `data/ai/completed/<task_id>.json`（provider=`workbuddy_queue`, model=`deepseek-v4-flash`, usage 全 0, strict JSON） | 20/20 写回，契约 0 错误 |
| collect | `EnrichmentProcessor` + 桥接 Provider（collect）装配 `enrichment_results.json` | **succeeded=20 / failed_terminal=0 / invalid_model_output=0 / cache_miss=20** |
| 重试 | 每条 `max_retries=1`（用户规则），实际重试次数 | 0（全部一次成功） |

## 三、自动质量检查（§六）

| 检查 | 维度 | pass/total | 说明 |
|---|---|---|---|
| c1_country_top_level | 一致性 | 20/20 | 顶层 `country_iso3` 与 canonical 一致 |
| c2_location_country | 一致性 | 20/20 | `location.country_iso3` 与 canonical 一致 |
| c3_body_country_signal | 一致性（观察） | 17/20 | 3 条信号，见 §五 发现 |
| n1_evidence_numbers_traceable | 数字 | 20/20 | key_facts 证据摘录数字可在正文追溯（法文千位分隔已规范化） |
| n2_summary_numbers_soft | 数字（软观察） | 2/20 | 18 条摘要数字按中文单位/日期改写（如 239 十亿→2390亿、8月1日→1er août），可追溯但非原样 |
| e1_location_entities_found | 实体 | 20/20 | location admin1/city/site 非空值均可在正文找到 |
| u1_uncertainty_preserved | 不确定性 | 20/20 | 正文含强不确定性标记时 uncertainties 均已保留 |
| u2_uncertainty_struct | 不确定性 | 20/20 | uncertainties 数组结构合法 |
| **硬失败** | — | **0/20** | 模型输出质量硬检查全部通过 |

## 四、统计（§八）

- `data/ai/trial_summary.json`：20 样本、succeeded=20、retry(max=1, used=0)、`model_identity.recorded_truthfully=true`、`hy3_placeholder_used=false`。
- `data/ai/token_usage.json`：经 WorkBuddy 队列由消费者内置模型执行，**无外部 API 计量**，usage 如实为 0/0/0。
- `data/ai/review_matrix.json`：逐条矩阵（含 20 行 checks 明细）。

## 五、发现与观察

1. **事件 9（`EVT_2520e85f1185795d`，TCD 标注）正文主体为利比亚**（苏尔特/班加西，利比亚军事行动室）。模型按契约输出 `country_iso3=TCD`，并在 `uncertainties` 如实记录「正文主体涉及利比亚，与 Canonical 标注国 TCD 不一致」；c3 亦给出 `LBY` 信号。**结论：Canonical 数据归因问题（乍得媒体 Alwihda 报道利比亚事务被归入 TCD），非模型输出错误，建议后续在采集层复核归因。**
2. **c3 信号 `FRA` ×2 为启发式噪声**：事件 8 正文含组织名「Expertise France」，事件 20 正文主体为「对法国的指控」（袭击对象在尼日尔），均非事件发生地，不计入模型输出失败。
3. **n2 软观察 18/20**：摘要数字经中文单位/日期改写（`239 milliards`→2390亿、`1er août`→8月1日），属正常本地化，非事实篡改。
4. **C 包小瑕疵（仅记录，不修改）**：`hy3_stage4_provider.py::write_handoff` 的任务清单行打印 `event=None country=None`（索引条目未含 event_id/country 键，不影响功能）；C 包 CLI `_load_canonical_eligible` 读取不存在的 `data/quarantine/quarantine.json`（实际在 `data/canonical/`），本轮以 manifest 驱动入队绕开，未改 C 包代码。

## 六、合规边界

- ✅ 未修改 Prompt / Schema / 样本；未重做 A 包、C 包（直接复用 `ad9c69a` / `527255b`）。
- ✅ `ai_result.model` 如实记录 `deepseek-v4-flash`，全仓无 `hy3` 模型标识伪装。
- ✅ 未人工修改模型输出；strict JSON 开启；每条重试上限 1 次。
- ✅ Canonical / Public 未修改；未合并 main、未部署、未进入下一执行包。
- ✅ 未启用网站直接 API 调用（`direct_website_api_call=false`）。
