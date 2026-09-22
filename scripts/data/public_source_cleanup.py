#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""public_source_cleanup.py — C6-R2.6 §C 裁决实现
KEEP_QUARANTINE_REMOVE_PUBLIC_REFERENCE。

规则：
  * quarantine 保持 production authoritative（不删除任何 quarantine 记录）
  * 对 PUBLIC_SOURCE_URL ∩ QUARANTINE_URL（reason ∈ {wrong_country, not_security_relevant}）：
      从 public event 的 source_refs / canonical_url 中**移除该 source**
  * 若 event 仍有其他有效 source → 保留 event
    否则 → 标记 source_insufficient = true（不删除 event）
  * 幂等、可审计：每次执行写出 C6_R2_6_PUBLIC_SOURCE_CLEANUP.json 统计
"""
from __future__ import annotations

import hashlib
import io
import json
import os

BLOCKING_REASONS = ("wrong_country", "not_security_relevant")
AUDIT_NAME = "C6_R2_6_PUBLIC_SOURCE_CLEANUP.json"


def _norm(u):
    return str(u or "").strip().rstrip("/").lower()


def _load(p):
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def _save(p, doc):
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)


def apply(root, audit_dir=None):
    """执行清理并返回审计统计（幂等）。"""
    root = str(root)
    qdoc = _load(os.path.join(root, "data", "canonical", "quarantine.json")) or {}
    qrows = qdoc.get("items") or []
    qmap = {}
    for q in qrows:
        u = _norm(q.get("original_id"))
        if u:
            qmap[u] = q.get("reason_code")

    pub_path = os.path.join(root, "data", "public", "published_events.json")
    pub = _load(pub_path) or {}
    items = pub.get("items")
    if items is None:
        return {"skipped": True, "reason": "published_events 无 items"}

    removed_urls, affected_events, affected_articles, excluded_events = [], [], [], []
    art_path = os.path.join(root, "data", "canonical", "articles.json")
    art_doc = _load(art_path) or {}
    arts = art_doc.get("items") or []
    by_link = {}
    for a in arts:
        if a.get("linked_event_id"):
            by_link.setdefault(a["linked_event_id"], []).append(a)

    for e in items:
        # 幂等修复：早期版本曾把 canonical_url 置 None（违反 published_event schema）
        if not e.get("canonical_url") and e.get("canonical_url_removed"):
            e["canonical_url"] = e.pop("canonical_url_removed")
        # 幂等归一：public 视图不得残留 schema 外字段（历史版本写入的标记）
        for _k in ("canonical_url_quarantined", "canonical_url_quarantine_reason",
                   "source_insufficient"):
            e.pop(_k, None)
        cand = []
        cu = _norm(e.get("canonical_url"))
        if cu:
            cand.append(cu)
        for l in (e.get("source_links") or []):
            if isinstance(l, dict) and l.get("url"):
                cand.append(_norm(l["url"]))
        hit = {u for u in cand if qmap.get(u) in BLOCKING_REASONS}
        if not hit:
            continue
        before_n = len(e.get("source_links") or [])
        e["source_links"] = [l for l in (e.get("source_links") or [])
                             if _norm((l or {}).get("url")) not in hit]
        after_n = len(e["source_links"])
        # canonical_url 保留为记录身份（published_event schema 要求 string）；
        # 隔离事实只记录在审计文件（public 视图不得出现 schema 外字段）
        for _k in ("canonical_url_quarantined", "canonical_url_quarantine_reason",
                   "source_insufficient"):
            e.pop(_k, None)
        remaining = [l.get("url") for l in e["source_links"] if l.get("url")]
        if not remaining:
            excluded_events.append({"event_id": e.get("event_id"),
                                    "reason": "NO_VALID_SOURCE_AFTER_QUARANTINE_CLEANUP",
                                    "removed": sorted(hit)})
        removed_urls.extend(sorted(hit))
        affected_events.append({
            "event_id": e.get("event_id"),
            "removed": sorted(hit),
            "reason_code": sorted({qmap[u] for u in hit}),
            "source_links_before": before_n, "source_links_after": after_n,
            "remaining_valid_sources": remaining,
            "source_insufficient": not remaining,
        })
        for a in by_link.get(e.get("event_id"), []):
            if _norm(a.get("canonical_url") or a.get("article_url")) in hit:
                a["source_quarantined"] = True          # 非破坏性标记；不改 identity
                affected_articles.append({
                    "article_id": a.get("article_id"),
                    "reason_code": sorted({qmap[u] for u in hit}),
                    "action": "MARKED_source_quarantined（URL 保留为 identity，不做删除）",
                })

    # 裁决：**保留 event**（不删除、不移出公开列表）；无有效来源者记入审计
    # excluded_events → 「排除」在此仅表示“无有效来源”，供审计与页面标注使用。
    _save(pub_path, pub)
    # 计数一致性：由 compatibility_export 在清理后**以 file 为准**计算 metrics
    # （此处不再自行扣减，避免重复计数偏差）
    if affected_articles:
        _save(art_path, art_doc)

    stats = {
        "audit_id": "C6_R2_6_PUBLIC_SOURCE_CLEANUP",
        "rule": "KEEP_QUARANTINE_REMOVE_PUBLIC_REFERENCE",
        "blocking_reasons": list(BLOCKING_REASONS),
        "removed_urls": sorted(set(removed_urls)),
        "removed_url_count": len(set(removed_urls)),
        "affected_events": affected_events,
        "affected_event_count": len(affected_events),
        "affected_articles": affected_articles,
        "affected_article_count": len(affected_articles),
        "excluded_events": excluded_events,
        "excluded_event_count": len(excluded_events),
        "quarantine_count": len(qrows),
        "article_count": len(arts),
        "quarantine_records_deleted": 0,
        "hash_after": hashlib.sha256(
            io.open(pub_path, "rb").read()).hexdigest()[:32],
    }
    if audit_dir:
        os.makedirs(audit_dir, exist_ok=True)
        _save(os.path.join(audit_dir, AUDIT_NAME), stats)
    return stats


if __name__ == "__main__":
    import sys
    r = apply(sys.argv[1] if len(sys.argv) > 1 else ".",
              audit_dir=sys.argv[2] if len(sys.argv) > 2 else None)
    print(json.dumps({k: v for k, v in r.items()
                      if k not in ("affected_events", "affected_articles")},
                     ensure_ascii=False, indent=1))
