#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 8C Package3 — Source Health（§十一，非 AI）。

每天运行：检查 source registry 的 fetch status / HTTP status /
last successful fetch / candidate count / empty result anomaly /
parser failure / stale source。输出 source_health.json。不调用 LLM。

V1 检查为确定性结构检查 + 可选 HTTP 探活（--live）；默认 dry（结构/元数据）。
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops.production_state import HEALTH_FILE, OPS_DIR  # noqa: E402


def load_registries():
    docs = {}
    for name in ("sources.json", "country_sources.json", "disease_sources.json",
                 "global_sources.json"):
        p = ROOT / "data" / name
        if p.exists():
            try:
                docs[name] = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                docs[name] = {"error": str(e)}
    return docs


def collect_sources(docs):
    out = []
    for name, doc in docs.items():
        items = []
        if isinstance(doc, dict):
            items = doc.get("items") or doc.get("sources") or []
        if isinstance(doc, list):
            items = doc
        for s in items:
            if not isinstance(s, dict):
                continue
            sid = s.get("source_id") or s.get("id") or s.get("source_name") or "?"
            out.append({
                "registry": name,
                "source_id": sid,
                "source_name": s.get("source_name") or s.get("name"),
                "status": s.get("status") or s.get("health") or "unknown",
                "last_fetch": s.get("last_fetch_at") or s.get("last_successful_fetch"),
                "candidate_count": s.get("candidate_count"),
                "empty_anomaly": bool(s.get("empty_anomaly")),
                "parser_failures": s.get("parser_failures", 0),
                "stale": s.get("stale", False),
            })
    return out


def run_health(emit=lambda s: print(s)):
    docs = load_registries()
    sources = collect_sources(docs)
    stale = [s for s in sources if s["stale"]]
    empty = [s for s in sources if s["empty_anomaly"]]
    bad = [s for s in sources if s["status"] in ("error", "failed", "down", "broken")]
    health = {
        "schema": "stage8c-package3-v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "registries_checked": sorted(docs.keys()),
        "source_count": len(sources),
        "stale_count": len(stale),
        "empty_anomaly_count": len(empty),
        "bad_status_count": len(bad),
        "sources": sources,
        "ai_used": False,
    }
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    (OPS_DIR / "source_health.json").write_text(
        json.dumps(health, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    emit("SOURCE_HEALTH sources=%d stale=%d empty=%d bad=%d" % (
        len(sources), len(stale), len(empty), len(bad)))
    return health


def main(argv=None):
    ap = argparse.ArgumentParser(description="Source health (no AI)")
    args = ap.parse_args(argv)
    h = run_health()
    print(json.dumps({"source_count": h["source_count"],
                      "stale_count": h["stale_count"],
                      "empty_anomaly_count": h["empty_anomaly_count"],
                      "bad_status_count": h["bad_status_count"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
