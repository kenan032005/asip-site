#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1 — quarantine 双格式存储验收测试（离线、无网络、无付费调用）。

覆盖任务书第三部分的五个必交结论：
  SOURCE_RECORD_EQUALITY / QUARANTINE_READ_WRITE_COMPATIBILITY /
  LEGACY_FORMAT_COMPATIBILITY / SHARD_ROLLOVER / ROLLBACK_TEST
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "scripts" / "data")):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.data.quarantine_store import (  # noqa: E402
    QuarantineStore, QuarantineCorrupt, _sha256,
)


def _rec_hash(it):
    return hashlib.sha256(json.dumps(it, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _mk_repo(tmp, n=60, months=("2026-09", "2026-10")):
    """构造临时"仓库"：data/canonical/quarantine.json（旧单体）。"""
    root = Path(tmp)
    (root / "data" / "canonical").mkdir(parents=True, exist_ok=True)
    items = []
    for i in range(n):
        m = months[i % len(months)]
        day = (i % 28) + 1
        items.append({
            "quarantine_id": "Q_%04d" % i,
            "original_object_type": "event",
            "original_id": "https://example.com/a%d" % i,
            "reason_code": ["other", "not_security_relevant", "wrong_country"][i % 3],
            "reason_cn": "测试",
            "detected_at": "%s-%02dT10:00:00Z" % (m, day),
            "legacy_payload": {"payload": "x" * (200 + i)},
        })
    (root / "data" / "canonical" / "quarantine.json").write_text(
        json.dumps({"schema_version": "2.0", "pipeline_version": 2, "run_id": "R0",
                    "updated_at": "2026-10-01T00:00:00Z", "items": items},
                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return root, items


class TestQuarantineStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="asip5_qs_")
        self.root, self.items = _mk_repo(self.tmp)
        self.store = QuarantineStore(root=self.root, max_shard_bytes=4096)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ── LEGACY_FORMAT_COMPATIBILITY ───────────────────────────────
    def test_legacy_monolith_readable(self):
        self.assertFalse(self.store.is_sharded())
        loaded = self.store.load_items()
        self.assertEqual(len(loaded), len(self.items))
        self.assertEqual({i["quarantine_id"] for i in loaded},
                         {i["quarantine_id"] for i in self.items})
        # url_map 语义与旧实现一致（排除三类原因）
        um = self.store.url_map()
        excluded = {"not_security_relevant", "wrong_country", ""}
        expect = {i["original_id"]: i["quarantine_id"] for i in self.items
                  if i["reason_code"] not in excluded}
        self.assertEqual(um, expect)

    # ── SOURCE_RECORD_EQUALITY ────────────────────────────────────
    def test_migration_record_equality(self):
        plan = self.store.migrate(dry_run=True)
        self.assertEqual(plan["source_items"], len(self.items))
        self.assertFalse(plan["destructive"])
        rep = self.store.migrate(dry_run=False)
        self.assertEqual(rep["total_items"], len(self.items))
        self.assertTrue(self.store.is_sharded())
        merged = self.store.load_items(verify_checksums=True)
        self.assertEqual(len(merged), len(self.items))
        a = {i["quarantine_id"]: _rec_hash(i) for i in self.items}
        b = {i["quarantine_id"]: _rec_hash(i) for i in merged}
        self.assertEqual(a, b, "迁移前后逐条内容必须完全一致")
        v = self.store.verify(expect_items=len(self.items))
        self.assertTrue(v["count_match"])
        self.assertEqual(v["duplicate_ids"], 0)
        self.assertTrue(v["checksums_ok"])

    # ── SHARD_ROLLOVER ───────────────────────────────────────────
    def test_shard_rollover_respects_limit(self):
        rep = self.store.migrate(dry_run=False, max_shard_bytes=4096)
        idx = json.loads((self.root / "data" / "canonical" / "quarantine" / "index.json")
                         .read_text(encoding="utf-8"))
        self.assertGreater(len(idx["shards"]), 2, "应产生多个分片")
        self.assertLessEqual(max(s["bytes"] for s in idx["shards"]), 4096 + 1024,
                             "单片不得超过上限（含单条超限的边界容忍）")
        names = [s["shard"] for s in idx["shards"]]
        self.assertTrue(any("-part2" in n for n in names), "应出现 partN 滚动")

    # ── READ_WRITE_COMPATIBILITY ─────────────────────────────────
    def test_upsert_add_skip_modify_and_late_arrival(self):
        self.store.migrate(dry_run=False, max_shard_bytes=4096)
        # 新增
        new_item = {"quarantine_id": "Q_new", "original_object_type": "event",
                    "original_id": "https://example.com/new", "reason_code": "other",
                    "detected_at": "2026-10-28T00:00:00Z", "legacy_payload": {}}
        r1 = self.store.upsert([new_item], run_id="R1")
        self.assertEqual((r1["added"], r1["modified"], r1["skipped"]), (1, 0, 0))
        # 重复（内容一致 → skipped）
        r2 = self.store.upsert([new_item], run_id="R2")
        self.assertEqual((r2["added"], r2["modified"], r2["skipped"]), (0, 0, 1))
        # 修改（review_status 变化 → modified，且只重写所属分片）
        changed = dict(new_item)
        changed["review_status"] = "released"
        r3 = self.store.upsert([changed], run_id="R3")
        self.assertEqual((r3["added"], r3["modified"]), (0, 1))
        got = [i for i in self.store.load_items() if i["quarantine_id"] == "Q_new"][0]
        self.assertEqual(got["review_status"], "released")
        # 跨月晚到：条目 detected_at 属于 8 月，但 8 月无分片 → 新建 8 月分片
        late = {"quarantine_id": "Q_late", "original_object_type": "event",
                "original_id": "https://example.com/late", "reason_code": "other",
                "detected_at": "2026-08-15T00:00:00Z", "legacy_payload": {}}
        r4 = self.store.upsert([late], run_id="R4")
        self.assertEqual(r4["added"], 1)
        months = {s["month"] for s in self.store.read_index()["shards"]}
        self.assertIn("2026-08", months, "晚到条目必须落到其所属月份分片")
        self.assertEqual(len(self.store.load_items()), len(self.items) + 2)

    def test_interrupted_write_and_corruption_detection(self):
        self.store.migrate(dry_run=False, max_shard_bytes=4096)
        shard_dir = self.root / "data" / "canonical" / "quarantine"
        # 孤儿 .tmp：读取时应清理，不影响结果
        (shard_dir / "2026-10.json.tmp").write_text("{ broken", encoding="utf-8")
        self.assertEqual(len(self.store.load_items()), len(self.items))
        self.assertFalse((shard_dir / "2026-10.json.tmp").exists())
        # 篡改分片：校验必须失败（fail-closed，不得静默跳过）
        first = sorted(shard_dir.glob("2026-09*.json"))[0]
        first.write_text('{"items": []}', encoding="utf-8")
        with self.assertRaises(QuarantineCorrupt):
            self.store.load_items(verify_checksums=True)

    # ── ROLLBACK_TEST ────────────────────────────────────────────
    def test_rollback_to_legacy_still_readable(self):
        self.store.migrate(dry_run=False, max_shard_bytes=4096)
        self.assertTrue(self.store.is_sharded())
        # 模拟 git revert：移除 manifest + 分片目录 → 自动回退旧单体
        (self.root / "data" / "canonical" / "quarantine_manifest.json").unlink()
        import shutil
        shutil.rmtree(self.root / "data" / "canonical" / "quarantine")
        self.assertFalse(self.store.is_sharded())
        loaded = self.store.load_items()
        self.assertEqual(len(loaded), len(self.items), "回滚后旧单体必须完整可读")
        hint = self.store.rollback_hint()
        self.assertEqual(hint["data_loss"], "none（迁移不删除记录；revert 恢复旧单体）")

    def test_plain_append_without_migration_stays_legacy(self):
        r = self.store.upsert([{"quarantine_id": "Q_x", "original_object_type": "event",
                                "original_id": "https://example.com/x", "reason_code": "other",
                                "detected_at": "2026-10-30T00:00:00Z"}], run_id="R9")
        self.assertEqual(r["mode"], "legacy")
        self.assertEqual(len(self.store.load_items()), len(self.items) + 1)


@unittest.skipUnless(os.environ.get("ASIP5_REAL_SNAPSHOT"),
                     "设置 ASIP5_REAL_SNAPSHOT=<path> 才跑真实 20,461 条数据比对")
class TestRealSnapshot(unittest.TestCase):
    def test_real_data_migration(self):
        src = Path(os.environ["ASIP5_REAL_SNAPSHOT"])
        tmp = tempfile.mkdtemp(prefix="asip5_real_")
        root = Path(tmp)
        (root / "data" / "canonical").mkdir(parents=True)
        (root / "data" / "canonical" / "quarantine.json").write_bytes(src.read_bytes())
        items = json.loads(src.read_text(encoding="utf-8"))["items"]
        store = QuarantineStore(root=root, max_shard_bytes=20 * 1024 * 1024)
        rep = store.migrate(dry_run=False)
        merged = store.load_items(verify_checksums=True)
        self.assertEqual(rep["total_items"], len(items))
        self.assertEqual({i["quarantine_id"]: _rec_hash(i) for i in items},
                         {i["quarantine_id"]: _rec_hash(i) for i in merged})
        idx = store.read_index()
        self.assertLessEqual(max(s["bytes"] for s in idx["shards"]), 20 * 1024 * 1024 + 4096)
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
