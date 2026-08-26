#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7A — Report Engine 配置（§七/§九/§二十 权重配置化，不散落 hardcode）。

importance / trigger 权重与数量上限全部集中在此，运行时可用
ASIP_REPORT_* 环境变量覆盖。
"""

import os

# §七 日报重要性权重（report_importance_score 0-100，cap 100）
IMPORTANCE_WEIGHTS = {
    "major_casualties": int(os.environ.get("ASIP_REPORT_W_MAJOR_CASUALTIES", "20")),
    "terrorism_armed_conflict": int(os.environ.get("ASIP_REPORT_W_TERRORISM", "20")),
    "coup_political_crisis": int(os.environ.get("ASIP_REPORT_W_COUP", "20")),
    "cross_border": int(os.environ.get("ASIP_REPORT_W_CROSS_BORDER", "15")),
    "official_statement_emergency": int(os.environ.get("ASIP_REPORT_W_OFFICIAL", "10")),
    "verified_multi_source": int(os.environ.get("ASIP_REPORT_W_VERIFIED", "10")),
    "developing": int(os.environ.get("ASIP_REPORT_W_DEVELOPING", "10")),
    "significant_change": int(os.environ.get("ASIP_REPORT_W_CHANGE", "15")),
    "priority_country": int(os.environ.get("ASIP_REPORT_W_PRIORITY", "10")),
    "disease_new_or_cross_border": int(os.environ.get("ASIP_REPORT_W_DISEASE", "15")),
}

# §九 数量控制
DAILY_SECURITY_MIN = 8
DAILY_SECURITY_MAX = 15
DAILY_DISEASE_MIN = 2
DAILY_DISEASE_MAX = 5
EXEC_SUMMARY_MAX = 8
EXEC_SUMMARY_MIN = 5

# §八 低价值内容关键词（security_relevance=none 原则延续）
LOW_VALUE_KEYWORDS = (
    "business meeting", "商务会见", "investment", "投资", "agricultural goods",
    "农业物资", "employment data", "就业数据", "cultural", "culture", "文化",
    "sports", "体育", "ceremonial visit", "礼仪性访问", "general development",
    "一般发展项目", "forum", "论坛", "seminar", "研讨会", "workshop",
)
# 低价值豁免：明确引发社会稳定/安全/重大公共卫生影响的信号
LOW_VALUE_EXEMPT_SIGNALS = (
    "stability", "security", "protests", "safety", "public health",
    "社会稳定", "安全", "公共卫生",
)

# §二十 Major Event Trigger 权重（0-100，≥ threshold → brief_candidate）
TRIGGER_WEIGHTS = {
    "mass_casualty": int(os.environ.get("ASIP_REPORT_T_MASS_CASUALTY", "25")),
    "terrorism_armed_conflict": int(os.environ.get("ASIP_REPORT_T_TERRORISM", "20")),
    "cross_border": int(os.environ.get("ASIP_REPORT_T_CROSS_BORDER", "15")),
    "capital_strategic": int(os.environ.get("ASIP_REPORT_T_CAPITAL", "10")),
    "official_emergency": int(os.environ.get("ASIP_REPORT_T_EMERGENCY", "10")),
    "rapid_escalation": int(os.environ.get("ASIP_REPORT_T_RAPID", "15")),
    "multi_country": int(os.environ.get("ASIP_REPORT_T_MULTI_COUNTRY", "15")),
}
TRIGGER_THRESHOLD = int(os.environ.get("ASIP_REPORT_TRIGGER_THRESHOLD", "70"))

# §十六 priority_report_country 配置（是否启用 weekly 由配置决定）
PRIORITY_REPORT_COUNTRIES = {
    "TCD": True,   # 默认启用（试点）
    "NER": True,
    "SSD": True,
    "BEN": False,  # 默认不启用
    "ETH": False,  # 默认不启用（Source 层 debt 未修复）
}

# §六 eligibility：被拒/隔离状态
REJECTED_STATUSES = {"rejected"}
QUARANTINE_MARKER = "quarantine"
REVIEW_BEFORE_ACTIVATION = {"review_before_activation"}
