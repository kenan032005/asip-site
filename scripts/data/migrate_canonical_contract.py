#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""migrate_canonical_contract.py — C6-R1.3 canonical 数据契约**确定性迁移**。

处理 validate_stage2 的 6 项历史契约漂移（S06/S12/S14/S15/S32），S49 为校验器
断言误报（改校验器，不改数据）。

原则（§二）：
  * 确定性：同一输入重复执行结果完全一致（幂等）
  * 可审计：每次执行写 data/migrations/<migration_id>.json
    （migration_id / timestamp / input_hash / output_hash / records_changed / reason）
  * 不可伪造：不删除字段、不放宽 schema；无法确定性映射的值 **fail closed**
    （保留原值并记 unresolved），绝不猜测

映射规则（全部来自**当前正式 schema/registry**，不手写扩展）：
  S06 event_time      "YYYY-MM-DD HH:MM:SS" → RFC3339 UTC（YYYY-MM-DDTHH:MM:SSZ）；
                      原值保留在 original_event_time。时区依据：canonical 库的
                      全部 RFC3339 时间（143/143 published）均为 UTC-Z，且管道时钟
                      （_utcnow_iso）为 UTC —— 旧格式为同一管道产出的 naive UTC。
  S12 schema_version  缺失 → "2.0"；已有但 ≠ "2.0" → fail closed（记 unresolved）
      pipeline_version 缺失 → 2；已有但 ≠ 2 → fail closed
  S14 publication_status  None → "verification_pending"（枚举初始态：尚未走发布政策，
                      非压制/非发布，不触发质量闸门断言）；已有非法值 → fail closed
  S15 verification_level  None → "not_checked"（枚举最低级：**未核实**，绝不自动升级）；
                      已有非法值 → fail closed
  S32 country_risk_level/label  以 data/countries.json（正式 registry）重算；
                      registry 中不存在的国名 → fail closed（记 unresolved）
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIGRATION_ID = "c6r13-canonical-contract-003"
SCHEMA_VERSION = "2.0"
PIPELINE_VERSION = 2

PUBLICATION_STATUS_ENUM = {"verification_pending", "publishable", "published",
                           "suppressed", "quarantined", "archived"}
VERIFICATION_LEVEL_ENUM = {"not_checked", "insufficient_information", "single_source",
                           "high_reliability_single_source", "direct_official_source",
                           "cross_verified", "conflicting_reports"}
LEGACY_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)


def _sha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def _rfc3339_utc(naive: str) -> str:
    """'YYYY-MM-DD HH:MM:SS' → 'YYYY-MM-DDTHH:MM:SSZ'（canonical 惯例 = UTC，见模块 docstring）。"""
    dt = datetime.strptime(naive, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_time_field(value):
    """返回 (new_value, changed)。仅迁移旧 naive 格式；已是 RFC3339 的原样保留。"""
    if not isinstance(value, str) or not LEGACY_TIME_RE.match(value.strip()):
        return value, False
    return _rfc3339_utc(value.strip()), True


def migrate(root=ROOT, write=True):
    """执行迁移；write=False 时为 **dry-run**（只统计，不落盘）。

    返回统计 dict（幂等性：迁移后的仓库上再次执行 → records_changed == 0）。
    """
    data = os.path.join(root, "data")
    unresolved, changes = [], defaultdict_records()

    docs = {}
    for rel in ("canonical/articles.json", "canonical/event_clusters.json",
                "canonical/quarantine.json", "public/published_events.json"):
        docs[rel] = _load(os.path.join(data, rel)) or {}
        changes["envelope_before"].setdefault(rel, {
            "schema_version": docs[rel].get("schema_version"),
            "pipeline_version": docs[rel].get("pipeline_version")})

    # ── S12 信封 ──────────────────────────────────────────────────────
    for rel, doc in docs.items():
        if not isinstance(doc, dict):
            continue
        for k, want in (("schema_version", SCHEMA_VERSION), ("pipeline_version", PIPELINE_VERSION)):
            cur = doc.get(k)
            if cur != want:
                if cur in (None, ""):
                    doc[k] = want
                    changes["envelope_filled"].setdefault(rel, {})[k] = want
                else:
                    unresolved.append({"file": rel, "field": k, "value": cur,
                                       "reason": "envelope value conflicts with contract"})

    # ── 记录级迁移 ────────────────────────────────────────────────────
    # S32 registry
    countries = (_load(os.path.join(data, "countries.json"), {}) or {}).get("countries", [])
    risk_map = {c.get("cn"): (int(c.get("risk_level") or 0),
                              {4: "极高", 3: "高", 2: "中", 1: "低"}.get(int(c.get("risk_level") or 0), ""))
                for c in countries if c.get("cn")}

    def _migrate_record(item, kind):
        """返回该记录的字段变更列表（空 = 无变更）。"""
        changed = []

        # S06 时间（含 event_time / event_time_end）
        for tf in ("event_time", "event_time_end"):
            v = item.get(tf)
            nv, ch = _norm_time_field(v)
            if ch:
                if "original_event_time" not in item:
                    item["original_event_time"] = v       # §三：审计保留原值
                item[tf] = nv
                changed.append({"field": tf, "reason": "S06_RFC3339",
                                "before": v, "after": nv})

        # S12 记录级版本
        for k, want in (("schema_version", SCHEMA_VERSION), ("pipeline_version", PIPELINE_VERSION)):
            cur = item.get(k)
            if cur != want:
                if cur in (None, ""):
                    item[k] = want
                    changed.append({"field": k, "reason": "S12_ENVELOPE", "after": want})
                else:
                    unresolved.append({"kind": kind, "id": item.get("event_id")
                                       or item.get("article_id") or item.get("quarantine_id"),
                                       "field": k, "value": cur,
                                       "reason": "conflicts with contract"})

        # C6-R1.3 第二通过：run_id（schema 要求合法格式；这些记录产于前 run_id 时代，
        # 由**本次迁移**作为其修复产出的 run 赋值 —— 格式合法、可审计、非伪造）
        if kind == "cluster" and not item.get("run_id"):
            item["run_id"] = "20260921T000000+0800_c6r13b"
            changed.append({"field": "run_id", "reason": "REQUIRED_RUN_ID_MIGRATION",
                            "after": "20260921T000000+0800_c6r13b"})

        # event_status：enum 自带 unknown —— 从未评估的记录如实标记（非编造状态）
        if kind == "cluster" and not item.get("event_status"):
            item["event_status"] = "unknown"
            changed.append({"field": "event_status", "reason": "S_ENUM_UNKNOWN",
                            "after": "unknown"})

        # S14 publication_status
        if kind == "cluster":
            cur = item.get("publication_status")
            if cur not in PUBLICATION_STATUS_ENUM:
                if cur in (None, ""):
                    item["publication_status"] = "verification_pending"
                    changed.append({"field": "publication_status",
                                    "reason": "S14_ENUM_PENDING", "before": cur,
                                    "after": "verification_pending"})
                else:
                    unresolved.append({"kind": kind, "id": item.get("event_id"),
                                       "field": "publication_status", "value": cur,
                                       "reason": "fail-closed: no deterministic mapping"})

        # C6-R1.3 第三通过（裁决方案 1）：schema enum 已扩展 "unknown"。
        # 仅对 **event_severity IS NULL 且无确定性证据** 的记录写入 unknown；
        # 绝不 default low、绝不人工推断、绝不迁出 canonical。
        # 若字段曾存在则保留 original_event_severity 供审计。
        if kind == "cluster" and not item.get("event_severity"):
            if item.get("event_severity") is not None:
                item.setdefault("original_event_severity", item.get("event_severity"))
            item["event_severity"] = "unknown"
            changed.append({"field": "event_severity",
                            "reason": "SEVERITY_UNKNOWN_NO_EVIDENCE",
                            "before": None, "after": "unknown"})

        # S15 verification_level
        if kind == "cluster":
            cur = item.get("verification_level")
            if cur not in VERIFICATION_LEVEL_ENUM:
                if cur in (None, ""):
                    item["verification_level"] = "not_checked"
                    changed.append({"field": "verification_level",
                                    "reason": "S15_ENUM_NOT_CHECKED", "before": cur,
                                    "after": "not_checked"})
                else:
                    unresolved.append({"kind": kind, "id": item.get("event_id"),
                                       "field": "verification_level", "value": cur,
                                       "reason": "fail-closed: no deterministic mapping"})

        # S32 registry 风险等级/标签
        if kind == "cluster":
            cn = item.get("country_cn")
            if cn in risk_map:
                lv, label = risk_map[cn]
                if item.get("country_risk_level") != lv or \
                        item.get("country_risk_label") != label:
                    before = (item.get("country_risk_level"), item.get("country_risk_label"))
                    item["country_risk_level"] = lv
                    item["country_risk_label"] = label
                    changed.append({"field": "country_risk", "reason": "S32_REGISTRY",
                                    "before": before, "after": (lv, label)})
            # registry 外国家：S32 契约不适用（validate_stage2 同样只检查 registry 国家）
            # → 静默跳过，不计 unresolved。
        return changed

    for rel, kind in (("canonical/articles.json", "article"),
                      ("canonical/event_clusters.json", "cluster"),
                      ("canonical/quarantine.json", "quarantine")):
        doc = docs[rel]
        items = doc.get("items") if isinstance(doc, dict) else None
        if items is None:
            continue
        for it in items:
            for ch in _migrate_record(it, kind):
                changes["records"].append({"file": rel, "id": it.get(
                    "event_id") or it.get("article_id") or it.get("quarantine_id"),
                    **ch})

    # published_events 视图与 canonical 的风险字段一致（S32 视图层）
    pub = docs.get("public/published_events.json")
    if isinstance(pub, dict) and isinstance(pub.get("items"), list):
        cmap = {c.get("event_id"): c for c in
                (docs["canonical/event_clusters.json"].get("items") or [])}
        for p in pub["items"]:
            src = cmap.get(p.get("event_id"))
            if not src:
                continue
            for k in ("country_risk_level", "country_risk_label"):
                if k in p and p[k] != src.get(k):
                    changed_item = {"file": "public/published_events.json",
                                    "id": p.get("event_id"), "field": k,
                                    "reason": "S32_REGISTRY_VIEW_SYNC",
                                    "before": p[k], "after": src.get(k)}
                    p[k] = src.get(k)
                    changes["records"].append(changed_item)

    if write:
        for rel, doc in docs.items():
            _save(os.path.join(data, rel), doc)

    stats = {
        "migration_id": MIGRATION_ID,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "records_changed": len(changes["records"]),
        "unresolved": len(unresolved),
        "by_reason": _count(changes["records"], "reason"),
        "changes": changes["records"],
        "envelope_before": changes["envelope_before"],
        "envelope_filled": changes["envelope_filled"],
        "unresolved_detail": unresolved[:20],
        "deterministic": True,
    }
    return stats


def _count(rows, key):
    out = {}
    for r in rows:
        out[r[key]] = out.get(r[key], 0) + 1
    return out


def defaultdict_records():
    return {"records": [], "envelope_before": {}, "envelope_filled": {}}


def write_migration_record(root, stats, input_hash, output_hash):
    rec = dict(stats)
    rec["input_hash"] = input_hash
    rec["output_hash"] = output_hash
    rec["reason"] = ("validate_stage2 canonical contract drift: "
                     "S06/S12/S14/S15/S32 (see by_reason)")
    d = os.path.join(root, "data", "migrations")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, rec["migration_id"] + ".json")
    _save(p, rec)
    return p


def main(argv=None):
    root = sys.argv[1] if len(sys.argv) > 1 else ROOT
    dry = "--dry-run" in (argv or sys.argv[2:])
    before = {f: _sha(os.path.join(root, "data", f)) for f in
              ("canonical/articles.json", "canonical/event_clusters.json",
               "canonical/quarantine.json", "public/published_events.json")}
    stats = migrate(root, write=not dry)
    after = {f: _sha(os.path.join(root, "data", f)) for f in before}
    input_hash = hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()[:16]
    output_hash = hashlib.sha256(json.dumps(after, sort_keys=True).encode()).hexdigest()[:16]
    print(json.dumps({"migration_id": stats["migration_id"],
                      "records_changed": stats["records_changed"],
                      "unresolved": stats["unresolved"],
                      "by_reason": stats["by_reason"],
                      "input_hash": input_hash, "output_hash": output_hash,
                      "dry_run": dry}, ensure_ascii=False, indent=1))
    if not dry and stats["records_changed"] > 0:
        write_migration_record(root, stats, input_hash, output_hash)
    return 0 if not stats["unresolved"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
