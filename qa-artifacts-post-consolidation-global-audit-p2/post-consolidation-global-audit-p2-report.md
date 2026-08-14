# Post-Consolidation Global Audit — Phase 2 验收报告

## 结论

**POST_CONSOLIDATION_GLOBAL_AUDIT_P2 = PASS**

95 个 P1 全部完成可信分类，Pack B 范围被合理压缩。**知识数据零改动。**

---

## 0. 基线确认

| 项 | 值 |
|---|---|
| source branch | `feature/asip-final-depth-consolidation-a` @ `7daf6a6` |
| local/remote HEAD | `7daf6a6`（一致），working tree clean |
| 建分支 | `feature/asip-post-consolidation-global-audit-p2` |
| 数据 SHA | pre/post 一致（见只读不变量） |

---

## 1. P1 Population（复用 Global Audit 同一逻辑）

**P1_TOTAL = 95**（与 Pack A 后基线一致）

| 维度 | 值 |
|---|---|
| P1_CLASSIFIED_COUNT | 95 |
| P1_UNCLASSIFIED_COUNT | 0 |
| tier 分布 | R1=65, R2=30（**无 R3**） |
| type 分布 | operates_in=40, led_by=12, fought_against=8, cooperates=6, member=4, affiliated=6, merged=4, 其他 |

**关键事实**：P1 里没有任何 R3 关系——Pack A 已将全部 R3 补厚到 R-A/R-B。剩余 95 个 P1 全是 R1/R2 的简单/操作性关系。

---

## 2. P1 四类分类结果

| 分类 | 数量 | 说明 |
|---|---|---|
| FINAL_MUST_FIX | **0** | 无「必须修」项 |
| HIGH_VALUE_DEPTH | **20** | R2 的 leadership/operational 关系，值得未来补厚 |
| ADEQUATE_FOR_ROLE | **50** | operates_in / member_of 等简单结构边，已符合设计职责 |
| DEFER_FUTURE | **25** | 边缘/历史关系，未来专题再扩 |

**BORDERLINE_REVIEW_COUNT = 6**：核心组织领导人关系（库法创立马西纳旅、伊亚德领导 JNIM、迪里耶领导青年党、巴卢库领导 ADF、优素福/法希耶领导 ISIS-Somalia）处于「补厚」与「够用」边界，需 ChatGPT 判断。

---

## 3. Relation-tier 一致性审计（只报告，不修改）

| 类别 | 数量 | 判断 |
|---|---|---|
| R3_BUT_SIMPLE_EDGE | 1 | rel-expd-fpl-niger-operates（R3+rich profile，Pack D 强制要求，合理） |
| R1_BUT_STRATEGIC | 11 | 简单 leadership/merger 事实（R1 足够，合理） |
| R2_BUT_STRATEGIC | 21 | leadership/operational（R2 足够，多数合理） |
| R3_AND_GENUINELY_STRATEGIC | 75 | 核心战略关系，已达标 |

---

## 4. Core Actor Readiness（18 个）

| 分类 | 数量 |
|---|---|
| READY | 17 |
| READY_MINOR_GAPS | 1（actor-africa-corps，grade B） |
| NOT_READY | 0 |

---

## 5. Core Relationship Readiness（20 个）

| 分类 | 数量 |
|---|---|
| READY | 9（R-A dossier） |
| READY_MINOR_GAPS | 11（R-B，有可补强的小缺口） |
| NOT_READY | 0 |

---

## 6. Theater Readiness（8 个战区）

| 战区 | 状态 |
|---|---|
| Sahel | READY_WITH_MINOR_GAPS（2 个 MINOR_GAPS 实体） |
| Lake Chad | READY |
| Somalia/Horn | READY |
| Mozambique | READY |
| DRC/Uganda | READY |
| Libya/North Africa | READY |
| Sudan | **NEEDS_FINAL_CONSOLIDATION**（actor-slm-aw grade C） |
| Coastal West Africa | READY |

---

## 7. Evidence Readiness（FINAL_MUST_FIX）

FINAL_MUST_FIX = 0，故：
- NEW_RESEARCH_REQUIRED_COUNT = 0
- EXISTING_EVIDENCE_SUFFICIENT_COUNT = 0

---

## 8. Pack B Scope Simulation

| 项 | 值 |
|---|---|
| FINAL_MUST_FIX_COUNT | 0 |
| HIGH_VALUE_DEPTH_COUNT | 20 |
| ADEQUATE_FOR_ROLE_COUNT | 50 |
| DEFER_FUTURE_COUNT | 25 |
| **PACK_B_RECOMMENDATION** | **SKIP** |

**推荐 Pack B target IDs**：空（FINAL_MUST_FIX = 0）。若 ChatGPT 决定做可选的「微补厚」，候选为 6 个 BORDERLINE 核心领导关系 + 20 个 HIGH_VALUE_DEPTH 关系。

---

## 9. P2 Escalation Check

P2_TOTAL = 34，P2_ESCALATION_CANDIDATE = 1：
- **actor-africom**（core actor，grade A 但 evidence 偏低，值得 ChatGPT 确认是否需补 evidence）

其余 33 个 P2（11 grade-C 次要实体 + 22 低证据 A/B）维持 P2，无误分。

---

## 10. 只读不变量

**KNOWLEDGE_DATA_CHANGED = 0**：`data/intelligence/africa/**` 17 个文件 pre/post SHA-256 全部 byte-identical。

OUT_OF_SCOPE_CHANGED_FILES = 0（仅新增 Phase 2 审计脚本 + QA 工件）。

---

## 11. 最终门禁

| 门禁 | 值 |
|---|---|
| KNOWLEDGE_DATA_CHANGED | **0** |
| P1_CLASSIFIED / P1_UNCLASSIFIED | 95 / 0 |
| PPT_NAMES_UNRESOLVED / PPT_RESOLUTION_CONFLICT | 0 / 0 |
| QUALITY_BYPASS_SUSPECT_COUNT | 0 |
| BROKEN_RELATIONSHIP / EVIDENCE / ALIAS TARGETS | 0 / 0 / 0 |
| DUPLICATE_CANONICAL_ENTITIES | 0 |
| MOBILE_HORIZONTAL_OVERFLOW / UI_REGRESSION | 0 / 0 |
| FULL_REGRESSION | **PASS**（41 套件 / 7204 用例 / 0 失败 0 跳过） |
| BUILD | **PASS**（333 routes） |
| BROWSER_QA | **PASS**（16 页 desktop+mobile） |
| NETWORK_QA | **PASS**（8 focus） |
| production / gh-pages / preview / force push | NO / NO / NO / NO |

---

## 12. 停止点

Phase 2 完成、95 个 P1 全部可信分类、知识数据零改动。PASS 含义 =「P1 全部完成可信分类，Pack B 范围已合理压缩」，**不等于 ASIP 已 Final Closure**。

**已停止**，未启动 Pack B / Final Closure / 部署。

等待 ChatGPT 根据 Phase 2 结果决定：Pack B（SKIP 建议）/ Skip Pack B / Final Closure。
