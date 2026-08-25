#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 冲突检测（§八）。

第一版只检测高价值字段冲突：country / date / location / deaths / injured /
responsible_party / event_type。不做全文事实图谱。

输入：baseline（canonical 基准值）+ sources_values（各来源提取的字段值）。
输出：conflicts = [{field, value_a, source_a, value_b, source_b}, ...]

发现冲突后由规则引擎置 verification_status=conflicting，绝不自动"选一个是真的"。
"""

from .constants import CONFLICT_FIELDS

_FIELD_ALIASES = {
    "country": ("country", "country_code", "detected_country", "event_country"),
    "date": ("date", "event_date", "published_date"),
    "location": ("location", "location_name", "detected_location", "city"),
    "deaths": ("deaths", "death_count", "fatalities"),
    "injured": ("injured", "injured_count", "wounded"),
    "responsible_party": ("responsible_party", "responsible", "perpetrator", "actor"),
    "event_type": ("event_type", "type"),
}


def _pick(d, keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", []):
            return v
    return None


def _norm(value):
    """字段值归一化（小写、去空白），用于比较。"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return str(value).strip()
    return str(value).strip().lower()


def detect_conflicts(baseline, sources_values):
    """检测高价值冲突。

    baseline: dict（canonical 基准，如 {"country": "TCD", "event_type": "x"}）
    sources_values: list[dict]，每个 dict 含 source_id 及可选字段值。
    返回 (conflicts, uncertainties)。
    """
    conflicts = []
    uncertainties = []
    for field in CONFLICT_FIELDS:
        base_val = _pick(baseline, _FIELD_ALIASES[field])
        seen = {}
        for sv in sources_values:
            sid = sv.get("source_id") or "?"
            val = _pick(sv, _FIELD_ALIASES[field])
            if val is None:
                continue
            nv = _norm(val)
            if nv in (None, ""):
                continue
            # 与基准冲突（基准存在且不同）
            if base_val is not None and _norm(base_val) != nv:
                conflicts.append({
                    "field": field,
                    "value_a": base_val,
                    "source_a": "canonical",
                    "value_b": val,
                    "source_b": sid,
                })
                continue
            # 来源间互不一致
            for other_sid, other_val in seen.items():
                if other_val != nv:
                    conflicts.append({
                        "field": field,
                        "value_a": other_val,
                        "source_a": other_sid,
                        "value_b": val,
                        "source_b": sid,
                    })
            seen[sid] = nv
        if base_val is None and not seen:
            uncertainties.append("%s 无法从来源确认" % field)
    return conflicts, uncertainties
