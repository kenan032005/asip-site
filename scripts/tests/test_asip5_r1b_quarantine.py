#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1B 任务3 — 全部 quarantine 读取统一、损坏 fail-closed、回滚保留增量。

验收：
  ALL_QUARANTINE_READERS_MIGRATED=YES / CORRUPT_SHARD_FAIL_CLOSED=PASS
  NO_SILENT_LEGACY_FALLBACK=YES / ATOMIC_RECOVERY_TEST=PASS
  RECORD_EQUALITY=PASS / ROLLBACK_WITH_NEW_RECORDS=PASS
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "scripts" / "data"),
          str(ROOT / "scripts" / "collectors")):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.data.quarantine_store import QuarantineStore, QuarantineCorrupt  # noqa: E402

READERS = [
    "scripts/collectors/framework.py",
    "scripts/data/article_persistence.py",
    "scripts/data/repository.py",
    "scripts/ai/hy3_stage4_provider.py",
]


def _rec_hash(it):
    return hashlib.sha256(json.dumps(it, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _mk(root, n=40):
    root = Path(root)
    (root / "data" / "canonical").mkdir(parents=True, exist_ok=True)
    items = [{"quarantine_id": "Q_%03d" % i, "original_object_type": "event" if i % 2 else "article",
              "original_id": "https://ex.com/%d" % i,
              "reason_code": ["other", "wrong_country", "not_security_relevant"][i % 3],
              "detected_at": "2026-10-%02dT00:00:00Z" % ((i % 28) + 1),
              "legacy_payload": {"p": "x" * (50 + i)}} for i in range(n)]
    (root / "data" / "canonical" / "quarantine.json").write_text(
        json.dumps({"schema_version": "2.0", "items": items}, ensure_ascii=False), encoding="utf-8")
    return root, items


class TestReadersMigrated(unittest.TestCase):
    def test_no_reader_reads_monolith_directly(self):
        for rel in READERS:
            src = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("QuarantineStore", src, "%s 未使用 QuarantineStore" % rel)
            # 不允许再用裸 json.load 读 canonical/quarantine.json
            for bad in ('json.load(open(os.path.join(root, "data", "canonical", "quarantine.json")',
                        'here / "data" / "canonical" / "quarantine.json"'):
                self.assertNotIn(bad, src, "%s 仍直接读取单体文件" % rel)


class TestQuarantineStrict(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="asip5_r1b_q_")
        self.root, self.items = _mk(self.tmp)
        self.store = QuarantineStore(root=self.root, max_shard_bytes=2048)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_readers_use_shards_after_migration(self):
        self.store.migrate(dry_run=False)
        # repository.load_quarantine 走 store
        from scripts.data.repository import Repository
        repo = Repository(root=Path(self.root))
        got = repo.load_quarantine()
        self.assertEqual(len(got), len(self.items))
        self.assertEqual({i["quarantine_id"] for i in got},
                         {i["quarantine_id"] for i in self.items})
        # framework.url_map 走 store
        import scripts.collectors.framework as fw
        old_root = fw.ROOT
        fw.ROOT = str(self.root)
        try:
            um = fw._load_quarantine_urls()
            self.assertTrue(um, "迁移后必须能读到隔离 URL")
        finally:
            fw.ROOT = old_root

    def test_manifest_without_index_raises(self):
        self.store.migrate(dry_run=False)
        (self.root / "data" / "canonical" / "quarantine" / "index.json").unlink()
        with self.assertRaises(QuarantineCorrupt):
            self.store.load_items()
        with self.assertRaises(QuarantineCorrupt):
            self.store.mode()

    def test_missing_shard_raises(self):
        self.store.migrate(dry_run=False)
        shard = sorted((self.root / "data" / "canonical" / "quarantine").glob("2026-10*.json"))[0]
        shard.unlink()
        with self.assertRaises(QuarantineCorrupt):
            self.store.load_items()
        with self.assertRaises(QuarantineCorrupt):
            self.store.verify_consistency()

    def test_corrupt_shard_raises_not_empty(self):
        self.store.migrate(dry_run=False)
        shard = sorted((self.root / "data" / "canonical" / "quarantine").glob("2026-10*.json"))[0]
        shard.write_text('{"items": [', encoding="utf-8")
        with self.assertRaises(QuarantineCorrupt):
            self.store.load_items(verify_checksums=True)
        with self.assertRaises(QuarantineCorrupt):
            list(self.store.iter_items())

    def test_atomic_recovery_orphan_tmp(self):
        self.store.migrate(dry_run=False)
        qdir = self.root / "data" / "canonical" / "quarantine"
        before = self.store.load_items(verify_checksums=True)
        (qdir / "2026-10.json.tmp").write_text('{"items": [ partial', encoding="utf-8")
        after = self.store.load_items(verify_checksums=True)
        self.assertEqual([_rec_hash(x) for x in before], [_rec_hash(x) for x in after],
                         "孤儿 .tmp 不得影响已提交分片")
        self.assertFalse((qdir / "2026-10.json.tmp").exists(), "孤儿 .tmp 应被清理")

    def test_consistency_check(self):
        self.store.migrate(dry_run=False)
        rep = self.store.verify_consistency()
        self.assertTrue(rep["consistent"])
        self.assertEqual(rep["on_disk"], len(self.items))
        self.assertEqual(rep["ids"], len(self.items))

    def test_rollback_keeps_new_records(self):
        self.store.migrate(dry_run=False)
        new = [{"quarantine_id": "Q_new1", "original_object_type": "event",
                "original_id": "https://ex.com/new1", "reason_code": "other",
                "detected_at": "2026-10-29T00:00:00Z", "legacy_payload": {}},
               {"quarantine_id": "Q_new2", "original_object_type": "article",
                "original_id": "https://ex.com/new2", "reason_code": "other",
                "detected_at": "2026-08-03T00:00:00Z", "legacy_payload": {}}]
        r = self.store.upsert(new, run_id="R1")
        self.assertEqual(r["added"], 2)
        total = len(self.items) + 2
        rb = self.store.rollback_to_monolith(expect_items=total)
        self.assertTrue(rb["ok"])
        self.assertEqual(rb["restored_items"], total)
        self.assertFalse(self.store.is_sharded())
        merged = self.store.load_items()
        ids = {i["quarantine_id"] for i in merged}
        self.assertEqual(len(merged), total)
        self.assertIn("Q_new1", ids)
        self.assertIn("Q_new2", ids, "回滚必须保留迁移后新增（跨月）记录")


@unittest.skipUnless(os.environ.get("ASIP5_REAL_SNAPSHOT"),
                     "设置 ASIP5_REAL_SNAPSHOT 才跑真实 20,461 条比对")
class TestRealSnapshotR1B(unittest.TestCase):
    def test_real_migration_and_rollback_with_new(self):
        src = Path(os.environ["ASIP5_REAL_SNAPSHOT"])
        tmp = tempfile.mkdtemp(prefix="asip5_real2_")
        root = Path(tmp)
        (root / "data" / "canonical").mkdir(parents=True)
        (root / "data" / "canonical" / "quarantine.json").write_bytes(src.read_bytes())
        items = json.loads(src.read_text(encoding="utf-8"))["items"]
        st = QuarantineStore(root=root, max_shard_bytes=20 * 1024 * 1024)
        rep = st.migrate(dry_run=False)
        self.assertEqual(rep["total_items"], len(items))
        idx = st.read_index()
        self.assertLessEqual(max(s["bytes"] for s in idx["shards"]), 20 * 1024 * 1024)
        merged = st.load_items(verify_checksums=True)
        self.assertEqual({i["quarantine_id"]: _rec_hash(i) for i in items},
                         {i["quarantine_id"]: _rec_hash(i) for i in merged})
        # 迁移后新增 → 回滚保留
        st.upsert([{"quarantine_id": "Q_r1b_new", "original_object_type": "event",
                    "original_id": "https://ex.com/r1b", "reason_code": "other",
                    "detected_at": "2026-11-01T00:00:00Z"}], run_id="R")
        rb = st.rollback_to_monolith(expect_items=len(items) + 1)
        self.assertEqual(rb["restored_items"], len(items) + 1)
        self.assertTrue(any(i["quarantine_id"] == "Q_r1b_new" for i in st.load_items()))
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
