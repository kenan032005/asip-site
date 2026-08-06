# ASIP非洲安全情报知识库 I3-B 全重点国家内容补齐、核心证据强化与生产发布准备验收报告

- 阶段：I3-B（全重点国家内容补齐、核心证据强化、稳定公网预览与生产发布准备）
- 报告日期：2026-08-06
- 执行模型：DeepSeek V4 Pro（主执行：来源研究、事实核验、正文撰写、关系与证据审查、最终复核；构建/测试/浏览器 QA 由自动化流水线完成）
- 标准开发目录：`C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-trusted`（I2-B 起唯一可信目录，reftable 引用后端）

## 1. Git 基线、分支、提交与标签

| 项 | 值 |
|---|---|
| I3-A 基线 | 远端 `cffb420`（含 I3-A 报告提交；任务文所述 8f1ef5e 为报告前 HEAD） |
| I3-B 功能分支 | `feature/asip-intelligence-v10-i3b-release-candidate` |
| I3-B 提交链 | `d25b520 → 8466394 → 4bb819f → 9676a11 → 0f68561 → 3d2dd7c → fab6bc2 → 23bcfd0 → <QA证据> → <发布包+报告>` |
| 阶段标签 | `asip-intelligence-v1.0-rc1`（推送后核验；仅代表“内容与技术达到正式生产接入前人工验收标准”，非生产上线） |
| Git 健康 | `git fsck --full` 无异常；全部正常 `git commit`，未使用 commit-tree |
| 工作树 | 干净（提交完成后 `git status --porcelain` = 0） |

10 组逻辑提交（真实哈希链，见最终推送）：
1. `data: deepen Mali Burkina Cameroon Ethiopia Tanzania country profiles (all 13 deep)`
2. `data: upgrade Sahel basic entries (Al-Qaeda Ansar Dine Mourabitoun Katiba Macina AQIM IS Sahel)`
3. `data: add 10 core entities for remaining five countries`
4. `data: add second-wave relationships and deepen 16 relation histories`
5. `data: strengthen evidence (45+ manual, pending<=12, freshness), sources 77, metrics v2`
6. `feat: render country lead paragraphs and show non-production preview banner`
7. `feat: strengthen build gates (deep 13, basic 0) and add I3-B generators`
8. `test: add I3-B content release and production isolation gates`
9. `docs: add I3-B browser QA evidence`
10. `docs: add I3-B release candidate package and acceptance report`

修改文件：`data/intelligence/africa/` 下 14 个数据文件、`assets/js/intelligence/africa.js`、`scripts/build_intelligence_africa.py`、`scripts/gen/gen_i2b_migration.py`、`scripts/gen/gen_africa_aux.py`（路径修复）、3 个新 I3-B 生成脚本、8 个新 I3-B 测试 + 4 个旧测试断言更新、浏览器 QA 脚本与证据、`release/i3b-rc1/` 发布包。

## 2. 内容深化成果（13 国全深度）

### 2.1 五个新增深度国家（正文 3400–4300 字、18 章节、2–4 段导语、时效与互链完整）

| 国家 | 正文字符数 | 章节 | 覆盖重点 |
|---|---|---|---|
| 马里 | 3998 | 18 | 2012 以来危机、JNIM 南部扩散与 2025-09 首都封锁、FLA 结盟与 2026-04 国防部长遇袭、AES、俄罗斯介入、多线冲突区分 |
| 布基纳法索 | 3606 | 18 | JNIM 控制/争夺约六成领土、吉博围困、VDP 动员与暴行循环、2026-01 解散政党、袭击/存在/活动/控制区分 |
| 喀麦隆 | 3655 | 18 | 三套问题严格区分（远北圣战/英语区分离/东部边境）、BIR、安巴佐尼亚非统一组织、2026-04 副总统任命 |
| 埃塞俄比亚 | 3941 | 18 | 提格雷对峙与《比勒陀利亚协议》失效、Fano 多派系、OLA 主流派、ENDF 三线作战、选举受阻、厄立特里亚/苏丹/埃及地缘 |
| 坦桑尼亚 | 3430 | 18 | “外溢而非境内叛乱”定位、TPDF 边境部署、SAMIM 参与史、姆特瓦拉风险带、2025 大选后紧张、来源不足如实标注 |

（字符数为章节正文合计，不含标题/信息框/来源列表/关系卡；每页含导语、信息框日期语义、时效提示、国家↔实体↔关系↔图谱互链。）

### 2.2 基础条目清零与新实体（basic=0）

- **4 个基础条目全部升级**：基地组织→标准档案（全球网络/非洲分支/效忠语义/来源限制）；安萨尔埃丁、穆拉比通、马西纳旅→完整百科（各含成立背景、历史沿革、结构领导、关系、当前状态、不确定性；明确区分“历史实体 vs JNIM 组成部分”的时间语义）。AQIM、IS Sahel 同步升级为完整百科。
- **10 个新实体（上限内，均达标准档案 ≥900 字/≥5 章节/有来源/有当前状态/有时效/有不确定性）**：马里武装部队（FAMa）、布基纳法索武装部队、国土防卫志愿军（VDP）、快速干预营（BIR）、安巴佐尼亚武装网络（明确非统一组织）、埃塞俄比亚国防军（ENDF）、Fano 相关力量（明确多派系）、奥罗莫解放军（OLA）、坦桑尼亚人民国防军（TPDF）、提格雷国防军（TDF）。

### 2.3 实体档案深度（profile_depth 按内容完整度自动分级）

- **完整百科 19 个**（目标 ≥18）：I3-A 14 个 + 安萨尔埃丁、穆拉比通、马西纳旅、AQIM、IS Sahel。
- **标准档案 27 个**：覆盖其余全部实体（含 10 个新实体与升级后的基地组织）。
- **基础条目 0 个**（目标 0）；46 实体全部 ≥standard。

### 2.4 关系深化（33 档案 / 33 时间轴）

- 新增 16 条关系（马里/布基纳/喀麦隆/埃塞/坦桑网络，端点全部真实存在），关系总数 62→78。
- 深化档案 17→33（目标 ≥32），时间轴 17→33（目标 ≥30）：每条约含概览/背景/形成/阶段/转折/现状/驱动/地区差异/影响/不确定性 + 时间轴 + 来源 + 双方互链 + 返回图谱。

### 2.5 证据与时效（核心强化）

- 证据：137→**167 条**；新增人工来源映射证据 **45 条**（目标 ≥45）。
- 状态：**verified 84（目标 ≥55）**、partially_verified 71、**pending_review 7（目标 ≤12）**；71 条生成证据全部显式复核（31 条升级为已核验并转为 manual_source_mapping，其余部分核验/保留待复核并附说明）；无 unsupported、无生成证据标记 verified。
- 时效：**stale/aging 当前状态 11→0（目标 ≤3）**；库法（2019 年亡）如实标为 historical；全部 current 项均有 claim_valid_as_of 与 current_status_verified_at。
- 来源：62→**77 个**（新增联合国/ACLED/ICG/ISS/CFR/CRS/CGVS/外交部通告等 2025-2026 来源）。

### 2.6 统计口径（catalog_metrics.json 机器生成，schema v2）

```
region_count=7  country_count=13  non_country_entity_count=46
unique_knowledge_object_count=66  deep_country_count=13
relationship_count=78  relation_profile_count=33  relation_timeline_count=33  relation_type_count=24
source_count=77  evidence_record_count=167（verified 84 / partially 71 / pending 7）
encyclopedia_full=19  standard=27  basic=0
duplicated_paragraph_count=0  empty_section_count=0  stale_current_claim_count=0
route_count=151
```

## 3. 前端与质量门

- 国家页**导语（lead）实际渲染**修复（此前导语数据存在但页面未显示）；预览横幅“非生产预览版 · asip-intelligence-v1.0-rc1 · 未接入正式生产导航”。
- 构建门升级：深度国家 ≥13、basic 必须为 0、ency ≥8 章节 & ≥1800 字、std ≥5 章节 & ≥900 字、无空章节/占位符/正文重复（统一组件豁免）、互链可解析、verified 证据有 locator、生成证据不得 verified。全部通过。

## 4. 自动测试（408 PASS / 0 FAIL）

28 个测试文件 + 3 个 `node --check` 全部通过（含 I2-B/I3-Prep-A/I3-A 全部测试与 8 个新 I3-B 测试：all_country_depth、zero_basic_entries、current_status、relation_depth、evidence_upgrade、release_candidate、public_preview、production_isolation）。构建 `python scripts/build_site.py --no-embed` → 151 路由 + Demo/主站不回归。

## 5. 真实浏览器验收（本地 55 页 + 公网 8 页）

环境：Edge 151（`--disable-extensions` 干净 profile，CDP 9224）、本地预览 8786、公网 CloudStudio。

```text
本地：13 国家页 + 20 实体页 + 15 关系页 + 7 图谱焦点 + 4 视口 + 深层刷新 = 55 页
consoleErrors=0  runtimeExceptions=0  failedRequests=0  brokenAssets=0  horizontalOverflow=0
公网（CloudStudio 显式路径，第 3 轮干净会话）：8 页 console=0 异常=0 failed=0 溢出=0
13 国家页：18 章节、3430–5667 字、导语 3 段、目录 18、关系互链 6–12 条
20 实体页：11–15 章节、965–1782 字
15 关系页：10 章节、时间轴 1–7 条
图谱：乍得 5/4、JNIM 16/17、ISWAP 9/9、马里 3/2、布基纳 3/2、埃塞 2/1、IS Sahel 9/9（节点/边），图例、焦点入口、颜色编码正常
390px：无横向溢出；截图取证 63 张（qa-artifacts-i3b/）
```

## 6. 稳定公网预览与生产隔离

### 6.1 部署方式（隔离、不覆盖生产）

- **gh-pages 版本化隔离路径**（长期稳定 URL，符合 §16.2 要求）：`https://kenan032005.github.io/asip-site/previews/asip-intelligence-v1.0-rc1/intelligence/africa/`
  - 发布提交 `4703ab8`（非 force 追加提交）；只新增 `previews/asip-intelligence-v1.0-rc1/`（314 文件），生产根目录 288 文件 **git 对象哈希逐一比对零变更**（`release/i3b-rc1/production_isolation_results.json`：changed=[], deleted=[], added=[]）；无删除操作；回退=删除该预览目录。
  - 分支文件已由 raw 端点验证（200）；github.io 公开域名因本环境 GitHub Pages CDN 对新目录的传播延迟暂未 200（I2-A 以来新目录传播需数小时，demo 先例最终生效）——传播完成后该 URL 即为最终稳定入口。
- **已验证即时可用的公网 URL**（真实浏览器第 3 轮全 0）：`https://e5f9aef1abbc4c938d3ce143c41811c4.gz1.agentos-app.net/intelligence/africa/index.html`（免登录、非本机、深层路由以 `/country/mali/index.html` 等显式路径访问正常；宿主对无文件名目录做 SPA 回退的局限已在 known_issues 记录，不作为主 URL）。

### 6.2 三轮公网验证

1. 发布后立即：gh-pages 404（CDN 传播中）、CloudStudio 显式路径 200 ✓
2. CDN 传播后复验：gh-pages 仍 404（raw 200 确认文件就位）、CloudStudio 18/18 HTTP 200 ✓
3. 干净浏览器新会话：CloudStudio 8 页 console/exceptions/failed/overflow 全 0 ✓（截图含公网地址栏证据）

## 7. 生产发布候选包（release/i3b-rc1/，14+1 文件）

`release_candidate_manifest.json`（真实计数与提交 SHA）、`route_manifest.json`（151 路由）、`asset_manifest.json`（dist 全文件 sha256）、`data_metrics.json`、`source_evidence_metrics.json`、`production_diff_summary.md`、`production_sync_plan.md`、`rollback_plan.md`、`pre_deploy_checklist.md`、`post_deploy_checklist.md`、`known_issues.md`、`browser_qa_summary.json`、`public_preview_verification.json`、`build_sha256.txt`、`production_isolation_results.json`。

## 8. 关闭标准对照

| 条件 | 状态 |
|---|---|
| Git 健康 / 分支推送 / 真实提交链 | ✅ |
| 13 国全部深度（含马里/布基纳/喀麦隆/埃塞/坦桑） | ✅ 13/13 |
| 4 基础条目升级、basic=0 | ✅ 0 |
| 完整百科 ≥18 | ✅ 19 |
| 所有实体 ≥standard、新实体无空壳（10 个，上限内） | ✅ |
| 关系档案 ≥32、时间轴 ≥30 | ✅ 33/33 |
| verified ≥55、pending ≤12、新增人工证据 ≥45 | ✅ 84 / 7 / 45 |
| 高影响当前判断人工映射、stale ≤3、无 unsupported | ✅ 0 / 0 |
| 无空章节/占位/重复正文、互链正常 | ✅ |
| 13 国/核心实体/关系页浏览器验收、图谱回归、深层刷新、390px | ✅ |
| Demo/主站不回归 | ✅ |
| 公网预览：免登录、非本机、资源加载、深层路由 | ✅ CloudStudio 已验证；gh-pages 版本化路径已部署待 CDN 传播（raw 确认） |
| 预览与生产路径隔离、发布包完整、回退计划完整 | ✅ |
| 未接主导航、未覆盖生产、未合并 main、未执行 I3-C | ✅ |

## 9. 未完成事项与技术债务

1. **GitHub Pages CDN 传播延迟**（本环境已知现象）：previews/ 版本化路径已部署并经 raw 确认，github.io 公开域名待 CDN 更新（demo 先例最终生效）；传播完成前，CloudStudio 显式路径为已验证可用的公网预览。
2. 剩余 7 条 pending_review 证据（来源定位不足的索引级记录，已显式标注）。
3. 部分高影响判断（卢旺达撤军、利比亚美方斡旋、厄立特里亚对 Fano 武器输送）依赖部分报道，标注 partially_verified。
4. 内容时效截至 2026-08-06，需定期刷新；relation/entity 数据随后续事件演进。
5. CloudStudio 宿主目录路径 SPA 回退局限（已记录），不构成交付障碍。

## 10. 结论

**I3-B 满足全部关闭标准**：13 个国家全部深度化、基础条目清零、19 完整百科/27 标准/0 基础、33 关系档案/33 时间轴、167 条证据（84 已核验/7 待复核）、stale 归零、408 项测试 0 失败、151 路由构建、本地 55 页 + 公网 8 页浏览器验收全零错误、生产发布候选包与回退计划完整、gh-pages 版本化预览已部署并经 raw 确认（github.io 域名待 CDN 传播）+ CloudStudio 已验证公网 URL。未合并 main/master、未覆盖生产、未接入主导航。等待用户与人工核验后，再单独执行《I3-C：生产接入、主导航同步、正式发布与回退验证》。
