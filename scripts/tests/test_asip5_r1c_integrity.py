#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1C 任务 A/B — 分片完整性保护 + 超限单体退役（离线）。

验收：R1C_DATA_INTEGRITY / R1C_NO_LEGACY_OVERSIZE_FILE / R1C_REAL_SNAPSHOT_EQUALITY
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
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "scripts" / "data")):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.data.quarantine_store import QuarantineStore, QuarantineCorrupt  # noqa: E402

REAL_QUAR = Path(r"C:\Users\kenan\WorkBuddy\2026-10-18-16-52-12\asip5\quarantine_snapshot.json")


def _rh(it):
    return hashlib.sha256(json.dumps(it, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _mk(root, n=40, max_shard=2048):
    root = Path(root)
    (root / "data" / "canonical").mkdir(parents=True, exist_ok=True)
    items = [{"quarantine_id": "Q_%03d" % i, "original_object_type": "article",
              "original_id": "https://ex.com/%d" % i, "reason_code": "other",
              "detected_at": "2026-10-%02dT00:00:00Z" % ((i % 28) + 1),
              "legacy_payload": {"p": "x" * (30 + i)}} for i in range(n)]
    (root / "data" / "canonical" / "quarantine.json").write_text(
        json.dumps({"schema_version": "2.0", "items": items}, ensure_ascii=False), encoding="utf-8")
    return QuarantineStore(root=root, max_shard_bytes=max_shard), items


class TestIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="asip5_r1c_")
        self.store, self.items = _mk(self.tmp)
        self.store.migrate(dry_run=False)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _p(self, *parts):
        return self.store.shard_dir.joinpath(*parts)

    def test_index_json_corrupt(self):
        self._p("index.json").write_text("{ broken", encoding="utf-8")
        with self.assertRaises(QuarantineCorrupt):
            self.store.mode()
        with self.assertRaises(QuarantineCorrupt):
            self.store.load_items()

    def test_ids_json_corrupt(self):
        self._p("ids.json").write_text("[1,2,3]", encoding="utf-8")
        with self.assertRaises(QuarantineCorrupt):
            self.store.read_ids()
        with self.assertRaises(QuarantineCorrupt):
            self.store.verify_consistency()

    def test_manifest_missing_but_shards_remain(self):
        self.store.manifest_path.unlink()
        with self.assertRaises(QuarantineCorrupt) as ctx:
            self.store.mode()
        self.assertIn("without manifest", str(ctx.exception))
        with self.assertRaises(QuarantineCorrupt):
            self.store.load_items()

    def test_manifest_schema_error(self):
        doc = json.loads(self.store.manifest_path.read_text(encoding="utf-8"))
        doc["schema"] = "bogus-v0"
        self.store.manifest_path.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaises(QuarantineCorrupt):
            self.store.mode()

    def test_sha_mismatch_blocks_readers(self):
        idx = self.store.read_index()
        victim = idx["shards"][0]["shard"]
        p = self._p(victim)
        raw = json.loads(p.read_text(encoding="utf-8"))
        raw["items"][0]["reason_code"] = "tampered"
        p.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
        with self.assertRaises(QuarantineCorrupt):
            self.store.load_items()             # 默认校验 sha256
        with self.assertRaises(QuarantineCorrupt):
            list(self.store.iter_items())
        with self.assertRaises(QuarantineCorrupt):
            self.store.verify_consistency()

    def test_consistency_detects_id_set_mismatch(self):
        ids = self.store.read_ids()
        ids.pop(sorted(ids)[0])
        self._p("ids.json").write_text(json.dumps(ids), encoding="utf-8")
        with self.assertRaises(QuarantineCorrupt) as ctx:
            self.store.verify_consistency()
        self.assertIn("ids mapping mismatch", str(ctx.exception))

    def test_consistency_detects_month_mismatch(self):
        ids = self.store.read_ids()
        k = sorted(ids)[0]
        ids[k] = "2026-01"
        self._p("ids.json").write_text(json.dumps(ids), encoding="utf-8")
        with self.assertRaises(QuarantineCorrupt) as ctx:
            self.store.verify_consistency()
        self.assertIn("month mismatch", str(ctx.exception))

    def test_consistency_detects_manifest_total_mismatch(self):
        doc = json.loads(self.store.manifest_path.read_text(encoding="utf-8"))
        doc["total_items"] = 1
        self.store.manifest_path.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaises(QuarantineCorrupt):
            self.store.verify_consistency()

    def test_remigrate_refused(self):
        rep = self.store.migrate(dry_run=False)
        self.assertTrue(rep.get("refused"))
        self.assertEqual(rep["total_items"], len(self.items))
        self.assertEqual(len(self.store.load_items()), len(self.items))

    def test_remigrate_cannot_drop_increments(self):
        self.store.upsert([{"quarantine_id": "Q_inc", "original_object_type": "event",
                            "original_id": "https://ex.com/inc", "reason_code": "other",
                            "detected_at": "2026-11-01T00:00:00Z"}])
        # 旧单体仍是迁移前快照（少一条）→ 再次迁移会丢增量 → 必须拒绝
        with self.assertRaises(QuarantineCorrupt) as ctx:
            self.store.migrate(dry_run=False, allow_remigrate=True)
        self.assertIn("would lose increments", str(ctx.exception))
        self.assertEqual(len(self.store.load_items()), len(self.items) + 1)


class TestRetireMonolith(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="asip5_retire_"))
        self.store, self.items = _mk(self.tmp)
        self.store.migrate(dry_run=False)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_retire_replaces_oversize_with_tombstone(self):
        pre_bytes = self.store.legacy.stat().st_size
        rep = self.store.retire_monolith(backup_dir=self.tmp / "backup", expect_items=len(self.items))
        self.assertTrue(rep["ok"])
        self.assertLess(rep["tombstone_bytes"], 4096, "墓碑必须远小于 100MB")
        self.assertLess(self.store.legacy.stat().st_size, 4096)
        tomb = json.loads(self.store.legacy.read_text(encoding="utf-8"))
        self.assertTrue(tomb["retired"])
        self.assertEqual(tomb["items"], [])
        self.assertEqual(tomb["pre_migration"]["bytes"], pre_bytes)
        self.assertEqual(tomb["total_items"], len(self.items))
        # 数据仍在分片中，且一致性不变
        self.assertEqual(len(self.store.load_items()), len(self.items))
        self.assertTrue(self.store.verify_consistency()["consistent"])
        # 预期树：全部文件远低于 100MB
        tree = self.store.expected_tree()
        self.assertTrue(tree["all_below_hard_limit"])
        self.assertLess(tree["max_bytes"], 100 * 1024 * 1024)

    def test_backup_hash_and_restore_path(self):
        rep = self.store.retire_monolith(backup_dir=self.tmp / "backup",
                                         expect_items=len(self.items))
        bk = rep["backup"]
        self.assertTrue(bk["ok"])
        p = Path(bk["path"])
        self.assertTrue(p.exists())
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), bk["sha256"])
        self.assertEqual(len(json.loads(p.read_text(encoding="utf-8"))["items"]), len(self.items))

    def test_rollback_after_retire(self):
        self.store.upsert([{"quarantine_id": "Q_after", "original_object_type": "event",
                            "original_id": "https://ex.com/after", "reason_code": "other",
                            "detected_at": "2026-11-01T00:00:00Z"}])
        self.store.retire_monolith(backup_dir=self.tmp / "backup")
        rb = self.store.rollback_to_monolith(expect_items=len(self.items) + 1)
        self.assertEqual(rb["restored_items"], len(self.items) + 1)
        ids = {i["quarantine_id"] for i in self.store.load_items()}
        self.assertIn("Q_after", ids, "退役后回滚仍必须保留增量")

    def test_retire_requires_sharded(self):
        st2, _ = _mk(self.tmp / "legacy_only")
        with self.assertRaises(QuarantineCorrupt):
            st2.retire_monolith()


@unittest.skipUnless(REAL_QUAR.exists(), "需要真实隔离快照")
class TestRealRetire(unittest.TestCase):
    def test_real_20461_retire_and_equality(self):
        tmp = Path(tempfile.mkdtemp(prefix="asip5_real3_"))
        try:
            (tmp / "data" / "canonical").mkdir(parents=True)
            shutil.copy2(REAL_QUAR, tmp / "data" / "canonical" / "quarantine.json")
            items = json.loads(REAL_QUAR.read_text(encoding="utf-8"))["items"]
            self.assertEqual(len(items), 20461)
            pre_bytes = (tmp / "data" / "canonical" / "quarantine.json").stat().st_size
            self.assertEqual(pre_bytes, 104825716)
            st = QuarantineStore(root=tmp, max_shard_bytes=20 * 1024 * 1024)
            rep = st.migrate(dry_run=False)
            self.assertEqual(rep["total_items"], 20461)
            self.assertEqual(rep["written_shards"], 9)
            cons = st.verify_consistency()
            self.assertTrue(cons["consistent"])
            retire = st.retire_monolith(backup_dir=tmp / "backup", expect_items=20461)
            self.assertTrue(retire["ok"])
            self.assertLess(retire["tombstone_bytes"], 4096)
            # 逐条哈希与 ID 集合
            after = st.load_items()
            self.assertEqual({i["quarantine_id"]: _rh(i) for i in items},
                             {i["quarantine_id"]: _rh(i) for i in after})
            # 分片上限
            idx = st.read_index()
            self.assertLessEqual(max(s["bytes"] for s in idx["shards"]), 20 * 1024 * 1024)
            # 单体已退役且不再超限
            self.assertLess(st.legacy.stat().st_size, 4096)
            # 演练：迁移后新增 → 回滚/前向恢复
            st.upsert([{"quarantine_id": "Q_drill", "original_object_type": "event",
                        "original_id": "https://ex.com/drill", "reason_code": "other",
                        "detected_at": "2026-11-02T00:00:00Z"}], run_id="drill")
            rb = st.rollback_to_monolith(expect_items=20462)
            self.assertEqual(rb["restored_items"], 20462)
            self.assertTrue(any(i["quarantine_id"] == "Q_drill" for i in st.load_items()))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
