#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 8D — Production timeline builder（确定性，无 AI）。

Stage 8D Canary 发现：前端视图（master_events / disease_outbreaks /
event_timelines）依赖 data/runtime/timeline/*.json，而该产物由 Stage6
clustering→timeline 链生成，production-state 分支无此数据（生产链未包含
Stage6 聚类步骤）。本模块提供最小确定性 bridge：

  已回写 canonical（enrichment safety PASS → public_eligible/master_event_id）
  + disease canonical
  → social_timelines.json / disease_timelines.json

字段契约与 scripts/frontend/build_frontend_views.py 的消费端一致；
不调用 LLM；不读取 Stage6 clustering 产物；幂等（同一 canonical 输入 → 同一输出）。
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ops import production_state as ps  # noqa: E402

TIMELINE_DIR = ps.OPS_DIR.parent / "timeline"


def _bj_fmt(ts):
    """保留原始时间字符串（视图端 bj_fmt 再格式化）；None 保留 None。"""
    return ts if ts else None


def _build_social_timelines(events):
    """canonical public_eligible 记录 → social timeline 结构。"""
    timelines = []
    for e in events:
        mid = e.get("master_event_id") or e.get("event_id")
        if not mid:
            continue
        if not e.get("public_eligible"):
            continue
        sl = e.get("source_links") or []
        srcs = [s.get("source_name") for s in sl if isinstance(s, dict) and s.get("source_name")]
        updates = []
        title = (e.get("title_cn") or e.get("title_original") or
                 e.get("summary_cn") or "")
        if title:
            updates.append({
                "update_type": (e.get("event_status") or "status_update").lower(),
                "evidence": {"title": title[:400]},
            })
        loc = e.get("location") or e.get("admin1") or e.get("city") or None
        timelines.append({
            "master_event_id": mid,
            "current_state": {
                "country": e.get("country_code") or e.get("country_cn"),
                "location": loc,
                "event_type": e.get("event_type"),
            },
            "updates": updates,
            "verification_status": (e.get("verification_level") or
                                    e.get("verification_status")),
            "source_count": len(srcs) if srcs else None,
            "independent_source_count": e.get("independent_source_count"),
            "first_reported_at": _bj_fmt(e.get("first_seen_at") or e.get("event_time")),
            "latest_update_at": _bj_fmt(e.get("event_time") or e.get("last_seen_at")),
            "country_iso3": e.get("country_iso3"),
        })
    return timelines


def _build_disease_timelines(diseases):
    """canonical disease 记录 → disease timeline 结构（unknown = null 保留）。"""
    timelines = []
    for d in diseases:
        oid = d.get("disease_event_id") or d.get("outbreak_id")
        if not oid:
            continue
        if not d.get("public_eligible"):
            continue
        sl = d.get("source_links") or []
        srcs = [s.get("source_name") for s in sl if isinstance(s, dict) and s.get("source_name")]
        timelines.append({
            "outbreak_id": oid,
            "disease_id": d.get("disease_id"),
            "country_iso3": d.get("country_iso3"),
            "outbreak_status": d.get("outbreak_status") or d.get("status"),
            "latest_counts": {
                "confirmed_cases": d.get("confirmed_cases"),
                "probable_cases": d.get("probable_cases"),
                "suspected_cases": d.get("suspected_cases"),
                "deaths": d.get("deaths"),
            },
            "latest_report_at": _bj_fmt(d.get("report_date") or d.get("event_end_date")),
            "verification_status": d.get("verification_level") or d.get("verification_status"),
            "source_count": len(srcs) if srcs else None,
            "independent_source_count": d.get("independent_source_count"),
            "uncertainties": [u for u in (d.get("uncertainties") or [])][:5],
            "affected_admin1": [a for a in (d.get("admin1") or [])][:10]
            if isinstance(d.get("admin1"), list) else
            ([d["admin1"]] if d.get("admin1") else []),
        })
    return timelines


def build_timelines(data_dir=None, emit=lambda s: print(s)):
    """从 canonical（public_eligible）确定性构建 timelines 并落盘。"""
    root = Path(data_dir) if data_dir else ROOT / "data"
    ec = json.loads((root / "canonical" / "event_clusters.json").read_text(
        encoding="utf-8"))
    events = ec.get("items", [])
    dc = json.loads((root / "disease" / "canonical" / "outbreak_events.json").read_text(
        encoding="utf-8"))
    diseases = dc.get("items", [])
    social_tls = _build_social_timelines(events)
    disease_tls = _build_disease_timelines(diseases)
    run_id = ps._utcnow_iso().replace(":", "").replace("-", "")[:15] + "_tl"
    TIMELINE_DIR.mkdir(parents=True, exist_ok=True)
    (TIMELINE_DIR / "social_timelines.json").write_text(
        json.dumps({"run_id": run_id, "timelines": social_tls},
                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (TIMELINE_DIR / "disease_timelines.json").write_text(
        json.dumps({"run_id": run_id, "timelines": disease_tls},
                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    emit("TIMELINES social=%d disease=%d -> %s" % (
        len(social_tls), len(disease_tls), TIMELINE_DIR))
    return {"social": len(social_tls), "disease": len(disease_tls)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Production timeline builder (no AI)")
    ap.add_argument("--data-dir", default=None,
                    help="canonical 数据根（测试隔离用临时目录）")
    args = ap.parse_args(argv)
    r = build_timelines(data_dir=args.data_dir)
    print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
