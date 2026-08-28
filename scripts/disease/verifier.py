#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 传染病核实（§十三）。

复用 Stage 5 verification 思路，但区分疾病模块特性：
- 数字优先级：Tier A 官方疫情来源 > 国家卫生部门 > 国际权威机构 > 高可信媒体
  > 本地媒体 > 聚合平台；
- WHO=120 / 媒体=118 等数字差异 → data_difference（不自动判错）；
- 不同报告时间的数字变化 → temporal_update（优先于 conflict）；
- 真正核心冲突（同一时点官方状态互相矛盾）才降级处理；
- 聚合平台（NewsNow）只作 lead，不得作为病例/死亡 primary source。
"""

from .constants import (
    VERIFY_OFFICIAL, VERIFY_CORROBORATED, VERIFY_SINGLE_SOURCE,
    VERIFY_DATA_DIFFERENCE, VERIFY_TEMPORAL_UPDATE, VERIFY_UNVERIFIED,
)

# 来源层级权重（官方源优先）
_TIER_WEIGHT = {"A": 4, "B": 3, "B2": 2, "C": 1, "D": 0}


def _best_source(sources):
    """sources: list of {source_id, source_tier, url, source_name, official}。
    返回最高权重来源（同权重取官方标记优先）。"""
    if not sources:
        return None
    return max(sources, key=lambda s: (_TIER_WEIGHT.get(s.get("source_tier"), 0),
                                       s.get("official", False)))


def verify_numbers(primary_value, others, primary_report_date, other_report_dates):
    """核心数字核实。

    primary_value: 最高权重来源的数字（官方优先）
    others: list of (source_id, value)
    返回 (status, reasons, notes)：
    - 官方来源存在且提供数字 → official；
    - 其他来源数字与官方不同：
      * 报告日期不同 → temporal_update；
      * 报告日期相同 → data_difference（不自动判错）；
    - 官方无数字、多来源一致 → corroborated；单一 → single_source；
    - 无任何来源数字 → unverified。
    """
    reasons = []
    if primary_value is not None:
        reasons.append("official_number:%s" % primary_value)
        diffs = []
        for sid, val in others:
            if val is None or val == primary_value:
                continue
            d = other_report_dates.get(sid)
            p = primary_report_date
            if d and p and d != p:
                diffs.append((sid, val, "temporal_update"))
            else:
                diffs.append((sid, val, "data_difference"))
        if diffs:
            reasons.append("differs:%s" % ";".join(
                "%s=%s(%s)" % (sid, val, kind) for sid, val, kind in diffs))
            kinds = {k for _, _, k in diffs}
            if kinds == {"temporal_update"}:
                return VERIFY_TEMPORAL_UPDATE, reasons, diffs
            return VERIFY_DATA_DIFFERENCE, reasons, diffs
        return VERIFY_OFFICIAL, reasons, []
    return VERIFY_UNVERIFIED, reasons + ["no_official_number"], []


def classify_event_verification(record, sources):
    """整条事件核实状态（组合数字核实与来源结构）。"""
    primary = _best_source(sources)
    if primary and primary.get("source_tier") == "A":
        return VERIFY_OFFICIAL, ["official_source_tier_a:%s" % primary.get("source_id")]
    tiers = [s.get("source_tier") for s in sources]
    if len(sources) >= 2 and all(t in ("A", "B", "B2") for t in tiers):
        return VERIFY_CORROBORATED, ["two_independent_official_or_media"]
    if sources:
        return VERIFY_SINGLE_SOURCE, ["single_source:%s" % sources[0].get("source_id")]
    return VERIFY_UNVERIFIED, ["no_sources"]
