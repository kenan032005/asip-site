#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1B 任务1 — checkpoint 在 state_src 提交的完整验证（本地裸仓库模拟）。

覆盖验收：
  CHECKPOINT_CORRECT_WORKTREE=PASS       （提交发生在 state_src，不在代码工作树）
  CHECKPOINT_STATE_CONTENT_VERIFIED=PASS （HEAD 内容含本轮结果，如 last_successful_collection）
  CHECKPOINT_REMOTE_REF_VERIFIED=PASS    （push 后远端 SHA == 本地 HEAD）
  CHECKPOINT_FAILURE_FAIL_CLOSED=PASS    （push/commit 失败 → 抛错 + strike，不吞）
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
for p in (str(ROOT), str(ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.ops import commit_state, paid_gate  # noqa: E402


def _git(args, cwd, check=True):
    r = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError("%s: %s" % (args, r.stderr[-300:]))
    return r


def _init_env(tmp):
    """bare 远端 + 代码工作树 + state_src（production-state 克隆）。"""
    tmp = Path(tmp)
    bare = tmp / "remote.git"
    _git(["init", "--bare", "-q", str(bare)], cwd=tmp)
    seed = tmp / "seed"
    seed.mkdir()
    _git(["init", "-q"], cwd=seed)
    _git(["config", "user.email", "t@t"], cwd=seed)
    _git(["config", "user.name", "t"], cwd=seed)
    (seed / "data" / "runtime" / "ops").mkdir(parents=True)
    (seed / "data" / "runtime" / "ops" / "production_state.json").write_text(
        json.dumps({"last_successful_collection": ""}), encoding="utf-8")
    _git(["add", "-A"], cwd=seed)
    _git(["commit", "-qm", "seed"], cwd=seed)
    _git(["push", "-q", str(bare), "HEAD:production-state"], cwd=seed)
    code = tmp / "code"
    (code / "data" / "runtime" / "ops").mkdir(parents=True)
    _git(["init", "-q"], cwd=code)
    _git(["config", "user.email", "t@t"], cwd=code)
    _git(["config", "user.name", "t"], cwd=code)
    state = tmp / "state_src"
    _git(["clone", "-q", "-b", "production-state", str(bare), str(state)], cwd=tmp)
    _git(["config", "user.email", "t@t"], cwd=state)
    _git(["config", "user.name", "t"], cwd=state)
    return bare, code, state


class TestCheckpoint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="asip5_ckpt_")
        self.bare, self.code, self.state = _init_env(self.tmp)
        self._saved = (commit_state.ROOT, commit_state.STATE_DIR,
                       commit_state.GIT_PATHS, paid_gate.BREAKER_PATH)
        commit_state.ROOT, commit_state.STATE_DIR = self.code, self.state
        commit_state.GIT_PATHS = ["data/runtime/ops"]
        commit_state.COPY_PAIRS = [("data/runtime/ops", "data/runtime/ops")]
        commit_state.COPY_FILES = []
        paid_gate.BREAKER_PATH = Path(self.tmp) / "breaker.json"

    def tearDown(self):
        (commit_state.ROOT, commit_state.STATE_DIR,
         commit_state.GIT_PATHS, paid_gate.BREAKER_PATH) = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_state(self, value="2026-11-02T09:00:00Z"):
        p = self.code / "data" / "runtime" / "ops" / "production_state.json"
        p.write_text(json.dumps({"last_successful_collection": value,
                                 "processed_hashes": {"social_enrichment": {"h1": {}}}}),
                     encoding="utf-8")

    def test_commit_in_state_worktree_and_verify_remote(self):
        self._write_state()
        res = commit_state.commit_now("ops: test", after="collection",
                                      expect={"path": "data/runtime/ops/production_state.json",
                                              "field": "last_successful_collection",
                                              "equals": "2026-11-02T09:00:00Z"})
        self.assertTrue(res["ok"] and res["pushed"])
        # 1) 提交发生在 state_src
        top = _git(["rev-parse", "--show-toplevel"], cwd=self.state).stdout.strip()
        self.assertEqual(Path(top).resolve(), self.state.resolve())
        local = _git(["rev-parse", "HEAD"], cwd=self.state).stdout.strip()
        # 2) 代码工作树未被提交
        code_status = _git(["status", "--porcelain"], cwd=self.code).stdout.strip()
        self.assertTrue(code_status, "代码工作树文件应仍为未跟踪（未被 checkpoint 提交）")
        # 代码仓库不得有任何提交（checkpoint 只在 state_src 提交）
        code_head = _git(["rev-parse", "HEAD"], cwd=self.code, check=False)
        self.assertNotEqual(code_head.returncode, 0, "代码工作树不应产生提交")
        self.assertNotEqual(code_head.stdout.strip(), local)
        # 3) 远端 ref 已指向本地提交
        remote = subprocess.run(["git", "--git-dir", str(self.bare), "rev-parse", "production-state"],
                                capture_output=True, text=True).stdout.strip()
        self.assertEqual(remote, local, "远端 SHA 必须等于本地 HEAD")
        # 4) 已提交内容确实包含本轮结果
        shown = json.loads(_git(["show", "HEAD:data/runtime/ops/production_state.json"],
                                cwd=self.state).stdout)
        self.assertEqual(shown["last_successful_collection"], "2026-11-02T09:00:00Z")
        self.assertIn("social_enrichment", shown["processed_hashes"])

    def test_refuses_code_worktree(self):
        commit_state.STATE_DIR = self.code          # 指向代码工作树
        self._write_state()
        with self.assertRaises(commit_state.CheckpointError) as ctx:
            commit_state.commit_now("should fail")
        self.assertEqual(ctx.exception.stage, "guard")
        # 代码工作树不得产生新提交
        self.assertNotEqual(_git(["rev-parse", "HEAD"], cwd=self.code, check=False).returncode, 0)

    def test_push_rejected_fail_closed(self):
        hook = self.bare / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\necho 'rejected by test' >&2\nexit 1\n", encoding="utf-8")
        try:
            os.chmod(hook, 0o755)
        except OSError:
            pass
        self._write_state("2026-11-02T10:00:00Z")
        with self.assertRaises(commit_state.CheckpointError) as ctx:
            commit_state.commit_now("ops: push should fail", after="collection")
        self.assertEqual(ctx.exception.stage, "push")
        # 熔断计数 +1（失败不被吞）
        self.assertGreaterEqual(int(paid_gate.load_breaker().get("strikes") or 0), 1)

    def test_commit_failure_fail_closed(self):
        self._write_state()
        real = commit_state._git

        def fake(args, cwd=None, timeout=180):
            if args and args[0] == "commit":
                class R:
                    returncode = 1
                    stdout = ""
                    stderr = "simulated commit failure"
                return R()
            return real(args, cwd=cwd, timeout=timeout)

        commit_state._git = fake
        try:
            with self.assertRaises(commit_state.CheckpointError) as ctx:
                commit_state.commit_now("ops: commit should fail")
            self.assertEqual(ctx.exception.stage, "commit")
        finally:
            commit_state._git = real

    def test_content_mismatch_detected(self):
        self._write_state("2026-11-02T11:00:00Z")
        with self.assertRaises(commit_state.CheckpointError) as ctx:
            commit_state.commit_now("ops: content check", expect={
                "path": "data/runtime/ops/production_state.json",
                "field": "last_successful_collection",
                "equals": "1999-01-01T00:00:00Z"})
        self.assertEqual(ctx.exception.stage, "verify_content")


if __name__ == "__main__":
    unittest.main(verbosity=2)
