#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 8C Package3 — AI Enrichment runner（§六/§七/§十六/§十七）。

只处理 NEW + eligible + not already enriched + not deduplicated away；
使用 content hash（state.processed_hashes）幂等，避免重复 token 消费。

Social：stage4_event_enrichment；Disease：disease_summary。
每条的流程：enrich（deepseek-v4-flash，thinking disabled）→ Attribution Safety
Layer → gate=PASS 才允许 Public（§十八）；HOLD/FAIL 进 failed_held_records。

Retry（§十六）：仅有限重试（provider 429/timeout/5xx），同模型无跨模型 fallback；
Report Analysis 失败直接 Fallback（见 reports_run）。
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.safety import manual_trial as mt  # noqa: E402
from scripts.ops import production_state as ps  # noqa: E402

DATA = ROOT / "data"
ENRICH_OUT = ps.OPS_DIR / "enrichment"


def _eligible_items(kind):
    """Social/Disease 生产候选（committed canonical + pending 增量合并）。"""
    items = []
    if kind == "social":
        p = DATA / "canonical" / "event_clusters.json"
        doc = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        items = [e for e in doc.get("items", []) if e.get("current_policy_passed")]
    else:
        p = DATA / "disease" / "canonical" / "outbreak_events.json"
        doc = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        items = [d for d in doc.get("items", [])
                 if d.get("outbreak_status") in ("active", "monitoring", "declining")]
    return items


def _write_back_canonical(kind, fid, summary, data_dir=None):
    """§十八 Public Admission：safety gate PASS 记录回写 canonical。

    social → data/canonical/event_clusters.json；
    disease → data/disease/canonical/outbreak_events.json。
    只添加字段（public_eligible/master_event_id/enrichment_*/safety），
    不删除/覆盖既有字段。data_dir 可注入（测试隔离用临时副本）。
    """
    root = Path(data_dir) if data_dir else DATA
    if kind == "social":
        p = root / "canonical" / "event_clusters.json"
        fid_field = "event_id"
    else:
        p = root / "disease" / "canonical" / "outbreak_events.json"
        fid_field = "disease_event_id"
    if not p.exists():
        return False
    doc = json.loads(p.read_text(encoding="utf-8"))
    items = doc.get("items", [])
    changed = 0
    for it in items:
        if it.get(fid_field) == fid:
            it["public_eligible"] = True
            it["master_event_id"] = it.get("master_event_id") or fid
            it["enrichment_status"] = "safety_gate_pass"
            it["enriched_at"] = ps._utcnow_iso()
            it["safety"] = summary
            changed += 1
    if changed:
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    return bool(changed)


def run_enrichment(kind, provider=None, state=None, ops_run=None, emit=lambda s: print(s),
                   max_items=0, write_back=True, data_dir=None, use_cache=False):
    """kind: social | disease。增量处理（content hash 幂等 + AI 结果缓存）。

    write_back：safety PASS 记录回写 canonical（§十八；测试可关闭或注入 data_dir）。
    use_cache：启用 scripts/ai/ai_result_cache（同 ai_input_hash 命中即跳过，不重复
    计费）。生产 CLI（main）默认启用；单测如需隔离必须显式传 False，否则会污染
    仓库内 data/ai/cache。
    """
    state = state or ps.load_state()
    kind_key = "social_enrichment" if kind == "social" else "disease_enrichment"
    task_type = "stage4_event_enrichment" if kind == "social" else "disease_summary"
    prov = provider if provider is not None else mt._flash_provider()
    items = _eligible_items(kind)
    telemetry = {}
    processed = 0
    skipped = 0
    cached = 0
    held = 0
    out = ENRICH_OUT
    out.mkdir(parents=True, exist_ok=True)
    for it in items:
        fid = it.get("event_id") if kind == "social" else it.get("disease_event_id")
        if not fid:
            continue
        ch = ps.content_hash({k: it.get(k) for k in
                              ("event_id", "disease_event_id", "title_cn",
                               "title_original", "summary_cn", "event_time",
                               "report_date", "source_links") if it.get(k)})
        if ps.is_processed(state, kind_key, fid):
            skipped += 1
            # 补偿回写（§十八）：已处理且 public_eligible=True 的记录，
            # 若 canonical 未回写（旧版运行产物），幂等补写，不重新 AI。
            if write_back:
                meta = (state.get("processed_hashes") or {}).get(kind_key, {}).get(fid) or {}
                if meta.get("public_eligible"):
                    _write_back_canonical(kind, fid, {
                        "gate": "PASS", "corrections": 0,
                        "status": "ok", "recovered": True},
                        data_dir=data_dir)
            continue
        if max_items and processed >= max_items:
            break
        label = ("S" if kind == "social" else "D") + "%s" % fid[-8:]
        rec = mt.enrich_and_safe(prov, task_type, it, label, telemetry,
                                 use_cache=use_cache)
        rec["event_id"] = fid if kind == "social" else None
        rec["disease_event_id"] = fid if kind != "social" else None
        rec["country_code"] = it.get("country_code") or it.get("country_iso3")
        cache_hit = bool(rec.get("cache_hit"))
        # §十八 Public Admission：attribution gate PASS 才可进 Public
        safe = rec.get("safety") or {}
        eligible_public = rec.get("status") == "ok" and safe.get("gate") == "PASS"
        (out / ("%s_%s.json" % (label, "ok" if eligible_public else "held"))).write_text(
            json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        ps.mark_processed(state, kind_key, fid, {
            "status": rec.get("status"), "public_eligible": eligible_public,
            "content_hash": ch, "ai_input_hash": rec.get("ai_input_hash"),
            "cache_hit": cache_hit})
        if eligible_public and write_back:
            _write_back_canonical(kind, fid, {
                "gate": safe.get("gate"),
                "corrections": safe.get("corrections_count") or 0,
                "status": rec.get("status")},
                data_dir=data_dir)
        if not eligible_public:
            held += 1
            state["failed_held_records"].append({
                "kind": kind, "record_id": fid, "status": rec.get("status"),
                "reason": safe.get("gate") or rec.get("status")})
        if cache_hit:
            cached += 1
        else:
            processed += 1
        emit("[%s] %s status=%s public=%s cache_hit=%s" % (
            label, fid[-12:], rec.get("status"), eligible_public, cache_hit))
    # AI usage 记账（§十七/§二十二）
    ps.add_ai_usage(state, kind_key, telemetry.get(task_type) or {})
    if ops_run is not None:
        ops_run["ai_attempted"] += processed
        ops_run["ai_succeeded"] += max(processed - held, 0)
        ops_run["ai_failed"] += held
        ops_run["safety_checked"] += processed + cached
        ops_run["safety_held"] += held
    t = telemetry.get(task_type) or {}
    emit("ENRICHMENT %s: processed=%d skipped=%d cached_same_input=%d held=%d "
         "calls=%d tokens=%d" % (
             kind, processed, skipped, cached, held,
             t.get("calls", 0), t.get("total_tokens", 0)))
    return {"kind": kind, "processed": processed, "skipped": skipped,
            "cached_same_input": cached, "held": held,
            "ai_calls": t.get("calls", 0),
            "input_tokens": t.get("input_tokens", 0),
            "output_tokens": t.get("output_tokens", 0),
            "total_tokens": t.get("total_tokens", 0),
            "telemetry": {task_type: t}}


def main(argv=None):
    ap = argparse.ArgumentParser(description="AI enrichment runner (incremental)")
    ap.add_argument("--kind", choices=["social", "disease"], required=True)
    ap.add_argument("--max-items", type=int, default=0)
    ap.add_argument("--fake", action="store_true", help="fake provider（AI_CALLS=0 测试）")
    args = ap.parse_args(argv)
    state = ps.load_state()
    prov = None
    if args.fake:
        class FakeProv:
            def submit_task(self, task):
                return {"status": "succeeded", "result": {
                    "returned_model": "deepseek-v4-flash",
                    "text": "not-json", "input_tokens": 1, "output_tokens": 1,
                    "total_tokens": 2, "finish_reason": "stop",
                    "thinking_requested": "disabled", "reasoning_tokens": None}}
        prov = FakeProv()
    # 生产 CLI 显式启用 AI 结果缓存（同输入不重复计费，Stage8D P0-2）
    r = run_enrichment(args.kind, provider=prov, state=state,
                       max_items=args.max_items, use_cache=True)
    ps.save_state(state)
    # Stage8D P1-2：真实 AI 遥测落盘，供 orchestrator 汇总（此前 ops 记为 0）
    try:
        ps.OPS_DIR.mkdir(parents=True, exist_ok=True)
        (ps.OPS_DIR / ("enrichment_summary_%s.json" % args.kind)).write_text(
            json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
