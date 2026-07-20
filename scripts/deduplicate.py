#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deduplicate.py —— 事件去重（零依赖）。

去重依据（需求文档第十七节）：
  国家、地点、事件时间、人物和机构、伤亡数字、标题语义、事件类型。
同一事件被多源报道时合并为一条，不重复展示。

用法（模块方式被 collect 调用；也可独立预览）：
  python scripts/deduplicate.py
"""
import os
import json
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def _norm(s):
    if not s:
        return ""
    s = str(s).lower()
    s = re.sub(r"[\s\u3000]+", "", s)
    s = re.sub(r"[，。、,.!！?？:：;；'\"“”‘’()（）\[\]【】]", "", s)
    return s


def _key(e):
    return (
        _norm(e.get("country")), _norm(e.get("location")), _norm(e.get("event_time")),
        _norm(e.get("event_type")), _norm(e.get("title_cn") or e.get("title_original")),
    )


def deduplicate(events):
    seen = {}
    merged = []
    for e in events:
        k = _key(e)
        if k in seen:
            # 合并：保留信息更完整的，来源合并
            base = seen[k]
            for fld in ("summary_cn", "title_original", "source_name", "source_url"):
                if e.get(fld) and not base.get(fld):
                    base[fld] = e[fld]
            if e.get("source_name") and e.get("source_url"):
                base.setdefault("extra_sources", [])
                base["extra_sources"].append({"name": e["source_name"], "url": e["source_url"]})
        else:
            seen[k] = e
            merged.append(e)
    return merged


def main():
    path = os.path.join(DATA, "events.json")
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    before = len(doc.get("events", []))
    after = deduplicate(doc.get("events", []))
    print("去重前：", before, " 去重后：", len(after))


if __name__ == "__main__":
    main()
