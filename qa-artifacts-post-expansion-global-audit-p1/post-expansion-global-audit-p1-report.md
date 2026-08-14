# Post-Expansion Global Audit — Phase 1 验收报告

## 结论

**POST_EXPANSION_GLOBAL_AUDIT_P1 = PASS**

含义：审计完整且可信（Audit complete and trustworthy），**不等于无 gap**。本轮为只读审计，未修改任何知识数据，未修复任何发现的 gap。

---

## 0. 基线确认

| 项 | 值 |
|---|---|
| source branch | `feature/asip-ppt-entity-expansion-e` |
| accepted HEAD | `34241bd` |
| local HEAD | `34241bd`（与远端一致） |
| source tree | clean（无未提交知识改动） |
| 审计分支 | `feature/asip-post-expansion-global-audit-p1`（从 34241bd 创建） |

Expansion E 基线（40 套件 / 7192 用例 / 0 失败 / 0 跳过）已确认。

---

## 1. 只读不变量（最重要 gate）

**KNOWLEDGE_DATA_CHANGED = 0**

`data/intelligence/africa/**` 17 个文件 pre/post SHA-256 全部 byte-identical（2,895,125 字节）。仅 `dist/` 与 QA 工件为派生产物，source-of-truth 知识数据零改动。

---

## 2. 各 Audit 目标结果

### Audit A — canonical / alias / identity 完整性

| 检查项 | 结果 |
|---|---|
| DUPLICATE_CANONICAL_IDS | **0** |
| DUPLICATE_SLUGS | **0** |
| DUPLICATE_NAME_ZH / NAME_EN | 0 / 0 |
| ACRONYM_COLLISIONS | 0 |
| ALIAS_COLLISIONS（别名指向多实体） | 0 |
| BROKEN_ALIAS_TARGETS（别名指向缺失实体） | **0** |
| ALIAS_SELF_LOOP | 0 |
| HISTORICAL_NAME_COLLISIONS | 0 |
| UNREACHABLE_ENTITIES（无别名入口） | 0 |

9 个历史身份连续体（GSPC↔AQIM、ABM↔ISIS-Sinai、ADF↔ISCAP、ISIS-Sahel↔ISGS、ISIS-Moz↔ASWJ、LAAF↔LNA、RDF↔RSF、Wagner↔Africa Corps、AMISOM↔ATMIS↔AUSSOM）全部符合已验收 modeling rules，无身份键缺失。

### Audit B — 实体 Wikipedia 级深度（108 个）

| grade | 数量 | 说明 |
|---|---|---|
| A (STRONG_WIKIPEDIA_LEVEL) | **70** | |
| B (GENERALLY_COMPLETE_MINOR_GAPS) | **15** | |
| C (NEEDS_DEPTH_CONSOLIDATION) | **11** | 主要 E1/E2 实体 |
| D (MATERIAL_GAP) | **12** | 见下方关键发现 |

关键发现：**12 个实体 grade D**（body 341–792 字、6–12 sections），多为 Expansion A 之前的早期实体。其中 **`actor-niger-armed-forces` 标着 `E3_FULL_ENCYCLOPEDIA` 但实际仅 792 字 / 11 sections**，是 maturity 标签与内容不匹配的典型（这正是本轮 Audit B 要抓的"早期 E3 太薄"问题）。

### Audit C — Current Posture / Freshness

| 分类 | 数量 |
|---|---|
| CURRENT_OK | 92 |
| HISTORICAL_OK | 16 |
| AGING / STALE / TIME_SENSITIVE_REVIEW_REQUIRED | 0 |

全部 active/current 实体的 `last_verified_at` 均为 2026 年（数据于 2026-08 生成），无停留在旧年份的现役实体。

### Audit D — 关系深度（205 条）

| grade | 数量 | 说明 |
|---|---|---|
| R-A (STRONG_DOSSIER) | **48** | |
| R-B (ACCEPTABLE_MINOR_GAPS) | **54** | |
| R-C (NEEDS_RELATION_DEPTH) | **54** | |
| R-D (EDGE_ONLY_OR_MATERIAL_GAP) | **49** | |

关键发现：**4 个 R3 关系实质偏薄**（P0）：
- `rel-jnim-benin-forces-fought`
- `rel-d1-dan-na-jnim-conflict`
- `rel-d2-jafar-jnim`
- `rel-d2-dozos-macina-jnim-conflict`

这些标着 R3 但正文/阶段/证据不足，属于"edge + 少量正文"而非真正的 R3 dossier。

### Audit E — 测试豁免审计

- depth_g downshift exemption：4 个（`_EXP_A_REL_DOWNSHIFT_EXEMPT`，LEGITIMATE_HISTORICAL_EXCEPTION）
- skip/xfail 标记：11 个（均在 `test_stage3b_final_repair.py` 的"数据缺失/fetch 失败"分支，属测试基础设施，非知识质量豁免）
- **QUALITY_BYPASS_SUSPECT_COUNT = 0**（不存在"为让 R3 PASS 跳过低质量 profile"或"为让新实体过 E3 gate 放宽标准"的 bypass）

### Audit F — Sources / Evidence 完整性

| 检查项 | 结果 |
|---|---|
| broken source_id refs | 0 |
| broken evidence source refs | 0 |
| orphan evidence | **1**（`ev-i3a-040`，乍得湖盆地冲突死亡数，country/region/entity/relation 均未关联） |
| unused sources | 51 |
| duplicate URLs | 0 |
| LOW_EVIDENCE_ENTITY | 27 |
| SINGLE_SOURCE_DEPENDENCY | 15 |
| LOW_EVIDENCE_R3_RELATION | 0 |

### Audit G — PPT 最终覆盖

| 项 | 值 |
|---|---|
| PPT_NAMES_TOTAL | **62**（A:14 + B:11 + C:13 + D:9 + E:17，去重后） |
| PPT_NAMES_RESOLVED | **62** |
| PPT_NAMES_UNRESOLVED | **0** |
| PPT_RESOLUTION_CONFLICT_COUNT | **0**（无同名不同 resolution 冲突） |

### Audit H — Country / Region

- 13 countries / 7 regions，region membership、country_ids 引用全部完整，无断裂。无 thin phantom country node。

### Audit I — Graph / Network 结构

| 检查项 | 结果 |
|---|---|
| orphan nodes | **4**（`actor-slm-aw`、`actor-cameroon-bir`、`actor-ecowas-standby-force`、`actor-minusma`，均无关系边） |
| orphan edges | **0** |
| self loops | 0 |
| duplicate edges | 0 |
| missing relation profiles | 0 |
| graph index 缺失实体 | 0 |

Network 13 focus 全部正常渲染（见下方 Network QA）。

### Audit J — UI / Route 回归

- BUILD = PASS（340 routes）
- 浏览器渲染完整性 = PASS（36 页 desktop+mobile，0 console error、0 exception、0 failed request）
- **水平溢出发现（6 个移动端实体页）**：mnjtf(31px)、rdf(6px)、africa_corps(6px)、lna(35px)、minusma(165px)、jnim(100px)。根因：`intel-bullets` / `intel-source-notes` 里长英文名/长 URL 未换行。**本轮不修复**（只读约束），记录为 P2 UI gap。

### Audit K — 全局厚度分布

- 实体：108（organization 84 / person 24），E3=80 / E2=23 / E1=5
- 关系：205，R3=75 / R2=57 / R1=73
- 来源：291（权威 70 + government 35；Reuters 40 / ACLED 31 / NCTC 14 为前三 publisher）
- 证据：405（entity 反向关联 354 条有 entity 目标）

### Audit L — 最后补厚候选清单

| 优先级 | 数量 | 主要构成 |
|---|---|---|
| P0 | **4** | 4 个薄 R3 关系 |
| P1 | **115** | 12 个 grade D 实体 + 49 个 R-D + 54 个 R-C 关系 |
| P2 | **32** | 11 个 grade C 实体 + 21 个低证据 A/B 实体 |

---

## 3. 最终门禁

| 门禁 | 值 |
|---|---|
| KNOWLEDGE_DATA_CHANGED | **0** |
| OUT_OF_SCOPE_CHANGED_FILES | **0** |
| DUPLICATE_CANONICAL_ENTITIES | **0** |
| BROKEN_ALIAS_TARGETS | **0** |
| ORPHAN_RELATIONSHIPS | **0** |
| ORPHAN_EVIDENCE | **1**（ev-i3a-040，已记录） |
| PPT_NAMES_UNRESOLVED | **0** |
| QUALITY_BYPASS_SUSPECT_COUNT | **0** |
| ENTITY GRADE A/B/C/D | 70 / 15 / 11 / 12 |
| RELATION GRADE A/B/C/D | 48 / 54 / 54 / 49 |
| P0/P1/P2 CONSOLIDATION | 4 / 115 / 32 |
| BUILD | **PASS**（340 routes） |
| FULL_REGRESSION | **PASS**（40 套件 / 7192 用例 / FAILED=0 SKIPPED=0） |
| BROWSER_QA | **PASS**（渲染完整性；6 个移动端溢出记录为 finding） |
| NETWORK_QA | **PASS**（13 focus） |
| production changed | **NO** |
| gh-pages changed | **NO** |
| preview changed | **NO** |
| force push | **NO** |

---

## 4. 交付

- **分支**：`feature/asip-post-expansion-global-audit-p1`（从 34241bd 创建，normal push）
- **只读审计脚本**：`scripts/qa/post_expansion_global_audit_p1.py`、`post_audit_p1_browser_qa.js`、`post_audit_p1_regression.py`
- **QA 工件**：`qa-artifacts-post-expansion-global-audit-p1/`（21 项）
- **禁止事项**：未修改知识数据、未改 UI、未部署 preview/gh-pages、未切 production、未启动 Consolidation/Final Closure

---

## 5. 停止点

审计完成、数据未改、结果可信。**不自动修复 P0/P1/P2、不补厚、不启动 Consolidation、不部署线上**。等待根据审计结果设计最后的内容补厚包。
