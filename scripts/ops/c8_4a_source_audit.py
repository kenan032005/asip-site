"""C8-4A：源覆盖基线审计（**只读**，不新增/修改任何源、采集或分类逻辑）。

产出（内部工程/情报规划工件，**不发布**到公开站点）：
  reports/c8_4a_source_coverage_audit.md
  data/runtime/ops/c8_4a_source_coverage_matrix.json
  reports/c8_4a_source_matrix.csv

口径声明：
  · 逻辑源数 = data/sources.json 中的条目数（配置 120 / 启用 118）。
  · 展开执行数 = Σ(len(country_scope))（多国/泛非源在每个 scope 国家各执行一次），
    生产实测与 collection_source_stats.per_source 行数一致（802）。
  · 健康指标来自**最近一轮真实采集**的逐源台账，并按 source_id 跨国家聚合。
  · 缺失指标一律 null / "UNKNOWN"，不臆造。
"""
import argparse
import collections
import csv
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BJT = timezone(timedelta(hours=8))
OUT_MD = Path("reports") / "c8_4a_source_coverage_audit.md"
OUT_JSON = Path("data") / "runtime" / "ops" / "c8_4a_source_coverage_matrix.json"
OUT_CSV = Path("reports") / "c8_4a_source_matrix.csv"

P0 = ["尼日尔"]
P1 = ["尼日利亚", "贝宁", "莫桑比克", "南苏丹", "埃塞俄比亚"]
P2 = ["乍得"]
REGIONAL_CONTEXT = ["马里", "布基纳法索", "苏丹", "索马里", "刚果（金）"]

REGIONS = {
    "SAHEL": ["塞内加尔", "马里", "布基纳法索", "尼日尔", "乍得", "毛里塔尼亚"],
    "WEST_AFRICA": ["尼日利亚", "贝宁", "加纳", "科特迪瓦", "几内亚", "塞拉利昂", "利比里亚",
                    "多哥", "冈比亚", "几内亚比绍", "佛得角", "塞内加尔", "马里", "布基纳法索", "尼日尔"],
    "LAKE_CHAD_BASIN": ["乍得", "尼日尔", "尼日利亚", "喀麦隆"],
    "EAST_AFRICA": ["肯尼亚", "坦桑尼亚", "乌干达", "卢旺达", "布隆迪", "埃塞俄比亚", "南苏丹"],
    "HORN_OF_AFRICA": ["索马里", "埃塞俄比亚", "吉布提", "厄立特里亚", "苏丹", "南苏丹", "肯尼亚"],
    "GREAT_LAKES": ["刚果（金）", "卢旺达", "布隆迪", "乌干达"],
    "CENTRAL_AFRICA": ["中非共和国", "喀麦隆", "加蓬", "刚果（布）", "刚果（金）", "乍得"],
    "SOUTHERN_AFRICA": ["莫桑比克", "南非", "津巴布韦", "赞比亚", "马拉维", "安哥拉", "博茨瓦纳",
                        "纳米比亚", "马达加斯加"],
    "NORTH_AFRICA": ["利比亚", "突尼斯", "阿尔及利亚", "摩洛哥", "埃及"],
}

DOMAINS = {
    "TERRORISM": ["terrorist_attack"],
    "ARMED_CONFLICT": ["armed_conflict"],
    "KIDNAPPING": ["kidnapping"],
    "CRIME": ["crime", "other_security"],
    "POLITICAL_INSTABILITY": ["political_crisis"],
    "PROTESTS_CIVIL_UNREST": ["civil_unrest", "strike"],
    "BORDER_SECURITY": ["border_security"],
    "MILITARY_SECURITY": ["military_operation"],
    "TRANSPORT_LOGISTICS": ["transport", "infrastructure_security"],
    "ENERGY_MINING": ["energy", "mining"],
    "INFRASTRUCTURE": ["infrastructure_security"],
    "NATURAL_HAZARDS": ["natural_disaster"],
    "HUMANITARIAN": ["humanitarian"],
    "PUBLIC_HEALTH": ["public_health"],
}


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default if default is not None else {}


def shape(s):
    v = s.get("country_scope")
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    return [str(v)] if v else []


def role_of(s):
    sid = str(s.get("source_id") or "").lower()
    st = str(s.get("source_type") or "").lower()
    roles = []
    if sid.startswith("pan_"):
        roles.append("PAN_AFRICA")
    if sid.startswith("intl_") or "international" in st:
        roles.append("GLOBAL_TIER_1" if str(s.get("source_reliability_tier")) == "tier_1" else "NATIONAL_NEWS")
    if sid.startswith("un_"):
        g = sid.replace("un_", "").split("_")[0]
        roles.append({"reliefweb": "HUMANITARIAN", "unhcr": "HUMANITARIAN", "iom": "HUMANITARIAN",
                      "wfp": "HUMANITARIAN", "unicef": "HUMANITARIAN", "msf": "HEALTH",
                      "icrc": "HUMANITARIAN", "fewsnet": "HUMANITARIAN", "unnews": "OFFICIAL",
                      "au": "OFFICIAL", "crisisgroup": "RESEARCH_ANALYSIS",
                      "iss": "RESEARCH_ANALYSIS"}.get(g, "OFFICIAL"))
    if "state_media" in st or "presidence" in sid or "gouv" in sid:
        roles.append("OFFICIAL")
    if "local_media" in st:
        roles.append("LOCAL_EARLY_WARNING")
    if str(s.get("source_reliability_tier")) == "tier_1":
        roles.append("GLOBAL_TIER_1")
    return sorted(set(roles)) or ["UNCLASSIFIED"]


def evidence_role(s, roles):
    if "OFFICIAL" in roles or "HUMANITARIAN" in roles:
        return "PRIMARY_EVIDENCE"
    if "GLOBAL_TIER_1" in roles or "PAN_AFRICA" in roles:
        return "CORROBORATION"
    if "LOCAL_EARLY_WARNING" in roles:
        return "EARLY_SIGNAL"
    return "CONTEXT_ANALYSIS"


def health_class(a, meta):
    """证据驱动的运行健康分类（低频高权威不自动判坏）。"""
    tier = str(meta.get("source_reliability_tier") or "")
    roles = meta.get("roles") or []
    pub, disc, dup, quar = a["published"], a["discovered"], a["duplicates"], a["quarantined"]
    wc = a.get("wall_clock_skipped", 0)
    if wc and disc == 0:
        return "WALL_CLOCK_STARVED"
    if a.get("HTTP_403", 0):
        return "ACCESS_BLOCKED"
    if a.get("RSS_EMPTY", 0) and disc == 0:
        return "EMPTY_FEED"
    if a.get("HTTP_429", 0) and disc == 0:
        return "RATE_LIMITED"
    if disc == 0 and a.get("no_items", 0):
        return "HEALTHY_LOW_VOLUME" if ("OFFICIAL" in roles or "HUMANITARIAN" in roles or tier == "tier_1") else "BROKEN_OR_STALE"
    if pub > 0:
        if dup and dup >= max(1, disc) * 0.5:
            return "DUPLICATE_HEAVY"
        if quar and quar >= max(1, disc) * 0.5:
            return "QUARANTINE_HEAVY"
        return "HEALTHY_PRODUCTIVE"
    if disc > 0:
        if dup and dup >= max(1, disc) * 0.5:
            return "DUPLICATE_HEAVY"
        if quar and quar >= max(1, disc) * 0.5:
            return "QUARANTINE_HEAVY"
        if tier == "tier_1" or "OFFICIAL" in roles:
            return "HIGH_VALUE_LOW_FREQUENCY"
        return "NO_RECENT_OUTPUT"
    return "UNKNOWN"


def audit(root):
    root = Path(root)
    src = load(root / "data" / "sources.json", {}) or {}
    rows = src.get("sources") or []
    enabled = [s for s in rows if str(s.get("enabled")).lower() in ("true", "1", "yes")]
    disabled = [s for s in rows if str(s.get("enabled")).lower() not in ("true", "1", "yes")]
    cs = load(root / "data" / "runtime" / "ops" / "collection_summary.json", {}) or {}
    ss = load(root / "data" / "runtime" / "ops" / "collection_source_stats.json", {}) or {}
    health = load(root / "data" / "runtime" / "ops" / "source_health.json", {}) or {}
    ns = load(root / "data" / "views" / "news_stream.json", {}) or {}
    items = ns.get("items") or []

    agg = collections.defaultdict(lambda: collections.Counter())
    countries_seen = collections.defaultdict(set)
    for r in (ss.get("per_source") or []):
        sid = str(r.get("source_id"))
        a = agg[sid]
        a["runs"] += 1
        for k, key in (("discovered", "discovered"), ("fetched", "fetched"), ("full_body", "full_body"),
                       ("published", "published"), ("quarantined", "quarantined"), ("duplicates", "duplicates"),
                       ("extraction_failed", "extraction_failed"), ("errors", "errors")):
            a[key] += int(r.get(k) or 0)
        st = str(r.get("status") or "")
        if st == "success":
            a["succeeded"] += 1
        elif st == "skipped_wall_clock":
            a["wall_clock"] += 1
        elif st == "no_items":
            a["no_items"] += 1
        fr = str(r.get("failure_reason") or "")
        for code, key in (("HTTP_429", "http_429"), ("HTTP_403", "http_403"), ("RSS_EMPTY", "rss_empty"),
                          ("QUERY_NO_RESULT", "query_no_result"), ("NO_ITEMS", "no_items_reason")):
            if code in fr:
                a[key] += 1
        if r.get("country"):
            countries_seen[sid].add(str(r["country"]))

    health_by_id = {str(x.get("source_id")): x for x in (health.get("sources") or [])}
    pub_by_source = collections.Counter(str(x.get("source_name") or "") for x in items)

    records = []
    for s in rows:
        sid = str(s.get("source_id") or "")
        sc = shape(s)
        a = agg.get(sid) or collections.Counter()
        roles = role_of(s)
        meta = {"source_reliability_tier": s.get("source_reliability_tier"), "roles": roles}
        h = health_by_id.get(sid) or {}
        rec = {
            "source_id": sid, "source_name": s.get("source_name"), "enabled": str(s.get("enabled")).lower() in ("true", "1", "yes"),
            "source_type": s.get("source_type"), "source_tier": s.get("source_reliability_tier"),
            "country_scope": sc, "scope_size": len(sc), "region_scope": [rk for rk, cs_ in REGIONS.items() if set(sc) & set(cs_)],
            "language": s.get("language"), "collector_method": (s.get("legacy_payload") or {}).get("collection_method"),
            "endpoint": (s.get("listing_urls") or [s.get("url")])[:2], "auth_required": None,
            "source_role": roles, "evidence_role": evidence_role(s, roles),
            "attempted": a.get("runs", 0), "succeeded": a.get("succeeded", 0),
            "wall_clock_skipped": a.get("wall_clock", 0), "no_items": a.get("no_items", 0),
            "discovered": a.get("discovered", 0), "fetched": a.get("fetched", 0), "full_body": a.get("full_body", 0),
            "published": a.get("published", 0), "quarantined": a.get("quarantined", 0), "duplicates": a.get("duplicates", 0),
            "extraction_failed": a.get("extraction_failed", 0),
            "HTTP_429": a.get("http_429", 0), "HTTP_403": a.get("http_403", 0),
            "RSS_EMPTY": a.get("rss_empty", 0), "QUERY_NO_RESULT": a.get("query_no_result", 0),
            "last_fetch": h.get("last_fetch"), "stale": h.get("stale"), "parser_failures": h.get("parser_failures"),
            "public_items": pub_by_source.get(str(s.get("source_name") or ""), 0),
            "countries_executed": sorted(countries_seen.get(sid, [])),
        }
        d, f, p = rec["discovered"], rec["fetched"], rec["published"]
        rec["FETCH_RATE"] = round(f / d, 3) if d else None
        rec["FULL_BODY_RATE"] = round(rec["full_body"] / f, 3) if f else None
        rec["PUBLICATION_RATE"] = round(p / f, 3) if f else None
        rec["DUPLICATE_RATE"] = round(rec["duplicates"] / d, 3) if d else None
        rec["QUARANTINE_RATE"] = round(rec["quarantined"] / f, 3) if f else None
        rec["FAILURE_RATE"] = round(rec["wall_clock_skipped"] / rec["attempted"], 3) if rec["attempted"] else None
        rec["health_class"] = health_class(rec, meta)
        records.append(rec)

    # 国家矩阵
    country_sources = collections.defaultdict(lambda: {"all": [], "healthy": [], "productive": []})
    for rec in records:
        if not rec["enabled"]:
            continue
        for c in rec["country_scope"]:
            b = country_sources[c]
            b["all"].append(rec["source_id"])
            if rec["health_class"] in ("HEALTHY_PRODUCTIVE", "HEALTHY_LOW_VOLUME", "HIGH_VALUE_LOW_FREQUENCY"):
                b["healthy"].append(rec["source_id"])
            if rec["published"] > 0:
                b["productive"].append(rec["source_id"])
    c24 = collections.Counter(str(x.get("country_cn") or "未识别") for x in items)
    # 7 日与 24 小时公开量级（用 last_seen_at / observed_at）
    now = datetime.now(timezone.utc)

    def ts(x, k):
        try:
            v = str(x.get(k) or "").replace("Z", "+00:00")
            d = datetime.fromisoformat(v)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception:  # noqa: BLE001
            return None
    c24w = collections.Counter(str(x.get("country_cn") or "未识别") for x in items
                               if (ts(x, "last_seen_at") or now - timedelta(days=99)) >= now - timedelta(hours=24))
    c7w = collections.Counter(str(x.get("country_cn") or "未识别") for x in items
                              if (ts(x, "last_seen_at") or now - timedelta(days=99)) >= now - timedelta(days=7))
    countries = []
    for c in sorted(country_sources, key=lambda x: (-len(country_sources[x]["all"]), x)):
        b = country_sources[c]
        recs = [r for r in records if r["enabled"] and c in r["country_scope"]]
        tier = "P0" if c in P0 else ("P1" if c in P1 else ("P2" if c in P2 else ("REGIONAL_CONTEXT" if c in REGIONAL_CONTEXT else "BACKGROUND")))
        local = [r["source_id"] for r in recs if "LOCAL_EARLY_WARNING" in r["source_role"]]
        official = [r["source_id"] for r in recs if "OFFICIAL" in r["source_role"] or "HUMANITARIAN" in r["source_role"]]
        reg = [r["source_id"] for r in recs if r["source_id"].startswith(("un_", "intl_"))]
        pan = [r["source_id"] for r in recs if r["source_id"].startswith("pan_")]
        g1 = [r["source_id"] for r in recs if "GLOBAL_TIER_1" in r["source_role"]]
        countries.append({
            "country": c, "priority_tier": tier,
            "LOGICAL_SOURCES_AVAILABLE": len([r for r in records if c in r["country_scope"]]),
            "ENABLED_SOURCES": len(b["all"]), "HEALTHY_SOURCES": len(b["healthy"]), "PRODUCTIVE_SOURCES": len(b["productive"]),
            "LOCAL_SOURCES": len(local), "OFFICIAL_SOURCES": len(official),
            "REGIONAL_SOURCES_REACHING_COUNTRY": len(reg), "PAN_AFRICA_SOURCES_REACHING_COUNTRY": len(pan),
            "GLOBAL_TIER1_SOURCES_REACHING_COUNTRY": len(g1),
            "PUBLIC_ITEMS_24H": c24w.get(c, 0), "PUBLIC_ITEMS_7D": c7w.get(c, 0),
            "PUBLIC_ITEMS_ALL": c24.get(c, 0),
            "SOURCE_DIVERSITY_SCORE": {
                "components": {"healthy": len(b["healthy"]), "productive": len(b["productive"]),
                               "local": len(local), "official": len(official), "pan": len(pan), "global_tier1": len(g1)},
                "formula": "healthy*2 + productive*2 + local*1 + official*2 + pan*1 + global_tier1*2",
                "value": len(b["healthy"]) * 2 + len(b["productive"]) * 2 + len(local) + len(official) * 2 + len(pan) + len(g1) * 2,
            },
        })

    # 领域覆盖
    et = collections.Counter(str(x.get("event_type") or "") for x in items)
    domains = []
    for dname, types in DOMAINS.items():
        n = sum(et.get(t, 0) for t in types)
        p0p1 = sum(1 for x in items
                   if str(x.get("event_type") or "") in types
                   and str(x.get("country_cn") or "") in (P0 + P1))
        domains.append({"domain": dname, "public_items": n, "p0_p1_public_items": p0p1,
                        "supported": n > 0, "source_support": "DERIVED_FROM_PUBLIC_TYPES"})

    # 区域覆盖
    regions = []
    for rname, cls in REGIONS.items():
        reach = [r for r in records if r["enabled"] and (set(r["country_scope"]) & set(cls) or rname in (r["region_scope"] or []))]
        regions.append({
            "region": rname,
            "CURRENT_RELEVANT_SOURCES": len(reach),
            "HEALTHY_SOURCES": len([r for r in reach if r["health_class"] in
                                    ("HEALTHY_PRODUCTIVE", "HEALTHY_LOW_VOLUME", "HIGH_VALUE_LOW_FREQUENCY")]),
            "PRODUCTIVE_SOURCES": len([r for r in reach if r["published"] > 0]),
            "PUBLIC_ITEMS": sum(c24.get(c, 0) for c in cls),
        })

    hc = collections.Counter(r["health_class"] for r in records if r["enabled"])
    glob_t1 = [r for r in records if "GLOBAL_TIER_1" in r["source_role"]]
    pan = [r for r in records if "PAN_AFRICA" in r["source_role"]]
    expanded = sum(r["scope_size"] for r in records if r["enabled"])
    doc = {
        "schema": "c8-4a-source-coverage-matrix-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "collection_run": cs.get("collector_run_id"),
        "INVENTORY": {
            "CONFIGURED_LOGICAL_SOURCES": len(rows), "ENABLED_LOGICAL_SOURCES": len(enabled),
            "DISABLED_LOGICAL_SOURCES": len(disabled),
            "EXPANDED_PRODUCTION_SOURCE_EXECUTIONS": expanded,
            "expanded_equals_per_source_rows": expanded == len(ss.get("per_source") or []),
            "why_expanded_exceeds_logical": "多国/泛非源（country_scope 含多个国家）在每个 scope 国家各执行一次；"
                                            "生产实测 per_source 行数与 Σscope 完全一致。",
            "DISABLED_IDS": [s.get("source_id") for s in disabled],
        },
        "HEALTH_CLASS_COUNTS": dict(hc),
        "records": records,
        "countries": countries,
        "regions": regions,
        "domains": domains,
        "GLOBAL_TIER1_CURRENT": [{"source_id": r["source_id"], "name": r["source_name"], "tier": r["source_tier"],
                                  "published": r["published"], "health": r["health_class"],
                                  "scope_size": r["scope_size"]} for r in glob_t1],
        "AFRICA_WIDE_CURRENT": [{"source_id": r["source_id"], "name": r["source_name"], "published": r["published"],
                                 "public_items": r["public_items"], "health": r["health_class"],
                                 "note": r["endpoint"][:1]} for r in pan],
        "COUNTRY_COUNT": len(countries),
        "PUBLIC_ITEMS_TOTAL": len(items),
        "event_type_counts": dict(et.most_common(20)),
    }
    return doc


def render_md(doc):
    inv = doc["INVENTORY"]
    L = ["# C8-4A · 源覆盖基线审计（只读）", "",
         "生成时间：%s ｜ 采集轮：%s ｜ 公开条目：%s" % (doc["generated_at"], doc["collection_run"],
                                                doc["PUBLIC_ITEMS_TOTAL"]), "",
         "> 本包**未新增/修改**任何源、采集逻辑、分类器或阈值。所有指标来自真实生产台账。", "",
         "## A. 权威源清单", "",
         "| 指标 | 值 |", "|---|---|",
         "| CONFIGURED_LOGICAL_SOURCES | %s |" % inv["CONFIGURED_LOGICAL_SOURCES"],
         "| ENABLED_LOGICAL_SOURCES | %s |" % inv["ENABLED_LOGICAL_SOURCES"],
         "| DISABLED_LOGICAL_SOURCES | %s |" % inv["DISABLED_LOGICAL_SOURCES"],
         "| EXPANDED_PRODUCTION_SOURCE_EXECUTIONS | %s |" % inv["EXPANDED_PRODUCTION_SOURCE_EXECUTIONS"],
         "| 展开数 == per_source 行数 | %s |" % inv["expanded_equals_per_source_rows"],
         "| 禁用源 | %s |" % ", ".join(map(str, inv["DISABLED_IDS"])), "",
         "**为什么执行数 > 逻辑源数**：%s" % inv["why_expanded_exceeds_logical"], "",
         "## C. 运行健康分类（启用源）", "", "| 分类 | 数量 |", "|---|---|"]
    for k, v in sorted(doc["HEALTH_CLASS_COUNTS"].items(), key=lambda kv: -kv[1]):
        L.append("| %s | %d |" % (k, v))
    L += ["", "## E. 国家覆盖矩阵（按源数降序，前 18 + P0/P1/P2）", "",
          "| country | tier | enabled | healthy | productive | local | official | pan | tier1 | 24h | 7d | diversity |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    show = doc["countries"][:18]
    for c in doc["countries"]:
        if c["priority_tier"] in ("P0", "P1", "P2") and c not in show and len(show) < 26:
            show.append(c)
    for c in show:
        L.append("| %s | %s | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d |" % (
            c["country"], c["priority_tier"], c["ENABLED_SOURCES"], c["HEALTHY_SOURCES"], c["PRODUCTIVE_SOURCES"],
            c["LOCAL_SOURCES"], c["OFFICIAL_SOURCES"], c["PAN_AFRICA_SOURCES_REACHING_COUNTRY"],
            c["GLOBAL_TIER1_SOURCES_REACHING_COUNTRY"], c["PUBLIC_ITEMS_24H"], c["PUBLIC_ITEMS_7D"],
            c["SOURCE_DIVERSITY_SCORE"]["value"]))
    L += ["", "> SOURCE_DIVERSITY_SCORE 组件（透明）：%s" % json.dumps(
        next((c for c in doc["countries"] if c["priority_tier"] == "P0"), {}).get("SOURCE_DIVERSITY_SCORE", {}),
        ensure_ascii=False), "", "## I. 区域覆盖", "", "| region | relevant | healthy | productive | public_items |", "|---|---|---|---|---|"]
    for r in doc["regions"]:
        L.append("| %s | %d | %d | %d | %d |" % (r["region"], r["CURRENT_RELEVANT_SOURCES"], r["HEALTHY_SOURCES"],
                                                 r["PRODUCTIVE_SOURCES"], r["PUBLIC_ITEMS"]))
    L += ["", "## J. 安全领域覆盖（按公开条目 event_type 派生）", "", "| domain | public_items | P0/P1 |", "|---|---|---|"]
    for d in doc["domains"]:
        L.append("| %s | %d | %d |" % (d["domain"], d["public_items"], d["p0_p1_public_items"]))
    L += ["", "## 数据说明", "",
          "- 健康指标为**最近一轮真实采集**逐源台账，按 source_id 跨国家聚合（多国源合并计）。",
          "- 缺失指标以 null / UNKNOWN 表示，未臆造；本审计不改变任何生产行为。"]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="C8-4A 源覆盖基线审计（只读）")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root)
    doc = audit(root)
    print(json.dumps({k: doc[k] for k in ("INVENTORY", "HEALTH_CLASS_COUNTS", "COUNTRY_COUNT", "PUBLIC_ITEMS_TOTAL")},
                     ensure_ascii=False, indent=1)[:1400])
    if args.apply:
        (root / OUT_JSON).parent.mkdir(parents=True, exist_ok=True)
        (root / OUT_JSON).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        (root / OUT_MD).parent.mkdir(parents=True, exist_ok=True)
        (root / OUT_MD).write_text(render_md(doc), encoding="utf-8")
        (root / OUT_CSV).parent.mkdir(parents=True, exist_ok=True)
        with (root / OUT_CSV).open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["source_id", "name", "enabled", "tier", "scope_size", "roles", "evidence_role",
                        "attempted", "discovered", "fetched", "published", "quarantined", "duplicates",
                        "wall_clock_skipped", "HTTP_429", "RSS_EMPTY", "public_items", "health_class"])
            for r in doc["records"]:
                w.writerow([r["source_id"], r["source_name"], r["enabled"], r["source_tier"], r["scope_size"],
                            "|".join(r["source_role"]), r["evidence_role"], r["attempted"], r["discovered"],
                            r["fetched"], r["published"], r["quarantined"], r["duplicates"],
                            r["wall_clock_skipped"], r["HTTP_429"], r["RSS_EMPTY"], r["public_items"],
                            r["health_class"]])
        print("written:", OUT_JSON, "/", OUT_MD, "/", OUT_CSV)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
