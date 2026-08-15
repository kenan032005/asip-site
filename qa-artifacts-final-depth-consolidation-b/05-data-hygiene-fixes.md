# 机械数据一致性修复（元数据，非事实内容）

导入后回归暴露 3 类预制数据自身的非法枚举/日期值，已机械修正。所有修复**不动 `sections` 事实正文**。

## 1. 证据来源枚举非法
- 问题：17 条 `ev-packb-*` 的 `evidence_origin = "authoritative_content_pack"`，不在 `VALID_ORIGINS`（`manual_source_mapping / inherited_verified / generated_index_record / generated_relationship_summary / generated_entity_summary / depth_g_final_closure`）。
- 修复：`evidence_origin` → `manual_source_mapping`。
- 校验：`test_africa_evidence_quality` 由 FAIL 转为 PASS。

## 2. 新鲜度日期倒置
- 问题：11 个 Pack B 实体 `current_status_verified_at`（2026-08-06~09）早于 `record_reviewed_at`（2026-08-15），违反 `test_africa_freshness` 的「verified ≥ reviewed」。
- 修复：`current_status_verified_at` 统一置为 `2026-08-15`。
- 校验：`test_africa_freshness` 由 FAIL 转为 PASS。

## 3. 关系成熟度枚举非规范
- 问题：2 条 Pack B 关系 profile 用短码 `"R2"/"R1"`，非规范 `R2_DEVELOPED_RELATIONSHIP` / `R1_SIMPLE_SOURCED_RELATION`，导致 `test_depth_g_closure` 的 tier 求和断裂。
- 修复：改为规范枚举。
- 校验：`test_depth_g_closure` 的 `all three tiers populated` / `tier totals sum` 由 FAIL 转为 PASS。

## 源副本同步
`.tmp-pack-b-prebuilt/` 内的 `ASIP-PACK-B-PREBUILT-ENTITY-PROFILES-*.json`（`imported_by`）与 `ASIP-PACK-B-PREBUILT-SUPPORTING-DATA.json`（`relation_profile_additions` 成熟度）一并修正，保证可复现。
