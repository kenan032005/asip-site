#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fact_content.py — 事实内容投影与可展示性判定（**报告层与 AI 层共用的单一口径**）。

背景缺陷（C4-C 定位）：事实进入报告与 AI fact pack 时，`headline_zh`/`verified_summary`
恒为 None，因为
  * `build_weekly_input` 没有把 `title_cn`/`summary_cn`/`title_original`/`summary_original`
    投影进 item，而 `fact_pack._social_fact` 读的是 `item["title"]` / `item["summary"]`；
  * 疾病侧 `build_weekly_input` 读 `latest_counts` / `updates` —— 真实 schema 里**不存在**
    这两个字段（真实字段是 `confirmed_cases` / `primary_source` / `report_date` …），
    于是静默返回空壳。

本模块建立**确定性 content resolver**（绝不调用 AI、绝不伪造翻译）：

社交事实内容顺序：``title_cn`` → ``title_original``；摘要：``summary_cn`` → ``summary_original``
疾病事实名称顺序：``disease_name_zh`` → ``disease_name_cn`` → ``disease_name_en`` → ``disease_id``

全部为空 → 该事实**无内容**，不得进入 AI fact pack（也不计入 LOW_DATA 阈值）。
使用原文（original）不算「完成中文本地化」，只是在**保留真实事实内容**；
缺口由 `content_language` 记录，另计 C5 本地化债务。
"""
from __future__ import annotations

#: 社交事实标题回退顺序：(字段, 语言标记)
SOCIAL_TITLE_FALLBACK = (("title_cn", "zh"), ("title_original", "original"))
#: 社交事实摘要回退顺序
SOCIAL_SUMMARY_FALLBACK = (("summary_cn", "zh"), ("summary_original", "original"))
#: 疾病名称回退顺序
DISEASE_NAME_FALLBACK = (("disease_name_zh", "zh"), ("disease_name_cn", "zh"),
                         ("disease_name_en", "en"), ("disease_id", "id"))
#: 疾病计数类真实字段
DISEASE_COUNT_FIELDS = ("confirmed_cases", "total_cases", "probable_cases",
                        "suspected_cases", "deaths", "recoveries")
#: 疾病的「真实更新」标记字段（名称之外的可用事实）
DISEASE_UPDATE_FIELDS = ("outbreak_status", "update_type")
#: 判定 pack 事实是否「有可展示内容」时查看的文本字段
_CONTENT_TEXT_KEYS = ("headline_zh", "headline", "summary_zh", "verified_summary",
                      "fact_summary", "title_zh", "title", "fact", "detail")
#: 可用于时间窗口校验的日期字段
_TIME_KEYS = ("report_date", "event_date", "event_start_date", "as_of_date",
              "latest_report_at", "reported_at", "created_at", "updated_at")


def _clean(v):
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def first_nonempty(item, pairs):
    """按顺序取第一个非空字段；返回 (value, language, field)。"""
    for field, lang in pairs:
        v = _clean((item or {}).get(field))
        if v:
            return v, lang, field
    return None, None, None


def resolve_social_content(item):
    """社交事实内容解析（title 与 summary 分别回退，互不覆盖）。"""
    title, tlang, tfield = first_nonempty(item, SOCIAL_TITLE_FALLBACK)
    summary, slang, sfield = first_nonempty(item, SOCIAL_SUMMARY_FALLBACK)
    return {"headline": title, "headline_language": tlang, "headline_field": tfield,
            "summary": summary, "summary_language": slang, "summary_field": sfield,
            "content_language": tlang or slang or None,
            "content_source_field": tfield or sfield}


def resolve_disease_content(item):
    """疾病事实内容解析（名称 + 真实计数/更新）。"""
    name, nlang, nfield = first_nonempty(item, DISEASE_NAME_FALLBACK)
    counts = {}
    for k in DISEASE_COUNT_FIELDS:
        v = (item or {}).get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            counts[k] = v
    if not counts:      # 兼容遗留 latest_counts 嵌套形状（不编造数字）
        for k, v in ((item or {}).get("latest_counts") or {}).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                counts[k] = v
    updates = {k: (item or {}).get(k) for k in DISEASE_UPDATE_FIELDS
               if _clean((item or {}).get(k))}
    return {"name": name, "name_language": nlang, "name_field": nfield,
            "counts": counts, "updates": updates,
            "content_language": nlang,
            "content_source_field": nfield}


def disease_has_content(item):
    """§八：疾病事实必须「有名称 + 至少一个真实事实字段」才算有内容。

    只有疾病名、没有任何计数或状态更新 → 不算关键事实。
    """
    r = resolve_disease_content(item)
    return bool(r["name"]) and bool(r["counts"] or r["updates"])


def social_has_content(item):
    r = resolve_social_content(item)
    return bool(r["headline"] or r["summary"])


def fact_sources(f):
    """事实的**真实**来源引用（source_refs 优先，其次 source_ids）。不伪造。"""
    out = []
    for key in ("source_refs", "source_ids"):
        v = (f or {}).get(key)
        if isinstance(v, str):
            v = [v]
        for x in (v or []):
            s = str(x).strip()
            if s and s not in out:
                out.append(s)
    return out


def fact_countries(f):
    out = set()
    for k in ("country_iso3", "country", "country_code", "affected_countries"):
        v = (f or {}).get(k)
        if isinstance(v, str):
            v = [v]
        for x in (v or []):
            s = str(x).strip().upper()
            if s:
                out.add(s)
    return out


def has_displayable_content(f):
    """pack 事实是否有**可展示内容**（只有 id/来源不算内容）。"""
    if not isinstance(f, dict):
        return False
    for k in _CONTENT_TEXT_KEYS:
        v = f.get(k)
        if isinstance(v, str) and v.strip():
            return True
        if isinstance(v, (list, dict)) and v:
            return True
    if f.get("numeric_facts"):
        return True
    # 疾病事实：名称 + 状态/更新标记也算可展示内容
    if f.get("disease_id") and any(_clean(f.get(k)) for k in DISEASE_UPDATE_FIELDS):
        return True
    return False


def is_displayable_fact(f):
    """进入展示/统计的最小条件：有内容 **且** 有真实来源。"""
    return has_displayable_content(f) and bool(fact_sources(f))


def fact_window_state(f, report):
    """True=在窗口内 / False=在窗口外 / None=未声明日期。

    未声明日期不作为排除理由（窗口筛选是上游 fact pack builder 的职责）。
    """
    ws = (report or {}).get("week_start") or (report or {}).get("period_start")
    we = (report or {}).get("week_end") or (report or {}).get("period_end")
    if not (ws and we):
        return None
    declared = [str(f.get(k))[:10] for k in _TIME_KEYS
                if isinstance(f.get(k), str) and len(str(f.get(k))) >= 10]
    if not declared:
        return None
    return any(str(ws)[:10] <= d <= str(we)[:10] for d in declared)


#: 各 report type 下疾病事实允许的国家范围（确定性 scope 规则）
DISEASE_SCOPE_BY_TYPE = {"country_weekly": "country",
                         "africa_weekly": "region",
                         "africa_daily": "region"}


def report_countries(report):
    out = set()
    for k in ("country_iso3", "country", "country_code"):
        v = (report or {}).get(k)
        if isinstance(v, str) and v.strip():
            out.add(v.strip().upper())
    return out


def fact_eligibility(f, report, kind):
    """**唯一**的 eligibility 判定（报告层与 AI 层共用）。

    返回违反的判据列表（每条独立评估、不短路）；空列表 = 合法可进入 AI fact pack。
    kind: "SOCIAL" | "DISEASE"。
    """
    reasons = []
    if not isinstance(f, dict):
        return ["NO_CONTENT"]
    if not has_displayable_content(f):
        reasons.append("NO_CONTENT")
    if not fact_sources(f):
        reasons.append("NO_SOURCE")
    if DISEASE_SCOPE_BY_TYPE.get((report or {}).get("report_type")) == "country":
        # §十一 Country Weekly 国家隔离：声明了国别就必须是报告国；
        # regional / 他国不因“区域”身份默认放行（无明确产品规则允许）。
        declared = fact_countries(f)
        rc = report_countries(report)
        if declared and rc and not (declared & rc):
            reasons.append("SCOPE")
    w = fact_window_state(f, report)
    if w is False:
        reasons.append("OUT_OF_WINDOW")
    return reasons


def is_ai_eligible(f, report, kind):
    return not fact_eligibility(f, report, kind)


def report_ai_eligible_fact_count(fact_pack, report):
    """报告里**可供 AI 使用**的事实数（0 → 该报告应当被重新分类为 LOW_DATA）。"""
    n = 0
    for kind, key in (("SOCIAL", "social_facts"), ("DISEASE", "disease_facts")):
        for f in (fact_pack.get(key) or []):
            if is_ai_eligible(f, report, kind):
                n += 1
    return n
