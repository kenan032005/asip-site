#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASIP 国别日报生成器（Stage-1：真实北京时间 24h 窗口 + 自动目标日期）。

窗口：目标日期前一日北京时间 22:00 → 目标日期当日北京时间 22:00。
目标日期自动计算：
  - 北京时间 < 22:00 → 前一天（其窗口已完整结束）
  - 北京时间 >= 22:00 → 当天（其窗口刚结束）

用法：
  python scripts/generate_reports.py [--date YYYY-MM-DD] [--run-id ID] [--dry]
  （不传 --date 时由 get_latest_completed_report_date 自动决定）
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pipeline_core import (
    TZ_BEIJING, bj_now, parse_time, get_latest_completed_report_date,
)

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
REPORTS = os.path.join(ROOT, "reports")

NO_EVENT = "过去24小时未发现经多源核实的重大新增事件。"
NO_CHINA = "过去24小时未发现经可靠来源证实的涉中国企业或中国公民重大社会安全事件。"
DEFAULT_BASIS = "基于北京时间前一日22:00至当日22:00公开来源信息整理；结论随后续核实可能调整。"


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def beijing_date(d):
    return d.strftime("%Y-%m-%d")


def to_bj(dt_utc_iso):
    """UTC/带偏移 ISO -> 北京时间 naive datetime；失败返回 None。"""
    if not dt_utc_iso:
        return None
    s = dt_utc_iso.strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            return dt.astimezone(TZ_BEIJING).replace(tzinfo=None)
        return dt
    except ValueError:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d")
        except ValueError:
            return None


GROUP_MAP = {
    "political_crisis": "politics", "election_security": "politics",
    "terrorist_attack": "conflict_terror", "military_operation": "conflict_terror",
    "armed_conflict": "conflict_terror",
    "protest": "stability", "strike": "stability", "civil_unrest": "stability",
    "kidnapping": "stability", "serious_crime": "stability",
    "communal_conflict": "stability", "border_security": "stability",
    "transport_disruption": "infrastructure", "infrastructure_security": "infrastructure",
    "natural_disaster": "infrastructure", "public_health": "infrastructure",
}
GROUP_CN = {
    "politics": "政治", "conflict_terror": "武装冲突与恐怖主义",
    "stability": "社会稳定与治安", "infrastructure": "公共卫生、灾害与基础设施",
    "china": "涉华",
}


def event_groups(events):
    g = {"politics": [], "conflict_terror": [], "stability": [], "infrastructure": [], "china": []}
    for e in events:
        grp = GROUP_MAP.get(e.get("event_type", ""))
        if grp:
            g[grp].append(e)
        if e.get("china_related") or e.get("involves_china"):
            g["china"].append(e)
    return g


def summarize(group_name, evs):
    if not evs:
        return None
    lines = ["· " + (e.get("title_cn") or e.get("title_original") or "") for e in evs[:6]]
    return "记录 {n} 起相关事件：\n".format(n=len(evs)) + "\n".join(lines)


def build_report(country, dc, events_all, date_str, generated_at, generated_at_iso, win_start, win_end, run_id):
    ev_c = [e for e in events_all if e.get("country") == country and not e.get("is_demo")]
    new_events, ongoing = [], []
    for e in ev_c:
        bj = to_bj(e.get("event_time") or e.get("published_time"))
        if bj is None:
            ongoing.append(e)
            continue
        if win_start <= bj <= win_end:
            new_events.append(e)
        else:
            ongoing.append(e)
    g = event_groups(new_events)
    has = len(new_events) > 0

    major = []
    for e in sorted(new_events, key=lambda x: x.get("published_time", ""), reverse=True)[:6]:
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
    for e in new_events:
        if e.get("source_name") and e.get("source_url") and e["source_url"] != "#":
            sources.append({"name": e["source_name"], "title": e.get("title_original", ""), "url": e["source_url"]})

    verified_n = sum(1 for e in new_events if e.get("verification_status") in ("cross_verified", "verified"))
    pending_n = len(new_events) - verified_n

    sections = {
        "conclusion": [
            ("今日" + country + "整体安全形势" + ("总体平稳，未记录重大新增事件。" if not has else "存在需关注的安全事件，详见下文。")),
            "管理层重点关注人员出行、营地与办公场所安全及信息报送。",
            "本日报为公开信息整理，不构成行动依据；具体决策以现场核实为准。",
        ],
        "overall": {
            "text": (NO_EVENT if not has else "最近24小时（北京时间前一日22:00至当日22:00）记录 {n} 起公开报道的社会安全相关事件，涉及{ts}。".format(
                n=len(new_events),
                ts="、".join(sorted(set(GROUP_CN.get(GROUP_MAP.get(e.get("event_type", ""), ""), "") for e in new_events if e.get("event_type")) - {""}) or ["多个领域"]))),
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
            "持续跟踪过去72小时仍在发展的重大事件（见持续跟踪项）。",
            "持续跟踪过去7天尚未结束的重要趋势。",
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
            "涉及边境及跨地区移动前确认通行与安全风险。",
        ],
        "sources": sources,
    }

    title = "《{country}社会安全信息日报（{date_cn}）》".format(
        country=country, date_cn="%s年%s月%s日" % tuple(date_str.split("-")))

    return {
        "country": country,
        "country_en": dc,
        "date": date_str,
        "run_id": run_id,
        "pipeline_version": 2,
        "generated_at_bj": generated_at,            # 显示用：YYYY-MM-DD HH:MM:SS（北京）
        "generated_at_bj_iso": generated_at_iso,    # 机器校验用：带 +08:00
        "reporting_window_start": win_start.strftime("%Y-%m-%d %H:%M"),
        "reporting_window_end": win_end.strftime("%Y-%m-%d %H:%M"),
        "new_event_count": len(new_events),
        "ongoing_event_count": len(ongoing),
        "pending_event_count": pending_n,
        "verified_event_count": verified_n,
        "window_text": "北京时间前一日22:00至当日22:00（24小时）",
        "title": title,
        "sections": sections,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD（北京时间目标日期，默认自动计算）")
    ap.add_argument("--run-id", help="指定 run_id 写入日报")
    ap.add_argument("--dry", action="store_true", help="仅预览")
    args = ap.parse_args()

    bj = bj_now()
    if args.date:
        date_str = args.date
        print(f"[generate_reports] 使用 --date={date_str}（补生成模式）")
    else:
        target = get_latest_completed_report_date(bj)
        date_str = beijing_date(target)
        print(f"[generate_reports] 自动目标日期={date_str}（当前北京时间 {bj.strftime('%H:%M:%S')}）")

    # 窗口：目标日期 22:00 结束，前一日 22:00 开始
    base = datetime.strptime(date_str, "%Y-%m-%d")
    win_end = base.replace(hour=22, minute=0, second=0, microsecond=0)
    win_start = win_end - timedelta(hours=24)
    generated_at = bj.strftime("%Y-%m-%d %H:%M:%S")
    generated_at_iso = datetime.now(TZ_BEIJING).isoformat()

    # ── 硬性窗口校验：reporting_window_end 必须 <= generated_at ──
    # 以北京时间比较（两者均为北京墙钟）
    if win_end > bj:
        print(f"⛔ 严重错误：统计窗口结束 {win_end} 晚于当前生成时间 {bj}。构建已阻止。")
        return 1

    run_id = args.run_id or ""
    countries = load_json(os.path.join(DATA, "countries.json"), {}).get("countries", [])
    events_all = load_json(os.path.join(DATA, "events.json"), {}).get("events", [])
    daily = [c for c in countries if c.get("has_daily")]

    print("日报日期（北京）：", date_str, "窗口：", win_start, "→", win_end)
    any_written = False
    for c in daily:
        cn = c["cn"]
        dc = c.get("daily_country", cn)
        rep = build_report(cn, dc, events_all, date_str, generated_at, generated_at_iso, win_start, win_end, run_id)
        out_dir = os.path.join(REPORTS, dc)
        os.makedirs(out_dir, exist_ok=True)
        fname = os.path.join(out_dir, date_str + ".json")
        idx_path = os.path.join(out_dir, "index.json")
        if args.dry:
            print("  [预览]", cn, "新增=", rep["new_event_count"], "持续跟踪=", rep["ongoing_event_count"])
            continue
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
        idx = load_json(idx_path, {"country": cn, "reports": []})
        idx["country"] = cn
        idx["reports"] = [r for r in idx.get("reports", []) if r["date"] != date_str]
        idx["reports"].insert(0, {"date": date_str, "title": rep["title"], "run_id": run_id})
        idx["reports"] = idx["reports"][:60]
        with open(idx_path, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, indent=2)
        print("  [生成]", cn, "新增=", rep["new_event_count"], "持续跟踪=", rep["ongoing_event_count"])
        any_written = True

    if any_written:
        print(f"✅ 日报已生成（目标日期 {date_str}，窗口 {win_start} → {win_end}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
