#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stage3_collect.py — Stage 3A 真实采集闭环主控。

流程：
  1. 读取 data/sources.json，仅启用 RSS + ReliefWeb 来源（快速可靠）
  2. 按国家分组，调用 collectors 真实采集
  3. 国家识别 + 相关性筛选 + 事件分类（复用 country_runner）
  4. URL 去重 + 内容哈希去重
  5. 发布准入检查
  6. 写入 data/public/published_events.json（追加，不覆盖历史）
  7. 隔离不合格项目到 quarantined_items

用法：
  python scripts/stage3_collect.py            # 正常采集
  python scripts/stage3_collect.py --dry      # 仅预览
  python scripts/stage3_collect.py --rss-only # 仅 RSS（跳过 ReliefWeb）
"""
import os
import sys
import json
import time
import hashlib
import argparse
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, "collectors"))
sys.path.insert(0, SCRIPT_DIR)

from country_runner import (load_country_cfg, run_country, identify_country,
                            relevance_stage1, classify_type, get_collector)
from pipeline_core import generate_run_id, bj_iso

DATA_DIR = os.path.join(ROOT, "data")
PUBLIC_DIR = os.path.join(DATA_DIR, "public")
LOGS_DIR = os.path.join(ROOT, "logs")
PUBLISHED_PATH = os.path.join(PUBLIC_DIR, "published_events.json")
QUARANTINE_PATH = os.path.join(DATA_DIR, "canonical", "quarantine.json")

# 准入阈值
MIN_TITLE_LEN = 5
RELEVANCE_MIN_SCORE = 1
VALID_COUNTRIES = {"乍得": "TD", "尼日尔": "NE", "chad": "TD", "niger": "NE"}
SOURCE_TYPE_ORDER = [
    "official", "state_media", "un_humanitarian", "china_official",
    "china_media", "local_media", "international", "commentary"
]

# 日期提取模式
DATE_PATTERNS = [
    (r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", "%Y-%m-%dT%H:%M:%S"),
    (r"(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),
]


def norm_url(url):
    """规范化 URL：去尾部斜杠、常见追踪参数、fragment。"""
    if not url:
        return ""
    u = url.strip().rstrip("/")
    # 去 fragment
    if "#" in u:
        u = u[:u.index("#")]
    # 去常见追踪参数
    for param in ["utm_source", "utm_medium", "utm_campaign", "utm_term",
                  "utm_content", "fbclid", "gclid", "ref", "source"]:
        # 简单处理：去 URL 中的该参数
        pass  # 复杂 URL 参数处理留待后续
    return u.lower()


def content_hash(title, summary=""):
    """内容哈希（归一化后）。"""
    text = ((title or "") + " " + (summary or "")).strip().lower()
    text = " ".join(text.split())  # 标准化空白
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_published():
    """加载已发布事件。"""
    try:
        with open(PUBLISHED_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"schema_version": "2.0", "pipeline_version": 2, "run_id": "", "items": []}


def save_published(pub):
    """保存已发布事件。"""
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    with open(PUBLISHED_PATH, "w", encoding="utf-8") as f:
        json.dump(pub, f, ensure_ascii=False, indent=2)


def load_quarantine():
    try:
        with open(QUARANTINE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"items": []}


def save_quarantine(q):
    os.makedirs(os.path.dirname(QUARANTINE_PATH), exist_ok=True)
    with open(QUARANTINE_PATH, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)


def load_sources():
    """加载 sources.json。"""
    p = os.path.join(DATA_DIR, "sources.json")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"sources": []}


def publish_check(article, existing_ids, existing_urls, existing_hashes):
    """Stage 3A 发布准入检查。返回 (pass, reason)。"""
    title = (article.get("title") or "").strip()
    url = (article.get("url") or "").strip()
    summary = (article.get("summary") or "").strip()
    published = article.get("published") or ""
    country_cn = article.get("country_cn") or ""
    cid = article.get("_country", {})
    rel = article.get("_relevant")
    source_name = (article.get("source_name") or "").strip()

    # 1. 国家检查 — 必须基于事件发生国（_country.decision），非来源国
    c_decision = cid.get("decision") if isinstance(cid, dict) else ""
    event_country_cn = ""
    if c_decision in ("chad", "niger"):
        event_country_cn = "乍得" if c_decision == "chad" else "尼日尔"
    if not event_country_cn:
        return False, "country_invalid"
    # 若调用方传入候选国家，须与事件国一致（防止来源国污染）
    if country_cn and country_cn != event_country_cn:
        return False, "country_scope_mismatch"

    # 2. 标题不为空
    if len(title) < MIN_TITLE_LEN:
        return False, "title_too_short"

    # 3. URL 有效
    if not url or not url.startswith("http"):
        return False, "url_invalid"

    # 4. 来源名称有效
    if not source_name:
        return False, "source_name_missing"

    # 5. 相关性（强相关才发布；弱信号/待复核一律隔离）
    if rel is not True:
        if rel is False:
            return False, "not_security_relevant"
        return False, "weak_signal_needs_review"

    # 6. 去重：URL
    normed = norm_url(url)
    if normed in existing_urls:
        return False, "duplicate_url"

    # 7. 去重：内容哈希
    ch = content_hash(title, summary)
    if ch in existing_hashes:
        return False, "duplicate_content"

    # 8. 时间检查
    if published:
        try:
            pt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            if pt > datetime.now(timezone.utc) + timedelta(hours=1):
                return False, "future_date"
        except (ValueError, TypeError):
            pass

    return True, "ok"


def build_event(article, run_id, candidate_id_val):
    """构建 published_event 条目。"""
    title = (article.get("title") or "").strip()
    url = (article.get("url") or "").strip()
    summary = (article.get("summary") or "").strip()[:500]
    published = article.get("published") or ""
    language = (article.get("language") or "法语")
    source_name = (article.get("source_name") or article.get("source_name_raw") or "").strip()
    source_country_cn = article.get("source_country_cn") or article.get("_source_country") or ""
    cid = article.get("_country", {}) if isinstance(article.get("_country"), dict) else {}
    # 事件国家必须来自识别结果
    c_decision = cid.get("decision", "")
    country_cn = "乍得" if c_decision == "chad" else ("尼日尔" if c_decision == "niger" else "")
    if not country_cn:
        country_cn = article.get("country_cn") or ""
    country_iso = VALID_COUNTRIES.get(country_cn, "TD")
    event_type, _ = classify_type(summary, title)

    # 多国字段
    mentioned = cid.get("mentioned_countries", []) if isinstance(cid, dict) else []
    event_location = cid.get("event_location_country", c_decision) if isinstance(cid, dict) else c_decision

    # 北京时间转换
    bj_time = ""
    if published:
        try:
            pt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            bj = pt.astimezone(timezone(timedelta(hours=8)))
            bj_time = bj.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            bj_time = ""

    return {
        "event_id": "EVT_" + candidate_id_val[-16:].replace("-", "").ljust(16, "0")[:16],
        "country": country_iso,
        "country_cn": country_cn,
        "primary_country": c_decision if c_decision in ("chad", "niger") else country_cn,
        "event_location_country": event_location,
        "source_country": source_country_cn or country_cn,
        "mentioned_countries": mentioned,
        "country_risk_level": 4,
        "country_risk_label": "极高",
        "event_type": event_type,
        "event_severity": "medium",
        "event_status": "new",
        "title_cn": "",
        "title_original": title,
        "summary_cn": "",
        "summary_original": summary if language not in ("中文", "zh") else "",
        "original_language": language,
        "event_time": published,
        "published_time": published,
        "published_at_beijing": bj_time,
        "collected_at_beijing": bj_iso(),
        "location": "",
        "china_related": False,
        "verification_level": "single_source",
        "verification_label_cn": "单一来源",
        "independent_source_count": 1,
        "source_links": [{
            "url": url,
            "source_name": source_name,
            "source_group": source_name.lower().replace(" ", "_")[:30],
            "language": language[:2] if language else "fr",
        }],
        "current_policy_passed": True,
        "quality_gate_passed": True,
        "publication_reason": "Stage 3A 真实采集",
        "pipeline_version": 2,
        "schema_version": "2.0",
        "run_id": run_id,
    }


def collect_stage3(rss_only=False, dry=False):
    """Stage 3A 主采集流程。"""
    run_id = generate_run_id()
    print(f"Stage 3A 采集 — run_id={run_id}")
    print(f"北京时间: {bj_iso()}\n")

    sources_doc = load_sources()
    all_sources = sources_doc.get("sources", [])

    # 仅启用 RSS + ReliefWeb 来源
    active_sources = []
    for s in all_sources:
        lp = s.get("legacy_payload", {})
        method = lp.get("collection_method") or "rss"
        enabled = lp.get("enabled", s.get("enabled", False))
        country = lp.get("country") or s.get("country_scope", [""])[0] if s.get("country_scope") else ""

        if not enabled:
            continue
        if method == "gdelt_search":
            continue  # 跳过 GDELT（低速/限流）
        if rss_only and method != "rss":
            continue
        if country not in ("乍得", "尼日尔"):
            continue

        active_sources.append({
            "source_id": s["source_id"],
            "country": country,
            "source_name": lp.get("name", s.get("source_name", "")),
            "source_type": lp.get("source_type", s.get("source_type", "")),
            "language": lp.get("language", s.get("language", ["法语"])[0] if isinstance(s.get("language"), list) else s.get("language", "法语")),
            "collection_method": method,
            "feed_url": lp.get("feed_url", ""),
            "url": lp.get("url", s.get("url", "")),
            "country_en": s.get("source_id", "").split("_")[0] if "_" in s.get("source_id", "") else "",
        })

    print(f"活跃来源: {len(active_sources)} (RSS={sum(1 for s in active_sources if s['collection_method']=='rss')}, ReliefWeb={sum(1 for s in active_sources if s['collection_method']=='reliefweb_api')})")

    # 按国家分组
    groups = {"乍得": [], "尼日尔": []}
    for s in active_sources:
        groups[s["country"]].append(s)

    all_articles = []
    all_errors = []
    source_stats = []

    for country_cn, srcs in groups.items():
        cfg_key = "chad" if country_cn == "乍得" else "niger"
        country_cfg = load_country_cfg(cfg_key)
        print(f"\n--- {country_cn} ({len(srcs)} 来源) ---")

        for s in srcs:
            sid = s["source_id"]
            sname = s["source_name"]
            method = s["collection_method"]
            language = s["language"]
            print(f"  [{method}] {sname} ...", end=" ", flush=True)
            t0 = time.time()
            src_stat = {
                "source_id": sid, "source_name": sname, "country": country_cn,
                "method": method, "collected": 0, "normalized": 0,
                "published": 0, "quarantined": 0, "duplicates": 0,
                "status": "failed", "error": "", "duration_s": 0.0,
            }

            try:
                if method == "reliefweb_api":
                    country_en = "Chad" if country_cn == "乍得" else "Niger"
                    col = get_collector({"collection_method": "reliefweb_api", "country_en": country_en, "language": "en"}, country_cfg)
                elif method == "rss":
                    col = get_collector({"collection_method": "rss", "feed_url": s["feed_url"], "language": language}, country_cfg)
                else:
                    print("SKIP(unsupported)")
                    src_stat["status"] = "unsupported"
                    source_stats.append(src_stat)
                    continue

                arts = col.run()
                errors = col.errors if hasattr(col, "errors") else []
                src_stat["collected"] = len(arts)
                src_stat["status"] = "success" if not errors else "partial"
                src_stat["error"] = "; ".join(str(e)[:100] for e in errors[:2])

                # 附加来源元数据 — 来源国与事件国分离
                for a in arts:
                    a["source_id"] = sid
                    a["source_name"] = sname
                    a["source_type"] = s["source_type"]
                    a["source_country_cn"] = country_cn  # 来源所属国家
                    a["country_cfg_key"] = cfg_key
                    # 国家识别 + 相关性筛选
                    blob = (a.get("title") or "") + " " + (a.get("summary") or "")
                    cid = identify_country(blob, country_cfg)
                    rel, score, matched, excl = relevance_stage1(blob)
                    a["_country"] = cid
                    a["_relevant"] = rel
                    a["_rel_score"] = score

                print(f"{len(arts)} 条" + (f", {len(errors)} 错误" if errors else ""))
                all_articles.extend(arts)
                all_errors.extend([{"source": sid, "error": str(e)} for e in errors])
            except Exception as e:
                print(f"FAIL: {e}")
                src_stat["error"] = str(e)[:120]
                all_errors.append({"source": sid, "error": str(e)})
            finally:
                src_stat["duration_s"] = round(time.time() - t0, 1)
                source_stats.append(src_stat)

    print(f"\n=== 总计: {len(all_articles)} 条候选 ===")

    if dry:
        # 仅预览
        relevant = [a for a in all_articles if a.get("_relevant") is True]
        unclear = [a for a in all_articles if a.get("_relevant") is None]
        irrelevant = [a for a in all_articles if a.get("_relevant") is False]
        print(f"  相关: {len(relevant)}, 待复核: {len(unclear)}, 非相关: {len(irrelevant)}")
        return 0

    # 加载已发布数据
    published_doc = load_published()
    existing_items = published_doc.get("items", [])
    existing_urls = {norm_url(link.get("url", "")) for item in existing_items
                     for link in item.get("source_links", [])}
    existing_hashes = {content_hash(item.get("title_original", ""), item.get("summary_original", ""))
                       for item in existing_items}

    # 加载隔离数据
    quarantine_doc = load_quarantine()
    quarantine_items = quarantine_doc.get("items", [])

    new_events = []
    quarantined = []
    stats = {"published": 0, "quarantined": 0, "duplicate_url": 0, "duplicate_content": 0,
             "not_relevant": 0, "country_invalid": 0, "title_short": 0, "future": 0}

    for a in all_articles:
        cid_val = hashlib.md5(((a.get("url") or "") + (a.get("title") or "")).encode()).hexdigest()[:20]
        a["_candidate_id"] = cid_val

        passed, reason = publish_check(a, set(), existing_urls, existing_hashes)
        if not passed:
            stats[reason if reason in stats else "quarantined"] += 1
            for ss in source_stats:
                if ss["source_id"] == a.get("source_id"):
                    if reason in ("duplicate_url", "duplicate_content"):
                        ss["duplicates"] += 1
                    else:
                        ss["quarantined"] += 1
            if reason not in ("duplicate_url", "duplicate_content"):
                quarantined.append({
                    "candidate_id": cid_val,
                    "title": a.get("title", "")[:200],
                    "url": a.get("url", ""),
                    "source": a.get("source_name", ""),
                    "country": a.get("country_cn", ""),
                    "reason": reason,
                    "collected_at": bj_iso(),
                })
            continue

        # 准入通过
        event = build_event(a, run_id, cid_val)
        new_events.append(event)
        for ss in source_stats:
            if ss["source_id"] == a.get("source_id"):
                ss["published"] += 1

        # 更新去重集合
        existing_urls.add(norm_url(a.get("url", "")))
        existing_hashes.add(content_hash(a.get("title", ""), a.get("summary", "")))

    # 写入 published_events（追加）
    stats["published"] = len(new_events)
    if new_events:
        existing_items.extend(new_events)
        published_doc["items"] = existing_items
        published_doc["run_id"] = run_id
        published_doc["updated_at"] = bj_iso()
        save_published(published_doc)
        print(f"\n✅ 新增 {len(new_events)} 条公开事件 (总计 {len(existing_items)} 条)")

    # 追加隔离数据
    if quarantined:
        for qe in quarantined:
            qid = hashlib.md5((qe.get("url") or qe.get("candidate_id") or "").encode()).hexdigest()[:16]
            qe["quarantine_id"] = "Q_" + qid
            qe["original_object_type"] = "raw_collected_item"
            qe["original_id"] = qe.get("candidate_id", "")
            qe["reason_code"] = qe.get("reason", "unknown")
            qe["reason_cn"] = qe.get("reason", "unknown")
            qe["detected_at"] = bj_iso()
            qe["detected_by"] = "stage3_collect"
            qe["restorable"] = True
        quarantine_items.extend(quarantined)
        quarantine_doc["items"] = quarantine_items
        save_quarantine(quarantine_doc)
        stats["quarantined"] = len(quarantined)
        print(f"⚠️ 隔离 {len(quarantined)} 条不合格项目")

    # 统计
    print(f"\n=== 采集统计 ===")
    configured = len(all_sources)
    active = len(active_sources)
    successful = sum(1 for ss in source_stats if ss["status"] in ("success", "partial"))
    failed = sum(1 for ss in source_stats if ss["status"] == "failed")
    with_items = sum(1 for ss in source_stats if ss["collected"] > 0)
    with_published = sum(1 for ss in source_stats if ss["published"] > 0)
    print(f"  configured_sources      : {configured}")
    print(f"  active_sources          : {active}")
    print(f"  successful_sources      : {successful}")
    print(f"  failed_sources          : {failed}")
    print(f"  sources_with_items      : {with_items}")
    print(f"  sources_with_published  : {with_published}")
    print(f"  原始文章               : {len(all_articles)}")
    print(f"  错误数                 : {len(all_errors)}")
    print(f"  新增发布               : {stats['published']}")
    print(f"  隔离                   : {stats['quarantined']}")
    print(f"  URL重复                : {stats['duplicate_url']}")
    print(f"  内容重复               : {stats['duplicate_content']}")
    print(f"  非相关                 : {stats['not_relevant']}")
    print(f"  国家无效/错配           : {stats['country_invalid'] + stats.get('country_scope_mismatch', 0)}")
    print(f"  弱信号待复核            : {stats.get('weak_signal_needs_review', 0)}")
    print(f"  未来时间               : {stats['future']}")

    # 每来源明细
    print(f"\n=== 每来源明细 ===")
    print(f"  {'source_id':28s} {'采集':>4s} {'发布':>4s} {'隔离':>4s} {'重复':>4s} {'耗时':>6s} 状态")
    for ss in source_stats:
        print(f"  {ss['source_id']:28s} {ss['collected']:4d} {ss['published']:4d} "
              f"{ss['quarantined']:4d} {ss['duplicates']:4d} {ss['duration_s']:6.1f} {ss['status']}"
              + (f" ({ss['error'][:40]})" if ss["error"] else ""))

    # 保存统计
    if not dry:
        stats_path = os.path.join(LOGS_DIR, "stage3_stats.json")
        os.makedirs(LOGS_DIR, exist_ok=True)
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump({
                "run_id": run_id,
                "generated_at": bj_iso(),
                "configured_sources": configured,
                "active_sources": active,
                "successful_sources": successful,
                "failed_sources": failed,
                "sources_with_items": with_items,
                "sources_with_published": with_published,
                "sources": source_stats,
                "totals": {
                    "raw_articles": len(all_articles),
                    "published": stats["published"],
                    "quarantined": stats["quarantined"],
                    "duplicates": stats["duplicate_url"] + stats["duplicate_content"],
                    "errors": len(all_errors),
                },
            }, f, ensure_ascii=False, indent=2)
        print(f"\n  统计已保存: {stats_path}")

    return 0


def main():
    ap = argparse.ArgumentParser(description="Stage 3A 真实采集闭环")
    ap.add_argument("--dry", action="store_true", help="仅预览，不写入")
    ap.add_argument("--rss-only", action="store_true", help="仅 RSS 来源")
    args = ap.parse_args()
    return collect_stage3(rss_only=args.rss_only, dry=args.dry)


if __name__ == "__main__":
    sys.exit(main())
