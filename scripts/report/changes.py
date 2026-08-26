#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7A §十-§十一 — Change Detection + Previous Report Comparison。

- change detection 复用 Stage6 timeline（§十）：不重新从原始新闻猜变化，
  直接读取 timeline updates 的 update_type 归纳为日报 change_type。
- previous report comparison（§十一）：report snapshot/history；
  已报告且无实质更新的 master event 不重复进 Executive Summary（进 Watch Items）；
  有新变化 → Key Changes。
- Facts / Analysis 分层（§十二）：facts（对象，带 evidence）与 analysis_inputs
  （中性输入）分离；禁止无依据百分比预测（§十三）。
"""

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# §十 Social change_type 映射（timeline update_type → report change_type）
SOCIAL_CHANGE_MAP = {
    "initial_report": "new_event",
    "casualty_update": "casualty_increase",
    "injury_update": "injury_increase",
    "official_confirmation": "official_confirmation",
    "actor_attribution_update": "actor_attribution_change",
    "location_update": "location_expansion",
    "status_update": "status_change",
    "correction": "correction",
    "closure_update": "closed",
    "context_update": None,
}
CONFLICT_FLAG_TO_CHANGE = {
    "casualty_difference": "conflict_detected",
    "injury_difference": "conflict_detected",
    "attribution_escalation": "actor_attribution_change",
}

# §十 Disease change_type 映射
DISEASE_CHANGE_MAP = {
    "new_outbreak": "new_outbreak",
    "case_update": "case_increase",
    "mortality_update": "mortality_increase",
    "geographic_spread": "geographic_spread",
    "status_change": "status_change",
    "final_update": "final_update",
    "response_update": "status_change",
}


def changes_from_timeline(timeline, since_ts=None):
    """从 timeline updates 归纳 change items（§十）。

    since_ts: 上次日报 cutoff；仅统计该时间之后的 update。
    返回 (change_items, latest_change_type, has_conflict, closed)。
    """
    changes = []
    has_conflict = False
    closed = False
    latest_type = None
    for u in timeline.get("updates", []):
        pt = u.get("published_at") or u.get("effective_at") or u.get("created_at")
        if since_ts and pt and str(pt) < since_ts:
            continue
        ut = u.get("update_type")
        ct = SOCIAL_CHANGE_MAP.get(ut)
        if ct:
            changes.append({
                "event_id": timeline.get("master_event_id") or u.get("master_event_id"),
                "update_id": u.get("update_id"),
                "change_type": ct,
                "published_at": pt,
                "source_id": u.get("source_id"),
                "description": "update_type=%s" % ut,
            })
            latest_type = ct
        if ut == "closure_update":
            closed = True
    for flag in timeline.get("conflict_flags", []):
        ct = CONFLICT_FLAG_TO_CHANGE.get(flag)
        if ct:
            changes.append({"event_id": timeline.get("master_event_id"),
                            "change_type": ct, "flag": flag})
            has_conflict = True
            latest_type = latest_type or ct
    return changes, latest_type, has_conflict, closed


def disease_changes_from_timeline(tl, since_ts=None):
    """从 outbreak timeline observations 归纳 disease change（§十/§十五）。"""
    changes = []
    latest_type = None
    prev_counts = {}
    for obs in tl.get("updates", []):
        rd = obs.get("report_date") or obs.get("as_of_date")
        if since_ts and rd and str(rd) < since_ts:
            prev_counts = {
                k: obs.get(k) for k in
                ("confirmed_cases", "probable_cases", "suspected_cases",
                 "total_cases", "deaths")}
            continue
        ct = DISEASE_CHANGE_MAP.get(obs.get("update_type"))
        if ct:
            changes.append({"outbreak_id": tl.get("outbreak_id"),
                            "disease_id": tl.get("disease_id"),
                            "change_type": ct,
                            "report_date": rd})
            latest_type = ct
    return changes, latest_type, prev_counts


# ── §十一 Previous Report snapshot / history ──

def save_snapshot(report_input, snapshot_dir=None):
    """保存 report snapshot（内部 runtime），返回 snapshot 路径。"""
    d = Path(snapshot_dir) if snapshot_dir else ROOT / "data" / "runtime" / "reports" / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    rid = report_input.get("report_id", "report_%s" % int(time.time()))
    p = d / ("%s.json" % rid)
    p.write_text(json.dumps(report_input, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def load_snapshot(report_id, snapshot_dir=None):
    """读取上一个 report snapshot；不存在返回 None。"""
    d = Path(snapshot_dir) if snapshot_dir else ROOT / "data" / "runtime" / "reports" / "snapshots"
    p = d / ("%s.json" % report_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def prev_report_event_ids(prev_report):
    """从上一日报提取已报告事件 id 集合（§十一 去重抑制基准）。"""
    ids = set()
    if not prev_report:
        return ids
    for sec_name in ("executive_summary", "major_security_developments",
                     "terrorism_armed_violence", "public_health_disease",
                     "political_social_stability", "cross_border_regional"):
        for it in (prev_report.get("sections", {}).get(sec_name) or []):
            eid = it.get("event_id") or it.get("master_event_id") or it.get("disease_id")
            if eid:
                ids.add(str(eid))
    return ids


def split_prev_reported(selected, prev_ids):
    """§十一：已报告无实质更新 → watch；有新变化 → key changes。
    selected 需带 change_type 信息。返回 (key_changes, watch_items)。"""
    key, watch = [], []
    for it in selected:
        eid = it.get("event_id") or it.get("master_event_id")
        if str(eid) in set(prev_ids) and not it.get("change_type"):
            watch.append(it)
        else:
            key.append(it)
    return key, watch
