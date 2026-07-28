#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""normalize_pending.py —— 规范化 pending_events.json 中的历史条目。

处理两类问题：
1. 旧格式条目缺 source_class / 结构化国家判定字段 → 按 sources.json 回填分级，
   并用新版国家识别 + 相关性筛选重新校验；不合格的移入隔离文件。
2. commentary（评论性）来源条目 → 标记 lead_only，仅作线索。

用法：python scripts/normalize_pending.py [--apply]
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "collectors"))

from country_runner import identify_country, relevance_stage1, classify_type, load_country_cfg  # noqa: E402

DATA = os.path.join(ROOT, "data")
APPLY = "--apply" in sys.argv


def jload(name, default):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def jsave(name, obj):
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main():
    pending = jload("pending_events.json", {"items": []})
    quarantine = jload("quarantine_events.json", {"items": []})
    sources = {s["source_id"]: s for s in jload("sources.json", {"sources": []})["sources"]}
    cfgs = {"乍得": load_country_cfg("chad"), "尼日尔": load_country_cfg("niger")}

    kept, moved, backfilled = [], 0, 0
    for it in pending["items"]:
        src = sources.get(it.get("source_id"), {})
        # 按 source_position 强制重算 source_class（修正旧采集逻辑的错误分级）
        pos = it.get("source_position") or src.get("source_position")
        new_cls = "A" if pos in (
            "official", "state_media", "un_humanitarian", "china_official") else "C"
        if it.get("source_class") != new_cls:
            it["source_class"] = new_cls
            backfilled += 1
        # commentary 仅线索
        if (it.get("source_position") or src.get("source_position")) == "commentary":
            it["lead_only"] = True
        # 全量相关性复检（用最新过滤器，含中性复合词免疫+弱信号降级）
        blob_all = " ".join([it.get("title_original") or "", it.get("summary_original") or ""])
        rel_all, _s, _m, excl_all = relevance_stage1(blob_all)
        if rel_all is False:
            it["quarantine_reason"] = "相关性复检排除:%s" % excl_all
            quarantine["items"].append(it)
            moved += 1
            continue
        if rel_all is None:
            it["needs_review"] = True
            it["relevance_reason"] = excl_all
        # 缺结构化判定字段的旧条目：重新校验
        if not it.get("country_decision"):
            cfg = cfgs.get(it.get("country"))
            if not cfg:
                kept.append(it)
                continue
            blob = " ".join([it.get("title_original", ""), it.get("summary_original", ""),
                             it.get("title_cn", ""), it.get("summary_cn", "")])
            cid = identify_country(blob, cfg)
            expect = "chad" if it.get("country") == "乍得" else "niger"
            rel, score, matched, excl = relevance_stage1(blob)
            ok_country = cid["decision"] in (expect, "regional")
            ok_rel = rel is not False
            if not (ok_country and ok_rel):
                it["quarantine_reason"] = ("国家判定=%s" % cid["decision"]) if not ok_country else ("相关性排除:%s" % excl)
                quarantine["items"].append(it)
                moved += 1
                continue
            # 回填结构化字段
            it["country_decision"] = cid["decision"]
            it["country_match_score"] = cid["country_match_score"]
            it["matched_country_entities"] = cid["matched_country_entities"]
            it["matched_location_entities"] = cid["matched_location_entities"]
            it["excluded_entities"] = cid["excluded_entities"]
            it["event_location_country"] = cid["event_location_country"]
            it["mentioned_countries"] = cid["mentioned_countries"]
            it["country_decision_reason"] = cid["country_decision_reason"]
            if rel is None:
                it["needs_review"] = True
            etype, need = classify_type(it.get("summary_original", ""), it.get("title_original", ""))
            if not it.get("event_type"):
                it["event_type"] = etype
                it["event_type_needs_review"] = need
        kept.append(it)

    print("pending 总数：%d → 保留 %d，隔离 %d，回填分级 %d" %
          (len(pending["items"]), len(kept), moved, backfilled))
    if APPLY:
        pending["items"] = kept
        jsave("pending_events.json", pending)
        jsave("quarantine_events.json", quarantine)
        print("已写入 pending_events.json / quarantine_events.json")
    else:
        print("[dry-run] 未写入。--apply 生效。")


if __name__ == "__main__":
    main()
