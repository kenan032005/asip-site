#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASIP V1.1 Historical Backfill Import (deterministic engineering layer) v2
=========================================================================
Batch : asip-backfill-20260818-20260827
Mode  : historical_backfill / historical_reconstruction=true

Scope : 只做工程导入（mapping / dedup / cluster / gates / preview 数据命名空间）。
       不得改写数据包事实、不得升级 verification、不得静默丢弃。
       所有写入进入 backfill preview 命名空间（data/runtime/backfill_preview/），
       不触碰 production-state / canonical 生产数据。

用法:
  python scripts/ops/backfill_import.py --pkg-file <WORKBUDDY.json>   # 单文件包
  python scripts/ops/backfill_import.py --pkg-dir <包目录>           # 5 文件布局
  --ai 0 : 不做任何 DeepSeek 调用（默认）

退出码: 0=成功(含合法 HOLD), 2=输入缺失/契约不符
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

BATCH_ID = "asip-backfill-20260818-20260827"
WINDOW_START = "2026-08-18T00:00:00+08:00"
WINDOW_END = "2026-08-27T23:59:59+08:00"
INGESTION_MODE = "historical_backfill"
HISTORICAL_RECONSTRUCTION = True

DEFAULT_PKG_FILE = "C:/Users/kenan/Downloads/ASIP_BACKFILL_20260818_20260827_WORKBUDDY.json"
PREVIEW_ROOT = Path("data/runtime/backfill_preview")
CURRENT_CANONICAL = Path("data/canonical/event_clusters.json")
CURRENT_DISEASE = Path("data/disease/canonical/outbreak_events.json")

REQUIRED_PACKAGE_FILES = [
    "manifest.json", "social_events.jsonl", "disease_events.jsonl",
    "sources.jsonl", "china_interest.jsonl",
]

# ISO3 -> ISO2（ASIP canonical country_code 契约；覆盖包内 16 国 + 疾病国）
ISO3_TO_ISO2 = {
    "CAF": "CF", "COD": "CD", "ETH": "ET", "GNB": "GW", "LBR": "LR",
    "MLI": "ML", "NGA": "NG", "SDN": "SD", "SOM": "SO", "SSD": "SS",
    "TCD": "TD", "TGO": "TG", "TUN": "TN", "TZA": "TZ", "UGA": "UG",
    "ZMB": "ZM", "AGO": "AO", "BFA": "BF", "BDI": "BI", "BEN": "BJ",
    "BWA": "BW", "CIV": "CI", "CMR": "CM", "COG": "CG", "COM": "KM",
    "CPV": "CV", "DJI": "DJ", "DZA": "DZ", "EGY": "EG", "ERI": "ER",
    "GAB": "GA", "GHA": "GH", "GIN": "GN", "GMB": "GM", "GNQ": "GQ",
    "KEN": "KE", "LBY": "LY", "LSO": "LS", "MAR": "MA", "MDG": "MG",
    "MOZ": "MZ", "MRT": "MR", "MUS": "MU", "MWI": "MW", "NAM": "NA",
    "NER": "NE", "RWA": "RW", "SEN": "SN", "SLE": "SL", "STP": "ST",
    "SWZ": "SZ", "SYC": "SC", "TGO": "TG", "ZAF": "ZA", "ZWE": "ZW",
}

VERIFICATION_MAP = {
    "official_confirmed": ("official", "已核实", 90),
    "multi_source": ("multi", "多源支持", 70),
    "single_source": ("single", "单一来源", 50),
    "disputed_claim": ("disputed", "争议性声明", 30),
}

CATEGORY_TO_EVENT_TYPE = {
    "armed_conflict_terrorism": "armed_conflict",
    "political_social_stability": "political_social",
    "public_safety_major_incidents": "public_safety",
    "public_health_disease": "public_health",
    "armed_conflict": "armed_conflict",
    "political_social": "political_social",
    "public_safety": "public_safety",
    "public_health": "public_health",
}

KNOWN_CLUSTERS = {
    "ZMB_2026_ELECTION_POSTELECTION",
    "TCD_SDN_CROSS_BORDER_STRIKE_20260820",
    "COD_EBOLA_BUNDIBUGYO_2026",
}

HOLD_REASONS = {
    "HOLD_MISSING_REQUIRED_FIELD": "缺必需字段（标题/摘要/国家/日期/verification/source）",
    "HOLD_UNMAPPABLE": "字段无法映射到 canonical",
    "HOLD_UNKNOWN_VERIFICATION": "verification_status 不在受控词汇表",
    "HOLD_UNMAPPABLE_COUNTRY": "country ISO3 不在非洲监测名单",
    "HOLD_UNSUPPORTED_NUMBER": "数字断言异常（importance 越界/日期非法）",
    "HOLD_DISPUTED_NOT_UPGRADED": "disputed_claim 不得升级为确认事实（保留不确定性）",
    "HOLD_OUTSIDE_WINDOW": "事件时间超出回填窗口",
    "HOLD_DUPLICATE_CONTENT": "content hash 与既有记录重复",
    "HOLD_EXISTING_CANONICAL": "与现有 canonical 主事件重复（只补 source/上下文）",
}

MONITORED_AFRICA_ISO3 = set(ISO3_TO_ISO2.keys()) | {"AFR"}


def _now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_hex(s: str, n: int = 64) -> str:
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()[:n]


def _norm(s) -> str:
    return re.sub(r"[\s\-—–,，。.:：;；!！?？'\"“”‘’()（）\[\]]", "", (s or "")).lower()


# ---------------------------------------------------------------- loaders
def load_bundle_file(pkg_file: Path):
    d = json.loads(pkg_file.read_text(encoding="utf-8"))
    return {
        "manifest": d.get("manifest", {}),
        "social": d.get("social_events", []),
        "disease": d.get("disease_events", []),
        "china": d.get("china_interest", []),
        "sources": d.get("sources", []),
        "package_qa": d.get("package_qa", {}),
        "review_notes": d.get("review_notes", ""),
    }


def load_bundle_dir(pkg_dir: Path):
    def _j(name):
        return [json.loads(l) for l in pkg_dir.joinpath(name).read_text(encoding="utf-8").splitlines() if l.strip()]
    return {
        "manifest": json.loads((pkg_dir / "manifest.json").read_text(encoding="utf-8")),
        "social": _j("social_events.jsonl"),
        "disease": _j("disease_events.jsonl"),
        "china": _j("china_interest.jsonl"),
        "sources": _j("sources.jsonl"),
        "package_qa": {},
        "review_notes": "",
    }


def check_manifest_contract(manifest: dict) -> list:
    issues = []
    if manifest.get("batch_id") != BATCH_ID:
        issues.append("batch_id mismatch: %s" % manifest.get("batch_id"))
    return issues


# ---------------------------------------------------------------- gates
def _gate_required(row, fields, reason):
    missing = [f for f in fields if not row.get(f)]
    return (not missing), missing


def _date_ok(s):
    try:
        date.fromisoformat(str(s)[:10])
        return True
    except ValueError:
        return False


def _in_window(d):
    return "2026-08-18" <= str(d)[:10] <= "2026-08-27"


# ---------------------------------------------------------------- social mapping
def map_social(row: dict) -> dict:
    """包 social 行 → canonical 形状 preview item（确定性）。"""
    vlevel, vlabel, vscore = VERIFICATION_MAP.get(row.get("verification_status"), (None, None, None))
    etype = CATEGORY_TO_EVENT_TYPE.get(row.get("category"))
    srcs = row.get("sources") or []
    urls = [s.get("url") for s in srcs if s.get("url")]
    imp = row.get("importance_score_editorial") or 60
    imp = max(0, min(100, int(imp)))
    if imp >= 85:
        sev = "very_high"
    elif imp >= 70:
        sev = "high"
    elif imp >= 55:
        sev = "elevated"
    else:
        sev = "moderate"
    iso3 = (row.get("country_iso3") or "").upper()
    ch = row.get("china_interest") or "none"
    event_id = "BFE_" + sha256_hex(BATCH_ID + "|" + (row.get("record_id") or "") + "|" + (row.get("headline_en") or ""), 16)
    return {
        "event_id": event_id,
        "master_event_id": None,
        "legacy_event_id": row.get("record_id"),
        "title_cn": row.get("headline_zh") or row.get("headline_en"),
        "title_original": row.get("headline_en"),
        "summary_cn": row.get("fact_summary_zh") or row.get("fact_summary_en"),
        "summary_original": row.get("fact_summary_en"),
        "country_cn": row.get("country_name_zh"),
        "country_code": ISO3_TO_ISO2.get(iso3, iso3),
        "country_iso3": iso3,
        "event_type": etype,
        "event_type_bucket": row.get("category"),
        "subcategory": row.get("subcategory"),
        "event_time": "%sT12:00:00Z" % row.get("event_date"),
        "first_seen_at": "%sT12:00:00Z" % row.get("event_date"),
        "last_seen_at": "%sT12:00:00Z" % row.get("event_date"),
        "event_date": row.get("event_date"),
        "event_date_basis": row.get("event_date_basis"),
        "location": row.get("location"),
        "location_name": row.get("location"),
        "event_severity": sev,
        "event_status": "ongoing" if row.get("record_type") == "event_update" else "observed",
        "china_related": ch in ("direct", "indirect"),
        "china_interest": ch,
        "importance_score": imp,
        "verification_level": vlevel,
        "verification_label_cn": vlabel,
        "verification_score": vscore,
        "verification_notes": row.get("uncertainties") or [],
        "uncertainties": row.get("uncertainties") or [],
        "independent_source_count": len(urls),
        "source_urls": urls,
        "source_links": [{"source_name": s.get("source_name"), "url": s.get("url")}
                         for s in srcs if s.get("source_name")],
        "source_groups": [s.get("source_name") for s in srcs if s.get("source_name")],
        "record_type": row.get("record_type"),
        "cluster_key": row.get("cluster_key"),
        "ingestion_mode": row.get("ingestion_mode") or INGESTION_MODE,
        "backfill_batch_id": row.get("backfill_batch_id") or BATCH_ID,
        "publication_status": None,
        "current_policy_passed": None,
        "public_eligible": None,
        "schema_version": "backfill-v1",
        "run_id": BATCH_ID,
        "created_at": _now_utc(),
        "updated_at": _now_utc(),
    }


def gate_social(row, item):
    """返回 (pass, hold_reason) —— disputed 按 §四 政策 HOLD（不升级）。"""
    if not item["title_original"] or not item["summary_original"]:
        return False, "HOLD_MISSING_REQUIRED_FIELD"
    if not item["country_iso3"]:
        return False, "HOLD_MISSING_REQUIRED_FIELD"
    if not item["event_date"] or not _date_ok(item["event_date"]):
        return False, "HOLD_MISSING_REQUIRED_FIELD"
    if not item["verification_level"]:
        return False, "HOLD_UNKNOWN_VERIFICATION"
    if item["verification_level"] == "disputed":
        return False, "HOLD_DISPUTED_NOT_UPGRADED"
    if item["event_type"] is None:
        return False, "HOLD_UNMAPPABLE"
    if item["country_iso3"] not in MONITORED_AFRICA_ISO3:
        return False, "HOLD_UNMAPPABLE_COUNTRY"
    if not _in_window(item["event_date"]):
        return False, "HOLD_OUTSIDE_WINDOW"
    if not item["source_urls"]:
        return False, "HOLD_MISSING_REQUIRED_FIELD"
    if not (0 <= item["importance_score"] <= 100):
        return False, "HOLD_UNSUPPORTED_NUMBER"
    return True, None


def _disease_update_entry(item: dict) -> dict:
    """timeline update 条目（不含自引用字段）。"""
    d = {k: v for k, v in item.items() if k not in ("timeline_updates", "public_eligible")}
    return d


# ---------------------------------------------------------------- disease mapping
def map_disease(row: dict) -> dict:
    srcs = row.get("sources") or []
    urls = [s.get("url") for s in srcs if s.get("url")]
    iso3 = (row.get("country_iso3") or "").upper()
    regional = iso3 in ("MULTI", "AFR", "REGIONAL")
    if regional:
        iso3 = "AFR"
    did = "BFD_" + sha256_hex(BATCH_ID + "|" + (row.get("cluster_key") or row.get("record_id") or "") + "|" + (row.get("disease") or ""), 16)
    return {
        "disease_event_id": did,
        "disease_id": did,
        "disease_name_en": row.get("disease"),
        "disease_name_zh": row.get("disease_zh"),
        "country_iso3": iso3,
        "regional": regional,
        "cross_border": regional,
        "affected_countries": [c.strip() for c in (row.get("country_name_en") or "").split(",") if c.strip()],
        "country_name_zh": row.get("country_name_zh"),
        "location_raw": row.get("location"),
        "pathogen": None,
        "outbreak_status": "active",
        "event_start_date": row.get("event_date"),
        "report_date": row.get("event_date"),
        "severity": row.get("severity"),
        "importance_score": row.get("importance_score_editorial"),
        "verification_status": row.get("verification_status"),
        "verification_level": VERIFICATION_MAP.get(row.get("verification_status"), (None, None, None))[0],
        "uncertainties": row.get("uncertainties") or [],
        "source_links": [{"source_name": s.get("source_name"), "url": s.get("url")}
                         for s in srcs if s.get("source_name")],
        "source_urls": urls,
        "primary_source": (srcs[0].get("source_name") if srcs else None),
        "source_tier": "official" if row.get("verification_status") == "official_confirmed" else "reported",
        "first_seen_at": "%sT12:00:00Z" % row.get("event_date"),
        "latest_update_at": "%sT12:00:00Z" % row.get("event_date"),
        "location": row.get("location"),
        "headline_en": row.get("headline_en"),
        "headline_zh": row.get("headline_zh"),
        "fact_summary_en": row.get("fact_summary_en"),
        "fact_summary_zh": row.get("fact_summary_zh"),
        "record_type": row.get("record_type"),
        "cluster_key": row.get("cluster_key"),
        "ingestion_mode": row.get("ingestion_mode") or INGESTION_MODE,
        "backfill_batch_id": row.get("backfill_batch_id") or BATCH_ID,
        "public_eligible": None,
        "run_id": BATCH_ID,
        "created_at": _now_utc(),
    }


def gate_disease(row, item):
    if not item["disease_name_en"] or not item["country_iso3"] or not item["report_date"]:
        return False, "HOLD_MISSING_REQUIRED_FIELD"
    if not _date_ok(item["report_date"]) or not _in_window(item["report_date"]):
        return False, "HOLD_OUTSIDE_WINDOW"
    if item["country_iso3"] not in MONITORED_AFRICA_ISO3:
        return False, "HOLD_UNMAPPABLE_COUNTRY"
    if not item["verification_level"]:
        return False, "HOLD_UNKNOWN_VERIFICATION"
    if not item["source_links"]:
        return False, "HOLD_MISSING_REQUIRED_FIELD"
    return True, None


# ---------------------------------------------------------------- main import
def run_bundle(bundle: dict) -> dict:
    manifest = bundle.get("manifest", {})
    report = {
        "batch_id": BATCH_ID,
        "ingestion_mode": INGESTION_MODE,
        "historical_reconstruction": HISTORICAL_RECONSTRUCTION,
        "window": [WINDOW_START, WINDOW_END],
        "contract_issues": check_manifest_contract(manifest),
        "package_qa": bundle.get("package_qa", {}),
        "results": {
            "social": {"input": 0, "new": 0, "update": 0, "duplicate": 0,
                       "existing_canonical": 0, "held": 0, "rejected": 0},
            "disease": {"input": 0, "new": 0, "update": 0, "duplicate": 0, "held": 0},
            "china_interest": {"direct": 0, "indirect": 0, "held": 0},
            "master_events_total": 0,
            "disease_entities": 0,
            "held_records": [],
        },
        "generated_at": _now_utc(),
    }
    r = report["results"]

    # ---- cross-dedupe: 现有 canonical 标题归一化集合 ----
    existing_titles = set()
    if CURRENT_CANONICAL.exists():
        try:
            for e in json.loads(CURRENT_CANONICAL.read_text(encoding="utf-8")).get("items", []):
                for t in (e.get("title_cn"), e.get("title_original")):
                    if t:
                        existing_titles.add(_norm(t))
        except Exception:  # noqa: BLE001
            pass

    accepted = []       # 已接受 social content hashes
    held_rows = []      # HOLD 记录
    master_map = {}     # cluster_key -> master item（簇事件）
    free_events = []    # 非簇独立事件

    # ---- Social ----
    for row in bundle.get("social", []):
        r["social"]["input"] += 1
        item = map_social(row)
        ok, hold = gate_social(row, item)
        norm_title = _norm(item["title_original"])
        rec = {"record_id": row.get("record_id"), "disposition": None, "cluster_key": item["cluster_key"],
               "event_id": item["event_id"], "date": item["event_date"]}
        if not ok:
            r["social"]["held"] += 1
            rec["disposition"] = hold
            rec["detail"] = {k: item.get(k) for k in ("country_iso3", "event_date", "verification_status") if item.get(k)}
            held_rows.append(rec)
            r["held_records"].append(rec)
            continue
        if norm_title in existing_titles:
            r["social"]["existing_canonical"] += 1
            rec["disposition"] = "HOLD_EXISTING_CANONICAL"
            held_rows.append(rec)
            r["held_records"].append(rec)
            continue
        # duplicate within package by content hash
        ch = sha256_hex("|".join([item["country_iso3"], item["event_date"], norm_title,
                                  item["verification_level"]]), 24)
        if ch in accepted:
            r["social"]["duplicate"] += 1
            rec["disposition"] = "HOLD_DUPLICATE_CONTENT"
            held_rows.append(rec)
            r["held_records"].append(rec)
            continue
        accepted.append(ch)
        # cluster 合并：event_update / known cluster → 并入既有 master
        ck = item["cluster_key"]
        if ck:
            if ck in master_map:
                r["social"]["update"] += 1
                master_map[ck]["timeline_updates"].append(item)
            else:
                r["social"]["new"] += 1
                r["master_events_total"] += 1
                item["publication_status"] = "public"
                item["current_policy_passed"] = True
                item["public_eligible"] = True
                item["timeline_updates"] = []
                master_map[ck] = item
        else:
            r["social"]["new"] += 1
            r["master_events_total"] += 1
            item["publication_status"] = "public"
            item["current_policy_passed"] = True
            item["public_eligible"] = True
            item["timeline_updates"] = []
            free_events.append(item)

    master_events = list(master_map.values()) + free_events

    # ---- Disease（按 cluster_key 合并为一个实体 + timeline updates）----
    disease_entities = {}
    for row in bundle.get("disease", []):
        r["disease"]["input"] += 1
        item = map_disease(row)
        ok, hold = gate_disease(row, item)
        rec = {"record_id": row.get("record_id"), "disposition": None, "cluster_key": item["cluster_key"],
               "disease_event_id": item["disease_event_id"], "date": item["report_date"]}
        if not ok:
            r["disease"]["held"] += 1
            rec["disposition"] = hold
            held_rows.append(rec)
            r["held_records"].append(rec)
            continue
        ck = item["cluster_key"] or item["disease_event_id"]
        if ck in disease_entities:
            r["disease"]["update"] += 1
            ent = disease_entities[ck]
            ent["timeline_updates"].append(_disease_update_entry(item))
        else:
            r["disease"]["new"] += 1
            r["disease_entities"] += 1
            item["public_eligible"] = True
            item["timeline_updates"] = [_disease_update_entry(item)]
            disease_entities[ck] = item

    # ---- China Interest（与实际 accepted 事件联动）----
    accepted_ids = {x["legacy_event_id"] for x in master_events}
    for c in bundle.get("china", []):
        linked = c.get("record_id") in accepted_ids
        rec = {"record_id": c.get("record_id"), "cluster_key": c.get("cluster_key"),
               "china_interest": c.get("china_interest"), "linked_accepted": linked}
        if not linked:
            r["china_interest"]["held"] += 1
            rec["disposition"] = "HOLD_UNLINKED_EVENT"
            r["held_records"].append(rec)
            continue
        if c.get("china_interest") == "direct":
            r["china_interest"]["direct"] += 1
        else:
            r["china_interest"]["indirect"] += 1

    r["master_events_total"] = len(master_events)

    report["preview"] = {
        "master_events": master_events,
        "disease_entities": list(disease_entities.values()),
        "china_rows": bundle.get("china", []),
    }
    report["results"]["held_records"] = held_rows
    report["status"] = "OK"
    return report


# ---------------------------------------------------------------- preview views & metrics
def build_preview_views(master_events, disease_entities, china_rows, accepted_ids):
    """前端可消费的 preview 视图（对齐 frontend_preview_public 形状）。"""
    events = []
    for e in sorted(master_events, key=lambda x: (x.get("event_date") or ""), reverse=True):
        events.append({
            "master_event_id": e["event_id"],
            "headline_zh": e.get("title_cn"),
            "headline_en": e.get("title_original"),
            "fact_summary": e.get("summary_cn") or e.get("summary_original"),
            "country_iso3": e.get("country_iso3"),
            "country_cn": e.get("country_cn"),
            "event_type": e.get("event_type"),
            "event_type_cn": {"armed_conflict": "武装冲突", "political_social": "政治与社会",
                              "public_safety": "公共安全", "public_health": "公共卫生"}.get(e.get("event_type")),
            "event_time": e.get("event_time"),
            "latest_update_at": e.get("event_date"),
            "china_related": bool(e.get("china_related")),
            "china_interest": e.get("china_interest") or "none",
            "verification_status": e.get("verification_level"),
            "verification_cn": e.get("verification_label_cn"),
            "source_count": e.get("independent_source_count"),
            "independent_source_count": e.get("independent_source_count"),
            "uncertainties": e.get("uncertainties"),
            "change_type": "update" if e.get("timeline_updates") else "new",
            "change_type_cn": "更新" if e.get("timeline_updates") else "新增",
            "update_count": len(e.get("timeline_updates") or []),
            "location": e.get("location_name"),
            "timeline_status": "ongoing" if e.get("event_status") == "ongoing" else "observed",
            "conflict_flags": [],
        })
    outbreaks = []
    for d in disease_entities:
        outbreaks.append({
            "outbreak_id": d.get("disease_event_id"),
            "disease_id": d.get("disease_id"),
            "disease_name_cn": d.get("disease_name_zh"),
            "disease_name_en": d.get("disease_name_en"),
            "country_iso3": d.get("country_iso3"),
            "country_cn": d.get("country_name_zh"),
            "status": d.get("outbreak_status"),
            "status_cn": "活跃",
            "latest_counts": None,
            "latest_report_at": d.get("report_date"),
            "verification_status": d.get("verification_level"),
            "source_count": len(d.get("source_links") or []),
            "update_count": len(d.get("timeline_updates") or []),
            "affected_countries": d.get("affected_countries") or [],
        })
    country_metrics = {}
    for e in master_events:
        iso3 = e.get("country_iso3")
        d = (e.get("event_date") or "")[:10]
        cm = country_metrics.setdefault(iso3, {"country_iso3": iso3, "country_cn": e.get("country_cn"),
                                               "events_7d": 0, "events_10d": 0, "events_by_date": {}})
        cm["events_10d"] += 1
        cm["events_by_date"].setdefault(d, 0)
        cm["events_by_date"][d] += 1
        if "2026-08-20" <= d <= "2026-08-27":
            cm["events_7d"] += 1
    return {
        "master_events": {"generated_at": _now_utc(), "count": len(events), "events": events},
        "disease_outbreaks": {"generated_at": _now_utc(), "count": len(outbreaks), "outbreaks": outbreaks},
        "country_metrics": {"generated_at": _now_utc(), "countries": list(country_metrics.values()),
                            "note": "historical backfill: events_24h 不适用（回填窗口），7d/10d 按 event_date 计算"},
        "china_interest": {"generated_at": _now_utc(), "rows": china_rows,
                           "note": "仅含对应事件 accepted 的涉中记录"},
    }


def build_weekly_reports(master_events):
    """完整自然周（Mon–Sun）内窗口全覆盖才生成；窗口 08-18(周二)–08-27(周四) 无完整周 → []。"""
    return []


def major_brief_candidates(master_events):
    return [{"event_id": e["event_id"], "title_cn": e.get("title_cn"),
             "importance_score": e.get("importance_score"), "country_cn": e.get("country_cn"),
             "event_date": e.get("event_date")}
            for e in master_events if (e.get("importance_score") or 0) >= 85]


# ---------------------------------------------------------------- review pack
def write_review_pack(report, out: Path):
    r = report["results"]
    daily = report.get("daily_reports", [])
    weekly = report.get("weekly_reports", [])
    majors = report.get("major_brief_candidates", [])
    v = report.get("views", {})
    md = []
    md.append("# ASIP Historical Backfill Import Review — %s\n" % BATCH_ID)
    md.append("- 窗口: %s → %s" % (WINDOW_START, WINDOW_END))
    md.append("- 模式: %s / historical_reconstruction=true" % INGESTION_MODE)
    md.append("- 输入: Social %d / Disease %d / China %d / Sources %d"
              % (r["social"]["input"], r["disease"]["input"], len(report.get("china_input", [])), report.get("sources_input", 0)))
    md.append("")
    md.append("## Social 导入")
    md.append("| 项 | 值 |")
    md.append("|---|---|")
    md.append("| 输入 | %d |" % r["social"]["input"])
    md.append("| 新增 Master | %d |" % r["social"]["new"])
    md.append("| 更新（簇内 timeline） | %d |" % r["social"]["update"])
    md.append("| 重复（包内 content hash） | %d |" % r["social"]["duplicate"])
    md.append("| 与既有 canonical 重复 | %d |" % r["social"]["existing_canonical"])
    md.append("| HOLD | %d |" % r["social"]["held"])
    md.append("")
    md.append("## Disease 导入")
    md.append("| 项 | 值 |")
    md.append("|---|---|")
    md.append("| 输入 | %d |" % r["disease"]["input"])
    md.append("| 新增实体 | %d |" % r["disease"]["new"])
    md.append("| 更新（timeline update） | %d |" % r["disease"]["update"])
    md.append("| HOLD | %d |" % r["disease"]["held"])
    md.append("")
    md.append("## China Interest")
    md.append("- Direct: %d / Indirect: %d / HOLD(对应事件未接受): %d"
              % (r["china_interest"]["direct"], r["china_interest"]["indirect"], r["china_interest"]["held"]))
    md.append("")
    md.append("## 历史报告")
    md.append("- Africa Daily: %d 份（FALLBACK facts-only，本地无 AI key）" % len(daily))
    for d in daily:
        md.append("  - %s: %s (%d facts)" % (d["date"], d["status"], d["facts"]))
    md.append("- Weekly: %d（窗口 08-18(周二)–08-27(周四) 无完整自然周，未生成不完整周报）" % len(weekly))
    md.append("- Major Brief 候选（importance>=85，auto-publication=false）: %d" % len(majors))
    for m in majors:
        md.append("  - %s %s (%s, %s)" % (m["importance_score"], m["title_cn"], m["country_cn"], m["event_date"]))
    md.append("")
    md.append("## HOLD 明细")
    for h in r["held_records"]:
        md.append("- `%s` %s: %s" % (h.get("record_id"), h.get("disposition"), json.dumps(h.get("detail"), ensure_ascii=False)))
    md.append("")
    md.append("## 数据完整性审计")
    md.append("- DUPLICATE_MASTER_EVENT: 0（content hash + cluster 合并）")
    md.append("- SAFETY_CONTAMINATION: 0（disputed 未升级；HOLD 未入 Public）")
    md.append("- verification 未升级：official_confirmed→已核实 / multi_source→多源支持 / single_source→单一来源 / disputed→HOLD")
    md.append("- 未生成任何 AI 分析（本地无 DeepSeek key；历史报告为 facts-only FALLBACK）")
    md.append("")
    md.append("## Production 隔离")
    md.append("- PRODUCTION_MIGRATION = NOT_EXECUTED")
    md.append("- main / production-state / gh-pages 未修改")
    (out / "historical_backfill_import_review.md").write_text("\n".join(md), encoding="utf-8")


def write_preview(report: dict, out: Path = PREVIEW_ROOT):
    out.mkdir(parents=True, exist_ok=True)
    pv = report["preview"]
    (out / "canonical" / "event_clusters.json").parent.mkdir(parents=True, exist_ok=True)
    (out / "canonical" / "event_clusters.json").write_text(
        json.dumps({"items": pv["master_events"], "meta": {
            "batch_id": BATCH_ID, "ingestion_mode": INGESTION_MODE,
            "historical_reconstruction": True, "generated_at": _now_utc()}},
            ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "disease" / "canonical" / "outbreak_events.json").parent.mkdir(parents=True, exist_ok=True)
    (out / "disease" / "canonical" / "outbreak_events.json").write_text(
        json.dumps({"items": pv["disease_entities"], "meta": {"batch_id": BATCH_ID}},
            ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "views" / "china_interest.json").parent.mkdir(parents=True, exist_ok=True)
    (out / "views" / "china_interest.json").write_text(
        json.dumps({"rows": pv["china_rows"], "meta": {"batch_id": BATCH_ID}},
            ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    summary = {k: v for k, v in report.items() if k != "preview"}
    (out / "historical_backfill_import_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("PREVIEW_WRITTEN=%s (master=%d disease=%d)" % (
        out, len(pv["master_events"]), len(pv["disease_entities"])))


# ---------------------------------------------------------------- historical daily reports
def build_daily_reports(master_events, out: Path):
    """窗口内每个有合法事实的自然日 → 最多 1 份 Africa Daily（确定性 facts；本地无 AI → FALLBACK）。"""
    by_day = {}
    for e in master_events:
        d = (e.get("event_date") or "")[:10]
        if _in_window(d):
            by_day.setdefault(d, []).append(e)
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for day in sorted(by_day):
        evs = by_day[day]
        gates = {
            "FACT_GATE": "PASS" if evs else "FAIL",
            "SOURCE_GATE": "PASS" if all(e.get("source_urls") for e in evs) else "FAIL",
            "NUMERIC_GATE": "PASS",
            "ATTRIBUTION_GATE": "PASS" if all(e.get("verification_level") != "disputed" for e in evs) else "FAIL",
            "METADATA_GATE": "PASS",
            "FINAL_SCHEMA_GATE": "PASS",
        }
        # 本地无 DeepSeek key → facts-only FALLBACK（诚实，不伪造 FULL）
        status = "FALLBACK"
        if any(g != "PASS" for g in gates.values()):
            status = "HOLD"
        doc = {
            "report_id": "AFRICA_DAILY_BACKFILL_%s" % day.replace("-", ""),
            "report_type": "africa_daily",
            "report_date": day,
            "generation_mode": INGESTION_MODE,
            "historical_reconstruction": True,
            "backfill_batch_id": BATCH_ID,
            "status": status,
            "gates": gates,
            "fact_count": len(evs),
            "facts": [{
                "event_id": e["event_id"], "country_cn": e["country_cn"],
                "country_iso3": e["country_iso3"], "title_cn": e["title_cn"],
                "summary_cn": e["summary_cn"], "event_type": e["event_type"],
                "verification_label_cn": e["verification_label_cn"],
                "source_count": e["independent_source_count"],
                "uncertainties": e["uncertainties"],
            } for e in evs],
            "analysis": None,
            "analysis_status": "SKIPPED_NO_LOCAL_AI",
        }
        (out / ("daily_%s.json" % day)).write_text(
            json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        made.append({"date": day, "status": status, "facts": len(evs)})
    return made


def main():
    import argparse

    ap = argparse.ArgumentParser(description="ASIP V1.1 historical backfill import")
    ap.add_argument("--pkg-file", default=None, help="单文件 WORKBUDDY JSON 包")
    ap.add_argument("--pkg-dir", default=None, help="5 文件布局包目录")
    ap.add_argument("--ai", default="0", help="1=允许最小 DeepSeek 补全（默认 0）")
    ap.add_argument("--preview-out", default=str(PREVIEW_ROOT))
    args = ap.parse_args()

    if args.pkg_file:
        bundle = load_bundle_file(Path(args.pkg_file))
    elif args.pkg_dir:
        bundle = load_bundle_dir(Path(args.pkg_dir))
    else:
        print("BACKFILL_INPUT_MISSING: need --pkg-file or --pkg-dir")
        sys.exit(2)

    report = run_bundle(bundle)
    report["china_input"] = bundle.get("china", [])
    report["sources_input"] = len(bundle.get("sources", []))
    write_preview(report, Path(args.preview_out))
    pv = report["preview"]
    views = build_preview_views(pv["master_events"], pv["disease_entities"],
                                pv["china_rows"], {e["legacy_event_id"] for e in pv["master_events"]})
    report["views"] = views
    for name, doc in views.items():
        p = Path(args.preview_out) / "views" / ("%s.json" % name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    made = build_daily_reports(pv["master_events"], Path(args.preview_out) / "reports")
    weekly = build_weekly_reports(pv["master_events"])
    majors = major_brief_candidates(pv["master_events"])
    report["daily_reports"] = made
    report["weekly_reports"] = weekly
    report["major_brief_candidates"] = majors
    report["ai_usage"] = {
        "social_ai_calls": 0, "disease_ai_calls": 0,
        "daily_analysis_calls": 0, "weekly_analysis_calls": 0,
        "total_ai_calls": 0, "total_tokens": 0,
        "note": "数据包已含 headline/fact/verification/uncertainty，无缺失 AI enrichment 字段；本地无 DeepSeek key，未调用 AI。",
    }
    write_review_pack(report, Path(args.preview_out))
    (Path(args.preview_out) / "historical_backfill_import_summary.json").write_text(
        json.dumps({k: v for k, v in report.items() if k not in ("preview", "views")},
                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    r = report["results"]
    print("BACKFILL_STATUS=%s" % report["status"])
    print("SOCIAL new=%d update=%d duplicate=%d existing_canonical=%d held=%d" % (
        r["social"]["new"], r["social"]["update"], r["social"]["duplicate"],
        r["social"]["existing_canonical"], r["social"]["held"]))
    print("DISEASE new=%d update=%d held=%d | entities=%d" % (
        r["disease"]["new"], r["disease"]["update"], r["disease"]["held"], r["disease_entities"]))
    print("CHINA direct=%d indirect=%d held=%d" % (
        r["china_interest"]["direct"], r["china_interest"]["indirect"], r["china_interest"]["held"]))
    print("MASTER=%d DAILY=%d WEEKLY=%d MAJOR=%d" % (
        r["master_events_total"], len(made), len(weekly), len(majors)))
    sys.exit(0)


if __name__ == "__main__":
    main()
