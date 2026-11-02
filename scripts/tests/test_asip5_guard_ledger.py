#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1 — 暂停门禁 / 统一账本 / 熔断 / 体积保护 验收测试（离线、零付费）。"""
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

from scripts.ops import paid_gate, ai_ledger  # noqa: E402
from scripts.ops import schedule_orchestrator as so  # noqa: E402


class _FakeProvider:
    """假 provider：固定返回 usage（含缓存命中），用于验证记账，不发网络请求。"""

    model = "deepseek-flash"

    def __init__(self, calls=1, fail=False, cache_hit=None):
        self.n = 0
        self.calls = calls
        self.fail = fail
        self.cache_hit = cache_hit

    def submit_task(self, task):
        self.n += 1
        if self.fail:
            raise RuntimeError("boom")
        return {"task_id": "t", "status": "succeeded", "result": {
            "requested_model": "deepseek-flash", "returned_model": "deepseek-flash",
            "input_tokens": 2348, "output_tokens": 479, "total_tokens": 2827,
            "cache_hit_tokens": self.cache_hit, "cache_miss_tokens": None,
            "http_status": 200, "attempt_count": self.calls, "latency_ms": 900,
            "provider_status": "ok", "billing_mode": "paid", "estimated_cost": None}}


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="asip5_g_")
        self._env = {k: os.environ.get(k) for k in (
            paid_gate.PAUSE_ENV, "ASIP_STATE_FILE_SOFT_LIMIT_MB",
            "ASIP_PRICE_INPUT_PER_MTOK", "ASIP_PRICE_OUTPUT_PER_MTOK",
            "ASIP_GITHUB_RUN_ID")}
        for k in (paid_gate.PAUSE_ENV, "ASIP_PRICE_INPUT_PER_MTOK", "ASIP_PRICE_OUTPUT_PER_MTOK"):
            os.environ.pop(k, None)
        self._breaker = paid_gate.BREAKER_PATH
        paid_gate.BREAKER_PATH = Path(self.tmp) / "breaker.json"
        self.ledger = Path(self.tmp) / "ai_usage.jsonl"
        self.summary = Path(self.tmp) / "ai_usage_summary.json"
        self._lpath, self._spath = ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH
        ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH = self.ledger, self.summary

    def tearDown(self):
        paid_gate.BREAKER_PATH = self._breaker
        ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH = self._lpath, self._spath
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestPauseGate(_Base):
    def test_env_pause_blocks_everything(self):
        os.environ[paid_gate.PAUSE_ENV] = "1"
        is_paused, why = paid_gate.paused(root=self.tmp)
        self.assertTrue(is_paused)
        self.assertIn(paid_gate.PAUSE_ENV, why)

    def test_execute_returns_early_without_subprocess(self):
        """三个入口（schedule / repository_dispatch / workflow_dispatch）都走同一 execute()。"""
        os.environ[paid_gate.PAUSE_ENV] = "true"
        calls = []
        orig = so._run_script
        so._run_script = lambda *a, **k: calls.append(a) or True
        try:
            for trigger in ("scheduled_orchestrator", "external_scheduler", "manual_canary"):
                res = so.execute({"due": [{"task": "collection", "reason": "x"},
                                          {"task": "social_ai", "reason": "x"}]},
                                 {"processed_hashes": {}}, trigger_meta={"trigger_source": trigger})
                self.assertEqual(res["executed"], [])
                self.assertIn("pause_reason", res)
                self.assertFalse(res["deploy_required"])
        finally:
            so._run_script = orig
        self.assertEqual(calls, [], "暂停时不得启动任何子任务（采集/本地化/评估/首页简报）")

    def test_size_guard_pauses_on_oversize(self):
        d = Path(self.tmp) / "data" / "canonical"
        d.mkdir(parents=True)
        (d / "quarantine.json").write_bytes(b"x" * (96 * 1024 * 1024))
        rep = paid_gate.state_size_report(root=self.tmp)
        self.assertFalse(rep["safe_to_persist"])
        is_paused, why = paid_gate.paused(root=self.tmp)
        self.assertTrue(is_paused)
        self.assertIn("state_oversize", why)

    def test_breaker_trips_after_two_strikes_and_clears(self):
        for _ in range(2):
            doc = paid_gate.record_strike("state_push_failed")
        self.assertTrue(doc["tripped"])
        is_paused, why = paid_gate.paused(root=self.tmp)
        self.assertTrue(is_paused)
        self.assertIn("breaker", why)
        paid_gate.clear_breaker()
        is_paused2, _ = paid_gate.paused(root=self.tmp)
        self.assertFalse(is_paused2)

    def test_provider_gate_blocks_before_network(self):
        os.environ[paid_gate.PAUSE_ENV] = "1"
        inner = _FakeProvider()
        prov = ai_ledger.wrap_provider(inner, component="social_ai")
        with self.assertRaises(paid_gate.PaidTasksPaused):
            prov.submit_task({"task_type": "stage4_event_enrichment"})
        self.assertEqual(inner.n, 0, "门禁必须在发出任何请求之前生效")
        self.assertEqual(ai_ledger.read_ledger(path=self.ledger), [], "被拦截的调用不应计入账本")


class TestUnifiedLedger(_Base):
    def test_records_all_components_and_tokens(self):
        os.environ.pop(paid_gate.PAUSE_ENV, None)
        for comp in ("social_ai", "disease_ai", "news_localization",
                     "daily_assessment", "homepage_brief", "daily_report", "weekly_report"):
            prov = ai_ledger.wrap_provider(_FakeProvider(cache_hit=1200),
                                           component=comp, run_id="R1",
                                           ledger_path=self.ledger)
            prov.submit_task({"task_type": "x"})
        s = ai_ledger.write_summary(run_id="R1", path=self.summary)
        self.assertEqual(s["totals"]["calls"], 7)
        self.assertEqual(set(s["by_component"].keys()), {
            "social_ai", "disease_ai", "news_localization", "daily_assessment",
            "homepage_brief", "daily_report", "weekly_report"})
        self.assertEqual(s["totals"]["input_tokens"], 7 * 2348)
        self.assertEqual(s["totals"]["output_tokens"], 7 * 479)
        self.assertEqual(s["totals"]["cache_hit_tokens"], 7 * 1200)
        # 未配置单价 → 估算费用必须为 null（不臆造价格）
        self.assertIsNone(s["pricing"]["input_per_mtok"])
        self.assertFalse(s["totals"]["estimated_cost_available"])
        for rec in ai_ledger.read_ledger(path=self.ledger):
            self.assertIsNone(rec["confirmed_cost"])
            self.assertEqual(rec["billing_mode"], "paid")

    def test_cache_tokens_missing_is_null_not_zero(self):
        prov = ai_ledger.wrap_provider(_FakeProvider(cache_hit=None), component="social_ai",
                                       run_id="R2", ledger_path=self.ledger)
        prov.submit_task({"task_type": "x"})
        rec = ai_ledger.read_ledger(path=self.ledger)[0]
        self.assertIsNone(rec["cache_hit_tokens"])
        self.assertFalse(rec["cache_tokens_available"])

    def test_failure_and_retry_recorded(self):
        prov = ai_ledger.wrap_provider(_FakeProvider(calls=3), component="daily_report",
                                       run_id="R3", ledger_path=self.ledger)
        prov.submit_task({"task_type": "x"})
        rec = ai_ledger.read_ledger(path=self.ledger)[0]
        self.assertEqual(rec["attempt_count"], 3)
        self.assertEqual(rec["retries"], 2)
        # 失败也记账
        prov2 = ai_ledger.wrap_provider(_FakeProvider(fail=True), component="daily_report",
                                        run_id="R3", ledger_path=self.ledger)
        with self.assertRaises(RuntimeError):
            prov2.submit_task({"task_type": "x"})
        recs = ai_ledger.read_ledger(path=self.ledger)
        self.assertEqual(recs[-1]["status"], "error")

    def test_estimated_cost_when_priced(self):
        os.environ["ASIP_PRICE_INPUT_PER_MTOK"] = "1.0"
        os.environ["ASIP_PRICE_OUTPUT_PER_MTOK"] = "2.0"
        prov = ai_ledger.wrap_provider(_FakeProvider(), component="social_ai",
                                       run_id="R4", ledger_path=self.ledger)
        prov.submit_task({"task_type": "x"})
        rec = ai_ledger.read_ledger(path=self.ledger)[0]
        self.assertAlmostEqual(rec["estimated_cost"],
                               2348 / 1e6 * 1.0 + 479 / 1e6 * 2.0, places=6)

    def test_coverage_vs_legacy_ledger(self):
        prov = ai_ledger.wrap_provider(_FakeProvider(), component="social_ai",
                                       run_id="R5", ledger_path=self.ledger)
        prov.submit_task({"task_type": "x"})
        recs = ai_ledger.read_ledger(path=self.ledger)
        cov = ai_ledger.coverage({"social_enrichment": {"calls": 1},
                                  "daily_analysis": {"calls": 0}}, recs)
        self.assertEqual(cov["legacy_calls"], 1)
        self.assertEqual(cov["ledger_calls"], 1)
        self.assertEqual(cov["coverage_pct"], 100.0)


class TestThresholds(_Base):
    def test_alerts_fire(self):
        a = paid_gate.check_thresholds(
            state={"last_successful_collection": "2026-10-27T04:55:16Z",
                   "last_successful_deploy": "2026-10-27T07:44:33Z"},
            ai_last_run_calls=999, ai_today_calls=9999, root=self.tmp)
        kinds = {x["kind"] for x in a}
        self.assertIn("state_stale", kinds)
        self.assertIn("deploy_stall", kinds)
        self.assertIn("single_run_ai_spike", kinds)
        self.assertIn("daily_ai_spike", kinds)

    def test_alert_written_locally(self):
        rec = paid_gate.emit_alert("state_stale", "test", root=self.tmp)
        p = Path(self.tmp) / "data" / "runtime" / "ops" / "alerts.jsonl"
        self.assertTrue(p.exists())
        self.assertEqual(json.loads(p.read_text(encoding="utf-8").strip())["kind"], "state_stale")
        self.assertEqual(rec["kind"], "state_stale")


if __name__ == "__main__":
    unittest.main(verbosity=2)
