#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalizers.py —— ASIP Stage-2 字段归一化

负责把遗留字段映射到规范枚举，并落实核心分离原则：
- 来源等级(source_reliability_tier) ≠ 核实状态(verification_level)
- 国家风险等级(country_risk_level) ≠ 事件严重程度(event_severity)
- 提及某国(mentioned_countries) ≠ 事件发生国(event_country)
- 处理状态(processing_status) ≠ 发布状态(publication_status)
- Reuters 单一来源不得标为 direct_official_source
- ReliefWeb 普通 NGO 内容不得自动变成联合国官方通报
"""

import re

# ── 国家中文名 → ISO 3166-1 alpha-2 ──────────────────────
COUNTRY_CN_TO_ISO = {
    "乍得": "TD", "尼日尔": "NE", "苏丹": "SD", "南苏丹": "SS",
    "尼日利亚": "NG", "肯尼亚": "KE", "埃塞俄比亚": "ET", "利比亚": "LY",
    "莫桑比克": "MZ", "贝宁": "BJ", "喀麦隆": "CM", "中非": "CF",
    "马里": "ML", "布基纳法索": "BF", "毛里塔尼亚": "MR", "塞内加尔": "SN",
    "几内亚": "GN", "科特迪瓦": "CI", "加纳": "GH", "多哥": "TG",
    "刚果（布）": "CG", "刚果（金）": "CD", "乌干达": "UG", "坦桑尼亚": "TZ",
    "索马里": "SO", "厄立特里亚": "ER", "吉布提": "DJ", "卢旺达": "RW",
    "布隆迪": "BI", "马拉维": "MW", "赞比亚": "ZM", "津巴布韦": "ZW",
    "安哥拉": "AO", "纳米比亚": "NA", "博茨瓦纳": "BW", "南非": "ZA",
    "埃及": "EG", "阿尔及利亚": "DZ", "摩洛哥": "MA", "突尼斯": "TN",
    "西撒哈拉": "EH", "佛得角": "CV", "冈比亚": "GM", "几内亚比绍": "GW",
    "塞拉利昂": "SL", "利比里亚": "LR", "加蓬": "GA", "赤道几内亚": "GQ",
    "圣多美和普林西比": "ST", "科摩罗": "KM", "马达加斯加": "MG",
    "毛里求斯": "MU", "塞舌尔": "SC", "斯威士兰": "SZ", "莱索托": "LS",
}

ISO_TO_CN = {v: k for k, v in COUNTRY_CN_TO_ISO.items()}

# ── 语言归一化 ───────────────────────────────────────────
LANGUAGE_CN_TO_ISO = {
    "中文": "zh", "汉语": "zh", "英文": "en", "英语": "en", "法文": "fr",
    "法语": "fr", "阿拉伯文": "ar", "阿拉伯语": "ar", "西班牙文": "es",
    "西班牙语": "es", "葡萄牙文": "pt", "葡萄牙语": "pt", "俄文": "ru",
    "俄语": "ru", "德文": "de", "德语": "de", "日文": "ja", "日语": "ja",
    "意大利文": "it", "土耳其语": "tr", "豪萨文": "ha", "斯瓦希里文": "sw",
    "未识别": "und", "未知": "und", "": "und",
}

# ── 事件严重程度枚举 ─────────────────────────────────────
EVENT_SEVERITY_ENUMS = {"low", "medium", "high", "critical"}

# ── 事件状态枚举 ───────────────────────────────────────
EVENT_STATUS_ENUMS = {"new", "ongoing", "developing", "easing", "ended", "unknown"}

# ── 核实等级枚举 ───────────────────────────────────────
VERIFICATION_LEVEL_ENUMS = {
    "not_checked", "insufficient_information", "single_source",
    "high_reliability_single_source", "direct_official_source",
    "cross_verified", "conflicting_reports",
}

# ── 发布状态枚举 ───────────────────────────────────────
PUBLICATION_STATUS_ENUMS = {
    "verification_pending", "publishable", "published",
    "suppressed", "quarantined", "archived",
}

# ── 处理状态枚举 ───────────────────────────────────────
PROCESSING_STATUS_ENUMS = {
    "raw", "normalized", "classified", "queued_for_verification",
    "linked_to_event", "quarantined", "archived",
}

# ── 待核实队列状态枚举 ─────────────────────────────────
VERIFICATION_QUEUE_STATUS_ENUMS = {
    "not_required", "waiting", "searching", "completed", "expired", "failed",
}

# ── 隔离原因枚举 ───────────────────────────────────────
QUARANTINE_REASON_ENUMS = {
    "wrong_country", "not_security_relevant", "duplicate", "invalid_url",
    "missing_required_fields", "unsupported_language", "conflicting_data",
    "low_quality_source", "legacy_invalid", "schema_validation_failed", "other",
}

# ── 来源类型枚举 ───────────────────────────────────────
SOURCE_TYPE_ENUMS = {
    "government", "military_or_police", "international_media", "state_media",
    "local_media", "humanitarian", "international_organization", "ngo",
    "research", "social_media", "aggregation_platform", "other",
}

# ── 来源可靠等级枚举 ───────────────────────────────────
SOURCE_RELIABILITY_TIER_ENUMS = {"tier_1", "tier_2", "tier_3", "lead_only"}

# ── claim 来源类型枚举 ─────────────────────────────────
CLAIM_ORIGIN_TYPE_ENUMS = {
    "direct_government_statement", "direct_military_statement",
    "direct_international_organization_report", "direct_humanitarian_report",
    "media_reporting", "ngo_report", "commentary", "unknown",
}


def normalize_country_code(name) -> str:
    """国家中文名 → ISO alpha-2；已是 ISO 则原样返回；未知返回 ''。"""
    if not name:
        return ""
    s = str(name).strip()
    if s.upper() in ISO_TO_CN:
        return s.upper()
    return COUNTRY_CN_TO_ISO.get(s, "")


def normalize_country_cn(code_or_name) -> str:
    """ISO 或中文名 → 中文名；未知返回原串。"""
    if not code_or_name:
        return ""
    s = str(code_or_name).strip()
    if s in COUNTRY_CN_TO_ISO:
        return s
    up = s.upper()
    if up in ISO_TO_CN:
        return ISO_TO_CN[up]
    return s


def normalize_language(lang) -> str:
    if not lang:
        return "und"
    return LANGUAGE_CN_TO_ISO.get(str(lang).strip(), "und")


def normalize_event_severity(sev) -> str:
    """遗留 severity（高/中/低/critical...）→ 枚举。"""
    if not sev:
        return "medium"
    s = str(sev).strip().lower()
    if s in EVENT_SEVERITY_ENUMS:
        return s
    m = {"高": "high", "中": "medium", "低": "low", "极高": "critical",
         "严重": "critical", "较重": "high", "较轻": "low"}
    return m.get(s, "medium")


def normalize_event_status(status) -> str:
    if not status:
        return "ongoing"
    s = str(status).strip().lower()
    if s in EVENT_STATUS_ENUMS:
        return s
    m = {"新发": "new", "进行中": "ongoing", "持续": "ongoing", "发展中": "developing",
         "缓和": "easing", "结束": "ended", "未知": "unknown"}
    return m.get(s, "ongoing")


def _is_direct_official(source_type: str, source_group: str, is_direct_origin: bool) -> bool:
    """事件是否「直接机构通报」：依据来源属性与 claim_origin_type，不依据域名简单判断。"""
    if is_direct_origin and source_type in ("government", "military_or_police",
                                            "international_organization"):
        return True
    # ReliefWeb 上的普通 NGO 报告 —— 不是联合国官方通报
    if source_group == "reliefweb":
        return False
    # 媒体（含 Reuters/新华社）单一报道 —— 不是官方通报
    if source_type in ("international_media", "state_media", "local_media", "social_media"):
        return False
    return False


def derive_verification_level(legacy_event: dict, *, source_type: str = "",
                              source_group: str = "", is_direct_origin: bool = False,
                              independent_source_count: int = 1,
                              claim_origin_type: str = "") -> str:
    """由遗留字段推导 verification_level（确定性、可解释、可复核）。

    核心约束：
    - 单一媒体来源（无论 Reuters 多可靠）不得为 direct_official_source / cross_verified；
    - ReliefWeb 平台上的 NGO 报告不得升级为联合国官方通报；
    - 仅当 claim_origin_type 明确为直接机构声明且来源为官方时，才为 direct_official_source。
    """
    vs = str(legacy_event.get("verification_status") or legacy_event.get("confidence") or "").strip().lower()
    conf = str(legacy_event.get("confidence") or "").strip().lower()

    # 明确直接机构声明
    if claim_origin_type in ("direct_government_statement", "direct_military_statement",
                             "direct_international_organization_report") and \
       _is_direct_official(source_type, source_group, is_direct_origin):
        return "direct_official_source"

    # 多源交叉核实
    if independent_source_count >= 2:
        return "cross_verified"

    # 来源本身是否高可靠媒体
    if source_group in ("reuters",) or source_type in ("international_media", "state_media"):
        # 单一高可靠媒体来源：只能是「高可靠单一来源」，绝不能直接官方通报
        return "high_reliability_single_source"

    # 已核实但来源非官方：单一来源
    if vs in ("verified", "已核实") or conf in ("已核实", "较高可信"):
        return "single_source"

    # 部分核实 / 待核实
    if vs in ("partial", "pending", "unverified", ""):
        return "insufficient_information"

    return "not_checked"


def derive_needs_translation(record: dict) -> bool:
    """是否仍需中文翻译：title_cn / summary_cn 为空即需要。"""
    return not (record.get("title_cn") or record.get("summary_cn"))


def canonical_article_title_cn(record: dict) -> str:
    return record.get("title_cn") or ""


def canonical_article_summary_cn(record: dict) -> str:
    return record.get("summary_cn") or ""


def strip_extra_whitespace(s) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", str(s).strip())
