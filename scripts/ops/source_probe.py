#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C7-4R P9 — 新源有界诊断：逐源探测（reachable / listing 耗时 / 解析条目数）。

全部请求使用有界超时（connect+read），失败如实记录，绝不阻塞整体运行。
用法：python scripts/ops/source_probe.py [source_id ...]
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TIMEOUT = 25
UA = "Mozilla/5.0 (compatible; ASIP-collector/1.0)"
DEFAULT = ["pan_allafrica", "pan_unnews_africa", "pan_africanews", "nga_premiumtimes",
           "pan_france24_africa", "gha_myjoyonline", "rwa_newtimes", "pan_reliefweb",
           "pan_bbc_africa", "pan_aljazeera"]


def fetch(url, timeout=TIMEOUT):
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(400000).decode("utf-8", "replace")
            return {"status": r.status, "seconds": round(time.time() - t0, 1),
                    "bytes": len(body), "body": body, "error": ""}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "seconds": round(time.time() - t0, 1),
                "bytes": 0, "body": "", "error": "HTTPError: %s" % e}
    except Exception as e:  # noqa: BLE001
        return {"status": None, "seconds": round(time.time() - t0, 1),
                "bytes": 0, "body": "", "error": "%s: %s" % (type(e).__name__, str(e)[:80])}


def count_items(body, kind):
    if not body:
        return 0
    if kind in ("rss", "atom", "rdf"):
        return body.count("<item") + body.count("<entry")
    return body.count("<a ")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("source_ids", nargs="*", default=DEFAULT)
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    args = ap.parse_args(argv)
    srcs = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))["sources"]
    idx = {s["source_id"]: s for s in srcs}
    out = []
    print("%-22s %-8s %-8s %-9s %s" % ("source_id", "http", "sec", "items", "detail"))
    for sid in args.source_ids:
        s = idx.get(sid)
        if not s:
            print("%-22s %s" % (sid, "NOT_IN_REGISTRY"))
            out.append({"source_id": sid, "error": "not_in_registry"})
            continue
        url = (s.get("listing_urls") or [s.get("url")])[0]
        kind = "rss" if (s.get("source_type") != "html_listing") else "html"
        r = fetch(url, args.timeout)
        n = count_items(r["body"], "rss" if url.endswith((".xml", ".rdf")) or "<rss" in r["body"][:400]
                        or "<feed" in r["body"][:400] else "html")
        parsed = n > 0
        print("%-22s %-8s %-8s %-9s %s" % (sid, r["status"], r["seconds"], n,
                                           r["error"] or ("parsed_ok" if parsed else "no_items_parsed")))
        out.append({"source_id": sid, "url": url, "http": r["status"],
                    "seconds": r["seconds"], "bytes": r["bytes"],
                    "items_parsed": n, "parsed": parsed,
                    "reachable": r["status"] is not None,
                    "failure_reason": r["error"] or ("" if parsed else "no_items_parsed")})
    ok = sum(1 for o in out if o.get("reachable") and o.get("parsed"))
    print()
    print("REACHABLE_AND_PARSED = %d / %d" % (ok, len(out)))
    print(json.dumps({"schema": "c7r4r-source-probe-v1",
                      "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "results": out}, ensure_ascii=False, indent=1)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
