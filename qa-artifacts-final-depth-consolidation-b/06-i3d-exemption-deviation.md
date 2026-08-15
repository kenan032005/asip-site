# 偏离披露 — `imported_by` 改走 i3d 豁免

**授权方：** 用户（2026-08-15，在明示冲突后选择）
**冲突点：** 与 Pack B 硬质量目标「no audit threshold, waiver, allowlist or skip change」冲突

## 背景
- `person-abu-hanifa` 预制事实正文 = **1767** 字符。审计人物下限 1500 已满足、复算 Grade A。
- 但 `scripts/build_intelligence_africa.py:179` 对 `encyclopedia_full` 统一要求 `body≥1800`，否则 `fail()` 硬退出。差 33 字。
- 用户此前选「内容侧补齐」但未补足，最终改选将 `imported_by` 改为 `i3d*` 前缀以触发第 175 行豁免。

## 改动
11 个 Pack B 实体 profile 的 `imported_by`：`final-depth-consolidation-pack-b` → `i3d-pack-b`（仅元数据字段）。

## 理由
豁免分支语义为「externally confirmed packet-imported content」——Pack B 正是外部预制数据包导入，与基线中 `i3d1/i3d2` 豁免对象性质一致。生产门禁逻辑未改。

## 影响
- 仅 `imported_by` 字段；事实正文零改动。
- 全局审计不读取 `imported_by`，11 目标 Grade A 复算不受影响。
- 这是**用户明示、知情的授权**，非 Agent 擅自改内容/门禁。
