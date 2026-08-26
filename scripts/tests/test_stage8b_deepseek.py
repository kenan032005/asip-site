#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8B continuation — DeepSeek V4 Flash Qualification 测试（§二十七）。

Flash-only 硬门禁 / Pro·legacy 拒绝 / 无跨模型 retry / requested·returned_model
校验 / secret 注入只报 bool / secret 泄漏扫描 / workflow YAML 合规。
全部确定性测试，不调用真实 API（使用 mock urlopen）。
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.providers import deepseek_v4_flash as ds


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


def ok_body(model="deepseek-v4-flash", content='{"status": "ok"}', usage=None):
    return {"model": model,
            "choices": [{"message": {"role": "assistant", "content": content}}],
            "usage": usage or {"prompt_tokens": 10, "completion_tokens": 5,
                               "total_tokens": 15}}


class TestFlashOnlyGate(unittest.TestCase):
    """§三：Flash-only 硬门禁。"""

    def test_allowlist(self):
        self.assertEqual(ds.ALLOWED_DEEPSEEK_MODELS, frozenset({"deepseek-v4-flash"}))

    def test_pro_rejected(self):
        with self.assertRaises(ds.UnsupportedDeepSeekModelError) as ctx:
            ds.DeepSeekV4FlashProvider(model="deepseek-v4-pro")
        self.assertIn("unsupported_deepseek_model", str(ctx.exception))

    def test_legacy_models_rejected(self):
        for m in ("deepseek-chat", "deepseek-reasoner"):
            with self.assertRaises(ds.UnsupportedDeepSeekModelError):
                ds.DeepSeekV4FlashProvider(model=m)

    def test_no_alias_fallback(self):
        p = ds.DeepSeekV4FlashProvider()
        self.assertEqual(p.model, "deepseek-v4-flash")

    def test_base_url_displayable(self):
        p = ds.DeepSeekV4FlashProvider()
        self.assertTrue(p.base_url.startswith("https://api.deepseek.com"))


class TestRequestModel(unittest.TestCase):
    """§四：requested_model 固定 flash。"""

    def test_requested_model(self):
        p = ds.DeepSeekV4FlashProvider()
        self.assertEqual(p.requested_model, "deepseek-v4-flash")
        self.assertEqual(p.model, "deepseek-v4-flash")

    def test_payload_model_flash_only(self):
        captured = {}

        def fake_urlopen(req, timeout=180):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return FakeResp(ok_body())

        p = ds.DeepSeekV4FlashProvider(api_key="test-key")
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            p.submit_task({"task_id": "T", "system_text": "s", "user_text": "u",
                           "task_type": "stage4_event_enrichment"})
        self.assertEqual(captured["body"]["model"], "deepseek-v4-flash")
        self.assertEqual(captured["body"]["response_format"], {"type": "json_object"})


class TestNoCrossModelRetry(unittest.TestCase):
    """§十一：Retry 只能 flash→flash，不得跨模型。"""

    def test_retry_never_changes_model(self):
        captured = []
        calls = {"n": 0}

        def fake_urlopen(req, timeout=180):
            calls["n"] += 1
            captured.append(json.loads(req.data.decode("utf-8")))
            if calls["n"] < 3:
                raise __import__("urllib.error").error.HTTPError(
                    "http://x", 429, "rate", None, None)
            return FakeResp(ok_body())

        p = ds.DeepSeekV4FlashProvider(api_key="test-key", max_retries=3,
                                       retry_backoff=(0, 0, 0))
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            res = p.submit_task({"task_id": "T", "system_text": "s",
                                 "user_text": "u", "task_type": "africa_daily"})
        self.assertEqual(res["status"], "succeeded")
        self.assertGreaterEqual(len(captured), 3)
        for body in captured:
            self.assertEqual(body["model"], "deepseek-v4-flash",
                             "retry 跨模型（禁止）")


class TestReturnedModelVerification(unittest.TestCase):
    """§四：returned_model 明确返回其它模型 → model_mismatch FAIL。"""

    def test_returned_pro_is_fail(self):
        p = ds.DeepSeekV4FlashProvider(api_key="test-key")
        with mock.patch("urllib.request.urlopen",
                        return_value=FakeResp(ok_body(model="deepseek-v4-pro"))):
            res = p.submit_task({"task_id": "T", "system_text": "s",
                                 "user_text": "u", "task_type": "africa_daily"})
        self.assertEqual(res["status"], "failed")
        self.assertEqual(res["result"]["error"]["code"], "model_mismatch")
        self.assertEqual(res["result"]["returned_model"], "deepseek-v4-pro")

    def test_returned_flash_ok(self):
        p = ds.DeepSeekV4FlashProvider(api_key="test-key")
        with mock.patch("urllib.request.urlopen",
                        return_value=FakeResp(ok_body(model="deepseek-v4-flash"))):
            res = p.submit_task({"task_id": "T", "system_text": "s",
                                 "user_text": "u", "task_type": "africa_daily"})
        self.assertEqual(res["status"], "succeeded")
        self.assertEqual(res["result"]["returned_model"], "deepseek-v4-flash")


class TestCredentialAndSecrets(unittest.TestCase):
    """§六/§二十三：credential 只报 bool；产物零泄漏。"""

    def test_credential_bool(self):
        self.assertIsInstance(ds.credential_available(), bool)

    def test_smoke_credential_missing(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            p = ds.DeepSeekV4FlashProvider(api_key="")
            r = p.smoke()
        self.assertFalse(r["credential_available"])
        self.assertEqual(r["result"], "credential_injection_failed")

    def test_smoke_ok_shape(self):
        p = ds.DeepSeekV4FlashProvider(api_key="test-key")
        with mock.patch("urllib.request.urlopen",
                        return_value=FakeResp(ok_body(content='{"status": "ok"}'))):
            r = p.smoke()
        self.assertTrue(r["strict_json"])
        self.assertEqual(r["status_body"], {"status": "ok"})
        self.assertEqual(r["requested_model"], "deepseek-v4-flash")

    def test_secret_leak_scan_repo(self):
        pats = re.compile(
            r"sk-[A-Za-z0-9]{16,}|Bearer\s+[A-Za-z0-9._-]{16,}|"
            r"ASIP_DEEPSEEK_API_KEY\s*=\s*[A-Za-z0-9]", re.I)
        hits = []
        for p in (ROOT / "scripts" / "ai").rglob("*.py"):
            txt = p.read_text(encoding="utf-8", errors="ignore")
            for m in pats.finditer(txt):
                hits.append(str(p))
        self.assertEqual(hits, [])

    def test_no_key_in_qualification_artifacts(self):
        d = ROOT / "data" / "runtime" / "ai_qualification"
        if not d.exists():
            self.skipTest("无资质产物目录")
        blob = "\n".join(p.read_text(encoding="utf-8", errors="ignore")
                         for p in d.rglob("*.json"))
        for bad in ("sk-", "Bearer ", "ASIP_DEEPSEEK_API_KEY="):
            self.assertNotIn(bad, blob)


class TestWorkflowYAML(unittest.TestCase):
    """§十二：workflow_dispatch only；Secret 注入；无 model input。"""

    def setUp(self):
        self.wf = (ROOT / ".github" / "workflows" /
                   "asip-stage8b-qualification.yml").read_text(encoding="utf-8")

    def test_dispatch_only(self):
        self.assertNotIn("push:", self.wf)
        self.assertNotIn("schedule:", self.wf)
        self.assertNotIn("cron:", self.wf)
        self.assertIn("workflow_dispatch:", self.wf)

    def test_secret_env_injection(self):
        self.assertIn("${{ secrets.ASIP_DEEPSEEK_API_KEY }}", self.wf)

    def test_no_model_input(self):
        self.assertNotIn("deepseek-v4-pro", self.wf)
        self.assertNotIn("model:", self.wf)


if __name__ == "__main__":
    unittest.main()
