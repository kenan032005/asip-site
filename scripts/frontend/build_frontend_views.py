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
                        daily_input, iso2cn, data_as_of=None, generated_at=None,
                        data_as_of_source=None):
    """§四-§八 + V1.1-H1 §十/§十二/§十四。

    cutoff（KPI 24h/7d 窗口基准）= **data_as_of**（Production processing window 截止），
    不再使用 latest event time（否则无新事件时窗口会停住）。
    同时输出三时间契约：data_as_of / latest_verified_event_time / generated_at。
    """
    now = generated_at or bj_iso()
    all_ev = list(events) + list(pub_events)
    cutoff = _as_dt(data_as_of)
    if cutoff is None:      # 兼容：未提供 processing cutoff 时退回最新事件时间
        times = [e.get("published_time") or e.get("event_time") for e in all_ev
                 if e.get("published_time") or e.get("event_time")]
        if times:
            try:
                cutoff = datetime.fromisoformat(max(times).replace("Z", "+00:00"))
            except Exception:
                cutoff = None
    latest_ev = latest_verified_event_time(events, pub_events)

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
    _tc = _time_contract(cutoff, latest_ev, now, extra=(data_as_of_source or None))
    if _tc["data_as_of"] is None:      # 有数据但无 processing cutoff 时，用窗口基准兜底
        _tc["data_as_of"] = cutoff.isoformat() if cutoff else None
        _tc["data_as_of_bj"] = bj_fmt(cutoff.isoformat()) if cutoff else None
    return {
        "generated_at": now,
        **_tc,
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


# ══════════════════════════════════════════════════════════════════════
# V1.1-H1 §三/§四：统一国家联结键（ISO3）单一实现
# 允许来源：approved country reference（含 iso_alpha2/iso_alpha3/name_zh/name_en）
# 禁止：字符串猜测、模糊匹配、LLM 判断；无法确认 → resolved=False，不强归类
# ══════════════════════════════════════════════════════════════════════
COUNTRY_REF_REL = "intelligence/africa/countries.json"


# ── 标准确定性 ISO2 → ISO3（V1.1-H1 §三 允许来源之一；非模糊匹配、非猜测）──
ISO2_TO_ISO3_STD = {
    "TD": "TCD", "SD": "SDN", "SS": "SSD", "NE": "NER", "BJ": "BEN", "ET": "ETH",
    "NG": "NGA", "ML": "MLI", "BF": "BFA", "CM": "CMR", "CF": "CAF", "TG": "TGO",
    "CI": "CIV", "GH": "GHA", "SN": "SEN", "MR": "MRT", "GN": "GIN", "SL": "SLE",
    "LR": "LBR", "GM": "GMB", "GW": "GNB", "CV": "CPV", "CD": "COD", "CG": "COG",
    "GA": "GAB", "ER": "ERI", "DJ": "DJI", "SO": "SOM", "KE": "KEN", "UG": "UGA",
    "RW": "RWA", "BI": "BDI", "TZ": "TZA", "MW": "MWI", "MZ": "MOZ", "ZM": "ZMB",
    "ZW": "ZWE", "AO": "AGO", "NA": "NAM", "BW": "BWA", "ZA": "ZAF", "LS": "LSO",
    "SZ": "SWZ", "MG": "MDG", "EG": "EGY", "LY": "LBY", "TN": "TUN", "DZ": "DZA",
    "MA": "MAR",
}


#: 已批准的监控国家名称别名（来自 data/countries.json 与情报参考的既有差异，非猜测）
APPROVED_NAME_ALIASES = {
    "刚果共和国（刚果布）": "COG", "Congo Republic": "COG", "刚果（布）": "COG",
    "刚果民主共和国": "COD", "刚果（金）": "COD", "DR Congo": "COD",
    "科特迪瓦": "CIV", "Côte d'Ivoire": "CIV", "Cote d'Ivoire": "CIV",
}


def load_country_ref(data_dir=None):
    """加载已批准国家参考，返回 {iso3:..., } 反查表（确定性，无猜测）。"""
    base = Path(data_dir) if data_dir else (ROOT / "data")
    p = base / COUNTRY_REF_REL
    ref = {"iso2": {}, "iso3": {}, "zh": {}, "en": {}, "by_iso3": {}}
    # 1) 标准确定性 ISO2→ISO3（§三 允许来源）
    ref["iso2"].update(ISO2_TO_ISO3_STD)
    for a3 in ISO2_TO_ISO3_STD.values():
        ref["iso3"][a3] = a3
    # 2) 显示表（既有单一映射）补充名称
    for a3, cn in ISO3_CN.items():
        ref["zh"].setdefault(cn, a3)
        ref["iso3"].setdefault(a3, a3)
    for a3, en in ISO3_EN.items():
        ref["en"].setdefault((en or "").lower(), a3)
    for name, a3 in APPROVED_NAME_ALIASES.items():
        ref["zh"].setdefault(name, a3)
        ref["en"].setdefault(name.lower(), a3)
        ref["iso3"].setdefault(a3, a3)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return ref
    for c in (doc.get("items") or doc.get("countries") or []):
        a2 = (c.get("iso_alpha2") or "").strip().upper()
        a3 = (c.get("iso_alpha3") or "").strip().upper()
        zh = (c.get("name_zh") or "").strip()
        en = (c.get("name_en") or "").strip()
        if not a3:
            continue
        ref["by_iso3"][a3] = c
        ref["iso3"][a3] = a3
        if a2:
            ref["iso2"][a2] = a3
        if zh:
            ref["zh"][zh] = a3
        if en:
            ref["en"][en.lower()] = a3
    return ref


def normalize_country_iso3(value, ref=None):
    """ISO3 / ISO2 / 已批准国家名 → ISO3。

    返回 {"iso3": str|None, "normalization_basis": str, "resolved": bool}。
    仅使用已批准映射；无法确认时 resolved=False（不得猜测、不得强归类）。
    """
    ref = ref or load_country_ref()
    v = (value or "").strip() if isinstance(value, str) else ""
    if not v:
        return {"iso3": None, "normalization_basis": "empty_input", "resolved": False}
    up = v.upper()
    if up in ref["iso3"]:
        return {"iso3": up, "normalization_basis": "iso3_passthrough", "resolved": True}
    if up in ref["iso2"]:
        return {"iso3": ref["iso2"][up], "normalization_basis": "iso2_to_iso3_approved_map",
                "resolved": True}
    if v in ref["zh"]:
        return {"iso3": ref["zh"][v], "normalization_basis": "approved_name_zh_map", "resolved": True}
    if v.lower() in ref["en"]:
        return {"iso3": ref["en"][v.lower()], "normalization_basis": "approved_name_en_map",
                "resolved": True}
    return {"iso3": None, "normalization_basis": "unresolved_not_in_approved_reference",
            "resolved": False}


# ══════════════════════════════════════════════════════════════════════
# V1.1-H1 §十/§十一：三时间契约
#   data_as_of                 系统已完整处理到的 Production data window 截止时间
#                              （来自 processing state，绝不用 view build time）
#   latest_verified_event_time 当前 public/canonical truth 中最新已核实事件的 event time
#   generated_at               本视图文件本次构建时间（不得冒充数据时间）
# ══════════════════════════════════════════════════════════════════════
DATA_AS_OF_FIELDS = ("last_successful_collection", "last_daily_report",
                     "last_weekly_report", "last_disease_run", "last_successful_ai")


def resolve_data_as_of(data_dir=None):
    """Production processing cutoff（确定性，来自 state；缺失则 fallback canonical.updated_at）。"""
    base = Path(data_dir) if data_dir else (ROOT / "data")
    cutoff, src = None, None
    try:
        st = json.loads((base / "runtime" / "ops" / "production_state.json").read_text(encoding="utf-8"))
        for f in DATA_AS_OF_FIELDS:
            v = st.get(f)
            if not v:
                continue
            try:
                dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
            except Exception:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if cutoff is None or dt > cutoff:
                cutoff, src = dt, "production_state.%s" % f
    except Exception:
        pass
    if cutoff is None:
        try:
            can = json.loads((base / "canonical" / "event_clusters.json").read_text(encoding="utf-8"))
            dt = datetime.fromisoformat(str(can.get("updated_at")).replace("Z", "+00:00"))
            cutoff, src = dt, "canonical.updated_at"
        except Exception:
            pass
    return cutoff, src


def latest_verified_event_time(*event_lists):
    """public/canonical truth 中最新已核实事件的 event time（ISO 字符串，无则 None）。"""
    best = None
    for evs in event_lists:
        for e in (evs or []):
            t = e.get("published_time") or e.get("event_time")
            if not t:
                continue
            s = str(t)
            if best is None or s > best:
                best = s
    return best


def _as_dt(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _time_contract(data_as_of_dt, latest_event, generated_at, extra=None):
    out = {
        "data_as_of": data_as_of_dt.isoformat() if data_as_of_dt else None,
        "data_as_of_bj": bj_fmt(data_as_of_dt.isoformat()) if data_as_of_dt else None,
        "data_as_of_source": extra,
        "latest_verified_event_time": latest_event,
        "generated_at": generated_at,
    }
    return out


def build_master_events(social_tls, clusters, cn2iso, iso2cn, iso2en, country_ref=None):
    """§二十七：master event 视图（同一现实事件只出现一次）。"""
    cluster_meta = {}
    for cl in clusters:
        cluster_meta[cl.get("master_event_id")] = cl
    out = []
    for tl in social_tls:
        mid = tl.get("master_event_id")
        cs = tl.get("current_state") or {}
        # V1.1-H1 §三：统一 ISO3 联结键（timeline 未带国家时回退 cluster 元数据，
        # 可能为 ISO2 → 经已批准映射确定性归一；无法确认则不强行归类）
        raw_iso = cs.get("country") or (cluster_meta.get(mid) or {}).get("primary_country_iso3")             or (cluster_meta.get(mid) or {}).get("country_code")
        _nrm = normalize_country_iso3(raw_iso, country_ref)
        iso = _nrm["iso3"]
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
    return {"generated_at": bj_iso(), "count": len(out), "events": out,
            "country_join_key": "iso3"}


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
                            cn2iso, iso2cn, iso2en, iso2risk,
                            country_ref=None, data_as_of=None, generated_at=None):
    """§十二 + V1.1-H1 §六/§十四/§十五：国家卡片。

    - 统一以 **ISO3** 为联结键（事件与 snapshots 同键）；
    - 24h/7d 窗口相对 **data_as_of**（processing window 截止），而非 latest event time；
    - 每个快照输出 data_as_of / latest_event_time / generated_at 三个语义不同的时间。
    无近期事件的国家 events_24h/7d = 0，但仍跟随当前 data_as_of（合法 CURRENT）。
    """
    ref = country_ref or load_country_ref()
    gen = generated_at or bj_iso()
    dtx = _as_dt(data_as_of)
    all_ev = list(events) + list(pub_events)

    by_iso, unresolved = {}, 0
    for e in all_ev:
        raw = e.get("country_iso3") or e.get("country") or e.get("country_cn")
        n = normalize_country_iso3(raw, ref)
        if n["resolved"]:
            by_iso.setdefault(n["iso3"], []).append(e)
        elif raw:
            unresolved += 1

    dis_by_iso = {}
    for t in disease_tls:
        dis_by_iso.setdefault(t.get("country_iso3"), []).append(t)

    def in_window(ev, days):
        if not dtx:
            return None
        t = _as_dt(ev.get("published_time") or ev.get("event_time"))
        if not t:
            return None
        age = (dtx - t).total_seconds() / 86400.0
        return 0 <= age <= days

    snapshots = []
    for c in countries:
        cn, en = c.get("cn"), c.get("en")
        iso = cn2iso.get(cn) or normalize_country_iso3(en, ref)["iso3"]
        evs = by_iso.get(iso) or []
        e24 = [e for e in evs if in_window(e, 1) is True]
        e7 = [e for e in evs if in_window(e, 7) is True]
        latest = None
        latest_time = None
        if evs:
            l = max(evs, key=lambda x: str(x.get("published_time") or x.get("event_time") or ""))
            latest_time = l.get("published_time") or l.get("event_time")
            latest = {"event_id": l.get("event_id"),
                      "title": l.get("title_cn") or l.get("title_original")
                      or l.get("summary_cn") or "",
                      "event_time": bj_fmt(latest_time)}
        active = [t for t in (dis_by_iso.get(iso) or [])
                  if (t.get("outbreak_status") or "").lower()
                  in ("active", "developing", "increasing", "geographic_spread", "monitoring")]
        snapshots.append({
            "country_cn": cn,
            "country_en": en,
            "iso3": iso,
            "region": c.get("region"),
            "baseline_risk": {1: "低", 2: "中", 3: "高", 4: "极高"}.get(c.get("risk_level")),
            "baseline_risk_level": c.get("risk_level"),
            "events_24h": len(e24),
            "events_7d": len(e7),
            "latest_major_event": latest,
            "active_outbreaks": len(active) if dis_by_iso.get(iso) else None,
            "last_updated": bj_fmt(latest_time),
            # V1.1-H1 §十五：国家快照三时间契约
            "data_as_of": dtx.isoformat() if dtx else None,
            "data_as_of_bj": bj_fmt(dtx.isoformat()) if dtx else None,
            "latest_event_time": latest_time,
            "generated_at": gen,
        })
    return {"generated_at": gen, "count": len(snapshots), "snapshots": snapshots,
            "unresolved_country_inputs": unresolved,
            "country_join_key": "iso3"}


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


def _prod_daily_identity(report_date, stored_rid=None):
    """Report Identity 单一真值：report_date = YYYY-MM-DD
    → report_id = DAILY_YYYYMMDD。返回 (rid, repaired, original_rid)。"""
    expected = None
    if report_date:
        compact = str(report_date).replace("-", "").strip()
        if compact.isdigit() and len(compact) == 8:
            expected = "DAILY_%s" % compact
    if expected is None:
        return (stored_rid or None), False, stored_rid
    if stored_rid and stored_rid != expected:
        return expected, True, stored_rid      # deterministic identity repair
    if not stored_rid:
        return expected, False, None
    return stored_rid, False, stored_rid


def _is_fixture_report_id(rid):
    """夹具/开发样例识别：MANUAL_TRIAL / DEV / TRIAL 一律不得进入 Production 公开索引。"""
    if not rid:
        return True
    up = str(rid).upper()
    return ("MANUAL_TRIAL" in up) or ("_DEV" in up) or up.endswith("_TRIAL")         or up.startswith("TRIAL_")


def _load_prod_reports(ops_reports_dir):
    """Production report outputs → public index entries（确定性装配）。

    来源：data/runtime/ops/reports/（production-state 持久化的正式报告产物）。
    规则：
      - daily：在 full/fallback/low_data/hold 中选取 **report_date 最新** 的合法产物；
      - weekly：每国别在 full/fallback/low_data 中选取最新合法产物；
      - 夹具（MANUAL_TRIAL / DEV / TRIAL）一律排除，不进入公开索引；
      - report_id 由 report_date 归一（deterministic，记录 repair 元数据）。
    不读取/不生成任何 AI 内容。
    """
    import os as _os
    entries = []
    if not ops_reports_dir or not _os.path.isdir(ops_reports_dir):
        return entries

    def _load(fname):
        d = load_json(_os.path.join(ops_reports_dir, fname), None)
        return d if isinstance(d, dict) else None

    # ---------- daily ----------
    cands = []
    for fname, cls in (("daily_full.json", "FULL"),
                       ("daily_fallback.json", "FALLBACK"),
                       ("daily_low_data.json", "LOW_DATA"),
                       ("daily_hold.json", "HOLD")):
        d = _load(fname)
        if not d or not d.get("report_date"):
            continue
        if _is_fixture_report_id(d.get("report_id")):
            continue
        cands.append((str(d.get("report_date")), str(d.get("generated_at") or ""), fname, cls, d))
    # 同一 report_date 只保留一个产物（FULL > FALLBACK > LOW_DATA > HOLD）
    _rank = {"FULL": 0, "FALLBACK": 1, "LOW_DATA": 2, "HOLD": 3}
    cands.sort(key=lambda t: (t[0], -_rank.get(t[3], 9), t[1]), reverse=True)
    _by_date = {}
    for c in cands:
        _by_date.setdefault(c[0], c)
    daily_entries = []
    for date_key in sorted(_by_date, reverse=True):
        _, _, fname, cls, d = _by_date[date_key]
        rid, repaired, orig = _prod_daily_identity(d.get("report_date"), d.get("report_id"))
        gates = _load("daily_gates.json") or {}
        ent = {
            "report_id": rid,
            "report_type": "africa_daily",
            "type": "africa_daily",
            "type_cn": "非洲日报",
            "title": d.get("title") or "非洲地区社会安全与综合形势日报",
            "country_iso3": None,
            "report_date": d.get("report_date"),
            "classification": cls,
            "fact_gate": gates.get("FACT_GATE"),
            "period_start": d.get("period_start"),
            "period_end": d.get("period_end"),
            "generated_at": d.get("generated_at"),
            "published_at": d.get("generated_at"),
            "status": "production",
            "status_cn": "生产报告",
            "path": "reports/daily/%s.json" % rid,
            "is_mock": False,
            "historical_reconstruction": False,
            "production_provenance": {
                "source": "production_state",
                "trigger": "scheduled_orchestrator",
                "artifact": fname,
            },
        }
        if repaired:
            ent["report_identity_repair"] = {
                "repair_type": "deterministic_report_identity_repair",
                "original_report_id": orig,
                "corrected_report_id": rid,
            }
        daily_entries.append(ent)
    entries.extend(daily_entries)

    # ---------- weekly（每国别取最新合法产物）----------
    for mode, ciso in (("tcd_weekly", "TCD"), ("ssd_weekly", "SSD")):
        wcands = []
        for fname, cls in (("%s_full.json" % mode, "FULL"),
                           ("%s_fallback.json" % mode, "FALLBACK"),
                           ("%s_low_data.json" % mode, "LOW_DATA")):
            d = _load(fname)
            if not d:
                continue
            if _is_fixture_report_id(d.get("report_id")):
                continue
            we = str(d.get("week_end") or d.get("report_date") or "")
            if not we:
                continue
            wcands.append((we, str(d.get("generated_at") or ""), fname, cls, d))
        if not wcands:
            continue
        wcands.sort(key=lambda t: (t[0], t[1]), reverse=True)
        _, _, fname, cls, d = wcands[0]
        week_end = d.get("week_end") or d.get("report_date")
        rid = d.get("report_id") or ("WEEKLY_%s_%s" % (ciso, str(week_end).replace("-", "")))
        entries.append({
            "report_id": rid,
            "report_type": "country_weekly",
            "type": "country_weekly",
            "type_cn": "国家周报",
            "title": d.get("title") or ("重点国家周报（%s）" % ciso),
            "country_iso3": ciso,
            "report_date": week_end,
            "classification": cls,
            "period_start": d.get("week_start") or d.get("period_start"),
            "period_end": week_end or d.get("period_end"),
            "generated_at": d.get("generated_at"),
            "published_at": d.get("generated_at"),
            "status": "production",
            "status_cn": "生产报告",
            "path": "reports/weekly/%s.json" % rid,
            "is_mock": False,
            "historical_reconstruction": False,
            "production_provenance": {
                "source": "production_state",
                "trigger": "scheduled_orchestrator",
                "artifact": fname,
            },
        })
    return entries


# ── China Interest（V1.1-H1 §六/§七）：确定性涉华关注视图 ──────────────
# 只使用已批准的结构化依据，禁止 LLM 判断、禁止关键词猜测中资关系：
#   1) 事件上的结构化涉华标记（china_related / event_type=china_related）
#   2) 已批准实体元数据中被显式标注为中国关联的实体 id（data/intelligence/africa/entities.json）
#   3) 已批准的中国利益暴露上下文（data/reference/china_exposure_context.json，可选；
#      未批准/不存在时 INDIRECT 恒为 0，并在 uncertainty 中如实标注）
CHINA_CONTEXT_PATH = "data/reference/china_exposure_context.json"


def _approved_china_entity_ids(entities):
    """已批准实体中被显式标注为中国关联的 entity_id（结构化字段，非名称猜测）。"""
    out = set()
    for e in (entities or []):
        if not isinstance(e, dict):
            continue
        if e.get("china_linked") is True or e.get("china_related") is True \
                or (e.get("china_linkage") in ("direct", "indirect")):
            eid = e.get("entity_id")
            if eid:
                out.add(eid)
    return out


def _event_entity_ids(ev):
    vals = ev.get("entity_ids") or ev.get("entity_refs") or []
    out = set()
    for v in vals:
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict) and v.get("entity_id"):
            out.add(v["entity_id"])
    return out


def build_china_interest(master_events, entities, countries, data_dir=None):
    """确定性涉华关注视图（Production-compatible，无 AI、无猜测）。

    DIRECT：存在明确结构化涉华依据（事件标记 / 已批准中国关联实体命中）。
    INDIRECT：事件本身不直接涉华，但命中已批准的中国利益暴露上下文（国家级）。
    每条保留 event_id / country / event_date / exposure_type / exposure_basis /
    matched_entities / source_refs / confidence / uncertainty。
    """
    import os as _os
    ent_ids = _approved_china_entity_ids(entities)
    ctx = {}
    try:
        base = data_dir or str(ROOT)
        cp = _os.path.join(base, CHINA_CONTEXT_PATH)
        if _os.path.exists(cp):
            ctx = json.loads(open(cp, encoding="utf-8").read()) or {}
    except Exception:
        ctx = {}
    approved_ctx_countries = set(ctx.get("countries") or [])
    approved_ctx_basis = ctx.get("basis") or ""

    direct, indirect = [], []
    for ev in (master_events or []):
        eid = ev.get("master_event_id") or ev.get("event_id")
        etype = (ev.get("event_type") or "").lower()
        flagged = bool(ev.get("china_related")) or etype == "china_related"
        hits = sorted(_event_entity_ids(ev) & ent_ids)
        iso = ev.get("country_iso3")
        row = {
            "event_id": eid,
            "country": iso,
            "event_date": ev.get("event_time") or ev.get("latest_update_at"),
            "exposure_type": "DIRECT",
            "exposure_basis": [],
            "matched_entities": hits,
            "source_refs": ((ev.get("source_ref") or {}) if isinstance(ev.get("source_ref"), dict) else {}),
            "confidence": "high" if flagged else "medium",
            "uncertainty": [],
        }
        if flagged:
            row["exposure_basis"].append("event_structured_flag")
        if hits:
            row["exposure_basis"].append("approved_china_entity_match")
        if row["exposure_basis"]:
            direct.append(row)
        elif iso and iso in approved_ctx_countries:
            indirect.append({
                "event_id": eid, "country": iso,
                "event_date": row["event_date"],
                "exposure_type": "INDIRECT",
                "exposure_basis": ["approved_country_exposure_context"],
                "matched_entities": [],
                "source_refs": row["source_refs"],
                "confidence": "low",
                "uncertainty": [approved_ctx_basis or "上下文依据需人工复核"],
            })

    notes = []
    if not direct:
        notes.append("当前公开可采信事件中无结构化涉华依据（china_related 标记 / 已批准中国关联实体命中）")
    if not indirect and not approved_ctx_countries:
        notes.append("未批准中国利益暴露上下文元数据（%s 不存在）→ INDIRECT 恒为 0，不进行任何推测" % CHINA_CONTEXT_PATH)
    # 兼容行数组（home-v11.js 既有契约）：direct/indirect 的扁平投影
    rows = []
    for kind, arr in (("direct", direct), ("indirect", indirect)):
        for r in arr:
            rows.append({
                "record_id": r["event_id"],
                "event_id": r["event_id"],
                "country": r["country"],
                "country_cn": None,
                "event_time": r["event_date"],
                "china_interest": kind,
                "china_related": kind == "direct",
                "exposure_type": r["exposure_type"],
                "exposure_basis": r["exposure_basis"],
                "matched_entities": r["matched_entities"],
                "source_refs": r["source_refs"],
                "confidence": r["confidence"],
                "uncertainty": r["uncertainty"],
            })
    return {
        "generated_at": bj_iso(),
        "method": "deterministic_china_interest_v1",
        "rows": rows,
        "inputs": {
            "master_events": len(master_events or []),
            "approved_entities": len(entities or []),
            "approved_china_entity_ids": len(ent_ids),
            "approved_context_countries": len(approved_ctx_countries),
            "countries_meta": len(countries or []),
        },
        "summary": {
            "direct_count": len(direct),
            "indirect_count": len(indirect),
            "limited_data": not (direct or indirect),
            "notes": notes,
        },
        "direct": direct,
        "indirect": indirect,
    }


def build_report_index(daily_input, weekly_inputs, brief_candidates,
                       preview_files, ops_reports_dir=None):
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
            "is_mock": True, "historical_reconstruction": True,
        })

    # 一级来源：production report outputs（data/runtime/ops/reports/）
    reports.extend(_load_prod_reports(ops_reports_dir))

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

    def _sort_key(r):
        # reverse=True 排序：production(1) 在 mock(0) 之前；同组内 report_date 新在前
        d = r.get("report_date") or r.get("period_end") or ""
        return (1 if r.get("status") == "production" else 0, d,
                r.get("published_at") or "")

    dedup.sort(key=_sort_key, reverse=True)
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
    ops_reports_dir = ROOT / "data" / "runtime" / "ops" / "reports"
    preview_files = sorted((ROOT / "data" / "runtime" / "report_preview").glob("*/DAILY_*.json"))
    preview_files += sorted((ROOT / "data" / "runtime" / "report_preview").glob("*/WEEKLY_*.json"))
    catalog = load_json(ROOT / "data" / "intelligence" / "africa" / "catalog_metrics.json", {})
    entities_d = load_json(ROOT / "data" / "intelligence" / "africa" / "entities.json", {})
    entities = entities_d.get("entities", []) if isinstance(entities_d, dict) else entities_d

    cn2iso, iso2cn, iso2en, iso2risk = build_country_indexes(countries)

    views_master_for_china = build_master_events(social_tls, clusters, cn2iso,
                                                 iso2cn, iso2en).get("events", [])

    # V1.1-H1：统一国家参考 + Production processing cutoff（三时间契约的单一口径）
    country_ref = load_country_ref(str(ROOT / "data"))
    data_as_of_dt, data_as_of_src = resolve_data_as_of(str(ROOT / "data"))
    data_as_of_iso = data_as_of_dt.isoformat() if data_as_of_dt else None
    gen_at = bj_iso()
    print("  [tz] data_as_of = %s (source=%s) | generated_at = %s" %
          (data_as_of_iso, data_as_of_src, gen_at))

    views = {
        "site_overview": build_site_overview(events, pub_events, countries,
                                             status, disease_tls, daily_input,
                                             iso2cn, data_as_of=data_as_of_iso,
                                             generated_at=gen_at,
                                             data_as_of_source=data_as_of_src),
        "master_events": build_master_events(social_tls, clusters, cn2iso,
                                             iso2cn, iso2en,
                                             country_ref=country_ref),
        "event_timelines": build_event_timelines(social_tls),
        "country_snapshots": build_country_snapshots(countries, events,
                                                     pub_events, disease_tls,
                                                     cn2iso, iso2cn, iso2en,
                                                     iso2risk,
                                                     country_ref=country_ref,
                                                     data_as_of=data_as_of_iso,
                                                     generated_at=gen_at),
        "disease_outbreaks": build_disease_outbreaks(disease_tls, iso2cn),
        "china_interest": build_china_interest(
            views_master_for_china, entities, countries, data_dir=str(ROOT)),
        "report_index": build_report_index(daily_input, weekly_inputs,
                                           brief_candidates, preview_files,
                                           ops_reports_dir=str(ops_reports_dir)),
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
