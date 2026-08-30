#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 8C Package3 — Collection runner（§五/§六）。

Collection 本身不调用 AI。本模块：
  1. 调用现有 deterministic 采集组件（stage3_collect_v2）；
  2. 从采集器真实产物读取指标（不得硬编码，见 Stage8D P1-1）；
  3. 更新 production state（last_collection_run / last_successful_collection）。

幂等（§十三）：重复 run 不重复产生 canonical entity —— 采集侧去重由
stage3_collect_v2 的 Deduplicator 保证；本模块记录采集窗口与 hash 于 state。

Stage8D P1-1 修复：此前 `sources_attempted = 1` 为硬编码常量，无法作为
"真实采集"的证据。现改为从采集器真实统计文件读取；读取不到时标记为
unavailable（并在 summary/notes 中显式标注），绝不猜值。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ops import production_state as ps  # noqa: E402

DATA = ROOT / "data"
COLLECTOR_STATS = ROOT / "logs" / "stage3_collection_stats.json"
COLLECTION_SUMMARY = ps.OPS_DIR / "collection_summary.json"

#: 采集统计中读取的真实字段 → 对外指标名
_STAT_FIELDS = {
    "sources_configured": "configured_sources",
    "sources_attempted": "attempted_sources",
    "sources_succeeded": "successful_sources",
    "sources_failed": "failed_sources",
    "articles_discovered": "articles_discovered",
    "duplicates": "duplicate_count",
    "published": "published_count",
    "quarantined": "quarantined_count",
}


def _count_candidates():
    n_raw = 0
    p = DATA / "raw_candidates.json"
    if p.exists():
        try:
            n_raw = len(json.loads(p.read_text(encoding="utf-8")).get("items", []))
        except Exception:
            n_raw = -1
    n_pending = 0
    p2 = DATA / "pending_events.json"
    if p2.exists():
        try:
            n_pending = len(json.loads(p2.read_text(encoding="utf-8")).get("items", []))
        except Exception:
            n_pending = -1
    return n_raw, n_pending


def read_collector_stats(since_iso=None):
    """读取采集器真实统计；缺失或早于本次运行（陈旧）返回 None。"""
    if not COLLECTOR_STATS.exists():
        return None
    try:
        doc = json.loads(COLLECTOR_STATS.read_text(encoding="utf-8"))
    except Exception:
        return None
    gen = doc.get("generated_at")
    if since_iso and gen and str(gen) < str(since_iso):
        return None  # 陈旧（本次采集未产生新统计）
    totals = doc.get("totals") or {}
    if not totals:
        return None
    return {"generated_at": gen, "run_id": doc.get("run_id"), "totals": totals}


def run_collection(execute=False, emit=lambda s: print(s), state=None, ops_run=None):
    """execute=False：仅编排记账（shadow/dry）；True：调用 stage3_collect_v2。"""
    state = state or ps.load_state()
    started = ps._utcnow_iso()
    ps.record_run(state, "last_collection_run", ok=False)
    ok = True
    if execute:
        try:
            r = subprocess.run([sys.executable, str(ROOT / "scripts/stage3_collect_v2.py")],
                               capture_output=True, text=True, timeout=900)
            if r.returncode != 0:
                emit("collection_exit=%d" % r.returncode)
                emit(r.stdout[-1500:])
                ok = False
            else:
                emit(r.stdout[-1500:])
        except Exception as e:
            emit("collection_exception=%s" % e)
            ok = False
    ps.record_run(state, "last_collection_run", ok=ok)
    n_raw, n_pending = _count_candidates()

    stats = read_collector_stats(started) if execute else None
    totals = (stats or {}).get("totals") or {}
    if stats:
        metrics = {k: totals.get(v) for k, v in _STAT_FIELDS.items()}
        metrics["metrics_source"] = "logs/stage3_collection_stats.json"
        metrics["collector_run_id"] = stats.get("run_id")
        metrics["collector_generated_at"] = stats.get("generated_at")
    else:
        # 不得猜值：标记为 unavailable（execute=False 属预期 shadow 记账）
        metrics = {k: None for k in _STAT_FIELDS}
        metrics["metrics_source"] = "none_shadow" if not execute else "unavailable"
        metrics["collector_run_id"] = None
        metrics["collector_generated_at"] = None
    metrics["ok"] = ok
    metrics["raw_candidates_on_disk"] = n_raw
    metrics["pending_events_on_disk"] = n_pending
    metrics["executed"] = bool(execute)
    metrics["started_at"] = started

    try:
        ps.OPS_DIR.mkdir(parents=True, exist_ok=True)
        COLLECTION_SUMMARY.write_text(
            json.dumps(metrics, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        emit("collection_summary_write_error=%s" % e)

    if ops_run is not None:
        for k in ("sources_configured", "sources_attempted", "sources_succeeded",
                  "sources_failed", "articles_discovered", "duplicates",
                  "published", "quarantined"):
            ops_run[k] = metrics.get(k)
        ops_run["candidates_new"] = max(n_pending, 0)
        if not stats:
            ops_run["notes"].append(
                "collection_metrics_unavailable" if execute
                else "collection_metrics_not_applicable_shadow")
    emit("COLLECTION_OK = %s | raw=%s pending=%s | metrics_source=%s" % (
        ok, n_raw, n_pending, metrics["metrics_source"]))
    emit("COLLECTION_METRICS = %s" % json.dumps(metrics, ensure_ascii=False))
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description="Collection runner (no AI)")
    ap.add_argument("--execute", action="store_true", help="调用真实采集（默认仅记账）")
    args = ap.parse_args(argv)
    state = ps.load_state()
    ok = run_collection(execute=args.execute, state=state)
    ps.save_state(state)
    if not ok and args.execute:
        # §二十二：采集失败（含 900s 超时）不污染 state，仅记录；下轮可 retry
        print("collection_failed_state_unchanged", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
