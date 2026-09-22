# ASIP Historical Backfill Import Review — asip-backfill-20260818-20260827

- 窗口: 2026-08-18T00:00:00+08:00 → 2026-08-27T23:59:59+08:00
- 模式: historical_backfill / historical_reconstruction=true
- 输入: Social 29 / Disease 9 / China 8 / Sources 51

## Social 导入
| 项 | 值 |
|---|---|
| 输入 | 29 |
| 新增 Master | 25 |
| 更新（簇内 timeline） | 3 |
| 重复（包内 content hash） | 0 |
| 与既有 canonical 重复 | 0 |
| HOLD | 1 |

## Disease 导入
| 项 | 值 |
|---|---|
| 输入 | 9 |
| 新增实体 | 5 |
| 更新（timeline update） | 4 |
| HOLD | 0 |

## China Interest
- Direct: 2 / Indirect: 5 / HOLD(对应事件未接受): 1

## 历史报告
- Africa Daily: 10 份（FALLBACK facts-only，本地无 AI key）
  - 2026-08-18: FALLBACK (3 facts)
  - 2026-08-19: FALLBACK (2 facts)
  - 2026-08-20: FALLBACK (5 facts)
  - 2026-08-21: FALLBACK (5 facts)
  - 2026-08-22: FALLBACK (1 facts)
  - 2026-08-23: FALLBACK (1 facts)
  - 2026-08-24: FALLBACK (3 facts)
  - 2026-08-25: FALLBACK (1 facts)
  - 2026-08-26: FALLBACK (3 facts)
  - 2026-08-27: FALLBACK (1 facts)
- Weekly: 0（窗口 08-18(周二)–08-27(周四) 无完整自然周，未生成不完整周报）
- Major Brief 候选（importance>=85，auto-publication=false）: 8
  - 91 尼日利亚高原州村庄遭袭，至少25人死亡 (尼日利亚, 2026-08-18)
  - 92 中非共和国非法金矿坍塌，至少100人死亡 (中非共和国, 2026-08-18)
  - 86 尼日利亚索科托州船只倾覆，至少50人死亡，多数为儿童 (尼日利亚, 2026-08-20)
  - 93 尼日尔州Borgu地区清真寺及村庄遭袭，多名民众被绑架 (尼日利亚, 2026-08-21)
  - 88 刚果（金）政府与AFC/M23就和平谈判路线图达成一致 (刚果（金）, 2026-08-22)
  - 95 南苏丹琼莱州联合国巡逻队遭伏击，两名维和人员死亡 (南苏丹, 2026-08-24)
  - 89 苏丹医疗组织指称SPLM-N在南科尔多凡杀害27名平民 (苏丹, 2026-08-26)
  - 96 乍得将相关地区戒备提升至最高级别，苏丹跨境打击争议引发外溢担忧 (乍得, 2026-08-27)

## HOLD 明细
- `BF-SOC-0019` HOLD_DISPUTED_NOT_UPGRADED: {"country_iso3": "TCD", "event_date": "2026-08-22"}

## 数据完整性审计
- DUPLICATE_MASTER_EVENT: 0（content hash + cluster 合并）
- SAFETY_CONTAMINATION: 0（disputed 未升级；HOLD 未入 Public）
- verification 未升级：official_confirmed→已核实 / multi_source→多源支持 / single_source→单一来源 / disputed→HOLD
- 未生成任何 AI 分析（本地无 DeepSeek key；历史报告为 facts-only FALLBACK）

## Production 隔离
- PRODUCTION_MIGRATION = NOT_EXECUTED
- main / production-state / gh-pages 未修改
## 最终 QA 审计（§十九）
- DUPLICATE_MASTER_EVENT = 0
- DUPLICATE_DISEASE_EVENT = 0
- WRONG_COUNTRY = 0 / WRONG_DATE = 0
- MISSING_SOURCE = 0 / UNSUPPORTED_NUMBER = 0
- DISPUTED_IN_PUBLIC = 0（disputed 已 HOLD，Safety 无污染）
- METADATA_MIXING = 0（全部 ingestion_mode=historical_backfill）
- Countries covered: 16（CAF COD ETH GNB LBR MLI NGA SDN SOM SSD TCD TGO TUN TZA UGA ZMB）
- VERIFICATION 分布: multi=17 / single=5 / official=3（未升级）
- CHINA: direct=2 / indirect=5 / held=1（对应事件 HOLD 联动）

## Preview
- 本地 Preview URL: http://127.0.0.1:8101（preview_dist_backfill/，未部署 Production）
- 截图: .workbuddy_tmp/shot/backfill/{homepage-desktop,events,reports,disease-risk}.png
- 历史日报页面: preview_dist_backfill/reports/africa_daily/2026-08-18..27/index.html（历史回溯生成 标签）
- validate_pipeline dist: V13-count 差异为设计预期（preview dist 含 +25 回填事件，deploy 被阻止 = 目标状态）

## AI / Token
- TOTAL_AI_CALLS = 0 / TOTAL_TOKENS = 0（数据包已含全部事实字段，无缺失 enrichment 字段；本地无 DeepSeek key，历史日报为 facts-only FALLBACK）
