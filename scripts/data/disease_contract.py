#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""disease_contract.py — 疾病数据的**全站统一契约**（C5-A §十二–§十五）。

真实 canonical schema（C4 已确认）：
  disease_event_id / disease_id / disease_name_en / disease_name_zh / country_iso3 /
  location_raw / report_date / confirmed_cases / probable_cases / suspected_cases /
  total_cases / deaths / recoveries / case_count_type / outbreak_status / update_type /
  primary_source / source_links[{url, source_id, source_name, source_tier}] /
  verification_status / uncertainties

**禁止再读**（历史幻觉字段，真实数据里不存在）：
  latest_counts / updates

本模块提供：normalize / source_identity / freshness / country scope（复用 C4 的
`fact_content.country_scope_decision`），以及 deprecated 读取的静态审计。
"""
from __future__ import annotations

import io
import json
import os
import re

#: canonical 疾病记录的真实字段
SCHEMA_FIELDS = ("disease_event_id", "disease_id", "disease_name_en", "disease_name_zh",
                 "pathogen", "country_iso3", "admin1", "location_raw", "report_date",
                 "event_start_date", "case_period_start", "case_period_end",
                 "confirmed_cases", "probable_cases", "suspected_cases", "total_cases",
                 "deaths", "recoveries", "case_count_type", "outbreak_status",
                 "update_type", "primary_source", "source_links", "source_tier",
                 "verification_status", "uncertainties", "affected_countries",
                 "cross_border")
#: **不得**在 active 路径读取的字段（真实 schema 里不存在）
DEPRECATED_FIELDS = ("latest_counts", "updates")
#: 计数类字段
COUNT_FIELDS = ("confirmed_cases", "probable_cases", "suspected_cases",
                "total_cases", "deaths", "recoveries")
#: 视为「活跃」的疫情状态
ACTIVE_STATUSES = ("active", "developing", "increasing", "geographic_spread",
                   "monitoring", "ongoing")
#: 伪造来源黑名单（不得出现）
FAKE_SOURCE_PATTERNS = ("source_unknown", "synthetic", "unknown_source",
                        "disease_source_0")

#: §十四 freshness 阈值（项目此前没有统一常量 —— 这里建立明确常量并测试）
FRESHNESS_CURRENT_MAX_DAYS = 14      # ≤14 天：CURRENT
FRESHNESS_STALE_MAX_DAYS = 60        # ≤60 天：STALE；更长：NO_RECENT_DATA

FRESHNESS_CURRENT = "CURRENT"
FRESHNESS_STALE = "STALE"
FRESHNESS_NONE = "NO_RECENT_DATA"


def load_items(root):
    p = os.path.join(str(root), "data", "disease", "canonical", "outbreak_events.json")
    if not os.path.exists(p):
        return []
    doc = json.load(io.open(p, encoding="utf-8"))
    if isinstance(doc, list):
        return doc
    return doc.get("items") or doc.get("events") or []


def load_source_registry(root):
    p = os.path.join(str(root), "data", "sources.json")
    if not os.path.exists(p):
        return {}
    doc = json.load(io.open(p, encoding="utf-8"))
    rows = doc.get("sources") or doc.get("items") or (doc if isinstance(doc, list) else [])
    out = {}
    for r in rows:
        if r.get("source_id"):
            out[str(r["source_id"]).lower()] = r
        if r.get("source_name"):
            out[str(r["source_name"]).lower()] = r
    return out


def source_identity(item, registry=None):
    """§十三 真实来源身份：优先 `source_links`；`primary_source` 仅在能**确定映射**时转换。"""
    ids, names, urls, methods = [], [], [], []
    for l in (item.get("source_links") or []):
        if not isinstance(l, dict):
            continue
        if l.get("source_id"):
            ids.append(l["source_id"])
            methods.append("SOURCE_LINK_ID")
        if l.get("source_name"):
            names.append(l["source_name"])
        if l.get("url"):
            urls.append(l["url"])
    ps = (item.get("primary_source") or "").strip()
    if ps and registry:
        hit = registry.get(ps.lower())
        if hit:
            if hit.get("source_id"):
                ids.append(hit["source_id"])
            if hit.get("source_name"):
                names.append(hit["source_name"])
            methods.append("PRIMARY_SOURCE_REGISTRY_MATCH")
    def _u(x):
        seen, out = set(), []
        for i in x:
            if i and i not in seen:
                seen.add(i); out.append(i)
        return out
    return {"source_ids": _u(ids), "source_names": _u(names), "urls": _u(urls),
            "identity_methods": _u(methods),
            "has_identity": bool(ids or names)}


def normalize(item, registry=None):
    """规范化为契约形状（只搬运真实字段，不编造）。"""
    counts = {k: item.get(k) for k in COUNT_FIELDS
              if isinstance(item.get(k), (int, float)) and not isinstance(item.get(k), bool)}
    si = source_identity(item, registry)
    return {
        "disease_event_id": item.get("disease_event_id"),
        "disease_id": item.get("disease_id"),
        "disease_name_cn": item.get("disease_name_zh") or None,
        "disease_name_en": item.get("disease_name_en") or None,
        "country_iso3": item.get("country_iso3"),
        "location": item.get("location_raw") or item.get("admin1"),
        "report_date": item.get("report_date"),
        "counts": counts,
        "outbreak_status": item.get("outbreak_status"),
        "update_type": item.get("update_type"),
        "case_count_type": item.get("case_count_type"),
        "primary_source": item.get("primary_source"),
        "verification_status": item.get("verification_status"),
        "uncertainties": item.get("uncertainties") or [],
        "affected_countries": item.get("affected_countries") or [],
        "source_ids": si["source_ids"], "source_names": si["source_names"],
        "urls": si["urls"], "identity_methods": si["identity_methods"],
        "has_source_identity": si["has_identity"],
        "is_active": (item.get("outbreak_status") or "").lower() in ACTIVE_STATUSES,
    }


def _days_between(a, b):
    from datetime import date
    try:
        da = date.fromisoformat(str(a)[:10])
        db = date.fromisoformat(str(b)[:10])
        return (db - da).days
    except Exception:  # noqa: BLE001
        return None


def freshness(items, data_as_of=None):
    """§十四 统一新鲜度：disease_data_as_of / latest_disease_report_date / status。"""
    dates = sorted(str(i.get("report_date"))[:10] for i in items if i.get("report_date"))
    latest = dates[-1] if dates else None
    ref = str(data_as_of)[:10] if data_as_of else None
    age = _days_between(latest, ref) if (latest and ref) else None
    if not latest:
        status = FRESHNESS_NONE
    elif age is None:
        status = FRESHNESS_STALE          # 无法计算年龄 → 保守判 STALE
    elif age <= FRESHNESS_CURRENT_MAX_DAYS:
        status = FRESHNESS_CURRENT
    elif age <= FRESHNESS_STALE_MAX_DAYS:
        status = FRESHNESS_STALE
    else:
        status = FRESHNESS_NONE
    return {"disease_data_as_of": ref, "latest_disease_report_date": latest,
            "disease_age_days": age, "disease_freshness_status": status,
            "records_total": len(items), "freshness_thresholds": {
                "CURRENT_MAX_DAYS": FRESHNESS_CURRENT_MAX_DAYS,
                "STALE_MAX_DAYS": FRESHNESS_STALE_MAX_DAYS}}


def country_scope(items, report):
    """§十五 复用 C4 已验证的 country scope 契约（唯一判定，不另写一套）。"""
    import sys
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if root not in sys.path:
        sys.path.insert(0, root)
    from scripts.report import fact_content as FC
    kept, excluded = [], []
    for it in items:
        (kept if FC.country_scope_ok(it, report) else excluded).append(it)
    return kept, excluded


#: 数据层分类（§十二：只有「读 canonical 疾病记录」才算违规）。
#: TIMELINE_LAYER：这些模块的 latest_counts/updates 是**该层自己的派生结构**
#:   （由 scripts/timeline/disease.py 从 canonical 真实字段派生），不是 canonical 字段。
LAYER_TIMELINE = ("scripts/timeline/",)
#: VIEW_LAYER 消费 timeline/view 记录（含其派生字段），不直接读 canonical
# 注：frontend 视图构建消费的是 **timeline 层的派生字段**（timeline/disease.py 由
# canonical 真实字段派生 latest_counts/updates），因此属 VIEW 层而非 canonical 违规。
LAYER_VIEW = ("scripts/frontend/", "scripts/ops/homepage_analysis.py",
              "scripts/ops/v2_preview_semantic_gate.py", "scripts/report/changes.py",
              "scripts/report/weekly.py", "scripts/report/gen/quality.py",
              "scripts/ops/backfill_import.py")
#: 显式允许：mock provider（非生产数据路径）与 fact_content 的**向后兼容回退**
LAYER_ALLOWED = ("scripts/report/gen/providers.py", "scripts/report/fact_content.py",
                 "scripts/report/builder.py", "scripts/report/dryrun.py",
                 "scripts/timeline/dryrun.py")


def _matches(p, patterns):
    """patterns 里以 "/" 结尾的是目录前缀，其余是精确文件路径。"""
    for pat in patterns:
        if pat.endswith("/"):
            if p.startswith(pat):
                return True
        elif p == pat:
            return True
    return False


def classify_hit(rel_path):
    """把静态命中归类到数据层：canonical（违规）/ timeline / view / allowed。"""
    p = rel_path.replace(os.sep, "/")
    if _matches(p, LAYER_TIMELINE):
        return "TIMELINE_LAYER_DERIVED"
    if _matches(p, LAYER_ALLOWED):
        return "ALLOWED_COMPAT_OR_MOCK"
    if _matches(p, LAYER_VIEW):
        return "VIEW_LAYER_CONSUMES_DERIVED"
    return "CANONICAL_LAYER_VIOLATION"


def audit_deprecated_readers(root):
    """§十二 静态审计：active 路径不得再读 latest_counts / updates。"""
    hits = []
    base = os.path.join(str(root), "scripts")
    skip = ("tests", "qualification", "legacy", "reference", "__pycache__")
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                src = io.open(p, encoding="utf-8").read()
            except Exception:  # noqa: BLE001
                continue
            for m in re.finditer(r'\.get\(\s*["\'](latest_counts|updates)["\']|'
                                 r'\[\s*["\'](latest_counts|updates)["\']\s*\]', src):
                line = src[:m.start()].count("\n") + 1
                rel = os.path.relpath(p, str(root)).replace(os.sep, "/")
                hits.append({"file": rel, "line": line,
                             "field": m.group(1) or m.group(2),
                             "layer": classify_hit(rel)})
    return hits


def build_view(root, data_as_of=None, write=False):
    """生成疾病契约视图（供 UI/审计使用），确定性、无 AI。"""
    items = load_items(root)
    reg = load_source_registry(root)
    norm = [normalize(i, reg) for i in items]
    with_identity = sum(1 for n in norm if n["has_source_identity"])
    fake = [n for n in norm for s in (n["source_ids"] + n["source_names"])
            if any(str(s).lower().startswith(f) for f in FAKE_SOURCE_PATTERNS)]
    view = {
        "generated_by": "scripts/data/disease_contract.py",
        "DISEASE_RECORDS_TOTAL": len(norm),
        "DISEASE_WITH_SOURCE_IDENTITY": with_identity,
        "DISEASE_WITHOUT_SOURCE_IDENTITY": len(norm) - with_identity,
        "FAKE_DISEASE_SOURCE_IDS": len(fake),
        "schema_fields": list(SCHEMA_FIELDS),
        "deprecated_fields": list(DEPRECATED_FIELDS),
        "freshness": freshness(items, data_as_of),
        "records": norm,
    }
    if write:
        vd = os.path.join(str(root), "data", "views")
        os.makedirs(vd, exist_ok=True)
        with io.open(os.path.join(vd, "disease_contract.json"), "w",
                     encoding="utf-8", newline="") as f:
            json.dump(view, f, ensure_ascii=False, indent=1)
    return view
