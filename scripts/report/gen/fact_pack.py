#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage8C Package2 — Deterministic Fact Pack builder（AI_CALLS=0）。

REPORT_ARCHITECTURE = DETERMINISTIC_FACTS_PLUS_AI_ANALYSIS

职责（§一/§三）：Python/Deterministic 负责 facts / event selection / dates /
countries / locations / numbers / source_refs / verification / uncertainties /
importance / selection reasons / trend metrics / disease metrics / report
metadata / period / sections / final structural schema。DeepSeek 只负责
executive_assessment / trend_analysis / outlook / watch_points。

本模块：把冻结的 Derived Report Input（hash 锁定，来自 Run#4 evidence snapshot）
确定性转换为 report_fact_pack —— 全部字段来自已验证输入，绝不调用 LLM。

Fact Pack 字段（§三）：
  report metadata / period / selected social facts / selected disease facts /
  source refs / verification / uncertainties / importance / selection reasons /
  numeric provenance / country distribution / trend metrics
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

_NUM_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})*|\d+)(?![\w.])")

# 实体后缀：用于分析实体边界检查（确定性启发，不做 NLP）
_ORG_SUFFIX = ("组织", "机构", "公司", "通讯社", "大学", "医院", "部队", "委员会",
               "政府", "卫生部", "外交部", "军队", "央行", "联合会", "基金会", "署")
_GEO_SUFFIX = ("省", "市", "县", "区", "州", "镇", "国", "地区", "流域", "湖",
               "河", "半岛", "海湾", "城")
# 归因升级词：Fact Pack 含不确定标记时，分析中出现这些词 → 归因升级 FAIL
_ESCALATION_WORDS = ("已证实", "已确认", "已确证", "确凿", "实锤", "confirmed",
                     "verified fact", "确认为事实", "已核实为")


def _num_from_text(text):
    """文本中出现的数字（int 列表，去重保序）。"""
    out = []
    for m in _NUM_RE.findall(str(text or "")):
        try:
            n = int(m.replace(",", ""))
        except ValueError:
            continue
        if n not in out:
            out.append(n)
    return out


def _fact_numeric_provenance(item, section):
    """fact 文本字段 → {value: [path]}（供 analysis 数字边界检查）。"""
    prov = {}
    text_fields = []
    for k, v in item.items():
        if isinstance(v, str):
            text_fields.append((k, v))
    for k, v in text_fields:
        for n in _num_from_text(v):
            prov.setdefault(n, []).append("sections.%s.%s" % (section, k))
    # facts 数组文本
    for i, f in enumerate(item.get("facts") or []):
        if not isinstance(f, dict):
            continue
        for k, v in f.items():
            if isinstance(v, str):
                for n in _num_from_text(v):
                    prov.setdefault(n, []).append("sections.%s.facts[%d].%s" % (section, i, k))
    return prov


def _social_fact(item, section):
    return {
        "fact_id": item.get("event_id"),
        "headline_zh": item.get("title"),
        "verified_summary": item.get("summary"),
        "country": item.get("country"),
        "country_iso3": item.get("country_iso3"),
        "category": item.get("category"),
        "event_type": item.get("event_type"),
        "importance_score": item.get("importance_score"),
        "verification_status": item.get("verification"),
        "single_source_warning": bool(item.get("single_source_warning")),
        "conflicting": bool(item.get("conflicting")),
        "uncertainties": [u for u in (item.get("uncertainties") or []) if u],
        "source_refs": [s.get("source_name") for s in (item.get("source_evidence") or [])
                        if s.get("source_name")],
        "source_ids": [s.get("source_id") for s in (item.get("source_evidence") or [])
                       if s.get("source_id")],
        "selection_reasons": item.get("selection_reasons") or [],
        "numeric_facts": _fact_numeric_provenance(item, section),
    }


def _disease_fact(item, section):
    return {
        "fact_id": item.get("disease_event_id") or item.get("disease_id"),
        "disease_id": item.get("disease_id"),
        "headline_zh": item.get("title"),
        "verified_summary": item.get("summary"),
        "country_iso3": item.get("country_iso3"),
        "verification_status": item.get("verification"),
        "uncertainties": [u for u in (item.get("uncertainties") or []) if u],
        "source_refs": [s.get("source_name") for s in (item.get("source_evidence") or [])
                        if s.get("source_name")],
        "source_ids": [s.get("source_id") for s in (item.get("source_evidence") or [])
                       if s.get("source_id")],
        "selection_reasons": item.get("selection_reasons") or [],
        "numeric_facts": _fact_numeric_provenance(item, section),
    }


def build_fact_pack(report_input):
    """Deterministic Fact Pack（§三）。report_input 必须为冻结 derived input。"""
    sections = report_input.get("sections") or {}
    rtype = report_input.get("report_type")
    social_items = (sections.get("executive_summary")
                    or sections.get("major_events") or [])
    if rtype == "country_weekly":
        social_items = sections.get("major_events") or []
    disease_items = (sections.get("public_health_disease")
                     if rtype == "africa_daily"
                     else sections.get("disease_public_health") or [])
    # 区分 weekly major_events 中的 disease 项（含 disease_id）
    if rtype == "country_weekly":
        dis_ids = {it.get("disease_id") or it.get("disease_event_id")
                   for it in social_items if it.get("disease_id") or it.get("disease_event_id")}
        pure_social = [it for it in social_items
                       if not (it.get("disease_id") or it.get("disease_event_id"))]
        weekly_dis = [it for it in social_items
                      if it.get("disease_id") or it.get("disease_event_id")]
        disease_items = disease_items + weekly_dis
        social_items = pure_social

    social_facts = [_social_fact(it, "social") for it in social_items]
    disease_facts = [_disease_fact(it, "disease") for it in disease_items]

    # numeric provenance（全 pack）
    numeric_prov = {}
    for f in social_facts + disease_facts:
        for n, paths in (f.get("numeric_facts") or {}).items():
            numeric_prov.setdefault(n, []).extend(paths)
    # metadata/date 数字
    for k in ("report_date", "cutoff", "period_start", "period_end",
              "week_start", "week_end", "generated_at"):
        v = report_input.get(k)
        if isinstance(v, str):
            for n in _num_from_text(v):
                numeric_prov.setdefault(n, []).append(k)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            numeric_prov.setdefault(int(v), []).append(k)
    # trend_metrics / stats 数字（分析引用这些指标数字属合法）
    for fld in ("trend_metrics", "stats"):
        v = report_input.get(fld) or {}
        if isinstance(v, dict):
            for k, vv in v.items():
                if isinstance(vv, (int, float)) and not isinstance(vv, bool):
                    numeric_prov.setdefault(int(vv), []).append("%s.%s" % (fld, k))

    # source refs（去重保序）
    source_refs = []
    for f in social_facts + disease_facts:
        for s in f["source_refs"]:
            if s and s not in source_refs:
                source_refs.append(s)

    # country distribution
    country_dist = {}
    for f in social_facts:
        c = f.get("country_iso3") or f.get("country") or "unknown"
        country_dist[c] = country_dist.get(c, 0) + 1

    # 实体词表（analysis 边界检查用）
    entity_vocab = set(source_refs)
    for f in social_facts + disease_facts:
        it = None  # 无 raw location 字段时跳过；有则并入
    # 从 input 收集 location 词（weekly event_item 有 location 字段）
    for it in social_items:
        loc = it.get("location")
        if isinstance(loc, str) and loc:
            entity_vocab.add(loc)

    pack = {
        "report_id": report_input.get("report_id"),
        "report_type": rtype,
        "report_date": report_input.get("report_date"),
        "week_start": report_input.get("week_start"),
        "week_end": report_input.get("week_end"),
        "cutoff": report_input.get("cutoff"),
        "generated_at": report_input.get("generated_at"),
        "period": {
            "start": report_input.get("period_start") or report_input.get("week_start"),
            "end": report_input.get("period_end") or report_input.get("week_end"),
        },
        "country_iso3": report_input.get("country_iso3"),
        "fact_count": len(social_facts) + len(disease_facts),
        "social_fact_count": len(social_facts),
        "disease_fact_count": len(disease_facts),
        "social_facts": social_facts,
        "disease_facts": disease_facts,
        "source_refs": source_refs,
        "verification": {
            "social_gate_pass": len(social_facts),
            "disease_gate_pass": len(disease_facts),
            "single_source_count": sum(1 for f in social_facts
                                       if f["single_source_warning"]),
            "conflicting_count": sum(1 for f in social_facts if f["conflicting"]),
        },
        "uncertainties": [u for f in social_facts + disease_facts
                          for u in f["uncertainties"]],
        "importance": {f["fact_id"]: f["importance_score"]
                       for f in social_facts if f.get("importance_score") is not None},
        "selection_reasons": {f["fact_id"]: f["selection_reasons"]
                              for f in social_facts},
        "numeric_provenance": {str(n): paths
                               for n, paths in sorted(numeric_prov.items())},
        "country_distribution": country_dist,
        "trend_metrics": report_input.get("trend_metrics") or {},
        "stats": report_input.get("stats") or {},
        "entity_vocab": sorted(entity_vocab),
        "architecture": "deterministic-facts-ai-analysis-v1",
    }
    return pack


def pack_hash(fact_pack):
    """Fact Pack 确定性 hash（same input → same hash）。"""
    import hashlib
    blob = json.dumps(fact_pack, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
