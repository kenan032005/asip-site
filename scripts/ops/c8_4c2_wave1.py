"""C8-4C2 WAVE 1：写入 16 个 P1 保证核心源 + stage3 PHASE 1 排序。"""
import ast
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# id, country, name, url, feed, method, roles, evidence_role, tier, note
W1 = [
    ("nga_gov_portal", "尼日利亚", "Federal Government Portal", "https://nigeria.gov.ng/",
     "https://nigeria.gov.ng/feed/", "rss", ["OFFICIAL"], "PRIMARY_EVIDENCE", "tier_2", "官方门户（严格重验全绿）"),
    ("nga_health_moh", "尼日利亚", "Federal Ministry of Health", "https://www.health.gov.ng/",
     "https://health.gov.ng/feed/", "rss", ["OFFICIAL", "HEALTH"], "PRIMARY_EVIDENCE", "tier_2", "联邦卫生部（全绿+新鲜）"),
    ("nga_nan", "尼日利亚", "News Agency of Nigeria", "https://nannews.ng/",
     "https://nannews.ng/feed/", "rss", ["NATIONAL_NEWS"], "CORROBORATION", "tier_2", "国家通讯社（全绿+新鲜）"),
    ("nga_transport_moh", "尼日利亚", "Federal Ministry of Transportation", "https://transportation.gov.ng/",
     "http://transportation.gov.ng/feed/", "rss", ["OFFICIAL", "TRANSPORT_INFRASTRUCTURE"], "PRIMARY_EVIDENCE", "tier_2", "交通部（全绿）"),
    ("nga_icir", "尼日利亚", "International Centre for Investigative Reporting", "https://www.icirnigeria.org/",
     "https://www.icirnigeria.org/feed/", "rss", ["RESEARCH_ANALYSIS"], "CONTEXT_ANALYSIS", "tier_2", "调查报道（全绿+新鲜）"),
    ("ben_gouv", "贝宁", "Gouvernement du Benin", "https://www.gouv.bj/", "",
     "html_listing", ["OFFICIAL"], "PRIMARY_EVIDENCE", "tier_2", "政府门户（全绿+新鲜）"),
    ("ben_sante", "贝宁", "Ministere de la Sante (Benin)", "https://sante.gouv.bj/", "",
     "html_listing", ["OFFICIAL", "HEALTH"], "PRIMARY_EVIDENCE", "tier_2", "卫生部（全绿）"),
    ("ben_fraternite", "贝宁", "Fraternite (官方日报)", "https://fraternite.bj/",
     "https://fraternite.bj/feed/", "rss", ["OFFICIAL", "NATIONAL_NEWS"], "PRIMARY_EVIDENCE", "tier_2", "官方日报（全绿+新鲜）"),
    ("moz_gov_portal", "莫桑比克", "Portal do Governo de Mocambique", "https://www.portaldogoverno.gov.mz/",
     "https://portaldogoverno.gov.mz/feed/", "rss", ["OFFICIAL"], "PRIMARY_EVIDENCE", "tier_2", "政府门户（全绿+新鲜）"),
    ("moz_defence", "莫桑比克", "Ministerio da Defesa Nacional", "https://www.mdn.gov.mz/",
     "https://mdn.gov.mz/index.php/feed/", "rss", ["SECURITY_DEFENCE"], "PRIMARY_EVIDENCE", "tier_2", "国防部（全绿）"),
    ("moz_zitamar", "莫桑比克", "Zitamar News", "https://zitamar.com/",
     "https://www.zitamar.com/rss/", "rss", ["RESEARCH_ANALYSIS", "LOCAL_EARLY_WARNING"], "CONTEXT_ANALYSIS", "tier_2",
     "Cabo Delgado 专精（全绿+新鲜）"),
    ("ssd_eyeradio", "南苏丹", "Eye Radio", "https://www.eyeradio.org/", "",
     "html_listing", ["NATIONAL_NEWS"], "CORROBORATION", "tier_2", "SSD 主要独立媒体（全绿）"),
    ("ssd_unmiss", "南苏丹", "UNMISS", "https://unmiss.unmissions.org/", "",
     "html_listing", ["HUMANITARIAN"], "PRIMARY_EVIDENCE", "tier_2", "联合国特派团（全绿+新鲜）"),
    ("eth_health_moh", "埃塞俄比亚", "Ministry of Health (Ethiopia)", "https://www.moh.gov.et/", "",
     "html_listing", ["OFFICIAL", "HEALTH"], "PRIMARY_EVIDENCE", "tier_2", "卫生部（全绿）"),
    ("eth_addisfortune", "埃塞俄比亚", "Addis Fortune", "https://addisfortune.news/",
     "https://addisfortune.news/feed", "rss", ["NATIONAL_NEWS"], "CORROBORATION", "tier_2", "主流商业/政治（全绿+新鲜）"),
    ("eth_insight", "埃塞俄比亚", "Ethiopia Insight", "https://www.ethiopia-insight.com/",
     "https://www.ethiopia-insight.com/feed/", "rss", ["RESEARCH_ANALYSIS"], "CONTEXT_ANALYSIS", "tier_2", "分析媒体（全绿）"),
]

P1_IDS = [w[0] for w in W1]
P1_COUNTRIES = ["尼日利亚", "贝宁", "莫桑比克", "南苏丹", "埃塞俄比亚"]

HELP = '''# ── C8-4C2 PHASE 1：P1 保证核心（在 P0 尼日尔之后、既有 Lane A 之前执行）──
# 来源：C8-4C2 严格重验通过（生产证书校验；文章 URL/日期/正文/国家范围全绿）的官方与高价值源。
P1_GUARANTEED_IDS = {
    "nga_gov_portal", "nga_health_moh", "nga_nan", "nga_transport_moh", "nga_icir",
    "ben_gouv", "ben_sante", "ben_fraternite",
    "moz_gov_portal", "moz_defence", "moz_zitamar",
    "ssd_eyeradio", "ssd_unmiss",
    "eth_health_moh", "eth_addisfortune", "eth_insight",
}
P1_COUNTRIES_ORDER = ["尼日利亚", "贝宁", "莫桑比克", "南苏丹", "埃塞俄比亚"]


def _p1_core_first(sources, country_cn):
    """C8-4C2 PHASE 1：P1 保证核心置顶（稳定排序；P0 已在更早阶段置顶，不受影响）。"""
    if str(country_cn) not in P1_COUNTRIES_ORDER:
        return sources

    def key(pair):
        idx, src = pair
        sid = str(getattr(src, "source_id", None)
                  or (src.get("source_id") if isinstance(src, dict) else ""))
        return (0 if sid in P1_GUARANTEED_IDS else 1, idx)

    return [src for _i, src in sorted(enumerate(sources), key=key)]


def _p1_countries_after_p0(countries):
    """C8-4C2：国家循环顺序 = 尼日尔(P0) → P1 五国 → 其余（保持原相对顺序）。"""
    head = [c for c in P1_COUNTRIES_ORDER if c in countries]
    rest = [c for c in countries if c not in head and c != P0_NIGER_COUNTRY]
    p0 = [P0_NIGER_COUNTRY] if P0_NIGER_COUNTRY in countries else []
    return p0 + head + rest


'''


def patch_stage3():
    p = ROOT / "scripts" / "stage3_collect_v2.py"
    s = io.open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    if "P1_GUARANTEED_IDS" in s:
        return "already"
    anchor = "def _p0_niger_countries_first(countries):"
    assert s.count(anchor) == 1
    s = s.replace(anchor, HELP + anchor, 1)
    old = "        countries = _p0_niger_countries_first(countries)"
    new = (old + "\n        # C8-4C2：P1 五国紧随 P0 之后（PHASE 1），其余国家保持既有顺序\n"
           "        countries = _p1_countries_after_p0(countries)")
    assert s.count(old) == 1
    s = s.replace(old, new, 1)
    old2 = "        sources = _p0_niger_first(sources, country_cn)"
    new2 = (old2 + "\n        # C8-4C2 PHASE 1：P1 保证核心置顶\n"
            "        sources = _p1_core_first(sources, country_cn)")
    assert s.count(old2) == 1
    s = s.replace(old2, new2, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", "\r\n"))
    ast.parse(s)
    return "patched"


def add_sources(wave_name, items):
    q = ROOT / "data" / "sources.json"
    d = json.loads(q.read_text(encoding="utf-8"))
    rows = d["sources"]
    have = {str(x.get("source_id")) for x in rows}
    added = []
    for (sid, cn, name, url, feed, method, roles, ev, tier, note) in items:
        if sid in have:
            continue
        if "OFFICIAL" in roles or "SECURITY_DEFENCE" in roles:
            stype = "official_media"
        elif "NATIONAL_NEWS" in roles or "HUMANITARIAN" in roles:
            stype = "international" if "HUMANITARIAN" in roles else "local_media"
        else:
            stype = "local_media"
        lang = ["fr"] if cn == "贝宁" else (["pt"] if cn == "莫桑比克" else (["en"] if cn != "埃塞俄比亚" else ["en", "am"]))
        rows.append({
            "source_id": sid, "source_group": sid, "source_name": name, "source_type": stype,
            "source_reliability_tier": tier, "country_scope": [cn], "language": lang,
            "is_direct_origin": True, "is_republication_platform": False,
            "enabled": True, "tested": True,
            "claim_origin_type": "primary_official" if "OFFICIAL" in roles else "original_reporting",
            "url": url,
            "notes": "C8-4C2 严格重验通过（生产证书校验）。角色：%s；证据角色：%s；优先级：%s。%s"
                     % (roles, ev, wave_name, note),
            "legacy_payload": {"collection_method": method, "feed_url": feed, "country": cn},
            "listing_urls": ([] if method == "rss" else [url]),
            "listing_max_items": 0, "article_link_selectors": [],
        })
        added.append(sid)
    d["sources"] = rows
    q.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    def shape(s):
        v = s.get("country_scope")
        return v if isinstance(v, list) else ([v] if v else [])

    en = [x for x in rows if str(x.get("enabled")).lower() in ("true", "1", "yes")]
    return {"added": added, "configured": len(rows), "enabled": len(en),
            "expanded": sum(len(shape(s)) for s in en)}


if __name__ == "__main__":
    print("stage3:", patch_stage3())
    r = add_sources("P1_GUARANTEED_CORE", W1)
    print("WAVE1 新增 =", len(r["added"]), r["added"])
    print("库存: CONFIGURED=%d ENABLED=%d EXPANDED=%d" % (r["configured"], r["enabled"], r["expanded"]))
