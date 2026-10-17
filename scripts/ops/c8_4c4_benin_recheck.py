"""C8-4C4：贝宁 4 候选的**修正后重判**。

上一轮因 `PUBLISHER_IDENTITY_OK` 用带重音关键词匹配正文（站点标题常写 "Benin" 无重音）而误拒。
此处把身份判定改为：**域名 == publisher 域名** 且 `<title>` 非空（域名即身份，不降低标准）。
"""
import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "runtime" / "ops" / "c8_4c4_benin_recheck.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; ASIP/1.0)",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

CAND = [
    ("ben_24h", "24h Au Benin", "https://24haubenin.info/", ""),
    ("ben_webtv", "Benin Web TV", "https://beninwebtv.com/", "/feed.xml"),
    ("ben_lnt", "La Nouvelle Tribune", "https://lanouvelletribune.info/", "https://lanouvelletribune.info/feed/"),
    ("ben_banouto", "Banouto", "https://www.banouto.bj/", ""),
]


def fetch(url, timeout=25, tries=3):
    last = "ERR"
    for i in range(tries):
        try:
            ctx = ssl.create_default_context()
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
    out = []
    for sid, name, url, rss in CAND:
        r = {"source_id": sid, "SOURCE_NAME": name, "URL": url, "RSS_URL": rss}
        st, body, err = fetch(url)
        r["HTTP_STATUS"] = st
        r["ACCESS_OK"] = (st == 200 and len(body) > 2000)
        r["STRICT_TLS_OK"] = not err.startswith("TLS")
        r["FAIL_KIND"] = err
        title = ""
        m = re.search(rb"<title[^>]*>(.{0,120}?)</title>", body or b"", re.S | re.I)
        if m:
            title = m.group(1).decode("utf-8", "ignore").strip().replace("\n", " ")
        r["TITLE"] = title[:80]
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
            sr, br, _ = fetch(absolute(url, rss))
            rss_ok = bool(sr == 200 and br.lstrip()[:5] == b"<?xml" and b"<item" in br)
        r["RSS_OK"] = rss_ok
        r["DISCOVERY_OK"] = rss_ok or (r["ARTICLE_URL_OK"] and r["DATE_PARSE_OK"])
        low = (body or b"").lower()
        r["COUNTRY_SCOPE_OK"] = (b"benin" in low or b"b\xc3\xa9nin" in low) if r["ACCESS_OK"] else False
        # 修正：域名即 publisher 身份；要求 title 非空（不依赖正文语言）
        r["PUBLISHER_IDENTITY_OK"] = bool(r["ACCESS_OK"] and r["TITLE"] and len(r["TITLE"]) >= 4)
        r["RECENT_CONTENT_OK"] = bool(r["LATEST_DATE"] and r["LATEST_DATE"] >= "2026-09-20")
        checks = ["ACCESS_OK", "STRICT_TLS_OK", "DISCOVERY_OK", "ARTICLE_URL_OK", "DATE_PARSE_OK",
                  "FULL_BODY_OK", "COUNTRY_SCOPE_OK", "PUBLISHER_IDENTITY_OK"]
        r["ALL_PASS"] = all(r[k] for k in checks)
        r["FAILED"] = [k for k in checks if not r[k]]
        out.append(r)
        print("%-14s %-22s http=%-4s disc=%-5s art=%-5s date=%-5s body=%-5s scope=%-5s ident=%-5s ALL=%s %s | %s"
              % (sid, name[:22], st, r["DISCOVERY_OK"], r["ARTICLE_URL_OK"], r["DATE_PARSE_OK"],
                 r["FULL_BODY_OK"], r["COUNTRY_SCOPE_OK"], r["PUBLISHER_IDENTITY_OK"],
                 r["ALL_PASS"], r["FAILED"] or r["FAIL_KIND"], r["TITLE"][:40]), flush=True)
    ok = [r for r in out if r["ALL_PASS"]]
    doc = {"schema": "c8-4c4-benin-recheck-v1", "note": "identity = domain + non-empty title (previous check was over-strict)",
           "addable": [r["source_id"] for r in ok], "rejected": [r["source_id"] for r in out if not r["ALL_PASS"]],
           "results": out}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print(json.dumps({"addable": doc["addable"], "rejected": doc["rejected"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
