#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7A §十六-§十八 — Priority Country Weekly Report 引擎。

- 配置驱动：priority_report_country（TCD/NER/SSD 试点启用，BEN/ETH 关闭）。
- Weekly 不是 7 份日报拼接（§十七）：基于 master events + timeline changes +
  确定性 trend metrics 聚合。
- Trend Metrics（§十八）：确定性计数，fatalities_known unknown 保持 null 不写 0；
  与上周比较 up/down/stable（无上周数据 → null）；不用 AI 生成数字。
"""

from scripts.report.config import PRIORITY_REPORT_COUNTRIES

# §十八 确定性指标字段
METRIC_FIELDS = (
    "event_count", "verified_event_count", "armed_attack_count",
    "civil_unrest_count", "major_crime_count", "natural_disaster_count",
    "fatalities_known", "injuries_known", "multi_source_event_count",
    "new_outbreak_count", "active_outbreak_count",
)

_TYPE_GROUP = {
    "terrorist_attack": "armed_attack", "armed_attack": "armed_attack",
    "armed_conflict": "armed_attack", "military_operation": "armed_attack",
    "civil_unrest": "civil_unrest", "mass_protest": "civil_unrest",
    "strike": "civil_unrest", "coup": "civil_unrest",
    "coup_attempt": "civil_unrest",
    "major_crime": "major_crime", "kidnapping": "major_crime",
    "natural_disaster": "natural_disaster",
}


def _num(v):
    if v is None or v == "":
        return None
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None


def weekly_metrics(events, disease_events, week_start, week_end,
                   prev_metrics=None):
    """§十八 确定性周度指标。events: 本周该国的 social events（含 verification）；
    disease_events: 本周该国的 disease timeline 条目。返回 metrics dict。"""
    m = {f: 0 for f in METRIC_FIELDS}
    m["fatalities_known"] = None
    m["injuries_known"] = None
    total_f = 0
    total_i = 0
    known_f = False
    known_i = False
    seen = set()

    for ev in events:
        eid = ev.get("event_id") or ev.get("master_event_id")
        if eid and eid in seen:
            continue  # §十七 duplicate/master 不重复计
        seen.add(eid)
        m["event_count"] += 1
        vs = (ev.get("verification_status") or "").lower()
        if vs == "verified" or (vs == "probable" and (ev.get("source_count") or 0) >= 2):
            m["verified_event_count"] += 1
        g = _TYPE_GROUP.get((ev.get("event_type") or "").lower())
        if g in ("armed_attack", "civil_unrest", "major_crime", "natural_disaster"):
            m[g + "_count"] += 1
        sc = ev.get("source_count") or (1 if (ev.get("source_name") or ev.get("source_id")) else 0)
        if sc >= 2:
            m["multi_source_event_count"] += 1
        d = _num(ev.get("deaths") or ev.get("casualties"))
        if d is not None:
            total_f += d
            known_f = True
        inj = _num(ev.get("injured"))
        if inj is not None:
            total_i += inj
            known_i = True

    if known_f:
        m["fatalities_known"] = total_f
    if known_i:
        m["injuries_known"] = total_i

    seen_d = set()
    for de in disease_events:
        did = de.get("outbreak_id") or de.get("disease_event_id") or de.get("disease_id")
        if did and did in seen_d:
            continue
        seen_d.add(did)
        # 周内 new outbreak：首条 observation 的 report_date 在本周
        first = (de.get("updates") or [{}])[0]
        frd = first.get("report_date") or de.get("report_date")
        if frd and week_start <= str(frd)[:10] <= week_end:
            m["new_outbreak_count"] += 1
        if de.get("outbreak_status") in ("active", "declining", "monitoring", "contained"):
            m["active_outbreak_count"] += 1

    # §十八 与上周比较（确定性 up/down/stable；无上周数据 → null）
    comp = {}
    if prev_metrics:
        for f in METRIC_FIELDS:
            if f in ("fatalities_known", "injuries_known"):
                continue
            cur = m[f]
            pre = prev_metrics.get(f, 0)
            if cur > pre:
                comp[f] = "up"
            elif cur < pre:
                comp[f] = "down"
            else:
                comp[f] = "stable"
    else:
        comp = {f: None for f in METRIC_FIELDS if f not in ("fatalities_known", "injuries_known")}
    m["comparison"] = comp
    return m


def enabled_weekly_countries():
    """§十六 配置驱动的启用国列表。"""
    return sorted([c for c, on in PRIORITY_REPORT_COUNTRIES.items() if on])
