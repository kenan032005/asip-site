#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_sources.py — 来源全面审计。

对 data/sources.json 中所有来源执行可达性/可用性检查，输出分类：
  active_and_usable / active_but_low_value / temporarily_unreachable /
  permanently_broken / duplicate_source / not_relevant / not_implemented

用法：
  python scripts/audit_sources.py            # 完整审计（网络检查）
  python scripts/audit_sources.py --offline # 仅静态审计（不访问网络）
"""
import os
import sys
import json
import time
import socket
import argparse
import concurrent.futures
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SOURCES_PATH = os.path.join(DATA, "sources.json")
OUT_PATH = os.path.join(ROOT, "logs", "source_health.json")

UA = ("Mozilla/5.0 (compatible; ASIP-Auditor/1.0; "
      "+https://github.com/kenan032005/asip-site)")
TIMEOUT = 12

# GDELT 搜索依赖 api.gdeltproject.org（限流 20s），标记为 not_implemented 分开统计
GDELT_HOST = "api.gdeltproject.org"


def check_url(url, timeout=TIMEOUT):
    """返回 (status, error)。status: ok / http_xxx / timeout / error / denied"""
    if not url:
        return "empty", "no_url"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return f"ok", f"http_{r.status}"
    except urllib.error.HTTPError as e:
        if e.code in (403, 401):
            return "denied", f"http_{e.code}"
        return "http_err", f"http_{e.code}"
    except urllib.error.URLError as e:
        reason = str(e.reason) if hasattr(e, "reason") else str(e)
        if isinstance(reason, str) and "timed out" in reason.lower():
            return "timeout", reason[:60]
        if isinstance(reason, str) and "Name or service not known" in reason.lower():
            return "dns_fail", reason[:60]
        if isinstance(reason, str) and "certificate" in reason.lower():
            return "tls_fail", reason[:60]
        return "error", reason[:60]
    except socket.timeout:
        return "timeout", "socket_timeout"
    except Exception as e:
        return "error", str(e)[:60]


def classify_source(s, offline=False):
    """对单个来源做审计。返回分类字典。"""
    lp = s.get("legacy_payload", {})
    sid = s.get("source_id", "")
    name = s.get("source_name", lp.get("name", ""))
    country = lp.get("country", s.get("country_scope", [""])[0] if s.get("country_scope") else "")
    stype = lp.get("source_type", s.get("source_type", ""))
    language = lp.get("language", "")
    method = lp.get("collection_method", "")
    feed_url = lp.get("feed_url", "")
    url = lp.get("url", s.get("url", ""))
    enabled = lp.get("enabled", s.get("enabled", False))
    last_success = lp.get("last_success_at", "")
    last_failure = lp.get("last_failure_at", "")
    failure_count = lp.get("failure_count", 0)

    entry = {
        "source_id": sid, "source_name": name, "country": country,
        "source_type": stype, "language": language, "collection_method": method,
        "feed_url": feed_url, "url": url, "enabled": enabled,
        "last_success_at": last_success, "last_failure_at": last_failure,
        "failure_count": failure_count, "category": "", "status": "",
        "http_status": "", "detail": "",
    }

    # GDELT 搜索：单独标记（依赖聚合器 API，非独立来源）
    if method == "gdelt_search":
        entry["category"] = "not_implemented"
        entry["status"] = "gdelt_mapped"
        entry["detail"] = "GDELT 域名映射，非独立来源；未纳入实时采集"
        return entry

    # 禁用来源
    if not enabled:
        entry["category"] = "not_relevant"
        entry["status"] = "disabled"
        entry["detail"] = "disabled in registry"
        return entry

    if offline:
        entry["category"] = "active_and_usable" if method in ("rss", "reliefweb_api") else "not_implemented"
        entry["status"] = "static_only"
        return entry

    # 网络检查：优先 feed_url，其次 url
    target = feed_url or url
    status, detail = check_url(target)
    entry["status"] = status
    entry["detail"] = detail

    if status == "ok":
        if method in ("rss", "reliefweb_api"):
            entry["category"] = "active_and_usable"
        elif method == "html_list":
            entry["category"] = "active_and_usable"
        else:
            entry["category"] = "active_but_low_value"
    elif status in ("timeout", "dns_fail", "tls_fail", "error", "http_err"):
        # 有历史成功记录 → 临时失败；否则永久失败
        if last_success and not last_failure:
            entry["category"] = "temporarily_unreachable"
        else:
            entry["category"] = "permanently_broken"
    elif status == "denied":
        entry["category"] = "temporarily_unreachable"
        entry["detail"] += " (403/401 可能需要JS或受限)"
    elif status == "empty":
        entry["category"] = "permanently_broken"
        entry["detail"] = "no URL configured"

    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="静态审计（不访问网络）")
    ap.add_argument("--limit", type=int, default=0, help="限制检查数量（0=全部）")
    args = ap.parse_args()

    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        doc = json.load(f)
    sources = doc.get("sources", [])

    print(f"审计开始: {len(sources)} 个来源" + ("（离线）" if args.offline else ""))
    print("=" * 70)

    results = []
    # 并行检查（避免长时间串行）
    to_check = sources if args.limit == 0 else sources[:args.limit]
    if args.offline:
        results = [classify_source(s, offline=True) for s in to_check]
    else:
        # 有 feed_url 的先检查 feed；纯 GDELT 的直接分类
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            futures = {ex.submit(classify_source, s): s for s in to_check}
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())

    # 分类统计
    from collections import Counter
    cats = Counter(r["category"] for r in results)
    print("\n=== 分类统计 ===")
    for c in sorted(cats, key=lambda c: -cats[c]):
        print(f"  {c:32s}: {cats[c]}")
    print(f"  {'TOTAL':32s}: {len(results)}")

    # 输出明细（按国家）
    for country in ("乍得", "尼日尔"):
        print(f"\n=== {country} 来源明细 ===")
        for r in results:
            if r["country"] != country:
                continue
            flag = {"active_and_usable": "✅", "active_but_low_value": "◐",
                    "temporarily_unreachable": "⚠️", "permanently_broken": "❌",
                    "duplicate_source": "dup", "not_relevant": "✖",
                    "not_implemented": "⚙️"}.get(r["category"], "?")
            print(f"  {flag} [{r['category'][:22]:22s}] {r['source_id']:26s} {r['status']:10s} {r['detail'][:40]}")

    # 保存报告
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "configured_sources": len(sources),
        "category_counts": dict(cats),
        "sources": results,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
