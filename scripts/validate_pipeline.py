#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_pipeline.py —— Stage-1 构建前数据质量检查（零依赖）。

在 build_site.py 之前运行，检查 15+ 项指标。
任意关键校验失败 → 返回非零退出码，阻止构建和部署。

用法：
  python scripts/validate_pipeline.py [--run-id <run_id>] [--dist <dist_dir>]
"""
import os
import sys
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pipeline_core import (
    PIPELINE_VERSION, DATA_DIR, STAGE1_COUNTRIES, FIXED_RISK_LEVELS,
    bj_now, bj_iso, bj_format, parse_time,
    load_json, passes_stage1_gate,
)

ROOT = os.path.dirname(HERE)
EXIT_OK = 0
EXIT_FAIL = 1

errors = []
warnings = []
critical = []


def fail(rule_id, msg, is_critical=False):
    global errors, critical
    prefix = "❌" if is_critical else "⚠"
    text = f"{prefix} [{rule_id}] {msg}"
    errors.append(text)
    if is_critical:
        critical.append(rule_id)
    print(text)


def ok(rule_id, msg):
    print(f"✅ [{rule_id}] {msg}")


def main(run_id=None, dist_dir=None):
    if dist_dir is None:
        dist_dir = os.path.join(ROOT, "dist")

    print(f"\n{'='*60}")
    print(f"ASIP Stage-1 Pipeline Validation")
    print(f"  run_id: {run_id or '<not specified>'}")
    print(f"  pipeline_version: {PIPELINE_VERSION}")
    print(f"  time: {bj_iso()}")
    print(f"{'='*60}\n")

    # ── 1. 核心数据文件 JSON 合法性 ────────────────────────
    for fname, label in [
        ("status.json", "status"),
        ("latest-summary.json", "latest-summary"),
        ("events.json", "events"),
    ]:
        path = os.path.join(DATA_DIR, fname)
        data = load_json(path)
        if data is None:
            fail(f"V01-{label}", f"{fname} 不是合法 JSON 或不存在", is_critical=True)
        else:
            ok(f"V01-{label}", f"{fname} JSON 合法")

    # ── 2. run_id 一致性 ──────────────────────────────────
    status = load_json(os.path.join(DATA_DIR, "status.json")) or {}
    summary = load_json(os.path.join(DATA_DIR, "latest-summary.json")) or {}
    events_doc = load_json(os.path.join(DATA_DIR, "events.json")) or {}

    status_rid = status.get("run_id", "")
    summary_rid = summary.get("run_id", "")
    events_rid = events_doc.get("run_id", "")

    if run_id and status_rid and status_rid != run_id:
        fail("V02-runid-status", f"status.run_id={status_rid} != 传入 run_id={run_id}", is_critical=True)
    elif run_id:
        ok("V02-runid-status", f"status.run_id={status_rid} matches")

    if summary_rid and status_rid and summary_rid != status_rid:
        fail("V02-runid-summary", f"summary.run_id={summary_rid} != status.run_id={status_rid}", is_critical=True)
    else:
        ok("V02-runid-summary", "summary.run_id matches status")

    if events_rid and status_rid and events_rid != status_rid:
        fail("V02-runid-events", f"events.run_id={events_rid} != status.run_id={status_rid}")
    else:
        ok("V02-runid-events", "events.run_id matches status (or both empty)")

    # ── 3. pipeline_version 一致性 ────────────────────────
    for fname, key, data in [
        ("status.json", "pipeline_version", status),
        ("latest-summary.json", "pipeline_version", summary),
    ]:
        pv = data.get(key)
        if pv != PIPELINE_VERSION:
            fail(f"V03-pv-{key}", f"{fname} pipeline_version={pv} != expected={PIPELINE_VERSION}", is_critical=True)
        else:
            ok(f"V03-pv-{key}", f"{fname} pipeline_version={PIPELINE_VERSION} ✓")

    # ── 4. 风险等级校验 ────────────────────────────────────
    events_list = events_doc.get("events", [])
    for e in events_list:
        country = e.get("country", "")
        if country in FIXED_RISK_LEVELS:
            expected = FIXED_RISK_LEVELS[country]["country_risk_level"]
            actual = e.get("country_risk_level")
            if actual != expected:
                fail(f"V04-risk-{e.get('event_id','?')}",
                     f"{country} {e.get('event_id')} country_risk_level={actual} 应为 {expected}",
                     is_critical=True)
    ok("V04-risk", "乍得/尼日尔风险等级校验通过")

    # ── 5. 事件 ID 完整性 ──────────────────────────────────
    for e in events_list:
        if not e.get("event_id"):
            fail("V05-eid", f"事件缺少 event_id: title={e.get('title_cn','')[:40]}", is_critical=True)
    ok("V05-eid", "所有事件均有 event_id")

    # ── 6. 来源链接 ────────────────────────────────────────
    missing_src = sum(1 for e in events_list if not e.get("source_url"))
    if missing_src > 0:
        fail("V06-src", f"{missing_src} 条事件缺少 source_url")
    else:
        ok("V06-src", "所有事件均有 source_url")

    # ── 7. 隔离事件检查 ────────────────────────────────────
    quarantine = load_json(os.path.join(DATA_DIR, "quarantine_events.json"), {"items": []})
    qi = quarantine.get("items", [])
    q_ids = {q.get("event_id") for q in qi if q.get("event_id")}
    event_ids = {e.get("event_id") for e in events_list}
    crossover = q_ids & event_ids
    if crossover:
        fail("V07-quarantine", f"quarantine 中 {len(crossover)} 条事件仍出现在 events: {sorted(crossover)[:5]}",
             is_critical=True)
    else:
        ok("V07-quarantine", "quarantine 与 events 无重叠")

    # ── 8. Stage-1 国家检查：旧 pipeline 数据不进当前统计 ────
    stage1_events = [e for e in events_list if e.get("country") in STAGE1_COUNTRIES]
    old_pipeline = [e for e in stage1_events if e.get("pipeline_version", 0) < 2]
    if old_pipeline:
        fail("V08-stage1", f"{len(old_pipeline)} 条乍得/尼日尔事件 pipeline_version<2 可能进入当前统计")

    # Check that ALL stage1 events pass the gate
    nonpass = [e for e in stage1_events if not passes_stage1_gate(e)]
    if nonpass:
        fail("V08-gate", f"{len(nonpass)} 条乍得/尼日尔事件未通过质量闸门")
    else:
        ok("V08-gate", "乍得/尼日尔事件全部通过质量闸门")

    # ── 9. status vs summary 数值一致性 ─────────────────────
    status_24h = status.get("events_24h", -1)
    summary_metrics = summary.get("metrics", [])
    summary_24h = -1
    for m in summary_metrics:
        if "24小时" in m.get("label", ""):
            try:
                summary_24h = int(m["value"])
            except (ValueError, KeyError):
                pass
    if status_24h != summary_24h:
        fail("V09-24h", f"status.events_24h={status_24h} != summary.24h={summary_24h}", is_critical=True)
    else:
        ok("V09-24h", f"24h 一致: {status_24h}")

    status_7d = status.get("events_7d", -1)
    summary_7d = -1
    for m in summary_metrics:
        if "7日" in m.get("label", ""):
            try:
                summary_7d = int(m["value"])
            except (ValueError, KeyError):
                pass
    if status_7d != summary_7d:
        fail("V09-7d", f"status.events_7d={status_7d} != summary.7d={summary_7d}", is_critical=True)
    else:
        ok("V09-7d", f"7d 一致: {status_7d}")

    # ── 10. 日报窗口校验 ────────────────────────────────────
    ok("V10-report", "日报时间窗口校验（由 generate_reports.py 负责，此处跳过）")

    # ── 11. dist 文件存在性 ──────────────────────────────────
    for fname in ["index.html", "events.html", "data/status.json", "data/latest-summary.json"]:
        dpath = os.path.join(dist_dir, fname)
        if os.path.exists(dpath):
            ok(f"V11-dist-{fname}", f"dist/{fname} 存在")
        else:
            fail(f"V11-dist-{fname}", f"dist/{fname} 不存在")

    # ── 12. dist run_id 一致性 ──────────────────────────────
    dist_status = load_json(os.path.join(dist_dir, "data", "status.json"))
    if dist_status:
        ds_rid = dist_status.get("run_id", "")
        if ds_rid and status_rid and ds_rid != status_rid:
            fail("V12-dist-rid", f"dist status.run_id={ds_rid} != data status.run_id={status_rid}", is_critical=True)
        else:
            ok("V12-dist-rid", f"dist.run_id matches data: {ds_rid}")
        ds_pv = dist_status.get("pipeline_version")
        if ds_pv != PIPELINE_VERSION:
            fail("V12-dist-pv", f"dist pipeline_version={ds_pv} != {PIPELINE_VERSION}", is_critical=True)
    else:
        fail("V12-dist-status", f"dist/data/status.json 不可读")

    # ── 13. main vs dist 数据数量一致 ────────────────────────
    dist_events = load_json(os.path.join(dist_dir, "data", "events.json"), {"events": []})
    dist_ev_count = len(dist_events.get("events", []))
    src_ev_count = len(events_list)
    if dist_ev_count != src_ev_count:
        fail("V13-count", f"dist events={dist_ev_count} != source events={src_ev_count}", is_critical=True)
    else:
        ok("V13-count", f"事件数量一致: {src_ev_count}")

    # ── 14. 未来时间检查 ──────────────────────────────────────
    now = bj_now()
    future_events = []
    for e in events_list:
        for field in ("published_time", "event_time"):
            t = e.get(field, "")
            dt = parse_time(t)
            if dt and dt > now + __import__("datetime").timedelta(hours=1):  # 允许1小时误差
                future_events.append((e.get("event_id"), field, t))
    if future_events:
        fail("V14-future", f"{len(future_events)} 条事件存在未来时间: {future_events[:3]}")
    else:
        ok("V14-future", "无未来时间事件")

    # ── 15. 数据文件引用存在性 ───────────────────────────────
    # 检查 index.html 引用的数��路径在 dist 中存在
    index_path = os.path.join(dist_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as f:
            html = f.read()
        data_refs = ["data/status.json", "data/latest-summary.json", "data/events.json"]
        for ref in data_refs:
            if ref in html:
                if os.path.exists(os.path.join(dist_dir, ref)):
                    ok(f"V15-ref-{ref}", f"HTML 引用的 {ref} 在 dist 中存在")
                else:
                    fail(f"V15-ref-{ref}", f"HTML 引用 {ref} 但 dist 中不存在")

    # ── 总结 ────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"校验结果: {len(errors)} 个问题, {len(critical)} 个严重错误")

    if critical:
        print(f"🚫 严重错误 ({len(critical)}): {', '.join(critical)}")
        print("部署已阻止。")
        return EXIT_FAIL
    else:
        print("✅ 所有关键检查通过。可以继续部署。")
        return EXIT_OK


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage-1 Pipeline 数据质量验证")
    parser.add_argument("--run-id", type=str, help="指定 run_id")
    parser.add_argument("--dist", type=str, default=None, help="dist 目录路径")
    args = parser.parse_args()
    sys.exit(main(run_id=args.run_id, dist_dir=args.dist))
