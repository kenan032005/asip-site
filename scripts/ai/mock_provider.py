#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 — MockProvider v2（只生成 semantic payload，元数据由 Processor 注入）。

支持模拟：
  - 纯合法 JSON
  - 代码围栏（```json）
  - 前置/后置解释
  - 双 JSON 对象
  - 元数据注入尝试（模型试图输出 ai_provider 等）
  - 错误国家 / 错误 event_id
  - 无效 JSON / 缺字段
  - 超时 / Retryable / Terminal 错误
"""

import hashlib
import json
import re
import time

from .stage4_provider import (
    Stage4Provider, ProviderTimeout, ProviderAPIError, ProviderTerminalError,
)
from .provider import BaseAIProvider
from .enrichment_validator import MODEL_OUTPUT_FIELDS

PROVIDER_NAME = "mock"


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class MockProvider(Stage4Provider, BaseAIProvider):
    """离线确定性 Mock。只生成 semantic payload。

    行为由 behavior dict 控制：
      "timeout" / "invalid_json" / "api_error" / "terminal_error"
      "code_fence"       → 返回含 ```json 围栏
      "prefix_text"      → 前置解释文字
      "suffix_text"      → 后置解释文字
      "double_json"      → 两个 JSON 对象
      "inject_metadata"  → 模型注入 event_id/ai_provider 等元数据
      "wrong_country"    → 返回错误的 country_iso3
      "wrong_event_id"   → 返回错误的 event_id
      "missing_fields"   → 从输出中删除指定字段列表
      "minimal"          → ���回最小 JSON（仅 event_id）
      "language": str     → source_language 值
    """

    provider_name = PROVIDER_NAME
    model_name = "mock-model-v1"

    def __init__(self, behavior=None, timeout=30, max_retries=2, delay_seconds=0.0):
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.behavior = behavior or {}
        self.delay_seconds = delay_seconds
        self.calls = 0

    # ── 公共接口 ──────────────────────────────────────────────
    def generate_structured(self, prompt_text):
        self.calls += 1
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)
        if self.behavior.get("timeout"):
            raise ProviderTimeout("mock timeout")
        if self.behavior.get("api_error"):
            raise ProviderAPIError("mock api error")
        if self.behavior.get("terminal_error"):
            raise ProviderTerminalError("mock terminal error")

        payload = self._build_payload(prompt_text)
        raw = self._wrap_output(payload)

        if self.behavior.get("invalid_json"):
            raw = "THIS IS NOT JSON {{{ broken"

        parsed = None
        err = None
        try:
            parsed = json.loads(raw)
        except Exception:
            err = {"code": "JSON_PARSE_ERROR", "message": "mock invalid json"}

        if parsed and self.behavior.get("missing_fields"):
            for f in self.behavior["missing_fields"]:
                parsed.pop(f, None)

        return {
            "ok": parsed is not None,
            "raw_text": raw,
            "parsed": parsed,
            "error": err,
            "token_usage": self.normalize_usage(),
            "raw_response_hash": _sha256(raw),
        }

    # ── 语义 payload 构造（仅 MODEL_OUTPUT_FIELDS）──
    def _build_payload(self, prompt_text):
        event_id = self._extract(prompt_text, r'"event_id"\s*:\s*"(EVT_[0-9a-f]{16})"')
        country = self._extract(prompt_text, r'"country_iso3"\s*:\s*"([A-Z]{3})"')
        title = self._extract(prompt_text, r'"original_title"\s*:\s*"(.*?)"')
        lang = self.behavior.get("language", "fr")

        # 故意错误
        if self.behavior.get("wrong_country"):
            country = "CHN"
        if self.behavior.get("wrong_event_id"):
            event_id = "EVT_0000000000000000"
            # 模型试图输出错误的 event_id
            extra_event_id = True
        else:
            extra_event_id = False

        zh_title = (title or "事件")[:30]
        payload = {
            "source_language": lang,
            "title_zh": zh_title + "（Mock）",
            "summary_zh": "（Mock 摘要）该事件涉及安全相关信息，基于输入正文生成的中文摘要。",
            "event_type": "other_security",
            "country_iso3": country,
            "location": {"country_iso3": country, "admin1": None,
                         "city": None, "site": None, "raw_text": ""},
            "key_facts": [{"fact": "（Mock）原文报道了该安全事件。",
                           "evidence_field": "body_extracted",
                           "evidence_excerpt": ""}],
            "uncertainties": [],
            "security_relevance": "direct",
            "classification_confidence": 70,
        }
        # 元数据注入模拟
        if self.behavior.get("inject_metadata"):
            payload["event_id"] = event_id
            payload["ai_provider"] = "hacked_provider"
            payload["ai_model"] = "hacked_model"
            payload["processing_status"] = "succeeded"
            payload["processed_at"] = "2099-01-01T00:00:00Z"
        if extra_event_id:
            payload["event_id"] = event_id  # 模型输出错误的 event_id
        return payload

    def _wrap_output(self, payload):
        raw = json.dumps(payload, ensure_ascii=False, indent=2)
        if self.behavior.get("minimal"):
            return json.dumps({"event_id": payload.get("event_id", "")})
        if self.behavior.get("code_fence"):
            return "```json\n" + raw + "\n```"
        if self.behavior.get("prefix_text"):
            return "Here is the result:\n" + raw
        if self.behavior.get("suffix_text"):
            return raw + "\nThis concludes the analysis."
        if self.behavior.get("double_json"):
            return raw + "\n" + raw
        return raw

    # ── 工具 ──────────────────────────────────────────────────
    @staticmethod
    def _extract(text, pattern):
        m = re.search(pattern, text)
        return m.group(1) if m else None

    def normalize_usage(self, raw_usage=None):
        return {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0}

    # ── BaseAIProvider 兼容 ────────────────────────────────────
    def validate_config(self):
        return []
    def submit_task(self, task):
        t = dict(task or {}); t["status"] = "completed"; return t
    def get_task_status(self, task_id):
        return "completed"
    def load_result(self, task_id):
        return {"task_id": task_id, "status": "completed", "result": "mock"}
    def health_check(self):
        return {"ok": True, "network": False, "provider": "mock"}
