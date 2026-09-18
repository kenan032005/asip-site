#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C1A S26 — news-stream-v1 contract, gate, dedup and separation tests.

Runs offline against the generated views.  Exit code 0 = all pass.
"""
import os
import sys
import json
import collections

VIEWS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "views")
VIEWS = os.path.abspath(VIEWS)

REQUIRED = [
    "news_id", "dedup_key", "lane", "recency", "title", "title_cn", "title_original",
    "title_cn_missing", "country_cn", "country_iso2", "event_type_cn",
    "source_name", "source_url", "observed_at_bj", "first_seen_bj", "last_seen_bj",
    "seen_count", "is_update", "verification_level", "verification_label_cn",
    "independent_source_count", "is_verified_event", "news_status",
    "has_body", "fetch_http_status", "china_related", "origin", "disclaimer_cn",
    "age_hours", "canonical_eligible",
]

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("  [%s] %-52s %s" % ("PASS" if ok else "FAIL", name, detail))
    return bool(ok)


def main():
    ns = json.load(open(os.path.join(VIEWS, "news_stream.json"), encoding="utf-8"))
    sy = json.load(open(os.path.join(VIEWS, "source_yield_report.json"), encoding="utf-8"))
    ga = json.load(open(os.path.join(VIEWS, "c1a_gate_audit.json"), encoding="utf-8"))
    items = ns["items"]
    counts = ns["counts"]

    print("=" * 78)
    print("C1A S26 TESTS   items=%d  sources=%d" % (len(items), len(sy["sources"])))
    print("=" * 78)

    print("\n-- schema contract --")
    check("schema id is news-stream-v1", ns.get("schema") == "news-stream-v1", ns.get("schema"))
    missing = [n["news_id"] for n in items if any(k not in n for k in REQUIRED)]
    check("every item has all required keys", not missing, "%d offenders" % len(missing))
    check("news_id unique", len({n["news_id"] for n in items}) == len(items))
    check("news_id well-formed", all(str(n["news_id"]).startswith("NEWS-") for n in items))
    check("lane is always 'news'", {n["lane"] for n in items} == {"news"})

    print("\n-- News Admission Gate (S13) --")
    check("no item without source_url", all(n["source_url"] for n in items))
    check("no item without observed_at", all(n["observed_at"] for n in items))
    check("no item without a title",
          all(n["title_cn"] or n["title_original"] for n in items))
    check("no item without country_iso2", all(n["country_iso2"] for n in items))
    qids = set()
    ip = os.path.join(os.path.dirname(VIEWS), "canonical", "quarantine.json")
    if os.path.exists(ip):
        qids = {q.get("original_id") for q in
                json.load(open(ip, encoding="utf-8"))["items"] if q.get("original_id")}
    check("no quarantined id admitted",
          not ({n["news_id"].replace("NEWS-", "") for n in items} & qids),
          "checked against %d quarantined ids" % len(qids))
    check("gate rejects are all accounted for",
          ns["gate"]["rejected"] == counts["rejected"])
    check("admitted == len(items)", ns["gate"]["admitted"] == len(items))
    check("candidates == admitted + rejected",
          ns["gate"]["candidates_seen"] == ns["gate"]["admitted"] + ns["gate"]["rejected"])

    print("\n-- dedup (S9) + update semantics (S10) --")
    dks = [n["dedup_key"] for n in items]
    check("dedup_key unique across items", len(set(dks)) == len(dks))
    check("seen_count >= 1", all(n["seen_count"] >= 1 for n in items))
    check("is_update consistent with seen_count",
          all(n["is_update"] == (n["seen_count"] > 1) for n in items))
    check("first_seen <= last_seen",
          all(str(n["first_seen_bj"]) <= str(n["last_seen_bj"]) for n in items))
    allurls = [n["source_url"] for n in items]
    check("no duplicate source_url", len(set(allurls)) == len(allurls))

    print("\n-- NEWS / VERIFIED EVENT separation (S2) --")
    bad = [n["news_id"] for n in items
           if n["is_verified_event"] and int(n["independent_source_count"] or 0) < 2]
    check("no item claims verified without >=2 independent sources", not bad, "%d offenders" % len(bad))
    check("is_verified_event matches independent_source_count",
          all(n["is_verified_event"] == (int(n["independent_source_count"] or 0) >= 2)
              for n in items))
    check("every item carries a provenance label",
          all(n["verification_label_cn"] for n in items))

    print("\n-- canonical thresholds NOT lowered (S2 control) --")
    pol = ns["policy"]
    check("policy flag canonical_thresholds_modified == False",
          pol["canonical_thresholds_modified"] is False)
    check("policy requires multi-source for canonical",
          pol["canonical_requires_multi_source"] is True)
    check("policy allows single-source news", pol["news_may_be_single_source"] is True)
    check("no auto-generated translation claimed",
          pol["translation_auto_generated"] is False)
    check("canonical_eligible control == count in items",
          counts["canonical_eligible"] == sum(1 for n in items if n["canonical_eligible"]))
    check("canonical_eligible == 0 while corpus is single-source",
          counts["canonical_eligible"] == 0,
          "control=%d" % counts["canonical_eligible"])
    check("control agrees with live metrics level",
          ga["control"]["canonical_eligible"] == counts["canonical_eligible"])

    print("\n-- no fabricated translation --")
    check("title_cn_missing is true exactly when title_cn is empty",
          all(n["title_cn_missing"] == (not n["title_cn"]) for n in items))
    check("display title falls back to original when cn missing",
          all(n["title"] == (n["title_cn"] or n["title_original"]) for n in items))
    check("title_cn_missing count matches",
          counts["title_cn_missing"] == sum(1 for n in items if n["title_cn_missing"]))

    print("\n-- count consistency --")
    check("counts.total == len(items)", counts["total"] == len(items))
    check("by_recency sums to total", sum(counts["by_recency"].values()) == counts["total"])
    check("by_origin sums to total", sum(counts["by_origin"].values()) == counts["total"])
    check("by_country sums to total", sum(counts["by_country"].values()) == counts["total"])
    check("fresh_24h == items with age_hours<=24",
          counts["fresh_24h"] == sum(1 for n in items if n["age_hours"] <= 24))
    check("fresh_7d == items with age_hours<=168",
          counts["fresh_7d"] == sum(1 for n in items if n["age_hours"] <= 168))
    check("fresh_24h <= fresh_72h <= fresh_7d <= fresh_30d",
          counts["fresh_24h"] <= counts["fresh_72h"] <= counts["fresh_7d"] <= counts["fresh_30d"])
    check("archive count == items older than 30d",
          counts["by_recency"].get("archive", 0) == sum(1 for n in items if n["age_hours"] > 720))

    print("\n-- source yield report (S22) --")
    grades = collections.Counter(r["grade"] for r in sy["sources"])
    check("grades only A-F", set(grades) <= set("ABCDEF"), str(dict(grades)))
    check("grade counts match totals", dict(grades) == sy["totals"]["grades"])
    check("source count matches", len(sy["sources"]) == sy["totals"]["sources"])
    a_names = {r["source_name"] for r in sy["sources"] if r["grade"] == "A"}
    top_names = {n for n, _ in sorted(counts["by_source"].items(),
                                       key=lambda kv: -kv[1])[:3]}
    check("grade A contains the top-yield sources", a_names >= top_names,
          "A=%s top3=%s" % (sorted(a_names), sorted(top_names)))

    print("\n-- recency honesty --")
    check("recency bands are monotonic with age",
          all((n["recency"] == "fresh") == (n["age_hours"] <= 168) for n in items))

    failed = [r for r in RESULTS if not r[1]]
    print("\n" + "=" * 78)
    print("RESULT: %d passed, %d failed, %d total"
          % (len(RESULTS) - len(failed), len(failed), len(RESULTS)))
    for r in failed:
        print("  FAILED:", r[0], r[2])
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
