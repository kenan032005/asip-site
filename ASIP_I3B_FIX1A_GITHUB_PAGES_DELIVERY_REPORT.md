# ASIP I3-B-Fix-1A GitHub Pages 稳定预览与 Git 交付链关闭报告

## §1 任务边界与结论

本执行包仅处理 GitHub Pages 公网预览发布机制和 Git 交付链；未修改知识库国家、实体、关系、证据或其他事实性内容，未修改正式导航、正式首页，未部署生产，未执行 I3-C。

**结论：工程关闭条件已满足，I3-B-Fix-1A 可关闭。**

## §2 Pages 发布源

| 项目 | 实际值 | 结果 |
|---|---|---|
| 仓库 | `kenan032005/asip-site` | PASS |
| 仓库公开状态 | `private=false`、`has_pages=true` | PASS |
| 稳定站点根地址 | `https://kenan032005.github.io/asip-site/` | PASS |
| 原发布机制 | GitHub Pages dynamic `pages-build-deployment` workflow，gh-pages 分支根目录作为输入 | 已核验 |
| 修复后机制 | gh-pages push 触发仓库内 `ASIP Pages Preview Republish`，完整上传 gh-pages 根树，使用 `actions/deploy-pages@v4` | PASS |
| `.nojekyll` | gh-pages 根目录存在 | PASS |
| CNAME | gh-pages 根目录未发现 CNAME；不存在自定义域名干扰 | PASS |
| 版本化预览树 | `previews/asip-intelligence-v1.0-rc1/` 位于 gh-pages 实际根目录 | PASS |

## §3 原 404 根因

原 404 不是 raw 文件缺失，也不能归因于普通 CDN 延迟。gh-pages `d8cb693` 树中已经存在完整版本化预览文件，raw 端点返回 200，但 Pages dynamic workflow 对 `d8cb693` 的 run `31128490735` 失败：

- `build` job `92709406793`：cancelled；
- `report-build-status` job `92710322219`：cancelled；
- `deploy` job `92710322528`：skipped；
- 因此没有新的成功 deployment，线上继续服务旧成功 deployment 的内容。

## §4 修复动作

### 4.1 Fix-1A 分支

从远端 I3-B 最终 HEAD `4064d6ddd1013d2b35acc12a29d5d688d77d46ba` 创建并推送：

`feature/asip-intelligence-v10-i3b-fix1a-pages`

Fix-1A 分支提交：

| SHA | 父提交 | 主题 |
|---|---|---|
| `d9c02db` / `d9c02dba7d3a423d23589df1bde9a8edba0ca788` | `4064d6d` | `fix: republish complete gh-pages preview artifact` |
| `3f8513f` / `3f8513ff979f16a5082953269d1cb45fdc8a1456` | `d9c02db` | `qa: record Fix-1A production isolation and git evidence` |
| `d5b74d2` / `d5b74d2fda4801dc36a11aeedbe97b47d3373986` | `3f8513f` | `fix: remove pages environment branch restriction` |

最终 Fix-1A 分支 HEAD：`d5b74d2fda4801dc36a11aeedbe97b47d3373986`，已推送远端。

### 4.2 gh-pages 正常追加提交

在独立 gh-pages 工作树中正常追加提交：

| SHA | 父提交 | 主题 |
|---|---|---|
| `ffb1704` / `ffb170437d22b434a53353cd95571983b46a98a1` | `d8cb693` | `fix: publish complete versioned preview via Pages workflow` |

推送为快进：`d8cb693..ffb1704 HEAD -> gh-pages`。未 force push，未删除正式网站文件。

该提交新增 `.github/workflows/asip-pages-preview-republish.yml`，只负责从 gh-pages 根目录完整上传静态树并部署 Pages；workflow 在 gh-pages 分支触发，以满足 `github-pages` 环境分支保护策略。

## §5 成功 Pages deployment

| 项目 | 实际值 |
|---|---|
| workflow | `ASIP Pages Preview Republish` |
| workflow run id | `31197908566` |
| workflow run number | `4` |
| trigger commit | `ffb170437d22b434a53353cd95571983b46a98a1` |
| conclusion | `success` |
| deployment id | `5798271991` |
| deployment commit | `ffb170437d22b434a53353cd95571983b46a98a1` |
| deployment status | `success` |
| environment | `github-pages` |
| deployment environment URL | `https://kenan032005.github.io/asip-site/` |
| 成功 job | `92930566334` |
| runner | `GitHub Actions 1000001667` |

成功 job 的 `Validate complete static tree`、`Upload complete static tree`、`Deploy Pages artifact` 均为 success。

## §6 公网 URL 验证

固定版本化预览入口：

`https://kenan032005.github.io/asip-site/previews/asip-intelligence-v1.0-rc1/intelligence/africa/`

部署成功后的首轮真实 HTTP 验证，六个目标均返回 200：

| 地址 | HTTP |
|---|---:|
| Africa 首页 | 200 |
| Mali 深层页 | 200 |
| Cameroon 深层页 | 200 |
| JNIM 实体页 | 200 |
| Network `?focus=actor-jnim` | 200 |
| `catalog_metrics.json` | 200 |

此前 404 的同组六个地址均已从 404 恢复为 200。raw 端点此前已为 200，证明修复点位于 Pages artifact/deployment 链而非 Git 文件缺失。

## §7 生产隔离

机器生成工件：

- `qa-artifacts-i3b-fix1a/production-before.json`
- `qa-artifacts-i3b-fix1a/production-after.json`
- `qa-artifacts-i3b-fix1a/production-diff.json`

对比范围为 gh-pages 正式根目录，排除允许新增的 `previews/asip-intelligence-v1.0-rc1/`。结果：

| 指标 | 结果 |
|---|---:|
| `existing_changed` | 0 |
| `existing_deleted` | 0 |
| `production_unchanged` | true |

唯一 gh-pages 工程变更为新增 Pages workflow；未覆盖正式根目录内容。

## §8 I3-B 提交链

I3-B 最终分支：`feature/asip-intelligence-v10-i3b-release-candidate`

I3-B 最终 HEAD：`4064d6ddd1013d2b35acc12a29d5d688d77d46ba`

I3-B 收尾提交链（从内容发布到候选收尾）：

| SHA | 父提交 | 主题 |
|---|---|---|
| `d25b520` | `cffb420` | 深化马里、布基纳法索、喀麦隆、埃塞俄比亚、坦桑尼亚国家档案 |
| `8466394` | `d25b520` | 升级 Sahel 基础实体 |
| `4bb819f` | `8466394` | 增加五国核心实体 |
| `9676a11` | `4bb819f` | 增加第二波关系与关系历史 |
| `0f68561` | `9676a11` | 强化证据、来源与指标 |
| `fab6bc2` | `3d2dd7c` | 强化构建门禁与 I3-B 生成器 |
| `133be6c` | `fdb287a` | 加入 I3-B release candidate 与验收报告 |
| `a54a078` | `133be6c` | 固化 RC manifest commit SHA |
| `4064d6d` | `a54a078` | 对齐公网预览测试语义 |

注：上述链条中的 `fab6bc2` 的直接父提交为 `3d2dd7c`，其前序内容提交链已在仓库历史中保留；本报告不重写历史、不合并主分支。

## §9 标签、远端 refs 与完整性

| 项目 | 实际值 |
|---|---|
| `asip-intelligence-v1.0-rc1` tag object | `0577f96def36ee74247544bcf26d79b65d7dd11e` |
| `asip-intelligence-v1.0-rc1` peeled commit | `a54a078dc306e633c29a209a530f7e2579f099f6` |
| 远端 rc1 tag | 与上述对象一致 |
| gh-pages 当前 HEAD | `ffb170437d22b434a53353cd95571983b46a98a1` |
| Fix-1A 远端 HEAD | `d5b74d2fda4801dc36a11aeedbe97b47d3373986` |
| I3-B 远端 HEAD | `4064d6ddd1013d2b35acc12a29d5d688d77d46ba` |

完整 `git ls-remote origin`、`git fsck --full`、`git status --porcelain` 结果已保存于：

`qa-artifacts-i3b-fix1a/git-state.json`

基线核验结果：`git fsck --full` 无输出错误；Fix-1A 工作树在提交后干净。

## §10 自动测试

已执行：

- `scripts/build_site.py --no-embed`：PASS；生成 151 条非洲知识库路由，未触碰知识内容；
- `test_i3b_public_preview.py`：8 PASS / 0 FAIL；
- `test_i3b_production_isolation.py`：5 PASS / 0 FAIL；
- `test_i3b_release_candidate.py`：6 PASS / 0 FAIL；
- `test_repository_integrity.py`：28 PASS / 0 FAIL；
- `test_stage2_frontend_final.py`：28 PASS / 0 FAIL；
- Fix-1A 证据脚本 Python 编译检查：PASS。

未虚构不存在的测试文件；仓库中没有预先存在的 `test_i3b_fix1a_pages_deployment.py`、`test_i3b_fix1a_git_chain.py`、`test_i3b_fix1a_production_isolation.py`，本轮未为了填名而伪造测试结果。

## §11 三轮公网验证说明

本轮已完成部署成功后的第一轮 HTTP 验证，六个 URL 均 200。由于用户要求第二轮与第三轮之间至少间隔 10 分钟，且第三轮必须使用全新无缓存真实浏览器会话，当前执行时间尚未满足这一时间条件，因此不能虚构三轮已完成。

当前报告将该项记录为：

`PUBLIC_3_ROUND_GATE_PENDING`

在第二、第三轮真实验证完成前，不应把“公网三轮门禁”标记为最终通过。

## §12 未完成事项

1. 等待至少 10 分钟后执行第二轮六 URL 验证；
2. 使用全新无缓存浏览器会话执行第三轮，记录 console errors、runtime exceptions、failed requests、broken assets、查询参数与深层刷新结果；
3. 完成后更新本报告和 QA 工件，并再次核验 Fix-1A 工作树干净。

本执行包不进入 I3-C，不合并 `main`，不部署生产。
