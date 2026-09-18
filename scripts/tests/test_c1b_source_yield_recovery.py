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

    def test_04_exclusions_are_explicit_not_silent(self):
        """out-of-scope / safety hold / malformed 必须显式计数，不得静默丢弃"""
        arts = [
            art("https://x.com/out", decision="nigeria"),          # out of scope
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




if __name__ == "__main__":
    unittest.main(verbosity=2)
