# ASIP-PPT-ENTITY-EXPANSION-C — Acceptance Report
## Historical Lineage & Precursor Networks

- **分支**: `feature/asip-ppt-entity-expansion-c`
- **基线**: `feature/asip-intelligence-uiux-v2 @ f663949`（UIUX_V2_FIX1 = PASS 验收点）
- **阶段**: 知识扩展（历史谱系与前驱网络）；未改 UI、未建薄国家页、未部署、未动 gh-pages
- **权威底稿**: `ASIP-PPT-ENTITY-EXPANSION-C-Authoritative-Content-Pack.md`（唯一事实来源，无联网研究）

---

## 1. 最终门禁（全部满足）

| 门禁 | 值 | 状态 |
|---|---|---|
| OUT_OF_SCOPE_CHANGED_FILES | **0** | ✅ |
| FACT_SEMANTIC_ERRORS | **0** | ✅ |
| DUPLICATE_CANONICAL_ENTITIES | **0** | ✅ |
| STANDARD_FINAL_ENTITY_COUNT | **0**（8 新 + 4 ENRICH 全部 encyclopedia_full） | ✅ |
| UIUX_V2_REGRESSION | **0** | ✅ |
| FAIL_TOTAL | **0**（全库 38 个测试套件全绿 = 6827 用例；含 Expansion C 专项 41 检查） | ✅ |
| BUILD | **PASS**（321 routes） | ✅ |
| BROWSER_QA | **PASS**（12 页面 × desktop/mobile = 24 截图 + 5 网络 focus，0 console / 0 req / 0 anchors / 0 overflow） | ✅ |
| NETWORK/LINK_QA | **PASS**（356 页 / 2070 链 / 0 死链） | ✅ |
| production / gh-pages / force push | 均无 | ✅ |

---

## 2. 第一阶段 dedup 裁定（pre-import-dedup-audit.json）

| 候选 | 裁定 | 关键依据 |
|---|---|---|
| EIJ | **NEW**（encyclopedia_full） | 仓库不存在；UN 叙述 + 国务院历史报告材料足 |
| GIA | **NEW** | 仓库不存在；UN GIA/AQIM 叙述 |
| **GSPC** | **HISTORICAL_PHASE / ALIAS_ONLY of AQIM** | 无独立节点；alias_index 已 `gspc->actor-aqim`；AQIM aliases/historical_names 已含 GSPC；本轮补 GIA→GSPC→AQIM 章节 + 时间线 + 关系叙述 → **PPT_ENTITY_COVERED = YES** |
| AIAI | **NEW** | UN AIAI + 专家组 S/2016/919、S/2017/924 |
| TCG | **NEW** | UN TCG + al-Maaroufi + State 2002 |
| GICM | **NEW** | UN GICM + LIFG + State 2002/2007 |
| Battar Brigade | **NEW** | UN 专家组 S/2015/891 + CTC |
| Maitatsine | **NEW** | 学术文献（Adesoji/Isichei/Hiskett/Lubeck）；无谱系边 |
| MUJAO | **NEW** | UN 综合参考 + NCTC 历史材料 |
| AQIM | **ENRICH_EXISTING** | 已 E3；补 GSPC 连续体/分裂史/萨赫勒埃米尔区/继任 |
| Ansar al-Dine | **ENRICH_EXISTING** | 已 E3；补 2016 再现/2017 JNIM/AQIM 关联 |
| Al-Murabitun | **ENRICH_EXISTING** | 已 E3；补 2013 合并/2015 faction-only |
| Macina/MLF | **ENRICH_EXISTING（轻）** | 已 E3；NCTC 四组事实 + 时间线节点 |

---

## 3. 内容规模（final-counts.json）

| 指标 | 前 | 后 |
|---|---|---|
| entities（非国家） | 94 | **102**（+8 全部 E3） |
| relationships | 181 | **192**（+11；10 个 R3 + 1 个 R1） |
| relation profiles | 181 | **192**（+11 新，全部带 profile；+3 既有升级 R2→R3） |
| relation timelines | 73 | **88**（+15：11 条新关系 + 4 条既有关系补 timeline） |
| sources | 221 | **246**（+25） |
| evidence | 358 | **380**（+22） |
| aliases | 393 | **443**（+50） |
| routes | 302 | **321** |

---

## 4. 五项强制事实语义（semantic-audit.json，全部通过）

- **A. EIJ→Al-Qaida 双日期**：保留 UN 1998 合并叙述 + 国务院 2001 年 6 月正式合并；关系档案与时间线明确「1998—2001 分阶段整合/正式化」，不强行归一。
- **B. AIAI→Al-Shabaab 限定**：以 `historically_associated_with` 建模，档案明确「重要意识形态/人事前身网络，公开来源不支持把青年党起源简化为单一直接组织传承」，保留 UN 归属性。
- **C. Maitatsine**：严禁创建与 Boko Haram 的 predecessor_of/split_from 边（无任何此类关系类型）；档案以「比较≠传承」表述无直接组织连续性；仅记录尼日利亚历史地理活动（operates_in）。
- **D. Al-Murabitun→ISIS-Sahel**：仅 2015 年**一个派别** defected（rel-is-mourabitoun-splinter 升级 R3，faction-only 限定）；贝尔穆赫塔尔派系保持基地组织结盟、2017 主体并入 JNIM；全文本无「整个组织转化」表述。
- **E. legal vs operational**：8 个历史实体 operational_status 以 `historical_*` 标注（freshness=historical），legal_status 章节单独保留（如 GIA/EIJ/TCG 的 UN 列名法律状态不因现实解体自动失效）。

其他语义纪律：GICM 马德里/卡萨布兰卡相关指认保留 UN/国务院归属性；MUJAO 合并语义用现有 ontology + profile 解释（未扩展 merged_into）；GSPC 无独立节点（规则 16.2）。

---

## 5. 核心关系（R3 dossier 全套字段 + timeline）

11 条新关系 + 3 条升级 R3 + katiba timeline 补充：

- GIA→GSPC/AQIM 谱系（split_from，4 时间线节点：1998 分裂/2001 UN 列名/2006 结盟/2007 更名）
- GSPC/AQIM→Al-Qaida 结盟（pledged_allegiance_to，2006-09-11/2007/2026）
- EIJ→Al-Qaida 分阶段整合（constituent_of，双日期时间线）
- AIAI↔Al-Shabaab 限定前身（historically_associated_with，4 节点）
- Battar→ISIS-Libya 前驱融合（constituent_of，Wilayat Barqa 融合）
- MUJAO→Al-Murabitun 合并谱系 / AQIM→MUJAO 分裂
- AQIM↔Ansar al-Dine 关联（2012—2017，NCTC 归属性）
- GICM↔Al-Qaida / TCG↔Al-Qaida 历史关联
- Maitatsine→Nigeria 历史活动（R1，无谱系）
- 升级 R3：rel-jnim-ansar-constituent、rel-jnim-mourabitoun-constituent、rel-is-mourabitoun-splinter
- 补时间线：rel-jnim-katiba-constituent（4 节点）

全部关系页经浏览器实测：party cards 2、timeline 阶段卡 3-4、正文 exact auto-links 32–86 个、disputed/历史徽章正确。

---

## 6. UI/UX V2 保持（uiux-v2-regression.json = 0）

- 8 个新历史实体页：auto TOC 20 项、key-facts 2-3 格、**「历史资料」徽章**（freshness=historical）、uncertainty 卡、disputed 徽章（如 SIM 相关）全部渲染。
- 关系页：party cards、timeline V2、relation body exact auto-links（32-86 个/页）正常。
- 网络 V2：AQIM（7 节点/6 边）、Al-Qaida（9/8）、JNIM（32/33）、Al-Murabitun（4/3）、ISIS-Libya（4/3）focus 全部渲染。
- desktop+mobile 0 溢出（修复了历史长 status 在 party card/rh-row 的换行，presentation-only CSS）。

---

## 7. PPT 覆盖（ppt-coverage-delta.json）

13/13 全覆盖；GSPC 以 HISTORICAL_PHASE/ALIAS_ONLY 计入 AQIM（PPT_ENTITY_COVERED = YES）。

---

## 8. QA 证据文件

`qa-artifacts-expansion-c/`：pre-import-dedup-audit / import-plan / entity-import-summary / historical-phase-decisions / relationship-import-summary / source-evidence-summary / semantic-audit / uiux-v2-regression / test-results / browser-qa-results / network-qa-results / ppt-coverage-delta / final-counts / 24 张截图 + acceptance report。

---

## 9. 结论

```
EXPANSION_C_LOCAL_CANDIDATE = PASS
```

已停止。未启动 Expansion D。

---
---

## 9. Acceptance Correction Audit（bookkeeping/regression only，追加）

本审计为只读核对，未修改任何知识数据 / 事实语义（HEAD 仍为 facff39）。

### 9.1 relation_profiles baseline 澄清

从 f663949 与 facff39 分别机械统计（git show 读取，非人工）：

| 指标 | f663949（baseline） | facff39（final） |
|---|---|---|
| BASELINE_RELATIONSHIPS / FINAL_RELATIONSHIPS | 181 | **192** |
| BASELINE_RELATION_PROFILES / FINAL_RELATION_PROFILES | **181** | **192** |
| BASELINE_RELATION_TIMELINES / FINAL_RELATION_TIMELINES | 73 | **88** |
| ORPHAN_RELATION_PROFILES | 0 | **0** |
| DUPLICATE_RELATION_PROFILES | 0 | **0** |
| RELATION_IDS_WITHOUT_PROFILES | 0 | **0** |

**结论**：baseline relation_profiles 真实值 = **181**（与 Expansion B acceptance 一致，也与 UI/UX V2 的 17 文件 hash 不变一致）。acceptance report 原写的「189 → 192」中的 **189 是报告笔误**，已修正为 **181 → 192**。数据本身无缺失、无重复、无孤儿：每一条新增关系（+11）均携带 profile，每一条既有关系均保持其 profile，未删除任何历史数据以凑数。

关系增量构成（已核对）：+11 新关系（10 个 R3 + 1 个 R1）全部带 profile；+3 既有关系升级 R2→R3（rel-is-mourabitoun-splinter、rel-jnim-ansar-constituent、rel-jnim-mourabitoun-constituent）；relation_timelines +15 = 11 条新关系 timeline + 4 条既有关系新增 timeline（含 rel-jnim-katiba-constituent）。

### 9.2 full regression test count 澄清

Expansion C 阶段使用的运行器 `_exp_c_runall.py` 只枚举了 **22 个** intelligence 测试文件，**遗漏了 14 个既有测试文件**（demo×3、git_delivery_manifest、i2b_audit、i3a_country_depth、i3a_source_coverage、i3b_×6、relation_ontology）以及 scripts/tests/ 下的 2 个 EXTRA 套件。因此原报告「22 tests」不是口径差异，而是**运行覆盖不足**。

本次 closure audit 改用全量入口（`scripts/qa/expansion_c_closure_audit.py`，枚举全部 test_*.py + 2 个 EXTRA）：

```
TEST_FILES_DISCOVERED = 38
TEST_CASES_DISCOVERED = 6827
TEST_CASES_RUN        = 6827
TEST_CASES_PASSED     = 6827
TEST_CASES_FAILED     = 0
TEST_CASES_SKIPPED    = 0
```

38 个套件名称（全部 PASS）：test_africa_data / test_africa_evidence_quality / test_africa_freshness / test_africa_metrics / test_africa_pages / test_demo_data / test_demo_pages / test_demo_v02 / test_depth_a_import / test_depth_b_import / test_depth_c_import / test_depth_d_import / test_depth_e_import / test_depth_f_import / test_depth_g_closure / test_expansion_b_gate / **test_expansion_c_gate** / test_git_delivery_manifest / test_i2b_audit / test_i3a_content_quality / test_i3a_country_depth / test_i3a_duplicate_text / test_i3a_entity_depth / test_i3a_preview / test_i3a_source_coverage / test_i3b_all_country_depth / test_i3b_current_status / test_i3b_evidence_upgrade / test_i3b_production_isolation / test_i3b_public_preview / test_i3b_relation_depth / test_i3b_release_candidate / test_i3b_zero_basic_entries / test_i3d1_import / test_i3d2_import / test_relation_ontology / test_no_local_paths / test_repository_integrity。

专项统计：**Expansion C 专项 41 检查**（test_expansion_c_gate.py，与全库回归分开统计）；既有历史套件（demo/i2b/i3b 等）均未删除、未过滤、未跳过——f663949→facff39 的 git diff 确认仅 12 个计数钉测试被修改 + test_expansion_c_gate 新增，**无任何测试文件被删除**。**TEST_CASES_FAILED = 0 未通过缩减测试覆盖获得**（本次运行的 38 个套件多于此前任何一轮）。

### 9.3 重新确认不变项

| 项 | 值 | 状态 |
|---|---|---|
| FACT_SEMANTIC_ERRORS | **0** | ✅（semantic-audit 重跑） |
| DUPLICATE_CANONICAL_ENTITIES | **0**（实体 ID / slug 均无重复） | ✅ |
| UIUX_V2_REGRESSION | **0** | ✅（semantic-audit 重跑） |
| OUT_OF_SCOPE_CHANGED_FILES | **0** | ✅（scope-audit 重跑，local-path-scan diff = ZERO） |
| BUILD | **PASS**（321 routes：102 实体 / 192 关系 / 7 区域 / 13 国家 / 246 来源 / 380 证据） | ✅ |

未重拍 24 张截图（知识数据未变，UI/UX V2 渲染已由既有 BROWSER_QA/LINK_QA 工件覆盖）。

### 9.4 更新文件

- `qa-artifacts-expansion-c/final-counts.json`：补 baseline（f663949）与 closure_audit 字段，relation_profiles baseline = **181**
- `qa-artifacts-expansion-c/test-results.json`：重写为全量 38 套件结果（TEST_CASES_FAILED = 0）
- `qa-artifacts-expansion-c/expansion-c-acceptance-report.md`：修正 §1 门禁表 FAIL_TOTAL 表述、§3 表 relation profiles（181→192）与 relation timelines（73→88）数字
- 新增审计工具 `scripts/qa/expansion_c_closure_audit.py`（全量回归入口，可复现）

```
EXPANSION_C_CLOSURE = PASS
```
