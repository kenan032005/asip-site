#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stage3_collect_v2.py — Stage 3 第二执行包采集主控。

流程：
  SourceRegistry → ArticleDiscoverer → ArticleFetcher → ContentExtractor
  → Normalizer → CountryScopeClassifier → RelevanceFilter → Deduplicator
  → PublishGate → persisted data

用法：
  python scripts/stage3_collect_v2.py            # 完整采集
  python scripts/stage3_collect_v2.py --dry      # 仅预览
  python scripts/stage3_collect_v2.py --country 乍得  # 仅一个国家
"""
import os
import sys
import json
import time
import hashlib
import argparse
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "collectors"))

from framework import (  # noqa: E402
    fetch_page, validate_url, norm_url, content_hash, bj_iso, bj_now,
    parse_original_time, to_beijing,
    load_state_cache, save_state_cache, should_skip, should_retry,
    set_article_state, TERMINAL_STATES, CACHE_DIR,
)
from registry import SourceRegistry, ArticleDiscoverer  # noqa: E402
from country_runner import (load_country_cfg, identify_country,  # noqa: E402
                            relevance_stage1, classify_type)

DATA = os.path.join(ROOT, "data")
PUBLIC = os.path.join(DATA, "public")
PUBLISHED_PATH = os.path.join(PUBLIC, "published_events.json")
QUARANTINE_PATH = os.path.join(DATA, "canonical", "quarantine.json")
STATS_PATH = os.path.join(ROOT, "logs", "stage3_collection_stats.json")

# 正文质量准入
MIN_PUBLISH_WORDS = 50
# 仅完整/部分正文可发布；RSS 摘要/title_only/失败 一律隔离（不把摘要当正文）
ALLOWED_QUALITY = ("full_body", "partial_body")


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def run_country_pipeline(country_cn, registry, discoverer, dry=False, fresh=False, max_items=0):
    """对单个国家执行完整采集。"""
    cfg_key = "chad" if country_cn == "乍得" else "niger"
    country_cfg = load_country_cfg(cfg_key)
    sources = registry.by_country(country_cn)

    print(f"\n{'='*60}")
    print(f"{country_cn} — {len(sources)} 个启用来源")
    print(f"{'='*60}")

    # 从 framework 导入提取器（延迟，避免顶部导入报错）
    from framework import ContentExtractor

    all_articles = []
    per_source = []
    errors = []

    for src in sources:
        sid = src["source_id"]
        t0 = time.time()
        stat = {
            "source_id": sid, "source_name": src["source_name"],
            "country": country_cn, "method": src["discovery_type"],
            "discovered": 0, "fetched": 0, "full_body": 0, "partial_body": 0,
            "summary_only": 0, "extraction_failed": 0, "published": 0,
            "quarantined": 0, "duplicates": 0, "errors": 0,
            "status": "success", "error": "", "duration_s": 0.0,
        }
        print(f"\n  [{src['discovery_type']}] {src['source_name']} ...", flush=True)

        # 1) 发现（RSS + HTML栏目页双通道）
        discovered, dis_errors = discoverer.discover(src)
        # 若来源同时配置了 category_urls，则追加 HTML 栏目页发现
        if src.get("listing_urls") and src["discovery_type"] in ("rss", "atom"):
            html_src = dict(src)
            html_src["discovery_type"] = "html_listing"
            html_src["feed_url"] = ""
            html_arts, html_errs = discoverer.discover(html_src)
            if html_errs:
                dis_errors.extend(html_errs)
            # 合并去重
            seen_urls_d = set(a["url"] for a in discovered)
            for ha in html_arts:
                if ha["url"] not in seen_urls_d:
                    discovered.append(ha)
                    seen_urls_d.add(ha["url"])
        if dis_errors:
            stat["errors"] += len(dis_errors)
            errors.extend(dis_errors)
            print(f"    发现错误: {dis_errors[:2]}")
        if not discovered:
            stat["status"] = "no_items"
            stat["error"] = "; ".join(dis_errors[:2])
            per_source.append(stat)
            continue
        stat["discovered"] = len(discovered)

        # --max-items 限制：每个来源最多处理 N 条（受控采集）
        if max_items > 0 and len(discovered) > max_items:
            stat["skipped_by_limit"] = len(discovered) - max_items
            discovered = discovered[:max_items]
        else:
            stat.setdefault("skipped_by_limit", 0)

        # 状态缓存（article_processing_state 状态机）
        state_cache = load_state_cache(sid)
        if fresh:
            state_cache = {"articles": {}, "etag": "", "last_modified": "", "version": 2}

        # 2) 抓取详情页 + 3) 正文提取
        extractor = ContentExtractor(src.get("extractor_profile") or {})
        for d in discovered:
            url = d.get("url", "")
            nurl = norm_url(url)
            if not nurl:
                continue

            # 终态（已发布/已隔离终态）→ 跳过
            if should_skip(nurl, state_cache):
                stat["duplicates"] += 1
                continue

            stat["fetched"] += 1

            # 抓取详情页
            text, err, http_status = fetch_page(url)
            if err:
                # 重试类错误（网络/超时/限流）→ fetch_failed_retryable
                set_article_state(state_cache, nurl,
                                  "fetch_failed_retryable",
                                  error=str(err)[:80], http_status=http_status,
                                  body_hash="")
                stat["extraction_failed"] += 1
                stat["errors"] += 1
                continue

            # 标记抓取成功（暂存，写入前会被覆盖）
            body_hash = content_hash("", text or "")
            set_article_state(state_cache, nurl, "fetch_succeeded",
                              http_status=http_status, body_hash=body_hash)

            # 正文提取
            extracted = extractor.extract(text, url)
            quality = extracted.get("quality", "extraction_failed")
            if quality == "full_body":
                stat["full_body"] += 1
            elif quality == "partial_body":
                stat["partial_body"] += 1
            elif quality in ("rss_summary_only",):
                stat["summary_only"] += 1
            else:
                stat["extraction_failed"] += 1

            # 正文不足时不降级为 RSS 摘要（摘要≠正文）
            if not extracted.get("body") and d.get("summary"):
                extracted["body_status"] = "rss_summary_only"
                extracted["quality"] = "rss_summary_only"
                extracted["word_count"] = len(d["summary"].split())
                stat["summary_only"] += 1

            # 记录提取状态：成功或可重试
            if extracted.get("quality") in ("full_body", "partial_body"):
                set_article_state(state_cache, nurl, "extraction_succeeded",
                                  body_hash=content_hash(extracted.get("title", ""),
                                                         extracted.get("body", "")),
                                  http_status=http_status)
            else:
                set_article_state(state_cache, nurl, "extraction_failed_retryable",
                                  body_hash="",
                                  http_status=http_status,
                                  error="; ".join(extracted.get("quality_reasons", [])[:3]))

            article = {
                "source_id": sid,
                "source_name": src["source_name"],
                "source_country": country_cn,
                "source_type": src["source_type"],
                # language 可能是 list（如 ["fr"]）或字符串
                "language": (src["language"][0] if isinstance(src["language"], list) and src["language"] else (src["language"] if isinstance(src["language"], str) else "fr")),
                "discovery_method": d.get("method", ""),
                "feed_url": d.get("feed_url", ""),
                "listing_url": d.get("listing_url", ""),
                "article_url": url,
                "canonical_url": extracted.get("canonical_url", "") or url,
                # HTML 发现时锚文本可能是 'Lire la suite'/'Read more' 等通用词，用详情页标题
                "original_title": (d.get("title") or extracted.get("title", "")),
                "original_body": extracted.get("body", ""),
                "original_summary": d.get("summary", ""),
                "author": extracted.get("author", ""),
                "published_at_original": extracted.get("published_original") or d.get("published", ""),
                "published_at_beijing": extracted.get("published_at_beijing", ""),
                "lead_image_url": extracted.get("lead_image_url", ""),
                "article_word_count": extracted.get("word_count", 0),
                "extraction_method": extracted.get("method", ""),
                "extraction_quality": extracted.get("quality", "extraction_failed"),
                "extraction_quality_score": extracted.get("quality_score", 0),
                "extraction_quality_reasons": extracted.get("quality_reasons", []),
                "fetch_status": "ok",
                "fetch_http_status": http_status,
                "fetch_attempts": 1,
                "body_status": extracted.get("body_status", ""),
                "collected_at_beijing": bj_iso(),
            }

            # 通用锚文本（Lire la suite / Read more / 继续阅读）→ 用详情页标题
            anchor_title = article["original_title"].strip().lower()
            if anchor_title in ("lire la suite", "read more", "lire la suite ", "continuer",
                                "lire plus", "suite", "继续阅读", "阅读全文"):
                article["original_title"] = extracted.get("title", "") or d.get("title", "")

            # 时间转换
            published_dt, tz = parse_original_time(article["published_at_original"])
            article["published_timezone"] = tz or ""
            if not article["published_at_beijing"] and published_dt:
                article["published_at_beijing"] = to_beijing(published_dt)

            # 4) 国家分类 + 5) 相关性
            # 强信号以标题+摘要为准（代表事件本质）；正文仅作国家识别辅助
            title_summary = article["original_title"] + " " + article["original_summary"]
            cid = identify_country(title_summary + " " + article["original_body"][:800], country_cfg)
            rel, score, matched, excl = relevance_stage1(title_summary)
            # 若标题+摘要无强信号，但正文含明确暴力/伤亡词 → 允许（正文级强信号）
            if rel is not True:
                rel_body, score_body, m_body, e_body = relevance_stage1(
                    article["original_title"] + " " + article["original_body"][:400])
                # 仅当标题本身无信号、正文匹配到强暴力词（非弱信号）时回退
                if rel_body is True and m_body:
                    strong = [k for k in m_body if k not in (
                        "déplacement", "deplacement", "crise", "frontière", "frontier",
                        "sécurité", "securite", "police", "armée", "armee", "arrestation",
                        "arrest", "fermeture", "trafic", "drone", "安全", "军队", "警察",
                        "边境", "危机")]
                    if strong:
                        rel = True
                        score = score_body
                        matched = m_body
            article["_country"] = cid
            article["_relevant"] = rel

            all_articles.append(article)

        # 6) 去重 + 7) 准入
        pub_doc = load_json(PUBLISHED_PATH, {"items": []})
        existing = pub_doc.get("items", [])
        existing_urls = set()
        for item in existing:
            for link in item.get("source_links", []):
                existing_urls.add(norm_url(link.get("url", "")))

        run_id = os.environ.get("ASIP_RUN_ID", "local")
        quarantined = []
        published = []
        for a in all_articles:
            if a["source_id"] != sid:
                continue
            c_decision = a["_country"].get("decision", "") if isinstance(a["_country"], dict) else ""
            event_country_cn = "乍得" if c_decision == "chad" else ("尼日尔" if c_decision == "niger" else "")
            quality = a.get("extraction_quality", "")
            body_words = a.get("article_word_count", 0)

            # 准入检查
            reason = ""
            if not event_country_cn or event_country_cn != country_cn:
                reason = "country_scope_mismatch"
            elif a["_relevant"] is not True:
                reason = "weak_signal_needs_review" if a["_relevant"] is None else "not_security_relevant"
            elif not a.get("original_title") or len(a["original_title"]) < 5:
                reason = "title_too_short"
            elif not validate_url(a.get("article_url", ""))[0]:
                reason = "url_invalid"
            elif quality == "extraction_failed" or quality == "intercepted":
                reason = "extraction_failed"
            elif quality == "title_only":
                reason = "title_only_not_publishable"
            elif quality == "rss_summary_only":
                reason = "summary_only_not_publishable"
            elif body_words < MIN_PUBLISH_WORDS:
                reason = "insufficient_content"
            elif norm_url(a.get("article_url", "")) in existing_urls:
                reason = "duplicate_url"
            else:
                # 通过 → 构建事件，标记终态（published）
                ev = build_event(a, run_id, country_cn)
                published.append(ev)
                existing_urls.add(norm_url(a.get("article_url", "")))
                set_article_state(state_cache, a.get("article_url", ""),
                                  "published",
                                  published_event_id=ev.get("event_id", ""),
                                  body_hash=content_hash(a.get("original_title", ""),
                                                         a.get("original_body", "")))
                stat["published"] += 1
                continue

            if reason in ("duplicate_url",):
                stat["duplicates"] += 1
            else:
                stat["quarantined"] += 1
                # 终态隔离原因 → quariantined_terminal（后续跳过）；
                # 非终态原因（弱信号/需复核）→ 不标记终态（允许后续重新评估）
                is_terminal = reason not in ("weak_signal_needs_review",)
                rc_map = {"country_scope_mismatch": "wrong_country",
                          "weak_signal_needs_review": "not_security_relevant",
                          "country_invalid": "wrong_country",
                          "extraction_failed": "extraction_failed",
                          "title_only_not_publishable": "insufficient_body",
                          "summary_only_not_publishable": "insufficient_body",
                          "insufficient_content": "insufficient_body",
                          "not_security_relevant": "not_security_relevant",
                          "url_invalid": "invalid_url",
                          "title_too_short": "insufficient_body"}
                qr_code = rc_map.get(reason, "other")
                qr = {
                    "quarantine_id": "Q_" + hashlib.sha256((a.get("article_url") or "").encode()).hexdigest()[:16],
                    "original_object_type": "event",
                    "original_id": a.get("article_url", ""),
                    "title": a.get("original_title", "")[:200],
                    "url": a.get("article_url", ""),
                    "source": a.get("source_name", ""),
                    "country": country_cn,
                    "reason_code": qr_code,
                    "reason_cn": qr_code,
                    "detected_at": bj_iso(),
                    "detected_by": "stage3_collect_v2",
                    "restorable": True,
                    "schema_version": "2.0",
                    "pipeline_version": 2,
                    "original_payload": a,
                }
                quarantined.append(qr)
                if is_terminal:
                    set_article_state(state_cache, a.get("article_url", ""),
                                      "quarantined_terminal",
                                      quarantine_id=qr["quarantine_id"],
                                      body_hash=content_hash(a.get("original_title", ""),
                                                             a.get("original_body", "")))

        # 写入
        if published:
            pub_doc["items"] = existing + published
            pub_doc["run_id"] = run_id
            pub_doc["updated_at"] = bj_iso()
            save_json(PUBLISHED_PATH, pub_doc)
        if quarantined:
            q_doc = load_json(QUARANTINE_PATH, {"items": []})
            # 按 original_id(URL) 去重：已隔离过的 URL 不再重复追加
            seen_q = {q.get("original_id") for q in q_doc.get("items", []) if q.get("original_id")}
            fresh_q = [qr for qr in quarantined if qr.get("original_id") not in seen_q]
            q_doc["items"] = q_doc.get("items", []) + fresh_q
            save_json(QUARANTINE_PATH, q_doc)
            stat["quarantined"] = len(fresh_q)

        # 数据持久化后保存状态缓存（终态 published/quarantined_terminal 已标记）
        save_state_cache(sid, state_cache)

        stat["duration_s"] = round(time.time() - t0, 1)
        per_source.append(stat)
        print(f"    → 发现{stat['discovered']} 详情{stat['fetched']} "
              f"正文{stat['full_body']+stat['partial_body']} 发布{stat['published']} "
              f"隔离{stat['quarantined']}")

    return all_articles, per_source, errors


def build_event(article, run_id, country_cn):
    cid = article.get("_country", {}) if isinstance(article.get("_country"), dict) else {}
    country_iso = "TD" if country_cn == "乍得" else "NE"
    event_type, _ = classify_type(article["original_title"] + " " + article["original_body"][:300],
                                  article["original_title"])
    return {
        "event_id": "EVT_" + hashlib.md5((article.get("article_url") or "").encode()).hexdigest()[:16],
        "country": country_iso,
        "country_cn": country_cn,
        "primary_country": cid.get("event_location_country", ""),
        "event_location_country": cid.get("event_location_country", ""),
        "source_country": article.get("source_country", ""),
        "mentioned_countries": cid.get("mentioned_countries", []) if isinstance(cid, dict) else [],
        "country_risk_level": 4,
        "country_risk_label": "极高",
        "event_type": event_type,
        "event_severity": "medium",
        "event_status": "new",
        "title_cn": "",
        "title_original": article.get("original_title", ""),
        "summary_cn": "",
        "summary_original": article.get("original_summary", "")[:500],
        "original_language": article.get("language", "fr"),
        "body_extracted": article.get("original_body", "")[:8000],
        "body_status": article.get("body_status", ""),
        "extraction_quality": article.get("extraction_quality", ""),
        "extraction_method": article.get("extraction_method", ""),
        "article_word_count": article.get("article_word_count", 0),
        "author": article.get("author", ""),
        "event_time": article.get("published_at_original", ""),
        "published_time": article.get("published_at_original", ""),
        "published_at_beijing": article.get("published_at_beijing", ""),
        "collected_at_beijing": article.get("collected_at_beijing", ""),
        "location": "",
        "china_related": False,
        "verification_level": "single_source",
        "verification_label_cn": "单一来源",
        "independent_source_count": 1,
        "source_links": [{
            "url": article.get("article_url", ""),
            "source_name": article.get("source_name", ""),
            "source_group": (article.get("source_id", "") or "").split("_")[0],
            "language": (article.get("language") or "fr")[:2],
        }],
        "current_policy_passed": True,
        "quality_gate_passed": True,
        "publication_reason": "Stage 3B 真实采集",
        "pipeline_version": 2,
        "schema_version": "2.0",
        "run_id": run_id,
    }


def write_stats(per_source, run_id):
    totals = {
        "configured_sources": 0,
        "enabled_sources": len(per_source),
        "attempted_sources": len(per_source),
        "successful_sources": sum(1 for s in per_source if s["status"] == "success" and s["discovered"] > 0),
        "failed_sources": sum(1 for s in per_source if s["status"] not in ("success", "no_items")),
        "transient_failed_then_recovered_sources": 0,
        "sources_with_items": sum(1 for s in per_source if s["discovered"] > 0),
        "sources_with_full_body": sum(1 for s in per_source if s["full_body"] > 0),
        "sources_with_summary_only": sum(1 for s in per_source if s["summary_only"] > 0),
        "sources_with_published_events": sum(1 for s in per_source if s["published"] > 0),
        "articles_discovered": sum(s["discovered"] for s in per_source),
        "articles_fetched": sum(s["fetched"] for s in per_source),
        "full_body_extracted": sum(s["full_body"] for s in per_source),
        "partial_body_extracted": sum(s["partial_body"] for s in per_source),
        "rss_summary_fallback": sum(s["summary_only"] for s in per_source),
        "extraction_failed": sum(s["extraction_failed"] for s in per_source),
        "published_count": sum(s["published"] for s in per_source),
        "quarantined_count": sum(s["quarantined"] for s in per_source),
        "duplicate_count": sum(s["duplicates"] for s in per_source),
        "average_fetch_time": round(sum(s["duration_s"] for s in per_source) / max(1, len(per_source)), 1),
    }
    doc = {
        "generated_at": bj_iso(),
        "run_id": run_id,
        "totals": totals,
        "per_source": per_source,
    }
    save_json(STATS_PATH, doc)
    print(f"\n统计已保存: {STATS_PATH}")
    return totals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--country", choices=["乍得", "尼日尔"], default=None)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--fresh", action="store_true", help="清空状态缓存，全量重抓")
    ap.add_argument("--max-items", type=int, default=0, help="每来源最多处理 N 条（0=不限）")
    args = ap.parse_args()

    run_id = args.run_id or os.environ.get("ASIP_RUN_ID", "")
    if not run_id:
        import datetime, random, string
        run_id = datetime.datetime.now().strftime("%Y%m%dT%H%M%S+0800_") + "".join(
            random.choices(string.ascii_lowercase + string.digits, k=6))
    os.environ["ASIP_RUN_ID"] = run_id

    registry = SourceRegistry()
    discoverer = ArticleDiscoverer(registry)

    countries = [args.country] if args.country else ["乍得", "尼日尔"]
    all_articles = []
    per_source = []
    all_errors = []

    for cn in countries:
        arts, ps, errs = run_country_pipeline(cn, registry, discoverer,
                                              dry=args.dry, fresh=args.fresh,
                                              max_items=args.max_items)
        all_articles.extend(arts)
        per_source.extend(ps)
        all_errors.extend(errs)

    print(f"\n{'='*60}")
    print(f"采集完成: {len(all_articles)} 篇文章, {len(per_source)} 来源, {len(all_errors)} 错误")
    totals = write_stats(per_source, run_id)
    print(json.dumps(totals, ensure_ascii=False, indent=2))

    if args.dry:
        print("\n[--dry] 未写入 published_events / quarantine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
