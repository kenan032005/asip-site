#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalize.py —— 事件字段规范化与校验（零依赖）。

确保每条事件具备需求文档规定的字段，缺失项填充合理默认值，
并对时间字段做统一处理（内部以 UTC 存储，前端统一换算北京时间展示）。

用法（作为模块被 collect/verify 调用，也可独立运行预览）：
  python scripts/normalize.py
"""
import os
import json
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# 需求文档规定的事件字段
FIELDS = [
    "event_id", "country", "country_cn", "region", "location", "latitude", "longitude",
    "event_type", "country_risk_level", "event_severity", "title_cn", "title_original",
    "summary_cn", "event_time", "published_time", "source_name", "source_url",
    "source_language", "china_related", "confidence", "verification_status",
    "created_at", "updated_at",
]

EVENT_TYPES = [
    "武装冲突", "恐怖袭击", "军事行动", "政变及政治危机", "选举及政治活动",
    "示威、罢工和社会骚乱", "绑架、抢劫和严重犯罪", "部族、族群和社区冲突",
    "边境关闭及跨境风险", "航空、道路、港口和交通中断",
    "油气、矿业、电力和重要基础设施", "自然灾害", "传染病及公共卫生",
    "涉中国企业和公民", "其他重大社会安全事件",
]


def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_event(e, risk_level_default=4):
    out = {}
    for f in FIELDS:
        out[f] = e.get(f)
    # 默认值补充
    out["event_id"] = out["event_id"] or ("EVT-" + now_iso())
    out["country_cn"] = out["country_cn"] or out["country"]
    out["country_risk_level"] = out["country_risk_level"] or risk_level_default
    out["event_type"] = out["event_type"] if out["event_type"] in EVENT_TYPES else "其他重大社会安全事件"
    out["confidence"] = out["confidence"] or "待进一步核实"
    out["verification_status"] = out["verification_status"] or "pending"
    out["china_related"] = bool(out["china_related"])
    out["created_at"] = out["created_at"] or now_iso()
    out["updated_at"] = out["updated_at"] or now_iso()
    # 时间缺省处理
    out["event_time"] = out["event_time"] or out["published_time"] or now_iso()
    out["published_time"] = out["published_time"] or out["event_time"] or now_iso()
    return out


def main():
    path = os.path.join(DATA, "events.json")
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    events = doc.get("events", [])
    norm = [normalize_event(e) for e in events]
    print("规范化事件数：", len(norm))
    # 不在 dry 模式下写回，避免覆盖演示数据；如需写回请调用 collect 流程
    missing = [e.get("event_id") for e in norm if not e.get("title_cn") and not e.get("title_original")]
    if missing:
        print("警告：以下事件缺少标题：", missing)


if __name__ == "__main__":
    main()
