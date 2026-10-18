#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C8-4D1 §8 — 真实网络效率测量（共享 feed 复用前后对照）。

在真实 HTTP 上对「多 source_id 指向同一 feed」的 5 组（12 个 source 执行）做
OLD（flag off）/ NEW（flag on）对照，测量：
  BASELINE_PHYSICAL_HTTP_REQUESTS / POST_PHYSICAL_HTTP_REQUESTS
  BASELINE_HTTP_TIME_SECONDS   / POST_HTTP_TIME_SECONDS
  CACHE_HITS / CACHE_MISSES / CACHE_BYTES
  ARTICLES_DISCOVERED / ARTICLES_UNIQUE
并逐源比对 URL 集合，确认复用不改变发现结果（真实响应等价性）。

用法：python scripts/ops/c8_4d1_measure.py --out ../asip_audit_tmp/c8_4d1_measure.json
"""
import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "scripts" / "collectors")):
    if p not in sys.path:
        sys.path.insert(0, p)

import framework  # noqa: E402
from registry import SourceRegistry, ArticleDiscoverer  # noqa: E402


def _groups(registry):
    """按有效 feed_url 分组，仅保留被 >1 个 source_id 引用的组。"""
    by = defaultdict(list)
    for s in registry.enabled():
        if s.get("discovery_type") not in ("rss", "atom"):
            continue
        fu = (s.get("feed_url") or "").strip()
        if fu:
            by[fu].append(s)
    return {u: ss for u, ss in by.items() if len(ss) > 1}


def run_round(sources, reuse: bool):
    if reuse:
        os.environ[framework.SHARED_REUSE_ENV] = "1"
    else:
        os.environ.pop(framework.SHARED_REUSE_ENV, None)
    os.environ.pop(framework.SHARED_REUSE_SOURCES_ENV, None)
    framework.reset_run_caches()
    disc = ArticleDiscoverer(registry=None)
    per = {}
    all_urls = []
    t0 = time.time()
    for src in sources:
        s0 = time.time()
        arts, errs = disc.discover(src)
        urls = sorted(a["url"] for a in arts)
        per[src["source_id"]] = {
            "feed_url": src["feed_url"],
            "count": len(arts),
            "url_sha": "%s" % hash(tuple(urls)),
            "urls": urls,
            "errors": errs,
            "elapsed_s": round(time.time() - s0, 2),
        }
        all_urls.extend(urls)
    elapsed = round(time.time() - t0, 2)
    stats = framework.get_request_stats()
    return {
        "reuse": reuse,
        "physical_http_requests": stats["physical_network_requests"],
        "http_time_seconds": elapsed,
        "cache_hits": stats["cache_hits"],
        "cache_misses": stats["cache_misses"],
        "cache_bytes": stats["cache_bytes"],
        "reused_requests": stats["reused_requests"],
        "articles_discovered": len(all_urls),
        "articles_unique": len(set(all_urls)),
        "per_source": per,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    reg = SourceRegistry()
    groups = _groups(reg)
    sources = []
    for u, ss in groups.items():
        sources.extend(ss)
    print("shared_feed_groups = %d | source_executions = %d" % (len(groups), len(sources)))
    for u, ss in groups.items():
        print("  %s -> %s" % (u, ", ".join(s["source_id"] for s in ss)))

    baseline = run_round(sources, reuse=False)
    time.sleep(1)
    post = run_round(sources, reuse=True)

    diffs = {}
    for sid, b in baseline["per_source"].items():
        p = post["per_source"].get(sid) or {}
        if b["urls"] != p.get("urls"):
            diffs[sid] = {
                "baseline_count": b["count"], "post_count": p.get("count"),
                "only_baseline": sorted(set(b["urls"]) - set(p.get("urls") or [])),
                "only_post": sorted(set(p.get("urls") or []) - set(b["urls"])),
            }

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "shared_feed_groups": {u: [s["source_id"] for s in ss] for u, ss in groups.items()},
        "source_executions": len(sources),
        "baseline": baseline,
        "post": post,
        "url_set_diffs": diffs,
        "savings": {
            "physical_requests_saved": baseline["physical_http_requests"] - post["physical_http_requests"],
            "physical_request_pct": round(
                100.0 * (baseline["physical_http_requests"] - post["physical_http_requests"])
                / max(1, baseline["physical_http_requests"]), 1),
            "http_time_saved_seconds": round(baseline["http_time_seconds"] - post["http_time_seconds"], 2),
        },
    }
    print(json.dumps({k: v for k, v in out.items() if k not in ("baseline", "post")},
                     ensure_ascii=False, indent=1))
    print("BASELINE requests=%d time=%.2fs | POST requests=%d time=%.2fs | hits=%d misses=%d bytes=%d" % (
        baseline["physical_http_requests"], baseline["http_time_seconds"],
        post["physical_http_requests"], post["http_time_seconds"],
        post["cache_hits"], post["cache_misses"], post["cache_bytes"]))
    if args.out:
        Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print("written:", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
