# ASIP Stage 1 — 整改前基线快照
- 北京时���备份：2026-07-29 14:07:34 (UTC+8)
- 备份目录：data/backup/stage1_20260729_140734/

## Git 状态
- main commit: 55307051d692cbcd230ab990ac7e459f9732e6d3
- main message: "docs+enh: 强制接入Reuters/新华网收尾复测..."
- gh-pages remote: 3b3a4e2d64f98081803afed690f180a7650901f4 ("Initial ASIP site")
- 分支: main (本地), origin/main (远程), origin/gh-pages (远程)

## 线上状态
- 站点: https://kenan032005.github.io/asip-site/
- 线上 events_24h: 81
- 线上 last_update_bj: 2026-07-29 13:47:23
- 线上 summary 近24小时事件: 0（与status 81矛盾！）
- 线上无 run_id
- 线上无 pipeline_version
- 线上无 ASIP_BUILD_META

## 数据池
- events.json: 143 条（乍得 2 / 尼日尔 0）
- pending_events.json: 26 条（乍得 19 / 尼日尔 7）
- quarantine_events.json: 54 条
- raw_candidates.json: 与 sources.json 同属采集侧

## 已知问题（本阶段需修复）
1. status 和 summary 的 24h 数字矛盾（81 vs 0）
2. 缺少 run_id 贯穿全链路
3. 缺少 pipeline_version 隔离
4. status.json 字段不完整（无 chad/niger/pending/quarantine 单独统计）
5. 前端无容错机制（整体加载失败）
6. HTML 内嵌数据快照可能导致数据不一致
7. 日报时间窗口校验不充分
8. gh-pages 仅 1 次初始提交，缺少部署记录
9. GitHub Actions workflow 本地存在但未提交到仓库
