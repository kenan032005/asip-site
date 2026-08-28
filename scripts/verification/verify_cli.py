#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 核实 CLI（§十四 dry-run / fixture 验证）。

用法：
  python scripts/verification/verify_cli.py --fixtures
  python scripts/verification/verify_cli.py --dry-run [--limit N] [--out data/verification/dry_run.json]

约束：
- dry-run 只计算，不写 Public、不覆盖 Canonical；
- 本阶段不使用 AI（确定性规则）；development 模式下 DeepSeek 仅用于开发验证链路。
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.verification.engine import verify_event
from scripts.verification.fixtures import FIXTURES


def load_json(rel, default):
    p = ROOT / rel
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_quarantine_ids(canonical_items):
    q = load_json("data/canonical/quarantine.json", {"items": []})
    qids = set()
    for it in q.get("items", []):
        if it.get("original_object_type") == "event" and it.get("original_id"):
            qids.add(it["original_id"])
    for ev in canonical_items:
        if ev.get("legacy_event_id") in qids:
            qids.add(ev.get("event_id"))
    return qids


def run_fixtures():
    from collections import Counter
    ok = 0
    rows = []
    for fx in FIXTURES:
        rec = verify_event(fx["event"], fx["articles"],
                           quarantine_ids=fx.get("quarantine_ids"))
        status = rec["verification_status"]
        match = status == fx["expect"]
        ok += 1 if match else 0
        rows.append((fx["name"], fx["expect"], status, "PASS" if match else "FAIL"))
    print("%-32s %-16s %-16s %s" % ("fixture", "expect", "actual", "result"))
    for name, exp, act, res in rows:
        print("%-32s %-16s %-16s %s" % (name, exp, act, res))
    print("\nfixture: PASS=%d/%d" % (ok, len(FIXTURES)))
    return ok == len(FIXTURES)


def synth_articles_from_groups(event):
    """Canonical 无关联 articles 时，从 source_groups（来源组名）合成来源记录。

    第一版仅用来源名（tier 由名称关键词判定），URL 留空；
    来源组名中的中文注释（如"苏丹军方背景媒体"）剥离，避免影响名称匹配。
    """
    arts = []
    for g in (event.get("source_groups") or []):
        name = g.split("（")[0].split("(")[0].strip()
        if not name:
            continue
        arts.append({
            "article_id": "ART_synth_%s" % (name[:24]),
            "source_id": "sg_" + name,
            "source_name": name,
            "article_url": "",
            "source_type": "unknown",
            "published_at": event.get("event_time"),
            "detected_country": "",
            "event_country": event.get("country_code"),
            "detected_locations": [],
            "event_type": event.get("event_type"),
            "content_hash": "",
        })
    return arts


def run_dry_run(limit=None, out=None):
    canon = load_json("data/canonical/event_clusters.json", {"items": []})
    articles = load_json("data/canonical/articles.json", {"items": []})
    items = canon.get("items", [])
    arts = articles.get("items", [])
    by_article_event = {}
    for a in arts:
        eid = a.get("linked_event_id")
        if eid:
            by_article_event.setdefault(eid, []).append(a)
    qids = load_quarantine_ids(items)

    print("canonical=%d articles=%d quarantine_ids=%d" % (len(items), len(arts), len(qids)))
    print()
    # 候选：优先非隔离事件（有来源信息或仅正文均可，无来源将如实输出 unverified）；
    # 不足时补隔离事件（展示 R1-quarantined）
    active_cands = [e for e in items
                    if e.get("event_id") not in qids
                    and (by_article_event.get(e.get("event_id"))
                         or e.get("source_groups") or e.get("body_extracted"))]
    quar_cands = [e for e in items
                  if e.get("event_id") in qids
                  and by_article_event.get(e.get("event_id"))]
    limit = limit or 15
    pick = list(active_cands[:limit])
    if len(pick) < limit:
        pick += quar_cands[:limit - len(pick)]

    rows = []
    for ev in pick:
        ev_arts = by_article_event.get(ev.get("event_id"), [])
        if not ev_arts:
            ev_arts = synth_articles_from_groups(ev)
        rec = verify_event(ev, ev_arts, quarantine_ids=qids)
        rows.append({
            "event_id": rec["event_id"],
            "verification_status": rec["verification_status"],
            "verification_confidence": rec["verification_confidence"],
            "source_count": rec["source_count"],
            "independent_source_count": rec["independent_source_count"],
            "official_source_count": rec["official_source_count"],
            "source_tiers": rec["source_trust_summary"]["tier_counts"],
            "reasons": rec["verification_reasons"],
        })
        print("%-22s %-14s conf=%-3d src=%d indep=%d tiers=%s" % (
            rec["event_id"], rec["verification_status"],
            rec["verification_confidence"], rec["source_count"],
            rec["independent_source_count"],
            rec["source_trust_summary"]["tier_counts"]))

    from collections import Counter
    dist = Counter(r["verification_status"] for r in rows)
    print("\ndry-run: events=%d status_distribution=%s" % (len(rows), dict(dist)))

    if out:
        op = ROOT / out
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(json.dumps({"count": len(rows), "rows": rows},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
        print("written: %s" % op)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description="ASIP Stage 5 事件核实 CLI")
    ap.add_argument("--fixtures", action="store_true", help="运行确定性 fixtures")
    ap.add_argument("--dry-run", action="store_true", help="真实 canonical dry-run")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=None, help="dry-run 结果输出路径（默认不写）")
    args = ap.parse_args(argv)

    if args.fixtures:
        return 0 if run_fixtures() else 2
    if args.dry_run:
        return 0 if run_dry_run(args.limit, args.out) else 2
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
