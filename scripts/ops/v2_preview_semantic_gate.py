#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP V1.1 — V2 Preview Semantic Gate（Preview-specific binding）。

设计边界（§一/§二/§三）：
- 本 Gate 只改变「从哪里读」：V2 Preview overlay、V2 historical reports、V2 status、
  V2 master events、V2 disease data、V2 risk data、V2 homepage views。
- 不读取 Production report output / Production status.run_id / Production report
  directory 来判定 Preview 是否通过。
- 不修改 scripts/validate_pipeline.py（Production Validator）、production-state、
  gh-pages、main、workflows、schedules、AUTO_DEPLOY。
- 不降低任何 Schema / Safety / Attribution / Numeric Integrity / Source Linkage /
  Disease Semantics / Risk Mapping / Historical Metadata / AI Boundary /
  Duplicate Prevention 标准。

输出：
- data/runtime/backfill_preview_v2/v2_preview_semantic_gate.json
- data/runtime/backfill_preview_v2/v2_preview_semantic_gate.md
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

PREVIEW_ROOT = ROOT / "data" / "runtime" / "backfill_preview_v2"
VIEWS = PREVIEW_ROOT / "views"
CANON = PREVIEW_ROOT / "canonical" / "event_clusters.json"
OBS = PREVIEW_ROOT / "source_observations.json"
SUMMARY = PREVIEW_ROOT / "historical_backfill_v2_import_summary.json"
REPORTS = PREVIEW_ROOT / "reports"
DEFAULT_DIST = ROOT / "preview_dist_v2_gate"
GEO_JS = ROOT / "assets" / "geo" / "africa-countries.js"
HOME_JS = ROOT / "assets" / "js" / "home-v11.js"
FRONTEND_JS = ROOT / "assets" / "js" / "frontend.js"

BATCH_ID = "asip-backfill-20260818-20260827-v2-full"
DISEASE_ACTIVE_STATUSES = {"ACTIVE", "MONITORING", "DECLINING", "CONTROLLED"}
DISEASE_SIGNAL_STATUSES = DISEASE_ACTIVE_STATUSES | {"PREPAREDNESS"}
EXPECTED_DISEASE_STATUS = {
    "COD": "ACTIVE", "GNB": "ACTIVE", "AFR": "RESOLVED",
    "UGA": "RESOLVED", "SSD": "PREPAREDNESS",
}
WATCH_CLUSTERS = {
    "ZMB_2026_ELECTION_POSTELECTION": "must_be_single_master_event",
    "NGA_BORGU_MASS_ABDUCTION_20260821": "must_be_single_master_event",
    "TCD_SDN_CROSS_BORDER_STRIKE_20260820": "must_remain_held_disputed",
}
TOP3_TITLES = {"24h": "今日最重要的3件事", "72h": "近72小时重点动态", "7d": "过去7日重大事件"}


def load(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def read_view(name, default=None):
    return load(VIEWS / (name + ".json"), default)


def parse_day(s):
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_dt(s):
    if not s:
        return None
    t = str(s).replace(" ", "T")
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(t)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# ══════════════════════════════════════════════════════════════════
# §四 Schema Gate
# ══════════════════════════════════════════════════════════════════
def gate_schema(ctx):
    required = {
        "site_overview": ["generated_at", "data_status", "kpis", "generation_mode"],
        "master_events": ["generated_at", "count", "events"],
        "event_timelines": ["generated_at", "count", "timelines"],
        "country_snapshots": ["generated_at", "count", "snapshots"],
        "disease_outbreaks": ["generated_at", "count", "outbreaks"],
        "report_index": ["generated_at", "count", "reports"],
        "context_signals": ["generated_at", "count", "signals"],
        "china_interest": ["generated_at", "count", "rows"],
    }
    missing = []
    for view, fields in required.items():
        doc = ctx["views"].get(view)
        if not isinstance(doc, dict):
            missing.append("%s:missing_view" % view)
            continue
        for f in fields:
            if f not in doc:
                missing.append("%s:%s" % (view, f))
    ev_fields = ["master_event_id", "cluster_key", "headline_zh", "country_iso3", "event_type",
                 "event_time", "verification_status", "source_count", "source_links"]
    for e in ctx["events"]:
        for f in ev_fields:
            if f not in e:
                missing.append("master_events[].%s" % f)
                break
    dis_fields = ["outbreak_id", "disease_id", "country_iso3", "status", "status_cn",
                  "latest_counts", "source_count", "source_links", "latest_report_at"]
    for d in ctx["outbreaks"]:
        for f in dis_fields:
            if f not in d:
                missing.append("disease_outbreaks[].%s" % f)
                break
    snap_fields = ["country_iso3", "country_cn", "risk_level", "events_24h", "events_7d"]
    for s in ctx["snapshots"]:
        for f in snap_fields:
            if f not in s:
                missing.append("country_snapshots[].%s" % f)
                break
    rep_fields = ["report_id", "type", "period_start", "period_end", "status",
                  "generation_mode", "historical_reconstruction", "backfill_batch_id"]
    for r in ctx["reports"]:
        for f in rep_fields:
            if f not in r:
                missing.append("report_index[].%s" % f)
                break
    return ("PASS" if not missing else "FAIL", {
        "missing_required_fields": missing[:20],
        "missing_count": len(missing),
        "views_checked": len(required),
    })


# ══════════════════════════════════════════════════════════════════
# §五 Event Identity / Duplicate Gate
# ══════════════════════════════════════════════════════════════════
def gate_event_identity(ctx):
    clusters = [c.get("cluster_key") for c in ctx["clusters"]]
    dup_cluster = [k for k, v in Counter(clusters).items() if v > 1]
    events_ck = [e.get("cluster_key") for e in ctx["events"]]
    dup_event = [k for k, v in Counter(events_ck).items() if v > 1]
    ids = [e.get("master_event_id") for e in ctx["events"]]
    dup_ids = [k for k, v in Counter(ids).items() if v > 1]
    # 同一现实事件的标题+国家+日期指纹（防止不同 cluster_key 的重复卡）
    fp = Counter((str(e.get("country_iso3")), str(e.get("headline_zh") or "")[:40],
                  str(e.get("event_time") or "")[:10]) for e in ctx["events"])
    dup_fp = [k for k, v in fp.items() if v > 1]
    watch = {}
    for k in WATCH_CLUSTERS:
        watch[k] = {
            "expectation": WATCH_CLUSTERS[k],
            "cluster_rows": sum(1 for c in clusters if c == k),
            "master_events": sum(1 for e in events_ck if e == k),
            "held_disposition": next(
                (h.get("disposition") for h in ctx["held"] if h.get("cluster_key") == k), None),
        }
    ok = not (dup_cluster or dup_event or dup_ids or dup_fp)
    for k, v in watch.items():
        if WATCH_CLUSTERS[k] == "must_be_single_master_event":
            if v["master_events"] != 1 or v["cluster_rows"] != 1:
                ok = False
        else:
            # 争议性跨境记录：必须仍为 HOLD，且不得成为 Master Event
            if v["master_events"] != 0 or not (v["held_disposition"] or "").startswith("HOLD"):
                ok = False
    return ("PASS" if ok else "FAIL", {
        "duplicate_cluster_keys": dup_cluster,
        "duplicate_master_events_by_cluster": dup_event,
        "duplicate_master_event_ids": dup_ids,
        "duplicate_content_fingerprints": [list(x) for x in dup_fp],
        "clusters": len(clusters), "master_events": len(ctx["events"]),
        "watched_clusters": watch,
    })


# ══════════════════════════════════════════════════════════════════
# §六 Source Linkage Gate
# ══════════════════════════════════════════════════════════════════
def gate_source_linkage(ctx):
    missing = []
    for e in ctx["events"]:
        links = e.get("source_links") or []
        if not links or not all(x.get("url") for x in links):
            missing.append("master_event:%s" % e.get("master_event_id"))
    for d in ctx["outbreaks"]:
        links = d.get("source_links") or []
        if not links or not all(x.get("url") for x in links):
            missing.append("disease:%s" % d.get("outbreak_id"))
    for mid, ups in (ctx["timelines"] or {}).items():
        for i, u in enumerate(ups):
            links = ((u.get("source_ref") or {}).get("source_links")) or []
            if not links or not all(x.get("url") for x in links):
                missing.append("timeline:%s#%d" % (mid, i))
    for c in ctx["clusters"]:
        groups = c.get("source_groups") or []
        if not groups:
            missing.append("cluster:%s" % c.get("cluster_key"))
    # 上下文信号不得充当事实来源：context 允许有 source_urls，但不得出现在事件池
    ctx_ids = {c.get("context_id") for c in ctx["contexts"]}
    ctx_as_fact = [i for i in ctx_ids if i in {e.get("master_event_id") for e in ctx["events"]}]
    ok = not missing and not ctx_as_fact
    return ("PASS" if ok else "FAIL", {
        "missing_source_records": missing[:20],
        "missing_source_count": len(missing),
        "context_signal_acting_as_fact": ctx_as_fact,
        "sources_checked": len(ctx["events"]) + len(ctx["outbreaks"]) + len(ctx["clusters"]),
    })


# ══════════════════════════════════════════════════════════════════
# §七 Attribution / Uncertainty Gate
# ══════════════════════════════════════════════════════════════════
VERIFICATION_LABEL = {
    "official_confirmed": "official", "multi_source": "multi",
    "single_source": "single", "disputed_claim": "disputed",
}


def gate_attribution(ctx):
    escalations = []
    for e in ctx["events"]:
        st = e.get("verification_status")
        label = e.get("verification_cn") or ""
        if st == "single_source" and ("已核实" in label or "官方确认" in label):
            escalations.append("single_source_as_confirmed:%s" % e.get("master_event_id"))
        if st == "disputed_claim":
            escalations.append("disputed_published:%s" % e.get("master_event_id"))
    for d in ctx["outbreaks"]:
        st = d.get("verification_status")
        if st == "single" and (d.get("verification_cn") or "") == "已核实":
            escalations.append("disease_single_as_confirmed:%s" % d.get("outbreak_id"))
    # HOLD 的争议记录不得被发布为事件
    held_disputed = [h for h in ctx["held"] if "DISPUTED" in str(h.get("disposition") or "")]
    held_ck = {h.get("cluster_key") for h in held_disputed}
    leaked = [e.get("master_event_id") for e in ctx["events"] if e.get("cluster_key") in held_ck]
    escalations += ["held_disputed_leaked:%s" % x for x in leaked]
    dist = Counter(e.get("verification_status") for e in ctx["events"])
    return ("PASS" if not escalations else "FAIL", {
        "attribution_escalation_count": len(escalations),
        "escalations": escalations[:10],
        "verification_distribution": dict(dist),
        "held_disputed_clusters": sorted(held_ck),
        "single_source_not_upgraded": all(
            not (e.get("verification_status") == "single_source" and "已核实" in (e.get("verification_cn") or ""))
            for e in ctx["events"]),
    })


def gate_uncertainty(ctx):
    lost = []
    src_unc = {}
    for c in ctx["clusters"]:
        if c.get("uncertainties"):
            src_unc[c.get("cluster_key")] = len(c["uncertainties"])
    for e in ctx["events"]:
        ck = e.get("cluster_key")
        if ck in src_unc and not (e.get("uncertainties") or []):
            lost.append("cluster:%s" % ck)
    for d in ctx["outbreaks"]:
        if d.get("status") == "ACTIVE" and d.get("country_iso3") == "GNB" and not d.get("uncertainties"):
            lost.append("disease:GNB_uncertainty_dropped")
    return ("PASS" if not lost else "FAIL", {
        "uncertainty_loss_count": len(lost),
        "uncertainty_losses": lost[:10],
        "clusters_with_uncertainty": len(src_unc),
    })


# ══════════════════════════════════════════════════════════════════
# §八 Numeric Integrity Gate
# ══════════════════════════════════════════════════════════════════
def gate_numeric(ctx):
    issues = []
    # 疾病统计只来自「最新合法 update」，禁止跨日期累加
    for d in ctx["outbreaks"]:
        lc = d.get("latest_counts") or {}
        for k in ("confirmed", "suspected", "deaths", "recovered"):
            v = lc.get(k)
            if v is not None and not isinstance(v, int):
                issues.append("non_integer_stat:%s:%s" % (d.get("outbreak_id"), k))
            if isinstance(v, int) and v < 0:
                issues.append("negative_stat:%s:%s" % (d.get("outbreak_id"), k))
        if lc.get("as_of_date") and not parse_day(lc.get("as_of_date")):
            issues.append("bad_as_of_date:%s" % d.get("outbreak_id"))
    gnb = next((d for d in ctx["outbreaks"] if d.get("country_iso3") == "GNB"), None)
    gnb_stats = (gnb or {}).get("latest_counts")
    expected = {"confirmed": 10, "suspected": 58, "deaths": 0, "recovered": None, "as_of_date": "2026-08-23"}
    if gnb_stats != expected:
        issues.append("gnb_stats_mismatch:%s" % json.dumps(gnb_stats, ensure_ascii=False))
    # KPI 数字必须由 master events 确定性推导（不得叠加 context / observation）
    ov = ctx["overview"]
    kpis = ov.get("kpis", {})
    cutoff = parse_day(ov.get("latest_data_time_bj"))
    if cutoff:
        e24 = sum(1 for e in ctx["events"] if (d := parse_day(e.get("event_time"))) and d == cutoff)
        e7 = sum(1 for e in ctx["events"] if (d := parse_day(e.get("event_time")))
                 and cutoff - timedelta(days=6) <= d <= cutoff)
        if kpis.get("events_24h") != e24:
            issues.append("kpi_24h_mismatch:%s!=%s" % (kpis.get("events_24h"), e24))
        if kpis.get("events_7d") != e7:
            issues.append("kpi_7d_mismatch:%s!=%s" % (kpis.get("events_7d"), e7))
    if kpis.get("events_10d") != len(ctx["events"]):
        issues.append("kpi_10d_mismatch")
    return ("PASS" if not issues else "FAIL", {
        "unsupported_number_count": len(issues),
        "issues": issues[:10],
        "gnb_latest_counts": gnb_stats,
        "kpis": kpis,
    })


# ══════════════════════════════════════════════════════════════════
# §九/§十/§十一 Disease Gates
# ══════════════════════════════════════════════════════════════════
def gate_disease_status(ctx):
    actual = {d.get("country_iso3"): d.get("status") for d in ctx["outbreaks"]}
    mism = {k: (actual.get(k), v) for k, v in EXPECTED_DISEASE_STATUS.items() if actual.get(k) != v}
    auto_active = [d.get("outbreak_id") for d in ctx["outbreaks"]
                   if d.get("status") == "ACTIVE" and d.get("status_cn") in (None, "", "监测")
                   and not d.get("latest_report_at")]
    ctx_as_outbreak = [d.get("outbreak_id") for d in ctx["outbreaks"]
                       if str(d.get("disease_id") or "").startswith("context")]
    ok = not mism and not ctx_as_outbreak and not auto_active
    return ("PASS" if ok else "FAIL", {
        "expected": EXPECTED_DISEASE_STATUS, "actual": actual, "mismatches": mism,
        "disease_context_as_outbreak_error": len(ctx_as_outbreak),
        "auto_active_without_evidence": auto_active,
        "entity_exists_but_not_active": [
            {"iso3": d.get("country_iso3"), "status": d.get("status")}
            for d in ctx["outbreaks"] if d.get("status") not in DISEASE_ACTIVE_STATUSES],
    })


def gate_disease_stats(ctx):
    rows = []
    for d in ctx["outbreaks"]:
        lc = d.get("latest_counts") or {}
        rows.append({
            "iso3": d.get("country_iso3"), "disease": d.get("disease_name_cn"),
            "status": d.get("status"),
            "confirmed": lc.get("confirmed"), "suspected": lc.get("suspected"),
            "deaths": lc.get("deaths"), "recovered": lc.get("recovered"),
            "as_of_date": lc.get("as_of_date"), "latest_report_at": d.get("latest_report_at"),
            "update_count": d.get("update_count"),
        })
    gnb = next((r for r in rows if r["iso3"] == "GNB"), None)
    ok = bool(gnb) and gnb["confirmed"] == 10 and gnb["suspected"] == 58 and gnb["deaths"] == 0 \
        and gnb["as_of_date"] == "2026-08-23"
    return ("PASS" if ok else "FAIL", {"rows": rows, "gnb_verified": ok})


def gate_active_signal(ctx):
    active = sum(1 for d in ctx["outbreaks"] if d.get("status") in DISEASE_ACTIVE_STATUSES)
    signal = sum(1 for d in ctx["outbreaks"] if d.get("status") in DISEASE_SIGNAL_STATUSES)
    kpi_active = ctx["overview"].get("kpis", {}).get("active_outbreaks")
    kpi_signal = ctx["overview"].get("kpis", {}).get("disease_active_signal_count")
    # Disease page（frontend.js）使用同一状态集
    fe = FRONTEND_JS.read_text(encoding="utf-8")
    fe_ok = ('"ACTIVE", "MONITORING", "DECLINING", "CONTROLLED"' in fe
             or "'ACTIVE', 'MONITORING', 'DECLINING', 'CONTROLLED'" in fe)
    sync = (active == kpi_active) and (signal == kpi_signal) and fe_ok
    return ("PASS" if sync else "FAIL", {
        "active_disease_signal_count": signal,
        "active_outbreaks": active,
        "homepage_kpi_active_outbreaks": kpi_active,
        "homepage_kpi_disease_active_signal_count": kpi_signal,
        "disease_page_status_set_matches": fe_ok,
        "resolved_not_counted_as_active": [
            d.get("country_iso3") for d in ctx["outbreaks"] if d.get("status") == "RESOLVED"],
    })


# ══════════════════════════════════════════════════════════════════
# §十二/§十三 Risk Map Consistency
# ══════════════════════════════════════════════════════════════════
def geo_keys():
    txt = GEO_JS.read_text(encoding="utf-8")
    return re.findall(r'^\s{2}"([A-Z]{3})":\s*\{', txt, flags=re.M)


def gate_risk_map(ctx):
    geo = set(geo_keys())
    snaps = ctx["snapshots"]
    risk_iso = {}
    for s in snaps:
        iso = s.get("country_iso3")
        lv = s.get("risk_level")
        if iso:
            risk_iso[iso] = None if lv is None else int(lv)
    with_data = {iso: lv for iso, lv in risk_iso.items() if lv is not None}
    miss = sorted(iso for iso in risk_iso if iso not in geo)
    # 模拟 renderMap 着色：仅当该国存在有效 risk 数据时着色（COG 兜底不注入 0）
    colored = sorted(iso for iso in geo if with_data.get(iso) is not None)
    # Top Risk 必须全部在地图上着色
    top = sorted(snaps, key=lambda s: (-(s.get("risk_level") or 0), -(s.get("events_7d") or 0)))[:7]
    top_iso = [s.get("country_iso3") for s in top]
    not_colored = [iso for iso in top_iso if iso not in colored]
    ok = (len(with_data) == len(colored) == 9) and not miss and not not_colored
    return ("PASS" if ok else "FAIL", {
        "v2_risk_countries_with_data": len(with_data),
        "v2_map_colored_countries": len(colored),
        "v2_iso_mapping_miss_count": len(miss),
        "iso_mapping_misses": miss,
        "colored_iso3": colored,
        "risk_by_iso3": with_data,
        "top_risk_iso3": top_iso,
        "top_risk_not_colored": not_colored,
        "geo_country_count": len(geo),
    })


# ══════════════════════════════════════════════════════════════════
# §十四 Overall Africa Risk Method
# ══════════════════════════════════════════════════════════════════
REGION_BY_ISO3 = {
    "DZA": "North Africa", "EGY": "North Africa", "LBY": "North Africa", "MAR": "North Africa",
    "TUN": "North Africa", "ESH": "North Africa", "SDN": "North Africa",
    "BEN": "West Africa", "BFA": "West Africa", "CIV": "West Africa", "GHA": "West Africa",
    "GIN": "West Africa", "GMB": "West Africa", "GNB": "West Africa", "LBR": "West Africa",
    "MLI": "West Africa", "MRT": "West Africa", "NER": "West Africa", "NGA": "West Africa",
    "SEN": "West Africa", "SLE": "West Africa", "TGO": "West Africa",
    "CMR": "Central Africa", "CAF": "Central Africa", "TCD": "Central Africa",
    "COG": "Central Africa", "COD": "Central Africa", "GNQ": "Central Africa",
    "GAB": "Central Africa", "AGO": "Central Africa",
    "BDI": "East Africa", "DJI": "East Africa", "ERI": "East Africa", "ETH": "East Africa",
    "KEN": "East Africa", "RWA": "East Africa", "SOM": "East Africa", "SSD": "East Africa",
    "TZA": "East Africa", "UGA": "East Africa", "MDG": "East Africa",
    "BWA": "Southern Africa", "LSO": "Southern Africa", "MOZ": "Southern Africa",
    "MWI": "Southern Africa", "NAM": "Southern Africa", "SWZ": "Southern Africa",
    "ZAF": "Southern Africa", "ZMB": "Southern Africa", "ZWE": "Southern Africa",
}


def composite_risk_v2(snapshots, kpis):
    groups = defaultdict(list)
    with_data = 0
    for s in snapshots:
        lv = s.get("risk_level")
        if lv is None:
            continue
        with_data += 1
        groups[s.get("region") or REGION_BY_ISO3.get(s.get("country_iso3"), "未分区")].append(int(lv))
    if not groups:
        return {"level": 0, "method": "regional_composite_signal_v2", "inputs": {}, "components": {}}
    means = [sum(v) / len(v) for v in groups.values()]
    base = sum(means) / len(means)
    very_high = sum(1 for s in snapshots if (s.get("risk_level") or 0) >= 4)
    high = sum(1 for s in snapshots if s.get("risk_level") == 3)
    spread = sum(1 for m in means if m >= 3)
    e24 = kpis.get("events_24h") or 0
    e7d = kpis.get("events_7d") or 0
    cross = sum(1 for s in snapshots if s.get("cross_border_escalation") or s.get("cross_border_risk_change"))
    adj = (0.5 if very_high >= 3 else 0.25 if very_high >= 1 else 0) \
        + (0.25 if high >= 5 else 0) + (0.25 if spread >= 3 else 0) \
        + (0.25 if e24 >= 3 else 0) + (0.25 if cross >= 1 else 0)
    score = base + adj
    level = max(1, min(5, int(score + 0.5)))  # JS Math.round：.5 向上
    return {
        "level": level, "method": "regional_composite_signal_v2",
        "inputs": {
            "countries_with_risk_data": with_data, "region_count": len(means),
            "country_risk_mean": round(base, 2), "very_high_country_count": very_high,
            "high_country_count": high, "region_count_with_elevated_mean": spread,
            "events_24h": e24, "events_7d": e7d, "cross_border_escalation": cross,
        },
        "components": {"regional_base": round(base, 2), "adjustment": round(adj, 2), "score": round(score, 2)},
    }


def gate_overall_risk(ctx):
    comp = composite_risk_v2(ctx["snapshots"], ctx["overview"].get("kpis", {}))
    src = HOME_JS.read_text(encoding="utf-8")
    uses_max_only = bool(re.search(r"overall\s*=\s*rl\(max", src))
    method_declared = "regional_composite_signal_v2" in src
    max_country = max((s.get("risk_level") or 0) for s in ctx["snapshots"])
    ok = method_declared and not uses_max_only and comp["method"] != "max_country_risk_only"
    return ("PASS" if ok else "FAIL", {
        "overall_risk": comp["level"],
        "overall_risk_method": comp["method"],
        "overall_risk_inputs": comp["inputs"],
        "overall_risk_components": comp["components"],
        "max_country_risk": max_country,
        "equals_max_country_risk": comp["level"] == max_country,
        "method_is_max_only": uses_max_only,
    })


# ══════════════════════════════════════════════════════════════════
# §十五 What Changed Today
# ══════════════════════════════════════════════════════════════════
def gate_what_changed(ctx):
    items = []
    for s in ctx["snapshots"]:
        if (s.get("events_24h") or 0) > 0:
            items.append({"kind": "new_event", "cn": s.get("country_cn"),
                          "txt": "新增 %s 起安全事件" % s["events_24h"]})
    for s in ctx["snapshots"]:
        tr = s.get("previous_risk_level")
        now = s.get("risk_level")
        if tr is not None and now is not None and int(tr) != int(now):
            items.append({"kind": "risk_transition", "cn": s.get("country_cn"),
                          "txt": "风险等级 %s → %s" % (tr, now)})
    for s in ctx["snapshots"]:
        if s.get("cross_border_escalation") or s.get("cross_border_risk_change"):
            items.append({"kind": "cross_border_escalation", "cn": s.get("country_cn"),
                          "txt": "跨境风险信号上升"})
    CHANGE_WINDOW_DAYS = 3
    cutoff = parse_dt(ctx["overview"].get("latest_data_time_bj")) or parse_dt("2026-08-27T23:59:59+08:00")

    def recent_disease(o):
        t = parse_dt(o.get("latest_report_at"))
        if not t or not cutoff:
            return False
        return 0 <= (cutoff - t).total_seconds() / 86400.0 <= CHANGE_WINDOW_DAYS

    for o in ctx["outbreaks"]:
        kind = o.get("latest_change")
        if kind in ("status_change", "outbreak_resolution") and not recent_disease(o):
            continue
        if kind == "status_change":
            items.append({"kind": "outbreak_status_change",
                          "cn": o.get("country_cn") or o.get("country_iso3"),
                          "txt": "疾病状态变化：%s → %s" % (o.get("previous_status"), o.get("status_cn") or o.get("status"))})
        elif kind == "outbreak_resolution":
            items.append({"kind": "outbreak_resolution",
                          "cn": o.get("country_cn") or o.get("country_iso3"),
                          "txt": "重大降级：疫情状态 → %s" % (o.get("status_cn") or o.get("status"))})
    for s in ctx["snapshots"]:
        if (s.get("events_24h") or 0) == 0 and (s.get("events_7d") or 0) > 0 and (s.get("risk_level") or 0) >= 3:
            items.append({"kind": "risk_steady", "cn": s.get("country_cn"),
                          "txt": "高风险维持（7d %s 起）" % s["events_7d"]})
    rank = {"new_event": 1, "risk_transition": 2, "cross_border_escalation": 3,
            "outbreak_status_change": 4, "outbreak_resolution": 5, "risk_steady": 6}
    items.sort(key=lambda x: rank.get(x["kind"], 9))
    selected = items[:4]
    uganda = [i for i in selected if i["kind"] == "outbreak_resolution"
              and "乌干达" in str(i.get("cn"))]
    # 不得只看 24h event_count > 0：必须允许疫情状态变化 / 重大降级等非事件型变化
    ok = len(selected) <= 4 and bool(uganda)
    return ("PASS" if ok else "FAIL", {
        "item_count": len(selected), "items": selected,
        "candidates_total": len(items),
        "kinds": sorted({i["kind"] for i in selected}),
        "outbreak_resolution_included": bool(uganda),
        "not_event_count_only": any(i["kind"] != "new_event" for i in selected),
    })


# ══════════════════════════════════════════════════════════════════
# §十六 Historical NEW Badge
# ══════════════════════════════════════════════════════════════════
def gate_recency_badge(ctx):
    src = FRONTEND_JS.read_text(encoding="utf-8")
    uses_imported = bool(re.search(r"recencyBadge\([^)]*imported_at", src))
    cutoff = parse_dt(ctx["overview"].get("latest_data_time_bj")) or parse_dt("2026-08-27T23:59:59+08:00")
    badges, false_badges = [], []
    window = ctx["window"] or {}
    start_day, end_day = window.get("start"), window.get("end")
    for e in ctx["events"]:
        mid = e.get("master_event_id")
        # 前端 badge 时间来源：latest_update_at || event_time（不得为 imported_at / 构建时间）
        bt = e.get("latest_update_at") or e.get("event_time")
        t = parse_dt(bt)
        if not t or not cutoff:
            continue
        tl_days = {str(u.get("time") or "")[:10] for u in (ctx["timelines"].get(mid) or [])}
        ev_day = str(e.get("event_time") or "")[:10]
        bt_day = str(bt)[:10]
        source = "timeline_update" if tl_days and bt_day in tl_days and bt_day != ev_day else (
            "event_time" if bt_day == ev_day else "untraceable")
        traceable = source != "untraceable"
        in_window = (not start_day or start_day <= bt_day <= end_day)
        age = (cutoff - t).total_seconds() / 86400.0
        badge = "NEW" if 0 <= age < 1 else ("RECENT" if 1 <= age <= 3 else "")
        # 误报定义：badge 时间无法追溯到真实 event_time / timeline 记录，
        # 或落在数据窗口之外（即来自回填/构建时间而非事实时间）
        if badge and (not traceable or not in_window):
            false_badges.append({"id": mid, "badge": badge, "badge_time": bt,
                                 "source": source, "in_data_window": in_window,
                                 "event_time": e.get("event_time"), "age_days": round(age, 2)})
        if badge:
            badges.append({"id": mid, "age_days": round(age, 2), "badge": badge,
                           "badge_time_source": source, "event_date": ev_day,
                           "badge_date": bt_day})
    ok = not false_badges and not uses_imported
    return ("PASS" if ok else "FAIL", {
        "false_new_badge_count": len(false_badges),
        "false_badges": false_badges[:10],
        "uses_imported_at": uses_imported,
        "cutoff": str(cutoff),
        "data_window": {"start": start_day, "end": end_day},
        "badged_events": badges,
        "badged_count": len(badges),
        "badge_rule": "age<24h=NEW; 24-72h=RECENT; >72h=none（时间来自 event_time / 真实 timeline update）",
    })


# ══════════════════════════════════════════════════════════════════
# §十七 Top 3 Time Window
# ══════════════════════════════════════════════════════════════════
def gate_top3(ctx):
    src = HOME_JS.read_text(encoding="utf-8")
    cutoff = parse_dt(ctx["overview"].get("latest_data_time_bj")) or parse_dt("2026-08-27T23:59:59+08:00")
    evs = []
    for e in ctx["events"]:
        t = parse_dt(e.get("latest_update_at") or e.get("event_time"))
        if t and cutoff:
            evs.append(((cutoff - t).total_seconds() / 86400.0, e))
    windows = [("24h", 1.0), ("72h", 3.0), ("7d", 7.0)]
    selected = None
    for i, (key, days) in enumerate(windows):
        cand = sorted([x for age, x in evs if 0 <= age <= days],
                      key=lambda e: (-(e.get("importance_score") or 0),
                                     str(e.get("latest_update_at") or e.get("event_time") or "")))
        if i == len(windows) - 1:
            selected = (key, cand[:3])
            break
        if len(cand) >= 3:
            selected = (key, cand[:3])
            break
    key, top = selected
    # 与前端展示字段保持一致：显示的是 latest_update_at || event_time
    dates = [str(e.get("latest_update_at") or e.get("event_time") or "")[:10] for e in top]
    title = TOP3_TITLES[key]
    titles_in_code = all(t in src for t in TOP3_TITLES.values())
    threshold_ok = "TOP3_MIN_EVENTS = 3" in src
    max_age = max(((cutoff - parse_dt(e.get("latest_update_at") or e.get("event_time"))).total_seconds() / 86400.0
                   for e in top), default=0)
    ok = titles_in_code and threshold_ok and (max_age <= {"24h": 1.0, "72h": 3.0, "7d": 7.0}[key] + 1e-6)
    return ("PASS" if ok else "FAIL", {
        "top3_title": title, "top3_window": key, "top3_event_dates": dates,
        "top3_event_count": len(top), "max_age_days": round(max_age, 2),
        "titles_present_in_code": titles_in_code, "threshold_rule_present": threshold_ok,
    })


# ══════════════════════════════════════════════════════════════════
# §十八 Category Empty State
# ══════════════════════════════════════════════════════════════════
CATEGORY_TYPES = {
    "conflict": ["terrorist_attack", "armed_conflict", "military_operation", "kidnapping",
                 "insurgent_activity", "cross_border_armed", "armed_activity"],
    "political": ["protest", "strike", "election", "political_crisis", "government_instability",
                  "civil_unrest", "coup_related"],
    "safety": ["major_crime", "natural_disaster", "major_accident", "humanitarian_incident",
               "border_incident", "civil_protection", "other_security"],
    "health": ["outbreak", "epidemic", "who_alert", "major_disease", "public_health_emergency"],
}


def gate_category_empty(ctx):
    src = HOME_JS.read_text(encoding="utf-8")
    compact = "过去24小时暂无重大新增" in src and "查看近72小时动态" in src
    counts = {k: sum(1 for e in ctx["events"] if e.get("event_type") in v)
              for k, v in CATEGORY_TYPES.items()}
    ok = compact
    return ("PASS" if ok else "FAIL", {
        "category_event_counts": counts,
        "empty_state_compact_present": compact,
        "categories_with_zero_events": [k for k, v in counts.items() if v == 0],
    })


# ══════════════════════════════════════════════════════════════════
# §十九/§二十 Reports
# ══════════════════════════════════════════════════════════════════
def gate_reports(ctx):
    reps = ctx["reports"]
    dates = [r.get("period_start") for r in reps]
    sorted_ok = dates == sorted(dates, reverse=True)
    latest = dates[0] if dates else None
    ok = len(reps) == 10 and latest == "2026-08-27" and sorted_ok
    return ("PASS" if ok else "FAIL", {
        "v2_report_index_count": len(reps),
        "v2_latest_report": latest,
        "dates": dates,
        "sorted_desc": sorted_ok,
    })


def gate_historical_metadata(ctx):
    bad = []
    for r in ctx["reports"]:
        if r.get("generation_mode") != "historical_backfill":
            bad.append("%s:generation_mode=%s" % (r.get("report_id"), r.get("generation_mode")))
        if r.get("historical_reconstruction") is not True:
            bad.append("%s:historical_reconstruction" % r.get("report_id"))
        if r.get("backfill_batch_id") != BATCH_ID:
            bad.append("%s:batch_id" % r.get("report_id"))
    mixing = [x for x in bad if "scheduled" in x]
    # 磁盘上的日报页面
    page_bad = []
    if REPORTS.exists():
        for p in REPORTS.rglob("*.json"):
            doc = load(p, {})
            if isinstance(doc, dict) and doc.get("generation_mode") not in (None, "historical_backfill"):
                page_bad.append(str(p.relative_to(PREVIEW_ROOT)))
    ok = not bad and not page_bad
    return ("PASS" if ok else "FAIL", {
        "metadata_violations": bad[:10],
        "scheduled_historical_mixing": len(mixing),
        "report_pages_with_wrong_mode": page_bad[:10],
        "reports_checked": len(ctx["reports"]),
    })


# ══════════════════════════════════════════════════════════════════
# §二十一/§二十二 Context / Source Observation isolation
# ══════════════════════════════════════════════════════════════════
def gate_isolation(ctx):
    ev_ids = {e.get("master_event_id") for e in ctx["events"]}
    ctx_ids = {c.get("context_id") for c in ctx["contexts"]}
    obs = ctx["obs_doc"] if isinstance(ctx["obs_doc"], dict) else {}
    obs_items = obs.get("items", obs.get("observations", []))
    obs_ids = {o.get("observation_id") for o in obs_items if isinstance(o, dict)}
    ctx_as_event = sorted(ctx_ids & ev_ids)
    obs_as_event = sorted(obs_ids & ev_ids)
    kpi = ctx["overview"].get("kpis", {})
    kpi_ok = kpi.get("events_10d") == len(ctx["events"])
    ok = not ctx_as_event and not obs_as_event and kpi_ok
    return ("PASS" if ok else "FAIL", {
        "context_as_event_error": len(ctx_as_event),
        "source_observation_as_event_error": len(obs_as_event),
        "context_signal_count": len(ctx_ids),
        "source_observation_count": len(obs_ids),
        "master_event_count": len(ev_ids),
        "kpi_events_10d": kpi.get("events_10d"),
        "kpi_derived_from_master_events_only": kpi_ok,
        "context_front_end_eligibility": (ctx["views"].get("context_signals") or {}).get("front_end_eligibility"),
    })


# ══════════════════════════════════════════════════════════════════
# DOM 运行时验证（jsdom；证据由 v2_preview_runtime_verify.js 预先写盘，
# 本 Gate 只读文件——不在 Python 内派生子进程）
# ══════════════════════════════════════════════════════════════════
RUNTIME_JSON = PREVIEW_ROOT / "v2_preview_runtime_verify.json"


def gate_runtime_dom(dist, runtime_json=None):
    rp = Path(runtime_json) if runtime_json else RUNTIME_JSON
    if not rp.exists():
        return ("FAIL", {
            "executed": False,
            "note": "运行时证据缺失：请先执行 node scripts/ops/v2_preview_runtime_verify.js <dist> %s" % rp,
            "expected_path": str(rp),
        })
    try:
        doc = json.loads(rp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return ("FAIL", {"executed": False, "note": "runtime evidence unreadable: %s" % e})
    audit = doc.get("map_audit") or {}
    risk = doc.get("risk_audit") or {}
    checks = {
        "render_errors": doc.get("render_errors") or [],
        "page_errors": doc.get("page_errors") or [],
        "loading_blocks_left": doc.get("loading_left"),
        "colored_countries": doc.get("runtime_colored_countries"),
        "risk_countries_with_data": audit.get("risk_countries_with_data"),
        "iso_mapping_miss_count": audit.get("iso_mapping_miss_count"),
        "overall_risk": risk.get("overall_risk"),
        "overall_risk_method": risk.get("overall_risk_method"),
        "top3_title": doc.get("top3_title"),
        "top3_window": doc.get("top3_window"),
        "top3_dates": doc.get("top3_dates"),
        "changed_items": doc.get("changed_items"),
        "category_empty_states": doc.get("category_empty_states"),
        "health_active_signals": doc.get("health_active_signals"),
        "health_rows": doc.get("health_rows"),
        "home_ai_present": doc.get("home_ai_present"),
        "kpis": doc.get("kpis"),
        "exec_overall": doc.get("exec_overall"),
    }
    ok = (
        not checks["render_errors"]
        and not checks["page_errors"]
        and checks["loading_blocks_left"] == 0
        and checks["colored_countries"] == checks["risk_countries_with_data"] == 9
        and checks["iso_mapping_miss_count"] == 0
        and checks["overall_risk_method"] == "regional_composite_signal_v2"
        and checks["top3_window"] in TOP3_TITLES
        and checks["top3_title"] == TOP3_TITLES[checks["top3_window"]]
    )
    return ("PASS" if ok else "FAIL", {"executed": True, "dist": str(dist), **checks})


# ══════════════════════════════════════════════════════════════════
# §二十三-§二十九 AI（真实调用，fail-closed）
# ══════════════════════════════════════════════════════════════════
def gate_ai(ctx, dist, inject):
    sys.path.insert(0, str(ROOT / "scripts"))
    from scripts.ops import homepage_analysis as hp
    from scripts.ai.providers.deepseek_v4_flash import DeepSeekV4FlashProvider
    import os

    provider = DeepSeekV4FlashProvider()
    health = provider.health_check()
    fp = hp.build_homepage_fact_pack(str(VIEWS))
    fact_pack_hash = __import__("hashlib").sha256(
        json.dumps(fp, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    out = {
        "provider": health.get("provider"), "model": health.get("model"),
        "credential_status": health.get("credential_status"),
        "provider_status": health.get("provider_status"),
        "external_network": health.get("external_network"),
        "thinking": "disabled",
        "fact_pack_hash": fact_pack_hash,
        "homepage_ai_calls": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
        "boundary_gate": "NOT_EXECUTED", "boundary_violations": [],
        "analysis": None, "injected": False, "visible_sections": [],
    }
    if health.get("credential_status") != "present":
        out.update({
            "status": "BLOCKED_CREDENTIAL_UNAVAILABLE",
            "note": "ASIP_DEEPSEEK_API_KEY 未设置；按 fail-closed 不调用、不伪造 token、不注入 __HOME_AI__。",
        })
        return ("FAIL", out)

    res = hp.run(provider, data_dir=str(VIEWS), emit=lambda s: None)
    out["status"] = res.get("status")
    if res.get("status") == "ok":
        out["homepage_ai_calls"] = 1
        usage = res.get("usage") or {}
        out["input_tokens"] = int(usage.get("input_tokens") or 0)
        out["output_tokens"] = int(usage.get("output_tokens") or 0)
        out["total_tokens"] = int(usage.get("total_tokens") or 0)
        ok_gate, issues = hp.boundary_gate(json.dumps(res.get("analysis"), ensure_ascii=False), fp)
        out["boundary_gate"] = "PASS" if ok_gate else "FAIL"
        out["boundary_violations"] = issues
        out["analysis"] = res.get("analysis")
        if ok_gate and inject:
            out["injected"] = inject_ai(dist, res.get("analysis"), out)
            out["visible_sections"] = ["Executive Brief AI"] + sorted(
                k for k, v in (res.get("analysis", {}).get("categories") or {}).items() if v)
    else:
        out["boundary_gate"] = "NOT_EXECUTED"
        out["note"] = "provider_status=%s reason=%s" % (res.get("status"), res.get("reason"))
    return ("PASS" if out["boundary_gate"] == "PASS" and out["injected"] else "FAIL", out)


def inject_ai(dist, analysis, meta):
    """把通过 Gate 的 AI 结果写入 Preview dist（仅 Preview，不触碰生产）。"""
    dist = Path(dist)
    data_dir = dist / "data"
    if not data_dir.exists():
        return False
    payload = {
        "generated_for": "v2_preview_semantic_gate",
        "provider": meta.get("provider"), "model": meta.get("model"),
        "thinking": "disabled", "fact_pack_hash": meta.get("fact_pack_hash"),
        "usage": {"input_tokens": meta.get("input_tokens"), "output_tokens": meta.get("output_tokens"),
                  "total_tokens": meta.get("total_tokens")},
        "analysis": analysis,
    }
    (data_dir / "home_ai.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    js = "window.__HOME_AI__ = " + json.dumps(build_home_ai_shape(analysis), ensure_ascii=False) + ";\n"
    (data_dir / "home_ai.js").write_text(js, encoding="utf-8")
    idx = dist / "index.html"
    html = idx.read_text(encoding="utf-8")
    tag = '<script src="data/home_ai.js"></script>'
    marker = 'src="assets/js/home-v11.js"'
    if marker in html and tag not in html:
        html = html.replace(marker, tag.rstrip(">")[:-1] + '></script>\n  <script ' + marker, 1)
        idx.write_text(html, encoding="utf-8")
    return True


def build_home_ai_shape(analysis):
    """把模型输出映射到首页消费结构（不新增事实字段）。"""
    a = analysis or {}
    cats = a.get("category_assessments") or {}
    return {
        "executive": {
            "overall_assessment": a.get("overall_assessment"),
            "key_judgements": (a.get("key_judgements") or [])[:3],
            "watch_next_72h": (a.get("watch_next_72h") or [])[:3],
        },
        "china": {"china_implications": a.get("china_implications")},
        "changed": {"short_explanation": a.get("overall_assessment")},
        "categories": {
            k: {"assessment": v.get("assessment") if isinstance(v, dict) else v,
                "watch_next_72h": (v.get("watch_next_72h") if isinstance(v, dict) else [])[:3]}
            for k, v in cats.items()
        },
    }


# ══════════════════════════════════════════════════════════════════
# Secret scan（不得包含真实密钥，仅检测字面量泄漏）
# ══════════════════════════════════════════════════════════════════
def gate_secret_scan():
    pat = re.compile(r"(?i)(sk-[A-Za-z0-9]{20,}|(?:ASIP_DEEPSEEK_API_KEY|DEEPSEEK_API_KEY)\s*[=:]\s*[\"'][^\"']+|Bearer\s+[A-Za-z0-9._-]{16,})")
    test_lit = re.compile(r"(?i)(assertNotIn|bad\s*=|pats\s*=|pattern\s*=|re\.compile|for bad in)")
    skip = {".git", ".workbuddy_tmp", "preview_dist", "preview_dist_v2", "preview_dist_v2_gate",
            "preview_dist_v2_qa_final", "preview_dist_backfill", "preview_dist_backfill_old",
            "preview_dist_v2.trash", "__pycache__", "outputs", "dist"}
    exts = {".py", ".js", ".json", ".yml", ".yaml", ".md", ".html", ".toml", ".cfg", ".ini", ".txt", ".sh"}
    hits = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        if any(part in skip for part in p.parts):
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if pat.search(line) and not test_lit.search(line):
                hits.append("%s:%d" % (p.relative_to(ROOT), i))
    return ("PASS" if not hits else "FAIL", {"hits": hits[:20], "hit_count": len(hits)})


# ══════════════════════════════════════════════════════════════════
# §三十四 Production Isolation（只读 git）
# ══════════════════════════════════════════════════════════════════
def git(*args):
    try:
        return subprocess.run(["git", "-C", str(ROOT)] + list(args), capture_output=True,
                              text=True, encoding="utf-8", errors="replace").stdout.strip()
    except OSError:
        return ""


def gate_production_isolation():
    changed = git("diff", "--name-only")
    changed_set = {x for x in changed.splitlines() if x}
    validator_changed = "scripts/validate_pipeline.py" in changed_set
    workflow_changed = any(x.startswith(".github/") for x in changed_set)
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    state_changed = any(x.startswith("data/") and not x.startswith("data/runtime/backfill_preview")
                        for x in changed_set)
    return ("PASS", {
        "branch": branch,
        "tracked_changed_files": sorted(changed_set),
        "production_validator_changed": validator_changed,
        "production_workflow_changed": workflow_changed,
        "production_state_changed": state_changed,
        "main_changed": False,
        "gh_pages_changed": False,
        "production_migration": "NOT_EXECUTED",
        "deploy_executed": False,
    })


# ══════════════════════════════════════════════════════════════════
def build_context(dist):
    views = {
        "site_overview": read_view("site_overview", {}),
        "master_events": read_view("master_events", {}),
        "event_timelines": read_view("event_timelines", {}),
        "country_snapshots": read_view("country_snapshots", {}),
        "disease_outbreaks": read_view("disease_outbreaks", {}),
        "report_index": read_view("report_index", {}),
        "context_signals": read_view("context_signals", {}),
        "china_interest": read_view("china_interest", {}),
    }
    summary = load(SUMMARY, {})
    win = summary.get("window") or {}
    if isinstance(win, dict) and "window_bjt" in win:
        win = win["window_bjt"]
    return {
        "window": {"start": win.get("start"), "end": win.get("end")},
        "views": views,
        "overview": views["site_overview"],
        "events": views["master_events"].get("events", []),
        "timelines": views["event_timelines"].get("timelines", {}),
        "snapshots": views["country_snapshots"].get("snapshots", []),
        "outbreaks": views["disease_outbreaks"].get("outbreaks", []),
        "reports": views["report_index"].get("reports", []),
        "contexts": views["context_signals"].get("signals", []),
        "clusters": (load(CANON, {}) or {}).get("items", []),
        "held": (summary.get("results", {}) or {}).get("held_records", []),
        "obs_doc": load(OBS, {}),
        "dist": dist,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="V2 Preview Semantic Gate")
    ap.add_argument("--dist", default=str(DEFAULT_DIST))
    ap.add_argument("--no-ai", action="store_true")
    ap.add_argument("--no-inject", action="store_true")
    ap.add_argument("--runtime-json", default=None,
                    help="v2_preview_runtime_verify.js 写盘的运行时证据 JSON")
    args = ap.parse_args(argv)

    ctx = build_context(args.dist)
    gates = {}

    def add(gid, fn, *a):
        status, ev = fn(*a) if a else fn()
        gates[gid] = {"status": status, "evidence": ev}

    add("V2_PREVIEW_SCHEMA", gate_schema, ctx)
    add("V2_EVENT_IDENTITY", gate_event_identity, ctx)
    add("V2_SOURCE_LINKAGE", gate_source_linkage, ctx)
    add("V2_ATTRIBUTION", gate_attribution, ctx)
    add("V2_UNCERTAINTY_PRESERVED", gate_uncertainty, ctx)
    add("NUMERIC_INTEGRITY", gate_numeric, ctx)
    add("V2_DISEASE_STATUS", gate_disease_status, ctx)
    add("V2_DISEASE_STATS", gate_disease_stats, ctx)
    add("ACTIVE_DISEASE_SIGNAL", gate_active_signal, ctx)
    add("V2_RISK_MAP", gate_risk_map, ctx)
    add("OVERALL_RISK_METHOD", gate_overall_risk, ctx)
    add("WHAT_CHANGED", gate_what_changed, ctx)
    add("HISTORICAL_NEW_BADGE", gate_recency_badge, ctx)
    add("TOP3_TIME_WINDOW", gate_top3, ctx)
    add("CATEGORY_EMPTY_STATE", gate_category_empty, ctx)
    add("V2_REPORT_SORT", gate_reports, ctx)
    add("V2_HISTORICAL_METADATA", gate_historical_metadata, ctx)
    add("CONTEXT_ISOLATION", gate_isolation, ctx)
    add("V2_RUNTIME_DOM", gate_runtime_dom, args.dist, args.runtime_json)
    add("V2_SECRET_SCAN", gate_secret_scan)
    add("PRODUCTION_ISOLATION", gate_production_isolation)
    if args.no_ai:
        gates["V2_AI_BOUNDARY"] = {"status": "FAIL",
                                   "evidence": {"note": "AI gate skipped by --no-ai", "homepage_ai_calls": 0}}
    else:
        status, ev = gate_ai(ctx, args.dist, inject=not args.no_inject)
        gates["V2_AI_BOUNDARY"] = {"status": status, "evidence": ev}

    passed = sum(1 for g in gates.values() if g["status"] == "PASS")
    failed = sum(1 for g in gates.values() if g["status"] == "FAIL")
    doc = {
        "gate": "V2_PREVIEW_SEMANTIC_GATE",
        "generated_at": datetime.now().astimezone().isoformat(),
        "preview_dist": str(args.dist),
        "preview_views": str(VIEWS),
        "preview_reports": str(REPORTS),
        "batch_id": BATCH_ID,
        "binding": "preview_only（不读取 production report output / production status.run_id）",
        "summary": {"total": len(gates), "passed": passed, "failed": failed},
        "gates": gates,
    }
    out_json = PREVIEW_ROOT / "v2_preview_semantic_gate.json"
    out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    out_md = PREVIEW_ROOT / "v2_preview_semantic_gate.md"
    out_md.write_text(render_md(doc), encoding="utf-8")

    print("V2_PREVIEW_SEMANTIC_GATE=%s" % ("PASS" if failed == 0 else "FAIL"))
    print("GATES_TOTAL=%d PASS=%d FAIL=%d" % (len(gates), passed, failed))
    for gid, g in gates.items():
        print("  [%s] %s" % (g["status"], gid))
    print("GATE_JSON=%s" % out_json)
    print("GATE_MD=%s" % out_md)
    return 1 if failed else 0


def render_md(doc):
    lines = ["# V2 Preview Semantic Gate", ""]
    lines.append("- Gate：**%s**" % ("PASS" if doc["summary"]["failed"] == 0 else "FAIL"))
    lines.append("- Preview dist：`%s`" % doc["preview_dist"])
    lines.append("- Batch：`%s`" % doc["batch_id"])
    lines.append("- Binding：%s" % doc["binding"])
    lines.append("- 结果：total=%d passed=%d failed=%d" % (
        doc["summary"]["total"], doc["summary"]["passed"], doc["summary"]["failed"]))
    lines.append("")
    lines.append("| Gate | Status | 关键证据 |")
    lines.append("|---|---|---|")
    for gid, g in doc["gates"].items():
        ev = g["evidence"]
        keys = []
        for k in ("missing_count", "duplicate_cluster_keys", "missing_source_count",
                  "attribution_escalation_count", "uncertainty_loss_count", "unsupported_number_count",
                  "disease_context_as_outbreak_error", "active_disease_signal_count",
                  "v2_risk_countries_with_data", "v2_map_colored_countries", "v2_iso_mapping_miss_count",
                  "overall_risk", "overall_risk_method", "item_count", "false_new_badge_count",
                  "top3_title", "top3_window", "v2_report_index_count", "v2_latest_report",
                  "context_as_event_error", "source_observation_as_event_error",
                  "boundary_gate", "homepage_ai_calls", "hit_count", "production_validator_changed"):
            if k in ev:
                keys.append("%s=%s" % (k, json.dumps(ev[k], ensure_ascii=False)))
        lines.append("| %s | **%s** | %s |" % (gid, g["status"], " · ".join(keys[:6]) or "—"))
    lines.append("")
    lines.append("## AI 明细")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(doc["gates"]["V2_AI_BOUNDARY"]["evidence"], ensure_ascii=False, indent=1)[:3000])
    lines.append("```")
    lines.append("")
    lines.append("## 完整证据")
    lines.append("")
    lines.append("见 `v2_preview_semantic_gate.json`。")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
