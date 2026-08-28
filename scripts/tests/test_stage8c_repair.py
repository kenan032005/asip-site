#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8C Package 2 Engineering Repair — 测试套件（AI_CALLS=0）。

§十四 覆盖：
  1. usage_purpose trial metadata regression（final schema const PASS）
  2. quality exception → FAIL，无 false PASS；malformed section → FAIL
  3. weekly section type contract（str[] → final schema FAIL）
  4. numeric provenance（nested facts / top-level metadata / date / year /
     event magnitude / identifier excluded）
  5. 12500 offline classification regression
  6. Safety：ID fields / source refs / enum / metadata immutable
  7. B2 仅作用于 user-facing natural language allowlist
  8. 无法确认 fact mapping → 不自动修
  9. 18 correction audit 可运行（Trial#1 artifacts 存在时）
  10. schema failure telemetry 与 safety HOLD 分离
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.safety import attribution_safety as saf
from scripts.ai.safety import manual_trial as mt
from scripts.ai.schema_validation import validate_against_schema
from scripts.report.gen.quality import run_quality_gate


class FakeProvider:
    """返回预置文本的 fake provider（测试用；AI_CALLS=0）。"""

    def __init__(self, text):
        self.text = text

    def submit_task(self, task):
        return {"status": "succeeded", "result": {
            "returned_model": "deepseek-v4-flash", "text": self.text,
            "input_tokens": 10, "output_tokens": 20, "total_tokens": 30,
            "finish_reason": "stop", "thinking_requested": "disabled",
            "reasoning_tokens": None,
        }}


class TestUsagePurpose(unittest.TestCase):
    """§一：usage_purpose 必须满足 final schema const（development_test）。"""

    def _run_report(self, ai_text, task_type, report_input, label):
        prov = FakeProvider(ai_text)
        tel = {}
        return mt.generate_report(prov, task_type, report_input,
                                  ROOT / "config/prompts/africa_daily_report_v1.md"
                                  if task_type == "africa_daily" else
                                  ROOT / "config/prompts/country_weekly_report_v1.md",
                                  label, tel)

    def test_daily_usage_purpose_const_passes(self):
        ri = json.loads((ROOT / "data/qualification/stage8b/daily/RD1.json")
                        .read_text(encoding="utf-8"))
        ai = {"title": "测试日报", "executive_summary": [], "overall_assessment": "x",
              "source_notes": [],
              "major_security_developments": [], "political_social_stability": [],
              "terrorism_armed_violence": [], "cross_border_regional_risks": [],
              "public_health_disease_risks": [], "key_changes": [], "watch_items": []}
        r = self._run_report(json.dumps(ai, ensure_ascii=False), "africa_daily", ri, "daily-t")
        # usage_purpose=development_test → final schema 的 const 通过
        ferr = [e for e in (r.get("final_schema_errors") or [])
                if "usage_purpose" in e]
        self.assertEqual(ferr, [], "usage_purpose const violation: %s" % ferr)
        self.assertIn("execution_mode", r)
        self.assertEqual(r["execution_mode"], "manual_human_review_trial")


class TestQualityFailClosed(unittest.TestCase):
    """§二：quality exception / malformed section → FAIL，绝不 false PASS。"""

    def test_malformed_section_no_crash(self):
        report = {"political_social_stability": ["字符串项"], "major_events": [],
                  "security_trend": "x", "executive_assessment": "y",
                  "disease_public_health": [], "report_id": "W1"}
        passed, status, issues, _ = run_quality_gate(
            report, {"sections": {}, "trend_metrics": {}}, "country_weekly")
        self.assertFalse(passed)
        self.assertIn("failed_quality_gate", status)
        self.assertTrue(any("malformed" in str(i) for i in issues))

    def test_weekly_str_array_schema_fail(self):
        # §三：str[] 违反 schema（$ref 修复后必须 FAIL）
        s = json.loads((ROOT / "schemas/country_weekly_report.schema.json")
                       .read_text(encoding="utf-8"))
        report = {"political_social_stability": ["x"], "major_events": [],
                  "security_trend": "t", "executive_assessment": "e",
                  "disease_public_health": [], "country_iso3": "TCD",
                  "report_type": "country_weekly", "report_id": "W1",
                  "week_start": "2026-08-01", "week_end": "2026-08-08",
                  "week_over_week_changes": [], "next_week_watch_items": [],
                  "generated_at": "t", "report_timezone": "z",
                  "generation_metadata": {"provider_name": "d", "model_name": "m",
                                          "prompt_version": "v",
                                          "usage_purpose": "development_test"},
                  "metrics": {}, "source_notes": []}
        errs = validate_against_schema(report, s, resolve_refs=True)
        self.assertTrue(any("expected type object, got string" in e for e in errs),
                        errs[:3])


class TestNumericProvenance(unittest.TestCase):
    """§四/§五：provenance-aware numeric gate。"""

    def test_metadata_date_numbers(self):
        ri = {"report_id": "W1", "report_type": "country_weekly",
              "country_iso3": "SSD", "week_start": "2026-07-25",
              "week_end": "2026-08-01",
              "sections": {"major_events": [], "weekly_executive_assessment": []},
              "trend_metrics": {}}
        report = {"executive_assessment": "本周（2026年7月25日至8月1日）数据有限。",
                  "security_trend": "x", "major_events": [],
                  "political_social_stability": []}
        ok, entries, unsupported = mt._numeric_provenance_check(report, ri)
        self.assertTrue(ok)
        for e in entries:
            self.assertEqual(e["semantic_type"], "metadata_date")

    def test_identifier_excluded(self):
        ri = {"report_id": "W1", "report_type": "country_weekly",
              "country_iso3": "TCD", "week_start": "2026-08-01",
              "week_end": "2026-08-08", "sections": {}, "trend_metrics": {}}
        report = {"major_events": [{"item_id": "E1", "headline_zh": "x",
                                    "fact_summary": "y", "assessment": "a",
                                    "outlook": "o", "verification_status": "v",
                                    "uncertainties": [], "source_refs": [],
                                    "country_iso3": "TCD"}]}
        ok, entries, unsupported = mt._numeric_provenance_check(report, ri)
        # item_id="E1" 的 1 属 identifier，不参与 → 无 unsupported
        self.assertTrue(ok)
        self.assertEqual([e["output_value"] for e in entries], [])

    def test_supported_input_number(self):
        ri = {"report_id": "W1", "report_type": "country_weekly",
              "country_iso3": "TCD", "week_start": "2026-08-01",
              "week_end": "2026-08-08",
              "sections": {"major_events": [{"event_id": "E1",
                                             "facts": [{"fact": "缴获302件武器"}],
                                             "body_extracted": "302件武器"}]},
              "trend_metrics": {}}
        report = {"major_events": [{"item_id": "M1", "headline_zh": "h",
                                    "fact_summary": "缴获302件武器",
                                    "assessment": "a", "outlook": "o",
                                    "verification_status": "v",
                                    "uncertainties": [], "source_refs": [],
                                    "country_iso3": "TCD"}]}
        ok, entries, unsupported = mt._numeric_provenance_check(report, ri)
        self.assertTrue(ok, unsupported)
        e302 = [e for e in entries if e["output_value"] == 302]
        self.assertTrue(e302)
        self.assertEqual(e302[0]["semantic_type"], "event_magnitude")
        self.assertIn("sections.major_events[0]", e302[0]["matched_input_path"])

    def test_unsupported_number_detected(self):
        ri = {"report_id": "W1", "report_type": "country_weekly",
              "country_iso3": "TCD", "week_start": "2026-08-01",
              "week_end": "2026-08-08", "sections": {}, "trend_metrics": {}}
        report = {"executive_assessment": "据报造成12500人伤亡。", "security_trend": "x",
                  "major_events": [], "political_social_stability": []}
        ok, entries, unsupported = mt._numeric_provenance_check(report, ri)
        self.assertFalse(ok)
        self.assertTrue(any(e["output_value"] == 12500 for e in unsupported))


class TestValue12500Regression(unittest.TestCase):
    """§六：12500 离线分类回归（daily input 中不存在 → TRUE_UNSUPPORTED）。"""

    def test_12500_classification(self):
        inputs = mt.build_inputs()
        from scripts.ai.safety.audit_trial1 import classify_value
        cls, path, sem = classify_value(12500, inputs["daily_input"])
        self.assertEqual(cls, "TRUE_UNSUPPORTED_AI_NUMBER")


class TestB2Boundary(unittest.TestCase):
    """§七/§八：B2 仅 user-facing allowlist + fact-aware。"""

    def test_id_field_immutable(self):
        inp = {"disease_event_id": "DSEV_20f86b15264c6d16",
               "confirmed_cases": 16, "title_original": "Yellow fever",
               "uncertainties": ["数字未核实"]}
        out = {"disease_event_id": "DSEV_20f86b15264c6d16",
               "title_zh": "非洲黄热病监测：16例确诊",
               "summary_zh": "报告16例确诊。",
               "key_changes": [{"type": "case_update", "description": "累计确诊16例",
                                "evidence_field": "confirmed_cases"}],
               "uncertainties": []}
        res = saf.run_attribution_safety(inp, out, "disease_summary")
        self.assertEqual(res["attribution_safety_gate"], "PASS")
        # disease_event_id 必须原样（不插入限定语）
        self.assertEqual(res["corrected_output"]["disease_event_id"],
                         "DSEV_20f86b15264c6d16")
        for c in res["corrections"]:
            self.assertNotEqual(c["field"], "disease_event_id")

    def test_b2_user_facing_only(self):
        inp = {"disease_event_id": "DSEV_X", "total_cases": 500,
               "uncertainties": ["媒体转述"]}
        out = {"disease_event_id": "DSEV_X", "title_zh": "疫情",
               "summary_zh": "累计500例。",
               "key_changes": [{"type": "case_update", "description": "累计500例",
                                "evidence_field": "total_cases"}],
               "uncertainties": []}
        res = saf.run_attribution_safety(inp, out, "disease_summary")
        for c in res["corrections"]:
            self.assertTrue(saf._leaf_is_user_facing(c["field"]),
                            "非 user-facing 字段被修正: %s" % c["field"])

    def test_cannot_map_fact_hold(self):
        # 输出数字在 input 无 unconfirmed 数字字段映射 → B2 不自动修
        inp = {"disease_event_id": "DSEV_Y", "confirmed_cases": None,
               "deaths": None, "total_cases": None, "uncertainties": []}
        out = {"disease_event_id": "DSEV_Y", "title_zh": "疫情",
               "summary_zh": "累计报告999例。", "key_changes": [], "uncertainties": []}
        res = saf.run_attribution_safety(inp, out, "disease_summary")
        # 数字 999 无 input 映射 → B2 不修；summary 无不确定词 → 事件级 B1 可修
        for c in res["corrections"]:
            self.assertNotEqual(c["rule_id"], "SAFETY-CORR-B2")


class TestTelemetrySeparation(unittest.TestCase):
    """§十：schema failure 与 safety hold 分离。"""

    def test_schema_failure_not_hold(self):
        from scripts.ai.safety.manual_trial import _tally
        s = {"checked": 0, "enrichment_schema_failure": 0, "attribution_pre_pass": 0,
             "attribution_pre_fail": 0, "attribution_auto_corrected": 0,
             "attribution_post_pass": 0, "attribution_hold": 0,
             "manual_review_required": 0}
        schema_held = []
        rec = {"status": "schema_failure", "schema_errors": ["x"], "country_code": "TD"}
        _tally(rec, "social", s, "EVT_1", schema_held)
        self.assertEqual(s["enrichment_schema_failure"], 1)
        self.assertEqual(s["attribution_hold"], 0)
        self.assertEqual(len(schema_held), 1)
        self.assertEqual(schema_held[0]["event_id"], "EVT_1")


class TestCorrectionAudit(unittest.TestCase):
    """§九：18 correction audit 可运行（Trial#1 artifacts 存在时）。"""

    def test_audit_runs(self):
        art = Path(r"C:/Users/kenan/WorkBuddy/2026-07-31-09-46-56/.workbuddy/tmp/trial_art")
        if not (art / "safety_layer_trial.json").exists():
            self.skipTest("Trial#1 artifacts 不在本地")
        import subprocess
        r = subprocess.run([sys.executable, str(ROOT / "scripts/ai/safety/audit_trial1.py")],
                           capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(r.returncode, 0, r.stderr[:300])
        out = json.loads((ROOT / "data/runtime/ai_safety/audit_trial1_report.json")
                         .read_text(encoding="utf-8"))
        summ = out["correction_audit_summary"]
        self.assertGreaterEqual(summ["total"], 18)
        # 修复后：仅历史 2 条 id 字段修正为 INVALID（新规则不再产生）
        for a in summ["invalid"]:
            self.assertIn("_id", a["field_path"])


if __name__ == "__main__":
    unittest.main()
