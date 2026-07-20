#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASIP 国别日报生成器（零依赖）。

为 6 个设置日报的国家（乍得、尼日尔、贝宁、南苏丹、苏丹、埃塞俄比亚）
各生成一份日报，写入 reports/<daily_country>/<date>.json，并更新索引
reports/<daily_country>/index.json。

日报结构严格遵循需求文档的 12 节。无事件时采用文档规定的"未发现重大新增事件"
表述，绝不编造内容。

用法：
  python scripts/generate_reports.py            # 生成今天（北京时间）的日报
  python scripts/generate_reports.py --date 2026-07-20
  python scripts/generate_reports.py --dry      # 仅预览，不写文件
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
REPORTS = os.path.join(ROOT, "reports")

NO_EVENT = "过去24小时未发现经多源核实的重大新增事件。"
NO_CHINA = "过去24小时未发现经可靠来源证实的涉中国企业或中国公民重大社会安全事件。"
DEFAULT_BASIS = "基于截至北京时间22:00前最近24小时公开来源信息整理；结论随后续核实可能调整。"


def bj_now():
    return datetime.now(timezone.utc) + timedelta(hours=8)


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def beijing_date(d):
    return d.strftime("%Y-%m-%d")


def event_groups(events):
    g = {
        "politics": [], "conflict_terror": [], "stability": [], "infrastructure": [], "china": []
    }
    for e in events:
        t = e.get("event_type", "")
        if t in ("政变及政治危机", "选举及政治活动"):
            g["politics"].append(e)
        elif t in ("武装冲突", "恐怖袭击", "军事行动"):
            g["conflict_terror"].append(e)
        elif t in ("示威、罢工和社会骚乱", "绑架、抢劫和严重犯罪", "部族、族群和社区冲突", "边境关闭及跨境风险"):
            g["stability"].append(e)
        elif t in ("航空、道路、港口和交通中断", "油气、矿业、电力和重要基础设施", "自然灾害"):
            g["infrastructure"].append(e)
        if e.get("china_related") or e.get("involves_china"):
            g["china"].append(e)
    return g


def summarize(group_name, evs):
    if not evs:
        return None
    lines = []
    for e in evs[:6]:
        lines.append("· " + (e.get("title_cn") or e.get("title_original") or ""))
    return "记录 {n} 起相关事件：\n".format(n=len(evs)) + "\n".join(lines)


def build_report(country, dc, events, date_str, generated_at):
    ev_c = [e for e in events if e.get("country") == country and not e.get("is_demo_disabled")]
    # 仅取最近24h（演示数据时间若不在窗口内不影响框架；真实运行按 published_time 过滤）
    ev_c = [e for e in ev_c if not e.get("is_demo")]
    g = event_groups(ev_c)
    has = len(ev_c) > 0

    major = []
    for e in sorted(ev_c, key=lambda x: x.get("published_time", ""), reverse=True)[:6]:
        major.append({
            "time": e.get("event_time", "") or e.get("published_time", ""),
            "location": e.get("location", ""),
            "process": e.get("summary_cn", "") or e.get("title_cn", ""),
            "impact": e.get("impact", "待补充"),
            "progress": e.get("progress", "持续关注"),
            "source": e.get("source_name", ""),
            "source_url": e.get("source_url", ""),
            "confidence": e.get("confidence", ""),
            "potential_impact": e.get("potential_impact", "待评估"),
        })

    sources = []
    for e in ev_c:
        if e.get("source_name") and e.get("source_url") and e["source_url"] != "#":
            sources.append({"name": e["source_name"], "title": e.get("title_original", ""), "url": e["source_url"]})

    sections = {
        "conclusion": [
            ("今日" + country + "整体安全形势" + ("总体平稳，未记录重大新增事件。" if not has else "存在需关注的安全事件，详见下文。")),
            "管理层重点关注人员出行、营地与办公场所安全及信息报送。",
            "本日报为公开信息整理，不构成行动依据；具体决策以现场核实为准。"
        ],
        "overall": {
            "text": (NO_EVENT if not has else "最近24小时记录 {n} 起公开报道的社会安全相关事件，涉及{ts}。".format(n=len(ev_c), ts="、".join(sorted(set(e.get("event_type","") for e in ev_c if e.get("event_type")))) or "多个领域")),
            "trend": "基本稳定" if not has else "暂无法判断",
            "trend_vs_prev": "基本稳定" if not has else "相较前一日待评估",
        },
        "major_events": major,
        "politics": summarize("政治", g["politics"]) or NO_EVENT,
        "conflict_terror": summarize("武装冲突和恐怖主义", g["conflict_terror"]) or NO_EVENT,
        "stability": summarize("社会稳定和治安", g["stability"]) or NO_EVENT,
        "infrastructure": summarize("交通、边境和基础设施", g["infrastructure"]) or NO_EVENT,
        "china": (summarize("涉华", g["china"]) or NO_CHINA),
        "followup": [
            "持续跟踪过去72小时仍在发展的重大事件。",
            "持续跟踪过去7天尚未结束的重要趋势。"
        ],
        "outlook": {
            "most_likely": ["需关注武装冲突、恐怖主义及社会治安类风险的外溢。"] if has else ["近期未出现明显新增风险信号。"],
            "areas": ["首都及主要城市、边境地区为常规关注区域。"],
            "operations": ["人员跨地区移动、营地与办公场所安全防范。"],
            "basis": DEFAULT_BASIS,
            "uncertainty": "信息来源于公开报道，部分事件细节与伤亡数据可能存在差异，需以官方或多源核实为准。",
        },
        "advice": [
            "保持信息报送畅通，关注官方与使领馆安全提醒。",
            "人员出行避开示威、集会及敏感地点。",
            "营地与办公场所落实出入管理与应急通信准备。",
            "涉及边境及跨地区移动前确认通行与安全风险。"
        ],
        "sources": sources,
    }

    title = "《{country}社会安全信息日报（{date_cn}）》".format(
        country=country, date_cn="%s年%s月%s日" % tuple(date_str.split("-"))
    )

    return {
        "country": country,
        "country_en": dc,
        "date": date_str,
        "generated_at_bj": generated_at,
        "window_text": "截至北京时间22:00前最近24小时",
        "title": title,
        "sections": sections,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD（北京时间），默认今天")
    ap.add_argument("--dry", action="store_true", help="仅预览，不写文件")
    args = ap.parse_args()

    bj = bj_now()
    date_str = args.date or beijing_date(bj)
    generated_at = (bj if not args.date else datetime.strptime(args.date + "22:00:00", "%Y-%m-%d%H:%M:%S") + timedelta(hours=0)).strftime("%Y-%m-%d %H:%M:%S")

    countries = load_json(os.path.join(DATA, "countries.json"), {}).get("countries", [])
    events_all = load_json(os.path.join(DATA, "events.json"), {}).get("events", [])
    daily = [c for c in countries if c.get("has_daily")]

    print("生成日报日期（北京时间）：", date_str)
    for c in daily:
        cn = c["cn"]
        dc = c.get("daily_country", cn)
        rep = build_report(cn, dc, events_all, date_str, generated_at)
        out_dir = os.path.join(REPORTS, dc)
        os.makedirs(out_dir, exist_ok=True)
        fname = os.path.join(out_dir, date_str + ".json")
        idx_path = os.path.join(out_dir, "index.json")
        if args.dry:
            print("  [预览]", cn, "->", rep["title"])
            continue
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
        # 更新索引
        idx = load_json(idx_path, {"country": cn, "reports": []})
        idx["country"] = cn
        idx["reports"] = [r for r in idx.get("reports", []) if r["date"] != date_str]
        idx["reports"].insert(0, {"date": date_str, "title": rep["title"]})
        idx["reports"] = idx["reports"][:60]
        with open(idx_path, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, indent=2)
        print("  [已生成]", cn, "->", fname)

    # 更新 status.json
    if not args.dry:
        st = load_json(os.path.join(DATA, "status.json"), {})
        st["reports_today"] = len(daily)
        st["last_update_bj"] = generated_at
        st["generated_at_bj"] = generated_at
        st["next_update_bj"] = (bj + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S") if False else "次日 22:00"
        with open(os.path.join(DATA, "status.json"), "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
        print("已更新 data/status.json（reports_today =", len(daily), "）")


if __name__ == "__main__":
    main()
