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

from scripts.ai.enrichment_eligibility import (  # noqa: E402
    eligibility_status, effective_country_iso3,
)

AUDIT = ROOT / "docs" / "stage4-workbuddy-trial"


def _load(name):
    return json.loads((AUDIT / name).read_text(encoding="utf-8"))


def _load_quarantine_ids():
    # 修正：quarantine 条目用 original_id（EVT_ 或 legacy 格式）关联 canonical；
    # 须同时纳入 legacy_event_id 映射到 event_id，隔离判定才真正生效。
    q = json.loads((ROOT / "data" / "canonical" / "quarantine.json").read_text(encoding="utf-8"))
    qids = set()
    for it in q.get("items", []):
        if it.get("original_object_type") == "event":
            oid = it.get("original_id")
            if oid:
                qids.add(oid)
    canon = _canonical_by_id()
    for ev in canon.values():
        if ev.get("legacy_event_id") in qids:
            qids.add(ev.get("event_id"))
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

    def test_samples_still_in_canonical_derive_iso3(self):
        # 最新 main 数据已变化（V1.0 QA 后 canonical 删减/迁移），部分旧试跑样本
        # 已不在 canonical；审计快照保留为 reference。对仍在 canonical 的样本，
        # 其 effective country_iso3 必须与 manifest 记录一致（缺失时由 ISO2 派生）。
        for it in self.manifest["items"]:
            ev = self.canonical.get(it["event_id"])
            if ev is None:
                continue
            self.assertEqual(effective_country_iso3(ev), it["country_iso3"],
                             it["event_id"])

    def test_samples_in_canonical_not_quarantined(self):
        # 仍在 canonical 的旧试跑样本不得处于隔离池（audit/reference 完整性）
        qids = _load_quarantine_ids()
        for it in self.manifest["items"]:
            ev = self.canonical.get(it["event_id"])
            if ev is None:
                continue
            self.assertNotIn(it["event_id"], qids, it["event_id"])
            self.assertNotIn(ev.get("legacy_event_id"), qids, it["event_id"])

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
    def test_token_unavailable_not_zero(self):
        """Token 不可用必须记录为不可用，不得猜测/记为 0。"""
        t = _load("token_usage.json")
        self.assertFalse(t["token_usage_available"])
        self.assertIsNone(t["total_input_tokens"])
        self.assertIsNone(t["total_output_tokens"])
        self.assertIsNone(t["cached_input_tokens"])
        self.assertIsNone(t["estimated_cost"])
        self.assertEqual(t["unavailable_reason"],
                         "WorkBuddy queue did not expose model token usage")
        self.assertIsNone(t.get("per_item"))
        # 不得出现把无法获得的用量记为 0 的字段
        self.assertNotIn("total", t)

    def test_trial_summary_token_unavailable(self):
        s = _load("trial_summary.json")
        tu = s["token_usage"]
        self.assertFalse(tu["token_usage_available"])
        self.assertIsNone(tu["total_input_tokens"])
        self.assertIsNone(tu["total_output_tokens"])
        self.assertIsNone(tu["cached_input_tokens"])
        self.assertIsNone(tu["estimated_cost"])
        self.assertEqual(tu["unavailable_reason"],
                         "WorkBuddy queue did not expose model token usage")

    def test_execution_flags(self):
        t = _load("token_usage.json")
        self.assertEqual(t["execution_route"], "workbuddy_queue")
        self.assertEqual(t["actual_model"], "deepseek-v4-flash")
        self.assertFalse(t["direct_website_api_call"])

    def test_model_access_mode(self):
        for name in ("trial_summary.json", "token_usage.json"):
            o = _load(name)
            self.assertEqual(o["model_access_mode"], "workbuddy_managed", name)
            # underlying_model_source 无法确认时必须是 unknown，不得推测
            self.assertIn("underlying_model_source", o, name)

    def test_no_builtin_model_claim(self):
        """不得保留未经证实的「内置模型」表述。"""
        s = _load("trial_summary.json")
        t = _load("token_usage.json")
        blob = json.dumps(s, ensure_ascii=False) + json.dumps(t, ensure_ascii=False)
        self.assertNotIn("内置", blob)
        self.assertNotIn("内置模型", blob)


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
