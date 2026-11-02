#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-2A — 账本收尾 / post_collection / 预算上限（离线、零付费）。"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.ops import ai_ledger, paid_gate  # noqa: E402
from scripts.ops import production_state as ps  # noqa: E402
from scripts.ops import schedule_orchestrator as so  # noqa: E402


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="asip5_2a_"))
        self._saved = (ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH,
                       paid_gate.BREAKER_PATH, paid_gate.BREAKER_REMOTE_PATH)
        ai_ledger.LEDGER_PATH = self.tmp / "ai.jsonl"
        ai_ledger.SUMMARY_PATH = self.tmp / "ai_summary.json"
        paid_gate.BREAKER_PATH = self.tmp / "breaker.json"
        paid_gate.BREAKER_REMOTE_PATH = self.tmp / "remote.json"
        paid_gate.save_remote_status(True, "test")
        # 隔离 production_state 落盘路径，避免写真实仓库 data/
        _ops = self.tmp / "ops"
        _ops.mkdir(parents=True, exist_ok=True)
        (_ops / "production_state.json").write_text(
            json.dumps({"last_successful_collection": "2026-11-02T18:00:00Z",
                        "processed_hashes": {"social_enrichment": {"h1": {}}}}), encoding="utf-8")
        self._ps_saved = (ps.OPS_DIR, ps.STATE_FILE, ps.OPS_STATUS_FILE)
        ps.OPS_DIR = _ops
        ps.STATE_FILE = _ops / "production_state.json"
        ps.OPS_STATUS_FILE = _ops / "operations_status.json"
        self._env = {k: os.environ.get(k) for k in
                     ("ASIP_RUN_MODE", "ASIP_AI_RUN_MAX_CALLS", "GITHUB_EVENT_NAME",
                      paid_gate.PAUSE_ENV)}
        for k in self._env:
            os.environ.pop(k, None)

    def tearDown(self):
        (ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH,
         paid_gate.BREAKER_PATH, paid_gate.BREAKER_REMOTE_PATH) = self._saved
        ps.OPS_DIR, ps.STATE_FILE, ps.OPS_STATUS_FILE = self._ps_saved
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _record(self, run_id, calls=1):
        for i in range(calls):
            ai_ledger.record(component="social_ai", input_tokens=100, output_tokens=50,
                             total_tokens=150, status="succeeded", run_id=run_id,
                             path=ai_ledger.LEDGER_PATH)


class TestLedgerFinalize(_Base):
    def test_zero_summary_for_run_without_calls(self):
        s = ai_ledger.finalize_run_ledger(run_id="R-empty")
        self.assertTrue(s["ok"] and s["verified"])
        self.assertEqual(s["totals"]["calls"], 0)
        self.assertTrue(s["zero_calls_confirmed"])
        self.assertEqual(s["run_id"], "R-empty")

    def test_real_calls_not_forced_to_zero(self):
        self._record("R-real", calls=3)
        s = ai_ledger.finalize_run_ledger(run_id="R-real")
        self.assertEqual(s["totals"]["calls"], 3, "真实调用不得被强制写 0")
        self.assertEqual(s["totals"]["input_tokens"], 300)
        self.assertFalse(s["zero_calls_confirmed"])

    def test_unwritable_ledger_reports_not_pass(self):
        d = self.tmp / "as_dir"
        d.mkdir()
        ai_ledger.SUMMARY_PATH = d        # 目标是目录 → 写入必失败
        s = ai_ledger.finalize_run_ledger(run_id="R-x", summary_path=d)
        self.assertFalse(s["ok"], "账本不可写不得报告 PASS")
        self.assertFalse(s["verified"])

    def test_run_id_aligns_with_ledger(self):
        self._record("R-align", calls=1)
        s = ai_ledger.finalize_run_ledger(run_id="R-align")
        self.assertEqual(s["run_id"], "R-align")
        self.assertEqual(s["records_for_run"], 1)


class TestPostCollection(_Base):
    def test_skips_collection_runs_ai_tasks(self):
        os.environ["ASIP_RUN_MODE"] = "post_collection"
        calls = []
        orig, orig_views = so._run_script, so._export_views
        so._run_script = lambda *a, **k: calls.append(a[0][0] if isinstance(a[0], (list, tuple))
                                                      else str(a[0])) or True
        so._export_views = lambda *a, **k: True      # 不触碰真实 data/
        try:
            res = so.execute({"due": [{"task": "collection", "reason": "gap"},
                                      {"task": "social_ai", "reason": "eligible"},
                                      {"task": "daily_report", "reason": "tick"}]},
                             {"processed_hashes": {}},
                             trigger_meta={"trigger_source": "workflow_dispatch"})
        finally:
            so._run_script, so._export_views = orig, orig_views
        self.assertEqual(res.get("mode"), "post_collection")
        self.assertFalse(any("collection_run.py" in c for c in calls),
                         "post_collection 必须跳过 stage3 采集")
        self.assertTrue(any("enrichment_run" in c or "reports_run" in c for c in calls),
                        "post_collection 应执行 AI/报告任务")

    def test_post_collection_requires_manual_auth(self):
        os.environ["ASIP_RUN_MODE"] = "post_collection"
        os.environ["GITHUB_EVENT_NAME"] = "workflow_dispatch"
        os.environ.pop("ASIP_ALLOW_MANUAL_PRODUCTION", None)
        self.assertFalse(so.manual_production_authorized())
        rc = so.main(["--run", "--json"])
        self.assertEqual(rc, 3, "未授权的人工 post_collection 必须被拒")

    def test_automatic_triggers_still_locked(self):
        for ev in ("schedule", "repository_dispatch"):
            os.environ["GITHUB_EVENT_NAME"] = ev
            self.assertTrue(so.automatic_runs_locked(), ev)


class TestBudget(_Base):
    def test_cap_counts_attempts_including_retries(self):
        os.environ["ASIP_AI_RUN_MAX_CALLS"] = "3"
        ai_ledger._BUDGET["cap"] = 3
        ai_ledger._BUDGET["used"] = 0
        for i in range(3):
            ai_ledger.charge_attempt()
        with self.assertRaises(ai_ledger.BudgetExceeded):
            ai_ledger.charge_attempt()          # 第 4 次（含重试）即拒绝
        self.assertEqual(ai_ledger.budget_remaining(), 0)

    def test_metered_provider_refuses_when_budget_zero(self):
        ai_ledger._BUDGET["cap"] = 0
        ai_ledger._BUDGET["used"] = 0
        inner_calls = []

        class _P:
            def submit_task(self, t):
                inner_calls.append(1)
                return {"status": "ok", "result": {}}

        prov = ai_ledger.wrap_provider(_P(), component="social_ai",
                                       ledger_path=self.tmp / "ai2.jsonl")
        with self.assertRaises(ai_ledger.BudgetExceeded):
            prov.submit_task({"task_type": "x"})
        self.assertEqual(inner_calls, [], "预算耗尽时不得发起请求")
        ai_ledger._BUDGET["cap"] = 80


if __name__ == "__main__":
    unittest.main(verbosity=2)
