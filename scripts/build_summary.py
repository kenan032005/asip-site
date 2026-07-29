#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_summary.py —— Stage-1 首页摘要与运行状态生成器（零依赖）。

从 data/events.json、data/countries.json、data/pending_events.json、
data/quarantine_events.json 与 reports/ 日报索引汇总数据，生成：
  1. data/status.json     —— 完整的 pipeline 运行状态
  2. data/latest-summary.json —— 首页概览摘要（仅 pipeline_version=2 数据）

用法：
  python scripts/build_summary.py [--run-id <run_id>]

不传 --run-id 时自动生成。由 pipeline runner 在数据生成后调用。
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone

# 将 scripts/ 加入 Python 搜索路径以便 import pipeline_core
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pipeline_core import (
    PIPELINE_VERSION, DATA_DIR, STAGE1_COUNTRIES,
    bj_now, bj_iso, bj_format, bj_24h_ago, bj_7d_ago, parse_time,
    generate_run_id, create_pipeline_meta, passes_stage1_gate,
    count_events_24h, count_events_7d, load_json, save_json,
    event_type_cn, normalize_event_type,
    FIXED_RISK_LEVELS,
)
ROOT = os.path.dirname(HERE)
REPORTS_DIR = os.path.join(ROOT, "reports")

# ── 数据加载 ──────────────────────────────────────────────

def load_events():
    """加载 events.json，返回事件列表。"""
    doc = load_json(os.path.join(DATA_DIR, "events.json"), {"events": []})
    return doc.get("events", [])


def load_pending():
    """加载 pending_events.json，返回条目列表。"""
    doc = load_json(os.path.join(DATA_DIR, "pending_events.json"), {"items": []})
    return doc.get("items", [])


def load_quarantine():
    """加载 quarantine_events.json，返回条目列表。"""
    doc = load_json(os.path.join(DATA_DIR, "quarantine_events.json"), {"items": []})
    return doc.get("items", [])


def load_sources():
    """加载 sources.json。"""
    doc = load_json(os.path.join(DATA_DIR, "sources.json"), {"sources": []})
    return doc.get("sources", [])


def load_countries():
    """加载 countries.json。"""
    doc = load_json(os.path.join(DATA_DIR, "countries.json"), {"countries": []})
    return doc.get("countries", [])


# ── 时间窗口计数（修复版：正确处理解析失败）───────────────

def count_events_in_window(events, cutoff, now, country=None):
    """统计 published_time 在 [cutoff, now] 内的事件。解析失败则跳过（不算）。"""
    cnt = 0
    for e in events:
        if country is not None and e.get("country") != country:
            continue
        t = e.get("published_time") or e.get("event_time") or e.get("created_at") or ""
        dt = parse_time(t)
        if dt is None:
            continue
        if cutoff <= dt <= now:
            cnt += 1
    return cnt


# ── 事件严重度排序 ────────────────────────────────────────

def sev_rank(e):
    return {"极高": 4, "高": 3, "中": 2, "低": 1}.get(e.get("event_severity"), 0)


# ── 构建 status.json ──────────────────────────────────────

def build_status(events, pending, quarantine, sources, run_id, pipeline_meta):
    """按 Stage-1 规范生成 status.json。"""
    now = bj_now()
    now_str = bj_format(now)
    now_iso = bj_iso()

    # 全量统计
    total_24h = count_events_in_window(events, bj_24h_ago(), now)
    total_7d = count_events_in_window(events, bj_7d_ago(), now)

    # Stage-1 国家单独统计（仅 pipeline_version=2）
    stage1_events = [e for e in events if passes_stage1_gate(e)]
    stage1_24h = count_events_in_window(stage1_events, bj_24h_ago(), now)
    stage1_7d = count_events_in_window(stage1_events, bj_7d_ago(), now)

    # 乍得/尼日尔单独统计
    chad_events = [e for e in stage1_events if e.get("country") == "乍得"]
    niger_events = [e for e in stage1_events if e.get("country") == "尼日尔"]
    chad_24h = count_events_in_window(chad_events, bj_24h_ago(), now)
    niger_24h = count_events_in_window(niger_events, bj_24h_ago(), now)

    # 来源统计
    src_success = sum(1 for s in sources if s.get("status") == "ok" or s.get("enabled"))
    src_failure = sum(1 for s in sources if s.get("status") in ("failed", "error") and s.get("enabled"))

    # 风险国家统计
    countries = load_countries()
    extreme = sum(1 for c in countries if (c.get("risk_level") or c.get("country_risk_level") or 0) >= 4)

    # 日报统计
    daily_countries = [c for c in countries if c.get("has_daily")]
    reports_today = 0
    today_str = now.strftime("%Y-%m-%d")
    for c in daily_countries:
        dc = c.get("daily_country", c.get("cn", ""))
        rpath = os.path.join(REPORTS_DIR, dc, f"{today_str}.json")
        if os.path.exists(rpath):
            reports_today += 1

    status = {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": run_id,
        "status": "success",
        "status_cn": "数据更新成功",
        "run_started_at": pipeline_meta.get("run_started_at", ""),
        "data_generated_at": now_iso,
        "build_completed_at": "",
        "deploy_completed_at": "",
        "last_updated_beijing": now_str,
        "next_scheduled_update_beijing": f"{(now + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')}（每2小时自动更新）",
        "events_24h": total_24h,
        "events_7d": total_7d,
        "chad_events_24h": chad_24h,
        "niger_events_24h": niger_24h,
        "published_event_count": len(events),
        "pending_event_count": len(pending),
        "quarantine_event_count": len(quarantine),
        "source_success_count": src_success,
        "source_failure_count": src_failure,
        "stage1_event_count": len(stage1_events),
        "extreme_risk_country_count": extreme,
        "reports_today": reports_today,
        "timezone": "Asia/Shanghai",
        "timezone_label": "北京时间（UTC+8）",
        "source_commit": pipeline_meta.get("source_commit", ""),
        "deployment_commit": pipeline_meta.get("deployment_commit", ""),
        "warnings": [],
        "note": "Stage 1 主链路重建：pipeline_version=2 仅统计乍得/尼日尔通过质量闸门事件",
    }

    return status


# ── 构建 latest-summary.json ──────────────────────────────

def build_summary(events, run_id, status):
    """按 Stage-1 规范生成 latest-summary.json。仅使用 pipeline_version=2 数据。"""
    now = bj_now()
    now_str = bj_format(now)
    cut24 = bj_24h_ago()
    cut7 = bj_7d_ago()

    # 全量 events 用于非 stage1 国家的历史数据显示
    # stage1_events 仅用于乍得/尼日尔当前统计
    stage1_events = [e for e in events if passes_stage1_gate(e)]

    # 全量 24h/7d 统计
    total_24h = count_events_in_window(events, cut24, now)
    total_7d = count_events_in_window(events, cut7, now)
    stage1_24h = count_events_in_window(stage1_events, cut24, now)

    # 高风险事件（全量，按严重度/top12）
    high = sorted(
        [e for e in events if (e.get("country_risk_level") or 0) >= 3],
        key=lambda e: (sev_rank(e), e.get("published_time", "")),
        reverse=True,
    )[:12]

    # 最新事件（全量，top15）
    latest = sorted(events, key=lambda e: e.get("published_time", ""), reverse=True)[:15]

    # 涉华事件
    china = [e for e in events if e.get("china_related") or e.get("involves_china")]

    # 概览（Stage 1 不再使用硬编码文本，统计有效数据后自动生成或使用缺省文案）
    if stage1_24h == 0:
        overview = [
            "过去24小时内，乍得和尼日尔通过新版质量闸门的有效动态数量较少，系统仍在持续采集。",
        ]
    else:
        # 用前几条事件标题拼接简要概览
        overview_items = []
        for e in stage1_events[:3]:
            title = e.get("title_cn") or e.get("title_original", "")
            country = e.get("country", "")
            etype = event_type_cn(normalize_event_type(e.get("event_type", "")))
            if title:
                overview_items.append(f"【{country}·{etype}】{title[:80]}")
        overview = overview_items if overview_items else ["系统持续监测中。"]

    # 最新日报索引
    latest_reports = []
    countries = load_countries()
    daily = [c for c in countries if c.get("has_daily")]
    for c in daily:
        dc = c.get("daily_country", c.get("cn", ""))
        idx = load_json(os.path.join(REPORTS_DIR, dc, "index.json"), {"reports": []})
        reps = idx.get("reports", [])
        if reps:
            r = reps[0]
            latest_reports.append({
                "country": c.get("cn", ""),
                "date": r.get("date", ""),
                "title": r.get("title", ""),
            })

    # 风险国家汇总
    risk_by_country = []
    for c in countries:
        risk = c.get("risk_level") or c.get("country_risk_level") or 0
        cn = c.get("cn", "")
        if risk >= 3:
            cnt = sum(1 for e in stage1_events if e.get("country") == cn) if cn in STAGE1_COUNTRIES else 0
            risk_by_country.append({
                "country": cn,
                "risk_level": risk,
                "risk_label": "极高" if risk >= 4 else ("高" if risk >= 3 else "中"),
                "stage1_recent": cnt,
            })

    summary = {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": run_id,
        "generated_at_bj": now_str,
        "window_start_bj": cut24.strftime("%Y-%m-%d %H:%M:%S"),
        "window_end_bj": now_str,
        "overall_risk": 4,
        "overall_risk_name": "极高",
        "trend_vs_prev": "监测中",
        "overview": overview,
        "metrics": [
            {"label": "监测国家", "value": str(len(countries)), "link": "countries.html"},
            {"label": "近7日事件", "value": str(total_7d), "link": "events.html"},
            {"label": "近24小时事件", "value": str(total_24h), "link": "events.html"},
            {"label": "极高风险国", "value": str(status.get("extreme_risk_country_count", 8)), "link": "countries.html"},
            {"label": "今日日报", "value": str(len(latest_reports)), "link": "reports.html"},
        ],
        "high_risk_events": high,
        "latest_events": latest,
        "china_related": china,
        "risk_by_country": risk_by_country,
        "latest_reports": latest_reports,
        "note": "Stage 1 主链路重建：乍得/尼日尔仅使用 pipeline_version=2 且通过质量闸门的数据",
    }

    return summary


# ── 修复风险等级 ──────────────────────────────────────────

def fix_risk_levels(events):
    """确保乍得/尼日尔事件固定 risk_level=4。返回修正数量。"""
    fixed = 0
    for e in events:
        country = e.get("country", "")
        if country in FIXED_RISK_LEVELS:
            target = FIXED_RISK_LEVELS[country]["country_risk_level"]
            current = e.get("country_risk_level")
            if current != target:
                e["country_risk_level"] = target
                e["country_risk_label"] = FIXED_RISK_LEVELS[country]["country_risk_label"]
                fixed += 1
            # 也确保 risk_label 一致
            elif e.get("country_risk_label") != FIXED_RISK_LEVELS[country]["country_risk_label"]:
                e["country_risk_label"] = FIXED_RISK_LEVELS[country]["country_risk_label"]
                fixed += 1
    return fixed


# ── 主入口 ────────────────────────────────────────────────

def main(run_id=None, dry_run=False):
    """构建 status.json + latest-summary.json + 修复风险等级。"""

    if run_id is None:
        run_id = generate_run_id()
    pipeline_meta = create_pipeline_meta(run_id)
    pipeline_meta["data_generated_at"] = bj_iso()

    # 加载数据
    events = load_events()
    pending = load_pending()
    quarantine = load_quarantine()
    sources = load_sources()

    print(f"[build_summary] run_id={run_id} pipeline_version={PIPELINE_VERSION}")
    print(f"  events: {len(events)}, pending: {len(pending)}, quarantine: {len(quarantine)}")

    # 修复风险等级
    risk_fixed = fix_risk_levels(events)
    if risk_fixed:
        print(f"  风险等级修正: {risk_fixed} 条 -> level=4（乍得/尼日尔）")

    # 将事件统一标准化为英文事件类型代码（向后兼容）
    type_normalized = 0
    for e in events:
        old_type = e.get("event_type", "")
        new_type = normalize_event_type(old_type)
        if new_type != old_type:
            e["event_type"] = new_type
            type_normalized += 1
    if type_normalized:
        print(f"  事件类型标准化: {type_normalized} 条 -> 英文枚举代码")

    # 构建 status.json
    status = build_status(events, pending, quarantine, sources, run_id, pipeline_meta)

    # 构建 latest-summary.json
    summary = build_summary(events, run_id, status)

    # 校验
    status_24h = status["events_24h"]
    summary_24h = int([m["value"] for m in summary["metrics"] if "24小时" in m["label"]][0])
    if status_24h != summary_24h:
        print(f"  ⚠ 警告: status 24h={status_24h} != summary 24h={summary_24h}")
        status["warnings"].append("24h mismatch between status and summary")

    status_7d = status["events_7d"]
    summary_7d = int([m["value"] for m in summary["metrics"] if "7日" in m["label"]][0])
    if status_7d != summary_7d:
        print(f"  ⚠ 警告: status 7d={status_7d} != summary 7d={summary_7d}")
        status["warnings"].append("7d mismatch between status and summary")

    if dry_run:
        print("[dry_run] 不写入文件。")
        return run_id

    # 写入 events.json（风险等级和事件类型可能已修正）
    events_doc = load_json(os.path.join(DATA_DIR, "events.json"), {"version": 1})
    events_doc["events"] = events
    events_doc["pipeline_version"] = PIPELINE_VERSION
    events_doc["run_id"] = run_id
    events_doc["updated_at"] = bj_iso()
    save_json(os.path.join(DATA_DIR, "events.json"), events_doc)

    # 写入 status.json
    save_json(os.path.join(DATA_DIR, "status.json"), status)
    print(f"  status.json: status={status['status']}, 24h={status_24h}, 7d={status_7d}")

    # 写入 latest-summary.json
    save_json(os.path.join(DATA_DIR, "latest-summary.json"), summary)
    print(f"  latest-summary.json: 24h={summary_24h}, 7d={summary_7d}, risk={len(summary['risk_by_country'])}")

    return run_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage-1 构建 status + summary")
    parser.add_argument("--run-id", type=str, default=None, help="指定 run_id（不指定则自动生成）")
    parser.add_argument("--dry-run", action="store_true", help="仅计算不写入")
    args = parser.parse_args()
    rid = main(run_id=args.run_id, dry_run=args.dry_run)
    print(f"\nDone. run_id: {rid}")
