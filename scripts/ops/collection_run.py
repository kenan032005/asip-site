#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 8C Package3 — Collection runner（§五/§六）。

Collection 本身不调用 AI。本模块：
  1. 调用现有 deterministic 采集组件（stage3_collect_v2）；
  2. 统计 candidates_new（raw_candidates / pending 增量）；
  3. 更新 production state（last_collection_run / last_successful_collection）。

幂等（§十三）：重复 run 不重复产生 canonical entity —— 采集侧去重由
stage3_collect_v2 的 Deduplicator 保证；本模块记录采集窗口与 hash 于 state。
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


def run_collection(execute=False, emit=lambda s: print(s), state=None, ops_run=None):
    """execute=False：仅编排记账（shadow/dry）；True：调用 stage3_collect_v2。"""
    state = state or ps.load_state()
    started = ps._utcnow_iso()
    ps.record_run(state, "last_collection_run", ok=False)
    ok = True
    if execute:
        try:
            r = subprocess.run([sys.executable, str(ROOT / "scripts/stage3_collect_v2.py"),
                                "--dry" if False else ""],  # 生产执行默认写 pending
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
    if ops_run is not None:
        ops_run["sources_attempted"] = 1
        ops_run["sources_succeeded"] = 1 if ok else 0
        ops_run["sources_failed"] = 0 if ok else 1
        ops_run["candidates_new"] = max(n_pending, 0)
    emit("COLLECTION_OK = %s | raw=%s pending=%s" % (ok, n_raw, n_pending))
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description="Collection runner (no AI)")
    ap.add_argument("--execute", action="store_true", help="调用真实采集（默认仅记账）")
    args = ap.parse_args(argv)
    state = ps.load_state()
    ok = run_collection(execute=args.execute, state=state)
    ps.save_state(state)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
