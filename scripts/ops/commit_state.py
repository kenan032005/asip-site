#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1 — 状态提交助手（可中途调用）。

目的：修复"采集与后续付费任务的超时冲突"。
原流程把唯一一次 state 提交放在整轮最末（采集 50min + AI + 报告 + build 之后），
一旦越过 job timeout，整轮采集成果全部丢弃，下一轮重复采集 + 重复 AI（费用放大）。

本模块让"采集完成即持久化"成为可能：
  commit_now(after="collection") → cp 到 state_src → git add/commit/push（带重试与 merge -X ours）

约束：
  - 提交路径与 orchestrator 现有 Commit state 完全一致（对称性不变）；
  - 不含任何凭据；使用 runner 自带 GITHUB_TOKEN（actions/checkout 已注入）；
  - 失败时 record_strike()，连续失败触发熔断（付费调用自锁）。
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "state_src"

#: 与 orchestrator "Commit state" 的路径集合保持一致（对称）
COPY_PAIRS = [
    ("data/runtime/ops", "data/runtime/ops"),
    ("data/canonical", "data/canonical"),
    ("data/disease", "data/disease"),
    ("data/runtime/timeline", "data/runtime/timeline"),
    ("data/public", "data/public"),
    ("data/intelligence", "data/intelligence"),
    ("data/views", "data/views"),
    ("data/reports", "data/reports"),
    ("logs/collector_cache", "logs/collector_cache"),
]
COPY_FILES = [
    "data/events.json", "data/pending_events.json", "data/raw_candidates.json",
    "data/quarantine_events.json", "data/runtime/article_processing_state.json",
    "data/runtime/article_processing_state.json.bak",
]
GIT_ADD = ("data/runtime/ops", "data/canonical", "data/disease", "data/runtime/timeline",
           "data/events.json", "data/pending_events.json", "data/raw_candidates.json",
           "data/quarantine_events.json", "data/public", "data/intelligence", "data/views",
           "data/reports", "logs", "data/runtime/article_processing_state.json")


def _run(args, timeout=180, check=True):
    r = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError("%s failed(%d): %s" % (" ".join(args[:3]), r.returncode,
                                                  (r.stderr or r.stdout)[-400:]))
    return r


def sync_to_state_branch():
    if not STATE_DIR.exists():
        raise RuntimeError("state_src missing (checkout production-state into state_src first)")
    for src, dst in COPY_PAIRS:
        s, d = ROOT / src, STATE_DIR / dst
        if s.is_dir():
            d.mkdir(parents=True, exist_ok=True)
            for f in s.rglob("*"):
                if f.is_file():
                    t = d / f.relative_to(s)
                    t.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, t)
    for rel in COPY_FILES:
        s = ROOT / rel
        if s.is_file():
            d = STATE_DIR / rel
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)


def commit_now(message, after="state", push=True, timeout=180):
    """提交 state 分支。返回 {ok, committed, pushed, message}。失败会 record_strike。"""
    from scripts.ops import paid_gate
    try:
        sync_to_state_branch()
        for p in GIT_ADD:
            _run(["git", "add", "-A", p], check=False)
        st = _run(["git", "status", "--porcelain"], check=False)
        if not (st.stdout or "").strip():
            return {"ok": True, "committed": False, "pushed": False,
                    "message": "no changes (%s)" % after}
        _run(["git", "commit", "-m", "%s [%s]" % (message, after)], check=False)
        committed = True
        if not push:
            return {"ok": True, "committed": committed, "pushed": False, "message": after}
        last = ""
        for attempt in range(3):
            try:
                _run(["git", "fetch", "origin", "production-state"], timeout=timeout, check=False)
                _run(["git", "merge", "-X", "ours", "origin/production-state", "-m",
                      "merge origin/production-state (ours) [%s]" % after], check=False)
                _run(["git", "push", "origin", "HEAD:production-state"], timeout=timeout)
                return {"ok": True, "committed": True, "pushed": True, "message": after}
            except Exception as e:  # noqa: BLE001
                last = str(e)[:300]
        paid_gate.record_strike("state_push_failed:%s" % last)
        return {"ok": False, "committed": committed, "pushed": False, "error": last}
    except Exception as e:  # noqa: BLE001
        paid_gate.record_strike("state_commit_failed:%s" % str(e)[:200])
        return {"ok": False, "committed": False, "pushed": False, "error": str(e)[:400]}


def main(argv=None):
    argv = argv or sys.argv[1:]
    msg = argv[0] if argv else "ops: state checkpoint"
    after = argv[1] if len(argv) > 1 else "manual"
    res = commit_now(msg, after=after)
    print(res)
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
