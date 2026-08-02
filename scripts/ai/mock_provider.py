#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 — MockProvider（确定性离线 Provider）。

约束：
- 不访问网络；不需要 API Key；可在 CI 与 Fresh Clone 稳定运行；
- 可模拟：成功 / 超时 / 无效 JSON / 字段缺失 / API 错误 / Terminal 错误；
- 确定性：相同输入产生相同输出（可测试缓存幂等）；
- 输出 JSON 基于输入中的 event_id 等内容推导，并尽量符合 ai_enrichment schema。
"""

import hashlib
import json
import re
import time

from .stage4_provider import (
    Stage4Provider,
    ProviderTimeout,
    ProviderAPIError,
    ProviderTerminalError,
)
from .provider import BaseAIProvider

PROVIDER_NAME = "mock"


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class MockProvider(Stage4Provider, BaseAIProvider):
    """确定性 Mock。行为由 environment 或实例参数控制。

    同时兼容 Stage 2.5 的 BaseAIProvider 接口（validate_config / submit_task /
    get_task_status / load_result / health_check），以便注册进统一 registry。
    """

    provider_name = PROVIDER_NAME
    model_name = "mock-model-v1"

    def __init__(self, behavior=None, timeout=30, max_retries=2, delay_seconds=0.0):
        """
        behavior: None | dict，可含：
          - "timeout": bool              抛 ProviderTimeout
          - "invalid_json": bool         返回不可解析文本
          - "missing_fields": list       输出 JSON 中删除指定字段
          - "api_error": bool            抛 ProviderAPIError
          - "terminal_error": bool       抛 ProviderTerminalError
          - "language": str              输出语言标记
          - "minimal": bool              返回最小 JSON（仅 event_id）
        """
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
            raise ProviderTimeout("mock timeout (simulated)")
        if self.behavior.get("api_error"):
            raise ProviderAPIError("mock api error (simulated)")
        if self.behavior.get("terminal_error"):
            raise ProviderTerminalError("mock terminal error (simulated)")

        raw = self._build_response(prompt_text)

        if self.behavior.get("invalid_json"):
            raw = "THIS IS NOT JSON {{{ broken"

        parsed = None
        err = None
        if not self.behavior.get("invalid_json"):
            try:
                parsed = json.loads(raw)
            except Exception as e:  # pragma: no cover - 防御
                err = {"code": "JSON_PARSE_ERROR", "message": str(e)}

        # 模拟字段缺失：从 parsed 中删除
        missing = self.behavior.get("missing_fields") or []
        if parsed is not None and missing:
            for f in missing:
                parsed.pop(f, None)

        return {
            "ok": parsed is not None and err is None,
            "raw_text": raw,
            "parsed": parsed,
            "error": err,
            "token_usage": self.normalize_usage(),
            "raw_response_hash": _sha256(raw),
        }

    # ── 确定性响应构造 ─────────────────────────────────────────
    def _build_response(self, prompt_text):
        """从 prompt 文本中提取 event_id/country/title，构造确定性 JSON。"""
        event_id = self._extract(prompt_text, r'"event_id"\s*:\s*"(EVT_[0-9a-f]{16})"')
        country = self._extract(prompt_text, r'"country_iso3"\s*:\s*"([A-Z]{3})"')
        title = self._extract(prompt_text, r'"original_title"\s*:\s*"(.*?)"')
        if country is None:
            country = self._extract(prompt_text, r'"primary_country"\s*:\s*"(.*?)"')
        if title is None:
            title = "事件"

        lang = self.behavior.get("language", "fr")
        zh_title = self._zh_title(title, event_id, country)
        out = {
            "event_id": event_id,
            "canonical_run_id": "20260802T084000+0800_084349",
            "input_hash": _sha256(prompt_text[:4096]),
            "source_language": lang,
            "title_zh": zh_title,
            "summary_zh": "（Mock 摘要）该事件涉及安全相关信息，基于输入正文生成的中文摘要，"
                          "保留原文关键要素，不添加背景与预测。",
            "event_type": "other_security",
            "country_iso3": country,
            "location": {
                "country_iso3": country,
                "admin1": None,
                "city": None,
                "site": None,
                "raw_text": "",
            },
            "key_facts": [
                {
                    "fact": "（Mock）原文报道了该安全事件，具体要素以正式模型输出为准。",
                    "evidence_field": "body_extracted",
                    "evidence_excerpt": "",
                }
            ],
            "uncertainties": [],
            "security_relevance": "direct",
            "classification_confidence": 70,
            "ai_provider": "mock",
            "ai_model": self.model_name,
            "prompt_version": "1.0.0",
            "processed_at": "2026-08-02T12:00:00+08:00",
            "processing_status": "succeeded",
            "error_code": None,
        }
        out["raw_response_hash"] = _sha256(json.dumps(out, ensure_ascii=False))
        # minimal 模式：只保留 event_id
        if self.behavior.get("minimal"):
            return json.dumps({"event_id": event_id}, ensure_ascii=False)
        return json.dumps(out, ensure_ascii=False, indent=2)

    @staticmethod
    def _extract(text, pattern):
        m = re.search(pattern, text)
        return m.group(1) if m else None

    @staticmethod
    def _zh_title(title, event_id, country):
        if not title or title == "事件":
            return "安全事件简报" + (("（" + event_id[-6:] + "）") if event_id else "")
        t = title[:30]
        return t

    # ── Stage 2.5 BaseAIProvider 兼容接口（离线，不联网）──
    def validate_config(self):
        """BaseAIProvider 兼容：无敏感配置要求，始终可用。"""
        return []

    def submit_task(self, task):
        """BaseAIProvider 兼容：Mock 同步完成，返回带 status 的任务。"""
        task = dict(task or {})
        task["status"] = "completed"
        return task

    def get_task_status(self, task_id):
        return "completed"

    def load_result(self, task_id):
        return {"task_id": task_id, "status": "completed", "result": "mock"}

    def health_check(self):
        return {"ok": True, "network": False, "provider": "mock"}
