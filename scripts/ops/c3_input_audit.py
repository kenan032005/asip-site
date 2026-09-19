#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c3_input_audit.py —— mode-aware AI 输入审计（C3F §三–§九）。

背景：full/first materialization 的审计把「任何既有 AI 产物」都当成污染，
于是在 c3f_incremental（设计上必须读取既有真实 AI 状态）里误报：
`stale FULL artifact` → STUB_AI_INPUT_CONTAMINATION > 0 → 真实 AI 从未开始。

正确语义：**既有真实 AI 状态 ≠ 污染**。按 provenance 分类：

  REAL_VALIDATED_PRIOR_OUTPUT  真实模型产物（model ∈ canonical/allowed 且 schema 完整）→ 允许作 prior state
  STALE_REAL_PRIOR_OUTPUT      真实产物但输入指纹已失效（例如 fact pack 变了）→ 允许，且标 dirty
  STUB_OUTPUT                  桩产物                          → **拒绝**
  SIMULATION_OUTPUT            模拟产物                        → **拒绝**
  UNKNOWN_PROVENANCE           缺 model/schema 等溯源字段      → **拒绝**（fail closed）

FULL 模式保持原有严格政策（不得带任何既有 AI 产物）。
C3F_INCREMENTAL 允许 REAL_*/STALE_REAL_* 存在，但 stub/simulation/unknown 依然 fail closed。
"""
import argparse
import io
import json
import os
import sys

REAL_MODELS = frozenset({"deepseek-flash", "deepseek-v4-flash"})
REJECTED = ("STUB_OUTPUT", "SIMULATION_OUTPUT", "UNKNOWN_PROVENANCE")
ALLOWED_PRIOR = ("REAL_VALIDATED_PRIOR_OUTPUT", "STALE_REAL_PRIOR_OUTPUT")

SECTIONS = ("localization", "event_analysis", "country_analysis", "homepage_analysis")


def _load(p):
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return None


def classify_provenance(rec):
    """单条 artifact 的 provenance 分类（缺溯源字段一律 UNKNOWN → fail closed）。"""
    if not isinstance(rec, dict):
        return "UNKNOWN_PROVENANCE"
    model = str(rec.get("model") or "").strip().lower()
    blob = json.dumps(rec, ensure_ascii=False).lower()
    if "simulation" in blob or "simulated" in blob:
        return "SIMULATION_OUTPUT"
    if model in ("stub", "mock", "fake") or "stub_provider" in blob or '"behavior": "stub' in blob:
        return "STUB_OUTPUT"
    # 真实产物必须同时具备 model(合法) + schema_version + prompt_version + input_hash
    if (model in REAL_MODELS and rec.get("schema_version")
            and rec.get("prompt_version") and rec.get("input_hash")):
        return "REAL_VALIDATED_PRIOR_OUTPUT"
    if model and model not in REAL_MODELS:
        return "UNKNOWN_PROVENANCE"
    return "UNKNOWN_PROVENANCE"


def current_homepage_fact_pack_hash(root):
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ai"))
        import c3_analysis as A
        return A.pack_hash(A.build_homepage_fact_pack_from_views(root))
    except Exception:  # noqa: BLE001
        return None


def audit(root, mode, require_full_window=True):
    root = str(root)
    ai = os.path.join(root, "data", "intelligence", "ai")
    counts = {k: 0 for k in ("REAL_VALIDATED_PRIOR_OUTPUT", "STALE_REAL_PRIOR_OUTPUT",
                             "STUB_OUTPUT", "SIMULATION_OUTPUT", "UNKNOWN_PROVENANCE")}
    by_section = {}
    stale_homepage = False
    cur_hash = current_homepage_fact_pack_hash(root)

    for sec in SECTIONS:
        d = os.path.join(ai, sec)
        if not os.path.isdir(d):
            continue
        n = 0
        for fn in os.listdir(d):
            if not fn.endswith(".json"):
                continue
            rec = _load(os.path.join(d, fn))
            kind = classify_provenance(rec)
            counts[kind] = counts.get(kind, 0) + 1
            n += 1
            if sec == "homepage_analysis" and kind == "REAL_VALIDATED_PRIOR_OUTPUT":
                if rec.get("fact_pack_hash") != cur_hash:
                    counts["REAL_VALIDATED_PRIOR_OUTPUT"] -= 1
                    counts["STALE_REAL_PRIOR_OUTPUT"] += 1
                    stale_homepage = True
        by_section[sec] = n

    # runs/ 下的 ci_status 与 run report 属于审计证据，不计入产物计数
    prior_total = sum(counts[k] for k in ALLOWED_PRIOR)
    bad_total = sum(counts[k] for k in REJECTED)

    incremental = (mode == "c3f_incremental")

    out = {
        "schema": "c3f-input-audit-v1",
        "mode": mode,
        "PREEXISTING_REAL_AI_ARTIFACTS": prior_total,
        "STALE_REAL_AI_ARTIFACTS": counts["STALE_REAL_PRIOR_OUTPUT"],
        "STUB_AI_INPUT_CONTAMINATION": counts["STUB_OUTPUT"],
        "SIMULATION_AI_INPUT_CONTAMINATION": counts["SIMULATION_OUTPUT"],
        "UNKNOWN_AI_PROVENANCE": counts["UNKNOWN_PROVENANCE"],
        "HOMEPAGE_REFRESH_REQUIRED": bool(stale_homepage),
        "HOMEPAGE_DIRTY": bool(stale_homepage),
        "homepage_fact_pack_hash_current": cur_hash,
        "provenance_counts": counts,
        "by_section": by_section,
    }

    # 文章语料检查（两种模式都做）
    arts = _load(os.path.join(root, "data", "canonical", "articles.json")) or {}
    items = arts.get("items") or []
    in_win = sum(1 for x in items
                 if "2026-09-05" <= (x.get("published_at") or "")[:10] <= "2026-09-18")
    out["articles"] = len(items)
    out["articles_in_window"] = in_win

    violations = []
    if not items:
        violations.append("empty authoritative article store")
    if require_full_window and in_win == 0:
        violations.append("no in-window articles: wrong corpus for the leadership window")
    if bad_total:
        violations.append("rejected-provenance AI artifacts present: %s"
                          % {k: counts[k] for k in REJECTED if counts[k]})

    if not incremental:
        # FULL / 首次 materialization：保持原有严格政策——不得带任何既有 AI 产物
        if prior_total:
            violations.append("full mode requires an AI-clean tree "
                              "(found %d prior artifacts)" % prior_total)
        out["policy"] = "STRICT_FULL"
    else:
        out["policy"] = "INCREMENTAL_PRIOR_STATE_ALLOWED"

    out["violations"] = violations
    out["ok"] = not violations
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--mode", default=os.environ.get("C3F_MODE", "c3f_incremental"))
    ap.add_argument("--require-full-window", action="store_true", default=True)
    a = ap.parse_args()
    res = audit(a.root, a.mode, a.require_full_window)
    for k in ("mode", "policy", "PREEXISTING_REAL_AI_ARTIFACTS", "STALE_REAL_AI_ARTIFACTS",
              "STUB_AI_INPUT_CONTAMINATION", "SIMULATION_AI_INPUT_CONTAMINATION",
              "UNKNOWN_AI_PROVENANCE", "HOMEPAGE_REFRESH_REQUIRED", "HOMEPAGE_DIRTY",
              "articles", "articles_in_window"):
        print("%-38s = %s" % (k, res.get(k)))
    print("%-38s = %s" % ("provenance_counts", json.dumps(res["provenance_counts"], ensure_ascii=False)))
    if res["violations"]:
        print("INPUT_AUDIT = FAIL")
        for v in res["violations"]:
            print("  -", v)
        return 1
    print("INPUT_AUDIT = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
