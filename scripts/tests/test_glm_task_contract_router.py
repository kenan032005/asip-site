#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP GLM Task Contract Router 测试（§十二 Final Compatibility Fix）。

覆盖：task router / social+disease schema selection / disease evidence fields /
AI 不得覆盖 canonical 数字 / unknown-null / wrong schema rejection。
无需真实 API Key（纯构造 + schema 校验 + 装配断言）。
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)

from scripts.ai.glm_golden_set import (
    build_security_samples, build_disease_samples, make_task,
    _schema_for, _glm_system_prompt, _disease_glm_system_prompt,
)
from scripts.ai.schema_validation import validate_against_schema


def _valid_social_output():
    return {
        "source_language": "fr",
        "title_zh": "首都Y发生抗议活动",
        "summary_zh": "AAA国首都Y市中心发生抗议活动，当地居民举行示威。暂无伤亡确认。",
        "event_type": "civil_unrest",
        "country_iso3": "AAA",
        "location": {"country_iso3": "AAA", "admin1": None, "city": "首都Y",
                     "site": "市中心", "raw_text": "Capital Y city center"},
        "key_facts": [{"fact": "AAA国首都Y发生抗议活动",
                       "evidence_field": "body_extracted",
                       "evidence_excerpt": "held a demonstration"}],
        "uncertainties": ["伤亡情况尚未确认"],
        "security_relevance": "direct",
        "classification_confidence": 80,
    }


def _valid_disease_output():
    return {
        "disease_event_id": "DSEV_example0001",
        "title_zh": "AAA国霍乱疫情持续",
        "summary_zh": "AAA国霍乱疫情仍在活跃期，累计报告120例确诊、5例死亡。",
        "key_changes": [
            {"type": "case_update", "description": "累计确诊增至120例",
             "evidence_field": "confirmed_cases"},
        ],
        "uncertainties": [],
        "public_health_relevance": "direct",
        "classification_confidence": 80,
    }


class TestTaskRouter(unittest.TestCase):
    def test_social_task_uses_social_contract(self):
        s = build_security_samples()[0]
        t = make_task(s, "glm-4.7-flash")
        self.assertEqual(t["task_type"], "stage4_event_enrichment")
        self.assertEqual(t["prompt_version"], "glm-v1.0.1")
        self.assertIn("OUTPUT SCHEMA", t["system_text"])
        self.assertNotIn("disease_event_id", t["system_text"])

    def test_disease_task_uses_disease_contract(self):
        s = build_disease_samples()[0]
        t = make_task(s, "glm-4.7-flash")
        self.assertEqual(t["task_type"], "disease_summary")
        self.assertEqual(t["prompt_version"], "disease-glm-v1.0.1")
        self.assertIn("OUTPUT SCHEMA", t["system_text"])
        self.assertIn("disease_event_id", t["system_text"])
        self.assertIn("key_changes", t["system_text"])

    def test_prompt_files_exist_and_distinct(self):
        s = _glm_system_prompt()
        d = _disease_glm_system_prompt()
        self.assertGreater(len(s), 500)
        self.assertGreater(len(d), 500)
        self.assertNotEqual(s, d)


class TestSchemaSelection(unittest.TestCase):
    def test_social_schema_accepts_social_output(self):
        errs = validate_against_schema(_valid_social_output(),
                                       _schema_for(is_disease=False))
        self.assertEqual(errs, [], "社安输出应通过社安 schema")

    def test_disease_schema_accepts_disease_output(self):
        errs = validate_against_schema(_valid_disease_output(),
                                       _schema_for(is_disease=True))
        self.assertEqual(errs, [], "疾病输出应通过疾病 schema")

    def test_wrong_schema_rejected_both_directions(self):
        # 疾病输出过社安 schema → 拒绝
        e1 = validate_against_schema(_valid_disease_output(),
                                     _schema_for(is_disease=False))
        self.assertTrue(e1, "疾病输出过社安 schema 应失败")
        # 社安输出过疾病 schema → 拒绝
        e2 = validate_against_schema(_valid_social_output(),
                                     _schema_for(is_disease=True))
        self.assertTrue(e2, "社安输出过疾病 schema 应失败")

    def test_disease_schema_rejects_extra_top_level(self):
        # §五 AI 不得覆盖 canonical 数字：顶层加 confirmed_cases → additionalProperties 拒绝
        bad = dict(_valid_disease_output())
        bad["confirmed_cases"] = 999
        errs = validate_against_schema(bad, _schema_for(is_disease=True))
        self.assertTrue(any("confirmed_cases" in e for e in errs),
                        "额外顶层数字字段应被拒绝: %s" % errs)


class TestDiseaseEvidenceFields(unittest.TestCase):
    def test_disease_evidence_field_allowed(self):
        out = _valid_disease_output()
        out["key_changes"] = [
            {"type": "mortality_update", "description": "死亡增至14例",
             "evidence_field": "deaths"},
            {"type": "geographic_spread", "description": "传播至新州",
             "evidence_field": "admin1"},
        ]
        errs = validate_against_schema(out, _schema_for(is_disease=True))
        self.assertEqual(errs, [], "疾病字段 evidence_field 应通过")

    def test_social_evidence_field_rejected_in_disease(self):
        # 社安专属 evidence_field（body_extracted）不得用于疾病合同
        out = _valid_disease_output()
        out["key_changes"] = [
            {"type": "case_update", "description": "确诊增加",
             "evidence_field": "body_extracted"},
        ]
        errs = validate_against_schema(out, _schema_for(is_disease=True))
        self.assertTrue(any("body_extracted" in e for e in errs),
                        "社安字段用于疾病合同应被拒绝: %s" % errs)

    def test_key_changes_type_enum(self):
        out = _valid_disease_output()
        out["key_changes"] = [
            {"type": "not_a_valid_type", "description": "非法类型",
             "evidence_field": "deaths"},
        ]
        errs = validate_against_schema(out, _schema_for(is_disease=True))
        self.assertTrue(any("not_a_valid_type" in e for e in errs))


class TestNumericGate(unittest.TestCase):
    def test_disease_numeric_gate_via_key_changes(self):
        from scripts.ai.glm_golden_set import run_quality_checks
        # 源无 deaths 但 AI 的 key_changes 引用 deaths 且 description 含数字 → failure
        row = {
            "category": "disease_other_numbers", "is_disease": True,
            "provider_status": "succeeded",
            "source_summary": {"disease_id": "marburg", "confirmed_cases": 14,
                               "deaths": None},
            "parsed": {
                "disease_event_id": "D",
                "title_zh": "疫情",
                "summary_zh": "疫情进展摘要",
                "key_changes": [{"type": "mortality_update",
                                 "description": "死亡20例",
                                 "evidence_field": "deaths"}],
                "uncertainties": [],
                "public_health_relevance": "direct",
                "classification_confidence": 80,
            },
        }
        stats = run_quality_checks([row])
        self.assertEqual(stats["disease_numeric_gate_failures"], 1,
                         "AI 引用源中不存在数字应触发 Evidence Gate")

    def test_unknown_null_preserved(self):
        # 源 null 字段保持未知：模型不引用数字字段则通过
        from scripts.ai.glm_golden_set import run_quality_checks
        row = {
            "category": "disease_cholera_tcd", "is_disease": True,
            "provider_status": "succeeded",
            "source_summary": {"disease_id": "cholera", "confirmed_cases": None,
                               "deaths": None},
            "parsed": {
                "disease_event_id": "D",
                "title_zh": "TCD霍乱监测",
                "summary_zh": "TCD霍乱疫情处于监测中，具体病例数字尚未公布。",
                "key_changes": [{"type": "status_change",
                                 "description": "进入监测状态",
                                 "evidence_field": "outbreak_status"}],
                "uncertainties": ["病例数字尚未公布"],
                "public_health_relevance": "indirect",
                "classification_confidence": 70,
            },
        }
        stats = run_quality_checks([row])
        self.assertEqual(stats["disease_numeric_gate_failures"], 0,
                         "未知数字保持未知不应触发 Gate")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    print("RESULT: PASS=%d FAIL=%d" % (n_run - n_fail, n_fail))
    sys.exit(1 if n_fail else 0)
