# -*- coding: utf-8 -*-
"""第二轮整改：复检 events.json 中乍得/尼日尔正式事件。
用新版 relevance_stage1 + classify_type 复检，不合规者移入 quarantine_events.json（不删除）。
用法：python scripts/revalidate_events.py [--apply]
"""
import json
import sys
import os
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
from collect import relevance_stage1, classify_type  # noqa: E402

EVENTS = os.path.join(BASE, "data", "events.json")
QUAR = os.path.join(BASE, "data", "quarantine_events.json")
TARGET_COUNTRIES = {"乍得", "尼日尔"}


def load(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    apply = "--apply" in sys.argv
    data = load(EVENTS, [])
    items = data if isinstance(data, list) else data.get("events", data.get("items", []))

    keep, removed = [], []
    for ev in items:
        if ev.get("country") not in TARGET_COUNTRIES:
            keep.append(ev)
            continue
        title = ev.get("title_original") or ev.get("title_cn") or ""
        summary = ev.get("summary_original") or ev.get("summary_cn") or ""
        text = "%s %s" % (title, summary)
        ok, score, hits, reason = relevance_stage1(text)
        etype, fallback = classify_type(text, title)
        problems = []
        if not ok:
            problems.append("relevance:%s" % reason)
        if ok:
            # 修正事件类型（旧版误标）
            cn_map = {
                "armed_conflict": "武装冲突", "terrorist_attack": "恐怖袭击",
                "civil_unrest": "社会骚乱", "crime": "刑事犯罪",
                "kidnapping": "绑架劫持", "political_event": "政治事件",
                "humanitarian_crisis": "人道主义危机", "natural_disaster": "自然灾害",
                "epidemic": "疫情疾病", "other_security": "其他安全事件",
            }
            new_cn = cn_map.get(etype, "其他安全事件")
            if ev.get("event_type") != new_cn:
                ev["event_type_prev"] = ev.get("event_type")
                ev["event_type"] = new_cn
                ev["revalidated"] = True
        if problems:
            ev["quarantine_reason"] = ";".join(problems)
            ev["quarantined_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            ev["quarantine_stage"] = "events_revalidate"
            removed.append(ev)
        else:
            keep.append(ev)

    print("events 总数：%d；乍得/尼日尔复检隔离：%d；保留：%d" % (len(items), len(removed), len(keep)))
    for ev in removed:
        print("  [隔离] %s | %s | %s" % (ev.get("event_id"), ev.get("country"), (ev.get("title_cn") or "")[:40]))
    retyped = [e for e in keep if e.get("revalidated")]
    for ev in retyped:
        print("  [改类] %s | %s -> %s | %s" % (ev.get("event_id"), ev.get("event_type_prev"), ev.get("event_type"), (ev.get("title_cn") or "")[:40]))

    if not apply:
        print("[dry-run] 未写入。--apply 生效。")
        return

    if isinstance(data, list):
        out = keep
    else:
        data["events" if "events" in data else "items"] = keep
        out = data
    with open(EVENTS, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    qdata = load(QUAR, [])
    qitems = qdata if isinstance(qdata, list) else qdata.get("items", qdata.get("events", []))
    qitems.extend(removed)
    with open(QUAR, "w", encoding="utf-8") as f:
        json.dump(qitems if isinstance(qdata, list) else qdata, f, ensure_ascii=False, indent=1)
    print("已写入 events.json / quarantine_events.json")


if __name__ == "__main__":
    main()
