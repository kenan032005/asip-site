#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reaudit_stage3.py — 用修复后的国家识别/相关性逻辑重新审计已采集的 Stage 3A 事件。

将 published_events.json 中 publication_reason='Stage 3A 真实采集' 的事件逐条
重新验证：事件发生国必须与标注国一致，且必须是强安全相关。不满足者移入隔离区。
"""
import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "collectors"))
from country_runner import identify_country, load_country_cfg, relevance_stage1

PUB = os.path.join(ROOT, "data", "public", "published_events.json")
Q = os.path.join(ROOT, "data", "canonical", "quarantine.json")

CHAD_CFG = load_country_cfg("chad")
NIGER_CFG = load_country_cfg("niger")


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def main():
    pub = load_json(PUB, {"items": []})
    items = pub.get("items", [])
    stage3 = [i for i in items if i.get("publication_reason") == "Stage 3A 真实采集"]
    other = [i for i in items if i.get("publication_reason") != "Stage 3A 真实采集"]

    print(f"重新审计 Stage 3A 事件: {len(stage3)} 条")
    print("=" * 70)

    keep = []
    removed = []
    for e in stage3:
        title = e.get("title_original", "")
        summary = e.get("summary_original", "") or e.get("summary_cn", "")
        blob = title + " " + summary
        country_cn = e.get("country_cn", "")
        cfg = CHAD_CFG if country_cn == "乍得" else NIGER_CFG
        cid = identify_country(blob, cfg)
        rel, score, m, ex = relevance_stage1(blob)
        decision = cid.get("decision", "")
        expected = "乍得" if decision == "chad" else ("尼日尔" if decision == "niger" else None)

        if expected == country_cn and rel is True:
            # 国家一致 + 强相关 → 保留
            keep.append(e)
            print(f"  [KEEP] {country_cn} | {title[:60]}")
        else:
            reason = "country_scope_mismatch" if expected != country_cn else (
                "weak_signal_needs_review" if rel is not True else "other")
            removed.append((e, reason))
            print(f"  [MOVE] {country_cn}→{decision} rel={rel} [{reason}] | {title[:55]}")

    print("=" * 70)
    print(f"保留: {len(keep)}  移出: {len(removed)}")

    # 重建 published_events
    new_items = other + keep
    pub["items"] = new_items
    save_json(PUB, pub)
    print(f"published_events: {len(items)} → {len(new_items)}")

    # 追加隔离
    if removed:
        q = load_json(Q, {"items": []})
        existing = {i.get("candidate_id") or i.get("original_event_id") for i in q.get("items", [])}
        added = 0
        for e, reason in removed:
            eid = e.get("event_id", "")
            if eid in existing:
                continue
            q["items"].append({
                "candidate_id": eid,
                "original_event_id": eid,
                "title": e.get("title_cn") or e.get("title_original", ""),
                "url": (e.get("source_links") or [{}])[0].get("url", ""),
                "source": (e.get("source_links") or [{}])[0].get("source_name", ""),
                "country": e.get("country_cn", ""),
                "reason": reason,
                "reason_detail": "Stage 3A 重新审计移出",
                "collected_at": e.get("collected_at_beijing", ""),
                "original_payload": e,
            })
            existing.add(eid)
            added += 1
        save_json(Q, q)
        print(f"隔离区: +{added}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
