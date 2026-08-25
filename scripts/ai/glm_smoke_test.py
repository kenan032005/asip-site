#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP AI Provider Migration — GLM Smoke Test（§十五）。

只发送一个极小、中性的连接测试：
  {"status": "ok", "provider_test": "glm47_flash"}

Smoke Test 只验证：认证成功 / endpoint 正确 / model 存在 / HTTP 成功 / JSON 可解析。
不使用真实敏感事件；不将响应加入 Public。

无 Key 时：credential_status=missing、provider_status=unavailable，安全跳过（exit 2）。
"""

import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from scripts.ai.providers.glm47_flash import _extract_json  # noqa: E402

SECRET_NAME = "ASIP_GLM_API_KEY"
BASE_URL = os.environ.get("ASIP_GLM_BASE_URL",
                          "https://open.bigmodel.cn/api/paas/v4").rstrip("/")
MODEL = os.environ.get("ASIP_GLM_MODEL", "glm-4.7-flash")

SMOKE_SYSTEM = ("你是连接测试助手。只输出一个 JSON 对象，不要其他文字。")
SMOKE_USER = ('请严格输出: {"status": "ok", "provider_test": "glm47_flash"}')


def main():
    key = os.environ.get(SECRET_NAME, "")
    if not key:
        print(json.dumps({
            "credential_status": "missing",
            "provider_status": "unavailable",
            "provider": "glm",
            "requested_model": MODEL,
            "api_base_url": BASE_URL,
            "result": "SKIP_NO_CREDENTIAL",
        }, ensure_ascii=False, indent=2))
        return 2

    url = BASE_URL + "/chat/completions"
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SMOKE_SYSTEM},
            {"role": "user", "content": SMOKE_USER},
        ],
        "temperature": 0.1,
        "max_tokens": 128,
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key,
    }, method="POST")

    import ssl
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            body = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as e:
        print(json.dumps({
            "credential_status": "present",
            "provider_status": "http_error",
            "http_status": e.code,
            "result": "FAIL",
        }, ensure_ascii=False, indent=2))
        return 1
    except Exception as e:
        print(json.dumps({
            "credential_status": "present",
            "provider_status": "connection_error",
            "error": type(e).__name__,
            "result": "FAIL",
        }, ensure_ascii=False, indent=2))
        return 1

    try:
        data = json.loads(body)
        content = data["choices"][0]["message"]["content"]
        parsed = _extract_json(content)
        if parsed is None:
            raise ValueError("content not strict json")
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as e:
        diag = {
            "credential_status": "present",
            "provider_status": "invalid_json",
            "http_status": status,
            "error": type(e).__name__,
            "result": "FAIL",
        }
        if isinstance(data, dict):
            diag["returned_model"] = data.get("model")
            diag["response_keys"] = sorted(data.keys())
            try:
                msg = data["choices"][0]["message"]
                diag["message_keys"] = sorted(msg.keys())
                diag["content_len"] = len(msg.get("content") or "")
                rc = msg.get("reasoning_content")
                diag["reasoning_content_len"] = len(rc) if rc else 0
                diag["reasoning_preview"] = (rc[:150] if rc else None)
                diag["choices_len"] = len(data.get("choices") or [])
            except Exception as ex:
                diag["shape_error"] = type(ex).__name__
            if "usage" in data:
                diag["usage_available"] = True
        print(json.dumps(diag, ensure_ascii=False, indent=2))
        return 1

    ok = parsed.get("status") == "ok" and parsed.get("provider_test") == "glm47_flash"
    print(json.dumps({
        "credential_status": "present",
        "provider_status": "ok" if ok else "unexpected_response",
        "http_status": status,
        "api_base_url": BASE_URL,
        "requested_model": MODEL,
        "returned_model": data.get("model"),
        "parsed": parsed,
        "token_usage_available": bool(data.get("usage")),
        "result": "PASS" if ok else "FAIL",
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
