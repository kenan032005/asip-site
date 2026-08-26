#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7A §十九-§二十 — Major Event Brief Trigger 引擎。

- 非 schedule，条件触发；只生成 trigger_candidate，不自动发布。
- trigger_score 0-100（配置化权重），≥ TRIGGER_THRESHOLD(70) → brief_candidate。
- conflicting 重大事件仍可 candidate（标注 conflicting）。
- 普通事件 / 低伤亡单源事件不触发。
"""

from scripts.report.config import TRIGGER_WEIGHTS, TRIGGER_THRESHOLD

# §十九 触发候选事件类型（含跨境冲突）
TRIGGER_TYPES = {
    "terrorist_attack", "armed_attack", "armed_conflict", "coup", "coup_attempt",
    "mass_protest", "civil_unrest", "kidnapping", "natural_disaster",
    "public_health", "border_incident", "cross_border", "displacement",
}
# 高伤亡门槛（mass casualty）：deaths ≥ 10 或 event_severity 高/极高
MASS_CASUALTY_DEATHS = 10

CROSS_BORDER_KW = ("border", "cross-border", "refugee", "displacement",
                   "跨境", "边境", "难民")
CAPITAL_HINTS = ("capital", "首都", "ndjamena", "n'djamena", "niamey", "juba",
                 "khartoum", "nairobi", "addis ababa")


def _num(v):
    if v is None or v == "":
        return None
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None


def trigger_score(ev, affected_countries=None):
    """§二十 major_event_trigger_score 0-100。返回 (score, reasons)。"""
    W = TRIGGER_WEIGHTS
    score = 0
    reasons = []
    ev_type = (ev.get("event_type") or "").lower()
    title = " ".join([str(ev.get("title_original") or ev.get("title") or ""),
                      str(ev.get("title_cn") or "")]).lower()
    deaths = _num(ev.get("deaths") or ev.get("casualties"))
    severity = ev.get("event_severity")

    # 重大伤亡（§二十）
    if deaths is not None and deaths >= MASS_CASUALTY_DEATHS or severity in ("高", "极高"):
        score += W["mass_casualty"]
        reasons.append("mass_casualty")

    # terrorism / armed conflict / 政变 / 大规模骚乱（§十九/§二十）
    if ev_type in ("terrorist_attack", "armed_attack", "armed_conflict",
                   "military_operation", "coup", "coup_attempt",
                   "mass_protest", "civil_unrest"):
        score += W["terrorism_armed_conflict"]
        reasons.append("terrorism_armed_conflict")

    # cross-border / multi-country
    ac = set(affected_countries or [])
    if ev_type in ("border_incident", "cross_border", "displacement") or \
            any(k in title for k in CROSS_BORDER_KW):
        score += W["cross_border"]
        reasons.append("cross_border")
    if len([c for c in ac if c]) >= 2 or ev.get("multi_country"):
        score += W["multi_country"]
        reasons.append("multi_country")

    # capital / strategic location
    if any(k in title for k in CAPITAL_HINTS) or ev.get("strategic_location"):
        score += W["capital_strategic"]
        reasons.append("capital_strategic")

    # official emergency
    if ev.get("official_emergency") or ev.get("official_declaration"):
        score += W["official_emergency"]
        reasons.append("official_emergency")

    # rapid escalation（timeline 多 update / 近 24h 显著变化）
    if (ev.get("update_count") or 0) >= 2 or ev.get("rapid_escalation"):
        score += W["rapid_escalation"]
        reasons.append("rapid_escalation")

    return min(score, 100), reasons


def evaluate_brief_candidates(events, threshold=None):
    """§十九/§二十：从事件中评估 brief candidates。

    返回 list of dict：{brief_id, trigger_score, trigger_reasons,
    candidate_status, event_id, ...}（≤ 传入数量，全部低于阈值也如实返回）。
    """
    threshold = threshold if threshold is not None else TRIGGER_THRESHOLD
    out = []
    for ev in events:
        ev_type = (ev.get("event_type") or "").lower()
        s, reasons = trigger_score(ev, ev.get("affected_countries"))
        # 低伤亡单源（§二十六 brief #7：不触发）
        if ev.get("single_source_warning") and s < threshold and \
                (ev.get("deaths") or 0) < MASS_CASUALTY_DEATHS:
            status = "below_threshold"
        else:
            status = "brief_candidate" if s >= threshold else "below_threshold"
        out.append({
            "brief_id": "BRF_%s" % (ev.get("event_id") or ev.get("master_event_id") or "x")[-14:],
            "report_type": "major_event_brief",
            "trigger_score": s,
            "trigger_threshold": threshold,
            "trigger_reasons": reasons,
            "candidate_status": status,
            "event_id": ev.get("event_id") or ev.get("master_event_id"),
            "master_event_id": ev.get("master_event_id"),
            "country": ev.get("country"),
            "country_iso3": ev.get("country_iso3"),
            "event_type": ev.get("event_type"),
            "event_time": ev.get("event_time") or ev.get("published_at"),
            "location": ev.get("location"),
            "verification": ev.get("verification_status"),
            "source_count": ev.get("source_count"),
            "conflicting": bool(ev.get("conflicting")),
        })
    out.sort(key=lambda x: -x["trigger_score"])
    return out
