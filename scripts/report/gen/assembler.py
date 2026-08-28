#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8B — Report Assembler（§三：deterministic envelope ↔ AI content 分离）。

程序责任（envelope）：report_id/report_type/report_date/period_start/period_end/
country_iso3/week_start/week_end/brief_id/event_time/country/generated_at/
report_timezone/generation_metadata/metrics/verification_status。
AI 责任（content）：title/executive_summary/sections/assessment/outlook/等。

流程：validated input → envelope；AI response → content；merge → final report；
final report schema validation 由调用方执行。
AI 即使返回 envelope 字段，也会被 input 确定性值覆盖（metadata cannot be
overridden by AI，§十三）。
"""

# §一：deterministic envelope（程序责任，AI 不得作为 source of truth）
ENVELOPE_FIELDS = {
    "africa_daily": ["report_id", "report_type", "report_date", "period_start",
                     "period_end", "generated_at", "report_timezone",
                     "generation_metadata"],
    "country_weekly": ["report_id", "report_type", "country_iso3", "week_start",
                       "week_end", "generated_at", "report_timezone",
                       "generation_metadata", "metrics"],
    "major_event_brief": ["brief_id", "report_type", "event_time", "country",
                          "country_iso3", "generated_at", "report_timezone",
                          "generation_metadata", "verification_status"],
}


def assemble_report(task_type, report_input, ai_content, meta=None):
    """merge envelope + AI content → final report object（§三）。

    report_input: 已验证的报告输入契约（fixture / development input）
    ai_content:   AI 返回的内容负载（已过 AI content schema）
    meta:         生成元数据（provider/model/prompt_version/usage_purpose 等）
    """
    src = report_input if isinstance(report_input, dict) else {}
    final = dict(ai_content or {})
    for f in ENVELOPE_FIELDS.get(task_type, []):
        if f == "generation_metadata":
            m = dict(meta or {})
            m.setdefault("provider_name", "deepseek")
            m.setdefault("model_name", "deepseek-v4-flash")
            m.setdefault("prompt_version", "v1.0.2")
            m.setdefault("usage_purpose", "production_qualification")
            m.setdefault("report_status", "draft")
            final[f] = m
        elif f == "report_timezone":
            final[f] = "Asia/Shanghai"
        elif f == "metrics" and task_type == "country_weekly":
            final[f] = src.get("trend_metrics") or {}
        elif f == "verification_status" and task_type == "major_event_brief":
            final[f] = src.get("verification_status")
        elif f == "country_iso3" and task_type == "major_event_brief":
            final[f] = src.get("country_iso3")
        else:
            final[f] = src.get(f)   # 确定性：始终以 input 为准（AI 不可覆盖）
    return final


def envelope_metadata(ai_content, task_type):
    """返回 AI 响应中（如有）的 envelope 字段，供审计（证明 AI 曾尝试覆盖）。"""
    return {f: ai_content.get(f) for f in ENVELOPE_FIELDS.get(task_type, [])
            if f in ai_content}
