#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C7-5 — 首页情报公开视图（data/views/homepage_intelligence.json）。

确定性装配（不重复任何 canonical 真相）：
  消费 homepage_intelligence_fact_pack（事实包）、当日首页 AI 简报（若 status=ok）、
  executive_summary、news_stream、public/published_events、public/disease_events、countries。
产出前端可直接消费的 8 个板块 + 非洲风险活动地图等级 + 轻量证据线索。

回退（Phase 15）：AI 简报不可用 → 确定性概览；健康数据缺失 → 诚实低数据态；地图缺数据 → 数据不足。
用法：python scripts/ops/homepage_view.py --apply
"""

import argparse
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BJT = timezone(timedelta(hours=8))
OUT = Path("data") / "views" / "homepage_intelligence.json"
PACK = Path("data") / "runtime" / "ops" / "homepage_intelligence_fact_pack.json"
BRIEF_DIR = Path("data") / "intelligence" / "ai" / "homepage"
LOW_DATA_CN = "过去24小时未发现足够高质量公开信息形成明确判断"
NO_CHINA_CN = "过去24小时未发现明确直接涉及中国企业或人员的重大公开安全事件。"

SECTORS = [("terrorism_conflict", "恐怖主义与武装冲突", "Terrorism & Armed Conflict"),
           ("political_social", "政治与社会稳定", "Political & Social Stability"),
           ("crime_public_security", "社会治安与犯罪", "Crime & Public Security"),
           ("military_border_maritime", "军事、边境与海上安全", "Military / Border / Maritime"),
           ("accident_disruption", "重大事故、灾害与运营中断", "Accidents / Disasters / Disruption")]
CAT2SECTOR = {
    "armed_conflict": "terrorism_conflict", "terrorist_attack": "terrorism_conflict",
    "military_operation": "military_border_maritime", "border_security": "military_border_maritime",
    "maritime_security": "military_border_maritime",
    "civil_unrest": "political_social", "strike": "political_social",
    "political_crisis": "political_social", "protest": "political_social",
    "kidnapping": "crime_public_security", "violent_crime": "crime_public_security",
    "banditry": "crime_public_security", "crime": "crime_public_security",
    "robbery": "crime_public_security",
    "natural_disaster": "accident_disruption", "accident": "accident_disruption",
    "public_health": "accident_disruption", "infrastructure": "accident_disruption",
    "transport_disruption": "accident_disruption",
}


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def write_atomic(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def parse_time(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=BJT)
    except ValueError:
        return None


def latest_brief(root):
    d = Path(root) / BRIEF_DIR
    if not d.is_dir():
        return {}
    for p in sorted(d.glob("*.json"), reverse=True):
        try:
            b = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        t = parse_time(b.get("generated_time"))
        if t and (datetime.now(BJT) - t) < timedelta(hours=24):
            return b
    return {}


ISO2_TO_ISO3 = {
    "TD":"TCD","NE":"NER","ML":"MLI","BF":"BFA","CM":"CMR","CF":"CAF","UG":"UGA","RW":"RWA",
    "BI":"BDI","SN":"SEN","GH":"GHA","CI":"CIV","EG":"EGY","DZ":"DZA","TN":"TUN","MA":"MAR",
    "ZW":"ZWE","TZ":"TZA","GA":"GAB","CG":"COG","GN":"GIN","MR":"MRT","BJ":"BEN","CD":"COD",
    "ET":"ETH","KE":"KEN","LY":"LBY","MZ":"MOZ","NG":"NGA","SO":"SOM","SS":"SSD","SD":"SDN",
    "ZA":"ZAF","AO":"AGO","ZM":"ZMB","MW":"MWI","ER":"ERI","DJ":"DJI","GM":"GMB","GW":"GNB",
    "SL":"SLE","LR":"LBR","TG":"TGO","GQ":"GNQ","BW":"BWA","NA":"NAM","LS":"LSO","SZ":"SWZ",
    "MG":"MDG","KM":"COM","MU":"MUS","SC":"SYC","CV":"CPV","ST":"STP",
}


def map_level(sig24, sig7, ev24, severity_high, monitored):
    """确定性风险/活动等级（非 AI）：数据不足必须与低风险区分。"""
    if not monitored:
        return "insufficient_data"
    score = sig24 * 2 + sig7 + ev24 * 3 + severity_high * 4
    if ev24 == 0 and sig24 == 0 and sig7 < 3:
        return "insufficient_data" if sig7 == 0 else "low"
    if score >= 24 or severity_high >= 2:
        return "high"
    if score >= 12:
        return "elevated"
    if score >= 4:
        return "moderate"
    return "low"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root)
    data = root / "data"
    now = datetime.now(BJT)

    pack = load_json(root / PACK, {}) or {}
    brief = latest_brief(root)
    ai_ok = brief.get("status") == "ok"
    exec_view = load_json(data / "views" / "executive_summary.json", {}) or {}
    feed = (load_json(data / "views" / "news_stream.json", {}) or {}).get("items") or []
    pubs = (load_json(data / "public" / "published_events.json", {}) or {}).get("items") or []
    disease = (load_json(data / "public" / "disease_events.json", {}) or {}).get("items") or []
    srcs = (load_json(data / "sources.json", {}) or {}).get("sources") or []
    countries = (load_json(data / "countries.json", {}) or {}).get("countries") \
        or (load_json(data / "countries.json", {}) or {}).get("items") or []
    tier_of_src = {s.get("source_name"): (s.get("source_tier") or "C") for s in srcs}
    role_of_src = {s.get("source_name"): (s.get("source_role") or "local_signal") for s in srcs}

    h24, d7 = now - timedelta(hours=24), now - timedelta(days=7)
    sig, ev = [], []
    for s in feed:
        if s.get("quarantined"):
            continue
        t = parse_time(s.get("last_seen_at") or s.get("observed_at"))
        if t and t >= d7:
            rec = dict(s)
            rec["_t"] = t
            rec["_tier"] = tier_of_src.get(str(s.get("source_name") or ""), "C")
            rec["_role"] = role_of_src.get(str(s.get("source_name") or ""), "local_signal")
            sig.append(rec)
    for e in pubs:
        t = parse_time(e.get("published_time") or e.get("event_time"))
        if t and t >= d7:
            ev.append(dict(e, _t=t))

    sig.sort(key=lambda x: x["_t"], reverse=True)
    ev.sort(key=lambda x: x["_t"], reverse=True)
    sig24 = [x for x in sig if x["_t"] >= h24]
    ev24 = [x for x in ev if x["_t"] >= h24]

    # ── 板块 2：五大领域 ──
    sectors = []
    bs = (brief.get("sectors") or {}) if ai_ok else {}
    sev_rank = {"critical": 3, "high": 2, "medium": 1}
    for key, zh, en in SECTORS:
        s24 = [x for x in sig24 if CAT2SECTOR.get(str(x.get("event_type") or "")) == key]
        e24 = [x for x in ev24 if CAT2SECTOR.get(str(x.get("event_type") or "")) == key]
        s7 = [x for x in sig if CAT2SECTOR.get(str(x.get("event_type") or "")) == key
              and x["_t"] >= now - timedelta(days=3)]
        reps = sorted(ev24 := e24, key=lambda x: (sev_rank.get(str(x.get("event_severity") or ""), 0),
                                                  x["_t"]), reverse=True)[:3]
        reps += sorted(s24, key=lambda x: x["_t"], reverse=True)[:max(0, 4 - len(reps))]
        b = (bs.get(key) or {}) if ai_ok else {}
        has = bool(s24 or e24 or s7)
        sectors.append({
            "key": key, "title_cn": zh, "title_en": en,
            "signals_24h": len(s24), "verified_events_24h": len(e24),
            "assessment_cn": b.get("assessment_cn") or ("" if has else LOW_DATA_CN),
            "trend": b.get("trend") or ("flat" if has else "flat"),
            "confidence": b.get("confidence") or ("low" if not has else "medium"),
            "ai_based": bool(b.get("assessment_cn")),
            "countries": sorted({str(x.get("country_cn") or "") for x in (s24 + e24)} - {""})[:6],
            "developments": [{"country": x.get("country_cn"), "title": (x.get("title_cn") or x.get("title_original") or "")[:110],
                              "time": x["_t"].strftime("%m-%d %H:%M"),
                              "level": "verified_event" if "event_id" in x else "news_signal",
                              "tier": x.get("_tier")} for x in reps],
        })

    # ── 板块 3：重点动态（AI 解读 + 事实字段）──
    facts = pack.get("facts") or {}
    btop = {str(t.get("fact_id")): t for t in ((brief.get("top_developments") or []) if ai_ok else [])}
    cand = []
    for e in ev24[:4]:
        cand.append(("verified_event", e.get("event_id"), e))
    for x in sorted(sig24, key=lambda x: ({"high": 2, "medium": 1}.get(str(x.get("importance")), 0),
                                          x["_t"]), reverse=True):
        if len(cand) >= 8:
            break
        cand.append(("news_signal", None, x))
    top = []
    for level, eid, x in cand[:8]:
        fid = str(eid) if eid else "news:%s" % ""
        f = facts.get(str(eid)) if eid else None
        if f is None:  # 信号：按 dedup 生成同构 id（与事实包一致）
            import hashlib
            fid = "news:%s" % hashlib.sha256(str(x.get("dedup_key") or x.get("news_id")
                                                    or x.get("src_id") or "").encode()).hexdigest()[:16]
            f = facts.get(fid) or {}
        b = btop.get(str(f.get("fact_id") or fid)) or {}
        top.append({
            "level": level,
            "event_id": eid or "",
            "fact_id": f.get("fact_id") or fid,
            "country": x.get("country_cn") or f.get("country"),
            "time": (x.get("_t") or now).strftime("%Y-%m-%d %H:%M"),
            "title": (x.get("title_cn") or x.get("title_original") or f.get("title") or "")[:140],
            "summary": (x.get("summary_cn") or x.get("summary_original") or "")[:200],
            "category_cn": x.get("event_type_cn") or x.get("event_type") or "",
            "source": x.get("source_name") or f.get("source") or "",
            "source_tier": x.get("_tier") or f.get("source_tier") or "C",
            "source_count": int(x.get("independent_source_count") or f.get("source_count") or 1),
            "why_it_matters": b.get("why_it_matters") or "",
            "impact": b.get("impact") or "",
            "watch_points": b.get("watch_points") or "",
            "ai_based": bool(b),
        })

    # ── 板块 4：中国企业与人员影响 ──
    cn_facts = [f for f in facts.values() if f.get("level") == "news_signal" and
                ("china" in json.dumps(f, ensure_ascii=False).lower() or "中国" in json.dumps(f, ensure_ascii=False))]
    cn_flag = [x for x in sig24 if x.get("china_related") is True]
    ci = (brief.get("china_impact") or {}) if ai_ok else {}
    china = {
        "overall_level": ci.get("overall_level") or ("low" if (cn_flag or cn_facts) else "none"),
        "summary_cn": ci.get("summary_cn") or ("" if (cn_flag or cn_facts) else NO_CHINA_CN),
        "items": [dict(i, ai_based=True) for i in (ci.get("items") or [])],
        "candidates": [{"country": x.get("country_cn"),
                        "title": (x.get("title_cn") or x.get("title_original") or "")[:120],
                        "time": x["_t"].strftime("%m-%d %H:%M"),
                        "source": x.get("source_name"), "tier": x.get("_tier"),
                        "evidence": "explicit_china_reference"} for x in cn_flag[:6]],
        "ai_based": bool(ci.get("items")),
    }

    # ── 板块 5：风险与活动地图（确定性）──
    per_country = defaultdict(lambda: {"sig24": 0, "sig7": 0, "ev24": 0, "sev_high": 0})
    for x in sig:
        c = str(x.get("country_cn") or "")
        if c:
            per_country[c]["sig7"] += 1
            if x["_t"] >= h24:
                per_country[c]["sig24"] += 1
    for e in ev:
        c = str(e.get("country_cn") or "")
        if c:
            if str(e.get("event_severity") or "") in ("high", "critical"):
                per_country[c]["sev_high"] += 1
            if e["_t"] >= h24:
                per_country[c]["ev24"] += 1
    cname2iso3 = {}
    cfg_dir = root / "config" / "countries"
    try:
        for fn in sorted(os.listdir(cfg_dir)):
            if fn.endswith(".json"):
                c = load_json(cfg_dir / fn, {})
                if c.get("country"):
                    cname2iso3[c["country"]] = (c.get("iso2") or "").upper()
    except Exception:  # noqa: BLE001
        cname2iso3 = {}
    monitored = [str(c.get("country") or c.get("name") or "") for c in countries if (c.get("country") or c.get("name"))]
    levels = []
    for c, d in per_country.items():
        levels.append({"country": c, "iso2": cname2iso3.get(c, ""),
                       "iso3": ISO2_TO_ISO3.get(cname2iso3.get(c, ""), ""),
                       "sig24": d["sig24"], "sig7": d["sig7"],
                       "ev24": d["ev24"], "level": map_level(d["sig24"], d["sig7"], d["ev24"],
                                                              d["sev_high"], True)})
    levels.sort(key=lambda x: ({"high": 3, "elevated": 2, "moderate": 1, "low": 0,
                                "insufficient_data": -1}[x["level"]], x["sig7"]), reverse=True)
    covered = {x["country"] for x in levels}
    for c in monitored:
        if c and c not in covered:
            levels.append({"country": c, "iso2": cname2iso3.get(c, ""), "iso3": ISO2_TO_ISO3.get(cname2iso3.get(c, ""), ""),
                           "sig24": 0, "sig7": 0,
                           "ev24": 0, "level": "insufficient_data"})

    # ── 板块 6：公共卫生与传染病安全 ──
    hs = (brief.get("health_security") or {}) if ai_ok else {}
    health_rows = [{"disease": d.get("disease_name_zh") or d.get("disease_name_en"),
                    "country_iso3": d.get("country_iso3"), "date": d.get("report_date"),
                    "location": d.get("location_raw")} for d in disease]
    health = {"available": bool(health_rows),
              "summary_cn": hs.get("summary_cn") or ("" if health_rows else
                                                     "公共卫生数据暂不可用或不足，不作推断。"),
              "key_issues": hs.get("key_issues") or [],
              "impact_cn": hs.get("impact_cn") or "",
              "confidence": hs.get("confidence") or ("low" if not health_rows else "medium"),
              "ai_based": bool(hs.get("summary_cn")),
              "items": health_rows[:10],
              "countries": sorted({h["country_iso3"] for h in health_rows if h.get("country_iso3")})}

    # ── 板块 7：最新情报流（20–30 条 + 过滤器分类）──
    feed_items = [{
        "country": x.get("country_cn") or "未识别",
        "title": (x.get("title_cn") or x.get("title_original") or "")[:160],
        "translated": bool(x.get("localized")),
        "category_cn": x.get("event_type_cn") or x.get("event_type") or "其他",
        "sector": CAT2SECTOR.get(str(x.get("event_type") or ""), "other"),
        "importance": x.get("importance") or "low",
        "level": "news_signal",
        "source": x.get("source_name") or "",
        "source_tier": x.get("_tier"),
        "time": x["_t"].strftime("%Y-%m-%d %H:%M"),
        "why_it_matters": (x.get("why_it_matters") or "")[:120],
    } for x in sig[:30]]

    doc = {
        "schema": "homepage-intelligence-v1",
        "generated_time": now.isoformat(timespec="seconds"),
        "ai": {"available": ai_ok, "status": brief.get("status") or "unavailable",
               "generated_time": brief.get("generated_time"),
               "model": brief.get("model"), "input_hash": (brief.get("input_hash") or "")[:12],
               "counts": brief.get("counts") or pack.get("counts") or {}},
        "overview": {
            "summary_cn": (brief.get("overall_assessment") or {}).get("summary_cn")
            or exec_view.get("overall_assessment") or "",
            "risk_direction": (brief.get("overall_assessment") or {}).get("risk_direction")
            or exec_view.get("risk_direction") or "",
            "confidence": (brief.get("overall_assessment") or {}).get("confidence")
            or exec_view.get("confidence") or "low",
            "key_judgments": (brief.get("overall_assessment") or {}).get("key_judgments") or [],
            "watch_24_72h": (brief.get("overall_assessment") or {}).get("watch_24_72h") or [],
            "ai_based": ai_ok and bool((brief.get("overall_assessment") or {}).get("summary_cn")),
        },
        "metrics": {
            "signals_24h": len(sig24), "verified_events_24h": len(ev24),
            "countries_24h": len({str(x.get("country_cn") or "") for x in sig24} |
                                 {str(e.get("country_cn") or "") for e in ev24} - {""}),
            "countries_7d": len({str(x.get("country_cn") or "") for x in sig} - {""}),
            "high_attention": len([t for t in top if t["level"] == "verified_event" or
                                   t["source_tier"] == "A"]),
            "source_tier_distribution": [{"tier": k, "count": v} for k, v in
                                         Counter(x.get("_tier") for x in sig).most_common()],
        },
        "sectors": sectors,
        "top_developments": top,
        "china_impact": china,
        "map": {"label_cn": "非洲安全风险与活动态势", "levels": levels,
                "legend": [{"level": "high", "label_cn": "高"}, {"level": "elevated", "label_cn": "偏高"},
                           {"level": "moderate", "label_cn": "中等"}, {"level": "low", "label_cn": "低"},
                           {"level": "insufficient_data", "label_cn": "数据不足"}],
                "scoring": "deterministic(v1): signals24*2 + signals7 + events24*3 + high_severity*4；"
                           "数据不足 ≠ 低风险"},
        "health_security": health,
        "latest_intelligence": feed_items,
        "reports": {"daily_href": "reports.html", "weekly_href": "reports.html"},
        "notes": ["news_signal 未经多源核实；verified_event 已核实（层级不得混用）",
                  "聚合器保留原始出版方与链接；tier 表示证据角色，不代表真假"],
    }
    print(json.dumps({"overview_ai": doc["overview"]["ai_based"], "sectors": len(sectors),
                      "top": len(top), "china_items": len(china["items"]),
                      "map_countries": len(levels), "feed": len(feed_items),
                      "health": health["available"]}, ensure_ascii=False, indent=1))
    if args.apply:
        write_atomic(root / OUT, doc)
        print(json.dumps({"written": str(root / OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
