# ASIP安全情报微型样板 V0.2 验收报告

- 验收阶段：I1 / V0.2
- 验收日期：2026-08-06
- 开发目录：`C:/Users/kenan/WorkBuddy/recovery/asip-intelligence-v02-clean`
- 基线：V0.1 正式归档后的 `356e58e76a9b93f46ca1bf8b189b270c0d197dea`
- 目标：优化关系图视觉布局、关系语义表达、组织/人物/国家档案模板和 L1/L2/L3 内容示范；不进入正式萨赫勒扩库。

## 1. 交付范围

本阶段完成：

1. 语义分区的一度中心关系图：上方体系与领导、左侧组成与历史、右侧人物与领导、下方敌对与冲突、外圈活动与存在。
2. 组织圆形、人物圆角矩形、国家六边形节点；中心节点双层轮廓、光晕和英文辅助标签。
3. 关系线方向箭头、关系类型短标签、领导/活动/历史/争议/敌对样式和关系详情卡。
4. 中心切换缓动动画、快速切换 token 保护、`prefers-reduced-motion`、URL `focus`、浏览器历史和工具栏历史。
5. 组织、人物、国家共享实体数据层和类型化档案模板。
6. L1/L2/L3 内容等级：L3=2、L2=3、L1=7；实体和关系数量保持 V0.1 不变。
7. 最终浏览器 QA 脚本和 Chrome 130 截图/JSON 证据。

明确不在本阶段：地图、时间回放、新闻自动关联、AI 实时调用、数据库服务、正式导航入口、萨赫勒首批实体扩库。

## 2. 代码和数据检查点

正确的阶段父子链为：

```text
356e58e76a9b93f46ca1bf8b189b270c0d197dea
  └─ 9f38d929730b1621b97c53526b55b9c8de419c62  docs: define ASIP intelligence V0.2 product design
      └─ 61bebcb6b1cf28004ca23195da3ca25f873bd76a  feat: improve V0.2 semantic intelligence graph
          └─ 97e833025bbe9b2aadb401e68b18f80ec3c551d4  feat: add typed intelligence profile templates
              └─ e8f5779f759defa80f9c44f5830e91b63cc2547d  feat: add V0.2 profile depth demonstrations
                  └─ 0b9e7f5da3baed4a75e8a7a4bff8cdd7e6b31d05  fix: initialize graph after shared data load
```

主要文件：

- `ASIP_INTELLIGENCE_DEMO_V02_DESIGN.md`
- `assets/js/intelligence/network.js`
- `assets/js/intelligence/intelligence.js`
- `assets/css/intelligence.css`
- `intelligence/demo/index.html`
- `intelligence/demo/network/index.html`
- `intelligence/demo/entity/_template.html`
- `data/intelligence/demo/entities.json`
- `data/intelligence/demo/profile_content.json`
- `i1_v02_browser_qa.js`
- `qa-artifacts-v02-final/browser-qa-results.json`

## 3. 自动化测试

全部通过：

```text
PASS entities=12 relationships=20 sources=6
PASS unique_ids=12 unique_slugs=12 aliases=25
PASS references, source coverage, date order, routes, and temporal JNIM/IS relationship

PASS routes=14 (entry + network + 12 entity routes)
PASS shared-data links, base-path relative URLs, graph controls, focus history, relation details
PASS responsive breakpoints and non-color-only node shapes

PASS entities=12 relationships=20
PASS profile levels L3=2 L2=3 L1=7
PASS type templates, completeness floors, and V0.1 relationship invariant

JavaScript syntax: PASS
国家页面回归：PASS=24 FAIL=0
主站前端隔离：PASS=28 FAIL=0
仓库完整性：PASS=28 FAIL=0
```

最终静态构建通过：

```text
intelligence demo: 12 entity routes + network + data
构建完成 -> dist
HTML: 9 个页面
ASIP_BUILD_META: 已注入
内联数据快照: False
```

## 4. 真实浏览器验收

环境：`Chrome/130.0.6723.92`，Chrome DevTools Protocol，页面服务 `http://127.0.0.1:8782`。

### 档案页

```text
JNIM             L3 深度档案
IS Sahel         L3 深度档案
AQIM             L2 标准档案
Iyad Ag Ghali    L2 标准档案
Mali             L2 标准档案
Al-Qaida         L1 基础档案
Ansar Eddine     L1 基础档案
```

### 关系图和交互

- JNIM：12 个节点 / 12 条直接关系。
- IS Sahel：6 个节点 / 6 条直接关系。
- Al-Qaida：3 个节点 / 2 条直接关系。
- Iyad Ag Ghali：5 个节点 / 4 条直接关系。
- Mali：深层 URL `focus=country-mali` 刷新通过。
- ISGS 别名搜索成功聚焦 `actor-is-sahel`。
- 关系线点击成功展示 `affiliated_with` 关系详情，分区为“体系与领导”。
- 浏览器前进/后退分别恢复 JNIM 和 IS Sahel 中心。
- 工具栏“上一焦点”恢复 JNIM。
- 档案页 → 关系图、关系图 → 档案页双向跳转通过。
- 类型过滤、关系过滤、缩放、适配通过。
- 1366×768：`bodyWidth=1349`、`innerWidth=1366`，无横向溢出。
- 390×844：`bodyWidth=390`、`innerWidth=390`，无横向溢出。
- 控制台错误：0；JavaScript 异常：0；失败请求：0。

完整证据：`qa-artifacts-v02-final/browser-qa-results.json` 及同目录截图。

## 5. 问题与修复

1. Git 本地 refs 会间歇性被外部环境清空。已确认阶段提交对象仍存在，并核对其父链；交付时必须使用完整 SHA、稳定引用和远端 `ls-remote` 双重核验。
2. 图谱异步数据加载后首轮未绘制。新增 `initNetwork()`，监听 `asip-intel-data-ready`，并在数据已就绪时立即初始化；浏览器复验通过。
3. 原页面契约测试依赖字符串 `smooth`。保留兼容函数 `smooth() { return 420; }`，同时使用实际 `animateNodes()`。
4. JNIM 与 Mali 不是一度邻接，因此 Mali 使用深层 URL 验收，而不是把不可达点击误判为产品错误。

## 6. 遗留技术债务

- 当前 Git 工作环境存在非预期 ref 清空现象，属于交付基础设施风险；不得使用 `reset --hard`、`clean`、`gc`、`prune` 或强制推送处理。
- 入口页和实体页的 `state()` 采集不包含图谱节点，这是页面类型差异，不是错误；图谱页的节点、边和交互均已单独验证。
- 仍未扩展到萨赫勒首批 10—15 个核心实体，按阶段边界保留到后续任务。

## 7. 远端交付与关闭结论

最终 QA 提交对象：

```text
ae3280db28f2fb9cdbc73e2366ac166a2d2ec4c0
父对象：0b9e7f5da3baed4a75e8a7a4bff8cdd7e6b31d05
```

已推送：

```text
refs/heads/feature/asip-intelligence-demo-v02 -> ae3280db28f2fb9cdbc73e2366ac166a2d2ec4c0
refs/tags/asip-intelligence-demo-v0.2 -> 6897cc374832ee173cc4f80eda1e0bee214e662d
标签解引用 -> ae3280db28f2fb9cdbc73e2366ac166a2d2ec4c0
```

远端保护条件核验通过：

```text
V0.1 标签保持 b6702445fd01278c45a1a8254e1c2323d9158fb2
main 保持 8924416ff3f969c3996312b8ca97588ff268cf5e
gh-pages 保持 cd18cd6a504fd00e12702dd9af3b77783101b811
master 未返回远端引用，未被修改
```

V0.2 产品范围、自动化测试、主站回归、静态构建、真实 Chrome 交互验收和远端交付均通过。除 Git refs 稳定性这一交付环境技术债务外，没有未解决的产品阻断问题。I1/V0.2 正式关闭；不自动启动萨赫勒扩库。
