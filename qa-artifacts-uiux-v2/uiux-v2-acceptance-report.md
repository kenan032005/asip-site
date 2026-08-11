# ASIP Intelligence UI/UX V2 — Acceptance Report

- **分支**: `feature/asip-intelligence-uiux-v2`
- **基线**: `feature/asip-ppt-entity-expansion-b @ 525012d`（Expansion B 验收 HEAD，本地/远端一致后建分支）
- **阶段**: 纯表现层/交互层升级（Phase 0 只读审计已通过：`UIUX_V2_CURRENT_STATE_AUDIT = PASS`）
- **范围**: 实体页 TOC / hero key-facts / 语义视觉层级 / 关系页 hero / 关系正文互链 / 时间轴 V2 / 实体列表搜索过滤排序 / 关系列表搜索过滤 / sources 分组 / Network V2（搜索 URL 同步 + 关系过滤 + 2-hop 密度保护）/ 响应式排版
- **数据冻结**: `data/intelligence/africa/**` 17 个文件 SHA-256 前后一致（`pre-ui-data-hashes.json` vs `post-ui-data-hashes.json`）

---

## 1. 最终门禁（全部满足）

| 门禁 | 值 | 状态 |
|---|---|---|
| KNOWLEDGE_DATA_CHANGED | **0**（17 文件 hash 全同） | ✅ |
| OUT_OF_SCOPE_CHANGED_FILES | **0** | ✅ |
| FAIL_TOTAL（37 测试） | **0**（37/37，含 Expansion B 专项） | ✅ |
| BUILD | **PASS**（302 routes） | ✅ |
| BROWSER_QA | **PASS**（57 页=19 页面×3 视口，console 0 / exceptions 0 / failedRequests 0 / brokenAnchors 0 / horizontalOverflow 0） | ✅ |
| INTERACTION_QA（专项 29 项） | **PASS**（29/29） | ✅ |
| TOC_QA | **PASS** | ✅ |
| LIST_FILTER_QA | **PASS** | ✅ |
| RELATION_INLINE_LINK_QA | **PASS** | ✅ |
| NETWORK_V2_QA | **PASS** | ✅ |
| RESPONSIVE_QA | **PASS**（mobile 0 溢出） | ✅ |
| NETWORK/LINK_QA | **PASS**（337 页 / 1956 链 / 0 死链） | ✅ |
| production / gh-pages / main | 均未改动 | ✅ |
| Depth G / Expansion C / UI-V2 之外工作 / force push | 均无 | ✅ |

---

## 2. 实现明细（对照需求）

### 2.1 实体页 TOC（Wikipedia-style long-page navigation）
- 复用现有但未启用的 **`.profile-toc`**（未建第二套样式体系；`test_i3a_preview` 契约同步更新 `intel-toc → profile-toc`）。
- 根据 `renderSections` 实际 section **自动生成**（Al-Shabaab 23 项 / Lakurawa 16 / UPDF 21 / Karate 14），每项自动 `#sec-<key>` anchor，无需手工维护；section 缺失时目录自动不显示（<3 项隐藏）。
- 点击平滑定位（`scroll-margin-top` + `scrollIntoView`）；**scroll-spy** 高亮当前章节（`.profile-toc a.active`）。
- desktop `position: sticky`（`.intel-toc-sticky`，top:64px）；**mobile <850px 可折叠「本页目录」**（`<details>` 默认收起，实测 open=false）。
- **deep-link** `#sec-leadership` 直接打开并定位（QA 验证 top<140px）。

### 2.2 Entity hero / key facts
- 中文主名称作 h1（+acronym）；**英文完整名独立第二行**（不再塞进标题括号）。
- 保留 type / importance / maturity / current status / freshness 徽章。
- 新增 **compact key-facts**（`#entityKeyFacts`，仅用现有数据，缺失自动不显示）：
  - 领导/核心人物（led_by/founded_by 关系推导，如 Karate→Diriye 系统内链）
  - 估计武装规模（force_estimates）
  - 活动国家/地区、所属区域
  - 归属/所属网络（affiliated_with/pledged_allegiance_to/constituent_of 等）
  - 最后核验（last_verified_at 等）
- 实测：Al-Shabaab 4 格、Lakurawa 3、Karate 3、UPDF 2；desktop `auto-fit` 网格，mobile 自动 1–2 列。

### 2.3 Semantic visual hierarchy
- 统一五类呈现组件（文字标签 + 边框/背景差异，非纯颜色）：`VERIFIED FACT`、`INSTITUTIONAL ASSESSMENT`（`.intel-sem-chip.institutional`，挂 sanctions_legal/legal_status）、`ASIP ANALYSIS`（蓝卡 + chip）、`UNCERTAINTY`（新独立卡 `.intel-uncertainty-card`，从普通段落提升）、`WATCH INDICATORS`（金卡 + chip）。
- 关系页 `uncertainties` 字段同样提升为独立卡。
- disputed 实体（Lakurawa / Puntland SF 等）与 disputed 关系（lakurawa-is-sahel 等）在页面顶部显示 **「身份/归属存在争议」/「关系状态存在争议」** 徽章（由现有 disputed 字段自动生成）。
- ASIP Analysis 始终以「平台分析」卡渲染，不与 verified fact 混淆。

### 2.4 关系页 Hero
- 启用/复用 `.relation-party-card`，新增 `#relationParties` 三栏：**Party A 卡 → 关系摘要 → Party B 卡**。
- 双方卡：name_zh / name_en / type / importance / status（有则显示）；摘要：关系类型、当前状态、时间范围、可信度、时效、争议标记。
- desktop 左—中—右；mobile 自动 `A ↓ 关系 ↓ B`（单列，箭头旋转 90°）。

### 2.5 关系正文实体互链
- **抽取/复用**实体页 `inlineLinks` renderer：关系档案全部文本字段改经 `inlineLinks(esc(...))` 渲染（overview、formation、evolution stages、drivers、timeline 等 20+ 处）。
- 无新识别逻辑、无模糊匹配；relation profiles 当前无 `[[...]]` 标记 → 保持普通文字（数据未改）。

### 2.6 关系时间轴 V2
- 数据（relation_timelines.json）不变，仅改 renderer：`阶段/日期 + 阶段标题 + 描述 + 影响 + 可信度/来源` 卡片化。
- **current phase** 用现有 `profile.current_status/current_assessment` 渲染为「当前阶段」banner（无推断）。
- desktop 横向阶段条（连接线、可横滚）；mobile 保持纵向。

### 2.7 实体列表搜索/过滤/排序
- 94 实体页新增：搜索（name_zh/name_en/acronym/aliases）、类型、重要程度、当前状态、区域、档案深度过滤、排序（重要程度/名称/最后核验/关系数）。
- 全部 client-side；**URL query 同步**（`entityQ/entityType/...`），reload/back/forward 恢复（QA 验证直接打开 `?entityQ=shabaab` 输入框与结果恢复）。
- 计数「当前结果 X / 总计 Y」；无结果时空状态提示。

### 2.8 关系列表搜索/过滤
- 181 关系页：搜索（双方名称/别名）、关系类型、当前/历史、档案深度、仅争议/不确定、时间敏感 checkbox；URL 同步；计数显示。未分页（client-side filtering 实测无性能问题，94/181 规模秒级）。

### 2.9 Sources/Evidence 呈现
- 数据结构未改；`initSources` 按 metadata 分组（5 组：官方权威 / 国际组织 / 研究机构 / 媒体与其他 / 其他来源），每组 **可折叠**（`<details open>`）。
- 无法可靠分类的（manifest_candidate 等）退化为「其他来源」组（publisher 分组兜底，不猜）。
- 每项显示 title / publisher / date / type / reliability / **证据数**（evidence.source_id 关联）。

### 2.10 Network V2
- 保持 focused **1-hop 为默认**（无全局 94 节点自动图）。
- **搜索后 `?focus=` URL 同步**（修复审计 F07）。
- 新增：关系类型过滤、当前/历史过滤、仅争议过滤（+ disputed 虚线红边样式）、图例补充（争议/当前）。
- **展开第二层**：默认 OFF（`aria-pressed=false`）；开启后按**重要程度优先**排序，**节点上限 20**，超出时显示密度提示（"候选较大…请继续筛选"），不生成蜘蛛网。

### 2.11 响应式排版
- 修复 F05/F15：h1 `clamp(23px,3.6vw,31px)`、英文副标题 `clamp(13px,2.2vw,15px)`、关系标题 `.rel-hero-title` clamp。
- 390px：中文名完整可读（实测 23px）、英文正常换行、TOC 折叠、key-facts 降列、party cards 纵向、表格沿用既有 wrap；**全 19 页 mobile 0 水平溢出**。

---

## 3. QA 证据

- `browser-qa.json`：57 页（19×3），gate=PASS；关键状态：Al-Shabaab TOC 23 链接/details open、key-facts 4；Lakurawa disputed 徽章 1 + uncertainty 卡 1；UPDF/Karate TOC 21/14；关系页 party 2+summary+timeline 阶段卡+当前阶段 banner；sources 5 组；network 7 节点/6 边。
- `interaction-qa.json`：29/29 PASS（TOC 存在/自动生成/desktop open/deep-link/scroll-spy/mobile 折叠、disputed 徽章、uncertainty 卡、key-facts、relation hero、时间轴 V2、inlineLinks 接线、实体搜索+URL 同步+reload 恢复、关系搜索、network 搜索 URL 同步、2-hop 展开、2-hop toggle 状态、关系类型过滤、disputed 边、mobile h1 clamp、mobile 无溢出、relation hero 单列、sources 分组）。
- `toc-qa.json` / `semantic-visual-qa.json` / `list-search-filter-qa.json` / `relation-inline-link-qa.json` / `network-v2-qa.json` / `responsive-qa.json`：全部 PASS。
- `link-qa.json`：337 页 / 1956 链 / 0 死链。
- `screenshots/`：**57 张真实截图**（19 页面 × desktop 1440×900 / laptop 1280×800 / mobile 390×844），`screenshot-manifest.json` 记录。
- `component-change-map.json`：10 项特性 → HTML/JS/CSS/generator 映射，供后续 V2 阶段定位改动点。

---

## 4. 数据不变性

| 指标 | 前 | 后 |
|---|---|---|
| countries | 13 | 13 |
| entities | 94 | 94 |
| relationships | 181 | 181 |
| sources | 221 | 221 |
| evidence | 358 | 358 |
| routes | 302 | 302 |
| data/intelligence/africa/** SHA-256 | 17 文件 | **全部一致** |

知识语义零变化；唯一非知识改动：`scripts/tests/intelligence/test_i3a_preview.py` 的 CSS 类契约（intel-toc→profile-toc，随 V2 复用 .profile-toc 同步）。

---

## 5. 变更文件（OUT_OF_SCOPE_CHANGED_FILES = 0）

**Tracked modified（7 + 1 测试）**：`assets/js/intelligence/africa.js`、`assets/css/intelligence.css`、6 个模板（entity/relation/network/entities/relations.html）、`scripts/tests/intelligence/test_i3a_preview.py`。

**Untracked（本轮新增）**：`scripts/qa/uiux_v2_browser_qa.js`、`uiux_v2_interaction_qa.js`、`uiux_v2_link_qa.js`、`uiux_v2_derive_qa.py`、`uiux_v2_scope_audit.py`、`qa-artifacts-uiux-v2/**`（含 57 截图）。

**未改动**：`data/intelligence/africa/**`（hash 一致）、`qa-artifacts-i3b-fix1c/local-path-scan.json`（diff ZERO）、gh-pages/production/main、任何历史 QA 工件。

---

## 6. 暂不处理（按需求 12 明确排除）

- F11 面包屑 `../` 基线行为（KNOWN_BASELINE，不在本轮）
- F12 africa.js 组件化重构（ui-component-map 已为后续定位）
- 全局全量图 / map / Expansion C / 知识内容 / production 部署 / gh-pages
- 与 UI/UX V2 无关的旧 Depth G 技术债
- F14 topbar 预览文案：仅普通文案，不影响导航，本轮**未**改动（保持零风险，未记为 COSMETIC 变更项）

---

## 7. 结论

```
UIUX_V2_LOCAL_CANDIDATE = PASS
```

全部门禁满足；知识数据零变化；57 张真实截图与全部专项 QA 工件齐备；分支已按建议逻辑提交并普通推送（无 force push）；未部署生产；未启动 Expansion C。
