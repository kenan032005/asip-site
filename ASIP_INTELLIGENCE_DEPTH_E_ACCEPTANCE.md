# ASIP Intelligence — DEPTH E Acceptance Report

**Package**: ASIP-DEPTH-E-ETHIOPIA-MULTI-FRONT-CORE-V1（Ethiopia Multi-Front Conflict Core 深度升级）
**Status**: **DEPTH E = CLOSED**（10/10 Gate PASS）

---

## 1. 基线 / 终态 SHA

| 项 | 基线（Depth D CLOSED） | 终态（本轮） |
|---|---|---|
| source | `1d48d2c`（分支 HEAD `d2e4250`） | `14f6b33`（分支 `feature/asip-intelligence-depth-e-ethiopia-core`） |
| gh-pages | `398aba3` | `f7feb36`（普通 push） |
| Pages run | `31302123532` | `31310002635`（success） |

## 2. Count Invariant（全程严格保持）

| 指标 | 值 |
|---|---|
| countries | **13**（不变） |
| non-country entities | **72**（不变，0 新增） |
| relationships | **150**（不变，0 新增） |
| routes | 249 |
| sources | 150 → **158**（+8 新增 + 2 复用） |
| evidence | 260 → **273**（+13） |

未新增实体/关系/国家/ontology，未扩 Somalia / Eritrea（未创建 node），未做地图，未启动 Depth F。

## 4. 七组事实/语义清洗（source-of-truth 层 + generator 一致）

| 组 | 内容 | 结果 |
|---|---|---|
| 1 | **Source 污染清除**：4 实体（ENDF/Fano/OLA/TDF）+ 2 关系（rel-endf-fano-conflict、rel-ethiopia-sudan-border）移除无关 `un-jnim-2018` | 全部清除，残留在 generator 回归中验证为 0 |
| 2 | **OLA primary_category**：`state_security_force` → `insurgent_group` | actor-ola.primary_category = insurgent_group ✓ |
| 3 | **Tigray control 语义**：TDF 旧"事实控制提格雷"降级为"竞争政治权威 + 显著武装能力"；"主权控制"仅在否定语境（"政治主导、军事存在和完整主权控制不能混同"） | PASS |
| 4 | **Pretoria COHA 仍现行**：AU 2026-01-30 声明将其视为关键现行框架；不写"协议已死" | PASS |
| 5 | **伊朗战争燃料短缺因果删除**：ENDF/TDF/rel-endf-tdf-conflict 中该因果 claim 移除（仅保留旧页面引用纠正语境） | PASS |
| 6 | **Fano 去中心化**：保持 umbrella/decentralized 语义；"统一中央指挥"仅否定语境；1,485 事件/5,129 死亡为地区总口径不全部归因 Fano | PASS |
| 7 | **2024-12 OLA 和平范围**：仅覆盖 splinter faction；主流/其他网络继续武装活动；历史 OLA-TPLF 合作不延伸为 2026 正式联盟 | PASS |

## 4. 4 实体成熟度前后

| entity | 前 | 后 | sections | 中文字数 | primary_category | freshness |
|---|---|---|---|---|---|---|
| actor-endf | 无 maturity | **E3_FULL_ENCYCLOPEDIA** | 23 | 1118 | state_security_force | current |
| actor-fano | 无 maturity | **E3_FULL_ENCYCLOPEDIA** | 20 | 840 | state_security_force | current |
| actor-ola | 无 maturity | **E3_FULL_ENCYCLOPEDIA** | 21 | 945 | **insurgent_group（修复）** | current |
| actor-tdf | 无 maturity | **E3_FULL_ENCYCLOPEDIA** | 22 | 986 | insurgent_group | current |

## 5. 4 关系成熟度前后

| relationship | 前 | 后 | type（锁定） | timeline |
|---|---|---|---|---|
| rel-endf-fano-conflict | 无 maturity | **R3** | hostile_to | 3 |
| rel-endf-ola-conflict | 无 maturity | **R3** | hostile_to | 2 |
| rel-endf-tdf-conflict | 无 maturity | **R3** | hostile_to | 4 |
| rel-ethiopia-sudan-border | 无 maturity | **R2** | cross_border_link | 2（UNHCR 2026 dated 语义 + al-Fashaga 历史） |

## 6. Source / Evidence Mapping

- **Sources**：150 → **158**（10 candidates → 8 新增 + 2 URL-exact 复用；published_at=null 未猜日期）
  - 复用：`depthe-au-tigray-2026-01-30`→`ETH_AU_2026_01_30`、`depthe-reuters-eritrea-2026-02-08`→`ETH_REUTERS_2026_02_08`
- **Evidence**：260 → **273**（+13，全部引用 resolve）
  - `analytical_synthesis`（depthe-ev-013，Fano 去中心化分析）→ partially_verified + claim_type=analysis
  - `verified_reported_allegation`（depthe-ev-010，Ethiopia 指责 Eritrea 支持武装）→ verified + method 注明 attributed allegation
  - `verified_with_scope_limit`（depthe-ev-003，1,485 事件/5,129 死亡为地区总口径）→ verified + method 注明 scope limit
  - `verified_analysis`（depthe-ev-011，ACLED current profile）→ verified + method 注明 analysis attribution
  - 最终：verified=12 / partially_verified=1

## 7. Generator Diff

regen diff（幂等重跑导入）：unexpected_object_deletions=0 / entity_count_change=0 / relationship_count_change=0 / country_count_change=0 / importance_level_change=0 / unintended_relation_type_change=0 / profile_depth_regressions=0 / evidence_regressions=0（8 项全 0）。

## 8. Tests / QA

- **专项测试**：11 项（test_depth_e_import.py）全部 PASS（counts、source cleanup、OLA category、Fano decentralized、OLA partial peace、Tigray control semantics、Pretoria current、no Iran fuel claim、Eritrea attribution、Sudan border refresh、generator regression）
- **全回归**：32 Python + Node + build，**FAIL_TOTAL=0**（1 个既有测试同步：metrics generated_by 白名单加 depth_e_import.py）
- **本地候选 Browser QA**：37 页（4 实体 + 4 关系 × 4 视口 + Ethiopia country + 4 索引），0 失败，32 maturity badge / 32 analysis / 32 watch
- **公网 Browser QA**：37 页全绿（与本地一致），consoleErrors/runtimeExceptions/failedRequests/brokenAssets/horizontalOverflow 全 0
- **Network QA**：4 焦点（ENDF/Fano/OLA/TDF）密度 PASS（本地与公网均一次通过，无需 CDN 重试）
- **production diff**：UNEXPECTED=0，白名单（intelligence/africa/**），无删除、无 RC 历史快照改动

## 9. 期间处理的问题

1. **门禁断言过严（4 处）**：TDF"主权控制/事实控制"、ENDF"伊朗战争燃料短缺"、Fano"统一中央指挥"均以否定/旧页面纠正语境存在（packet 原文如此），修正断言为否定语境判定后 PASS。
2. **regen diff scratch**：按 Depth D 经验，qa-artifacts-depth-e/scratch/ 提前加入 .gitignore，提交无污染。

## 10. Remaining Bottom 变化

Depth A 审计 Bottom-20 中，本轮 4 个 Ethiopia 核心实体全部受益：
- **actor-endf** → E3（1118 字，2026 三线战场 + 争议政治逻辑）
- **actor-fano** → E3（840 字，decentralized umbrella + 2026 选举日 90 起交火）
- **actor-ola** → E3（945 字，insurgent_group + splinter-only peace）
- **actor-tdf** → E3（986 字，rival authority + Pretoria 承压）
- 对应 4 条关系 → R3/R2

Depth A 审计中剩余非 Ethiopia 项（如 wagner、dozos 已覆盖等）留待后续候选，本轮未触碰。

---

**DEPTH E = CLOSED。** 已停止，未自动执行 Depth F，未扩广度，未扩 Somalia/Eritrea。
