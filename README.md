# 非洲地区社会安全信息平台（ASIP）

**Africa Security Information Platform**

一个面向企业管理人员的中东以外区域社会安全信息聚合平台。本仓库是**独立新建**项目，
与既有中东平台（mesip-site）**无任何代码或仓库耦合**，仅参考其页面风格、信息展示逻辑与操作方式。

- 建议网站名：非洲地区社会安全信息平台
- 英文副标题：Africa Security Information Platform
- 仓库（已创建）：`asip-site`
- 线上地址（已上线）：`https://kenan032005.github.io/asip-site/`

> 第一阶段为**可运行框架版**：已完成网站框架、22 国风险分类、事件数据结构、六国日报框架
> 与 GitHub Pages 部署链路。实时信息采集（各信息源适配器）为后续阶段，按"先框架、再接入"推进。

---

## 一、项目文件结构

```
asip-site/
├── index.html              首页
├── events.html             最新事件（多维筛选）
├── countries.html          国家选择（四类风险分组）
├── country.html            国家详情（?country=中文名）
├── event.html              事件详情（?id=）
├── reports.html            日报列表
├── report.html             日报详情（?country=&date=）
├── disease-risk.html       非洲传染病风险（建设中占位）
├── 404.html
├── assets/
│   ├── css/style.css       统一样式（风险配色：低=蓝/中=黄/高=橙/极高=深红）
│   └── js/
│       ├── api.js         数据层（优先内联快照，回退 fetch + localStorage）
│       ├── common.js       表头/页脚/风险徽章/北京时间换算/筛选
│       ├── home/events/... 各页逻辑（内联于对应 HTML 的 <script>）
├── data/                   运行时数据（单一数据源）
│   ├── risk-levels.json    22 国四类固定顺序 + 风险配色
│   ├── countries.json      22 国基础信息（首都/区域/基准等级/是否日报）
│   ├── events.json         事件数据（当前为演示占位）
│   ├── sources.json        五层信息源（均 tested=false，启用前需测试）
│   ├── status.json         更新时间/下次更新/计数/演示模式开关
│   └── latest-summary.json 首页概览/指标/各区块摘要
├── reports/<国家>/          六国日报（按日期归档的 JSON）
├── scripts/
│   ├── collect.py           采集流水线（规范化→去重→核实→翻译）
│   ├── normalize.py         字段规范化与校验
│   ├── deduplicate.py       事件去重（多源合并）
│   ├── verify.py            可信度推断
│   ├── translate.py         翻译/摘要占位（不编造）
│   ├── generate_reports.py  六国 12 节结构日报生成
│   └── build_site.py        构建静态站点到 dist/
├── config/
│   ├── keywords.json        多语言安全关键词（采集检索用）
│   └── glossary.json        专有名词词库（占位）
├── tools/setup_gh_pages.py  GitHub Pages 一次性初始化
├── .github/workflows/deploy.yml  构建+校验+部署（含 22:00 北京时间定时）
├── server.py                本地静态预览（零依赖）
├── .nojekyll
└── README.md
```

**单一数据源原则**：国家名单只维护 `data/countries.json`；风险等级只维护 `data/risk-levels.json`；
信息源只维护 `data/sources.json`。前端、报告生成、校验均从这唯一来源读取，不多处硬编码。

---

## 二、本地预览

```bash
cd asip-site
python server.py              # 默认 http://127.0.0.1:8000
PORT=8080 python server.py    # 自定义端口
```

> 也可直接双击 `index.html` 打开（已内联数据快照，离线可渲染）。

---

## 三、生成日报 / 构建站点

```bash
# 生成今天（北京时间）的六国日报
python scripts/generate_reports.py
python scripts/generate_reports.py --date 2026-07-20
python scripts/generate_reports.py --dry     # 仅预览

# 构建静态站点到 dist/（供 GitHub Pages 发布）
python scripts/build_site.py
```

---

## 四、自动更新与部署

### GitHub Pages 部署链路（当前已上线）
- 站点已上线：`https://kenan032005.github.io/asip-site/`
- 部署方式：构建产物（`dist/`）直接推送到 `gh-pages` 分支，Pages 以该分支根目录为源。
- `main` 分支保存全部源码（不含密钥、不含工作流文件，符合安全规范）。

### 自动定时更新（Actions 待启用）
- `deploy.yml` 已编写完成，保存在磁盘 `.github/workflows/`（因本次部署所用令牌仅含 `repo` 权限、不含 `workflow`，故未推送至仓库）。
- 启用方法（二选一）：
  1. 提供带 `workflow` 权限的令牌后，运行 `git add .github && git push` 推送工作流；或
  2. 在 GitHub 网页端确认 Pages 源为 `gh-pages` 后，由 Actions 接管。
- 启用后：北京时间每天 22:00（cron `0 14 * * *` UTC）自动运行 数据校验 → 生成日报 → 构建 → 部署。

### 当前每日更新由 WorkBuddy 驱动（符合需求"优先由 WorkBuddy 每天北京时间 22:00 执行"）
- 在 WorkBuddy 中配置每日 22:00 自动化任务，执行：抓取→去重→翻译→核实→生成六份日报→更新首页/事件/国家→构建→推送 `gh-pages`。
- 亦可手动执行（见第五节）。
- **第一阶段**尚未接入实时抓取；日报在"无事件"时按文档生成默认表述，保证链路可用、不产生空白覆盖。

### 失败后重新执行
- 在仓库 **Actions** 页面对应工作流点击 **Re-run jobs**；或本地 `python scripts/build_site.py` 后手动部署。
- **失败保护**：仅当构建与校验全部成功才部署；`gh-pages` 上一次成功内容持续对外，不会用空白覆盖历史数据，不删除历史日报。

---

## 五、手动更新方法

```bash
# 1) 维护数据（编辑 data/*.json 或用脚本处理 events.json）
python scripts/collect.py --write     # 运行处理流水线并写回

# 2) 生成日报
python scripts/generate_reports.py

# 3) 构建并本地预览
python scripts/build_site.py
python server.py

# 4) 推送到 GitHub（首次初始化见第七节）
git add -A && git commit -m "更新数据" && git push
```

---

## 六、信息源配置（data/sources.json）

分五层（详见需求文档第十三~十六节）：
1. 官方和直接来源（政府/使领馆/联合国/卫生等）
2. 国际通讯社与大型媒体（Reuters/AP/AFP/BBC/…）
3. 中文媒体与泛非/区域媒体
4. 国际/区域组织、人道主义与研究机构
5. 社交媒体（仅作线索，不直接作为已核实事实）

> 所有条目 `tested` 均为 `false`，表示**尚未逐一测试可访问性、更新频率与抓取稳定性**。
> 正式启用前须逐源验证；无法合法访问的标记为 `paused`，**不得绕过登录/付费墙/反爬**。

---

## 七、GitHub 仓库与 Secrets 配置

### 方式 A：一次性初始化脚本（需 repo 权限 PAT）
```bash
python tools/setup_gh_pages.py
# 按提示输入：令牌、用户名（默认 kenan032005）、仓库名（默认 asip-site）
```
该脚本会创建仓库、推送 `dist/` 到 `gh-pages`、开启 Pages。

### 方式 B：连接器 / Actions 自动部署
部署由 `deploy.yml` 使用仓库 **GITHUB_TOKEN** 自动完成，无需手动令牌。
**任何密钥（API Key、翻译服务密钥等）只放在 GitHub Secrets 或环境变量**，
绝不写入 HTML / JS / JSON / Git 提交记录 / README。本仓库当前不含任何明文密钥。

---

## 八、合规与安全（必须遵守）

- 仅发布公开信息；不抓取/展示企业内部文件、内部安保安排、员工信息、精确坐标、未公开研判、密钥。
- 尊重 robots.txt、访问频率限制与网站条款；不绕过登录/付费墙/验证码/地区限制。
- 无法合法访问的来源标记 `paused`，不得通过不合规手段抓取。
- 所有时间统一为**北京时间（UTC+8）**，并明确标注"北京时间"。
- 不得编造新闻、链接、来源名称或官方账号；待核实信息进入"待核实"区域，不进入日报主要结论。

---

## 九、验收对照（第一阶段目标）

| 项 | 状态 |
|---|---|
| 原中东网站未被修改 | ✅ 独立仓库/目录，零耦合 |
| 新非洲网站可独立访问 | ✅ 已上线 https://kenan032005.github.io/asip-site/ |
| 顶部导航严格五项 | ✅ 首页/最新事件/国家/日报/非洲传染病风险 |
| 22 国完整显示 | ✅ 单数据源 |
| 四类风险与顺序准确 | ✅ risk-levels.json 固定顺序 |
| 极高风险 8 国顺序正确 | ✅ 乍得…利比亚 |
| 国家可进详情页 | ✅ country.html?country= |
| 事件可按国家/类型筛选 | ✅ events.html |
| 六国分别生成日报 | ✅ generate_reports.py |
| 日报按日期+国家归档 | ✅ reports/<国>/<日期>.json |
| 每条信息有来源+原文链接 | ✅ 事件字段 |
| 页面时间均为北京时间 | ✅ 前端统一换算 |
| 每天 22:00 更新 | ⚠️ Actions 定时待启用（需 workflow 令牌）；当前由 WorkBuddy/手动 22:00 更新 |
| 失败不覆盖上一版 | ✅ 仅成功才部署 |
| 传染病页仅占位 | ✅ 无虚构数据 |
| 手机端正常 | ✅ 响应式 CSS |
| 仓库无明文密钥 | ✅ .gitignore + Secrets |
| 单源失效不整体报错 | ✅ 各页 try/catch + 空态 |

---

## 十、已知限制（第一阶段）

- 实时信息采集适配器尚未实现；当前 `events.json` 为**演示占位数据**（已标注 `is_demo`，上线前须清空并置 `status.demo_mode=false`）。
- 日报在"无事件"时按文档生成默认表述，未做自然语言研判（后续接入经授权的摘要能力）。
- 传染病风险模块仅占位，未接入任何疫情数据源。
- 六国日报的"持续跟踪/趋势判断/建议"为模板化内容，真实运行需结合多日事件与人工研判。
