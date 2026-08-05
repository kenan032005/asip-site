# ASIP安全情报微型样板 V0.1 Git仓库恢复与交付基线重建报告

- **任务**：I0-C：Git仓库恢复与V0.1交付基线重建
- **执行日期**：2026-08-05（北京时间，UTC+08:00）
- **原项目目录**：`C:/Users/kenan/WorkBuddy/2026-07-20-22-01-23/asip-site-v01`
- **恢复目录**：`C:/Users/kenan/WorkBuddy/recovery/asip-site-v01-i0c-clean`
- **远端**：`https://github.com/kenan032005/asip-site.git`
- **范围边界**：只处理 Git 恢复、V0.1 基线、QA 证据、备份、测试和交付；未扩充情报数据库，未开发地图/时间轴，未进入萨赫勒详细版。

## 1. 最终结论

**当前结论：V0.1 功能源码和浏览器 QA 已在远端 main 可靠基线上完成可追溯重建，功能提交与 QA 提交分离；恢复分支和版本标签已成功推送并通过 `ls-remote` 验证。原始提交 843e9c9/a2164d9 无法恢复，重建提交不伪装为原哈希。**

I0-C 的交付链为：

```text
8924416ff3f969c3996312b8ca97588ff268cf5e 远端 main 可靠父基线
  └─ bf5b60f817380117fe53455785e4e2857a8c1e1a  V0.1 功能源码
      └─ 238f02baae6d2f8fff8d71762bcb2c5adfcea6a9  V0.1B 浏览器 QA
          └─ d5db2eaae7994fd92e1686e2f4d5a49bc8701c8c  日期说明 + I0-C 最小复验
      └─ 320c6d6b2a1c4edbfbb40d62667d83c25ad5d057  I0-C 恢复报告 + WIP 保护证明
```

最终交付提交：`320c6d6b2a1c4edbfbb40d62667d83c25ad5d057`。

> 说明：WorkBuddy 当前 Git 环境存在分支引用间歇性清空现象。每次提交对象均先用 `git cat-file`/`git show` 验证，再用明确的本地 ref 保护；最终链已能连续读取，报告保留该环境问题。

## 2. Stage 0：冻结现场与完整备份

### 2.1 现场记录

- 本地时间：2026-08-05 21:40:40（北京时间）
- UTC：2026-08-05 18:40:40
- 用户：`kenan`
- 主机：`Paco-T14P`
- 原项目：`C:/Users/kenan/WorkBuddy/2026-07-20-22-01-23/asip-site-v01`
- 远端：`https://github.com/kenan032005/asip-site.git`

已只读记录 `status --short`、`status`、`branch -a -vv`、`remote -v`、`log --all --decorate --oneline -30`、`reflog --all`、`worktree list`、`stash list`。没有执行 reset、clean、gc、prune、reflog expire、init、强制推送或主分支修改。

### 2.2 完整备份

- **备份目录**：`C:/Users/kenan/WorkBuddy/backups/asip-site-v01-pre-i0c-20260805-214040/`
- **完整项目副本**：`.../project/`
- **文件数**：11,673
- **总大小**：719,977,341 bytes
- **完整 manifest**：`backup-manifest.json`
- **V0.1 关键文件 SHA-256**：`sha256-v01-key-files.txt`
- **Stage 1 取证记录**：`_i0c_stage1_forensics.txt`

备份包含整个工作目录、完整 `.git`、未跟踪 WIP、`.workbuddy`、`.workbuddy_recovery`、V0.1 源码、QA 脚本/截图/报告、`.gitignore`、`dist` 和临时内容。备份读取验证通过：`.git` 与 `data/intelligence/demo/entities.json` 均可读取。

## 3. Stage 1：Git取证与恢复判断

### 3.1 原仓库状态

取证记录显示：

- `HEAD` 曾指向 `refs/heads/feature/asip-intelligence-demo-v01b-browser-qa`
- `.git/packed-refs` 存在，包含远端 main、gh-pages、历史阶段分支和标签
- 原 QA ref 曾出现 trailing garbage 警告
- `logs/HEAD` 和相关分支 reflog 仅能看到 `5e6fe83` 的 QA root commit
- `stash list` 为空
- 当前本地远端跟踪分支未包含 V0.1 功能分支
- 对象库存在 pack 和少量松散对象，但没有可用原提交对象

### 3.2 原提交验证

```text
git cat-file -t 843e9c9
fatal: Not a valid object name 843e9c9

 git cat-file -t a2164d9
fatal: Not a valid object name a2164d9
```

两者均不可恢复。

### 3.3 fsck 结果

```text
git fsck --full --no-reflogs --unreachable --no-progress
```

仅发现若干 unreachable tree/blob，没有 dangling commit；`git fsck --lost-found` 同样没有可用于恢复 V0.1 历史的 commit。不能仅凭文件名把这些对象判定为 V0.1。

### 3.4 远端取证

远端默认分支：

```text
refs/heads/main
8924416ff3f969c3996312b8ca97588ff268cf5e
```

远端已有功能分支中未发现 `feature/asip-intelligence-demo-v01`、`feature/asip-intelligence-demo-v01b-browser-qa` 或对应原哈希。

### 3.5 恢复判断

选择：**B：原提交不可恢复，但远端主线基线可靠。**

远端 `main` 可以干净克隆，提交 `8924416...` 可读取，工作树干净，适合作为重建父基线。

## 4. Stage 2：路径B干净基线重建

未在混合原工作目录中重建，而是在：

```text
C:/Users/kenan/WorkBuddy/recovery/asip-site-v01-i0c-clean
```

执行：

```text
git clone --branch main --single-branch https://github.com/kenan032005/asip-site.git asip-site-v01-i0c-clean
```

确认父基线：

```text
8924416ff3f969c3996312b8ca97588ff268cf5e
```

从 Stage 0 备份逐项迁入 16 个 V0.1 文件，未复制整个 `data`、`assets` 或 `scripts` 目录。迁入 SHA-256 全部匹配，迁移元数据保留在：

```text
i0c-v01-source-sha256.json
```

该迁移元数据未进入功能提交。

## 5. Stage 3：提交重建

### 5.1 V0.1 功能提交

```text
分支：feature/asip-intelligence-demo-v01-rebuilt
提交：bf5b60f817380117fe53455785e4e2857a8c1e1a
信息：feat: restore ASIP intelligence demo v0.1 baseline
父提交：8924416ff3f969c3996312b8ca97588ff268cf5e
文件：16
```

提交仅包含：

- `assets/css/intelligence.css`
- `assets/js/intelligence/intelligence.js`
- `assets/js/intelligence/network.js`
- `data/intelligence/demo/` 下 6 个共享数据文件
- 3 个样板页面/模板
- `scripts/build_intelligence_demo.py`
- `scripts/build_site.py`
- 2 个样板测试文件

功能数据仍为 12 个实体、20 条关系、6 个来源。

### 5.2 V0.1B QA 提交

```text
提交：238f02baae6d2f8fff8d71762bcb2c5adfcea6a9
信息：test: add browser QA evidence for intelligence demo v0.1
父提交：bf5b60f817380117fe53455785e4e2857a8c1e1a
文件：23
```

仅包含：

- `qa_browser.js`
- `qa-artifacts/`（21 个原始浏览器证据文件）
- `ASIP_INTELLIGENCE_DEMO_V01B_ACCEPTANCE.md`

I0-B 未修改生产源码，这一点保持不变。

### 5.3 日期归档与最小复验提交

```text
提交：d5db2eaae7994fd92e1686e2f4d5a49bc8701c8c
信息：docs: archive V0.1 dates and recovery browser evidence
父提交：238f02baae6d2f8fff8d71762bcb2c5adfcea6a9
```

包含：

- `ASIP_INTELLIGENCE_DEMO_V01_ARCHIVE_DATE_NOTE.md`
- `i0c_min_browser_qa.js`
- `i0c-browser-artifacts/`（最小真实浏览器复验截图和 JSON）

## 6. Stage 4：测试、构建和真实浏览器复验

### 6.1 自动测试

恢复目录执行结果：

```text
python scripts/tests/intelligence/test_demo_data.py
PASS entities=12 relationships=20 sources=6
PASS unique_ids=12 unique_slugs=12 aliases=25
PASS references, source coverage, date order, routes, and temporal JNIM/IS relationship

python scripts/tests/intelligence/test_demo_pages.py
PASS routes=14 (entry + network + 12 entity routes)
PASS shared-data links, base-path relative URLs, graph controls, focus history, relation details
PASS responsive breakpoints and non-color-only node shapes

node --check assets/js/intelligence/network.js
exit=0

node --check assets/js/intelligence/intelligence.js
exit=0

python scripts/tests/test_country.py
结果：PASS=24 FAIL=0

python scripts/tests/test_stage2_frontend_final.py
前端隔离最终修复测试：PASS=28 FAIL=0

python scripts/tests/test_repository_integrity.py
Commit 1 完整性测试：PASS=28 FAIL=0
```

### 6.2 构建

```text
python scripts/build_site.py --no-embed
exit=0
构建完成 -> dist
intelligence demo: 12 entity routes + network + data
内联数据快照: False
```

构建产物：

```text
C:/Users/kenan/WorkBuddy/recovery/asip-site-v01-i0c-clean/dist/
```

### 6.3 最小真实浏览器复验

- 浏览器：Headless Chrome 130
- 服务：恢复分支 `dist`，端口 `8776`
- 入口：正常加载，标题正确
- JNIM 档案页：正常加载
- JNIM 关系图：`focus=actor-jnim`，12 节点、12 条边
- JNIM → IS Sahel → JNIM：真实点击切换通过
- 关系线：详情卡显示双方、类型、时间、可信度、来源
- 深层刷新：`focus=person-iyad-ag-ghali` 正常，5 节点、4 条边
- 390px 视口：`bodyWidth=390 / innerWidth=390`，无横向溢出
- 控制台：0
- 未捕获异常：0
- 网络失败：0

证据目录：

```text
C:/Users/kenan/WorkBuddy/recovery/asip-site-v01-i0c-clean/i0c-browser-artifacts/
```

第一次复验出现 0 节点是脚本等待条件过早，已修正等待逻辑并重跑通过；不是页面缺陷。

## 7. Stage 5：远端备份、分支和标签

### 7.1 远端刷新

已执行：

```text
git fetch origin --prune
```

结果：exit=0，无错误。

推送目标分支：

```text
feature/asip-intelligence-demo-v01-rebuilt
```

目标分支在推送前不存在；不覆盖远端已有分支，不触碰 `main`、`master` 或 `gh-pages`。

### 7.2 版本标签

目标标签：

```text
asip-intelligence-demo-v0.1
```

标签指向最终交付提交：`320c6d6b2a1c4edbfbb40d62667d83c25ad5d057`。

标签说明：

```text
ASIP intelligence demo V0.1:
12 entities, 20 relationships, wiki-style profiles,
dynamic focus graph, browser QA passed.
```

### 7.3 远端验证

已成功执行：

```text
git push origin feature/asip-intelligence-demo-v01-rebuilt
To https://github.com/kenan032005/asip-site.git
 * [new branch]      feature/asip-intelligence-demo-v01-rebuilt -> feature/asip-intelligence-demo-v01-rebuilt

git push origin asip-intelligence-demo-v0.1
To https://github.com/kenan032005/asip-site.git
 * [new tag]         asip-intelligence-demo-v0.1 -> asip-intelligence-demo-v0.1

git ls-remote origin refs/heads/feature/asip-intelligence-demo-v01-rebuilt refs/tags/asip-intelligence-demo-v0.1 refs/tags/asip-intelligence-demo-v0.1^{}
320c6d6b2a1c4edbfbb40d62667d83c25ad5d057  refs/heads/feature/asip-intelligence-demo-v01-rebuilt
b6702445fd01278c45a1a8254e1c2323d9158fb2  refs/tags/asip-intelligence-demo-v0.1
320c6d6b2a1c4edbfbb40d62667d83c25ad5d057  refs/tags/asip-intelligence-demo-v0.1^{}
```

其中 `b6702445...` 是带注释标签对象哈希，`^{}` 解引用结果确认标签实际指向最终提交 `320c6d6...`。远端推送与读取验证均成功，因此不需要转入 bundle/patch 备用交付路径。

## 8. 原工作目录与无关 WIP 保护

原工作目录未执行：

- `git reset --hard`
- `git clean`
- `git gc`
- `git prune`
- `git reflog expire`
- `git init`
- 强制推送
- 主分支修改
- 批量删除或覆盖

Stage 0 完整备份复制了原工作目录全部 11,673 个文件，包括无关 WIP、缓存、`.workbuddy`、`.workbuddy_recovery` 和原 `.git`。原工作目录仍保留在原路径；恢复工作全部在新目录完成。

保护证明：

```text
i0c-original-wip-protection.json
```

由于原仓库索引/refs 已损坏，最终 `git status` 将大量原内容显示为未跟踪，不能把“clean working tree”作为 WIP 未变化的证据；因此采用了完整目录备份和文件存在性/哈希方式保护现场。

## 9. 日期归档说明

原 V0.1 报告写有 `日期：2026-08-06`，V0.1B 报告写有 `验收日期：2026-08-05`。现有证据不足以严格区分跨北京时间午夜、时区差异或报告日期字段误差，因此：

- 不修改原始报告；
- 新增 `ASIP_INTELLIGENCE_DEMO_V01_ARCHIVE_DATE_NOTE.md`；
- 后续 I0-C 记录统一使用北京时间 UTC+08:00；
- 不在缺乏证据时猜测原报告日期原因。

## 10. 未解决问题与技术债务

1. 原提交 `843e9c9` 与 `a2164d9` 无法恢复，不应在任何后续报告中声称新提交等同原哈希。
2. WorkBuddy Git 环境存在 refs 间歇性清空和 trailing garbage，需要后续在稳定 Git 环境中检查新推送分支是否可正常读取。
3. 原工作目录索引已损坏，不建议继续在该目录开发；应使用恢复目录或重新克隆的工作区。
4. V0.1B 原报告中的 Niger→Al-Qaida 点击不可达是“一度关系”产品边界，不应为了恢复任务扩库。
5. 没有生成动画录屏；已有真实 CDP 截图和结构化状态证据，I0-C 仅要求最小浏览器复验，不补做完整录屏。
6. 迁移 SHA 元数据 `i0c-v01-source-sha256.json` 保留在恢复目录但未提交，作为重建审计辅助文件。

## 11. 是否允许进入下一阶段

**本 I0-C 任务完成后停止，不自动创建或执行萨赫勒详细版任务。**

只有在远端分支和标签的 `ls-remote` 验证成功后，才可以给出：

> V0.1功能和浏览器验收已通过；Git交付基线已恢复或重建并完成远端备份，允许规划萨赫勒详细版。

该句仅表示“允许规划”，不表示自动进入下一阶段。
