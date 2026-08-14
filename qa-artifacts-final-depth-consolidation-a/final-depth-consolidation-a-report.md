# Final Depth Consolidation Pack A — 验收报告

## 结论

**FINAL_DEPTH_CONSOLIDATION_PACK_A = PASS**

只处理 Global Audit P1 的 severity floor（4 个 P0 关系 + 12 个 grade-D 实体 + 1 个 orphan evidence + 4 个 isolated node + 6 个 mobile overflow），未处理 115 个 P1 / 32 个 P2。

---

## 0. 基线确认

| 项 | 值 |
|---|---|
| source branch | `feature/asip-post-expansion-global-audit-p1` @ `406f858` |
| local/remote HEAD | `406f858`（一致） |
| working tree | clean |
| data SHA | 与 Global Audit post-audit manifest 一致 |
| 建分支 | `feature/asip-final-depth-consolidation-a`（从 406f858） |

---

## 1. Grade-D 实体 Triage 结果

### De-formalize 3 个 standalone person

| person | resolution | leadership 保留位置 |
|---|---|---|
| person-sidi-ongoiba | DEFORMALIZE_STANDALONE_PERSON | actor-dana-atem（Sidi Ongoiba 是 Dana Atem 领导者） |
| person-amadou-nionson-diarra | DEFORMALIZE_STANDALONE_PERSON | actor-dozos-of-macina（ACLED 认定的核心领导人） |
| person-abou-ghosmane | DEFORMALIZE_STANDALONE_PERSON | actor-jnim（UN S/2026/44 记录的尼日尔西北部行动领导人） |

**ABOU_GHOSMANE_REVIEW_REQUIRED = False**：repository 仅有 1 个 source（UN S/2026/44），不满足 ≥2 strong independent sources 阈值 → 执行 de-formalize。

### Retain + Enrich 9 个实体到 encyclopedia_full

全部达到 ≥1800 chars / ≥8 sections（实际 1802–1935 chars / 21–30 sections）：

| 实体 | chars | 关键语义 |
|---|---|---|
| actor-katiba-serma | 1892 | JNIM-linked operational katiba with local autonomy（非确定内部结构） |
| person-ibrahim-malam-dicko | 1818 | deceased_2017，Ansaroul Islam 创始人 |
| person-ousmane-dicko | 1807 | 布基纳法索 JNIM 副指挥官（非整个 JNIM 埃米尔） |
| person-youssouf-toloba | 1831 | Dan Na Ambassagou 创始人/军事领袖 |
| person-sadou-samahouna | 1802 | time_sensitive / status_uncertain（未写 definitive deceased） |
| actor-hcua | 1840 | historical / merged_into_FLA 2024-11-30（未归类 jihadist） |
| actor-dana-atem | 1816 | 保留 formation-date nuance（2018 ACLED vs 2020 公开显著） |
| actor-dozos-of-macina | 1805 | 与 Dan Na Ambassagou / Dana Atem 明确区分 |
| actor-niger-armed-forces | 1935 | 无未验证的当前兵力数字 |

---

## 2. 4 个 P0 关系升级

| relation | profile_chars | timeline_nodes | 结果 |
|---|---|---|---|
| rel-jnim-benin-forces-fought | 496→~700 | 0→5 | 54 士兵死亡（政府确认数）与 JNIM 宣称数分离 |
| rel-d1-dan-na-jnim-conflict | 398→~650 | 3→4 | 不简化为「多贡 vs 富拉尼」 |
| rel-d2-jafar-jnim | 315→~650 | 2→4 | Jafar = Ansaroul 领导人 + JNIM 布基纳法索领导人（非整体埃米尔） |
| rel-d2-dozos-macina-jnim-conflict | 159→~600 | 2→4 | 非全国性反恐同盟 |

4 个 P0 全部达到 R3 substantive（≥4 timeline nodes，substantive profile），grade ≥ R-B。

---

## 3. Orphan Evidence

ev-i3a-040（乍得湖盆地冲突累计 4 万人死亡）→ 机械恢复到 `region-lake-chad-basin`（唯一机械目标）。

**ORPHAN_EVIDENCE = 0**

---

## 4. Isolated Graph Nodes 分类

| node | classification | reason |
|---|---|---|
| actor-slm-aw | LEGITIMATE_ISOLATE | 苏丹内战行动者，与反恐网络无关 |
| actor-cameroon-bir | LEGITIMATE_ISOLATE | 喀麦隆国内反恐单位，无漏写证据 |
| actor-ecowas-standby-force | LEGITIMATE_ISOLATE | 待命部队尚未部署 |
| actor-minusma | LEGITIMATE_ISOLATE | 历史任务，JNIM 历史敌对已在 narrative 体现 |

**BROKEN_ORPHAN_NODE_COUNT = 0，LEGITIMATE_ISOLATE_COUNT = 4**（未制造任何 edge）

---

## 5. Mobile Overflow

根因：`intel-bullets` / `intel-source-notes` 长英文名/URL 未换行。

修复：`intelligence.css` 加 `overflow-wrap: anywhere` + `word-break: break-word`（最小修复，无 UI redesign）。

**MOBILE_HORIZONTAL_OVERFLOW = 0**（6 个溢出全部消除），**UI_REGRESSION = 0**

---

## 6. Counts（机械统计）

| | countries | entities | rels | profiles | timelines | sources | evidence | aliases | routes |
|---|---|---|---|---|---|---|---|---|---|
| 前（Expansion E） | 13 | 108 | 205 | 205 | 104 | 291 | 405 | 495 | 340 |
| 后 | 13 | **105** | **201** | **201** | **104** | 291 | 405 | **500** | **333** |

-3 entities（3 person de-formalize），-4 relations（person-only led_by/affiliated/operates 边吸收进组织正文），routes 340→333。

---

## 7. 门禁结果

| 门禁 | 值 |
|---|---|
| ENTITY_GRADE_D_COUNT | **0**（12 → 0） |
| P0_CONSOLIDATION_COUNT | **0**（4 → 0） |
| ORPHAN_EVIDENCE | **0** |
| BROKEN_RELATIONSHIP_TARGETS | **0** |
| BROKEN_EVIDENCE_TARGETS | **0** |
| BROKEN_ALIAS_TARGETS | **0** |
| DUPLICATE_CANONICAL_ENTITIES | **0** |
| PPT_NAMES_UNRESOLVED | **0** |
| QUALITY_BYPASS_SUSPECT_COUNT | **0** |
| MOBILE_HORIZONTAL_OVERFLOW | **0** |
| FACT_SEMANTIC_ERRORS | **0** |
| UI_REGRESSION | **0** |
| FULL_REGRESSION | **PASS**（41 套件 / 7204 用例 / FAILED=0 SKIPPED=0） |
| BUILD | **PASS**（333 routes） |
| BROWSER_QA | **PASS**（26 页 + 3 removed route 404） |
| NETWORK_QA | **PASS**（6 focus） |
| production / gh-pages / preview / force push | NO / NO / NO / NO |

### 重跑 Global Audit（同一评分标准，未改阈值）

| 指标 | 前 | 后 |
|---|---|---|
| ENTITY GRADE A/B/C/D | 70/15/11/12 | **79/15/11/0** |
| RELATION GRADE A/B/C/D | 48/54/54/49 | **50/56/50/45** |
| P0/P1/P2 | 4/115/32 | **0/95/34** |

---

## 8. 交付

- **分支**：`feature/asip-final-depth-consolidation-a`
- **提交**：4 个逻辑 commit（entity consolidation/deformalization、P0 relationship depth、integrity/mobile fix、QA artifacts）
- **normal push**（非 force）
- **未动**：main / gh-pages / preview / production

---

## 9. 停止点

Pack A 完成、结果可信。**不自动开始 Pack B、不处理剩余 95 个 P1、不 Final Closure、不部署线上。** 等待根据 post-consolidation audit 结果设计后续补厚包。
