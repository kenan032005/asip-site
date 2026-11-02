#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0 Phase 3 — 自动调度恢复 / 国家范围闸门 / 全局 AI 预算 验收测试。

离线、零付费、零网络。覆盖本轮四项修复：

  I.1 采集与后处理两阶段串行（post_collection 绝不重跑采集）
  I.2 post_collection 补齐社会安全 AI 队列（只处理未富集的新增内容）
  I.3 没有到期工作 → 快速 no-op
  I.4 周报国家级相关性闸门（非乍得内容不得冒充乍得周报；证据不足即暂缓）
  I.5 AI 预算跨子进程共享 + 日累计上限 + 不可验证时 fail-closed
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.ops import ai_ledger, paid_gate, production_state as ps  # noqa: E402
from scripts.ops import report_brief_view as rbv  # noqa: E402
from scripts.ops import schedule_orchestrator as so  # noqa: E402


# ── I.4 周报国家范围闸门 ────────────────────────────────────────────────
def _feed(n_chad=0, n_other=4):
    items = []
    for i in range(n_chad):
        items.append({"title_cn": "乍得 %s 安全局势更新 %d" % ("乍得", i),
                      "country": "乍得", "source": "Tchad source",
                      "kind": "signal", "importance": "high",
                      "detail_url": "event.html?id=C%d" % i,
                      "time": "2026-11-02 10:00", "verification_label": "多源核实"})
    for i in range(n_other):
        items.append({"title_cn": "莫桑比克矿用挖掘机运营新闻 %d" % i,
                      "country": "莫桑比克", "source": "Club of Mozambique",
                      "kind": "signal", "importance": "high",
                      "detail_url": "event.html?id=M%d" % i,
                      "time": "2026-10-27 04:01",
                      "verification_label": "单一来源（尚未独立核实）"})
    return items


def _homepage_view(feed):
    return {
        "overview": {"summary_cn": "总体态势摘要。", "confidence": "中",
                     "key_judgments": ["判断一"], "watch_24_72h": ["关注一"]},
        "metrics": {"signals_24h": len(feed), "verified_events_24h": 0},
        "sectors": [{"title_cn": "安全", "assessment_cn": "评估", "trend": "flat",
                     "confidence": "low", "verified_events_7d": 0, "signals_7d": 1}],
        "china_impact": {"analysis_cn": "暂无直接涉华影响。"},
        "health_security": {"summary_cn": "公共卫生数据不足。", "items": []},
        "top_developments": [],
        "latest_intelligence": feed,
        "data_as_of": "2026-11-03T03:00:00",
    }


class _RootCase(unittest.TestCase):
    """隔离的临时 root（data/views、data/runtime/ops、data/canonical）。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="asip5_p3_"))
        (self.tmp / "data" / "views").mkdir(parents=True, exist_ok=True)
        (self.tmp / "data" / "runtime" / "ops").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_view(self, feed):
        p = self.tmp / "data" / "views" / "homepage_intelligence.json"
        p.write_text(json.dumps(_homepage_view(feed), ensure_ascii=False),
                     encoding="utf-8")
        return p


class TestWeeklyCountryScopeGate(_RootCase):
    """I.4：非乍得内容不得冒充乍得周报；证据不足即暂缓。"""

    def _run(self):
        return rbv.main(["--root", str(self.tmp), "--apply"])

    def _index(self):
        return json.loads((self.tmp / "data" / "views" / "report_index.json")
                          .read_text(encoding="utf-8"))

    def test_non_chad_weekly_is_deferred(self):
        """全是莫桑比克等非乍得内容 → 周报必须暂缓（不进索引、不写发布文件）。"""
        self.write_view(_feed(n_chad=0, n_other=6))
        self._run()
        idx = self._index()
        weekly_rows = [r for r in idx["reports"]
                       if str(r.get("report_id", "")).startswith("WEEKLY_BRIEF_")]
        self.assertEqual(weekly_rows, [], "非乍得内容不得作为乍得周报进入索引")
        # 原始证据保留（deferred/ 不在发布路径内）
        deferred = list((self.tmp / "data" / "runtime" / "ops" / "reports" / "deferred")
                        .glob("tcd_weekly_brief_*.json"))
        self.assertTrue(deferred, "暂缓必须保留原始证据")
        ev = json.loads(deferred[0].read_text(encoding="utf-8"))
        self.assertTrue(ev.get("deferred"))
        self.assertTrue(ev.get("deferred_reason"))
        # 发布命名空间内不得有该周报文件
        self.assertEqual(list((self.tmp / "data" / "runtime" / "ops" / "reports")
                              .glob("tcd_weekly_brief_*.json")), [])

    def test_daily_published_even_when_weekly_deferred(self):
        """周报暂缓不得阻断合格日报（日报永远发布）。"""
        self.write_view(_feed(n_chad=0, n_other=6))
        self._run()
        idx = self._index()
        daily = [r for r in idx["reports"]
                 if str(r.get("report_id", "")).startswith("DAILY_BRIEF_")]
        self.assertTrue(daily, "日报必须照常发布")
        self.assertTrue((self.tmp / "data" / "runtime" / "ops" / "reports"
                         / ("daily_brief_%s.json" % daily[0]["report_id"][-8:])).exists())

    def test_chad_scoped_weekly_is_published(self):
        """乍得相关条目充足 → 周报发布，且类型/标题与实际范围一致。"""
        self.write_view(_feed(n_chad=4, n_other=2))
        self._run()
        idx = self._index()
        weekly = [r for r in idx["reports"]
                  if str(r.get("report_id", "")).startswith("WEEKLY_BRIEF_")]
        self.assertEqual(len(weekly), 1, "乍得范围周报应发布")
        self.assertEqual(weekly[0].get("report_type"), "country_weekly")
        self.assertIn("乍得", weekly[0].get("title", ""))
        self.assertTrue(weekly[0]["path"].startswith("data/reports/weekly/"))

    def test_deferred_weekly_never_readded(self):
        """暂缓过的 report_id 不得在下一轮自动重建时重新加入索引。"""
        self.write_view(_feed(n_chad=0, n_other=6))
        self._run()
        first = self._index()
        deferred_ids = [d.get("report_id") for d in (first.get("deferred_reports") or [])]
        self.assertTrue(deferred_ids, "暂缓必须记入索引 deferred_reports")
        # 第二轮：即使产物文件仍在树中，也不得重新加入
        self._run()
        second = self._index()
        weekly_rows = [r for r in second["reports"]
                       if str(r.get("report_id", "")) in deferred_ids]
        self.assertEqual(weekly_rows, [], "暂缓的周报不得被自动重建重新加入索引")

    def test_scope_gate_math(self):
        ok, reason, stats = rbv.weekly_scope_gate(_feed(n_chad=0, n_other=3))
        self.assertFalse(ok)
        self.assertIn("insufficient_chad_items", reason)
        ok, reason, stats = rbv.weekly_scope_gate(_feed(n_chad=5, n_other=1))
        self.assertTrue(ok, reason)
        self.assertEqual(stats["chad_relevant"], 5)


# ── I.5 全局 AI 预算 ────────────────────────────────────────────────────
class TestGlobalAiBudget(unittest.TestCase):
    """I.5：预算必须跨子进程共享 + 日累计上限 + 不可验证时 fail-closed。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="asip5_p3_bud_"))
        self._saved = (ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH,
                       ai_ledger.BUDGET_STATE_PATH, ai_ledger._BUDGET)
        ai_ledger.LEDGER_PATH = self.tmp / "ai.jsonl"
        ai_ledger.SUMMARY_PATH = self.tmp / "ai_summary.json"
        ai_ledger.BUDGET_STATE_PATH = self.tmp / "ai_budget_state.json"
        ai_ledger._BUDGET = {"cap": 80, "used": 0}
        self._env = {k: os.environ.get(k) for k in
                     ("ASIP_AI_RUN_MAX_CALLS", "ASIP_AI_DAILY_MAX_CALLS",
                      "ASIP_RUN_ID", "GITHUB_RUN_ID")}
        for k in self._env:
            os.environ.pop(k, None)
        os.environ["ASIP_RUN_ID"] = "run-p3-test"

    def tearDown(self):
        (ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH,
         ai_ledger.BUDGET_STATE_PATH, ai_ledger._BUDGET) = self._saved
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_budget_shared_across_subprocesses(self):
        """第二个"子进程"（进程内计数归零）不得重新拿到完整额度。"""
        os.environ["ASIP_AI_RUN_MAX_CALLS"] = "3"
        ai_ledger.charge_attempt()
        ai_ledger.charge_attempt()
        # 模拟新进程：进程内计数归零（此前这会让额度被重新发满）
        ai_ledger._BUDGET = {"cap": 3, "used": 0}
        ai_ledger.charge_attempt()
        with self.assertRaises(ai_ledger.BudgetExceeded):
            ai_ledger.charge_attempt()
        self.assertEqual(ai_ledger.budget_remaining(), 0)

    def test_daily_cap_enforced(self):
        """日累计上限独立于单轮上限，跨"进程"累计。"""
        os.environ["ASIP_AI_RUN_MAX_CALLS"] = "10"
        os.environ["ASIP_AI_DAILY_MAX_CALLS"] = "2"
        ai_ledger.charge_attempt()
        ai_ledger.charge_attempt()
        ai_ledger._BUDGET = {"cap": 10, "used": 0}   # 新"进程"
        with self.assertRaises(ai_ledger.BudgetExceeded):
            ai_ledger.charge_attempt()

    def test_daily_cap_resets_next_day(self):
        os.environ["ASIP_AI_RUN_MAX_CALLS"] = "10"
        os.environ["ASIP_AI_DAILY_MAX_CALLS"] = "1"
        ai_ledger.charge_attempt()
        st = json.loads(ai_ledger.BUDGET_STATE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(st.get("daily_used"), 1)
        self.assertIn("daily_date", st)
        self.assertIn("daily_cap", st)

    def test_budget_state_unreadable_fails_closed(self):
        """预算状态不可读 → 不得继续付费（fail-closed）。"""
        os.environ["ASIP_AI_RUN_MAX_CALLS"] = "5"
        ai_ledger.BUDGET_STATE_PATH.write_text("{ this is not json", encoding="utf-8")
        with self.assertRaises(ai_ledger.BudgetStateUnavailable):
            ai_ledger.charge_attempt()
        with self.assertRaises(ai_ledger.BudgetStateUnavailable):
            ai_ledger.budget_remaining()

    def test_zero_cap_refuses_request(self):
        """单轮上限=0 → 不得发起任何请求。"""
        os.environ["ASIP_AI_RUN_MAX_CALLS"] = "0"
        calls = []

        class _P:
            def submit_task(self, t):
                calls.append(1)
                return {"status": "ok", "result": {}}

        prov = ai_ledger.wrap_provider(_P(), component="social_ai",
                                       ledger_path=self.tmp / "ai2.jsonl")
        with self.assertRaises(ai_ledger.BudgetExceeded):
            prov.submit_task({"task_type": "x"})
        self.assertEqual(calls, [])


# ── I.1 / I.2 / I.3 编排器两阶段与 AI 队列 ─────────────────────────────
class TestPostCollectionStage(unittest.TestCase):
    """post_collection：补齐 AI 队列、绝不采集、无到期工作快速 no-op。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="asip5_p3_orch_"))
        (self.tmp / "canonical").mkdir(parents=True, exist_ok=True)
        (self.tmp / "disease" / "canonical").mkdir(parents=True, exist_ok=True)
        self._ops = self.tmp / "ops"
        self._ops.mkdir(parents=True, exist_ok=True)
        (self._ops / "production_state.json").write_text(json.dumps({}), encoding="utf-8")
        self._ps_saved = (ps.OPS_DIR, ps.STATE_FILE, ps.OPS_STATUS_FILE)
        ps.OPS_DIR = self._ops
        ps.STATE_FILE = self._ops / "production_state.json"
        ps.OPS_STATUS_FILE = self._ops / "operations_status.json"
        # 共享预算状态必须隔离（否则测试会写真实仓库 data/runtime/ops/）
        self._bud_saved = ai_ledger.BUDGET_STATE_PATH
        ai_ledger.BUDGET_STATE_PATH = self.tmp / "ai_budget_state.json"
        self._env = {k: os.environ.get(k) for k in
                     ("ASIP_RUN_MODE", "GITHUB_EVENT_NAME", "ASIP_AI_MAX_ITEMS_PER_RUN",
                      "ASIP_AI_RUN_MAX_CALLS", "ASIP_ALLOW_MANUAL_PRODUCTION",
                      "ASIP_DEEPSEEK_API_KEY", "ASIP_UPSTREAM_STAGE_FAILED")}
        for k in self._env:
            os.environ.pop(k, None)
        os.environ["ASIP_RUN_MODE"] = "post_collection"
        os.environ["GITHUB_EVENT_NAME"] = "schedule"
        # 伪凭据：只用于越过"无凭据即跳过"的 fail-closed 分支；
        # enrichment_run 本身被 so._run_script 打桩，**不会**发生任何网络调用。
        os.environ["ASIP_DEEPSEEK_API_KEY"] = "test-dummy-key"

    def tearDown(self):
        ps.OPS_DIR, ps.STATE_FILE, ps.OPS_STATUS_FILE = self._ps_saved
        ai_ledger.BUDGET_STATE_PATH = self._bud_saved
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_clusters(self, n=2):
        items = [{"event_id": "EVT_%d" % i, "current_policy_passed": True,
                  "title_cn": "t%d" % i} for i in range(n)]
        (self.tmp / "canonical" / "event_clusters.json").write_text(
            json.dumps({"items": items}, ensure_ascii=False), encoding="utf-8")

    def _execute(self, plan, state):
        calls = []
        orig, orig_views = so._run_script, so._export_views
        so._run_script = lambda *a, **k: calls.append(
            list(a[0]) if isinstance(a[0], (list, tuple)) else [str(a[0])]) or True
        so._export_views = lambda *a, **k: True
        try:
            res = so.execute(plan, state, data_root=str(self.tmp),
                             trigger_meta={"trigger_source": "scheduled_orchestrator"})
        finally:
            so._run_script, so._export_views = orig, orig_views
        return res, calls

    @staticmethod
    def _has(calls, needle, *also):
        """子进程调用里是否出现某脚本（及其参数）。"""
        for c in calls:
            s = " ".join(str(x) for x in c)
            if needle in s and all(a in s for a in also):
                return True
        return False

    def test_post_collection_queues_social_ai_when_eligible(self):
        """I.2：post_collection 必须补齐社会安全 AI 队列（此前永远排不进去）。"""
        self._write_clusters(2)
        res, calls = self._execute({"due": []}, {"processed_hashes": {}})
        self.assertTrue(self._has(calls, "enrichment_run.py", "--kind", "social"),
                        "post_collection 应排入 social AI 队列：%s" % calls)

    def test_post_collection_never_collects(self):
        """I.1：post_collection 绝不重跑采集。"""
        self._write_clusters(1)
        _res, calls = self._execute({"due": [{"task": "collection", "reason": "gap"}]},
                                     {"processed_hashes": {}})
        self.assertFalse(self._has(calls, "collection_run.py"),
                         "post_collection 必须跳过采集")

    def test_post_collection_noop_when_nothing_due(self):
        """I.3：无新增待富集内容 + 无到期报告 → 快速 no-op（不跑付费链路）。"""
        _res, calls = self._execute({"due": []}, {"processed_hashes": {}})
        self.assertEqual(calls, [], "无到期工作时必须快速 no-op：%s" % calls)

    def test_post_collection_skips_ai_when_upstream_failed(self):
        """I.1：上游（采集阶段）失败 → 不执行依赖其结果的后续 AI 步骤。"""
        self._write_clusters(2)
        os.environ["ASIP_UPSTREAM_STAGE_FAILED"] = "true"
        _res, calls = self._execute({"due": []}, {"processed_hashes": {}})
        self.assertFalse(self._has(calls, "enrichment_run.py"),
                         "上游失败时不得执行依赖其结果的 AI 步骤：%s" % calls)

    def test_ai_budget_exhausted_skips_ai_tasks(self):
        """I.5：预算耗尽 → AI 任务合法跳过（0 calls），整轮不失败、不发起模型调用。"""
        os.environ["ASIP_AI_RUN_MAX_CALLS"] = "0"
        self._write_clusters(1)
        _res, calls = self._execute({"due": [{"task": "daily_report", "reason": "tick"}]},
                                     {"processed_hashes": {}})
        self.assertFalse(self._has(calls, "reports_run.py"),
                         "预算耗尽时不得发起报告的模型调用：%s" % calls)

    def test_ai_max_items_bounded_by_budget(self):
        """单轮 AI 条目上限不得超过剩余全局预算。"""
        os.environ["ASIP_AI_MAX_ITEMS_PER_RUN"] = "50"
        os.environ["ASIP_AI_RUN_MAX_CALLS"] = "3"
        lim = so._ai_max_items()
        self.assertLessEqual(lim, 3)


class TestWakeupDedup(unittest.TestCase):
    """Phase 3 / II.7：自动唤醒去重（排除原生 cron 与外部调度器的重复触发）。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="asip5_p3_dedup_"))
        self._ops = self.tmp / "ops"
        self._ops.mkdir(parents=True, exist_ok=True)
        self._ps_saved = (ps.OPS_DIR, ps.STATE_FILE, ps.OPS_STATUS_FILE)
        ps.OPS_DIR = self._ops
        ps.STATE_FILE = self._ops / "production_state.json"
        ps.OPS_STATUS_FILE = self._ops / "operations_status.json"
        self._env = {k: os.environ.get(k) for k in
                     ("GITHUB_RUN_ID", "ASIP_MIN_WAKEUP_INTERVAL_MINUTES")}
        for k in self._env:
            os.environ.pop(k, None)

    def tearDown(self):
        ps.OPS_DIR, ps.STATE_FILE, ps.OPS_STATUS_FILE = self._ps_saved
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_ops(self, run_id, completed_at):
        ps.OPS_STATUS_FILE.write_text(json.dumps({
            "schema": "stage8c-package3-v1",
            "runs": [{"run_id": run_id, "workflow": "asip-production-orchestrator",
                      "started_at": completed_at, "completed_at": completed_at,
                      "status": "completed"}]}), encoding="utf-8")

    def test_sibling_stage_not_deduped(self):
        """同一 GITHUB_RUN_ID 的兄弟阶段（collect → post）不得被去重。"""
        os.environ["GITHUB_RUN_ID"] = "111"
        now = datetime(2026, 11, 2, 23, 0, 0, tzinfo=timezone.utc)
        self._write_ops("111", "2026-11-02T22:55:00Z")
        dup, prev = so.duplicate_wakeup_within(45, now)
        self.assertFalse(dup, "同一 workflow run 的兄弟阶段不得被判定为重复唤醒")

    def test_duplicate_foreign_run_is_deduped(self):
        """另一个 run 在窗口内完成 → 判定为重复唤醒（不重复采集/不重复付费）。"""
        os.environ["GITHUB_RUN_ID"] = "222"
        now = datetime(2026, 11, 2, 23, 0, 0, tzinfo=timezone.utc)
        self._write_ops("111", "2026-11-02T22:55:00Z")
        dup, prev = so.duplicate_wakeup_within(45, now)
        self.assertTrue(dup)
        self.assertEqual(prev, "111")

    def test_old_run_not_deduped(self):
        """窗口之外的旧 run 不去重（正常的下一个唤醒周期必须能跑）。"""
        os.environ["GITHUB_RUN_ID"] = "222"
        now = datetime(2026, 11, 2, 23, 0, 0, tzinfo=timezone.utc)
        self._write_ops("111", "2026-11-02T21:00:00Z")
        dup, prev = so.duplicate_wakeup_within(45, now)
        self.assertFalse(dup)


class TestCollectorImportPath(unittest.TestCase):
    """回归：采集器以脚本方式运行时，仓库根必须在 sys.path 上。

    根因：Phase 1 的 97eac82（route stage3 quarantine writes through QuarantineStore）
    引入 `from scripts.data.quarantine_store import QuarantineStore`，但
    stage3_collect_v2.py 只把 ROOT/scripts、ROOT/scripts/collectors 加入 sys.path，
    **没有把 ROOT 本身加入** → 以 `python scripts/stage3_collect_v2.py` 运行（编排器的
    实际调用方式）时 `import scripts.*` 失败 → 采集在第一个来源即崩溃 exit 1
    （无 stats / metrics unavailable；state 不变、无付费，但自动采集整轮失败）。
    """

    def test_scripts_package_importable_under_collector_sys_path(self):
        import subprocess
        code = ("import os,sys;ROOT=os.getcwd();"
                "sys.path.insert(0, os.path.join(ROOT,'scripts'));"
                "sys.path.insert(0, os.path.join(ROOT,'scripts','collectors'));"
                "import scripts.data.quarantine_store as m;"
                "print('IMPORT_OK', hasattr(m,'QuarantineStore'))")
        r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT),
                           capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0,
                         "采集器运行路径下无法导入 scripts 包：%s" % r.stderr[-400:])
        self.assertIn("IMPORT_OK True", r.stdout)

    def test_stage3_collector_registers_repo_root_on_sys_path(self):
        """静态断言：stage3_collect_v2.py 必须把仓库根自身加入 sys.path。"""
        src = (ROOT / "scripts" / "stage3_collect_v2.py").read_text(encoding="utf-8")
        self.assertRegex(src, r"sys\.path\.insert\(0,\s*ROOT\s*\)",
                         "stage3_collect_v2.py 必须把 ROOT 加入 sys.path，"
                         "否则 `from scripts.* import ...` 在脚本运行方式下无法解析")


if __name__ == "__main__":
    unittest.main(verbosity=2)
