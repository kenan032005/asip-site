#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 — 模型输出校验 v2（元数据分离 + 严格 JSON + 语义约束）。

字段分层：
  MODEL_OUTPUT_FIELDS = 模型可输出的语义字段（10 个）
  SYSTEM_METADATA_FIELDS = 处理器注入的可信元数据（模型不得决定）
"""

import json

# ── 字段分层 ──────────────────────────────────────────────────
MODEL_OUTPUT_FIELDS = [
    "source_language", "title_zh", "summary_zh", "event_type",
    "country_iso3", "location", "key_facts",
    "uncertainties", "security_relevance", "classification_confidence",
]

SYSTEM_METADATA_FIELDS = [
    "result_id", "event_id", "canonical_run_id", "input_hash", "cache_key",
    "ai_provider", "ai_model", "prompt_version", "prompt_content_hash",
    "processed_at", "processing_status", "error_code", "raw_response_hash",
]

ALL_ENRICHMENT_FIELDS = MODEL_OUTPUT_FIELDS + SYSTEM_METADATA_FIELDS

# 固定枚举
EVENT_TYPES = {
    "armed_conflict", "terrorism", "civil_unrest", "political_instability",
    "crime_kidnapping", "border_security", "transport_disruption",
    "infrastructure_incident", "natural_disaster", "other_security",
}
SECURITY_RELEVANCE = {"direct", "indirect", "none"}
PROCESSING_STATUS = {"pending", "processing", "succeeded",
                     "failed_retryable", "failed_terminal",
                     "skipped_ineligible", "invalid_model_output"}
EVIDENCE_FIELDS = {"title_original", "body_extracted", "event_time", "location", "source_links"}


# ── 严格 JSON 解析 ───────────────────────────────────────────
def parse_json_response_strict(raw_text, strict=True):
    """严格模式：只接受纯 JSON object（无围栏/无解释/无多对象/非数组）。

    返回 (parsed, warnings, error)。
    strict=False 时允许旧版容错（围栏剥离/提取第一个对象），但标记 lenient。
    """
    if not raw_text or not isinstance(raw_text, str):
        return None, [], "empty_response"

    text = raw_text.strip()

    if strict:
        if not text.startswith("{"):
            return None, [], "strict_not_object_start"
        if not text.endswith("}"):
            return None, [], "strict_not_object_end"
        if "```" in text:
            return None, [], "strict_code_fence"
        try:
            parsed = json.loads(text)
        except Exception:
            return None, [], "strict_json_parse_error"
        if not isinstance(parsed, dict):
            return None, [], "strict_not_object"
        if isinstance(parsed, list):
            return None, [], "strict_array_not_allowed"
        return parsed, [], None

    # 非严格模式（未来诊断用，默认不用）
    warnings = []
    if text.startswith("```") and "```" in text[3:]:
        inner = text[3:]
        if inner.startswith("json"):
            inner = inner[4:]
        end = inner.rfind("```")
        if end > 0:
            text = inner[:end].strip()
            warnings = ["lenient_code_fence_stripped"]
    try:
        parsed = json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(text[start:end + 1])
                warnings.append("lenient_extracted_json_object")
            except Exception:
                return None, warnings, "json_parse_error"
        else:
            return None, warnings, "json_parse_error"
    if not isinstance(parsed, dict):
        return None, warnings, "not_object"
    if isinstance(parsed, list):
        return None, warnings, "array_not_allowed"
    return parsed, warnings, None


# ── 语义校验 ─────────────────────────────────────────────────
def validate_enrichment_semantics(parsed, input_event, expected_run_id=None):
    """对模型输出的 semantic_payload 做语义校验。"""
    errors = []
    warnings = []

    expect_eid = input_event.get("event_id")
    if parsed.get("event_id") and parsed["event_id"] != expect_eid:
        errors.append(f"event_id_mismatch: got={parsed.get('event_id')} expect={expect_eid}")

    expect_iso = input_event.get("country_iso3") or ""
    model_iso = parsed.get("country_iso3")
    if not model_iso:
        errors.append("country_iso3_missing: country_iso3 为必填且不得为 null")
    elif expect_iso and model_iso != expect_iso:
        errors.append(f"country_iso3_mismatch: got={model_iso} expect={expect_iso}")
    elif not isinstance(model_iso, str) or len(model_iso) != 3 or model_iso != model_iso.upper():
        errors.append(f"country_iso3_invalid: {model_iso!r} 不是合法 ISO3")

    loc = parsed.get("location")
    if isinstance(loc, dict) and loc.get("country_iso3"):
        lc = loc["country_iso3"]
        if expect_iso and lc != expect_iso:
            errors.append(f"location.country_iso3_mismatch: got={lc} expect={expect_iso}")

    if not parsed.get("title_zh"):
        errors.append("title_zh_empty")
    if not parsed.get("summary_zh"):
        errors.append("summary_zh_empty")

    if parsed.get("event_type") not in EVENT_TYPES:
        errors.append(f"event_type_invalid: {parsed.get('event_type')!r}")
    if parsed.get("security_relevance") not in SECURITY_RELEVANCE:
        errors.append(f"security_relevance_invalid: {parsed.get('security_relevance')!r}")

    conf = parsed.get("classification_confidence")
    if not isinstance(conf, int) or isinstance(conf, bool):
        errors.append(f"confidence_not_int: {conf!r}")
    elif not (0 <= conf <= 100):
        errors.append(f"confidence_out_of_range: {conf}")

    kf = parsed.get("key_facts")
    if not isinstance(kf, list):
        errors.append("key_facts_not_array")
    else:
        for i, f in enumerate(kf):
            if not isinstance(f, dict) or not f.get("fact"):
                errors.append(f"key_facts[{i}].fact_invalid")
            if f.get("evidence_field") not in EVIDENCE_FIELDS:
                errors.append(f"key_facts[{i}].evidence_field_invalid")

    if not isinstance(parsed.get("uncertainties"), list):
        errors.append("uncertainties_not_array")

    if "```" in (parsed.get("title_zh") or "") or "```" in (parsed.get("summary_zh") or ""):
        errors.append("title_or_summary_contains_fence")

    return len(errors) == 0, errors, warnings


def validate_enrichment(parsed, input_event, expected_run_id=None):
    """兼容旧接口。"""
    return validate_enrichment_semantics(parsed, input_event, expected_run_id)
