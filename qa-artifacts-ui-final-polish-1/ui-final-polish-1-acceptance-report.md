# ASIP Intelligence — UI Final Polish Pack 1 验收报告

## 摘要

| 项 | 值 |
|---|---|
| **UI_FINAL_POLISH_PACK_1** | **PASS** |
| 分支 | `feature/asip-ppt-entity-expansion-c`（基线 d6d0d01） |
| Preview namespace | gh-pages / `previews/asip-intelligence-v2/**`（覆盖更新，production 零改动） |
| Preview 首页 | https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/ |
| gh-pages preview commit | `d8311bc33c58a92df9ecafb7bf95c4ad8bd76810` |
| 全量测试 | 38 套件 / 6827 用例 / **FAIL = 0** |
| 数据 | `KNOWLEDGE_DATA_CHANGED = 0`（17 文件 hash 前后一致） |
| Production | `PRODUCTION_NAMESPACE_HASH_CHANGED = 0`（412=412 byte-identical） |

---

## 1. 实现内容（8 项全站模板级优化）

1. **HOMEPAGE_SECTION_UI = PASS**：首页 `01/02/03/04` 编号放大为 23px + 金色渐变底色块 + 圆角标签（原 12px 透明装饰），成为真正的模块导视。
2. **COUNTRY_ENTRY_REDESIGN = PASS**：国家卡重构为一体化卡片——中文名 / 英文名 / 国家代码小号 / 风险等级 badge / **region chip（可点击、多区域分开显示）** / 完整一句风险摘要；移除「国家卡右侧区域模块」的割裂结构，Chad/Niger/Mali/Burkina Faso 等 13 国全部 chip 化（23 个 region chip 均可点击跳转 region 页）。
3. **NETWORK_REDESIGN = PASS**：
   - 标签分层：center 完整标签 / 1-hop 短标签（acronym 优先）/ 2-hop 极简标签；hover tooltip（SVG `<title>`）显示完整名；`label mode`（自动/完整/仅焦点）切换；
   - 安全边距：layout clamp 到 900×630 viewBox 内（X 74~826、Y 58~552），标签不再被上下边界裁切；
   - Node 详情面板：点击节点右侧面板显示中文名/英文名/类型/状态/关键关系数/打开实体页按钮；
   - Edge 详情面板沿用（双方、类型、状态、时间、来源、关系页按钮）。
4. **LEGEND_VISIBILITY_FILTER = PASS**：底部图例升级为交互式显示控制器——节点类型（组织/人物/国家）+ 关系分组（对抗冲突/从属效忠/活动于/协作关联/其他）共 8 个 checkbox，默认全选；取消即隐藏对应节点/边并自动 relayout（隐藏节点的边联动消失，无悬空边）；实时「当前可见 X 节点 · Y 关系」统计；全选（节点/关系分组各自）+ 重置视图；全部取消时显示空状态「当前筛选条件下无可见节点，请重新勾选图例项。」
5. **RELATION_HERO_SIMPLIFIED = PASS**：关系页顶部只保留人类可读信息（双方中文名/关系类型/状态/时间/可信度/时效自然语言/争议 badge）；`relation_id`、`freshness_status`、`display_ring`、成熟度等机器字段统一折叠进「技术元数据（展开）」；时效提示不再输出 `freshness=stale` 原始字段。
6. **BODY_ENTITY_AUTOLINK_EXPANDED = PASS**：正文 exact auto-linking 范围扩展——region 名称加入 index（链到 region 页），并修复国家合并时序（`buildAutoLinkIndex()` 移至国家 merge 之后，`尼日尔` 等国家名可链）。实测 JNIM↔Niger 正文 21 个「尼日尔」链接 + 2 个 region 链接；实体页正文 124 个 auto-links；仍为 exact canonical/alias + 最长优先 + denylist + URL/ID 保护，无 fuzzy。
7. **ENTITY_TOC_BEHAVIOR = PASS**：TOC 变窄、sticky 高度限制 44vh、内部滚动、提供「收起」按钮（点击折叠为轻量条）；mobile 默认折叠。
8. **ENTITY_SOURCE_ORDER = PASS**：「来源与注释」章节统一移到最后（所有 prose + uncertainty + ASIP 分析 + watch 之后），不再打断阅读；Al-Shabaab 23 节中 `sec-sources` 为最后一节。

---

## 2. QA 结果（全部针对真实公网 Preview URL）

### 2.1 Online Browser QA（28 页 = 14 页面 × desktop 1440 / mobile 390，28 张真实截图）

覆盖：homepage（含国家入口模块）/ Al-Shabaab / AQIM / EIJ / GIA / Lakurawa 实体页 / JNIM↔Niger / EIJ↔Al-Qaida / Lakurawa↔IS-Sahel 关系页 / 5 个 network focus（Al-Shabaab / AQIM / JNIM / ISIS-Somalia / Lakurawa）。

```
consoleErrors = 0
runtimeExceptions = 0
failedRequests = 0
brokenAnchors = 0
horizontalOverflow = 0（含 mobile）
```

全部 7 个 feature gate = true（homepage markers / country chips+summary / relation hero / entity TOC / sources order / network labels / legend visibility）。

### 2.2 Online Interaction QA（11/11 PASS）

- region auto-links：尼日尔 21 + region 2（exact canonical）✓
- entity body auto-links：124 ✓
- relation 技术元数据点击展开 ✓
- network 2-hop 展开（7→23 节点）✓
- node 点击详情面板（名称+8 关系+按钮）✓
- 图例取消隐藏组织节点 + 统计更新 ✓
- 图例全选恢复 ✓
- 全部取消显示空状态 ✓
- label mode full 显示完整标签 ✓
- 实体 TOC 收起按钮 ✓
- 实体 sources 最后（sec-sources）✓

### 2.3 Online Link QA（PASS）

公网 URL 爬虫：0 dead / 0 unreachable / 0 assets 404（基线 `../` 面包屑豁免为 KNOWN_BASELINE，与生产一致）。

### 2.4 本地验证（14/14 PASS）

修复了 3 个真实实现问题：① `renderBody` 接入 exact auto-linking（实体正文也互链）；② node label class 随 label mode 更新；③ auto-link index 在 country merge 后构建（国家名可链）。

---

## 3. 数据与 Production 隔离

| 门禁 | 值 |
|---|---|
| KNOWLEDGE_DATA_CHANGED | **0**（pre/post-ui-data-hashes.json，17 文件 SHA 一致） |
| PRODUCTION_CONTENT_CHANGED | **0**（`git diff 099fc2f..HEAD -- . ':(exclude)previews'` = 空） |
| PRODUCTION_NAMESPACE_HASH_CHANGED | **0**（412=412 byte-identical） |
| main / force push / production cutover | 均无 |
| Expansion D | 未启动 |
| gh-pages preview commits | `d17d057`（主体）+ `8b43aa3`（autolink/label fix）+ `d8311bc`（index 时序）——均仅 `previews/asip-intelligence-v2/**` |

---

## 4. 交付 URL

1. **Preview 首页**：https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/
2. **JNIM ↔ Niger 关系页**：https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/relation/jnim-niger-operates/
3. **Al-Shabaab 实体页**：https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/entity/al-shabaab/
4. **AQIM Network focus**：https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa/network/?focus=actor-aqim
5. **Before/After 截图**（`qa-artifacts-ui-final-polish-1/screenshots/`，28 张 after；本地 before 留存于 `qa-artifacts-uiux-v2-audit/screenshots/` 与上一轮在线 QA）：
   - `home_desktop.png`（首页编号 + 国家卡）
   - `entity_al_shabaab_desktop.png`（TOC + sources 末尾）
   - `rel_jnim_niger_desktop.png`（关系 hero 简化 + 正文国家互链）
   - `network_al_shabaab_desktop.png`（短标签 + 交互图例）
   - `network_jnim_desktop.png`（2-hop + 详情面板）
   - `entity_aqim_mobile.png` / `network_al_shabaab_mobile.png`（移动端）

```
UI_FINAL_POLISH_PACK_1 = PASS
```
