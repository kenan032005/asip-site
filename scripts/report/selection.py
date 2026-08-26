#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7A §六-§九/§二十七 — 确定性选材引擎。

- eligibility（§六）：Public/eligible、非 quarantine、非 review_before_activation、
  country 有效或 regional、≥1 真实 source；rejected 不入；conflicting 标注进入。
- importance score（§七）：report_importance_score 0-100，权重配置化，不用 AI。
- low-value suppression（§八）：security_relevance=none 原则，除非触发豁免信号。
- 数量控制（§九）：security 8-15 / disease 2-5，少则短，不填充。
- 可解释（§二十七）：每个入选 item 带 selection_reasons；抑制高分边界项记录
  suppression_reason。
- Temporal Window（Stage7B §二）：≤24h 新事件 eligible；24-72h 仅 developing/
  ongoing/有变化 eligible；72h-7d 重大持续仅 watch；>7d 不进正文。
"""

from datetime import datetime

from scripts.report.config import (
    IMPORTANCE_WEIGHTS, LOW_VALUE_KEYWORDS, LOW_VALUE_EXEMPT_SIGNALS,
    DAILY_SECURITY_MIN, DAILY_SECURITY_MAX, DAILY_DISEASE_MIN, DAILY_DISEASE_MAX,
    EXEC_SUMMARY_MAX, REJECTED_STATUSES,
)

# 高危事件类型（§七 terrorism/armed conflict/政变/大规模骚乱）
HIGH_IMPACT_TYPES = {
    "terrorist_attack", "armed_conflict", "armed_attack", "coup_attempt",
    "mass_protest", "civil_unrest", "coup",
}
# 板块路由（§四 A-I）
CATEGORY_BY_TYPE = {
    "terrorist_attack": "terrorism",
    "armed_attack": "terrorism",
    "armed_conflict": "security",
    "military_operation": "security",
    "civil_unrest": "political",
    "mass_protest": "political",
    "coup": "political",
    "coup_attempt": "political",
    "strike": "political",
    "major_crime": "security",
    "kidnapping": "security",
    "border_incident": "cross_border",
    "cross_border": "cross_border",
    "displacement": "cross_border",
    "natural_disaster": "security",
    "public_health": "public_health",
}
# 交叉板块关键词（title/type 命中 → cross_border 板块）
CROSS_BORDER_KEYWORDS = ("border", "cross-border", "refugee", "displacement",
                         "跨境", "边境", "难民", "流离失所")

# 数字解析
def _num(v):
    if v is None or v == "":
        return None
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _norm_vstatus(v):
    """verification_status 归一化：verified/probable/single_source/conflicting/
    unverified/rejected；旧值 partial → single_source。"""
    v = (v or "").strip().lower()
    if v in REJECTED_STATUSES:
        return "rejected"
    if v == "verified":
        return "verified"
    if v in ("probable",):
        return "probable"
    if v in ("single_source", "partial", "official_unverified", "unverified"):
        return "single_source"
    if v == "conflicting":
        return "conflicting"
    return "unverified"


def is_low_value(text):
    """§八 低价值判定：命中关键词且无豁免信号。"""
    t = (text or "").lower()
    if not t:
        return False
    hit = any(k in t for k in LOW_VALUE_KEYWORDS)
    if not hit:
        return False
    exempt = any(s in t for s in LOW_VALUE_EXEMPT_SIGNALS)
    return not exempt


def _country_iso3(ev, iso2to3=None):
    """country（中文/ISO2/ISO3/英文）→ ISO3 或 None。"""
    c = ev.get("country_iso3") or ev.get("event_primary_country") or ev.get("country")
    if not c:
        return None
    c = str(c).strip()
    up = c.upper()
    if iso2to3 and up in iso2to3:
        return iso2to3[up]
    if up in {"TCD", "NER", "SSD", "BEN", "ETH", "SDN", "NGA", "KEN", "COD",
              "MLI", "BFA", "CMR", "CAF", "SOM", "ERI", "DJI", "LBY", "TZA",
              "UGA", "RWA", "BDI", "MOZ", "ZMB", "ZWE", "MWI", "AGO", "COG",
              "GAB", "GNQ", "STP", "SEN", "GMB", "GNB", "GIN", "SLE", "LBR",
              "CIV", "GHA", "TGO", "BEN", "NGA", "MRT", "MAR", "DZA", "TUN",
              "EGY", "SWZ", "LSO", "BWA", "NAM", "ZAF", "MDG", "COM", "SYC",
              "MUS", "CPV", "ESH"}:
        return up
    return c if len(c) == 3 else None


def _eligibility(ev, quarantine_ids=None, iso2to3=None):
    """§六 eligibility 判定。返回 (ok, reason)。"""
    q = set(quarantine_ids or [])
    eid = ev.get("event_id") or ev.get("master_event_id")
    if eid and eid in q:
        return False, "quarantine"
    if ev.get("processing_status") in REJECTED_STATUSES:
        return False, "rejected"
    if ev.get("review_before_activation") or ev.get("activation_status") in ("review", "review_before_activation"):
        return False, "review_before_activation"
    if not _country_iso3(ev, iso2to3) and not ev.get("regional"):
        return False, "no_valid_country"
    nsrc = ev.get("source_count") or (1 if (ev.get("source_name") or ev.get("source_id")) else 0)
    if nsrc < 1:
        return False, "no_real_source"
    return True, None


def importance_score(ev, priority_countries=None, prev_changed=False,
                     casualties=None, extra_reasons=None):
    """§七 report_importance_score 0-100（确定性，配置化权重）。"""
    W = IMPORTANCE_WEIGHTS
    score = 0
    reasons = []
    ev_type = (ev.get("event_type") or "").lower()
    title = " ".join([str(ev.get("title_original") or ev.get("title") or ""),
                      str(ev.get("title_cn") or "")]).lower()

    # 重大伤亡（§七 顶部）
    deaths = _num(casualties if casualties is not None
                  else ev.get("deaths") or ev.get("casualties"))
    severity = ev.get("event_severity")
    if deaths is not None and deaths >= 10 or severity in ("高", "极高"):
        score += W["major_casualties"]
        reasons.append("major_casualties")

    # terrorism / armed attack / conflict
    if ev_type in ("terrorist_attack", "armed_attack", "armed_conflict",
                   "military_operation"):
        score += W["terrorism_armed_conflict"]
        reasons.append("terrorism_armed_conflict")

    # 政变/重大政治危机/大规模骚乱
    if ev_type in ("coup", "coup_attempt", "mass_protest", "civil_unrest"):
        score += W["coup_political_crisis"]
        reasons.append("coup_political_crisis")

    # 跨境影响（§七/板块交叉）
    if ev_type in ("border_incident", "cross_border", "displacement") or \
            any(k in title for k in CROSS_BORDER_KEYWORDS):
        score += W["cross_border"]
        reasons.append("cross_border")

    # 官方重大声明/紧急措施
    if ev.get("official_declaration") or ev.get("official_emergency"):
        score += W["official_statement_emergency"]
        reasons.append("official_statement_emergency")

    # verified / strong multi-source
    vs = _norm_vstatus(ev.get("verification_status"))
    sc = ev.get("source_count") or (1 if (ev.get("source_name") or ev.get("source_id")) else 0)
    if vs == "verified" or (vs in ("verified", "probable") and sc >= 2):
        score += W["verified_multi_source"]
        reasons.append("verified")

    # 事件正在快速发展（timeline ongoing / 高 severity）
    tl_status = ev.get("timeline_status")
    if tl_status in ("developing", "ongoing"):
        score += W["developing"]
        reasons.append("developing")

    # 较上日报显著变化（§七 / §十一）
    if prev_changed:
        score += W["significant_change"]
        reasons.append("significant_change")

    # priority country
    iso3 = _country_iso3(ev)
    if iso3 and priority_countries and iso3 in set(priority_countries):
        score += W["priority_country"]
        reasons.append("priority_country")

    # 重大疾病新暴发/跨境传播
    if ev_type == "public_health":
        score += W["disease_new_or_cross_border"]
        reasons.append("disease_new_or_cross_border")

    for r in (extra_reasons or []):
        if r not in reasons:
            reasons.append(r)
    return min(score, 100), reasons


def _in_prev(ev, prev):
    """§十一 是否已在上日报出现：event_id 或 master_event_id 任一命中。"""
    return (ev.get("event_id") in prev) or (ev.get("master_event_id") in prev)


def _age_days(published_at, cutoff_dt):
    """相对 cutoff 的年龄天数；无时间 → None。"""
    if not published_at:
        return None
    try:
        d = datetime.strptime(str(published_at)[:10], "%Y-%m-%d")
    except ValueError:
        return None
    return (cutoff_dt - d).days


def temporal_bucket(ev, cutoff_dt):
    """Stage7B §二 时间窗语义。

    返回 (bucket, note)：
      new_24h | ongoing_72h | trend_7d | outside_7d | no_time
    对 disease item 用 latest_report_at 作为时间。
    """
    if not cutoff_dt:
        return None, "no_window"
    t = ev.get("latest_report_at") or ev.get("published_at") or ev.get("event_time")
    age = _age_days(t, cutoff_dt)
    if age is None:
        return "no_time", None
    if age <= 1:
        return "new_24h", None
    if age <= 3:
        return "ongoing_72h", None
    if age <= 7:
        return "trend_7d", None
    return "outside_7d", "超过7天，不得进入日报正文（极少数长期危机仅可 watch context）"


def select_daily(events, quarantine_ids=None, priority_countries=None,
                 prev_event_ids=None, iso2to3=None, security_range=None,
                 disease_range=None, cutoff=None, temporal=True):
    """§六-§九 + §二 Temporal Window Africa Daily selection。

    cutoff: 报告期截止（ISO 日期/时间）；开启 temporal 后按 §二 规则过滤。
    events: list of dict（Social events + Disease items 按 is_disease 区分）。
    返回 (selected, stats, suppressed_log)。
    """
    security_range = security_range or (DAILY_SECURITY_MIN, DAILY_SECURITY_MAX)
    disease_range = disease_range or (DAILY_DISEASE_MIN, DAILY_DISEASE_MAX)
    q = set(quarantine_ids or [])
    prev = set(prev_event_ids or [])
    cutoff_dt = None
    if cutoff:
        try:
            cutoff_dt = datetime.strptime(str(cutoff)[:10], "%Y-%m-%d")
        except ValueError:
            cutoff_dt = None
    stats = {"eligible_events": 0, "selected_security_events": 0,
             "selected_disease_events": 0, "suppressed_low_value": 0,
             "conflicting_events": 0, "single_source_events": 0,
             "change_items": 0, "watch_items": 0,
             "social_new_24h": 0, "social_ongoing_72h": 0,
             "social_trend_watch_7d": 0, "social_outside_7d": 0,
             "disease_new_24h": 0, "disease_significant_7d": 0,
             "disease_active_watch": 0, "no_time": 0}
    suppressed_log = []

    eligible, security, disease = [], [], []
    watch_7d = []   # 72h-7d 重大持续（仅 watch，§二 C）
    for ev in events:
        ok, reason = _eligibility(ev, q, iso2to3)
        if not ok:
            continue
        stats["eligible_events"] += 1
        vs = _norm_vstatus(ev.get("verification_status"))
        if vs == "conflicting":
            stats["conflicting_events"] += 1
            ev = dict(ev, conflicting=True)
        if vs == "single_source":
            stats["single_source_events"] += 1
            ev = dict(ev, single_source_warning=True)
        is_dis = ev.get("is_disease")
        # ── §二 Temporal Window ──
        if temporal and cutoff_dt:
            bucket, note = temporal_bucket(ev, cutoff_dt)
            ev = dict(ev, temporal_bucket=bucket, temporal_note=note)
            if is_dis:
                if bucket == "new_24h":
                    stats["disease_new_24h"] += 1
                elif bucket in ("ongoing_72h", "trend_7d"):
                    stats["disease_significant_7d"] += 1
                    if bucket == "trend_7d" and not ev.get("change_type"):
                        stats["disease_active_watch"] += 1
                        if _in_prev(ev, prev):
                            continue   # 已报告且仅 watch → 不重复
                        watch_7d.append(dict(ev, importance_score=0))
                        continue
                else:
                    stats["disease_active_watch"] += 1
                    continue   # >7d 或 no_time → 不进正文
            else:
                if bucket == "new_24h":
                    stats["social_new_24h"] += 1
                elif bucket == "ongoing_72h":
                    stats["social_ongoing_72h"] += 1
                    # §二 B：24-72h 仅 developing/ongoing/显著变化 eligible
                    if ev.get("timeline_status") not in ("developing", "ongoing") \
                            and not ev.get("change_type"):
                        continue
                elif bucket == "trend_7d":
                    stats["social_trend_watch_7d"] += 1
                    # §二 C：72h-7d 仅重大持续 → watch 候选（不进正文）
                    watch_7d.append(dict(ev, importance_score=0,
                                         watch_context=True))
                    continue
                else:
                    stats["social_outside_7d"] += 1
                    continue   # §二 D：>7d 不进正文
        else:
            if ev.get("published_at") is None and not is_dis:
                stats["no_time"] += 1

        cat = ev.get("category") or CATEGORY_BY_TYPE.get(
            (ev.get("event_type") or "").lower(), "security")
        if is_dis:
            # §十五 普通无变化疫情不每天重复（已报告且无 change → 抑制）
            if _in_prev(ev, prev) and not ev.get("change_type"):
                continue
            disease.append(ev)
        else:
            # §八 low-value 抑制
            blob = " ".join([str(ev.get("title_original") or ev.get("title") or ""),
                             str(ev.get("summary_cn") or "")])
            if is_low_value(blob):
                stats["suppressed_low_value"] += 1
                suppressed_log.append({"event_id": ev.get("event_id"),
                                       "suppression_reason": "low_value_content"})
                continue
            security.append(ev)

    # §十一/§十七 duplicate/master 只算一次（按 master_event_id 去重，保留首条）
    seen_master = set()
    sec_dedup = []
    for ev in security:
        mk = ev.get("master_event_id")
        if mk and mk in seen_master:
            continue
        if mk:
            seen_master.add(mk)
        sec_dedup.append(ev)
    security = sec_dedup

    # 打分 + 排序（§七 确定性）
    def scored(ev):
        changed = not _in_prev(ev, prev)
        s, reasons = importance_score(ev, priority_countries, prev_changed=changed)
        return s, reasons

    sec_scored = [(ev, *scored(ev)) for ev in security]
    dis_scored = [(ev, *scored(ev)) for ev in disease]

    # §九 数量控制：security 8-15 / disease 2-5（少则短，不填充）
    sec_scored.sort(key=lambda x: -x[1])
    dis_scored.sort(key=lambda x: -x[1])

    sec_selected = [dict(ev, importance_score=s, selection_reasons=r)
                    for ev, s, r in sec_scored[:security_range[1]]]
    dis_selected = [dict(ev, importance_score=s, selection_reasons=r)
                    for ev, s, r in dis_scored[:disease_range[1]]]
    # 不因 range 下限填充低价值项（§九）
    stats["selected_security_events"] = len(sec_selected)
    stats["selected_disease_events"] = len(dis_selected)

    # Executive Summary（§五：最高价值 5-8 项）
    exec_cand = sorted(sec_selected + dis_selected,
                       key=lambda x: -x["importance_score"])
    exec_summary = exec_cand[:min(EXEC_SUMMARY_MAX, len(exec_cand))]
    # Key Changes（§十一：有变化的新事件/update）
    changes = [dict(ev, importance_score=ev["importance_score"],
                    selection_reasons=ev["selection_reasons"])
               for ev in sec_selected + dis_selected
               if not _in_prev(ev, prev)]
    stats["change_items"] = len(changes)
    # Watch Items（§十一：已报告但持续关注）
    watch = [dict(ev, importance_score=ev["importance_score"],
                  selection_reasons=ev["selection_reasons"])
             for ev in sec_selected + dis_selected
             if _in_prev(ev, prev)]
    stats["watch_items"] = len(watch)

    return {"executive_summary": exec_summary, "security": sec_selected,
            "disease": dis_selected, "changes": changes, "watch": watch,
            "watch_7d": watch_7d}, stats, suppressed_log
