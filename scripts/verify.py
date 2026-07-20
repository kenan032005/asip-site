#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify.py —— 信息核实与可信度标注（零依赖框架）。

规则（需求文档第十三/十七节）：
  - 重大事件原则上至少两个独立来源交叉核实；
  - 单一官方来源（政府/警方/军方/联合国/使领馆）可采用，但标注"尚待独立来源进一步核实"；
  - 社交媒体仅作线索，不得直接作为已核实事实。

本框架提供基础可信度推断（依据来源数量），真实核实由人工/后续流程完成。
  - 多来源（>=2 不同 source_name）-> 较高可信
  - 单一官方来源 -> 较高可信（标注待独立核实）
  - 单一非官方/未知 -> 待进一步核实

用法：
  python scripts/verify.py
"""
import os
import json
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

OFFICIAL_HINTS = ["政府", "总统", "总理", "内政", "国防", "警察", "军队", "民航", "卫生", "使馆", "使领馆",
                  "联合国", "UN", "官方", "gov", "police", "army", "ministry", "embassy", "fmprc"]


def count_sources(e):
    names = set()
    if e.get("source_name"):
        names.add(e["source_name"])
    for s in e.get("extra_sources", []) or []:
        if s.get("name"):
            names.add(s["name"])
    return names


def is_official(e):
    blob = " ".join([str(e.get("source_name", ""))] + [str(s.get("name", "")) for s in e.get("extra_sources", []) or []])
    return any(h.lower() in blob.lower() for h in OFFICIAL_HINTS)


def verify_event(e):
    names = count_sources(e)
    if len(names) >= 2:
        e["confidence"] = "较高可信"
        e["verification_status"] = "partial" if e.get("verification_status") != "verified" else "verified"
    elif is_official(e):
        e["confidence"] = "较高可信"
        e["verification_status"] = e.get("verification_status") or "partial"
        e["verify_note"] = "目前主要依据官方单一来源，尚待独立来源进一步核实。"
    else:
        e["confidence"] = e.get("confidence") or "待进一步核实"
        e["verification_status"] = e.get("verification_status") or "pending"
    e["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    return e


def main():
    path = os.path.join(DATA, "events.json")
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    for e in doc.get("events", []):
        verify_event(e)
    print("已完成", len(doc.get("events", [])), "条事件的可信度推断（预览，未写回）。")


if __name__ == "__main__":
    main()
