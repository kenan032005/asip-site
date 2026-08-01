#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立验证 RSS 和 HTML 栏目页两条链路。"""
import sys, os, time, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "collectors"))

from framework import fetch_page, ContentExtractor
from registry import SourceRegistry, ArticleDiscoverer

reg = SourceRegistry()
discoverer = ArticleDiscoverer(reg)

# ── RSS 链路测试 ──
RSS_TEST_SOURCES = [
    # 乍得
    ("chad_tchadinfos", "Tchadinfos", "乍得", "https://tchadinfos.com/feed/"),
    ("chad_alwihda", "Alwihda Info", "乍得", "https://www.alwihdainfo.com/feed/"),
    ("chad_journaldutchad", "Journal du Tchad", "乍得", "https://journaldutchad.com/feed/"),
    # 尼日尔
    ("niger_anp", "ANP", "尼日尔", "https://anp.ne/feed/"),
    ("niger_lesahel", "Le Sahel", "尼日尔", "https://www.lesahel.org/feed/"),
    ("niger_sahelien", "Sahelien", "尼日尔", "https://sahelien.com/feed/"),
]

# ── HTML 栏目页链路测试（仅使用 listing_urls，禁用 feed）──
HTML_TEST_SOURCES = [
    ("chad_tchadinfos_html", "Tchadinfos(HTML)", "乍得",
     "https://tchadinfos.com/category/securite/", "https://tchadinfos.com/"),
    ("chad_journaldutchad_html", "Journal du Tchad(HTML)", "乍得",
     "https://journaldutchad.com/category/securite/", "https://journaldutchad.com/"),
    ("niger_nigerinter_html", "Niger Inter(HTML)", "尼日尔",
     "https://nigerinter.com/category/actualite/", "https://nigerinter.com/"),
    ("niger_studiokalangou_html", "Studio Kalangou(HTML)", "尼日尔",
     "https://www.studiokalangou.org/category/actualite/", "https://www.studiokalangou.org/"),
]

def test_rss(sid, name, country, feed_url):
    """RSS 链路：发现 → 详情页 → 正文提取。"""
    src = {
        "source_id": sid, "source_name": name, "source_country": country,
        "source_type": "local_media", "discovery_type": "rss",
        "feed_url": feed_url, "listing_urls": [], "base_url": "",
        "max_items": 3, "language": "fr", "enabled": True,
        "extractor_profile": {},
    }
    results = []
    arts, errs = discoverer.discover(src)
    if errs:
        print(f"  RSS 发现错误: {errs[:1]}")
    print(f"  RSS 发现 {len(arts)} 条 → ", end="", flush=True)
    for art in arts[:3]:
        text, err, status = fetch_page(art["url"])
        if err:
            results.append({"url": art["url"], "error": str(err)[:60], "discovery_method": "rss"})
            continue
        ext = ContentExtractor({}).extract(text, art["url"])
        results.append({
            "source_id": sid, "source_name": name, "country": country,
            "feed_url": feed_url, "article_url": art["url"],
            "canonical_url": ext.get("canonical_url", ""),
            "original_title": art.get("title", ext.get("title", ""))[:80],
            "discovery_method": "rss",
            "extraction_method": ext.get("method", ""),
            "body_status": ext.get("body_status", ""),
            "extraction_quality": ext.get("quality", ""),
            "article_word_count": ext.get("word_count", 0),
            "extraction_quality_score": ext.get("quality_score", 0),
            "extraction_quality_reasons": ext.get("quality_reasons", [])[:5],
            "publishable": ext.get("quality") in ("full_body", "partial_body"),
        })
        time.sleep(0.3)
    ok = [r for r in results if r.get("publishable")]
    print(f"正文成功 {len(ok)}/{len(results)}")
    return results


def test_html_listing(sid, name, country, listing_url, base_url):
    """HTML 栏目页链路：仅使用 listing_urls，禁用 feed。"""
    src = {
        "source_id": sid, "source_name": name, "source_country": country,
        "source_type": "local_media", "discovery_type": "html_listing",
        "feed_url": "", "listing_urls": [listing_url], "base_url": base_url,
        "max_items": 5, "language": "fr", "enabled": True,
        "extractor_profile": {},
    }
    results = []
    arts, errs = discoverer.discover(src)
    if errs:
        print(f"  HTML 发现错误: {errs[:1]}")
    print(f"  HTML 发现 {len(arts)} 条 → ", end="", flush=True)
    for art in arts[:3]:
        text, err, status = fetch_page(art["url"])
        if err:
            results.append({"url": art["url"], "error": str(err)[:60], "discovery_method": "html_listing"})
            continue
        ext = ContentExtractor({}).extract(text, art["url"])
        results.append({
            "source_id": sid, "source_name": name, "country": country,
            "listing_url": listing_url, "article_url": art["url"],
            "canonical_url": ext.get("canonical_url", ""),
            "original_title": art.get("title", ext.get("title", ""))[:80],
            "discovery_method": "html_listing",
            "extraction_method": ext.get("method", ""),
            "body_status": ext.get("body_status", ""),
            "extraction_quality": ext.get("quality", ""),
            "article_word_count": ext.get("word_count", 0),
            "extraction_quality_score": ext.get("quality_score", 0),
            "extraction_quality_reasons": ext.get("quality_reasons", [])[:5],
            "publishable": ext.get("quality") in ("full_body", "partial_body"),
        })
        time.sleep(0.3)
    ok = [r for r in results if r.get("publishable")]
    print(f"正文成功 {len(ok)}/{len(results)}")
    return results


def main():
    print("=" * 60)
    print("RSS 详情页链路验证")
    print("=" * 60)
    rss_results = {}
    for sid, name, country, feed_url in RSS_TEST_SOURCES:
        print(f"\n[{country}] {name}")
        rss_results[sid] = test_rss(sid, name, country, feed_url)

    print("\n" + "=" * 60)
    print("HTML 栏目页链路验证（仅 listing_urls，无 RSS）")
    print("=" * 60)
    html_results = {}
    for sid, name, country, listing_url, base_url in HTML_TEST_SOURCES:
        print(f"\n[{country}] {name}")
        html_results[sid] = test_html_listing(sid, name, country, listing_url, base_url)

    # 输出汇总
    all_results = {"rss": rss_results, "html_listing": html_results}
    out_path = os.path.join(ROOT, "logs", "channel_verification.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n详细结果已保存: {out_path}")
    print(f"\n=== 汇总 ===")
    for ch, res in [("RSS", rss_results), ("HTML栏目页", html_results)]:
        total = sum(len(v) for v in res.values())
        ok = sum(sum(1 for r in v if r.get("publishable")) for v in res.values())
        print(f"  {ch}: {ok}/{total} 篇有有效正文")
    return 0


if __name__ == "__main__":
    sys.exit(main())
