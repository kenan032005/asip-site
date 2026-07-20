#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translate.py —— 翻译与中文摘要生成（零依赖框架，占位）。

职责（需求文档第五/十七节）：
  - 原文为英文/法文/阿拉伯文/葡萄牙文或其他语言时，统一生成中文标题与中文摘要；
  - 同时保留原文标题、原文语言、原始来源名称、原文链接、原文发布时间；
  - 翻译不得改变：人名、地名、组织名称、武装组织名称、行政区名称、伤亡数字、官方机构名称；
  - 首次出现的重要专有名词采用「中文译名（原文）」，并建立词库保持每天一致；
  - 不得将分析判断写成事实。

本框架为占位实现：不调用任何外部翻译服务，也不自动编造中文内容。
真实运行时应接入经授权的翻译/摘要能力（企业 LLM 或翻译 API），
并对生成内容标注「初步判断/可能/预计/存在…风险」等谨慎措辞。

若 title_cn 缺失，则标记为 needs_translation=True，由后续流程处理。
"""
import os
import json
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def translate_event(e):
    if not e.get("title_cn") and e.get("title_original"):
        e["needs_translation"] = True
    if not e.get("summary_cn") and e.get("title_original"):
        e["needs_summary"] = True
    # 真实翻译在此接入；框架阶段仅做标记，绝不编造
    e["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    return e


def main():
    path = os.path.join(DATA, "events.json")
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    need = 0
    for e in doc.get("events", []):
        translate_event(e)
        if e.get("needs_translation"):
            need += 1
    print("扫描事件", len(doc.get("events", [])), "条；待翻译", need, "条（框架阶段不自动生成，避免编造）。")


if __name__ == "__main__":
    main()
