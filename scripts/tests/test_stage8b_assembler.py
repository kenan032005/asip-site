#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8B — Report Envelope Separation 测试（§十三）。

deterministic envelope / AI content schema / assembler / final schema /
metadata override 保护 / false-positive(exact_match=null) / max_tokens policy /
JSON truncation guard。
"""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.qualification import stage8b as q
from scripts.report.gen.assembler import assemble_report, ENVELOPE_FIELDS


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class TestEnvelopeSeparation(unittest.TestCase):
    """§一/§二：envelope 字段归属与 AI content schema。"""

    def test_envelope_fields_per_type(self):
        self.assertEqual(ENVELOPE_FIELDS["africa_daily"],
                         ["report_id", "report_type", "report_date", "period_start",
                          "period_end", "generated_at", "report_timezone",
                          "generation_metadata"])
        self.assertIn("week_start", ENVELOPE_FIELDS["country_weekly"])
        self.assertIn("event_time", ENVELOPE_FIELDS["major_event_brief"])

    def test_ai_content_schema_excludes_envelope(self):
        for tt, sch in (("africa_daily", "schemas/africa_daily_ai_content.schema.json"),
                        ("country_weekly", "schemas/country_weekly_ai_content.schema.json"),
                        ("major_event_brief", "schemas/major_event_brief_ai_content.schema.json")):
            s = load(sch)
            for f in ENVELOPE_FIELDS[tt]:
                self.assertNotIn(f, s.get("required", []))
                self.assertNotIn(f, s.get("properties", {}))

    def test_ai_content_schema_valid_content(self):
        from scripts.ai.schema_validation import validate_against_schema
        s = load("schemas/africa_daily_ai_content.schema.json")
        content = {"title": "非洲地区社会安全与综合形势日报",
                   "executive_summary": [{"item_id": "i1", "fact_summary": "事实"}],
                   "overall_assessment": "整体评估",
                   "source_notes": [{"source_id": "s1"}]}
        errs = validate_against_schema(content, s)
        self.assertEqual(errs, [])

    def test_ai_content_schema_missing_title(self):
        from scripts.ai.schema_validation import validate_against_schema
        s = load("schemas/africa_daily_ai_content.schema.json")
        errs = validate_against_schema({"executive_summary": []}, s)
        self.assertTrue(any("title" in e for e in errs))


class TestAssembler(unittest.TestCase):
    """§三/§四：merge + final schema + metadata 不可被 AI 覆盖。"""

    def test_assembler_merges_envelope(self):
        inp = {"report_id": "DAILY_X", "report_type": "africa_daily",
               "report_date": "2026-08-26",
               "period_start": "2026-08-25T15:00:08+08:00",
               "period_end": "2026-08-26T15:00:08+08:00", "generated_at": "t"}
        ai = {"title": "日报", "executive_summary": []}
        final = assemble_report("africa_daily", inp, ai)
        self.assertEqual(final["report_id"], "DAILY_X")
        self.assertEqual(final["period_start"], "2026-08-25T15:00:08+08:00")
        self.assertEqual(final["report_timezone"], "Asia/Shanghai")
        self.assertEqual(final["title"], "日报")

    def test_metadata_cannot_be_overridden_by_ai(self):
        """AI 恶意/错误返回 envelope 字段 → assembler 以 input 为准覆盖。"""
        inp = {"report_id": "DAILY_X", "report_type": "africa_daily",
               "report_date": "2026-08-26",
               "period_start": "2026-08-25T15:00:08+08:00",
               "period_end": "2026-08-26T15:00:08+08:00"}
        ai = {"title": "日报", "period_start": "2020-01-01T00:00:00+08:00",   # 错误
              "period_end": None, "report_id": "FAKE"}
        final = assemble_report("africa_daily", inp, ai)
        self.assertEqual(final["period_start"], "2026-08-25T15:00:08+08:00")
        self.assertEqual(final["period_end"], "2026-08-26T15:00:08+08:00")
        self.assertEqual(final["report_id"], "DAILY_X")

    def test_final_schema_valid_when_content_valid(self):
        from scripts.ai.schema_validation import validate_against_schema
        s = load("schemas/africa_daily_report.schema.json")
        inp = {"report_id": "DAILY_X", "report_type": "africa_daily",
               "report_date": "2026-08-26",
               "period_start": "2026-08-25T15:00:08+08:00",
               "period_end": "2026-08-26T15:00:08+08:00", "generated_at": "t"}
        ai = {"title": "日报",
              "executive_summary": [{"item_id": "i1", "fact_summary": "事实",
                                     "assessment": "判断", "outlook": "展望"}],
              "overall_assessment": "整体", "source_notes": [{"source_id": "s1"}]}
        final = assemble_report("africa_daily", inp, ai)
        errs = validate_against_schema(final, s)
        self.assertEqual(errs, [])

    def test_period_exact_on_assembled(self):
        inp = {"report_id": "DAILY_X", "report_type": "africa_daily",
               "report_date": "2026-08-26",
               "period_start": "2026-08-25T15:00:08+08:00",
               "period_end": "2026-08-26T15:00:08+08:00"}
        ai = {"title": "日报", "executive_summary": []}
        final = assemble_report("africa_daily", inp, ai)
        ok, errs = q.check_exact_copy(final, inp, "africa_daily")
        self.assertTrue(ok, errs)

    def test_weekly_assembler_metrics_from_input(self):
        inp = {"report_id": "W", "report_type": "country_weekly",
               "country_iso3": "TCD", "week_start": "2026-08-24",
               "week_end": "2026-08-30",
               "trend_metrics": {"event_count": 5}}
        ai = {"executive_assessment": "评估", "security_trend": "趋势",
              "week_over_week_changes": [], "next_week_watch_items": [],
              "source_notes": []}
        final = assemble_report("country_weekly", inp, ai)
        self.assertEqual(final["metrics"], {"event_count": 5})
        self.assertEqual(final["week_start"], "2026-08-24")


class TestProbeFalsePositive(unittest.TestCase):
    """§七：exact_match 未真实比较 → null（不得默认 true）。"""

    def test_probe_exact_match_null_on_failure(self):
        import scripts.ai.qualification.stage8b as qq
        qq.credential_available = lambda n: False
        rc = qq.run_report_probe("deepseek")
        self.assertEqual(rc, 1)
        res = json.loads((qq.ARTIFACT_DIR / "report_probe_result.json")
                         .read_text(encoding="utf-8"))
        self.assertIsNone(res.get("period_start_exact_match"))
        self.assertIsNone(res.get("period_end_exact_match"))


class TestMaxTokensPolicy(unittest.TestCase):
    """§八：per-task max_tokens + provider 请求携带。"""

    def test_policy_values(self):
        self.assertEqual(q.MAX_TOKEN_POLICY["africa_daily"], 4096)
        self.assertEqual(q.MAX_TOKEN_POLICY["country_weekly"], 3072)
        self.assertEqual(q.MAX_TOKEN_POLICY["major_event_brief"], 2048)
        self.assertEqual(q.MAX_TOKEN_POLICY["stage4_event_enrichment"], 2048)

    def test_task_builder_uses_policy(self):
        cases = {c["case_id"]: c for c in q.build_cases()}
        task = q._glm_task_builder(cases["RD1"])
        self.assertEqual(task["max_output_tokens"], 4096)
        task2 = q._glm_task_builder(cases["S1"])
        self.assertEqual(task2["max_output_tokens"], 2048)

    def test_provider_sends_max_tokens(self):
        from scripts.ai.providers import deepseek_v4_flash as ds
        captured = {}

        class FakeResp:
            status = 200

            def read(self):
                return json.dumps({
                    "model": "deepseek-v4-flash",
                    "choices": [{"message": {"content": '{"status":"ok"}'}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1,
                              "total_tokens": 2}}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout=180):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return FakeResp()

        p = ds.DeepSeekV4FlashProvider(api_key="test-key")
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            p.submit_task({"task_id": "T", "system_text": "s", "user_text": "u",
                           "task_type": "africa_daily", "max_output_tokens": 4096})
        self.assertEqual(captured["body"].get("max_tokens"), 4096)

    def test_truncation_guard_budget(self):
        # §九：budget 必须足够容纳典型完整 report（不低于合理下限）
        self.assertGreaterEqual(q.MAX_TOKEN_POLICY["africa_daily"], 4096)
        self.assertGreaterEqual(q.MAX_TOKEN_POLICY["country_weekly"], 3072)


if __name__ == "__main__":
    unittest.main()
