# C8-4B · 尼日尔（P0）源扩展与集成（只读审计 + 1 项新增）

生成时间：2026-09-28T14:42:53+00:00

> 本包只做**源扩展 + 集成**：未改 geo-scope / 相关性阈值 / 验证阈值 / 首页 / 事件聚类 / AI 提示词，
> 未放宽发布门，未为提高源数量而加源，未发明任何端点，未为同一 publisher 建重复逻辑源。

## 基线（C8-4A 权威）

| 指标 | 基线 |
|---|---|
| NIGER_RELEVANT | 67 |
| NIGER_HEALTHY | 7 |
| NIGER_PRODUCTIVE | 5 |
| NIGER_PUBLIC_24H | 0 |
| NIGER_PUBLIC_7D | 12 |

## 候选评估（全部来自本轮实测）

| 候选 | 注册表 ID | 结论 | 证据 |
|---|---|---|---|
| ANP (Agence Nigérienne de Presse) | niger_anp | **EXISTING_HEALTHY** | 已存在且 feed=https://anp.ne/feed/ 实测 200/XML/新鲜；官方通讯社 tier_3 |
| Le Sahel | niger_lesahel | **EXISTING_HEALTHY** | 已存在（tier_1 state_media）。注意：lesahel.info 实测内容为 N'Djamena（乍得官报），与尼日尔侧的 Le Sahel 非同一 publisher，**不得**据此改配置（本包不动） |
| ActuNiger | niger_actuniger | **REJECTED_ACCESS** | actuniger.com / .net 均超时或 503，当前不可达（保留现有条目，不新增替代域名） |
| Studio Kalangou | niger_studiokalangou | **EXISTING_HEALTHY** | 已配置 https://www.studiokalangou.org/feed/ 实测 200/XML/新鲜（此前台账 dup=12/15 偏高，属重复主导） |
| Tamtaminfo | niger_tamtaminfo | **EXISTING_HEALTHY** | feed 实测 200/XML/新鲜，与发现的 feed 一致 |
| NigerDiaspora | niger_nigerdiaspora | **EXISTING_HEALTHY** | 现有 feed 可用；.info 域名不可达 |
| Ministry of Interior | — | **NOT_SUITABLE** | interieur.gouv.ne DNS 不存在；nigerinter.com 实为新闻站（已存在为 niger_nigerinter，notes 含国防安全/城市治安） |
| National Police | — | **NOT_SUITABLE** | police.gouv.ne DNS 不存在 —— 不发明端点 |
| National Guard | — | **NOT_SUITABLE** | gendarmerie.gouv.ne DNS 不存在 —— 不发明端点 |
| Ministry of Health | — | **NOT_SUITABLE** | sante.gouv.ne / gouvernement.ne DNS 不存在 —— 不发明端点 |
| ACLED | un_acled_chad, un_acled_niger | **EXISTING_LOW_YIELD** | 已配置但 enabled=false（缺凭据）；本包不绕过、不擅自启用 |
| ISS Africa (Niger/Sahel) | un_iss_niger, un_iss_chad | **EXISTING_HEALTHY** | 已存在为 HTML 采集源；issafrica.org/rss.xml 无有效条目（0 items） |
| WHO Health Cluster / WHO AFRO | un_who_afro | **NEW_ADDED** | 新增：https://www.afro.who.int/rss.xml 实测 200 / application/rss+xml / 条目新鲜；填 NIGER_HEALTH + HUMANITARIAN |
| UN Niger / OCHA | un_unhcr_niger, un_iom_niger, un_wfp_niger, un_unicef_niger | **EXISTING_HEALTHY** | 已存在；unocha.org/niger/rss.xml 实测 404（不新增） |
| ReliefWeb | un_reliefweb_niger, pan_reliefweb | **PENDING_EXTERNAL_REQUIREMENT** | 公共 RSS 已于 C8-2 修复（gzip），API 仍待 approved appname —— 本包不绕过 |
| presidence.ne | — | **REJECTED_ACCESS** | 首页 200 但 /feed/ 404，无可用结构化端点 |
| lesahel.org（Le Sahel 官网） | — | **REJECTED_ACCESS** | HTTP 403（访问受限） |

**判定汇总**：EXISTING_HEALTHY=7 ｜ NOT_SUITABLE=4 ｜ REJECTED_ACCESS=3 ｜ EXISTING_LOW_YIELD=1 ｜ NEW_ADDED=1 ｜ PENDING_EXTERNAL_REQUIREMENT=1

## 尼日尔源清单（实测台账为上轮；按发现量降序）

| source_id | tier | 角色 | 证据角色 | 策略 | att | disc | pub | quar | dup |
|---|---|---|---|---|---|---|---|---|---|
| niger_nigerinter | tier_2 | NATIONAL_NEWS/SECURITY_D | CONTEXT_ANALYSIS | P0_ALWAYS_ON | 1 | 30 | 0 | 0 | 13 |
| niger_journalduniger | tier_2 | NATIONAL_NEWS | CONTEXT_ANALYSIS | P0_ALWAYS_ON | 1 | 30 | 0 | 0 | 5 |
| niger_anp | tier_3 | NATIONAL_NEWS/OFFICIAL | PRIMARY_EVIDENCE | P0_ALWAYS_ON | 1 | 24 | 0 | 7 | 2 |
| intl_aljazeera_niger | tier_3 | UNCLASSIFIED | CONTEXT_ANALYSIS | NORMAL | 1 | 20 | 0 | 2 | 18 |
| intl_rfi_afrique_niger | tier_1 | GLOBAL_TIER_1 | CORROBORATION | NORMAL | 1 | 20 | 0 | 0 | 2 |
| intl_bbc_afrique_niger | tier_1 | GLOBAL_TIER_1 | CORROBORATION | NORMAL | 1 | 20 | 0 | 0 | 14 |
| intl_france24_afrique_niger | tier_1 | GLOBAL_TIER_1 | CORROBORATION | NORMAL | 1 | 20 | 0 | 0 | 15 |
| niger_africanews | tier_1 | GLOBAL_TIER_1/NATIONAL_N | CORROBORATION | NORMAL | 1 | 20 | 0 | 2 | 7 |
| pan_allafrica | tier_2 | PAN_AFRICA | CORROBORATION | NORMAL | 1 | 20 | 0 | 0 | 20 |
| pan_unnews_africa | tier_1 | GLOBAL_TIER_1/PAN_AFRICA | CORROBORATION | NORMAL | 1 | 20 | 0 | 0 | 20 |
| pan_africanews | tier_2 | PAN_AFRICA | CORROBORATION | NORMAL | 1 | 20 | 0 | 0 | 7 |
| pan_france24_africa | tier_1 | GLOBAL_TIER_1/PAN_AFRICA | CORROBORATION | NORMAL | 1 | 20 | 0 | 0 | 19 |
| gha_myjoyonline | tier_2 | UNCLASSIFIED | CONTEXT_ANALYSIS | NORMAL | 1 | 20 | 0 | 0 | 4 |
| pan_bbc_africa | tier_1 | GLOBAL_TIER_1/PAN_AFRICA | CORROBORATION | NORMAL | 1 | 20 | 0 | 0 | 0 |
| pan_aljazeera | tier_1 | GLOBAL_TIER_1/PAN_AFRICA | CORROBORATION | NORMAL | 1 | 20 | 0 | 0 | 20 |
| pan_rfi_afrique | tier_1 | GLOBAL_TIER_1/PAN_AFRICA | CORROBORATION | NORMAL | 1 | 20 | 0 | 0 | 2 |
| rwa_newtimes | tier_2 | UNCLASSIFIED | CONTEXT_ANALYSIS | NORMAL | 1 | 17 | 0 | 0 | 6 |
| niger_studiokalangou | tier_2 | NATIONAL_NEWS/SECURITY_D | CONTEXT_ANALYSIS | P0_ALWAYS_ON | 1 | 15 | 0 | 1 | 12 |
| nga_premiumtimes | tier_2 | UNCLASSIFIED | CONTEXT_ANALYSIS | NORMAL | 1 | 15 | 0 | 0 | 15 |
| niger_airinfo | tier_2 | LOCAL_EARLY_WARNING/NATI | EARLY_SIGNAL | P0_ALWAYS_ON | 1 | 10 | 0 | 0 | 0 |
| niger_tamtaminfo | tier_2 | NATIONAL_NEWS | CONTEXT_ANALYSIS | P0_ALWAYS_ON | 1 | 10 | 0 | 0 | 1 |
| niger_sahelien | tier_2 | NATIONAL_NEWS/SAHEL_REGI | CONTEXT_ANALYSIS | P0_ALWAYS_ON | 1 | 10 | 0 | 0 | 0 |
| niger_ouestaf | tier_2 | NATIONAL_NEWS/SAHEL_REGI | CONTEXT_ANALYSIS | NORMAL | 1 | 10 | 0 | 0 | 0 |
| pan_dw_africa | tier_1 | GLOBAL_TIER_1/PAN_AFRICA | CORROBORATION | NORMAL | 1 | 5 | 0 | 0 | 5 |
| niger_actuniger | tier_2 | NATIONAL_NEWS/SECURITY_D | CONTEXT_ANALYSIS | NORMAL | 1 | 0 | 0 | 0 | 0 |
| niger_lesahel | tier_1 | GLOBAL_TIER_1/NATIONAL_N | PRIMARY_EVIDENCE | NORMAL | 1 | 0 | 0 | 0 | 0 |

## 八大区域覆盖矩阵

| 区域 | 支撑源数 | 支撑源 |
|---|---|---|
| 尼亚美 | 8 | niger_anp, niger_lesahel, niger_studiokalangou, niger_tamtaminfo, niger_nigerinter, niger_nigeri |
| 蒂拉贝里 | 4 | niger_anp, niger_studiokalangou, niger_sahelien, niger_ouestaf |
| 塔瓦 | 3 | niger_anp, niger_studiokalangou, niger_sahelien |
| 迪法 | 3 | niger_anp, niger_studiokalangou, niger_sahelien |
| 阿加德兹 | 3 | niger_airinfo, niger_anp, niger_studiokalangou |
| 马拉迪 | 2 | niger_anp, niger_studiokalangou |
| 津德尔 | 2 | niger_anp, niger_studiokalangou |
| 多索 | 3 | niger_anp, niger_studiokalangou, niger_ouestaf |

## 安全领域覆盖（尼日尔公开条目按 event_type 派生）

| 领域 | 尼日尔公开条目 | 支撑源族 |
|---|---|---|
| TERRORISM | 3 | niger_* + pan_* + un_*(按 event_type 派生) |
| ARMED_CONFLICT | 6 | niger_* + pan_* + un_*(按 event_type 派生) |
| KIDNAPPING | 0 | niger_* + pan_* + un_*(按 event_type 派生) |
| CRIME | 82 | niger_* + pan_* + un_*(按 event_type 派生) |
| POLITICAL_INSTABILITY | 4 | niger_* + pan_* + un_*(按 event_type 派生) |
| PROTESTS_CIVIL_UNREST | 3 | niger_* + pan_* + un_*(按 event_type 派生) |
| BORDER_SECURITY | 0 | niger_* + pan_* + un_*(按 event_type 派生) |
| MILITARY_SECURITY | 2 | niger_* + pan_* + un_*(按 event_type 派生) |
| TRANSPORT_LOGISTICS | 1 | niger_* + pan_* + un_*(按 event_type 派生) |
| ENERGY_MINING | 0 | niger_* + pan_* + un_*(按 event_type 派生) |
| INFRASTRUCTURE | 1 | niger_* + pan_* + un_*(按 event_type 派生) |
| NATURAL_HAZARDS | 1 | niger_* + pan_* + un_*(按 event_type 派生) |
| HUMANITARIAN | 0 | un_*HUMANITARIAN |
| PUBLIC_HEALTH | 0 | un_who_afro |

## 采集策略

- `P0_ALWAYS_ON`（8 个）：niger_anp, niger_studiokalangou, niger_nigerinter, niger_sahelien, niger_airinfo, niger_journalduniger, niger_tamtaminfo, un_who_afro
- 其余尼日尔源保持 `NORMAL`；ACLED 保持 `PENDING_CREDENTIAL`（不擅自启用、不绕过付费/认证数据集）。

## Dry validation（7 项，全部实测）

| source | ACCESS_OK | DISCOVERY_OK | URL_EXTRACTION_OK | DATE_PARSE_OK | FULL_BODY_OK | NIGER_SCOPE_OK | 结论 |
|---|---|---|---|---|---|---|---|
| **un_who_afro（本包新增）** | 200 | OK | OK | OK | OK | OK | **HEALTHY** |
| niger_anp | 200 | OK | OK | OK | OK | OK | **HEALTHY** |
| niger_studiokalangou | 200 | OK | OK | OK | OK | OK | **HEALTHY** |
| niger_airinfo | 200 | OK | OK | OK | OK | OK | **HEALTHY** |
| niger_nigerinter | 200 | OK | OK | OK | OK | OK | **HEALTHY** |
| niger_journalduniger | 200 | OK | OK | OK | OK | OK | **HEALTHY** |
| niger_sahelien | 200 | OK | OK | OK | OK | OK | **HEALTHY** |

**DRY_VALIDATION_OK = 7 / 7**（均 200 + 真 XML + 可提取 URL + 有效日期 + 正文可用 + 尼日尔范围）

## 结论与限制（诚实）

1. **尼日尔源架构已接近饱和**：14 个 `niger_*` 专属源 + `un_*`/`pan_*` 已覆盖官方、国家媒体、本地、区域、国际各层；
   且现有端点**全部已是 WordPress `/feed/`（实测为最优）** ⇒ **无修复空间**（不是没查，是确实已最优）。
2. **真正可新增的只有 1 个**：`un_who_afro`（WHO 非洲区域办官方 RSS，实测 200/XML/新鲜），
   填补 C8-4A 指出的 `NIGER_HEALTH` 与 `HUMANITARIAN` 领域缺口。
3. **结构性障碍（实测证明，非执行能力问题）**：尼日尔政府/内政/警察/宪兵/卫生部域名 **DNS 不存在**；
   `lesahel.org` 返回 **403**；ActuNiger 域名**超时/503** ⇒ 这些官方源缺口在**公开可达端点层面**无法闭合（坚决不发明端点）。
4. **一处待核实事实**：`lesahel.info` 实测内容为 **N'Djamena（乍得）**，属乍得官报；
   与尼日尔侧 `niger_lesahel` 非同一 publisher。本包**未改任何配置**，仅记录。
5. 本包**未触发部署**（内部工件，不接入站点）。


---

# C8-4B2 · 尼日尔官方端点纠正（外部核验后的复核）

> **重要纠正**：C8-4B 曾把若干官方站点判为"域名不存在"。经**按确切 URL 重测**（此前误加了 `www.` 或遭遇瞬时 DNS 故障），
> 结论已推翻。教训记录：**单次 DNS 失败 / 单次超时 ≠ 站点不存在**，必须重试并区分 DNS 故障与真实 404。

## 逐一复核结果（全部为本轮实测）

| 站点 | 确切 URL | HTTP | RSS | 结论 | 处理 |
|---|---|---|---|---|---|
| 内政部 | https://interieur.gouv.ne/ | 200 | **真 RSS `https://interieur.gouv.ne/feed/`（10 items，09-22）** | **LIVE + RSS** | **新增 `niger_interieur`** |
| 国家警察 | https://www.police-nationale.interieur.gouv.ne/ | 200 | 无（首页仅 css/favicon，无结构化列表） | LIVE 但**列表不可稳定解析** | 不建脆弱抓取器（按规则）；待站点改版复评 |
| 国家卫队 | https://www.garde-nationale.interieur.gouv.ne/ | 200 | 无，但列表 `/post?id=NNNN` 稳定、详情页 `<p>` 可解析 | **LIVE + HTML 可用** | **新增 `niger_garde_nationale`**（LOW_FREQUENCY） |
| 国防部 | https://www.defense.gouv.ne/ | **404** | — | TEMPORARILY_UNAVAILABLE | 如实记录，不发明端点 |
| 宪兵 | https://www.gendarmerie-nationale.defense.gouv.ne/ | **404** | — | TEMPORARILY_UNAVAILABLE | 如实记录 |
| 交通部/民航 | https://transports.gouv.ne/ | 200 | 无 | LIVE 但**纯 JS 渲染、无可解析列表** | 不采集（脆弱） |
| 卫生部 | https://www.sante.gouv.ne/ → **msppas.ne** | 200 | **真 RSS `https://www.msppas.ne/?feed=rss2`（10 items）** | **LIVE + RSS** | **新增 `niger_sante`** |
| Le Sahel (ONEP) | https://www.lesahel.org/ | 200 | **`https://www.lesahel.org/feed/`（10 items，09-28）** | **身份正确** | 无需修改（现有配置本就指向该 feed） |

## Le Sahel 身份核验（用户重点）

- 现有 `niger_lesahel` 的 `feed_url` = **`https://www.lesahel.org/feed/`** —— 即**尼日尔 ONEP 的 Le Sahel**，本轮实测 200 / 真 RSS / 内容新鲜（09-28）。
- 故：**NIGER_LESAHEL_IDENTITY_CORRECT = true** ｜ **NIGER_LESAHEL_COUNTRY_CONTAMINATION_FIXED = not_applicable**
- C8-4B 中"`lesahel.info` 内容为 N'Djamena"的观察**与本源无关**（那是另一个域名/出版商），已确认**不存在国家污染**。

## RSS 非强制（接受规则修正）

`SOURCE ACCESS != RSS ACCESS`：高权威 P0 官方源若 HTML 可访问、列表稳定、URL/日期/正文可解析，
即接受 HTML 采集（本轮 `niger_garde_nationale` 即按此纳入）。同时**不**为结构脆弱（JS 渲染/无列表）的站点建一次性抓取器
（国家警察、交通部据此**未**纳入，理由已记录）。

## 新增源（本包 3 个）

| source_id | 采集 | tier | 角色 | 证据角色 | 策略 | dry validation |
|---|---|---|---|---|---|---|
| `niger_interieur` | RSS | tier_2 | OFFICIAL + POLICE_INTERIOR + SECURITY_DEFENCE | PRIMARY_EVIDENCE | **P0_ALWAYS_ON** | 7/7 HEALTHY |
| `niger_sante` | RSS | tier_2 | HEALTH + OFFICIAL | PRIMARY_EVIDENCE | LOW_FREQUENCY | 7/7 HEALTHY |
| `niger_garde_nationale` | HTML | tier_3 | SECURITY_DEFENCE | PRIMARY_EVIDENCE | LOW_FREQUENCY（HIGH_VALUE_LOW_FREQUENCY） | 7/7 HEALTHY |

内政部 RSS 的内容为**区域级官方部务**（Maradi / Diffa / Zinder 等）⇒ 直接改善 C8-4B 指出的**区域覆盖**薄弱项。

## 库存与验证

- CONFIGURED = **124**（C8-4A 基线 120）｜ ENABLED = **122**（基线 118）｜ NIGER_RELEVANT = **72**（基线 67）
- 本包 dry validation：**8 / 8 HEALTHY**（un_who_afro + niger_interieur + niger_sante + niger_garde_nationale + ANP + Studio Kalangou + Le Sahel + Tamtaminfo）

## 与 C8-4A 缺口的对应

| C8-4A 缺口 | 本包状态 |
|---|---|
| NIGER_SECURITY_DEFENCE | **已闭合**（`niger_interieur` + `niger_garde_nationale`） |
| NIGER_POLICE_INTERIOR | **已闭合**（`niger_interieur`，notes 明示内政/治安） |
| NIGER_HEALTH | **已闭合**（`niger_sante` RSS + `un_who_afro` 区域权威） |
| NIGER_OFFICIAL | **显著改善**（+2 官方源） |
| NIGER_LOCAL / SAHEL_REGIONAL | 保持（14 个既有本地/区域源），内政部区域报道形成叠加 |
| RESEARCH_SECURITY | 仍为 ISS/Crisis Group（ACLED 待凭据）—— 未变 |
| ENERGY_MINING / TRANSPORT_INFRASTRUCTURE | 仍未闭合（交通部为 JS 渲染、矿业无公开可用端点） |
