#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Global Source Layer — A 包 detail extraction 补检（§二，Source Expansion B）。

对 Source Expansion A listing 成功的 Global Sources 做真实 detail 抽检
（每 source 最多 2 篇）：title/published_at/canonical_url/body/body_length/
language/source_id。只写 runtime audit；不写 Canonical/Public。
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.global_source.registry import load_registry
from scripts.global_source.adapters import collect_source
from scripts.global_source.detail import detail_extract
from scripts.global_source.health import record_health

AUDIT_PATH = ROOT / "data" / "runtime" / "global_detail_audit.json"
PER_SOURCE = 2


def main(argv=None):
    ap = argparse.ArgumentParser(description="Global A detail 补检")
    ap.add_argument("--per-source", type=int, default=PER_SOURCE)
    args = ap.parse_args(argv)

    sources, errs = load_registry()
    if errs:
        print("registry errors:", errs)
        return 2

    audit = {"run_id": time.strftime("GDET%Y%m%dT%H%M%S+0800"),
             "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
             "per_source": {}, "stats": {}}
    healths = []
    detail_success = {}

    for src in sources:
        sid = src["source_id"]
        if not src.get("enabled", False):
            continue
        items, health = collect_source(src, max_items=10)
        healths.append(health)
        if health["listing_status"] != "success" or not items:
            audit["per_source"][sid] = {"listing": health["listing_status"],
                                        "failure_type": health["failure_type"],
                                        "detail_skipped": True}
            continue
        per = {"listing": "success", "detail_success": 0, "detail_failed": 0,
               "samples": []}
        for it in items[:args.per_source]:
            d = detail_extract(it.get("url") or "", sid,
                               language_hint=src.get("language", [""])[0])
            rec = {k: d.get(k) for k in
                   ("source_id", "canonical_url", "title", "published_at",
                    "body_length", "language", "detail_success", "failure_type")}
            if d["detail_success"]:
                rec["body_preview"] = (d.get("body_extracted") or "")[:120]
                per["detail_success"] += 1
                detail_success[sid] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
            else:
                per["detail_failed"] += 1
            per["samples"].append(rec)
        audit["per_source"][sid] = per

    audit["stats"] = {
        "sources_checked": len(audit["per_source"]),
        "detail_success": sum(v.get("detail_success", 0) for v in audit["per_source"].values()
                              if isinstance(v, dict)),
        "detail_failed": sum(v.get("detail_failed", 0) for v in audit["per_source"].values()
                             if isinstance(v, dict)),
    }
    record_health(healths, scope="global", last_detail=detail_success)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    print(json.dumps(audit["stats"], ensure_ascii=False, indent=2))
    for sid, v in audit["per_source"].items():
        if isinstance(v, dict) and "samples" in v:
            print("  %-26s ok=%d fail=%d" % (sid, v["detail_success"], v["detail_failed"]))
        else:
            print("  %-26s %s" % (sid, v))
    print("audit written: %s" % AUDIT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
