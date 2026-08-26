#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6A — Golden Set 评估（§十六）：24 对 fixture 期望值 PASS/FAIL。

期望映射：
  duplicate        → dedup_articles 判为 duplicate
  same_event       → 非 duplicate、hard reject 通过、score>=auto(75)
  different_event  → hard reject 或 verdict==separate
  needs_review     → verdict==review（55-74）
"""

import json
import sys
import time

from .dedup import dedup_articles
from .scoring import hard_reject, score_pair
from .cluster import compare_to_anchor, THRESHOLDS
from .golden import build_fixture_pairs


def evaluate_pair(a, b, expected):
    """单对评估 → (ok, detail)。"""
    # 1) duplicate
    unique, dups = dedup_articles([dict(a), dict(b)])
    is_dup = len(unique) == 1
    if expected == "duplicate":
        return is_dup, {"dedup": is_dup}
    if is_dup:
        return False, {"dedup": True, "expected": expected}

    # 2) same-event path
    res = compare_to_anchor(a, b)
    if expected == "different_event":
        ok = res["rejected"] or res["verdict"] == "separate"
        return ok, {"hard_reject": res["rejected"], "reason": res["reason"],
                    "score": res["score"], "verdict": res["verdict"]}
    if expected == "same_event":
        ok = (not res["rejected"]) and res["score"] >= THRESHOLDS["auto"]
        return ok, {"hard_reject": res["rejected"], "reason": res["reason"],
                    "score": res["score"], "verdict": res["verdict"],
                    "features": res["features"], "conflicts": res["conflict_flags"]}
    if expected == "needs_review":
        ok = (not res["rejected"]) and res["verdict"] == "review"
        return ok, {"hard_reject": res["rejected"], "reason": res["reason"],
                    "score": res["score"], "verdict": res["verdict"],
                    "features": res["features"]}
    return False, {"error": "unknown expected %s" % expected}


def run_golden(verbose=False):
    pairs = build_fixture_pairs()
    results = []
    passed = 0
    for pair_id, a, b, expected in pairs:
        ok, detail = evaluate_pair(a, b, expected)
        results.append({"pair_id": pair_id, "expected": expected, "pass": ok,
                        "detail": detail})
        if ok:
            passed += 1
        if verbose:
            print("%-3s %-32s expected=%-15s score=%s verdict=%s reject=%s %s" % (
                "OK" if ok else "FAIL", pair_id, expected,
                detail.get("score"), detail.get("verdict"),
                detail.get("hard_reject"), detail.get("reason") or ""))
    return {"total": len(results), "passed": passed,
            "failed": len(results) - passed, "results": results}


if __name__ == "__main__":
    r = run_golden(verbose=True)
    print("GOLDEN: %d/%d PASS" % (r["passed"], r["total"]))
    for res in r["results"]:
        if not res["pass"]:
            print("  FAIL %s expected=%s detail=%s" % (
                res["pair_id"], res["expected"], json.dumps(res["detail"], ensure_ascii=False)))
    sys.exit(0 if r["failed"] == 0 else 1)
