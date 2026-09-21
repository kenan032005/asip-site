#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""country_fact_pack.py — Country Fact Pack 确定性做厚（C5-A §十八–§二十）。

历史状态：`country_snapshots.snapshots[]` 只有计数（events_24h/events_7d/active_outbreaks）→
12~22 个国家 pack 全部判为 THIN。

本模块**不用 AI**，只把 canonical 里已有的结构化信息投影进 pack：
  recent_events[] / timeline[] / risk_changes[] / top_locations[] / source_refs[] /
  verification_distribution / latest_verified_event_time / data_as_of / coverage_status

§二十：继续复用 C4 的 `fact_content.country_scope_ok`，**不得跨国污染**。
数据少不是 THIN —— 结构完整即可；只有确实没有内容时 coverage_status = LOW_DATA。
"""
from __future__ import annotations

import os
import sys
from collections import Counter

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from scripts.report import fact_content as FC  # noqa: E402

COVERAGE_OK = "OK"
COVERAGE_LOW = "LOW_DATA"

#: §十九 结构目标（每国 pack 必须能表达这些字段）
PACK_STRUCTURE_FIELDS = ("recent_events", "timeline", "risk_changes", "top_locations",
                         "source_refs", "verification_distribution",
                         "latest_verified_event_time", "data_as_of", "coverage_status")
#: 低于此事实数视为 LOW_DATA（结构仍完整）
PACK_LOW_DATA_MIN_EVENTS = 1


def _iso2to3(root):
    """复用既有 ISO2→ISO3 映射（report factory 的单一真值），不要自建一份。"""
    from scripts.report import materialize as M
    try:
        return dict(M.iso2to3_map(root) or {})
    except Exception:  # noqa: BLE001
        return {}


def load_clusters(root):
    """读取 canonical clusters，并把 country_code(ISO2) 规范成 country_iso3(ISO3)。

    **必须规范化**：canonical 用 ISO2（如 TCD 记录里是 `country_code: "TD"`），
    而 country scope 契约按 ISO3 比较 —— 不规范化会让每国 pack 都静默变成 0 条
    （假通过）。
    """
    import io
    import json
    p = os.path.join(str(root), "data", "canonical", "event_clusters.json")
    if not os.path.exists(p):
        return []
    doc = json.load(io.open(p, encoding="utf-8"))
    rows = doc.get("items") or doc.get("clusters") or (doc if isinstance(doc, list) else [])
    iso = _iso2to3(root)
    out = []
    for c in rows:
        c = dict(c)
        cc = str(c.get("country_code") or "").upper()
        if not c.get("country_iso3") and cc:
            c["country_iso3"] = iso.get(cc, cc if len(cc) == 3 else None)
        out.append(c)
    return out


def _sources(ev):
    return [g for g in (ev.get("source_groups") or []) if g] or \
           ([ev["source_id"]] if ev.get("source_id") else [])


def build_country_pack(iso3, clusters, snapshot=None, data_as_of=None):
    """构造（或加厚）某国的 fact pack。所有字段来自 canonical，确定性、无 AI。"""
    snapshot = dict(snapshot or {})
    scope = {"report_type": "country_weekly", "country_iso3": iso3}
    mine = [c for c in clusters if FC.country_scope_ok(c, scope)]
    # 事件时间倒序（字符串 ISO 可比）
    mine.sort(key=lambda c: str(c.get("event_time") or c.get("first_seen_at") or ""), reverse=True)

    def _event(c):
        return {
            "event_id": c.get("event_id"),
            "title": c.get("title_cn") or c.get("title_original"),
            "event_type": c.get("event_type"),
            "event_time": c.get("event_time"),
            "location": c.get("location_name") or c.get("location_admin1"),
            "verification_status": c.get("verification_level") or c.get("verification_status"),
            "independent_source_count": c.get("independent_source_count"),
            "sources": _sources(c),
            "source_refs": _sources(c),
        }

    recent = [_event(c) for c in mine[:10]]
    verified = [c for c in mine
                if str(c.get("verification_level") or c.get("verification_status") or "")
                .lower() in ("verified", "official", "multiple_source", "high")]
    locations = Counter(str(c.get("location_name") or c.get("location_admin1"))
                        for c in mine
                        if (c.get("location_name") or c.get("location_admin1")))
    refs = sorted({s for c in mine for s in _sources(c)})
    vdist = Counter(str(c.get("verification_level") or c.get("verification_status") or "unknown")
                    for c in mine)
    types = Counter(str(c.get("event_type") or "unknown") for c in mine)

    pack = dict(snapshot)
    pack.update({
        "iso3": iso3,
        "recent_events": recent,
        "timeline": [{"event_id": c.get("event_id"), "event_time": c.get("event_time"),
                      "event_type": c.get("event_type"),
                      "change_type": c.get("verification_notes") and None or None}
                     for c in mine[:20]],
        "risk_changes": [{"event_id": c.get("event_id"),
                          "risk_level": c.get("country_risk_level"),
                          "risk_label": c.get("country_risk_label"),
                          "event_time": c.get("event_time")}
                         for c in mine[:10] if c.get("country_risk_level") is not None],
        "top_locations": [{"location": k, "events": v} for k, v in locations.most_common(5)],
        "source_refs": refs,
        "verification_distribution": dict(vdist),
        "event_type_distribution": dict(types),
        "latest_verified_event_time": (verified[0].get("event_time") if verified else None),
        "latest_event_time": (mine[0].get("event_time") if mine else None),
        "data_as_of": data_as_of or snapshot.get("data_as_of"),
        "coverage_status": COVERAGE_OK if len(mine) >= PACK_LOW_DATA_MIN_EVENTS else COVERAGE_LOW,
        "pack_structure_version": "c5a-v1",
    })
    return pack


def structurally_thin(pack):
    """§十九 判定：**结构**缺失才算 THIN（数据少不算）。"""
    return [f for f in PACK_STRUCTURE_FIELDS if f not in pack]


def enrich_snapshots(root, snapshots, data_as_of=None):
    """把国家快照批量加厚；返回 (snapshots, stats)。"""
    clusters = load_clusters(root)
    out, thin_before, thin_after, cross = [], 0, 0, 0
    before_fields = ("recent_events", "timeline", "risk_changes", "top_locations")
    for s in snapshots:
        if not any(isinstance(s.get(k), list) and s.get(k) for k in before_fields):
            thin_before += 1
        iso = s.get("iso3")
        pack = build_country_pack(iso, clusters, s, data_as_of)
        missing = structurally_thin(pack)
        if missing:
            thin_after += 1
        scope = {"report_type": "country_weekly", "country_iso3": iso}
        cross += sum(1 for e in pack["recent_events"]
                     if e.get("event_id") and not FC.country_scope_ok(
                         next((c for c in clusters if c.get("event_id") == e["event_id"]), {}),
                         scope))
        out.append(pack)
    return out, {"COUNTRY_FACT_PACKS_TOTAL": len(out),
                 "COUNTRY_FACT_PACKS_THIN_BEFORE": thin_before,
                 "COUNTRY_FACT_PACKS_STRUCTURALLY_THIN": thin_after,
                 "CROSS_COUNTRY_FACTS_IN_COUNTRY_PACKS": cross,
                 "PACK_STRUCTURE_FIELDS": list(PACK_STRUCTURE_FIELDS)}
