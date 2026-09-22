#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""source_admission.py —— C1C §八/§十一：直接来源准入闸门 + 源记录构造。

准入闸门（全部满足才 ENABLED，任一不满足 → CANDIDATE_REJECTED + 具体 reject_reason）：
    reachable / recent_content / parser_ok / publisher_identity_known /
    public_access / asip_relevance_possible

设计纪律：
  * 闸门是**确定性**的：只看传入的探测事实（HTTP 状态、解析结果、时间戳），
    不做任何语义猜测、不调用 LLM、不为了凑数量放宽条件；
  * 不可从本环境验证的情形（本地出口代理故障）单独返回
    UNVERIFIABLE_FROM_ENV，既不算通过也不算源故障；
  * §八 Source Identity：publisher_identity_id 由 data.source_identity 确定性产出，
    同一 publisher 的多个 feed 共享同一身份，独立来源计数按身份而非 feed 数。

本模块被 C1C 扩源工具与正式测试共用（测试不依赖工作区脚本）。
"""
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))          # scripts/collectors
_SCRIPTS = os.path.dirname(_HERE)
_DATA = os.path.join(_SCRIPTS, "data")
for p in (_SCRIPTS, _DATA, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from data.source_identity import source_identity  # noqa: E402

#: §十二 低价值内容信号（仅用于 asip_relevance_possible；不用于降低 relevance 门槛）
LOW_VALUE_RX = re.compile(
    r"\b(sport|sports|football|soccer|basketball|celebrity|entertainment|"
    r"nollywood|music|movie|films?|fashion|lifestyle|beauty|gossip|horoscope|"
    r"desporto|futebol|entretenimento|celebridades|moda)\b", re.I)

COUNTRY_PREFIX = {"尼日利亚": "ng", "苏丹": "sd", "南苏丹": "ss", "刚果（金）": "cd",
                  "埃塞俄比亚": "et", "莫桑比克": "mz", "肯尼亚": "ke",
                  "利比亚": "ly", "贝宁": "bj", "索马里": "so",
                  "乍得": "chad", "尼日尔": "niger"}

#: 允许接入的语言（§九）
ALLOWED_LANGUAGES = {"en", "fr", "ar", "pt"}

#: 判定常量
ENABLED = "ENABLED"
REJECTED = "CANDIDATE_REJECTED"
UNVERIFIABLE = "UNVERIFIABLE_FROM_ENV"

#: 近期内容阈值
MAX_LATEST_AGE_HOURS = 24 * 30
MIN_ENTRIES = 5
MIN_URL_EXTRACTION = 0.90
MIN_PUBLISHED_EXTRACTION = 0.50


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "", str(s or "").lower())


def admit(pub):
    """对一个 publisher 候选执行 §十一 闸门。

    参数 pub 需含：domain / source_name / country / language / source_type /
                  homepage_status / homepage_error / discovered_feeds /
                  validated_feeds / best_feed
    返回 (decision, reasons:list, best_feed|None)
    """
    reasons = []
    bf = pub.get("best_feed") or {}
    hp = pub.get("homepage_status")
    hp_err = pub.get("homepage_error")

    # 环境不可验证 → 单列（既不算通过也不算失败）
    if bf.get("fetch_error") == UNVERIFIABLE or hp_err == UNVERIFIABLE:
        return UNVERIFIABLE, ["本地出口代理故障，无法从本环境验证"], None

    reachable = bool(bf.get("reachable")) or (isinstance(hp, int) and hp < 400)
    if not reachable:
        if hp_err in ("DNS", "TIMEOUT", "URLError"):
            reasons.append("NOT_REACHABLE:%s" % hp_err)
        elif isinstance(hp, int) and hp >= 400:
            reasons.append("NOT_REACHABLE:HTTP_%d" % hp)
        else:
            reasons.append("NOT_REACHABLE:no_response")
        return REJECTED, reasons, None

    if not bf or (bf.get("entry_count") or 0) == 0:
        reasons.append("NO_PARSABLE_FEED:discovered=%d"
                       % len(pub.get("discovered_feeds") or []))
        return REJECTED, reasons, None

    # parser_ok
    if not bf.get("xml_valid"):
        reasons.append("PARSER_NOT_OK:xml_invalid")
    if (bf.get("url_extraction") or 0) < MIN_URL_EXTRACTION:
        reasons.append("PARSER_NOT_OK:url_extraction=%.2f" % (bf.get("url_extraction") or 0))
    if (bf.get("published_extraction") or 0) < MIN_PUBLISHED_EXTRACTION:
        reasons.append("PARSER_NOT_OK:published_extraction=%.2f"
                       % (bf.get("published_extraction") or 0))

    # recent_content
    age = bf.get("age_hours_of_latest")
    if bf.get("latest_entry") is None:
        reasons.append("NO_RECENT_CONTENT:no_parseable_date")
    elif age is None or age > MAX_LATEST_AGE_HOURS:
        reasons.append("NO_RECENT_CONTENT:latest_age_hours=%s" % age)
    if (bf.get("entry_count") or 0) < MIN_ENTRIES:
        reasons.append("NO_RECENT_CONTENT:entries=%d" % (bf.get("entry_count") or 0))

    # public_access
    if bf.get("http_status") in (401, 402, 403):
        reasons.append("PUBLIC_ACCESS_FAIL:HTTP_%s" % bf.get("http_status"))
    if hp in (401, 402, 403):
        reasons.append("PUBLIC_ACCESS_FAIL:homepage_HTTP_%s" % hp)

    # publisher_identity_known
    if not pub.get("source_name") or not pub.get("domain"):
        reasons.append("PUBLISHER_IDENTITY_UNKNOWN:missing_name_or_domain")

    # 语言（§九）
    if pub.get("language") and pub["language"] not in ALLOWED_LANGUAGES:
        reasons.append("LANGUAGE_NOT_SUPPORTED:%s" % pub["language"])

    # asip_relevance_possible
    titles = bf.get("sample_titles") or []
    if titles and all(LOW_VALUE_RX.search(t or "") for t in titles):
        reasons.append("ASIP_RELEVANCE_IMPLAUSIBLE:all_samples_low_value")

    return (REJECTED, reasons, bf) if reasons else (ENABLED, [], bf)


def build_record(pub, bf, run_id_note=""):
    """生成符合 source.schema + 业务规则的 V1.1 源记录。"""
    cc = pub.get("country_code") or ""
    prefix = COUNTRY_PREFIX.get(pub.get("country"), str(cc).lower())
    sid = "%s_%s" % (prefix, _slug(pub["domain"].split(".")[0]))
    dom = pub["domain"]
    name = pub.get("source_name") or dom
    lang = pub.get("language") or "en"
    ident = source_identity({"source_id": sid, "source_name": name,
                             "source_group": _slug(dom.split(".")[0]),
                             "url": "https://" + dom + "/",
                             "feed_url": bf["feed_url"]})
    group = _slug(dom.split(".")[0])
    note = ("C1C direct source expansion（%s）；feed=%s；entries=%s；latest=%s；"
            "publisher_identity=%s" % (pub.get("priority"), bf["feed_url"],
                                       bf.get("entry_count"), bf.get("latest_entry"),
                                       ident["identity_key"]))
    return {
        "source_id": sid,
        "source_group": group,
        "publisher_identity_id": ident["source_identity_id"],
        "source_name": name,
        "source_type": pub.get("source_type") or "local_media",
        "source_reliability_tier": "tier_2",
        "country_scope": [pub.get("country")],
        "language": [lang],
        "is_direct_origin": True,
        "is_republication_platform": False,
        "enabled": True,
        "tested": True,
        "claim_origin_type": ("media_reporting"
                              if pub.get("source_type") == "local_media" else "unknown"),
        "url": "https://" + dom + "/",
        "notes": note,
        "legacy_payload": {
            "source_id": sid, "name": name, "country": pub.get("country"),
            "url": "https://" + dom + "/", "language": lang,
            "source_type": pub.get("source_type") or "local_media",
            "source_position": pub.get("source_type") or "local_media",
            "collection_method": "rss", "feed_url": bf["feed_url"],
            "category_urls": [], "query": "", "domain": dom,
            "enabled": True, "tested": True, "lead_only": False,
            "requires_api": False, "last_test_at": bf.get("latest_entry") or "",
            "last_success_at": "", "last_failure_at": "", "failure_count": 0,
            "articles_detected_last_run": 0, "relevant_articles_last_run": 0,
            "status": "active", "notes": note,
            "c1c_batch": pub.get("batch", "user_list"),
            "c1c_priority": pub.get("priority"),
            "publisher_identity_id": ident["source_identity_id"],
            "c1c_run_note": run_id_note,
        },
        "listing_urls": [], "listing_max_items": 0,
        "article_link_selectors": [], "exclude_link_patterns": [],
    }


def direct_vs_gdelt_counts(sources):
    """§十四：分别统计 DIRECT_SOURCE_COUNT 与 GDELT_CONFIG_COUNT。

    DIRECT = 直接 publisher 来源（rss/atom/html/reliefweb 等直达发布方的通道）
    GDELT   = 通过 GDELT 检索接入的记录数（同一域名按国家重复登记只会重复计数，
              因此同时给出 GDELT distinct publisher 数，避免把 config 数当独立 publisher）。
    """
    direct, gdelt, gdelt_pub = [], [], set()
    for s in sources:
        if not s.get("enabled", (s.get("legacy_payload") or {}).get("enabled", False)):
            continue
        lp = s.get("legacy_payload") or {}
        m = lp.get("collection_method") or ""
        if m == "gdelt_search":
            gdelt.append(s.get("source_id"))
            q = lp.get("query") or ""
            for d in re.findall(r"domain:([^\s()]+)", q):
                gdelt_pub.add(d.lower())
        else:
            direct.append(s.get("source_id"))
    return {
        "DIRECT_SOURCE_COUNT": len(direct),
        "GDELT_CONFIG_COUNT": len(gdelt),
        "GDELT_DISTINCT_PUBLISHER_DOMAINS": len(gdelt_pub),
        "note": "GDELT config 数不得当作独立 publisher 数；独立出源性按 "
                "publisher_identity / 域名判定。",
    }
