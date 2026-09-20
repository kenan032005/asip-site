#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report_ai.py — C4-C 报告 AI enrichment（真实 DeepSeek analysis，server-side only）。

复用既有报告 AI 资产，不另造一套：
  * prompt        → scripts.report.gen.analysis_contract.build_analysis_prompt
  * 分析事实闸门  → scripts.report.gen.analysis_contract.validate_analysis
  * 机器闸门      → scripts.report.gen.deterministic_assembler.machine_gates
  * provider      → scripts.report.gen.providers.make_provider（auto → 有 key 用 DeepSeek）

策略：
  * **LOW_DATA 不调用 AI**（保持确定性报告，绝不为凑数强调）
  * SOURCE_BACKED_ONLY 不变：AI fact pack 只含 source-backed facts
  * cache = artifact 自身：status=FULL 且 input_hash 一致 → 命中（0 调用）
    负缓存 = artifact 记录 ai_negative_input_hash（gate 拒绝的终态，0 调用）
  * 每份报告最多 1 次 analysis call
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.report import factory as F                      # noqa: E402
from scripts.report import materialize as M                  # noqa: E402
from scripts.report.gen import analysis_contract as AC       # noqa: E402
from scripts.report.gen import deterministic_assembler as DA  # noqa: E402
from scripts.report.gen import providers as P                # noqa: E402

PROMPT_VERSION = "analysis-v1.0.0"
MODEL = "deepseek-flash"
AI_FIELDS = ("executive_assessment", "trend_analysis", "outlook", "watch_points")

STATUS_FULL = "FULL"
STATUS_FALLBACK = "FALLBACK"
STATUS_LOW_DATA = "LOW_DATA"
STATUS_FAIL = "FAIL"


def ai_input_hash(report_id, fact_pack_hash, model=MODEL, prompt_version=PROMPT_VERSION):
    return F.input_hash(report_id, fact_pack_hash, model, "report_analysis", prompt_version)


# ── §五 Target Planner（只读）─────────────────────────────────────────────
def plan_targets(root):
    """计算 AI 目标：只有「非 LOW_DATA + 有事实 + 无合法 cache」才需要调用。"""
    reports = M.list_report_artifacts(root)
    low, eligible, cached, negative = [], [], [], []
    for r in reports:
        st = r.get("status")
        nfacts = r.get("fact_count") or 0
        if st == STATUS_LOW_DATA:
            low.append(r)
            continue
        if not nfacts:
            low.append(r)
            continue
        ih = ai_input_hash(r.get("report_id"), r.get("fact_pack_hash"))
        if st == STATUS_FULL and r.get("ai_input_hash") in (None, ih):
            cached.append(r)
            continue
        if r.get("ai_negative_input_hash") == ih:
            negative.append(r)
            continue
        eligible.append(r)
    return {
        "TOTAL_REPORTS": len(reports),
        "LOW_DATA_REPORTS": len(low),
        "ALREADY_CACHED_REPORTS": len(cached),
        "NEGATIVE_CACHED_REPORTS": len(negative),
        "FULL_ELIGIBLE_REPORTS": len(eligible),
        "AI_TARGET_REPORTS": len(eligible),
        "EXPECTED_REAL_AI_CALLS_MAX": len(eligible),
        "target_ids": [r.get("report_id") for r in eligible],
        "low_data_ids": [r.get("report_id") for r in low],
    }


# ── fact pack 重建（确定性；hash 必须与 artifact 一致）──────────────────
def rebuild_fact_pack(root, report):
    """按报告期重建 fact pack；返回 (pack, hash)。hash 与 artifact 不一致视为 DIRTY。"""
    rtype = report.get("report_type")
    events = M.load_canonical_events(root)
    disease = M.load_disease_items(root)
    iso = M.iso2to3_map(root)
    if rtype == "africa_daily":
        tgt = {"report_date": report.get("report_date") or str(report.get("period_end"))[:10],
               "report_id": report.get("report_id")}
        _rep, fp = M.materialize_daily(root, tgt, events, disease, iso)
        return fp, F.fact_pack_hash(fp)
    if rtype == "africa_weekly":
        wk = {"report_id": report.get("report_id"), "week_start": report.get("week_start"),
              "week_end": report.get("week_end")}
        _rep, fp = M.materialize_africa_weekly(root, wk, events, disease, iso)
        return fp, F.fact_pack_hash(fp)
    if rtype == "country_weekly":
        tgt = {"report_id": report.get("report_id"), "country_iso3": report.get("country_iso3"),
               "week_start": report.get("week_start"), "week_end": report.get("week_end"),
               "selection_reason": report.get("selection_reason")}
        _rep, fp = M.materialize_country_weekly(root, tgt, events, disease, iso)
        return fp, F.fact_pack_hash(fp)
    return None, None


def _unattributed_in_pack(fp):
    """§十二：AI fact pack 里不得出现无来源事实。"""
    n = 0
    for f in (fp.get("social_facts") or []) + (fp.get("disease_facts") or []):
        if not (f.get("source_refs") or []):
            n += 1
    return n


# ── 单份报告 enrichment ─────────────────────────────────────────────────
def enrich_one(root, report, provider=None, write=True, fact_pack=None):
    """返回 (outcome_dict)。outcome: SKIPPED_LOW_DATA / CACHED_FULL / CACHED_NEGATIVE /
    CALLED_FULL / CALLED_FALLBACK / FACT_PACK_DIRTY。"""
    rid = report.get("report_id")
    st = report.get("status")
    out = {"report_id": rid, "old_status": st, "ai_call": 0, "gate_result": None,
           "new_status": st, "report_type": report.get("report_type")}

    if st == STATUS_LOW_DATA or not (report.get("fact_count") or 0):
        out["outcome"] = "SKIPPED_LOW_DATA"          # §四
        return out

    if fact_pack is not None:
        fp, fph = fact_pack, F.fact_pack_hash(fact_pack)
    else:
        fp, fph = rebuild_fact_pack(root, report)
    if fp is None:
        out["outcome"] = "FACT_PACK_DIRTY"
        out["gate_result"] = "NO_FACT_PACK"
        return out
    if fph != report.get("fact_pack_hash"):
        out["outcome"] = "FACT_PACK_DIRTY"
        out["gate_result"] = "HASH_MISMATCH"
        out["expected_hash"] = report.get("fact_pack_hash")
        out["rebuilt_hash"] = fph
        return out

    ih = ai_input_hash(rid, fph)
    if st == STATUS_FULL and report.get("ai_input_hash") in (None, ih):
        out["outcome"] = "CACHED_FULL"               # §七
        return out
    if report.get("ai_negative_input_hash") == ih:
        out["outcome"] = "CACHED_NEGATIVE"           # §八
        return out

    prov = provider or P.make_provider()
    sys_text, user_text = AC.build_analysis_prompt(fp, max_facts=12)
    task = {"task_id": "REPORT_AI_%s" % rid, "task_type": "report_analysis",
            "prompt_version": PROMPT_VERSION, "system_text": sys_text,
            "user_text": user_text, "usage_purpose": "report_materialization",
            "max_output_tokens": 1024}
    res = prov.submit_task(task)
    out["ai_call"] = 1
    rr = (res or {}).get("result") or {}
    raw = rr.get("text") or ""
    if (res or {}).get("status") != "succeeded":
        out["outcome"] = "CALLED_FALLBACK"
        out["gate_result"] = "PROVIDER_FAILED"
        out["error"] = ((rr.get("error") or {}).get("code")) or "provider_failed"
        _persist(root, report, write, extra={"ai_negative_input_hash": None,
                                             "ai_last_error": out["error"]})
        return out

    okp, parsed, jerr = _strict_json(raw)
    if not okp:
        out["outcome"] = "CALLED_FALLBACK"
        out["gate_result"] = "SCHEMA_FAILURE"
        out["error"] = jerr
        _persist(root, report, write, extra={"ai_negative_input_hash": ih,
                                             "ai_negative_reason": "SCHEMA_FAILURE"})
        return out

    ok, errs = AC.validate_analysis(parsed, fp)          # Fact / Attribution gate
    if ok:
        out["gate_result"] = "PASS"
    else:
        # 区分「结构不合规」与「事实越界」——两者都拒绝，但诊断口径不同
        schema_only = bool(errs) and all(str(e).startswith("analysis schema:") for e in errs)
        out["gate_result"] = "SCHEMA_FAILURE" if schema_only else "FACT_GATE_REJECTED"
    if not ok:
        out["outcome"] = "CALLED_FALLBACK"
        out["gate_errors"] = errs[:5]
        _persist(root, report, write, extra={"ai_negative_input_hash": ih,
                                             "ai_negative_reason": out["gate_result"]})
        return out

    merged = dict(report)
    for k in AI_FIELDS:
        merged[k] = parsed.get(k)
    merged["status"] = STATUS_FULL
    merged["ai_input_hash"] = ih
    merged["ai_model"] = MODEL
    merged["ai_prompt_version"] = PROMPT_VERSION
    merged["report_status_cn"] = M._status_cn(STATUS_FULL)
    if merged.get("report_type") == "country_weekly":
        merged["executive_assessment"] = parsed.get("executive_assessment")
        merged["security_trend"] = parsed.get("trend_analysis")
        merged["next_week_watch_items"] = parsed.get("watch_points") or []
    merged["overall_assessment"] = parsed.get("executive_assessment")
    out["outcome"] = "CALLED_FULL"
    out["new_status"] = STATUS_FULL
    _persist(root, merged, write)
    return out


def _strict_json(raw):
    t = (raw or "").strip()
    if not t:
        return False, None, "empty_content"
    if t.startswith("```"):
        t = t.strip("`")
        t = t.split("\n", 1)[1] if "\n" in t else t
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        t = t[i:j + 1]
    try:
        return True, json.loads(t), None
    except Exception as e:  # noqa: BLE001
        return False, None, "invalid_json:%s" % type(e).__name__


def _persist(root, report, write, extra=None):
    if not write:
        return
    doc = dict(report)
    if extra:
        doc.update({k: v for k, v in extra.items() if v is not None})
    M.write_report_artifact(root, report.get("report_type"), doc)


# ── 批量 ────────────────────────────────────────────────────────────────
def enrich_all(root, provider=None, write=True, limit=None, fact_pack_map=None):
    plan = plan_targets(root)
    stats = {"TOTAL_REPORTS": plan["TOTAL_REPORTS"],
             "LOW_DATA_REPORTS": plan["LOW_DATA_REPORTS"],
             "AI_TARGET_REPORTS": plan["AI_TARGET_REPORTS"],
             "EXPECTED_REAL_AI_CALLS_MAX": plan["EXPECTED_REAL_AI_CALLS_MAX"],
             "AI_CALLS_TOTAL": 0, "AI_CALLS_DAILY": 0, "AI_CALLS_AFRICA_WEEKLY": 0,
             "AI_CALLS_COUNTRY_WEEKLY": 0, "FULL": 0, "FALLBACK": 0,
             "LOW_DATA": 0, "FAIL": 0, "FACT_GATE_REJECTIONS": 0,
             "ATTRIBUTION_GATE_REJECTIONS": 0, "UNATTRIBUTED_FACTS_IN_AI_FACT_PACK": 0,
             "outcomes": {}}
    prov = provider or P.make_provider()
    ids = plan["target_ids"][:limit] if limit else plan["target_ids"]
    key = {"africa_daily": "AI_CALLS_DAILY", "africa_weekly": "AI_CALLS_AFRICA_WEEKLY",
           "country_weekly": "AI_CALLS_COUNTRY_WEEKLY"}
    for rid in ids:
        rtype = None
        for t in ("africa_daily", "africa_weekly", "country_weekly"):
            r = M.read_report_artifact(root, t, rid)
            if r:
                rtype = t
                rep = r
                break
        if not rtype:
            continue
        if fact_pack_map and rid in fact_pack_map:
            fp = fact_pack_map[rid]
        else:
            fp, _ = rebuild_fact_pack(root, rep)
        if fp:
            stats["UNATTRIBUTED_FACTS_IN_AI_FACT_PACK"] += _unattributed_in_pack(fp)
        o = enrich_one(root, rep, provider=prov, write=write,
                       fact_pack=(fact_pack_map or {}).get(rid))
        stats["outcomes"][o["outcome"]] = stats["outcomes"].get(o["outcome"], 0) + 1
        stats["AI_CALLS_TOTAL"] += o["ai_call"]
        if o["ai_call"]:
            stats[key.get(rtype, "AI_CALLS_TOTAL")] += 1
        if o["gate_result"] == "FACT_GATE_REJECTED":
            stats["FACT_GATE_REJECTIONS"] += 1
        if o["gate_result"] == "ATTRIBUTION_GATE_REJECTED":
            stats["ATTRIBUTION_GATE_REJECTIONS"] += 1
    # 终态统计（以 artifact 为准）
    import collections
    c = collections.Counter(r.get("status") for r in M.list_report_artifacts(root))
    stats["FULL"] = c.get(STATUS_FULL, 0)
    stats["FALLBACK"] = c.get(STATUS_FALLBACK, 0)
    stats["LOW_DATA"] = c.get(STATUS_LOW_DATA, 0)
    stats["FAIL"] = c.get(STATUS_FAIL, 0)
    return stats


def _cli():
    import argparse
    ap = argparse.ArgumentParser(description="C4-C report AI enrichment (server-side)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--provider", default=None, help="auto|mock|deepseek")
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=None, help="把统计写入该 JSON（供幂等校验）")
    a = ap.parse_args()
    if a.plan_only:
        print(json.dumps(plan_targets(a.root), ensure_ascii=False, indent=1))
        return 0
    prov = P.make_provider(a.provider)
    ready = bool(getattr(prov, "api_key", "") or a.provider == "mock")
    if a.dry_run and not ready:
        print(json.dumps({"provider_ready": False, "AI_CALLS": 0,
                          "plan": plan_targets(a.root)}, ensure_ascii=False, indent=1))
        return 0
    st = enrich_all(a.root, provider=prov, write=not a.dry_run, limit=a.limit)
    if a.out:
        with io.open(a.out, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=1)
    print(json.dumps(st, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
