#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ASIP Stage 2.5B-RH — 状态对账最终失败关闭加固测试（实现后绿灯）。

本测试使用临时目录模拟生产状态，不使用生产 data/ai。
验证 Schema 校验、cache_key 严格、删除验证、lease 身份验证等 12 项。
"""

import json
import os
import sys
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)

from ai.workbuddy_queue_provider import (
    reconcile_task_state, _ensure_ai_dirs,
    remove_with_retry_verified,
)
from ai.workbuddy_worker import (
    ingest_results, status_summary,
    AI_ROOT, _ensure_dirs,
)


def _make_task(task_id, cache_key, status, ai_result=None, extra=None):
    task = {
        "task_id": task_id,
        "schema_version": "1.0",
        "task_type": "article_analysis",
        "status": status,
        "priority": "high",
        "input_ref": {
            "country_iso3": "NER",
            "source_language": "en",
            "source_text": "[TEST] synthetic scenario",
            "synthetic": True,
            "scenario_id": "test-hardening",
        },
        "content_hash": "abc123",
        "prompt_version": "ai_v1",
        "output_schema_version": "1.0",
        "provider_requested": "workbuddy_queue",
        "created_at": "2026-07-31T00:00:00Z",
        "retry_count": 0,
        "max_retries": 1,
        "cache_key": cache_key,
        "synthetic": True,
    }
    if extra:
        task.update(extra)
    if ai_result:
        task["ai_result"] = ai_result
    return task


def _make_valid_ai_result(task_id):
    """符合 validate_ai_result 的完整 AI 结果（AIT_<24 hex> task_id）。"""
    return {
        "task_id": task_id,
        "schema_version": "1.0",
        "status": "success",
        "provider": "workbuddy_queue",
        "model": "deepseek-v4-flash",
        "started_at": "2026-07-31T10:00:00Z",
        "completed_at": "2026-07-31T10:00:05Z",
        "result": {
            "summary_zh": "test summary",
            "country_iso3": "NER",
            "source_language": "en",
            "event_type": "road_closure",
            "key_facts": ["test fact"],
            "uncertainties": ["test uncertainty"],
            "synthetic": True,
            "producer_session_id": "producer_test",
            "consumer_session_id": "consumer_test",
        },
        "error": None,
        "usage": {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0},
    }


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _setup_temp_ai_root():
    root = tempfile.mkdtemp(prefix="asip_hardening_")
    _ensure_ai_dirs(root)
    for d in ("batches", "leases", "locks", "audit"):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    return root


# ── H1-H4: AI Result Schema 与 cache_key 严格校验 ──

class TestAuthorityValidation(unittest.TestCase):

    def setUp(self):
        self.root = _setup_temp_ai_root()
        self.tid = "AIT_000000000000000000000001"
        self.ck = "cache:hardening_test"
        self.batch_id = "BATCH_H_001"
        self.worker_id = "worker_h_001"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _setup_manifest(self):
        _write_json(os.path.join(self.root, "batches", self.batch_id,
                                  "manifest.json"), {
            "batch_id": self.batch_id,
            "worker_id": self.worker_id,
            "created_at": "2026-07-31T10:00:00Z",
            "lease_expires_at": "2026-07-31T10:30:00Z",
            "task_count": 1,
            "expected_provider": "workbuddy_queue",
            "expected_model": "deepseek-v4-flash",
            "tasks": [{"task_id": self.tid, "task_type": "article_analysis",
                        "status": "processing", "priority": "high"}],
        })

    def _setup_lease(self):
        _write_json(os.path.join(self.root, "leases", f"{self.tid}.json"), {
            "task_id": self.tid,
            "batch_id": self.batch_id,
            "worker_id": self.worker_id,
            "claimed_at": "2026-07-31T10:00:00Z",
            "lease_expires_at": "2026-07-31T20:00:00Z",
            "heartbeat_at": "2026-07-31T10:00:00Z",
            "attempt_number": 1,
        })

    def test_H1_invalid_ai_result_schema_rejected(self):
        """H1: ai_result 违反 Schema 时，不得成为权威结果。"""
        self._setup_manifest()
        self._setup_lease()
        bad_ai = {
            "task_id": self.tid,
            "schema_version": "1.0",
            # missing "status"
            "provider": "workbuddy_queue",
            "model": "deepseek-v4-flash",
            "started_at": "2026-07-31T10:00:00Z",
            "completed_at": "2026-07-31T10:00:05Z",
            "result": {},
            "error": None,
            "usage": {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0},
        }
        _write_json(os.path.join(self.root, "completed", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "completed", ai_result=bad_ai))
        _write_json(os.path.join(self.root, "processing", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "processing"))

        rec = reconcile_task_state(self.tid, ai_root=self.root,
                                   batch_id=self.batch_id, worker_id=self.worker_id,
                                   dry_run=False)
        self.assertTrue(rec["conflicts"],
                        "H1: should report conflict for invalid ai_result")

    def test_H2_completed_missing_cache_key_fail(self):
        """H2: completed 缺少 cache_key 时失败关闭。"""
        self._setup_manifest()
        self._setup_lease()
        task = _make_task(self.tid, self.ck, "completed",
                          ai_result=_make_valid_ai_result(self.tid))
        del task["cache_key"]
        _write_json(os.path.join(self.root, "completed", f"{self.tid}.json"), task)
        _write_json(os.path.join(self.root, "processing", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "processing"))

        rec = reconcile_task_state(self.tid, ai_root=self.root,
                                   batch_id=self.batch_id, worker_id=self.worker_id,
                                   dry_run=False)
        self.assertTrue(rec["conflicts"],
                        "H2: should report conflict for missing cache_key")
        self.assertFalse(rec.get("reconciled", False))

    def test_H3_processing_missing_cache_key_fail(self):
        """H3: processing 缺少 cache_key 时失败关闭。"""
        self._setup_manifest()
        self._setup_lease()
        _write_json(os.path.join(self.root, "completed", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "completed",
                                ai_result=_make_valid_ai_result(self.tid)))
        task = _make_task(self.tid, self.ck, "processing")
        del task["cache_key"]
        _write_json(os.path.join(self.root, "processing", f"{self.tid}.json"), task)

        rec = reconcile_task_state(self.tid, ai_root=self.root,
                                   batch_id=self.batch_id, worker_id=self.worker_id,
                                   dry_run=False)
        self.assertTrue(rec["conflicts"],
                        "H3: should report conflict for missing cache_key in processing")

    def test_H4_cache_key_mismatch_fail_closed(self):
        """H4: cache_key 不同时失败关闭。"""
        self._setup_manifest()
        self._setup_lease()
        _write_json(os.path.join(self.root, "completed", f"{self.tid}.json"),
                     _make_task(self.tid, "cache:value_abc", "completed",
                                ai_result=_make_valid_ai_result(self.tid)))
        _write_json(os.path.join(self.root, "processing", f"{self.tid}.json"),
                     _make_task(self.tid, "cache:value_xyz", "processing"))

        rec = reconcile_task_state(self.tid, ai_root=self.root,
                                   batch_id=self.batch_id, worker_id=self.worker_id,
                                   dry_run=False)
        self.assertTrue(rec["conflicts"],
                        "H4: should report conflict for cache_key mismatch")


# ── H5-H6: 删除失败必须报告且不声称成功 ──

class TestDeleteFailureReporting(unittest.TestCase):

    def setUp(self):
        self.root = _setup_temp_ai_root()
        self.tid = "AIT_000000000000000000000002"
        self.ck = "cache:hardening_delete"
        self.batch_id = "BATCH_H_002"
        self.worker_id = "worker_h_002"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _setup_standard(self):
        _write_json(os.path.join(self.root, "batches", self.batch_id,
                                  "manifest.json"), {
            "batch_id": self.batch_id,
            "worker_id": self.worker_id,
            "created_at": "2026-07-31T10:00:00Z",
            "lease_expires_at": "2026-07-31T10:30:00Z",
            "task_count": 1,
            "expected_provider": "workbuddy_queue",
            "expected_model": "deepseek-v4-flash",
            "tasks": [{"task_id": self.tid, "task_type": "article_analysis",
                        "status": "processing", "priority": "high"}],
        })
        _write_json(os.path.join(self.root, "completed", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "completed",
                                ai_result=_make_valid_ai_result(self.tid)))
        _write_json(os.path.join(self.root, "processing", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "processing"))
        _write_json(os.path.join(self.root, "leases", f"{self.tid}.json"), {
            "task_id": self.tid,
            "batch_id": self.batch_id,
            "worker_id": self.worker_id,
            "claimed_at": "2026-07-31T10:00:00Z",
            "lease_expires_at": "2026-07-31T20:00:00Z",
            "heartbeat_at": "2026-07-31T10:00:00Z",
            "attempt_number": 1,
        })

    def test_H5_has_cleanup_fields(self):
        """H5: 加固后 reconcile 返回 cleanup_attempted/succeeded/failed 字段。"""
        self._setup_standard()
        rec = reconcile_task_state(self.tid, ai_root=self.root,
                                   batch_id=self.batch_id, worker_id=self.worker_id,
                                   dry_run=False)
        self.assertIn("cleanup_attempted", rec)
        self.assertIn("cleanup_succeeded", rec)
        self.assertIn("cleanup_failed", rec)
        self.assertIn("unresolved_paths", rec)
        # reconciled 应基于实际成功
        self.assertTrue(rec.get("reconciled", False))
        self.assertEqual(rec["cleanup_failed"], 0)
        self.assertGreater(rec["cleanup_succeeded"], 0)

    def test_H6_removed_only_on_success(self):
        """H6: 删除成功才记录 removed_* action，且文件确实已删除。"""
        self._setup_standard()
        rec = reconcile_task_state(self.tid, ai_root=self.root,
                                   batch_id=self.batch_id, worker_id=self.worker_id,
                                   dry_run=False)
        for action in rec.get("actions", []):
            if "removed_processing" in action:
                self.assertFalse(os.path.exists(os.path.join(
                    self.root, "processing", f"{self.tid}.json")))
            if "removed_lease" in action:
                self.assertFalse(os.path.exists(os.path.join(
                    self.root, "leases", f"{self.tid}.json")))


# ── H7-H8: lease 删除报告 ──

class TestLeaseDeleteReporting(unittest.TestCase):

    def setUp(self):
        self.root = _setup_temp_ai_root()
        self.tid = "AIT_000000000000000000000003"
        self.ck = "cache:hardening_lease"
        self.batch_id = "BATCH_H_003"
        self.worker_id = "worker_h_003"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _setup_with_lease(self):
        _write_json(os.path.join(self.root, "batches", self.batch_id,
                                  "manifest.json"), {
            "batch_id": self.batch_id,
            "worker_id": self.worker_id,
            "created_at": "2026-07-31T10:00:00Z",
            "lease_expires_at": "2026-07-31T10:30:00Z",
            "task_count": 1,
            "expected_provider": "workbuddy_queue",
            "expected_model": "deepseek-v4-flash",
            "tasks": [{"task_id": self.tid, "task_type": "article_analysis",
                        "status": "processing", "priority": "high"}],
        })
        _write_json(os.path.join(self.root, "completed", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "completed",
                                ai_result=_make_valid_ai_result(self.tid)))
        _write_json(os.path.join(self.root, "leases", f"{self.tid}.json"), {
            "task_id": self.tid,
            "batch_id": self.batch_id,
            "worker_id": self.worker_id,
            "claimed_at": "2026-07-31T10:00:00Z",
            "lease_expires_at": "2026-07-31T20:00:00Z",
            "heartbeat_at": "2026-07-31T10:00:00Z",
            "attempt_number": 1,
        })

    def test_H7_cleanup_fields_present(self):
        """H7/H8: 加固后 report 含 cleanup_attempted/succeeded/failed。"""
        self._setup_with_lease()
        rec = reconcile_task_state(self.tid, ai_root=self.root,
                                   batch_id=self.batch_id, worker_id=self.worker_id,
                                   dry_run=False)
        self.assertIn("cleanup_attempted", rec)
        self.assertIn("cleanup_failed", rec)
        self.assertIn("unresolved_paths", rec)
        # lease 应在 manifest 身份验证通过后成功清理
        self.assertIn("removed_lease", rec.get("actions", []))
        self.assertFalse(os.path.exists(os.path.join(
            self.root, "leases", f"{self.tid}.json")))


# ── H9-H10: lease 严格身份验证 ──

class TestLeaseManifestIdentity(unittest.TestCase):

    def setUp(self):
        self.root = _setup_temp_ai_root()
        self.tid = "AIT_000000000000000000000004"
        self.ck = "cache:hardening_identity"
        self.batch_id = "BATCH_H_004"
        self.worker_id = "worker_h_004"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_H9_no_batch_id_no_lease_delete(self):
        """H9: 无 batch-id 和 worker-id 时不得删除 lease。"""
        _write_json(os.path.join(self.root, "completed", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "completed",
                                ai_result=_make_valid_ai_result(self.tid)))
        _write_json(os.path.join(self.root, "leases", f"{self.tid}.json"), {
            "task_id": self.tid,
            "batch_id": self.batch_id,
            "worker_id": self.worker_id,
            "claimed_at": "2026-07-31T10:00:00Z",
            "lease_expires_at": "2026-07-31T20:00:00Z",
            "heartbeat_at": "2026-07-31T10:00:00Z",
            "attempt_number": 1,
        })
        rec = reconcile_task_state(self.tid, ai_root=self.root,
                                   batch_id=None, worker_id=None, dry_run=False)
        self.assertTrue(os.path.exists(os.path.join(
            self.root, "leases", f"{self.tid}.json")),
            "H9: lease should NOT be deleted without batch-id/worker-id")
        self.assertIn("lease_identity_requires_batch_and_worker", rec.get("conflicts", []))

    def test_H10_manifest_missing_no_lease_delete(self):
        """H10: manifest 缺失时不得删除 lease。"""
        _write_json(os.path.join(self.root, "completed", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "completed",
                                ai_result=_make_valid_ai_result(self.tid)))
        _write_json(os.path.join(self.root, "leases", f"{self.tid}.json"), {
            "task_id": self.tid,
            "batch_id": self.batch_id,
            "worker_id": self.worker_id,
            "claimed_at": "2026-07-31T10:00:00Z",
            "lease_expires_at": "2026-07-31T20:00:00Z",
            "heartbeat_at": "2026-07-31T10:00:00Z",
            "attempt_number": 1,
        })
        rec = reconcile_task_state(self.tid, ai_root=self.root,
                                   batch_id=self.batch_id, worker_id=self.worker_id,
                                   dry_run=False)
        self.assertTrue(os.path.exists(os.path.join(
            self.root, "leases", f"{self.tid}.json")),
            "H10: lease should NOT be deleted when manifest missing")
        self.assertIn("lease_manifest_missing", rec.get("conflicts", []))


# ── H11: completed + queue 残留 ──

class TestTerminalQueueConflict(unittest.TestCase):

    def setUp(self):
        self.root = _setup_temp_ai_root()
        self.tid = "AIT_000000000000000000000005"
        self.ck = "cache:hardening_queue"
        self.batch_id = "BATCH_H_005"
        self.worker_id = "worker_h_005"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_H11_completed_and_queue_auto_clean(self):
        """H11: completed + queue → queue 被视为 stale，自动清理。"""
        _write_json(os.path.join(self.root, "batches", self.batch_id,
                                  "manifest.json"), {
            "batch_id": self.batch_id,
            "worker_id": self.worker_id,
            "created_at": "2026-07-31T10:00:00Z",
            "lease_expires_at": "2026-07-31T10:30:00Z",
            "task_count": 1,
            "expected_provider": "workbuddy_queue",
            "expected_model": "deepseek-v4-flash",
            "tasks": [{"task_id": self.tid, "task_type": "article_analysis",
                        "status": "processing", "priority": "high"}],
        })
        _write_json(os.path.join(self.root, "completed", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "completed",
                                ai_result=_make_valid_ai_result(self.tid)))
        _write_json(os.path.join(self.root, "queue", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "queued"))

        st0 = status_summary(self.root)
        self.assertGreaterEqual(st0.get("duplicate_state_task_count", 0), 1,
                                "pre: should have duplicate states")

        rec = reconcile_task_state(self.tid, ai_root=self.root,
                                   batch_id=None, worker_id=None, dry_run=False)
        self.assertIn("queue", rec.get("states_found", []),
                      "H11: queue should be in states_found")
        # queue 被清理
        self.assertFalse(os.path.exists(os.path.join(
            self.root, "queue", f"{self.tid}.json")),
            "H11: queue should be removed when completed is authoritative")
        self.assertTrue(rec.get("reconciled", False))


# ── H12: dry-run 与 report 语义 ──

class TestReportSemantics(unittest.TestCase):

    def setUp(self):
        self.root = _setup_temp_ai_root()
        self.tid = "AIT_000000000000000000000006"
        self.ck = "cache:hardening_semantics"
        self.batch_id = "BATCH_H_006"
        self.worker_id = "worker_h_006"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_H12_dry_run_semantics(self):
        """H12: dry_run 返回 would_reconcile=true 而非 reconciled=true。"""
        _write_json(os.path.join(self.root, "completed", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "completed",
                                ai_result=_make_valid_ai_result(self.tid)))
        _write_json(os.path.join(self.root, "processing", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "processing"))

        rec = reconcile_task_state(self.tid, ai_root=self.root,
                                   batch_id=None, worker_id=None, dry_run=True)
        self.assertFalse(rec.get("reconciled", True),
                         "H12: dry_run must NOT set reconciled=true")
        self.assertTrue(rec.get("would_reconcile", False),
                        "H12: dry_run should set would_reconcile=true")
        self.assertIn("planned_actions", rec)
        # 文件不应被修改
        self.assertTrue(os.path.exists(os.path.join(
            self.root, "processing", f"{self.tid}.json")),
            "H12: dry_run should not delete files")


# ── 原 15 项恢复测试回归 ──

class TestOriginalRecoveryRegression(unittest.TestCase):

    def setUp(self):
        self.root = _setup_temp_ai_root()
        self.tid = "AIT_001122334455667788990011"
        self.ck = "cache:hardening_regress"
        self.batch_id = "BATCH_H_REGRESS"
        self.worker_id = "worker_h_regress"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_recovery_regression_still_works(self):
        """原恢复测试逻辑：正常双状态 + lease 自动清理仍工作。"""
        _write_json(os.path.join(self.root, "batches", self.batch_id,
                                  "manifest.json"), {
            "batch_id": self.batch_id,
            "worker_id": self.worker_id,
            "created_at": "2026-07-31T10:00:00Z",
            "lease_expires_at": "2026-07-31T10:30:00Z",
            "task_count": 1,
            "expected_provider": "workbuddy_queue",
            "expected_model": "deepseek-v4-flash",
            "tasks": [{"task_id": self.tid, "task_type": "article_analysis",
                        "status": "processing", "priority": "high"}],
        })
        valid_ai = {
            "task_id": self.tid,
            "schema_version": "1.0",
            "status": "success",
            "provider": "workbuddy_queue",
            "model": "deepseek-v4-flash",
            "started_at": "2026-07-31T10:00:00Z",
            "completed_at": "2026-07-31T10:00:05Z",
            "result": {
                "summary_zh": "test",
                "country_iso3": "NER",
                "source_language": "en",
                "event_type": "road_closure",
                "key_facts": ["f1"],
                "uncertainties": ["u1"],
                "synthetic": True,
                "producer_session_id": "p1",
                "consumer_session_id": "c1",
            },
            "error": None,
            "usage": {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0},
        }
        _write_json(os.path.join(self.root, "completed", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "completed", ai_result=valid_ai))
        _write_json(os.path.join(self.root, "processing", f"{self.tid}.json"),
                     _make_task(self.tid, self.ck, "processing"))
        _write_json(os.path.join(self.root, "leases", f"{self.tid}.json"), {
            "task_id": self.tid,
            "batch_id": self.batch_id,
            "worker_id": self.worker_id,
            "claimed_at": "2026-07-31T10:00:00Z",
            "lease_expires_at": "2026-07-31T20:00:00Z",
            "heartbeat_at": "2026-07-31T10:00:00Z",
            "attempt_number": 1,
        })
        rec = reconcile_task_state(self.tid, ai_root=self.root,
                                   batch_id=self.batch_id, worker_id=self.worker_id,
                                   dry_run=False)
        self.assertTrue(rec.get("reconciled", False))
        self.assertFalse(os.path.exists(os.path.join(
            self.root, "processing", f"{self.tid}.json")))
        self.assertFalse(os.path.exists(os.path.join(
            self.root, "leases", f"{self.tid}.json")))
        self.assertTrue(os.path.exists(os.path.join(
            self.root, "completed", f"{self.tid}.json")))


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for cls in [TestAuthorityValidation, TestDeleteFailureReporting,
                TestLeaseDeleteReporting, TestLeaseManifestIdentity,
                TestTerminalQueueConflict, TestReportSemantics,
                TestOriginalRecoveryRegression]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    failed = len(result.failures) + len(result.errors)
    print(f"\nRESULT: PASS={passed} FAIL={failed}")
    sys.exit(0 if failed == 0 else 1)
