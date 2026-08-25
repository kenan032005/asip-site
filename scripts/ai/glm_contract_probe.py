#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP GLM-4.7-Flash Contract Probe（§三 Final Contract Qualification）。

完全中性的真实 API probe：验证 glm-4.7-flash 能否严格返回固定目标 shape。
不属于 Golden Set；不写 Public；不敏感。

流程：
  1) 读取 ASIP_GLM_API_KEY（缺失 → credential_status=missing 安全跳过）
  2) 用 Glm47FlashProvider 发送固定 shape 请求（system 明确要求
     "Return exactly one JSON object. No analysis. No markdown. No explanation."）
  3) strict JSON parse + shape 校验（字段存在、类型、enum 取值）
  4) 输出 PASS/FAIL + 返回 shape + 审计字段（http/attempt/returned_model/usage）

判定：
  - probe 成功返回目标 shape → PASS
  - 任何 shape 偏差 / 解析失败 / 非 JSON → FAIL
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.registry import get_provider

PROBE_SYSTEM = (
    "Return exactly one JSON object. No analysis. No markdown. No explanation. "
    "Do not output reasoning. Do not echo the input."
)
PROBE_USER = (
    'Output exactly this JSON object with these values: '
    '{"title_zh":"测试标题","summary_zh":"测试摘要","event_type":"other",'
    '"security_relevance":"none","classification_confidence":0.9,'
    '"location":null,"key_facts":[],"uncertainties":[]}'
)

# 期望 shape：字段 -> 类型校验（None 表示允许 null）
EXPECTED_SHAPE = {
    "title_zh": (str,),
    "summary_zh": (str,),
    "event_type": (str,),
    "security_relevance": (str,),
    "classification_confidence": (int, float),
    "location": (type(None), dict),
    "key_facts": (list,),
    "uncertainties": (list,),
}
ENUM_RELEVANCE = {"none", "indirect", "direct"}


def validate_shape(parsed):
    """返回 (ok, errors[])。parsed 必须严格匹配 EXPECTED_SHAPE。"""
    if not isinstance(parsed, dict):
        return False, ["not_an_object"]
    errs = []
    for k, types in EXPECTED_SHAPE.items():
        if k not in parsed:
            errs.append("missing:%s" % k)
            continue
        v = parsed[k]
        if not isinstance(v, types):
            errs.append("type:%s=%s" % (k, type(v).__name__))
    if "security_relevance" in parsed and parsed["security_relevance"] not in ENUM_RELEVANCE:
        errs.append("enum:security_relevance=%r" % parsed["security_relevance"])
    # 不允许额外顶层字段（unexpected_top_level_shape=reject，§七）
    extra = set(parsed) - set(EXPECTED_SHAPE)
    if extra:
        errs.append("extra_top_level:%s" % sorted(extra))
    return (len(errs) == 0), errs


def main():
    provider = get_provider("glm47_flash")
    if provider.credential_status == "missing":
        print(json.dumps({
            "credential_status": "missing",
            "provider_status": "unavailable",
            "result": "SKIP_NO_CREDENTIAL",
        }, ensure_ascii=False, indent=2))
        return 2

    task = {
        "task_id": "GLMPROBE_001",
        "task_type": "contract_probe",
        "prompt_version": "glm-probe-v1",
        "input_hash": "probe_fixed_shape_001",
        "system_text": PROBE_SYSTEM,
        "user_text": PROBE_USER,
        "usage_purpose": "production_qualification",
        "max_output_tokens": 512,
    }
    out = provider.submit_task(task)
    result = out.get("result") or {}
    parsed = result.get("result") or {}
    ok_shape, errs = validate_shape(parsed) if parsed else (False, ["no_parsed"])

    meta = {k: result.get(k) for k in (
        "http_status", "attempt_count", "latency_ms", "requested_model",
        "returned_model", "token_usage_available", "input_tokens",
        "output_tokens", "total_tokens") if k in result}
    if result.get("error"):
        meta["error"] = result["error"]

    doc = {
        "credential_status": provider.credential_status,
        "provider_status": out.get("status"),
        "usage_purpose": "production_qualification",
        "probe": "contract_probe_fixed_shape",
        "shape_ok": ok_shape,
        "shape_errors": errs,
        "parsed": parsed if ok_shape else None,
        "parsed_preview": json.dumps(parsed, ensure_ascii=False)[:400] if parsed else None,
        "meta": meta,
        "result": "PASS" if ok_shape else "FAIL",
    }
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0 if ok_shape else 1


if __name__ == "__main__":
    sys.exit(main())
