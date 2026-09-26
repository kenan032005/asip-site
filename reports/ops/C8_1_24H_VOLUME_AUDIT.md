# C8-1 · 24h 情报量漏斗审计

生成时间：2026-09-26T13:20:23+00:00 ｜ data_as_of：2026-09-26T11:48:49+00:00 ｜ 采集轮：20260926T110622+0800_pznfs9

> 口径：逐源台账为**最近一轮**采集；24h 视窗指标由 `news_stream.last_seen_at` 派生。

## 1. 漏斗（PHASE 1）

| 阶段 | 计数 |
|---|---|
| CONFIGURED_SOURCES | 103 |
| ENABLED_SOURCES | 101 |
| SOURCES_ATTEMPTED_24H | 118 |
| SOURCES_HTTP_OK | 18 |
| SOURCES_PRODUCTIVE | 18 |
| SOURCES_ZERO_OUTPUT | 100 |
| SOURCES_FAILED | 100 |
| SOURCES_BLOCKED_BY_EXTERNAL | 36 |
| SOURCES_NO_OUTPUT_NOT_BLOCKED | 64 |
| RAW_ITEMS_DISCOVERED | 273 |
| RAW_ITEMS_FETCHED | 254 |
| DUPLICATES_AT_COLLECT | 40 |
| QUARANTINED_AT_COLLECT | 30 |
| ARTICLES_PERSISTED_NEW | 3 |
| ITEMS_WITH_VALID_TIME_7D | 62 |
| ITEMS_WITH_NO_TIME | 0 |
| ITEMS_IN_24H_WINDOW | 9 |
| MULTI_SOURCE_ITEMS_24H | 0 |
| SINGLE_SOURCE_ITEMS_24H | 9 |
| LOCALIZED_ITEMS_24H | 9 |
| PUBLIC_ELIGIBLE_SIGNALS | 30 |
| UNIQUE_DEVELOPMENTS | 59 |
| VERIFIED_MULTI_SOURCE_EVENTS_24H | 0 |
| HOMEPAGE_24H_VISIBLE | 9 |

## 2. 信息消失点（PHASE 2）

| 原因 | 计数 |
|---|---|
| HTTP_429 | 35 |
| PARSE_ERROR | 38 |
| RSS_EMPTY | 5 |
| NO_ITEMS | 26 |
| DATE_PARSE_FAIL | 1 |
| SECURITY_FILTER_REJECT | 30 |
| DUPLICATE_EXACT | 40 |
| OTHER | 34 |

运行期原因明细：

- WALL_CLOCK_LIMIT_REACHED = 33（预算截断，源未执行）
- HTTP_429 = 35
- QUERY_NO_RESULT = 26
- OK_PRODUCTIVE = 18

## 3. 产出分类（PHASE 3 汇总）

| 分类 | 源数 |
|---|---|
| BROKEN | 99 |
| HIGH_YIELD | 9 |
| MEDIUM_YIELD | 9 |
| ACCESS_LIMITED | 1 |

### 高产源（按已接受条数）

| source_id | name | tier | scope | discovered | accepted | quarantined | dup | class |
|---|---|---|---|---|---|---|---|---|
| chad_alwihda | Alwihda Info | tier_2 | ['乍得'] | 15 | 1 | 2 | 1 | HIGH_YIELD |
| chad_tchadinfos | Tchadinfos | tier_2 | ['乍得'] | 13 | 1 | 3 | 1 | MEDIUM_YIELD |
| chad_lepaystchad | Le Pays Tchad | tier_2 | ['乍得'] | 10 | 1 | 0 | 1 | MEDIUM_YIELD |
| chad_journaldutchad | Journal du Tchad | tier_2 | ['乍得'] | 24 | 0 | 0 | 7 | HIGH_YIELD |
| drc_radiookapi | Radio Okapi |  | 刚果（金） | 20 | 0 | 0 | 1 | HIGH_YIELD |
| intl_aljazeera_chad | Al Jazeera（乍得） | tier_3 | ['乍得'] | 20 | 0 | 15 | 0 | HIGH_YIELD |
| intl_aljazeera_niger | Al Jazeera（尼日尔） | tier_3 | ['尼日尔'] | 20 | 0 | 1 | 19 | HIGH_YIELD |
| intl_bbc_afrique_chad | BBC Afrique (Chad) | tier_1 | ['乍得'] | 20 | 0 | 2 | 0 | HIGH_YIELD |
| intl_france24_afrique_chad | France24 Afrique (Chad) | tier_1 | ['乍得'] | 20 | 0 | 0 | 0 | HIGH_YIELD |
| intl_rfi_afrique_chad | RFI Afrique (Chad) | tier_1 | ['乍得'] | 20 | 0 | 4 | 0 | HIGH_YIELD |
| pan_rfi_afrique | RFI Afrique |  | 乍得 | 20 | 0 | 0 | 0 | HIGH_YIELD |
| ssd_radiotamazuj | Radio Tamazuj |  | 南苏丹 | 14 | 0 | 0 | 3 | MEDIUM_YIELD |
| chad_lendjampost | Le N'Djam Post | tier_2 | ['乍得'] | 10 | 0 | 0 | 0 | MEDIUM_YIELD |
| chad_portail | 乍得复兴门户 | tier_3 | ['乍得'] | 10 | 0 | 1 | 2 | MEDIUM_YIELD |
| chad_tachad | Tachad.com | tier_2 | ['乍得'] | 10 | 0 | 1 | 1 | MEDIUM_YIELD |
| chad_tchadone | Tchad One | tier_3 | ['乍得'] | 10 | 0 | 0 | 4 | MEDIUM_YIELD |
| chad_toumaiweb | Toumaï Web Médias | tier_2 | ['乍得'] | 10 | 0 | 1 | 0 | MEDIUM_YIELD |
| pan_dw_africa | DW Africa |  | 乍得 | 7 | 0 | 0 | 0 | MEDIUM_YIELD |

### 零产出 / 失败源（前 18）

| source_id | name | status | reason | class |
|---|---|---|---|---|
| chad_presidence | 乍得总统府 | fail | HTTP_403 | ACCESS_LIMITED |
| cn_cctv_chad | 央视新闻（乍得） | fail | HTTP_429 | BROKEN |
| cn_cctv_niger | 央视新闻（尼日尔） | fail | WALL_CLOCK_LIMIT_REACHED | BROKEN |
| cn_cgtn_chad | CGTN Africa（乍得） | fail | HTTP_429 | BROKEN |
| cn_cgtn_niger | CGTN Africa（尼日尔） | fail | WALL_CLOCK_LIMIT_REACHED | BROKEN |
| cn_chinadaily_chad | 中国日报（乍得） | fail | HTTP_429 | BROKEN |
| cn_chinadaily_niger | 中国日报（尼日尔） | fail | WALL_CLOCK_LIMIT_REACHED | BROKEN |
| cn_chinanews_chad | 中国新闻网（乍得） | fail | HTTP_429 | BROKEN |
| cn_chinanews_niger | 中国新闻网（尼日尔） | fail | WALL_CLOCK_LIMIT_REACHED | BROKEN |
| cn_emb_chad_chad | 中国驻乍得使馆（乍得） | fail | HTTP_429 | BROKEN |
| cn_emb_chad_niger | 中国驻乍得使馆（尼日尔） | fail | WALL_CLOCK_LIMIT_REACHED | BROKEN |
| cn_emb_niger_chad | 中国驻尼日尔使馆（乍得） | fail | HTTP_429 | BROKEN |
| cn_emb_niger_niger | 中国驻尼日尔使馆（尼日尔） | fail | WALL_CLOCK_LIMIT_REACHED | BROKEN |
| cn_mfa_chad | 中国外交部（乍得） | fail | HTTP_429 | BROKEN |
| cn_mfa_niger | 中国外交部（尼日尔） | fail | HTTP_429 | BROKEN |
| cn_people_chad | 人民网（乍得） | fail | HTTP_429 | BROKEN |
| cn_people_niger | 人民网（尼日尔） | fail | WALL_CLOCK_LIMIT_REACHED | BROKEN |
| gha_myjoyonline | MyJoyOnline | fail | WALL_CLOCK_LIMIT_REACHED | BROKEN |

## 4. 24h 国家覆盖（PHASE 17 基线）

- ACTIVE_COUNTRIES_24H = 2 ｜ ACTIVE_COUNTRIES_7D = 3 ｜ COUNTRY_UNRESOLVED_24H = 0
- 24h 前十国家：乍得=8, 南苏丹=1

## 5. 阻塞项（不计入 C8-1 失败）

- RELIEFWEB_STATUS = PENDING_APPROVED_APPNAME
- ACLED = CREDENTIAL_REQUIRED
- REUTERS = metadata_only_via_gdelt
- AP = verification_only
