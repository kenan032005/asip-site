"""C8-4C4 WAVE 2：集成 13 个严格重验通过的源（NORMAL / LOW_FREQUENCY，不进 P1 核心）。"""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "sources.json"

# id, country, name, url, feed, method, role, evidence, tier, priority, note
W2 = [
    ("nga_nrc", "尼日利亚", "Nigerian Railway Corporation", "https://nrc.gov.ng/",
     "http://nrc.gov.ng/feed/", "rss", ["OFFICIAL", "TRANSPORT_INFRASTRUCTURE"], "PRIMARY_EVIDENCE", "tier_2",
     "NORMAL", "铁路官方（重验全绿）"),
    ("nga_ports", "尼日利亚", "Nigerian Ports Authority", "https://nigerianports.gov.ng/",
     "https://nigerianports.gov.ng/feed/", "rss", ["OFFICIAL", "TRANSPORT_INFRASTRUCTURE"], "PRIMARY_EVIDENCE",
     "tier_2", "NORMAL", "港口官方（重验全绿）"),
    ("nga_nnpc", "尼日利亚", "NNPC Ltd", "https://nnpcgroup.com/", "", "html_listing",
     ["ENERGY_MINING"], "CORROBORATION", "tier_2", "NORMAL", "国家石油公司（重验全绿）"),
    ("nga_punch", "尼日利亚", "Punch", "https://punchng.com/", "https://punchng.com/feed/", "rss",
     ["NATIONAL_NEWS"], "CORROBORATION", "tier_2", "NORMAL", "主流大报（重验全绿）"),
    ("nga_sahara", "尼日利亚", "Sahara Reporters", "https://saharareporters.com/", "", "html_listing",
     ["NATIONAL_NEWS"], "EARLY_SIGNAL", "tier_3", "NORMAL", "需交叉核实（重验全绿）"),
    ("nga_thecable", "尼日利亚", "TheCable", "https://www.thecable.ng/", "https://www.thecable.ng/feed/", "rss",
     ["NATIONAL_NEWS"], "CORROBORATION", "tier_2", "NORMAL", "主流媒体（重验全绿）"),
    ("ben_24h", "贝宁", "24h Au Benin", "https://24haubenin.info/", "", "html_listing",
     ["NATIONAL_NEWS"], "CORROBORATION", "tier_2", "NORMAL", "主流媒体（重验全绿）"),
    ("ben_webtv", "贝宁", "Benin Web TV", "https://beninwebtv.com/", "/feed.xml", "rss",
     ["NATIONAL_NEWS"], "CORROBORATION", "tier_2", "NORMAL", "主流媒体（重验全绿）"),
    ("ben_lnt", "贝宁", "La Nouvelle Tribune", "https://lanouvelletribune.info/",
     "https://lanouvelletribune.info/feed/", "rss", ["NATIONAL_NEWS"], "CORROBORATION", "tier_2",
     "NORMAL", "主流媒体（重验全绿）"),
    ("moz_cip", "莫桑比克", "CIP Mozambique", "https://www.cipmoz.org/", "https://www.cipmoz.org/feed/", "rss",
     ["RESEARCH_ANALYSIS"], "CONTEXT_ANALYSIS", "tier_2", "LOW_FREQUENCY", "Cabo Delgado 冲突研究（重验全绿）"),
    ("moz_clubmoz", "莫桑比克", "Club of Mozambique", "https://clubofmozambique.com/",
     "https://clubofmozambique.com/feed/", "rss", ["NATIONAL_NEWS"], "CORROBORATION", "tier_2",
     "NORMAL", "英文综合（重验全绿）"),
    ("moz_opais", "莫桑比克", "O Pais", "https://opais.co.mz/", "https://opais.co.mz/feed/", "rss",
     ["NATIONAL_NEWS"], "CORROBORATION", "tier_2", "NORMAL", "主流媒体（重验全绿）"),
    ("ssd_jubaecho", "南苏丹", "Juba Echo", "https://jubaecho.com/", "https://jubaecho.com/feed/", "rss",
     ["NATIONAL_NEWS"], "CORROBORATION", "tier_2", "NORMAL", "朱巴本地媒体（重验全绿）"),
]


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    rows = d["sources"]
    have = {str(x.get("source_id")) for x in rows}
    added, skipped = [], []
    for (sid, cn, name, url, feed, method, roles, ev, tier, pri, note) in W2:
        if sid in have:
            skipped.append(sid)
            continue
        if "OFFICIAL" in roles or "SECURITY_DEFENCE" in roles:
            stype = "official_media"
        elif "RESEARCH_ANALYSIS" in roles:
            stype = "regional_media"
        else:
            stype = "local_media"
        lang = ["fr"] if cn == "贝宁" else (["pt"] if cn == "莫桑比克" else ["en"])
        rows.append({
            "source_id": sid, "source_group": sid, "source_name": name, "source_type": stype,
            "source_reliability_tier": tier, "country_scope": [cn], "language": lang,
            "is_direct_origin": True, "is_republication_platform": False,
            "enabled": True, "tested": True,
            "claim_origin_type": "primary_official" if "OFFICIAL" in roles else "original_reporting",
            "url": url,
            "notes": "C8-4C4 WAVE 2 严格重验通过（生产证书校验；ACCESS/TLS/DISCOVERY/ARTICLE_URL/"
                     "DATE/FULL_BODY/COUNTRY_SCOPE/PUBLISHER_IDENTITY 全绿）。角色：%s；证据角色：%s；优先级：%s。%s"
                     % (roles, ev, pri, note),
            "legacy_payload": {"collection_method": method, "feed_url": feed, "country": cn},
            "listing_urls": ([] if method == "rss" else [url]),
            "listing_max_items": 0, "article_link_selectors": [],
        })
        added.append(sid)
    d["sources"] = rows
    SRC.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    def shape(s):
        v = s.get("country_scope")
        return v if isinstance(v, list) else ([v] if v else [])

    en = [x for x in rows if str(x.get("enabled")).lower() in ("true", "1", "yes")]
    print("WAVE2 新增 =", len(added), added)
    if skipped:
        print("已存在跳过 =", skipped)
    print("库存：CONFIGURED =", len(rows), "| ENABLED =", len(en),
          "| EXPANDED =", sum(len(shape(s)) for s in en))
    print("预期 EXPANDED = 888（875 + 13）")


if __name__ == "__main__":
    main()
    ast.parse(Path(__file__).read_text(encoding="utf-8"))
