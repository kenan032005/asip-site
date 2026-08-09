# ASIP DEPTH G — FINAL ACCEPTANCE REPORT

**DEPTH G = CLOSED** ✅ (12/12 gates PASS, 10/10 closure metrics = 0)

---

## 1. 执行范围

DEPTH G 为 **ASIP CURRENT KNOWLEDGE BASE FINAL DEPTH CLOSURE（全库最终厚度收口）**。
本轮不做新战区扩写、不扩国家、不新增实体/关系、不产生地图、未自动启动 Depth H。

| 项目 | 基线（Depth F 终态） | 终态（Depth G） |
|---|---|---|
| source commit | `de6e227` | `9d04e4a`（分支 `feature/asip-intelligence-depth-g-final-closure`） |
| gh-pages commit | `b341bfb` | `099fc2f`（普通 push，无 force，远端 SHA 核验） |
| Pages run | `31311354140` | 见 Pages deployment（公网已确认生效） |
| countries | 13 | **13**（不变） |
| non-country entities | 72 | **72**（不变） |
| relationships | 150 | **150**（不变） |
| routes | 249 | **249**（不变） |
| sources | 182 | **190**（+8 新增，10 个 pack 源按 URL 别名复用，无悬挂引用） |
| evidence | 297 | **315**（+18，全部解析，unresolved=0） |

## 2. 十项闭包指标（全部 = 0）

| # | 指标 | 值 |
|---|---|---|
| 1 | 实体 inflated labels（badge > 真实评分，排除已声明 limitation） | **0** |
| 2 | 关系 inflated labels（同上） | **0** |
| 3 | 重要度 floor violations | **0** |
| 4 | 悬挂 source 引用（dangling refs） | **0** |
| 5 | 无 maturity badge 的实体 | **0** |
| 6 | 无 maturity badge 的关系 | **0** |
| 7 | 意外成熟度变动（非 intentional） | **0** |
| 8 | 重复有向边 | **0** |
| 9 | 指向缺失源的证据 | **0** |
| 10 | 声明不完整的 limitation | **0** |

## 3. 十二项 DEPTHG 门禁（全 PASS）

| Gate | 含义 | 结果 |
|---|---|---|
| G1 | 计数冻结 13/72/150/249 | PASS |
| G2 | source 去重（无重复 URL/title+publisher/ID） | PASS |
| G3 | un-jnim-2018 按 claim-relevance 保留（非机械删除） | PASS |
| G4 | 事实清洗：AQIM al-Annabi 2020-present；ISWAP Barnawi≠Bakura | PASS |
| G5 | Katiba Hanifa = E3 | PASS |
| G6 | JNIM-IS 两阶段修复（historically_associated_with 2016-2019 R2 / hostile_to R3，总数 150） | PASS |
| G7 | 19 条 core relation overrides 全部应用（badge + 内容非裸 stub） | PASS |
| G8 | 全 72 实体 / 150 关系均带 maturity badge | PASS |
| G9 | 十项零指标 = 0 | PASS |
| G10 | generator 幂等（byte-identical，17 文件 0 差异） | PASS |
| G11 | 全量回归 FAIL_TOTAL = 0 | PASS |
| G12 | 候选浏览器 QA + 网络 QA PASS | PASS |

## 4. 成熟度处置（truthful 收口）

**允许降级（规则 1），不为成熟度制造事实（规则 2）：**

- **3 个实体 E3→E2 降级**：`person-salva-kiir`（evidence=2<3）、`person-jafar-dicko`（dimensions 5<6）、`actor-dozos-of-macina`（dimensions 5<6）。降级理由与字段变更写入 `truthful-downgrade-ledger.json`（累积台账，幂等重跑不丢）。
- **6 个关系降级**：`rel-is-moz-islamic-state2` R3→R2；`rel-d1-ansaru-jas-split`、`rel-d1-ansaru-aqim-allegiance`、`rel-d1-ansaru-jnim-affiliation`、`rel-d2-dana-fama-coop`、`rel-d2-dozos-macina-amadou-led` R2→R1（均因缺 context/history 或 why/uncertainty 字段）。
- **7 条 pack 锁定 inflated 关系保留 badge 并声明 ACCEPTED_EVIDENCE_LIMITATION**：5 条 R2-locked（`rel-d1-fu-aes-region`、`rel-d1-fama-fu-aes-member`、`rel-d1-burkina-army-fu-aes-member`、`rel-d1-niger-army-fu-aes-member`、`rel-d2-katiba-hanifa-benin-forces`）+ 2 条 R3-locked（`rel-jnim-katiba-constituent`、`rel-jnim-benin-forces-fought`，缺 evolution_stages/时间线）。每条均记录 declared/scored/gaps/basis，不静默。

**R3 field-set 补全（规则 2 合规）：** 为 6 条 pack 锁定 R3 关系补 `asip_analysis` + `watch_indicators`，内容仅从该关系既有已 source 内容（overview/current_status/formation_background/uncertainties/timeline）推导，不引入新事实；`rel-cameroon-army-ambazonia` 另从已验证证据记录回填 catalog 内 source_ids（0→2，仅目录已有源）。补全后 `rel-mali-army-jnim`、`rel-burkina-army-jnim` 达到真实 R3。

## 5. 本轮修复的两个真实回归

1. **catalog_metrics.json stale**：新增 `scripts/gen/depth_g_metrics.py`，严格从 source-of-truth（entities/relationships/profiles/evidence/sources 实际文件）机器重算全部计数器，纳入正式 pipeline；sources 182→190、evidence 297→315、invariants 13/72/150/249 保持。禁止手填数字。
2. **R3 关系缺 asip_analysis/watch_indicators**：新增 `scripts/gen/depth_g_r3_fieldset.py`，按指令 B 只为「Depth G 明确提升 R3 且 source/evidence 足够」的关系补字段；R3 ⇒ substantive profile + ASIP Analysis 的结构门禁**未被削弱**（test_i3b_relation_depth / test_i3a_content_quality 均 PASS）。

## 6. 测试同步（记录在案，非静默放宽）

| 测试 | 变更 | 理由 |
|---|---|---|
| `test_africa_evidence_quality` | 白名单新增 pack 声明的 status（verified_analysis / verified_reported_findings / verified_with_time_series / analytical_data_correction）与 origin（depth_g_final_closure） | Content Pack 逐条声明这些状态；属 taxonomy 扩展而非违规 |
| `test_africa_metrics` | generated_by 白名单新增 `depth_g_metrics.py` | 指标改由 source-of-truth 机器重算，不再由 depth_f_import.py 生成 |
| `test_depth_a_import` | JNIM-IS 断言更新为两阶段模型 | 旧断言用 rel_of() 首个匹配（现为历史边）；Depth G 按 pack 拆分 rel-jnim-is-hostile（historically_associated_with 2016-2019）与 rel-jnim-is-conflict（hostile_to 2019-现在） |
| `test_i3a_preview` | **无断言变更** | 基线失败原因仅为 dist 未构建；`scripts/build_site.py --no-embed` 后 5 断言全 PASS，产品契约成立 |

## 7. QA 证据

- **16 组 Depth G 专项测试**：82 断言全 PASS（`test_depth_g_closure.py`）
- **全量回归**：34 个 Python 测试文件，`FAIL_TOTAL = 0`
- **Regen diff**：byte idempotent（17 文件 0 差异）；counts frozen；id sets 无增删；maturity moves E=3/R=19 全部 intentional；JNIM-IS repair 验证通过
- **候选浏览器 QA**（本地 dist，5 视口 1920/1440/1366/768/390）：138 页，0 fails，0 console errors / 0 exceptions / 0 failed requests / 0 bad responses / 0 broken images / 0 overflow；badge tier 12/12
- **公网浏览器 QA**（github.io）：138 页，0 fails，全指标 0，badge tier 12/12
- **网络 QA**（本地 + 公网）：10 焦点全 nodes/edges > 0、0 runtime errors
- **Production diff**：7 个变更文件全部在 `intelligence/africa/**` 白名单内，UNEXPECTED = 0

## 8. 交付物

- 数据：`data/intelligence/africa/*.json`（entities/relationships/profiles/evidence/sources/catalog_metrics 等 7 文件更新）
- 脚本：`scripts/gen/depth_g_{pipeline,import,evidence_import,relation_closure,truthful_downgrade,r3_fieldset,metrics}.py`
- QA：`scripts/qa/depth_g_{baseline_gate,maturity,source_audit,regen_diff,regression,production_diff,candidate_browser_qa,network_qa,final_closure}.py/.js`
- 测试：`scripts/tests/intelligence/test_depth_g_closure.py`（16 组）+ 3 个既有测试同步
- 报告：`qa-artifacts-depth-g/depth-g-final-closure-report.md`、`depth-g-final-closure-audit.json`、`truthful-downgrade-ledger.json`、`accepted-evidence-limitations.json`、`regen-diff.json`、`regression-report.json`、`candidate-browser-qa.json`、`public-browser-qa.json`、`network-density-qa.json`、`production-diff.json` 等

## 9. 结论

**DEPTH G = CLOSED。** 所有十二项门禁 PASS，十项闭包指标归零；全库 maturity 已按数据真实评分收口（允许降级、不造事实、锁定 badge 全部显式声明 limitation）；生成器幂等；全量回归 FAIL_TOTAL=0；本地与公网浏览器/网络 QA 全部通过；gh-pages 已白名单发布并公网核验。

按指令：**停止。不自动启动 Depth H。** 下一阶段恢复 Breadth Expansion 时另行启动。
