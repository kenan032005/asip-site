# ASIP Stage 8B — Real AI Review Pack（Human Review）

> 本文档为**人工验收包**（§二十二-§二十四）：自动 Gate 只负责 schema / 数字 / 来源 /
> 归因 / 重复 / metrics；可读性、研判质量、管理价值由 **ChatGPT + 用户** 人工验收。
> 不得调用第二个 AI 评价第一个 AI。

---

## 0. 当前状态（本包执行时）

**qualification_version = stage8b-v1**

| Provider | credential_available | cases_total | cases_succeeded | role |
| --- | --- | --- | --- | --- |
| glm47_flash | **false** | 20 | 0 | **provider_unresolved** |
| deepseek | **false** | 20 | 0 | **provider_unresolved** |

- 本地 / GitHub Actions 均未注入 `ASIP_GLM_API_KEY` / `ASIP_DEEPSEEK_API_KEY`
  （GitHub Secrets 未配置或 Actions 未运行）。
- 按 §五 执行策略：GLM 无法开展真实 qualification → DeepSeek 无 credential →
  **Stage8B = BLOCKED_PROVIDER_SELECTION（PROVIDER_UNRESOLVED）**，暂停，不进 Stage8C。
- 未调用任何真实 API（20×2 case 全部如实记录 `credential_unavailable`，零伪造调用）。
- 真实 Africa Daily / TCD Weekly / SSD Weekly / Brief 草稿**未生成**（无合格 provider）。

**解锁方式（二选一）**：
1. 在 GitHub Repository Secrets 配置 `ASIP_GLM_API_KEY`（或 `ASIP_DEEPSEEK_API_KEY`），
   在 GitHub Actions 以 `ASIP_MODE=development` 运行 Stage8B qualification（workflow_dispatch）；
2. 或在本地 shell 临时注入 `ASIP_GLM_API_KEY=...` 后重跑
   `python scripts/ai/qualification/stage8b.py --provider glm47_flash`。

credential 注入后，本 review 文件应随之填充真实草稿供人工验收。

---

## 1. 验收清单（credential 注入后逐项填写）

### 1.1 Africa Daily ×1（真实模型生成，§二十一）

**记录**：provider / returned_model / prompt_version / input_hash / generated_at / quality_status

| 项 | 值 |
| --- | --- |
| report_id |  |
| provider |  |
| returned_model |  |
| prompt_version | africa-daily-v1.0.0 |
| input_hash |  |
| generated_at |  |
| quality_status | （最高 passed_quality_gate，不得 approved_for_publication） |

### 1.2 Daily 逐条人工审核表（§二十二）

| # | INPUT FACTS（源事实） | AI FACT SUMMARY | AI ASSESSMENT | AI OUTLOOK | VERIFICATION | UNCERTAINTIES | SOURCE REFS | QUALITY GATE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |  |
| … |  |  |  |  |  |  |  |  |

审核要点（§二十四）：事实是否只来自 input；研判是否保守有据；展望是否无凭据概率；
归因是否保留（据称/单一来源/说法不一）；来源是否全部可追溯。

### 1.3 TCD Weekly ×1 / SSD Weekly ×1（§二十三）

**附件**：Executive Assessment / Major Events / Security Trend / Disease·Public Health /
Week-over-week / Watch Items + 对应 input metrics（trend_metrics 必须与 input 一致，
不得 AI 自行统计新闻数量、不得编造趋势、unknown 不得写 0）。

| 项 | TCD | SSD |
| --- | --- | --- |
| Executive Assessment |  |  |
| Major Events |  |  |
| Security Trend |  |  |
| Disease / Public Health |  |  |
| Week-over-week |  |  |
| Watch Items |  |  |
| input metrics 回显 |  |  |

### 1.4 Major Event Brief（qualification_sample 标注，§十二/§二十）

无真实 brief candidate → 使用 Golden structured input，标注 **qualification_sample**。
检查：事实 / 来源 / 不确定性 / immediate implications / watch items；**不得扩写**
战术、武器能力、攻击方法、组织行动建议。

---

## 2. 自动 Gate 结果（credential 注入后回填）

- strict_json_pass：/20（阈值 ≥19）
- schema_pass：/20（阈值 ≥19）
- 核心错误：major_fabrication / country_error / magnitude_error / attribution_loss /
  disease_identity_error / disease_numeric_gate_failure / unsupported_source_reference
- Report Quality Gate：/8 report cases（阈值 ≥7，且无核心事实错误）
- invalid_response_shape（post-retry）：（≥2 → 不得为唯一 Primary）
- 429 / timeout / 5xx 次数

## 3. 角色结论

- [ ] PRIMARY_PRODUCTION_CANDIDATE
- [ ] SECONDARY_PROVIDER
- [ ] NOT_QUALIFIED
- [ ] PROVIDER_UNRESOLVED（当前）

## 4. 人工签字（用户 + ChatGPT）

| 角色 | 结论 | 备注 |
| --- | --- | --- |
| 自动 Gate |  |  |
| ChatGPT 人工研判验收 |  |  |
| 用户 管理价值验收 |  |  |
