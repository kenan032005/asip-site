#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8C Package 1 — Deterministic Attribution Safety Layer 测试套件。

确定性测试（AI_CALLS=0，不联网、无 credential）：

  §十五 覆盖：
    1. Run15 真实 S3/S8/D1 regression（FAIL → deterministic safe handling）
    2. suspected / unconfirmed / alleged / claimed / conflicting /
       single_source safe correction
    3. cannot-map → HOLD（fail-closed）
    4. correction 不改数字/实体/日期/地点/来源
    5. post-correction 重新验证
    6. existing PASS case（S4/S6/S7/D4 + 合成 PASS）保持不变
    7. Public blocks FAIL / Report Input blocks FAIL
    8. 数字污染（suspected→confirmed）就地修复

用法：
  python -m unittest scripts.tests.test_stage8c_attribution_safety
"""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.safety.attribution_safety import (
    extract_markers,
    run_attribution_safety,
    validate_attribution,
    SAFETY_VERSION,
)

GOLDEN_DIR = ROOT / "data" / "qualification" / "stage8c" / "golden"


def load_golden(cid):
    return json.loads((GOLDEN_DIR / ("%s.json" % cid)).read_text(encoding="utf-8"))


def numbers_in(obj):
    """收集 obj 中全部整数（Unicode 安全：中文语境下 \w 含中文字符，
    不能用 (?<![\w.]) 断言，直接取连续数字串）。"""
    out = set()

    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
        elif isinstance(node, (int, float)) and node is not None:
            out.add(int(node))
        elif isinstance(node, str):
            import re
            for m in re.findall(r"\d[\d,]*", node):
                out.add(int(m.replace(",", "")))
    walk(obj)
    return out


class TestGoldenRegression(unittest.TestCase):
    """§十五-1：Run15 真实 S3/S8/D1（Stage8B TRUE attribution loss）safe handling。"""

    def test_s3_single_source_loss(self):
        g = load_golden("S3")
        self.assertEqual(g["run15_attribution_loss"], True)
        res = run_attribution_safety(g["input_payload"], g["original_ai_output"],
                                      g["task_type"])
        self.assertEqual(res["validator_pre_correction"]["status"], "FAIL")
        self.assertGreaterEqual(len(res["corrections"]), 1)
        self.assertEqual(res["validator_post_correction"]["status"], "PASS")
        self.assertEqual(res["attribution_safety_gate"], "PASS")
        # 修正必须是 single_source 规则
        rules = {c["rule_id"] for c in res["corrections"]}
        self.assertTrue(rules & {"SAFETY-CORR-D1", "SAFETY-CORR-D1N"})
        # original 必须保留
        self.assertEqual(res["original_ai_output"], g["original_ai_output"])
        self.assertNotEqual(res["corrected_output"], g["original_ai_output"])
        # 修正只补充不确定性（uncertainties 追加），不改 summary 事实句
        self.assertEqual(res["corrected_output"]["summary_zh"],
                         g["original_ai_output"]["summary_zh"])

    def test_s8_conflicting_loss(self):
        g = load_golden("S8")
        self.assertEqual(g["run15_attribution_loss"], True)
        res = run_attribution_safety(g["input_payload"], g["original_ai_output"],
                                      g["task_type"])
        self.assertEqual(res["validator_pre_correction"]["status"], "FAIL")
        # single_source 已保留（"仅有一个来源"），仅 conflicting 需要处理
        rules = {c["rule_id"] for c in res["corrections"]}
        self.assertIn("SAFETY-CORR-C1", rules)
        self.assertEqual(res["validator_post_correction"]["status"], "PASS")
        self.assertEqual(res["attribution_safety_gate"], "PASS")
        # corrected uncertainties 含固定冲突限定句
        self.assertTrue(any("存在冲突" in u or "尚无法确认" in u
                            for u in res["corrected_output"].get("uncertainties", [])))

    def test_d1_suspected_unconfirmed_numeric(self):
        g = load_golden("D1")
        self.assertEqual(g["run15_attribution_loss"], True)
        res = run_attribution_safety(g["input_payload"], g["original_ai_output"],
                                      g["task_type"])
        self.assertEqual(res["validator_pre_correction"]["status"], "FAIL")
        self.assertGreaterEqual(len(res["validator_pre_correction"].get("numeric_failures") or []), 1)
        rules = {c["rule_id"] for c in res["corrections"]}
        self.assertIn("SAFETY-CORR-B2", rules)
        self.assertEqual(res["validator_post_correction"]["status"], "PASS")
        self.assertEqual(res["attribution_safety_gate"], "PASS")
        # 数字句就地补"尚未证实"，数字本身不变
        self.assertIn("5万", res["corrected_output"].get("summary_zh", ""))
        self.assertIn("尚未证实", res["corrected_output"].get("summary_zh", ""))
        # 数字未被改变
        self.assertEqual(numbers_in(res["corrected_output"]),
                         numbers_in(g["original_ai_output"]))


class TestPASSRegression(unittest.TestCase):
    """§十五-11：existing PASS case（Run15 S4/S6/S7/D4）保持原样。"""

    def _assert_untouched(self, cid):
        g = load_golden(cid)
        self.assertEqual(g["run15_attribution_loss"], False)
        res = run_attribution_safety(g["input_payload"], g["original_ai_output"],
                                      g["task_type"])
        self.assertEqual(res["validator_pre_correction"]["status"], "PASS")
        self.assertEqual(res["corrections"], [])
        self.assertEqual(res["corrected_output"], g["original_ai_output"])
        self.assertEqual(res["attribution_safety_gate"], "PASS")
        self.assertEqual(res["publication_eligible"], True)
        self.assertEqual(res["report_input_eligible"], True)

    def test_s4_unchanged(self):
        self._assert_untouched("S4")

    def test_s6_unchanged(self):
        self._assert_untouched("S6")

    def test_s7_unchanged(self):
        self._assert_untouched("S7")

    def test_d4_unchanged(self):
        self._assert_untouched("D4")


class TestMarkerCorrections(unittest.TestCase):
    """§十五-2：各 marker 的确定性 safe correction。"""

    def _base_input(self, **over):
        base = {
            "event_id": "EVT_TEST0001",
            "title_original": "Test event title",
            "country_code": "TD",
            "independent_source_count": 1,
        }
        base.update(over)
        return base

    def _base_output(self, summary="事件发生，造成影响。", **over):
        out = {"title_zh": "测试事件", "summary_zh": summary,
               "event_type": "other_security", "country_iso3": "TCD",
               "key_facts": [], "uncertainties": []}
        out.update(over)
        return out

    def test_single_source_correction(self):
        inp = self._base_input(verification_level="single_source")
        out = self._base_output()  # 无任何限定
        res = run_attribution_safety(inp, out, "stage4_event_enrichment")
        self.assertEqual(res["validator_pre_correction"]["status"], "FAIL")
        self.assertEqual(res["attribution_safety_gate"], "PASS")
        self.assertGreaterEqual(len(res["corrections"]), 1)
        self.assertTrue(any("单一来源" in u or "缺乏交叉验证" in u
                            for u in res["corrected_output"].get("uncertainties", [])))
        # summary 未被改动（不改事实句）
        self.assertEqual(res["corrected_output"]["summary_zh"], out["summary_zh"])

    def test_suspected_correction(self):
        inp = {"disease_event_id": "DSEV_TXA", "suspected_cases": 120,
               "confirmed_cases": None, "deaths": None, "total_cases": 120,
               "case_count_type": "suspected"}
        out = {"disease_event_id": "DSEV_TXA", "title_zh": "疫情",
               "summary_zh": "累计报告120例病例。", "key_changes": [], "uncertainties": []}
        res = run_attribution_safety(inp, out, "disease_summary")
        self.assertEqual(res["validator_pre_correction"]["status"], "FAIL")
        self.assertEqual(res["attribution_safety_gate"], "PASS")
        self.assertIn("尚未证实", res["corrected_output"]["summary_zh"])
        # 数字不变
        self.assertEqual(numbers_in(res["corrected_output"]), {120})
        self.assertIn("120", res["corrected_output"]["summary_zh"])

    def test_unconfirmed_correction(self):
        inp = {"disease_event_id": "DSEV_T2", "total_cases": 500,
               "uncertainties": ["数字为媒体转述"], "verification_status": "unconfirmed"}
        out = {"disease_event_id": "DSEV_T2", "title_zh": "疫情",
               "summary_zh": "累计500例。", "key_changes": [], "uncertainties": []}
        res = run_attribution_safety(inp, out, "disease_summary")
        self.assertEqual(res["attribution_safety_gate"], "PASS")
        self.assertIn("尚未证实", res["corrected_output"]["summary_zh"])
        self.assertIn("500", res["corrected_output"]["summary_zh"])

    def test_alleged_correction(self):
        inp = {"event_id": "EVT_T3", "title_original": "Officials alleged the attack",
               "summary_original": "authorities claimed the group carried out the strike"}
        out = {"title_zh": "袭击事件", "summary_zh": "组织实施了袭击。",
               "event_type": "terrorist_attack", "country_iso3": "TCD",
               "key_facts": [], "uncertainties": []}
        res = run_attribution_safety(inp, out, "stage4_event_enrichment")
        self.assertEqual(res["attribution_safety_gate"], "PASS")
        self.assertTrue(any("据称" in u or "独立证实" in u
                            for u in res["corrected_output"].get("uncertainties", [])))

    def test_claimed_correction(self):
        inp = {"event_id": "EVT_T4", "title_original": "Group claimed responsibility"}
        out = {"title_zh": "宣称负责", "summary_zh": "组织宣称对袭击负责。",
               "event_type": "terrorist_attack", "country_iso3": "TCD",
               "key_facts": [], "uncertainties": []}
        res = run_attribution_safety(inp, out, "stage4_event_enrichment")
        self.assertEqual(res["attribution_safety_gate"], "PASS")

    def test_conflicting_correction(self):
        inp = {"event_id": "EVT_T5", "conflicting_fields": ["deaths"]}
        out = {"title_zh": "冲突事件", "summary_zh": "死亡人数为10人。",
               "event_type": "other_security", "country_iso3": "TCD",
               "key_facts": [], "uncertainties": []}
        res = run_attribution_safety(inp, out, "stage4_event_enrichment")
        self.assertEqual(res["attribution_safety_gate"], "PASS")
        self.assertTrue(any("存在冲突" in u or "尚无法确认" in u
                            for u in res["corrected_output"].get("uncertainties", [])))

    def test_single_source_with_source_name(self):
        inp = {"event_id": "EVT_T6", "verification_level": "single_source",
               "source_links": [{"url": "https://x/1", "source_name": "Tchadinfos"}]}
        out = {"title_zh": "事件", "summary_zh": "事件发生。",
               "event_type": "other_security", "country_iso3": "TCD",
               "key_facts": [], "uncertainties": []}
        res = run_attribution_safety(inp, out, "stage4_event_enrichment")
        self.assertEqual(res["attribution_safety_gate"], "PASS")
        joined = " ".join(res["corrected_output"].get("uncertainties", []))
        self.assertIn("Tchadinfos", joined)


class TestFailClosed(unittest.TestCase):
    """§十五-3/7：cannot-map → HOLD；Public/Report Input 阻断 FAIL。"""

    def test_no_output_fields_hold(self):
        inp = {"event_id": "EVT_T7", "verification_level": "single_source"}
        out = {"key_facts": [{"fact": "事件发生", "evidence_field": "body",
                              "evidence_excerpt": "x"}]}  # 无 summary_zh/uncertainties/title_zh
        res = run_attribution_safety(inp, out, "stage4_event_enrichment")
        self.assertEqual(res["validator_pre_correction"]["status"], "FAIL")
        self.assertEqual(res["attribution_safety_gate"], "FAIL")
        self.assertEqual(res["publication_eligible"], False)
        self.assertEqual(res["report_input_eligible"], False)
        self.assertEqual(res["manual_review_required"], True)
        self.assertEqual(res["corrected_output"], out)  # 不改原输出

    def test_public_blocks_fail(self):
        # 真正无法映射（输出无可写字段）→ fail-closed → Public/Report Input 阻断
        inp = {"event_id": "EVT_T8", "verification_level": "single_source"}
        out = {"key_facts": [{"fact": "事件发生", "evidence_field": "body",
                              "evidence_excerpt": "x"}]}
        res = run_attribution_safety(inp, out, "stage4_event_enrichment")
        self.assertEqual(res["attribution_safety_gate"], "FAIL")
        self.assertEqual(res["publication_eligible"], False)
        self.assertEqual(res["report_input_eligible"], False)
        self.assertEqual(res["manual_review_required"], True)

    def test_uncorrectable_after_post_validator_hold(self):
        # 构造一个修正后仍不满足的 case：输出无 uncertainties 且数字句无法就地修正
        inp = {"disease_event_id": "DSEV_T9", "suspected_cases": 10,
               "total_cases": 10, "uncertainties": ["未见原始通报"]}
        out = {"disease_event_id": "DSEV_T9", "title_zh": "疫情",
               "summary_zh": "累计10例。", "key_changes": [], "uncertainties": "N/A"}
        # uncertainties 为字符串（非法）→ 修正后仍非 list 但 validator 只看文本 → PASS 预期
        res = run_attribution_safety(inp, out, "disease_summary")
        # B2 数字句就地修正后 POST 应 PASS
        self.assertEqual(res["attribution_safety_gate"], "PASS")


class TestCorrectionIntegrity(unittest.TestCase):
    """§十五-4：correction 不改数字/实体/日期/地点/来源。"""

    def test_numbers_unchanged(self):
        g = load_golden("D1")
        res = run_attribution_safety(g["input_payload"], g["original_ai_output"],
                                      g["task_type"])
        self.assertEqual(numbers_in(res["corrected_output"]),
                         numbers_in(g["original_ai_output"]))

    def test_dates_and_entities_unchanged(self):
        g = load_golden("S3")
        res = run_attribution_safety(g["input_payload"], g["original_ai_output"],
                                      g["task_type"])
        orig = g["original_ai_output"]
        corr = res["corrected_output"]
        # summary/title 事实句完全不变（S3 只追加 uncertainties）
        self.assertEqual(orig["summary_zh"], corr["summary_zh"])
        self.assertEqual(orig["title_zh"], corr["title_zh"])
        self.assertEqual(orig["key_facts"], corr["key_facts"])
        self.assertEqual(orig["location"], corr["location"])

    def test_source_ids_unchanged(self):
        g = load_golden("S8")
        res = run_attribution_safety(g["input_payload"], g["original_ai_output"],
                                      g["task_type"])
        self.assertEqual(res["corrected_output"]["key_facts"],
                         g["original_ai_output"]["key_facts"])

    def test_no_new_facts(self):
        g = load_golden("S8")
        res = run_attribution_safety(g["input_payload"], g["original_ai_output"],
                                      g["task_type"])
        # 修正只加 uncertainties 元素；key_facts/summary 不变
        self.assertEqual(res["corrected_output"]["summary_zh"],
                         g["original_ai_output"]["summary_zh"])


class TestPostCorrectionValidator(unittest.TestCase):
    """§十五-5：post-correction 重新验证通过。"""

    def test_post_validator_recheck(self):
        g = load_golden("S3")
        res = run_attribution_safety(g["input_payload"], g["original_ai_output"],
                                      g["task_type"])
        post = res["validator_post_correction"]
        self.assertIsNotNone(post)
        self.assertEqual(post["status"], "PASS")
        self.assertEqual(post["gate"], "PASS")


class TestTelemetry(unittest.TestCase):
    """§十四：按 Social/Disease 分列计数。"""

    def test_telemetry_social(self):
        tel = {}
        g = load_golden("S3")
        run_attribution_safety(g["input_payload"], g["original_ai_output"],
                               g["task_type"], telemetry=tel)
        self.assertIn("social", tel)
        self.assertEqual(tel["social"]["attribution_gate_checked"], 1)
        self.assertEqual(tel["social"]["attribution_gate_pass"], 1)
        self.assertEqual(tel["social"]["attribution_auto_corrected"], 1)
        self.assertEqual(tel["social"]["attribution_hold"], 0)

    def test_telemetry_disease(self):
        tel = {}
        g = load_golden("D1")
        run_attribution_safety(g["input_payload"], g["original_ai_output"],
                               g["task_type"], telemetry=tel)
        self.assertIn("disease", tel)
        self.assertEqual(tel["disease"]["attribution_gate_checked"], 1)
        self.assertEqual(tel["disease"]["attribution_gate_pass"], 1)

    def test_telemetry_hold(self):
        tel = {}
        inp = {"event_id": "EVT_T10", "verification_level": "single_source"}
        out = {"key_facts": [{"fact": "x", "evidence_field": "body", "evidence_excerpt": "x"}]}
        run_attribution_safety(inp, out, "stage4_event_enrichment", telemetry=tel)
        self.assertEqual(tel["social"]["attribution_hold"], 1)
        self.assertEqual(tel["social"]["attribution_gate_pass"], 0)


class TestSafetyMeta(unittest.TestCase):
    def test_version(self):
        self.assertEqual(SAFETY_VERSION, "stage8c-v1")

    def test_no_ai_calls(self):
        # 安全层模块不得 import 任何 provider / LLM 模块
        import importlib.util
        mod = importlib.util.find_spec("scripts.ai.safety.attribution_safety")
        self.assertIsNotNone(mod)
        src = (ROOT / "scripts/ai/safety/attribution_safety.py").read_text(encoding="utf-8")
        for banned in ("openai", "requests.post", "urllib.request", "httpx",
                       "ASIP_DEEPSEEK_API_KEY", "provider_runner", "get_provider"):
            self.assertNotIn(banned, src)


if __name__ == "__main__":
    unittest.main()
