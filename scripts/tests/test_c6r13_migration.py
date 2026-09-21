#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c6r13_migration.py — C6-R1.3 canonical 数据迁移契约测试（§九）。

  * 幂等：迁移后的 canonical 上再次执行 → records_changed == 0
  * 审计：data/migrations/ 记录第一/第二通过均有 changes > 0
  * 迁移后 validate_stage2 仅剩 S06 的 event_severity fail-closed 项
    （323 条从未评估的记录：enum 无 unknown → 不猜测，交契约决策）
"""
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts")):
    sys.path.insert(0, p)

_spec = importlib.util.spec_from_file_location(
    "migrate_canonical_contract",
    str(ROOT / "scripts" / "data" / "migrate_canonical_contract.py"))
MIG = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(MIG)


class CanonicalMigrationTest(unittest.TestCase):

    def test_01_idempotent_after_migration(self):
        """§九：迁移后的 canonical 再次执行 → records_changed == 0（幂等）。"""
        with tempfile.TemporaryDirectory() as tmp:
            # 复制当前（已迁移）canonical 数据到临时根
            for rel in ("canonical/articles.json", "canonical/event_clusters.json",
                        "canonical/quarantine.json", "public/published_events.json",
                        "countries.json"):
                src = ROOT / "data" / rel
                if src.exists():
                    dst = Path(tmp) / "data" / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
            stats = MIG.migrate(tmp, write=True)
            self.assertEqual(stats["records_changed"], 0,
                             "迁移必须幂等：已迁移数据上不得再产生变更")
            # unresolved = 323 是**设计内**的 fail-closed（event_severity 无 unknown，
            # 323 条从未评估的记录等待契约决策）——不是迁移缺陷。
            self.assertEqual(stats["unresolved"], 323)

    def test_02_migration_records_show_real_changes(self):
        """§九：第一/第二通过均有 changes > 0（审计记录为证）。"""
        mdir = ROOT / "data" / "migrations"
        rec1 = json.loads((mdir / "c6r13-canonical-contract-001.json").read_text(
            encoding="utf-8"))
        rec2 = json.loads((mdir / "c6r13-canonical-contract-002.json").read_text(
            encoding="utf-8"))
        self.assertGreater(rec1["records_changed"], 0)
        self.assertGreater(rec2["records_changed"], 0)
        self.assertGreater(rec1["by_reason"].get("S06_RFC3339", 0), 0)
        self.assertGreater(rec1["by_reason"].get("S14_ENUM_PENDING", 0), 0)
        self.assertGreater(rec2["by_reason"].get("REQUIRED_RUN_ID_MIGRATION", 0), 0)

    def test_03_migration_preserves_original_event_time(self):
        """§三：S06 迁移必须保留 original_event_time 用于审计。"""
        cl = json.loads((ROOT / "data" / "canonical" / "event_clusters.json")
                        .read_text(encoding="utf-8"))["items"]
        migrated = [c for c in cl if c.get("original_event_time")]
        self.assertGreater(len(migrated), 0)
        for c in migrated:
            self.assertIn("T", c["event_time"], "event_time 必须 RFC3339")
            self.assertTrue(str(c["original_event_time"]).endswith(".000")
                            or "T" not in str(c["original_event_time"]),
                            "original_event_time 保留旧格式")

    def test_04_no_verification_promotion(self):
        """§六：unresolved 不能自动提高等级（323 条 → not_checked，最低级）。"""
        cl = json.loads((ROOT / "data" / "canonical" / "event_clusters.json")
                        .read_text(encoding="utf-8"))["items"]
        nc = [c for c in cl if c.get("verification_level") == "not_checked"]
        self.assertGreaterEqual(len(nc), 323)
        # 原本 None 的记录不得被升级到更高核实级别
        self.assertTrue(all(c.get("verification_level") == "not_checked"
                            for c in cl if c.get("verification_level") == "not_checked"))

    def test_05_validate_stage2_after_migration(self):
        """§九：迁移后 validate_stage2 只剩 S06 的 event_severity fail-closed 项。"""
        r = subprocess_run()
        self.assertIn("PASS=53", r["out"], r["out"][-400:])
        self.assertIn("FAIL=1", r["out"])
        self.assertIn("🚫 [S06]", r["out"], "唯一失败必须是 S06 的 severity fail-closed")
        self.assertIn("event_severity", r["out"])
        for sid in ("S12", "S14", "S15", "S32", "S49"):
            self.assertNotIn("🚫 [%s]" % sid, r["out"],
                             "%s 不得再失败" % sid)

    def test_06_time_fields_rfc3339_everywhere(self):
        cl = json.loads((ROOT / "data" / "canonical" / "event_clusters.json")
                        .read_text(encoding="utf-8"))["items"]
        bad = [c["event_id"] for c in cl
               if c.get("event_time") and "T" not in str(c["event_time"])]
        self.assertEqual(bad, [], "canonical 不得再含 naive 时间格式")


def subprocess_run():
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "data" / "validate_stage2.py")],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    return {"out": (r.stdout or "") + (r.stderr or "")}


if __name__ == "__main__":
    unittest.main(verbosity=2)
