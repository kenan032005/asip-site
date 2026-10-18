# C8-4D1 — Shared-Feed Reuse and Collection Efficiency

合并报告（Gate A 确定性缺陷修复 + Gate B 共享请求复用）。只读审计基线 + 单一工程包，
未新增信源、未改 AI prompt/DeepSeek 行为、未放宽地理/安全/准入规则。

生成时间：2026-10-18（BJT）· 分支：`feature/asip-c8-4d1-shared-feed` · 基线 SHA：`e5ab2fbe`

---

## 0. 关键字段（可机读）

```
SOURCE_COMMIT=e0628ac99a3230dca29b5368e7379307e0b6ec48
MAIN_RELEASE_SHA=c2c48d12175489b256a9914d74bdfad7b66f9bfc   (release: pin C8-4D1 (e0628ac9))
PRODUCTION_STATE_SHA=c64d70399b371643f75cc06c3384461e0f6e30c5   (as of 2026-10-18T17:21Z)
GH_PAGES_SHA=ec6eb48f335e03912b4cdfcfa3c2297087b4cdbd         (as of 2026-10-18T17:21Z)

BASELINE_LOGICAL_SOURCES=153
FINAL_LOGICAL_SOURCES=153
BASELINE_ENABLED_SOURCES=151
FINAL_ENABLED_SOURCES=151
BASELINE_EXPANDED_EXECUTIONS=888
FINAL_EXPANDED_EXECUTIONS=888

MULTI_COUNTRY_SOURCES_AUDITED=16
STATIC_FEEDS_CONFIRMED=16
COUNTRY_DEPENDENT_FEEDS_CONFIRMED=0
SHARED_FEED_GROUPS=5
SHARED_FEED_SOURCE_IDS=12
SOURCES_REUSE_ENABLED=0        (生产 flag 仍为 OFF；canary 待仓库变量开启)

HTTP_REQUESTS_BEFORE=12        (5 shared feeds × 各自 source_id 执行，真实网络)
HTTP_REQUESTS_AFTER=5
MEASURED_REQUEST_SAVINGS=7     (58.3%)
HTTP_TIME_BEFORE=9.89
HTTP_TIME_AFTER=2.27
CACHE_HITS=7
CACHE_MISSES=5
CACHE_BYTES=162729
CACHE_TTL_SECONDS=600

P0_SKIPS=PENDING               (默认关闭周期尚未到达：下一次 collection-due = 2026-10-18T18:05Z 起)
P1_SKIPS=PENDING
LANE_A_SKIPS=PENDING

GEO_EQUIVALENCE=PASS
ARTICLE_EQUIVALENCE=PASS
PUBLICATION_GATE_PRESERVED=PASS

BEN_WEBTV_FIX=PASS
NGA_NRC_FIX=PASS
PHASE_TELEMETRY_FIX=PASS       (代码+回归测试；生产首轮实证待观察)
METRIC_NAMING_FIX=PASS
ROLLBACK_TESTED=PASS           (flag=0 时行为等价于 C8-4C4；默认关闭路径有测试)

GATE_A_FIX=PASS
PHASE_TELEMETRY=PASS
DEFAULT_OFF_RUN=PENDING

CANARY_ALLOWLIST=intl_rfi_afrique_chad,intl_rfi_afrique_niger,pan_rfi_afrique
CANARY_ALLOWLIST_VERIFIED=YES  (三 ID 均存在于 e0628ac9 注册表；feed 同为 https://www.rfi.fr/fr/afrique/rss；请求身份一致 89568512c1683f6a)
CANARY_RUN_1=PENDING
CANARY_RUN_2=PENDING

FINAL_RESULT=PARTIAL_PENDING_PRODUCTION_OBSERVATION
```

---

## 1. 基线（权威口径）

| 项 | 值 | 来源 |
|---|---|---|
| LOGICAL_SOURCES | 153 | `data/sources.json`（pin 树） |
| ENABLED | 151 | 同上（`legacy_payload.enabled`） |
| discovery_type 分布 | rss 72 / gdelt_search 70 / reliefweb_api 2 / html_listing 9 | 同上 |
| EXPANDED_EXECUTIONS | 888 | production-state ops 账本（run 39118717379，2026-10-18 11:05Z） |
| WALL_CLOCK | 3000s | `COLLECTION_WALL_CLOCK_LIMIT`（`ASIP_COLLECTION_WALL_CLOCK_SECONDS` 可覆写） |
| 多国源（country_scope>1） | 16 | 见 §3 |

SHA 快照（编辑前）：`data/sources.json` = `13842532a`（编辑后 blob）；编辑前 blob `defb3f4e0`。
registry 代码：`scripts/collectors/registry.py` = `d5fdfa3e3`（编辑前）。

---

## 2. Gate A — 确定性缺陷修复

### 2.1 ben_webtv（相对 feed URL）

严格复测（默认证书校验，无 `-k`）：

| URL | HTTP | Content-Type | 解析 |
|---|---|---|---|
| `https://beninwebtv.com/feed/` | **200** | `application/rss+xml; charset=UTF-8` | **50 items，日期/URL 全非空** |
| `https://beninwebtv.com/feed.xml` | **404** | `text/html` | — |
| `http://beninwebtv.com/feed.xml` | 301 | `text/html` | 重定向，非规范 |

结论：旧值 `"/feed.xml"` 是相对路径且后缀错误（404）。改为 `https://beninwebtv.com/feed/`。

### 2.2 nga_nrc（HTTP 端点）

| URL | HTTP | Content-Type | 解析 |
|---|---|---|---|
| `https://nrc.gov.ng/feed/` | **200** | `application/rss+xml; charset=UTF-8` | **1 valid item，含日期** |
| `http://nrc.gov.ng/feed/` | 301 | — | 非规范/不安全 |

结论：改为 `https://nrc.gov.ng/feed/`。注：该源天然低频（当前仅 1 条），但 RSS 结构有效、
条目带日期与绝对 URL，符合"真实可解析响应"要求。

（两条均未改动 article URL 方案与来源身份，未新增来源。）

### 2.3 PHASE 遥测上抛

- `stage3_collect_v2.write_stats` 已产出 `PHASE0..4_{EXECUTIONS,SKIPPED_WALL_CLOCK,ELAPSED_SECONDS}`；
  本包改为**显式 UNKNOWN**：上游 `phase_stats` 不可用时写 `"UNKNOWN"` 并附
  `PHASE_TELEMETRY_AVAILABLE=false`，不再静默跳过（原实现 `except NameError: pass` 会让字段整体消失）。
- `collection_run` 通过 `_EXTRA_FIELDS` 把 15 个 PHASE 字段 + 执行行/物理请求/复用计数写入
  `data/runtime/ops/collection_summary.json` 与 ops 账本 run 记录。
- `operations.py` 在 `operations_summary.md` 增加两行：`execution_rows:` 与 `phases(exec/skip_wc/elapsed):`。

### 2.4 指标命名拆分（旧名语义不变）

新增（精确语义）：

```
execution_rows_configured          = 注册表配置行数（153）
execution_rows_enumerated          = len(per_source)（本轮枚举的执行行，含墙钟跳过）
execution_rows_skipped_wall_clock  = status == skipped_wall_clock 的行数
execution_rows_actually_attempted  = enumerated - skipped_wall_clock
physical_network_requests          = 真实 urlopen 次数（含重试；来自 framework 计数器）
successful_source_executions       = successful_sources（语义等同，新名更明确）
```

迁移别名（显式写入 `metrics_alias`）：

```
sources_attempted  -> execution_rows_enumerated
sources_succeeded  -> successful_source_executions
note: attempted_sources 历史上即枚举行数（含墙钟跳过），并非真实网络请求数
```

旧字段 `attempted_sources` / `successful_sources` **取值与含义未变**（已用合成数据验证：
3 行中 1 行 skipped_wall_clock → `attempted_sources=3`、`execution_rows_actually_attempted=2`）。

### 2.5 Gate A 测试

| 测试 | 结果 |
|---|---|
| 新增 `scripts/tests/test_c8_4d1_shared_feed.py` | **18/18 PASS** |
| `test_c1c_source_expansion`（来源准入/扩展） | **12/12 PASS** |
| `test_c2b_time_and_relevance`（时间/RSS 解析/相关性） | **19/19 PASS** |
| 生产 source 数 | 153/151 **未变**（测试内断言） |

已知基线噪声（**非本次改动引入**）：裸 clone 上 `validate_pipeline.py --stage source` 报
`V-PB1-nonempty-sanity`（master_events/disease_outbreaks built=0）。已用 pin 原始树对照复现同一错误；
生产 deploy 在 `--stage dist` 且 state 视图加载后校验，与本包无关。

---

## 3. 多国源请求身份审计（16 个）

| source_id | discovery | 生效请求 | scope | 国家是否进入请求 | 判定 |
|---|---|---|---|---|---|
| pan_allafrica | rss | `allafrica.com/.../headlines.rdf` | 54 | 否 | STATIC |
| pan_unnews_africa | rss | `news.un.org/.../africa/feed/rss.xml` | 54 | 否 | STATIC |
| pan_africanews | rss | `africanews.com/feed/` | 54 | 否 | STATIC |
| nga_premiumtimes | rss | `premiumtimesng.com/feed/` | 32 | 否 | STATIC |
| pan_france24_africa | rss | `france24.com/en/africa/rss` | 54 | 否 | STATIC |
| gha_myjoyonline | rss | `myjoyonline.com/feed/` | 32 | 否 | STATIC |
| rwa_newtimes | rss | `newtimes.co.rw/rss/` | 32 | 否 | STATIC |
| pan_reliefweb | rss | `reliefweb.int/updates/rss.xml` | 54 | 否 | STATIC |
| pan_bbc_africa | rss | `feeds.bbci.co.uk/news/world/africa/rss.xml` | 54 | 否 | STATIC |
| pan_aljazeera | rss | `aljazeera.com/xml/rss/all.xml` | 54 | 否 | STATIC |
| pan_voa_africa | rss | `voaafrica.com/api/zrqiteukiq` | 54 | 否 | STATIC |
| pan_voa_afrique | rss | `voaafrique.com/api/zrqiteukiq` | 54 | 否 | STATIC |
| pan_rfi_afrique | rss | `rfi.fr/fr/afrique/rss` | 54 | 否 | STATIC |
| pan_dw_africa | rss | `rss.dw.com/rdf/rss-en-africa` | 54 | 否 | STATIC |
| specialist_acss | rss | `africacenter.org/feed/` | 9 | 否 | STATIC |
| un_who_afro | rss | `afro.who.int/rss.xml` | 54 | 否 | STATIC |

审计结论：
- 16/16 均为 **静态 RSS**，国家只影响**抓取后的地理判定**，不进入 URL/头/请求体 → 请求身份国家无关。
- 其中 5 条 feed 被**多个 source_id** 同时引用（这是本次复用的真实收益来源）：

| feed | source_ids |
|---|---|
| `feeds.bbci.co.uk/afrique/rss.xml` | intl_bbc_afrique_chad, intl_bbc_afrique_niger |
| `www.africanews.com/feed/` | niger_africanews, pan_africanews |
| `www.aljazeera.com/xml/rss/all.xml` | intl_aljazeera_chad, intl_aljazeera_niger, pan_aljazeera |
| `www.france24.com/fr/afrique/rss` | intl_france24_afrique_chad, intl_france24_afrique_niger |
| `www.rfi.fr/fr/afrique/rss` | intl_rfi_afrique_chad, intl_rfi_afrique_niger, pan_rfi_afrique |

排除项（**未优化**，符合 §B2）：
- `gdelt_search` 70 源：查询词/国家相关 → 不参与复用。
- `reliefweb_api` 2 源：API 已失效（410），维持既有"不执行 HTML 兜底"策略。
- `html_listing` 9 源：分页/条件抓取，本包**不启用**复用（保守 rollout）。
- 单 source 的 54 国展开：已由既有 `_DISCOVER_CACHE`（key=source_id）在 C8-3 时实现每轮一次抓取，
  本包不重复计算这部分"节省"。

---

## 4. Gate B — 实现

### 4.1 结构

```
SOURCE-COUNTRY EXECUTION（国家管线，逐国照旧）
        |
        v
EXACT REQUEST IDENTITY（sha256: method + url + 相关头 + 鉴权上下文摘要）
        |
        +-- MISS -> 真实 HTTP（计数 physical_network_requests）-> 存原始响应
        |
        +-- HIT  -> 复用原始响应（计数 cache_hits）
                          |
                          v
                同一解析器 parse_feed_robust
                          v
                逐国地理门槛 / 相关性 / 准入（未改动）
                          v
                持久化与发布门槛（未改动）
```

- 代码位置：`scripts/collectors/framework.py`（`fetch_page(..., reuse=True, source_id=...)` +
  `request_identity` / `_cache_put` / `reset_run_caches` / `get_request_stats`），
  `scripts/collectors/registry.py`（仅 RSS/Atom 发现路径传入 `reuse=True`）。
- 缓存特性：run-local；FIFO 有界（默认 64 条 / 24MB，可 env 调整）；**只缓存成功响应**；
  敏感头只以 sha256 摘要参与身份、不落明文；`stage3_collect_v2.main()` 每轮 `reset_run_caches()`。
- 计数器：`cache_hits` / `cache_misses` / `cache_bytes` / `reused_requests` /
  `bypass_flag_disabled` / `bypass_not_allowlisted` / `evictions`。

### 4.2 特性开关（默认关闭）

| env | 默认 | 作用 |
|---|---|---|
| `ASIP_SHARED_FEED_REUSE` | `0`（关闭） | `1/true/yes/on` 才启用复用 |
| `ASIP_SHARED_FEED_REUSE_SOURCES` | 空 | 逗号分隔 source_id 白名单；非空时仅白名单内生效 |
| `ASIP_SHARED_FEED_REUSE_MAX_ENTRIES` | 64 | 缓存条目上限 |
| `ASIP_SHARED_FEED_REUSE_MAX_BYTES` | 25165824 | 缓存字节上限 |

回滚 = 将 `ASIP_SHARED_FEED_REUSE` 置 `0`（或删除变量）即回到 C8-4C4 行为，无需回滚代码。

### 4.3 生产启用路径（已随 release pin 完成透传，默认关闭）

工作流定义在 `main`（pin 树不含 orchestrator）。**已于 release 提交
`c2c48d12` 中加入**下列 env 透传（`asip-production-orchestrator.yml` 的
`Run due-task orchestrator` 步骤、`asip-production-collection.yml` 的 `Collection run` 步骤）：

```yaml
          ASIP_SHARED_FEED_REUSE: ${{ vars.ASIP_SHARED_FEED_REUSE || '0' }}
          ASIP_SHARED_FEED_REUSE_SOURCES: ${{ vars.ASIP_SHARED_FEED_REUSE_SOURCES || '' }}
```

编排器以 `subprocess.run(...)`（未传 `env=`）调用 `scripts/ops/collection_run.py --execute`，环境变量正常继承。
激活时只需在仓库变量（Settings → Secrets and variables → Actions → Variables）写入
`ASIP_SHARED_FEED_REUSE=1` 与 `ASIP_SHARED_FEED_REUSE_SOURCES=intl_rfi_afrique_chad,intl_rfi_afrique_niger,pan_rfi_afrique`，
无需再改代码或 workflow；回滚就是把它置 0。

---

## 5. 等价性对照（OLD vs NEW）

### 5.1 固定 fixture（确定性）

- 同一 feed 被 3 个不同 source_id 执行（模拟 BBC/RFI/AlJazeera 共享 feed）：
  - DISCOVERED ARTICLE URL SET：**完全一致**
  - ARTICLE COUNTS：一致（3×20）
  - 每篇文章 payload（title/url/summary/published/method/feed_url/language）：**逐字段一致**
  - 国家归属：对 3 个国别配置（乍得/尼日尔/尼日利亚）逐条比对 `identify_country` 输出：**一致**
  - 物理请求：3 → 1（hits=2）
- 反例保护：不同 URL / 不同方法 / 不同鉴权上下文 / 敏感头变化 → **不共享**（各自独立请求）。
- 失败不缓存：错误响应两次调用 → 0 hits、2 misses（各自完整重试）。
- 跨轮隔离：`reset_run_caches()` 后同 URL 重新发起真实请求。

### 5.2 真实网络（非 fixture）

对 12 个共享 feed 执行行做 OLD→NEW 两轮：

| 指标 | OLD | NEW |
|---|---|---|
| 物理 HTTP 请求 | **12** | **5** |
| HTTP 耗时（秒） | 10.21 | 3.14 |
| 发现文章数 | 240 | 240 |
| 唯一 URL 数 | 100 | 100 |
| 逐源 URL 集合差异 | — | **0 差异**（`url_set_diffs={}`） |
| cache hits / misses / bytes | — | 7 / 5 / 162,729 |

---

## 6. 效率口径（避免夸大）

- **888 执行行 ≠ 888 次网络请求**。C8-3 的 `_DISCOVER_CACHE` 已让"同一 source 在 54 国管线"
  每轮只抓一次 feed；因此本轮**不能**把 550 条墙钟跳过行折算为"节省 550 次请求"。
- 本包真实新增节省来自**跨 source_id 的同请求重复**：5 组 feed、12 个 source 执行 → **7 次/轮**。
- 全量口径推算（RSS 静态源 72 条，去重后 65 个物理目标）：一轮约 72 → 65 次 feed 抓取（**-7**），
  约占"feed 抓取"总量的 9.7%；相对"含正文抓取的全部物理请求"比例更小。
  正文抓取由既有 `_EXTRACT_CACHE` 吸收，不属于本包新增收益。
- 未观测到额外 AI 调用（本包不触碰 AI 层）；未改变重试策略（`MAX_RETRIES=2` 不变），
  故不产生"额外 HTTP 重试"。

---

## 7. 收尾结论与待办

**已完成且可复核**：Gate A 四项（ben_webtv / nga_nrc / PHASE 遥测 / 指标命名）、
Gate B 实现（身份判定 + run-local 有界缓存 + TTL + 开关 + 计数）、固定 fixture 与真实网络等价性、
真实节省测量、**24 项新增测试（18 + 6）全部通过**，release pin 已切到 `e0628ac9`（见 §9）。

**未完成（阻塞 PASS 的硬条件）**：
1. `DEFAULT_OFF_RUN`：部署后**尚未到达**首个 collection-due 周期。
   最后一次成功采集 `2026-10-18T11:58:33Z`；阈值 5h45m → 17:43Z 之后才 due；
   下一次 orchestrator 唤醒 `18:05Z` 才会命中。本报告生成于 17:21Z。
2. `CANARY_RUN_1 / CANARY_RUN_2`：canary 需先在仓库变量中设置
   `ASIP_SHARED_FEED_REUSE=1` 与 `ASIP_SHARED_FEED_REUSE_SOURCES=<三 RFI ID>`，
   再观察两个**自然** collection-due 周期。
3. `P0_SKIPS/P1_SKIPS/LANE_A_SKIPS`：本轮仍为 PENDING——改动前遥测未进入 summary 层，
   历史 run 无该字段；新指标随 `e0628ac9` 生效后首轮即可实测。

**FINAL_RESULT = PARTIAL_PENDING_PRODUCTION_OBSERVATION**（A–E 成立；F 待两轮自然周期）。
未新增全局/区域源；未启动 C8-4D2；canary 白名单未自动扩大。

---

## 9. 生产切换执行记录（Controlled Cutover）

### 9.1 STEP 0 — 预部署修正（已实施）

独立评审指出的问题属实：`phase_stats` 在 `main()` 局部构造，`write_stats()` 靠全局查找 +
`except NameError` 吞掉缺失，导致生产可能长期 UNKNOWN。实际修法：

- `write_stats(..., phase_stats=phase_stats)` **显式入参**；调用点同步传入。
- 相位归因改为**行级戳**：`_run_phase_pass` 对每条 source-country 执行行写入 `phase`，
  遥测从 `per_source` 派生（`PHASE_TELEMETRY_BASIS=measured_source_country_rows`）。
- 每相位三组计数：`PHASE{p}_ENUMERATED / _ATTEMPTED / _SKIPPED_WALL_CLOCK`，
  且 `PHASE{p}_EXECUTIONS`＝ATTEMPTED（明确语义）。
- 相位耗时 **只累加逐行实测 `duration_s`**（`PHASE_ELAPSED_BASIS=measured_row_durations`）；
  删除原先把"一次调用耗时 ÷ 相位个数"均分后当精确值上报的逻辑。
- 对账：`PHASE_SKIPPED_TOTAL` 与 `per_source` 墙钟跳过数比对 → `PHASE_SKIP_RECONCILED`；
  未枚举键（未进入任何国家管线即被墙钟截断）单独披露为 `PHASE_UNENUMERATED_KEYS`。
- 无 `phase` 戳但显式传入 `phase_stats` → `aggregate_fallback`，**耗时标记 UNKNOWN**（不冒充精确值）。
- 6 项确定性回归测试覆盖：行派生、fallback、全缺失→UNKNOWN、对账失败显式暴露、TTL 过期重取、TTL 内复用。

### 9.2 STEP 1 — 释放安全核对

| 检查 | 结果 |
|---|---|
| ALL_TESTS | **PASS**（55 tests：18 + 6 + 12 + 19） |
| SOURCE_COUNT / ENABLED | 153 / 151 |
| EXPANDED_EXECUTIONS | 888（本轮未改变展开逻辑） |
| ben_webtv / nga_nrc | 绝对 https + 实测 200 RSS |
| flag 默认 OFF | `shared_reuse_enabled()` 默认 False；默认路径 0 命中 |
| allowlist 行为 | 白名单外一律 bypass（`bypass_not_allowlisted` 计数） |
| 请求身份 | 同 URL/方法/相关头/鉴权上下文才同键；敏感头只参与摘要 |
| 缓存隔离 | 每轮 `reset_run_caches()`；跨轮不复用 |
| 有界内存 | 64 条 / 24MB，FIFO 淘汰 + `evictions` 计数 |
| 仅成功响应缓存 | 失败不写缓存 |
| **新鲜度上限（新增）** | `ASIP_SHARED_FEED_REUSE_TTL_SECONDS` 默认 **600s**；超龄视为未命中并重取（`cache_expired`） |
| 回滚 | `ASIP_SHARED_FEED_REUSE=0` 即回到 C8-4C4 行为（无需回滚代码） |
| 文章安全/地理策略 | 未改动 |

### 9.3 STEP 2 — Release Pin

- NEW_SOURCE_COMMIT = `e0628ac99a3230dca29b5368e7379307e0b6ec48`（feature 分支 tip，已推送）
- MAIN_RELEASE_SHA = `c2c48d12175489b256a9914d74bdfad7b66f9bfc`（main 上一次性 release-controller 提交）
- 变更范围：仅 5 个 production workflow 的 `ref:`（e5ab2fbe → e0628ac9），共 5 行；
  **未** merge 整个 feature 分支到 main（两侧发布历史不同），**未**触碰
  production-state / gh-pages / canonical 数据 / 报告 / 调度。
- 环境变量透传（默认关闭）已加入：
  - `asip-production-orchestrator.yml`（`Run due-task orchestrator` 步骤）
  - `asip-production-collection.yml`（`Collection run` 步骤）
  - 取值 `${{ vars.ASIP_SHARED_FEED_REUSE || '0' }}` / `${{ vars.ASIP_SHARED_FEED_REUSE_SOURCES || '' }}`
- YAML 校验：5 个文件 `yaml.safe_load` 全部 OK；pin 与 env 均被解析器确认。
- 触发器未变（无 `push` 触发），故本次 main 提交不会自动触发任何生产运行。

### 9.4 STEP 3/4 待执行（下一个人工/自然窗口）

```text
# 1) 默认关闭周期（验证 PHASE 遥测与 P0/P1/LaneA 健康）
#    仓库变量保持 ASIP_SHARED_FEED_REUSE=0（或不存在）
#    等待 2026-10-18T18:05Z 起的自然 collection-due 周期
# 2) canary 开启（三 RFI 源，已核验请求身份一致）
ASIP_SHARED_FEED_REUSE=1
ASIP_SHARED_FEED_REUSE_SOURCES=intl_rfi_afrique_chad,intl_rfi_afrique_niger,pan_rfi_afrique
# 3) 观察两个自然 collection-due 周期（约 5h45m 间隔）
```

观测取数位置（production-state 分支，无需登录 Actions 日志）：

- `data/runtime/ops/operations_status.json` → 每轮 run 记录（新字段已随 `e0628ac9` 落盘）：
  `execution_rows_*`、`physical_network_requests`、`PHASE0..4_*`、`PHASE_TELEMETRY_AVAILABLE`、
  `PHASE_SKIP_RECONCILED`、`shared_feed_reuse{cache_hits,cache_misses,cache_expired,reused_requests}`
- `data/runtime/ops/collection_summary.json` → 同一组指标
- `data/runtime/ops/operations_summary.md` → 人类可读的 `execution_rows:` / `phases(...)` 行

判定阈值（任一触发即回滚 `ASIP_SHARED_FEED_REUSE=0`）：
P0/P1 保证键被墙钟跳过 > 0；Lane A material starvation > 0；缓存身份碰撞或错误复用；
文章/国家归属回归；异常持续错误；生产处理中断。

**说明**：`framework.fetch_page` 的 `physical_network_requests` 只覆盖走该函数的请求；
GDELT 采集器与其它独立 HTTP 客户端（reliefweb 等）不计入，比较时须按同一口径。

---

## 8. 复现命令

```bash
# 测试
python -m unittest scripts.tests.test_c8_4d1_shared_feed -v      # 18/18
python -m unittest scripts.tests.test_c1c_source_expansion      # 12/12
python -m unittest scripts.tests.test_c2b_time_and_relevance    # 19/19

# 真实效率测量（需外网）
ASIP_SHARED_FEED_REUSE=0 python scripts/ops/c8_4d1_measure.py --out /tmp/c8_4d1.json
```

（`c8_4d1_measure.py` 内部已自行切换 flag 做 OLD/NEW 两轮，并输出 `savings` 与 `url_set_diffs`。）
