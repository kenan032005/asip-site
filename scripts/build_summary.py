#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_summary.py —— Stage-2 首页摘要与运行状态生成器（零依赖，真实统计）。

数据来源（Stage-2 最终收尾）：唯一读取 data/public/published_events.json 与
data/public/current_metrics.json（Canonical→Public 单向生成）。
不再读取 data/events.json 等遗留事件池；统计仅计 current_policy_passed=true 的
当前政策通过事件，历史迁移保留事件（legacy_migration_preserved）保留展示但
不计入 24h/7d/首页统计。

生成：
  1. data/status.json        —— 完整 pipeline 运行状态（真实统计）
  2. data/latest-summary.json —— 首页概览

用法：
  python scripts/build_summary.py [--run-id <run_id>]
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pipeline_core import (
    PIPELINE_VERSION, DATA_DIR, STAGE1_COUNTRIES,
    bj_now, bj_iso, bj_format, bj_24h_ago, bj_7d_ago, parse_time,
    generate_run_id, create_pipeline_meta, passes_stage1_gate,
    calculate_public_statistics, compute_source_statistics,
    _is_current_event, load_json, save_json,
    event_type_cn, normalize_event_type,
    FIXED_RISK_LEVELS, TZ_BEIJING,
)
# Stage-2 最终收尾：sources.json 2.0 展开工具（信源统计仍读信源配置）
from data.migrate_stage2 import _unwrap_source
ROOT = os.path.dirname(HERE)
REPORTS_DIR = os.path.join(ROOT, "reports")
PUBLIC_DIR = os.path.join(DATA_DIR, "public")


def load_published():
    """Stage-2：唯一事件数据来源 —— data/public/published_events.json。"""
    doc = load_json(os.path.join(PUBLIC_DIR, "published_events.json"), {"items": []})
    out = []
    for p in doc.get("items", []):
        v = dict(p)
        # 公开模型 country=ISO2 / country_cn=中文；统计与展示统一用中文国名
        v["country"] = p.get("country_cn", "") or p.get("country", "")
        out.append(v)
    return out


def load_public_metrics():
    return load_json(os.path.join(PUBLIC_DIR, "current_metrics.json"), {}) or {}


def load_sources():
    """读取信源。Stage-2 升级后 sources.json 为 2.0 格式（运行字段在
    legacy_payload 内），此处展开为运行视图供统计使用。"""
    recs = load_json(os.path.join(DATA_DIR, "sources.json"), {"sources": []}).get("sources", [])
    out = []
    for r in recs:
        op = _unwrap_source(r)
        # 顶层 enabled/tested 优先（升级记录维护于顶层）
        if "enabled" in r:
            op["enabled"] = r.get("enabled")
        if "tested" in r:
            op["tested"] = r.get("tested")
        out.append(op)
    return out


def load_countries():
    return load_json(os.path.join(DATA_DIR, "countries.json"), {"countries": []}).get("countries", [])


def sev_rank(e):
    return {"极高": 4, "高": 3, "中": 2, "低": 1}.get(e.get("event_severity"), 0)


def build_status(events, pending_count, quarantine_count, sources, run_id, pipeline_meta, stats, src_stats):
    """按 Stage-1 规范生成 status.json（真实统计）。"""
    now = bj_now()
    now_str = bj_format(now)
    now_iso = bj_iso()

    countries = load_countries()
    extreme = sum(1 for c in countries if (c.get("risk_level") or c.get("country_risk_level") or 0) >= 4)

    # 日报统计：当天（北京时间）是否已生成
    reports_today = 0
    today_str = now.strftime("%Y-%m-%d")
    for c in countries:
        if not c.get("has_daily"):
            continue
        dc = c.get("daily_country", c.get("cn", ""))
        idx = load_json(os.path.join(REPORTS_DIR, dc, "index.json"), {"reports": []})
        if any(r.get("date") == today_str for r in idx.get("reports", [])):
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
        "next_scheduled_update_beijing": (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S") + "（每2小时自动更新）",
        # 统一统计（与 latest-summary 共用 calculate_public_statistics）
        "events_24h": stats["events_24h"],
        "events_7d": stats["events_7d"],
        "chad_events_24h": stats["chad_events_24h"],
        "niger_events_24h": stats["niger_events_24h"],
        "chad_events_7d": stats["chad_events_7d"],
        "niger_events_7d": stats["niger_events_7d"],
        "current_event_count": stats["current_event_count"],
        "published_event_count": stats["published_event_count"],
        "pending_event_count": pending_count,
        "quarantine_event_count": quarantine_count,
        # 信息源真实运行统计（不再把 enabled 当 success）
        "source_configured_count": src_stats["source_configured_count"],
        "source_enabled_count": src_stats["source_enabled_count"],
        "source_tested_count": src_stats["source_tested_count"],
        "source_request_success_count_last_run": src_stats["source_request_success_count_last_run"],
        "source_with_articles_count_last_run": src_stats["source_with_articles_count_last_run"],
        "source_with_relevant_articles_count_last_run": src_stats["source_with_relevant_articles_count_last_run"],
        "source_failed_count_last_run": src_stats["source_failed_count_last_run"],
        "source_degraded_count": src_stats["source_degraded_count"],
        "source_rate_limited_count_last_run": src_stats["source_rate_limited_count_last_run"],
        "source_blocked_count": src_stats["source_blocked_count"],
        "source_requires_api_count": src_stats["source_requires_api_count"],
        "extreme_risk_country_count": extreme,
        "reports_today": reports_today,
        "timezone": "Asia/Shanghai",
        "timezone_label": "北京时间（UTC+8）",
        "source_commit": pipeline_meta.get("source_commit", ""),
        "deployment_commit": pipeline_meta.get("deployment_commit", ""),
        "warnings": [],
        "note": "Stage 2：仅统计 current_policy_passed=true 的当前政策通过事件；历史迁移保留事件不计入统计",
    }
    return status


def build_summary(events, run_id, status, stats):
    """生成 latest-summary.json。仅使用 pv2 + 闸门 的当前有效事件。"""
    now = bj_now()
    now_str = bj_format(now)
    cut24 = bj_24h_ago()
    cut7 = bj_7d_ago()

    # 当前政策通过事件（仅 current_policy_passed=true 计入统计）
    current = [e for e in events if e.get("current_policy_passed") is True and _is_current_event(e)]
    stage1 = [e for e in current if passes_stage1_gate(e)]
    stage1_24h = sum(1 for e in stage1 if cut24 <= (parse_time(e.get("published_time") or e.get("event_time") or "") or datetime.min) <= now)

    # 可见事件（历史迁移保留事件 legacy_visibility=true 仍保留展示，但不计入统计）
    visible = [e for e in events if e.get("legacy_visibility", True)]

    # 高风险事件（展示列表，含历史保留事件；不标注为通过质量闸门）
    high = sorted(
        [e for e in visible if (e.get("country_risk_level") or 0) >= 3],
        key=lambda e: (sev_rank(e), e.get("published_time", "")), reverse=True,
    )[:12]

    # 最新事件（展示列表，含历史保留事件）
    latest = sorted(visible, key=lambda e: e.get("published_time", ""), reverse=True)[:15]

    # 涉华事件（展示列表）
    china = [e for e in visible if e.get("china_related") or e.get("involves_china")]

    if stage1_24h == 0:
        overview = [
            "过去24小时内，乍得和尼日尔通过新版质量闸门的有效动态数量较少，系统仍在持续采集。",
        ]
    else:
        overview_items = []
        for e in stage1[:3]:
            title = e.get("title_cn") or e.get("title_original", "")
            country = e.get("country", "")
            etype = event_type_cn(normalize_event_type(e.get("event_type", "")))
            if title:
                overview_items.append(f"【{country}·{etype}】{title[:80]}")
        overview = overview_items if overview_items else ["系统持续监测中。"]

    # 最新日报索引
    latest_reports = []
    countries = load_countries()
    for c in countries:
        if not c.get("has_daily"):
            continue
        dc = c.get("daily_country", c.get("cn", ""))
        idx = load_json(os.path.join(REPORTS_DIR, dc, "index.json"), {"reports": []})
        reps = idx.get("reports", [])
        if reps:
            r = reps[0]
            latest_reports.append({"country": c.get("cn", ""), "date": r.get("date", ""), "title": r.get("title", "")})

    risk_by_country = []
    for c in countries:
        risk = c.get("risk_level") or c.get("country_risk_level") or 0
        cn = c.get("cn", "")
        if risk >= 3:
            cnt = sum(1 for e in stage1 if e.get("country") == cn) if cn in STAGE1_COUNTRIES else 0
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
        "generated_at_bj_iso": datetime.now(TZ_BEIJING).isoformat(),
        "window_start_bj": cut24.strftime("%Y-%m-%d %H:%M:%S"),
        "window_end_bj": now_str,
        "overall_risk": 4,
        "overall_risk_name": "极高",
        "trend_vs_prev": "监测中",
        "overview": overview,
        "metrics": [
            {"label": "监测国家", "value": str(len(countries)), "link": "countries.html"},
            {"label": "近7日事件", "value": str(stats["events_7d"]), "link": "events.html"},
            {"label": "近24小时事件", "value": str(stats["events_24h"]), "link": "events.html"},
            {"label": "极高风险国", "value": str(status.get("extreme_risk_country_count", 8)), "link": "countries.html"},
            {"label": "今日日报", "value": str(len(latest_reports)), "link": "reports.html"},
        ],
        "high_risk_events": high,
        "latest_events": latest,
        "china_related": china,
        "risk_by_country": risk_by_country,
        "latest_reports": latest_reports,
        "note": "Stage 2：数据来自 Canonical→Public 单向导出；统计仅计 current_policy_passed=true 事件，历史迁移保留事件仅展示不计入统计",
    }
    return summary


def main(run_id=None, dry_run=False):
    if run_id is None:
        run_id = generate_run_id()
    pipeline_meta = create_pipeline_meta(run_id)
    pipeline_meta["data_generated_at"] = bj_iso()

    # Stage-2 最终收尾：唯一事件来源为 Public 导出（Canonical→Public 单向）
    events = load_published()
    metrics = load_public_metrics()
    pending_count = int(metrics.get("pending_articles") or 0)
    quarantine_count = int(metrics.get("quarantine") or 0)
    sources = load_sources()

    print(f"[build_summary] run_id={run_id} pipeline_version={PIPELINE_VERSION}")
    print(f"  public events: {len(events)}, pending_articles: {pending_count}, "
          f"quarantine: {quarantine_count}, sources: {len(sources)}")

    # 统一统计（status 与 summary 共用；仅当前政策通过事件计入）
    current_events = [e for e in events if e.get("current_policy_passed") is True]
    stats = calculate_public_statistics(current_events)
    stats["published_event_count"] = len(events)
    src_stats = compute_source_statistics(sources)
    n_hist = sum(1 for e in events if e.get("legacy_migration_preserved"))
    print(f"  统计: 24h={stats['events_24h']} 7d={stats['events_7d']} chad24h={stats['chad_events_24h']} niger24h={stats['niger_events_24h']} current={stats['current_event_count']} 历史保留={n_hist}")
    print(f"  信源: configured={src_stats['source_configured_count']} enabled={src_stats['source_enabled_count']} success_last_run={src_stats['source_request_success_count_last_run']} rate_limited={src_stats['source_rate_limited_count_last_run']}")

    status = build_status(events, pending_count, quarantine_count, sources, run_id, pipeline_meta, stats, src_stats)
    summary = build_summary(events, run_id, status, stats)

    # 校验一致性
    s24 = int([m["value"] for m in summary["metrics"] if "24小时" in m["label"]][0])
    s7 = int([m["value"] for m in summary["metrics"] if "7日" in m["label"]][0])
    if status["events_24h"] != s24:
        status["warnings"].append(f"24h status({status['events_24h']}) != summary({s24})")
        print(f"  ⚠ 24h 不一致: status={status['events_24h']} summary={s24}")
    if status["events_7d"] != s7:
        status["warnings"].append(f"7d status({status['events_7d']}) != summary({s7})")
        print(f"  ⚠ 7d 不一致: status={status['events_7d']} summary={s7}")

    if dry_run:
        print("[dry_run] 不写入文件。")
        return run_id

    # Stage-2 最终收尾：build_summary 只生成站点状态文件，
    # canonical/legacy 的修正统一由 apply_publication_semantics + compatibility_export 完成。
    save_json(os.path.join(DATA_DIR, "status.json"), status)
    save_json(os.path.join(DATA_DIR, "latest-summary.json"), summary)
    print(f"  status.json: 24h={status['events_24h']}, 7d={status['events_7d']}, src_success_last_run={status['source_request_success_count_last_run']}")
    print(f"  latest-summary.json: 24h={s24}, 7d={s7}, risk_countries={len(summary['risk_by_country'])}")
    return run_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage-1 构建 status + summary")
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rid = main(run_id=args.run_id, dry_run=args.dry_run)
    print(f"\nDone. run_id: {rid}")
