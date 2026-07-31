#!/usr/bin/env python3
"""ASIP Stage 2.5D/E — Generic OpenAI-Compatible API Provider

Sends Prompt Binding to an OpenAI-compatible API endpoint.
Supports: generic_api (env-configurable), openai_api (explicit entry).
"""

import os
import json
import urllib.request
import urllib.error
import ssl

from .base import BaseProvider, ProviderConfig


class GenericAPIProvider(BaseProvider):
    """OpenAI 兼容 API Provider。通过环境变量配置。"""

    def __init__(self, config=None):
        super().__init__(config or ProviderConfig("generic_api"))
        self.base_url = None
        self.api_key = None
        self.model = None
        self.timeout = 120
        self.max_output_tokens = 2048
        self._load_env()

    def _load_env(self, env=None):
        e = env or os.environ
        self.base_url = e.get("ASIP_AI_BASE_URL", "").rstrip("/")
        self.api_key = e.get("ASIP_AI_API_KEY", "")
        self.model = e.get("ASIP_AI_MODEL", "")
        self.timeout = int(e.get("ASIP_AI_TIMEOUT_SECONDS", "120"))
        self.max_output_tokens = int(
            e.get("ASIP_AI_MAX_OUTPUT_TOKENS", "2048"))

    def validate_config(self):
        if not self.config.processing_enabled:
            return False, "ASIP_AI_PROCESSING_ENABLED is false"
        if not self.base_url:
            return False, "ASIP_AI_BASE_URL not set"
        if not self.api_key:
            return False, "ASIP_AI_API_KEY not set"
        if not self.model:
            return False, "ASIP_AI_MODEL not set"
        return True, ""

    def process_binding(self, binding, budget):
        """调用 OpenAI 兼容 API 处理 Prompt Binding。"""
        url = self.base_url + "/chat/completions"
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": binding["system_text"]},
                {"role": "user", "content": binding["user_text"]},
            ],
            "temperature": 0.0,
            "max_tokens": self.max_output_tokens,
            "response_format": {"type": "json_object"},
        }, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            url, data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.api_key,
            },
            method="POST")

        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout,
                                        context=ctx) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            status = e.code
            body = e.read().decode("utf-8") if e.fp else ""
            return self._error_result(binding, "http_%d" % status,
                                      "HTTP %d from API" % status)
        except urllib.error.URLError as e:
            return self._error_result(binding, "connection_error",
                                      "API unreachable: %s" % e.reason)
        except Exception as e:
            return self._error_result(binding, "api_error",
                                      type(e).__name__)

        return self.parse_response(body, binding)

    def parse_response(self, raw, binding=None):
        """解析 OpenAI chat/completions 响应为标准化 AI Result。"""
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            return self._error_result(binding, "invalid_json",
                                      "API returned non-JSON")

        try:
            content_str = data["choices"][0]["message"]["content"]
            result_obj = json.loads(content_str)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            return self._error_result(binding, "parse_failed",
                                      type(e).__name__)

        usage = self.normalize_usage(data.get("usage", {}))
        tid = binding.get("task_id", "?") if binding else "?"
        return {
            "task_id": tid,
            "schema_version": "1.0",
            "status": "success",
            "provider": self.config.provider_type,
            "model": self.model,
            "started_at": "",
            "completed_at": "",
            "result": result_obj,
            "error": None,
            "usage": usage,
        }

    def normalize_usage(self, raw_usage):
        return {
            "input_tokens": int(raw_usage.get("prompt_tokens", 0)),
            "output_tokens": int(raw_usage.get("completion_tokens", 0)),
            "estimated_cost_usd": 0,
        }

    def _error_result(self, binding, code, message):
        tid = binding.get("task_id", "?") if binding else "?"
        return {
            "task_id": tid,
            "schema_version": "1.0",
            "status": "failed",
            "provider": self.config.provider_type,
            "model": self.model or "unknown",
            "started_at": "",
            "completed_at": "",
            "result": {},
            "error": {"code": code, "message": message[:200]},
            "usage": {"input_tokens": 0, "output_tokens": 0,
                      "estimated_cost_usd": 0},
        }

    def healthcheck(self):
        ok, msg = self.validate_config()
        if not ok:
            return False, msg
        return True, "generic_api: %s/%s" % (self.base_url, self.model)

    def __repr__(self):
        return "GenericAPIProvider(url=%s, model=%s)" % (
            self.base_url, self.model)
