#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""content_eligibility.py — 领导/情报视图的统一内容准入（C5-A §十六–§十七）。

历史债务：Homepage Fact Pack 曾把**纯体育**项目当成安全情报。

统一契约（复用既有 `factory.report_eligibility`，不另造第二套判定）：
  * 纯体育（仅命中题材词，且无任何安全语义）→ **排除**
  * 命中 terror / riot / stampede / public disorder / security incident 等安全语义的体育场景
    → **保留**（不得因为出现 "football" 就删掉安全事件）

适用范围：Homepage / Country intelligence / Reports / Executive views（`leadership` 层）。
News Stream 允许更宽内容（§十七），不在本过滤范围。
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from scripts.report import factory as F  # noqa: E402

#: 领导层使用的题材排除词（与 factory 保持一致，只做导出便于审计）
LEADERSHIP_EXCLUDED_TOPICS = F.REPORT_EXCLUDED_TOPICS
#: 安全豁免词（命中即保留）
LEADERSHIP_SECURITY_EXEMPT = F.REPORT_SECURITY_EXEMPT


def leadership_content_eligibility(text, event_type=None):
    """领导层内容准入：返回 (eligible, reason)。复用 factory 的单一判定。"""
    return F.report_eligibility(text, event_type)


def is_leadership_eligible(text, event_type=None):
    return leadership_content_eligibility(text, event_type)[0]


def _blob(item, text_keys):
    parts = []
    for k in text_keys:
        v = (item or {}).get(k)
        if isinstance(v, str):
            parts.append(v)
    parts.append(str((item or {}).get("event_type") or ""))
    return " ".join(parts)


def filter_leadership_items(items, text_keys=("title_cn", "title_original", "headline_zh",
                                             "headline_en", "summary_cn", "summary_original")):
    """返回 (kept, excluded_with_reason)。排除项带原因，便于审计与 UI 提示。"""
    kept, excluded = [], []
    for it in (items or []):
        ok, reason = leadership_content_eligibility(_blob(it, text_keys),
                                                   (it or {}).get("event_type"))
        if ok:
            kept.append(it)
        else:
            excluded.append({"item": it, "reason": reason})
    return kept, excluded


def audit_leadership_views(root, views=("country_snapshots.json", "master_events.json",
                                       "ai_intelligence.json")):
    """§十六 审计：领导视图里是否仍有**纯体育**项目（按各自真实的列表键）。"""
    import io
    import json
    out = {"scanned_views": [], "PURE_SPORTS_IN_LEADERSHIP_VIEWS": 0, "offenders": []}
    vd = os.path.join(str(root), "data", "views")
    for name in views:
        p = os.path.join(vd, name)
        if not os.path.exists(p):
            continue
        doc = json.load(io.open(p, encoding="utf-8"))
        rows = []
        if isinstance(doc, dict):
            for k in ("snapshots", "items", "events", "master_events", "cards", "rows"):
                if isinstance(doc.get(k), list):
                    rows = doc[k]
                    break
        elif isinstance(doc, list):
            rows = doc
        # 国家快照：逐国检查 latest_major_event
        if name == "country_snapshots.json":
            cand = [dict(s.get("latest_major_event") or {}, country_iso3=s.get("iso3"))
                    for s in rows if isinstance(s, dict) and s.get("latest_major_event")]
        else:
            cand = [r for r in rows if isinstance(r, dict)]
        for it in cand:
            ok, reason = leadership_content_eligibility(_blob(it, ()), it.get("event_type"))
            if not ok:
                out["offenders"].append({"view": name, "reason": reason,
                                         "title": (it.get("title") or it.get("headline_zh")
                                                   or it.get("title_cn"))})
        out["scanned_views"].append({"view": name, "rows": len(cand)})
    out["PURE_SPORTS_IN_LEADERSHIP_VIEWS"] = len(out["offenders"])
    return out
