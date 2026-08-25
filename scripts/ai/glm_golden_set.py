#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP AI Provider Migration — GLM-4.7-Flash Production Qualification（§十七-§二十）。

样本 20 条（社安 12 + Disease 8），全部为现有 Canonical / Disease Canonical 的真实事件
（非隔离优先；个别类别在非隔离池无匹配时使用真实隔离事件并标注），不伪造 fixture。

分阶段执行（§三/§五）：
  --limit 8   → 社安前 5（disputed allegation / casualty uncertainty / direct security /
                ordinary economic / partial_body）+ 疾病前 3（cholera / mpox / 带数字其他疾病）
  --limit 20  → 全量 20（社安 12：另含 civil unrest / multi-country / ordinary security /
                TCD+NER 补充；疾病 8：另含 measles / meningitis / yellow_fever / 未知数字通报）

执行模式：
  python scripts/ai/glm_golden_set.py --provider glm47_flash [--mock] [--limit 8|20] [--out ...]
  - 真实模式：provider 用 ASIP_GLM_API_KEY（无 Key → credential_status=missing /
    WAITING_FOR_GITHUB_SECRET 安全跳过）；usage_purpose=production_qualification。
  - --mock：mock provider 跑通链路（不联网、不写 Public）。

质量检查（§十九 硬性 + 保守确定性启发）：
  重大事实编造 / 国家错误 / 数字数量级错误 / 疾病名称重大错误 / 争议性指控失去归因 / 
  疾病数字确定性 Evidence Gate / 普通经济新闻不得判 direct / uncertainty 保留。
  语义细节由审计 artifact（含 source_summary + parsed）供人工逐条复核（§四）。

产出：不写 Public、不 deploy、不恢复 schedule；结果存 --out 供审计。
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.registry import get_provider
from scripts.ai.mock_provider import MockProvider
from scripts.ai.schema_validation import validate_against_schema

PAYLOAD_SCHEMA = ROOT / "schemas" / "ai_enrichment_payload.schema.json"

# ── 社安样本：显式选择现有 Canonical 真实事件（非隔离优先，TCD/NER 为主）──
SECURITY_IDS = [
    ("disputed_allegation", "EVT_5291228872082f78"),   # TD 据称归因（attaques de chacals qui pourraient être）
    ("casualty_uncertainty", "EVT_68ba0eb89452a250"),  # TD 不确定伤亡
    ("direct_security", "EVT_15fee76f358f8d07"),       # NE 恐袭（Diffa）
    ("economic_news", "EVT_b3861ba5c8d78187"),         # TD OIM 人道/发展援助（普通非安全）
    ("partial_body", "EVT_8c9d4096815dd33c"),          # TD partial_body
    ("civil_unrest", "EVT_9a551301360773c7"),          # TD 教师罢工（strike）
    ("multi_country", "EVT_1c75828bd994ec7b"),         # TD 霍乱 DREF（区域/多国语境）
    ("ordinary_security", "EVT_451cac52bc310619"),     # TD 武器缴获
    ("supplement_td_salamat", "EVT_0f85e5f42626ce7d"), # TD Salamat 省
    ("supplement_td_cp", "EVT_1c75a026db7edada"),      # TD 新指挥所
    ("supplement_td_ong", "EVT_027bb57061ef0ce3"),     # TD NGO 社区干预
    ("supplement_ng_econ", "EVT_34ab8fae7ab73dd0"),    # NG 经济稳定（真实隔离样本，标注）
]

# ── 疾病样本：显式选择现有 Disease Canonical 真实通报（数字优先 + 未知数字场景）──
DISEASE_IDS = [
    ("disease_cholera", "DSEV_df9984f4005978cb"),          # NGA 2026-07-31 deaths=338
    ("disease_mpox", "DSEV_e1ff7d33d007ad96"),             # COD deaths=122
    ("disease_other_numbers", "DSEV_a2755bd33d02595d"),    # marburg ETH confirmed=14 deaths=14
    ("disease_measles", "DSEV_32e4395421a0cfc2"),          # COD deaths=370
    ("disease_meningitis", "DSEV_5fe8870f42f814b6"),       # NER Agadez（无数字）
    ("disease_yellow_fever", "DSEV_20f86b15264c6d16"),     # regional confirmed=16
    ("disease_cholera_tcd", "DSEV_ac0ee92b04bc87c6"),      # TCD 2026-08-12（未知数字场景）
    ("disease_cholera_bauchi", "DSEV_923093263017b71c"),   # NGA Bauchi confirmed=6 deaths=16
]

# 归因关键词（§四：不得把"指称参与"强化为"策划"）
ATTR_SRC_KW = ("accuse", "claim", "allege", "denounce", "reportedly",
               "according to", "指控", "声称", "据称", "aurait", "selon",
               "pourrait", "pourraient", "non confirm", "unconfirmed")
ATTR_OUT_KW = ("指控", "声称", "据称", "被指", "指称", "报道", "尚未证实")

NUMERIC_FIELDS = ("confirmed_cases", "probable_cases", "suspected_cases",
                  "total_cases", "deaths", "recoveries")


def load_payload_schema():
    return json.loads(PAYLOAD_SCHEMA.read_text(encoding="utf-8"))


def _load_json(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _iso2_to_iso3():
    try:
        m = _load_json("data/reference/iso2_to_iso3.json")
        return m.get("map") or {}
    except Exception:
        return {}


def _find_event(eid):
    for e in _load_json("data/canonical/event_clusters.json").get("items", []):
        if e.get("event_id") == eid:
            return e
    return None


def _find_disease(did):
    for it in _load_json("data/disease/canonical/outbreak_events.json").get("items", []):
        if it.get("disease_event_id") == did:
            return it
    return None


def build_security_samples():
    samples = []
    for label, eid in SECURITY_IDS:
        ev = _find_event(eid)
        if not ev:
            ev = {"event_id": "MISSING_%s" % eid, "title_original": "MISSING", "note": "event not in canonical"}
        samples.append({"category": label, "event_id": ev.get("event_id"), "event": ev,
                        "is_disease": False, "missing": ev.get("event_id", "").startswith("MISSING")})
    return samples


def build_disease_samples():
    samples = []
    for label, did in DISEASE_IDS:
        it = _find_disease(did)
        if not it:
            it = {"disease_event_id": "MISSING_%s" % did, "disease_id": "other", "note": "not in disease canonical"}
        samples.append({"category": label, "event_id": it.get("disease_event_id"), "event": it,
                        "is_disease": True, "missing": it.get("disease_event_id", "").startswith("MISSING")})
    return samples


def make_task(sample, provider_model):
    ev = sample["event"]
    if sample["is_disease"]:
        task_type = "disease_summary"
    else:
        task_type = "stage4_event_enrichment"
    return {
        "task_id": "GLMG_%s" % (ev.get("event_id") or ev.get("disease_event_id") or "x")[-16:],
        "task_type": task_type,
        "prompt_version": "1.1.0",
        "input_hash": "gh_" + (ev.get("event_id") or ev.get("disease_event_id") or "x")[-8:],
        "system_text": "你是 ASIP 事件增强引擎。只输出 JSON。",
        "user_text": json.dumps(ev, ensure_ascii=False)[:2000],
        "usage_purpose": "production_qualification",
        "max_output_tokens": 1500,
    }


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _summary_of(sample):
    """构造可审计的源摘要（不含敏感信息）。"""
    src_ev = sample["event"]
    summary = {
        "event_id": src_ev.get("event_id") or src_ev.get("disease_event_id"),
        "category": sample["category"],
        "country_code": src_ev.get("country_code"),
        "country_iso3": src_ev.get("country_iso3"),
        "title": (src_ev.get("title_original") or src_ev.get("disease_name_en") or "")[:120],
    }
    if sample["is_disease"]:
        summary["disease_id"] = src_ev.get("disease_id")
        summary["disease_name_en"] = src_ev.get("disease_name_en")
        summary["disease_name_zh"] = src_ev.get("disease_name_zh")
        summary["disease_aliases"] = src_ev.get("aliases") or []
        for f in NUMERIC_FIELDS:
            summary[f] = src_ev.get(f)
        summary["has_uncertainties"] = bool(src_ev.get("uncertainties"))
        summary["report_date"] = src_ev.get("report_date")
    else:
        summary["has_uncertainties"] = bool(src_ev.get("uncertainties"))
    return summary


def _meta_of(result):
    """提取 result 的安全审计字段（不含 credential/header）。"""
    return {k: result.get(k) for k in (
        "http_status", "attempt_count", "latency_ms",
        "requested_model", "returned_model",
        "token_usage_available", "input_tokens", "output_tokens",
        "total_tokens", "error") if k in result}


def _attribution_in_text(text):
    t = (text or "").lower()
    return any(k in t for k in ATTR_SRC_KW)


def _attribution_preserved(parsed):
    t = json.dumps(parsed, ensure_ascii=False)
    return any(k in t for k in ATTR_OUT_KW)


def run_quality_checks(rows):
    iso2 = _iso2_to_iso3()
    stats = {
        "total": len(rows),
        "strict_json_pass": 0,
        "schema_pass": 0,
        "major_fabrication": 0,        # 由人工语义复核补充（artifact 含 source+parsed）
        "country_error": 0,            # 保守启发：parsed.country_iso3 vs 源 ISO3
        "magnitude_error": 0,          # 由人工语义复核补充（数字数量级）
        "disease_name_error": 0,       # 保守启发：parsed 是否含源疾病名/别名
        "attribution_loss": 0,         # 保守启发：源含归因词而 parsed 无任何归因词
        "economic_as_direct": 0,       # 经济新闻不得判 direct
        "economic_none_correct": 0,
        "economic_total": 0,
        "disease_numeric_gate_failures": 0,  # 确定性：parsed 数字必须在源可找到或为 null
        "uncertainty_preservation_issues": 0,  # 保守：源 uncertainties 存在而 parsed 无
    }
    schema = load_payload_schema()
    for row in rows:
        res = row.get("parsed") or {}
        src = row.get("source_summary") or {}
        ok_json = bool(res)
        if ok_json:
            stats["strict_json_pass"] += 1
            if not validate_against_schema(res, schema):
                stats["schema_pass"] += 1
        cat = row.get("category", "")
        is_disease = row.get("is_disease", False)

        # 普通经济/发展：security_relevance 应为 none
        if cat == "economic_news":
            stats["economic_total"] += 1
            if res.get("security_relevance") == "none":
                stats["economic_none_correct"] += 1
            if res.get("security_relevance") == "direct":
                stats["economic_as_direct"] += 1

        # 指控归因保留（社安）
        if not is_disease and _attribution_in_text(src.get("title", "")) and res and not _attribution_preserved(res):
            stats["attribution_loss"] += 1

        # 国家一致性（保守：parsed 明确给出 country_iso3 才比）
        if not is_disease:
            src_cc = src.get("country_code") or ""
            src_iso = src.get("country_iso3") or iso2.get(src_cc, "")
            p_iso = res.get("country_iso3")
            if isinstance(p_iso, str) and p_iso.strip() and src_iso and p_iso.strip().upper() != src_iso.upper():
                stats["country_error"] += 1

        # 疾病名称一致性
        if is_disease and res:
            names = {src.get("disease_name_en") or "", src.get("disease_name_zh") or ""}
            for a in (src.get("disease_aliases") or []):
                names.add(a)
            names = {n for n in names if n}
            if names:
                hay = json.dumps(res, ensure_ascii=False)
                if not any(n.lower() in hay.lower() for n in names):
                    stats["disease_name_error"] += 1

        # 疾病数字确定性 Evidence Gate：parsed 数字必须在源可找到或为 null
        if is_disease and res:
            for f in NUMERIC_FIELDS:
                pv = res.get(f)
                if pv is None:
                    continue
                sv = _int(src.get(f))
                pv_int = _int(pv)
                if sv is None:
                    stats["disease_numeric_gate_failures"] += 1  # 源无此数字而模型给出
                elif pv_int is not None and pv_int != sv:
                    stats["disease_numeric_gate_failures"] += 1  # 数字不符

        # uncertainty 保留
        if src.get("has_uncertainties") and res and not res.get("uncertainties"):
            stats["uncertainty_preservation_issues"] += 1
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description="GLM-4.7-Flash Production Qualification")
    ap.add_argument("--provider", default="glm47_flash")
    ap.add_argument("--mock", action="store_true", help="mock provider 跑链路（不联网）")
    ap.add_argument("--limit", type=int, default=0,
                    help="只取前 N 条（8=第一 Gate 组合；20=全量）")
    ap.add_argument("--out", default="docs/glm-golden-set.json")
    args = ap.parse_args(argv)

    sec = build_security_samples()
    dis = build_disease_samples()
    samples = sec + dis
    missing = [s for s in samples if s.get("missing")]
    if missing:
        print("WARN missing samples: %s" % [s["category"] for s in missing], file=sys.stderr)
    if args.limit == 8:
        # §三 第一 Gate 组合：社安前 5（disputed allegation / casualty uncertainty /
        # direct security / ordinary economic / partial_body）+ 疾病前 3（cholera / mpox /
        # 带数字其他疾病）
        samples = sec[:5] + dis[:3]
    elif args.limit:
        samples = (sec + dis)[:args.limit]
    else:
        samples = sec + dis
    print("golden samples=%d (security=%d disease=%d)" % (
        len(samples), sum(1 for s in samples if not s["is_disease"]),
        sum(1 for s in samples if s["is_disease"])))

    if args.mock:
        provider = MockProvider()
    else:
        provider = get_provider(args.provider)
        if provider.credential_status == "missing":
            print(json.dumps({
                "credential_status": "missing",
                "provider_status": "unavailable",
                "result": "WAITING_FOR_GITHUB_SECRET",
                "golden_set": "SKIPPED",
            }, ensure_ascii=False, indent=2))
            return 2

    rows = []
    run_started = time.time()
    max_runtime = float(
        os.environ.get("ASIP_GLM_QUALIFICATION_MAX_RUNTIME_MINUTES", "45")) * 60
    stopped_early = None
    for s in samples:
        # §七 wall-clock 保护：超过上限安全停止，剩余任务保持 retryable
        if time.time() - run_started > max_runtime:
            stopped_early = "max_runtime_%ds" % int(max_runtime)
            break
        task = make_task(s, getattr(provider, "model", "glm-4.7-flash"))
        out = provider.submit_task(task)
        result = out.get("result") or {}
        parsed = result.get("result") or {}
        # §一 401/403 credential blocked → 直接停止当前 run（不掩盖、不继续）
        if out.get("status") == "blocked":
            rows.append({
                "category": s["category"],
                "is_disease": s["is_disease"],
                "task_id": task["task_id"],
                "provider_status": "blocked",
                "raw_status": result.get("status"),
                "source_summary": _summary_of(s),
                "parsed": None,
                "meta": _meta_of(result),
            })
            stopped_early = "credential_blocked"
            break
        rows.append({
            "category": s["category"],
            "is_disease": s["is_disease"],
            "task_id": task["task_id"],
            "provider_status": out.get("status"),
            "raw_status": result.get("status"),
            "source_summary": _summary_of(s),
            "parsed": parsed,
            "meta": _meta_of(result),
        })

    stats = run_quality_checks(rows)
    telemetry = None
    if not args.mock and hasattr(provider, "telemetry"):
        tel = dict(provider.telemetry)
        tel["retry_after_seconds"] = getattr(provider, "_last_retry_after_seconds", None)
        tel["request_start_gap_seconds"] = getattr(provider, "_request_start_gap", None)
        tel["rate_limit_until_remaining"] = (
            max(0.0, (provider._rate_limit_until or 0) - time.time())
            if getattr(provider, "_rate_limit_until", None) else 0.0)
        telemetry = tel
    doc = {
        "provider": args.provider,
        "mock": args.mock,
        "limit": args.limit,
        "usage_purpose": "production_qualification",
        "rows": rows,
        "stats": stats,
        "telemetry": telemetry,
        "stopped_early": stopped_early,
        "total_elapsed_s": round(time.time() - run_started, 1),
        "strict_json_rate": round(stats["strict_json_pass"] / max(len(rows), 1), 4),
        "note": "major_fabrication / magnitude_error 由人工语义复核补充；其余为确定性/保守启发计数。",
    }
    print(json.dumps({k: v for k, v in doc.items() if k != "rows"}, ensure_ascii=False, indent=2))

    if args.out:
        out_path = ROOT / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print("written: %s" % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
