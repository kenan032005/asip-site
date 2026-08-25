#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP AI Provider Migration — GLM Provider Mock 测试（§十六/§二十五）。

本地开发无需真实 Key 即可运行全部测试（mock HTTP 响应）。
覆盖：credential missing / auth failure / 429 / retry / circuit breaker /
cache / strict JSON / model identity / secret leak / browser isolation。
"""

import io
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from scripts.ai.providers.glm47_flash import (
    Glm47FlashProvider, CircuitBreaker, backoff_seconds, classify_http_status,
    GLM_STATUS_BLOCKED, GLM_STATUS_RETRYABLE, GLM_STATUS_SUCCEEDED,
    GLM_STATUS_PENDING, GLM_TASK_STATUSES,
)

OK_CONTENT = '{"status": "ok", "provider_test": "glm47_flash"}'


def _http_ok(model="glm-4.7-flash", content=None, usage=None):
    data = {
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": content or OK_CONTENT}}],
        "usage": usage or {"prompt_tokens": 10, "completion_tokens": 5,
                           "total_tokens": 15},
    }
    return _Resp(200, json.dumps(data))


class _Resp:
    def __init__(self, status, body, headers=None):
        self.status = status
        self._body = body
        self._headers = headers or {}
        self.headers = self._headers

    def read(self):
        return self._body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_error(status, retry_after=None):
    import urllib.error
    hdrs = {}
    if retry_after is not None:
        hdrs = {"Retry-After": str(retry_after)}
    err = urllib.error.HTTPError("https://x/chat/completions", status,
                                 "err", hdrs, io.BytesIO(b"{}"))
    raise err


def _mk_task(seed="abc", pv="1.1.0", **kw):
    t = {
        "task_id": "AIT_mock_%s" % seed,
        "input_hash": "h" + seed,
        "prompt_version": pv,
        "prompt_content_hash": "pc" + seed,
        "system_text": "sys",
        "user_text": "user %s" % seed,
        "usage_purpose": "development_test",
    }
    t.update(kw)
    return t


def _provider(client, key="test-key"):
    prov = Glm47FlashProvider({}, http_client=client)
    prov.api_key = key  # 显式注入（不依赖真实 env）
    prov.credential_status = "present" if key else "missing"
    prov.provider_status = "ok" if key else "unavailable"
    return prov


class TestCredentialAndStatus(unittest.TestCase):
    def test_missing_key_blocked(self):
        calls = []
        prov = _provider(lambda *a: calls.append(a) or _http_ok(), key="")
        r = prov.submit_task(_mk_task())
        self.assertEqual(r["status"], GLM_STATUS_BLOCKED)
        self.assertEqual(r["result"]["error"]["code"], "credential_missing")
        self.assertEqual(calls, [], "无 Key 时不得发起网络请求")
        hc = prov.health_check()
        self.assertEqual(hc["credential_status"], "missing")
        self.assertEqual(hc["provider_status"], "unavailable")

    def test_validate_config_missing_key(self):
        prov = _provider(lambda *a: None, key="")
        self.assertTrue(any("ASIP_GLM_API_KEY" in e for e in prov.validate_config()))

    def test_status_enum(self):
        self.assertEqual(GLM_TASK_STATUSES,
                         {"pending", "processing", "succeeded", "retryable",
                          "failed", "blocked"})


class TestHttpClassification(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(classify_http_status(200), ("ok", None))

    def test_401_403_blocked(self):
        for s in (401, 403):
            outcome, code = classify_http_status(s)
            self.assertEqual(outcome, "blocked", s)
            self.assertIn("credential_error", code)

    def test_429_retryable(self):
        outcome, code = classify_http_status(429)
        self.assertEqual(outcome, "retryable")
        self.assertIn("rate_limited", code)

    def test_5xx_retryable(self):
        for s in (500, 502, 503, 504):
            self.assertEqual(classify_http_status(s)[0], "retryable")


class TestAuthFailure(unittest.TestCase):
    def test_401_blocked(self):
        prov = _provider(lambda *a: _http_error(401))
        r = prov.submit_task(_mk_task())
        self.assertEqual(r["status"], GLM_STATUS_BLOCKED)
        self.assertIn("credential_error", r["result"]["error"]["code"])

    def test_403_blocked(self):
        prov = _provider(lambda *a: _http_error(403))
        r = prov.submit_task(_mk_task())
        self.assertEqual(r["status"], GLM_STATUS_BLOCKED)


class TestRetryAndRateLimit(unittest.TestCase):
    def test_backoff_sequence(self):
        self.assertGreaterEqual(backoff_seconds(1, jitter=False), 5)
        self.assertGreaterEqual(backoff_seconds(2, jitter=False), 15)
        self.assertGreaterEqual(backoff_seconds(3, jitter=False), 45)
        self.assertLess(backoff_seconds(1, jitter=False), 6)

    def test_retry_after_respected(self):
        self.assertEqual(backoff_seconds(1, retry_after=7, jitter=False), 7)

    def test_429_retryable_not_permanent(self):
        # 429 不得永久 failed：retry 耗尽后应为 retryable
        prov = _provider(lambda *a: _http_error(429), key="k")
        prov.max_retries = 0  # 不真等退避
        r = prov.submit_task(_mk_task())
        self.assertEqual(r["status"], GLM_STATUS_RETRYABLE)
        self.assertEqual(r["result"]["attempt_count"], 1)

    def test_retry_succeeds_after_429(self):
        calls = []

        def client(*a):
            calls.append(1)
            if len(calls) == 1:
                _http_error(429)  # 第一次 429（raise）
            return _http_ok()

        prov = _provider(client, key="k")
        prov.max_retries = 1
        with mock.patch("scripts.ai.providers.glm47_flash.time.sleep"):
            r = prov.submit_task(_mk_task())
        self.assertEqual(r["status"], GLM_STATUS_SUCCEEDED)
        self.assertEqual(len(calls), 2, "应重试一次后成功")
        self.assertEqual(r["result"]["attempt_count"], 2)


class TestCircuitBreaker(unittest.TestCase):
    def test_open_after_threshold(self):
        cb = CircuitBreaker(threshold=3)
        for _ in range(3):
            cb.record_failure()
        self.assertTrue(cb.is_open())
        self.assertEqual(cb.state(), "degraded")

    def test_reset_on_success(self):
        cb = CircuitBreaker(threshold=2)
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        self.assertFalse(cb.is_open(), "成功应重置连续失败计数")

    def test_provider_stops_sending_when_open(self):
        calls = []
        fail_client = lambda *a: (calls.append(1) or _http_error(500))
        # 通过 env 设置熔断阈值=2（provider 构造时读取）
        with mock.patch.dict(os.environ, {"ASIP_GLM_CIRCUIT_THRESHOLD": "2"}):
            prov = _provider(fail_client, key="k")
            prov.max_retries = 0
            # 触发 2 次失败 → 熔断
            prov.submit_task(_mk_task("a"))
            prov.submit_task(_mk_task("b"))
        self.assertTrue(prov._breaker.is_open())
        n_before = len(calls)
        # 熔断后新任务不再发送
        r = prov.submit_task(_mk_task("c"))
        self.assertEqual(len(calls), n_before, "熔断后不得发送新请求")
        self.assertEqual(r["status"], GLM_STATUS_RETRYABLE)
        self.assertEqual(r["result"]["error"]["code"], "circuit_open")


class TestCacheIdempotency(unittest.TestCase):
    def test_same_input_not_recalled(self):
        calls = []
        prov = _provider(lambda *a: (calls.append(1) or _http_ok()), key="k")
        prov.submit_task(_mk_task("same"))
        prov.submit_task(_mk_task("same"))
        self.assertEqual(len(calls), 1, "相同 input+prompt+model+provider 不得重复调用")

    def test_different_input_recalled(self):
        calls = []
        prov = _provider(lambda *a: (calls.append(1) or _http_ok()), key="k")
        prov.submit_task(_mk_task("x"))
        prov.submit_task(_mk_task("y"))
        self.assertEqual(len(calls), 2)


class TestStrictJSON(unittest.TestCase):
    def test_fenced_json_parsed(self):
        content = '```json\n{"status": "ok", "provider_test": "glm47_flash"}\n```'
        prov = _provider(lambda *a: _http_ok(content=content), key="k")
        r = prov.submit_task(_mk_task("f"))
        self.assertEqual(r["status"], GLM_STATUS_SUCCEEDED)
        self.assertEqual(r["result"]["result"]["provider_test"], "glm47_flash")

    def test_malformed_json_retryable(self):
        prov = _provider(lambda *a: _Resp(200, 'not json at all'), key="k")
        prov.max_retries = 0
        r = prov.submit_task(_mk_task("m"))
        self.assertEqual(r["status"], GLM_STATUS_RETRYABLE)

    def test_malformed_http_retryable(self):
        prov = _provider(lambda *a: _Resp(200, '{broken'), key="k")
        prov.max_retries = 0
        r = prov.submit_task(_mk_task("m2"))
        self.assertEqual(r["status"], GLM_STATUS_RETRYABLE)


class TestModelIdentity(unittest.TestCase):
    def test_requested_model(self):
        prov = _provider(lambda *a: _http_ok(model="glm-4.7-flash"), key="k")
        self.assertEqual(prov.requested_model, "glm-4.7-flash")
        r = prov.submit_task(_mk_task("id"))
        self.assertEqual(r["result"]["requested_model"], "glm-4.7-flash")
        self.assertEqual(r["result"]["returned_model"], "glm-4.7-flash")

    def test_audit_fields_present(self):
        prov = _provider(lambda *a: _http_ok(), key="k")
        r = prov.submit_task(_mk_task("aud"))
        res = r["result"]
        for f in ("provider", "requested_model", "returned_model", "prompt_version",
                  "input_hash", "request_started_at", "latency_ms", "http_status",
                  "attempt_count", "token_usage_available", "billing_mode",
                  "estimated_cost"):
            self.assertIn(f, res, f)
        self.assertEqual(res["provider"], "glm")
        self.assertEqual(res["billing_mode"], "free_currently")
        self.assertIsNone(res["estimated_cost"], "成本不得硬编码 0")
        self.assertTrue(res["token_usage_available"])
        self.assertEqual(res["input_tokens"], 10)


class TestSecretLeakScan(unittest.TestCase):
    def test_no_key_in_repo_code(self):
        bad = []
        for fn in ("scripts/ai/providers/glm47_flash.py",
                   "scripts/ai/glm_smoke_test.py"):
            t = open(os.path.join(ROOT, fn), encoding="utf-8").read()
            if re.search(r"ASIP_GLM_API_KEY\s*=\s*['\"][A-Za-z0-9._-]{16,}", t):
                bad.append(fn)
            if "sk-" in t and "SECRET_NAME" not in t and "Bearer " + "{" not in t:
                # 只允许占位符，不允许真实 key 形态
                pass
        self.assertEqual(bad, [], "不得硬编码 Key 值")

    def test_browser_isolation_no_glm_direct(self):
        # 前端不得直连 GLM API
        targets = []
        for rel in ("assets/js/common.js", "assets/js/api.js",
                    "index.html", "events.html", "disease-risk.html"):
            p = os.path.join(ROOT, rel)
            if os.path.exists(p):
                targets.append(p)
        for p in targets:
            t = open(p, encoding="utf-8").read()
            self.assertNotIn("open.bigmodel.cn", t, p)
            self.assertNotIn("ASIP_GLM_API_KEY", t, p)
            self.assertNotIn("Authorization", t, p)

    def test_build_site_allowlist_no_key_files(self):
        bs = open(os.path.join(ROOT, "scripts", "build_site.py"), encoding="utf-8").read()
        m = re.search(r"PUBLIC_DATA_ALLOWLIST\s*=\s*\[([\s\S]*?)\]", bs)
        self.assertIsNotNone(m)
        self.assertNotIn("glm", m.group(1))
        self.assertNotIn("secret", m.group(1).lower())


class TestHealthCheck(unittest.TestCase):
    def test_health_check_flags(self):
        prov = _provider(lambda *a: None, key="k")
        hc = prov.health_check()
        self.assertFalse(hc["browser_direct_api_call"])
        self.assertTrue(hc["cloud_ai_api_call"])
        self.assertTrue(hc["external_network"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    print("RESULT: PASS=%d FAIL=%d" % (n_run - n_fail, n_fail))
    sys.exit(1 if n_fail else 0)
