#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP AI Provider Migration — GLM-4.7-Flash Provider（§五-§十四）。

生产 AI 目标：智谱 BigModel OpenAI 兼容接口。
  base_url: https://open.bigmodel.cn/api/paas/v4（配置化，env ASIP_GLM_BASE_URL 可覆盖）
  endpoint: {base_url}/chat/completions
  auth:     Authorization: Bearer <ASIP_GLM_API_KEY>

安全约束：
- 唯一正式 Secret 名：ASIP_GLM_API_KEY（os.environ 读取，绝不 hardcode/写 runtime/
  repo/日志/audit/dist/gh-pages/前端 JS/CLI 参数）；
- Key 缺失 → credential_status=missing、provider_status=unavailable、安全停止；
- 不自动 fallback 到其他付费模型或 WorkBuddy；
- 浏览器不得直连（browser_direct_api_call=false 由配置与前端共同保证）。

任务状态（§九）：pending/processing/succeeded/retryable/failed/blocked
- HTTP 429 / 5xx / timeout / connection error → retryable
- HTTP 401 / 403 → blocked（credential_error）
- 解析失败 → failed（invalid_output），不进入 Public

Retry（§十）：max_retries=3，退避 5s/15s/45s + jitter；尊重服务端 Retry-After。
熔断（§十一）：同一 run 连续 5 次 provider 级失败 → provider_status=degraded，
停止新请求；未处理任务保持 pending/retryable；下次 run 重新尝试。
Cache（§十二）：复用 input_hash+prompt_version+model+provider → result_id；
命中已有成功结果则不重复调用 API。
审计字段（§十四）：requested/returned_model、latency_ms、http_status、
attempt_count、token_usage_available、billing_mode=free_currently、
estimated_cost=null（不得硬编码 0 成本）。
"""

import http.client
import json
import os
import random
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from ..provider import BaseAIProvider

# ── §九 任务状态 ──
GLM_STATUS_PENDING = "pending"
GLM_STATUS_PROCESSING = "processing"
GLM_STATUS_SUCCEEDED = "succeeded"
GLM_STATUS_RETRYABLE = "retryable"
GLM_STATUS_FAILED = "failed"
GLM_STATUS_BLOCKED = "blocked"
GLM_TASK_STATUSES = {
    GLM_STATUS_PENDING, GLM_STATUS_PROCESSING, GLM_STATUS_SUCCEEDED,
    GLM_STATUS_RETRYABLE, GLM_STATUS_FAILED, GLM_STATUS_BLOCKED,
}

# §十 退避（秒）
BACKOFF_SECONDS = (5, 15, 45)        # 5xx / connection / timeout
BACKOFF_429_SECONDS = (60, 120, 240) # 429 限流专用退避（无 Retry-After 时）
DEFAULT_CIRCUIT_THRESHOLD = 5
# 限流友好默认值（env 可覆盖）
DEFAULT_MIN_REQUEST_INTERVAL = 90    # 请求开始→请求开始 最小间隔（秒）
DEFAULT_CONNECT_TIMEOUT = 20         # connect 阶段超时（秒）
DEFAULT_READ_TIMEOUT = 180           # read/request 阶段超时（秒）
DEFAULT_RATE_LIMIT_COOLDOWN = 60     # 429 无 Retry-After 时的全局冷却（秒）

# 唯一 Secret 名（只写名称，不写值）
SECRET_NAME = "ASIP_GLM_API_KEY"


class CircuitBreaker:
    """轻量熔断器：连续 threshold 次 provider 级失败 → open（degraded）。"""

    def __init__(self, threshold=DEFAULT_CIRCUIT_THRESHOLD):
        self.threshold = threshold
        self.consecutive_failures = 0
        self.open = False

    def record_success(self):
        self.consecutive_failures = 0
        self.open = False

    def record_failure(self):
        # 仅 provider 级持续故障（5xx/timeout/connection）计数；429 限流不计数
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.threshold:
            self.open = True

    def record_soft_failure(self):
        # 429 限流：可恢复，不计入连续故障（不触发熔断）
        pass

    def is_open(self):
        return self.open

    def state(self):
        return "degraded" if self.open else "ok"


def backoff_seconds(attempt, retry_after=None, jitter=True, kind="default"):
    """第 attempt 次重试前的退避秒数（1-based attempt）。

    优先级：服务端 Retry-After > 类型专用退避序列。
    - kind="429"：60/120/240（限流需更长冷却）；
    - kind="default"：5/15/45（5xx/connection/timeout）。
    允许 ±20% jitter。
    """
    if retry_after and retry_after > 0:
        base = float(retry_after)
    else:
        seq = BACKOFF_429_SECONDS if kind == "429" else BACKOFF_SECONDS
        idx = min(max(attempt - 1, 0), len(seq) - 1)
        base = float(seq[idx])
    if jitter:
        return round(base * random.uniform(0.8, 1.2), 2)
    return round(base, 2)


def classify_http_status(status):
    """HTTP 状态分类。返回 (outcome, error_code)。

    outcome ∈ {"ok", "retryable", "blocked"}
    """
    if status == 200:
        return "ok", None
    if status in (401, 403):
        return "blocked", "credential_error_%d" % status
    if status == 429:
        return "retryable", "rate_limited_429"
    if status >= 500:
        return "retryable", "server_error_%d" % status
    return "retryable", "http_%d" % status


def _extract_json(content):
    """strict JSON 解析：先整体解析，失败则提取首个 { ... } 块。"""
    if not content:
        return None
    text = content.strip()
    # 去掉可能的 Markdown 围栏
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 提取首个平衡 JSON 对象
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


class Glm47FlashProvider(BaseAIProvider):
    """GLM-4.7-Flash 云端 API Provider（OpenAI 兼容）。

    provider_name = "glm"；model = glm-4.7-flash（env ASIP_GLM_MODEL 可覆盖）。
    """

    name = "glm47_flash"
    provider_name = "glm"
    requested_model = "glm-4.7-flash"

    def __init__(self, config=None, name="glm47_flash", http_client=None):
        BaseAIProvider.__init__(self, config or {}, name)
        self._load_env()
        self._breaker = CircuitBreaker(self.circuit_threshold)
        self._cache = {}          # 同 run 内存缓存：cache_key -> result
        self._tasks = {}          # task_id -> task dict（含状态/结果）
        self._http = http_client  # 可注入（测试用）；None 时用 urllib
        self.credential_status = "present" if self.api_key else "missing"
        self.provider_status = "ok" if self.api_key else "unavailable"
        # 单次 HTTP 尝试的最近状态（供审计字段）
        self._last_status = None
        self._last_retry_after = None
        self._last_parsed = None
        self._last_usage = None
        self._last_returned_model = None
        self._run_started_at = None
        self._last_request_at = None      # 上次请求「开始」时刻（start-to-start 节流）
        self._request_start_gap = None    # 遥测：上次请求开始→本次请求开始间隔（秒）
        self._rate_limit_until = None     # 全局限流冷却截止（绝对 epoch 秒）；之前不发请求
        self._last_retry_after_seconds = None  # 遥测：最近一次 Retry-After（秒）
        # 遥测计数（安全字段，不记录 credential/header）
        self.telemetry = {
            "rate_limited_count": 0,
            "retry_after_seen": 0,
            "cooldown_seconds": 0.0,
            "timeout_count": 0,
            "http5xx_count": 0,
        }

    # ── 配置 ──
    def _load_env(self, env=None):
        e = env or os.environ
        self.api_key = e.get(SECRET_NAME, "")
        self.model = e.get("ASIP_GLM_MODEL", self.requested_model)
        self.base_url = e.get(
            "ASIP_GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4").rstrip("/")
        self.max_retries = int(e.get("ASIP_GLM_MAX_RETRIES", "3"))
        self.circuit_threshold = int(
            e.get("ASIP_GLM_CIRCUIT_THRESHOLD", str(DEFAULT_CIRCUIT_THRESHOLD)))
        # 请求间最小间隔（秒）：按「上一次请求开始 → 下一次请求开始」计算
        self.min_request_interval = float(
            e.get("ASIP_GLM_MIN_REQUEST_INTERVAL_SECONDS",
                  str(DEFAULT_MIN_REQUEST_INTERVAL)))
        # 429 无 Retry-After 时的全局冷却（秒）
        self.rate_limit_cooldown = float(
            e.get("ASIP_GLM_RATE_LIMIT_COOLDOWN_SECONDS",
                  str(DEFAULT_RATE_LIMIT_COOLDOWN)))
        # connect / read 超时分离（长响应场景）
        self.connect_timeout = float(
            e.get("ASIP_GLM_CONNECT_TIMEOUT_SECONDS", str(DEFAULT_CONNECT_TIMEOUT)))
        self.read_timeout = float(
            e.get("ASIP_GLM_READ_TIMEOUT_SECONDS", str(DEFAULT_READ_TIMEOUT)))

    def validate_config(self):
        errors = []
        if not self.api_key:
            errors.append("%s missing（credential_status=missing）" % SECRET_NAME)
        return errors

    # ── BaseAIProvider 接口 ──
    def submit_task(self, task):
        task = dict(task or {})
        tid = task.get("task_id") or task.get("id") or "?"
        self._tasks[tid] = dict(task, status=GLM_STATUS_PROCESSING)
        task["status"] = GLM_STATUS_PROCESSING

        # 密钥缺失：安全停止
        if not self.api_key:
            result = self._mk_result(task, GLM_STATUS_BLOCKED,
                                     "credential_missing", "ASIP_GLM_API_KEY not set",
                                     http_status=None, attempt_count=0)
            self._tasks[tid] = dict(task, status=GLM_STATUS_BLOCKED, result=result)
            return self._tasks[tid]

        # 熔断：连续失败已达阈值 → 不再发送
        if self._breaker.is_open():
            result = self._mk_result(task, GLM_STATUS_RETRYABLE,
                                     "circuit_open",
                                     "provider degraded; retry next run",
                                     http_status=None, attempt_count=0)
            self._tasks[tid] = dict(task, status=GLM_STATUS_RETRYABLE, result=result)
            return self._tasks[tid]

        # Cache / Idempotency（§十二）
        cache_key = self._cache_key(task)
        if cache_key in self._cache:
            cached = dict(self._cache[cache_key])
            cached["task_id"] = tid
            cached["cache_hit"] = True
            task["status"] = cached.get("status") or GLM_STATUS_SUCCEEDED
            self._tasks[tid] = dict(task, result=cached)
            return self._tasks[tid]

        result = self._call_api(task, cache_key)
        task["status"] = result.get("status") or GLM_STATUS_FAILED
        self._tasks[tid] = dict(task, result=result)
        if result.get("status") == GLM_STATUS_SUCCEEDED:
            self._breaker.record_success()
            self._cache[cache_key] = result
        elif (result.get("error") or {}).get("code") == "rate_limited_429":
            # 429 限流：可恢复，不计入熔断计数
            self._breaker.record_soft_failure()
        else:
            self._breaker.record_failure()
        return self._tasks[tid]

    def get_task_status(self, task_id):
        t = self._tasks.get(task_id)
        return (t or {}).get("status", GLM_STATUS_PENDING)

    def load_result(self, task_id):
        t = self._tasks.get(task_id)
        return (t or {}).get("result")

    def health_check(self):
        return {
            "provider": self.provider_name,
            "model": self.model,
            "credential_status": self.credential_status,
            "provider_status": self.provider_status,
            "circuit_state": self._breaker.state(),
            "external_network": True,
            "browser_direct_api_call": False,
            "cloud_ai_api_call": True,
            "api_base_url": self.base_url,
            "requested_model": self.requested_model,
        }

    # ── 核心调用 ──
    def _cache_key(self, task):
        return "|".join([
            task.get("input_hash") or "",
            task.get("prompt_version") or "",
            task.get("prompt_content_hash") or "",
            self.provider_name,
            self.model,
        ]) or (task.get("task_id") or "?")

    def _call_api(self, task, cache_key):
        started = time.time()
        last_retry_after = None
        attempt = 0

        while attempt <= self.max_retries:
            # 全局 Rate Limit Cooldown：限流截止前不再发任何请求（§三）
            if self._rate_limit_until is not None:
                wait = self._rate_limit_until - time.time()
                if wait > 0:
                    time.sleep(wait)
                self._rate_limit_until = None
            # 请求间最小间隔（start-to-start，§二）：不足则补足
            if self._last_request_at is not None and self.min_request_interval > 0:
                elapsed = time.time() - self._last_request_at
                if elapsed < self.min_request_interval:
                    time.sleep(self.min_request_interval - elapsed)
                self._request_start_gap = max(elapsed, self.min_request_interval)
            attempt += 1
            self._last_request_at = time.time()  # 记录本次请求「开始」时刻
            outcome, err_code = self._http_attempt(task)
            if outcome == "ok":
                finished = time.time()
                return self._mk_result(
                    task, GLM_STATUS_SUCCEEDED, None, None,
                    http_status=200, attempt_count=attempt,
                    latency_ms=int((finished - started) * 1000),
                    returned_model=self._last_returned_model,
                    usage=self._last_usage,
                    parsed=self._last_parsed,
                    finished_at=finished)
            if outcome == "blocked":
                # 401/403：credential/config blocked，直接停止（不掩盖、不重试）
                return self._mk_result(task, GLM_STATUS_BLOCKED, err_code,
                                       "credential or permission error",
                                       http_status=self._last_status,
                                       attempt_count=attempt)
            # retryable
            if attempt > self.max_retries:
                return self._mk_result(task, GLM_STATUS_RETRYABLE, err_code,
                                       "retries exhausted",
                                       http_status=self._last_status,
                                       attempt_count=attempt)
            # 429 走全局冷却 + 专用退避；5xx/timeout 用短退避
            if err_code == "rate_limited_429":
                time.sleep(backoff_seconds(attempt, retry_after=self._last_retry_after,
                                           kind="429"))
            else:
                time.sleep(backoff_seconds(attempt, retry_after=self._last_retry_after))
        # 不可达（理论不会到）
        return self._mk_result(task, GLM_STATUS_RETRYABLE, "retry_exhausted",
                               "unreachable", http_status=None, attempt_count=attempt)

    def _http_attempt(self, task):
        """单次 HTTP 尝试。返回 (outcome, error_code)；副作用记录 last_*。"""
        url = self.base_url + "/chat/completions"
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system",
                 "content": task.get("system_text") or task.get("prompt_text") or ""},
                {"role": "user",
                 "content": task.get("user_text") or task.get("prompt_text") or ""},
            ],
            "temperature": 0.1,
            "max_tokens": int(task.get("max_output_tokens") or 2048),
        }, ensure_ascii=False).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.api_key,
        }
        try:
            resp = self._do_post(url, payload, headers, self.read_timeout)
            # _last_request_at 已在 _call_api 请求开始时记录（start-to-start 语义）
        except urllib.error.HTTPError as e:
            self._last_status = e.code
            self._last_retry_after = _retry_after_of(e)
            self._last_parsed = None
            self._last_usage = None
            self._last_returned_model = None
            outcome, code = classify_http_status(e.code)
            if e.code == 429:
                # 全局 Rate Limit Cooldown：设置截止时间，后续任务不得立即请求
                self.telemetry["rate_limited_count"] += 1
                ra = self._last_retry_after
                if ra and ra > 0:
                    self._rate_limit_until = time.time() + ra
                    self.telemetry["retry_after_seen"] += 1
                    self._last_retry_after_seconds = ra
                else:
                    self._rate_limit_until = time.time() + self.rate_limit_cooldown
                self.telemetry["cooldown_seconds"] = (
                    self._rate_limit_until - time.time())
            elif e.code >= 500:
                self.telemetry["http5xx_count"] += 1
            return outcome, code
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError) as e:
            self._last_status = None
            self._last_retry_after = None
            self._last_parsed = None
            self._last_usage = None
            self._last_returned_model = None
            if isinstance(e, (TimeoutError, ssl.SSLError)) or (
                    isinstance(e, urllib.error.URLError) and isinstance(e.reason, (TimeoutError, socket.timeout))):
                self.telemetry["timeout_count"] += 1
            return "retryable", "connection_or_timeout"
        except Exception as e:  # 其他网络/解析异常
            self._last_status = None
            self._last_retry_after = None
            self._last_parsed = None
            self._last_usage = None
            self._last_returned_model = None
            return "retryable", "network_%s" % type(e).__name__

        body = resp.read().decode("utf-8") if hasattr(resp, "read") else resp
        self._last_status = 200
        self._last_retry_after = None
        try:
            data = json.loads(body) if isinstance(body, str) else body
        except json.JSONDecodeError:
            self._last_parsed = None
            self._last_usage = None
            self._last_returned_model = None
            return "retryable", "malformed_json"

        # OpenAI 兼容响应
        try:
            _msg = data["choices"][0]["message"]
            content = _msg.get("content") or ""
            if not content.strip():
                # GLM 思考模型可能把输出放在 reasoning_content
                content = _msg.get("reasoning_content") or ""
            parsed = _extract_json(content)
            if parsed is None:
                self._last_parsed = None
                self._last_usage = None
                self._last_returned_model = data.get("model")
                return "retryable", "invalid_output_json"
            self._last_parsed = parsed
            self._last_returned_model = data.get("model")
            self._last_usage = {
                "input_tokens": data.get("usage", {}).get("prompt_tokens"),
                "output_tokens": data.get("usage", {}).get("completion_tokens"),
                "total_tokens": data.get("usage", {}).get("total_tokens"),
            }
            return "ok", None
        except (KeyError, IndexError, TypeError):
            self._last_parsed = None
            self._last_usage = None
            self._last_returned_model = data.get("model")
            return "retryable", "invalid_response_shape"

    def _do_post(self, url, payload, headers, timeout):
        """POST；timeout 参数 = read 超时；connect 用 self.connect_timeout 分离。

        测试可注入 http_client(url, payload, headers, timeout)。
        """
        if self._http is not None:
            return self._http(url, payload, headers, timeout)
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        ctx = ssl.create_default_context()
        conn = http.client.HTTPSConnection(
            host, port, timeout=self.connect_timeout, context=ctx)
        try:
            conn.connect()
            if conn.sock is not None:
                conn.sock.settimeout(timeout)  # read 阶段超时
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            conn.request("POST", path, body=payload, headers=headers)
            return conn.getresponse()
        except Exception:
            conn.close()
            raise

    # ── 结果构造（§十四 审计字段）──
    def _mk_result(self, task, status, err_code, err_msg, http_status,
                   attempt_count, latency_ms=None, returned_model=None,
                   usage=None, parsed=None, finished_at=None):
        r = {
            "task_id": task.get("task_id") or "?",
            "provider": self.provider_name,
            "requested_model": self.requested_model,
            "returned_model": returned_model or self._last_returned_model,
            "prompt_version": task.get("prompt_version"),
            "input_hash": task.get("input_hash"),
            "result_id": task.get("result_id") or task.get("cache_key"),
            "request_started_at": getattr(self, "_run_started_at", None),
            "request_finished_at": _iso(finished_at) if finished_at else None,
            "latency_ms": latency_ms,
            "http_status": http_status,
            "attempt_count": attempt_count,
            "token_usage_available": bool(usage and usage.get("input_tokens") is not None),
            "input_tokens": (usage or {}).get("input_tokens"),
            "output_tokens": (usage or {}).get("output_tokens"),
            "total_tokens": (usage or {}).get("total_tokens"),
            "billing_mode": "free_currently",
            "estimated_cost": None,   # 无法从 provider 实际计费可靠计算 → null
            "usage_purpose": task.get("usage_purpose") or "production_qualification",
            "status": status,
            "error": {"code": err_code, "message": err_msg} if err_code else None,
            "result": parsed or {},
        }
        return r


def _retry_after_of(e):
    try:
        v = e.headers.get("Retry-After")
        if v:
            return int(float(v))
    except Exception:
        pass
    return None


def _iso(ts):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
