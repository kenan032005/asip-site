#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c3_qualify.py —— C3R §四 最小 DeepSeek qualification。

只输出 PRESENT/MISSING 与 PASS/FAIL，**绝不**输出 key、Authorization、前缀/后缀。
校验四件事：HTTP 成功 / model 正确 / 返回结构化 JSON / thinking disabled（reasoning_tokens=null）。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(os.path.dirname(HERE))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

SECRET_NAME = "ASIP_DEEPSEEK_API_KEY"
EXPECTED_MODEL = "deepseek-v4-flash"
TASK_TYPE = "stage4_event_enrichment"      # thinking=disabled


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-pass", action="store_true")
    a = ap.parse_args()

    present = bool(os.environ.get(SECRET_NAME, "").strip())
    print("%s = %s" % (SECRET_NAME, "PRESENT" if present else "MISSING"))
    if not present:
        print("DEEPSEEK_QUALIFICATION = FAIL")
        print("reason = credential_missing")
        print("USER_ACTION_REQUIRED = ADD_REPOSITORY_SECRET_%s" % SECRET_NAME)
        return 2 if a.require_pass else 0

    from ai.providers.deepseek_v4_flash import (DeepSeekV4FlashProvider,
                                                ALLOWED_DEEPSEEK_MODELS,
                                                THINKING_POLICY)
    prov = DeepSeekV4FlashProvider()
    thinking, effort = THINKING_POLICY.get(TASK_TYPE, (None, None))
    checks = {
        "provider_model": prov.model == EXPECTED_MODEL,
        "model_allowed": prov.model in ALLOWED_DEEPSEEK_MODELS,
        "base_url": str(getattr(prov, "base_url", "")).startswith("https://api.deepseek.com"),
        "thinking_disabled": thinking == "disabled",
        "credential_present": getattr(prov, "credential_status", "") == "present",
    }
    resp = prov.submit_task({
        "task_id": "qual",
        "task_type": TASK_TYPE,
        "system_text": 'You are a JSON echo. Reply ONLY with {"ok":true,"n":1}',
        "user_text": 'Return {"ok":true,"n":1}',
        "max_output_tokens": 64,
    })
    res = (resp or {}).get("result") or {}
    checks["http_success"] = (resp or {}).get("status") == "succeeded"
    text = res.get("text") or ""
    parsed, json_ok = None, False
    try:
        parsed = json.loads(text)
        json_ok = isinstance(parsed, dict) and parsed.get("ok") is True
    except Exception:
        json_ok = False
    checks["structured_json"] = json_ok
    checks["returned_model_ok"] = (res.get("returned_model") in (None, EXPECTED_MODEL))
    checks["reasoning_tokens_null"] = res.get("reasoning_tokens") in (None, 0)

    passed = all(checks.values())
    print("checks = %s" % json.dumps(checks, ensure_ascii=False))
    print("finish_reason = %s | content_len = %s"
          % (res.get("finish_reason"), len(text)))
    print("DEEPSEEK_QUALIFICATION = %s" % ("PASS" if passed else "FAIL"))
    if not passed:
        err = (res.get("error") or {}).get("code")
        print("reason = %s" % (err or "qualification_check_failed"))
        return 2 if a.require_pass else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
