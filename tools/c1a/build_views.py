#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C1A build integration —— 在正常 V1.1 build 中自动生成 news-stream-v1 视图。

背景（C1B §二）：
  C1A 的 `data/views/*.json` 当时是手工从 preview 目录复制的，属于 preview-only
  产物。本模块把它变成 build 的一等步骤：每次 `scripts/build_site.py` 都会用
  仓库自身数据（canonical / public / frontend views）重新生成

      data/views/news_stream.json
      data/views/source_yield_report.json
      data/views/c1a_gate_audit.json

  不依赖手工复制，也不依赖 `c1a_preview/`。

输入映射（build_news_stream.build 期望的 live_dir 扁平命名 ← 仓库真实数据）：
  data_public_published_events.json  ← data/public/published_events.json
  data_master_events.json            ← data/runtime/frontend_preview_public/master_events.json
  data_site_overview.json            ← data/runtime/frontend_preview_public/site_overview.json
  data_events.json                   ← data/events.json
  data_public_current_metrics.json   ← data/public/current_metrics.json
  …（其余公开视图同理；缺失时跳过，不伪造）

失败语义：build 步骤本身**不阻断**站点构建（返回 ok=False 并打印原因），
  因为 news_stream 是展示层视图；阻断会复制 C1A 之前"构建成功但页面空白"的
  不可观测故障。但会显式打印 C1A_VIEWS_OK=False，便于验收与 CI 门禁抓取。
"""
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))          # tools/c1a
ROOT = os.path.dirname(os.path.dirname(HERE))              # repo root
sys.path.insert(0, HERE)

from build_news_stream import build as _build_news_stream   # noqa: E402

#: live_dir 扁平名 ← 仓库相对路径（按优先级顺序探测，先命中先用）
LIVE_INPUTS = [
    ("data_site_overview.json", ["data/runtime/frontend_preview_public/site_overview.json",
                                 "data/site_overview.json"]),
    ("data_master_events.json", ["data/runtime/frontend_preview_public/master_events.json",
                                 "data/master_events.json"]),
    ("data_country_snapshots.json", ["data/runtime/frontend_preview_public/country_snapshots.json",
                                     "data/country_snapshots.json"]),
    ("data_disease_outbreaks.json", ["data/runtime/frontend_preview_public/disease_outbreaks.json",
                                     "data/disease_outbreaks.json"]),
    ("data_report_index.json", ["data/runtime/frontend_preview_public/report_index.json",
                                "data/report_index.json"]),
    ("data_event_timelines.json", ["data/runtime/frontend_preview_public/event_timelines.json",
                                   "data/event_timelines.json"]),
    ("data_knowledge_summary.json", ["data/runtime/frontend_preview_public/knowledge_summary.json",
                                     "data/knowledge_summary.json"]),
    ("data_china_interest.json", ["data/runtime/frontend_preview_public/china_interest.json",
                                  "data/china_interest.json"]),
    ("data_events.json", ["data/events.json"]),
    ("data_sources.json", ["data/sources.json"]),
    ("data_countries.json", ["data/countries.json"]),
    ("data_risk-levels.json", ["data/risk-levels.json"]),
    ("data_latest-summary.json", ["data/latest-summary.json"]),
    ("data_public_published_events.json", ["data/public/published_events.json"]),
    ("data_public_current_metrics.json", ["data/public/current_metrics.json"]),
    ("data_public_disease_events.json", ["data/public/disease_events.json"]),
    ("data_public_legacy_archive_events.json", ["data/public/legacy_archive_events.json"]),
]


def _assemble_live_dir(root, dest):
    """把仓库公开数据摊平成 builder 期望的 live_dir；返回 (命中数, 缺失名列表)。"""
    os.makedirs(dest, exist_ok=True)
    hit, missing = 0, []
    for flat, candidates in LIVE_INPUTS:
        src = None
        for rel in candidates:
            p = os.path.join(root, rel.replace("/", os.sep))
            if os.path.exists(p):
                src = p
                break
        if src is None:
            missing.append(flat)
            continue
        shutil.copy2(src, os.path.join(dest, flat))
        hit += 1
    return hit, missing


def build_c1a_views(root=None, internal_dir=None, out_root=None, now=None, verbose=True):
    """生成 C1A 三个视图文件。返回 (ok, stats dict)。

    root          : 仓库根目录（默认本文件上溯两级）
    internal_dir  : builder 读取 canonical/ 等内部数据的根（默认 <root>/data）
    out_root      : 输出根，最终写到 <out_root>/data/views/（默认 <root>）
    """
    root = root or ROOT
    internal_dir = internal_dir or os.path.join(root, "data")
    out_root = out_root or root
    stats = {"ok": False, "views": [], "live_inputs": 0, "live_missing": []}
    tmp = tempfile.mkdtemp(prefix="c1a_live_")
    try:
        hit, missing = _assemble_live_dir(root, tmp)
        stats["live_inputs"] = hit
        stats["live_missing"] = missing
        if verbose and missing:
            print("  C1A live inputs missing (skipped): %s" % ",".join(missing))
        ns, sy = _build_news_stream(tmp, internal_dir, out_root, now=now)
        views_dir = os.path.join(out_root, "data", "views")
        stats["views"] = sorted(os.listdir(views_dir))
        c = ns["counts"]
        stats.update({
            "ok": True,
            "news_items": c["admitted"],
            "fresh_24h": c["fresh_24h"],
            "fresh_72h": c["fresh_72h"],
            "fresh_7d": c["fresh_7d"],
            "fresh_30d": c["fresh_30d"],
            "canonical_eligible": c["canonical_eligible"],
            "grades": sy["totals"]["grades"],
        })
        if verbose:
            print("  C1A views: news=%d 24h=%d 72h=%d 7d=%d 30d=%d canonical_eligible=%d"
                  % (c["admitted"], c["fresh_24h"], c["fresh_72h"],
                     c["fresh_7d"], c["fresh_30d"], c["canonical_eligible"]))
            print("  C1A source yield grades: %s" % json.dumps(sy["totals"]["grades"]))
        return True, stats
    except Exception as e:  # noqa: BLE001
        stats["error"] = "%s: %s" % (type(e).__name__, e)
        if verbose:
            print("  ⚠ C1A 视图生成失败（站点构建继续）: %s" % e)
        return False, stats
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


#: 需要在 dist 中公开的 C1A 视图（其余为内部审计产物，不进公开构建）
PUBLIC_C1A_VIEWS = ["news_stream.json"]


def copy_public_c1a_views(dist_root, root=None):
    """把公开安全的 C1A 视图复制进 dist/data/views/。返回复制数。"""
    root = root or ROOT
    src_dir = os.path.join(root, "data", "views")
    dst_dir = os.path.join(dist_root, "data", "views")
    n = 0
    for name in PUBLIC_C1A_VIEWS:
        src = os.path.join(src_dir, name)
        if not os.path.exists(src):
            continue
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src, os.path.join(dst_dir, name))
        n += 1
    return n


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Generate C1A news-stream views from repo data")
    ap.add_argument("--root", default=None)
    ap.add_argument("--out", default=None, help="输出根（默认仓库根）")
    ap.add_argument("--now", default=None, help="ISO8601，固定时间便于可复现")
    args = ap.parse_args()
    from build_news_stream import ts as _ts
    now = _ts(args.now) if args.now else None
    ok, st = build_c1a_views(root=args.root, out_root=args.out, now=now)
    print("C1A_VIEWS_OK = %s" % ("TRUE" if ok else "FALSE"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
