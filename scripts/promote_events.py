#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
promote_events.py —— 多源聚类与正式事件提升（第三阶段）。

输入：data/pending_events.json（相关+国家明确+待核实/待复核）。
可选：data/review_decisions.json（Hy3 语义复核结论，candidate_id -> 决策）。

规则：
  - 聚类签名 = 国家 + 事件类型 + 地点 + 日期；
  - B类：聚类含 ≥2 个独立来源 → 正式事件(cross_verified)；
  - A类：聚类含官方/国家媒体单一来源 → 正式事件(official_unverified)；
  - C类：单一普通媒体 → 仅留在 pending，不进 events.json；
  - 仍需语义复核(needs_review 且 review 未通过) → 不进 events；
  - 单篇 Reuters 多转载 / 新华社中英文稿 → 计为 1 个独立来源（通过 source_group 去重）。

仅当 --apply 时写回 events.json；否则预览。
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
DATA = os.path.join(ROOT, "data")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def date_key(s):
    if not s:
        return ""
    return s[:10]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="写回 events.json")
    args = ap.parse_args()

    pending = json.load(open(os.path.join(DATA, "pending_events.json"), encoding="utf-8")).get("items", [])
    events_doc = json.load(open(os.path.join(DATA, "events.json"), encoding="utf-8"))

    # 语义复核结论
    rpath = os.path.join(DATA, "review_decisions.json")
    reviews = {}
    if os.path.exists(rpath):
        reviews = {d["candidate_id"]: d for d in json.load(open(rpath, encoding="utf-8"))}

    # 仅考虑可进聚类池的候选
    pool = []
    for p in pending:
        if p.get("lead_only"):
            continue
        if p.get("country_decision") not in ("chad", "niger"):
            continue
        cid = p.get("candidate_id")
        rv = reviews.get(cid)
        if rv:
            if not rv.get("is_security_relevant") or (rv.get("relevance_score") or 0) < 0.70 \
               or not rv.get("event_country") or rv.get("event_type") == "unknown":
                p["_review_failed"] = True
                continue
            # 复核通过：采纳复核结论
            p["_review_passed"] = True
            p["event_type"] = rv.get("event_type") or p.get("event_type")
            p["country_decision"] = "niger" if rv.get("event_country") == "尼日尔" else ("chad" if rv.get("event_country") == "乍得" else p.get("country_decision"))
        else:
            if p.get("needs_review"):
                p["_review_failed"] = True  # 待复核但未提供结论 → 不进 events
                continue
            if p.get("relevant") is not True:
                continue
        pool.append(p)

    # 聚类
    clusters = {}
    for p in pool:
        loc = (p.get("matched_location_entities") or [""])[0]
        sig = "|".join([p.get("country_decision", ""), p.get("event_type", ""),
                         loc, date_key(p.get("published_time"))])
        clusters.setdefault(sig, []).append(p)

    promoted = []
    stayed = 0
    for sig, items in clusters.items():
        # 独立来源（按 source_group 去重：同一通讯社多转载/中英文算1）
        groups = {}
        src_ids = set()
        for it in items:
            g = it.get("source_group") or it.get("source_id")
            groups.setdefault(g, it)
            src_ids.add(it.get("source_id"))
        distinct = list(groups.values())
        is_official = any(it.get("source_class") == "A" for it in distinct)
        if len(distinct) >= 2:
            cls = "B"
        elif is_official:
            cls = "A"
        else:
            cls = "C"
        if cls == "C":
            stayed += 1
            continue
        # 主事件 = 信息最全的一条
        main = max(distinct, key=lambda x: len(x.get("summary_original") or ""))
        etype = main.get("event_type") or "other_security"
        country = "乍得" if main.get("country_decision") == "chad" else "尼日尔"
        ev = {
            "event_id": "",
            "country": country, "country_cn": country,
            "country_risk_level": 4 if etype in ("armed_conflict", "terrorist_attack", "military_operation", "kidnapping") else 3,
            "region": loc, "location": loc, "latitude": None, "longitude": None,
            "event_type": etype, "event_severity": "高" if cls == "B" else "中",
            "title_cn": main.get("title_cn", ""),
            "title_original": main.get("title_original"),
            "summary_cn": main.get("summary_cn", ""),
            "summary_original": main.get("summary_original"),
            "event_time": main.get("published_time"), "published_time": main.get("published_time"),
            "source_name": main.get("source_name"),
            "source_url": main.get("url"),
            "source_language": main.get("language"),
            "china_related": ("chinois" in (main.get("title_original", "") + main.get("summary_original", "")).lower()
                              or "中国" in (main.get("title_original", "") + main.get("summary_original", ""))
                              or "china" in (main.get("title_original", "") + main.get("summary_original", "")).lower()),
            "confidence": "已核实" if cls == "B" else "官方单一来源",
            "verification_status": "cross_verified" if cls == "B" else "official_unverified",
            "official_claim": cls == "A",
            "independent_source_count": len(distinct),
            "source_position": main.get("source_position"),
            "impact": "待评估", "progress": "持续关注", "potential_impact": "待评估",
            "created_at": now_iso(), "updated_at": now_iso(),
            "is_demo": False, "auto_collected": True, "needs_translation": main.get("title_cn") in (None, ""),
            "source_links": [{"name": it.get("source_name"), "url": it.get("url")} for it in distinct],
            "promotion_class": cls,
        }
        promoted.append(ev)

    # 去重写入 events.json
    existing_urls = {e.get("source_url") for e in events_doc.get("events", [])}
    existing_titles = {e.get("title_original", "").strip().lower() for e in events_doc.get("events", [])}
    max_n = 0
    for e in events_doc.get("events", []):
        try:
            n = int(str(e.get("event_id", "")).split("-")[-1])
            max_n = max(max_n, n)
        except ValueError:
            pass
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    added = 0
    for ev in promoted:
        if ev["source_url"] in existing_urls:
            continue
        if ev["title_original"] and ev["title_original"].strip().lower() in existing_titles:
            continue
        max_n += 1
        ev["event_id"] = "EVT-%s-%03d" % (date_str, max_n)
        events_doc["events"].append(ev)
        existing_urls.add(ev["source_url"])
        added += 1

    if args.apply:
        events_doc["updated_at"] = now_iso()
        json.dump(events_doc, open(os.path.join(DATA, "events.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print("已写入 events.json，本次新增：%d" % added)
    else:
        print("[预览] 可提升为正式事件：%d（A/B类）；保留在 pending：%d（C类）" % (len(promoted), stayed))
        print("本次将新增：%d" % added)
    # 按国统计
    byc = {}
    for ev in promoted:
        byc[ev["country"]] = byc.get(ev["country"], 0) + 1
    print("提升按国家：", byc)


if __name__ == "__main__":
    main()
