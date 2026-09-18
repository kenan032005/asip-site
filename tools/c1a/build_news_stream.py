#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP V1.1-C1A -- news-stream-v1 builder.

Builds an ADDITIVE News / Signal Stream from content ASIP already collects.
It never touches, relaxes or re-derives the Canonical (Verified Event) tier:
the two tiers are computed side by side and reported separately.

Funnel:  Source Observation -> News/Signal Stream -> Event Cluster
         -> Verified Event -> Priority Intelligence

Design invariants
-----------------
1. NEWS_ELIGIBLE  requires a URL + a time + a title + in-scope country +
   not quarantined + not a duplicate.  Multi-source is NOT required --
   that is the entire point of a signal tier.
2. CANONICAL_ELIGIBLE keeps the untouched production threshold
   (independent_source_count >= 2).  It is computed here purely as a
   control number so any accidental relaxation is visible.
3. Nothing is translated, generated or inferred.  Where the upstream
   pipeline has not populated title_cn, the item is emitted with
   title_cn = null and title_cn_missing = true, and the original-language
   title is surfaced instead.  No fabricated Chinese content.

Usage:
  python tools/c1a/build_news_stream.py \
      --live  <dir with data_*.json productions> \
      --internal <dir with canonical/ etc.> \
      --out   <repo root>
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import sys

SCHEMA = "news-stream-v1"
SCHEMA_VERSION = "1.0.0"
BUILDER_VERSION = "c1a-1.0.0"

CN = datetime.timezone(datetime.timedelta(hours=8))
UTC = datetime.timezone.utc

# Chad / Niger first (ASIP core), plus the wider Sahel / Lake Chad Basin
# neighbourhood that already appears in the corpus.
ISO2 = {
    "乍得": "TD", "尼日尔": "NE", "尼日利亚": "NG", "苏丹": "SD", "南苏丹": "SS",
    "肯尼亚": "KE", "埃塞俄比亚": "ET", "利比亚": "LY", "贝宁": "BJ",
    "莫桑比克": "MZ", "埃及": "EG", "阿尔及利亚": "DZ", "乌干达": "UG",
    "安哥拉": "AO", "加纳": "GH", "马里": "ML", "布基纳法索": "BF",
    "喀麦隆": "CM", "中非共和国": "CF", "刚果民主共和国": "CD", "索马里": "SO",
    "塞内加尔": "SN", "毛里塔尼亚": "MR", "多哥": "TG", "科特迪瓦": "CI",
}
ISO2_REV = {v: k for k, v in ISO2.items()}
ISO3 = {"TD": "TCD", "NE": "NER", "NG": "NGA", "SD": "SDN", "SS": "SSD",
        "KE": "KEN", "ET": "ETH", "LY": "LBY", "BJ": "BEN", "MZ": "MOZ",
        "EG": "EGY", "DZ": "DZA", "UG": "UGA", "AO": "AGO", "GH": "GHA"}

ETYPE_CN = {
    "armed_conflict": "武装冲突", "other_security": "其他安全",
    "terrorist_attack": "恐怖袭击", "military_operation": "军事行动",
    "public_health": "公共卫生", "strike": "罢工行动",
    "civil_unrest": "民众骚乱", "natural_disaster": "自然灾害",
    "infrastructure_security": "基础设施安全", "political_crisis": "政治危机",
    "serious_crime": "严重犯罪", "communal_conflict": "族群冲突",
    "protest": "抗议示威", "kidnapping": "绑架", "border_security": "边境安全",
    "china_related": "涉华安全", "displacement": "流离失所",
    "food_security": "粮食安全", "maritime_security": "海上安全",
}
VERIF_CN = {
    "single_source": "单一来源 · 待核实",
    "high_reliability_single_source": "高可信单一来源 · 待核实",
    "multi_source": "多来源已核实",
    "verified": "已核实",
    "not_checked": "尚未核实",
    "partial": "部分核实",
}
# Recency bands.  Deliberately wide so a dormant collector cannot be
# silently disguised as "fresh".
FRESH_H = 24 * 7
RECENT_H = 24 * 30

CORE_SCOPE = {"TD", "NE"}


# --------------------------------------------------------------------- util
def rd(p, default=None):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def items(o, *ks):
    if isinstance(o, list):
        return o
    if isinstance(o, dict):
        for k in ks or ("items", "events", "sources", "snapshots"):
            if isinstance(o.get(k), list):
                return o[k]
    return []


def ts(v):
    if v in (None, ""):
        return None
    try:
        d = datetime.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    except Exception:
        return None


def bj(d):
    return d.astimezone(CN).strftime("%Y-%m-%d %H:%M") if d else None


def bj_iso(d):
    return d.astimezone(CN).isoformat() if d else None


_URL_JUNK = re.compile(r"^(https?://)?(www\.)?", re.I)
_WS = re.compile(r"\s+")
_NONWORD = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")


def norm_url(u):
    if not u:
        return ""
    u = str(u).strip()
    u = u.split("#", 1)[0].split("?", 1)[0]
    u = _URL_JUNK.sub("", u).rstrip("/").lower()
    return u


def norm_text(t):
    if not t:
        return ""
    t = _WS.sub(" ", str(t)).strip().lower()
    return _NONWORD.sub(" ", t).strip()


def sha1(*parts):
    h = hashlib.sha1()
    for p in parts:
        h.update(str(p).encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


def iso2_of(country_cn=None, country_raw=None):
    if country_raw and str(country_raw).upper() in ISO2_REV:
        return str(country_raw).upper()
    if country_cn in ISO2:
        return ISO2[country_cn]
    return None


# --------------------------------------------------------------------- gate
class Gate:
    """News Admission Gate.  Ordered, explicit, auditable."""

    def __init__(self):
        self.seen_keys = {}
        self.counts = collections.Counter()
        self.rejects = collections.Counter()
        self.reject_examples = collections.defaultdict(list)

    def reject(self, code, item, why):
        self.rejects[code] += 1
        if len(self.reject_examples[code]) < 3:
            self.reject_examples[code].append(
                {"id": item.get("src_id"), "why": why})
        return None

    def admit(self, cand):
        """cand: dict with url/title/time/country/quarantine/dedup_key."""
        chk = [
            ("REJ_NO_URL", bool(norm_url(cand.get("source_url"))), "no usable url"),
            ("REJ_NO_TIME", bool(cand.get("observed_at")), "no observed_at/published time"),
            ("REJ_NO_TITLE", bool((cand.get("title_cn") or cand.get("title_original"))) , "no title in any language"),
            ("REJ_QUARANTINED", not cand.get("quarantined"), "id present in quarantine store"),
            ("REJ_OUT_OF_SCOPE", bool(cand.get("country_iso2")), "country not resolvable / out of scope"),
        ]
        for code, ok, why in chk:
            if not ok:
                return self.reject(code, cand, why)
        dk = cand["dedup_key"]
        if dk in self.seen_keys:
            return self.reject("REJ_DUPLICATE", cand, "dedup_key=%s already admitted" % dk[:12])
        self.seen_keys[dk] = cand["src_id"]
        self.counts["ADMIT"] += 1
        return cand


# --------------------------------------------------------------------- build
def build(live_dir, internal_dir, out_root, now=None):
    now = now or datetime.datetime.now(UTC)
    gateway = Gate()

    live = lambda n: rd(os.path.join(live_dir, n), {})
    ipe = items(live("data_public_published_events.json"))
    ime = items(live("data_master_events.json"), "events")
    iev = items(live("data_events.json"), "events")
    icm = live("data_public_current_metrics.json")
    iso_ = live("data_site_overview.json")

    inl = lambda n: rd(os.path.join(internal_dir, n), {})
    arts = items(inl(os.path.join("canonical", "articles.json")))
    clusters = items(inl(os.path.join("canonical", "event_clusters.json")))
    qcanon = items(inl(os.path.join("canonical", "quarantine.json")))
    pend = items(inl("pending_events.json"))
    srcs = items(inl("sources.json"))

    q_ids = {q.get("original_id") for q in qcanon if q.get("original_id")}
    q_urls = {norm_url((q.get("legacy_payload") or {}).get("source_url")) for q in qcanon}
    q_urls.discard("")

    # article_id -> canonical cluster
    art2ev = {}
    for c in clusters:
        for aid in (c.get("article_ids") or []):
            art2ev[aid] = c.get("event_id")
    cluster_ids = {c.get("event_id") for c in clusters}

    src_meta = {s.get("source_id"): s for s in srcs}
    candidates = []

    # ---- A. LIVING LAYER: live published observations (URL-bearing, fresh)
    for x in ipe:
        sl = (x.get("source_links") or [{}])
        sl0 = sl[0] if sl else {}
        url = sl0.get("url") or x.get("canonical_url") or ""
        t = ts(x.get("event_time")) or ts(x.get("published_time"))
        cn = x.get("country_cn")
        c2 = iso2_of(cn, x.get("country"))
        cand = {
            "src_id": x.get("event_id"), "origin": "live_published_events",
            "source_url": url, "observed_at": t,
            "title_cn": x.get("title_cn") or None,
            "title_original": x.get("title_original") or None,
            "summary_cn": x.get("summary_cn") or None,
            "summary_original": x.get("summary_original") or None,
            "country_cn": cn or ISO2_REV.get(c2),
            "country_iso2": c2,
            "event_type": x.get("event_type"),
            "source_name": sl0.get("source_name") or x.get("source_name"),
            "source_group": sl0.get("source_group"),
            "source_language": sl0.get("language"),
            "verification_level": x.get("verification_level") or "not_checked",
            "independent_source_count": int(x.get("independent_source_count") or 0),
            "quality_gate_passed": x.get("quality_gate_passed"),
            "current_policy_passed": x.get("current_policy_passed"),
            "china_related": bool(x.get("china_related")),
            "has_body": bool(x.get("body_extracted")) or x.get("body_status") in ("full_body", "partial_body"),
            "body_status": x.get("body_status") or "",
            "fetch_http_status": x.get("fetch_http_status") or 0,
            "discovery_method": x.get("discovery_method") or "",
            "run_id": x.get("run_id") or "",
            "linked_event_id": x.get("event_id") if x.get("event_id") in cluster_ids else None,
            "quarantined": x.get("event_id") in q_ids,
            "news_status": "signal",
        }
        cand["dedup_key"] = sha1("u", norm_url(url)) if norm_url(url) else sha1(
            "t", c2, norm_text(cand["title_original"] or cand["title_cn"]), str(t)[:10])
        candidates.append(cand)

    # ---- B. ARCHIVE LAYER: canonical article corpus (FROZEN upstream)
    for a in arts:
        url = a.get("canonical_url") or a.get("article_url") or ""
        t = ts(a.get("published_at"))
        cn = a.get("event_country") or a.get("detected_country")
        c2 = iso2_of(cn)
        cand = {
            "src_id": a.get("article_id"), "origin": "canonical_articles",
            "source_url": url, "observed_at": t,
            "title_cn": a.get("title_cn") or None,
            "title_original": a.get("title_original") or None,
            "summary_cn": a.get("summary_cn") or None,
            "summary_original": a.get("summary_original") or None,
            "country_cn": cn, "country_iso2": c2,
            "event_type": a.get("event_type"),
            "source_name": a.get("source_name"),
            "source_group": a.get("source_group"),
            "source_language": a.get("language"),
            "verification_level": "single_source",
            "independent_source_count": 1,
            "quality_gate_passed": None,
            "current_policy_passed": None,
            "china_related": bool(a.get("china_related")),
            "has_body": bool(a.get("content_excerpt")),
            "body_status": "excerpt" if a.get("content_excerpt") else "",
            "fetch_http_status": 0,
            "discovery_method": "",
            "run_id": a.get("run_id") or "",
            "linked_event_id": a.get("linked_event_id") or art2ev.get(a.get("article_id")),
            "quarantined": a.get("article_id") in q_ids or norm_url(url) in q_urls,
            "news_status": "signal",
        }
        cand["dedup_key"] = sha1("u", norm_url(url)) if norm_url(url) else sha1(
            "t", c2, norm_text(cand["title_original"] or cand["title_cn"]), str(t)[:10])
        candidates.append(cand)

    # ---- C. HELD LAYER: pending events awaiting a second source
    for p in pend:
        url = p.get("url") or ""
        t = ts(p.get("published_time"))
        cn = p.get("country")
        c2 = iso2_of(cn)
        cand = {
            "src_id": p.get("candidate_id"), "origin": "pending_events",
            "source_url": url, "observed_at": t,
            "title_cn": p.get("title_cn") or None,
            "title_original": p.get("title_original") or None,
            "summary_cn": p.get("summary_cn") or None,
            "summary_original": p.get("summary_original") or None,
            "country_cn": cn, "country_iso2": c2,
            "event_type": p.get("event_type"),
            "source_name": p.get("source_name"), "source_group": None,
            "source_language": None,
            "verification_level": "single_source",
            "independent_source_count": 1,
            "quality_gate_passed": False, "current_policy_passed": False,
            "china_related": False,
            "has_body": bool(p.get("summary_original")),
            "body_status": "excerpt" if p.get("summary_original") else "",
            "fetch_http_status": 0, "discovery_method": "",
            "run_id": "",
            "linked_event_id": art2ev.get(p.get("candidate_id")),
            "quarantined": p.get("candidate_id") in q_ids,
            "news_status": "held",
        }
        cand["dedup_key"] = sha1("u", norm_url(url)) if norm_url(url) else sha1(
            "t", c2, norm_text(cand["title_original"] or cand["title_cn"]), str(t)[:10])
        candidates.append(cand)

    total_candidates = len(candidates)

    # ---- gate + dedup + update semantics
    admitted = []
    for c in candidates:
        ok = gateway.admit(c)
        if ok is not None:
            admitted.append(c)

    # group by dedup_key to derive update semantics (first/last seen, count)
    by_key = collections.defaultdict(list)
    for c in admitted:
        by_key[c["dedup_key"]].append(c)

    news = []
    for dk, group in by_key.items():
        group.sort(key=lambda g: g["observed_at"] or now)
        head = dict(group[0])
        head["first_seen_at"] = min(g["observed_at"] for g in group if g["observed_at"])
        head["last_seen_at"] = max(g["observed_at"] for g in group if g["observed_at"])
        head["seen_count"] = len(group)
        head["is_update"] = len(group) > 1
        head["update_count"] = len(group) - 1
        head["corroborating_sources"] = sorted({g["source_name"] for g in group if g["source_name"]})
        head["news_id"] = "NEWS-" + dk[:16]
        head["dedup_key"] = dk
        news.append(head)

    news.sort(key=lambda x: x["last_seen_at"], reverse=True)

    # ---- classify + decorate
    for n in news:
        t = n["last_seen_at"]
        age_h = (now - t).total_seconds() / 3600.0
        n["age_hours"] = round(age_h, 1)
        n["recency"] = "fresh" if age_h <= FRESH_H else ("recent" if age_h <= RECENT_H else "archive")
        n["observed_at_bj"] = bj(n["observed_at"])
        n["first_seen_bj"] = bj(n["first_seen_at"])
        n["last_seen_bj"] = bj(n["last_seen_at"])
        n["first_seen_at"] = bj_iso(n["first_seen_at"])
        n["last_seen_at"] = bj_iso(n["last_seen_at"])
        n["observed_at"] = bj_iso(n["observed_at"])
        n["title"] = n["title_cn"] or n["title_original"]
        n["title_cn_missing"] = not bool(n["title_cn"])
        n["title_lang"] = n["source_language"] or ("zh" if n["title_cn"] else None)
        n["event_type_cn"] = ETYPE_CN.get(n["event_type"] or "", n["event_type"] or "其他")
        n["verification_label_cn"] = VERIF_CN.get(n["verification_level"], "尚未核实")
        n["is_verified_event"] = int(n["independent_source_count"] or 0) >= 2
        n["country_iso3"] = ISO3.get(n["country_iso2"] or "")
        n["lane"] = "news"
        n["disclaimer_cn"] = ("本条为单一来源信号，尚未完成多来源交叉核实，"
                              "不得作为已核实事件引用。")
        # canonical control flag -- untouched production threshold
        n["canonical_eligible"] = bool(
            int(n["independent_source_count"] or 0) >= 2 and n.get("quality_gate_passed") is True)
        n.pop("quarantined", None)

    # ---- counts
    def tally(fn):
        return dict(collections.Counter(fn(n) for n in news if fn(n)).most_common())

    counts = {
        "total": len(news),
        "candidates_seen": total_candidates,
        "admitted": len(news),
        "rejected": sum(gateway.rejects.values()),
        "rejects_by_code": dict(gateway.rejects.most_common()),
        "by_recency": tally(lambda n: n["recency"]),
        "by_origin": tally(lambda n: n["origin"]),
        "by_country": tally(lambda n: n.get("country_cn")),
        "by_country_iso2": tally(lambda n: n.get("country_iso2")),
        "by_event_type_cn": tally(lambda n: n.get("event_type_cn")),
        "by_verification": tally(lambda n: n.get("verification_level")),
        "by_news_status": tally(lambda n: n.get("news_status")),
        "by_source": tally(lambda n: n.get("source_name")),
        "fresh_24h": sum(1 for n in news if n["age_hours"] <= 24),
        "fresh_72h": sum(1 for n in news if n["age_hours"] <= 72),
        "fresh_7d": sum(1 for n in news if n["age_hours"] <= 168),
        "fresh_30d": sum(1 for n in news if n["age_hours"] <= 720),
        "title_cn_missing": sum(1 for n in news if n["title_cn_missing"]),
        "is_verified_event": sum(1 for n in news if n["is_verified_event"]),
        "linked_to_event": sum(1 for n in news if n.get("linked_event_id")),
        "canonical_eligible": sum(1 for n in news if n["canonical_eligible"]),
        "china_related": sum(1 for n in news if n.get("china_related")),
    }

    # ---- source yield report (A-F)
    yield_rows = []
    src_news = collections.Counter(n.get("source_name") for n in news)
    src_fresh = collections.Counter(n.get("source_name") for n in news if n["recency"] == "fresh")
    src_miss = collections.Counter(n.get("source_name") for n in news if n["title_cn_missing"])
    for s in srcs:
        nm = s.get("source_name")
        rows = src_news.get(nm, 0)
        fresh = src_fresh.get(nm, 0)
        if rows >= 30 or (rows >= 20 and fresh >= 5):
            grade = "A"
        elif rows >= 15:
            grade = "B"
        elif rows >= 5:
            grade = "C"
        elif rows >= 1:
            grade = "D"
        elif s.get("tested") and s.get("enabled"):
            grade = "E"
        else:
            grade = "F"
        yield_rows.append({
            "source_id": s.get("source_id"), "source_name": nm,
            "source_type": s.get("source_type"),
            "reliability_tier": s.get("source_reliability_tier"),
            "country_scope": s.get("country_scope"),
            "enabled": s.get("enabled"), "tested": s.get("tested"),
            "news_items": rows, "fresh_items": fresh,
            "title_cn_missing": src_miss.get(nm, 0),
            "grade": grade,
        })
    yield_rows.sort(key=lambda r: (-r["news_items"], str(r["source_name"])))
    yield_counts = dict(collections.Counter(r["grade"] for r in yield_rows).most_common())

    news_stream = {
        "schema": SCHEMA, "schema_version": SCHEMA_VERSION,
        "builder_version": BUILDER_VERSION,
        "generated_at": now.astimezone(UTC).isoformat(),
        "generated_at_bj": bj(now),
        "generated_at_bj_iso": bj_iso(now),
        "source_run_id": icm.get("run_id"),
        "source_data_updated_at": icm.get("updated_at"),
        "policy": {
            "news_eligible": [
                "has_url", "has_time", "has_title_any_language",
                "country_in_scope", "not_quarantined", "not_duplicate",
            ],
            "canonical_eligible": [
                "independent_source_count>=2", "quality_gate_passed==true",
            ],
            "news_may_be_single_source": True,
            "canonical_requires_multi_source": True,
            "canonical_thresholds_modified": False,
            "translation_auto_generated": False,
        },
        "recency_bands_hours": {"fresh": FRESH_H, "recent": RECENT_H, "archive": None},
        "counts": counts,
        "gate": {
            "candidates_seen": total_candidates,
            "admitted": len(news),
            "rejected": sum(gateway.rejects.values()),
            "by_code": dict(gateway.rejects.most_common()),
            "examples": {k: v for k, v in gateway.reject_examples.items()},
        },
        "items": news,
    }

    source_yield = {
        "schema": "source-yield-report-v1",
        "generated_at_bj": bj(now),
        "grading_rule": {
            "A": "news_items>=30 or (news_items>=20 and fresh_items>=5)",
            "B": "news_items>=15", "C": "news_items>=5", "D": "news_items>=1",
            "E": "enabled and tested but zero yield",
            "F": "disabled / untested / blocked",
        },
        "totals": {"sources": len(yield_rows), "grades": yield_counts},
        "sources": yield_rows,
    }

    os.makedirs(os.path.join(out_root, "data", "views"), exist_ok=True)
    for name, obj in (("news_stream.json", news_stream),
                      ("source_yield_report.json", source_yield),
                      ("c1a_gate_audit.json", {
                          "schema": "c1a-gate-audit-v1", "generated_at_bj": bj(now),
                          "counts": counts, "gate": news_stream["gate"],
                          "control": {
                              "canonical_eligible": counts["canonical_eligible"],
                              "note": "computed with untouched production threshold (independent_source_count>=2)",
                          }})):
        p = os.path.join(out_root, "data", "views", name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)

    return news_stream, source_yield


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", required=True)
    ap.add_argument("--internal", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--now", default=None, help="ISO8601 override for reproducibility")
    a = ap.parse_args()
    now = ts(a.now) if a.now else None
    ns, sy = build(a.live, a.internal, a.out, now=now)
    c = ns["counts"]
    print("news-stream-v1 written -> %s/data/views/news_stream.json" % a.out)
    print("  candidates_seen     : %d" % c["candidates_seen"])
    print("  admitted (news)     : %d" % c["admitted"])
    print("  rejected            : %d  %s" % (c["rejected"], c["rejects_by_code"]))
    print("  by_recency          : %s" % c["by_recency"])
    print("  fresh 24h/72h/7d/30d: %d / %d / %d / %d"
          % (c["fresh_24h"], c["fresh_72h"], c["fresh_7d"], c["fresh_30d"]))
    print("  by_country          : %s" % c["by_country"])
    print("  title_cn_missing    : %d" % c["title_cn_missing"])
    print("  is_verified_event   : %d" % c["is_verified_event"])
    print("  canonical_eligible  : %d   (control: must stay 0 unless multi-source exists)"
          % c["canonical_eligible"])
    print("  linked_to_event     : %d" % c["linked_to_event"])
    print("  sources graded      : %s" % sy["totals"]["grades"])


if __name__ == "__main__":
    main()
