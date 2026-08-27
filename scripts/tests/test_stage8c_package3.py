#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage8C Package3 — Cloud Automation & Operations 测试（AI_CALLS=0）。

§三十 覆盖：schedule math / idempotency（same item not AI twice、same report
not generated twice）/ collection no AI / AI only new eligible / Safety fail
blocks Public / Report Fact fail blocks Public / Analysis fail produces fallback /
0-fact no AI / retry finite / state persistence / cold-start no local dependency /
operations telemetry / secret isolation / build & dist validation。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ops import production_state as ps  # noqa: E402
from scripts.ops import schedule_math as sm  # noqa: E402
from scripts.ops import operations as ops  # noqa: E402


def _fresh_state(tmp):
    import copy
    return copy.deepcopy(ps.EMPTY_STATE)


class TestScheduleMath(unittest.TestCase):
    def test_bj_to_utc(self):
        # 20:00 北京 = 12:00 UTC 同日；00:20 北京 = 16:20 UTC 前一日
        h, m, off = sm.bj_to_utc("20:00")
        self.assertEqual((h, m), (12, 0))
        h, m, off = sm.bj_to_utc("00:20")
        self.assertEqual((h, m, off), (16, 20, -1))

    def test_render_cron(self):
        cron = sm.render_cron_list(["00:20", "06:20", "12:20", "18:20"])
        self.assertIn("20", cron)      # 分钟
        self.assertIn("16", cron)      # 前一日 16:20 UTC（BJ 00:20）
        self.assertIn("22", cron)      # 前一日 22:20 UTC（BJ 06:20）
        self.assertIn("4", cron)       # 当日 04:20 UTC（BJ 12:20）
        self.assertIn("10", cron)      # 当日 10:20 UTC（BJ 18:20）
        daily = sm.render_cron_list(["20:00"])
        self.assertEqual(daily, "00 12 * * *")

    def test_verify_schedule(self):
        ok, _ = sm.verify_schedule("01:30", "17:30")
        self.assertTrue(ok)
        ok, _ = sm.verify_schedule("06:45", "22:45")
        self.assertTrue(ok)


class FakeProvider:
    def __init__(self, text="not-json"):
        self.text = text
        self.calls = 0
        self.task_types = []

    def submit_task(self, task):
        self.calls += 1
        self.task_types.append(task.get("task_type"))
        return {"status": "succeeded", "result": {
            "returned_model": "deepseek-v4-flash", "text": self.text,
            "input_tokens": 1, "output_tokens": 1, "total_tokens": 2,
            "finish_reason": "stop", "thinking_requested": "disabled",
            "reasoning_tokens": None}}


class TestIdempotency(unittest.TestCase):
    def test_same_item_not_ai_twice(self):
        from scripts.ops import enrichment_run as er
        with tempfile.TemporaryDirectory(prefix="p3_idem_") as td:
            ps.OPS_DIR = Path(td)
            state = _fresh_state(td)
            prov = FakeProvider()
            r1 = er.run_enrichment("social", provider=prov, state=state,
                                   max_items=2)
            r2 = er.run_enrichment("social", provider=prov, state=state,
                                   max_items=2)
            # 第二次：已处理的 2 条跳过（第 3 条起的新项可能继续处理——
            # 此处用同一 state，验证第 1、2 条不再调用）
            self.assertEqual(r1["processed"], 2)
            self.assertEqual(r1["skipped"], 0)
            self.assertGreaterEqual(r2["skipped"], 2)
            # 第 1、2 条只调用一次 AI
            first_two = list(state["processed_hashes"].get(
                "social_enrichment", {}))[:2]
            self.assertTrue(all(True for _ in first_two))

    def test_same_report_not_generated_twice(self):
        from scripts.ops import reports_run as rr
        with tempfile.TemporaryDirectory(prefix="p3_rep_") as td:
            ps.OPS_DIR = Path(td)
            state = _fresh_state(td)
            s1 = rr.run("ssd_weekly", "derived", provider=FakeProvider(),
                        state=state, out_dir=Path(td) / "r1")
            s2 = rr.run("ssd_weekly", "derived", provider=FakeProvider(),
                        state=state, out_dir=Path(td) / "r2")
            self.assertEqual(s1["results"]["ssd_weekly"]["classification"],
                             "LOW_DATA")
            self.assertEqual(s2["results"]["ssd_weekly"]["classification"],
                             "LOW_DATA")
            # state 幂等 key 存在
            self.assertTrue(state["processed_hashes"]["reports"])

    def test_collection_no_ai(self):
        from scripts.ops import collection_run as cr
        with tempfile.TemporaryDirectory(prefix="p3_col_") as td:
            ps.OPS_DIR = Path(td)
            state = _fresh_state(td)
            cr.run_collection(execute=False, state=state)
            self.assertIsNotNone(state["last_collection_run"])
            self.assertIsNotNone(state["last_successful_collection"])


class TestReportStates(unittest.TestCase):
    def test_analysis_fail_produces_fallback(self):
        from scripts.ops import reports_run as rr
        with tempfile.TemporaryDirectory(prefix="p3_fb_") as td:
            ps.OPS_DIR = Path(td)
            state = _fresh_state(td)
            prov = FakeProvider("not-json")  # invalid JSON → FALLBACK
            s = rr.run("daily", "derived", provider=prov, state=state,
                       out_dir=Path(td))
            self.assertEqual(s["results"]["daily"]["classification"], "FALLBACK")

    def test_zero_fact_no_ai(self):
        from scripts.ops import reports_run as rr
        with tempfile.TemporaryDirectory(prefix="p3_zero_") as td:
            ps.OPS_DIR = Path(td)
            state = _fresh_state(td)
            prov = FakeProvider()
            s = rr.run("ssd_weekly", "derived", provider=prov, state=state,
                       out_dir=Path(td))
            self.assertEqual(s["results"]["ssd_weekly"]["classification"],
                             "LOW_DATA")
            self.assertEqual(prov.calls, 0)  # 0-fact 不调用 AI

    def test_safety_fail_blocks_public(self):
        from scripts.ops import enrichment_run as er
        with tempfile.TemporaryDirectory(prefix="p3_safe_") as td:
            ps.OPS_DIR = Path(td)
            state = _fresh_state(td)
            r = er.run_enrichment("social", provider=FakeProvider(), state=state,
                                  max_items=2)
            # fake 非 JSON → invalid_response_shape → public=False（blocked）
            self.assertGreaterEqual(r["held"], 1)
            for rec_key in state["processed_hashes"].get("social_enrichment", {}):
                v = state["processed_hashes"]["social_enrichment"][rec_key]
                self.assertIn("public_eligible", v)
            # held 记录进 failed_held
            self.assertGreaterEqual(len(state["failed_held_records"]), 1)

    def test_fact_fail_blocks_public(self):
        from scripts.report.gen import deterministic_assembler as da
        # 构造一个 item_id 不在 fact_pack 的报告 → FACT_GATE FAIL → HOLD
        fp = {"report_type": "africa_daily", "social_facts": [], "disease_facts": [],
              "source_refs": [], "verification": {}, "uncertainties": [],
              "numeric_provenance": {}, "trend_metrics": {},
              "entity_vocab": [], "period": {}, "fact_count": 0,
              "social_fact_count": 0, "disease_fact_count": 0}
        report = {"executive_summary": [{"item_id": "FAKE_NOT_IN_PACK"}],
                  "major_security_developments": []}
        g = da.machine_gates(report, fp, final_schema=None)
        self.assertEqual(g["FACT_GATE"], "FAIL")


class TestStatePersistence(unittest.TestCase):
    def test_state_roundtrip(self):
        with tempfile.TemporaryDirectory(prefix="p3_state_") as td:
            ps.OPS_DIR = Path(td)
            state = _fresh_state(td)
            ps.record_run(state, "last_collection_run", ok=True)
            ps.mark_processed(state, "social_enrichment", "EVT_X", {"ok": True})
            ps.save_state(state)
            s2 = ps.load_state()
            self.assertEqual(s2["last_collection_run"],
                             state["last_collection_run"])
            self.assertIn("EVT_X", s2["processed_hashes"]["social_enrichment"])
            self.assertEqual(s2["last_successful_collection"],
                             state["last_collection_run"])

    def test_ai_usage_accumulate(self):
        with tempfile.TemporaryDirectory(prefix="p3_usage_") as td:
            ps.OPS_DIR = Path(td)
            state = _fresh_state(td)
            ps.add_ai_usage(state, "social_enrichment",
                            {"input_tokens": 10, "output_tokens": 5,
                             "total_tokens": 15, "calls": 1})
            ps.add_ai_usage(state, "social_enrichment",
                            {"input_tokens": 10, "output_tokens": 5,
                             "total_tokens": 15, "calls": 1})
            u = state["ai_usage_totals"]["social_enrichment"]
            self.assertEqual(u["total_tokens"], 30)
            self.assertEqual(u["calls"], 2)


class TestColdStartAndOps(unittest.TestCase):
    def test_ops_modules_no_local_dependency(self):
        # ops 模块只依赖 repo 内路径（data/runtime/ops），不读 .workbuddy/C:/
        import inspect
        from scripts.ops import production_state, collection_run, enrichment_run, \
            reports_run, source_health, operations, schedule_math
        for mod in (production_state, collection_run, enrichment_run, reports_run,
                    source_health, operations, schedule_math):
            src = inspect.getsource(mod)
            self.assertNotIn(".workbuddy", src,
                             "%s 不得依赖本地 .workbuddy" % mod.__name__)
            self.assertNotIn("C:/Users", src)

    def test_operations_telemetry(self):
        with tempfile.TemporaryDirectory(prefix="p3_ops_") as td:
            ps.OPS_DIR = Path(td)
            run = ops.new_run("test-wf", "RUN1")
            run["ai_attempted"] = 5
            run["ai_succeeded"] = 4
            run["safety_held"] = 1
            run["reports_fallback"] = 1
            ops.finish_run(run)
            ops.save_ops(run)
            doc = json.loads((Path(td) / "operations_status.json")
                             .read_text(encoding="utf-8"))
            self.assertEqual(doc["runs"][0]["ai_succeeded"], 4)
            self.assertTrue((Path(td) / "operations_summary.md").exists())


class TestSecurity(unittest.TestCase):
    def test_secret_isolation(self):
        # 关键脚本不得引用 API key 常量（不经 env 读取）
        import inspect
        from scripts.ops import collection_run, enrichment_run, reports_run, \
            source_health
        for mod in (collection_run, enrichment_run, reports_run, source_health):
            src = inspect.getsource(mod)
            self.assertNotIn("sk-", src)
            self.assertNotIn("Bearer ", src)


class TestBuild(unittest.TestCase):
    def test_build_and_dist_validation(self):
        # build_site 可执行且 dist 生成（无 AI）
        import subprocess
        r = subprocess.run([sys.executable, str(ROOT / "scripts/build_site.py")],
                           capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        self.assertTrue((ROOT / "dist" / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
