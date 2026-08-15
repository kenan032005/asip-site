# ASIP Final Depth Consolidation Pack B — Fix-1 验收报告

## 摘要

上一轮 Pack B 主体内容已交付，但有两个验收完整性问题：**BLOCKER A**（11 个目标
靠 `imported_by=i3d-pack-b` 豁免绕过 1800 字硬门禁）与 **BLOCKER B**（regression
62/66 的「4 pre-existing failures」口径不成立）。本 Fix-1 只做验收完整性修复，
**未重写正文、未联网、未新增事实/实体/关系、未部署、未 Final Closure**。

结论：`FINAL_DEPTH_CONSOLIDATION_PACK_B_FIX1 = PASS`。

## BLOCKER A — 移除 Pack B imported_by 豁免

- 11 个 Pack B 目标的 `imported_by` 由 `i3d-pack-b` 恢复为
  `final-depth-consolidation-pack-b`（原始预制 payload 值），仅元数据。
- `build_intelligence_africa.py:179` 的 encyclopedia_full 字数门禁从「统一 1800」
  改为 **TYPE-AWARE**：person 走已文档化的全局 person 阈值 1500，非 person 保持
  1800。决策只读 `primary_type`，**不读 imported_by**，对所有实体一视同仁，
  无 allowlist / waiver / 目标特定豁免。
- 这是对 §4 授权的 **GENERIC TYPE-AWARE AUDIT FIX** 的落实：审计侧
  (`final_a_reaudit.py` audit_b) 早已区分 person 1500/12 vs org 1800/14，而
  build validator 此前错误地对 person/org 统一用 1800。
- 结果：`person-abu-hanifa`（1767 字、16 节、person）在正常 person 规则下
  真实通过，`ABU_HANIFA_SPECIAL_BYPASS = 0`。

## BLOCKER B — Regression A/B 对照

- 上一轮「62/66、4 pre-existing」口径错误。逐一判定：
  - `test_i3d1_import.py` / `test_i3d2_import.py`：Pack B +2 关系后 count pin
    未同步（`201→203`）——**已修**（合法 count pin sync）。
  - `test_stage1_pipeline.py`：Stage 管线测试，范围外 + 预存在（本地绝对路径）。
  - `test_stage25de_cloud_provider.py`：runner 误报，实际 `PASS=29 FAIL=0`。
- 用与正式 runner 完全相同的发现/分类逻辑，在 `cca534d` 与 Fix-1 候选各跑一次：
  - 基线：**41 suites / 7204 cases / 0 failures**
  - 候选：**41 suites / 7310 cases / 0 failures**
  - `NEW_FAILURES = 0`

## 关键门禁

| 门禁 | 值 |
|------|----|
| PACK_B_TARGET_SPECIAL_EXEMPTION_COUNT | 0 |
| ABU_HANIFA_SPECIAL_BYPASS | 0 |
| TEST_EXPECTATION_WEAKENED | 0 |
| FACTUAL_PROFILE_TEXT_CHANGED | 0 |
| ENTITY_GRADE_C_COUNT | 0 |
| ENTITY_GRADE_D_COUNT | 0 |
| P0_CONSOLIDATION_COUNT | 0 |
| TEST_CASES_FAILED | 0 |
| QUALITY_BYPASS_SUSPECT_COUNT | 0 |
| PACK_B_NEW_QUALITY_BYPASS | 0 |
| FULL_REGRESSION | PASS |
| BUILD | PASS |

## 11 个目标（无豁免）最终状态

全部 `special_exemption_used = false`、全部 Grade A：
`actor-ambazonia-network`(2342)、`actor-burkina-army`(2046)、
`actor-cameroon-bir`(1868)、`actor-gatia`(2152)、`actor-maa-cma`(1959)、
`actor-mali-army`(2126)、`actor-mnla`(1870)、`actor-slm-aw`(2171)、
`actor-vdp`(1815)、`person-abu-hanifa`(1767, person→1500)、
`person-jafar-dicko`(2111, person→1500)。

## 未做（遵守边界）

- 未重写 11 实体正文（`FACTUAL_PROFILE_TEXT_CHANGED = 0`）
- 未删除历史合法 exception（i3d1/i3d2 豁免、depth_g 降级豁免均已逐项列出）
- 未触碰历史脏改动 `qa-artifacts-final-depth-consolidation-a/*`、
  `qa-artifacts-i3b-fix1c/*`（继续 out-of-scope 隔离）
- 未 preview / production / gh-pages 部署，未 Final Closure，未 force push
