#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DeepSeek V4 Flash Provider（Stage 8B continuation，§二-§十一）。

只允许调用 ASIP Production 批准的模型：

    ALLOWED_DEEPSEEK_MODELS = { "deepseek-v4-flash" }

- base_url = https://api.deepseek.com（可显示；ASIP_DEEPSEEK_BASE_URL 可覆盖）
- 端点：{base_url}/chat/completions（OpenAI 兼容）
- 认证：Authorization: Bearer <ASIP_DEEPSEEK_API_KEY>（仅 os.environ，绝不落盘/
  runtime/artifact/log/repo/CLI 参数）
- model 固定 deepseek-v4-flash；任何其他模型（deepseek-v4-pro /
  deepseek-chat / deepseek-reasoner / 其他）→ raise unsupported_deepseek_model
  （配置错误，禁止 fallback / 自动选择 best available）
- response_format={"type":"json_object"}；prompt 侧由调用方强制 JSON-only
- returned_model 校验：响应明确返回非 flash 模型 → model_mismatch（case FAIL）
- Retry：仅 flash→flash，禁止跨模型 retry；429/5xx/timeout/connection 退避重试
- Telemetry：usage.input_tokens/output_tokens/total_tokens（缺失 → null）；
  billing_mode=paid（可变外部配置，不硬编码价格）；estimated_cost=null
- Thinking policy（显式，不依赖 DeepSeek 默认值——默认 thinking=enabled、
  reasoning_effort=high）：
    stage4_event_enrichment / disease_summary → thinking=disabled
    africa_daily / country_weekly / major_event_brief → thinking=enabled,
    reasoning_effort=low
  传参方式（裸 HTTP，等价 OpenAI SDK extra_body）：顶层
  "thinking":{"type":"enabled|disabled"} + "reasoning_effort":"low"
- Thinking enabled 时 temperature/top_p 等不产生实际效果（temperature_effective
  = false_when_thinking），保留兼容传参但不得宣称有效
- Response telemetry：finish_reason（stop/length/content_filter/...）、
  reasoning_content_present/length_chars（不落完整 CoT）、
  content_present/content_length_chars、reasoning_tokens
  （usage.completion_tokens_details.reasoning_tokens，缺失 → null）
- credential 缺失 → credential_status=missing / provider_status=unavailable，
  快速安全停止，不调用 API
"""

import json
import os
import random
import time
import urllib.error
import urllib.request

from ..provider import BaseAIProvider   # 相对导入，与 glm47/registry 一致（避免 ai. 别名双重基类）

ALLOWED_DEEPSEEK_MODELS = frozenset({"deepseek-v4-flash"})
FLASH_MODEL = "deepseek-v4-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com"
SECRET_NAME = "ASIP_DEEPSEEK_API_KEY"

# §二：显式 Thinking Policy（不依赖 DeepSeek 默认值）
THINKING_POLICY = {
    # task_type -> (thinking, reasoning_effort)
    "stage4_event_enrichment": ("disabled", None),
    "disease_summary": ("disabled", None),
    "africa_daily": ("enabled", "low"),
    "country_weekly": ("enabled", "low"),
    "major_event_brief": ("enabled", "low"),
}
DEFAULT_THINKING = "disabled"   # 未知 task_type 安全兜底（非思考）


class UnsupportedDeepSeekModelError(ValueError):
    """配置错误：请求了未批准的 DeepSeek 模型（§三）。"""


def _require_flash_model(model):
    if model not in ALLOWED_DEEPSEEK_MODELS:
        raise UnsupportedDeepSeekModelError(
            "unsupported_deepseek_model: %r（仅允许 %s）" % (
                model, sorted(ALLOWED_DEEPSEEK_MODELS)))


def credential_available():
    """§六：只报告 bool，不显示任何 key 信息。"""
    return bool(os.environ.get(SECRET_NAME, "").strip())


class DeepSeekV4FlashProvider(BaseAIProvider):
    """Stage 8B qualification 专用 Flash provider（OpenAI 兼容）。

    实现 BaseAIProvider 统一接口（registry 路由）；qualification runner 亦可直接使用。
    """

    name = "deepseek"

    def __init__(self, config=None, name=None, base_url=None, api_key=None,
                 model=None, timeout=180, max_retries=3, retry_backoff=(5, 15, 45)):
        # 兼容 BaseAIProvider(config, name) 与独立构造两种调用方式
        if name is None:
            name = self.name
        BaseAIProvider.__init__(self, config or {}, name=name)
        base_url = base_url or os.environ.get(
            "ASIP_DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get(SECRET_NAME, "")
        self.model = model if model is not None else FLASH_MODEL
        # §三：Flash-only 硬门禁（任何未批准模型 → 配置错误）
        _require_flash_model(self.model)
        self.timeout = int(os.environ.get("ASIP_DEEPSEEK_TIMEOUT_SECONDS", "180"))
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.credential_status = "present" if self.api_key else "missing"
        self.provider_status = "ok" if self.api_key else "unavailable"
        self.requested_model = self.model
        self._tasks = {}

    def validate_config(self):
        errors = []
        if self.model not in ALLOWED_DEEPSEEK_MODELS:
            errors.append("unsupported_deepseek_model: %s" % self.model)
        return errors

    def get_task_status(self, task_id):
        t = self._tasks.get(task_id) or {}
        return t.get("status")

    def load_result(self, task_id):
        t = self._tasks.get(task_id) or {}
        return t.get("result")

    def health_check(self):
        return {"provider": self.name, "model": self.model,
                "credential_status": self.credential_status,
                "provider_status": self.provider_status,
                "external_network": True, "base_url": self.base_url}

    # ── 供 qualification runner 使用的统一接口 ──
    def submit_task(self, task):
        task = dict(task or {})
        tid = task.get("task_id") or "?"
        if not self.api_key:
            return {"task_id": tid, "status": "blocked", "result": {
                "error": {"code": "credential_missing",
                          "message": "%s not set" % SECRET_NAME},
                "credential_status": "missing",
                "provider_status": "unavailable",
                "requested_model": self.model, "returned_model": None,
                "http_status": None, "attempt_count": 0,
                "token_usage_available": False,
                "input_tokens": None, "output_tokens": None, "total_tokens": None,
                "billing_mode": "paid", "estimated_cost": None}}
        system = task.get("system_text") or ""
        user = task.get("user_text") or ""
        # §二：显式 Thinking Policy（不再依赖 DeepSeek 默认 enabled/high）
        thinking, reasoning_effort = THINKING_POLICY.get(
            task.get("task_type"), (DEFAULT_THINKING, None))
        attempt = 0
        last_err = None
        last_info = None
        while attempt < self.max_retries:
            attempt += 1
            try:
                return self._call_api(system, user, tid, attempt,
                                      task.get("max_output_tokens"),
                                      thinking, reasoning_effort)
            except urllib.error.HTTPError as e:
                info = self._http_error_info(e)
                last_info = info
                last_err = "http_%s" % e.code
                if e.code in (429, 500, 502, 503, 504):
                    time.sleep(self._backoff(attempt))
                    continue
                return self._fail(tid, last_err, attempt, info)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last_err = "transport_error:%s" % type(e).__name__
                time.sleep(self._backoff(attempt))
                continue
            except Exception as e:
                return self._fail(tid, "provider_error:%s" % str(e)[:80], attempt)
        return self._fail(tid, "retry_exhausted:%s" % last_err, attempt, last_info)

    def _http_error_info(self, e):
        """§十一：捕获 HTTPError body，仅提取安全字段（不记录 Authorization/完整 payload）。"""
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:600]
        except Exception:
            body = ""
        info = {"http_status": e.code,
                "provider_error_type": None, "provider_error_code": None,
                "sanitized_error_message": None}
        try:
            d = json.loads(body) if body else {}
            err = d.get("error") if isinstance(d, dict) else None
            if isinstance(err, dict):
                info["provider_error_type"] = err.get("type")
                info["provider_error_code"] = err.get("code")
                info["sanitized_error_message"] = str(err.get("message") or "")[:300]
        except Exception:
            import re as _re
            cleaned = _re.sub(r"sk-[A-Za-z0-9]{16,}|Bearer\s+[A-Za-z0-9._-]{16,}",
                              "[redacted]", body)
            info["sanitized_error_message"] = cleaned[:300] or None
        return info

    def _backoff(self, attempt):
        base = self.retry_backoff[min(attempt - 1, len(self.retry_backoff) - 1)]
        return base + random.uniform(0, 1.5)

    def _call_api(self, system, user, tid, attempt, max_tokens=None,
                  thinking=None, reasoning_effort=None):
        thinking = thinking or DEFAULT_THINKING
        # §三/§四：裸 HTTP 等价 OpenAI SDK extra_body——顶层 thinking + reasoning_effort
        payload_dict = {
            "model": FLASH_MODEL,          # §二：固定 flash，绝不 fallback
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": 0.2,            # §四：thinking 时无效，兼容传参（见下）
            "response_format": {"type": "json_object"},   # §十
            "max_tokens": max_tokens,      # §八：按 task 预算，防无限输出/截断
            "thinking": {"type": thinking},  # 显式，不依赖默认值
        }
        if reasoning_effort:
            payload_dict["reasoning_effort"] = reasoning_effort
        payload = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions", data=payload,
            headers={"Authorization": "Bearer %s" % self.api_key,
                     "Content-Type": "application/json"},
            method="POST")
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
        latency = int((time.time() - t0) * 1000)
        data = json.loads(body)
        returned = data.get("model")
        # §四：returned_model 校验（明确返回其它模型 → model_mismatch）
        if returned and returned not in ALLOWED_DEEPSEEK_MODELS:
            return {"task_id": tid, "status": "failed",
                    "result": {"error": {"code": "model_mismatch",
                                         "message": "returned %s" % returned},
                               "credential_status": self.credential_status,
                               "provider_status": "ok",
                               "requested_model": FLASH_MODEL,
                               "returned_model": returned,
                               "http_status": getattr(resp, "status", 200),
                               "attempt_count": attempt,
                               "latency_ms": latency,
                               "token_usage_available": False,
                               "input_tokens": None, "output_tokens": None,
                               "total_tokens": None,
                               "billing_mode": "paid", "estimated_cost": None}}
        usage = data.get("usage") or {}
        usage_details = usage.get("completion_tokens_details") or {}
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content") or ""
        reasoning_content = message.get("reasoning_content") or ""
        finish_reason = choice.get("finish_reason")
        # §六/§七：telemetry——不落完整 CoT，仅存在性/长度/token 数
        reasoning_tokens = usage_details.get("reasoning_tokens")
        return {"task_id": tid, "status": "succeeded", "result": {
            "text": content,
            "credential_status": self.credential_status,
            "provider_status": "ok",
            "requested_model": FLASH_MODEL,
            "returned_model": returned or None,
            "http_status": getattr(resp, "status", 200),
            "attempt_count": attempt,
            "latency_ms": latency,
            "token_usage_available": bool(usage),
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "finish_reason": finish_reason,
            "reasoning_content_present": bool(reasoning_content),
            "reasoning_content_length_chars": len(reasoning_content) if reasoning_content else 0,
            "reasoning_tokens": reasoning_tokens,
            "content_present": bool(content),
            "content_length_chars": len(content),
            "thinking_requested": thinking,
            "reasoning_effort_requested": reasoning_effort,
            "temperature_effective": "false_when_thinking" if thinking == "enabled" else "true",
            "billing_mode": "paid",
            "estimated_cost": None,     # §十七：无可靠 billing 字段 → null
        }}

    def _fail(self, tid, err, attempt, info=None):
        info = info or {}
        return {"task_id": tid, "status": "failed",
                "result": {"error": {"code": err, "message": err},
                           "credential_status": self.credential_status,
                           "provider_status": self.provider_status,
                           "requested_model": FLASH_MODEL, "returned_model": None,
                           "http_status": info.get("http_status"),
                           "provider_error_type": info.get("provider_error_type"),
                           "provider_error_code": info.get("provider_error_code"),
                           "sanitized_error_message": info.get("sanitized_error_message"),
                           "attempt_count": attempt,
                           "token_usage_available": False,
                           "input_tokens": None, "output_tokens": None,
                           "total_tokens": None,
                           "billing_mode": "paid", "estimated_cost": None}}

    # ── smoke（§七）：最小 JSON 请求，验证连接与 Flash 模型 ──
    def smoke(self):
        """1 个最小请求；成功返回 {"status":"ok"} 型 JSON。"""
        if not self.api_key:
            return {"credential_available": False,
                    "result": "credential_injection_failed",
                    "requested_model": FLASH_MODEL, "returned_model": None,
                    "strict_json": False}
        system = "You are a connectivity test. Reply with JSON only, no markdown, no extra text."
        user = 'Reply with exactly this JSON: {"status": "ok"}'
        res = self.submit_task({"task_id": "SMOKE_FLASH", "system_text": system,
                                "user_text": user,
                                "task_type": "stage4_event_enrichment"})
        ok_status = (res.get("status") == "succeeded")
        rr = res.get("result") or {}
        returned = rr.get("returned_model")
        text = rr.get("text") or ""
        ok_json = False
        parsed = None
        try:
            parsed = json.loads(text.strip())
            ok_json = bool(parsed)
        except Exception:
            ok_json = False
        return {
            "credential_available": True,
            "http_status": rr.get("http_status"),
            "requested_model": FLASH_MODEL,
            "returned_model": returned,
            "returned_flash_ok": (returned is None or returned in ALLOWED_DEEPSEEK_MODELS),
            "strict_json": ok_json and ok_status,
            "status_body": parsed if ok_json else None,
            "result": "ok" if (ok_status and ok_json and returned in ALLOWED_DEEPSEEK_MODELS)
                      else ("model_mismatch" if (returned and returned not in ALLOWED_DEEPSEEK_MODELS)
                            else "failed"),
        }
