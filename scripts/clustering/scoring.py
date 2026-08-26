#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6A — Hard Reject 规则（§八 R1-R5）与 Positive Features（§九）。

Hard Reject 任一成立 → same_event=false，且不得被 score 覆盖。
Positive Features 通过 Hard Reject 后打分（配置化权重，100 封顶）。
数值不一致（casualty）不自动 reject → 仅 conflict_flag（§十一）。
"""

import re

from .sources import time_delta_hours

# ── §九 权重（配置化，勿散落 hardcode）──
WEIGHTS = {
    "same_normalized_country": 0,      # prerequisite（不计分，Hard Reject 前检查）
    "same_normalized_location": 25,
    "same_calendar_day": 20,
    "within_24h": 15,
    "compatible_event_type": 15,
    "shared_distinctive_named_entity": 15,
    "shared_uncommon_numeric_fact": 10,
    "same_casualty_figure": 10,
    "same_named_facility": 15,
    "high_title_similarity": 10,
    "shared_original_event_reference": 20,
}
SCORE_CAP = 100

# §八 R4 event_type compatibility matrix（最小集；不在表内视为不兼容，保守）
COMPATIBLE_TYPES = {
    "armed_attack": {"armed_attack", "terrorism", "other_security"},
    "terrorism": {"terrorism", "armed_attack", "other_security"},
    "civil_unrest": {"civil_unrest", "protest", "strike"},
    "protest": {"civil_unrest", "protest", "strike"},
    "strike": {"civil_unrest", "protest", "strike"},
    "kidnapping": {"kidnapping", "crime_kidnapping", "other_security"},
    "crime_kidnapping": {"kidnapping", "crime_kidnapping", "other_security"},
    "border_security": {"border_security", "other_security"},
    "political_instability": {"political_instability", "civil_unrest", "other_security"},
    "other_security": {"armed_attack", "terrorism", "kidnapping", "crime_kidnapping",
                       "border_security", "other_security"},
    "economic": {"economic", "natural_disaster"},
    "natural_disaster": {"natural_disaster", "economic", "humanitarian"},
    "humanitarian": {"humanitarian", "natural_disaster"},
}
DEFAULT_COMPATIBLE = False


def event_types_compatible(t1, t2):
    if not t1 or not t2:
        return True  # 类型未知不 reject（保守通过，分数自会低）
    if t1 == t2:
        return True
    return t2 in COMPATIBLE_TYPES.get(t1, {}) or t1 in COMPATIBLE_TYPES.get(t2, {})


def _norm_loc(loc):
    if not loc:
        return None
    return " ".join(str(loc).strip().lower().split())


def hard_reject(a, b):
    """返回 (rejected, reason)。任一 Hard Reject 成立 → rejected。"""
    # R1 Country mismatch
    ca, cb = a.get("primary_country_iso3"), b.get("primary_country_iso3")
    if ca and cb and ca != cb:
        from .sources import cross_border
        if not cross_border(a, b):
            return True, "R1_country_mismatch"

    # R2 Time separation > 72h
    ts_a = a.get("event_time") or a.get("published_at")
    ts_b = b.get("event_time") or b.get("published_at")
    if ts_a and ts_b:
        dh = time_delta_hours(ts_a, ts_b)
        if dh is not None and dh > 72:
            return True, "R2_time_separation_gt72h"

    # R3 Distinct explicit location
    la, lb = _norm_loc(a.get("location")), _norm_loc(b.get("location"))
    if la and lb and la != lb:
        # 同一行政区别名/上级区域判定（简化：完全字符串相等才放行；别名库后续扩展）
        if not (la in lb or lb in la):
            return True, "R3_distinct_location"

    # R4 Incompatible event types
    if not event_types_compatible(a.get("event_type"), b.get("event_type")):
        return True, "R4_incompatible_event_type"

    # R5 Distinct target/event：同国家同日同 actor 但明确目标不同 → 分离
    ta, tb = _norm_loc(a.get("target")), _norm_loc(b.get("target"))
    if (a.get("actor") and b.get("actor") and a.get("actor") == b.get("actor")
            and ta and tb and ta != tb):
        return True, "R5_distinct_target"

    return False, None


def _norm_title_similarity(a_title, b_title):
    """跨语言标题相似度（辅助 feature）：字符 n-gram Jaccard。"""
    from difflib import SequenceMatcher
    a = (a_title or "").lower()
    b = (b_title or "").lower()
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _shared_distinctive_entity(a, b):
    """共享独特命名实体（长度≥5 的 title token 交集，排除停用词）。"""
    stop = {"the", "and", "for", "with", "from", "that", "this", "was", "are",
            "le", "la", "les", "des", "une", "du", "et", "pour", "dans", "sur",
            "de", "en", "au", "aux", "a", "l", "d", "on", "an", "the"}
    ta = {w for w in re.split(r"\W+", (a.get("title") or "").lower()) if len(w) >= 5 and w not in stop}
    tb = {w for w in re.split(r"\W+", (b.get("title") or "").lower()) if len(w) >= 5 and w not in stop}
    shared = ta & tb
    # 排除通用词（数字、月份、星期）
    generic = {"august", "september", "october", "november", "december", "january",
               "february", "march", "april", "may", "june", "july", "monday",
               "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
               "report", "update", "news", "kills", "dies", "dead", "africa"}
    return shared - generic


def _same_day(a_ts, b_ts):
    from datetime import datetime
    try:
        da = datetime.fromisoformat(str(a_ts).replace("Z", "+00:00")).date()
        db = datetime.fromisoformat(str(b_ts).replace("Z", "+00:00")).date()
        return da == db
    except (ValueError, TypeError):
        return False


def score_pair(a, b):
    """Hard Reject 通过后的 positive feature 打分（0-100）。返回 (score, features)。"""
    s = 0
    feats = []
    # same normalized location
    la, lb = _norm_loc(a.get("location")), _norm_loc(b.get("location"))
    if la and lb and (la == lb or la in lb or lb in la):
        s += WEIGHTS["same_normalized_location"]
        feats.append("same_location")
    # time
    ts_a = a.get("event_time") or a.get("published_at")
    ts_b = b.get("event_time") or b.get("published_at")
    if ts_a and ts_b:
        if _same_day(ts_a, ts_b):
            s += WEIGHTS["same_calendar_day"]
            feats.append("same_calendar_day")
        else:
            dh = time_delta_hours(ts_a, ts_b)
            if dh is not None and dh <= 24:
                s += WEIGHTS["within_24h"]
                feats.append("within_24h")
    # event type compatible（Hard Reject 已保证兼容，这里给分）
    if a.get("event_type") and a.get("event_type") == b.get("event_type"):
        s += WEIGHTS["compatible_event_type"]
        feats.append("same_event_type")
    # shared distinctive entity
    shared = _shared_distinctive_entity(a, b)
    if shared:
        s += WEIGHTS["shared_distinctive_named_entity"]
        feats.append("shared_entity:%s" % ",".join(sorted(shared))[:40])
    # shared uncommon numeric fact
    na, nb = a.get("numeric_facts") or [], b.get("numeric_facts") or []
    if na and nb and set(na) & set(nb):
        s += WEIGHTS["shared_uncommon_numeric_fact"]
        feats.append("shared_numeric")
    # same casualty figure
    ca, cb = a.get("casualties"), b.get("casualties")
    if ca and cb and ca == cb:
        s += WEIGHTS["same_casualty_figure"]
        feats.append("same_casualties:%s" % ca)
    # same named facility
    fa, fb = _norm_loc(a.get("facility")), _norm_loc(b.get("facility"))
    if fa and fb and (fa == fb or fa in fb or fb in fa):
        s += WEIGHTS["same_named_facility"]
        feats.append("same_facility")
    # title similarity（辅助）
    sim = _norm_title_similarity(a.get("title"), b.get("title"))
    if sim >= 0.75:
        s += WEIGHTS["high_title_similarity"]
        feats.append("title_similarity:%.2f" % sim)
    # shared original event reference
    if (a.get("original_event_ref") and a.get("original_event_ref") == b.get("original_event_ref")):
        s += WEIGHTS["shared_original_event_reference"]
        feats.append("shared_original_ref")
    return min(s, SCORE_CAP), feats
