#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect.py —— 乍得/尼日尔采集主控（第二轮整改版）。

三级数据池 + 结构化国家识别 + 确定性相关性筛选 + 来源分级(A/B/C) + 多源聚类。

流程（严格按需求文档）：
  1. 读取 data/sources.json（已测试来源）；
  2. 按国家分组，调用 collectors 真实采集；
  3. 国家识别（结构化字段，单词边界，尼日尔/尼日利亚 & Lake Chad 防误判）；
  4. 相关性第一阶段（确定性排除体育/农业/会议/评论等）；
  5. 去重（URL + 标题）；
  6. 写入 raw_candidates.json（一级：所有候选+诊断）；
  7. 相关且国家明确 → 进入聚类；
  8. 聚类后按来源分级：
       A类：官方/国家媒体单一来源 → 可正式发布（official_unverified 标注）；
       B类：≥2 独立可靠来源 → 可正式发布（cross_verified）；
       C类：单一普通媒体 → 仅进 pending_events，不进 events.json；
     需语义复核(needs_review) → 仅进 pending，不进 events；
  9. 回写 sources.json 运行状态。

合规：仅公开信息；不绕过限制；评论类(lead_only)不进正式事件。
不自动把单普通来源提升为正式事件（修复旧逻辑）。

用法：
  python scripts/collect.py            # 采集+三级池+聚类（写入 events 由 clean+promote 决定）
  python scripts/collect.py --dry      # 仅写 raw/pending，不写 events
  python scripts/collect.py --hours 72 # 回溯窗口（默认 72h）
"""
import os
import sys
import json
import re
import hashlib
import argparse
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, "collectors"))

from country_runner import (load_country_cfg, run_country, identify_country,
                            relevance_stage1, classify_type)  # noqa: E402

DATA = os.path.join(ROOT, "data")

CONFIG = {
    "乍得": load_country_cfg("chad"),
    "尼日尔": load_country_cfg("niger"),
}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def beijing_now():
    return datetime.now(timezone.utc) + timedelta(hours=8)


def load_json(name, default):
    p = os.path.join(DATA, name)
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def candidate_id(title, url):
    h = hashlib.md5((title + url).encode("utf-8")).hexdigest()[:10]
    return "CAND-" + h


def source_class(src):
    pos = src.get("source_position")
    if pos in ("official", "state_media", "un_humanitarian", "china_official"):
        return "A"  # 官方/国家媒体/联合国与人道机构/中国官方
    return "C"  # 普通媒体（默认待核实）


def build_candidate(a, src, country, cid):
    c = cid
    etype, needs_review_type = classify_type(a.get("summary", ""), a.get("title", ""))
    return {
        "candidate_id": candidate_id(a["title"], a["url"]),
        "title_original": a["title"],
        "url": a["url"],
        "summary_original": a["summary"],
        "published_time": a["published"],
        "fetched_at": now_iso(),
        "source_id": src.get("source_id"),
        "source_name": src.get("name"),
        "source_url": src.get("url"),
        "source_position": src.get("source_position"),
        "source_class": source_class(src),
        "language": a["language"],
        "country": country,
        "country_en": CONFIG[country].get("country_en"),
        # 国家识别结构化字段
        "country_decision": c["decision"],
        "country_match_score": c["country_match_score"],
        "matched_country_entities": c["matched_country_entities"],
        "matched_location_entities": c["matched_location_entities"],
        "excluded_entities": c["excluded_entities"],
        "event_location_country": c["event_location_country"],
        "mentioned_countries": c["mentioned_countries"],
        "country_decision_reason": c["country_decision_reason"],
        # 相关性
        "relevant": a.get("_relevant"),
        "rel_score": a.get("_rel_score"),
        "rel_matched": a.get("_rel_matched"),
        "rel_excluded": a.get("_rel_excluded"),
        # 分类
        "event_type": etype,
        "event_type_needs_review": needs_review_type,
        "needs_review": bool(a.get("_needs_review")) or needs_review_type,
        # 翻译/提升状态
        "needs_translation": True,
        "title_cn": "",
        "summary_cn": "",
        "promoted": False,
        "lead_only": bool(src.get("lead_only")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="不写 events.json")
    ap.add_argument("--hours", type=int, default=72, help="回溯窗口(小时)")
    args = ap.parse_args()

    sources = load_json("sources.json", {}).get("sources", [])
    by_country = {}
    for s in sources:
        if not s.get("enabled"):
            continue
        if s.get("status") in ("test_failed", "blocked"):
            continue
        by_country.setdefault(s["country"], []).append(s)

    raw = load_json("raw_candidates.json", {"items": [], "updated_at": ""})
    pending = load_json("pending_events.json", {"items": [], "updated_at": ""})

    seen_urls = {i.get("url") for i in raw.get("items", [])}
    seen_urls |= {i.get("url") for i in pending.get("items", [])}
    seen_keys = {i.get("title_original", "").strip().lower() for i in raw.get("items", [])}

    src_stats = {}

    for country, cf in CONFIG.items():
        srcs = by_country.get(country, [])
        if not srcs:
            continue
        print("[采集] %s：%d 个来源" % (country, len(srcs)))
        results = run_country(cf, srcs)
        for res in results:
            src = res["source"]
            arts = res["articles"]
            det = len(arts)
            rel = 0
            for a in arts:
                dec = (a.get("_country") or {}).get("decision")
                # 只收「明确属于本国」或「区域(Lake Chad Basin)」候选
                if dec not in ("chad", "niger", "regional"):
                    continue
                rel_flag = a.get("_relevant")
                if rel_flag is not True:
                    # 非相关或待复核：仅进 raw（不进 pending/events）
                    url = a["url"]
                    if url and url not in seen_urls:
                        cand = build_candidate(a, src, country, a["_country"])
                        cand["relevant"] = False
                        raw["items"].append(cand)
                        seen_urls.add(url)
                    continue
                url = a["url"]
                if not url:
                    continue
                if url in seen_urls:
                    continue
                key = (a["title"] or "").strip().lower()
                if key and key in seen_keys:
                    continue
                cand = build_candidate(a, src, country, a["_country"])
                raw["items"].append(cand)
                seen_urls.add(url)
                if key:
                    seen_keys.add(key)
                rel += 1
                # 进 pending（待核实/待第二来源/待语义复核）
                pcand = dict(cand)
                pcand["needs_second_source"] = (cand["source_class"] == "C")
                pcand["verification_status"] = "pending" if cand["source_class"] == "C" else "official_unverified"
                pending["items"].append(pcand)
            src_stats[src.get("source_id")] = (det, rel)

    raw["updated_at"] = now_iso()
    pending["updated_at"] = now_iso()
    with open(os.path.join(DATA, "raw_candidates.json"), "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    with open(os.path.join(DATA, "pending_events.json"), "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)

    # 回写 sources.json 运行统计
    sd = load_json("sources.json", {})
    for s in sd.get("sources", []):
        sid = s.get("source_id")
        if sid in src_stats:
            det, rel = src_stats[sid]
            s["articles_detected_last_run"] = det
            s["relevant_articles_last_run"] = rel
            s["last_success_at"] = now_iso() if det > 0 else s.get("last_success_at", "")
            s["last_failure_at"] = "" if det > 0 else now_iso()
            s["failure_count"] = 0 if det > 0 else (s.get("failure_count", 0) + 1)
            if det > 0:
                s["status"] = "active" if s.get("status") != "degraded" else "degraded"
            elif s.get("status") not in ("test_failed", "blocked", "requires_api"):
                s["status"] = "degraded"
    with open(os.path.join(DATA, "sources.json"), "w", encoding="utf-8") as f:
        json.dump(sd, f, ensure_ascii=False, indent=2)

    print("原始候选池条目：%d" % len(raw["items"]))
    print("待核实池：%d" % len(pending["items"]))
    byc = {}
    for p in pending.get("items", []):
        byc[p["country"]] = byc.get(p["country"], 0) + 1
    print("待核实池按国家：", byc)
    # 相关性≠True 但仍进 raw 的数量
    nonrel = sum(1 for i in raw["items"] if i.get("relevant") is not True)
    print("raw 中非相关/待复核候选：%d（不进 pending/events）" % nonrel)


if __name__ == "__main__":
    main()
