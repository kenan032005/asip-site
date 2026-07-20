#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect.py —— 信息采集与处理流水线（零依赖框架）。

完整流程（真实运行）：
  collect -> normalize -> deduplicate -> verify -> translate -> generate_reports -> build_site

合规要求（需求文档第二十节，必须严格遵守）：
  - 仅发布公开信息；不绕过登录/付费墙/验证码/反爬/地区限制；
  - 尊重 robots.txt、访问频率限制与网站使用条款；
  - 无法合法访问的来源标记为 paused，不得通过不合规方法抓取；
  - 密钥仅存于 GitHub Secrets / 环境变量，绝不写入代码或提交记录。

本框架阶段：
  - 不主动访问任何外部网站（避免合规风险与滥用）；
  - 对 data/events.json 中已有事件运行处理流水线（规范化/去重/核实/翻译标记）；
  - 真实"抓取最新信息"由各信息源适配器（读取 config/sources.json，逐源测试后启用）
    在后续阶段实现，并严格遵守上述合规约束。

用法：
  python scripts/collect.py            # 预览流水线结果（不写回）
  python scripts/collect.py --write    # 将处理结果写回 data/events.json
"""
import os
import json
import argparse
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

import normalize as _norm
import deduplicate as _dd
import verify as _ver
import translate as _tr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="将处理结果写回 data/events.json")
    args = ap.parse_args()

    path = os.path.join(DATA, "events.json")
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    events = doc.get("events", [])

    # 流水线
    events = [_norm.normalize_event(e) for e in events]
    events = _dd.deduplicate(events)
    for e in events:
        _ver.verify_event(e)
        _tr.translate_event(e)

    doc["events"] = events
    doc["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    print("流水线完成：", len(events), "条事件。")
    conf = {}
    for e in events:
        conf[e.get("confidence", "未知")] = conf.get(e.get("confidence", "未知"), 0) + 1
    print("可信度分布：", conf)

    if args.write:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        print("已写回", path)
    else:
        print("（预览模式，未写回。加 --write 可持久化）")


if __name__ == "__main__":
    main()
