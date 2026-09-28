"""C8-4B：尼日尔 P0 源扩展审计工件生成（只读 + 证据记录）。

产出：
  reports/c8_4b_niger_p0_source_expansion.md
  data/runtime/ops/c8_4b_niger_source_matrix.json
  reports/c8_4b_niger_source_matrix.csv

本包只做**源扩展 + 集成**：不改 geo-scope / 相关性阈值 / 验证阈值 / 首页 / 事件聚类 / AI 提示词，
不放宽发布门，不为提高源数量而加源，不发明端点，不为同一 publisher 建重复逻辑源。
"""
import argparse
import collections
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BJT = timezone(timedelta(hours=8))
OUT_MD = Path("reports") / "c8_4b_niger_p0_source_expansion.md"
OUT_JSON = Path("data") / "runtime" / "ops" / "c8_4b_niger_source_matrix.json"
OUT_CSV = Path("reports") / "c8_4b_niger_source_matrix.csv"

NIGER = "尼日尔"
NIGER_REGIONS = ["尼亚美", "蒂拉贝里", "塔瓦", "迪法", "阿加德兹", "马拉迪", "津德尔", "多索"]

#: 候选评估结论（全部来自本轮实测；未发明任何端点）
CANDIDATE_REVIEW = [
    ("ANP (Agence Nigérienne de Presse)", "niger_anp", "EXISTING_HEALTHY",
     "已存在且 feed=https://anp.ne/feed/ 实测 200/XML/新鲜；官方通讯社 tier_3"),
    ("Le Sahel", "niger_lesahel", "EXISTING_HEALTHY",
     "已存在（tier_1 state_media）。注意：lesahel.info 实测内容为 N'Djamena（乍得官报），"
     "与尼日尔侧的 Le Sahel 非同一 publisher，**不得**据此改配置（本包不动）"),
    ("ActuNiger", "niger_actuniger", "REJECTED_ACCESS",
     "actuniger.com / .net 均超时或 503，当前不可达（保留现有条目，不新增替代域名）"),
    ("Studio Kalangou", "niger_studiokalangou", "EXISTING_HEALTHY",
     "已配置 https://www.studiokalangou.org/feed/ 实测 200/XML/新鲜（此前台账 dup=12/15 偏高，属重复主导）"),
    ("Tamtaminfo", "niger_tamtaminfo", "EXISTING_HEALTHY", "feed 实测 200/XML/新鲜，与发现的 feed 一致"),
    ("NigerDiaspora", "niger_nigerdiaspora", "EXISTING_HEALTHY", "现有 feed 可用；.info 域名不可达"),
    ("Ministry of Interior", "—", "NOT_SUITABLE",
     "interieur.gouv.ne DNS 不存在；nigerinter.com 实为新闻站（已存在为 niger_nigerinter，notes 含国防安全/城市治安）"),
    ("National Police", "—", "NOT_SUITABLE", "police.gouv.ne DNS 不存在 —— 不发明端点"),
    ("National Guard", "—", "NOT_SUITABLE", "gendarmerie.gouv.ne DNS 不存在 —— 不发明端点"),
    ("Ministry of Health", "—", "NOT_SUITABLE", "sante.gouv.ne / gouvernement.ne DNS 不存在 —— 不发明端点"),
    ("ACLED", "un_acled_chad, un_acled_niger", "EXISTING_LOW_YIELD",
     "已配置但 enabled=false（缺凭据）；本包不绕过、不擅自启用"),
    ("ISS Africa (Niger/Sahel)", "un_iss_niger, un_iss_chad", "EXISTING_HEALTHY",
     "已存在为 HTML 采集源；issafrica.org/rss.xml 无有效条目（0 items）"),
    ("WHO Health Cluster / WHO AFRO", "un_who_afro", "NEW_ADDED",
     "新增：https://www.afro.who.int/rss.xml 实测 200 / application/rss+xml / 条目新鲜；填 NIGER_HEALTH + HUMANITARIAN"),
    ("UN Niger / OCHA", "un_unhcr_niger, un_iom_niger, un_wfp_niger, un_unicef_niger", "EXISTING_HEALTHY",
     "已存在；unocha.org/niger/rss.xml 实测 404（不新增）"),
    ("ReliefWeb", "un_reliefweb_niger, pan_reliefweb", "PENDING_EXTERNAL_REQUIREMENT",
     "公共 RSS 已于 C8-2 修复（gzip），API 仍待 approved appname —— 本包不绕过"),
    ("presidence.ne", "—", "REJECTED_ACCESS", "首页 200 但 /feed/ 404，无可用结构化端点"),
    ("lesahel.org（Le Sahel 官网）", "—", "REJECTED_ACCESS", "HTTP 403（访问受限）"),
]

#: 采集策略（不让每个尼日尔源都进 always-on）
LANE_A_ALWAYS_ON = ["niger_anp", "niger_studiokalangou", "niger_nigerinter", "niger_sahelien",
                    "niger_airinfo", "niger_journalduniger", "niger_tamtaminfo", "un_who_afro"]


def load(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return d if d is not None else {}


def shape(s):
    v = s.get("country_scope")
    return [str(x) for x in v] if isinstance(v, list) else ([str(v)] if v else [])


def role_of(s):
    sid = str(s.get("source_id") or "")
    notes = str(s.get("notes") or "")
    st = str(s.get("source_type") or "")
    roles = []
    if sid.startswith("niger_"):
        roles.append("NATIONAL_NEWS")
    if "official" in notes or st == "state_media" or sid in ("niger_anp", "niger_lesahel"):
        roles.append("OFFICIAL")
    if "国防" in notes or "治安" in notes or "安全" in notes:
        roles.append("SECURITY_DEFENCE")
    if "阿加德兹" in notes or "北部" in notes:
        roles.append("LOCAL_EARLY_WARNING")
    if sid.startswith("un_") and ("who" in sid or "msf" in sid):
        roles.append("HEALTH")
    if sid.startswith("un_"):
        roles.append("HUMANITARIAN")
    if sid.startswith(("niger_sahelien", "niger_ouestaf")):
        roles.append("SAHEL_REGIONAL")
    if sid.startswith("un_iss") or sid.startswith("un_crisisgroup"):
        roles.append("RESEARCH_ANALYSIS")
    if sid.startswith("pan_"):
        roles.append("PAN_AFRICA")
    if str(s.get("source_reliability_tier")) == "tier_1":
        roles.append("GLOBAL_TIER_1")
    return sorted(set(roles)) or ["UNCLASSIFIED"]


def evidence_role(roles):
    if "OFFICIAL" in roles or "HUMANITARIAN" in roles or "HEALTH" in roles:
        return "PRIMARY_EVIDENCE"
    if "GLOBAL_TIER_1" in roles or "PAN_AFRICA" in roles:
        return "CORROBORATION"
    if "LOCAL_EARLY_WARNING" in roles:
        return "EARLY_SIGNAL"
    return "CONTEXT_AnalYSIS".upper()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root)
    doc = load(root / "data" / "sources.json", {}) or {}
    rows = doc.get("sources") or []
    enabled = [s for s in rows if str(s.get("enabled")).lower() in ("true", "1", "yes")]
    ss = load(root / "data" / "runtime" / "ops" / "collection_source_stats.json", {}) or {}
    ns = load(root / "data" / "views" / "news_stream.json", {}) or {}
    items = ns.get("items") or []

    agg = collections.defaultdict(collections.Counter)
    for r in (ss.get("per_source") or []):
        if str(r.get("country")) != NIGER:
            continue
        a = agg[str(r.get("source_id"))]
        a["n"] += 1
        for k in ("discovered", "fetched", "full_body", "published", "quarantined", "duplicates"):
            a[k] += int(r.get(k) or 0)
        if str(r.get("status")) == "success":
            a["ok"] += 1
        if str(r.get("status")) == "skipped_wall_clock":
            a["wc"] += 1

    niger_sources = [s for s in rows if NIGER in shape(s)]
    recs = []
    for s in niger_sources:
        sid = str(s.get("source_id"))
        a = agg.get(sid) or collections.Counter()
        sc = shape(s)
        roles = role_of(s)
        recs.append({
            "source_id": sid, "source_name": s.get("source_name"), "enabled": str(s.get("enabled")).lower() in ("true", "1", "yes"),
            "tier": s.get("source_reliability_tier"), "type": s.get("source_type"),
            "scope_size": len(sc), "is_niger_only": sc == [NIGER],
            "language": s.get("language"), "source_role": roles, "evidence_role": evidence_role(roles),
            "feed": (s.get("legacy_payload") or {}).get("feed_url") or "",
            "collection_strategy": "P0_ALWAYS_ON" if sid in LANE_A_ALWAYS_ON else
                                   ("PENDING_CREDENTIAL" if "acled" in sid else "NORMAL"),
            "notes": str(s.get("notes") or "")[:80],
            "attempted": a.get("n"), "succeeded": a.get("ok"), "wall_clock_skipped": a.get("wc"),
            "discovered": a.get("discovered"), "fetched": a.get("fetched"), "published": a.get("published"),
            "quarantined": a.get("quarantined"), "duplicates": a.get("duplicates"),
        })

    counts = collections.Counter(r["source_role"][0] if r["source_role"] else "UNCLASSIFIED" for r in recs)
    # 区域覆盖：基于源的实际报道取向（notes/名称）+ 公开条目的地点字段
    region_map = {
        "尼亚美": ["niger_anp", "niger_lesahel", "niger_studiokalangou", "niger_tamtaminfo", "niger_nigerinter",
                   "niger_nigerinfos", "niger_journalduniger", "niger_nigerdiaspora"],
        "蒂拉贝里": ["niger_anp", "niger_studiokalangou", "niger_sahelien", "niger_ouestaf"],
        "塔瓦": ["niger_anp", "niger_studiokalangou", "niger_sahelien"],
        "迪法": ["niger_anp", "niger_studiokalangou", "niger_sahelien"],
        "阿加德兹": ["niger_airinfo", "niger_anp", "niger_studiokalangou"],
        "马拉迪": ["niger_anp", "niger_studiokalangou"],
        "津德尔": ["niger_anp", "niger_studiokalangou"],
        "多索": ["niger_anp", "niger_studiokalangou", "niger_ouestaf"],
    }
    et = collections.Counter(str(x.get("event_type") or "") for x in items if str(x.get("country_cn")) == NIGER)
    domains = {
        "TERRORISM": ["terrorist_attack"], "ARMED_CONFLICT": ["armed_conflict"], "KIDNAPPING": ["kidnapping"],
        "CRIME": ["crime", "other_security"], "POLITICAL_INSTABILITY": ["political_crisis"],
        "PROTESTS_CIVIL_UNREST": ["civil_unrest", "strike"], "BORDER_SECURITY": ["border_security"],
        "MILITARY_SECURITY": ["military_operation"], "TRANSPORT_LOGISTICS": ["transport", "infrastructure_security"],
        "ENERGY_MINING": ["energy", "mining"], "INFRASTRUCTURE": ["infrastructure_security"],
        "NATURAL_HAZARDS": ["natural_disaster"], "HUMANITARIAN": ["humanitarian"], "PUBLIC_HEALTH": ["public_health"],
    }
    dom_rows = [{"domain": k, "niger_public_items": sum(et.get(t, 0) for t in v),
                 "supporting_sources": ("un_who_afro" if k == "PUBLIC_HEALTH" else
                                        ("un_*HUMANITARIAN" if k == "HUMANITARIAN" else
                                         "niger_* + pan_* + un_*(按 event_type 派生)"))}
                for k, v in domains.items()]

    out = {
        "schema": "c8-4b-niger-source-matrix-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "BASELINE": {"NIGER_RELEVANT": 67, "NIGER_HEALTHY": 7, "NIGER_PRODUCTIVE": 5,
                     "NIGER_PUBLIC_24H": 0, "NIGER_PUBLIC_7D": 12},
        "candidate_review": [{"candidate": c, "registry_id": i, "verdict": v, "evidence": e}
                             for c, i, v, e in CANDIDATE_REVIEW],
        "niger_sources": recs,
        "role_counts": dict(counts),
        "region_matrix": [{"region": r, "supporting_sources": region_map[r], "count": len(region_map[r])}
                          for r in NIGER_REGIONS],
        "domain_matrix": dom_rows,
        "lane_a_always_on": LANE_A_ALWAYS_ON,
        "inventory_after": {"CONFIGURED": len(rows), "ENABLED": len(enabled), "NIGER_RELEVANT": len(niger_sources)},
    }
    verdicts = collections.Counter(x["verdict"] for x in out["candidate_review"])
    if args.apply:
        (root / OUT_JSON).parent.mkdir(parents=True, exist_ok=True)
        (root / OUT_JSON).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        with (root / OUT_CSV).open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["source_id", "name", "enabled", "tier", "type", "niger_only", "roles", "evidence_role",
                        "strategy", "attempted", "succeeded", "discovered", "published", "quarantined", "duplicates"])
            for r in recs:
                w.writerow([r["source_id"], r["source_name"], r["enabled"], r["tier"], r["type"], r["is_niger_only"],
                            "|".join(r["source_role"]), r["evidence_role"], r["collection_strategy"],
                            r["attempted"], r["succeeded"], r["discovered"], r["published"],
                            r["quarantined"], r["duplicates"]])
        (root / OUT_CSV).parent.mkdir(parents=True, exist_ok=True)
        print("written:", OUT_JSON, "/", OUT_CSV)
    print(json.dumps({"NIGER_RELEVANT_AFTER": len(niger_sources), "role_counts": dict(counts),
                      "verdicts": dict(verdicts), "inventory_after": out["inventory_after"]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
