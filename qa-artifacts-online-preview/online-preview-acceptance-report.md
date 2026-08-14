# ASIP Intelligence — Online Preview 发布验收报告

## 摘要

| 项 | 值 |
|---|---|
| **ASIP_ONLINE_PREVIEW** | **PASS** |
| Preview 首页 | https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/ |
| Preview 根 | https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/ |
| 发布载体 | gh-pages 分支子目录 `previews/asip-intelligence-v2/**`（复用既有 preview 机制） |
| gh-pages 发布 commit | `ec04618ebfe14d14149befb6f76488b97d1cff80` |
| 构建来源 | `feature/asip-ppt-entity-expansion-c @ facff39`（git archive 干净提取，不含旧 dist） |
| Production URL | https://kenan032005.github.io/asip-site/intelligence/africa/（未改动） |

---

## 1. 部署架构侦察

| 指标 | 值 |
|---|---|
| PREVIEW_DEPLOYMENT_METHOD | GitHub Pages（gh-pages 分支 "Deploy from branch" 模式）+ 既有 `previews/<name>/` 子目录机制；本次新增 `previews/asip-intelligence-v2/**` |
| PRODUCTION_ROOT | gh-pages 分支根（`intelligence/africa/` 为线上 ASIP Intelligence） |
| PREVIEW_ROOT | `previews/asip-intelligence-v2/` |
| SOURCE_HEAD | `facff39a68e4b694924442d09abb98a232be624e` |
| SOURCE_BRANCH | `feature/asip-ppt-entity-expansion-c` |
| 既有 preview 机制 | `previews/asip-intelligence-v1.0-rc1/`（v1.0 时代）——已确认可复用，故不另造部署系统 |
| 站点链接形式 | 全相对路径（`../../assets/...`），天然支持任意子路径部署，无绝对路径跳回 host root |

**构建**：从 facff39 用 `git archive` 提取干净源码 → `python scripts/build_site.py --no-embed` → **BUILD = PASS，routes = 321**（entities=102 / relations=192 / profiles=192 / timelines=88 / sources=246 / evidence=380 / aliases=443 / countries=13 / regions=7）。未复用任何旧 dist。

---

## 2. 在线发布与 Production 隔离

- 在 gh-pages 上**仅新增** `previews/asip-intelligence-v2/**`（483 个文件），production root 零改动。
- 发布前后 production namespace（排除 previews/）SHA manifest：**412 = 412 文件 byte-identical**，`PRODUCTION_NAMESPACE_HASH_CHANGED = 0`。
- `git diff 099fc2f..ec04618 -- . ':(exclude)previews'` = 空（production 零差异）。
- 未覆盖现有 production dist、未改正式导航、未做 release cutover、未改 main、非 force push（`099fc2f..ec04618 HEAD -> gh-pages`）。
- 部署过渡期生产页曾短暂返回 503（GitHub Pages 更新 CDN），数秒后恢复 200，最终 `production_url = 200`。

---

## 3. 在线 QA（真实公网 HTTPS URL）

### 3.1 Online Browser QA（46 页 = 23 页面 × desktop 1440×900 / mobile 390×844，真实截图 46 张）

覆盖：Landing / 8 实体页（Al-Shabaab、Lakurawa、AQIM、EIJ、GIA、AIAI、UPDF、Maitatsine）/ 6 关系页（Shabaab↔ISIS-Somalia、Lakurawa↔IS-Sahel、EIJ↔Al-Qaida、GIA-AQIM lineage、Battar↔ISIS-Libya、Al-Murabitun↔IS-Sahel）/ 3 列表页（entities、relations、sources）/ 5 network focus（Al-Shabaab、AQIM、JNIM、ISIS-Somalia、ADF/ISIS-CA）。

```
consoleErrors = 0
runtimeExceptions = 0
failedRequests = 0
logErrors = 0
brokenAnchors = 0
horizontalOverflow = 0（含 mobile）
gate = PASS
```

关键渲染抽查（desktop）：实体 TOC（Al-Shabaab 23 项 / Lakurawa 16 / EIJ 20 / Maitatsine 20）、key-facts（3–4 格）、uncertainty 卡（1）、关系 party 卡（2）、timeline 阶段卡（3–6）、network 节点（8 个 1-hop）+ 2-hop 开关、实体列表 filters（7 控件）。mobile：关系 hero 单列、TOC details 折叠、0 溢出。

### 3.2 Online Interaction QA（12/12 PASS）

- entity TOC 链接全部解析到真实 section（23/23）✓
- entity deep-link `#sec-*` 锚点定位 ✓
- relation body exact auto-links 实际存在（21 个/页）✓
- 实体搜索（102→1）+ 类型过滤（person→24）✓
- 关系搜索（192→7，`relQ` URL 同步）✓
- network 1-hop focus 渲染（7 节点）+ 2-hop toggle 存在 ✓
- mobile 关系 hero 单列无溢出 ✓
- mobile TOC 折叠 ✓

### 3.3 Online Link QA + 全路由可达性

- 静态爬虫（公网 URL，豁免基线 `../` 面包屑——与本地 QA 一致的 KNOWN_BASELINE）：**0 dead / 0 unreachable / 0 assets 404**，gate = PASS。
- **全路由可达性**：dist 全部 321 个路由逐一在线 HTTP 检查 → **321/321 = 200**，gate = PASS。SPA 动态互链（Fix-1 auto-links）由 3.2 实测确认。

---

## 4. 版本覆盖确认（Preview 完整包含）

- **Expansion A**：核心安全实体扩展（Al-Shabaab / ISIS-Somalia / al-Karrar / ADF-ISIS-CA / SIM / BBMB 等 11 实体 + 19 关系）
- **Expansion B**：AUSSOM / SNAF / Puntland Security Forces / FARDC / UPDF / MONUSCO / IRGC 等 11 实体 + 17 关系
- **UI/UX V2**：entity TOC、hero/key-facts、semantic hierarchy、uncertainty cards、relation party cards、timeline V2、实体/关系搜索过滤、sources 分组、network V2（1-hop 默认 + 2-hop 可选）、响应式——全部在线实测通过
- **UIUX V2 Fix-1**：relation body exact auto-linking 在线实测 21 链接/页
- **Expansion C**：EIJ / GIA / AIAI / TCG / GICM / Battar / Maitatsine / MUJAO + AQIM/GSPC、Ansar al-Dine、Al-Murabitun、Katiba Macina enrichment——在线渲染正常

---

## 5. 最终门禁

| 门禁 | 值 | 状态 |
|---|---|---|
| SOURCE_BRANCH | feature/asip-ppt-entity-expansion-c | ✅ |
| SOURCE_HEAD | facff39（构建目录 = facff39 git archive 干净源码） | ✅ |
| BUILD | **PASS**（321 routes） | ✅ |
| ROUTES | 321 | ✅ |
| ONLINE_PREVIEW_REACHABLE | YES（全部 curl/CDP 200） | ✅ |
| HTTPS | YES（https://kenan032005.github.io/...） | ✅ |
| ONLINE_BROWSER_QA | **PASS**（46 页，0 console / 0 exc / 0 req / 0 anchors / 0 overflow） | ✅ |
| ONLINE_INTERACTION_QA | **PASS**（12/12） | ✅ |
| ONLINE_LINK_QA | **PASS**（0 dead） | ✅ |
| ONLINE_ROUTE_QA | **PASS**（321/321 可达） | ✅ |
| CONSOLE_ERRORS / RUNTIME_EXCEPTIONS / FAILED_REQUESTS / BROKEN_INTERNAL_LINKS | 0 / 0 / 0 / 0 | ✅ |
| PRODUCTION_CONTENT_CHANGED | 0 | ✅ |
| PRODUCTION_NAMESPACE_HASH_CHANGED | **0**（412=412） | ✅ |
| KNOWLEDGE_SEMANTICS_CHANGED | 0（知识数据零改动） | ✅ |
| main changed | NO | ✅ |
| production cutover | NO | ✅ |
| force push | NO | ✅ |

**KNOWN_BASELINE（非本轮引入）**：面包屑 `../` 指向 entity/ relation/ 目录（GitHub Pages 静态 404，SPA fallback 仅 app shell），production 同样存在；本地与在线 link QA 均一致豁免记录。

---

## 6. 交付 URL 清单

1. **Preview 首页**：https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/
2. **Al-Shabaab 实体页**：https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/entity/al-shabaab/
3. **AQIM 实体页**：https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/entity/aqim/
4. **EIJ 实体页**：https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/entity/egyptian-islamic-jihad/
5. **R3 关系页（EIJ↔Al-Qaida）**：https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/relation/expc-eij-alqaida-integration/
6. **Network 页**：https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/network/
7. **正式 production URL**：https://kenan032005.github.io/asip-site/intelligence/africa/
8. **部署 branch / path**：gh-pages / `previews/asip-intelligence-v2/**`
9. **Preview deployment commit**：`ec04618ebfe14d14149befb6f76488b97d1cff80`
10. **Production namespace hash 核验**：`PRODUCTION_NAMESPACE_HASH_CHANGED = 0`（412 文件 byte-identical）

```
ASIP_ONLINE_PREVIEW = PASS
```
