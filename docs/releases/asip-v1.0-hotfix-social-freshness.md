# ASIP V1.0 Production Hotfix — Social Freshness（state load/commit symmetry）

- **类型**: DATA INTEGRITY / PRODUCTION PIPELINE REPAIR（非新功能）
- **日期**: 2026-09-11（BJT）
- **Production tag**: `asip-v1.0-production`（未移动）
- **状态**: 已修复并上线；数据恢复待下一次自然采集周期确认

## 现象

首页与站点数据长期停留在 **2026-08-02**：`data/canonical/event_clusters.json` 一直是
`run 20260802T084000`、152 条；而 Collection 仍在正常运行（最近成功：2026-09-11T07:05Z，
101 源尝试 / 27 源成功）。

## 根因（HIGH confidence，字节级证据）

orchestrator 的 **Load 与 Commit 路径不对称**：

| 步骤 | 恢复/写回的路径 |
|---|---|
| `Load state（cold start）`（修复前） | **仅** `data/runtime/ops/` |
| `Commit state → production-state` | ops + `canonical` + `disease` + `timeline` + `events.json` + `pending_events.json` + `raw_candidates.json` + `quarantine_events.json` + `public` |

后果：每个 run 都从 **release 代码 checkout 里仓库自带的静态 `data/`** 起步。
- 采集轮（约每 6 小时）会写入新事件 → canonical 前进（如 179 条 / run 20260911T070527）
- **其余每小时的 run 不做采集**，其 canonical 仍是仓库静态副本（152 条 / 20260802），
  提交时被写回 production-state → **状态回退**

证据：
1. `git log origin/production-state -- data/canonical/event_clusters.json` 呈**交替模式**：
   推进(179) → 回退(152) → 推进(184) → 回退(152) → …（09-10 12:20 起每 6 小时一次）
2. 回退后的 canonical blob = `4dc5d072e7f113c30d0411ead3b2de53fafa4af7`，
   与 release 仓库 `7e653da:data/canonical/event_clusters.json` **逐字节相同**
3. 回退发生在**未执行 collection** 的 run（如 run 34575907199 只执行
   `disease_ai / timeline / views_export`），其提交 diff 为 `21435 deletions`
4. 隔离 canary（真实 state 快照 + 仓库副本）复现并验证修复：

```
BEFORE FIX (load=ops only)  | state_before=20260911T070527 | after_load=20260802T084000 | *** REVERTED ***
AFTER  FIX (load=symmetric) | state_before=20260911T070527 | after_load=20260911T070527 | PRESERVED
```

## 修复（最小范围）

`.github/workflows/asip-production-orchestrator.yml` — `Load state（cold start）` 改为**与 Commit 完全对称**，
并追加**载入后 fail-closed 校验**（`data/canonical` 必须采用 state 快照，否则 run 失败）：

```yaml
cp -rf state_src/data/canonical/. data/canonical/
cp -rf state_src/data/disease/. data/disease/
cp -rf state_src/data/runtime/timeline/. data/runtime/timeline/
cp -f  state_src/data/events.json data/events.json
cp -f  state_src/data/pending_events.json data/pending_events.json
cp -f  state_src/data/raw_candidates.json data/raw_candidates.json
cp -f  state_src/data/quarantine_events.json data/quarantine_events.json
cp -rf state_src/data/public/. data/public/
# + STATE_LOAD_OK / STATE_LOAD_MISMATCH 校验
```

未改动：schedule、Cloudflare、concurrency、permissions、Shadow 逻辑、AI 逻辑、Daily 逻辑、
Deploy 门禁、canonical schema、任何 admission/promotion 规则。

`SAFETY_RULE_CHANGED = false`｜`PROMOTION_THRESHOLD_CHANGED = false`｜`PUBLIC_ADMISSION_RULE_CHANGED = false`

## 回归测试

`scripts/tests/test_production_state_symmetry.py`（release 侧，随本 hotfix 一同固化）：
11 项全通过，其中对**修复前**的 workflow 有 3 项按预期失败（证明测试确实锁定该缺陷）。

## 版本记录

| 项目 | SHA |
|---|---|
| Production release（修复前） | `7e653da88fb45bf67f4c53a7ce356441d4ab9607` |
| **Production hotfix release（含回归测试）** | `c42d13de76ecd97c8d660b3e04bd78213878e0cc` |
| Control plane（main） | 见本次提交 |

`asip-v1.0-production` tag 未移动（历史 release 记录）。

## 待观察

下一次自然采集周期（约 2026-09-11T13:05Z 起）应自然完成：
Collection → Candidate persistence → Verification/Admission → Promotion → State commit → View rebuild，
且 `PIPELINE_DATA_AS_OF` 从 2026-08-02 前移。
