#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 — 模型输出校验（Schema + 语义）。

流程：raw response → JSON 解析 → Schema 校验 → 语义校验 → 保存。
无效输出进入 invalid_model_output，保留错误原因，不公开原始完整响应。
"""

import json

from .enrichment_eligibility import is_article_url

# 固定枚举
EVENT_TYPES = {
    "armed_conflict", "terrorism", "civil_unrest", "political_instability",
    "crime_kidnapping", "border_security", "transport_disruption",
    "infrastructure_incident", "natural_disaster", "other_security",
}
SECURITY_RELEVANCE = {"direct", "indirect", "none"}
PROCESSING_STATUS = {
    "pending", "processing", "succeeded", "failed_retryable",
    "failed_terminal", "skipped_ineligible", "invalid_model_output",
}
EVIDENCE_FIELDS = {"title_original", "body_extracted", "event_time", "location", "source_links"}


def parse_json_response(raw_text):
    """解析模型原始响应。

    容忍：前后空白、单个 ```json ... ``` 围栏（记录 warning）、前后解释文字包裹。
    返回 (parsed, warnings, error)。
    """
    if not raw_text or not isinstance(raw_text, str):
        return None, [], "empty_response"
    text = raw_text.strip()
    # 去除单个代码围栏
    cleaned = text
    if text.startswith("```") and text.rstrip().endswith("```"):
        inner = text[3:]
        if inner.startswith("json"):
            inner = inner[4:]
        cleaned = inner.rstrip()[:-3].strip()
        warnings = ["code_fence_stripped"]
    else:
        warnings = []
    try:
        parsed = json.loads(cleaned)
    except Exception:
        # 尝试提取第一个 {...} 对象
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(cleaned[start:end + 1])
                warnings.append("extracted_json_object")
            except Exception:
                return None, warnings, "json_parse_error"
        else:
            return None, warnings, "json_parse_error"
    if not isinstance(parsed, dict):
        return None, warnings, "not_object"
    return parsed, warnings, None


def validate_enrichment_semantics(parsed, input_event, expected_run_id=None):
    """语义校验。返回 (errors, warnings)。

    errors 非空 => invalid_model_output。
    """
    errors = []
    warnings = []

    # event_id 与输入一致
    expect_eid = input_event.get("event_id")
    if parsed.get("event_id") != expect_eid:
        errors.append(f"event_id_mismatch: got={parsed.get('event_id')} expect={expect_eid}")
    # canonical_run_id 一致（若有）
    if expected_run_id and parsed.get("canonical_run_id") != expected_run_id:
        errors.append(f"canonical_run_id_mismatch")
    # country 与 Canonical 一致
    expect_iso = input_event.get("country_iso3") or ""
    if expect_iso and parsed.get("country_iso3") != expect_iso:
        errors.append(f"country_iso3_mismatch: got={parsed.get('country_iso3')} expect={expect_iso}")
    # location.country_iso3 也必须一致（若存在）
    loc = parsed.get("location") or {}
    if isinstance(loc, dict) and loc.get("country_iso3") and expect_iso \
            and loc["country_iso3"] != expect_iso:
        errors.append(f"location.country_iso3_mismatch")

    # title/summary 非空
    if not parsed.get("title_zh"):
        errors.append("title_zh_empty")
    if not parsed.get("summary_zh"):
        errors.append("summary_zh_empty")

    # 枚举
    if parsed.get("event_type") not in EVENT_TYPES:
        errors.append(f"event_type_invalid: {parsed.get('event_type')!r}")
    if parsed.get("security_relevance") not in SECURITY_RELEVANCE:
        errors.append(f"security_relevance_invalid: {parsed.get('security_relevance')!r}")
    if parsed.get("processing_status") not in PROCESSING_STATUS:
        errors.append(f"processing_status_invalid: {parsed.get('processing_status')!r}")

    # confidence 0-100 整数
    conf = parsed.get("classification_confidence")
    if not isinstance(conf, int) or isinstance(conf, bool):
        errors.append(f"confidence_not_int: {conf!r}")
    elif not (0 <= conf <= 100):
        errors.append(f"confidence_out_of_range: {conf}")

    # key_facts / uncertainties 数组
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

    # 不允许 Markdown 围栏 / 额外自由文本（title/summary 内）
    for field in ("title_zh", "summary_zh"):
        val = parsed.get(field) or ""
        if "```" in val:
            errors.append(f"{field}_contains_fence")
    if not isinstance(parsed.get("ai_provider"), str) or not parsed.get("ai_model"):
        errors.append("provider_model_missing")

    return errors, warnings


def validate_enrichment(parsed, input_event, expected_run_id=None):
    """完整校验（Schema 已由外部 json 校验器执行；这里补语义）。

    返回 (ok, errors, warnings)。
    """
    errors, warnings = validate_enrichment_semantics(parsed, input_event, expected_run_id)
    return len(errors) == 0, errors, warnings
