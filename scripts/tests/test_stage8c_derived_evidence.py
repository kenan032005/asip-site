#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage8C Package2 — Derived Frozen Report Evidence 测试套件（AI_CALLS=0）。

§十五 覆盖：
  1. derived snapshot deterministic build（same artifacts → same SHA）
  2. three report inputs complete（非空、完整结构化 payload）
  3. no fixture/mock contamination
  4. every included record has provenance
  5. held/excluded auditable
  6. counts close to 28 without double counting
  7. report input contract validation（官方 input schema + $ref）
  8. numeric provenance preparation（metadata date / 事实数字）
  9. generation_metadata 排除在 factual numeric gate 之外
  10. raw persistence（schema failure 前 raw 已持久化）
  11. report-stage-only mode 无 enrichment 调用
  12. exact expected report calls = 3
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.safety import derive_frozen_report_evidence as dfe  # noqa: E402
from scripts.ai.safety import report_evidence_recovery as rer  # noqa: E402
from scripts.ai.safety import manual_trial as mt  # noqa: E402
from scripts.ai.schema_validation import validate_against_schema  # noqa: E402

ART = dfe.ART
EXPECTED = {
    "input_total": 28,
    "social_total": 9,
    "disease_total": 19,
    "social_included": 8,
    "disease_included": 9,
    "excluded_insufficient": 9,
    "exclusions": 11,
    "africa": 17,
    "tcd": 7,
    "ssd": 0,
}


class CountingProvider:
    """统计调用的 fake provider；返回指定文本。"""

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
            "reasoning_tokens": None,
        }}


def build_once(tmp):
    return dfe.build_derived_snapshot(art_dir=ART, out_dir=tmp / "derived",
                                      manifest_path=tmp / "manifest.json")


class TestDeterministicBuild(unittest.TestCase):
    def test_same_artifacts_same_sha(self):
        with tempfile.TemporaryDirectory(prefix="derived_det_") as td:
            root = Path(td)
            m1, _ = build_once(root)
            m2, _ = build_once(root)
            self.assertEqual(m1["hashes"], m2["hashes"],
                             "两次构建 hash 必须一致（确定性）")
            for f in ("africa_daily_report_input.json",
                      "tcd_weekly_report_input.json",
                      "ssd_weekly_report_input.json"):
                self.assertEqual((root / "derived" / f).read_bytes(),
                                 (root / "derived" / f).read_bytes())

    def test_aggregate_hash_is_concat_of_three(self):
        with tempfile.TemporaryDirectory(prefix="derived_agg_") as td:
            root = Path(td)
            m, _ = build_once(root)
            blob = b"".join((root / "derived" / f).read_bytes()
                            for f in ("africa_daily_report_input.json",
                                      "tcd_weekly_report_input.json",
                                      "ssd_weekly_report_input.json"))
            self.assertEqual(m["hashes"]["aggregate_snapshot_sha256"],
                             dfe.sha256_bytes(blob))


class TestThreeInputsComplete(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(prefix="derived_comp_") as td:
            cls.m, cls.art = build_once(Path(td))

    def test_three_payloads_present_and_complete(self):
        daily, tcd, ssd = self.art["daily"], self.art["tcd"], self.art["ssd"]
        for obj in (daily, tcd, ssd):
            self.assertIsInstance(obj, dict)
            self.assertIn("sections", obj)
            self.assertTrue(obj["report_id"].endswith("33066148566"))
        # daily：8 social + 9 disease 完整 items（非 count/excerpt）
        self.assertEqual(len(daily["sections"]["executive_summary"]), 8)
        self.assertEqual(len(daily["sections"]["public_health_disease"]), 9)
        it = daily["sections"]["executive_summary"][0]
        self.assertIn("event_id", it)
        self.assertIn("summary", it)
        self.assertIn("facts", it)
        self.assertIn("uncertainties", it)
        self.assertIn("source_evidence", it)
        self.assertTrue(it["summary"], "summary 必须完整落盘，不能只存 count")
        self.assertEqual(len(tcd["sections"]["major_events"]), 7)
        self.assertEqual(len(ssd["sections"]["major_events"]), 0)

    def test_no_fixture_mock_contamination(self):
        m = self.m
        self.assertFalse(m["fixtures_used"])
        self.assertFalse(m["golden_set_used"])
        self.assertFalse(m["mock_used"])
        self.assertEqual(m["evidence_sources"], [
            "input_summary.json", "safety_layer_trial.json",
            "manual_trial_summary.json", "human_review_pack.md"])
        # 内容全部来自 Run#4 corrected_output（抽查标题）
        titles = {it["title"] for it in self.art["daily"]["sections"]["executive_summary"]}
        self.assertIn("乍得：国际移民组织向穆索罗市提供抗洪援助", titles)


class TestProvenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(prefix="derived_prov_") as td:
            cls.m, cls.art = build_once(Path(td))

    def test_every_included_record_has_provenance(self):
        prov = self.art["provenance"]["records"]
        by_report = {}
        for r in prov:
            by_report.setdefault(r["report"], []).append(r)
        self.assertEqual(len(by_report["africa_daily"]), 17)
        self.assertEqual(len(by_report["tcd_weekly"]), 7)
        for r in prov:
            for k in ("event_id", "disease_event_id", "source_run", "source_ref",
                      "country", "input_type", "original_enrichment_record",
                      "safety_status", "safety_corrected", "correction_rule_ids",
                      "included_section", "inclusion_reason",
                      "time_window_evidence"):
                self.assertIn(k, r, "provenance 缺字段 %s" % k)
            self.assertEqual(r["source_run"], "33066148566")
            self.assertTrue(r["source_ref"], "included 记录必须有 source_ref")
            self.assertEqual(r["safety_status"], "PASS")

    def test_historical_equivalence_false(self):
        self.assertEqual(self.m["historical_report_input_equivalence"], False)
        self.assertEqual(self.m["reconstruction_claim"], "none")
        self.assertEqual(self.m["report_input_snapshot_reconstructable"], False)
        self.assertEqual(self.m["historical_reconstruction_attempt_hash"],
                         "5b03bfcc3bf9287934b550eba98177c69ae2cb1d8805eecf45b940cfe18148d8")

    def test_held_excluded_auditable(self):
        ex = self.art["exclusions"]
        self.assertEqual(len(ex), 11)
        reasons = sorted({e["reason"] for e in ex})
        self.assertIn("invalid_response_shape", reasons)
        self.assertIn("enrichment_schema_failure", reasons)
        self.assertIn("insufficient_provenance", reasons)
        for e in ex:
            for k in ("record_id", "type", "country", "reason"):
                self.assertIn(k, e)
        # S04 / D07 具体存在
        rids = [e["record_id"] for e in ex]
        self.assertIn("EVT_8c9d4096815dd33c", rids)
        self.assertIn("DSEV_4044139de1bafb0d", rids)


class TestCountsClosure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(prefix="derived_cnt_") as td:
            cls.m, cls.art = build_once(Path(td))

    def test_counts_close_to_28_no_double_count(self):
        c = self.art["counts"]
        self.assertEqual(c["input_total"], 28)
        self.assertEqual(c["social_total"], 9)
        self.assertEqual(c["disease_total"], 19)
        self.assertEqual(c["social_enrichment_accepted"], 8)
        self.assertEqual(c["disease_enrichment_accepted"], 18)
        self.assertEqual(c["social_report_included"], 8)
        self.assertEqual(c["disease_report_included"], 9)
        self.assertTrue(c["closure_ok"])
        # 28 = included(17) + exclusions(11)；无超 28 双计
        self.assertEqual(c["social_report_included"] + c["disease_report_included"]
                         + len(self.art["exclusions"]), 28)
        self.assertLessEqual(c["africa_daily_input_count"], 28)
        self.assertLessEqual(c["tcd_weekly_input_count"], 28)
        self.assertEqual(c["africa_daily_input_count"], 17)
        self.assertEqual(c["tcd_weekly_input_count"], 7)
        self.assertEqual(c["ssd_weekly_input_count"], 0)

    def test_no_52_style_double_count(self):
        c = self.art["counts"]
        self.assertLess(c["social_report_included"] + c["disease_report_included"], 28)


class TestContractAndNumeric(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(prefix="derived_schema_") as td:
            cls.m, cls.art = build_once(Path(td))

    def test_report_input_contract_validation(self):
        # 官方 input schema + $ref
        cases = [
            (self.art["daily"], "africa_daily_report_input.schema.json"),
            (self.art["tcd"], "country_weekly_report_input.schema.json"),
            (self.art["ssd"], "country_weekly_report_input.schema.json"),
        ]
        for obj, schema_name in cases:
            s = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
            errs = validate_against_schema(obj, s, resolve_refs=True)
            self.assertEqual(errs, [], "%s: %s" % (schema_name, errs[:3]))

    def test_numeric_provenance_preparation(self):
        for obj in (self.art["daily"], self.art["tcd"], self.art["ssd"]):
            prov = mt._collect_input_provenance(obj)
            self.assertTrue(prov, "input 必须提供数字 provenance")
        # metadata date 分类：week_start/week_end 的数字归 metadata_date
        prov = mt._collect_input_provenance(self.art["tcd"])
        dates = [p for paths in prov.values() for p in paths
                 if p["semantic_type"] == "metadata_date"]
        self.assertTrue(any("week_start" in p["input_field_path"] for p in dates))

    def test_generation_metadata_excluded(self):
        report = {"executive_assessment": "x",
                  "generation_metadata": {"model_name": "deepseek-v4-flash",
                                          "prompt_version": "v1.0.3",
                                          "usage_purpose": "development_test"}}
        ok, _entries, unsupported = mt._numeric_provenance_check(
            report, {"sections": {}})
        self.assertTrue(ok, "machine envelope 数字不得触发 factual numeric gate")
        self.assertEqual(unsupported, [])


class TestReportStageOnlyMode(unittest.TestCase):
    def test_ready_check_offline(self):
        with tempfile.TemporaryDirectory(prefix="derived_ready_") as td:
            root = Path(td)
            m, _ = build_once(root)
            pre = rer.check_ready(derived_dir=root / "derived",
                                  manifest_path=root / "manifest.json")
            self.assertTrue(pre["ready"])
            self.assertEqual(pre["expected_api_calls"], 3)
            self.assertEqual(pre["aggregate_snapshot_sha256"],
                             m["hashes"]["aggregate_snapshot_sha256"])
            self.assertFalse(pre["reconstructable"])

    def test_hash_mismatch_blocks_ready(self):
        with tempfile.TemporaryDirectory(prefix="derived_mis_") as td:
            root = Path(td)
            m, _ = build_once(root)
            p = root / "derived" / "africa_daily_report_input.json"
            p.write_text(json.dumps({"tampered": True}), encoding="utf-8")
            pre = rer.check_ready(derived_dir=root / "derived",
                                  manifest_path=root / "manifest.json")
            self.assertFalse(pre["ready"])
            self.assertFalse(pre["gates"]["hash_lock"])

    def test_run_three_calls_no_enrichment(self):
        with tempfile.TemporaryDirectory(prefix="derived_run_") as td:
            root = Path(td)
            m, _ = build_once(root)
            prov = CountingProvider("not-json")
            res = rer.run_evidence(provider=prov,
                                   out_dir=root / "evidence_run")
            self.assertEqual(res["ai_calls"], 3)
            self.assertEqual(prov.calls, 3)
            self.assertEqual(sorted(prov.task_types),
                             ["africa_daily", "country_weekly", "country_weekly"])
            self.assertNotIn("stage4_event_enrichment", prov.task_types)
            self.assertNotIn("disease_summary", prov.task_types)
            # raw 持久化：3 个 raw_response 文件存在
            for k in ("africa_daily", "tcd_weekly", "ssd_weekly"):
                rp = root / "evidence_run" / ("%s_raw_response.json" % k)
                self.assertTrue(rp.exists(), "%s raw 未持久化" % k)
                saved = json.loads(rp.read_text(encoding="utf-8"))
                self.assertEqual(saved["raw_content"], "not-json")

    def test_exact_expected_report_calls(self):
        self.assertEqual(rer.EXPECTED_API_CALLS, 3)


if __name__ == "__main__":
    unittest.main()
