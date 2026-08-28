#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Global Source Layer — 真实 Dry-run CLI（§十五，Source Expansion A）。

手动执行一次 Global Source discovery（过去 72h），只生成 internal audit：
  - data/runtime/global_discovery_audit.json（candidates + 统计）
  - data/runtime/source_health.json（健康记录）
不写 Social/Disease Canonical/Public。不恢复 schedule。
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.global_source.registry import load_registry, check_registry
from scripts.global_source.adapters import run_listing
from scripts.global_source.candidates import (
    dedup_candidates, independent_count, origin_group, new_candidate,
)
from scripts.global_source.africa_filter import filter_candidates, country_hints
from scripts.global_source.health import record_health

AUDIT_PATH = ROOT / "data" / "runtime" / "global_discovery_audit.json"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Global Source Layer dry-run")
    ap.add_argument("--max-items", type=int, default=25)
    ap.add_argument("--skip-aljazeera", action="store_true",
                    help="跳过 Al Jazeera（全球 feed，选项性）")
    args = ap.parse_args(argv)

    # 1. registry 校验
    sources, errs = load_registry()
    if errs:
        print("registry errors: %d" % len(errs))
        for e in errs:
            print("  - %s" % e)
        return 2
    print("registry sources: %d" % len(sources))

    # 2. listing discovery
    doc, healths = run_listing(max_items=args.max_items)
    if doc is None:
        print("run failed:", healths)
        return 2
    run_id = doc["run_id"]
    results = doc["results"]
    print("run_id=%s" % run_id)

    # 3. candidates 构造；仅全球 feed（scope=global，如 Al Jazeera）走 Africa 确定性过滤
    all_cands = []
    for sid, items in results.items():
        src = next((s for s in sources if s["source_id"] == sid), {})
        for it in items:
            it["country_hints"] = country_hints(
                " ".join([str(it.get("title") or ""), str(it.get("url") or "")]))
            c = new_candidate(src, it)
            if c:
                all_cands.append(c)
    global_feed = [c for c in all_cands if c.get("scope") == "global"]
    africa_scoped = [c for c in all_cands if c.get("scope") != "global"]
    pass_f, filtered = filter_candidates(global_feed)
    africa_cands = pass_f + africa_scoped
    africa_cands, dup = dedup_candidates(africa_cands)

    # 4. 统计
    per_source = {}
    for c in africa_cands:
        per_source.setdefault(c["source_id"], []).append(c)
    stats = {
        "run_id": run_id,
        "sources_attempted": len(results),
        "items_discovered": len(all_cands),
        "africa_candidates": len(africa_cands),
        "filtered_non_africa": len(filtered),
        "duplicate_candidates": dup,
        "per_source": {sid: len(items) for sid, items in sorted(per_source.items())},
        "lead_only_candidates": len([c for c in africa_cands
                                     if c.get("source_group") in ("allafrica", "reliefweb")]),
    }
    # 独立来源组
    n_indep, groups = independent_count(africa_cands)
    stats["independent_origin_groups"] = n_indep
    stats["origin_groups"] = groups

    # 5. 健康记录（latest_item_at 取各 source 最新）
    latest = {}
    for sid, items in results.items():
        ts = [i.get("published_at") for i in items if i.get("published_at")]
        latest[sid] = max(ts) if ts else None
    record_health(healths, latest_items=latest)

    audit = {"stats": stats, "candidates": africa_cands,
             "filtered_non_africa": filtered[:20]}
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print("audit written: %s" % AUDIT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
