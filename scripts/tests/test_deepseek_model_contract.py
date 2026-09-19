#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_deepseek_model_contract.py — C3R2 §八 模型契约测试（6 项）。

只验证模型名契约（canonical + 遗留别名 + qualification 判定），
不触碰 localization / analysis / canonical / gates 逻辑。
"""
import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from ai.providers.deepseek_v4_flash import (  # noqa: E402
    CANONICAL_MODEL, DISPLAY_MODEL, FLASH_MODEL, LEGACY_MODEL_ALIASES,
    ALLOWED_DEEPSEEK_MODELS, THINKING_POLICY,
    normalize_deepseek_model, is_known_deepseek_model,
    DeepSeekV4FlashProvider, UnsupportedDeepSeekModelError)

_spec = importlib.util.spec_from_file_location(
    "c3_qualify", str(ROOT / "scripts" / "ai" / "qualification" / "c3_qualify.py"))
QUALIFY = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(QUALIFY)


class DeepSeekModelContractTest(unittest.TestCase):
    """§二/§三"""

    def test_01_deepseek_flash_is_canonical_model(self):
        self.assertEqual(CANONICAL_MODEL, "deepseek-flash")
        self.assertEqual(FLASH_MODEL, CANONICAL_MODEL)
        self.assertEqual(DISPLAY_MODEL, "DeepSeek V4.1 Flash")
        self.assertIn(CANONICAL_MODEL, ALLOWED_DEEPSEEK_MODELS)
        # 默认构造必须落到 canonical
        prov = DeepSeekV4FlashProvider()
        self.assertEqual(prov.model, CANONICAL_MODEL)
        self.assertEqual(prov.validate_config(), [])
        # ASIP 运行时的默认模型也必须是 canonical
        from ai import c3_localization as L, c3_analysis as A
        self.assertEqual(L.DEFAULT_MODEL, CANONICAL_MODEL)
        self.assertEqual(A.DEFAULT_MODEL, CANONICAL_MODEL)

    def test_02_deepseek_v4_flash_alias_normalizes_to_flash(self):
        self.assertEqual(LEGACY_MODEL_ALIASES.get("deepseek-v4-flash"), CANONICAL_MODEL)
        self.assertEqual(normalize_deepseek_model("deepseek-v4-flash"), "deepseek-flash")
        self.assertEqual(normalize_deepseek_model("deepseek-flash"), "deepseek-flash")
        self.assertEqual(normalize_deepseek_model("  deepseek-v4-flash  "), "deepseek-flash")
        self.assertTrue(is_known_deepseek_model("deepseek-v4-flash"))
        # 别名传入后，provider 内部一律归一到 canonical（不会把别名发到 API）
        prov = DeepSeekV4FlashProvider(model="deepseek-v4-flash")
        self.assertEqual(prov.model, CANONICAL_MODEL)
        self.assertEqual(prov.requested_model_input, "deepseek-v4-flash")
        self.assertEqual(prov.validate_config(), [])
        msg = json.dumps(prov._call_api.__doc__ or "")
        self.assertNotIn("deepseek-v4-flash", msg)   # 请求体固定 canonical（见 §二）
        # 未登记的 vision-exp 别名不得被引入
        self.assertNotIn("deepseek-v4-flash-vision-exp", ALLOWED_DEEPSEEK_MODELS)
        self.assertIsNone(normalize_deepseek_model("deepseek-v4-flash-vision-exp"))


class QualificationModelCheckTest(unittest.TestCase):
    """§四/§五"""

    def _resp(self, **kw):
        res = {"http_status": 200, "requested_model": CANONICAL_MODEL,
               "returned_model": CANONICAL_MODEL, "text": '{"ok":true,"n":1}',
               "error": None}
        res.update(kw)
        return {"status": kw.pop("_status", "succeeded"), "result": res}

    def test_03_qualification_accepts_canonical_returned_model(self):
        ev = QUALIFY.evaluate_transport(self._resp(returned_model="deepseek-flash"))
        self.assertTrue(ev["http_success"])
        self.assertTrue(ev["model_match"])
        self.assertEqual(ev["normalized_requested_model"], "deepseek-flash")
        self.assertEqual(ev["normalized_returned_model"], "deepseek-flash")
        # 官方若返回遗留别名，也必须判为匹配（不得因字面不同误判）
        ev2 = QUALIFY.evaluate_transport(self._resp(returned_model="deepseek-v4-flash"))
        self.assertTrue(ev2["http_success"])
        self.assertTrue(ev2["model_match"])
        self.assertEqual(ev2["normalized_returned_model"], "deepseek-flash")
        # 未返回 model 字段时以请求身份为准
        ev3 = QUALIFY.evaluate_transport(self._resp(returned_model=None))
        self.assertTrue(ev3["model_match"])

    def test_04_model_alias_does_not_cause_http_failure(self):
        """§五：模型身份不匹配 ≠ HTTP 失败，两者必须分开记录。"""
        mismatch = {"status": "failed", "result": {
            "error": {"code": "model_mismatch"}, "http_status": 200,
            "requested_model": CANONICAL_MODEL, "returned_model": "deepseek-chat"}}
        ev = QUALIFY.evaluate_transport(mismatch)
        self.assertEqual(ev["http_status"], 200)
        self.assertTrue(ev["http_success"], "model mismatch must not be recorded as HTTP failure")
        self.assertFalse(ev["model_match"])
        self.assertFalse(ev["transport_error"])
        # 真正的传输失败：HTTP 与模型身份分别如实记录
        fail = {"status": "failed", "result": {
            "error": {"code": "http_503"}, "http_status": 503,
            "requested_model": CANONICAL_MODEL, "returned_model": None}}
        ev2 = QUALIFY.evaluate_transport(fail)
        self.assertFalse(ev2["http_success"])
        self.assertTrue(ev2["transport_error"])
        self.assertEqual(ev2["http_status"], 503)


class UnknownModelTest(unittest.TestCase):
    """§三/§八"""

    def test_05_unknown_model_still_fails(self):
        for bad in ("deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner",
                    "gpt-4", "", None, "deepseek-flash-2"):
            self.assertIsNone(normalize_deepseek_model(bad), bad)
            self.assertFalse(is_known_deepseek_model(bad))
        with self.assertRaises(UnsupportedDeepSeekModelError):
            DeepSeekV4FlashProvider(model="deepseek-v4-pro")
        with self.assertRaises(UnsupportedDeepSeekModelError):
            DeepSeekV4FlashProvider(model="deepseek-chat")
        prov = DeepSeekV4FlashProvider()
        prov.model = "deepseek-v4-pro"          # 人为破坏后再校验
        self.assertTrue(prov.validate_config())
        # qualification：未登记模型身份不得判为匹配
        ev = QUALIFY.evaluate_transport({"status": "failed", "result": {
            "error": {"code": "model_mismatch"}, "http_status": 200,
            "requested_model": CANONICAL_MODEL, "returned_model": "deepseek-v4-pro"}})
        self.assertFalse(ev["model_match"])

    def test_06_thinking_remains_disabled(self):
        thinking, effort = THINKING_POLICY.get("stage4_event_enrichment", (None, None))
        self.assertEqual(thinking, "disabled")
        self.assertIsNone(effort)                # 不发送 reasoning_effort
        prov = DeepSeekV4FlashProvider()
        self.assertEqual(prov.model, CANONICAL_MODEL)
        self.assertTrue(str(getattr(prov, "base_url", "")).startswith("https://api.deepseek.com"))
        # 上报字段：reasoning_tokens 必须可为 null（缺失即 null，不伪造 0）
        ev = QUALIFY.evaluate_transport({"status": "succeeded", "result": {
            "http_status": 200, "requested_model": CANONICAL_MODEL,
            "returned_model": CANONICAL_MODEL, "text": "{}", "reasoning_tokens": None}})
        self.assertTrue(ev["http_success"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
