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

### 第一轮：部署成功后

成功 deployment `5798271991` / workflow run `31197908566` 完成后，六个目标均返回 HTTP 200。

### 第二轮：稳定时间间隔后

成功 deployment 完成时间为 `2026-08-07T16:31:09Z`；第二轮验证时间为 `2026-08-07T16:41:29Z`，间隔约 10 分 20 秒。

机器可读证据：`qa-artifacts-i3b-fix1a/public-gate-round-2.json`

| 地址 | HTTP | 最终 URL | 内容/行为 |
|---|---:|---|---|
| Africa 首页 | 200 | 保持 github.io 版本化路径 | HTML 正常，CSS/JS 引用存在，深层刷新通过 |
| Mali 深层页 | 200 | 保持 github.io 版本化路径 | HTML 正常，CSS/JS 引用存在，深层刷新通过 |
| Cameroon 深层页 | 200 | 保持 github.io 版本化路径 | HTML 正常，CSS/JS 引用存在，深层刷新通过 |
| JNIM 实体页 | 200 | 保持 github.io 版本化路径 | HTML 正常，CSS/JS 引用存在，深层刷新通过 |
| Network `?focus=actor-jnim` | 200 | 查询参数保留 | HTML 正常，CSS/JS 引用存在，focus 参数保留 |
| `catalog_metrics.json` | 200 | 保持 github.io 版本化路径 | JSON 可解析，深层刷新通过 |

第二轮汇总：`all_http_200=true`、`all_content_valid=true`。

### 第三轮：全新无缓存、无扩展浏览器

使用全新 user-data-dir、`--headless=new`、`--disable-extensions`、`--disable-cache` 的 Edge 会话，并通过 CDP `Network.setCacheDisabled` 再次禁用缓存。保存了包含 github.io 地址栏 URL 的截图：

目录：`qa-artifacts-i3b-fix1a/round-3-browser/`

| 指标 | 结果 |
|---|---:|
| 页面数量 | 6 |
| `consoleErrors` | 0 |
| `runtimeExceptions` | 0 |
| `unexpectedUnhandledRejections` | 0 |
| `unexpectedFailedRequests` | 0 |
| `brokenAssets` | 0 |
| `horizontalOverflow` | 0 |
| HTML 页面 | 5/5 正常 |
| JSON 页面 | 1/1 可解析 |
| CSS 加载 | 5/5 页面均有 2 个 CSS 引用 |
| JS 加载 | 5/5 页面均有 1 个 JS 引用 |
| 查询参数 | `focus=actor-jnim` 保留 |
| 深层刷新 | 6/6 通过 |

机器可读证据：`qa-artifacts-i3b-fix1a/round-3-browser/browser-qa-round-3.json`

第三轮截图：

- `africa-home.png`
- `country-mali.png`
- `country-cameroon.png`
- `entity-jnim.png`
- `network-focus-jnim.png`
- `catalog-metrics.png`

三轮公网门禁结果：

```text
PUBLIC_3_ROUND_GATE = PASS
```

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

## §8 I3-B 完整提交链

I3-B 最终分支：`feature/asip-intelligence-v10-i3b-release-candidate`

I3-B 最终 HEAD：`4064d6ddd1013d2b35acc12a29d5d688d77d46ba`

以下为从 I3-B 非洲知识库基线 `2119be6` 到 I3-B 最终 HEAD 的完整线性提交链。每一行均由机器读取，包含 short SHA、full SHA、parent SHA 和 subject：

| # | short SHA | full SHA | parent SHA | subject |
|---:|---|---|---|---|
| 1 | `2119be6` | `2119be641b1057cbd3ce440a7b66d30310ac1388` | `d5899d6e50d39a91334f0181a1f2b3966a9173de` | feat: add Africa intelligence production schema and regional taxonomy |
| 2 | `9a97aa0` | `9a97aa00b7f8343f584266bc7f2d898f195d8970` | `2119be641b1057cbd3ce440a7b66d30310ac1388` | feat: add high-risk country profiles and regional views |
| 3 | `0a812ce` | `0a812cef3bc5c512030aa5b11ffc36598316fe92` | `9a97aa00b7f8343f584266bc7f2d898f195d8970` | feat: migrate demo entities and add Lake Chad Sudan Mozambique entities |
| 4 | `6d1706e` | `6d1706e20a5a3666c34a736ba3ffdea7850fd841` | `0a812cef3bc5c512030aa5b11ffc36598316fe92` | feat: add Africa relationship evidence and source registry |
| 5 | `2a70a28` | `2a70a282bc163c7d5ef4704c6c987e1acf7f8a0f` | `6d1706e20a5a3666c34a736ba3ffdea7850fd841` | test: add Africa intelligence page filters network and browser validation |
| 6 | `7e977f1` | `7e977f1829b515248303617dfa3ec5cf509be4f5` | `2a70a282bc163c7d5ef4704c6c987e1acf7f8a0f` | chore: validate trusted worktree commit flow |
| 7 | `d09c52a` | `d09c52a3f8215a3cd7cde50afef4d8d54e9fe82b` | `7e977f1829b515248303617dfa3ec5cf509be4f5` | chore: establish trusted git delivery baseline |
| 8 | `490c9e5` | `490c9e51c2adaf3b15f8db65e57559e32bd3f770` | `d09c52a3f8215a3cd7cde50afef4d8d54e9fe82b` | feat: add canonical Africa catalog metrics and profile depth |
| 9 | `4776848` | `477684822689667c2f7ccf44b8eb3a4934156dc8` | `490c9e51c2adaf3b15f8db65e57559e32bd3f770` | data: audit Lake Chad Sudan and Mozambique intelligence claims |
| 10 | `ea78827` | `ea788270aa74c0284b9a9ea4f82e71415520116b` | `477684822689667c2f7ccf44b8eb3a4934156dc8` | fix: preserve intelligence relationship ontology |
| 11 | `154072b` | `154072b00aff11b7ab7c78a1b448221178b3664d` | `ea788270aa74c0284b9a9ea4f82e71415520116b` | fix: eliminate navigation abort noise and add freshness semantics UI |
| 12 | `1d40fcc` | `1d40fcc09b189d8c347fac31084b8e6af6e5d576` | `154072b00aff11b7ab7c78a1b448221178b3664d` | test: add I2-B browser trust and preview gate validation |
| 13 | `6774a74` | `6774a74e3814d87fb2fa310af24cfdce18b2b3e0` | `1d40fcc09b189d8c347fac31084b8e6af6e5d576` | docs: add I2-B trust audit and preview gate acceptance report |
| 14 | `1582e83` | `1582e83630a5d29b0da775b152e3b2002799d555` | `6774a74e3814d87fb2fa310af24cfdce18b2b3e0` | test: relax risk-level assertion to schema compliance (no low-risk country exists) |
| 15 | `f8d3003` | `f8d300365b3876685e5201ecf7d5a3bd0ae0a33b` | `1582e83630a5d29b0da775b152e3b2002799d555` | fix: disperse graph layout 360-deg, encode relation types, restore focus detail entry |
| 16 | `88fe881` | `88fe8811890882edd585d4bd211762a2c8c56cf0` | `f8d300365b3876685e5201ecf7d5a3bd0ae0a33b` | data: deepen country intelligence profiles (Nigeria Libya South Sudan Niger Benin + Chad Sudan Mozambique maintenance) |
| 17 | `87cb492` | `87cb492ebf6c8c708007386093584ca359391ea1` | `88fe8811890882edd585d4bd211762a2c8c56cf0` | data: upgrade core entity encyclopedia and standard profiles |
| 18 | `0cffbb7` | `0cffbb77dad57709d5c3c5c2a0925e14a19da942` | `87cb492ebf6c8c708007386093584ca359391ea1` | data: deepen relationship histories, evidence and sources |
| 19 | `6c4c6d8` | `6c4c6d8b19115eb1178f241067f42d38bebcbdee` | `0cffbb77dad57709d5c3c5c2a0925e14a19da942` | feat: improve encyclopedia reading experience (lead, TOC, tables, in-text links) |
| 20 | `51ba8c1` | `51ba8c1e8e1f755c4519bf2b6e5344b837f52100` | `6c4c6d8b19115eb1178f241067f42d38bebcbdee` | feat: strengthen build-time content quality gates and I3-A generators |
| 21 | `76e4d68` | `76e4d68b6fed19172901645bfede972e4557b3a7` | `51ba8c1e8e1f755c4519bf2b6e5344b837f52100` | test: add I3-A content depth and source coverage validation |
| 22 | `8f1ef5e` | `8f1ef5e6fcdeb2057e976510f6e14659afbf7b9d` | `76e4d68b6fed19172901645bfede972e4557b3a7` | docs: add I3-A browser acceptance evidence |
| 23 | `cffb420` | `cffb420330e9d5721398abb92e14ae9c779a593b` | `8f1ef5e6fcdeb2057e976510f6e14659afbf7b9d` | docs: add I3-A content deepening acceptance report |
| 24 | `d25b520` | `d25b520c3e1463e9c2d00396fd56ef420296c362` | `cffb420330e9d5721398abb92e14ae9c779a593b` | data: deepen Mali Burkina Cameroon Ethiopia Tanzania country profiles (all 13 deep) |
| 25 | `8466394` | `8466394699a8f39b91313277ccacd063811bc960` | `d25b520c3e1463e9c2d00396fd56ef420296c362` | data: upgrade Sahel basic entries (Al-Qaeda Ansar Dine Mourabitoun Katiba Macina AQIM IS Sahel) |
| 26 | `4bb819f` | `4bb819f0e5fb73db7d1073734f72a30640fcc6a2` | `8466394699a8f39b91313277ccacd063811bc960` | data: add 10 core entities for remaining five countries (FAMa Burkina army VDP BIR Ambazonia ENDF Fano OLA TPDF TDF) |
| 27 | `9676a11` | `9676a11892dab6599f43d4e7fb5c01b277247276` | `4bb819f0e5fb73db7d1073734f72a30640fcc6a2` | data: add second-wave relationships and deepen 16 relation histories |
| 28 | `0f68561` | `0f685618fe733626c55ccdc92c748a838395511d` | `9676a11892dab6599f43d4e7fb5c01b277247276` | data: strengthen evidence (45+ manual, pending<=12, freshness), sources 77, metrics v2 |
| 29 | `3d2dd7c` | `3d2dd7c1aff0413bd7ad57a852b00a020ba93155` | `0f685618fe733626c55ccdc92c748a838395511d` | feat: render country lead paragraphs and show non-production preview banner |
| 30 | `fab6bc2` | `fab6bc260d16aa206b8c9df786b3ff99f038061e` | `3d2dd7c1aff0413bd7ad57a852b00a020ba93155` | feat: strengthen build gates (deep 13, basic 0) and add I3-B generators |
| 31 | `23bcfd0` | `23bcfd078b0af80d0cdd2387f2f9ec0dc99ab5bb` | `fab6bc260d16aa206b8c9df786b3ff99f038061e` | test: add I3-B content release and production isolation gates |
| 32 | `fdb287a` | `fdb287a879c6ead072ce0fc4a1c80698863cf67` | `23bcfd078b0af80d0cdd2387f2f9ec0dc99ab5bb` | docs: add I3-B browser QA evidence (55 local + 8 public pages) |
| 33 | `133be6c` | `133be6cf8ce72b2e2638b775a85b16909121130a` | `fdb287a879c6ead072ce0fc4a1c80698863cf67` | docs: add I3-B release candidate package and acceptance report |
| 34 | `a54a078` | `a54a078dc306e633c29a209a530f7e2579f099f6` | `133be6cf8ce72b2e2638b775a85b16909121130a` | docs: finalize RC manifest commit sha |
| 35 | `4064d6d` | `4064d6ddd1013d2b35acc12a29d5d688d77d46ba` | `a54a078dc306e633c29a209a530f7e2579f099f6` | test: align public preview test with verified-alternate-URL semantics (gh-pages CDN propagation pending) |

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

## §12 最终门禁状态

| 门禁 | 状态 |
|---|---|
| github.io 预览首页真实 200 | PASS |
| 深层页面真实 200 | PASS |
| CSS/JS/JSON 正常 | PASS |
| Pages deployment conclusion=success | PASS |
| 成功 run id 明确 | PASS：`31197908566` |
| 三轮公网验证 | PASS |
| 正式网站已有文件零意外修改 | PASS：`existing_changed=0`、`existing_deleted=0` |
| I3-B 完整提交链 | PASS：35 个提交逐项列出 |
| 标签指向明确 | PASS |
| Fix-1A 分支已推送 | PASS |
| 工作树干净 | PASS |
| 未修改事实内容 | PASS |
| 未部署生产 | PASS |
| 未执行 I3-C | PASS |

最终状态：

```text
PUBLIC_3_ROUND_GATE = PASS
I3-B-Fix-1A = CLOSED
```

完成后停止。本执行包不进入 I3-C，不合并 `main`，不部署生产。
