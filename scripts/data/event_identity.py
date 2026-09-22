#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""event_identity.py — event_cluster_id ↔ master_event_id 的**确定性**身份桥（C5-A §九–§十一）。

历史债务：`event_analysis` 用 event_cluster id，公开 Event Detail 用 master_event_id，
两边没有可解析的桥。本模块只做**有证据的**映射：

  证据（按优先级，全部要求**精确 id 相等**）：
    1. EXACT_ID            —— 该 cluster id 本身就在 master event 集合中
                              （master_events 的 master_event_id 即 cluster id）
    2. PUBLISHED_MAPPING   —— published event 显式携带 master_event_id（若将来补上）
    3. EXISTING_MEMBERSHIP —— master event 记录里显式列出 cluster_id / cluster_ids

禁止：标题相似、日期接近、文本相似度等无证据合并。
1 cluster → 多个 master（或多 cluster → 1 master 但 cluster 未声明）时记 AMBIGUOUS，
**fail-closed**（不静默任选）。
"""
from __future__ import annotations

import io
import json
import os

EXACT_ID = "EXACT_ID"
PUBLISHED_MAPPING = "PUBLISHED_MAPPING"
EXISTING_MEMBERSHIP = "EXISTING_MEMBERSHIP"
AMBIGUOUS = "AMBIGUOUS"
UNRESOLVED = "UNRESOLVED"


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _rows(doc, *keys):
    if isinstance(doc, list):
        return doc
    for k in keys:
        if isinstance((doc or {}).get(k), list):
            return doc[k]
    return []


def load_master_events(root):
    return _rows(load_json(os.path.join(str(root), "data", "views", "master_events.json"),
                           {}) or {}, "items", "events", "masters")


def build_identity_bridge(root):
    """构建 cluster → master 的确定性映射。

    返回 dict：
      mappings           {cluster_id: {"master_event_id":..., "method":..., "evidence":...}}
      ambiguous          [{"cluster_id":..., "candidates":[...]}]
      unresolved         未映射的 cluster id 列表
      master_total / cluster_total / exact / ambiguous_count / unresolved_count
    """
    clusters = _rows(load_json(os.path.join(str(root), "data", "canonical",
                                            "event_clusters.json"), {}) or {},
                     "items", "clusters")
    masters = load_master_events(root)
    cluster_ids = {c.get("event_id") for c in clusters if c.get("event_id")}
    master_ids = {m.get("master_event_id") or m.get("event_id")
                  for m in masters}
    master_ids = {m for m in master_ids if m}

    mappings, ambiguous = {}, []
    for cid in sorted(cluster_ids):
        cands, method, evidence = [], None, None
        if cid in master_ids:                                   # 1 EXACT_ID
            cands, method, evidence = [cid], EXACT_ID, "cluster id ∈ master_event_id 集合"
        if len(cands) > 1:
            ambiguous.append({"cluster_id": cid, "candidates": sorted(cands),
                              "reason": "multiple_master_candidates"})
            continue
        if cands:
            mappings[cid] = {"master_event_id": cands[0], "method": method,
                             "evidence": evidence}
    # 显式 membership / published mapping（有则优先，且冲突即 AMBIGUOUS）
    for m in masters:
        mid = m.get("master_event_id") or m.get("event_id")
        for cid in (m.get("cluster_ids") or ([m.get("cluster_id")] if m.get("cluster_id") else [])):
            if cid not in cluster_ids:
                continue
            cur = mappings.get(cid)
            if cur and cur["master_event_id"] != mid:
                ambiguous.append({"cluster_id": cid,
                                  "candidates": sorted({cur["master_event_id"], mid}),
                                  "reason": "membership_conflicts_with_exact_id"})
                mappings.pop(cid, None)
                continue
            mappings[cid] = {"master_event_id": mid, "method": EXISTING_MEMBERSHIP,
                             "evidence": "master_event.cluster_ids 显式声明"}

    unresolved = sorted(cluster_ids - set(mappings) - {a["cluster_id"] for a in ambiguous})
    by_method = {}
    for v in mappings.values():
        by_method[v["method"]] = by_method.get(v["method"], 0) + 1
    return {"mappings": mappings, "ambiguous": ambiguous, "unresolved": unresolved,
            "cluster_total": len(cluster_ids), "master_total": len(master_ids),
            "exact": by_method.get(EXACT_ID, 0),
            "by_method": by_method,
            "ambiguous_count": len(ambiguous), "unresolved_count": len(unresolved),
            "master_ids_subset_of_clusters": bool(master_ids) and master_ids <= cluster_ids}


def resolve_master_event(bridge, event_id):
    """公开 Event / analysis 只能挂到**已确定映射**的 master_event_id。

    UNRESOLVED / AMBIGUOUS 一律返回 None —— 不得伪装成已集成。
    """
    m = (bridge.get("mappings") or {}).get(event_id)
    return m["master_event_id"] if m else None


def enrich_published_events(root, bridge=None, write=False):
    """给公开事件补 `master_event_id`（仅当映射确定）。

    返回 (rows, stats)。write=True 时写回 data/public/published_events.json。
    """
    bridge = bridge or build_identity_bridge(root)
    path = os.path.join(str(root), "data", "public", "published_events.json")
    doc = load_json(path, {}) or {}
    rows = _rows(doc, "items") if isinstance(doc, dict) else list(doc)
    stats = {"PUBLISHED_EVENTS_TOTAL": len(rows), "BRIDGED": 0, "UNRESOLVED": 0,
             "ALREADY_BRIDGED": 0}
    for r in rows:
        eid = r.get("event_id")
        mid = resolve_master_event(bridge, eid)
        if r.get("master_event_id"):
            stats["ALREADY_BRIDGED"] += 1
            continue
        if mid:
            r["master_event_id"] = mid
            r["master_event_bridge_method"] = bridge["mappings"][eid]["method"]
            stats["BRIDGED"] += 1
        else:
            stats["UNRESOLVED"] += 1
    if write and isinstance(doc, dict) and isinstance(doc.get("items"), list):
        doc["items"] = rows
        with io.open(path, "w", encoding="utf-8", newline="") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
    return rows, stats
