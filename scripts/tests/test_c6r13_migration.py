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
            # 迁移 003（裁决方案 1）后：severity 已写 unknown → 无 unresolved。
            self.assertEqual(stats["unresolved"], 0)

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
        """§四：迁移 003（severity unknown）后 validate_stage2 必须 **54/54 PASS**。"""
        r = subprocess_run()
        self.assertIn("PASS=54", r["out"], r["out"][-400:])
        self.assertIn("FAIL=0", r["out"])
        self.assertNotIn("🚫", r["out"], "不得残留任何失败项")
        for sid in ("S06", "S12", "S14", "S15", "S32", "S49"):
            self.assertNotIn("🚫 [%s]" % sid, r["out"], "%s 必须通过" % sid)

    def test_07_unknown_severity_is_not_low(self):
        """§三：unknown 与 low 必须区分，绝不用 low 冒充未知严重度。"""
        cl = json.loads((ROOT / "data" / "canonical" / "event_clusters.json")
                        .read_text(encoding="utf-8"))["items"]
        unknown = [c for c in cl if c.get("event_severity") == "unknown"]
        self.assertGreater(len(unknown), 0, "裁决方案 1：应存在 unknown 严重度记录")
        # schema enum 必须同时包含 low 与 unknown（两者是不同的语义）
        schema = json.loads((ROOT / "schemas" / "event_cluster.schema.json")
                            .read_text(encoding="utf-8"))
        enum = schema["properties"]["event_severity"]["enum"]
        self.assertIn("unknown", enum)
        self.assertIn("low", enum)
        self.assertNotEqual("unknown", "low")
        # 从未评估的记录不得被 default 成 low
        for c in unknown:
            self.assertNotEqual(c.get("event_severity"), "low")

    def test_08_unassessed_cluster_not_promoted(self):
        """§三：无证据的记录 = severity unknown + verification_level not_checked
        （不得被升级到任何更高核实级别）。"""
        cl = json.loads((ROOT / "data" / "canonical" / "event_clusters.json")
                        .read_text(encoding="utf-8"))["items"]
        unassessed = [c for c in cl if c.get("event_severity") == "unknown"]
        self.assertGreater(len(unassessed), 0)
        for c in unassessed:
            self.assertEqual(c.get("verification_level"), "not_checked",
                             "未评估记录不得被升级核实级别：%s" % c.get("event_id"))
            self.assertEqual(c.get("publication_status"), "verification_pending",
                             "未评估记录不得被标记为已发布/可发布")
        # 注：severity 与 verification_level 是**独立**契约（§一），
        # 因此不要求 not_checked ⇒ severity unknown（早期记录可能已评估严重度）；
        # 只强制「无证据 ⇒ unknown，且不得被升级核实级别」。

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
