#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8A — PUBLIC-SAFE FRONTEND VIEW BUILDER V1（§二十四-§三十）。

把 Stage1-7 已就绪的后台能力，转换成最小化、公开安全的前端视图契约，
供前端页面消费。前端绝不直接读 data/runtime/。

输入（只读）：
  - data/events.json（legacy 公开事件，build_site 白名单内）
  - data/public/published_events.json（当前公开事件）
  - data/countries.json / data/risk-levels.json / data/status.json
  - data/runtime/timeline/social_timelines.json + disease_timelines.json（Stage6B）
  - data/runtime/clustering/clusters-v2.json（Stage6A master 元数据）
  - data/runtime/reports/{daily_input,weekly_input,brief_candidates}/（Stage7A）
  - data/runtime/report_preview/（Stage7B mock 报告产物）
  - data/intelligence/africa/{catalog_metrics,entities}.json（知识库摘要）

输出（开发阶段，public-safe，不直接进 production）：
  data/runtime/frontend_preview_public/
    site_overview.json        §二十六
    master_events.json        §二十七
    event_timelines.json      §二十八
    country_snapshots.json    §十二/§十三
    disease_outbreaks.json    §十五/§十六/§二十九
    report_index.json         §三十
    knowledge_summary.json    §二十三

规则：
  - PUBLIC ELIGIBLE only；内部 merge score / review pair / raw body / feature
    scores / candidate ids 一律不带出。
  - unknown = null，绝不 null→0（§二十九）。
  - 不重新计算 verification / same-event / disease 数字；只消费既有确定性层。
  - 不使用 AI；country 归属复用 Stage6 既有结果，不重新猜测。

用法：
  python scripts/frontend/build_frontend_views.py [--out DIR]
"""
import os
import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DEFAULT = ROOT / "data" / "runtime" / "frontend_preview_public"

BJ = timezone(timedelta(hours=8))

# ── ISO3 → 中文名（显示映射；优先用 countries.json en 反查，缺失用此表）──
ISO3_CN = {
    "TCD": "乍得", "SDN": "苏丹", "SSD": "南苏丹", "NER": "尼日尔", "BEN": "贝宁",
    "ETH": "埃塞俄比亚", "NGA": "尼日利亚", "MLI": "马里", "BFA": "布基纳法索",
    "CMR": "喀麦隆", "CAF": "中非共和国", "TGO": "多哥", "CIV": "科特迪瓦",
    "GHA": "加纳", "SEN": "塞内加尔", "MRT": "毛里塔尼亚", "GIN": "几内亚",
    "SLE": "塞拉利昂", "LBR": "利比里亚", "GMB": "冈比亚", "GNB": "几内亚比绍",
    "CPV": "佛得角", "COD": "刚果（金）", "COG": "刚果（布）", "GAB": "加蓬",
    "ERI": "厄立特里亚", "DJI": "吉布提", "SOM": "索马里", "KEN": "肯尼亚",
    "UGA": "乌干达", "RWA": "卢旺达", "BDI": "布隆迪", "TZA": "坦桑尼亚",
    "MWI": "马拉维", "MOZ": "莫桑比克", "ZMB": "赞比亚", "ZWE": "津巴布韦",
    "AGO": "安哥拉", "NAM": "纳米比亚", "BWA": "博茨瓦纳", "ZAF": "南非",
    "LSO": "莱索托", "SWZ": "斯威士兰", "MDG": "马达加斯加", "EGY": "埃及",
    "LBY": "利比亚", "TUN": "突尼斯", "DZA": "阿尔及利亚", "MAR": "摩洛哥",
    "SSD": "南苏丹",
}
ISO3_EN = {
    "TCD": "Chad", "SDN": "Sudan", "SSD": "South Sudan", "NER": "Niger",
    "BEN": "Benin", "ETH": "Ethiopia", "NGA": "Nigeria", "MLI": "Mali",
    "BFA": "Burkina Faso", "CMR": "Cameroon", "CAF": "Central African Republic",
    "TGO": "Togo", "CIV": "Côte d'Ivoire", "GHA": "Ghana", "SEN": "Senegal",
    "MRT": "Mauritania", "GIN": "Guinea", "SLE": "Sierra Leone", "LBR": "Liberia",
    "GMB": "Gambia", "GNB": "Guinea-Bissau", "CPV": "Cabo Verde",
    "COD": "DR Congo", "COG": "Congo", "GAB": "Gabon", "ERI": "Eritrea",
    "DJI": "Djibouti", "SOM": "Somalia", "KEN": "Kenya", "UGA": "Uganda",
    "RWA": "Rwanda", "BDI": "Burundi", "TZA": "Tanzania", "MWI": "Malawi",
    "MOZ": "Mozambique", "ZMB": "Zambia", "ZWE": "Zimbabwe", "AGO": "Angola",
    "NAM": "Namibia", "BWA": "Botswana", "ZAF": "South Africa", "LSO": "Lesotho",
    "SWZ": "Eswatini", "MDG": "Madagascar", "EGY": "Egypt", "LBY": "Libya",
    "TUN": "Tunisia", "DZA": "Algeria", "MAR": "Morocco",
}

EVENT_TYPE_CN = {
    "armed_conflict": "武装冲突", "terrorist_attack": "恐怖袭击",
    "military_operation": "军事行动", "political_crisis": "政治危机",
    "election_security": "选举安全", "protest": "抗议示威", "strike": "罢工",
    "civil_unrest": "社会动荡", "kidnapping": "绑架劫持",
    "serious_crime": "严重刑事犯罪", "communal_conflict": "社区及部族冲突",
    "border_security": "边境安全", "transport_disruption": "交通中断",
    "infrastructure_security": "基础设施安全", "natural_disaster": "自然灾害",
    "public_health": "传染病及公共卫生", "china_related": "涉华安全事件",
    "foreign_national_security": "外籍人员安全", "policy_security": "安全政策法规",
    "other_security": "其他安全事件",
}

UPDATE_TYPE_CN = {
    "initial_report": "首次报道", "new_event": "首次报道",
    "casualty_increase": "伤亡增加", "injury_increase": "受伤增加",
    "official_confirmation": "官方确认", "actor_attribution_change": "归因变化",
    "location_expansion": "地点扩展", "status_change": "状态变化",
    "correction": "更正", "conflict_detected": "来源冲突", "closed": "事件结束",
    "new_outbreak": "新暴发", "case_increase": "病例增加",
    "mortality_increase": "死亡增加", "geographic_spread": "疫情扩散",
    "final_update": "最终更新",
}

DISEASE_CN = {
    "marburg": "马尔堡出血热", "cholera": "霍乱", "measles": "麻疹",
    "meningitis": "脑膜炎", "mpox": "猴痘", "ebola": "埃博拉出血热",
    "dengue": "登革热", "malaria": "疟疾", "lassa": "拉沙热",
    "polio": "脊髓灰质炎", "yellow_fever": "黄热病", "diphtheria": "白喉",
}

OUTBREAK_STATUS_CN = {
    "active": "活跃", "developing": "发展", "increasing": "上升",
    "geographic_spread": "扩散", "declining": "下降", "contained": "已控制",
    "monitoring": "监测", "closed": "已结束", "final": "已结束",
}

VERIFY_CN = {
    "verified": "已核实", "probable": "较可信", "partial": "部分核实",
    "single_source": "单一来源", "conflicting": "信息存在冲突",
    "pending": "待进一步核实", "unverified": "未经证实",
}

# 安全可输出的字段白名单（§二十七 最小化）
_MASTER_FIELDS = ("master_event_id", "headline_zh", "headline_en", "country_iso3",
                  "country_cn", "location", "event_type", "event_type_cn",
                  "event_time", "latest_update_at", "verification_status",
                  "verification_cn", "source_count", "independent_source_count",
                  "fact_summary", "change_type", "change_type_cn",
                  "update_count", "timeline_status", "uncertainties",
                  "conflict_flags")
_TIMELINE_FIELDS = ("master_event_id", "updates")
_TL_UPDATE_FIELDS = ("time", "update_type", "update_type_cn", "fact_change",
                     "source_ref", "verification_status")
_COUNTRY_FIELDS = ("country_cn", "country_en", "iso3", "region",
                   "baseline_risk", "baseline_risk_level", "events_24h",
                   "events_7d", "latest_major_event", "active_outbreaks",
                   "last_updated")
_DISEASE_FIELDS = ("outbreak_id", "disease_id", "disease_name_cn",
                   "country_iso3", "country_cn", "status", "status_cn",
                   "latest_counts", "delta", "latest_change",
                   "latest_report_at", "verification_status", "source_count",
                   "independent_source_count", "uncertainties",
                   "affected_admin1")
_REPORT_FIELDS = ("report_id", "type", "type_cn", "title", "country_iso3",
                  "period_start", "period_end", "status", "status_cn",
                  "published_at", "path", "is_mock")


def load_json(p, default=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


def bj_iso(dt=None):
    dt = dt or datetime.now(BJ)
    return dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def bj_fmt(s):
    """ISO → 'YYYY-MM-DD HH:mm'（UTC 转北京时间），失败返回原串。"""
    if not s:
        return None
    s = str(s).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(BJ)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(s)[:16]


def build_country_indexes(countries):
    """cn→iso3 / iso3→cn / iso3→en / iso3→risk。"""
    cn2iso, iso2cn, iso2en, iso2risk = {}, {}, {}, {}
    for c in countries:
        cn, en, lvl = c.get("cn"), c.get("en"), c.get("risk_level")
        iso = None
        for k, v in ISO3_EN.items():
            if v.lower() == (en or "").lower():
                iso = k
                break
        if cn:
            cn2iso[cn] = iso
        if iso:
            iso2cn[iso] = cn
            iso2en[iso] = en
            iso2risk[iso] = lvl
    # 补齐静态映射中缺失的
    for iso, cn in ISO3_CN.items():
        iso2cn.setdefault(iso, cn)
    for iso, en in ISO3_EN.items():
        iso2en.setdefault(iso, en)
    return cn2iso, iso2cn, iso2en, iso2risk


def norm_vstatus(v, source_count=0, independent=0):
    """Stage5 状态归一化：single/conflicting 优先；其余按原值。"""
    v = (v or "").lower()
    if v in ("conflicting", "conflict"):
        return "conflicting"
    if v in ("single_source", "single"):
        return "single_source"
    if v in ("verified", "probable", "partial", "pending", "unverified"):
        return v
    if source_count and independent and source_count > 1 and independent > 1:
        return "verified"
    return "probable"


def build_site_overview(events, pub_events, countries, status, disease_tls,
                        daily_input, iso2cn):
    now = bj_iso()
    all_ev = list(events) + list(pub_events)
    times = [e.get("published_time") or e.get("event_time") for e in all_ev if e.get("published_time") or e.get("event_time")]
    cutoff = None
    if times:
        try:
            cutoff = datetime.fromisoformat(max(times).replace("Z", "+00:00"))
        except Exception:
            cutoff = None

    def age_days(ev):
        t = ev.get("published_time") or ev.get("event_time")
        if not t or not cutoff:
            return None
        try:
            dt = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (cutoff - dt).total_seconds() / 86400.0
        except Exception:
            return None

    ev24 = [e for e in all_ev if (age_days(e) is not None and age_days(e) <= 1)]
    ev72 = [e for e in all_ev if (age_days(e) is not None and 1 < age_days(e) <= 3)]
    # verification 统计（events.json + published）
    vc = {}
    for e in all_ev:
        vs = norm_vstatus(e.get("verification_status"),
                          e.get("source_count"), e.get("independent_source_count"))
        vc[vs] = vc.get(vs, 0) + 1
    active_out = [t for t in disease_tls if (t.get("outbreak_status") or "").lower()
                  in ("active", "developing", "increasing", "geographic_spread",
                      "monitoring")]
    priority = [c for c in countries if (c.get("tier") in ("extreme", "high")
                                         or (c.get("risk_level") or 0) >= 3)]
    data_status = "current"
    st_status = (status.get("status") or "").lower()
    if st_status in ("degraded", "error"):
        data_status = "degraded"
    elif st_status in ("delayed", "partial"):
        data_status = "delayed"
    latest_daily = None
    if daily_input:
        latest_daily = {
            "report_id": daily_input.get("report_id"),
            "generated_at": daily_input.get("generated_at"),
            "status": "development_sample",
            "status_cn": "开发样例",
        }
    return {
        "generated_at": now,
        "data_status": data_status,
        "data_status_text": {"current": "数据正常", "delayed": "数据更新存在延迟",
                             "degraded": "数据质量降级"}[data_status],
        "latest_data_time_bj": bj_fmt(status.get("last_update_bj")
                                      or status.get("generated_at_bj")
                                      or (cutoff.isoformat() if cutoff else None)),
        "kpis": {
            "events_24h": len(ev24),
            "events_72h_ongoing": len(ev72),
            "priority_country_count": len(priority),
            "priority_countries": [{"cn": c.get("cn"),
                                    "risk_level": c.get("risk_level")}
                                   for c in priority],
            "verified_probable_count": vc.get("verified", 0) + vc.get("probable", 0),
            "active_outbreaks": len(active_out),
            "latest_daily": latest_daily,
        },
        "verification_summary": vc,
        "source_freshness": {"data_status": data_status},
    }


def build_master_events(social_tls, clusters, cn2iso, iso2cn, iso2en):
    """§二十七：master event 视图（同一现实事件只出现一次）。"""
    cluster_meta = {}
    for cl in clusters:
        cluster_meta[cl.get("master_event_id")] = cl
    out = []
    for tl in social_tls:
        mid = tl.get("master_event_id")
        cs = tl.get("current_state") or {}
        iso = cs.get("country") or (cluster_meta.get(mid) or {}).get("primary_country_iso3")
        loc = cs.get("location")
        etype = cs.get("event_type") or (cluster_meta.get(mid) or {}).get("event_type")
        updates = tl.get("updates") or []
        latest = updates[-1] if updates else {}
        # headline：优先最近一次有 evidence title 的更新；否则确定性拼接
        headline_en = None
        for u in reversed(updates):
            t = (u.get("evidence") or {}).get("title")
            if t:
                headline_en = t
                break
        country_cn = iso2cn.get(iso) if iso else None
        headline_zh = " · ".join(filter(None, [country_cn,
                                                EVENT_TYPE_CN.get(etype or "")]))
        if not headline_zh:
            headline_zh = "非洲地区安全事件（ID %s）" % (mid or "")[:8]
        ver = norm_vstatus(tl.get("verification_status"),
                           tl.get("source_count"), tl.get("independent_source_count"))
        first = bj_fmt(tl.get("first_reported_at"))
        last = bj_fmt(tl.get("latest_update_at"))
        fact = "首次报道：%s；最近更新：%s（%s）；来源 %s 个 / 独立来源 %s 个。" % (
            first or "—", last or "—",
            UPDATE_TYPE_CN.get((latest.get("update_type") or "").lower(), "状态更新"),
            tl.get("source_count") if tl.get("source_count") is not None else "—",
            tl.get("independent_source_count") if tl.get("independent_source_count") is not None else "—")
        change = (latest.get("update_type") or "").lower()
        out.append({
            "master_event_id": mid,
            "headline_zh": headline_zh,
            "headline_en": headline_en,
            "country_iso3": iso,
            "country_cn": country_cn,
            "location": loc,
            "event_type": etype,
            "event_type_cn": EVENT_TYPE_CN.get(etype or ""),
            "event_time": bj_fmt(tl.get("first_reported_at")),
            "latest_update_at": last,
            "verification_status": ver,
            "verification_cn": VERIFY_CN.get(ver, ver),
            "source_count": tl.get("source_count"),
            "independent_source_count": tl.get("independent_source_count"),
            "fact_summary": fact,
            "change_type": change,
            "change_type_cn": UPDATE_TYPE_CN.get(change, "状态更新"),
            "update_count": len(updates),
            "timeline_status": tl.get("timeline_status"),
            "uncertainties": [u for u in (tl.get("uncertainties") or [])][:5],
            "conflict_flags": (tl.get("conflict_flags") or [])[:5],
        })
    out.sort(key=lambda x: (x["latest_update_at"] or ""), reverse=True)
    return {"generated_at": bj_iso(), "count": len(out), "events": out}


def build_event_timelines(social_tls):
    """§二十八：只输出用户需要的时间/类型/变化/来源。"""
    tl_map = {}
    for tl in social_tls:
        updates = []
        for u in tl.get("updates") or []:
            ev = u.get("evidence") or {}
            updates.append({
                "time": bj_fmt(u.get("effective_at") or u.get("event_time")
                               or u.get("published_at")),
                "update_type": (u.get("update_type") or "").lower(),
                "update_type_cn": UPDATE_TYPE_CN.get(
                    (u.get("update_type") or "").lower(), "状态更新"),
                "fact_change": ", ".join(u.get("changed_fields") or []) or None,
                "source_ref": {"source_id": u.get("source_id"),
                               "source_name": u.get("source_group"),
                               "title": ev.get("title"),
                               "url": ev.get("url")},
                "verification_status": norm_vstatus(u.get("verification_status")),
            })
        if updates:
            tl_map[tl.get("master_event_id")] = updates
    return {"generated_at": bj_iso(), "count": len(tl_map), "timelines": tl_map}


def build_country_snapshots(countries, events, pub_events, disease_tls,
                            cn2iso, iso2cn, iso2en, iso2risk):
    """§十二：国家卡片（24h/7d 事件数、最新重大事件、活跃疫情；未知 → null）。"""
    cutoff = None
    times = [e.get("published_time") or e.get("event_time")
             for e in list(events) + list(pub_events)
             if e.get("published_time") or e.get("event_time")]
    if times:
        try:
            cutoff = datetime.fromisoformat(max(times).replace("Z", "+00:00"))
        except Exception:
            cutoff = None

    def age_days(ev):
        t = ev.get("published_time") or ev.get("event_time")
        if not t or not cutoff:
            return None
        try:
            dt = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (cutoff - dt).total_seconds() / 86400.0
        except Exception:
            return None

    by_cn = {}
    for e in list(events) + list(pub_events):
        cn = e.get("country") or e.get("country_cn")
        if cn:
            by_cn.setdefault(cn, []).append(e)
    dis_by_iso = {}
    for t in disease_tls:
        iso = t.get("country_iso3")
        dis_by_iso.setdefault(iso, []).append(t)

    snapshots = []
    for c in countries:
        cn, en = c.get("cn"), c.get("en")
        iso = cn2iso.get(cn)
        evs = by_cn.get(cn) or []
        e24 = [e for e in evs if (age_days(e) is not None and age_days(e) <= 1)]
        e7 = [e for e in evs if (age_days(e) is not None and age_days(e) <= 7)]
        latest = None
        if evs:
            l = max(evs, key=lambda x: x.get("published_time") or x.get("event_time") or "")
            latest = {"event_id": l.get("event_id"), "title": l.get("title_cn")
                      or l.get("title_original") or l.get("summary_cn") or "",
                      "event_time": bj_fmt(l.get("published_time") or l.get("event_time"))}
        active = [t for t in (dis_by_iso.get(iso) or []) if (t.get("outbreak_status") or "").lower()
                  in ("active", "developing", "increasing", "geographic_spread", "monitoring")]
        snapshots.append({
            "country_cn": cn,
            "country_en": en,
            "iso3": iso,
            "region": c.get("region"),
            "baseline_risk": {1: "低", 2: "中", 3: "高", 4: "极高"}.get(c.get("risk_level")),
            "baseline_risk_level": c.get("risk_level"),
            "events_24h": len(e24) if evs else None,
            "events_7d": len(e7) if evs else None,
            "latest_major_event": latest,
            "active_outbreaks": len(active) if dis_by_iso.get(iso) else None,
            "last_updated": bj_fmt(max((e.get("published_time") or e.get("event_time") or "" for e in evs), default=None)),
        })
    return {"generated_at": bj_iso(), "count": len(snapshots), "snapshots": snapshots}


def _latest_counts_from_updates(dt):
    """从 disease updates 取最近一次计数（如存在）。"""
    for u in reversed(dt.get("updates") or []):
        counts = u.get("counts") or u.get("latest_counts")
        if isinstance(counts, dict) and any(v is not None for v in counts.values()):
            return counts
    return None


def build_disease_outbreaks(disease_tls, iso2cn):
    """§十五/§十六/§二十九：outbreak-centric；unknown = null；类别分离。

    同一 outbreak_id 的多条观察（supersede 链/快照）按 outbreak_id 去重，
    保留最新一次（latest_report_at 最大者）——同一现实疫情在 UI 只出现一次。
    """
    by_oid = {}
    for dt in disease_tls:
        oid = dt.get("outbreak_id")
        if not oid:
            continue
        cur = by_oid.get(oid)
        if cur is None or (dt.get("latest_report_at") or "") > (cur.get("latest_report_at") or ""):
            by_oid[oid] = dt
    out = []
    for oid, dt in by_oid.items():
        iso = dt.get("country_iso3")
        lc = dict(dt.get("latest_counts") or {})
        prev = _latest_counts_from_updates(dt)
        delta = None
        if prev:
            delta = {}
            for k in ("confirmed_cases", "probable_cases", "suspected_cases", "deaths"):
                cur, pre = lc.get(k), prev.get(k)
                if cur is not None and pre is not None:
                    delta[k] = cur - pre
        st = (dt.get("outbreak_status") or "").lower()
        change = (dt.get("updates") or [{}])[-1].get("update_type", "") if dt.get("updates") else ""
        out.append({
            "outbreak_id": dt.get("outbreak_id"),
            "disease_id": dt.get("disease_id"),
            "disease_name_cn": DISEASE_CN.get(dt.get("disease_id") or ""),
            "country_iso3": iso,
            "country_cn": iso2cn.get(iso) if iso else None,
            "status": dt.get("outbreak_status"),
            "status_cn": OUTBREAK_STATUS_CN.get(st, dt.get("outbreak_status")),
            "latest_counts": lc,   # confirmed/probable/suspected 分离，null 保留
            "delta": delta,
            "latest_change": (change or "").lower() or None,
            "latest_report_at": bj_fmt(dt.get("latest_report_at")),
            "verification_status": norm_vstatus(dt.get("verification_status"),
                                                dt.get("source_count"),
                                                dt.get("independent_source_count")),
            "source_count": dt.get("source_count"),
            "independent_source_count": dt.get("independent_source_count"),
            "uncertainties": [u for u in (dt.get("uncertainties") or [])][:5],
            "affected_admin1": [a for a in (dt.get("affected_admin1") or [])][:10],
        })
    out.sort(key=lambda x: (x["latest_report_at"] or ""), reverse=True)
    return {"generated_at": bj_iso(), "count": len(out), "outbreaks": out}


def build_report_index(daily_input, weekly_inputs, brief_candidates,
                       preview_files):
    """§三十：report index。只标记 status；development 阶段全为 development_sample。

    path 一律为 preview-safe 相对路径（report-mock/sample-*.json），
    绝不暴露 data/runtime 内部路径；is_mock=true 由前端显式标注。
    """
    reports = []
    TYPE_CN = {"africa_daily": "非洲日报", "country_weekly": "国家周报",
               "major_event_brief": "重大事件简报"}
    SAMPLE = {"africa_daily": "report-mock/sample-daily.json",
              "TCD": "report-mock/sample-weekly-tcd.json",
              "NER": "report-mock/sample-weekly-ner.json",
              "SSD": "report-mock/sample-weekly-ssd.json"}

    def push(rid, typ, title, country, ps, pe, published, path):
        reports.append({
            "report_id": rid, "type": typ, "type_cn": TYPE_CN.get(typ, typ),
            "title": title, "country_iso3": country, "period_start": ps,
            "period_end": pe, "status": "development_sample",
            "status_cn": "开发样例", "published_at": published, "path": path,
            "is_mock": True,
        })

    di = daily_input or {}
    push(di.get("report_id") or "DAILY_DEV", "africa_daily",
         di.get("title") or "非洲地区社会安全与综合形势日报（开发样例）",
         None, di.get("period_start"), di.get("period_end"),
         di.get("generated_at"), SAMPLE["africa_daily"])
    # 周报仅收录已有可展示样例的（TCD/SSD）；NER 有 input 无生成报告 → 不入 index
    for ciso in ("TCD", "SSD"):
        wi = (weekly_inputs or {}).get(ciso)
        if not wi:
            continue
        push(wi.get("report_id") or "WEEKLY_%s_DEV" % ciso, "country_weekly",
             wi.get("title") or "重点国家周报（开发样例）", ciso,
             wi.get("week_start"), wi.get("week_end"),
             wi.get("generated_at"), SAMPLE.get(ciso, "report-mock/"))
    seen, dedup = set(), []
    for r in reports:
        key = (r["report_id"], r["type"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)
    return {"generated_at": bj_iso(), "count": len(dedup), "reports": dedup}


def build_knowledge_summary(catalog, entities):
    """§二十三：知识库摘要（数量 + 顶层实体链接，approved IDs only）。"""
    top = []
    for e in (entities or [])[:12]:
        top.append({"entity_id": e.get("entity_id"),
                    "name_zh": e.get("name_zh"),
                    "entity_type": e.get("entity_type"),
                    "importance_level": e.get("importance_level")})
    return {
        "generated_at": bj_iso(),
        "entity_count": (catalog or {}).get("entity_page_count")
        or (catalog or {}).get("non_country_entity_count"),
        "relationship_count": (catalog or {}).get("relationship_count"),
        "region_count": (catalog or {}).get("region_count"),
        "country_count": (catalog or {}).get("country_count"),
        "source_count": (catalog or {}).get("source_count"),
        "top_entities": top,
        "note": "实体与关系仅来自人工维护的知识库（manual update only）；"
                "不与前端字符串猜测组织。",
    }


def main():
    out_dir = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv \
        else OUT_DEFAULT
    out_dir.mkdir(parents=True, exist_ok=True)

    events = load_json(ROOT / "data" / "events.json", {}).get("events", [])
    pub = load_json(ROOT / "data" / "public" / "published_events.json", {})
    pub_events = pub if isinstance(pub, list) else (pub.get("items") or pub.get("events") or [])
    countries = load_json(ROOT / "data" / "countries.json", {}).get("countries", [])
    status = load_json(ROOT / "data" / "status.json", {})
    risk = load_json(ROOT / "data" / "risk-levels.json", {})
    social_tls = load_json(ROOT / "data" / "runtime" / "timeline" / "social_timelines.json", {}).get("timelines", [])
    disease_tls = load_json(ROOT / "data" / "runtime" / "timeline" / "disease_timelines.json", {}).get("timelines", [])
    clusters = load_json(ROOT / "data" / "runtime" / "clustering" / "clusters-v2.json", {}).get("clusters", [])
    daily_input = load_json(ROOT / "data" / "runtime" / "reports" / "daily_input" / "latest.json", None)
    weekly_inputs = {}
    for ciso in ("TCD", "NER", "SSD"):
        weekly_inputs[ciso] = load_json(ROOT / "data" / "runtime" / "reports" / "weekly_input" / ("%s.json" % ciso), None)
    brief_candidates = load_json(ROOT / "data" / "runtime" / "reports" / "brief_candidates" / "latest.json", None)
    preview_files = sorted((ROOT / "data" / "runtime" / "report_preview").glob("*/DAILY_*.json"))
    preview_files += sorted((ROOT / "data" / "runtime" / "report_preview").glob("*/WEEKLY_*.json"))
    catalog = load_json(ROOT / "data" / "intelligence" / "africa" / "catalog_metrics.json", {})
    entities_d = load_json(ROOT / "data" / "intelligence" / "africa" / "entities.json", {})
    entities = entities_d.get("entities", []) if isinstance(entities_d, dict) else entities_d

    cn2iso, iso2cn, iso2en, iso2risk = build_country_indexes(countries)

    views = {
        "site_overview": build_site_overview(events, pub_events, countries,
                                             status, disease_tls, daily_input,
                                             iso2cn),
        "master_events": build_master_events(social_tls, clusters, cn2iso,
                                             iso2cn, iso2en),
        "event_timelines": build_event_timelines(social_tls),
        "country_snapshots": build_country_snapshots(countries, events,
                                                     pub_events, disease_tls,
                                                     cn2iso, iso2cn, iso2en,
                                                     iso2risk),
        "disease_outbreaks": build_disease_outbreaks(disease_tls, iso2cn),
        "report_index": build_report_index(daily_input, weekly_inputs,
                                           brief_candidates, preview_files),
        "knowledge_summary": build_knowledge_summary(catalog, entities),
    }
    for name, data in views.items():
        (out_dir / ("%s.json" % name)).write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  [view] %s.json  (%d bytes)" % (name,
              os.path.getsize(out_dir / ("%s.json" % name))))
    print("FRONTEND_VIEWS_OK -> %s" % out_dir)


if __name__ == "__main__":
    main()
