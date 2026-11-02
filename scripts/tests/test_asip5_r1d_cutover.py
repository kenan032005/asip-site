#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1D — 四处生产切换风险修复验收（离线、零付费）。

验收：
  R1D_MIGRATION_COMMIT_ISOLATED / R1D_PRE_PUSH_CONTENT_VERIFIED
  R1D_NO_CHANGE_EXPECT_VERIFIED / R1D_COLLECTION_ONLY_ZERO_AI
  R1D_BACKUP_PREFLIGHT / R1D_REAL_SNAPSHOT_E2E（由真实快照用例承担）
"""
import hashlib
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
from scripts.ops import commit_state, paid_gate, ai_ledger  # noqa: E402
from scripts.ops import schedule_orchestrator as so  # noqa: E402
from scripts.ops import production_state as ps  # noqa: E402


def _git(args, cwd, check=True):
    r = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError("%s: %s" % (args, (r.stderr or r.stdout)[-300:]))
    return r


class _Repo:
    """bare 远端 + 代码树（含旧单体）+ state_src（production-state 克隆）。"""

    def __init__(self, tmp, legacy_items=60, code_bytes=None):
        self.tmp = Path(tmp)
        self.bare = self.tmp / "remote.git"
        _git(["init", "--bare", "-q", str(self.bare)], self.tmp)
        seed = self.tmp / "seed"
        (seed / "data" / "canonical").mkdir(parents=True)
        (seed / "data" / "runtime" / "ops").mkdir(parents=True)
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
        _git(["push", "-q", str(self.bare), "HEAD:production-state"], seed)

        self.code = self.tmp / "code"
        (self.code / "data" / "canonical").mkdir(parents=True)
        (self.code / "data" / "runtime" / "ops").mkdir(parents=True)
        _git(["init", "-q"], self.code)
        _git(["config", "user.email", "t@t"], self.code)
        _git(["config", "user.name", "t@t"], self.code)
        # 代码树里仍带旧单体（R1D 注入场景）
        items = [{"quarantine_id": "Q_%04d" % i, "original_object_type": "article",
                  "original_id": "https://ex.com/%d" % i, "reason_code": "other",
                  "detected_at": "2026-10-%02dT00:00:00Z" % ((i % 28) + 1),
                  "legacy_payload": {"pad": "x" * (code_bytes or 0)}} for i in range(legacy_items)]
        (self.code / "data" / "canonical" / "quarantine.json").write_text(
            json.dumps({"schema_version": "2.0", "items": items}, ensure_ascii=False), encoding="utf-8")
        (self.code / "data" / "runtime" / "ops" / "production_state.json").write_text(
            json.dumps({"last_successful_collection": "2026-11-02T09:00:00Z",
                        "processed_hashes": {"social_enrichment": {"h": {}}}}), encoding="utf-8")

        self.state = self.tmp / "state_src"
        _git(["clone", "-q", "-b", "production-state", str(self.bare), str(self.state)], self.tmp)
        _git(["config", "user.email", "t@t"], self.state)
        _git(["config", "user.name", "t@t"], self.state)
        # state_src 里也是"未迁移"的同一份单体
        shutil.copy2(self.code / "data" / "canonical" / "quarantine.json",
                     self.state / "data" / "canonical" / "quarantine.json")


class _Base(unittest.TestCase):
    code_bytes = None
    legacy_items = 60

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="asip5_r1d_")
        self.repo = _Repo(self.tmp, legacy_items=self.legacy_items, code_bytes=self.code_bytes)
        self._saved = (commit_state.ROOT, commit_state.STATE_DIR, commit_state.GIT_PATHS,
                       commit_state.COPY_PAIRS, commit_state.COPY_FILES,
                       paid_gate.BREAKER_PATH, paid_gate.BREAKER_REMOTE_PATH,
                       ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH,
                       ps.OPS_DIR, ps.STATE_FILE, ps.OPS_STATUS_FILE)
        commit_state.ROOT, commit_state.STATE_DIR = self.repo.code, self.repo.state
        commit_state.GIT_PATHS = ["data/runtime/ops", "data/canonical"]
        commit_state.COPY_PAIRS = [("data/runtime/ops", "data/runtime/ops"),
                                   ("data/canonical", "data/canonical")]
        commit_state.COPY_FILES = []
        paid_gate.BREAKER_PATH = Path(self.tmp) / "breaker.json"
        paid_gate.BREAKER_REMOTE_PATH = Path(self.tmp) / "breaker_remote.json"
        ai_ledger.LEDGER_PATH = Path(self.tmp) / "ai.jsonl"
        ai_ledger.SUMMARY_PATH = Path(self.tmp) / "ai_summary.json"
        # 把 production_state 的落盘路径指到临时代码树（避免污染真实仓库 data/）
        _opsdir = self.repo.code / "data" / "runtime" / "ops"
        _opsdir.mkdir(parents=True, exist_ok=True)
        ps.OPS_DIR = _opsdir
        ps.STATE_FILE = _opsdir / "production_state.json"
        ps.OPS_STATUS_FILE = _opsdir / "operations_status.json"
        paid_gate.save_remote_status(True, "test")
        os.environ.pop(paid_gate.PAUSE_ENV, None)
        os.environ.pop("GITHUB_ACTIONS", None)
        os.environ.pop("ASIP_RUN_MODE", None)
        # 本地裸仓库路径不含 asip-site：置空以跳过远端子串断言（仅测试环境）
        self._prev_sub = os.environ.get("ASIP_EXPECT_REPO_SUBSTR")
        os.environ["ASIP_EXPECT_REPO_SUBSTR"] = ""

    def tearDown(self):
        if self._prev_sub is None:
            os.environ.pop("ASIP_EXPECT_REPO_SUBSTR", None)
        else:
            os.environ["ASIP_EXPECT_REPO_SUBSTR"] = self._prev_sub
        (commit_state.ROOT, commit_state.STATE_DIR, commit_state.GIT_PATHS,
         commit_state.COPY_PAIRS, commit_state.COPY_FILES,
         paid_gate.BREAKER_PATH, paid_gate.BREAKER_REMOTE_PATH,
         ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH,
         ps.OPS_DIR, ps.STATE_FILE, ps.OPS_STATUS_FILE) = self._saved
        os.environ.pop("ASIP_RUN_MODE", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _migrate_state(self):
        st = QuarantineStore(root=self.repo.state, max_shard_bytes=2048)
        st.migrate(dry_run=False)
        st.retire_monolith(backup_dir=Path(self.tmp) / "offline_backup",
                           expect_items=len(json.loads(
                               (self.repo.state / "data" / "canonical" /
                                "quarantine.json").read_text(encoding="utf-8"))["items"]) or 60)
        return st


class TestMigrationCommitIsolated(_Base):
    code_bytes = 300 * 1024          # 代码树里每条 300KB → 约 18MB 旧单体

    def test_state_only_does_not_overwrite_tombstone(self):
        code_mono = self.repo.code / "data" / "canonical" / "quarantine.json"
        self.assertGreater(code_mono.stat().st_size, 15 * 1024 * 1024, "注入：代码树仍含大单体")
        st = self._migrate_state()
        tomb = st.legacy.read_text(encoding="utf-8")
        self.assertLess(st.legacy.stat().st_size, 4096)

        # 反证：若沿用旧路径（sync 覆盖），墓碑会被 18MB 单体取代
        commit_state.sync_to_state_branch()
        self.assertGreater(st.legacy.stat().st_size, 15 * 1024 * 1024,
                           "sync 会把代码树旧单体覆盖到 state_src（这就是必须 state_only 的原因）")
        # 恢复迁移状态
        st2 = QuarantineStore(root=self.repo.state, max_shard_bytes=2048)
        st2.migrate(dry_run=False, allow_remigrate=True)
        st2.retire_monolith(expect_items=60)

        res = commit_state.commit_now("ops: migration", after="migration", state_only=True,
                                      migration={"root": self.repo.state, "expect_items": 60},
                                      expect={"path": "data/runtime/ops/production_state.json",
                                              "fields_present": ["processed_hashes"]},
                                      require_expect=True)
        self.assertTrue(res["ok"] and res["pushed"])
        # state_src 仍是墓碑，且远端树逐文件字节与预期一致
        self.assertLess(st2.legacy.stat().st_size, 4096)
        self.assertEqual(json.loads(st2.legacy.read_text(encoding="utf-8"))["retired"], True)
        self.assertTrue(res["stages"]["verify_remote_tree"]["checked"])
        self.assertLess(res["stages"]["verify_remote_tree"]["max_bytes"], 100 * 1024 * 1024)
        # 代码树未被提交
        self.assertNotEqual(_git(["rev-parse", "HEAD"], self.repo.code, check=False).returncode, 0)


class TestCheckpointOrdering(_Base):
    def test_content_verified_before_push(self):
        remote_before = _git(["--git-dir", str(self.repo.bare), "rev-parse", "production-state"],
                             self.tmp).stdout.strip()
        with self.assertRaises(commit_state.CheckpointError) as ctx:
            commit_state.commit_now("x", after="collection", require_expect=True,
                                    expect={"path": "data/runtime/ops/production_state.json",
                                            "field": "last_successful_collection",
                                            "equals": "1999-01-01T00:00:00Z"})
        self.assertEqual(ctx.exception.stage, "verify_content")
        # 未推送：远端 SHA 必须仍是失败前那个（本地可以有提交，但绝不能发布）
        remote_after = _git(["--git-dir", str(self.repo.bare), "rev-parse", "production-state"],
                            self.tmp).stdout.strip()
        local = _git(["rev-parse", "HEAD"], self.repo.state).stdout.strip()
        self.assertEqual(remote_after, remote_before, "校验失败时不得推送新提交")
        self.assertNotEqual(local, remote_after, "本地提交存在但未发布（预期）")

    def test_merge_failure_not_masked(self):
        real = commit_state._git

        def fake(args, cwd=None, timeout=180):
            if args and args[0] == "merge":
                class R:
                    returncode, stdout, stderr = 1, "", "CONFLICT (content)"
                return R()
            return real(args, cwd=cwd, timeout=timeout)

        commit_state._git = fake
        try:
            with self.assertRaises(commit_state.CheckpointError) as ctx:
                commit_state.commit_now("x", after="collection")
            self.assertEqual(ctx.exception.stage, "merge", "merge 非零不得被 ahead-count 掩盖")
        finally:
            commit_state._git = real

    def test_push_failure_no_bad_data(self):
        hook = self.repo.bare / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        os.chmod(hook, 0o755)
        with self.assertRaises(commit_state.CheckpointError) as ctx:
            commit_state.commit_now("x", after="collection")
        self.assertEqual(ctx.exception.stage, "push")

    def test_no_change_still_verifies_head_and_remote(self):
        exp = {"path": "data/runtime/ops/production_state.json",
               "fields_present": ["processed_hashes"]}
        r1 = commit_state.commit_now("first", require_expect=True, expect=exp)
        self.assertTrue(r1["ok"] and r1["pushed"])
        r2 = commit_state.commit_now("second", require_expect=True, expect=exp)
        self.assertTrue(r2["ok"])
        self.assertFalse(r2["committed"], "无变更时不应产生新提交")
        self.assertTrue(r2["content_verified"], "无变更也必须校验 HEAD 内容")
        self.assertEqual(r2["remote"], r2["head"], "无变更也必须校验远端引用")


class TestCollectionOnly(_Base):
    def test_due_ai_tasks_are_dropped_and_zero_paid_calls(self):
        os.environ["ASIP_RUN_MODE"] = "collection_only"
        calls = []
        orig = so._run_script
        so._run_script = lambda *a, **k: calls.append(a[0][0] if isinstance(a[0], (list, tuple)) else str(a[0])) or True
        try:
            res = so.execute({"due": [{"task": "collection", "reason": "gap"},
                                      {"task": "social_ai", "reason": "eligible"},
                                      {"task": "daily_report", "reason": "tick"},
                                      {"task": "news_localization", "reason": "x"}]},
                             {"processed_hashes": {}},
                             trigger_meta={"trigger_source": "external_scheduler"})
        finally:
            so._run_script = orig
        self.assertEqual(res["mode"], "collection_only")
        self.assertFalse(res["deploy_required"], "collection_only 不得触发部署")
        modes = [str(c) for c in calls]
        self.assertTrue(any("collection_run.py" in c for c in modes), "必须执行采集")
        for bad in ("enrichment_run", "reports_run", "news_localization_run",
                    "assessment_run", "homepage_brief_run", "timeline_run"):
            self.assertFalse(any(bad in c for c in modes), "collection_only 不得执行 %s" % bad)
        # 门禁层：任何付费调用都会被拒（不依赖 pause 开关）
        self.assertNotIn(paid_gate.PAUSE_ENV, os.environ)
        from scripts.ops import ai_ledger as al
        prov = al.wrap_provider(object(), component="social_ai")
        with self.assertRaises(paid_gate.PaidTasksPaused) as ctx:
            prov.submit_task({"task_type": "x"})
        self.assertIn("collection_only", str(ctx.exception))


class TestBackupPreflight(_Base):
    def test_backup_outside_worktree_and_manifest_gate(self):
        from scripts.ops import quarantine_migrate as qm
        # 工作树内 → 拒绝
        rc = qm.main(["--root", str(self.repo.state), "--backup",
                      "--backup-dir", str(self.repo.state / "backup"), "--expect", "60"])
        self.assertEqual(rc, qm.EXIT_BACKUP, "备份不得放进 Git 工作树")
        # 工作树外 → 通过，并写清单
        out = Path(self.tmp) / "offline"
        rc2 = qm.main(["--root", str(self.repo.state), "--backup",
                       "--backup-dir", str(out), "--expect", "60"])
        self.assertEqual(rc2, qm.EXIT_OK)
        man = json.loads((out / "quarantine.backup.json").read_text(encoding="utf-8"))
        self.assertEqual(man["items"], 60)
        self.assertEqual(man["bytes"], (self.repo.state / "data/canonical/quarantine.json").stat().st_size)
        self.assertEqual(len(man["sha256"]), 64)
        # 无清单 → 拒绝迁移
        rc3 = qm.main(["--root", str(self.repo.state), "--apply", "--expect", "60"])
        self.assertEqual(rc3, qm.EXIT_REFUSED)
        # 单体被改动 → 清单不匹配 → 拒绝
        p = self.repo.state / "data/canonical/quarantine.json"
        doc = json.loads(p.read_text(encoding="utf-8"))
        doc["items"].append({"quarantine_id": "Q_extra", "detected_at": "2026-11-01T00:00:00Z"})
        p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        rc4 = qm.main(["--root", str(self.repo.state), "--apply", "--expect", "60",
                       "--backup-dir", str(out)])
        self.assertEqual(rc4, qm.EXIT_VERIFY, "备份过期必须拒绝迁移")
        # 重新备份 + 正确 expect → 成功，且 --expect 生效
        rc5 = qm.main(["--root", str(self.repo.state), "--backup",
                       "--backup-dir", str(out), "--expect", "61"])
        self.assertEqual(rc5, qm.EXIT_OK)
        rc6 = qm.main(["--root", str(self.repo.state), "--apply", "--expect", "61",
                       "--backup-dir", str(out)])
        self.assertEqual(rc6, qm.EXIT_OK)
        st = QuarantineStore(root=self.repo.state)
        self.assertTrue(st.is_sharded())
        self.assertEqual(st.verify_consistency()["on_disk"], 61)
        # 迁移后退役 + 树校验
        rc7 = qm.main(["--root", str(self.repo.state), "--retire", "--expect", "61"])
        self.assertEqual(rc7, qm.EXIT_OK)
        self.assertLess((self.repo.state / "data/canonical/quarantine.json").stat().st_size, 4096)


if __name__ == "__main__":
    unittest.main(verbosity=2)
