#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 8C Package3 — Observability（§二十二/§二十三）。

统一 operations summary：每次 run 记录 run_id / workflow / started_at /
completed_at / status / sources_* / candidates_new / ai_* / safety_* /
reports_* / build_status / deploy_status / token_usage。
输出 operations_status.json + operations_summary.md。不记录 CoT。
"""
import json
import time
from pathlib import Path

from scripts.ops.production_state import OPS_STATUS_FILE, OPS_DIR


def new_run(workflow, run_id):
    return {
        "run_id": run_id or "local",
        "workflow": workflow,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "completed_at": None,
        "status": "running",
        "sources_attempted": 0, "sources_succeeded": 0, "sources_failed": 0,
        "candidates_new": 0,
        "ai_attempted": 0, "ai_succeeded": 0, "ai_failed": 0, "ai_held": 0,
        "safety_checked": 0, "safety_corrected": 0, "safety_held": 0,
        "reports_full": 0, "reports_fallback": 0, "reports_low_data": 0,
        "reports_hold": 0,
        "build_status": "not_executed",
        "deploy_status": "not_executed",
        "token_usage": {},
        "notes": [],
    }


def save_ops(run, previous=None):
    from scripts.ops.production_state import OPS_DIR
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    doc = {"schema": "stage8c-package3-v1", "runs": (previous or []) + [run]}
    (OPS_DIR / "operations_status.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # 人类可读 summary
    lines = ["# ASIP Operations Summary", ""]
    for r in reversed(doc["runs"][-10:]):
        lines += [
            "## %s %s" % (r.get("workflow"), r.get("run_id")),
            "- status: %s | started: %s | completed: %s" % (
                r.get("status"), r.get("started_at"), r.get("completed_at")),
            "- sources: attempted=%d succeeded=%d failed=%d" % (
                r.get("sources_attempted"), r.get("sources_succeeded"),
                r.get("sources_failed")),
            "- candidates_new: %d | ai: attempted=%d ok=%d fail=%d held=%d" % (
                r.get("candidates_new"), r.get("ai_attempted"), r.get("ai_succeeded"),
                r.get("ai_failed"), r.get("ai_held")),
            "- safety: checked=%d corrected=%d held=%d" % (
                r.get("safety_checked"), r.get("safety_corrected"), r.get("safety_held")),
            "- reports: full=%d fallback=%d low_data=%d hold=%d" % (
                r.get("reports_full"), r.get("reports_fallback"),
                r.get("reports_low_data"), r.get("reports_hold")),
            "- build=%s deploy=%s" % (r.get("build_status"), r.get("deploy_status")),
            "- tokens: %s" % json.dumps(r.get("token_usage"), ensure_ascii=False),
            "",
        ]
    (OPS_DIR / "operations_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return OPS_DIR / "operations_status.json"


def finish_run(run, status="completed"):
    run["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    run["status"] = status
    return run
