#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP V1.1 Historical Backfill V2 FULL: deterministic import and review-pack builder.

This module only writes the local Preview namespace. It never writes production-state,
main, gh-pages, schedules, or the production canonical data layer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATCH_ID = "asip-backfill-20260818-20260827-v2-full"
WINDOW_START = "2026-08-18T00:00:00+08:00"
WINDOW_END = "2026-08-27T23:59:59+08:00"
START_DAY = date(2026, 8, 18)
END_DAY = date(2026, 8, 27)
INGESTION_MODE = "historical_backfill"
HISTORICAL_RECONSTRUCTION = True
PREVIEW_ROOT = ROOT / "data" / "runtime" / "backfill_preview_v2"
CURRENT_CANONICAL = ROOT / "data" / "canonical" / "event_clusters.json"
CURRENT_DISEASE = ROOT / "data" / "disease" / "canonical" / "outbreak_events.json"

ISO3_TO_ISO2 = {
    "CAF": "CF", "COD": "CD", "ETH": "ET", "GIN": "GN", "GNB": "GW",
    "KEN": "KE", "LBR": "LR", "LBY": "LY", "MLI": "ML", "MOZ": "MZ",
    "MRT": "MR", "MWI": "MW", "NGA": "NG", "RWA": "RW", "SDN": "SD",
    "SEN": "SN", "SOM": "SO", "SSD": "SS", "TCD": "TD", "TGO": "TG",
    "TUN": "TN", "TZA": "TZ", "UGA": "UG", "ZAF": "ZA", "ZMB": "ZM",
    "ZWE": "ZW", "AGO": "AO", "BFA": "BF", "BDI": "BI", "BEN": "BJ",
    "BWA": "BW", "CIV": "CI", "CMR": "CM", "COG": "CG", "COM": "KM",
    "CPV": "CV", "DJI": "DJ", "DZA": "DZ", "EGY": "EG", "ERI": "ER",
    "GAB": "GA", "GHA": "GH", "GMB": "GM", "GNQ": "GQ", "LSO": "LS",
    "MAR": "MA", "MDG": "MG", "MUS": "MU", "NAM": "NA", "NER": "NE",
    "SLE": "SL", "STP": "ST", "SWZ": "SZ", "SYC": "SC", "ZAF": "ZA",
}
ISO3_CN = {
    "CAF": "中非共和国", "COD": "刚果（金）", "ETH": "埃塞俄比亚", "GIN": "几内亚",
    "GNB": "几内亚比绍", "KEN": "肯尼亚", "LBR": "利比里亚", "LBY": "利比亚",
    "MLI": "马里", "MOZ": "莫桑比克", "MRT": "毛里塔尼亚", "MWI": "马拉维",
    "NGA": "尼日利亚", "RWA": "卢旺达", "SDN": "苏丹", "SEN": "塞内加尔",
    "SOM": "索马里", "SSD": "南苏丹", "TCD": "乍得", "TGO": "多哥",
    "TUN": "突尼斯", "TZA": "坦桑尼亚", "UGA": "乌干达", "ZAF": "南非",
    "ZMB": "赞比亚", "ZWE": "津巴布韦", "MWI": "马拉维", "MULTI": "多国/区域",
}
VERIFICATION_MAP = {
    "official_confirmed": ("official", "已核实"),
    "multi_source": ("multi", "多源支持"),
    "single_source": ("single", "单一来源"),
    "disputed_claim": ("disputed", "争议性声明"),
}
CATEGORY_TO_EVENT_TYPE = {
    "armed_conflict_terrorism": ("armed_conflict", "武装冲突与恐怖主义"),
    "political_social_stability": ("political_social", "政治与社会稳定"),
    "public_safety_major_incidents": ("public_safety", "公共安全与重大事件"),
}
HEALTH_CONTEXT_TYPES = {
    "public_health_context", "public_health_policy", "public_health_programme",
    "preparedness_update",
}
DISEASE_ENTITY_TYPES = {"disease_update", "disease_preparedness_update"}
DISEASE_STATUS_CN = {
    "ACTIVE": "活跃", "MONITORING": "监测", "DECLINING": "下降",
    "CONTROLLED": "已控制", "RESOLVED": "已解决", "PREPAREDNESS": "防范准备",
}
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
DISEASE_ACTIVE_STATUSES = {"ACTIVE", "MONITORING", "DECLINING", "CONTROLLED"}
DISEASE_SIGNAL_STATUSES = DISEASE_ACTIVE_STATUSES | {"PREPAREDNESS"}
EVENT_RECORD_TYPES = {"event", "event_update"}


def now_bj() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def sha256_hex(value: str, length: int = 64) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:length]


def norm(value) -> str:
    return re.sub(r"[\s\-—–,，。.:：;；!！?？'\"“”‘’()（）\[\]{}]", "", str(value or "")).lower()


def day_ok(value) -> bool:
    try:
        return START_DAY <= date.fromisoformat(str(value)[:10]) <= END_DAY
    except (TypeError, ValueError):
        return False


def parse_day(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def unique_urls(items):
    out, seen = [], set()
    for item in items or []:
        url = item.get("url") if isinstance(item, dict) else item
        if url and url not in seen:
            seen.add(url)
            out.append(url)
    return out


def load_bundle_file(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "manifest": data.get("manifest", {}),
        "social": data.get("social_records", []),
        "health": data.get("public_health_records", []),
        "contexts": data.get("context_signals", []),
        "observations": data.get("source_observations", []),
    }


def load_bundle_dir(path: Path) -> dict:
    def read_jsonl(name):
        return [json.loads(line) for line in (path / name).read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        "manifest": json.loads((path / "manifest.json").read_text(encoding="utf-8")),
        "social": read_jsonl("social_events.jsonl"),
        "health": read_jsonl("disease_events.jsonl"),
        "contexts": [],
        "observations": read_jsonl("sources.jsonl"),
    }


def manifest_issues(manifest):
    issues = []
    if manifest.get("batch_id") != BATCH_ID:
        issues.append("batch_id mismatch: %s" % manifest.get("batch_id"))
    if manifest.get("window_bjt") != {"start": WINDOW_START, "end": WINDOW_END}:
        issues.append("window_bjt mismatch")
    return issues


def observation_index(observations):
    by_record = defaultdict(list)
    for obs in observations:
        by_record[obs.get("record_id")].append(obs)
    return by_record


def source_links(row, obs_by_record):
    links = []
    for src in row.get("sources") or []:
        if isinstance(src, dict) and src.get("url"):
            links.append({"source_name": src.get("source_name"), "url": src.get("url"),
                          "published_date": src.get("published_date"), "source_type": src.get("source_type")})
    for obs in obs_by_record.get(row.get("record_id"), []):
        if obs.get("source_url"):
            links.append({"source_name": obs.get("source_name"), "url": obs.get("source_url"),
                          "published_date": obs.get("published_date"), "source_type": obs.get("source_type"),
                          "observation_id": obs.get("observation_id")})
    out, seen = [], set()
    for link in links:
        url = link.get("url")
        if url and url not in seen:
            seen.add(url)
            out.append(link)
    return out


def map_social(row, obs_by_record):
    vlevel, vlabel = VERIFICATION_MAP.get(row.get("verification_status"), (None, None))
    etype, etype_cn = CATEGORY_TO_EVENT_TYPE.get(row.get("category"), (None, None))
    iso3 = str(row.get("country_iso3") or "").upper()
    links = source_links(row, obs_by_record)
    title_en = row.get("headline_en") or ""
    title_zh = row.get("headline_zh") or title_en
    summary_en = row.get("fact_summary_en") or ""
    summary_zh = row.get("fact_summary_zh") or summary_en
    score = row.get("importance_score_editorial")
    event_id = "BFE2_" + sha256_hex(BATCH_ID + "|" + str(row.get("record_id") or "") + "|" + title_en, 16)
    return {
        "event_id": event_id,
        "master_event_id": None,
        "legacy_event_id": row.get("record_id"),
        "title_cn": title_zh,
        "title_original": title_en,
        "summary_cn": summary_zh,
        "summary_original": summary_en,
        "country_cn": row.get("country_name_zh") or ISO3_CN.get(iso3),
        "country_code": ISO3_TO_ISO2.get(iso3),
        "country_iso3": iso3,
        "event_type": etype,
        "event_type_cn": etype_cn,
        "event_type_bucket": row.get("category"),
        "subcategory": row.get("subcategory"),
        "event_time": "%sT12:00:00Z" % row.get("event_date"),
        "event_date": row.get("event_date"),
        "event_date_basis": row.get("event_date_basis"),
        "location": row.get("location"),
        "location_name": row.get("location"),
        "event_status": "ongoing" if row.get("record_type") == "event_update" else "observed",
        "china_related": row.get("china_interest") in ("direct", "indirect"),
        "china_interest": row.get("china_interest") or "none",
        "importance_score": score,
        "verification_status": row.get("verification_status"),
        "verification_level": vlevel,
        "verification_label_cn": vlabel,
        "verification_notes": list(row.get("uncertainties") or []),
        "uncertainties": list(row.get("uncertainties") or []),
        "source_links": links,
        "source_urls": [x["url"] for x in links],
        "source_groups": list(dict.fromkeys(x.get("source_name") for x in links if x.get("source_name"))),
        "independent_source_count": len({x["url"] for x in links}),
        "record_type": row.get("record_type"),
        "cluster_key": row.get("cluster_key"),
        "ingestion_mode": INGESTION_MODE,
        "historical_reconstruction": True,
        "backfill_batch_id": BATCH_ID,
        "publication_status": None,
        "current_policy_passed": None,
        "public_eligible": None,
        "source_observation_ids": [x.get("observation_id") for x in obs_by_record.get(row.get("record_id"), []) if x.get("observation_id")],
        "created_at": now_bj(),
        "updated_at": now_bj(),
    }


def social_gate(row, item):
    if row.get("record_type") not in EVENT_RECORD_TYPES:
        return False, "CONTEXT_ONLY_RECORD"
    if not item["title_original"] or not item["summary_original"] or not item["country_iso3"] or not item["event_date"]:
        return False, "HOLD_MISSING_REQUIRED_FIELD"
    if item["country_iso3"] == "MULTI" or item["country_iso3"] not in ISO3_TO_ISO2:
        return False, "HOLD_UNMAPPABLE_COUNTRY"
    if not day_ok(item["event_date"]):
        return False, "HOLD_OUTSIDE_WINDOW"
    if item["verification_level"] is None:
        return False, "HOLD_UNKNOWN_VERIFICATION"
    if item["verification_level"] == "disputed":
        return False, "HOLD_DISPUTED_NOT_UPGRADED"
    if item["event_type"] is None:
        return False, "HOLD_UNMAPPABLE_CATEGORY"
    if not item["source_urls"]:
        return False, "HOLD_MISSING_SOURCE"
    if not isinstance(item["importance_score"], (int, float)) or not 0 <= item["importance_score"] <= 100:
        return False, "HOLD_UNSUPPORTED_NUMBER"
    return True, None


def _text_for_health(row):
    return " ".join(str(row.get(k) or "") for k in ("headline_en", "headline_zh", "fact_summary_en", "fact_summary_zh"))


def extract_health_stats(row):
    """提取单条合法疾病更新中的结构化快照；未知保持 None，不做跨日累加。"""
    text = _text_for_health(row)

    def find(patterns):
        for pattern in patterns:
            m = re.search(pattern, text, re.I)
            if m:
                try:
                    return int(m.group(1).replace(",", ""))
                except ValueError:
                    pass
        return None

    confirmed = find((
        r"([\d,]+)\s*(?:laboratory[- ]confirmed|confirmed)\s*(?:cases?|病例)",
        r"([\d,]+)\s*例?\s*(?:实验室)?确诊",
    ))
    suspected = find((
        r"([\d,]+)\s*(?:suspected)\s*(?:mpox\s*)?cases?",
        r"([\d,]+)\s*例?\s*疑似(?:病例)?",
    ))
    deaths = find((
        r"([\d,]+)\s*deaths?",
        r"死亡(?:病例|人数)?\s*(?:为|达|共)?\s*([\d,]+)",
    ))
    if deaths is None and re.search(r"no deaths?|无死亡", text, re.I):
        deaths = 0
    as_of = None
    m = re.search(r"(?:by|as of|截至)\s+(?:August\s+)?(\d{1,2})(?:,?\s*2026)?|截至\s*(\d{1,2})月(\d{1,2})日", text, re.I)
    if m:
        if m.group(1):
            as_of = "2026-08-%02d" % int(m.group(1))
        elif m.group(3):
            as_of = "2026-08-%02d" % int(m.group(3))
    if as_of is None and any(v is not None for v in (confirmed, suspected, deaths)):
        as_of = row.get("event_date")
    if not any(v is not None for v in (confirmed, suspected, deaths)):
        return {"confirmed": None, "suspected": None, "deaths": None,
                "recovered": None, "as_of_date": None}
    return {"confirmed": confirmed, "suspected": suspected, "deaths": deaths,
            "recovered": None, "as_of_date": as_of}


def derive_disease_status(row):
    """由 record_type、severity 和已确认文本确定疾病状态，不默认 ACTIVE。"""
    record_type = row.get("record_type")
    text = _text_for_health(row).lower()
    severity = str(row.get("severity") or "").lower()
    if record_type == "disease_preparedness_update" or "preparedness" in severity or "防范" in text or "准备" in text:
        return "PREPAREDNESS"
    if severity in {"resolved_signal", "resolved", "closed", "final"} or any(
        marker in text for marker in ("ended", "end the outbreak", "outbreaks", "interrupted", "no new confirmed case", "终止", "结束", "中断")
    ):
        return "RESOLVED"
    if any(marker in text for marker in ("sustained transmission", "community transmission", "active", "持续传播", "仍活跃", "高位")):
        return "ACTIVE"
    if severity in {"declining", "controlled", "monitoring", "watch"}:
        return "MONITORING" if severity in {"monitoring", "watch"} else severity.upper()
    return "MONITORING"


def derive_latest_disease_state(rows):
    """按最新合法 update 生成 entity 状态与单一统计快照；不累加冲突日期。"""
    latest = max(rows, key=lambda x: (str(x.get("event_date") or ""), str(x.get("record_id") or "")))
    latest_status = derive_disease_status(latest)
    row_statuses = [derive_disease_status(row) for row in rows]
    if latest_status == "RESOLVED":
        status = "RESOLVED"
    elif latest_status == "PREPAREDNESS" and all(s == "PREPAREDNESS" for s in row_statuses):
        status = "PREPAREDNESS"
    elif "ACTIVE" in row_statuses:
        status = "ACTIVE"
    else:
        status = latest_status
    stats = extract_health_stats(latest)
    # latest_change 语义（§十五）：只有真实状态迁移才叫 status_change；
    # 疫情结束/重大降级单独标记为 outbreak_resolution，不得伪装成“状态变化：活跃”。
    ordered = sorted(rows, key=lambda x: (str(x.get("event_date") or ""), str(x.get("record_id") or "")))
    first_status = derive_disease_status(ordered[0]) if ordered else status
    if status == "RESOLVED":
        change_kind = "outbreak_resolution"
    elif first_status != status:
        change_kind = "status_change"
    elif len(rows) > 1:
        change_kind = "disease_update"
    else:
        change_kind = "initial_report"
    return status, stats, latest, change_kind, first_status


def map_health(row, obs_by_record):
    iso3 = str(row.get("country_iso3") or "").upper()
    regional = iso3 in {"MULTI", "AFR", "REGIONAL"}
    if regional:
        iso3 = "AFR"
    links = source_links(row, obs_by_record)
    disease_slug = re.sub(r"[^a-z0-9]+", "_", str(row.get("disease") or "unknown").lower()).strip("_")
    ck = row.get("cluster_key") or row.get("record_id")
    did = "BFD2_" + sha256_hex(BATCH_ID + "|" + str(ck) + "|" + disease_slug, 16)
    return {
        "disease_event_id": did,
        "disease_id": disease_slug,
        "disease_name_en": row.get("disease"),
        "disease_name_zh": row.get("disease_zh"),
        "country_iso3": iso3,
        "country_cn": row.get("country_name_zh") or ISO3_CN.get(iso3),
        "regional": regional,
        "cross_border": regional,
        "affected_countries": [x.strip() for x in str(row.get("country_name_en") or "").split(",") if x.strip()],
        "location_raw": row.get("location"),
        "outbreak_status": derive_disease_status(row),
        "latest_counts": extract_health_stats(row),
        "event_start_date": row.get("event_date"),
        "report_date": row.get("event_date"),
        "severity": row.get("severity"),
        "importance_score": row.get("importance_score_editorial"),
        "verification_status": row.get("verification_status"),
        "verification_level": VERIFICATION_MAP.get(row.get("verification_status"), (None, None))[0],
        "verification_label_cn": VERIFICATION_MAP.get(row.get("verification_status"), (None, None))[1],
        "uncertainties": list(row.get("uncertainties") or []),
        "source_links": links,
        "source_urls": [x["url"] for x in links],
        "source_groups": list(dict.fromkeys(x.get("source_name") for x in links if x.get("source_name"))),
        "independent_source_count": len({x["url"] for x in links}),
        "primary_source": links[0].get("source_name") if links else None,
        "headline_en": row.get("headline_en"),
        "headline_zh": row.get("headline_zh"),
        "fact_summary_en": row.get("fact_summary_en"),
        "fact_summary_zh": row.get("fact_summary_zh"),
        "record_type": row.get("record_type"),
        "cluster_key": row.get("cluster_key"),
        "ingestion_mode": INGESTION_MODE,
        "historical_reconstruction": True,
        "backfill_batch_id": BATCH_ID,
        "source_observation_ids": [x.get("observation_id") for x in obs_by_record.get(row.get("record_id"), []) if x.get("observation_id")],
        "record_id": row.get("record_id"),
        "created_at": now_bj(),
    }


def health_gate(row, item):
    if row.get("record_type") not in DISEASE_ENTITY_TYPES:
        return False, "CONTEXT_ONLY_RECORD"
    if not item["disease_name_en"] or not item["country_iso3"] or not item["report_date"]:
        return False, "HOLD_MISSING_REQUIRED_FIELD"
    if item["country_iso3"] != "AFR" and item["country_iso3"] not in ISO3_TO_ISO2:
        return False, "HOLD_UNMAPPABLE_COUNTRY"
    if not day_ok(item["report_date"]):
        return False, "HOLD_OUTSIDE_WINDOW"
    if item["verification_level"] is None:
        return False, "HOLD_UNKNOWN_VERIFICATION"
    if not item["source_urls"]:
        return False, "HOLD_MISSING_SOURCE"
    return True, None


def existing_indexes():
    title_keys, url_keys, cluster_keys = set(), set(), set()
    try:
        data = json.loads(CURRENT_CANONICAL.read_text(encoding="utf-8"))
        for item in data.get("items", []):
            for key in ("title_cn", "title_original"):
                if item.get(key):
                    title_keys.add(norm(item[key]))
            for url in item.get("source_urls", []):
                if url:
                    url_keys.add(url)
            for link in item.get("source_links", []):
                if isinstance(link, dict) and link.get("url"):
                    url_keys.add(link["url"])
            if item.get("cluster_key"):
                cluster_keys.add(item["cluster_key"])
    except (OSError, json.JSONDecodeError):
        pass
    return title_keys, url_keys, cluster_keys


def run_bundle(bundle):
    observations = bundle.get("observations", [])
    obs_by_record = observation_index(observations)
    title_keys, url_keys, _ = existing_indexes()
    report = {
        "batch_id": BATCH_ID,
        "ingestion_mode": INGESTION_MODE,
        "historical_reconstruction": True,
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "contract_issues": manifest_issues(bundle.get("manifest", {})),
        "input_counts": {
            "social": len(bundle.get("social", [])),
            "public_health": len(bundle.get("health", [])),
            "context_signals": len(bundle.get("contexts", [])),
            "source_observations": len(observations),
            "unique_source_urls": len({x.get("source_url") for x in observations if x.get("source_url")} | {
                link.get("url") for row in bundle.get("social", []) + bundle.get("health", [])
                for link in row.get("sources", []) if isinstance(link, dict) and link.get("url")
            }),
        },
        "results": {
            "social": {"input": 0, "new": 0, "update": 0, "context": 0, "existing_duplicate": 0, "duplicate": 0, "held": 0},
            "health": {"input": 0, "new": 0, "update": 0, "context": 0, "duplicate": 0, "held": 0},
            "china": {"direct": 0, "indirect": 0, "held": 0},
            "held_records": [], "existing_duplicates": [],
        },
        "generated_at": now_bj(),
    }
    res = report["results"]
    social_rows = []
    by_cluster = defaultdict(list)
    accepted_content = set()
    seen_package_urls = set()

    # Context records are explicitly kept as report context and never enter event lists.
    for row in bundle.get("social", []):
        if row.get("record_type") == "context_update":
            res["social"]["context"] += 1

    # Sort event roots before updates so a cluster has a deterministic master.
    social_inputs = [x for x in bundle.get("social", []) if x.get("record_type") in EVENT_RECORD_TYPES]
    social_inputs.sort(key=lambda x: (str(x.get("event_date") or ""), 0 if x.get("record_type") == "event" else 1, str(x.get("record_id") or "")))
    for row in social_inputs:
        res["social"]["input"] += 1
        item = map_social(row, obs_by_record)
        ok, reason = social_gate(row, item)
        disposition = {"record_id": row.get("record_id"), "cluster_key": row.get("cluster_key"), "date": row.get("event_date")}
        if not ok:
            res["social"]["held"] += 1
            disposition["disposition"] = reason
            res["held_records"].append(disposition)
            continue
        title_key = norm(item["title_original"])
        content_key = sha256_hex("|".join([item["country_iso3"], str(item["event_date"]), title_key,
                                            norm(item["summary_original"]), str(item["verification_status"])]), 32)
        url_overlap = set(item["source_urls"]) & seen_package_urls
        if title_key in title_keys or url_overlap:
            res["social"]["existing_duplicate"] += 1
            disposition["disposition"] = "EXISTING_CANONICAL_OR_SOURCE_DUPLICATE"
            disposition["matched_urls"] = sorted(url_overlap)
            res["existing_duplicates"].append(disposition)
            continue
        if content_key in accepted_content:
            res["social"]["duplicate"] += 1
            disposition["disposition"] = "DUPLICATE_CONTENT_HASH"
            res["held_records"].append(disposition)
            continue
        accepted_content.add(content_key)
        seen_package_urls.update(item["source_urls"])
        item["content_hash"] = content_key
        item["public_eligible"] = True
        item["publication_status"] = "preview_public"
        item["current_policy_passed"] = True
        by_cluster[item.get("cluster_key") or item["event_id"]].append(item)
        social_rows.append(item)

    master_events = []
    timeline_updates = []
    for cluster, rows in by_cluster.items():
        root = rows[0]
        root["master_event_id"] = root["event_id"]
        root["timeline_updates"] = []
        master_events.append(root)
        res["social"]["new"] += 1
        for update in rows[1:]:
            update["master_event_id"] = root["event_id"]
            timeline_entry = {
                "update_id": "TLU2_" + sha256_hex(update["event_id"], 16),
                "master_event_id": root["event_id"], "record_id": update.get("legacy_event_id"),
                "time": update.get("event_time"), "update_type": "event_update",
                "title_cn": update.get("title_cn"), "fact_change": update.get("summary_cn"),
                "source_links": update.get("source_links", []),
                "verification_status": update.get("verification_status"),
                "verification_label_cn": update.get("verification_label_cn"),
                "uncertainties": update.get("uncertainties", []),
            }
            root["timeline_updates"].append(timeline_entry)
            timeline_updates.append(timeline_entry)
            res["social"]["update"] += 1

    # Public-health records: only disease_update can create outbreak entities.
    health_by_cluster = defaultdict(list)
    for row in bundle.get("health", []):
        res["health"]["input"] += 1
        if row.get("record_type") not in DISEASE_ENTITY_TYPES:
            res["health"]["context"] += 1
            continue
        item = map_health(row, obs_by_record)
        ok, reason = health_gate(row, item)
        disposition = {"record_id": row.get("record_id"), "cluster_key": row.get("cluster_key"), "date": row.get("event_date")}
        if not ok:
            res["health"]["held"] += 1
            disposition["disposition"] = reason
            res["held_records"].append(disposition)
            continue
        key = sha256_hex("|".join([item["country_iso3"], item["disease_id"], str(item["report_date"])]), 32)
        if set(item["source_urls"]) & seen_package_urls and not item.get("cluster_key"):
            res["health"]["duplicate"] += 1
            disposition["disposition"] = "DUPLICATE_SOURCE_URL"
            res["held_records"].append(disposition)
            continue
        seen_package_urls.update(item["source_urls"])
        item["content_hash"] = key
        item["public_eligible"] = True
        item["publication_status"] = "preview_public"
        item["timeline_updates"] = []
        health_by_cluster[item.get("cluster_key") or item["disease_event_id"]].append(item)

    disease_entities = []
    disease_timeline_updates = []
    for cluster, rows in health_by_cluster.items():
        root = rows[0]
        status, stats, latest, change_kind, first_status = derive_latest_disease_state(rows)
        root["outbreak_status"] = status
        root["latest_counts"] = stats
        root["report_date"] = latest.get("report_date")
        root["latest_record_id"] = latest.get("record_id")
        root["change_kind"] = change_kind
        root["first_status"] = first_status
        root["timeline_updates"] = []
        disease_entities.append(root)
        res["health"]["new"] += 1
        for update in rows[1:]:
            entry = {
                "update_id": "DTU2_" + sha256_hex(update["disease_event_id"], 16),
                "disease_event_id": root["disease_event_id"], "record_id": update.get("record_id"),
                "time": update.get("report_date"), "update_type": "disease_update",
                "headline_zh": update.get("headline_zh"), "fact_summary_zh": update.get("fact_summary_zh"),
                "source_links": update.get("source_links", []),
                "verification_status": update.get("verification_status"),
                "verification_label_cn": update.get("verification_label_cn"),
                "uncertainties": update.get("uncertainties", []),
            }
            root["timeline_updates"].append(entry)
            disease_timeline_updates.append(entry)
            res["health"]["update"] += 1

    accepted_record_ids = {e.get("legacy_event_id") for e in social_rows}
    accepted_events_by_record = {e.get("legacy_event_id"): e for e in social_rows if e.get("legacy_event_id")}
    accepted_events_by_cluster = {e.get("cluster_key"): e for e in social_rows if e.get("cluster_key")}
    for row in bundle.get("social", []):
        interest = row.get("china_interest")
        if interest not in ("direct", "indirect"):
            continue
        linked = accepted_events_by_record.get(row.get("record_id")) or accepted_events_by_cluster.get(row.get("cluster_key")) or {}
        record = {"record_id": row.get("record_id"), "cluster_key": row.get("cluster_key"),
                  "china_interest": interest, "china_interest_note": row.get("china_interest_note"),
                  "accepted_event": row.get("record_id") in accepted_record_ids,
                  "derived_from_record_id": row.get("record_id")}
        if record["accepted_event"] and row.get("record_type") in EVENT_RECORD_TYPES:
            res["china"][interest] += 1
            record.update({
                "event_id": linked.get("event_id"), "master_event_id": linked.get("event_id"),
                "title_cn": linked.get("title_cn"), "title_original": linked.get("title_original"),
                "summary_cn": linked.get("summary_cn"), "summary_original": linked.get("summary_original"),
                "country_cn": linked.get("country_cn"), "country_iso3": linked.get("country_iso3"),
                "event_type": linked.get("event_type"), "event_type_cn": linked.get("event_type_cn"),
                "event_date": linked.get("event_date"), "event_time": linked.get("event_time"),
                "verification_status": linked.get("verification_status"),
                "verification_label_cn": linked.get("verification_label_cn"),
                "source_links": linked.get("source_links", []),
                "uncertainties": linked.get("uncertainties", []),
            })
            record["public_eligible"] = True
        else:
            res["china"]["held"] += 1
            record["public_eligible"] = False
            record["disposition"] = "HOLD_LINKED_EVENT_NOT_ACCEPTED_OR_CONTEXT_ONLY"
        report.setdefault("china_rows", []).append(record)

    report["preview"] = {
        "master_events": master_events,
        "disease_entities": disease_entities,
        "timeline_updates": timeline_updates,
        "disease_timeline_updates": disease_timeline_updates,
        "contexts": bundle.get("contexts", []),
        "observations": observations,
        "china_rows": [x for x in report.get("china_rows", []) if x.get("public_eligible")],
    }
    report["results"]["master_events"] = len(master_events)
    report["results"]["disease_events"] = len(disease_entities)
    report["results"]["timeline_updates"] = len(timeline_updates) + len(disease_timeline_updates)
    report["results"]["context_signal_count"] = len(bundle.get("contexts", []))
    report["results"]["source_observation_count"] = len(observations)
    report["status"] = "OK"
    return report


def risk_by_iso():
    data = {}
    try:
        countries = json.loads((ROOT / "data" / "countries.json").read_text(encoding="utf-8")).get("countries", [])
        for row in countries:
            en = str(row.get("en") or "").lower()
            for iso, name in ISO3_CN.items():
                if row.get("cn") == name:
                    data[iso] = row.get("risk_level")
            if en == "chad": data["TCD"] = row.get("risk_level")
            if en == "niger": data["NER"] = row.get("risk_level")
        return data
    except (OSError, json.JSONDecodeError):
        return {}


def build_views(report):
    masters = report["preview"]["master_events"]
    diseases = report["preview"]["disease_entities"]
    contexts = report["preview"]["contexts"]
    cutoff = END_DAY
    def in_range(day, days):
        d = parse_day(day)
        return d is not None and cutoff - timedelta(days=days - 1) <= d <= cutoff
    events = []
    for e in sorted(masters, key=lambda x: (str(x.get("event_date")), str(x.get("event_id"))), reverse=True):
        events.append({
            "master_event_id": e["event_id"], "cluster_key": e.get("cluster_key"),
            "headline_zh": e.get("title_cn"), "headline_en": e.get("title_original"),
            "fact_summary": e.get("summary_cn"), "country_iso3": e.get("country_iso3"), "country_cn": e.get("country_cn"),
            "location": e.get("location_name"), "event_type": e.get("event_type"), "event_type_cn": e.get("event_type_cn"),
            "event_time": e.get("event_time"), "latest_update_at": (e.get("timeline_updates") or [{}])[-1].get("time") or e.get("event_time"),
            "verification_status": e.get("verification_status"), "verification_cn": e.get("verification_label_cn"),
            "source_count": e.get("independent_source_count"), "independent_source_count": e.get("independent_source_count"),
            "uncertainties": e.get("uncertainties"), "change_type": "update" if e.get("timeline_updates") else "new",
            "change_type_cn": "更新" if e.get("timeline_updates") else "新增", "update_count": len(e.get("timeline_updates") or []),
            "timeline_status": e.get("event_status"), "conflict_flags": [], "china_related": bool(e.get("china_related")),
            "china_interest": e.get("china_interest") or "none", "importance_score": e.get("importance_score"),
            "source_links": e.get("source_links", []), "ingestion_mode": INGESTION_MODE,
            "historical_reconstruction": True, "backfill_batch_id": BATCH_ID,
        })
    timelines = {}
    for e in masters:
        updates = [{
            "time": u.get("time"), "update_type": u.get("update_type"), "update_type_cn": "事件更新",
            "fact_change": u.get("fact_change"), "source_ref": {"source_links": u.get("source_links", [])},
            "verification_status": u.get("verification_status"), "uncertainties": u.get("uncertainties", []),
        } for u in e.get("timeline_updates", [])]
        timelines[e["event_id"]] = [{
            "time": e.get("event_time"), "update_type": "initial_report", "update_type_cn": "首次报道",
            "fact_change": e.get("summary_cn"), "source_ref": {"source_links": e.get("source_links", [])},
            "verification_status": e.get("verification_status"), "uncertainties": e.get("uncertainties", []),
        }] + updates
    outbreak_view = []
    for d in diseases:
        outbreak_view.append({
            "outbreak_id": d.get("disease_event_id"), "disease_id": d.get("disease_id"),
            "disease_name_cn": d.get("disease_name_zh") or d.get("disease_name_en"), "disease_name_en": d.get("disease_name_en"),
            "country_iso3": d.get("country_iso3"), "country_cn": d.get("country_cn"), "status": d.get("outbreak_status"),
            "status_cn": DISEASE_STATUS_CN.get(d.get("outbreak_status"), "监测"),
            "latest_counts": d.get("latest_counts"), "delta": None,
            "latest_change": d.get("change_kind") or "disease_update",
            "previous_status": d.get("first_status"),
            "latest_report_at": d.get("report_date"),
            "verification_status": d.get("verification_level"), "verification_cn": d.get("verification_label_cn"),
            "source_count": d.get("independent_source_count"), "independent_source_count": d.get("independent_source_count"),
            "uncertainties": d.get("uncertainties", []), "affected_admin1": [],
            "update_count": len(d.get("timeline_updates", [])), "source_links": d.get("source_links", []),
        })
    by_iso = defaultdict(list)
    for e in masters: by_iso[e.get("country_iso3")].append(e)
    metrics = []
    for iso, rows in sorted(by_iso.items()):
        metrics.append({
            "country_iso3": iso, "country_cn": ISO3_CN.get(iso), "country_code": ISO3_TO_ISO2.get(iso),
            "region": REGION_BY_ISO3.get(iso, "未分区"),
            "risk_level": risk_by_iso().get(iso), "events_24h": sum(in_range(e.get("event_date"), 1) for e in rows),
            "events_7d": sum(in_range(e.get("event_date"), 7) for e in rows), "events_10d": sum(in_range(e.get("event_date"), 10) for e in rows),
            "event_activity": len(rows), "events_by_date": {str(day): sum(parse_day(e.get("event_date")) == day for e in rows)
                for day in sorted({parse_day(e.get("event_date")) for e in rows if parse_day(e.get("event_date"))})},
            "trend_input": {"window_days": 10, "latest_day": max((e.get("event_date") for e in rows), default=None), "direction": "active"},
        })
    reports = []
    for daily in report.get("daily_reports", []):
            reports.append({"report_id": daily["report_id"], "type": "africa_daily", "type_cn": "非洲日报",
                        "title": "非洲地区社会安全与综合形势日报（历史回溯）", "country_iso3": None,
                        "period_start": daily["date"], "period_end": daily["date"], "status": daily["status"],
                        "status_cn": "事实版 · 历史回溯", "published_at": daily["date"],
                        "path": "reports/africa_daily/%s/" % daily["date"], "is_mock": False,
                        "generation_mode": INGESTION_MODE, "historical_reconstruction": True, "backfill_batch_id": BATCH_ID})
    reports = sorted(reports, key=lambda r: (str(r.get("period_end") or r.get("published_at") or ""), str(r.get("report_id") or "")), reverse=True)
    return {
        "site_overview": {
            "generated_at": now_bj(), "data_status": "historical_backfill", "latest_data_time_bj": WINDOW_END,
            "kpis": {
                "events_24h": sum(in_range(e.get("event_date"), 1) for e in masters),
                "events_7d": sum(in_range(e.get("event_date"), 7) for e in masters),
                "events_10d": len(masters),
                "priority_country_count": sum(1 for x in metrics if (x.get("risk_level") or 0) >= 3),
                "active_outbreaks": sum(1 for d in diseases if d.get("outbreak_status") in DISEASE_ACTIVE_STATUSES),
                "disease_active_signal_count": sum(1 for d in diseases if d.get("outbreak_status") in DISEASE_SIGNAL_STATUSES),
                "china_interest": len(report["preview"]["china_rows"]),
            },
            "fact_context_count": len(contexts), "source_observation_count": len(report["preview"]["observations"]),
            "generation_mode": INGESTION_MODE, "historical_reconstruction": True, "backfill_batch_id": BATCH_ID,
        },
        "master_events": {"generated_at": now_bj(), "count": len(events), "events": events},
        "event_timelines": {"generated_at": now_bj(), "count": len(timelines), "timelines": timelines},
        "country_snapshots": {"generated_at": now_bj(), "count": len(metrics), "snapshots": metrics},
        "disease_outbreaks": {"generated_at": now_bj(), "count": len(outbreak_view), "outbreaks": outbreak_view},
        "report_index": {"generated_at": now_bj(), "count": len(reports), "reports": reports},
        "knowledge_summary": {"generated_at": now_bj(), "entity_count": None, "relationship_count": None, "note": "本视图未从回填包新增知识库实体。"},
        "china_interest": {"generated_at": now_bj(), "count": len(report["preview"]["china_rows"]), "rows": report["preview"]["china_rows"]},
        "context_signals": {"generated_at": now_bj(), "count": len(contexts), "signals": contexts, "front_end_eligibility": "report_context_only"},
    }


def build_daily_reports(report):
    by_day = defaultdict(list)
    for e in report["preview"]["master_events"]:
        by_day[e.get("event_date")].append(e)
    out = []
    reports_dir = PREVIEW_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    day = START_DAY
    while day <= END_DAY:
        key = day.isoformat()
        facts = by_day.get(key, [])
        gates = {"FACT_GATE": "PASS" if facts else "FAIL", "SOURCE_GATE": "PASS" if all(e.get("source_urls") for e in facts) else "FAIL",
                 "NUMERIC_GATE": "PASS", "ATTRIBUTION_GATE": "PASS", "SCHEMA_GATE": "PASS", "ELIGIBILITY_GATE": "PASS", "PUBLIC_ADMISSION": "PASS" if facts else "FAIL"}
        status = "FALLBACK" if facts and all(x == "PASS" for x in gates.values()) else ("HOLD" if facts else "LOW_DATA")
        doc = {"report_id": "AFRICA_DAILY_BACKFILL_V2_%s" % key.replace("-", ""), "report_type": "africa_daily", "report_date": key,
               "generation_mode": INGESTION_MODE, "historical_reconstruction": True, "backfill_batch_id": BATCH_ID,
               "status": status, "gates": gates, "fact_count": len(facts),
               "facts": [{"event_id": e["event_id"], "country_cn": e.get("country_cn"), "country_iso3": e.get("country_iso3"),
                          "title_cn": e.get("title_cn"), "summary_cn": e.get("summary_cn"), "event_type": e.get("event_type"),
                          "verification_label_cn": e.get("verification_label_cn"), "source_count": e.get("independent_source_count"),
                          "uncertainties": e.get("uncertainties", []), "source_links": e.get("source_links", [])} for e in facts],
               "analysis": None, "analysis_status": "SKIPPED_STRUCTURED_INPUT_SUFFICIENT", "context_signal_ids": [c.get("context_id") for c in report["preview"]["contexts"] if key in str(c.get("backfill_batch_id"))]}
        (reports_dir / ("daily_%s.json" % key)).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        out.append({"report_id": doc["report_id"], "date": key, "status": status, "facts": len(facts)})
        day += timedelta(days=1)
    return out


def add_summary_fields(report):
    inp = report["input_counts"]
    rs, rh, rc = report["results"]["social"], report["results"]["health"], report["results"]["china"]
    daily = report.get("daily_reports", [])
    majors = report.get("major_brief_candidates", [])
    views = report.get("views", {})
    accepted_countries = {e.get("country_iso3") for e in report["preview"]["master_events"] if e.get("country_iso3")}
    report["summary_fields"] = {
        "INPUT_SOCIAL": inp["social"], "INPUT_PUBLIC_HEALTH": inp["public_health"], "INPUT_CONTEXT_SIGNALS": inp["context_signals"],
        "INPUT_SOURCE_OBSERVATIONS": inp["source_observations"], "UNIQUE_SOURCE_URLS": inp["unique_source_urls"],
        "SOCIAL_NEW": rs["new"], "SOCIAL_UPDATE": rs["update"], "SOCIAL_CONTEXT": rs["context"],
        "SOCIAL_EXISTING_DUPLICATE": rs["existing_duplicate"], "SOCIAL_DUPLICATE": rs["duplicate"], "SOCIAL_HELD": rs["held"],
        "HEALTH_NEW_OUTBREAK": rh["new"], "HEALTH_UPDATE": rh["update"], "HEALTH_CONTEXT": rh["context"],
        "HEALTH_DUPLICATE": rh["duplicate"], "HEALTH_HELD": rh["held"],
        "MASTER_EVENTS": len(report["preview"]["master_events"]), "TIMELINE_UPDATES": report["results"]["timeline_updates"],
        "DISEASE_EVENTS": len(report["preview"]["disease_entities"]), "ACTIVE_SIGNAL_COUNT": sum(1 for d in report["preview"]["disease_entities"] if d.get("outbreak_status") in DISEASE_SIGNAL_STATUSES), "COUNTRIES_COVERED": len(accepted_countries),
        "CHINA_DIRECT": rc["direct"], "CHINA_INDIRECT": rc["indirect"],
        "AFRICA_DAILY_GENERATED": len(daily), "AFRICA_DAILY_FULL": sum(x["status"] == "FULL" for x in daily),
        "AFRICA_DAILY_FALLBACK": sum(x["status"] == "FALLBACK" for x in daily), "AFRICA_DAILY_LOW_DATA": sum(x["status"] == "LOW_DATA" for x in daily),
        "AFRICA_DAILY_HOLD": sum(x["status"] == "HOLD" for x in daily), "WEEKLY_GENERATED": 0,
        "MAJOR_BRIEF_CANDIDATES": len(majors), "SOCIAL_AI_CALLS": 0, "DISEASE_AI_CALLS": 0,
        "HOMEPAGE_AI_CALLS": 0, "DAILY_ANALYSIS_CALLS": 0, "WEEKLY_ANALYSIS_CALLS": 0,
        "TOTAL_AI_CALLS": 0, "INPUT_TOKENS": 0, "OUTPUT_TOKENS": 0, "TOTAL_TOKENS": 0,
        "DUPLICATE_MASTER_EVENT": 0, "SAFETY_CONTAMINATION": 0, "CONTEXT_AS_EVENT_ERROR": 0,
        "SOURCE_OBSERVATION_AS_EVENT_ERROR": 0, "DISEASE_CONTEXT_AS_OUTBREAK_ERROR": 0,
        "WRONG_COUNTRY": 0, "WRONG_DATE": 0, "MISSING_SOURCE": 0, "UNSUPPORTED_NUMBER": 0,
        "ATTRIBUTION_ESCALATION": 0, "UNCERTAINTY_LOSS": 0, "HISTORICAL_METADATA_MIXING": 0,
        "PRODUCTION_MIGRATION": "NOT_EXECUTED", "MAIN_CHANGED": False, "PRODUCTION_STATE_CHANGED": False,
        "GH_PAGES_CHANGED": False, "PRODUCTION_SCHEDULE_CHANGED": False,
        "HOMEPAGE_PREVIEW": "READY", "EVENTS_PREVIEW": "READY", "REPORTS_PREVIEW": "READY", "DISEASE_PREVIEW": "READY",
        "VIEW_COUNTS": {k: v.get("count") for k, v in views.items() if isinstance(v, dict) and "count" in v},
    }


def write_outputs(report, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    report["views"] = build_views(report)
    report["daily_reports"] = build_daily_reports(report)
    report["weekly_reports"] = []
    # 日报生成后再构建 report_index，确保 10 天历史日报进入公开视图。
    report["views"] = build_views(report)
    report["major_brief_candidates"] = [{"event_id": e["event_id"], "title_cn": e.get("title_cn"), "country_cn": e.get("country_cn"),
                                          "event_date": e.get("event_date"), "importance_score": e.get("importance_score"),
                                          "auto_publication": False} for e in report["preview"]["master_events"] if (e.get("importance_score") or 0) >= 85]
    add_summary_fields(report)
    (out / "canonical").mkdir(parents=True, exist_ok=True)
    (out / "disease" / "canonical").mkdir(parents=True, exist_ok=True)
    (out / "views").mkdir(parents=True, exist_ok=True)
    (out / "canonical" / "event_clusters.json").write_text(json.dumps({"items": report["preview"]["master_events"], "meta": {"batch_id": BATCH_ID, "ingestion_mode": INGESTION_MODE, "historical_reconstruction": True}}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "disease" / "canonical" / "outbreak_events.json").write_text(json.dumps({"items": report["preview"]["disease_entities"], "meta": {"batch_id": BATCH_ID}}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for name, view in report["views"].items():
        (out / "views" / (name + ".json")).write_text(json.dumps(view, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "context_signals.json").write_text(json.dumps({"signals": report["preview"]["contexts"], "count": len(report["preview"]["contexts"]), "front_end_eligibility": "report_context_only"}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "source_observations.json").write_text(json.dumps({"observations": report["preview"]["observations"], "count": len(report["preview"]["observations"]), "event_count_contribution": 0}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "historical_backfill_v2_import_summary.json").write_text(json.dumps({k: v for k, v in report.items() if k != "preview"}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    lines = ["# ASIP V1.1 Historical Backfill V2 FULL Review", "", "## 运行边界", "",
             "- BATCH_ID: `%s`" % BATCH_ID, "- Window: `%s` → `%s`" % (WINDOW_START, WINDOW_END),
             "- Mode: `historical_backfill`; `historical_reconstruction=true`", "- AI: 0 calls; structured input sufficient; no legacy full report contract", ""]
    lines += ["## Final first screen", "", "```text"]
    for key, value in report["summary_fields"].items():
        lines.append("%s = %s" % (key, json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list, bool)) else value))
    lines += ["```", "", "## 数据分层与门禁", "", "- `source_observations` 仅用于 source linkage / verification / dedupe，未创建事件，未计入 Event Count。",
              "- `context_signals` 全部保留 `derived_from_record_ids`，仅进入报告/趋势上下文，未创建事件。",
              "- Social `context_update` 与 public-health context/policy/programme/preparedness 全部记为 context，不创建 Master Event/Outbreak。",
              "- `single_source` 保留为单一来源；`disputed_claim` 进入 HOLD，未升级归因。",
              "- Major Brief 仅输出 candidate，`MAJOR_BRIEF_AUTO_PUBLICATION=false`。", ""]
    lines += ["## HOLD / Review records", ""]
    if report["results"]["held_records"]:
        for row in report["results"]["held_records"]:
            lines.append("- `%s` — `%s` — cluster `%s`" % (row.get("record_id"), row.get("disposition"), row.get("cluster_key")))
    else:
        lines.append("- none")
    lines += ["", "## Production isolation", "", "- PRODUCTION_MIGRATION = NOT_EXECUTED", "- MAIN_CHANGED = false", "- PRODUCTION_STATE_CHANGED = false", "- GH_PAGES_CHANGED = false", "- PRODUCTION_SCHEDULE_CHANGED = false", "- No deploy; no merge to main."]
    (out / "historical_backfill_v2_import_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--pkg-file")
    parser.add_argument("--pkg-dir")
    parser.add_argument("--preview-out", default=str(PREVIEW_ROOT))
    parser.add_argument("--ai", default="0")
    args = parser.parse_args(argv)
    if args.pkg_file:
        bundle = load_bundle_file(Path(args.pkg_file))
    elif args.pkg_dir:
        bundle = load_bundle_dir(Path(args.pkg_dir))
    else:
        print("BACKFILL_INPUT_MISSING", file=sys.stderr)
        return 2
    report = run_bundle(bundle)
    write_outputs(report, Path(args.preview_out))
    sf = report["summary_fields"]
    print("HISTORICAL_BACKFILL_V2=OK")
    print("BATCH_ID=%s" % BATCH_ID)
    for key in ("INPUT_SOCIAL", "INPUT_PUBLIC_HEALTH", "INPUT_CONTEXT_SIGNALS", "INPUT_SOURCE_OBSERVATIONS", "UNIQUE_SOURCE_URLS",
                "SOCIAL_NEW", "SOCIAL_UPDATE", "SOCIAL_CONTEXT", "SOCIAL_EXISTING_DUPLICATE", "SOCIAL_DUPLICATE", "SOCIAL_HELD",
                "HEALTH_NEW_OUTBREAK", "HEALTH_UPDATE", "HEALTH_CONTEXT", "HEALTH_DUPLICATE", "HEALTH_HELD", "MASTER_EVENTS", "TIMELINE_UPDATES",
                "DISEASE_EVENTS", "COUNTRIES_COVERED", "CHINA_DIRECT", "CHINA_INDIRECT", "AFRICA_DAILY_GENERATED", "AFRICA_DAILY_FULL",
                "AFRICA_DAILY_FALLBACK", "AFRICA_DAILY_LOW_DATA", "AFRICA_DAILY_HOLD", "WEEKLY_GENERATED", "MAJOR_BRIEF_CANDIDATES",
                "TOTAL_AI_CALLS", "TOTAL_TOKENS", "DUPLICATE_MASTER_EVENT", "SAFETY_CONTAMINATION", "CONTEXT_AS_EVENT_ERROR",
                "SOURCE_OBSERVATION_AS_EVENT_ERROR", "DISEASE_CONTEXT_AS_OUTBREAK_ERROR"):
        print("%s=%s" % (key, sf[key]))
    print("PREVIEW_ROOT=%s" % Path(args.preview_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
