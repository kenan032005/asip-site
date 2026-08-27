#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 8C Package3 — Production State persistence（§十二/§十三）。

State 不依赖本地 WorkBuddy 文件；全部持久化到 GitHub repo 的
production-state 分支（data/runtime/ops/ 目录，force-add 提交）。

字段（§十二）：
  last_collection_run / last_successful_collection / last_ai_run /
  last_successful_ai / last_disease_run / last_daily_report /
  last_weekly_report / last_deploy / processed_hashes /
  failed_held_records / ai_usage_totals

幂等（§十三）：processed_hashes 记录已处理的 source item / event /
disease record 的 content hash，重复 run 不得重复 AI/enrichment/report。
"""
import json
import time
from pathlib import Path

OPS_DIR = Path(__file__).resolve().parents[2] / "data" / "runtime" / "ops"
STATE_FILE = OPS_DIR / "production_state.json"
OPS_STATUS_FILE = OPS_DIR / "operations_status.json"
HEALTH_FILE = OPS_DIR / "source_health.json"

EMPTY_STATE = {
    "schema": "stage8c-package3-v1",
    "last_collection_run": None,
    "last_successful_collection": None,
    "last_ai_run": None,
    "last_successful_ai": None,
    "last_disease_run": None,
    "last_daily_report": None,
    "last_weekly_report": None,
    "last_deploy": None,
    "processed_hashes": {},
    "failed_held_records": [],
    "ai_usage_totals": {"social_enrichment": {}, "disease_enrichment": {},
                        "daily_analysis": {}, "weekly_analysis": {},
                        "brief_analysis": {}},
    "reports": {},
}


def _utcnow_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# last_* → last_successful_* 映射（§十二）
_SUCCESS_FIELD = {
    "last_collection_run": "last_successful_collection",
    "last_ai_run": "last_successful_ai",
    "last_disease_run": "last_successful_disease",
    "last_daily_report": "last_successful_daily_report",
    "last_weekly_report": "last_successful_weekly_report",
    "last_deploy": "last_successful_deploy",
}


def record_run(state, field, ok=True):
    now = _utcnow_iso()
    state[field] = now
    if ok:
        succ = _SUCCESS_FIELD.get(field)
        if succ:
            state[succ] = now
    return state


def load_state():
    if STATE_FILE.exists():
        try:
            s = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            base = dict(EMPTY_STATE)
            base.update(s)
            return base
        except Exception:
            pass
    return dict(EMPTY_STATE)


def save_state(state):
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")
    return STATE_FILE


def content_hash(obj):
    """确定性 content hash（§十三：content hash 幂等）。"""
    import hashlib
    blob = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def is_processed(state, pool, key):
    return key in (state.get("processed_hashes") or {}).get(pool, {})


def mark_processed(state, pool, key, extra=None):
    ph = state.setdefault("processed_hashes", {})
    ph.setdefault(pool, {})[key] = extra or _utcnow_iso()
    return state


def add_ai_usage(state, pool, tokens):
    u = state.setdefault("ai_usage_totals", {}).setdefault(pool, {})
    for k in ("input_tokens", "output_tokens", "total_tokens", "calls"):
        u[k] = u.get(k, 0) + (tokens.get(k) or 0)
    return state
