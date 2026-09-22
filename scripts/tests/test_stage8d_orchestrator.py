#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage8D schedule-fix tests: mode routing + due-task planner + idempotency."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ops import schedule_orchestrator as so  # noqa: E402
from scripts.ops.schedule_math import (  # noqa: E402
    SCHEDULES, render_cron_list, verify_schedule, verify_weekly_dow)

BJT = timezone(timedelta(hours=8))


def bjt(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=BJT)


def state(**kw):
    base = {
        "last_collection_run": None, "last_successful_collection": None,
        "last_ai_run": None, "last_successful_ai": None,
        "last_disease_run": None, "last_daily_report": None,
        "last_weekly_report": None, "last_deploy": None,
        "processed_hashes": {}, "failed_held_records": [],
    }
    base.update(kw)
    return base


class TestModeRouting(unittest.TestCase):
    def test_schedule_event_enters_production_mode(self):
        self.assertEqual(so.resolve_mode("schedule", {}), "production")

    def test_manual_shadow_remains_shadow(self):
        self.assertEqual(so.resolve_mode("workflow_dispatch", {}), "shadow")
        self.assertEqual(so.resolve_mode("workflow_dispatch", {"execute": "false"}), "shadow")
        self.assertEqual(so.resolve_mode("workflow_dispatch", {"run_ai": "false"}), "shadow")

    def test_manual_explicit_production(self):
        self.assertEqual(so.resolve_mode("workflow_dispatch", {"execute": "true"}), "production")
        self.assertEqual(so.resolve_mode("workflow_dispatch", {"run_ai": "true"}), "production")
        self.assertEqual(so.resolve_mode("workflow_dispatch", {"source": "production"}), "production")

    def test_production_schedule_enabled_false_blocks(self):
        p = so.plan_due_tasks(state(), now_bjt=bjt(2026, 8, 29, 21, 0),
                              schedule_enabled=False)
        self.assertFalse(p["enabled"])
        self.assertEqual(p["due"], [])


class TestDuePlanner(unittest.TestCase):
    def test_collection_due_when_never_run(self):
        p = so.plan_due_tasks(state(), now_bjt=bjt(2026, 8, 29, 3, 0))
        self.assertIn("collection", [t["task"] for t in p["due"]])

    def test_collection_not_due_within_gap(self):
        # now = 03:00 BJT = 19:00Z；上次成功在 13:30Z（BJT 21:30 前一日）→ 间隔 5h30m < 5h45m
        st = state(last_successful_collection="2026-08-28T13:30:00Z")
        p = so.plan_due_tasks(st, now_bjt=bjt(2026, 8, 29, 3, 0))
        self.assertNotIn("collection", [t["task"] for t in p["due"]])

    def test_collection_due_after_gap(self):
        # 上次成功 12:10Z（BJT 20:10 前一日）→ 间隔 6h50m ≥ 5h45m
        st = state(last_successful_collection="2026-08-28T12:10:00Z")
        p = so.plan_due_tasks(st, now_bjt=bjt(2026, 8, 29, 3, 0))
        self.assertIn("collection", [t["task"] for t in p["due"]])

    def test_disease_tick_route(self):
        # 未过 01:30 → 不 due
        p = so.plan_due_tasks(state(), now_bjt=bjt(2026, 8, 29, 1, 0))
        self.assertNotIn("disease_ai", [t["task"] for t in p["due"]])
        # 已过 01:30 且今天未跑 → due
        p = so.plan_due_tasks(state(), now_bjt=bjt(2026, 8, 29, 3, 0))
        self.assertIn("disease_ai", [t["task"] for t in p["due"]])
        # 今天已跑（UTC 18:00Z = BJT 次日 02:00）→ 不 due（BJT 日期相同）
        st = state(last_disease_run="2026-08-28T18:00:00Z")
        p = so.plan_due_tasks(st, now_bjt=bjt(2026, 8, 29, 3, 0))
        self.assertNotIn("disease_ai", [t["task"] for t in p["due"]])

    def test_daily_tick_route(self):
        # 未过 20:00 → 不 due
        p = so.plan_due_tasks(state(), now_bjt=bjt(2026, 8, 28, 19, 0))
        self.assertNotIn("daily_report", [t["task"] for t in p["due"]])
        # 已过 20:00 且今天未出 → due
        p = so.plan_due_tasks(state(), now_bjt=bjt(2026, 8, 28, 21, 0))
        self.assertIn("daily_report", [t["task"] for t in p["due"]])
        # 今天已出 → 不 due
        st = state(last_daily_report="2026-08-28T12:30:00Z")
        p = so.plan_due_tasks(st, now_bjt=bjt(2026, 8, 28, 21, 0))
        self.assertNotIn("daily_report", [t["task"] for t in p["due"]])

    def test_weekly_tick_route(self):
        # 周日 06:45 后且本周未出 → due；非周日不 due
        p = so.plan_due_tasks(state(), now_bjt=bjt(2026, 8, 30, 7, 0))  # 周日
        self.assertIn("weekly_report", [t["task"] for t in p["due"]])
        p = so.plan_due_tasks(state(), now_bjt=bjt(2026, 8, 28, 7, 0))  # 周五
        self.assertNotIn("weekly_report", [t["task"] for t in p["due"]])
        st = state(last_weekly_report="2026-08-29T22:50:00Z")  # 本周已出
        p = so.plan_due_tasks(st, now_bjt=bjt(2026, 8, 30, 7, 0))
        self.assertNotIn("weekly_report", [t["task"] for t in p["due"]])

    def test_no_duplicate_cycle_execution(self):
        st = state()
        p1 = so.plan_due_tasks(st, now_bjt=bjt(2026, 8, 29, 3, 0))
        p2 = so.plan_due_tasks(st, now_bjt=bjt(2026, 8, 29, 3, 0))
        self.assertEqual([t["task"] for t in p1["due"]],
                         [t["task"] for t in p2["due"]])
        # 标记 collection 成功并推进时间 → collection 不再重复
        st["last_successful_collection"] = "2026-08-28T20:10:00Z"
        p3 = so.plan_due_tasks(st, now_bjt=bjt(2026, 8, 29, 3, 0))
        self.assertNotIn("collection", [t["task"] for t in p3["due"]])


class TestNewEligible(unittest.TestCase):
    def _seed(self, kind, processed_ids=(), unprocessed_ids=()):
        tmp = Path(tempfile.mkdtemp(prefix="asip-orch-"))
        processed_ids = list(processed_ids)
        unprocessed_ids = list(unprocessed_ids)
        if kind == "social":
            sub = tmp / "canonical"
            sub.mkdir(parents=True, exist_ok=True)
            items = [{"event_id": i, "current_policy_passed": True}
                     for i in unprocessed_ids + processed_ids]
            (sub / "event_clusters.json").write_text(
                json.dumps({"items": items}), encoding="utf-8")
        else:
            sub = tmp / "disease" / "canonical"
            sub.mkdir(parents=True, exist_ok=True)
            items = [{"disease_event_id": i, "outbreak_status": "active"}
                     for i in unprocessed_ids + processed_ids]
            (sub / "outbreak_events.json").write_text(
                json.dumps({"items": items}), encoding="utf-8")
        return tmp

    def test_new_eligible_detected(self):
        tmp = self._seed("social", processed_ids=["A"], unprocessed_ids=["B"])
        st = state(processed_hashes={"social_enrichment": {"A": {"content_hash": "x"}}})
        self.assertTrue(so.new_eligible_exists(st, "social", tmp))

    def test_all_processed_returns_false(self):
        tmp = self._seed("social", processed_ids=["A"])
        st = state(processed_hashes={"social_enrichment": {"A": {"content_hash": "x"}}})
        self.assertFalse(so.new_eligible_exists(st, "social", tmp))

    def test_disease_new_eligible(self):
        tmp = self._seed("disease", unprocessed_ids=["D1"])
        st = state(processed_hashes={"disease_enrichment": {}})
        self.assertTrue(so.new_eligible_exists(st, "disease", tmp))


class TestViewsExportImport(unittest.TestCase):
    def test_export_import_path_resolves(self):
        """compatibility_export 的 scripts/ + scripts/data 双路径导入必须可解析。"""
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(root / "scripts"))
        sys.path.insert(0, str(root / "scripts" / "data"))
        from scripts.data.repository import Repository  # noqa: F401
        from scripts.data.compatibility_export import export_all  # noqa: F401
        import inspect
        sig = inspect.signature(export_all)
        self.assertIn("repo", sig.parameters)
        self.assertIn("run_id", sig.parameters)


class TestScheduleMath(unittest.TestCase):
    def test_bj_to_utc_conversions(self):
        cases = {"00:20": "16:20", "06:20": "22:20", "12:20": "04:20",
                 "18:20": "10:20", "00:30": "16:30", "20:00": "12:00",
                 "01:30": "17:30"}
        for bj, utc in cases.items():
            ok, _ = verify_schedule(bj, utc)
            self.assertTrue(ok, "%s -> %s" % (bj, utc))

    def test_render_cron_matches_remote(self):
        # 与远端 main 上实际 cron 逐一对照（小时列表顺序无关，按集合比较）
        def norm(cron):
            m, hrs = cron.split()[0], cron.split()[1]
            return (int(m), frozenset(hrs.split(",")))
        self.assertEqual(norm(render_cron_list(SCHEDULES["social_collection"])),
                         norm("20 16,22,4,10 * * *"))
        self.assertEqual(norm(render_cron_list(SCHEDULES["social_ai"])),
                         norm("30 16,22,4,10 * * *"))
        self.assertEqual(render_cron_list(SCHEDULES["disease_ai"]), "30 17 * * *")
        self.assertEqual(norm(render_cron_list(SCHEDULES["africa_daily"])),
                         norm("0 12 * * *"))

    def test_weekly_dow_roundtrip(self):
        ok, info = verify_weekly_dow(bj_dow_py=6, bj_hm="06:45", cron_dow=6)
        self.assertTrue(ok, info)
        self.assertEqual(info["utc_cron_dow"], 6)


if __name__ == "__main__":
    unittest.main()
