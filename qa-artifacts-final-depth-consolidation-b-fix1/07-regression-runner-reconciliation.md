# 07 — Regression Runner Reconciliation

## 结论一句话

上一轮报告的「62/66、4 failures 全部 pre-existing」是**错误口径**：这 4 个
「failure」里有 2 个是 Pack B 引入的**真实新失败**（count pin 未同步），1 个是
runner 的**误报**，1 个是**正式回归范围之外**的 Stage 管线测试。Fix-1 已把正式
回归口径跑成 **41 suites / 0 failures**。

## 两个 runner 的口径差异

| 维度 | 正式 runner（accepted） | 上一轮 ad-hoc runner |
|------|------------------------|----------------------|
| 脚本 | `scripts/qa/post_consolidation_audit_p2_regression.py` | 临时 subprocess 循环 |
| 发现范围 | `scripts/tests/intelligence/test_*.py`（39）+ 2 EXTRA | 全部 `scripts/tests/**/*.py` |
| suite 数 | 41 | 66 |
| 分类 | `rc == 0` 判 PASS | 模糊匹配（有误报） |
| 基线结果 | **41 suites / 7204 cases / 0 failures** | （未在基线跑） |

66 = 39 intelligence + 2 EXTRA（`test_no_local_paths` / `test_repository_integrity`）
+ 25 个 Stage 管线测试（`test_stage*.py`、`test_country.py` 等）。后 25 个属于
新闻管线（Stage-2 pipeline），**不属于 Africa intelligence 回归**。

## 4 个 failure 的逐一判定

| suite | 实际现象 | 判定 | 处置 |
|-------|---------|------|------|
| `intelligence/test_i3d1_import.py` | `relationships=203 != 201` | **Pack B 新失败**（+2 关系后 count pin 未同步） | 已修：`201→203` |
| `intelligence/test_i3d2_import.py` | `relationships=203 != 201` | **Pack B 新失败**（同上） | 已修：`201→203` |
| `tests/test_stage1_pipeline.py` | 本地绝对路径扫描 FAIL | **范围外 + 预存在**（baseline 同样 rc=1） | 不修（Stage 管线测试） |
| `tests/test_stage25de_cloud_provider.py` | 实际 `PASS=29 FAIL=0`，rc=0 | **误报**（runner 分类 bug） | 不修（本来就通过） |

## 基线 A/B 对照（同一 runner、同一环境）

| 指标 | 基线 `cca534d` | Fix-1 候选 |
|------|----------------|-----------|
| suites | 41 | 41 |
| cases | 7204 | 7310 |
| pass | 7204 | 7310 |
| **fail** | **0** | **0** |
| FULL_REGRESSION | PASS | PASS |

- `NEW_FAILURES = 0`
- case 增量 +106：Pack B 新增 2 关系 + 16 来源 + 17 证据 + 11 个 encyclopedia_full
  profile，断言数量自然增加，无新增失败。

## 7204 vs 7310 的解释

「41 suites / 7204 cases / 0 failures」是**基线（Pack B 之前）**的正式回归口径。
Pack B 导入数据后，case 数增至 7310（数据变多、断言变多），但仍为 **0 失败**。
两者用**同一个 runner、同一套发现与分类逻辑**，口径一致，只是数据规模变化。

## 正式验收口径

`FULL_REGRESSION = PASS`，`TEST_CASES_FAILED = 0`。不接受「pre-existing」作为
最终 PASS 替代——4 个 failure 已逐一判定并闭环（2 修、1 误报排除、1 范围外排除）。
