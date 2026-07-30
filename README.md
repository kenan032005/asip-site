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
│   ├── canonical/          规范数据层（schema_version=2.0）：articles / event_clusters / quarantine / migration_state / idempotency_report
│   ├── public/             发布视图（由 canonical 单向生成）：published_events.json / current_metrics.json
│   ├── risk-levels.json    22 国四类固定顺序 + 风险配色
│   ├── countries.json      22 国基础信息（首都/区域/基准等级/是否日报）
│   ├── events.json         事件数据（★ 单向生成视图：generated_from_canonical，业务脚本不得直接写）
│   ├── sources.json        五层信息源（2.0 升级格式，legacy_payload 保留原字段；均 tested=false）
│   ├── status.json         更新时间/下次更新/计数/演示模式开关
│   └── latest-summary.json 首页概览/指标/各区块摘要
├── reports/<国家>/          六国日报（按日期归档的 JSON）
├── scripts/
│   ├── pipeline_runner.py   ★ 统一编排器（唯一运行入口，见第十二节）
│   ├── pipeline_core.py     ★ 时区/run_id/锁/统计/闸门 公共库
│   ├── validate_pipeline.py ★ 分阶段校验器（失败非零退出码）
│   ├── tests/               单元与回归测试（test_country / test_stage1_pipeline / test_stage2_schema_repo / test_repository_integrity / test_no_local_paths）
│   ├── data/                规范数据层模块：repository（唯一读写入口）/ identifiers（稳定 SHA-256 ID）/ normalizers / publication_policy（确定性发布闸门）/ schema_validator / migrate_stage2 / compatibility_export / validate_stage2 / verify_idempotency
│   ├── collect.py           采集流水线（规范化→去重→核实→翻译，由编排器调用；写入 canonical，不直接写旧池）
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

**唯一运行入口是统一编排器**（数据文件 `events.json` 等均为单向生成视图，禁止手工编辑）：

```bash
# 完整链路：pull → 测试 → 语义/导出 → 汇总 → 日报 → 48 项校验 → 构建 → 部署 → 线上验证
python scripts/pipeline_runner.py --mode full --trigger manual

# 仅校验（不提交、不部署）
python scripts/pipeline_runner.py --mode validate-only

# 本地预览
python server.py
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
| 每天 22:00 更新 | ✅ WorkBuddy 自动化已实测（2026-07-29 22:53 定时触发 run_id `20260729T225349+0800_37nrdr` 全链路成功）；Actions 定时为备用（blocked_by_permission：PAT 无 workflow 权限） |
| 失败不覆盖上一版 | ✅ 仅成功才部署 |
| 传染病页仅占位 | ✅ 无虚构数据 |
| 手机端正常 | ✅ 响应式 CSS |
| 仓库无明文密钥 | ✅ .gitignore + Secrets |
| 单源失效不整体报错 | ✅ 各页 try/catch + 空态 |

---

## 十、已知限制

- 线上事件为**历史迁移保留数据**（`legacy_migration_preserved=true`，未按当前发布政策重新核实，不计入 24h/7d 统计）；当前政策通过（`current_policy_passed=true`）事件数为 0，待实时采集与核实链路产出新事件后增长。
- 日报在"无事件"时按文档生成默认表述，未做自然语言研判（后续接入经授权的摘要能力）。
- 传染病风险模块仅占位，未接入任何疫情数据源。
- 六国日报的"持续跟踪/趋势判断/建议"为模板化内容，真实运行需结合多日事件与人工研判。

---

## 十一、第二轮整改（乍得/尼日尔，2026-07）

针对国家误判、无关信息、分类错误、日报时间窗四类问题完成系统性整改：

### 11.1 国家识别（scripts/collectors/country_runner.py）
- **词边界匹配**：`(?<![a-zà-ÿ0-9])kw(?![a-zà-ÿ0-9])`，杜绝 `Lac→place`、`riot→patriot` 类误匹配。
- **结构化判定字段**：每条候选输出 `event_location_country / mentioned_countries / country_match_score / matched_country_entities / matched_location_entities / excluded_entities / country_decision_reason`。
- **排除优先**：Nigeria / Niger State / Niger Delta / Nigerian Army / Benin City 等命中即排除，除非同现 Niamey、"République du Niger" 或尼日尔行政地名等强实体。
- **跨国规则**："Lake Chad / bassin du lac Tchad" 且无乍得境内行政地名 → 判 `regional`（跨国事件），不落入乍得。
- 判定不明（仅裸词 "niger" 无地名）→ `unclear`，进待核实，不直接发布。
- 单元测试：`scripts/tests/test_country.py`，24/24 通过。

### 11.2 相关性与事件分类
- 两级相关性过滤：确定性排除（体育/农业/宣传/会议/纯经济，中法英三语词表）+ 语义评分，`relevance_score >= 0.70` 才可进入发布链路。
- 事件类型从标准枚举按优先级判定，**不再默认 armed_conflict**。

### 11.3 采集暂存与发布架构（厘清）
- **采集暂存（草稿，非发布数据源）**：`raw_candidates.json`（原始候选）→ `pending_events.json`（相关+国家判定通过）。这是采集阶段的草稿池，**不是**对外发布的数据源。
- **规范数据层（唯一真实来源）**：`data/canonical/`（articles / event_clusters / quarantine / migration_state，schema_version=2.0, pipeline_version=2）。所有发布判定以 canonical 为准；该目录**仅用于内部数据处理，不部署到公网**。
- **发布视图（唯一当前公开层）**：`data/public/published_events.json` / `current_metrics.json`，由 canonical 单向生成；`build_summary.py` / `generate_reports.py` 只读取 public 层。
- **遗留兼容视图（仅旧前端兼容，非主架构）**：`data/events.json`、旧池（pending/raw/quarantine_events）由 `compatibility_export` 单向生成，带 `generated_from_canonical + do_not_edit_manually` 信封，**业务脚本不得直接写**，且**不部署到公网**。
- **风险分级 A/B/C 仅为采集相关性分级**，并非发布准入；当前发布准入统一走 `current_policy_passed`（且 `quality_gate_passed` 通过、`publication_status` 合规、非历史迁移保留）。C 级单源只进待核实池，不发布。
- 历史数据清洗：`scripts/clean_events.py`（误判/无关移入 `data/quarantine_events.json` 隔离，不物理删除）。

### 11.4 信息源扩容（data/sources.json）
- 信息源的**配置总数 / 启用数 / 分国家分布以 `data/sources.json` 与 `data/status.json` 的实时内容为准**，本文档不再硬编码数量；查询方式：`python -c "import json;d=json.load(open('data/sources.json',encoding='utf-8'));print(len(d.get('sources',d)))"`，或直接查看线上 `data/status.json` 的源统计字段。
- **强制接入路透社（Reuters）与新华网（Xinhua）**：通过 GDELT ArtList 域名限定检索（`domain:reuters.com` / `domain:news.cn` 等）合法公开发现，不抓取付费全文。
- 五层结构：当地媒体（RSS）/ 国际媒体（GDELT）/ 联合国与人道机构（ReliefWeb API + GDELT）/ 中国官方与媒体 / 官方机构。

### 11.5 日报时间窗与前端
- 日报窗口严格为**北京时间前一日 22:00 → 当日 22:00**，报告含 `reporting_window_start/end`、新增/持续事件拆分。
- 前端 `Promise.allSettled` 按模块隔离加载失败，单一数据文件异常不再导致整页无法加载。

### 11.6 自动化
- WorkBuddy 自动化：每 2 小时增量采集 + 每日北京 22:00 全量核实与日报。
- GitHub Actions 备用：`.github/workflows/auto-update.yml`（每 2 小时 / 北京 21:30 补充 / 22:00 日报，需 workflow 权限 PAT 推送启用）。

---

## 十二、第一阶段收尾整改（2026-07-29）

针对"线上数据不一致、日期硬编码、时区伪造、统计失真、校验可跳过"等 12 项遗留问题完成收尾。

### 12.1 统一编排器（scripts/pipeline_runner.py，pipeline_version=2）
- **唯一入口**：手动与自动任务均只调用
  `python scripts/pipeline_runner.py --mode {incremental|daily|full} --trigger {manual|scheduled}`。
  旧 `collect.py` 直跑链路已废弃（自动任务不再调用，避免覆盖新数据）。
- **链路**：git_pull → 单元测试 → 数据汇总 → 日报生成 → source 校验 → 提交 main → 构建 → dist 校验 → 推送 main → 部署 gh-pages → **线上验证**（轮询线上 status.json，run_id 一致才算成功）。（第二阶段收尾后链路已升级为 canonical-first，见第十四节。）
- **失败即失败**：任一步骤失败/校验不通过/线上 run_id 不一致 → 退出码非零、不部署、不覆盖上一版。
- **run_id**：`YYYYMMDDTHHMMSS+0800_xxxxxx`，全链路（main 提交、gh-pages 提交、线上 JSON、运行日志）一致可追溯。
- 运行日志：`logs/pipeline_<run_id>.json`（含每步状态、main/gh-pages commit、线上验证时间）。
- 运行锁 `data/.pipeline.lock`（不入库）防并发覆盖。

### 12.2 真实时区与日报窗口
- 所有时间基于 `zoneinfo.ZoneInfo("Asia/Shanghai")` / `ZoneInfo("UTC")`（依赖 `tzdata`），**禁止** `utcnow()+8h` 手工换算。
- 日报目标日期由 `get_latest_completed_report_date()` 按北京时间自动计算（<22:00 取前一日，≥22:00 取当日），**无任何日期硬编码**。
- 日报窗口严格校验（V10）：起止均为北京 22:00、长度 24h、结束不晚于生成时间、文件名与窗口一致；legacy 报告显式标注跳过，当前 pipeline 报告不可跳过。

### 12.3 校验器（scripts/validate_pipeline.py）
- 分阶段：`--stage source`（构建前，跳过 dist 检查）/ `--stage dist`（构建后完整 16 项检查）。
- 检查项含：JSON 合法性、三处 run_id 一致、pipeline_version=2、风险等级、event_id/source_url 完备、隔离池无重叠、质量闸门、24h/7d 统计一致、日报窗口、dist 与 source 事件数一致、无未来时间、summary 可追溯。
- **失败返回非零退出码并阻止部署**（已由回归测试覆盖验证）。

### 12.4 数据隔离与真实统计
- 旧 pipeline（pv<2）与误判数据隔离于 `data/quarantine_events.json`，不进入首页/统计/日报；统计仅计"pv2 + 闸门通过 + 未隔离 + 字段完整"事件（`calculate_public_statistics` 单一实现，status 与 summary 共用）。
- 信息源统计来自真实运行结果（`compute_source_statistics`），**杜绝 enabled=success**。

### 12.5 测试
- `scripts/tests/test_country.py`：国家识别 24 项。
- `scripts/tests/test_stage1_pipeline.py`：第一阶段回归 36 项（run_id/时区/日报窗口/统计闸门/源统计/运行锁/校验退出码/绝对路径扫描/status 元数据）。
- 两者均纳入 pipeline 单测步骤，任一 FAIL 即整体失败。

### 12.6 自动任务（当前生效）
- WorkBuddy 自动化 ×2：每 2 小时增量（`--mode incremental --trigger scheduled`）、每日北京 22:00 日报（`--mode daily --trigger scheduled`）。
- 实测证据：2026-07-29 22:53（北京）定时触发 daily，run_id `20260729T225349+0800_37nrdr`，11 步全部 success，线上验证通过。
- GitHub Actions 定时：**blocked_by_permission**——现有 PAT 仅 `repo` 权限、无 `workflow` scope，工作流文件无法推送。提供带 workflow 权限的令牌后 `git add .github && git push` 即可启用为备用链路。

### 12.7 已知限制
- 线上生效以 WorkBuddy 桌面端在线为前提（自动任务由本机执行）。
- 源码与配置中不含本机绝对路径（由回归测试持续扫描保障）。

---

## 十三、第二阶段整改（统一数据模型与发布状态模型，2026-07）

针对"Article 与 Event 混用、发布状态与处理状态混淆、来源分级与核实级别混用、旧池与新数据双向漂移"等结构性问题，建立**规范数据层（canonical）**作为唯一真实来源，旧池（events/pending/raw/quarantine_events）降级为单向生成视图。

### 13.1 三个检查点（独立提交，任一失败不进入下一阶段）
- **2A 数据结构与仓储（已提交）**：`scripts/data/` 规范层（repository / identifiers / normalizers / publication_policy / schema_validator）+ `schemas/*.schema.json` + 单元测试 57 项（`test_stage2_schema_repo`）。
- **2B 迁移与兼容（已提交）**：`scripts/data/migrate_stage2.py` 旧池→canonical 无损迁移；`compatibility_export.py` canonical→旧池单向生成；幂等验证 8/8 文件 SHA-256 两次完全一致、计数稳定（articles=328 / clusters=143 / quarantine=53 / published=143）；可回滚。
- **2C 流水线接入（本阶段）**：`collect.py` / `promote_events.py` / `build_summary.py` 改为经 `Repository` 读写 canonical，发布判定统一走 `publication_policy.evaluate()`；新增 `validate_stage2.py`（25 项，收尾阶段扩至 48 项）；本 README 同步更新。

### 13.2 三层数据架构（严格单向）
```
data/canonical/  规范数据层（唯一真实来源，schema_version=2.0, pipeline_version=2，内部使用，不部署公网）
      │  单向生成
      ▼
data/public/     发布视图（published_events.json / current_metrics.json / legacy_archive_events.json）
      │
data/events.json 遗留兼容视图（仅旧前端兼容，单向生成，不部署公网）
```
- 业务脚本（collect/promote/build_summary）只经 `Repository` 读写 canonical；旧池由 `compatibility_export.export_all` 在每次 apply 后自动再生成。
- 旧字段完整保留于各记录的 `legacy_payload`（事件另有 `legacy_event_id`），迁移零信息丢失。
- **部署边界（Stage-2 收尾新增）**：`build_site.py` 仅按白名单部署 `status / latest-summary / events(脱敏) / countries / risk-levels / sources(脱敏) / public/* / reports`，**绝不部署 `data/canonical/`、`data/backup/`、`quarantine_events.json` 等内部文件**，杜绝内部数据（含 legacy_payload、本机路径、完整 Article 正文）外泄。

### 13.3 关键分离（写入规范层红线）
- **Article ≠ Event**：`article_id`（ART_）与 `event_id`（EVT_）分离；一篇报道可关联多个事件，一个事件可聚合多篇报道（cluster.article_ids）。
- **来源分级 ≠ 核实状态**：`source_type`/`source_reliability_tier`（来源属性）与 `verification_level`（事件核实级别）互不替代。
- **国家风险 ≠ 事件严重度**：`country_risk_level`（国家固定风险）与 `event_severity`（事件严重度）分离。
- **提及 ≠ 事件国**：`mentioned_countries`（提及）与 `country_code`（事件主国）分离。
- **处理状态 ≠ 发布状态**：`processing_status`（queued_for_verification / linked_to_event / …）与 `publication_status`（publishable / published / verification_pending / …）分离。

### 13.4 发布状态模型（确定性，零随机）
- `publication_policy.evaluate(verification_level)` 唯一裁决：`cross_verified` 或 `direct_official_source` → `publishable`（→ `published`）；其余（含单源媒体 `single_source`、转发平台 `high_reliability_single_source`）→ `verification_pending`，**不自动发布**。
- 红线：Reuters/新华社等**转载**来源单源 ≠ 官方直接来源（Section 十）；ReliefWeb 为 NGO 报告聚合平台 ≠ 联合国官方直接来源。
- 历史已发布事件迁移后标记 `legacy_migration_preserved=true / current_policy_passed=false / quality_gate_passed=false`，仅进入 `data/public/legacy_archive_events.json` 历史归档，**不进入首页当前态势与日报当前内容**（其 `verification_level` 仍保留供后续自动核实）。

### 13.5 迁移与幂等（2B 证据）
- 无损：8 类关键文件两次 apply 的 SHA-256 完全一致；计数稳定不漂移。
- 可回滚：迁移前 5 个旧池文件由 Git 基线 `3c61e85` 标记，rollback 可恢复。
- 唯一 ID：基于内容 SHA-256（16 位）；隔离记录 `Q_` 因旧池存在大量 `event_id/detected_at` 为空的排除类记录，引入 `seed` 保证 53 条 1:1 无损。
- 版本标记：保留 `pipeline_version=2`，新增 `schema_version="2.0"`，**不升到 3**。

### 13.6 校验与回归（全绿）
| 套件 | 项 | 结果 |
|---|---|---|
| `validate_stage2.py` | 48 项（结构/ Schema / ID / 发布策略 / 来源分级 / 单向生成 / 1:1 / 幂等 + 收尾 S26-S48：仓储强制校验、双向关联、public 溯源、同批导出、统计口径、历史语义、风险一致、业务属性、legacy_payload 不外泄、路径卫生、链路静态检查、run_id 全链路一致、首页隔离 S43、日报持续跟踪 S44-S46、dist 无内部数据 S47、publishable_clusters 语义 S48） | ✅ 48/48 |
| `verify_idempotency.py` | 8 文件两次 apply SHA-256 一致 | ✅ PASS |
| `test_stage2_schema_repo`（2A） | 仓储/ID/归一化/发布闸门/导出 | ✅ 57/57 |
| `test_stage1_pipeline`（第一阶段） | run_id/时区/窗口/统计/锁/校验退出码 | ✅ 36/36 |
| `test_repository_integrity` | 双向关联/事务/来源规则 | ✅ 28/28 |
| `test_no_local_paths` | 全仓/ dist / public 无本机路径 | ✅ 6/6 |
| `test_stage2_closeout`（本收尾新增） | 首页隔离/日报持续跟踪/build_site 白名单/README 一致性等 20 项 | ✅ 通过 |
| `test_country` | 国家识别 | ✅ 24/24 |
| `validate_pipeline.py` | V1–V19（含 V16 首页仅 current_policy_passed、V18 日报持续跟踪、V19 统计语义） | ✅ 0 严重错误 |

### 13.7 范围边界（本阶段不做）
- 不新增信息源、不改 Reuters/新华社/GDELT 采集策略、不引入 Hy3 翻译/摘要、不做自动二次核实引擎、不改首页/国家页视觉、不新增国家、不改日报正文、不等待定时任务、不批量重新抓取。
- 验收达到校验指标即停止，**不进入第三阶段**。

---

## 十四、第二阶段最终收尾（2026-07-30）

在第十三节基础上关闭全部遗留问题，形成 canonical-first 的完整闭环：

### 14.1 仓储层强制约束（Commit：Stage 2A Fix）
- **保存前强制 Schema 校验**：`Repository` 所有保存路径（含临时文件回读复验）强制校验；100 条中 1 条非法 → 整个保存失败且原文件字节不变（`RepositorySchemaError`）。
- **事务式双向关联**：`link_article_to_event` 一次事务更新 Article.linked_event_id 与 Event.article_ids，任一侧失败则两文件均回滚；重复关联不改变文件内容。
- **来源业务规则**（`source_rules.py`）：Reuters/新华社单源转载 ≠ 官方直接来源；ReliefWeb=转载平台；`save_sources` 违规即拒绝。
- 测试：`test_repository_integrity.py` 28/28。

### 14.2 canonical-first 发布链路（Commit：Stage 2 Final）
- **public 为唯一展示来源**：`build_summary.py` / `generate_reports.py` 只读 `data/public/published_events.json` 与 `current_metrics.json`，不再读取遗留 `events.json`。
- **历史迁移发布语义**（`apply_publication_semantics.py`）：未达当前政策的迁移事件标记
  `legacy_migration_preserved=true / legacy_visibility=true / current_policy_passed=false / quality_gate_passed=false`，
  原因="历史迁移保留，未按当前政策重新核实"；仅进入 `data/public/legacy_archive_events.json` 历史归档，**不进入首页当前态势与日报当前内容**。
- **22 国风险统一**：以 `countries.json` 为准（4=极高/3=高/2=中/1=低），cluster 顶层与 legacy_payload 同步修正。
- **路径卫生**：日志/迁移状态中的本机绝对路径已清洗；`save_run_log` 自动脱敏；`test_no_local_paths.py` 持续扫描 main/dist/public。
- **编排器升级**：`pipeline_runner.py` 为 Stage-2 编排器——pull 失败即中止（`PULL_FAILURE_BLOCKS`）、5 套测试全过才继续、语义与导出入链、`validate_stage2`（48 项）失败即中止、提交信息 `Stage-2 run_id=`。
- **校验强化**：`validate_stage2.py` 从 25 项扩至 **48 项**（S26-S48：仓储强制校验、双向关联、public 溯源、同批导出、统计口径、历史语义、风险一致、业务属性、legacy_payload 不外泄、路径卫生、链路静态检查、run_id 全链路一致、首页隔离 S43、日报持续跟踪 S44-S46、dist 无内部数据 S47、publishable_clusters 语义 S48）。

---

## 十五、第二阶段正式收尾与统一声明（2026-07-30）

本节为第二阶段的**权威结论**，与前文任何旧表述冲突时以本节为准。

### 15.1 本次收尾关闭的 6 个遗留问题
1. **首页当前态势被历史迁移数据污染** → 新增统一过滤 `is_current_public_event()`（`scripts/pipeline_core.py`），首页重要事件 / 最新事件 / 涉华事件三个当前模块**只使用该过滤**；不满足当前发布政策的事件一律不进入。
2. **日报"持续跟踪"错误纳入历史事件** → 新增 `is_ongoing_report_event()`，`generate_reports.py` 重建 new / ongoing 分类；历史迁移事件不得进入持续跟踪，ongoing 需状态合法（ongoing/developing/easing）且 7 天内有活动痕迹。
3. **Canonical 内部数据被部署到公网** → `build_site.py` 改为**显式白名单复制**（不再整目录 copy），`__DB__` 内联快照同样只含白名单且脱敏；`data/canonical/**`、`data/backup/**`、`legacy_payload`、本机绝对路径**均不进入 dist / gh-pages**。
4. **README 旧三级数据池与 Canonical 架构并存矛盾** → 11.3 / 13.2 / 13.4 / 14.2 已统一为「采集暂存（草稿，非发布源）→ Canonical（唯一真实来源，内部不部署）→ Public（唯一公开层）→ Legacy（单向生成的兼容视图，不部署）」；A/B/C 明确为**采集相关性分级**而非发布准入。
5. **状态字段为空或语义不准** → `current_metrics.publishable_clusters` 改为统计真正 `current_policy_passed == true` 的事件；运行日志补齐 `deploy_completed_at` 与 `deployment_commit`。
6. **验收规则不完整** → `validate_pipeline.py` 重写 V16（删除"历史可见即可进首页"的错误逻辑）并新增 V18 / V19；`validate_stage2.py` 由 42 项扩至 **48 项**（新增 S43–S48）；新增测试套件 `scripts/tests/test_stage2_closeout.py`。

### 15.2 当前数据事实（不掩饰）
- Canonical 中保留的全部历史迁移事件 `current_policy_passed = false`，因此**当前公开事件数为 0**，首页当前态势三个模块显示"暂无"，日报持续跟踪显示"当前无符合条件的持续跟踪事项。"——这是**正确行为**，不是故障。
- 历史数据未被删除，完整保留在 Canonical，并以裁剪脱敏形式提供 `data/public/legacy_archive_events.json`（不含 `legacy_payload`、不含本机路径、不含完整正文）。

### 15.3 边界声明
- Canonical 层**永不部署**到 gh-pages；公网仅可访问白名单内的 `data/*.json` 与 `data/public/*.json`。
- 本次收尾**未**执行历史数据全量重新迁移、**未**删除任何 Canonical 历史、**未**新增信息源、**未**抓取外部新闻、**未**调用 Hy3、**未**开发自动核实与智能聚类、**未**修改网站整体样式、**未**扩展国家。
- **Stage 2.5 与第三阶段均未开始。**
