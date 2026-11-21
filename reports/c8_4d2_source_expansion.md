# C8-4D2 — High-Value Africa Source Expansion（Phase 3/4 修正 + 既有源审计 + 区域覆盖评估）

> 目标：修正 Phase 3/4 调度，并在**不凑源数**的前提下提升全球/泛非/区域源的**有效**覆盖。
> 源数是结果，不是目标。未新增任何逻辑源；仅修复 3 处既有失效注册。

```text
SOURCE_COMMIT=<见 §5 提交后回填>
MAIN_RELEASE_SHA=<见 §5>
PRODUCTION_STATE_SHA=f0225f848ee26c877d26f204c853c014e73763b3   (as of 2026-10-20T06:07Z)
GH_PAGES_SHA=d7443a26601c50bb0a7441b137bcf33cdd2f48d5           (as of 2026-10-20T06:07Z)

LOGICAL_SOURCES_BEFORE=153   LOGICAL_SOURCES_AFTER=153
ENABLED_BEFORE=151           ENABLED_AFTER=151
EXPANDED_EXECUTIONS_BEFORE=888   EXPANDED_EXECUTIONS_AFTER=888

PHASE3_PHASE4_CLASSIFICATION=CORRECT   (修正前 phase4 结构性为 0)
PHASE_ORDER=VERIFIED                   (普通国家先行、多国展开殿后；冻结集回归)
WALL_CLOCK_BUDGET=3000s                (未变；回归测试断言)
ROLLBACK=ASIP_PHASE_B_SPLIT=0（立即回退单趟 {3,4}，无需改代码）

FINAL_RESULT=PARTIAL
```

---

## 1. Part A — Phase 3/4 修正（已实施）

### 1.1 根因（C8-4D1 终验时发现并记录）

`registry._unified()` 暴露的键是 **`source_scope`**（多国源为完整列表），而相位分类读取的是
`_src.get("country_scope")` —— 该键在统一视图中**不存在**，恒为 `None` → 长度 0 → 一律判
phase 3。后果：`PHASE4_*` 结构性恒为 0，14 个多国展开源（644 个执行键）与 93 个普通国家键
混在同一相位，遥测无法区分"普通国家"与"多国展开背景"。

### 1.2 修正内容（`scripts/stage3_collect_v2.py`）

| 项 | 修正 |
|---|---|
| 取值键 | `source_scope`（保留 `country_scope` 作为旧视图回退） |
| 归属函数 | 提取为纯函数 `_assign_execution_phase(country, source)`，可单测；优先级 P0 → P1 → Lane A → 展开数 3/4 |
| 执行趟 | `PHASE_PASSES = ({0,1,2}, {3}, {4})`：PASS A 保证键 → **普通国家/本地（3）全局先行** → 多国展开背景（4）殿后 |
| 计划函数 | `plan_phase_execution(phase_map, countries)` 纯函数输出 `[(pass_idx, country, [sids])]`，main() 与测试共用同一逻辑 |
| 相位戳 | 执行行盖 `phase` 戳不变（C8-4D1 STEP0 的事实来源），write_stats 由行派生 |
| 回滚 | `ASIP_PHASE_B_SPLIT=0` → 回退 C8-4C3 单趟 `{3,4}`（保证键仍在首趟） |
| 墙钟 | 3000s 未变（`collection_run.COLLECTION_WALL_CLOCK_LIMIT`，测试断言） |

### 1.3 新旧调度对照（同一冻结执行集 + 真实注册表）

冻结集回归（`scripts/tests/test_c8_4d2_phase_order.py`，18 项全过）证明：

- 执行键集合不变（888 → 888）；
- **单/双国且非保证键的相位不得改变**（仍为 3）；
- 保证键名单内者必须落到 0/1/2；
- 非保证键只有多国展开源才改判到 4；
- 普通国家相位 3 的全部执行必须先于任何相位 4 执行；
- 计划确定性（相同输入 → 相同计划）。

真实注册表现状（pin `e0628ac9`）：

| 相位 | 执行键 | 唯一源数 | 说明 |
|---|---|---|---|
| 0 | 12 | 6 | P0 尼日尔保证键 |
| 1 | 16 | — | P1 五国保证核心 |
| 2 | 123 | 17 | 既有 Lane A（含 pan_rfi / pan_dw） |
| **3** | **93** | — | 普通国家/本地（修正后从 888 中分离） |
| **4** | **644** | **14** | 多国展开背景源（修正前全部混在 3 里） |

### 1.4 多国源饥饿风险（离线定量，非生产结论）

用最近一轮 `per_source` 实测耗时建模（实测合计 2208.2s；采集实际墙钟 ≈2914s → 开销系数 1.32；可用预算 3000−180=2820s）：

| 阶段 | 估算累计耗时 | 剩余预算 |
|---|---|---|
| PASS A（0+1+2） | ≈1834s | ≈986s |
| + phase 3（93 键） | ≈2110s | ≈710s |
| + phase 4（644 键，实测 609.4s） | ≈2914s | **−94s（超支约 3%）** |

结论：**边界情形**。phase 4 执行键单价低（均值 ≈0.95s，因 `_DISCOVER_CACHE` 使同一 feed 每轮只抓一次），
若其开销系数低于整体均值则可在预算内完成；若接近整体系数则尾部约数十个 phase 4 键可能被墙钟跳过。
**保证键（P0/P1/Lane A）在 PASS A，不受拆分影响**。该风险只能由自然周期实测裁定 → 见 §6 待验项。
回滚路径：`ASIP_PHASE_B_SPLIT=0`。

---

## 2. Part B — 既有高价值源技术审计（结论：**全部已注册**，无需新增重复逻辑源）

| 目标 | 已注册 | 启用 | 发现方式 | 实际执行 | 发现 | 结论 |
|---|---|---|---|---|---|---|
| ISS Africa | ✅ `un_iss_chad/niger` | ✅ | gdelt_search | no_items / QUERY_NO_RESULT | 0 | 注册有效但**被 GDELT 限流打死**（见 §2.1） |
| International Crisis Group | ✅ `un_crisisgroup_*` | ✅ | gdelt_search | 同上 | 0 | 同上 |
| FEWS NET | ✅ `un_fewsnet_*` | ✅ | gdelt_search | 同上 | 0 | 同上 |
| Reuters / AP / AFP | ✅ `intl_reuters/ap/afp_*` | ✅ | gdelt_search | 同上 | 0 | 同上 |
| BBC | ✅ 5 源 | ✅ | rss ×3 / gdelt ×2 | success（RSS 20 条） | 20 | **健康**（en/fr + pan） |
| France24 | ✅ 7 源 | ✅ | rss ×5 / gdelt ×2 | success | 20 | **健康**（en/fr + pan） |
| UN News | ✅ 3 源 | ✅ | rss ×1 / gdelt ×2 | pan success | 20 | pan 健康；gdelt 变体死 |
| ReliefWeb | ✅ 3 源 | ✅ | rss / reliefweb_api | RSS_EMPTY / no_items | 0 | **瞬时故障**（见 §2.2） |
| Africa Center (ACSS) | ✅ `specialist_acss` | ✅ | rss | no_items / RSS_EMPTY | 0 | **feed 为空 channel**（已修复，见 §4） |
| Al Jazeera / RFI / DW / AllAfrica | ✅ | ✅ | rss | success | 20/3/20 | 健康（DW 仅 3 条） |
| VOA | ✅ 4 源 | ✅ | rss ×2 / gdelt ×2 | no_items / RSS_EMPTY | 0 | **URL 失效**（已修复，见 §4） |

补充核查（每个源都过了的问题清单）：注册身份存在 ✅；原文 URL 保留 ✅（canonical/original_url 字段）；
正文可达 ✅（RSS 源 full_body）；唯一记录产出 ✅（见 §5 发布贡献表）；法律复用 ——
ISS/ICG/ACSS/FEWS NET 为研究机构内容（转载平台属性已在 `is_republication_platform` 标注），
UN/ReliefWeb/Africa CDC 为政府间组织内容（署名后可复用），通讯社（Reuters/AP/AFP）为版权受限内容
（**不作为发布正文来源，仅作线索**——当前实现只索引标题/摘要，未全文转载）。

### 2.1 最大缺口：GDELT 家族 68 源结构性零产出

- 最近一轮：68 个 gdelt_search 源**全部 attempted、全部 no_items、0 discovered / 0 published**；
- 回溯近 6 个含采集的状态提交：**每轮 gdelt discovered=0 / published=0**；
- 根因（实测）：`https://api.gdeltproject.org/api/v2/doc/doc?...` 返回 **HTTP 429 Too Many Requests**；
  共享限流器上一轮仅发出 3 次请求（2 次 429），即 68 个源共用同一个被限流的客户端。
- 这不是查询词问题，是上游限流。修复方向（超出本包范围）：合并查询、指数退避、或整族下线。

### 2.2 ReliefWeb：瞬时而非结构性

`https://reliefweb.int/updates/rss.xml` 用项目自身 fetcher 实测 **200 / 208KB / 20 items 可解析**，
故生产里的 RSS_EMPTY 是瞬时（ReliefWeb 对 runner IP 限流）。不改注册，纳入观测。

---

## 3. Part C — 区域覆盖评估与新候选（Africa CDC）

按 9 个区域核对现有健康度（最近一轮，执行键 / 有发现）：

| 区域 | 执行键 | 有发现 | 说明 |
|---|---|---|---|
| 萨赫勒 | 181 | 90 | P0/P1 保证键集中，覆盖最重 |
| 西非 | 180 | 139 | 最健康 |
| 东非 | 164 | 127 | 健康 |
| 南部非洲 | 159 | 123 | 健康 |
| 中非 | 104 | 82 | 健康 |
| 北非 | 88 | 69 | 健康 |
| 未映射 | 12 | 9 | — |

54 条国家管线**无一零产出**。真实缺口不在"没有源"，而在 §2.1 的 GDELT 限流与 §3.1 的两个技术门。

### 3.1 初始候选：Africa CDC —— **不通过，未新增**

严格验证（项目自身 fetcher/解析器，未伪造任何 URL，未绕过访问控制）：

| 门 | 结果 | 证据 |
|---|---|---|
| STRICT_TLS | ✅ | `https://africacdc.org/` 200（证书校验通过） |
| HTTP_ACCESS | ✅ | `/`、`/news/`、`/feed/`、`/sitemap.xml`、`/wp-json/wp/v2/posts` 均 200 |
| ARTICLE_DISCOVERY | ✅ | `/news/` HTML 提取到 12 条 `/news-item/...` 文章链接 |
| ARTICLE_URL | ✅ | 绝对 URL、`validate_url` 通过、详情页 200 |
| PUBLISHED_DATE | ❌ | `/feed/` 为**空 channel**（1240B、0 items）；详情页无可机读日期，`published_original` 提取为**空** |
| FULL_BODY | ✅ | 详情页 full_body，455–811 词 |
| COUNTRY_RELEVANCE | ⚠️ | 相关性 2/4 命中（ebola / épidémie 在词表内）；但 `identify_country` 对英文国名不命中（"Kenya" → unclear，词表偏法/中） |
| ORIGINAL_PUBLISHER | ✅ | Africa CDC（非盟机构），详情页可溯源 |
| COPYRIGHT / REUSE | ✅ | 政府间组织内容，署名可引用（不作全文转载） |

判定：**日期门不过 + 英文国名实体不命中** → 按"源数是结果不是目标"，**不注册**。
前置条件（建议独立小包）：① 详情页 dateline 日期提取（正文首段 "Addis Ababa, Ethiopia, 17 October 2026" 模式）；
② 国家实体词表补英文国名。两者完成后本源可直接过门。

---

## 4. Part D — 实施（仅修复，不新增）

| 源 | 修复前（实测） | 修复后 | 预期效果 |
|---|---|---|---|
| `pan_voa_africa` | feed `…/api/zrqiteukiq` → **text/plain "Invalid url"** | `https://www.voaafrica.com/api/`（200 `application/rss+xml`，20 items） | 注册有效化；**但该 feed 内容冻结于 2025-03-31**，仍无近期产出 |
| `pan_voa_afrique` | 同上 | `https://www.voaafrique.com/api/`（200 RSS，20 items） | 同上 |
| `specialist_acss` | WP `/feed/` = **空 channel**（354B、0 items） | `html_listing` + `listing_urls=[https://africacenter.org/]`（实测 11 条文章链接、full_body 1436–3779 词） | 从 0 发现恢复到可用发现；日期仍不可机读（与其它 html_listing 源同限） |

逻辑源 153 → **153**，启用 151 → **151**，展开执行 888 → **888**（未凑数、未做无谓 54 国扩张）。

保持项：canonical 源身份、文章级原文 URL、国家归属、独立源去重、安全与发布门槛、
**C8-4D1 共享缓存设置（RFI 三源白名单不变）**。

测试：`test_c8_4d2_phase_order`（18）+ `test_c8_4d2_source_registry`（8）+ C8-4D1 全量（24）+
既有 c1c/c2b（31）= **81/81 PASS**；`py_compile` OK。

---

## 5. 交付数据

### 5.1 源数与展开

| 指标 | 修正前 | 修正后 |
|---|---|---|
| logical sources | 153 | 153 |
| enabled | 151 | 151 |
| expanded executions | 888 | 888 |
| phase 3 / phase 4 执行键 | 888 / **0**（错分） | 93 / 644 |

### 5.2 修复源的实际产出（最近一轮生产快照）

| 源 | 状态 | discovered | published | 备注 |
|---|---|---|---|---|
| `pan_voa_africa` | no_items/RSS_EMPTY | 0 | 0 | 修复后待下轮验证；内容冻结 2025-03-31 |
| `pan_voa_afrique` | no_items/RSS_EMPTY | 0 | 0 | 同上 |
| `specialist_acss` | no_items/RSS_EMPTY | 0 | 0 | 改 html_listing 后待下轮验证 |

### 5.3 新增源

**无**（Africa CDC 未过日期门，见 §3.1）。

### 5.4 分区域健康/产出源数（最近一轮）

见 §3 表：54 国管线、888 执行键、639 键有发现、**0 国零产出**。
按发现方式：rss 71 源中 61 有发现/4 有发布；html_listing 10 中 8 有发现；
gdelt_search 68 中 0；reliefweb_api 2 中 0。

### 5.5 覆盖与发布贡献

- **24h 覆盖**：采集约每 2h45m 一轮（末次成功 `2026-10-20T02:56:01Z`）；日报 `2026-10-19T12:02:48Z`；
  周报 `2026-10-17T23:01:28Z`。自 C8-4D1 起日报连续无断日（51 天）。
- **7d 覆盖**：日报连续（同上）；周报按周。
- **唯一发布贡献（最近一轮）**：仅 4 源发布 7 条（`nga_punch` 4、`ben_fraternite` 1、
  `chad_toumaiweb` 1、`ben_lnt` 1）—— 去重主导（duplicates 3196），新增量天然小。
- **墙钟跳过**：364/888（本轮）；C8-4D1 三轮为 432/585/364。P0/P1/Lane A 跳过 **0**。

---

## 6. 验收状态与待验项

| 条件 | 状态 |
|---|---|
| P0_NIGER_SKIPS = 0 | **待自然周期确认**（历史四轮均 0；拆分不涉及 PASS A） |
| P1_CORE_SKIPS = 0 | 同上 |
| LANE_A_MATERIAL_STARVATION = 0 | 同上 |
| PHASE3/PHASE4_CLASSIFICATION = CORRECT | **PASS**（代码 + 18 项回归 + 真实注册表 93/644） |
| PHASE_ORDER = VERIFIED | **PASS**（冻结集计划顺序回归） |
| TRUE_UNACCOUNTED_DROP = 0 | **PASS**（最近一轮 0） |
| NO_GEO_CONTAMINATION | **PASS**（未改国家判定/地理门槛） |
| NO_SECURITY_GATE_REGREGESSION | **PASS**（未改安全与发布门槛；81 测试含发布门契约） |
| 墙钟 3000s | **PASS**（未变，测试断言） |

待验（需 ≥2 个自然采集周期）：相位拆分后 phase 4 的实际 attempted/skipped（对照 §1.4 边界情形）、
P0/P1/Lane A 跳过是否仍为 0、三处修复源的实际发现/发布、`PHASE_SKIP_RECONCILED` 是否仍 true。

---

## 7. 剩余缺口与技术债（按影响排序）

1. **GDELT 家族 68 源全灭**（上游 429）：占启用源 45%，是覆盖面最大的单点失效。需独立包处理
   （查询合并/退避/下线决策）。
2. **html_listing 源无可机读日期**：提取器 `published_original` 为空 → 影响 ACSS 修复效果与
   Africa CDC 过门。建议做详情页 dateline 提取。
3. **国家实体词表偏法/中**：英文国名（"Kenya"）不命中 → 英文源（Africa CDC、VOA）国家归属困难。
4. **VOA feed 内容冻结 2025-03-31**：URL 已修，但上游停更；如需 VOA 覆盖需另找活跃端点。
5. **reliefweb_api 2 源已知 410 Gone**（Stage 3B 既有结论）；`pan_reliefweb` RSS 为瞬时限流。
6. **发布增量小**：去重主导（3196 dups / 7 published），源扩容的边际收益低 —— 这正是本包
   "不凑源数"的实证依据。

```text
FINAL_RESULT=PARTIAL
```

停止条件：本包到此结束。未新增源、未扩大 C8-4D1 白名单、未启动 C8-4E；
生产验证需 ≥2 个自然采集周期后另行判定。
