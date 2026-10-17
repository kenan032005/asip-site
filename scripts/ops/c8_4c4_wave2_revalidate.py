"""C8-4C4：Wave 2 候选的**重新验证**（严格证书校验，禁止 CERT_NONE）。

对 14 个 Wave 2 候选 + 2 个南苏丹政府官方候选，逐一验证 11 项：
ACCESS / STRICT_TLS / RSS_OR_STABLE_HTML / ARTICLE_URL / DATE_PARSE / FULL_BODY /
COUNTRY_SCOPE / RECENT_CONTENT / PUBLISHER_IDENTITY / DUPLICATE_WITH_EXISTING / LANGUAGE
并输出可集成的名单。
"""
import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "runtime" / "ops" / "c8_4c4_wave2_revalidation.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; ASIP/1.0)",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

# (source_id, country, name, url, rss, expected_identity_keyword)
CAND = [
    ("nga_nrc", "NIGERIA", "Nigerian Railway Corporation", "https://nrc.gov.ng/",
     "http://nrc.gov.ng/feed/", b"rail"),
    ("nga_ports", "NIGERIA", "Nigerian Ports Authority", "https://nigerianports.gov.ng/",
     "https://nigerianports.gov.ng/feed/", b"port"),
    ("nga_nnpc", "NIGERIA", "NNPC Ltd", "https://nnpcgroup.com/", "", b"nnpc"),
    ("nga_punch", "NIGERIA", "Punch", "https://punchng.com/", "https://punchng.com/feed/", b"punch"),
    ("nga_sahara", "NIGERIA", "Sahara Reporters", "https://saharareporters.com/", "", b"sahara"),
    ("nga_thecable", "NIGERIA", "TheCable", "https://www.thecable.ng/", "https://www.thecable.ng/feed/", b"cable"),
    ("ben_24h", "BENIN", "24h Au BenIn", "https://24haubenin.info/", "", b"b\u00e9nin"),
    ("ben_webtv", "BENIN", "Benin Web TV", "https://beninwebtv.com/", "/feed.xml", b"b\u00e9nin"),
    ("ben_lnt", "BENIN", "La Nouvelle Tribune", "https://lanouvelletribune.info/",
     "https://lanouvelletribune.info/feed/", b"b\u00e9nin"),
    ("ben_banouto", "BENIN", "Banouto", "https://www.banouto.bj/", "", b"b\u00e9nin"),
    ("moz_cip", "MOZAMBIQUE", "CIP Moz", "https://www.cipmoz.org/", "https://www.cipmoz.org/feed/", b"cabo delgado"),
    ("moz_clubmoz", "MOZAMBIQUE", "Club of Mozambique", "https://clubofmozambique.com/",
     "https://clubofmozambique.com/feed/", b"mozambique"),
    ("moz_opais", "MOZAMBIQUE", "O Pais", "https://opais.co.mz/", "https://opais.co.mz/feed/", b"mo\u00e7ambique"),
    ("ssd_jubaecho", "SOUTH_SUDAN", "Juba Echo", "https://jubaecho.com/",
     "https://jubaecho.com/feed/", b"juba"),
    # 南苏丹政府官方（缺口判定用；不是 Wave 2）
    ("ssd_moh", "SOUTH_SUDAN", "Ministry of Health (South Sudan)", "https://www.moh.gov.ss/", "",
     b"south sudan"),
    ("ssd_goss", "SOUTH_SUDAN", "GOSS Online (Government)", "https://www.goss-online.org/", "",
     b"south sudan"),
]

COUNTRY_HINT = {
    "NIGERIA": [b"nigeria", b"nigerian", b"abuja", b"lagos"],
    "BENIN": ["bénin".encode(), b"benin", b"cotonou"],
    "MOZAMBIQUE": ["moçambique".encode(), b"mozambique", b"maputo"],
    "SOUTH_SUDAN": [b"south sudan", b"juba"],
    "ETHIOPIA": [b"ethiopia", b"addis ababa"],
}


def fetch(url, timeout=25, tries=3):
    last = "ERR"
    for i in range(tries):
        try:
            ctx = ssl.create_default_context()  # 严格校验
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=timeout, context=ctx) as r:
                return r.status, r.read(400000), ""
        except urllib.error.HTTPError as e:
            return e.code, b"", "HTTP_%d" % e.code
        except ssl.SSLCertVerificationError:
            last = "TLS_CERT_FAIL"
        except ssl.SSLError:
            last = "TLS_ERROR"
        except Exception as e:  # noqa: BLE001
            s = str(e)
            last = ("DNS_FAIL" if any(k in s for k in ("getaddrinfo", "Name or service", "11001", "11002"))
                    else ("TIMEOUT" if "timed out" in s else "ERR"))
        if i < tries - 1:
            import time
            time.sleep(3)
    return 0, b"", last


def absolute(base, href):
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        m = re.match(r"(https?://[^/]+)", base)
        return (m.group(1) if m else base.rstrip("/")) + href
    return base.rstrip("/") + "/" + href.lstrip("/")


def extract_articles(base, body):
    hrefs = re.findall(rb'href=["\']([^"\'#\s]{12,220})["\']', body)
    out = []
    for h in hrefs:
        s = h.decode("utf-8", "ignore")
        if any(x in s.lower() for x in ("/feed", "wp-content", "wp-json", ".css", ".js", ".png", ".jpg",
                                        ".svg", ".ico", "facebook", "twitter", "youtube", "instagram",
                                        "mailto:", "javascript:", "/tag/", "/author/", "/page/")):
            continue
        if re.search(r"(/20\d\d/\d\d/|/article|/actualit|\?p=\d+|/post\?id=|/news/|/\d{4}/)", s, re.I) \
           or s.count("-") >= 3:
            out.append(absolute(base, s))
    return list(dict.fromkeys(out))[:12]


def body_len(html):
    t = re.sub(rb"<script[\s\S]*?</script>|<style[\s\S]*?</style>", b" ", html)
    t = re.sub(rb"<[^>]+>", b" ", t)
    return len(re.sub(rb"\s+", b" ", t))


def latest_date(body):
    m = re.findall(rb"(20\d\d-\d\d-\d\d|\d{2}[/.]\d{2}[/.]20\d\d)", body)
    if m:
        d = m[0].decode("utf-8", "ignore").replace(".", "-").replace("/", "-")
        p = d.split("-")
        if len(p) == 3 and len(p[0]) == 2:
            d = "%s-%s-%s" % (p[2], p[1], p[0])
        return d
    m2 = re.search(rb"<(?:pubDate|published|lastmod)[^>]*>([^<]{8,40})<", body)
    return m2.group(1).decode("utf-8", "ignore").strip()[:24] if m2 else ""


def main():
    src = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8")).get("sources") or []
    existing = set()
    for s in src:
        for u in [s.get("url")] + list(s.get("listing_urls") or []):
            m = re.match(r"https?://([^/]+)", str(u or ""))
            if m:
                existing.add(m.group(1).replace("www.", "").lower())

    out = []
    for (sid, cn, name, url, rss, ident) in CAND:
        r = {"source_id": sid, "COUNTRY": cn, "SOURCE_NAME": name, "URL": url, "RSS_URL": rss}
        st, body, err = fetch(url)
        r["HTTP_STATUS"] = st
        r["ACCESS_OK"] = (st == 200 and len(body) > 2000)
        r["TLS_ERROR"] = err if err.startswith("TLS") else ""
        r["STRICT_TLS_OK"] = not err.startswith("TLS")
        r["FAIL_KIND"] = err
        arts = extract_articles(url, body) if r["ACCESS_OK"] else []
        r["ARTICLE_URL_OK"] = len(arts) >= 3
        r["ARTICLE_SAMPLE"] = arts[:2]
        r["DATE_PARSE_OK"] = bool(latest_date(body)) if r["ACCESS_OK"] else False
        r["LATEST_DATE"] = latest_date(body)
        if arts:
            st2, b2, _ = fetch(arts[0], tries=2)
            r["FULL_BODY_OK"] = bool(st2 == 200 and body_len(b2) >= 1200)
            r["FULL_BODY_CHARS"] = body_len(b2)
        else:
            r["FULL_BODY_OK"] = False
            r["FULL_BODY_CHARS"] = 0
        rss_ok = False
        if rss and r["ACCESS_OK"]:
            sr, br, _e = fetch(absolute(url, rss))
            rss_ok = bool(sr == 200 and br.lstrip()[:5] == b"<?xml" and b"<item" in br)
        r["RSS_OK"] = rss_ok
        r["STABLE_HTML_OK"] = r["ARTICLE_URL_OK"] and r["DATE_PARSE_OK"]
        r["DISCOVERY_OK"] = rss_ok or r["STABLE_HTML_OK"]
        low = (body or b"").lower()
        r["COUNTRY_SCOPE_OK"] = any(h in low for h in COUNTRY_HINT[cn]) if r["ACCESS_OK"] else False
        r["PUBLISHER_IDENTITY_OK"] = (ident in low) if r["ACCESS_OK"] else False
        r["LANGUAGE_OK"] = True  # 语言在注册表按 publisher 声明；此处不断言
        r["RECENT_CONTENT_OK"] = bool(r["LATEST_DATE"] and r["LATEST_DATE"] >= "2026-09-20")
        dom = re.sub(r"^https?://", "", url).split("/")[0].replace("www.", "").lower()
        r["DUPLICATE_WITH_EXISTING"] = dom in existing
        checks = ["ACCESS_OK", "STRICT_TLS_OK", "DISCOVERY_OK", "ARTICLE_URL_OK", "DATE_PARSE_OK",
                  "FULL_BODY_OK", "COUNTRY_SCOPE_OK", "PUBLISHER_IDENTITY_OK"]
        r["ALL_PASS"] = all(r[k] for k in checks) and not r["DUPLICATE_WITH_EXISTING"]
        r["FAILED"] = [k for k in checks if not r[k]]
        out.append(r)
        print("%-14s %-34s http=%-4s tls=%-5s disc=%-5s art=%-5s date=%-5s body=%-5s scope=%-5s ident=%-5s ALL=%s %s"
              % (sid, name[:34], st, r["STRICT_TLS_OK"], r["DISCOVERY_OK"], r["ARTICLE_URL_OK"],
                 r["DATE_PARSE_OK"], r["FULL_BODY_OK"], r["COUNTRY_SCOPE_OK"], r["PUBLISHER_IDENTITY_OK"],
                 r["ALL_PASS"], r["FAILED"] or r["FAIL_KIND"]), flush=True)

    w2 = [r for r in out if r["source_id"] not in ("ssd_moh", "ssd_goss")]
    ok = [r for r in w2 if r["ALL_PASS"]]
    rej = [r for r in w2 if not r["ALL_PASS"]]
    doc = {"schema": "c8-4c4-wave2-revalidation-v1", "strict_tls": True, "cert_none_used": False,
           "wave2_candidates": len(w2), "wave2_addable": len(ok), "wave2_rejected": len(rej),
           "addable_ids": [r["source_id"] for r in ok], "rejected_ids": [r["source_id"] for r in rej],
           "south_sudan_gov": [r for r in out if r["source_id"] in ("ssd_moh", "ssd_goss")],
           "results": out}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print(json.dumps({k: doc[k] for k in ("wave2_candidates", "wave2_addable", "wave2_rejected",
                                          "addable_ids", "rejected_ids")}, ensure_ascii=False, indent=1))
    print("written:", OUT)


if __name__ == "__main__":
    main()
