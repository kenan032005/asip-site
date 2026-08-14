# UI Hard Fix Pack A — Acceptance Report

> 目标：以**用户感知效果**为最高验收标准。上一轮 UI_FINAL_POLISH_PACK_1 技术上通过但用户在真实 Preview 中未看到明显变化，本轮以「一眼能看出变化」为验收门槛。

- **Source branch**: `feature/asip-ppt-entity-expansion-c`
- **Source HEAD**: `1946c19`（本轮 UI 改动均基于该基线，未改任何知识数据）
- **Preview namespace**: `gh-pages / previews/asip-intelligence-v2/**`
- **Preview URL**: https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/

---

## 1. 最终门禁

| 门禁 | 值 | 状态 |
|---|---|---|
| KNOWLEDGE_DATA_CHANGED | **0**（17 个数据文件 git 级 blob 一致，`git hash-object` 对比，autocrlf 安全） | ✅ |
| OUT_OF_SCOPE_CHANGED_FILES | 0（仅 UI 模板/CSS/JS + QA 工件） | ✅ |
| NETWORK_HARD_FIX | **PASS**（默认标签大幅减少、无裁切、详情面板主出口、图例联动无悬空边） | ✅ |
| RELATION_HERO_HARD_FIX | **PASS**（机器字段不再默认直出，全部折叠进技术元数据） | ✅ |
| BODY_ENTITY_AUTOLINK_VISIBLE | **PASS**（JNIM↔Niger 正文尼日尔/马里/贝宁 16 处可点链接，用户可见） | ✅ |
| ENTITY_TOC_HARD_FIX | **PASS**（更窄、44vh→36vh 受限、滚动后自动收起、可手动展开） | ✅ |
| ENTITY_SOURCE_LAST | **PASS**（来源与注释恒为页面最后，不再打断正文） | ✅ |
| BUILD | **PASS**（321 routes） | ✅ |
| 全量回归 | 38 suites / 6827 cases / **FAILED = 0** | ✅ |
| ONLINE_BROWSER_QA | **PASS**（14 页 × desktop/mobile = 28 页，**268/268 gates**，console/exc/req/overflow 全 0） | ✅ |
| ONLINE_INTERACTION_QA | **PASS**（13/13：图例联动/无悬空边/详情面板/空状态/TOC 自动收起/正文互链） | ✅ |
| ONLINE_LINK_QA | **PASS**（0 dead / 0 unreachable / 0 assets 404） | ✅ |
| ONLINE_ROUTE_QA | **PASS**（321/321 公网可达） | ✅ |
| PRODUCTION_CONTENT_CHANGED | 0（gh-pages diff 排除 previews = 空） | ✅ |
| PRODUCTION_NAMESPACE_HASH_CHANGED | **0**（412 个 production 文件 byte-identical，`git show` 对比） | ✅ |
| force push / cutover / Expansion D | 均无 | ✅ |

---

## 2. 五处硬化改动（用户可感知差异）

### 2.1 Network：默认更干净 + 无裁切 + 详情面板主出口
- **严格默认标签策略**（`labelMode="auto"` 重定义）：中心节点完整标签；**L1 关键邻居**才显示短标签/缩写；其余节点只显示图形点，不再铺满文字。
  - JNIM focus：32 节点 → 仅 10 个标签
  - AQIM focus：7 节点 → 仅 2 个标签
  - Al-Shabaab focus：8 节点 → 仅 4 个标签
- **标签边界自适应**：靠近画布边缘的标签自动移到节点上方/外侧/调整对齐，默认视图不再出现「上下标签只显示一半」。
- **安全边距扩大**：节点布局约束 `x∈[96,804] y∈[66,534]`；圈层辅助线改为椭圆（匹配 `yk=0.9` 布局），不再被画布裁剪。
- **缩放保护**：缩放改为围绕画布中心（`translate(cx-cx*z, cy-cy*z) scale(z)`），并新增 `maxSafeZoom()` 按当前布局计算最大安全缩放，放大后内容不再被裁切。
- **降噪**：非关键节点在 auto 模式下连 L1/L2/L3 小标也不显示；信息进入点击后的详情面板。
- **悬空边修复（真实 bug）**：图例取消某节点类型后，此前其关联边仍显示。已在 `draw()` 中按可见节点过滤 rels，取消组织 → 32 节点/33 边 → 13 节点/**13 边**，统计同步 `当前可见 13 个节点 · 13 条关系`。
- **图例交互控制器**保留并强化：节点类型（组织/人物/国家）+ 关系类型（对抗/协作/从属/活动于）checkbox、全选/重置、可见统计、空状态提示全部在线实测 PASS。

### 2.2 Relation Hero：彻底去技术化
- `current_status` 原始 enum 不再直接渲染：新增 `statusLabel()`（约 110 个精确中文映射 + 前缀兜底），例如 `reported_activity_presence → 据报存在活动`、`historical_staged_integration → 历史分阶段整合`。
- 关系页顶部标题行/状态行/双方卡全部走 `statusLabel`；`rel-jnim-niger-operates` 这类 machine id 不再出现在任何 hero 区域。
- 头部徽章精简：去掉重复的双方 importance badge（party 卡已含），只保留成熟度/时效/争议。
- 技术字段（关系 ID、圈层、freshness 原始 code、语义说明、成熟度）统一在「技术元数据（展开）」内默认收起。
- 关系类型补漏：`part_of_network → 网络组成关系`（此前 5 条关系类型裸显示）。
- 实测：JNIM↔Niger =「活动于 · 据报存在活动」；EIJ↔Al-Qaida =「组成关系 · 历史分阶段整合」；Lakurawa↔IS-Sahel =「网络组成关系 · 持续」。

### 2.3 正文互链：真正可见
- 之前已接入 exact-safe auto-link；本轮把 `buildAutoLinkIndex()` 调用移到 countries 合并**之后**（上轮遗留的时序问题），确保「尼日尔/马里/贝宁」等国家名进入索引。
- 实测：JNIM↔Niger 正文中**尼日尔/马里/贝宁 16 处**为可点击实体链接（desktop/mobile 一致）；Lakurawa↔IS-Sahel 正文 2 处。
- 实体页正文同样可见互链（复用同一 renderer）。

### 2.4 Entity TOC：从「霸屏」到「轻量导航工具」
- 高度限制 44vh → **36vh**，内部滚动，容器变窄变薄。
- 一键收起按钮（收起↔展开标签实时切换）。
- **滚动自动弱化**：页面下滑 >200px 自动收起为细条，仅剩「☰ 本页目录 展开」；回到顶部自动恢复。
- Mobile 保持默认收起，不占首屏。

### 2.5 Entity「来源与注释」固定放最后
- 强模板规则：`renderSections` 支持 `detachTail`，entity 正文（`#entityBody`）不再包含 sources/notes；新增 `#entitySources` 面板固定在主列最后（正文 → 直接关系 → 相关证据 → **来源与注释**）。
- 专项页 Al-Shabaab/AQIM/EIJ/GIA/Lakurawa 全部验证：正文最后一个 section 为 `watch_indicators`，`entitySources` 为主列最后一个面板。

---

## 3. QA 结果摘要

### 3.1 在线浏览器 QA（真实公网 HTTPS）
- 28 页（14 页 × desktop 1440×900 / mobile 390×844）
- **268/268 gates**，console errors / runtime exceptions / failed requests / broken anchors / horizontal overflow 全 0
- network 专项（5 focus）：clean default 标签量、中心完整标签、可见统计、无 machine 标签全部 PASS

### 3.2 在线交互 QA（13/13）
- 图例取消组织 → 节点 32→13、边 33→13（**无悬空边**）、统计同步更新
- 全选恢复 32 节点；节点点击填充详情面板；全部取消显示空状态提示
- TOC 滚动自动收起 + 回到顶部自动恢复
- 关系 hero 无 machine id；正文国家链接可见；状态中文
- 实体来源面板为最后面板；状态中文

### 3.3 Link / Route QA
- 在线 link QA：14 页爬取、0 dead、0 unreachable、0 assets 404（口径与上轮一致）
- 全路由可达：**321/321** HTTP 200

### 3.4 全量回归
- `expansion_c_closure_audit.py`：38 套件 / 6827 用例 / **FAILED = 0**（多次重跑一致）

---

## 4. Before/After 对照截图

after 截图：`qa-artifacts-ui-hard-fix-a/screenshots/`（28 张 = 14 页 × 2 视口）
before 截图：`qa-artifacts-ui-final-polish-1/screenshots/`（上轮，同页面同视口）

| 对照对 | before | after | 可见差异 |
|---|---|---|---|
| network_al_shabaab_desktop | polish-1 截图 | hard-fix 截图 | 默认标签从全节点短标签 → 仅中心+关键节点 |
| network_aqim_desktop | 同上 | 同上 | 7 节点仅 2 标签，画布更空 |
| relation_jnim_niger_desktop | 同上 | 同上 | 顶部「活动于 · 据报存在活动」，无 machine 字段 |
| entity_al_shabaab_desktop | 同上 | 同上 | TOC 更窄 + sources 移至页面末尾 |
| entity_aqim_desktop | 同上 | 同上 | 同上 |
| network_jnim_desktop / mobile | 同上 | 同上 | 32 节点仅 10 标签 |

完整清单见 `screenshot-manifest.json`（28 after + 28 before 映射）。

---

## 5. 交付 URL

1. Preview 首页：https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/
2. AQIM Network focus：https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/network/?focus=actor-aqim
3. JNIM ↔ Niger 关系页：https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/relation/jnim-niger-operates/
4. Al-Shabaab 实体页：https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/entity/al-shabaab/
5. Production（未覆盖）：https://kenan032005.github.io/asip-site/intelligence/africa/（200）
6. gh-pages preview commit：`7a7a0be`（非 force，`d8311bc..7a7a0be`）

---

## 6. 过程中修复的真实问题
- **悬空边**：图例隐藏节点类型后其关联边仍显示 → 按可见节点过滤 rels（真实功能 bug，交互 QA 发现并修复）
- **relLabel 缺映射**：`part_of_network` 裸显示 → 补中文映射
- **prehash 口径**：Windows autocrlf 导致字节对比误报 → 改用 `git hash-object` blob 对比
- **浏览器缓存**：Edge 命中旧 JS 导致 QA 假阴性 → 所有在线 QA 前置 `Network.clearBrowserCache()`

## 7. 更新文件
- `assets/js/intelligence/africa.js`（statusLabel、network 严格标签/无悬空边/maxSafeZoom、relation hero、TOC 自动收起、sources detach）
- `assets/css/intelligence.css`（TOC 轻量、network 干净视图、relation hero 排版）
- `intelligence/africa/_templates/entity.html`（新增 `#entitySources` 末尾面板）
- `intelligence/africa/_templates/network.html`（标签模式「干净（默认）」）

```
UI_HARD_FIX_A = PASS
```

已停止。未启动 Expansion D，未切换 production，未 force push。
