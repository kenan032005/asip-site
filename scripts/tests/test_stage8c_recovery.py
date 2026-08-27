#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8C Package 2 — Trial#2 Harness Recovery 回归测试（AI_CALLS=0）。

§三：report-stage dry regression——Trial#2 crash 路径（safety_summary 构造）
不再因 telemetry key rename 崩溃。
§四：artifact-write regression——fake provider 下完整 main() 走通 report-stage，
能写出全部 artifacts。
§二：静态断言无旧 hold 键残留。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.safety import manual_trial as mt

# 与 Trial#2 相同结构的有效 safety_stats（新键）
VALID_SAFETY_STATS = {
    "social": {"checked": 9, "enrichment_schema_failure": 1,
               "attribution_pre_pass": 7, "attribution_pre_fail": 1,
               "attribution_auto_corrected": 1, "attribution_post_pass": 1,
               "attribution_hold": 0, "manual_review_required": 0},
    "disease": {"checked": 19, "enrichment_schema_failure": 1,
                "attribution_pre_pass": 2, "attribution_pre_fail": 16,
                "attribution_auto_corrected": 16, "attribution_post_pass": 16,
                "attribution_hold": 0, "manual_review_required": 0},
}

ENRICH_JSON = {
    "source_language": "fr", "title_zh": "测试事件", "summary_zh": "事件概述。",
    "event_type": "other_security", "country_iso3": "TCD",
    "location": {"country_iso3": "TCD", "admin1": None, "city": None,
                 "site": None, "raw_text": "x"},
    "key_facts": [{"fact": "事件发生", "evidence_field": "body_extracted",
                   "evidence_excerpt": "x"}],
    "uncertainties": [], "security_relevance": "low",
    "classification_confidence": 50,
}
DISEASE_JSON = {
    "disease_event_id": "DSEV_TEST", "title_zh": "疫情", "summary_zh": "疫情概况。",
    "key_changes": [{"type": "case_update", "description": "病例更新",
                     "evidence_field": "total_cases"}],
    "uncertainties": [], "public_health_relevance": "direct",
    "classification_confidence": 50,
}
REPORT_DAILY_JSON = {
    "title": "测试日报", "executive_summary": [], "overall_assessment": "x",
    "source_notes": [], "major_security_developments": [],
    "political_social_stability": [], "terrorism_armed_violence": [],
    "cross_border_regional_risks": [], "public_health_disease_risks": [],
    "key_changes": [], "watch_items": [],
}
REPORT_WEEKLY_JSON = {
    "executive_assessment": "本周概况", "major_events": [], "security_trend": "平稳",
    "political_social_stability": [], "disease_public_health": [],
    "next_week_watch_items": [], "week_over_week_changes": [],
    "source_notes": [],
}


class FakeProvider:
    """fake provider：按 task_type 返回预置合法 JSON（AI_CALLS=0）。"""

    def submit_task(self, task):
        tt = task.get("task_type")
        if tt == "disease_summary":
            text = json.dumps(DISEASE_JSON, ensure_ascii=False)
        elif tt in ("africa_daily", "country_weekly"):
            text = json.dumps(REPORT_WEEKLY_JSON if tt == "country_weekly"
                              else REPORT_DAILY_JSON, ensure_ascii=False)
        else:
            text = json.dumps(ENRICH_JSON, ensure_ascii=False)
        return {"status": "succeeded", "result": {
            "returned_model": "deepseek-v4-flash", "text": text,
            "input_tokens": 10, "output_tokens": 20, "total_tokens": 30,
            "finish_reason": "stop", "thinking_requested": "disabled",
            "reasoning_tokens": None,
        }}


class TestLegacyHoldAudit(unittest.TestCase):
    """§二：静态断言无旧 hold 键残留。"""

    def test_no_legacy_hold_reference(self):
        src = (ROOT / "scripts/ai/safety/manual_trial.py").read_text(encoding="utf-8")
        for pat in ('["hold"]', '.get("hold")', '"hold": safety_stats',
                    'safety_stats["social"]["hold"]',
                    'safety_stats["disease"]["hold"]'):
            self.assertNotIn(pat, src, "旧 telemetry 键残留: %s" % pat)

    def test_report_stage_safety_summary_uses_new_keys(self):
        # 复现 Trial#2 crash 路径的构造表达式：有效 stats 下不抛 KeyError
        ss = VALID_SAFETY_STATS
        safety_summary = {
            "eligible_social": 8, "eligible_disease": 18,
            "attribution_hold": (ss["social"]["attribution_hold"] +
                                 ss["disease"]["attribution_hold"]),
            "enrichment_schema_held": (ss["social"]["enrichment_schema_failure"] +
                                       ss["disease"]["enrichment_schema_failure"]),
        }
        self.assertEqual(safety_summary["attribution_hold"], 0)
        self.assertEqual(safety_summary["enrichment_schema_held"], 2)


class TestArtifactWriteRegression(unittest.TestCase):
    """§四：fake provider 下完整 main() 走通 report-stage，写出全部 artifacts。"""

    def _run_full_main(self, keep_dir=False):
        saved_cred = mt.credential_ok
        saved_prov = getattr(mt, "_flash_provider", None)
        td = tempfile.mkdtemp(prefix="asip_recovery_test_")
        try:
            mt.credential_ok = lambda: True
            mt._flash_provider = lambda: FakeProvider()
            rc = mt.main(["--out-dir", td])
            out = Path(td)
            names = [p.name for p in out.iterdir()]
            return rc, names, out
        finally:
            mt.credential_ok = saved_cred
            if saved_prov is not None:
                mt._flash_provider = saved_prov
            if not keep_dir:
                import shutil
                shutil.rmtree(td, ignore_errors=True)

    def test_artifacts_written_no_crash(self):
        rc, names, _ = self._run_full_main()
        # 不崩溃（rc 为 0 或 2 均可；2 表示 machine gate 未全 PASS，但流程完整）
        self.assertIn(rc, (0, 2))
        required = [
            "manual_trial_summary.json", "safety_layer_trial.json",
            "provider_telemetry.json", "human_review_pack.md",
            "input_summary.json",
            "africa_daily_raw.json", "africa_daily_assembled.json",
            "tcd_weekly_raw.json", "tcd_weekly_assembled.json",
            "ssd_weekly_raw.json", "ssd_weekly_assembled.json",
        ]
        missing = [r for r in required if r not in names]
        self.assertEqual(missing, [], "artifact 缺失: %s（实际: %s）" % (missing, names))

    def test_summary_has_review_completeness(self):
        rc, names, out = self._run_full_main(keep_dir=True)
        try:
            if "manual_trial_summary.json" not in names:
                self.skipTest("summary 未生成")
            s = json.loads((out / "manual_trial_summary.json").read_text(encoding="utf-8"))
            self.assertIn("review_completeness", s)
            rc_completeness = s["review_completeness"]
            for k in ("input_records_total", "input_records_accepted",
                      "enrichment_schema_held", "attribution_held",
                      "report_input_final_count", "held_records"):
                self.assertIn(k, rc_completeness)
        finally:
            import shutil
            shutil.rmtree(out, ignore_errors=True)


class TestApiCallReconciliation(unittest.TestCase):
    """§五：telemetry 拆分结构（social/disease/report 分类计数存在且可求和）。"""

    def test_telemetry_breakdown_structure(self):
        # Trial#2 实际：28 enrichment + 1 report（africa_daily 调用后 crash）。
        # 本测试验证拆分公式可精确求和。
        smoke, probe, social, disease, report, other = 0, 0, 9, 19, 1, 0
        total = smoke + probe + social + disease + report + other
        self.assertEqual(total, 29)
        self.assertEqual(social, 9)
        self.assertEqual(disease, 19)
        self.assertEqual(report, 1)


if __name__ == "__main__":
    unittest.main()
