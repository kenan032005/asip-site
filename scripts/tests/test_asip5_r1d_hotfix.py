#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 R1D-HOTFIX — collection_only 严格隔离 / shadow 只读 / 迁移 CLI 端到端。

验收：COLLECTION_ONLY_STRICT / SHADOW_READ_ONLY / MIGRATION_CLI_E2E / AUTOMATIC_TRIGGER_LOCKED
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

from scripts.data.quarantine_store import QuarantineStore  # noqa: E402
from scripts.ops import ai_ledger, paid_gate  # noqa: E402
from scripts.ops import production_state as ps  # noqa: E402
from scripts.ops import schedule_orchestrator as so  # noqa: E402


def _git(args, cwd, check=True):
    r = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError("%s: %s" % (args, (r.stderr or r.stdout)[-300:]))
    return r


def _mk_repo(tmp, legacy_items=40, pad=0):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    bare = tmp / "remote.git"
    _git(["init", "--bare", "-q", str(bare)], tmp)
    seed = tmp / "seed"
    (seed / "data" / "runtime" / "ops").mkdir(parents=True)
    (seed / "data" / "canonical").mkdir(parents=True)
    (seed / "data" / "runtime" / "ops" / "production_state.json").write_text(
        json.dumps({"last_successful_collection": "2026-11-02T09:00:00Z",
                    "processed_hashes": {"social_enrichment": {"h": {}}}}), encoding="utf-8")
    (seed / "data" / "canonical" / "quarantine.json").write_text(
        json.dumps({"schema_version": "2.0", "items": []}), encoding="utf-8")
    _git(["init", "-q"], seed)
    _git(["config", "user.email", "t@t"], seed)
    _git(["config", "user.name", "t"], seed)
    _git(["add", "-A"], seed)
    _git(["commit", "-qm", "seed"], seed)
    _git(["push", "-q", str(bare), "HEAD:production-state"], seed)

    code = tmp / "code"
    (code / "data" / "runtime" / "ops").mkdir(parents=True)
    (code / "data" / "canonical").mkdir(parents=True)
    items = [{"quarantine_id": "Q_%03d" % i, "original_object_type": "article",
              "original_id": "https://ex.com/%d" % i, "reason_code": "other",
              "detected_at": "2026-10-%02dT00:00:00Z" % ((i % 28) + 1),
              "legacy_payload": {"pad": "x" * pad}} for i in range(legacy_items)]
    (code / "data" / "canonical" / "quarantine.json").write_text(
        json.dumps({"schema_version": "2.0", "items": items}, ensure_ascii=False), encoding="utf-8")
    (code / "data" / "runtime" / "ops" / "production_state.json").write_text(
        json.dumps({"last_successful_collection": "2026-11-02T09:00:00Z",
                    "processed_hashes": {"social_enrichment": {"h": {}}}}), encoding="utf-8")
    _git(["init", "-q"], code)
    _git(["config", "user.email", "t@t"], code)
    _git(["config", "user.name", "t"], code)

    state = tmp / "state_src"
    _git(["clone", "-q", "-b", "production-state", str(bare), str(state)], tmp)
    _git(["config", "user.email", "t@t"], state)
    _git(["config", "user.name", "t"], state)
    shutil.copy2(code / "data" / "canonical" / "quarantine.json",
                 state / "data" / "canonical" / "quarantine.json")
    return bare, code, state


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="asip5_fix_")
        self._env = {k: os.environ.get(k) for k in
                     ("ASIP_RUN_MODE", "GITHUB_EVENT_NAME", "ASIP_ALLOW_AUTOMATIC_RUNS",
                      "ASIP_ALLOW_MANUAL_PRODUCTION", paid_gate.PAUSE_ENV, "GITHUB_ACTIONS",
                      "ASIP_EXPECT_REPO_SUBSTR")}
        for k in ("ASIP_RUN_MODE", "GITHUB_EVENT_NAME", "ASIP_ALLOW_AUTOMATIC_RUNS",
                  "ASIP_ALLOW_MANUAL_PRODUCTION", paid_gate.PAUSE_ENV, "GITHUB_ACTIONS"):
            os.environ.pop(k, None)
        os.environ["ASIP_EXPECT_REPO_SUBSTR"] = ""
        self._saved = (paid_gate.BREAKER_PATH, paid_gate.BREAKER_REMOTE_PATH,
                       ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH,
                       ps.OPS_DIR, ps.STATE_FILE, ps.OPS_STATUS_FILE)
        paid_gate.BREAKER_PATH = Path(self.tmp) / "breaker.json"
        paid_gate.BREAKER_REMOTE_PATH = Path(self.tmp) / "remote.json"
        ai_ledger.LEDGER_PATH = Path(self.tmp) / "ai.jsonl"
        ai_ledger.SUMMARY_PATH = Path(self.tmp) / "ai_summary.json"
        _ops = Path(self.tmp) / "ops"
        _ops.mkdir(parents=True, exist_ok=True)
        (_ops / "production_state.json").write_text(
            json.dumps({"last_successful_collection": "2026-10-27T04:55:16Z",
                        "processed_hashes": {"social_enrichment": {"h1": {}}}}), encoding="utf-8")
        ps.OPS_DIR = _ops
        ps.STATE_FILE = _ops / "production_state.json"
        ps.OPS_STATUS_FILE = _ops / "operations_status.json"
        paid_gate.save_remote_status(True, "test")

    def tearDown(self):
        (paid_gate.BREAKER_PATH, paid_gate.BREAKER_REMOTE_PATH,
         ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH,
         ps.OPS_DIR, ps.STATE_FILE, ps.OPS_STATUS_FILE) = self._saved
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestCollectionOnlyStrict(_Base):
    def test_auto_ai_not_triggered_even_if_new_eligible(self):
        os.environ["ASIP_RUN_MODE"] = "collection_only"
        os.environ["ASIP_COMMIT_AFTER_COLLECTION"] = "0"   # 本用例只验证子进程隔离
        calls = []
        orig_run, orig_elig = so._run_script, so.new_eligible_exists
        so._run_script = lambda *a, **k: calls.append(a[0][0] if isinstance(a[0], (list, tuple))
                                                      else str(a[0])) or True
        so.new_eligible_exists = lambda *a, **k: True        # 强制"有新 eligible"
        try:
            res = so.execute({"due": [{"task": "collection", "reason": "gap"},
                                      {"task": "social_ai", "reason": "eligible"},
                                      {"task": "disease_ai", "reason": "eligible"},
                                      {"task": "daily_report", "reason": "tick"}]},
                             {"processed_hashes": {}},
                             trigger_meta={"trigger_source": "workflow_dispatch"})
        finally:
            so._run_script, so.new_eligible_exists = orig_run, orig_elig
            os.environ.pop("ASIP_COMMIT_AFTER_COLLECTION", None)
        self.assertEqual(res["mode"], "collection_only")
        self.assertFalse(res["deploy_required"], "collection_only 不得部署")
        self.assertEqual(len(calls), 1, "只允许 collection 子进程，实际：%s" % calls)
        self.assertIn("collection_run.py", calls[0])
        self.assertEqual(ai_ledger.read_ledger(), [], "AI_PROVIDER_CALLS 必须为 0")


class TestShadowReadOnly(_Base):
    def test_shadow_does_nothing(self):
        os.environ["ASIP_RUN_MODE"] = "shadow"
        calls = []
        orig = so._run_script
        so._run_script = lambda *a, **k: calls.append(a) or True
        before = ps.STATE_FILE.read_text(encoding="utf-8")
        try:
            res = so.execute({"due": [{"task": "collection", "reason": "gap"}]},
                             {"processed_hashes": {}},
                             trigger_meta={"trigger_source": "workflow_dispatch"})
        finally:
            so._run_script = orig
        self.assertEqual(res["mode"], "shadow")
        self.assertEqual(res["executed"], [])
        self.assertFalse(res["deploy_required"])
        self.assertEqual(calls, [], "shadow 不得启动任何子进程")
        self.assertEqual(ps.STATE_FILE.read_text(encoding="utf-8"), before, "shadow 不得写回")

    def test_invalid_mode_rejected_not_downgraded(self):
        os.environ["ASIP_RUN_MODE"] = "production_like"
        with self.assertRaises(so.InvalidRunMode):
            so.run_mode()
        with self.assertRaises(so.InvalidRunMode):
            so.execute({"due": []}, {}, trigger_meta={"trigger_source": "workflow_dispatch"})

    def test_shadow_blocks_paid_calls(self):
        os.environ["ASIP_RUN_MODE"] = "shadow"
        with self.assertRaises(paid_gate.PaidTasksPaused) as ctx:
            paid_gate.assert_paid_allowed("social_ai")
        self.assertIn("shadow_read_only", str(ctx.exception))


class TestTriggerGates(_Base):
    def _main(self, argv, event):
        os.environ["GITHUB_EVENT_NAME"] = event
        return so.main(argv)

    def test_automatic_triggers_locked(self):
        for ev in ("schedule", "repository_dispatch"):
            os.environ.pop("ASIP_ALLOW_AUTOMATIC_RUNS", None)
            rc = self._main(["--run", "--json"], ev)
            self.assertEqual(rc, 0, ev)
            self.assertTrue(so.automatic_runs_locked(), ev)

    def test_automatic_allowed_only_with_flag(self):
        os.environ["ASIP_ALLOW_AUTOMATIC_RUNS"] = "1"
        os.environ["GITHUB_EVENT_NAME"] = "schedule"
        self.assertFalse(so.automatic_runs_locked())

    def test_manual_collection_only_allowed_without_production_auth(self):
        os.environ["ASIP_RUN_MODE"] = "collection_only"
        os.environ.pop("ASIP_ALLOW_MANUAL_PRODUCTION", None)
        os.environ["GITHUB_EVENT_NAME"] = "workflow_dispatch"
        self.assertFalse(so.automatic_runs_locked())
        # 人工 collection_only 不需要 production 授权
        self.assertFalse(so.manual_production_authorized())

    def test_manual_production_requires_authorization(self):
        os.environ["ASIP_RUN_MODE"] = "production"
        os.environ.pop("ASIP_ALLOW_MANUAL_PRODUCTION", None)
        rc = self._main(["--run", "--json"], "workflow_dispatch")
        self.assertEqual(rc, 3, "人工 production 未授权必须拒绝")
        os.environ["ASIP_ALLOW_MANUAL_PRODUCTION"] = "1"
        self.assertTrue(so.manual_production_authorized())


class TestMigrationCliE2E(_Base):
    def test_runbook_command_end_to_end(self):
        bare, code, state = _mk_repo(Path(self.tmp) / "repo", legacy_items=40, pad=300 * 1024)
        # 迁移 + 退役（state_src 内）
        st = QuarantineStore(root=state, max_shard_bytes=2048)
        st.migrate(dry_run=False, expect_items=40)
        st.retire_monolith(backup_dir=Path(self.tmp) / "bk", expect_items=40)
        self.assertLess(st.legacy.stat().st_size, 4096)
        self.assertGreater((code / "data/canonical/quarantine.json").stat().st_size,
                           10 * 1024 * 1024, "代码树仍带大单体（注入）")

        # 执行与 Runbook 完全相同的命令（子进程 + 环境变量指向临时工作区）
        env = dict(os.environ)
        env.update({"ASIP_CODE_ROOT": str(code), "ASIP_STATE_DIR": str(state),
                    "ASIP_EXPECT_REPO_SUBSTR": "", "PYTHONPATH": str(ROOT)})
        for k in ("ASIP_RUN_MODE", "GITHUB_EVENT_NAME"):
            env.pop(k, None)
        r = subprocess.run([sys.executable, "-m", "scripts.ops.commit_state",
                            "ops: quarantine sharded + retire", "migration",
                            "--state-only", "--migration", "--expect-items", "40"],
                           cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, "CLI 失败：%s\n%s" % (r.stdout[-800:], r.stderr[-800:]))
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertTrue(out["ok"] and out["pushed"])
        self.assertTrue(out["content_verified"], "迁移提交必须完成内容校验")
        self.assertTrue(out["stages"]["verify_remote_tree"]["checked"])
        # state_src 墓碑未被代码树 18MB 单体覆盖
        self.assertLess(st.legacy.stat().st_size, 4096)
        self.assertTrue(json.loads(st.legacy.read_text(encoding="utf-8"))["retired"])
        # 远端：墓碑 + 分片，且无 >100MB 文件
        remote = _git(["--git-dir", str(bare), "rev-parse", "production-state"], self.tmp).stdout.strip()
        ls = _git(["--git-dir", str(bare), "ls-tree", "-r", "-l", remote, "--", "data/canonical"],
                  self.tmp).stdout
        sizes = [int(l.split()[3]) for l in ls.splitlines() if l.strip()]
        self.assertTrue(sizes and max(sizes) < 100 * 1024 * 1024)
        self.assertTrue(any("quarantine/" in l for l in ls.splitlines()), "远端应含分片")
        tomb_line = [l for l in ls.splitlines() if l.endswith("data/canonical/quarantine.json")]
        self.assertTrue(tomb_line)
        self.assertLess(int(tomb_line[0].split()[3]), 4096, "远端单体必须是墓碑")


if __name__ == "__main__":
    unittest.main(verbosity=2)
