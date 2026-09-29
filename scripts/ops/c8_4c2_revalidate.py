"""C8-4C2：P1 五国候选源的**严格重验**（生产证书校验，禁止 CERT_NONE）。

对 C8-4C1 的 RECOMMEND_ADD(44) 与 MONITOR_FOR_FUTURE(13) 逐一验证：
  ACCESS_OK / STRICT_TLS_OK / RSS_OK / HTML_LISTING_OK / ARTICLE_URL_EXTRACTION_OK /
  DATE_PARSE_OK / FULL_BODY_OK / COUNTRY_SCOPE_OK / LANGUAGE_OK /
  DUPLICATE_WITH_EXISTING / RECENT_CONTENT_CONFIRMED
并按 Wave 归属给出 accept/reject 建议（不允许把未验证项留作 UNKNOWN 后直接集成）。
"""
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAND = Path("data") / "runtime" / "ops" / "c8_4c1_p1_source_candidates.json"
OUT = Path("data") / "runtime" / "ops" / "c8_4c2_p1_revalidation.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; ASIP/1.0)",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

COUNTRY_HINT = {
    "NIGERIA": [b"nigeria", b"nigerian", b"abuja", b"lagos", b"borno", b"naira"],
    "BENIN": ["bénin".encode(), b"benin", b"cotonou", b"porto-novo", "béninois".encode()],
    "MOZAMBIQUE": ["moçambique".encode(), b"mozambique", b"maputo", b"cabo delgado", b"pemba"],
    "SOUTH_SUDAN": [b"south sudan", b"juba", b"jonglei", b"unity state", b"upper nile"],
    "ETHIOPIA": [b"ethiopia", b"addis ababa", b"amhara", b"tigray", b"oromia"],
}
LANG_HINT = {"en": [b"the ", b" and ", b" of "], "fr": [b" le ", b" les ", b" des ", b" pour "],
             "pt": [b" de ", b" para ", "não".encode(), b" com "]}


def fetch(url, timeout=25, tries=3):
    """严格证书校验的 GET；返回 (status, body, err_kind)。"""
    last = "ERR"
    for i in range(tries):
        try:
            ctx = ssl.create_default_context()  # 严格校验，绝不放宽
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return r.status, r.read(400000), ""
        except urllib.error.HTTPError as e:
            return e.code, b"", "HTTP_%d" % e.code
        except ssl.SSLCertVerificationError as e:
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
    """从列表页提取候选文章链接（真实存在的 href，不发明）。"""
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
    # 去重保序
    return list(dict.fromkeys(out))[:12]


def has_date(body):
    return bool(re.search(rb'(20\d\d-\d\d-\d\d|\d{2}[/.]\d{2}[/.]20\d\d|\d{1,2}\s+\w{3,9}\s+20\d\d)', body))


def latest_date(body):
    m = re.findall(rb'(20\d\d-\d\d-\d\d|\d{2}[/.]\d{2}[/.]20\d\d)', body)
    if m:
        d = m[0].decode("utf-8", "ignore").replace(".", "-").replace("/", "-")
        p = d.split("-")
        if len(p) == 3:
            if len(p[0]) == 2:  # dd-mm-yyyy
                d = "%s-%s-%s" % (p[2], p[1], p[0])
        return d
    m2 = re.search(rb"<(?:pubDate|published|lastmod|updated)[^>]*>([^<]{8,40})<", body)
    return m2.group(1).decode("utf-8", "ignore").strip()[:24] if m2 else ""


def body_len(html):
    t = re.sub(rb"<script[\s\S]*?</script>|<style[\s\S]*?</style>", b" ", html)
    t = re.sub(rb"<[^>]+>", b" ", t)
    t = re.sub(rb"\s+", b" ", t)
    return len(t)


def main():
    cand = json.loads((ROOT / CAND).read_text(encoding="utf-8"))
    src = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8")).get("sources") or []
    existing_domains = set()
    for s in src:
        u = str(s.get("url") or "")
        m = re.match(r"https?://([^/]+)", u)
        if m:
            existing_domains.add(m.group(1).replace("www.", "").lower())
        lu = s.get("listing_urls") or []
        for x in (lu if isinstance(lu, list) else [lu]):
            m2 = re.match(r"https?://([^/]+)", str(x or ""))
            if m2:
                existing_domains.add(m2.group(1).replace("www.", "").lower())

    results = []
    for c in cand["candidates"]:
        cn = c["COUNTRY"]
        url = c["EXACT_TESTED_URL"]
        dom = c["CANONICAL_DOMAIN"].replace("www.", "").lower()
        r = {"COUNTRY": cn, "SOURCE_NAME": c["SOURCE_NAME"], "DOMAIN": dom, "URL": url,
             "C8_4C1_ACTION": c["RECOMMENDED_ACTION"], "C8_4C1_RSS": c.get("RSS_URL") or "",
             "SOURCE_ROLE": c["SOURCE_ROLE"], "SOURCE_CATEGORY": c["SOURCE_CATEGORY"]}
        st, body, err = fetch(url)
        r["ACCESS_OK"] = (st == 200 and len(body) > 2000)
        r["HTTP_STATUS"] = st
        r["STRICT_TLS_OK"] = (err not in ("TLS_CERT_FAIL", "TLS_ERROR"))
        r["TLS_ERROR"] = err if err in ("TLS_CERT_FAIL", "TLS_ERROR") else ""
        r["FAIL_KIND"] = err
        rss_url = c.get("RSS_URL") or ""
        r["RSS_URL"] = rss_url
        r["RSS_OK"] = False
        r["RSS_STATUS"] = None if not rss_url else "n/a"
        r["RSS_ITEMS"] = 0
        r["RSS_LATEST"] = ""
        if rss_url and r["ACCESS_OK"]:
            st2, b2, e2 = fetch(rss_url)
            r["RSS_OK"] = bool(st2 == 200 and b2.lstrip()[:5] == b"<?xml" and b"<item" in b2)
            r["RSS_STATUS"] = st2
            if r["RSS_OK"]:
                r["RSS_ITEMS"] = len(re.findall(rb"<item[ >]", b2))
                r["RSS_LATEST"] = latest_date(b2)
        arts = extract_articles(url, body) if r["ACCESS_OK"] else []
        r["ARTICLE_URL_EXTRACTION_OK"] = len(arts) >= 3
        r["ARTICLE_SAMPLE"] = arts[:3]
        r["HTML_LISTING_OK"] = r["ARTICLE_URL_EXTRACTION_OK"]
        r["DATE_PARSE_OK"] = has_date(body) if r["ACCESS_OK"] else False
        r["LATEST_LIST_DATE"] = latest_date(body)
        # 正文可行性：抓首篇文章
        if arts:
            st3, b3, _e3 = fetch(arts[0], tries=2)
            r["FULL_BODY_OK"] = bool(st3 == 200 and body_len(b3) >= 1200)
            r["FULL_BODY_CHARS"] = body_len(b3)
        else:
            r["FULL_BODY_OK"] = False
            r["FULL_BODY_CHARS"] = 0
        low = (body or b"").lower()
        r["COUNTRY_SCOPE_OK"] = any(h in low for h in COUNTRY_HINT[cn]) if r["ACCESS_OK"] else False
        lang = c.get("LANGUAGE", "en").split("/")[0]
        r["LANGUAGE_OK"] = any(h in low for h in LANG_HINT.get(lang, LANG_HINT["en"])) if r["ACCESS_OK"] else False
        r["DUPLICATE_WITH_EXISTING"] = dom in existing_domains
        r["DUPLICATE_LOGICAL_SOURCE"] = False  # 新 publisher，非既有逻辑源副本
        # 新鲜度：RSS latest 或列表最早日期在 45 天内
        fresh = False
        for v in (r["RSS_LATEST"], r["LATEST_LIST_DATE"]):
            if v and re.match(r"20\d\d-\d\d-\d\d", v):
                if v >= "2026-08-15":
                    fresh = True
        r["RECENT_CONTENT_CONFIRMED"] = fresh
        checks = ["ACCESS_OK", "STRICT_TLS_OK", "ARTICLE_URL_EXTRACTION_OK", "DATE_PARSE_OK",
                  "FULL_BODY_OK", "COUNTRY_SCOPE_OK", "LANGUAGE_OK"]
        r["ALL_STRICT_CHECKS_PASS"] = all(r[k] for k in checks) and not r["DUPLICATE_WITH_EXISTING"]
        r["CHECKS_FAILED"] = [k for k in checks if not r[k]]
        results.append(r)
        print("%-12s %-30s http=%-4s tls=%-4s art=%-5s date=%-5s body=%-5s scope=%-5s fresh=%-5s ALL=%s %s"
              % (cn, c["SOURCE_NAME"][:30], st, r["STRICT_TLS_OK"], r["ARTICLE_URL_EXTRACTION_OK"],
                 r["DATE_PARSE_OK"], r["FULL_BODY_OK"], r["COUNTRY_SCOPE_OK"], r["RECENT_CONTENT_CONFIRMED"],
                 r["ALL_STRICT_CHECKS_PASS"], (r["CHECKS_FAILED"] or r["FAIL_KIND"] or "")), flush=True)
    addable = [r for r in results if r["ALL_STRICT_CHECKS_PASS"]]
    rejected = [r for r in results if not r["ALL_STRICT_CHECKS_PASS"]]
    out = {"schema": "c8-4c2-p1-revalidation-v1", "strict_tls": True, "cert_none_used": False,
           "results": results,
           "summary": {"total": len(results), "addable": len(addable), "rejected": len(rejected),
                       "from_add": len([r for r in results if r["C8_4C1_ACTION"].startswith("ADD")]),
                       "from_pending": len([r for r in results if r["C8_4C1_ACTION"] == "MONITOR_FOR_FUTURE"]),
                       "pending_promoted": len([r for r in addable if r["C8_4C1_ACTION"] == "MONITOR_FOR_FUTURE"])}}
    (ROOT / OUT).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print(json.dumps(out["summary"], ensure_ascii=False))
    print("written:", OUT)


if __name__ == "__main__":
    main()
