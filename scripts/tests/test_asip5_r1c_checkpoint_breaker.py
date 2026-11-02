#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1C 任务 C — checkpoint expect/guard 严格化 + breaker 失败退出码。

验收：R1C_CHECKPOINT_EXPECT_VERIFIED / R1C_BREAKER_FAIL_CLOSED
"""
import base64
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

from scripts.ops import commit_state, paid_gate, breakerctl  # noqa: E402


def _git(args, cwd, check=True):
    r = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError("%s: %s" % (args, r.stderr[-200:]))
    return r


class _Repo:
    def __init__(self, tmp):
        self.tmp = Path(tmp)
        self.bare = self.tmp / "remote.git"
        _git(["init", "--bare", "-q", str(self.bare)], self.tmp)
        seed = self.tmp / "seed"
        seed.mkdir()
        _git(["init", "-q"], seed)
        _git(["config", "user.email", "t@t"], seed)
        _git(["config", "user.name", "t"], seed)
        (seed / "data" / "runtime" / "ops").mkdir(parents=True)
        (seed / "data" / "runtime" / "ops" / "production_state.json").write_text(
            json.dumps({"last_successful_collection": "", "processed_hashes": {}}), encoding="utf-8")
        _git(["add", "-A"], seed)
        _git(["commit", "-qm", "seed"], seed)
        _git(["push", "-q", str(self.bare), "HEAD:production-state"], seed)
        self.base_sha = _git(["rev-parse", "HEAD"], seed).stdout.strip()
        self.code = self.tmp / "code"
        (self.code / "data" / "runtime" / "ops").mkdir(parents=True)
        _git(["init", "-q"], self.code)
        _git(["config", "user.email", "t@t"], self.code)
        _git(["config", "user.name", "t"], self.code)
        self.state = self.tmp / "state_src"
        _git(["clone", "-q", "-b", "production-state", str(self.bare), str(self.state)], self.tmp)
        _git(["config", "user.email", "t@t"], self.state)
        _git(["config", "user.name", "t"], self.state)


class TestCheckpointStrict(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="asip5_r1c_ck_")
        self.repo = _Repo(self.tmp)
        self._saved = (commit_state.ROOT, commit_state.STATE_DIR, commit_state.GIT_PATHS,
                       commit_state.COPY_PAIRS, commit_state.COPY_FILES, paid_gate.BREAKER_PATH)
        commit_state.ROOT, commit_state.STATE_DIR = self.repo.code, self.repo.state
        commit_state.GIT_PATHS = ["data/runtime/ops"]
        commit_state.COPY_PAIRS = [("data/runtime/ops", "data/runtime/ops")]
        commit_state.COPY_FILES = []
        paid_gate.BREAKER_PATH = Path(self.tmp) / "breaker.json"
        (self.repo.code / "data" / "runtime" / "ops" / "production_state.json").write_text(
            json.dumps({"last_successful_collection": "2026-11-02T09:00:00Z",
                        "processed_hashes": {"social_enrichment": {"h": {}}}}), encoding="utf-8")

    def tearDown(self):
        (commit_state.ROOT, commit_state.STATE_DIR, commit_state.GIT_PATHS,
         commit_state.COPY_PAIRS, commit_state.COPY_FILES, paid_gate.BREAKER_PATH) = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_require_expect_rejects_missing(self):
        with self.assertRaises(commit_state.CheckpointError) as ctx:
            commit_state.commit_now("x", require_expect=True)
        self.assertEqual(ctx.exception.stage, "expect_required")

    def test_fields_present_must_exist(self):
        with self.assertRaises(commit_state.CheckpointError) as ctx:
            commit_state.commit_now("x", after="collection",
                                    expect={"path": "data/runtime/ops/production_state.json",
                                            "fields_present": ["last_successful_collection",
                                                               "not_a_real_field"]},
                                    require_expect=True)
        self.assertEqual(ctx.exception.stage, "verify_content")
        self.assertIn("not_a_real_field", str(ctx.exception))

    def test_equals_mismatch_rejected(self):
        with self.assertRaises(commit_state.CheckpointError) as ctx:
            commit_state.commit_now("x", expect={
                "path": "data/runtime/ops/production_state.json",
                "field": "last_successful_collection",
                "equals": "1999-01-01T00:00:00Z"}, require_expect=True)
        self.assertEqual(ctx.exception.stage, "verify_content")

    def test_guard_rejects_wrong_branch(self):
        _git(["checkout", "-qb", "wrong-branch"], self.repo.state)
        with self.assertRaises(commit_state.CheckpointError) as ctx:
            commit_state.commit_now("x", expect={"path": "data/runtime/ops/production_state.json",
                                                 "fields_present": ["processed_hashes"]},
                                    require_expect=True)
        self.assertEqual(ctx.exception.stage, "guard")
        self.assertIn("expected 'production-state'", str(ctx.exception))

    def test_guard_rejects_wrong_remote(self):
        _git(["remote", "set-url", "origin", "https://github.com/someone/other-repo.git"],
             self.repo.state)
        with self.assertRaises(commit_state.CheckpointError) as ctx:
            commit_state.commit_now("x", guard_extra={"expected_remote_substr": "asip-site"})
        self.assertEqual(ctx.exception.stage, "guard")
        self.assertIn("does not contain expected", str(ctx.exception))

    def test_guard_rejects_unknown_base(self):
        with self.assertRaises(commit_state.CheckpointError) as ctx:
            commit_state.commit_now("x", guard_extra={"expected_base_sha": "f" * 40})
        self.assertEqual(ctx.exception.stage, "guard")
        self.assertIn("not an ancestor", str(ctx.exception))

    def test_happy_path_verified(self):
        res = commit_state.commit_now(
            "ops: ok", after="collection",
            expect={"path": "data/runtime/ops/production_state.json",
                    "field": "last_successful_collection", "equals": "2026-11-02T09:00:00Z",
                    "fields_present": ["processed_hashes"]},
            require_expect=True, guard_extra={"expected_base_sha": self.repo.base_sha})
        self.assertTrue(res["ok"] and res["pushed"])
        self.assertTrue(res["stages"]["verify_content"]["checked"])


class _FakeAPI:
    def __init__(self):
        self.refs = {"main": "a" * 40}
        self.contents = {}
        self.fail = None

    def __call__(self, url, token, method="GET", body=None, timeout=20):
        if self.fail:
            raise breakerctl.RemoteError(self.fail)
        if "/git/ref/heads/" in url and method == "GET":
            br = url.rsplit("/", 1)[1]
            return ({"object": {"sha": self.refs[br]}}, 200) if br in self.refs else (None, 404)
        if url.endswith("/git/refs") and method == "POST":
            self.refs[body["ref"].split("/")[-1]] = body["sha"]
            return ({}, 201)
        if "/contents/" in url and method == "GET":
            br = url.split("ref=")[-1]
            body = self.contents.get((br, "breaker.json"))
            if body is None:
                return (None, 404)
            return ({"content": base64.b64encode(json.dumps(body).encode()).decode(),
                     "sha": "s1"}, 200)
        if "/contents/" in url and method == "PUT":
            self.contents[(body["branch"], "breaker.json")] = json.loads(
                base64.b64decode(body["content"]).decode())
            return ({"content": {}}, 200)
        if url.endswith("/repos/o/r"):
            return ({"default_branch": "main"}, 200)
        raise breakerctl.RemoteError("unhandled %s %s" % (method, url))


class TestBreakerExitCodes(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="asip5_r1c_br_"))
        self._saved = (paid_gate.BREAKER_PATH, paid_gate.BREAKER_REMOTE_PATH)
        paid_gate.BREAKER_PATH = self.tmp / "breaker.json"
        paid_gate.BREAKER_REMOTE_PATH = self.tmp / "breaker_remote.json"
        self.api = _FakeAPI()
        self._orig = breakerctl._api
        breakerctl._api = self.api
        self._tok = os.environ.get("GITHUB_TOKEN")
        os.environ["GITHUB_TOKEN"] = "t"

    def tearDown(self):
        breakerctl._api = self._orig
        paid_gate.BREAKER_PATH, paid_gate.BREAKER_REMOTE_PATH = self._saved
        if self._tok is None:
            os.environ.pop("GITHUB_TOKEN", None)
        else:
            os.environ["GITHUB_TOKEN"] = self._tok
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_bootstrap_ok_then_fetch_ok(self):
        rc = breakerctl.main(["bootstrap", "--repo", "o/r"])
        self.assertEqual(rc, 0)
        rc2 = breakerctl.main(["fetch", "--repo", "o/r"])
        self.assertEqual(rc2, 0)

    def test_fetch_failure_nonzero(self):
        self.api.fail = "network down"
        rc = breakerctl.main(["fetch", "--repo", "o/r"])
        self.assertEqual(rc, 3, "远端不可验证必须非零退出（fail-closed）")
        self.assertFalse(paid_gate.breaker_remote()["reachable"])

    def test_publish_failure_nonzero(self):
        self.api.fail = "403 forbidden"
        rc = breakerctl.main(["publish", "--repo", "o/r"])
        self.assertEqual(rc, 4)

    def test_strike_publish_failure_nonzero(self):
        self.api.fail = "network down"
        rc = breakerctl.main(["strike", "--reason", "state_push_failed", "--repo", "o/r"])
        self.assertEqual(rc, 6, "远端持久化失败 → 非零（不得当成功）")
        self.assertGreaterEqual(int(paid_gate.load_breaker().get("strikes") or 0), 1)

    def test_clear_without_reason_rejected(self):
        rc = breakerctl.main(["clear"])
        self.assertEqual(rc, 2)

    def test_clear_publish_failure_nonzero(self):
        paid_gate.record_strike("a")
        paid_gate.record_strike("b")
        self.api.fail = "network down"
        rc = breakerctl.main(["clear", "--by", "kenan", "--reason", "migrated",
                              "--repo", "o/r"])
        self.assertEqual(rc, 7, "本地已解除但远端未同步 → 非零")
        self.assertFalse(paid_gate.load_breaker()["tripped"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
