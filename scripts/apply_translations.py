#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_translations.py —— 将翻译补丁合并进 events.json，并统一 source_language 为中文。

- 读取 data/translations_pending.json（[{event_id, title_cn, summary_cn}]）
- 按 event_id 覆盖对应事件的 title_cn / summary_cn，并标记 needs_translation=False
- 将全部事件的 source_language 由英文代码（English/French…）规范为中文（英语/法语…）
- 写回 data/events.json（就地更新，保留其它所有字段）

用法：
  python scripts/apply_translations.py
"""
import os
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
EVENTS = os.path.join(DATA, "events.json")
PATCH = os.path.join(DATA, "translations_pending.json")

LANG_MAP = {
    "English": "英语", "French": "法语", "German": "德语", "Spanish": "西班牙语",
    "Italian": "意大利语", "Portuguese": "葡萄牙文", "Turkish": "土耳其语",
    "Arabic": "阿拉伯文", "Russian": "俄文", "Chinese": "中文",
}


def norm_lang(s):
    return LANG_MAP.get((s or "").strip(), (s or "英语").strip())


def main():
    with open(EVENTS, "r", encoding="utf-8") as f:
        doc = json.load(f)
    events = doc.get("events", [])

    # 读取翻译补丁
    patch = {}
    if os.path.exists(PATCH):
        with open(PATCH, "r", encoding="utf-8") as f:
            for item in json.load(f):
                patch[item["event_id"]] = item

    applied = 0
    lang_fixed = 0
    for e in events:
        eid = e.get("event_id")
        # 合并翻译
        if eid in patch:
            p = patch[eid]
            e["title_cn"] = p.get("title_cn", e.get("title_cn"))
            e["summary_cn"] = p.get("summary_cn", e.get("summary_cn"))
            e["needs_translation"] = False
            applied += 1
        # 规范 source_language 为中文
        old = e.get("source_language")
        new = norm_lang(old)
        if new != old:
            e["source_language"] = new
            lang_fixed += 1

    doc["events"] = events
    with open(EVENTS, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    print("合并翻译：", applied, "条")
    print("规范语言字段：", lang_fixed, "条")
    print("事件总数：", len(events))


if __name__ == "__main__":
    main()
