#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 事件自动核实核心 V1：常量与枚举。"""

# verification_status 固定枚举（§三）
STATUS_VERIFIED = "verified"
STATUS_PROBABLE = "probable"
STATUS_SINGLE_SOURCE = "single_source"
STATUS_CONFLICTING = "conflicting"
STATUS_UNVERIFIED = "unverified"
STATUS_REJECTED = "rejected"

STATUS_ENUM = {
    STATUS_VERIFIED, STATUS_PROBABLE, STATUS_SINGLE_SOURCE,
    STATUS_CONFLICTING, STATUS_UNVERIFIED, STATUS_REJECTED,
}

# 来源可信度层级（§四）
TIER_A = "A"  # 官方政府 / WHO-UN-Africa CDC / Reuters-AP 等高可信国际通讯社
TIER_B = "B"  # BBC-RFI-France24-Al Jazeera / 国家级主流媒体 / 稳定区域媒体
TIER_C = "C"  # 本地媒体 / 专题媒体 / 有稳定历史但核实能力有限
TIER_D = "D"  # 聚合平台 / 未确认来源 / 低稳定来源
TIERS = {TIER_A, TIER_B, TIER_C, TIER_D}

# support_type（§七）
SUPPORT_PRIMARY = "primary"
SUPPORT_SUPPORTING = "supporting"
SUPPORT_OFFICIAL = "official_confirmation"
SUPPORT_SECONDARY = "secondary_report"
SUPPORT_LEAD_ONLY = "lead_only"
SUPPORT_TYPES = {
    SUPPORT_PRIMARY, SUPPORT_SUPPORTING, SUPPORT_OFFICIAL,
    SUPPORT_SECONDARY, SUPPORT_LEAD_ONLY,
}

# 聚合平台标记（NewsNow 一类，只能 discovery/lead，不得作 primary/official）
AGGREGATOR_KEYWORDS = (
    "newsnow", "aggregat", "feedly", "allafrica", "miragenews", "google news",
    "smartnews", "flipboard",
)

# 核实方法（§九）
METHOD_DETERMINISTIC = "deterministic_rules_v1"
METHOD_AI_DEV_TEST = "hybrid_ai_development_test"

# 规则版本
RULES_VERSION = "1.0.0"

# 一致性枚举
CONSISTENT = "consistent"
CONFLICT = "conflict"
UNKNOWN = "unknown"
CONSISTENCY_ENUM = {CONSISTENT, CONFLICT, UNKNOWN}

# 冲突字段（§八：高价值冲突）
CONFLICT_FIELDS = (
    "country", "date", "location", "deaths", "injured", "responsible_party", "event_type",
)

# 确定性规则产出（§五）默认置信度区间
CONFIDENCE_VERIFIED = 85
CONFIDENCE_PROBABLE = 70
CONFIDENCE_SINGLE_SOURCE = 45
CONFIDENCE_CONFLICTING = 25
CONFIDENCE_UNVERIFIED = 10
CONFIDENCE_REJECTED = 5
