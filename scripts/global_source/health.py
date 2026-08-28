#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Global Source Layer — Source Health 独立运行层（§十一，Source Expansion A）。

轻量健康记录：listing/detail 状态、http、item 数、latest_item_at、failure_type。
Runtime 数据：data/runtime/source_health.json（gitignore，不进 dist/registry）。
"""

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEALTH_PATH = ROOT / "data" / "runtime" / "source_health.json"

FAILURE_TYPES = {
    "none", "timeout", "http_error", "blocked", "parse_error",
    "empty", "requires_js", "access_restricted", "unknown",
}


def load_health(path=None):
    p = Path(path) if path else HEALTH_PATH
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"schema_version": "1.0.0", "entries": []}


def record_health(healths, path=None, latest_items=None, scope="global",
                  country_iso3=None, stable=None, last_detail=None):
    """写入/合并健康记录。healths: 本次 run 的 health dict 列表。"""
    p = Path(path) if path else HEALTH_PATH
    doc = load_health(p)
    by_id = {e["source_id"]: e for e in doc.get("entries", [])}
    latest_items = latest_items or {}
    for h in healths:
        sid = h.get("source_id")
        h["latest_item_at"] = latest_items.get(sid)
        h.setdefault("scope", scope)
        if country_iso3:
            h["country_iso3"] = country_iso3
        if stable is not None:
            h["stable_source"] = stable.get(sid) if isinstance(stable, dict) else stable
        if last_detail:
            h["last_detail_success_at"] = last_detail.get(sid)
        by_id[sid] = h
    doc["entries"] = sorted(by_id.values(), key=lambda e: e["source_id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def summary(doc=None):
    doc = doc or load_health()
    entries = doc.get("entries", [])
    ok = sum(1 for e in entries if e.get("listing_status") == "success")
    return {"entries": len(entries), "listing_success": ok,
            "listing_failed": len(entries) - ok}
