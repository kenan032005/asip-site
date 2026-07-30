# ASIP 第二阶段最终收尾 · 正式验收报告

- 验收时间：2026-07-30（北京时间 21:57–22:10）
- 验收运行：`run_id = 20260730T215708+0800_74kjaq`（唯一一次 `--mode full --trigger manual`）
- main：`44034f9c5d1c3a9d5c2ce89aea98151454979de2`
- gh-pages：`20c07856ed380e0261432a9f9ee54ba65398bda0`
- 回滚点：tag `pre-stage2-closeout`；备份 `data/backup/stage2_closeout_20260730T115059+0000/`

## 一、24 项验收证据

### A. 开工前基线（1–3）
| # | 证据 | 结果 |
|---|------|------|
| 1 | 开工前 `git pull --rebase` 成功，基线 main=73497ca / gh-pages=3c86e48 / 线上 run_id=20260730T035933+0800_8psi3h | ✅ |
| 2 | 回滚 tag `pre-stage2-closeout` 已建并推送 | ✅ |
| 3 | 备份目录 `data/backup/stage2_closeout_20260730T115059+0000/`（canonical/public/events/status/latest-summary/reports/5 脚本/README） | ✅ |

### B. 首页当前事件隔离（4–7）
| # | 证据 | 结果 |
|---|------|------|
| 4 | `is_current_public_event()` 统一过滤入 `pipeline_core.py`，首页三个当前模块（high_risk/latest/china_related）只经它准入 | ✅ |
| 5 | 线上 `latest-summary.json`：high_risk_events=0、latest_events=0、china_related=0（143 条历史迁移全部 current_policy_passed=false，0 是正确结果） | ✅ |
| 6 | `data/public/legacy_archive_events.json` 生成，count=143，字段已裁剪（无 legacy_payload / 本机路径 / 完整正文），线上 HTTP 200 | ✅ |
| 7 | summary note 明确声明"历史迁移保留事件仅存于历史归档，不进入当前态势" | ✅ |

### C. 日报持续跟踪修复（8–11）
| # | 证据 | 结果 |
|---|------|------|
| 8 | `is_ongoing_report_event()`：仅 ongoing/developing/easing、7 天内有活动、非历史迁移方可进入持续跟踪 | ✅ |
| 9 | 线上 `reports/chad/2026-07-29.json`：new_event_count=0=len(new_events)，ongoing_event_count=0=len(ongoing_events) | ✅ |
| 10 | 无持续跟踪时输出说明文案"当前无符合条件的持续跟踪事项。"（ongoing_note 非空） | ✅ |
| 11 | 六国日报均由本次 run 重新生成（run_id=74kjaq、pipeline_version=2） | ✅ |

### D. 内部数据公网隔离（12–17）
| # | 证据 | 结果 |
|---|------|------|
| 12 | `build_site.py` 改为 `PUBLIC_DATA_ALLOWLIST` 显式白名单复制，删除整目录 copytree | ✅ |
| 13 | `__DB__` 内联快照改用 `load_public_db()`（仅白名单 + 脱敏） | ✅ |
| 14 | 线上 404 验证：`data/canonical/articles.json`、`event_clusters.json`、`sources.json`、`migration_state.json`、`data/backup/` 均 404 | ✅ |
| 15 | 线上 404 验证：`pending_events.json`、`raw_candidates.json`、`quarantine_events.json` 均 404 | ✅ |
| 16 | 线上 `sources.json` / `index.html` / 归档文件：无 legacy_payload、无本机路径 | ✅ |
| 17 | gh-pages 以全新 tree 部署（commit-tree），旧 canonical 泄漏文件已从公网移除 | ✅ |

### E. 统计与日志语义（18–19）
| # | 证据 | 结果 |
|---|------|------|
| 18 | 线上 `current_metrics.json`：publishable_clusters=0 == current_policy_passed_events=0；legacy_migration_preserved_events=143 | ✅ |
| 19 | 运行日志补齐：deploy_completed_at=2026-07-30T21:57:32+08:00、deployment_commit=20c07856（=gh-pages HEAD） | ✅ |

### F. 校验、测试与文档（20–22）
| # | 证据 | 结果 |
|---|------|------|
| 20 | `validate_pipeline`：V16 重写（历史可见≠可进首页）、新增 V18/V19，dist 阶段 0 严重错误；`validate_stage2` 48 项 PASS=48 FAIL=0 | ✅ |
| 21 | 新增 `scripts/tests/test_stage2_closeout.py` 22 项全过；6 套测试套件（24+36+57+28+5+22）全部 FAIL=0 且已入流水线闸门 | ✅ |
| 22 | README 矛盾消除：11.3/13.2 分层与部署边界、42→48 项、源数量动态化、新增第十五节统一声明 | ✅ |

### G. 发布与线上一致性（23–24）
| # | 证据 | 结果 |
|---|------|------|
| 23 | 两个功能 commit 按规格拆分：`3a35a1d`（isolate current events and fix report tracking）、`09aaf2a`（protect internal data and finalize documentation）+ 修复 `e98a12b`/`4adee71`/`a45cdb1`，均已推送 | ✅ |
| 24 | 9 个公开 URL 全部 200（首页、status、latest-summary、events、countries、risk-levels、sources、published_events、current_metrics + legacy_archive_events）；线上 run_id 与本地一致（74kjaq），online_verified_at=21:58:03 | ✅ |

## 二、边界确认

未重新全量迁移、未删除 Canonical 历史（143 条完整保留）、未新增信息源、未抓取外部新闻、未调用 Hy3、未开发自动核实/智能聚类、未修改网站样式、未扩展国家。**Stage 2.5 与第三阶段均未开始。**

## 三、结论

24 项证据全部满足，遗留 6 问题全部关闭：

**第二阶段正式完成。**
