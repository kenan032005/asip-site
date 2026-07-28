#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clean_events.py —— 第二轮整改：清理现有 events.json 中的错误数据。

对乍得/尼日尔事件重新执行结构化国家识别 + 相关性筛选 + 来源分级：
  - 国家误判（如尼日利亚→尼日尔、跨国湖区→乍得、利比亚等→乍得）→ 隔离(quarantine)；
  - 非社会安全（体育/农业/会议/评论）→ 隔离；
  - 单一普通媒体却标记为「较高可信/已核实」→ 降为 pending_events（不得作为正式事件）；
  - 官方单一来源 → 保留但更正 verification_status=official_unverified；
  - 双独立来源 → 保留为 cross_verified。

错误数据移入 data/quarantine_events.json（不永久删除），含隔离原因与审查状态。
其余国家事件原样保留（不在本轮清理范围）。
"""
import os
import sys
import json
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, "collectors"))
from country_runner import (load_country_cfg, identify_country, relevance_stage1)  # noqa

DATA = os.path.join(ROOT, "data")
CFG = {"乍得": load_country_cfg("chad"), "尼日尔": load_country_cfg("niger")}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    doc = json.load(open(os.path.join(DATA, "events.json"), encoding="utf-8"))
    events = doc.get("events", [])

    kept = []
    quarantined = []
    downgraded = []  # 降为 pending

    for e in events:
        c = e.get("country")
        if c not in CFG:
            kept.append(e)  # 非乍得/尼日尔，原样保留
            continue
        cfg = CFG[c]
        blob = (e.get("title_original") or "") + " " + (e.get("summary_original") or "")
        cid = identify_country(blob, cfg)
        dec = cid["decision"]
        if dec in ("exclude", "regional", "unclear"):
            e["quarantine_reason"] = "country_misassignment:%s" % cid["country_decision_reason"]
            e["detected_at"] = now_iso()
            e["original_country"] = c
            e["original_event_type"] = e.get("event_type")
            e["review_status"] = "auto_quarantined"
            quarantined.append(e)
            continue
        # 国家正确 → 检查相关性
        rel, score, matched, excl = relevance_stage1(blob)
        if rel is False:
            e["quarantine_reason"] = "non_security:%s" % (excl or "no_security_signal")
            e["detected_at"] = now_iso()
            e["original_country"] = c
            e["original_event_type"] = e.get("event_type")
            e["review_status"] = "auto_quarantined"
            quarantined.append(e)
            continue
        # 相关性成立 → 来源分级
        pos = e.get("source_position")
        isc = e.get("independent_source_count", 1)
        if pos in ("official", "state_media"):
            e["verification_status"] = "official_unverified"
            e["confidence"] = "官方单一来源"
            e["official_claim"] = True
            kept.append(e)
        elif isc and isc >= 2:
            e["verification_status"] = "cross_verified"
            e["confidence"] = "已核实"
            kept.append(e)
        else:
            # 单一普通媒体：不得作为正式事件 → 降为 pending
            e["verification_status"] = "pending"
            e["confidence"] = "待进一步核实"
            e["_downgraded_from_events"] = True
            downgraded.append(e)

    # 写回
    doc["events"] = kept
    doc["updated_at"] = now_iso()
    json.dump(doc, open(os.path.join(DATA, "events.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # quarantine 文件（累加，不覆盖历史）
    qpath = os.path.join(DATA, "quarantine_events.json")
    qd = json.load(open(qpath, encoding="utf-8")) if os.path.exists(qpath) else {"items": []}
    qd["items"] = qd.get("items", []) + quarantined
    qd["updated_at"] = now_iso()
    json.dump(qd, open(qpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # downgraded → pending_events（带降级标记）
    ppath = os.path.join(DATA, "pending_events.json")
    pdoc = json.load(open(ppath, encoding="utf-8")) if os.path.exists(ppath) else {"items": []}
    for e in downgraded:
        pdoc["items"].append({
            "candidate_id": "DOWNGRADED-" + e.get("event_id", ""),
            "title_original": e.get("title_original"),
            "url": e.get("source_url"),
            "summary_original": e.get("summary_original"),
            "published_time": e.get("published_time"),
            "source_id": e.get("source_id"),
            "source_name": e.get("source_name"),
            "source_position": e.get("source_position"),
            "source_class": "C",
            "country": e.get("country"),
            "country_decision": e.get("country"),
            "country_decision_reason": "原正式事件降级：单一普通来源",
            "relevant": True,
            "event_type": e.get("event_type"),
            "needs_second_source": True,
            "verification_status": "pending",
            "downgraded_from_events": True,
            "needs_translation": e.get("title_cn") in (None, ""),
            "title_cn": e.get("title_cn", ""),
            "summary_cn": e.get("summary_cn", ""),
            "promoted": False,
            "lead_only": bool(e.get("lead_only")),
        })
    pdoc["updated_at"] = now_iso()
    json.dump(pdoc, open(ppath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("原 events.json 总数：%d" % (len(kept) + len(quarantined) + len(downgraded)))
    print("保留（乍得/尼日尔）：%d" % len([k for k in kept if k.get("country") in CFG]))
    print("隔离(quarantine)：%d" % len(quarantined))
    print("降级为 pending：%d" % len(downgraded))
    print("其他国保留：%d" % len([k for k in kept if k.get("country") not in CFG]))


if __name__ == "__main__":
    main()
