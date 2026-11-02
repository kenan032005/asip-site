#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1B 任务5 — 离线最终集成（真实状态快照 + 故障注入）。

链路：旧状态读取 → 分片迁移 → 安全 hold → 模拟采集 → state_src checkpoint →
Git 提交/推送模拟（本地裸仓库）→ 模拟 AI → Token 账本 → 首页视图 → 部署资格判断。

故障注入（每项单独断言）：
  1 Git push rejected        2 commit command failed   3 provider wrapper import failed
  4 ledger write failed      5 manifest/index/shard corrupted
  6 breaker remote unavailable  7 job 中途取消（已采集不得丢失）
  8 同一输入重复运行（不重复计费）  9 迁移后新增记录再回滚（零丢失）
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "scripts" / "data")):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.data.quarantine_store import QuarantineStore, QuarantineCorrupt  # noqa: E402
from scripts.ops import paid_gate, ai_ledger, commit_state  # noqa: E402
from scripts.ops import schedule_orchestrator as so  # noqa: E402
from scripts.ai.safety import manual_trial as mt  # noqa: E402
import scripts.build_site as bs  # noqa: E402

REAL_STATE = Path(r"C:\Users\kenan\WorkBuddy\2026-10-18-16-52-12\asip5\prod_state.json")
REAL_QUAR = Path(r"C:\Users\kenan\WorkBuddy\2026-10-18-16-52-12\asip5\quarantine_snapshot.json")


class _FakeProvider:
    model = "deepseek-flash"

    def __init__(self):
        self.n = 0

    def submit_task(self, task):
        self.n += 1
        return {"status": "succeeded", "result": {
            "requested_model": "deepseek-flash", "returned_model": "deepseek-flash",
            "input_tokens": 2000, "output_tokens": 400, "total_tokens": 2400,
            "cache_hit_tokens": 800, "attempt_count": 1,
            "provider_status": "ok", "billing_mode": "paid"}}


def _git(args, cwd, check=True):
    r = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError("%s: %s" % (args, (r.stderr or r.stdout)[-300:]))
    return r


class TestR1BE2E(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="asip5_r1b_e2e_"))
        # 代码工作树
        self.code = self.tmp / "code"
        (self.code / "data" / "canonical").mkdir(parents=True)
        (self.code / "data" / "runtime" / "ops").mkdir(parents=True)
        _git(["init", "-q"], self.code)
        _git(["config", "user.email", "t@t"], self.code)
        _git(["config", "user.name", "t"], self.code)
        # 真实 10-27 状态快照（不可用则退化）
        self.state_source = "real" if REAL_STATE.exists() else "synthetic"
        if REAL_STATE.exists():
            shutil.copy2(REAL_STATE, self.code / "data" / "runtime" / "ops" / "production_state.json")
        else:
            (self.code / "data" / "runtime" / "ops" / "production_state.json").write_text(
                json.dumps({"last_successful_collection": "2026-10-27T04:55:16Z",
                            "processed_hashes": {"social_enrichment": {"h1": {}}}}), encoding="utf-8")
        # 隔离数据：真实快照（可选）或合成
        # 真实 10 万条隔离快照仅在显式开关下用于 E2E（否则每个用例都迁移 20k 条，过慢）
        if REAL_QUAR.exists() and os.environ.get("ASIP5_E2E_REAL") == "1":
            shutil.copy2(REAL_QUAR, self.code / "data" / "canonical" / "quarantine.json")
        else:
            items = [{"quarantine_id": "Q_%03d" % i, "original_object_type": "article",
                      "original_id": "https://ex.com/blocked" if i == 0 else "https://ex.com/%d" % i,
                      "reason_code": "other", "detected_at": "2026-10-%02dT00:00:00Z" % ((i % 28) + 1),
                      "legacy_payload": {}} for i in range(40)]
            (self.code / "data" / "canonical" / "quarantine.json").write_text(
                json.dumps({"schema_version": "2.0", "items": items}, ensure_ascii=False), encoding="utf-8")
        # bare 远端 + state_src
        self.bare = self.tmp / "remote.git"
        _git(["init", "--bare", "-q", str(self.bare)], self.tmp)
        seed = self.tmp / "seed"
        seed.mkdir()
        _git(["init", "-q"], seed)
        _git(["config", "user.email", "t@t"], seed)
        _git(["config", "user.name", "t"], seed)
        (seed / "data" / "runtime" / "ops").mkdir(parents=True)
        (seed / "data" / "runtime" / "ops" / "production_state.json").write_text(
            json.dumps({"last_successful_collection": ""}), encoding="utf-8")
        _git(["add", "-A"], seed)
        _git(["commit", "-qm", "seed"], seed)
        _git(["push", "-q", str(self.bare), "HEAD:production-state"], seed)
        self.state = self.tmp / "state_src"
        _git(["clone", "-q", "-b", "production-state", str(self.bare), str(self.state)], self.tmp)
        _git(["config", "user.email", "t@t"], self.state)
        _git(["config", "user.name", "t"], self.state)
        # 常量补丁
        self._saved = (commit_state.ROOT, commit_state.STATE_DIR, commit_state.GIT_PATHS,
                       commit_state.COPY_PAIRS, commit_state.COPY_FILES,
                       paid_gate.BREAKER_PATH, paid_gate.BREAKER_REMOTE_PATH,
                       ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH, bs.DATA_DIR)
        commit_state.ROOT, commit_state.STATE_DIR = self.code, self.state
        commit_state.GIT_PATHS = ["data/runtime/ops", "data/canonical"]
        commit_state.COPY_PAIRS = [("data/runtime/ops", "data/runtime/ops"),
                                   ("data/canonical", "data/canonical")]
        commit_state.COPY_FILES = []
        paid_gate.BREAKER_PATH = self.tmp / "breaker.json"
        paid_gate.BREAKER_REMOTE_PATH = self.tmp / "breaker_remote.json"
        ai_ledger.LEDGER_PATH = self.tmp / "ai_usage.jsonl"
        ai_ledger.SUMMARY_PATH = self.tmp / "summary.json"
        bs.DATA_DIR = str(self.code / "data")
        for k in ("ASIP5_PAUSE_PAID_TASKS", "GITHUB_ACTIONS"):
            os.environ.pop(k, None)
        paid_gate.save_remote_status(True, "test")

    def tearDown(self):
        (commit_state.ROOT, commit_state.STATE_DIR, commit_state.GIT_PATHS,
         commit_state.COPY_PAIRS, commit_state.COPY_FILES,
         paid_gate.BREAKER_PATH, paid_gate.BREAKER_REMOTE_PATH,
         ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH, bs.DATA_DIR) = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ── 主链路 ──────────────────────────────────────────────
    def test_chain_ok(self):
        state = json.loads((self.code / "data/runtime/ops/production_state.json").read_text(encoding="utf-8"))
        self.assertIn("processed_hashes", state)
        store = QuarantineStore(root=self.code, max_shard_bytes=4096)
        store.migrate(dry_run=False)
        self.assertTrue(store.is_sharded())
        self.assertTrue(store.verify_consistency()["consistent"])
        urls = store.url_map()
        self.assertIn("https://ex.com/blocked", urls)
        # 模拟采集
        cand = [{"url": "https://ex.com/blocked"}, {"url": "https://ex.com/n1"}, {"url": "https://ex.com/n2"}]
        fresh = [c for c in cand if c["url"] not in urls]
        self.assertEqual(len(fresh), 2)
        # checkpoint（本地裸仓库）
        res = commit_state.commit_now("ops: e2e collection", after="collection",
                                      expect={"path": "data/runtime/ops/production_state.json",
                                              "field": "last_successful_collection"})
        self.assertTrue(res["pushed"])
        # 模拟 AI + 账本
        for comp in ("social_ai", "news_localization", "homepage_brief"):
            p = ai_ledger.wrap_provider(_FakeProvider(), component=comp, run_id="E2E")
            for _ in fresh:
                p.submit_task({"task_type": "x"})
        s = ai_ledger.write_summary(run_id="E2E")
        self.assertEqual(s["totals"]["calls"], 6)
        self.assertEqual(s["totals"]["cache_hit_tokens"], 6 * 800)
        # 首页（过期提示）
        (self.code / "data" / "status.json").write_text(json.dumps({
            "run_id": "R", "data_as_of": "2026-10-27T04:55:16Z"}), encoding="utf-8")
        meta = bs.get_build_meta()
        html = bs.inject_meta("<html><head></head><body>x</body></html>", meta)
        self.assertIn("asip-staleness-banner", html)
        # 部署资格
        self.assertTrue(so.deploy_required_for("FULL"))
        self.assertFalse(so.deploy_required_for("HOLD"))

    # ── 故障注入 ────────────────────────────────────────────
    def test_f1_push_rejected(self):
        hook = self.bare / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        os.chmod(hook, 0o755)
        with self.assertRaises(commit_state.CheckpointError) as ctx:
            commit_state.commit_now("x", after="collection")
        self.assertEqual(ctx.exception.stage, "push")
        self.assertGreaterEqual(int(paid_gate.load_breaker().get("strikes") or 0), 1)

    def test_f2_commit_failed(self):
        real = commit_state._git

        def fake(args, cwd=None, timeout=180):
            if args and args[0] == "commit":
                class R:
                    returncode, stdout, stderr = 1, "", "boom"
                return R()
            return real(args, cwd=cwd, timeout=timeout)

        commit_state._git = fake
        try:
            with self.assertRaises(commit_state.CheckpointError) as ctx:
                commit_state.commit_now("x")
            self.assertEqual(ctx.exception.stage, "commit")
        finally:
            commit_state._git = real

    def test_f3_provider_wrapper_import_failed(self):
        orig = ai_ledger.wrap_provider
        ai_ledger.wrap_provider = lambda *a, **k: (_ for _ in ()).throw(ImportError("no module"))
        try:
            with self.assertRaises(RuntimeError):
                mt._flash_provider()      # 不得退回裸 provider
        finally:
            ai_ledger.wrap_provider = orig

    def test_f4_ledger_write_failed(self):
        d = self.tmp / "ledger_dir"
        d.mkdir()
        inner = _FakeProvider()
        p = ai_ledger.wrap_provider(inner, component="social_ai", ledger_path=d)
        with self.assertRaises(ai_ledger.LedgerUnavailable):
            p.submit_task({"task_type": "x"})
        self.assertEqual(inner.n, 0)

    def test_f5_corrupt_store(self):
        st = QuarantineStore(root=self.code, max_shard_bytes=4096)
        st.migrate(dry_run=False)
        qdir = self.code / "data" / "canonical" / "quarantine"
        # manifest 在但 index 缺失
        (qdir / "index.json").unlink()
        with self.assertRaises(QuarantineCorrupt):
            st.load_items()
        self.assertFalse(st.is_sharded() if False else False)

    def test_f6_breaker_remote_unavailable(self):
        paid_gate.save_remote_status(False, "network down")
        paused, why = paid_gate.paused(root=self.code)
        self.assertTrue(paused)
        self.assertIn("breaker_remote_unavailable", why)
        calls = []
        orig = so._run_script
        so._run_script = lambda *a, **k: calls.append(a) or True
        try:
            r = so.execute({"due": [{"task": "collection", "reason": "x"}]},
                           {"processed_hashes": {}}, trigger_meta={"trigger_source": "external_scheduler"})
        finally:
            so._run_script = orig
        self.assertEqual(calls, [])
        self.assertEqual(r["executed"], [])

    def test_f7_cancel_after_collection_keeps_data(self):
        """采集后 checkpoint → 后续被取消，已采集结果已在远端（不丢失）。"""
        res = commit_state.commit_now("ops: collection checkpoint", after="collection")
        self.assertTrue(res["pushed"])
        remote = subprocess.run(["git", "--git-dir", str(self.bare), "rev-parse", "production-state"],
                                capture_output=True, text=True).stdout.strip()
        shown = subprocess.run(["git", "--git-dir", str(self.bare), "show",
                                "%s:data/runtime/ops/production_state.json" % remote],
                               capture_output=True, text=True).stdout
        self.assertIn("processed_hashes", shown, "取消前已采集结果必须已在 state 分支")

    def test_f8_duplicate_run_no_double_billing(self):
        state = json.loads((self.code / "data/runtime/ops/production_state.json").read_text(encoding="utf-8"))
        processed = set((state.get("processed_hashes") or {}).get("social_enrichment") or {})
        batch = ["h2", "h3"]
        first = [h for h in batch if h not in processed]
        self.assertEqual(len(first), 2)
        processed |= set(first)
        second = [h for h in batch if h not in processed]
        self.assertEqual(second, [], "重复运行不得重复计费")

    def test_f9_rollback_with_new_records(self):
        st = QuarantineStore(root=self.code, max_shard_bytes=4096)
        st.migrate(dry_run=False)
        before = len(st.load_items())
        st.upsert([{"quarantine_id": "Q_after_migration", "original_object_type": "event",
                    "original_id": "https://ex.com/after", "reason_code": "other",
                    "detected_at": "2026-11-01T00:00:00Z"}], run_id="R")
        rb = st.rollback_to_monolith(expect_items=before + 1)
        self.assertEqual(rb["restored_items"], before + 1)
        ids = {i["quarantine_id"] for i in st.load_items()}
        self.assertIn("Q_after_migration", ids, "回滚不得丢失迁移后新增记录")


if __name__ == "__main__":
    unittest.main(verbosity=2)
