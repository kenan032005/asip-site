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

Stage-2C 起：promote 读写规范数据层（canonical articles / event_clusters），
新事件的发布状态由确定性发布政策决定（仅 cross_verified / direct_official_source
自动达发布门槛；单一来源进入 verification_pending，不自动发布）。
events.json 等遗留池由 compatibility_export 单向再生成。

仅当 --apply 时写回；否则预览。
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, SCRIPT_DIR)

from data.repository import Repository  # noqa: E402
from data.migrate_stage2 import (event_to_cluster, build_source_index,
                                 _unwrap_source)  # noqa: E402
from data.compatibility_export import export_all  # noqa: E402
from pipeline_core import generate_run_id  # noqa: E402


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

    # Stage-2C：读规范数据层
    run_id = generate_run_id()
    repo = Repository(root=ROOT, run_id=run_id)
    articles = repo.load_articles()
    clusters_all = repo.load_event_clusters()
    # pending 视图（与遗留 pending_events.json 语义一致）
    pending = [dict(a.get("legacy_payload") or {}) for a in articles
               if a.get("processing_status") == "queued_for_verification"]

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

    # 去重（对既有 clusters：URL 与标题）
    existing_urls = set()
    existing_titles = set()
    for c in clusters_all:
        lp = c.get("legacy_payload") or {}
        for u in (lp.get("source_url"), ):
            if u:
                existing_urls.add(u)
        t = (c.get("title_original") or lp.get("title_original") or "").strip().lower()
        if t:
            existing_titles.add(t)

    # legacy 顺序号仅用于 legacy_event_id 展示（canonical event_id 为内容指纹）
    max_n = 0
    for c in clusters_all:
        try:
            n = int(str(c.get("legacy_event_id", "")).split("-")[-1])
            max_n = max(max_n, n)
        except ValueError:
            pass
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    upgraded_sources = repo.load_sources()
    idx = build_source_index([_unwrap_source(s) for s in upgraded_sources])

    new_clusters = []
    new_src_articles = []
    added = 0
    for ev in promoted:
        if ev["source_url"] in existing_urls:
            continue
        if ev["title_original"] and ev["title_original"].strip().lower() in existing_titles:
            continue
        max_n += 1
        ev["event_id"] = "EVT-%s-%03d" % (date_str, max_n)
        cl, src_art = event_to_cluster(ev, idx, is_new=True)
        new_clusters.append(cl)
        new_src_articles.append(src_art)
        existing_urls.add(ev["source_url"])
        added += 1

    if args.apply:
        if new_clusters:
            # 已提升候选 → 文章状态标记 linked_to_event
            promoted_cids = {ev.get("candidate_id") for ev in promoted if ev.get("candidate_id")}
            for a in articles:
                lp = a.get("legacy_payload") or {}
                if lp.get("candidate_id") in promoted_cids:
                    a["processing_status"] = "linked_to_event"
            # 合并来源文章
            byid = {a["article_id"]: a for a in articles}
            for sa in new_src_articles:
                if sa["article_id"] in byid:
                    byid[sa["article_id"]]["processing_status"] = "linked_to_event"
                else:
                    byid[sa["article_id"]] = sa
            repo.save_articles(list(byid.values()), run_id)
            repo.save_event_clusters(clusters_all + new_clusters, run_id)
        # 遗留池单向再生成
        stats = export_all(repo, run_id)
        pub_pending = sum(1 for c in new_clusters
                          if c["publication_status"] == "verification_pending")
        print("已写入 canonical event_clusters，本次新增：%d（其中待核实不发布：%d）"
              % (added, pub_pending))
        print("兼容导出: events=%d pending=%d raw=%d published=%d"
              % (stats["legacy_events"], stats["legacy_pending"],
                 stats["legacy_raw"], stats["published_events"]))
    else:
        print("[预览] 可提升为正式事件：%d（A/B类）；保留在 pending：%d（C类）" % (len(promoted), stayed))
        print("本次将新增：%d" % added)
        for c in new_clusters:
            print("  - %s publication_status=%s (%s)"
                  % (c["event_id"], c["publication_status"], c["verification_level"]))
    # 按国统计
    byc = {}
    for ev in promoted:
        byc[ev["country"]] = byc.get(ev["country"], 0) + 1
    print("提升按国家：", byc)


if __name__ == "__main__":
    main()
