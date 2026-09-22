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


def evaluate_transport(resp):
    """§五：把 provider 响应拆成「HTTP 传输结果」与「模型身份」两组独立事实。

    返回 dict：http_status / http_success / requested_model /
    normalized_requested_model / returned_model / normalized_returned_model /
    model_match / error_code。
    **model_mismatch 不得被计成 HTTP failure**：它意味着 HTTP 200 已成功返回，
    只是模型身份不合规。
    """
    from ai.providers.deepseek_v4_flash import normalize_deepseek_model
    res = (resp or {}).get("result") or {}
    err = (res.get("error") or {}).get("code")
    http_status = res.get("http_status")
    requested = res.get("requested_model")
    returned = res.get("returned_model")
    norm_req = normalize_deepseek_model(requested)
    norm_ret = normalize_deepseek_model(returned)
    transport_error = ((resp or {}).get("status") != "succeeded") and (err != "model_mismatch")
    http_ok = bool((not transport_error) and isinstance(http_status, int)
                   and 200 <= http_status < 300)
    model_match = (returned is None) or (norm_ret is not None and norm_ret == norm_req)
    return {"http_status": http_status, "http_success": http_ok,
            "requested_model": requested, "normalized_requested_model": norm_req,
            "returned_model": returned, "normalized_returned_model": norm_ret,
            "model_match": model_match, "error_code": err,
            "transport_error": transport_error}


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

    from ai.providers.deepseek_v4_flash import (
        DeepSeekV4FlashProvider, ALLOWED_DEEPSEEK_MODELS, THINKING_POLICY,
        CANONICAL_MODEL, DISPLAY_MODEL,
        normalize_deepseek_model)
    prov = DeepSeekV4FlashProvider()
    thinking, effort = THINKING_POLICY.get(TASK_TYPE, (None, None))
    checks = {
        "provider_model_is_canonical": prov.model == CANONICAL_MODEL,
        "model_allowed": normalize_deepseek_model(prov.model) is not None,
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
    ev = evaluate_transport(resp)
    http_status = ev["http_status"]
    http_ok = ev["http_success"]
    requested = ev["requested_model"]
    norm_req = ev["normalized_requested_model"]
    returned = ev["returned_model"]
    norm_ret = ev["normalized_returned_model"]
    model_match = ev["model_match"]
    err = ev["error_code"]
    checks["http_success"] = bool(http_ok)
    checks["model_match"] = bool(model_match)

    text = res.get("text") or ""
    try:
        parsed = json.loads(text)
        json_ok = isinstance(parsed, dict) and parsed.get("ok") is True
    except Exception:  # noqa: BLE001
        json_ok = False
    checks["structured_json"] = json_ok
    checks["returned_model_registered"] = (returned is None) or (norm_ret is not None)
    checks["reasoning_tokens_null"] = res.get("reasoning_tokens") in (None, 0)

    passed = all(checks.values())

    print("HTTP_STATUS           = %s" % http_status)
    print("HTTP_SUCCESS          = %s" % ("true" if http_ok else "false"))
    print("REQUESTED_MODEL       = %s" % requested)
    print("NORMALIZED_REQUESTED_MODEL = %s" % norm_req)
    print("RETURNED_MODEL        = %s" % returned)
    print("NORMALIZED_RETURNED_MODEL  = %s" % norm_ret)
    print("MODEL_MATCH           = %s" % ("true" if model_match else "false"))
    print("CANONICAL_MODEL       = %s (%s)" % (CANONICAL_MODEL, DISPLAY_MODEL))
    print("ALLOWED_MODELS        = %s" % sorted(ALLOWED_DEEPSEEK_MODELS))
    print("checks = %s" % json.dumps(checks, ensure_ascii=False))
    print("finish_reason = %s | content_len = %s" % (res.get("finish_reason"), len(text)))
    print("DEEPSEEK_QUALIFICATION = %s" % ("PASS" if passed else "FAIL"))
    if not passed:
        err = (res.get("error") or {}).get("code")
        print("reason = %s" % (err or "qualification_check_failed"))
        return 2 if a.require_pass else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
