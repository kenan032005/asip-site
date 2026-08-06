# I3-Prep-A 关系图布局分散化、关系视觉编码与焦点页入口修正报告

- 执行日期：2026-08-06
- 分支：`feature/asip-intelligence-v10-i3-prep-a`（基于 I2-B 最终提交 `1582e83`）
- 工作目录：`C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-trusted`
- 范围：仅修正 `/intelligence/africa/network/` 图谱可读性与交互入口；不扩库、不新增实体/关系、不改事实结论

---

## 1. 修改的问题

| # | 问题 | 根因 |
|---|---|---|
| 1 | 节点集中在一个方向，未利用画布其余区域 | 布局 `start = -π/2 - 0.55π`、`spread ≤ 1.15π`，全部节点分布在顶部约 207° 扇形内（实测 I2-B 版 JNIM 中心象限分布 1/0/6/6，最大空隙 183°） |
| 2 | 不同关系类型视觉区分度不足 | 旧 `classFor` 仅区分 hostile/historical/leadership/presence/normal 5 类，且图例只列 3 种线型 |
| 3 | 中心焦点缺少"进入详细页"入口 | 中心节点点击行为与外围节点相同（切换中心）；右侧信息卡为静态占位；焦点名称区无链接 |

## 2-3. 布局算法调整（360 度分散 + 重心平衡）

`assets/js/intelligence/africa.js` `layout()` 重构：

- **全圆 360 度均匀展开**：`spread = 2π`，起始角 `-π/2 + 圈层相位`（内圈 0、中圈 π/6、外圈 π/3），同圈层节点按 `2π/n` 等分；不同圈层起始角交错，避免跨圈层共线射线。
- **圈层半径加大并自适应**：`RINGS = { inner: 175, middle: 265, outer: 345 }`（原 158/248/338）；节点多时按最小间距（桌面 96px、窄屏 80px）循环扩径（上限 350），y 方向椭圆系数 0.9 保证不越出画布。
- **整体重心平衡（新增）**：圈层定位 + 碰撞推挤 3 轮后，计算非中心节点重心；当重心偏离中心 >14px 时整体平移 60% 并再推挤 2 轮——保证"虽然满足最小间距，但视觉重心不偏向一边"。
- 保留平滑过渡（`positions` 记忆 + 70/30 插值）、碰撞推挤、窄屏降距等既有能力。

**量化对比（Edge 151 实测，JNIM 中心 13 节点）**：

| 指标 | 修正前（I2-B） | 修正后 |
|---|---|---|
| 象限分布 | 1 / 0 / 6 / 6（12/13 挤在上左） | 4 / 4 / 3 / 2 |
| 最大象限占比 | 46% | 31% |
| 最大空隙角 | 183° | 56° |
| 重心偏移 | —（偏向顶部） | 7px |

多中心验证：ISWAP 象限 1/2/2/2（maxShare 29%、重心 3px）；乍得 1/0/2/1（覆盖 3 象限，旧版 4 节点全挤顶部 207°）；苏丹/莫桑比克各 2 个邻居呈对向分布（直径两端，天然合理）。

## 4. 关系颜色/线型设计

`relationGroup()` 替代旧 `classFor()`，7+2 组稳定配色（克制、专业、色觉友好）：

| 组 | 包含类型 | 颜色 | 线型 |
|---|---|---|---|
| conflict | hostile_to / fought_against / competes_with | 红 #b04848 | 实线 2.4px |
| allegiance | pledged_allegiance_to / affiliated_with / constituent_of / part_of_network | 蓝 #14507e | 实线 |
| presence | operates_in / active_in_region | 绿 #37715c | 虚线 4-5 |
| crossborder | cross_border_link | 紫 #7d5a94 | 点线 2-4 |
| cooperation | cooperates_with / allied_with | 青 #2e6e8e | 实线 |
| support | supported_by / supports / alleged_support | 金 #8a641c | 虚线 5-4 |
| historical | historically_associated_with | 灰 #9aa4ad | 长虚线 8-6 |
| leadership | led_by / founded_by / member_of_force / deployed_in / political_affiliation | 深蓝 #0f3a5d | 实线 2.6px |
| temporal | 时间敏感（temporal_sensitive） | 橙 #c9952b | 短虚线 2-4 |

箭头（marker）按组着色；关系标签底色按组微调。悬停/选中仍统一金色高亮（交互反馈，不混淆组色）。实测 6 个组实际出现在当前数据（allegiance/presence/crossborder/conflict/historical/leadership），6 种不同 stroke 色 + 线型。

## 5. 图例实现

`network.html` 的 `.graph-legend` 扩展为三段式：**节点形状**（组织/人物/国家）、**圈层**（内/中/外）、**关系类型**（7 组：敌对/冲突、隶属/效忠、活动于、跨境关联、合作/结盟、支持/据称支持、历史关联），每项用同色同线型的 `legend-line` 色条。样式简洁（11px、浅灰文字），不喧宾夺主。

## 6. 中心焦点详细页入口

三重入口（`draw()` 动态更新，`entityHref()` 自动区分国家/实体路由）：

1. **中心节点点击进入档案页**：中心节点 click → `window.location.href = entityHref(id)`（国家 → `/intelligence/africa/country/<slug>/`，组织/人物 → `/intelligence/africa/entity/<slug>/`）；外围节点点击仍切换中心（不回归）。
2. **右侧信息卡**：`#nodeInfo` 实时显示焦点名称/类型/重要程度/时效徽章/简介 + 按钮「进入国家详细页 / 查看详细档案」。
3. **焦点名称下方链接**：`#focusLink`「查看档案 / 进入国家页」，随焦点切换更新 href 与文案。

实测：点击乍得中心 → `country/chad/` ✅；点击 JNIM 中心 → `entity/jnim/` ✅；莫桑比克焦点时链接文案「进入国家页」→ `country/mozambique/` ✅；外围节点（MNJTF）点击切换中心 ✅。

## 7. 标签位置优化

关系标签从中点（半径一半处，聚拢在中心圆周附近）移至**连线 62% 处**（靠近目标节点），并沿法线偏移 16px、按连线方向翻转——标签不再堆在中心附近，不遮挡箭头/线条/中心标题。窄屏（≤560px）仍按既有规则隐藏标签层。

## 8. 浏览器测试结果（Edge 151，`--disable-extensions` 干净实例）

```text
布局分散：JNIM 4/4/3/2（maxShare 31%、maxGap 56°、重心 7px）；ISWAP 1/2/2/2；乍得/苏丹/莫桑比克合理
关系编码：6 组实际出现，6 种 stroke 色 + 线型；图例完整
焦点入口：国家→country/chad ✅ 实体→entity/jnim ✅ 外围切换 ✅ 右侧卡按钮 ✅ 焦点链接 ✅
交互不回归：关系线点击 → 关系详情卡（含 bay'ah 语义说明）✅
深层 URL 刷新：?focus=country-chad（5 节点/乍得）、?focus=actor-iswap（8 节点/ISWAP）✅
响应式：1366 与 390 均无横向溢出 ✅
控制台错误 0 · 未捕获异常 0 · 网络失败 0
全量回归：14 项测试 PASS=2578 FAIL=0 · node --check 3/3 · 构建 125 路由
```

截图（`qa-artifacts-i3prepa/`）：layout-chad / layout-jnim / layout-iswap / layout-sudan / layout-mozambique / before-chad / before-jnim（修正前基线）/ encoding-jnim / entry-chad-click / entry-jnim-click / entry-peripheral-switch / edge-click / viewport-1366 / viewport-390 及 browser-qa-results.json。

## 9. 结论

| 问题 | 是否解决 |
|---|---|
| 节点堆叠/一侧集中 | ✅ 360 度全圆分布 + 重心平衡；JNIM 象限 1/0/6/6→4/4/3/2，最大空隙 183°→56° |
| 关系难辨认 | ✅ 7 组稳定颜色 + 线型差异 + 完整图例 |
| 焦点页入口缺失 | ✅ 中心点击 / 右侧按钮 / 焦点链接三入口，国家与实体路由正确 |

**交付**：分支 `feature/asip-intelligence-v10-i3-prep-a`（提交见 Git 记录）；未合并 main/master、未部署生产、未接入主导航。任务完成即停止，不自动进入下一轮深度扩库。

*修改文件：`assets/js/intelligence/africa.js`、`assets/css/intelligence.css`、`intelligence/africa/_templates/network.html`、`i3prepa_browser_qa.js`、`i3prepa_before.js`、`qa-artifacts-i3prepa/`、`i3prepa-qa-summary.json`。*
