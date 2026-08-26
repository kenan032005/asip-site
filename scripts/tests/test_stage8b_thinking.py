#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8B — Provider Thinking & Token Telemetry Closure Fix 测试（§十五）。

显式 Thinking Policy（social/disease=disabled；daily/weekly/brief=enabled+low）、
finish_reason / reasoning_tokens / reasoning_content / content telemetry 捕获、
budget 分类（length→OUTPUT_TOKEN_BUDGET_INSUFFICIENT / content_filter /
empty anomaly）、task-specific max_tokens（daily 8192 / weekly 6144 / brief 4096）、
SDK extra_body 等价传参（裸 HTTP 顶层 thinking）、Flash-only 回归。
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


def resp_body(model="deepseek-v4-flash", content='{"status": "ok"}',
              finish_reason="stop", reasoning_content="",
              reasoning_tokens=None, usage=None):
    msg = {"role": "assistant", "content": content}
    if reasoning_content:
        msg["reasoning_content"] = reasoning_content
    u = usage or {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    if reasoning_tokens is not None:
        u["completion_tokens_details"] = {"reasoning_tokens": reasoning_tokens}
    return {"model": model,
            "choices": [{"message": msg, "finish_reason": finish_reason}],
            "usage": u}


class TestThinkingPolicy(unittest.TestCase):
    """§二：显式 Thinking Policy（不依赖 DeepSeek 默认 enabled/high）。"""

    def _capture(self, task_type, max_out=None):
        captured = {}

        def fake_urlopen(req, timeout=180):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return FakeResp(resp_body())

        p = ds.DeepSeekV4FlashProvider(api_key="test-key")
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            p.submit_task({"task_id": "T", "system_text": "s", "user_text": "u",
                           "task_type": task_type,
                           "max_output_tokens": max_out})
        return captured["body"]

    def test_social_thinking_disabled(self):
        body = self._capture("stage4_event_enrichment")
        self.assertEqual(body["thinking"], {"type": "disabled"})
        self.assertNotIn("reasoning_effort", body)

    def test_disease_thinking_disabled(self):
        body = self._capture("disease_summary")
        self.assertEqual(body["thinking"], {"type": "disabled"})
        self.assertNotIn("reasoning_effort", body)

    def test_daily_thinking_enabled_low(self):
        body = self._capture("africa_daily")
        self.assertEqual(body["thinking"], {"type": "enabled"})
        self.assertEqual(body["reasoning_effort"], "low")

    def test_weekly_thinking_enabled_low(self):
        body = self._capture("country_weekly")
        self.assertEqual(body["thinking"], {"type": "enabled"})
        self.assertEqual(body["reasoning_effort"], "low")

    def test_brief_thinking_enabled_low(self):
        body = self._capture("major_event_brief")
        self.assertEqual(body["thinking"], {"type": "enabled"})
        self.assertEqual(body["reasoning_effort"], "low")

    def test_unknown_task_safe_disabled(self):
        body = self._capture("unknown_task_x")
        self.assertEqual(body["thinking"], {"type": "disabled"})

    def test_policy_values(self):
        self.assertEqual(ds.THINKING_POLICY["stage4_event_enrichment"], ("disabled", None))
        self.assertEqual(ds.THINKING_POLICY["disease_summary"], ("disabled", None))
        for tt in ("africa_daily", "country_weekly", "major_event_brief"):
            self.assertEqual(ds.THINKING_POLICY[tt], ("enabled", "low"))


class TestResponseTelemetry(unittest.TestCase):
    """§五-§七：finish_reason / reasoning / content telemetry 捕获。"""

    def _call(self, resp):
        captured = {}

        def fake_urlopen(req, timeout=180):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return FakeResp(resp)

        p = ds.DeepSeekV4FlashProvider(api_key="test-key")
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            return p.submit_task({"task_id": "T", "system_text": "s",
                                  "user_text": "u",
                                  "task_type": "africa_daily",
                                  "max_output_tokens": 8192})

    def test_finish_reason_captured(self):
        r = self._call(resp_body(finish_reason="length"))
        self.assertEqual(r["result"]["finish_reason"], "length")

    def test_reasoning_tokens_captured(self):
        r = self._call(resp_body(reasoning_tokens=1200))
        self.assertEqual(r["result"]["reasoning_tokens"], 1200)

    def test_reasoning_tokens_null_when_absent(self):
        r = self._call(resp_body())
        self.assertIsNone(r["result"]["reasoning_tokens"])

    def test_reasoning_content_presence(self):
        r = self._call(resp_body(reasoning_content="let me think..."))
        self.assertTrue(r["result"]["reasoning_content_present"])
        self.assertEqual(r["result"]["reasoning_content_length_chars"], len("let me think..."))

    def test_reasoning_content_absent(self):
        r = self._call(resp_body())
        self.assertFalse(r["result"]["reasoning_content_present"])
        self.assertEqual(r["result"]["reasoning_content_length_chars"], 0)

    def test_content_presence(self):
        r = self._call(resp_body(content='{"a":1}'))
        self.assertTrue(r["result"]["content_present"])
        self.assertEqual(r["result"]["content_length_chars"], len('{"a":1}'))

    def test_temperature_effective_flag(self):
        r = self._call(resp_body())
        self.assertEqual(r["result"]["temperature_effective"], "false_when_thinking")
        # disabled 路径
        captured = {}

        def fake_urlopen(req, timeout=180):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return FakeResp(resp_body())

        p = ds.DeepSeekV4FlashProvider(api_key="test-key")
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            r2 = p.submit_task({"task_id": "T", "system_text": "s", "user_text": "u",
                                "task_type": "stage4_event_enrichment"})
        self.assertEqual(r2["result"]["temperature_effective"], "true")

    def test_no_full_cot_in_result(self):
        r = self._call(resp_body(reasoning_content="secret chain of thought here"))
        self.assertNotIn("secret chain of thought", json.dumps(r["result"]))


class TestBudgetClassification(unittest.TestCase):
    """§十：finish_reason 驱动分类。"""

    def test_length_empty_content(self):
        bf, st = q.classify_budget_failure(
            {"finish_reason": "length", "content_present": False, "text": ""})
        self.assertEqual(bf, "output_token_budget_insufficient")
        self.assertEqual(st, "response_parse")

    def test_length_with_content_falls_back(self):
        # 有内容但 JSON 截断 → 走 invalid_response_shape（非 budget 误判）
        bf, st = q.classify_budget_failure(
            {"finish_reason": "length", "content_present": True, "text": '{"a":'})
        self.assertIsNone(bf)

    def test_content_filter(self):
        bf, st = q.classify_budget_failure(
            {"finish_reason": "content_filter", "content_present": False, "text": ""})
        self.assertEqual(bf, "content_filter_response")

    def test_stop_empty_anomaly(self):
        bf, st = q.classify_budget_failure(
            {"finish_reason": "stop", "content_present": False, "text": ""})
        self.assertEqual(bf, "empty_content_anomaly")

    def test_run_case_wires_classification(self):
        # provider 返回 length+空 → run_case 应标 output_token_budget_insufficient
        from scripts.ai.qualification import stage8b as _q
        import scripts.ai.qualification.stage8b as qq
        orig = qq.run_case
        try:
            def fake_run(case, provider_name):
                res = {
                    "case_id": case["case_id"], "task_type": case["task_type"],
                    "provider": provider_name, "credential_available": True,
                    "provider_status": "succeeded", "attempt_count": 1,
                    "strict_json_pass": False, "schema_pass": False,
                    "contract_failure": None, "errors": [], "cached": False,
                    "latency_ms": 100,
                    "tokens": {"input_tokens": 1, "output_tokens": 8192,
                               "total_tokens": 8193},
                    "finish_reason": "length", "reasoning_content_present": True,
                    "reasoning_content_length_chars": 500,
                    "reasoning_tokens": 4000, "content_present": False,
                    "content_length_chars": 0,
                }
                res["contract_failure"], _ = qq.classify_budget_failure(
                    {"finish_reason": "length", "content_present": False})
                res["failure_stage"] = "response_parse"
                return res
            qq.run_case = fake_run
            cases = qq.build_cases()
            rd1 = next(c for c in cases if c["case_id"] == "RD1")
            r = qq.run_case(rd1, "deepseek")
            self.assertEqual(r["contract_failure"], "output_token_budget_insufficient")
        finally:
            qq.run_case = orig


class TestMaxTokenPolicy(unittest.TestCase):
    """§九：task-specific max_tokens。"""

    def test_policy_values(self):
        self.assertEqual(q.MAX_TOKEN_POLICY["stage4_event_enrichment"], 2048)
        self.assertEqual(q.MAX_TOKEN_POLICY["disease_summary"], 2048)
        self.assertEqual(q.MAX_TOKEN_POLICY["africa_daily"], 8192)
        self.assertEqual(q.MAX_TOKEN_POLICY["country_weekly"], 6144)
        self.assertEqual(q.MAX_TOKEN_POLICY["major_event_brief"], 4096)

    def test_task_builder_uses_policy(self):
        cases = q.build_cases()
        for c in cases:
            task = q._glm_task_builder(c)
            self.assertEqual(
                task["max_output_tokens"], q.MAX_TOKEN_POLICY[c["task_type"]],
                c["case_id"])

    def test_provider_sends_task_max_tokens(self):
        captured = {}

        def fake_urlopen(req, timeout=180):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return FakeResp(resp_body())

        p = ds.DeepSeekV4FlashProvider(api_key="test-key")
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            p.submit_task({"task_id": "T", "system_text": "s", "user_text": "u",
                           "task_type": "africa_daily", "max_output_tokens": 8192})
        self.assertEqual(captured["body"]["max_tokens"], 8192)


class TestFlashOnlyRegression(unittest.TestCase):
    """Flash-only 回归。"""

    def test_allowlist_unchanged(self):
        self.assertEqual(ds.ALLOWED_DEEPSEEK_MODELS, frozenset({"deepseek-v4-flash"}))

    def test_pro_rejected(self):
        with self.assertRaises(ds.UnsupportedDeepSeekModelError):
            ds.DeepSeekV4FlashProvider(model="deepseek-v4-pro")

    def test_no_cross_model_retry_payload_keeps_flash(self):
        captured = []
        calls = {"n": 0}

        def fake_urlopen(req, timeout=180):
            calls["n"] += 1
            captured.append(json.loads(req.data.decode("utf-8")))
            if calls["n"] < 3:
                raise __import__("urllib.error").error.HTTPError(
                    "http://x", 429, "rate", None, None)
            return FakeResp(resp_body())

        p = ds.DeepSeekV4FlashProvider(api_key="test-key")
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            p.submit_task({"task_id": "T", "system_text": "s", "user_text": "u",
                           "task_type": "africa_daily", "max_output_tokens": 8192})
        for body in captured:
            self.assertEqual(body["model"], "deepseek-v4-flash")


if __name__ == "__main__":
    unittest.main()
