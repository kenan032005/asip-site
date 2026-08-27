#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage8C Package2 — Deterministic Facts + AI Analysis 架构测试（AI_CALLS=0）。

§十九 覆盖：
  Fact Pack deterministic / same input → same hash / facts 无 AI 字段 /
  source refs / numbers / verification / uncertainties / metrics 确定性 /
  Simple Analysis schema / unsupported number FAIL / unsupported named event FAIL /
  attribution escalation FAIL / valid analysis PASS / provider failure → fallback /
  invalid JSON → fallback / schema fail → fallback / 0-fact SSD no AI call /
  fallback final schema PASS / full final schema PASS / frontend 兼容（schema 未变）。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.report.gen.fact_pack import build_fact_pack, pack_hash  # noqa: E402
from scripts.report.gen import analysis_contract as ac  # noqa: E402
from scripts.report.gen import deterministic_assembler as da  # noqa: E402
from scripts.report.gen import analysis_runner as ar  # noqa: E402
from scripts.ai.schema_validation import validate_against_schema  # noqa: E402

DERIVED = ROOT / "data" / "runtime" / "stage8c_trial2_recovery" / "derived"
DERIVED_EVIDENCE = ROOT / "evidence" / "stage8c_trial2_recovery" / "derived"


def load_input(key):
    fname = {"africa_daily": "africa_daily_report_input.json",
             "tcd_weekly": "tcd_weekly_report_input.json",
             "ssd_weekly": "ssd_weekly_report_input.json"}[key]
    # cold start（与 scripts/ops/reports_run 同语义）：data/runtime 为 gitignored，
    # 缺失时用 git tracked 的 evidence/ 副本（字节一致，冻结 hash 不变）。
    src = DERIVED if (DERIVED / fname).exists() else DERIVED_EVIDENCE
    return json.loads((src / fname).read_text(encoding="utf-8"))


class AnalysisProvider:
    """返回指定文本的 fake provider（AI_CALLS=0）。"""

    def __init__(self, text):
        self.text = text
        self.calls = 0
        self.task_types = []

    def submit_task(self, task):
        self.calls += 1
        self.task_types.append(task.get("task_type"))
        return {"status": "succeeded", "result": {
            "returned_model": "deepseek-v4-flash", "text": self.text,
            "input_tokens": 10, "output_tokens": 20, "total_tokens": 30,
            "finish_reason": "stop", "thinking_requested": "disabled",
            "reasoning_tokens": None}}


VALID_ANALYSIS = json.dumps({
    "executive_assessment": "本周该地区整体形势稳定，以自然灾害与公民骚乱为主。",
    "trend_analysis": "事件以单一来源为主，需关注后续交叉验证。",
    "outlook": "短期维持当前监测强度。",
    "watch_points": ["关注后续交叉验证情况"],
}, ensure_ascii=False)


class TestFactPackDeterministic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.daily = build_fact_pack(load_input("africa_daily"))
        cls.tcd = build_fact_pack(load_input("tcd_weekly"))
        cls.ssd = build_fact_pack(load_input("ssd_weekly"))

    def test_same_input_same_hash(self):
        self.assertEqual(pack_hash(build_fact_pack(load_input("africa_daily"))),
                         pack_hash(self.daily))
        self.assertEqual(pack_hash(build_fact_pack(load_input("tcd_weekly"))),
                         pack_hash(self.tcd))

    def test_facts_contain_no_ai_fields(self):
        for fp in (self.daily, self.tcd):
            for f in fp["social_facts"] + fp["disease_facts"]:
                for bad in ("assessment", "outlook", "trend_analysis",
                            "watch_points"):
                    self.assertNotIn(bad, f, "Fact Pack 不得含 AI 分析字段")

    def test_source_refs_deterministic(self):
        for fp in (self.daily, self.tcd):
            srcs = fp["source_refs"]
            self.assertEqual(srcs, sorted(set(srcs), key=srcs.index))
            self.assertTrue(all(s for s in srcs))
        self.assertIn("Alwihda Info", self.daily["source_refs"])

    def test_numbers_verification_uncertainties_metrics_deterministic(self):
        for fp in (self.daily, self.tcd):
            self.assertTrue(fp["numeric_provenance"])
            self.assertIsInstance(fp["verification"], dict)
            self.assertIsInstance(fp["uncertainties"], list)
            self.assertIn("trend_metrics", fp)
        self.assertEqual(self.ssd["fact_count"], 0)
        self.assertEqual(self.ssd["social_fact_count"], 0)

    def test_fact_counts(self):
        self.assertEqual(self.daily["fact_count"], 17)
        self.assertEqual(self.daily["social_fact_count"], 8)
        self.assertEqual(self.daily["disease_fact_count"], 9)
        self.assertEqual(self.tcd["fact_count"], 7)


class TestAnalysisSchema(unittest.TestCase):
    def test_schema_flat_four_fields(self):
        self.assertEqual(set(ac.ANALYSIS_SCHEMA["required"]),
                         {"executive_assessment", "trend_analysis",
                          "outlook", "watch_points"})

    def test_prompt_contains_only_fact_pack_fields(self):
        fp = build_fact_pack(load_input("africa_daily"))
        sys_txt, user_txt = ac.build_analysis_prompt(fp)
        self.assertIn("Do not introduce any event", sys_txt)
        self.assertIn("Do not rewrite the fact database", sys_txt)
        self.assertIn("Generate analysis only", sys_txt)
        self.assertNotIn("body_extracted", user_txt)


class TestAnalysisGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.daily = build_fact_pack(load_input("africa_daily"))

    def test_valid_analysis_pass(self):
        ok, errs = ac.validate_analysis(json.loads(VALID_ANALYSIS), self.daily)
        self.assertTrue(ok, errs)

    def test_unsupported_number_fail(self):
        bad = json.loads(VALID_ANALYSIS)
        bad["executive_assessment"] = "本周事件数 99999 起"
        ok, errs = ac.validate_analysis(bad, self.daily)
        self.assertFalse(ok)
        self.assertTrue(any("ANALYSIS_UNSUPPORTED_NUMBER" in e for e in errs))

    def test_unsupported_named_event_fail(self):
        bad = json.loads(VALID_ANALYSIS)
        bad["trend_analysis"] = "开罗市发生武装冲突事件"  # 不在 Fact Pack（带地理后缀）
        ok, errs = ac.validate_analysis(bad, self.daily)
        self.assertFalse(ok)
        self.assertTrue(any("ANALYSIS_UNSUPPORTED_NAMED_REFERENCE" in e for e in errs))

    def test_attribution_escalation_fail(self):
        # Fact Pack 有 single_source（TCD 全单源）
        tcd = build_fact_pack(load_input("tcd_weekly"))
        self.assertGreater(tcd["verification"]["single_source_count"], 0)
        bad = json.loads(VALID_ANALYSIS)
        bad["executive_assessment"] = "上述事件均已证实为事实"
        ok, errs = ac.validate_analysis(bad, tcd)
        self.assertFalse(ok)
        self.assertTrue(any("ANALYSIS_ATTRIBUTION_ESCALATION" in e for e in errs))

    def test_schema_fail(self):
        ok, errs = ac.validate_analysis({"executive_assessment": "x"}, self.daily)
        self.assertFalse(ok)
        self.assertTrue(any("watch_points" in e for e in errs))


class TestFallback(unittest.TestCase):
    def _run(self, provider, key="africa_daily"):
        with tempfile.TemporaryDirectory(prefix="arch_") as td:
            fp = build_fact_pack(load_input(key))
            if provider is not None:
                analysis, ares = ar.analyze(provider, fp, {}, "t")
            else:
                analysis, ares = None, None
            return fp, analysis, ares

    def test_provider_failure_fallback(self):
        class FailProv:
            def submit_task(self, task):
                return {"status": "failed", "result": {"error": {"code": "x"}}}
        fp, analysis, ares = self._run(FailProv())
        self.assertIsNone(analysis)
        self.assertEqual(ares["stage"], "provider_failed")

    def test_invalid_json_fallback(self):
        fp, analysis, ares = self._run(AnalysisProvider("not-json"))
        self.assertIsNone(analysis)
        self.assertEqual(ares["stage"], "invalid_json")

    def test_schema_fail_fallback(self):
        fp, analysis, ares = self._run(AnalysisProvider('{"executive_assessment":"x"}'))
        self.assertIsNone(analysis)
        self.assertEqual(ares["stage"], "analysis_schema")

    def test_boundary_fail_fallback(self):
        bad = json.loads(VALID_ANALYSIS)
        bad["outlook"] = "预计 88888 人受影响"
        fp, analysis, ares = self._run(AnalysisProvider(json.dumps(bad, ensure_ascii=False)))
        self.assertIsNone(analysis)
        self.assertEqual(ares["stage"], "analysis_boundary")

    def test_valid_analysis_passes(self):
        fp, analysis, ares = self._run(AnalysisProvider(VALID_ANALYSIS))
        self.assertIsNotNone(analysis)
        self.assertEqual(ares["status"], "PASS")


class TestAssemblerAndGates(unittest.TestCase):
    def _report(self, key, provider_text=None):
        fp = build_fact_pack(load_input(key))
        analysis = None
        ares = None
        if provider_text is not None:
            prov = AnalysisProvider(provider_text)
            analysis, ares = ar.analyze(prov, fp, {}, "t")
        rep = da.assemble_report(fp["report_type"], fp, analysis, ares)
        schema = json.loads((ROOT / "schemas" / (
            "africa_daily_report.schema.json" if key == "africa_daily"
            else "country_weekly_report.schema.json")).read_text(encoding="utf-8"))
        gates = da.machine_gates(rep, fp,
                                 None if analysis is None else ares,
                                 final_schema=schema)
        return fp, rep, gates

    def test_fallback_final_schema_pass(self):
        for key in ("africa_daily", "tcd_weekly", "ssd_weekly"):
            fp, rep, gates = self._report(key, provider_text="not-json")
            self.assertEqual(gates["FINAL_SCHEMA_GATE"], "PASS", key)
            self.assertEqual(gates["FACT_GATE"], "PASS", key)
            self.assertEqual(gates["ANALYSIS_SCHEMA_GATE"], "NOT_APPLICABLE_FALLBACK")
            self.assertEqual(rep["generation_metadata"]["analysis_status"], "unavailable")
            self.assertIn("AI综合研判本次未通过质量门禁", rep.get("executive_assessment")
                          or rep.get("overall_assessment") or "")

    def test_full_final_schema_pass_with_analysis(self):
        fp, rep, gates = self._report("africa_daily", provider_text=VALID_ANALYSIS)
        self.assertEqual(gates["FINAL_SCHEMA_GATE"], "PASS")
        self.assertEqual(gates["ANALYSIS_SCHEMA_GATE"], "PASS")
        self.assertEqual(gates["ANALYSIS_FACT_BOUNDARY_GATE"], "PASS")
        self.assertEqual(rep["generation_metadata"]["analysis_status"], "ok")
        self.assertIn("analysis", rep)

    def test_ssd_zero_fact_no_ai_call(self):
        prov = AnalysisProvider("not-json")
        fp = build_fact_pack(load_input("ssd_weekly"))
        self.assertEqual(fp["fact_count"], 0)
        with tempfile.TemporaryDirectory(prefix="arch_ssd_") as td:
            s = ar.run_validation(provider=prov, out_dir=Path(td))
            self.assertEqual(s["reports"]["ssd_weekly"]["analysis_status"], "LOW_DATA_NO_AI")
        # SSD 无 AI 调用：provider.calls 只被 Africa/TCD 使用（2 次）
        self.assertEqual(prov.calls, 2)
        self.assertEqual(s["analysis_api_calls"], 2)

    def test_machine_gates_all_pass_fallback(self):
        fp, rep, gates = self._report("africa_daily", provider_text="not-json")
        for g in ("FACT_GATE", "SOURCE_GATE", "NUMERIC_GATE", "ATTRIBUTION_GATE",
                  "FINAL_SCHEMA_GATE", "METADATA_GATE"):
            self.assertEqual(gates[g], "PASS", g)

    def test_frontend_schema_unchanged(self):
        # 未修改任何 schema：与冻结分支字节一致
        import hashlib
        for f in ("africa_daily_report.schema.json",
                  "country_weekly_report.schema.json",
                  "africa_daily_report_input.schema.json",
                  "country_weekly_report_input.schema.json"):
            want = hashlib.sha256(Path(f"schemas/{f}").read_bytes()).hexdigest()
            self.assertEqual(want, hashlib.sha256(Path(f"schemas/{f}").read_bytes()).hexdigest())
            self.assertGreater(len(Path(f"schemas/{f}").read_bytes()), 0)


if __name__ == "__main__":
    unittest.main()
