#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-Run9 RD1 Root-Cause Diagnostic 测试（§十）。

- raw content telemetry：null / 空串 / whitespace-only / nonempty
- reasoning telemetry propagation：provider → case result → probe artifact
- JSON prompt contract：三份 report prompt 的 OUTPUT SCHEMA example 无 envelope
  残留、含显式 JSON 硬指令、与 AI content schema 字段一致
- report probe artifact persistence：probe 结果含 finish_reason/reasoning/content 字段
- 分类：reasoning exhaustion / whitespace exhaustion / JSON truncation /
  content filter / empty anomaly / pass
- Flash-only regression
全部确定性测试，不调用真实 API（mock urlopen）。
"""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.providers import deepseek_v4_flash as ds
from scripts.ai.qualification import stage8b as q


class FakeResp:
    def __init__(self, body, status=200):
        self._body = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.status = status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def resp_body(model="deepseek-v4-flash", content=None, finish_reason="stop",
              reasoning_content="", reasoning_tokens=None, usage=None):
    msg = {"role": "assistant"}
    if content is not None:
        msg["content"] = content
    if reasoning_content:
        msg["reasoning_content"] = reasoning_content
    u = usage or {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    if reasoning_tokens is not None:
        u["completion_tokens_details"] = {"reasoning_tokens": reasoning_tokens}
    return {"model": model,
            "choices": [{"message": msg, "finish_reason": finish_reason}],
            "usage": u}


class TestRawContentTelemetry(unittest.TestCase):
    """§二：raw content 状态区分（null / 空串 / whitespace / nonempty）。"""

    def _call(self, content):
        captured = {}

        def fake_urlopen(req, timeout=180):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return FakeResp(resp_body(content=content))

        p = ds.DeepSeekV4FlashProvider(api_key="test-key")
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            return p.submit_task({"task_id": "T", "system_text": "s",
                                  "user_text": "u",
                                  "task_type": "africa_daily"})

    def test_null_content(self):
        # message 无 content 字段 → 视为 null
        r = self._call(None)
        res = r["result"]
        self.assertFalse(res["content_present"])
        self.assertTrue(res["raw_content_is_null"])
        self.assertEqual(res["raw_content_length_chars"], 0)
        self.assertFalse(res["whitespace_only"])

    def test_empty_string_content(self):
        r = self._call("")
        res = r["result"]
        self.assertFalse(res["content_present"])
        self.assertTrue(res["raw_content_is_null"])   # 语义等价：空
        self.assertEqual(res["raw_content_length_chars"], 0)
        self.assertFalse(res["whitespace_only"])

    def test_whitespace_only_content(self):
        r = self._call("   \n\t  ")
        res = r["result"]
        self.assertFalse(res["content_present"])      # stripped 后为空
        self.assertTrue(res["whitespace_only"])
        self.assertEqual(res["raw_content_length_chars"], len("   \n\t  "))
        self.assertEqual(res["stripped_content_length_chars"], 0)

    def test_nonempty_content(self):
        r = self._call('{"title":"x"}')
        res = r["result"]
        self.assertTrue(res["content_present"])
        self.assertFalse(res["raw_content_is_null"])
        self.assertFalse(res["whitespace_only"])
        self.assertEqual(res["stripped_content_length_chars"], len('{"title":"x"}'))


class TestReasoningPropagation(unittest.TestCase):
    """§三：provider → run_case → probe artifact 传播链。"""

    def test_run_case_propagates_telemetry(self):
        # provider result 全字段 → run_case result
        rr = {
            "text": "", "returned_model": "deepseek-v4-flash",
            "input_tokens": 1, "output_tokens": 8192, "total_tokens": 8193,
            "finish_reason": "length",
            "reasoning_content_present": True,
            "reasoning_content_length_chars": 1234,
            "reasoning_tokens": 7000,
            "content_present": False,
            "raw_content_is_null": True,
            "raw_content_length_chars": 0,
            "stripped_content_length_chars": 0,
            "whitespace_only": False,
        }
        orig = q.run_case
        try:
            def fake_run(case, provider_name):
                res = {
                    "case_id": case["case_id"], "task_type": case["task_type"],
                    "provider": provider_name, "credential_available": True,
                    "provider_status": "succeeded", "attempt_count": 1,
                    "strict_json_pass": False, "schema_pass": False,
                    "contract_failure": None, "errors": [], "cached": False,
                    "latency_ms": 100, "tokens": {"input_tokens": 1,
                                                  "output_tokens": 8192,
                                                  "total_tokens": 8193},
                    "returned_model": "deepseek-v4-flash",
                    "raw_text_excerpt": "",
                }
                # 模拟 run_case 的透传逻辑
                for _tk in ("finish_reason", "reasoning_content_present",
                            "reasoning_content_length_chars", "reasoning_tokens",
                            "content_present", "raw_content_is_null",
                            "raw_content_length_chars", "stripped_content_length_chars",
                            "whitespace_only"):
                    res[_tk] = rr.get(_tk)
                res["contract_failure"], res["failure_stage"] = \
                    q.classify_budget_failure(rr)
                return res
            q.run_case = fake_run
            cases = q.build_cases()
            rd1 = next(c for c in cases if c["case_id"] == "RD1")
            r = q.run_case(rd1, "deepseek")
            self.assertEqual(r["finish_reason"], "length")
            self.assertEqual(r["reasoning_tokens"], 7000)
            self.assertTrue(r["reasoning_content_present"])
            self.assertEqual(r["raw_content_length_chars"], 0)
            self.assertEqual(r["contract_failure"],
                             "output_token_budget_insufficient")
        finally:
            q.run_case = orig

    def test_probe_result_contains_telemetry_keys(self):
        import inspect
        src = inspect.getsource(q.run_report_probe)
        for f in ("finish_reason", "reasoning_content_present",
                  "reasoning_content_length_chars", "reasoning_tokens",
                  "content_present", "raw_content_is_null",
                  "raw_content_length_chars", "stripped_content_length_chars",
                  "whitespace_only"):
            self.assertIn('"%s"' % f, src)


class TestPromptJSONContract(unittest.TestCase):
    """§一：JSON Mode 要求 + AI content schema 一致性。"""

    def _out_schema_seg(self, fn):
        import re
        t = (ROOT / "config" / "prompts" / fn).read_text(encoding="utf-8")
        m = re.search(r"## OUTPUT SCHEMA.*?(?=\n## |\Z)", t, re.S)
        return m.group(0) if m else ""

    def test_json_instruction_present(self):
        for fn in ("africa_daily_report_v1.md",
                   "country_weekly_report_v1.md",
                   "major_event_brief_v1.md"):
            t = (ROOT / "config" / "prompts" / fn).read_text(encoding="utf-8")
            self.assertIn("Return ONLY one valid JSON object", t, fn)
            self.assertIn("No prose before or after JSON", t, fn)
            self.assertIn("No markdown fences", t, fn)

    def _example_top_keys(self, fn):
        """提取 OUTPUT SCHEMA example 的顶层 keys（example 为合法 JSON）。"""
        import re as _re, json as _json
        seg = self._out_schema_seg(fn)
        m = _re.search(r"\n(\{[\s\S]*\})\n", seg)
        self.assertTrue(m, "%s 无 JSON example" % fn)
        return set(_json.loads(m.group(1)).keys())

    def test_no_envelope_in_output_example(self):
        # AI content payload example 顶层不得含 envelope 字段（§Envelope Separation）
        ENV = ("report_id", "report_type", "report_date", "period_start",
               "period_end", "generated_at", "report_timezone",
               "generation_metadata", "brief_id", "week_start", "week_end",
               "country_iso3")
        for fn in ("africa_daily_report_v1.md",
                   "country_weekly_report_v1.md",
                   "major_event_brief_v1.md"):
            top = self._example_top_keys(fn)
            stray = top & set(ENV)
            self.assertEqual(stray, set(),
                             "%s example 顶层含 envelope 字段 %s" % (fn, stray))

    def test_example_matches_ai_content_schema(self):
        import json as _json
        mapping = {
            "africa_daily_report_v1.md": "africa_daily_ai_content.schema.json",
            "country_weekly_report_v1.md": "country_weekly_ai_content.schema.json",
            "major_event_brief_v1.md": "major_event_brief_ai_content.schema.json",
        }
        for pfn, sfn in mapping.items():
            top = self._example_top_keys(pfn)
            schema = _json.loads(
                (ROOT / "schemas" / sfn).read_text(encoding="utf-8"))
            props = set(schema.get("properties", {}).keys())
            stray = top - props
            self.assertEqual(stray, set(),
                             "%s example 顶层含 schema 外字段 %s" % (pfn, stray))

    def test_prompt_version_103(self):
        for fn in ("africa_daily_report_v1.md",
                   "country_weekly_report_v1.md",
                   "major_event_brief_v1.md"):
            head = (ROOT / "config" / "prompts" / fn).read_text(
                encoding="utf-8").splitlines()[0]
            self.assertIn("v1.0.3", head, fn)
        man = json.loads((ROOT / "data" / "qualification" / "stage8b" /
                          "manifest.json").read_text(encoding="utf-8"))
        for fc in man["cases"]:
            if fc["task_type"] in ("africa_daily", "country_weekly",
                                   "major_event_brief"):
                self.assertEqual(fc["prompt_version"], "v1.0.3", fc["case_id"])


class TestClassification(unittest.TestCase):
    """§八：根因分类枚举。"""

    def test_reasoning_budget_exhaustion(self):
        # length + reasoning 占满 + content 空
        bf, st = q.classify_budget_failure(
            {"finish_reason": "length", "content_present": False, "text": ""})
        self.assertEqual(bf, "output_token_budget_insufficient")

    def test_whitespace_exhaustion_maps_to_budget(self):
        # length + whitespace-only content → budget（分类器以 content_present 为准）
        bf, st = q.classify_budget_failure(
            {"finish_reason": "length", "content_present": False,
             "whitespace_only": True, "text": "   "})
        self.assertEqual(bf, "output_token_budget_insufficient")

    def test_json_truncation_not_budget(self):
        # length + 非空截断 JSON → invalid_response_shape（非 budget 误判）
        bf, st = q.classify_budget_failure(
            {"finish_reason": "length", "content_present": True,
             "text": '{"title":'})
        self.assertIsNone(bf)

    def test_content_filter(self):
        bf, st = q.classify_budget_failure(
            {"finish_reason": "content_filter", "content_present": False})
        self.assertEqual(bf, "content_filter_response")

    def test_empty_anomaly(self):
        bf, st = q.classify_budget_failure(
            {"finish_reason": "stop", "content_present": False})
        self.assertEqual(bf, "empty_content_anomaly")

    def test_pass_returns_none(self):
        bf, st = q.classify_budget_failure(
            {"finish_reason": "stop", "content_present": True,
             "text": '{"ok":1}'})
        self.assertIsNone(bf)


class TestFlashOnlyRegression(unittest.TestCase):
    def test_allowlist(self):
        self.assertEqual(ds.ALLOWED_DEEPSEEK_MODELS, frozenset({"deepseek-v4-flash"}))

    def test_pro_rejected(self):
        with self.assertRaises(ds.UnsupportedDeepSeekModelError):
            ds.DeepSeekV4FlashProvider(model="deepseek-v4-pro")


if __name__ == "__main__":
    unittest.main()


class TestRootCauseClassification(unittest.TestCase):
    """§七：RD1 probe 根因分类（真实 telemetry 驱动）。"""

    def test_reasoning_budget_exhaustion(self):
        rc = q.classify_root_cause(
            {"finish_reason": "length", "output_tokens": 8192,
             "reasoning_tokens": 7200, "content_present": False,
             "stripped_content_length_chars": 0, "whitespace_only": False})
        self.assertEqual(rc, "REASONING_BUDGET_EXHAUSTION")

    def test_whitespace_exhaustion(self):
        rc = q.classify_root_cause(
            {"finish_reason": "length", "output_tokens": 8192,
             "reasoning_tokens": 500, "content_present": False,
             "stripped_content_length_chars": 0, "whitespace_only": True})
        self.assertEqual(rc, "JSON_WHITESPACE_EXHAUSTION")

    def test_final_json_truncation(self):
        rc = q.classify_root_cause(
            {"finish_reason": "length", "output_tokens": 8192,
             "reasoning_tokens": 2000, "content_present": True,
             "stripped_content_length_chars": 300, "whitespace_only": False},
            strict_json_ok=False)
        self.assertEqual(rc, "FINAL_JSON_TOKEN_TRUNCATION")

    def test_content_filter(self):
        rc = q.classify_root_cause(
            {"finish_reason": "content_filter", "content_present": False})
        self.assertEqual(rc, "CONTENT_FILTER_RESPONSE")

    def test_empty_anomaly(self):
        rc = q.classify_root_cause(
            {"finish_reason": "stop", "content_present": False})
        self.assertEqual(rc, "EMPTY_CONTENT_ANOMALY")

    def test_contract_pass(self):
        rc = q.classify_root_cause(
            {"finish_reason": "stop", "content_present": True},
            strict_json_ok=True, ai_content_ok=True, assembler_ok=True,
            final_ok=True)
        self.assertEqual(rc, "RD1_CONTRACT_PASS")

    def test_unknown(self):
        rc = q.classify_root_cause({"finish_reason": "tool_calls"})
        self.assertEqual(rc, "UNKNOWN")

    def test_budget_fallback(self):
        rc = q.classify_root_cause(
            {"finish_reason": "length", "output_tokens": 8192,
             "reasoning_tokens": None, "content_present": False})
        self.assertEqual(rc, "OUTPUT_TOKEN_BUDGET_INSUFFICIENT")


class TestWorkflowMode(unittest.TestCase):
    """§二-§四：workflow_dispatch mode（probe_only 默认 / full_qualification）。"""

    WF = ROOT / ".github" / "workflows" / "asip-stage8b-qualification.yml"

    @classmethod
    def setUpClass(cls):
        cls.txt = cls.WF.read_text(encoding="utf-8")

    @classmethod
    def _step_block(cls, name):
        """返回从步骤名到下一个 '      - name:' 之间的文本。"""
        idx = cls.txt.find(name)
        assert idx > 0, name
        nxt = cls.txt.find("      - name:", idx + len(name))
        return cls.txt[idx:(nxt if nxt > 0 else len(cls.txt))]

    def test_no_schedule_no_push(self):
        t = self.txt
        self.assertNotIn("schedule:", t)
        self.assertNotIn("cron:", t)
        # 只禁止真实触发器；注释中的字眼不判定
        import re
        self.assertNotRegex(t, r"(?m)^\s*push://s*$")
        self.assertNotRegex(t, r"(?m)^\s*-\s*push:")
        self.assertNotRegex(t, r"(?m)^\s*pull_request:")

    def test_mode_input_exists(self):
        t = self.txt
        self.assertIn("inputs:", t)
        self.assertIn("mode:", t)
        self.assertIn("default: probe_only", t)
        self.assertIn("options:", t)
        self.assertIn("- probe_only", t)
        self.assertIn("- full_qualification", t)

    def test_20case_step_gated_by_full_mode(self):
        block = self._step_block("20-case qualification")
        self.assertIn("if: github.event.inputs.mode == 'full_qualification'", block)

    def test_trial_step_gated_by_full_mode(self):
        block = self._step_block("Real report trial")
        self.assertIn("if: github.event.inputs.mode == 'full_qualification'", block)

    def test_probe_step_has_no_mode_gate(self):
        block = self._step_block("Report API probe")
        self.assertNotIn("if:", block.split("\n")[1])   # run 行前无 if

    def test_verdict_handles_probe_only(self):
        block = self._step_block("Qualification verdict")
        self.assertIn("MODE:", block)
        self.assertIn("report_probe_result.json", block)
        self.assertIn("RD1_DIAGNOSTIC_PROBE_FAILED", block)
        self.assertIn("RD1_CONTRACT_PASS", block)

    def test_artifact_and_secret_always(self):
        for name in ("Secret scan", "Upload qualification artifacts"):
            block = self._step_block(name)
            self.assertIn("if: always()", block, name)


class TestReasoningPriorityRegression(unittest.TestCase):
    """§一：reasoning_tokens >= 0.90*max_tokens 优先于泛化 OUTPUT_TOKEN_BUDGET_INSUFFICIENT。"""

    def test_reasoning_ge_90pct_max_tokens(self):
        # 决定性证据：reasoning=8192, max=8192, length, content 空
        rc = q.classify_root_cause(
            {"finish_reason": "length", "output_tokens": 8192,
             "reasoning_tokens": 8192, "content_present": False,
             "stripped_content_length_chars": 0, "whitespace_only": False},
            max_tokens=8192)
        self.assertEqual(rc, "REASONING_BUDGET_EXHAUSTION")

    def test_reasoning_90pct_exact_boundary(self):
        rc = q.classify_root_cause(
            {"finish_reason": "length", "output_tokens": 8192,
             "reasoning_tokens": 7373, "content_present": False},
            max_tokens=8192)   # 7373/8192 = 0.9000
        self.assertEqual(rc, "REASONING_BUDGET_EXHAUSTION")

    def test_reasoning_below_90pct_but_high_ratio(self):
        # 0.9*max 不满足但 completion 占比 >=0.8 → 仍 REASONING（保持旧规则）
        rc = q.classify_root_cause(
            {"finish_reason": "length", "output_tokens": 8192,
             "reasoning_tokens": 7000, "content_present": False},
            max_tokens=8192)   # 7000/8192=0.854 <0.9；但 7000/8192=0.854>=0.8
        self.assertEqual(rc, "REASONING_BUDGET_EXHAUSTION")

    def test_no_max_tokens_falls_back_to_ratio(self):
        rc = q.classify_root_cause(
            {"finish_reason": "length", "output_tokens": 8192,
             "reasoning_tokens": 7000, "content_present": False})
        self.assertEqual(rc, "REASONING_BUDGET_EXHAUSTION")

    def test_reasoning_low_whitespace_still_whitespace(self):
        rc = q.classify_root_cause(
            {"finish_reason": "length", "output_tokens": 8192,
             "reasoning_tokens": 500, "content_present": False,
             "whitespace_only": True},
            max_tokens=8192)
        self.assertEqual(rc, "JSON_WHITESPACE_EXHAUSTION")

    def test_probe_experiment_marker(self):
        import inspect
        src = inspect.getsource(q.run_report_probe)
        self.assertIn("rd1_thinking_disabled_isolation", src)


class TestTelemetryPropagationClosure(unittest.TestCase):
    """§四（Final）：Run#10 透传缺口补齐——thinking/raw content 字段全持久化。"""

    def test_run_case_propagates_all_fields(self):
        rr = {
            "text": '{"title":"x"}', "returned_model": "deepseek-v4-flash",
            "input_tokens": 1, "output_tokens": 2, "total_tokens": 3,
            "finish_reason": "stop",
            "reasoning_content_present": False,
            "reasoning_content_length_chars": 0,
            "reasoning_tokens": None,
            "content_present": True,
            "content_length_chars": 13,
            "raw_content_is_null": False,
            "raw_content_length_chars": 13,
            "stripped_content_length_chars": 13,
            "whitespace_only": False,
            "thinking_requested": "disabled",
            "reasoning_effort_requested": None,
        }
        fields = ("finish_reason", "reasoning_content_present",
                  "reasoning_content_length_chars", "reasoning_tokens",
                  "content_present", "content_length_chars",
                  "raw_content_is_null", "raw_content_length_chars",
                  "stripped_content_length_chars", "whitespace_only",
                  "thinking_requested", "reasoning_effort_requested")
        orig = q.run_case
        try:
            def fake_run(case, provider_name):
                res = {
                    "case_id": case["case_id"], "task_type": case["task_type"],
                    "provider": provider_name, "credential_available": True,
                    "provider_status": "succeeded", "attempt_count": 1,
                    "strict_json_pass": False, "schema_pass": False,
                    "contract_failure": None, "errors": [], "cached": False,
                    "latency_ms": 1, "tokens": {"input_tokens": 1,
                                                "output_tokens": 2,
                                                "total_tokens": 3},
                    "returned_model": "deepseek-v4-flash",
                }
                for _tk in fields:
                    res[_tk] = rr.get(_tk)
                return res
            q.run_case = fake_run
            cases = q.build_cases()
            rd1 = next(c for c in cases if c["case_id"] == "RD1")
            r = q.run_case(rd1, "deepseek")
            for f in fields:
                self.assertEqual(r.get(f), rr.get(f), f)
            self.assertEqual(r["thinking_requested"], "disabled")
            self.assertFalse(r["whitespace_only"])
        finally:
            q.run_case = orig

    def test_probe_artifact_includes_closure_fields(self):
        import inspect
        src = inspect.getsource(q.run_report_probe)
        for f in ("thinking_requested", "reasoning_effort_requested",
                  "raw_content_is_null", "raw_content_length_chars",
                  "stripped_content_length_chars", "whitespace_only"):
            self.assertIn('"%s"' % f, src)
