#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""provenance_recovery.py — canonical provenance / localization 的**确定性**恢复（C5-A §三–§八、§二十一–§二十三）。

只允许**确定性证据**恢复，证据优先级（§四）：
  1 EXACT_ID              —— cluster 已显式声明 article_ids / source_groups（无需恢复）
  2 EXISTING_MEMBERSHIP   —— Article Store 的 `linked_event_id` 指向该 cluster（稳定 id 相等）
  3 EXISTING_PROVENANCE   —— cluster.legacy_payload 中携带的 article/source 线索（精确 id）
  4 UNRESOLVED            —— 无任何确定性证据 → **保持原样**，不猜、不伪造

禁止：文本相似度猜来源、按域名伪造 source_id、按标题人工配对、生成 synthetic identity。
每个 cluster 都会得到一行审计记录（§五）：
  cluster_id / previous_* / recovered_* / recovery_method / recovery_evidence / confidence_class

本地化复用（§二十一–§二十三）：仅当 cluster 通过**稳定 id**对应到已本地化的 article 时，
复用其 title_cn / summary_cn，并记录 localization_source_id / localization_projection_method；
多个候选且文本冲突 → LOCALIZATION_CONFLICT（fail-closed，不任选）。
"""
from __future__ import annotations

import io
import json
import os
from collections import defaultdict

EXACT_ID = "EXACT_ID"
EXISTING_MEMBERSHIP = "EXISTING_MEMBERSHIP"
EXISTING_PROVENANCE = "EXISTING_PROVENANCE"
UNRESOLVED = "UNRESOLVED"
LOCALIZATION_CONFLICT = "LOCALIZATION_CONFLICT"


def _load(path, default=None):
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


def _cluster_doc(root):
    return _rows(_load(os.path.join(str(root), "data", "canonical", "event_clusters.json"), {}) or {},
                 "items", "clusters")


def _article_doc(root):
    return _rows(_load(os.path.join(str(root), "data", "canonical", "articles.json"), {}) or {},
                 "items", "articles")


def _registry_ids(root):
    doc = _load(os.path.join(str(root), "data", "sources.json"), {}) or {}
    rows = _rows(doc, "sources", "items")
    return {r.get("source_id") for r in rows if r.get("source_id")}


def build_article_index(root):
    """Article Store 的确定性索引：linked_event_id → [article]，以及 id → article。"""
    arts = _article_doc(root)
    by_event, by_id = defaultdict(list), {}
    for a in arts:
        aid = a.get("article_id")
        if aid:
            by_id[aid] = a
        ev = a.get("linked_event_id")
        if ev:
            by_event[ev].append(a)
    return by_id, by_event


def recover_provenance(root):
    """恢复 canonical provenance + localization，返回 (clusters_after, audit_rows, stats)。"""
    clusters = [dict(c) for c in _cluster_doc(root)]
    by_id, by_event = build_article_index(root)
    reg = _registry_ids(root)
    rows, stats = [], defaultdict(int)
    sums = defaultdict(int)

    for c in clusters:
        cid = c.get("event_id")
        prev_arts = list(c.get("article_ids") or [])
        prev_groups = list(c.get("source_groups") or [])
        prev_src = c.get("source_id")
        rec = {"cluster_id": cid, "previous_article_ids": prev_arts,
               "recovered_article_ids": [], "previous_source_groups": prev_groups,
               "recovered_source_groups": [], "recovery_method": UNRESOLVED,
               "recovery_evidence": None, "confidence_class": UNRESOLVED,
               "previous_title_cn": bool((c.get("title_cn") or "").strip()),
               "localization_status": "NONE", "localization_source_id": None,
               "localization_projection_method": None}

        # ── 1. 已有显式声明 → 无需恢复 ────────────────────────────────
        if prev_arts or prev_groups or prev_src:
            rec["recovery_method"] = EXACT_ID
            rec["confidence_class"] = EXACT_ID
            rec["recovery_evidence"] = "cluster 已显式声明 article_ids/source_groups/source_id"
            stats["ALREADY_PRESENT"] += 1
        else:
            # ── 2. Article Store 的稳定反向关联 ──────────────────────
            linked = by_event.get(cid) or []
            ids = sorted({a["article_id"] for a in linked if a.get("article_id")})
            groups = sorted({g for a in linked for g in [a.get("source_group") or a.get("source_id")]
                             if g and g in reg})
            if ids or groups:
                rec["recovery_method"] = EXISTING_MEMBERSHIP
                rec["confidence_class"] = EXISTING_MEMBERSHIP
                rec["recovery_evidence"] = "article.linked_event_id == cluster.event_id"
                rec["recovered_article_ids"] = [i for i in ids if i not in prev_arts]
                rec["recovered_source_groups"] = [g for g in groups if g not in prev_groups]
                if rec["recovered_article_ids"]:
                    c["article_ids"] = prev_arts + rec["recovered_article_ids"]
                if rec["recovered_source_groups"]:
                    c["source_groups"] = prev_groups + rec["recovered_source_groups"]
                stats["RECOVERABLE"] += 1
                if rec["recovered_article_ids"] or rec["recovered_source_groups"]:
                    stats["RECOVERED"] += 1
            else:
                # ── 3. legacy_payload 精确线索 ────────────────────────
                lp = c.get("legacy_payload") if isinstance(c.get("legacy_payload"), dict) else {}
                l_ids = [i for i in (lp.get("article_ids") or []) if i in by_id]
                if l_ids:
                    rec["recovery_method"] = EXISTING_PROVENANCE
                    rec["confidence_class"] = EXISTING_PROVENANCE
                    rec["recovery_evidence"] = "legacy_payload.article_ids ∩ Article Store"
                    rec["recovered_article_ids"] = l_ids
                    c["article_ids"] = prev_arts + l_ids
                    stats["RECOVERABLE"] += 1
                    stats["RECOVERED"] += 1
                else:
                    stats["UNRESOLVED_NO_EVIDENCE"] += 1

        # ── §二十一 本地化确定性复用（仅稳定 id 关联）────────────────
        if not (c.get("title_cn") or "").strip():
            linked = by_event.get(cid) or []
            cands = {}
            for a in linked:
                t = (a.get("title_cn") or "").strip()
                if t:
                    cands.setdefault(t, []).append(a)
            if len(cands) == 1:
                title, arts_ = next(iter(cands.items()))
                c["title_cn"] = title
                s = (arts_[0].get("summary_cn") or "").strip()
                if s and not (c.get("summary_cn") or "").strip():
                    c["summary_cn"] = s
                rec["localization_status"] = "RECOVERED"
                rec["localization_source_id"] = arts_[0].get("article_id")
                rec["localization_projection_method"] = EXISTING_MEMBERSHIP
                stats["LOCALIZATION_RECOVERED"] += 1
            elif len(cands) > 1:
                rec["localization_status"] = LOCALIZATION_CONFLICT
                rec["localization_evidence"] = sorted(cands)[:5]
                stats["LOCALIZATION_CONFLICTS"] += 1
            elif linked:
                sums["LOC_NO_EVIDENCE"] += 1      # 有关联文章，但都没有已本地化文本
            else:
                sums["LOC_NO_LINK"] += 1          # 没有任何稳定 article 关联
        rows.append(rec)

    total = len(clusters)
    with_any = sum(1 for c in clusters
                   if (c.get("article_ids") or c.get("source_groups")
                       or c.get("source_id") or c.get("source_name")))
    with_groups = sum(1 for c in clusters if [g for g in (c.get("source_groups") or []) if g])
    out = {
        "CANONICAL_CLUSTERS_TOTAL": total,
        "CANONICAL_WITH_SOURCE_GROUPS": with_groups,
        "CANONICAL_WITH_ANY_SOURCE_IDENTITY": with_any,
        "CANONICAL_SOURCE_IDENTITY_COVERAGE": round(with_any / total * 100, 1) if total else 0.0,
        "CANONICAL_WITH_ARTICLE_IDS": sum(1 for c in clusters if c.get("article_ids")),
        "CANONICAL_WITH_TITLE_CN": sum(1 for c in clusters if (c.get("title_cn") or "").strip()),
        "CANONICAL_WITH_SUMMARY_CN": sum(1 for c in clusters if (c.get("summary_cn") or "").strip()),
        "RECOVERABLE_PROVENANCE_CASES": stats["RECOVERABLE"],
        "PROVENANCE_RECOVERED": stats["RECOVERED"],
        "RECOVERABLE_BUT_FAILED": max(0, stats["RECOVERABLE"] - stats["RECOVERED"]),
        "UNRESOLVED_NO_EVIDENCE": stats["UNRESOLVED_NO_EVIDENCE"],
        "ALREADY_PRESENT": stats["ALREADY_PRESENT"],
        "LOCALIZATION_RECOVERED_FROM_EXISTING": stats["LOCALIZATION_RECOVERED"],
        "LOCALIZATION_CONFLICTS": stats["LOCALIZATION_CONFLICTS"],
        "CANONICAL_STILL_WITHOUT_TITLE_CN": sum(
            1 for c in clusters if not (c.get("title_cn") or "").strip()),
        # 残余缺口的**分类解释**（§八：必须能说明为什么没恢复）
        "ARTICLE_IDS_UNRESOLVED_NO_EVIDENCE": sum(
            1 for c in clusters if not (c.get("article_ids") or [])),
        "LOCALIZATION_UNRESOLVED_NO_EVIDENCE": sums["LOC_NO_EVIDENCE"],
        "LOCALIZATION_BLOCKED_NO_ARTICLE_LINK": sums["LOC_NO_LINK"],
    }
    return clusters, rows, out


def verify_recovery(root, clusters=None, audit_rows=None):
    """§七 完整性：不得有 dangling article ref / 伪造 source id。"""
    by_id, _ = build_article_index(root)
    reg = _registry_ids(root)
    clusters = clusters if clusters is not None else _cluster_doc(root)
    dangling, fake = [], []
    KNOWN_FAKE = ("source_unknown", "synthetic", "unknown_source", "disease_source_0")
    for c in clusters:
        for aid in (c.get("article_ids") or []):
            if aid not in by_id:
                dangling.append({"cluster_id": c.get("event_id"), "article_id": aid})
        for sid in ([c.get("source_id")] if c.get("source_id") else []) + \
                   [g for g in (c.get("source_groups") or []) if g]:
            if str(sid).lower() in KNOWN_FAKE or str(sid).lower().startswith("synthetic"):
                fake.append({"cluster_id": c.get("event_id"), "source_id": sid})
    return {"DANGLING_ARTICLE_REFS": len(dangling), "dangling_sample": dangling[:5],
            "FAKE_SOURCE_IDS": len(fake), "fake_sample": fake[:5],
            "SOURCE_REGISTRY_TOTAL": len(reg)}


def write_views(root, clusters, audit_rows, stats, bridge=None):
    """写出恢复审计表与身份桥视图（确定性、无 AI）。"""
    vd = os.path.join(str(root), "data", "views")
    os.makedirs(vd, exist_ok=True)
    payload = {"generated_by": "scripts/data/provenance_recovery.py", "stats": stats,
               "audit_rows": audit_rows}
    with io.open(os.path.join(vd, "canonical_provenance_audit.json"), "w",
                 encoding="utf-8", newline="") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    if bridge is not None:
        with io.open(os.path.join(vd, "event_identity_bridge.json"), "w",
                     encoding="utf-8", newline="") as f:
            json.dump({"generated_by": "scripts/data/event_identity.py",
                       "EVENT_CLUSTER_TOTAL": bridge["cluster_total"],
                       "MASTER_EVENT_TOTAL": bridge["master_total"],
                       "EXACT_IDENTITY_MAPPINGS": bridge["exact"],
                       "AMBIGUOUS_MAPPINGS": bridge["ambiguous_count"],
                       "UNRESOLVED_MAPPINGS": bridge["unresolved_count"],
                       "mappings": bridge["mappings"], "ambiguous": bridge["ambiguous"]},
                      f, ensure_ascii=False, indent=1)
    return payload


def apply(root, write=False):
    """执行恢复（可选写回 canonical）+ 生成审计视图。返回 stats。"""
    clusters, rows, stats = recover_provenance(root)
    stats.update(verify_recovery(root, clusters))
    bridge = None
    try:
        from scripts.data import event_identity as EI
        bridge = EI.build_identity_bridge(root)
    except Exception:  # noqa: BLE001
        pass
    write_views(root, clusters, rows, stats, bridge)
    if write:
        path = os.path.join(str(root), "data", "canonical", "event_clusters.json")
        doc = _load(path, {}) or {}
        if isinstance(doc, dict) and isinstance(doc.get("items"), list):
            doc["items"] = clusters
            with io.open(path, "w", encoding="utf-8", newline="") as f:
                json.dump(doc, f, ensure_ascii=False, indent=1)
    return stats
