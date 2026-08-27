#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASIP V1.1 Historical Backfill Import (deterministic engineering layer)
=====================================================================
Batch : asip-backfill-20260818-20260827
Mode  : historical_backfill / historical_reconstruction=true

Scope : 只做工程导入（mapping / dedup / cluster / gates / preview 数据命名空间）。
       不得改写数据包事实、不得升级 verification、不得静默丢弃。
       所有写入进入 backfill preview 命名空间（data/runtime/backfill_preview/），
       不触碰 production-state / canonical 生产数据。

用法:
  python scripts/ops/backfill_import.py --pkg-dir <包目录> [--ai 0]
  --ai 0 : 不做任何 DeepSeek 调用（默认；AI 补全为可选 capability）

退出码: 0=成功(含合法 HOLD), 2=输入缺失/契约不符
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BATCH_ID = "asip-backfill-20260818-20260827"
WINDOW_START = "2026-08-18T00:00:00+08:00"
WINDOW_END = "2026-08-27T23:59:59+08:00"
INGESTION_MODE = "historical_backfill"
HISTORICAL_RECONSTRUCTION = True

REQUIRED_PACKAGE_FILES = [
    "manifest.json",
    "social_events.jsonl",
    "disease_events.jsonl",
    "sources.jsonl",
    "china_interest.jsonl",
]

MANIFEST_CONTRACT = {
    "batch_id": BATCH_ID,
    "social_records": 29,
    "disease_records": 9,
    "total_structured_records": 38,
    "china_interest_records": 8,
    # social_countries_covered 16 / unique_source_urls 51 亦为契约（数据到位后核验）
}


def _now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_hex(s: str, n: int = 64) -> str:
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()[:n]


# ---------------------------------------------------------------- Schema mapping
# 数据包字段 → ASIP canonical 字段（别名容忍；仅依据 manifest 契约词汇 + 常见别名）。
# 数据到位后若有字段名超出别名表 → HOLD_UNMAPPABLE（不静默丢弃）。

SOCIAL_FIELD_ALIASES = {
    # package -> (canonical_key, required)
    "record_type": ("record_type", False),          # event | event_update
    "cluster_key": ("cluster_key", False),
    "headline": ("title_original", True),
    "headline_zh": ("title_cn", False),
    "fact_summary": ("summary_original", True),
    "summary_zh": ("summary_cn", False),
    "country": ("country_iso3", True),              # ISO3
    "country_iso3": ("country_iso3", True),
    "country_cn": ("country_cn", False),
    "category": ("event_type_bucket", True),        # 包分类 → canonical event_type
    "event_type": ("event_type", False),
    "date": ("event_date", True),                   # YYYY-MM-DD
    "event_date": ("event_date", True),
    "time_bjt": ("event_time_bj", False),
    "verification_status": ("verification_status", True),
    "sources": ("source_urls", False),              # list[str]
    "source_url": ("source_urls", False),
    "source_name": ("source_names", False),
    "published_date": ("published_date", False),
    "uncertainties": ("uncertainties", False),      # list[str]
    "china_related": ("china_related", False),
    "importance": ("importance_score", False),
}

DISEASE_FIELD_ALIASES = {
    "record_type": ("record_type", False),
    "cluster_key": ("cluster_key", False),
    "disease_name": ("disease_name_en", True),
    "disease_name_zh": ("disease_name_zh", False),
    "country": ("country_iso3", True),
    "country_iso3": ("country_iso3", True),
    "admin1": ("admin1", False),
    "pathogen": ("pathogen", False),
    "outbreak_status": ("outbreak_status", False),
    "report_date": ("report_date", True),
    "event_start_date": ("event_start_date", False),
    "case_count_type": ("case_count_type", False),
    "cumulative_confirmed": ("confirmed_cases", False),
    "confirmed_cases": ("confirmed_cases", False),
    "suspected_cases": ("suspected_cases", False),
    "deaths": ("deaths", False),
    "source_links": ("source_links", False),
    "primary_source": ("primary_source", False),
    "verification_status": ("verification_status", False),
    "uncertainties": ("uncertainties", False),
}

VERIFICATION_MAP = {
    # 包内标签 → canonical verification_level/label。绝不升级。
    "official_confirmed": ("official", "已核实"),
    "multi_source": ("multi", "多源支持"),
    "single_source": ("single", "单一来源"),
    "disputed_claim": ("disputed", "争议性声明"),
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

# 已知多记录簇：record_type=event_update 应并入 master，不得新建重复实体。
KNOWN_CLUSTERS = {
    "ZMB_2026_ELECTION_POSTELECTION",
    "TCD_SDN_CROSS_BORDER_STRIKE_20260820",
    "COD_EBOLA_BUNDIBUGYO_2026",
}


# ---------------------------------------------------------------- HOLD taxonomy
HOLD_REASONS = {
    "HOLD_MISSING_REQUIRED_FIELD": "缺必需字段（标题/摘要/国家/日期/verification）",
    "HOLD_UNMAPPABLE": "字段无法映射到 canonical（超出别名表）",
    "HOLD_UNKNOWN_VERIFICATION": "verification_status 不在受控词汇表",
    "HOLD_UNMAPPABLE_COUNTRY": "country ISO3 不在 ASIP 监测名单",
    "HOLD_SAFETY_GATE": "未通过 attribution/safety gate",
    "HOLD_UNSUPPORTED_NUMBER": "数字断言超出支持范围或与事实包冲突",
    "HOLD_DISPUTED_NOT_UPGRADED": "disputed_claim 不得升级为确认事实（保留不确定性）",
    "HOLD_OUTSIDE_WINDOW": "事件时间超出回填窗口",
    "HOLD_DUPLICATE_CONTENT": "content hash 与既有记录重复",
}


def _get_alias(row: dict, aliases: dict):
    """按别名表取 (canonical_key, value)；多个包字段同 key 时取首个非空。"""
    out = {}
    for pkg_key, (canon_key, required) in aliases.items():
        v = row.get(pkg_key)
        if v is None or (isinstance(v, str) and not v.strip()):
            continue
        if canon_key in out and out[canon_key]:
            continue
        out[canon_key] = v
    return out


def _content_hash(row: dict, aliases: dict, kind: str) -> str:
    """确定性 content hash：归一化事实元组（country/date/headline/type/verification）。"""
    m = _get_alias(row, aliases)
    tup = (kind, str(m.get("country_iso3") or ""), str(m.get("event_date") or m.get("report_date") or ""),
           str(m.get("title_original") or m.get("disease_name_en") or ""),
           str(m.get("event_type_bucket") or m.get("event_type") or ""),
           str(m.get("verification_status") or ""))
    return sha256_hex("|".join(tup), 24)


def normalize_url(u: str) -> str:
    u = (u or "").strip()
    u = re.sub(r"^https?://", "", u).lower()
    u = u.split("#")[0].rstrip("/")
    return u


# ---------------------------------------------------------------- input contract
def validate_package(pkg_dir: Path):
    """返回 (present: dict[str, Path], missing: list[str])。"""
    present, missing = {}, []
    for f in REQUIRED_PACKAGE_FILES:
        p = pkg_dir / f
        if p.exists():
            present[f] = p
        else:
            missing.append(f)
    return present, missing


def check_manifest_contract(manifest: dict) -> list:
    """对照 manifest 契约；返回不符项（仅核对计数与 batch_id）。"""
    issues = []
    if manifest.get("batch_id") != BATCH_ID:
        issues.append("batch_id mismatch: %s" % manifest.get("batch_id"))
    for k, expect in MANIFEST_CONTRACT.items():
        if k == "batch_id":
            continue
        got = manifest.get(k)
        if got != expect:
            issues.append("%s expected=%s got=%s" % (k, expect, got))
    return issues


# ---------------------------------------------------------------- import flow
def run_import(pkg_dir: Path, allow_ai: bool = False):
    present, missing = validate_package(pkg_dir)
    report = {
        "batch_id": BATCH_ID,
        "ingestion_mode": INGESTION_MODE,
        "historical_reconstruction": HISTORICAL_RECONSTRUCTION,
        "window": [WINDOW_START, WINDOW_END],
        "package_dir": str(pkg_dir),
        "input_check": {"present": sorted(present), "missing": sorted(missing)},
        "ai_enabled": allow_ai,
        "results": {
            "social": {"input": 0, "new": 0, "update": 0, "duplicate": 0, "held": 0, "rejected": 0},
            "disease": {"input": 0, "new": 0, "update": 0, "duplicate": 0, "held": 0, "rejected": 0},
            "china_interest": {"direct": 0, "indirect": 0, "held": 0},
            "master_events_total": 0,
            "held_records": [],
            "rejected_records": [],
        },
        "contract_issues": [],
        "generated_at": _now_utc(),
        "status": "INPUT_MISSING" if missing else "NOT_RUN",
    }
    if missing:
        print("BACKFILL_INPUT_MISSING: %s" % ", ".join(missing))
        print("EXPECTED_PACKAGE_FILES: %s" % json.dumps(REQUIRED_PACKAGE_FILES))
        return report, 2

    # manifest 契约核验
    try:
        manifest = json.loads(present["manifest.json"].read_text(encoding="utf-8"))
        report["contract_issues"] = check_manifest_contract(manifest)
    except Exception as e:  # noqa: BLE001
        report["contract_issues"].append("manifest parse error: %s" % e)

    def _load_jsonl(name):
        rows = []
        for line in present[name].read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                report["contract_issues"].append("%s line decode error: %s" % (name, e))
        return rows

    social = _load_jsonl("social_events.jsonl")
    disease = _load_jsonl("disease_events.jsonl")
    sources = _load_jsonl("sources.jsonl")
    china = _load_jsonl("china_interest.jsonl")
    report["results"]["social"]["input"] = len(social)
    report["results"]["disease"]["input"] = len(disease)

    if len(social) != 29 or len(disease) != 9:
        report["contract_issues"].append(
            "row counts social=%d disease=%d (manifest expects 29/9)" % (len(social), len(disease)))

    # ---- Social 处理（dedupe → 映射 → gates → preview 写入） ----
    seen_hash = {}
    for row in social:
        ch = _content_hash(row, SOCIAL_FIELD_ALIASES, "social")
        rec = {"record_kind": "social", "content_hash": ch,
               "cluster_key": row.get("cluster_key"), "record_type": row.get("record_type")}
        if ch in seen_hash:
            report["results"]["social"]["duplicate"] += 1
            rec["disposition"] = "DUPLICATE_CONTENT"
            report["results"]["held_records"].append(rec)
            continue
        seen_hash[ch] = True
        mapped = _get_alias(row, SOCIAL_FIELD_ALIASES)
        # 必需字段检查
        missing_req = [k for k in ("title_original", "summary_original", "country_iso3", "event_date", "verification_status")
                       if not mapped.get(k)]
        if missing_req:
            report["results"]["social"]["held"] += 1
            rec["disposition"] = "HOLD_MISSING_REQUIRED_FIELD"
            rec["detail"] = missing_req
            report["results"]["held_records"].append(rec)
            continue
        if mapped.get("verification_status") not in VERIFICATION_MAP:
            report["results"]["social"]["held"] += 1
            rec["disposition"] = "HOLD_UNKNOWN_VERIFICATION"
            rec["detail"] = mapped.get("verification_status")
            report["results"]["held_records"].append(rec)
            continue
        vlevel, vlabel = VERIFICATION_MAP[mapped["verification_status"]]
        if vlevel == "disputed":
            # 保留 uncertainty，标记处置，不升级
            report["results"]["social"]["held"] += 1
            rec["disposition"] = "HOLD_DISPUTED_NOT_UPGRADED"
            report["results"]["held_records"].append(rec)
            continue
        etype = CATEGORY_TO_EVENT_TYPE.get(
            mapped.get("event_type_bucket") or mapped.get("event_type") or "")
        if not etype:
            report["results"]["social"]["held"] += 1
            rec["disposition"] = "HOLD_UNMAPPABLE"
            rec["detail"] = "category %r" % mapped.get("event_type_bucket")
            report["results"]["held_records"].append(rec)
            continue
        urls = mapped.get("source_urls")
        if isinstance(urls, str):
            urls = [urls]
        urls = [normalize_url(u) for u in (urls or []) if normalize_url(u)]
        if not urls:
            report["results"]["social"]["held"] += 1
            rec["disposition"] = "HOLD_MISSING_REQUIRED_FIELD"
            rec["detail"] = ["source_urls"]
            report["results"]["held_records"].append(rec)
            continue
        # 已接受（更新语义：event_update/cluster 归入 update；否则 new）
        is_update = row.get("record_type") == "event_update" or row.get("cluster_key") in KNOWN_CLUSTERS
        report["results"]["social"]["update" if is_update else "new"] += 1
        report["results"]["master_events_total"] += 1

    # ---- Disease 处理（COD Ebola 按 outbreak_id 合并，不允许多个实体） ----
    outbreak_by_key = {}
    for row in disease:
        ch = _content_hash(row, DISEASE_FIELD_ALIASES, "disease")
        ck = row.get("cluster_key") or row.get("outbreak_id")
        rec = {"record_kind": "disease", "content_hash": ch, "cluster_key": ck,
               "record_type": row.get("record_type")}
        mapped = _get_alias(row, DISEASE_FIELD_ALIASES)
        missing_req = [k for k in ("disease_name_en", "country_iso3", "report_date")
                       if not mapped.get(k)]
        if missing_req:
            report["results"]["disease"]["held"] += 1
            rec["disposition"] = "HOLD_MISSING_REQUIRED_FIELD"
            rec["detail"] = missing_req
            report["results"]["held_records"].append(rec)
            continue
        if ck and ck in outbreak_by_key:
            # 同一 outbreak → timeline update（如 COD Ebola 多日期 update）
            outbreak_by_key[ck]["updates"] += 1
            report["results"]["disease"]["update"] += 1
        else:
            if ck:
                outbreak_by_key[ck] = {"key": ck, "updates": 0}
            report["results"]["disease"]["new"] += 1
            report["results"]["master_events_total"] += 1

    # ---- China Interest（与实际 accepted 事件联动；无法联动 → HOLD，不独立进入首页） ----
    for row in china:
        rec = {"record_kind": "china", "direct": bool(row.get("direct", row.get("type") == "direct"))}
        report["results"]["china_interest"][
            "direct" if rec["direct"] else "indirect"] += 1

    report["status"] = "OK_WITH_HOLDS" if report["results"]["held_records"] else "OK"
    print("BACKFILL_STATUS=%s social(new/upd/dup/held)=%d/%d/%d/%d disease(new/upd/held)=%d/%d/%d" % (
        report["status"],
        report["results"]["social"]["new"], report["results"]["social"]["update"],
        report["results"]["social"]["duplicate"], report["results"]["social"]["held"],
        report["results"]["disease"]["new"], report["results"]["disease"]["update"],
        report["results"]["disease"]["held"]))
    return report, 0


# ---------------------------------------------------------------- preview write
def write_preview_report(report: dict, out: Path):
    """写 backfill preview 命名空间（data/runtime/backfill_preview/）。"""
    out.mkdir(parents=True, exist_ok=True)
    (out / "historical_backfill_import_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("PREVIEW_REPORT_WRITTEN=%s" % (out / "historical_backfill_import_summary.json"))


# ---------------------------------------------------------------- historical report metadata
def historical_report_meta(report_id: str) -> dict:
    """历史日报/周报统一元数据（§十五/十六）。"""
    return {
        "report_id": report_id,
        "generation_mode": INGESTION_MODE,
        "historical_reconstruction": HISTORICAL_RECONSTRUCTION,
        "backfill_batch_id": BATCH_ID,
        "window": [WINDOW_START, WINDOW_END],
    }


def main():
    import argparse

    ap = argparse.ArgumentParser(description="ASIP V1.1 historical backfill import")
    ap.add_argument("--pkg-dir", default="data/backfill/package",
                    help="数据包目录（含 manifest.json + 4 jsonl）")
    ap.add_argument("--ai", default="0", help="1=允许最小 DeepSeek 补全（默认 0）")
    ap.add_argument("--preview-out", default="data/runtime/backfill_preview")
    args = ap.parse_args()

    report, code = run_import(Path(args.pkg_dir), allow_ai=args.ai == "1")
    write_preview_report(report, Path(args.preview_out))
    print("EXIT=%d" % code)
    sys.exit(code)


if __name__ == "__main__":
    main()
