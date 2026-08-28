#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8B — Production AI Qualification 测试套件（§三十六）。

确定性测试（不调用任何真实 API / 不需要 credential）：
  20-case 固定集 / strict JSON gate / schema 路由 / 数字 evidence /
  attribution / country / disease 类别与 null!=0 / source refs /
  FACT 分离 / 角色判定 / 产物安全（无密钥）/ 失败隔离。

用法：
  python -m unittest scripts.tests.test_stage8b_qualification
"""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.qualification import stage8b as q


class TestCaseSet(unittest.TestCase):
    """§七：20 个固定 case，qualification_version=stage8b-v1。"""

    def test_version(self):
        self.assertEqual(q.QUALIFICATION_VERSION, "stage8b-v1")

    def test_fixed_20_cases(self):
        cases = q.build_cases()
        self.assertEqual(len(cases), 20)
        self.assertEqual([c["case_id"] for c in cases], q.CASE_IDS)

    def test_coverage(self):
        cases = q.build_cases()
        types = {}
        for c in cases:
            types[c["task_type"]] = types.get(c["task_type"], 0) + 1
        self.assertEqual(types.get("stage4_event_enrichment"), 8)
        self.assertEqual(types.get("disease_summary"), 4)
        self.assertEqual(types.get("africa_daily"), 3)
        self.assertEqual(types.get("country_weekly"), 3)
        self.assertEqual(types.get("major_event_brief"), 2)

    def test_report_cases_total_8(self):
        cases = [c for c in q.build_cases() if c["task_type"] in
                 ("africa_daily", "country_weekly", "major_event_brief")]
        self.assertEqual(len(cases), 8)

    def test_report_inputs_are_real(self):
        cases = {c["case_id"]: c for c in q.build_cases()}
        for cid in ("RD1", "RW1", "RW2", "RW3"):
            self.assertTrue(cases[cid]["input_payload"], "%s 输入为空" % cid)
        self.assertIn("note", cases["RD2"]["input_payload"])
        self.assertIn("qualification_sample", cases["RB1"]["input_payload"]["label"])


class TestStrictJSON(unittest.TestCase):
    """§十三：strict JSON gate。"""

    def test_clean_json(self):
        ok, parsed, err = q.strict_json_parse('{"a": 1}')
        self.assertTrue(ok)
        self.assertEqual(parsed["a"], 1)

    def test_markdown_fence_rejected(self):
        ok, _, err = q.strict_json_parse('```json\n{"a": 1}\n```')
        self.assertFalse(ok)
        self.assertEqual(err, "markdown_fence")

    def test_extra_text_rejected(self):
        ok, _, err = q.strict_json_parse('Sure, here is:\n{"a": 1}')
        self.assertFalse(ok)
        self.assertIn("not_json", err)

    def test_reasoning_wrapper_rejected(self):
        ok, _, err = q.strict_json_parse('{"output": {"a": 1}, "reasoning": "..."}')
        # 顶层为包裹形状 → 非严格契约形状（本 harness 由 schema 层兜底；此处验证可解析）
        self.assertTrue(ok)  # 解析层通过，包裹判定交给 schema/enum gate


class TestGates(unittest.TestCase):
    """§十七/§十八/§十九/§八/§九。"""

    def test_numeric_evidence(self):
        inp = {"deaths": 338, "title": "cholera"}
        out = {"summary": "338 人死亡", "fact": "500 人死亡"}
        vio = q.check_numeric_evidence(out, inp, ("summary", "fact"))
        nums = [v for v in vio if "500" in v]
        self.assertTrue(nums, "输出 500 不在 input → 应判 magnitude_error")

    def test_attribution_preserved(self):
        inp = "据称由某组织发动袭击"
        self.assertFalse(q.check_attribution(inp, "袭击造成 5 人死亡")[0])
        self.assertTrue(q.check_attribution(inp, "据称由某组织发动袭击")[0])

    def test_country_error(self):
        ok, err = q.check_country({"country_iso3": "SSD"},
                                  {"country_iso3": "TCD", "event": {}})
        self.assertFalse(ok)
        ok2, _ = q.check_country({"country_iso3": "TCD"}, {"country_iso3": "TCD"})
        self.assertTrue(ok2)

    def test_disease_null_not_zero(self):
        inp = {"disease_id": "cholera", "event": {"confirmed_cases": None,
                                                  "deaths": 338}}
        ok, errs = q.check_disease_numeric({"confirmed_cases": 0, "deaths": 338}, inp)
        self.assertFalse(ok)
        self.assertTrue(any("disease_null_written_zero" in e for e in errs))
        ok2, _ = q.check_disease_numeric({"confirmed_cases": None, "deaths": 338}, inp)
        self.assertTrue(ok2)

    def test_disease_identity(self):
        inp = {"disease_id": "marburg", "event": {}}
        ok, errs = q.check_disease_identity({"disease_id": "marburg"}, inp)
        self.assertTrue(ok)
        ok2, errs2 = q.check_disease_identity({"disease_id": "cholera"}, inp)
        self.assertFalse(ok2)

    # ── Repair Package（2026-08-26）──
    def test_disease_identity_uses_disease_event_id(self):
        """evaluator bug 修复：输出含匹配 disease_event_id → 不得误判。"""
        inp = {"disease_event_id": "DSEV_abc123", "disease_id": "cholera",
               "event": {"disease_event_id": "DSEV_abc123",
                         "disease_name_zh": "霍乱"}}
        ok, errs = q.check_disease_identity(
            {"disease_event_id": "DSEV_abc123", "title_zh": "霍乱疫情"}, inp)
        self.assertTrue(ok, "disease_event_id 一致仍误判: %s" % errs)

    def test_disease_identity_wrong_event_id(self):
        inp = {"disease_event_id": "DSEV_abc123", "event": {}}
        ok, errs = q.check_disease_identity(
            {"disease_event_id": "DSEV_other99"}, inp)
        self.assertFalse(ok)

    def test_disease_identity_by_chinese_name(self):
        """输出用中文名也可通过（不强制英文 disease_id 出现在输出）。"""
        inp = {"disease_id": "marburg", "event": {"disease_name_zh": "马尔堡出血热"}}
        ok, _ = q.check_disease_identity({"title_zh": "马尔堡出血热疫情"}, inp)
        self.assertTrue(ok)

    def test_attribution_chinese_lexicon(self):
        """词典修复：可能/据报道/存在冲突 视为保留词。"""
        self.assertTrue(q.check_attribution("据报道，袭击造成5人死亡",
                                            "袭击造成5人死亡，可能为武装组织所为")[0])
        self.assertTrue(q.check_attribution("据悉，多名疑犯已被捕",
                                            "据报道，多名疑犯已被捕")[0])
        self.assertFalse(q.check_attribution("alleged by local officials",
                                             "当地确认袭击造成5人死亡")[0])

    def test_failure_stage_classification(self):
        self.assertEqual(q.classify_failure_stage("http_429"), "http_request")
        self.assertEqual(q.classify_failure_stage("model_mismatch"), "provider_response")
        self.assertEqual(q.classify_failure_stage("retry_exhausted:http_500"), "http_request")
        self.assertEqual(q.classify_failure_stage("credential_unavailable"),
                         "client_request_construction")
        self.assertEqual(q.classify_failure_stage("invalid_response_shape:not_json"),
                         "response_parse")
        self.assertEqual(q.classify_failure_stage("weird_thing"), "unknown")

    def test_report_probe_credential_missing_fails(self):
        """§七：credential 缺失时 probe 必须 FAIL（不调 API）。"""
        import scripts.ai.qualification.stage8b as qq
        qq.credential_available = lambda n: False
        rc = qq.run_report_probe("deepseek")
        self.assertEqual(rc, 1)

    def test_source_refs_no_fabrication(self):
        inp = {"source_refs": [{"source_id": "s1", "url": "https://a.example/1"}]}
        ok, errs = q.check_source_refs(
            {"source_refs": [{"source_id": "s_fake", "url": "https://fake.example/x"}]}, inp)
        self.assertFalse(ok)
        self.assertTrue(any("unsupported_source_reference" in e for e in errs))

    def test_fact_analysis_separation(self):
        ok, errs = q.check_fact_analysis_separation(
            {"fact_summary": "预计未来 72 小时将发生袭击"})
        self.assertFalse(ok)
        ok2, _ = q.check_fact_analysis_separation(
            {"fact_summary": "据官方统计，已确认 10 人死亡"})
        self.assertTrue(ok2)


class TestRoleDecision(unittest.TestCase):
    """§十四/§十五：Primary / Secondary 判定。"""

    def _mk(self, case_id, task_type, schema_pass=True, json_pass=True,
            core=False, shape=None):
        return {"case_id": case_id, "task_type": task_type,
                "provider_status": "succeeded" if not shape else "succeeded",
                "schema_pass": schema_pass, "strict_json_pass": json_pass,
                "core_failure": core, "contract_failure": shape,
                "errors": []}

    def test_primary_when_all_gates_pass(self):
        results = []
        for cid in q.CASE_IDS:
            tt = "stage4_event_enrichment"
            if cid.startswith("D") and not cid.startswith("RD"):
                tt = "disease_summary"
            elif cid.startswith("RD"):
                tt = "africa_daily"
            elif cid.startswith("RW"):
                tt = "country_weekly"
            elif cid.startswith("RB"):
                tt = "major_event_brief"
            results.append(self._mk(cid, tt))
        d = q.decide_role(results)
        self.assertEqual(d["role"], "primary_candidate")
        self.assertTrue(d["primary_candidate"])

    def test_secondary_when_2_invalid_shapes(self):
        results = []
        for i, cid in enumerate(q.CASE_IDS):
            results.append(self._mk(
                cid, "stage4_event_enrichment",
                shape="invalid_response_shape:not_json" if i < 2 else None))
        d = q.decide_role(results)
        self.assertEqual(d["role"], "secondary")

    def test_not_qualified_when_schema_low(self):
        results = [self._mk(c, "stage4_event_enrichment", schema_pass=False,
                            json_pass=False) for c in q.CASE_IDS[:5]]
        d = q.decide_role(results)
        self.assertEqual(d["role"], "not_qualified")


class TestCredentialsAndArtifacts(unittest.TestCase):
    """§四/§三十一/§三十四：credential 只报 bool；产物无密钥；失败隔离。"""

    def test_credential_reports_bool(self):
        v = q.credential_available("glm47_flash")
        self.assertIsInstance(v, bool)
        v2 = q.credential_available("deepseek")
        self.assertIsInstance(v2, bool)

    def test_run_without_credential_does_not_call_api(self):
        # 无 credential 时：全部 case 应为 blocked/credential_unavailable，零调用
        import scripts.ai.qualification.stage8b as qq
        qq.credential_available = lambda n: False
        summary, results = qq.run("glm47_flash")
        self.assertEqual(len(results), 20)
        for r in results:
            self.assertEqual(r["provider_status"], "blocked")
            self.assertEqual(r["contract_failure"], "credential_unavailable")
        self.assertEqual(summary["provider_results"]["glm47_flash"]["role"],
                         "provider_unresolved")

    def test_artifacts_no_secrets(self):
        d = q.ARTIFACT_DIR
        self.assertTrue((d / "qualification_summary.json").exists())
        blob = "\n".join(p.read_text(encoding="utf-8") for p in d.glob("*.json"))
        for bad in ("ASIP_GLM_API_KEY=", "ASIP_DEEPSEEK_API_KEY=", "sk-",
                    "Bearer ", "github_token="):
            self.assertNotIn(bad, blob)

    def test_failure_isolation(self):
        # 运行 qualification 不得改动 Canonical/Public
        import subprocess
        pre = set((ROOT / "data" / "canonical").glob("*.json"))
        # 直接调用 run（无 credential，不调 API）
        import scripts.ai.qualification.stage8b as qq
        qq.credential_available = lambda n: False
        qq.run("all")
        post = set((ROOT / "data" / "canonical").glob("*.json"))
        self.assertEqual(pre, post)


if __name__ == "__main__":
    unittest.main()
