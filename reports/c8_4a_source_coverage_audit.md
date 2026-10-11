# C8-4A · 源覆盖基线审计（只读）

生成时间：2026-09-28T14:22:09+00:00 ｜ 采集轮：20260928T125608+0800_i7x97j ｜ 公开条目：923

> 本包**未新增/修改**任何源、采集逻辑、分类器、geo-scope 或 UI；未调整任何阈值。
> 所有数值来自真实生产台账；缺失项标 null/UNKNOWN，不臆造。

## A. 权威源清单

| 指标 | 值 |
|---|---|
| CONFIGURED_LOGICAL_SOURCES | 120 |
| ENABLED_LOGICAL_SOURCES | 118 |
| DISABLED_LOGICAL_SOURCES | 2（un_acled_chad, un_acled_niger） |
| EXPANDED_PRODUCTION_SOURCE_EXECUTIONS | 802 |
| 展开数 == per_source 行数 | True |

**执行数 > 逻辑源数的原因**：多国/泛非源（country_scope 含多个国家）在每个 scope 国家各执行一次；生产实测 per_source 行数与 Σscope 完全一致。

## C. 运行健康分类（启用源）

| 分类 | 数量 |
|---|---|
| RATE_LIMITED | 34 |
| BROKEN_OR_STALE | 27 |
| NO_RECENT_OUTPUT | 16 |
| DUPLICATE_HEAVY | 15 |
| HEALTHY_LOW_VOLUME | 11 |
| HEALTHY_PRODUCTIVE | 4 |
| WALL_CLOCK_STARVED | 4 |
| HIGH_VALUE_LOW_FREQUENCY | 3 |
| EMPTY_FEED | 2 |
| QUARANTINE_HEAVY | 1 |
| ACCESS_BLOCKED | 1 |

## K. 源数量 ≠ 覆盖质量（强制区分）

| 口径 | 数值 |
|---|---|
| TOTAL_SOURCES（启用逻辑源） | 118 |
| HEALTHY_SOURCES | 18 |
| PRODUCTIVE_SOURCES（本轮有 published） | 6 |
| UNIQUE_INFORMATION_CONTRIBUTORS（有公开条目） | 30 |

⇒ 启用 118 源中，仅 18 个处于健康类、6 个有产出、30 个真正向公开层贡献了条目。

## F. P0 专项 — 尼日尔（NIGER）

| 指标 | 值 |
|---|---|
| NIGER_CURRENT_SOURCE_COUNT | 67 |
| NIGER_HEALTHY_SOURCE_COUNT | 7 |
| NIGER_PRODUCTIVE_SOURCE_COUNT | 5 |
| NIGER_24H_PUBLIC_ITEMS | 0 |
| NIGER_7D_PUBLIC_ITEMS | 12 |

### 按类别分布

| 类别 | 源数 |
|---|---|
| NIGER_NATIONAL | 33 |
| PAN_AFRICA | 11 |
| NIGER_LOCAL | 8 |
| UN_HUMANITARIAN | 7 |
| NIGER_OFFICIAL | 4 |
| OTHER | 3 |
| GLOBAL_TIER_1 | 1 |

### 逐源明细（前 24，按发现量降序）

| source_id | 类别 | tier | health | attempted | discovered | fetched | published | quar | dup | public | 语言 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pan_allafrica | PAN_AFRICA | tier_2 | DUPLICATE_HEAVY | 54 | 780 | 10 | 0 | 9 | 770 | 0 | ['en'] |
| pan_unnews_africa | PAN_AFRICA | tier_1 | DUPLICATE_HEAVY | 54 | 780 | 0 | 0 | 0 | 780 | 0 | ['en'] |
| pan_africanews | PAN_AFRICA | tier_2 | HEALTHY_PRODUCTIVE | 54 | 780 | 509 | 3 | 4 | 276 | 5 | ['en', 'fr'] |
| pan_france24_africa | PAN_AFRICA | tier_1 | DUPLICATE_HEAVY | 54 | 780 | 49 | 1 | 1 | 733 | 0 | ['en'] |
| pan_bbc_africa | PAN_AFRICA | tier_1 | HEALTHY_PRODUCTIVE | 54 | 780 | 780 | 1 | 1 | 7 | 0 | ['en'] |
| pan_aljazeera | PAN_AFRICA | tier_1 | DUPLICATE_HEAVY | 54 | 760 | 12 | 0 | 12 | 748 | 0 | ['en'] |
| pan_rfi_afrique | PAN_AFRICA | tier_1 | HEALTHY_PRODUCTIVE | 54 | 760 | 684 | 3 | 2 | 80 | 6 | ['fr'] |
| gha_myjoyonline | OTHER | tier_2 | HEALTHY_PRODUCTIVE | 32 | 423 | 347 | 4 | 21 | 76 | 72 | ['en'] |
| rwa_newtimes | OTHER | tier_2 | NO_RECENT_OUTPUT | 32 | 357 | 231 | 0 | 0 | 126 | 0 | ['en'] |
| nga_premiumtimes | OTHER | tier_2 | DUPLICATE_HEAVY | 32 | 315 | 15 | 0 | 15 | 300 | 0 | ['en'] |
| pan_dw_africa | PAN_AFRICA | tier_1 | DUPLICATE_HEAVY | 54 | 190 | 3 | 0 | 0 | 187 | 0 | ['en'] |
| niger_nigerinter | NIGER_LOCAL | tier_2 | NO_RECENT_OUTPUT | 1 | 30 | 21 | 0 | 0 | 13 | 7 | ['fr'] |
| niger_journalduniger | NIGER_LOCAL | tier_2 | NO_RECENT_OUTPUT | 1 | 30 | 28 | 0 | 0 | 5 | 18 | ['fr'] |
| niger_anp | NIGER_NATIONAL | tier_3 | NO_RECENT_OUTPUT | 1 | 24 | 24 | 0 | 7 | 2 | 43 | ['fr'] |
| intl_aljazeera_niger | NIGER_NATIONAL | tier_3 | DUPLICATE_HEAVY | 1 | 20 | 2 | 0 | 2 | 18 | 0 | en |
| intl_rfi_afrique_niger | NIGER_NATIONAL | tier_1 | HIGH_VALUE_LOW_FREQUENCY | 1 | 20 | 18 | 0 | 0 | 2 | 0 | ['fr'] |
| intl_bbc_afrique_niger | NIGER_NATIONAL | tier_1 | DUPLICATE_HEAVY | 1 | 20 | 6 | 0 | 0 | 14 | 0 | ['fr'] |
| intl_france24_afrique_niger | NIGER_NATIONAL | tier_1 | DUPLICATE_HEAVY | 1 | 20 | 5 | 0 | 0 | 15 | 0 | ['fr'] |
| niger_africanews | NIGER_NATIONAL | tier_1 | HIGH_VALUE_LOW_FREQUENCY | 1 | 20 | 13 | 0 | 2 | 7 | 2 | ['fr'] |
| niger_studiokalangou | NIGER_LOCAL | tier_2 | DUPLICATE_HEAVY | 1 | 15 | 4 | 0 | 1 | 12 | 8 | ['fr'] |
| niger_airinfo | NIGER_LOCAL | tier_2 | NO_RECENT_OUTPUT | 1 | 10 | 10 | 0 | 0 | 0 | 10 | ['fr'] |
| niger_tamtaminfo | NIGER_LOCAL | tier_2 | NO_RECENT_OUTPUT | 1 | 10 | 10 | 0 | 0 | 1 | 5 | ['fr'] |
| niger_sahelien | NIGER_NATIONAL | tier_2 | NO_RECENT_OUTPUT | 1 | 10 | 10 | 0 | 0 | 0 | 0 | ['fr'] |
| niger_ouestaf | NIGER_NATIONAL | tier_2 | NO_RECENT_OUTPUT | 1 | 10 | 10 | 0 | 0 | 0 | 0 | ['fr'] |

### 缺失类别（NIGER_MAJOR_GAPS）

| 期望类别 | 当前是否存在 |
|---|---|
| GLOBAL_TIER_1 | YES |
| NIGER_HEALTH | **MISSING** |
| NIGER_LOCAL | YES |
| NIGER_NATIONAL | YES |
| NIGER_OFFICIAL | YES |
| NIGER_SECURITY_DEFENCE | **MISSING** |
| PAN_AFRICA | YES |
| RESEARCH_SECURITY | **MISSING** |
| SAHEL_REGIONAL | **MISSING** |
| UN_HUMANITARIAN | YES |

注：`NIGER_SECURITY_DEFENCE` / `NIGER_HEALTH` 为**角色**类，当前配置中无 source_role 标注为SECURITY_DEFENCE/POLICE_INTERIOR/HEALTH 的尼日尔专属源 ⇒ 由类别表判定为缺失。

## G. P1 国家缺口审计

### 尼日利亚

- 非泛非/非 Tier-1 的属地源数 = **-5**（ENABLED 15 − pan 11 − tier1 9）
- 本地源 = 3 ｜ 官方/人道源 = 0 ｜ 区域源 = 0 ｜ Tier-1 触达 = 9
- 健康源 = 4 ｜ 有产出源 = 5 ｜ 公开条目 24h/7d = 0 / 2
- **低量主因（数值判定）** = `working(有公开条目)`
- 欠覆盖领域 = 见 §J（按 P0/P1 汇总列）

### 贝宁

- 非泛非/非 Tier-1 的属地源数 = **-5**（ENABLED 14 − pan 11 − tier1 8）
- 本地源 = 3 ｜ 官方/人道源 = 0 ｜ 区域源 = 0 ｜ Tier-1 触达 = 8
- 健康源 = 4 ｜ 有产出源 = 5 ｜ 公开条目 24h/7d = 0 / 0
- **低量主因（数值判定）** = `produced_but_not_public(源有产出但未进入公开层：relevance 过滤/隔离/本地化)`
- 欠覆盖领域 = 见 §J（按 P0/P1 汇总列）

### 莫桑比克

- 非泛非/非 Tier-1 的属地源数 = **-5**（ENABLED 14 − pan 11 − tier1 8）
- 本地源 = 3 ｜ 官方/人道源 = 0 ｜ 区域源 = 0 ｜ Tier-1 触达 = 8
- 健康源 = 4 ｜ 有产出源 = 5 ｜ 公开条目 24h/7d = 0 / 0
- **低量主因（数值判定）** = `produced_but_not_public(源有产出但未进入公开层：relevance 过滤/隔离/本地化)`
- 欠覆盖领域 = 见 §J（按 P0/P1 汇总列）

### 南苏丹

- 非泛非/非 Tier-1 的属地源数 = **-4**（ENABLED 16 − pan 11 − tier1 9）
- 本地源 = 4 ｜ 官方/人道源 = 0 ｜ 区域源 = 0 ｜ Tier-1 触达 = 9
- 健康源 = 4 ｜ 有产出源 = 6 ｜ 公开条目 24h/7d = 4 / 9
- **低量主因（数值判定）** = `working(有公开条目)`
- 欠覆盖领域 = 见 §J（按 P0/P1 汇总列）

### 埃塞俄比亚

- 非泛非/非 Tier-1 的属地源数 = **-5**（ENABLED 15 − pan 11 − tier1 9）
- 本地源 = 3 ｜ 官方/人道源 = 0 ｜ 区域源 = 0 ｜ Tier-1 触达 = 9
- 健康源 = 4 ｜ 有产出源 = 5 ｜ 公开条目 24h/7d = 3 / 18
- **低量主因（数值判定）** = `working(有公开条目)`
- 欠覆盖领域 = 见 §J（按 P0/P1 汇总列）

## H. 乍得（CHAD）质量审计（非扩源目标）

- 乍得触达源 = 64 ｜ 健康 = 15 ｜ 有产出 = 5 ｜ 公开条目 24h/7d = 8 / 62
- DUPLICATE_HEAVY 源 = 9（intl_aljazeera_chad, intl_bbc_afrique_chad, intl_france24_afrique_chad, pan_allafrica, pan_unnews_africa, nga_premiumtimes, pan_france24_africa, pan_aljazeera）
- QUARANTINE_HEAVY 源 = 1（chad_lendjampost）
- WALL_CLOCK_STARVED 源 = 4（pan_reliefweb, pan_voa_africa, pan_voa_afrique, specialist_acss）
- 源多样性：本地 10 ｜ 官方/人道 11 ｜ pan 11 ｜ tier1 14

**结论（不执行任何变更）**：乍得覆盖数量充足；质量侧证据显示存在 重复主导/隔离主导/墙钟饥饿 三类源，可在 C8-4 后期评估**降频/替换为更高质量源**，但本包不动任何配置。

## I. 全球 Tier-1 / 泛非 / 区域基线

### GLOBAL_TIER_1 CURRENT（21）

| source_id | name | tier | scope | published | health |
|---|---|---|---|---|---|
| niger_lesahel | Le Sahel | tier_1 | 1 | 0 | HEALTHY_LOW_VOLUME |
| intl_reuters_chad | Reuters（乍得） | tier_1 | 1 | 0 | HEALTHY_LOW_VOLUME |
| intl_xinhua_chad | 新华社/新华网（乍得） | tier_1 | 1 | 0 | HEALTHY_LOW_VOLUME |
| intl_reuters_niger | Reuters（尼日尔） | tier_1 | 1 | 0 | RATE_LIMITED |
| intl_xinhua_niger | 新华社/新华网（尼日尔） | tier_1 | 1 | 0 | RATE_LIMITED |
| intl_rfi_afrique_chad | RFI Afrique (Chad) | tier_1 | 1 | 0 | HIGH_VALUE_LOW_FREQUENCY |
| intl_rfi_afrique_niger | RFI Afrique (Niger) | tier_1 | 1 | 0 | HIGH_VALUE_LOW_FREQUENCY |
| intl_bbc_afrique_chad | BBC Afrique (Chad) | tier_1 | 1 | 0 | DUPLICATE_HEAVY |
| intl_bbc_afrique_niger | BBC Afrique (Niger) | tier_1 | 1 | 0 | DUPLICATE_HEAVY |
| intl_france24_afrique_chad | France24 Afrique (Chad) | tier_1 | 1 | 0 | DUPLICATE_HEAVY |
| intl_france24_afrique_niger | France24 Afrique (Niger) | tier_1 | 1 | 0 | DUPLICATE_HEAVY |
| niger_africanews | AfricaNews (Niger) | tier_1 | 1 | 0 | HIGH_VALUE_LOW_FREQUENCY |
| pan_unnews_africa | UN News (Africa) | tier_1 | 54 | 0 | DUPLICATE_HEAVY |
| pan_france24_africa | France 24 (Africa) | tier_1 | 54 | 1 | DUPLICATE_HEAVY |
| pan_bbc_africa | BBC News (Africa) | tier_1 | 54 | 1 | HEALTHY_PRODUCTIVE |
| pan_aljazeera | Al Jazeera | tier_1 | 54 | 0 | DUPLICATE_HEAVY |
| pan_voa_africa | VOA Africa | tier_1 | 54 | 0 | WALL_CLOCK_STARVED |
| pan_voa_afrique | VOA Afrique | tier_1 | 54 | 0 | WALL_CLOCK_STARVED |
| pan_rfi_afrique | RFI Afrique | tier_1 | 54 | 3 | HEALTHY_PRODUCTIVE |
| pan_dw_africa | DW Africa | tier_1 | 54 | 0 | DUPLICATE_HEAVY |
| specialist_acss | Africa Center for Strategic Studies | tier_1 | 9 | 0 | WALL_CLOCK_STARVED |

### AFRICA_WIDE CURRENT（11）

| source_id | name | published | public_items | health |
|---|---|---|---|---|
| pan_allafrica | AllAfrica | 0 | 0 | DUPLICATE_HEAVY |
| pan_unnews_africa | UN News (Africa) | 0 | 0 | DUPLICATE_HEAVY |
| pan_africanews | Africanews | 3 | 5 | HEALTHY_PRODUCTIVE |
| pan_france24_africa | France 24 (Africa) | 1 | 0 | DUPLICATE_HEAVY |
| pan_reliefweb | ReliefWeb | 0 | 0 | WALL_CLOCK_STARVED |
| pan_bbc_africa | BBC News (Africa) | 1 | 0 | HEALTHY_PRODUCTIVE |
| pan_aljazeera | Al Jazeera | 0 | 0 | DUPLICATE_HEAVY |
| pan_voa_africa | VOA Africa | 0 | 0 | WALL_CLOCK_STARVED |
| pan_voa_afrique | VOA Afrique | 0 | 0 | WALL_CLOCK_STARVED |
| pan_rfi_afrique | RFI Afrique | 3 | 6 | HEALTHY_PRODUCTIVE |
| pan_dw_africa | DW Africa | 0 | 0 | DUPLICATE_HEAVY |

### REGIONAL_AFRICA CURRENT

| region | relevant | healthy | productive | public_items |
|---|---|---|---|---|
| SAHEL | 116 | 18 | 5 | 412 |
| WEST_AFRICA | 67 | 7 | 5 | 371 |
| LAKE_CHAD_BASIN | 116 | 18 | 5 | 592 |
| EAST_AFRICA | 16 | 4 | 6 | 83 |
| HORN_OF_AFRICA | 16 | 4 | 6 | 136 |
| GREAT_LAKES | 16 | 4 | 5 | 45 |
| CENTRAL_AFRICA | 65 | 15 | 5 | 337 |
| SOUTHERN_AFRICA | 14 | 4 | 5 | 59 |
| NORTH_AFRICA | 14 | 4 | 5 | 20 |

## J. 安全领域覆盖

| domain | public_items | P0/P1 |
|---|---|---|
| TERRORISM | 32 | 18 |
| ARMED_CONFLICT | 150 | 74 |
| KIDNAPPING | 5 | 2 |
| CRIME | 356 | 122 |
| POLITICAL_INSTABILITY | 8 | 5 |
| PROTESTS_CIVIL_UNREST | 26 | 9 |
| BORDER_SECURITY | 2 | 0 |
| MILITARY_SECURITY | 11 | 5 |
| TRANSPORT_LOGISTICS | 6 | 3 |
| ENERGY_MINING | 0 | 0 |
| INFRASTRUCTURE | 6 | 3 |
| NATURAL_HAZARDS | 10 | 3 |
| HUMANITARIAN | 0 | 0 |
| PUBLIC_HEALTH | 12 | 0 |

- 零覆盖领域 = ENERGY_MINING, HUMANITARIAN
- 稀薄领域（≤5 条）= KIDNAPPING, BORDER_SECURITY
- `other_security` 与空 `event_type` 合计 647 条 ⇒ 分类颗粒度仍是覆盖评估的噪声源。

## L. 排名缺口矩阵（四维：业务优先级 / 当前产出 / 源多样性 / 源健康）

### P0_CRITICAL_GAPS

| country | enabled | healthy | productive | 7d public | diversity | 判定 |
|---|---|---|---|---|---|---|
| 尼日尔 | 67 | 7 | 5 | 12 | 100 | working(有公开条目) |

### P1_CRITICAL_GAPS

| country | enabled | healthy | productive | 7d public | diversity | 判定 |
|---|---|---|---|---|---|---|
| 莫桑比克 | 14 | 4 | 5 | 0 | 48 | produced_but_not_public(源有产出但未进入公开层：relevance 过滤/隔离/本地化) |
| 贝宁 | 14 | 4 | 5 | 0 | 48 | produced_but_not_public(源有产出但未进入公开层：relevance 过滤/隔离/本地化) |
| 尼日利亚 | 15 | 4 | 5 | 2 | 50 | working(有公开条目) |
| 南苏丹 | 16 | 4 | 6 | 9 | 53 | working(有公开条目) |
| 埃塞俄比亚 | 15 | 4 | 5 | 18 | 50 | working(有公开条目) |

### GLOBAL_TIER1_GAPS

- 已配置 Tier-1 源 21 个；其中本轮零产出 18 个：niger_lesahel, intl_reuters_chad, intl_xinhua_chad, intl_reuters_niger, intl_xinhua_niger, intl_rfi_afrique_chad, intl_rfi_afrique_niger, intl_bbc_afrique_chad, intl_bbc_afrique_niger, intl_france24_afrique_chad
- 结构性缺口：**通讯社/全球商业媒体**（如 wire service / 财经）在配置中未见独立条目 —— 需在 C8-4D 规划。

### AFRICA_WIDE_GAPS

- 已配置泛非源 11 个；本轮零产出 7 个：pan_allafrica, pan_unnews_africa, pan_reliefweb, pan_aljazeera, pan_voa_africa, pan_voa_afrique, pan_dw_africa
- 结构性缺口：VOA Africa/Afrique（端点失效）、ReliefWeb（API appname 未获批）已在 C8-2 记录。

### REGIONAL_GAPS

| region | relevant | productive | 判定 |
|---|---|---|---|
| SAHEL | 116 | 5 | 可用 |
| WEST_AFRICA | 67 | 5 | 可用 |
| LAKE_CHAD_BASIN | 116 | 5 | 可用 |
| GREAT_LAKES | 16 | 5 | 可用 |
| CENTRAL_AFRICA | 65 | 5 | 可用 |
| SOUTHERN_AFRICA | 14 | 5 | 可用 |
| NORTH_AFRICA | 14 | 5 | 可用 |
| EAST_AFRICA | 16 | 6 | 可用 |
| HORN_OF_AFRICA | 16 | 6 | 可用 |

### DOMAIN_GAPS

- 零覆盖：ENERGY_MINING, HUMANITARIAN
- 稀薄：KIDNAPPING, BORDER_SECURITY
- P0/P1 视角下最需补强的领域 = 见 §J 的 P0/P1 列（数值直接可比）。

## N. 下一包扩源需求（**仅需求，不实施**）

### C8-4B — NIGER（P0）要求

按**类别**提出（不发明具体源名；已存在者标注其 id）：

| 需求类别 | 理由（数值依据） |
|---|---|
| NIGER_SECURITY_DEFENCE（国防/内政/警察） | 当前无该角色源 ⇒ §F 类别表 MISSING |
| NIGER_HEALTH（卫生部/疾控/WHO 驻尼日尔） | 同上 |
| NIGER_OFFICIAL（政府/总统府/内政部公告） | 官方源数 11（含区域）偏低 |
| NIGER_LOCAL（省市级/早警） | 本地源 11 |
| SAHEL_REGIONAL（萨赫勒专题/跨境安全） | 区域源 31 |

### C8-4C — P1 国家要求

| 国家 | 主要缺口（按 §G 判定） | 需求类别 |
|---|---|---|
| 尼日利亚 | working(有公开条目) | NATIONAL/LOCAL/OFFICIAL/REGIONAL（按缺失项） |
| 贝宁 | produced_but_not_public(源有产出但未进入公开层：relevance 过滤/隔离/本地化) | NATIONAL/LOCAL/OFFICIAL/REGIONAL（按缺失项） |
| 莫桑比克 | produced_but_not_public(源有产出但未进入公开层：relevance 过滤/隔离/本地化) | NATIONAL/LOCAL/OFFICIAL/REGIONAL（按缺失项） |
| 南苏丹 | working(有公开条目) | NATIONAL/LOCAL/OFFICIAL/REGIONAL（按缺失项） |
| 埃塞俄比亚 | working(有公开条目) | NATIONAL/LOCAL/OFFICIAL/REGIONAL（按缺失项） |

### C8-4D — GLOBAL / AFRICA-WIDE / REGIONAL 要求

| 层 | 需求类别 |
|---|---|
| GLOBAL_TIER_1 | 通讯社（wire）、国际广播（非洲分台）、全球商业/财经媒体 |
| AFRICA_WIDE | 泛非新媒体 + 泛非官方（AU/UN Africa）+ 泛非人道/研究 |
| REGIONAL_AFRICA | SAHEL / LAKE_CHAD_BASIN / HORN / GREAT_LAKES / SOUTHERN / NORTH 专题源 |

## O. 验收自检

| 标准 | 结果 |
|---|---|
| 1 权威逻辑源清单已核对 | PASS（120/118/2，展开 802 = per_source 行数） |
| 2 enabled/disabled 已知 | PASS |
| 3 健康来自真实生产证据 | PASS（最近一轮逐源台账聚合） |
| 4 P0 尼日尔专章 | PASS（§F） |
| 5 P1 五国逐国缺口 | PASS（§G） |
| 6 乍得质量/重复 | PASS（§H） |
| 7 全球 Tier-1 基线 | PASS（§I） |
| 8 泛非基线 | PASS（§I） |
| 9 区域覆盖矩阵 | PASS（§I，9 区域） |
| 10 领域缺口 | PASS（§J） |
| 11 源数 ≠ 有效覆盖 | PASS（§K） |
| 12 未改变任何生产行为 | PASS（只读；工件不接入站点） |

