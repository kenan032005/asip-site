#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 传染病事件归一化（§十/§十一/§十二）。

核心准确性约束：
- 病例/死亡数字：confirmed/probable/suspected 分开；total_cases 优先用来源
  明确提供的总数（case_count_type=source_total）；仅当来源记录明确允许相加
  时才计算并标记 computed_total；未知一律 null，不得用 0 代替；
- 日期：report_date（发布日）≠ event_start_date（事件开始）≠ case_period
  （统计窗口），不得混淆；
- 地域：country_iso3/admin1/admin2/location_raw；跨境事件 cross_border=true
  + affected_countries，不复制成多个独立事件。
"""

import re

from .diseases import resolve_disease_id
from .constants import (
    CASE_COUNT_SOURCE_TOTAL, CASE_COUNT_COMPUTED_TOTAL,
    CASE_COUNT_CONFIRMED_ONLY, CASE_COUNT_UNKNOWN,
    NUMERIC_FIELDS,
)

_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def _int_or_none(v):
    """数字解析：None/空/非数字 → None（未知，不得 0）。"""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if v >= 0 else None
    if isinstance(v, float):
        return int(v) if v >= 0 else None
    s = str(v).strip().replace(",", "").replace(" ", "")
    if not s or not s.isdigit():
        return None
    n = int(s)
    return n if n >= 0 else None


def _valid_date(v):
    if not v:
        return None
    s = str(v).strip()[:10]
    return s if _DATE_RE.match(s) else None


def normalize_numeric(raw, field):
    """单个数字字段归一化（负值/非法 → None）。"""
    return _int_or_none(raw)


def normalize_case_counts(cases):
    """归一化病例数字。

    cases: dict，可含 confirmed_cases/probable_cases/suspected_cases/
    total_cases/deaths/recoveries（来源原值，可为 str/int/None）。

    返回 (record_fields, data_quality_flags)：
    - 各数字字段为 int 或 None（未知绝不写 0）；
    - 若来源未给 total 但给 confirmed，不自动相加；
    - case_count_type 按来源是否提供 total 判定。
    """
    out = {}
    flags = []
    for f in NUMERIC_FIELDS:
        raw = cases.get(f)
        if isinstance(raw, (dict, list)):
            flags.append("numeric_field_unparseable:%s" % f)
            out[f] = None
            continue
        v = _int_or_none(raw)
        out[f] = v
        if raw is not None and v is None:
            flags.append("numeric_field_unparseable:%s" % f)

    src_total = cases.get("total_cases")
    cct_explicit = cases.get("case_count_type")
    if cct_explicit in (CASE_COUNT_SOURCE_TOTAL, CASE_COUNT_COMPUTED_TOTAL,
                        CASE_COUNT_CONFIRMED_ONLY, CASE_COUNT_UNKNOWN):
        # 来源语义优先：候选/解析器显式给定的 case_count_type 保留
        out["case_count_type"] = cct_explicit
    elif src_total is not None and _int_or_none(src_total) is not None:
        out["case_count_type"] = CASE_COUNT_SOURCE_TOTAL
    elif out.get("confirmed_cases") is not None:
        out["case_count_type"] = CASE_COUNT_CONFIRMED_ONLY
    else:
        out["case_count_type"] = CASE_COUNT_UNKNOWN

    # 未知数字必须 null（而不是 0）—— 断言性检查（数据完整性）
    for f in NUMERIC_FIELDS:
        if out.get(f) == 0 and cases.get(f) is None:
            flags.append("zero_instead_of_unknown:%s" % f)
    return out, flags


def compute_total_from_components(confirmed, probable, suspected, record_case_counts=True):
    """仅当调用方明确允许时，由 confirmed+probable+suspected 计算 total。

    返回 (total, computed_flag)。未知分量按 0 参与计算时会在 flag 中记录，
    供质量 Gate 判定（默认不建议使用 computed_total）。
    """
    parts = [x for x in (confirmed, probable, suspected) if x is not None]
    if not parts:
        return None, False
    return sum(parts), True


def normalize_dates(dates):
    """日期归一化。dates 可含 report_date/event_start_date/event_end_date/
    case_period_start/case_period_end。

    返回 (out, flags)。区分 report_date 与事件日期/统计窗口。
    """
    out = {}
    flags = []
    for k in ("report_date", "event_start_date", "event_end_date",
              "case_period_start", "case_period_end"):
        v = _valid_date(dates.get(k))
        out[k] = v
        if dates.get(k) is not None and v is None:
            flags.append("invalid_date:%s" % k)
    if not out.get("report_date"):
        flags.append("missing_report_date")
    return out, flags


def normalize_geo(geo):
    """地域归一化。geo 可含 country_iso3/admin1/admin2/location_raw/
    cross_border/affected_countries。

    返回 (out, flags)。跨境不复制事件，仅标记 cross_border + affected_countries。
    """
    out = {}
    flags = []
    iso3 = (geo.get("country_iso3") or "").strip().upper()
    if iso3 == "AFRICA" or iso3 == "REGIONAL":
        iso3 = "regional"
    out["country_iso3"] = iso3 if iso3 else None
    if not out["country_iso3"]:
        flags.append("missing_country_iso3")
    elif len(iso3) != 3 and iso3 != "regional":
        flags.append("invalid_country_iso3:%s" % iso3)
    for k in ("admin1", "admin2", "location_raw"):
        v = (geo.get(k) or "").strip() or None
        out[k] = v
    cross = bool(geo.get("cross_border"))
    out["cross_border"] = cross
    affected = [c.strip().upper() for c in (geo.get("affected_countries") or []) if c and c.strip()]
    out["affected_countries"] = affected if affected else []
    if cross and not affected:
        flags.append("cross_border_without_affected_countries")
    return out, flags


def build_disease_event(canonical_id, raw):
    """把一条来源原始通报归一化为 disease event 字段（不含 verified_at 等审计字段）。

    raw: dict，来源字段（disease_raw/country_iso3/dates/cases/geo/source...）。
    返回 (fields, flags)；解析失败以 flags=normalization_incomplete 标记，不猜测。
    """
    flags = []

    disease_id = resolve_disease_id(raw.get("disease_raw") or raw.get("disease_name"))
    if not disease_id:
        # 无法解析：不猜测为 other（other 仅用于来源明确声明"其他"）；质量 Gate 将拒绝
        flags.append("normalization_incomplete:disease_unresolved")
    disease_id = disease_id or None

    fields = {
        "disease_event_id": canonical_id,
        "disease_id": disease_id,
        "disease_name_en": raw.get("disease_name_en") or "",
        "disease_name_zh": raw.get("disease_name_zh") or "",
        "pathogen": raw.get("pathogen"),
    }
    if not fields["disease_name_en"]:
        fields["disease_name_en"] = raw.get("disease_raw") or ""

    geo, gflags = normalize_geo(raw)
    fields.update(geo)
    flags.extend(gflags)

    dates, dflags = normalize_dates(raw)
    fields.update(dates)
    flags.extend(dflags)

    cases, cflags = normalize_case_counts(raw)
    fields.update(cases)
    flags.extend(cflags)

    fields["outbreak_status"] = raw.get("outbreak_status") or "unknown"
    fields["update_type"] = raw.get("update_type") or "new_outbreak"

    fields["source_links"] = raw.get("source_links") or []
    fields["primary_source"] = raw.get("primary_source") or ""
    fields["source_tier"] = raw.get("source_tier") or "C"

    fields["verification_status"] = raw.get("verification_status") or "unverified"
    fields["verification_confidence"] = raw.get("verification_confidence") or 0
    fields["previous_event_id"] = raw.get("previous_event_id")
    fields["supersedes_event_id"] = raw.get("supersedes_event_id")
    fields["data_quality_flags"] = flags
    fields["uncertainties"] = raw.get("uncertainties") or []
    return fields
