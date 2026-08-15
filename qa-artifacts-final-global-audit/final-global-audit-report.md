# ASIP Intelligence — Final Global Audit / Final Closure Audit

## 结论

`FINAL_GLOBAL_AUDIT = PASS`
`ASIP_V1_RELEASE_READY = YES`

`FINAL_RELEASE_BLOCKER_COUNT = 0`

## 审计范围与原则

本轮为 **READ-ONLY FINAL AUDIT**：不新增/删除/修改任何知识数据，不修改阈值、
不添加 waiver/allowlist/skip，不修改 UI，不部署。

`KNOWLEDGE_DATA_CHANGED = 0`（pre/post sha256 byte-identical，17 个数据文件）。

## 基线

| 项 | 值 |
|----|----|
| base branch | feature/asip-final-depth-consolidation-b |
| base HEAD | 71b9911 |
| entities | 105 |
| relationships | 203 |
| sources | 307 |
| evidence | 422 |
| countries | 13 |
| regions | 7 |
| routes | 335 |

## 关键门禁结果

| 门禁 | 值 |
|------|----|
| KNOWLEDGE_DATA_CHANGED | 0 |
| DUPLICATE_CANONICAL_ENTITIES | 0 |
| BROKEN_ALIAS_TARGETS | 0 |
| ALIAS_COLLISION_UNRESOLVED | 0 |
| ENTITY_GRADE_C_COUNT | 0 |
| ENTITY_GRADE_D_COUNT | 0 |
| ENTITY_NOT_READY_COUNT | 0 |
| RELATION_NOT_READY_COUNT | 0 |
| P0_CONSOLIDATION_COUNT | 0 |
| PPT_NAMES_UNRESOLVED | 0 |
| PPT_RESOLUTION_CONFLICT_COUNT | 0 |
| BROKEN_SOURCE_REFS | 0 |
| BROKEN_EVIDENCE_TARGETS | 0 |
| ORPHAN_EVIDENCE | 0 |
| DUPLICATE_SOURCE_URLS | 0 |
| BROKEN_COUNTRY_REFS | 0 |
| BROKEN_REGION_REFS | 0 |
| BROKEN_ORPHAN_NODE | 0 |
| QUALITY_BYPASS_SUSPECT_COUNT | 0 |
| THEATER_NOT_READY_COUNT | 0 |
| STALE_RELEASE_BLOCKING | 0 |
| CONFLICTING_STATUS | 0 |
| RELEASE_BLOCKING_DEFERRED_COUNT | 0 |
| MOBILE_HORIZONTAL_OVERFLOW | 0 |
| BROKEN_INTERNAL_LINKS | 0 |
| JS_RUNTIME_ERRORS | 0 |
| UI_REGRESSION | 0 |
| TEST_CASES_FAILED | 0 |
| BUILD | PASS |
| FULL_REGRESSION | PASS |

## 实体与关系

- 实体 Grade：A=90 / B=15 / C=0 / D=0（person 1500 / org 1800 type-aware）
- 关系 Grade：R-A=50 / R-B=56 / R-C=52 / R-D=45；R3 全部达到当前可接受深度
  （无 R3 落入 R-C/R-D），P0=0。
- R1/R2 关系按角色判定（READY_FOR_ROLE），不因短而自动判失败。

## 历史 P1/P2 处置

Phase 2 的 HIGH_VALUE_DEPTH=20 / ADEQUATE_FOR_ROLE=50 / DEFER_FUTURE=25 全部
保留且 **无一 RELEASE_BLOCKING**。DEFER_FUTURE 归入 V1.1_PLUS，不阻断 V1.0。

## Africa Corps 专项

`actor-africa-corps`：Grade A，有 Wagner 区分、AES 关系、马里存在。结论
`READY_WITH_MINOR_GAPS`（证据密度偏低，非阻断），`FINAL_CLOSURE_BLOCKER=false`。

## Theater Readiness

8 个战区全部 READY / READY_WITH_MINOR_GAPS，`THEATER_NOT_READY_COUNT=0`。
Sudan 不再因 `actor-slm-aw` 触发 NEEDS_FINAL_CONSOLIDATION。

## Regression

正式 auto-discovery runner：41 suites / 7310 cases / 0 failed / 0 skipped。

## 非阻断技术债（FINAL_TECH_DEBT_LIST）

- 43 条长 source URL（CSS word-break 处理，无确认溢出）
- `actor-africa-corps` 证据密度偏低（READY_WITH_MINOR_GAPS，非阻断）
- 52 R-C + 45 R-D 关系（DEFER_FUTURE / ADEQUATE_FOR_ROLE，非阻断）
- 历史脏 QA 制品 diff 未提交（IGNORE_SAFE，非阻断）

以上均不触发 FAIL。

## 部署隔离

production changed = NO；gh-pages changed = NO；preview changed = NO；
main changed = NO；force push = NO。

## 下一步（等待 ChatGPT 验收）

`ASIP_V1_RELEASE_READY = YES` 后，进入：
FINAL PREVIEW RELEASE → 用户人工验收 → PRODUCTION CUTOVER。
