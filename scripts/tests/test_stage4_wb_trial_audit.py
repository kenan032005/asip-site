#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 第二执行包 — §十一 试跑审计测试（WorkBuddy 真实 AI 质量试跑）。

审计对象：docs/stage4-workbuddy-trial/ 下已提交的审计快照（manifest / review_matrix /
trial_summary / token_usage），全部基于 committed 数据，fresh-clone 可复现。

断言要点：
- 样本：20 条（TCD=10 / NER=10），全部存在于 canonical 且按官方资格函数判定 eligible；
- 模型标识合规：actual_model=deepseek-v4-flash、execution_route=workbuddy_queue、
  direct_website_api_call=false、recorded_truthfully=true、hy3_placeholder_used=false；
- 质量矩阵：20 行、模型输出硬检查（c1/c2/n1/e1/u1/u2）全过；
- Token：usage 全 0（WorkBuddy 队列执行，无外部 API 计量）；
- 严禁 hy3 伪装：审计快照中不得出现 model=hy3。
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.enrichment_eligibility import eligibility_status  # noqa: E402

AUDIT = ROOT / "docs" / "stage4-workbuddy-trial"


def _load(name):
    return json.loads((AUDIT / name).read_text(encoding="utf-8"))


def _load_quarantine_ids():
    q = json.loads((ROOT / "data" / "canonical" / "quarantine.json").read_text(encoding="utf-8"))
    qids = set()
    for it in q.get("items", []):
        if it.get("original_object_type") == "event":
            qid = it.get("quarantine_id")
            if qid:
                qids.add(qid)
    return qids


def _canonical_by_id():
    d = json.loads((ROOT / "data" / "canonical" / "event_clusters.json").read_text(encoding="utf-8"))
    return {ev.get("event_id"): ev for ev in d.get("items", [])}


class TestSampleManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = _load("sample_manifest.json")
        cls.canonical = _canonical_by_id()

    def test_manifest_has_20(self):
        items = self.manifest["items"]
        self.assertEqual(len(items), 20)

    def test_manifest_country_balance(self):
        from collections import Counter
        c = Counter(it["country_iso3"] for it in self.manifest["items"])
        self.assertEqual(c, {"TCD": 10, "NER": 10})

    def test_all_samples_in_canonical_with_iso3(self):
        for it in self.manifest["items"]:
            ev = self.canonical.get(it["event_id"])
            self.assertIsNotNone(ev, it["event_id"])
            self.assertEqual(ev.get("country_iso3"), it["country_iso3"])

    def test_all_samples_eligible_by_official_rule(self):
        qids = _load_quarantine_ids()
        for it in self.manifest["items"]:
            ev = self.canonical[it["event_id"]]
            st, reason = eligibility_status(ev, qids)
            self.assertEqual(st, "eligible", "%s: %s" % (it["event_id"], reason))

    def test_execution_flags_in_manifest(self):
        self.assertEqual(self.manifest["execution_route"], "workbuddy_queue")
        self.assertEqual(self.manifest["actual_model"], "deepseek-v4-flash")


class TestTrialSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = _load("trial_summary.json")

    def test_execution_route(self):
        self.assertEqual(self.summary["execution_route"], "workbuddy_queue")

    def test_actual_model(self):
        self.assertEqual(self.summary["actual_model"], "deepseek-v4-flash")

    def test_direct_website_api_call_false(self):
        self.assertFalse(self.summary["direct_website_api_call"])

    def test_processing_all_succeeded(self):
        p = self.summary["processing"]
        self.assertEqual(p["succeeded"], 20)
        self.assertEqual(p["failed_terminal"], 0)
        self.assertEqual(p["invalid_model_output"], 0)

    def test_retry_limit_one(self):
        self.assertEqual(self.summary["retry"]["max_retries_per_item"], 1)
        self.assertEqual(self.summary["retry"]["retries_used"], 0)

    def test_model_identity_truthful(self):
        mi = self.summary["model_identity"]
        self.assertEqual(mi["provider"], "workbuddy_queue")
        self.assertEqual(mi["model"], "deepseek-v4-flash")
        self.assertTrue(mi["recorded_truthfully"])
        self.assertFalse(mi["hy3_placeholder_used"])


class TestReviewMatrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = _load("review_matrix.json")

    def test_rows_20(self):
        self.assertEqual(len(self.matrix["rows"]), 20)

    def test_no_hard_fail(self):
        self.assertEqual(self.matrix["events_with_hard_fail"], [])
        for r in self.matrix["rows"]:
            self.assertEqual(r.get("hard_fails"), [], r["event_id"])

    def test_hard_checks_all_pass(self):
        hard = ["c1_country_top_level", "c2_location_country",
                "n1_evidence_numbers_traceable", "e1_location_entities_found",
                "u1_uncertainty_preserved", "u2_uncertainty_struct"]
        for k in hard:
            cs = self.matrix["check_summary"][k]
            self.assertEqual(cs["pass"], 20, k)

    def test_execution_flags(self):
        self.assertEqual(self.matrix["execution_route"], "workbuddy_queue")
        self.assertEqual(self.matrix["actual_model"], "deepseek-v4-flash")
        self.assertFalse(self.matrix["direct_website_api_call"])


class TestTokenUsage(unittest.TestCase):
    def test_all_zero(self):
        t = _load("token_usage.json")
        self.assertEqual(t["total"], {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0})
        for eid, item in t["per_item"].items():
            self.assertEqual(item, {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0}, eid)

    def test_execution_flags(self):
        t = _load("token_usage.json")
        self.assertEqual(t["execution_route"], "workbuddy_queue")
        self.assertEqual(t["actual_model"], "deepseek-v4-flash")
        self.assertFalse(t["direct_website_api_call"])


class TestNoHy3Fake(unittest.TestCase):
    def test_no_hy3_model_in_audit_snapshots(self):
        for name in ("sample_manifest.json", "review_matrix.json", "trial_summary.json", "token_usage.json"):
            o = _load(name)
            if "actual_model" in o:
                self.assertNotEqual(o["actual_model"], "hy3", name)
            if "model" in o:
                self.assertNotEqual(o["model"], "hy3", name)
        self.assertEqual(_load("trial_summary.json")["model_identity"]["model"], "deepseek-v4-flash")

    def test_review_doc_present_and_flagged(self):
        doc = (ROOT / "docs" / "stage4-workbuddy-trial-review.md")
        self.assertTrue(doc.exists())
        text = doc.read_text(encoding="utf-8")
        self.assertIn("workbuddy_queue", text)
        self.assertIn("deepseek-v4-flash", text)
        self.assertIn("direct_website_api_call", text)
        self.assertIn("false", text)


if __name__ == "__main__":
    unittest.main()
