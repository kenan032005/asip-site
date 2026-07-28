#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect.py —— 乍得/尼日尔采集主控（三级数据池 + 防误判 + 提升正式事件）。

流程：
  1. 读取 data/sources.json（已测试来源）；
  2. 按国家分组，调用 collectors 真实采集；
  3. 过滤：仅保留「国家可归本国(_country_ok=True)」且「社会安全相关(_relevant)」；
  4. 去重（URL + 标题）；
  5. 写入 data/raw_candidates.json（一级：原始候选）；
  6. 相关且国家明确的写入 data/pending_events.json（二级：待核实/待第二来源）；
  7. 可靠单来源（非 lead_only）提升为正式事件写入 data/events.json（三级），
     标记 auto_collected / needs_translation / verification_status=partial；
  8. 回写 sources.json 运行状态（检测数、相关数、成功时间、失败数、status）。

合规：仅公开信息；不绕过限制；评论类(lead_only)来源不直接进入正式事件。

用法：
  python scripts/collect.py            # 全量采集+三级池+提升
  python scripts/collect.py --dry      # 仅写入 raw/pending，不提升 events
"""
import os
import sys
import json
import re
import hashlib
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, "collectors"))

from country_runner import load_country_cfg, run_country  # noqa: E402

DATA = os.path.join(ROOT, "data")

CONFIG = {
    "乍得": load_country_cfg("chad"),
    "尼日尔": load_country_cfg("niger"),
}

TERROR = ["terror", "terrorist", "terrorisme", "boko haram", "iswap", "fact",
          "jnim", "gsim", "isgs", "恐怖", "袭击", "武装", "叛乱", "伏击",
          "embuscade", "attaque", "attack", "insurgent", "insurgé", "rebel",
          "milice", "armé", "clash", "conflit", "affrontement", "killed",
          "mort", "交火", "战乱"]
KIDNAP = ["kidnap", "kidnapping", "enlèvement", "otage", "hostage", "绑架", "人质"]
PROTEST = ["manifest", "manifestation", "protest", "grève", "greve", "strike",
           "示威", "骚乱"]
DISASTER = ["inondation", "flood", "crue", "洪水", "drought", "sécheresse", "干旱",
            "cholera", "霍乱", "epidemic", "épidémie", "earthquake", "séisme",
            "地震"]
BORDER = ["frontière", "frontier", "边境", "fermeture", "闭关", "couvre-feu", "宵禁"]
CHINA_KW = ["中国", "chinese", "china", "chine", "citoyens chinois",
            "ressortissants chinois", "entreprises chinoises", "citéoyens chinois",
            "使馆", "ambassade", "中资", "中国公民"]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(name, default):
    p = os.path.join(DATA, name)
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def map_type(matched):
    m = " ".join(matched).lower()
    if any(k in m for k in TERROR):
        return "武装冲突", "高"
    if any(k in m for k in KIDNAP):
        return "绑架、抢劫和严重犯罪", "高"
    if any(k in m for k in DISASTER):
        return "自然灾害", "中"
    if any(k in m for k in BORDER):
        return "边境关闭及跨境风险", "中"
    if any(k in m for k in PROTEST):
        return "示威、罢工和社会骚乱", "中"
    return "武装冲突", "中"


def is_china(text):
    t = (text or "").lower()
    return any(k in t for k in CHINA_KW)


def candidate_id(title, url):
    h = hashlib.md5((title + url).encode("utf-8")).hexdigest()[:10]
    return "CAND-" + h


def build_candidate(a, src, country, cf):
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
        "language": a["language"],
        "country": country,
        "country_en": cf.get("country_en"),
        "country_ok": a.get("_country_ok"),
        "country_reason": a.get("_country_reason"),
        "relevant": a.get("_relevant"),
        "rel_score": a.get("_rel_score"),
        "rel_matched": a.get("_rel_matched"),
        "needs_translation": True,
        "title_cn": "",
        "summary_cn": "",
        "promoted": False,
        "lead_only": bool(src.get("lead_only")),
    }


def build_event(p, event_id):
    etype, sev = map_type(p["rel_matched"])
    china = is_china(p["title_original"] + " " + (p["summary_original"] or ""))
    risk = 4 if etype in ("武装冲突", "恐怖袭击", "绑架、抢劫和严重犯罪") else 3
    return {
        "event_id": event_id,
        "country": p["country"], "country_cn": p["country"],
        "country_risk_level": risk,
        "region": "", "location": "", "latitude": None, "longitude": None,
        "event_type": etype, "event_severity": sev,
        "title_cn": "", "title_original": p["title_original"],
        "summary_cn": "", "summary_original": p["summary_original"],
        "event_time": p["published_time"], "published_time": p["published_time"],
        "source_name": p["source_name"], "source_url": p["url"],
        "source_language": p["language"],
        "china_related": china,
        "confidence": "较高可信", "verification_status": "partial",
        "impact": "待评估", "progress": "持续关注", "potential_impact": "待评估",
        "created_at": now_iso(), "updated_at": now_iso(),
        "is_demo": False, "auto_collected": True, "needs_translation": True,
        "independent_source_count": 1,
        "source_position": p.get("source_position"),
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="不提升为正式事件")
    args = ap.parse_args()

    sources = load_json("sources.json", {}).get("sources", [])
    by_country = {}
    for s in sources:
        if not s.get("enabled"):
            continue
        if s.get("status") in ("test_failed",):
            continue
        by_country.setdefault(s["country"], []).append(s)

    raw = load_json("raw_candidates.json", {"items": [], "updated_at": ""})
    pending = load_json("pending_events.json", {"items": [], "updated_at": ""})
    events_doc = load_json("events.json", {"events": []})

    seen_urls = {i.get("url") for i in raw.get("items", [])}
    seen_urls |= {i.get("url") for i in pending.get("items", [])}
    seen_urls |= {e.get("source_url") for e in events_doc.get("events", [])}
    seen_keys = {i.get("title_original", "").strip().lower() for i in raw.get("items", [])}
    seen_keys |= {e.get("title_original", "").strip().lower() for e in events_doc.get("events", [])}

    src_stats = {}  # source_id -> (detected, relevant)

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
                if a.get("_country_ok") is not True:
                    continue
                if not a.get("_relevant"):
                    continue
                url = a["url"]
                if not url:
                    continue
                if url in seen_urls:
                    continue
                key = (a["title"] or "").strip().lower()
                if key and key in seen_keys:
                    continue
                cand = build_candidate(a, src, country, cf)
                raw["items"].append(cand)
                seen_urls.add(url)
                if key:
                    seen_keys.add(key)
                rel += 1
                # 进入 pending（待核实/待第二来源）
                pcand = dict(cand)
                pcand["needs_second_source"] = True
                pcand["verification_status"] = "pending"
                pending["items"].append(pcand)
            src_stats[src.get("source_id")] = (det, rel)
            # 回写 source 错误
            if res["errors"]:
                src["_errors"] = res["errors"]

    # 提升可靠单来源 -> 正式事件
    existing_urls = {e.get("source_url") for e in events_doc.get("events", [])}
    existing_titles = {e.get("title_original", "").strip().lower()
                       for e in events_doc.get("events", [])}
    max_n = 0
    for e in events_doc.get("events", []):
        try:
            n = int(str(e.get("event_id", "")).split("-")[-1])
            max_n = max(max_n, n)
        except ValueError:
            pass
    promoted = 0
    new_events = []
    if not args.dry:
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        for p in pending.get("items", []):
            if p.get("promoted"):
                continue
            if p.get("lead_only"):
                continue  # 评论类不进正式事件
            url = p["url"]
            if url in existing_urls:
                p["promoted"] = True
                continue
            t = (p["title_original"] or "").strip().lower()
            if t and t in existing_titles:
                p["promoted"] = True
                continue
            max_n += 1
            ev = build_event(p, "EVT-%s-%03d" % (date_str, max_n))
            new_events.append(ev)
            existing_urls.add(url)
            seen_urls.add(url)
            p["promoted"] = True
            promoted += 1
        events_doc["events"].extend(new_events)
        events_doc["updated_at"] = now_iso()
        events_doc["is_demo"] = False

    # 写回三级池
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
            s["status"] = "active" if det > 0 else ("degraded" if s.get("status") != "test_failed" else "test_failed")
    with open(os.path.join(DATA, "sources.json"), "w", encoding="utf-8") as f:
        json.dump(sd, f, ensure_ascii=False, indent=2)

    if not args.dry:
        with open(os.path.join(DATA, "events.json"), "w", encoding="utf-8") as f:
            json.dump(events_doc, f, ensure_ascii=False, indent=2)

    print("原始候选池新增：%d 条（总计 %d）" % (
        len(raw["items"]) - len([1 for _ in []]), len(raw["items"])))
    print("待核实池：%d 条" % len(pending["items"]))
    if not args.dry:
        print("提升为正式事件：%d 条（events.json 总计 %d）" % (
            promoted, len(events_doc["events"])))
    else:
        print("（dry 模式，未提升正式事件）")
    # 按国统计
    byc = {}
    for p in pending.get("items", []):
        byc[p["country"]] = byc.get(p["country"], 0) + 1
    print("待核实池按国家：", byc)


if __name__ == "__main__":
    main()
