#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c1b_source_yield_recovery.py — C1B §二十二 正式测试。

分组：
  A. Article Persistence（§五/§六）        4 项
  B. Source Identity / Corroboration（§十三–§十七）  4 项
  C. GDELT 共享限流（§八/§九）             3 项
  D. RSS / 来源失败原因（§七/§十）          3 项
  E. 阈值与 AI 成本不变量（§十五/§二十一）   2 项
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "data"))
sys.path.insert(0, str(ROOT / "scripts" / "collectors"))

from data.article_persistence import (  # noqa: E402
    persist_collected_articles, AUTHORITATIVE_ARTICLE_STORE,
    EX_DUPLICATE_URL, EX_OUT_OF_SCOPE, EX_SAFETY_HOLD, EX_MALFORMED_TITLE)
from data.repository import Repository  # noqa: E402


def make_root(tmp, sources=None):
    d = os.path.join(tmp, "data", "canonical")
    os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.join(tmp, "data", "public"), exist_ok=True)
    src = {"schema_version": "2.0", "pipeline_version": 2, "run_id": "t",
           "sources": sources or []}
    with open(os.path.join(tmp, "data", "sources.json"), "w", encoding="utf-8") as f:
        json.dump(src, f, ensure_ascii=False, indent=1)
    return tmp


def art(url, title="Titre securitaire au Tchad", summary="Resume", body="Corps " * 40,
        decision="chad", source_id="chad_tchadinfos", source_name="Tchadinfos",
        published="2026-09-18T10:00:00+08:00", quarantine_reason=None):
    a = {
        "source_id": source_id, "source_name": source_name, "source_country": "乍得",
        "source_type": "local_media", "language": "fr",
        "discovery_method": "rss", "feed_url": "https://tchadinfos.com/feed",
        "listing_url": "", "article_url": url, "canonical_url": url,
        "original_title": title, "original_body": body, "original_summary": summary,
        "author": "", "published_at_original": published,
        "published_at_beijing": published, "collected_at_beijing": "2026-09-18T20:00:00+08:00",
        "article_word_count": len(body.split()), "extraction_quality": "full_body",
        "extraction_method": "generic_density", "fetch_status": "ok",
        "body_status": "full_body", "fetch_http_status": 200,
        "_country": {"decision": decision}, "_relevant": True, "_rel_score": 0.9,
    }
    if quarantine_reason:
        a["_quarantine_reason"] = quarantine_reason
    return a


class ArticlePersistenceTest(unittest.TestCase):
    """A. Article Persistence（§五/§六）"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="c1b_ap_")
        make_root(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _store(self):
        p = os.path.join(self.tmp, "data", "canonical", "articles.json")
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as f:
            return json.load(f).get("items", [])

    def test_01_new_unique_article_persists(self):
        """新 unique article 必须进入授权 Article Store（§五）"""
        st = persist_collected_articles(self.tmp, [art("https://tchadinfos.com/a/1")],
                                        "20260918T200000+0800_c1btst", verbose=False)
        self.assertEqual(st["new_articles_persisted"], 1)
        self.assertEqual(len(self._store()), 1)
        self.assertEqual(st["authoritative_store"], AUTHORITATIVE_ARTICLE_STORE)
        # 文章入库不得等于事实已核实
        rec = self._store()[0]
        self.assertIn(rec["processing_status"], ("normalized", "raw"))
        self.assertNotEqual(rec["processing_status"], "linked_to_event")

    def test_02_article_store_survives_next_run(self):
        """Article Store 必须跨 cycle 累积，不得 advance→revert（§二十三）"""
        persist_collected_articles(self.tmp, [art("https://tchadinfos.com/a/1")],
                                    "20260918T200001+0800_c1brun", verbose=False)
        persist_collected_articles(self.tmp, [art("https://tchadinfos.com/a/2")],
                                    "20260918T200002+0800_c1brun", verbose=False)
        # Cycle B：无采集（空输入）——store 不得回退
        st3 = persist_collected_articles(self.tmp, [], "20260918T200003+0800_c1brun", verbose=False)
        self.assertEqual(st3["store_after"], 2)
        self.assertEqual(len(self._store()), 2)

    def test_03_duplicate_article_not_reinserted(self):
        """重复 URL 不得重复入库（§九 去重）"""
        a = art("https://tchadinfos.com/a/1")
        persist_collected_articles(self.tmp, [a], "20260918T200001+0800_c1brun", verbose=False)
        st2 = persist_collected_articles(self.tmp, [dict(a)], "20260918T200002+0800_c1brun", verbose=False)
        self.assertEqual(len(self._store()), 1)
        self.assertEqual(st2["excludes"].get(EX_DUPLICATE_URL, 0), 1)

    def test_03b_collector_local_time_is_normalized_to_rfc3339(self):
        """采集器的 "%Y-%m-%d %H:%M:%S"（无时区）必须归一为 RFC3339 后入库"""
        from data.article_persistence import _rfc3339
        self.assertEqual(_rfc3339("2026-09-11 16:11:47"), "2026-09-11T16:11:47+08:00")
        self.assertEqual(_rfc3339("2026-09-18T20:07:05+08:00"), "2026-09-18T20:07:05+08:00")
        self.assertEqual(_rfc3339("Wed, 18 Sep 2026 09:00:00 EST"),
                         "2026-09-18T14:00:00+00:00")
        self.assertIsNone(_rfc3339("garbage"))
        # 真实采集形状（空格分隔、无时区）必须能成功入库
        st = persist_collected_articles(
            self.tmp,
            [art("https://tchadinfos.com/a/ts", published="2026-09-11 16:11:47")],
            "20260918T200009+0800_c1btst", verbose=False)
        self.assertEqual(st["new_articles_persisted"], 1)
        self.assertEqual(st["excludes"], {})

    def test_04_exclusions_are_explicit_not_silent(self):
        """out-of-scope / safety hold / malformed 必须显式计数，不得静默丢弃"""
        arts = [
            # C1C 起尼日利亚已成为在范围内国家，故用「非任何已配置国别」作 out-of-scope 样例
            art("https://x.com/out", decision="not_a_configured_country"),  # out of scope
            art("https://x.com/hold", quarantine_reason="extraction_failed"),
            art("https://x.com/nodetitle", title=""),
            art("https://x.com/ok"),
        ]
        st = persist_collected_articles(self.tmp, arts, "20260918T200001+0800_c1brun", verbose=False)
        self.assertEqual(st["excludes"].get(EX_OUT_OF_SCOPE, 0), 1)
        self.assertEqual(st["excludes"].get(EX_SAFETY_HOLD, 0), 1)
        self.assertEqual(st["excludes"].get(EX_MALFORMED_TITLE, 0), 1)
        self.assertEqual(st["excluded_total"], 3)
        self.assertEqual(len(self._store()), 1)


class GdeltSharedRateLimiterTest(unittest.TestCase):
    """C. GDELT 共享限流（§八/§九）"""

    def setUp(self):
        import urllib.request as _ur
        from gdelt_rate_limiter import GdeltSharedRateLimiter
        self._ur = _ur
        self._orig = _ur.urlopen
        self.calls = []
        self.sleeps = []

    def tearDown(self):
        self._ur.urlopen = self._orig

    def _limiter(self, **kw):
        from gdelt_rate_limiter import GdeltSharedRateLimiter
        ticks = [1000.0]

        def clock():
            return ticks[0]

        def sleeper(s):
            self.sleeps.append(s)
            ticks[0] += s

        return GdeltSharedRateLimiter(min_interval=20.0, max_interval=80.0,
                                      max_attempts=3, budget=50,
                                      clock=clock, sleeper=sleeper, **kw)

    def test_05_gdelt_shared_rate_limiter_single_flight_and_pacing(self):
        """68 个源查同一服务：同签名只请求一次；不同签名按全局节流铺开"""
        from gdelt_rate_limiter import build_gdelt_url
        lim = self._limiter()

        class R:
            status = 200

            class h:
                @staticmethod
                def get_content_charset():
                    return "utf-8"

            headers = h()

            def read(self):
                return b'{"articles":[{"url":"https://x/a","title":"t"}]}'

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_open(req, timeout=None):
            self.calls.append(req.full_url)
            return R()

        self._ur.urlopen = fake_open
        u1 = build_gdelt_url("domain:reuters.com Chad", timespan="72h", maxrecords=250)
        # 同一签名（仅参数顺序/等价）→ 命中共享缓存，不再发起 HTTP
        t1, e1, m1 = lim.fetch(u1, label="chad|k1")
        t2, e2, m2 = lim.fetch(u1, label="chad|k2")
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(m1["cache"])
        self.assertTrue(m2["cache"])
        # 跨标签共享：第二个源零额外请求（这正是 68 源共用一个闸门的含义）
        self.assertEqual(lim.stats()["cache_hits"], 1)

        # 不同签名 → 必须经过全局节流（至少睡满一个 min_interval）
        u2 = build_gdelt_url("domain:reuters.com Niger", timespan="72h", maxrecords=250)
        lim.fetch(u2, label="niger|k2")
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(any(s >= 19.9 for s in self.sleeps),
                        "global pacing not enforced: sleeps=%s" % self.sleeps)

        # 请求预算：不得无限放大
        st = lim.stats()
        self.assertEqual(st["requests"], 2)
        self.assertEqual(st["success_rate"], 1.0)

    def test_06_gdelt_retry_after_respected(self):
        """429 + Retry-After 必须被遵循，且间隔指数退避、有上限"""
        import urllib.error
        import email.message
        from gdelt_rate_limiter import GdeltSharedRateLimiter, build_gdelt_url
        lim = self._limiter()
        state = {"n": 0}

        def fake_open(req, timeout=None):
            state["n"] += 1
            if state["n"] == 1:
                h = email.message.Message()
                h["Retry-After"] = "45"
                raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", h, None)
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", None, None)

        self._ur.urlopen = fake_open
        u = build_gdelt_url("domain:x.com Chad")
        text, err, meta = lim.fetch(u, label="chad|rl")
        self.assertIsNone(text)
        self.assertTrue(meta["rate_limited"])
        self.assertEqual(meta["retry_after"], 45)
        st = lim.stats()
        self.assertGreaterEqual(st["retry_after_honored"], 1)
        self.assertGreaterEqual(st["backoff_events"], 1)
        # 间隔必须从 min 翻倍，且不超过 max
        self.assertEqual(st["current_interval_s"], 80.0)
        self.assertTrue(any(s >= 45.0 for s in self.sleeps),
                        "Retry-After not honored: sleeps=%s" % self.sleeps)
        # 重试次数受 max_attempts 限制（不得暴力重试）
        self.assertEqual(state["n"], 3)


class FailureReasonTest(unittest.TestCase):
    """D. 逐源失败原因必须具体（§七）"""

    def test_07_source_failure_reason_specific(self):
        from failure_reasons import (classify_source_failure, HTTP_429, HTTP_403,
                                     TIMEOUT, DNS, RSS_EMPTY, QUERY_NO_RESULT,
                                     SOURCE_MAPPING_ERROR, DUPLICATE_ONLY, UNKNOWN,
                                     OK_PRODUCTIVE)
        cases = [
            ({"discovered": 0, "fetched": 0, "method": "rss"},
             ["fetch https://x 429"], HTTP_429),
            ({"discovered": 0, "fetched": 0, "method": "rss"},
             ["fetch https://x 403 Forbidden"], HTTP_403),
            ({"discovered": 0, "fetched": 0, "method": "rss"},
             ["ReadTimeout: timed out"], TIMEOUT),
            ({"discovered": 0, "fetched": 0, "method": "rss"},
             ["gaierror: Name or service not known"], DNS),
            ({"discovered": 0, "fetched": 0, "method": "rss"}, [], RSS_EMPTY),
            ({"discovered": 0, "fetched": 0, "method": "gdelt_search"}, [], QUERY_NO_RESULT),
            ({"discovered": 0, "fetched": 0, "method": "rss"},
             ["source: no feed_url configured"], SOURCE_MAPPING_ERROR),
            ({"discovered": 5, "fetched": 0, "duplicates": 5, "method": "rss"}, [], DUPLICATE_ONLY),
            ({"discovered": 3, "fetched": 3, "method": "rss"}, [], OK_PRODUCTIVE),
            ({"discovered": 0, "fetched": 0, "method": "unknown_method", "status": "x"}, [], UNKNOWN),
        ]
        for stat, errs, want in cases:
            got, _ = classify_source_failure(stat, errs)
            self.assertEqual(got, want, "stat=%s errs=%s got=%s want=%s"
                             % (stat, errs, got, want))
        # BLOCKED 不得作为兜底词
        self.assertNotIn("BLOCKED", [c[2] for c in cases])



class SourceIdentityTest(unittest.TestCase):
    """B. Source Identity / Corroboration（§十三–§十七）"""

    def test_08_same_publisher_country_variants_are_one_identity(self):
        """同一媒体按国家重复登记必须收敛为 1 个独立来源"""
        from data.source_identity import source_identity, independent_source_count
        recs = [
            {"source_id": "intl_reuters_chad", "source_name": "Reuters (Chad)",
             "url": "https://www.reuters.com/"},
            {"source_id": "intl_reuters_niger", "source_name": "Reuters (Niger)",
             "url": "https://www.reuters.com/"},
            {"source_id": "intl_rfi_chad", "source_name": "RFI (Chad)",
             "url": "https://www.rfi.fr/"},
            {"source_id": "intl_rfi_niger", "source_name": "RFI (Niger)",
             "url": "https://www.rfi.fr/"},
        ]
        ids = [source_identity(r)["source_identity_id"] for r in recs]
        self.assertEqual(len(set(ids)), 2)              # Reuters=1, RFI=1
        self.assertEqual(independent_source_count(recs)["independent_source_count"], 2)

    def test_09_two_real_publishers_count_as_two_sources(self):
        """两家真正独立的媒体必须算 2 个来源"""
        from data.source_identity import independent_source_count
        recs = [
            {"source_id": "chad_tchadinfos", "source_name": "Tchadinfos",
             "article_url": "https://tchadinfos.com/a"},
            {"source_id": "chad_alwihda", "source_name": "Alwihda Info",
             "article_url": "https://www.alwihdainfo.com/a"},
        ]
        self.assertEqual(independent_source_count(recs)["independent_source_count"], 2)

    def test_10_same_syndicated_story_is_one_independent_source(self):
        """同一篇通讯社稿被多站转载：不得算成多个独立来源"""
        from data.source_identity import independent_source_count, source_identity
        recs = [
            {"source_id": "intl_allafrica_chad", "source_name": "AllAfrica",
             "article_url": "https://allafrica.com/stories/202609180001.html",
             "origin_publisher": "Reuters"},
            {"source_id": "chad_journaldutchad", "source_name": "Journal du Tchad",
             "article_url": "https://journaldutchad.com/reuters-story"},
            {"source_id": "un_reliefweb_chad", "source_name": "ReliefWeb",
             "article_url": "https://reliefweb.int/report/chad/x",
             "origin_publisher": "Reuters"},
        ]
        ic = independent_source_count(recs)
        # syndicated_copy 归并到 origin:reuters；聚合器单独归类；独立发布方 1 家
        self.assertEqual(ic["independent_source_count"], 1)
        self.assertIn("origin:reuters", ic["syndicated_identities"])
        self.assertEqual(source_identity(recs[0])["independence_class"], "syndicated_copy")

    def test_11_multisource_cluster_can_be_canonical_eligible(self):
        """同一事件由两家独立媒体分别报道 → 可产生 isc>=2 的 cluster"""
        from clustering.event_clusterer import cluster_events
        def ev(uid, title, src, url, tt):
            return {"event_id": uid, "title_original": title, "country_code": "TD",
                    "event_type": "public_health", "event_time": tt,
                    "canonical_url": url, "source_id": src, "source_name": src,
                    "article_id": "ART_" + uid, "quality_gate_passed": True}
        e1 = ev("E1", "Tchad : Point sur la riposte contre le cholera dans quatre provinces",
                "chad_journaldutchad", "https://journaldutchad.com/x", "2026-09-18 18:57:39")
        e2 = ev("E2", "Point sur la riposte contre le cholera dans quatre provinces au Tchad",
                "chad_tchadinfos", "https://tchadinfos.com/y", "2026-09-18 19:10:00")
        e3 = ev("E3", "Greve seche des greffiers au Tchad",
                "chad_alwihda", "https://alwihdainfo.com/z", "2026-09-18 10:00:00")
        clusters, st = cluster_events([e1, e2, e3])
        self.assertEqual(st["multi_source_clusters"], 1)
        multi = [c for c in clusters if (c.get("independent_source_count") or 0) >= 2]
        self.assertEqual(len(multi), 1)
        self.assertEqual(len(multi[0]["article_ids"]), 2)
        self.assertTrue(multi[0]["source_groups"])

    def test_12_event_clusterer_does_not_overmerge(self):
        """不同事件不得被过度合并（§十七 明令）"""
        from clustering.event_clusterer import cluster_events
        def ev(uid, title, src, url, tt):
            return {"event_id": uid, "title_original": title, "country_code": "TD",
                    "event_type": "armed_conflict", "event_time": tt,
                    "canonical_url": url, "source_id": src, "article_url": url}
        a = ev("E1", "Attaque armee a Doba : trois morts", "s1", "https://a/1", "2026-09-18 08:00:00")
        b = ev("E2", "Greve des enseignants a N'Djamena", "s2", "https://a/2", "2026-09-18 09:00:00")
        c = ev("E3", "Riposte contre le cholera au Lac", "s3", "https://a/3", "2026-09-18 10:00:00")
        clusters, st = cluster_events([a, b, c])
        self.assertEqual(st["output_clusters"], 3)
        self.assertEqual(st["merged_pairs"], 0)


class FeedParserTest(unittest.TestCase):
    """D2. RSS/Atom 兼容性（§十）"""

    def test_13_rss_atom_namespace_supported(self):
        """Atom 0.3 / 带前缀命名空间 / RSS 1.0 RDF / BOM / HTML 实体 必须可解析"""
        from feed_parser import parse_feed_robust
        atom03 = ('<?xml version="1.0"?><feed xmlns="http://purl.org/atom/ns#" version="0.3">'
                  '<entry><title>Atom 0.3 title</title>'
                  '<link rel="alternate" href="https://y.com/1"/>'
                  '<issued>2026-09-18T07:30:00Z</issued><id>tag:y,1</id></entry></feed>')
        rdf = ('<?xml version="1.0"?><rdf:RDF '
               'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
               'xmlns="http://purl.org/rss/1.0/"><item rdf:about="https://z.com/1">'
               '<title>RDF item</title><link>https://z.com/1</link></item></rdf:RDF>')
        rss = ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
               '<item><title>Attaque &agrave; N&#8217;Djamena &nbsp; &mdash; 3 morts</title>'
               '<link>https://x.com/a</link>'
               '<pubDate>Wed, 18 Sep 2026 10:00:00 EST</pubDate></item>'
               '</channel></rss>')
        self.assertEqual(len(parse_feed_robust(atom03, "https://y.com")), 1)
        self.assertEqual(len(parse_feed_robust(rdf, "https://z.com")), 1)
        items = parse_feed_robust("\ufeff\n  " + rss, "https://x.com")
        self.assertEqual(len(items), 1)
        self.assertIn("N\u2019Djamena", items[0]["title"])
        self.assertEqual(items[0]["published"], "2026-09-18T15:00:00Z")  # EST = UTC-5

    def test_14_named_timezone_dates_parsed(self):
        from feed_parser import parse_feed_date
        for raw, want_h in (("Wed, 18 Sep 2026 09:00:00 GMT", 9),
                            ("Wed, 18 Sep 2026 09:00:00 EST", 14),
                            ("Wed, 18 Sep 2026 09:00:00 +0800", 1),
                            ("Wed, 18 Sep 2026 09:00:00 WAT", 8)):
            dt, tz = parse_feed_date(raw)
            self.assertIsNotNone(dt, raw)
            self.assertEqual(dt.hour, want_h, raw)


class InvariantTest(unittest.TestCase):
    """E. 阈值与 AI 成本不变量（§十五/§二十一）"""

    def test_15_canonical_threshold_unchanged(self):
        """canonical 阈值必须仍为 independent_source_count>=2 + quality_gate_passed"""
        from data.normalizers import derive_verification_level
        one = derive_verification_level({}, source_type="local_media",
                                         independent_source_count=1)
        two = derive_verification_level({}, source_type="local_media",
                                         independent_source_count=2)
        self.assertNotEqual(one, "cross_verified")
        self.assertEqual(two, "cross_verified")
        # 单一高可靠媒体（Reuters）仍不得升级
        r = derive_verification_level({}, source_type="international_media",
                                      source_group="reuters", independent_source_count=1)
        self.assertNotEqual(r, "cross_verified")

    def test_16_news_volume_does_not_trigger_ai_per_article(self):
        """news 数量增长不得导致 AI 调用按文章线性增长"""
        import io as _io
        import os as _os
        # 1) 新闻流构建本身不调用 AI（源码中不得出现 AI provider 调用）
        p = _os.path.join(str(ROOT), "tools", "c1a", "build_news_stream.py")
        src = _io.open(p, encoding="utf-8").read().lower()
        for banned in ("deepseek", "openai", "requests.post", "api_key", "llm"):
            self.assertNotIn(banned, src, "news stream builder must stay AI-free")
        # 2) 采集器同样不得调用 AI
        p2 = _os.path.join(str(ROOT), "scripts", "stage3_collect_v2.py")
        src2 = _io.open(p2, encoding="utf-8").read().lower()
        for banned in ("deepseek", "openai", "api_key"):
            self.assertNotIn(banned, src2, "collector must stay AI-free")
        # 3) 入库的 article 不得携带 AI 结果字段（enrichment 是独立选择性步骤）
        from data.article_persistence import article_to_candidate
        cand = article_to_candidate({"canonical_url": "https://x/y", "original_title": "t",
                                     "original_summary": "s", "_country": {"decision": "chad"}})
        for k in ("ai_result", "enrichment", "summary_cn"):
            if k in cand:
                self.assertEqual(cand[k], "", "AI fields must not be produced at ingest")


if __name__ == "__main__":
    unittest.main(verbosity=2)
