# ASIP Intelligence I3-C Browser Blocker Fix 最终验收报告

- 任务：I3-C Browser Blocker Fix（Network 运行时异常与节点焦点切换）
- 结论：**I3-C = CLOSED · ASIP Intelligence V1.0 = PRODUCTION · 八项 Gate 全部 PASS**
- 验收日期：2026-08-08
- 版本标签：`asip-intelligence-v1.0.1`（新建），`asip-intelligence-v1.0`（保留，未移动）

---

## 1. 根因链（经真实证据确认，非猜测）

| 层级 | 问题 | 证据 |
|---|---|---|
| 第一层 | route depth 不同，但 asset prefix 被错误统一（`../../..assets` 缺斜杠） | 初次公网 Network 加载 3 个 404：`/assets/js/intelligence/africa.js`、`/assets/css/style.css`、`/assets/css/intelligence.css` |
| 第二层 | 深层页面公共 JS/CSS 大量 404 | 临时全量扫描 708 → 648 → 60 个 broken assets（旧 QA 脚本含失效实体 slug 残余） |
| 第三层 | 公共 header（`renderHeader` 等价功能）未加载，产生 runtime exception 与 unhandled rejection | `ReferenceError: renderHeader is not defined`（QA 脚本使用了不存在旧路由时） |
| 第四层 | 资源修复后重新判断 Network focus 是否存在独立产品 bug | 单页 + 四视口专项全部通过 → **无独立 bug** |

**最终归类：`SECONDARY_FAILURE_CAUSED_BY_ASSET_PATH`**，无需修改任何产品 JS。

## 2. 修复方式（严格 source of truth，禁止全局替换）

- 修复对象：`intelligence/africa/_templates/*.html`（9 个模板，定向修改 asset prefix）
- 浅层索引页（regions/countries/entities/relations/sources/network）：`../../../assets/`
- 深层详情页（country/entity/region/relation 各 `<slug>`）：`../../../../assets/`
- Africa 根页：`../../assets/`（保持原样）
- 未修改：`data/intelligence/africa/`（知识内容零改动）、`assets/js/intelligence/africa.js`（产品 JS 零改动）
- 重新执行真实 generator：`python scripts/build_site.py --no-embed` → 151 routes、数据规模冻结（46 实体 / 78 关系 / 13 国家 / 96 来源 / 167 证据）

## 3. 验证证据（全部留存于 qa-artifacts-i3c/）

### 3.1 路由-资源矩阵与静态扫描
- `asset-path-route-matrix.json`：11 类路由 × 151 生成页，prefix 与目录深度逐一匹配（expected == actual_after）→ **PASS**
- `asset-resolution-scan.json`：151 HTML 全量扫描，`missing_local_assets=0`、`broken_script_src=0`、`broken_stylesheet_href=0`；公共资源 `common.js / africa.js / network.js / intelligence.js / style.css / intelligence.css` 全部存在 → **PASS**

### 3.2 公网浏览器 QA（无扩展 Edge，cache disabled）
- 代表页门禁（11 类页面 @1366）：`runtimeExceptions=0, consoleErrors=0, failedRequests=0, brokenAssets=0, overflow=0`，公共 header 逐页加载成功 → **PASS**
- 完整公网 QA（85 页 = 61 路由 @1366 + 6 代表路由 × 1920/1366/768/390）：全部指标 0，`node_click_focus_switch=true` → **PASS**
- Network 单页诊断（公网）：`focus_before=actor-jnim → clicked=actor-al-qaida → focus_after=actor-al-qaida`，URL focus 与右侧面板同步，邻居集合变化 → **PASS**
- Network 四视口专项（公网，每视口 10 次真实节点点击）：1920/1366/768/390 全部 `all_focus_switches=true`，0 异常 → **PASS**

### 3.3 数据冻结与生产隔离
- `browser-fix-data-freeze-recheck.json`：**KNOWLEDGE_DATA_CHANGED=0**；source == dist == gh-pages 三处 sha256 完全一致（等于 v10 冻结基线）→ **PASS**
- `browser-fix-production-diff.json`：白名单（`intelligence/africa/**` + `common.js` + `africa.js`）170 文件与生产完全一致；主站 10 文件仅 build 元数据差异（`browser-fix-mainsite-diff-review.json` 证明 0 业务行）；RC 预览 `previews/**` 313 文件保留区；`UNEXPECTED_MODIFIED=0, UNEXPECTED_DELETED=0` → **PASS**

## 4. 发布记录

| 项目 | 值 |
|---|---|
| 源码分支 | `feature/asip-intelligence-v10-i3c-production` |
| 源码 HEAD | `d1382a9`（修复主提交 `db9ba76`，QA 收尾 `16e180a`、`d1382a9`） |
| gh-pages 发布提交 | `b666fef`（普通 push，无 force） |
| Pages workflow | run `31265830778`，head_sha `b666fef`，conclusion **success** |
| I3C_BROWSER_FIX_GH_PAGES_SHA | `b666fefbd82e68e9d479020d74a4240e35fde199` |
| 正式公网路径 | `https://kenan032005.github.io/asip-site/intelligence/africa/` |
| RC 预览（保留） | `https://kenan032005.github.io/asip-site/previews/asip-intelligence-v1.0-rc1/intelligence/africa/` |

## 5. 八项 Gate 汇总

| Gate | 状态 |
|---|---|
| I3C_BASELINE_GATE | PASS |
| I3C_REGRESSION_GATE | PASS |
| I3C_PRODUCTION_DIFF_GATE | PASS |
| I3C_DEPLOYMENT_GATE | PASS |
| I3C_PUBLIC_QA_GATE | **PASS**（原 OPEN，本轮关闭） |
| I3C_MAIN_SITE_GATE | PASS |
| I3C_DATA_FREEZE_GATE | PASS |
| I3C_ROLLBACK_GATE | PASS |
| **overall_gate** | **PASS** |

## 6. 标签记录

- `asip-intelligence-v1.0`：`45856a21`（tag object）→ `7880cf9c`（commit）——**保持原样，未移动、未覆盖**
- `asip-intelligence-v1.0.1`：`39cf54b2`（tag object）→ `d1382a9`（commit）——**已创建并推送**

## 7. 结论与后续边界

1. I3-C 正式关闭，ASIP Intelligence V1.0 处于正式生产状态。
2. 本轮未执行 I3-D；后续阶段需由用户另行启动。
