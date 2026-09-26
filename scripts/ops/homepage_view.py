"""C7-6 首页情报公开视图（确定性，无 AI 调用）。

输入（全部既有视图/公开产物，不新建 truth store）：
  data/sources.json · data/views/news_stream.json（C1A 情报流，含 news_id/linked_event_id）
  data/public/published_events.json（已核实事件）· data/public/disease_events.json
  data/countries.json · data/views/executive_summary.json · config/countries/*.json
  data/intelligence/ai/homepage/<YYYYMMDDHH>.json（首页 AI 简报，仅 status=ok 采用）
  data/runtime/ops/homepage_intelligence_fact_pack.json（计数真值）

输出：
  data/views/homepage_intelligence.json（8 板块 + 去重后条目 + detail_url）
  data/public/intelligence_items.json（公开安全的情报项投影，供 intelligence.html 消费）

C7-6 变更：
  - 每个公开条目带**中心化 detail_url**（已核实事件 → event.html?id=EVT_…；情报信号 → intelligence.html?id=NEWS-…）
  - **去重引擎**：信号已关联已核实事件 → 只显示事件；同 dedup_key/同事件的多篇 → 合并为一条 development
  - 五大领域改用 **7 日窗口**（含 7 日条目列表，前 6–8 条 + 展开全部）
  - 地图板块移交旧版「非洲风险地图」组件（本视图不再产出 map）
  - 输出 RAW_ITEMS / DEDUPED_DEVELOPMENTS / COLLAPSED_DUPLICATES 指标
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BJT = timezone(timedelta(hours=8))
OUT_VIEW = Path("data") / "views" / "homepage_intelligence.json"
OUT_PUBLIC = Path("data") / "public" / "intelligence_items.json"
PACK = Path("data") / "runtime" / "ops" / "homepage_intelligence_fact_pack.json"
BRIEF_DIR = Path("data") / "intelligence" / "ai" / "homepage"

LOW_DATA_CN = "过去24小时未发现足够高质量公开信息形成明确判断"
#: 只有**多源独立核实**才可标注「已核实事件」；平台真实标签见 published_events.verification_label_cn。
#: 生产实测：7 日窗口 58 条公开事件中 57 条为"单一来源" → 一律按情报信号口径展示，绝不标 已核实。
VERIFIED_CN = "已核实事件"
SIGNAL_CN = "情报信号（尚未独立核实）"
SECTORS = [
    ("terrorism_conflict", "恐怖主义与武装冲突", "Terrorism & Armed Conflict"),
    ("political_social", "政治与社会稳定", "Political & Social Stability"),
    ("crime_public_security", "社会治安与犯罪", "Crime & Public Security"),
    ("military_border_maritime", "军事、边境与海上安全", "Military / Border / Maritime Security"),
    ("accident_disruption", "重大事故、灾害与运营中断", "Accidents / Disasters / Operational Disruption"),
]

# 事件类型 → 领域（一个条目的主领域由事件类型决定；无法归类者仅出现在总览/重点，不进领域列表）
CAT2SECTOR = {}
for _types, _key in [
    (["terrorist_attack", "armed_conflict", "insurgency", "clashes", "ethnic_conflict",
      "bombing", "kidnapping", "massacre"], "terrorism_conflict"),
    (["protest", "demonstration", "riot", "civil_unrest", "strike", "election_security",
      "political_crisis", "government_change", "corruption_politics"], "political_social"),
    (["crime", "violent_crime", "robbery", "gang_violence", "illegal_mining",
      "trafficking", "public_disorder"], "crime_public_security"),
    (["border_security", "military_operation", "maritime_security", "airspace_incident",
      "defense", "border_incident", "civil_protection"], "military_border_maritime"),
    (["accident", "disaster", "natural_disaster", "flood", "drought", "fire",
      "industrial_accident", "infrastructure_failure", "disruption", "utility_outage",
      "transport_disruption"], "accident_disruption"),
]:
    for _t in _types:
        CAT2SECTOR[_t] = _key

ISO2_TO_ISO3 = {
    "TD": "TCD", "NE": "NER", "ML": "MLI", "BF": "BFA", "CM": "CMR", "CF": "CAF",
    "UG": "UGA", "RW": "RWA", "BI": "BDI", "SN": "SEN", "GH": "GHA", "CI": "CIV",
    "EG": "EGY", "DZ": "DZA", "TN": "TUN", "MA": "MAR", "ZW": "ZWE", "TZ": "TZA",
    "GA": "GAB", "CG": "COG", "GN": "GIN", "MR": "MRT", "BJ": "BEN", "CD": "COD",
    "ET": "ETH", "KE": "KEN", "LY": "LBY", "MZ": "MOZ", "NG": "NGA", "SO": "SOM",
    "SS": "SSD", "SD": "SDN", "ZA": "ZAF", "AO": "AGO", "ZM": "ZMB", "MW": "MWI",
    "ER": "ERI", "DJ": "DJI", "GM": "GMB", "GW": "GNB", "SL": "SLE", "LR": "LBR",
    "TG": "TGO", "GQ": "GNQ", "BW": "BWA", "NA": "NAM", "LS": "LSO", "SZ": "SWZ",
    "MG": "MDG", "KM": "COM", "MU": "MUS", "SC": "SYC", "CV": "CPV", "ST": "STP",
}


# ───────────────────────── 基础工具 ─────────────────────────

def load_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def write_atomic(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, str(path))


def parse_time(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=BJT)
    except ValueError:
        return None


def _clean(o):
    """输出前清理：去掉内部字段（_ 前缀）并把 datetime 转 ISO。"""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, list):
        return [_clean(x) for x in o]
    if isinstance(o, datetime):
        return o.isoformat()
    return o


def latest_brief(root):
    d = Path(root) / BRIEF_DIR
    if not d.is_dir():
        return {}
    for p in sorted(d.glob("*.json"), reverse=True):
        b = load_json(p, {})
        if b.get("status") == "ok":
            return b
    return {}


# ─────────────── PHASE 4：中心化 detail_url ───────────────

def event_detail_url(event_id):
    return "event.html?id=%s" % event_id if event_id else ""


def signal_detail_url(news_id):
    return "intelligence.html?id=%s" % news_id if news_id else ""


def item_detail_url(kind, item):
    """中心化 detail_url：有事件记录 → event.html?id=EVT_…；纯文章 → intelligence.html?id=NEWS-…。"""
    eid = str(item.get("event_id") or "")
    if eid:
        return event_detail_url(eid)
    return signal_detail_url(str(item.get("news_id") or ""))


# ───────────────────────── 主构建 ─────────────────────────

def build(root, now, apply=False):
    root = Path(root)
    data = root / "data"
    srcs = (load_json(data / "sources.json", {}) or {}).get("sources") or []
    feed = (load_json(data / "views" / "news_stream.json", {}) or {}).get("items") or []
    pubs = (load_json(data / "public" / "published_events.json", {}) or {}).get("items") or []
    disease = (load_json(data / "public" / "disease_events.json", {}) or {}).get("items") or []
    exec_view = load_json(data / "views" / "executive_summary.json", {}) or {}
    pack = load_json(root / PACK, {}) or {}
    brief = latest_brief(root)
    ai_ok = brief.get("status") == "ok"

    tier_of_src = {s.get("source_name"): (s.get("source_tier") or "C") for s in srcs}
    role_of_src = {s.get("source_name"): (s.get("source_role") or "local_signal") for s in srcs}

    h24, d7 = now - timedelta(hours=24), now - timedelta(days=7)

    # ── 收录：7 日窗口的信号与事件 ──
    raw_signals, raw_events = [], []
    for s in feed:
        if s.get("quarantined"):
            continue
        t = parse_time(s.get("last_seen_at") or s.get("observed_at"))
        if t and t >= d7:
            raw_signals.append(dict(s, _t=t))
    for e in pubs:
        t = parse_time(e.get("published_time") or e.get("event_time"))
        if t and t >= d7:
            raw_events.append(dict(e, _t=t))

    RAW_ITEMS = len(raw_signals) + len(raw_events)

    # ── PHASE 12 去重引擎 ──
    # 规则 1：信号已关联已核实事件（linked_event_id 命中事件集）→ 丢弃信号，保留事件
    ev_ids = {str(e.get("event_id") or "") for e in raw_events if e.get("event_id")}
    kept_signals, collapsed_to_event = [], 0
    for s in raw_signals:
        le = str(s.get("linked_event_id") or "")
        if le and le in ev_ids:
            collapsed_to_event += 1
            continue
        kept_signals.append(s)

    # 规则 2/3：同一事件/同一 dedup_key 的多篇信号 → 合并为一条 development（保留多源与原链接）
    groups = defaultdict(list)
    for s in kept_signals:
        key = str(s.get("linked_event_id") or s.get("dedup_key") or s.get("news_id") or "")
        groups[key].append(s)
    developments = []
    for key, items in groups.items():
        items.sort(key=lambda x: x["_t"], reverse=True)
        head = items[0]
        sources = []
        for x in items:
            nm = str(x.get("source_name") or "")
            if nm and nm not in [d["name"] for d in sources]:
                sources.append({"name": nm, "url": x.get("source_url") or "",
                                "tier": tier_of_src.get(nm, "C")})
        corrob = sorted({str(c) for x in items for c in (x.get("corroborating_sources") or []) if c})
        best = max(items, key=lambda x: (1 if str(x.get("title_cn") or "").strip() else 0,
                                         1 if str(x.get("summary_cn") or "").strip() else 0,
                                         x["_t"]))
        developments.append({
            "kind": "news_signal",
            "development_id": str(best.get("news_id") or key),
            "news_id": str(best.get("news_id") or ""),
            "country": head.get("country_cn") or "未识别",
            "country_iso2": head.get("country_iso2") or "",
            "title_cn": best.get("title_cn") or "",
            "title_original": best.get("title_original") or "",
            "summary_cn": best.get("summary_cn") or "",
            "category": head.get("event_type") or "other_security",
            "category_cn": head.get("event_type_cn") or "其他",
            "sector": CAT2SECTOR.get(str(head.get("event_type") or ""), ""),
            "source": head.get("source_name") or "",
            "sources": sources[:6],
            "source_count": len(sources) or 1,
            "tier": tier_of_src.get(str(head.get("source_name") or ""), "C"),
            "role": role_of_src.get(str(head.get("source_name") or ""), "local_signal"),
            "time": head["_t"].strftime("%Y-%m-%d %H:%M"),
            "_t": head["_t"],
            "localized": bool(str(best.get("title_cn") or "").strip() and str(best.get("summary_cn") or "").strip()),
            "importance": head.get("importance") or ("high" if len(items) > 2 or corrob else "medium" if len(items) > 1 else "low"),
            "verification_status": head.get("verification_status") or "single_source",
            "verification_label": head.get("verification_label_cn") or "情报信号（尚未独立核实）",
            "original_url": best.get("source_url") or "",
            "merged_count": len(items),
            "related_sources": sources[:6],
            "source_urls": [x.get("source_url") for x in items if x.get("source_url")][:6],
        })
    for e in raw_events:
        eid = str(e.get("event_id") or "")
        sf = (e.get("source_links") or [])
        _isc = int(e.get("independent_source_count") or len(sf) or 0)
        _verified = _isc >= 2 or str(e.get("verification_level") or "") in ("multi_source", "verified")
        dev = {
            "kind": "verified_event" if _verified else "news_signal",
            "event_id": eid,
            "development_id": eid,
            "event_id": eid,
            "country": e.get("country_cn") or e.get("country") or "未识别",
            "country_iso2": e.get("country_code") or "",
            "title_cn": e.get("title_cn") or e.get("title_original") or "",
            "title_original": e.get("title_original") or "",
            "summary_cn": e.get("summary_cn") or e.get("summary_original") or "",
            "category": e.get("event_type") or "other_security",
            "category_cn": e.get("event_type_cn") or e.get("event_type") or "其他",
            "sector": CAT2SECTOR.get(str(e.get("event_type") or ""), ""),
            "source": (sf[0].get("source_name") if sf and isinstance(sf[0], dict) else "") or e.get("source_name") or "",
            "sources": [{"name": (s or {}).get("source_name") or "", "url": (s or {}).get("url") or "",
                         "tier": tier_of_src.get(str((s or {}).get("source_name") or ""), "C")}
                        for s in sf[:6] if isinstance(s, dict)],
            "source_count": int(e.get("independent_source_count") or len(sf) or 1),
            "tier": tier_of_src.get(str((sf[0].get("source_name") if sf and isinstance(sf[0], dict) else "") or ""), "C"),
            "role": "primary_evidence",
            "time": e["_t"].strftime("%Y-%m-%d %H:%M"),
            "_t": e["_t"],
            "localized": bool(str(e.get("title_cn") or "").strip() and str(e.get("summary_cn") or "").strip()),
            "importance": ("high" if _isc >= 2 else
                           "medium" if str(e.get("event_severity") or "") in ("high", "critical") else "low"),
            "verification_status": ("verified" if _verified else "single_source"),
            "verification_label": (VERIFIED_CN if _verified else
                                   (str(e.get("verification_label_cn") or "").strip()
                                    and "%s（尚未独立核实）" % str(e.get("verification_label_cn")).strip()
                                    or SIGNAL_CN)),
            "severity": e.get("event_severity") or "",
            "original_url": (sf[0].get("url") if sf and isinstance(sf[0], dict) else "") or "",
            "merged_count": 1,
            "related_sources": [],
        }
        dev["related_sources"] = dev["sources"]
        developments.append(dev)

    # 规则 5：同一事件/同一 development 只保留一条（按 id），并计算塌缩数
    uniq = {}
    for d in developments:
        uniq[d["development_id"]] = d
    DEDUPED = len(uniq)
    COLLAPSED = RAW_ITEMS - DEDUPED
    all_devs = sorted(uniq.values(), key=lambda d: d["_t"], reverse=True)

    # 领域归属：每条 development 只进**一个**主领域（跨领域不重复）
    for d in all_devs:
        d["detail_url"] = item_detail_url(d["kind"], d)

    # 仅公开可链接（中文标题+中文摘要齐备）者进入公开列表
    linkable = [d for d in all_devs if d["localized"] and d["detail_url"]]

    sig24 = [d for d in linkable if d["kind"] == "news_signal" and d["_t"] >= h24]
    ev24 = [d for d in linkable if d["kind"] == "verified_event" and d["_t"] >= h24]
    # 指标口径：已核实=多源核实；其余公开条目一律计入情报信号（诚实计数，不虚增核实数）

    # ── 板块 1：过去24小时非洲安全态势 ──
    oa = (brief.get("overall_assessment") or {}) if ai_ok else {}
    exec_assess = (exec_view.get("assessment") or {})
    metrics = {
        "signals_24h": len(sig24),
        "verified_events_24h": len(ev24),
        "countries_24h": len({d["country"] for d in (sig24 + ev24)}),
        "countries_7d": len({d["country"] for d in linkable} - {"未识别"}),
        "high_attention": len([d for d in linkable if d["_t"] >= h24 and
                               (d["importance"] == "high" or d["source_count"] >= 2)]),
        "source_tier_distribution": [{"tier": k, "count": v} for k, v in
                                     Counter(d["tier"] for d in linkable).most_common()],
    }
    overview = {
        "summary_cn": oa.get("summary_cn") or exec_assess.get("overall_assessment") or
                      "过去 24 小时未形成足够公开信息支撑的稳定研判。",
        "risk_direction": oa.get("risk_direction") or exec_assess.get("risk_direction") or "stable",
        "confidence": oa.get("confidence") or "low",
        "key_judgments": oa.get("key_judgments") or [],
        "watch_24_72h": oa.get("watch_24_72h") or [],
        "ai_based": bool(oa.get("summary_cn")),
    }

    # ── 板块 2：五大安全领域（7 日窗口）──
    bs = (brief.get("sectors") or {}) if ai_ok else {}
    sectors = []
    for key, zh, en in SECTORS:
        rows7 = [d for d in linkable if d["sector"] == key]
        rows7.sort(key=lambda d: d["_t"], reverse=True)
        e7 = [d for d in rows7 if d["kind"] == "verified_event"]
        s7 = [d for d in rows7 if d["kind"] == "news_signal"]
        b = (bs.get(key) or {}) if ai_ok else {}
        has = bool(rows7)
        sectors.append({
            "key": key, "title_cn": zh, "title_en": en,
            "window": "7d",
            "signals_7d": len(s7), "verified_events_7d": len(e7),
            "signals_24h": len([d for d in s7 if d["_t"] >= h24]),
            "verified_events_24h": len([d for d in e7 if d["_t"] >= h24]),
            "assessment_cn": b.get("assessment_cn") or ("" if has else LOW_DATA_CN),
            "trend": b.get("trend") or "flat",
            "confidence": b.get("confidence") or ("low" if not has else "medium"),
            "ai_based": bool(b.get("assessment_cn")),
            "countries": sorted({d["country"] for d in rows7} - {"未识别"})[:6],
            "changes_cn": b.get("changes_cn") or "",
            "watch_cn": b.get("watch_cn") or "",
            "developments": [{k: d[k] for k in ("development_id", "kind", "country", "title_cn",
                                                "time", "tier", "source_count", "detail_url",
                                                "verification_label")} for d in rows7],
            "developments_total": len(rows7),
        })

    # ── 板块 3：重点信息与事件解读 ──
    facts = pack.get("facts") or {}
    btop = {str(t.get("fact_id")): t for t in ((brief.get("top_developments") or []) if ai_ok else [])}
    by_fid = {}
    for d in all_devs:
        if d["kind"] == "verified_event":
            by_fid.setdefault(str(d.get("event_id")), d)
    by_news = {d["news_id"]: d for d in all_devs if d.get("news_id")}

    top, seen = [], set()
    for fid, t in btop.items():
        d = by_fid.get(fid) or by_news.get(fid)
        if not d or d["development_id"] in seen:
            continue
        seen.add(d["development_id"])
        row = dict(d)
        row["why_it_matters"] = t.get("why_important_cn") or t.get("why_it_matters") or ""
        row["ai_analysis"] = t.get("analysis_cn") or ""
        row["ai_impact"] = t.get("impact_cn") or t.get("impact") or ""
        row["ai_watch"] = t.get("watch_cn") or t.get("watch_points") or ""
        row["ai_based"] = bool(row["ai_analysis"] or row["why_it_matters"])
        top.append(row)
    if len(top) < 5:  # AI 缺失或不足 → 确定性补齐（不标 AI）
        for d in linkable:
            if len(top) >= 8:
                break
            if d["development_id"] in seen:
                continue
            seen.add(d["development_id"])
            row = dict(d)
            row.update({"why_it_matters": "", "ai_analysis": "", "ai_impact": "",
                        "ai_watch": "", "ai_based": False})
            top.append(row)
    top = top[:8]

    # ── 板块 4：对中国企业及人员影响 ──
    ci = (brief.get("china_impact") or {}) if ai_ok else {}
    cn_direct = [d for d in all_devs if str(d.get("china_related")) == "True" or d.get("china_related") is True]
    explicit = [d for d in linkable if "涉华" in str(d.get("category_cn") or "") or
                str(d.get("category") or "") == "china_security"]
    hc = [d for d in linkable if d["source_count"] >= 2 or d["kind"] == "verified_event"]
    regional = sorted(hc, key=lambda d: d["_t"], reverse=True)[:8]
    china_items = []
    for it in (ci.get("items") or []):
        fid = str(it.get("fact_id") or "")
        d = by_fid.get(fid) or by_news.get(fid)
        if not d:
            continue
        row = dict(d)
        row["impact_level"] = it.get("impact_level") or "low"
        row["impact_note"] = it.get("impact_note") or it.get("interpretation") or ""
        row["sector_cn"] = it.get("sector") or ""
        china_items.append(row)
    china = {
        "overall_level": ci.get("overall_level") or ("medium" if explicit else "none"),
        "summary_cn": ci.get("summary_cn") or "",
        "analysis_cn": ci.get("analysis_cn") or "",
        "items": china_items,
        "direct_items": [{k: d[k] for k in ("development_id", "kind", "country", "title_cn", "time",
                                            "detail_url", "source_count")} for d in explicit[:8]],
        "regional_items": [{k: d[k] for k in ("development_id", "kind", "country", "title_cn", "time",
                                              "detail_url", "source_count")} for d in regional],
        "ai_based": bool(ci.get("summary_cn")),
    }

    # ── 板块 6：公共卫生与传染病安全 ──
    hs = (brief.get("health_security") or {}) if ai_ok else {}
    health_rows = []
    for d in disease:
        started = d.get("report_date") or d.get("first_report_at")
        health_rows.append({
            "disease": d.get("disease_name_zh") or d.get("disease_name_en") or "—",
            "country_iso3": d.get("country_iso3"),
            "location": d.get("location_raw"),
            "date": started,
            "start_known": bool(started),
            "as_of": d.get("report_date") or d.get("as_of_date"),
            "severity": d.get("severity") or d.get("risk_level") or "",
        })
    health_rows.sort(key=lambda x: str(x.get("as_of") or ""), reverse=True)
    health = {
        "available": bool(health_rows),
        "summary_cn": hs.get("summary_cn") or ("" if health_rows else
                                               "公共卫生数据暂不可用或不足，不作推断。"),
        "issues": hs.get("issues") or [],
        "key_issues": hs.get("key_issues") or [],
        "impact_cn": hs.get("impact_cn") or "",
        "trend": hs.get("trend") or "unclear",
        "confidence": hs.get("confidence") or ("low" if not health_rows else "medium"),
        "ai_based": bool(hs.get("summary_cn")),
        "items": health_rows[:12],
        "countries": sorted({h["country_iso3"] for h in health_rows if h.get("country_iso3")}),
        "start_date_unknown_cn": "起始时间尚未从现有公开数据中确认",
    }

    # ── 板块 7：最新情报流（30 条，全部可点 detail_url）──
    feed_items = []
    for d in all_devs[:80]:
        feed_items.append({
            "detail_id": str(d.get("event_id") or d.get("news_id") or d["development_id"]),
            "kind": d["kind"],
            "title_cn": d["title_cn"] or d.get("title_original") or "（无标题）",
            "localized": d["localized"],
            "country": d["country"],
            "time": d["time"],
            "category_cn": d["category_cn"],
            "sector": d["sector"],
            "importance": d["importance"],
            "level": d["kind"],
            "verification_label": d["verification_label"],
            "source": d["source"],
            "source_count": d["source_count"],
            "tier": d["tier"],
            "summary_cn": d["summary_cn"],
            "original_url": d["original_url"],
            "detail_url": d["detail_url"],
        })

    # ── 板块 8：日报与周报（直接指向当期报告页）──
    reports = {"daily_href": "reports.html", "weekly_href": "reports.html",
               "daily_id": "", "weekly_id": ""}
    try:
        ridx = load_json(data / "views" / "report_index.json", {}) or {}
        rows = ridx.get("reports") or []
        drow = next((r for r in rows if str(r.get("report_type")) == "africa_daily"), None)
        wrow = next((r for r in rows if str(r.get("report_type")) in ("africa_weekly", "weekly")), None)
        if drow:
            reports["daily_id"] = str(drow.get("report_id") or "")
            reports["daily_href"] = "report.html?id=" + str(drow.get("report_id"))
            reports["daily_title"] = drow.get("title_cn") or drow.get("title") or ""
            reports["daily_period"] = "%s → %s" % (str(drow.get("period_start") or "")[:16],
                                                   str(drow.get("period_end") or "")[:16])
        if wrow:
            reports["weekly_id"] = str(wrow.get("report_id") or "")
            reports["weekly_href"] = "report.html?id=" + str(wrow.get("report_id"))
            reports["weekly_title"] = wrow.get("title_cn") or wrow.get("title") or ""
            reports["weekly_period"] = "%s → %s" % (str(wrow.get("period_start") or "")[:16],
                                                    str(wrow.get("period_end") or "")[:16])
    except Exception:  # noqa: BLE001
        pass

    doc = {
        "schema": "homepage-intelligence-view-v2",
        "generated_time": now.isoformat(timespec="seconds"),
        "data_as_of": (exec_view.get("period") or {}).get("data_as_of")
                      or (pack.get("generated_at") or "")[:19],
        "ai": {
            "available": ai_ok,
            "status": brief.get("status") or "unavailable",
            "generated_time": brief.get("generated_time"),
            "input_hash": brief.get("input_hash") or "",
            "gate_version": brief.get("gate_version"),
            "counts": brief.get("counts") or {},
        },
        "overview": overview,
        "metrics": metrics,
        "sectors": sectors,
        "top_developments": top,
        "china_impact": china,
        "health_security": health,
        "latest_intelligence": feed_items[:30],
        "reports": reports,
        "dedup": {
            "raw_items": RAW_ITEMS,
            "deduped_developments": DEDUPED,
            "collapsed_duplicates": COLLAPSED,
            "collapsed_signals_into_verified_event": collapsed_to_event,
            "policy": "signal linked to a verified event → event only; same incident → one development",
        },
        "notes": [
            "news_signal 未经多源核实；verified_event 已核实（层级不得混用）",
            "聚合器保留原始出版方与链接；tier 表示证据角色，不代表真假",
            "每条公开条目均带 detail_url，可直接打开对应详情页",
        ],
    }

    # ── 公开详情投影（intelligence.html 消费；不含内部字段）──
    pub_items = []
    for d in all_devs:
        if not d["localized"]:
            continue
        pub_items.append({
            "item_id": str(d.get("event_id") or d.get("news_id") or d["development_id"]),
            "kind": d["kind"],
            "detail_url": d["detail_url"],
            "title_cn": d["title_cn"],
            "title_original": d["title_original"],
            "summary_cn": d["summary_cn"],
            "country": d["country"],
            "country_iso2": d["country_iso2"],
            "category_cn": d["category_cn"],
            "time": d["time"],
            "verification_status": d["verification_status"],
            "verification_label": d["verification_label"],
            "source": d["source"],
            "source_count": d["source_count"],
            "sources": d.get("sources") or [],
            "original_url": d["original_url"],
            "related_event_id": d.get("event_id") if d["kind"] == "verified_event" else "",
            "severity": d.get("severity") or "",
            "importance": d["importance"],
            "last_updated": now.isoformat(timespec="seconds"),
        })
    pub = {"schema": "intelligence-items-v1", "generated_time": now.isoformat(timespec="seconds"),
           "count": len(pub_items), "items": pub_items}

    doc = _clean(doc)
    pub = _clean(pub)
    if apply:
        write_atomic(root / OUT_VIEW, doc)
        write_atomic(root / OUT_PUBLIC, pub)
    return doc, pub


def main(argv=None):
    ap = argparse.ArgumentParser(description="C7-6 首页情报公开视图（确定性）")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    now = datetime.now(BJT)
    doc, pub = build(Path(args.root), now, apply=args.apply)
    print(json.dumps({
        "overview_ai": doc["overview"]["ai_based"],
        "sectors": len(doc["sectors"]),
        "top_developments": len(doc["top_developments"]),
        "feed": len(doc["latest_intelligence"]),
        "public_items": pub["count"],
        "map_countries": 0,
        "health": doc["health_security"]["available"],
        "dedup": doc["dedup"],
        "china_items": len(doc["china_impact"]["items"]),
        "reports": {"daily": doc["reports"].get("daily_id"), "weekly": doc["reports"].get("weekly_id")},
    }, ensure_ascii=False, indent=1))
    if args.apply:
        print("written: %s / %s" % (OUT_VIEW, OUT_PUBLIC))
    return 0


if __name__ == "__main__":
    sys.exit(main())
