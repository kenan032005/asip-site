#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1B 任务2/4 — 付费门禁三角色 fail-closed + 熔断自举/可达性/审计。

验收：
  CHECKPOINT_FAILURE_AI_CALLS=0 / PROVIDER_GATE_BYPASS=0
  LEDGER_FAILURE_POLICY=FAIL_CLOSED / PAUSE_GATE_3_TRIGGERS=PASS
  BREAKER_BOOTSTRAP=PASS / BREAKER_REMOTE_UNAVAILABLE=FAIL_CLOSED
  BREAKER_CROSS_RUN_RECOVERY=PASS / BREAKER_CLEAR_AUDIT=PASS
"""
import base64
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

from scripts.ops import paid_gate, ai_ledger, breakerctl  # noqa: E402
from scripts.ops import schedule_orchestrator as so  # noqa: E402
from scripts.ai.safety import manual_trial as mt  # noqa: E402


class _FakeProvider:
    model = "deepseek-flash"

    def __init__(self):
        self.n = 0

    def submit_task(self, task):
        self.n += 1
        return {"status": "succeeded", "result": {
            "requested_model": "deepseek-flash", "returned_model": "deepseek-flash",
            "input_tokens": 10, "output_tokens": 5, "total_tokens": 15,
            "attempt_count": 1, "provider_status": "ok", "billing_mode": "paid"}}


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="asip5_r1b_"))
        self._env = {k: os.environ.get(k) for k in
                     (paid_gate.PAUSE_ENV, "GITHUB_ACTIONS", "ASIP_REQUIRE_BREAKER_REMOTE")}
        for k in self._env:
            os.environ.pop(k, None)
        os.environ.pop("GITHUB_ACTIONS", None)
        self._saved = (paid_gate.BREAKER_PATH, paid_gate.BREAKER_REMOTE_PATH,
                       ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH)
        paid_gate.BREAKER_PATH = self.tmp / "breaker.json"
        paid_gate.BREAKER_REMOTE_PATH = self.tmp / "breaker_remote.json"
        ai_ledger.LEDGER_PATH = self.tmp / "ai_usage.jsonl"
        ai_ledger.SUMMARY_PATH = self.tmp / "summary.json"
        paid_gate.save_remote_status(True, "test")

    def tearDown(self):
        (paid_gate.BREAKER_PATH, paid_gate.BREAKER_REMOTE_PATH,
         ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH) = self._saved
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestCheckpointBlocksPaidTasks(_Base):
    def _run(self, trigger, commit_impl, pause=False):
        if pause:
            os.environ[paid_gate.PAUSE_ENV] = "1"
        calls = []
        prov = _FakeProvider()
        orig_run = so._run_script
        orig_commit = __import__("scripts.ops.commit_state", fromlist=["commit_now"]).commit_now
        so._run_script = lambda *a, **k: calls.append(a) or True
        import scripts.ops.commit_state as cs
        cs.commit_now = commit_impl
        try:
            plan = {"due": [{"task": "collection", "reason": "gap"},
                            {"task": "social_ai", "reason": "eligible"},
                            {"task": "disease_ai", "reason": "eligible"}]}
            err = None
            try:
                so.execute(plan, {"processed_hashes": {}},
                           trigger_meta={"trigger_source": trigger})
            except Exception as e:  # noqa: BLE001
                err = e
            return {"calls": calls, "err": err, "provider_calls": prov.n}
        finally:
            so._run_script = orig_run
            cs.commit_now = orig_commit

    def test_pause_zero_calls_three_triggers(self):
        for trig in ("scheduled_orchestrator", "external_scheduler", "manual_canary"):
            r = self._run(trig, lambda *a, **k: {"ok": True}, pause=True)
            self.assertEqual(r["calls"], [], trig)
            self.assertEqual(r["provider_calls"], 0, trig)
            self.assertIsNone(r["err"], trig)

    def test_checkpoint_false_aborts_before_ai(self):
        import scripts.ops.commit_state as cs
        for trig in ("scheduled_orchestrator", "external_scheduler", "manual_canary"):
            r = self._run(trig, lambda *a, **k: {"ok": False, "error": "push rejected"})
            self.assertIsInstance(r["err"], so.CheckpointFailed, trig)
            # 只允许 collection 那一次子进程，后续 AI/本地化/评估/首页一律不得启动
            self.assertEqual(len(r["calls"]), 1, trig)
            self.assertIn("collection_run.py", " ".join(r["calls"][0][0]), trig)

    def test_checkpoint_exception_aborts_before_ai(self):
        def boom(*a, **k):
            raise RuntimeError("git exploded")

        for trig in ("scheduled_orchestrator", "external_scheduler", "manual_canary"):
            r = self._run(trig, boom)
            self.assertIsInstance(r["err"], so.CheckpointFailed, trig)
            self.assertEqual(len(r["calls"]), 1, trig)
            self.assertEqual(r["provider_calls"], 0, trig)


class TestProviderGate(_Base):
    def test_wrapper_failure_raises_not_bare_provider(self):
        orig = ai_ledger.wrap_provider
        ai_ledger.wrap_provider = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("wrap boom"))
        try:
            with self.assertRaises(RuntimeError) as ctx:
                mt._flash_provider()
            self.assertIn("provider_gate_unavailable", str(ctx.exception))
        finally:
            ai_ledger.wrap_provider = orig

    def test_partial_tasks_paused_provider_refuses(self):
        os.environ[paid_gate.PAUSE_ENV] = "1"
        with self.assertRaises(paid_gate.PaidTasksPaused):
            mt._flash_provider()

    def test_ledger_unwritable_blocks_call(self):
        # 把账本路径指向目录 → 不可写
        d = self.tmp / "ledger_dir"
        d.mkdir()
        inner = _FakeProvider()
        prov = ai_ledger.wrap_provider(inner, component="social_ai", ledger_path=d)
        with self.assertRaises(ai_ledger.LedgerUnavailable):
            prov.submit_task({"task_type": "x"})
        self.assertEqual(inner.n, 0, "账本不可写时不得发起付费调用")

    def test_remote_breaker_unverified_pauses(self):
        os.environ["GITHUB_ACTIONS"] = "true"
        paid_gate.BREAKER_REMOTE_PATH = self.tmp / "missing.json"
        is_paused, why = paid_gate.paused(root=self.tmp)
        self.assertTrue(is_paused)
        self.assertIn("breaker_remote_unverified", why)


class _FakeGitHub:
    """本地模拟 GitHub API（refs + contents），不接触真实远端。"""

    def __init__(self, default="main"):
        self.refs = {default: "a" * 40}
        self.contents = {}
        self.default = default
        self.calls = []
        self.fail = None

    def __call__(self, url, token, method="GET", body=None, timeout=20):
        self.calls.append((method, url))
        if self.fail:
            raise breakerctl.RemoteError(self.fail)
        if "/repos/" in url and "/git/ref/heads/" in url and method == "GET":
            br = url.rsplit("/", 1)[1]
            return ({"object": {"sha": self.refs[br]}}, 200) if br in self.refs else (None, 404)
        if url.endswith("/git/refs") and method == "POST":
            br = body["ref"].split("/")[-1]
            self.refs[br] = body["sha"]
            return ({"ref": body["ref"]}, 201)
        if "/contents/" in url and method == "GET":
            br = url.split("ref=")[-1]
            key = (br, "breaker.json")
            if key in self.contents:
                return ({"content": base64.b64encode(json.dumps(self.contents[key]).encode()).decode(),
                         "sha": "s1"}, 200)
            return (None, 404)
        if "/contents/" in url and method == "PUT":
            self.contents[(body["branch"], "breaker.json")] = json.loads(
                base64.b64decode(body["content"]).decode())
            return ({"content": {}}, 200)
        if url.endswith("/repos/o/r"):
            return ({"default_branch": self.default}, 200)
        raise breakerctl.RemoteError("unhandled %s %s" % (method, url))


class TestBreakerBootstrap(_Base):
    def setUp(self):
        super().setUp()
        self.gh = _FakeGitHub()
        self._orig_api = breakerctl._api
        breakerctl._api = self.gh
        self._token = os.environ.get("GITHUB_TOKEN")
        os.environ["GITHUB_TOKEN"] = "test-token"

    def tearDown(self):
        breakerctl._api = self._orig_api
        if self._token is None:
            os.environ.pop("GITHUB_TOKEN", None)
        else:
            os.environ["GITHUB_TOKEN"] = self._token
        super().tearDown()

    def test_bootstrap_creates_branch_when_absent(self):
        self.assertNotIn("ops-health", self.gh.refs)
        boot = breakerctl.ensure_branch("o/r", "ops-health", "test-token")
        self.assertTrue(boot["created"])
        self.assertIn("ops-health", self.gh.refs)
        # 二次调用不重复创建
        boot2 = breakerctl.ensure_branch("o/r", "ops-health", "test-token")
        self.assertFalse(boot2["created"])

    def test_publish_bootstraps_then_writes(self):
        doc = {"tripped": True, "reason": "state_push_failed", "strikes": 2}
        r = breakerctl.publish("o/r", "ops-health", "test-token", doc=doc)
        self.assertTrue(r["ok"])
        self.assertTrue(r["bootstrapped"])
        self.assertEqual(self.gh.contents[("ops-health", "breaker.json")]["reason"],
                         "state_push_failed")

    def test_fetch_unreachable_fail_closed(self):
        self.gh.fail = "network down"
        r = breakerctl.fetch("o/r", "ops-health", "test-token")
        self.assertFalse(r["ok"])
        self.assertFalse(paid_gate.breaker_remote()["reachable"])
        is_paused, why = paid_gate.paused(root=self.tmp)
        self.assertTrue(is_paused)
        self.assertIn("breaker_remote_unavailable", why)

    def test_cross_run_recovery(self):
        breakerctl.publish("o/r", "ops-health", "test-token",
                           doc={"tripped": True, "reason": "x", "strikes": 3})
        paid_gate.clear_breaker()          # 模拟"新 runner 本地无状态"
        self.assertFalse(paid_gate.load_breaker()["tripped"])
        r = breakerctl.fetch("o/r", "ops-health", "test-token")
        self.assertTrue(r["ok"])
        self.assertTrue(paid_gate.load_breaker()["tripped"], "远端熔断必须被新 runner 读回")

    def test_clear_requires_reason_and_is_audited(self):
        paid_gate.record_strike("a")
        paid_gate.record_strike("b")
        self.assertTrue(paid_gate.load_breaker()["tripped"])
        rc = breakerctl.main(["clear"])            # 缺 --reason
        self.assertEqual(rc, 2)
        doc = paid_gate.clear_breaker(by="kenan", reason="storage migrated")
        self.assertFalse(doc["tripped"])
        self.assertEqual(doc["cleared_by"], "kenan")
        audit = (self.tmp / "breaker_audit.jsonl").read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(json.loads(audit[-1])["reason"], "storage migrated")


if __name__ == "__main__":
    unittest.main(verbosity=2)
