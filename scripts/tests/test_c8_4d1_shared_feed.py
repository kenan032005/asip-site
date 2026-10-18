#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C8-4D1 — Shared-feed 复用与采集指标测试（Gate A/B 确定性验证）。

覆盖：
  §A4  指标命名拆分（execution_rows_* / physical_network_requests / aliases）
  §B1  有效请求身份等价性判定（同 URL/同方法/相关头/鉴权上下文才算同一请求）
  §B3  run-local 有界缓存：命中复用原始响应、失败不缓存、跨轮清空、越界淘汰
  §B4  国家语义保持：OLD vs NEW 在固定 fixture 上 URL 集合/国家归属/计数完全一致
  §B7  特性开关：默认关闭；allowlist 仅白名单源生效
"""
import io
import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "scripts" / "collectors")):
    if p not in sys.path:
        sys.path.insert(0, p)

import framework  # noqa: E402
from registry import ArticleDiscoverer  # noqa: E402

FIXTURE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Fixture Africa</title><link>https://fixture.example/</link>
<item><title>Niger : attaque pres de la frontiere</title>
<link>https://fixture.example/a1</link>
<description>Attaque armee dans la region de Tillaberi au Niger.</description>
<pubDate>Sat, 18 Oct 2026 10:00:00 +0000</pubDate></item>
<item><title>Tchad : incident a N'Djamena</title>
<link>https://fixture.example/a2</link>
<description>Incident securitaire a N'Djamena, Tchad.</description>
<pubDate>Sat, 18 Oct 2026 09:00:00 +0000</pubDate></item>
<item><title>Nigeria : pipeline explosion in Lagos</title>
<link>https://fixture.example/a3</link>
<description>Pipeline explosion reported in Lagos, Nigeria.</description>
<pubDate>Sat, 18 Oct 2026 08:00:00 +0000</pubDate></item>
</channel></rss>
"""


class _FakeHeaders:
    def __init__(self, charset="utf-8", encoding=""):
        self._charset = charset
        self._encoding = encoding

    def get_content_charset(self):
        return self._charset

    def get(self, key, default=None):
        if str(key).lower() == "content-encoding":
            return self._encoding or default
        return default


class _FakeResponse(io.BytesIO):
    def __init__(self, body: bytes, status=200, headers=None):
        super().__init__(body)
        self.status = status
        self.headers = headers or _FakeHeaders()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class _Transport:
    """可控 HTTP 传输：统计真实请求次数，按 URL 返回固定字节或抛错。"""

    def __init__(self, bodies=None, fail_urls=(), status=200):
        self.calls = []
        self.bodies = bodies or {}
        self.fail_urls = set(fail_urls)
        self.status = status

    def __call__(self, req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        self.calls.append(url)
        if url in self.fail_urls:
            raise urllib.error.HTTPError(url, 500, "boom", {}, None)
        body = self.bodies.get(url, FIXTURE_RSS.encode("utf-8"))
        return _FakeResponse(body, status=self.status)


class _Base(unittest.TestCase):
    def setUp(self):
        self._saved_env = {k: os.environ.get(k) for k in (
            framework.SHARED_REUSE_ENV, framework.SHARED_REUSE_SOURCES_ENV)}
        for k in (framework.SHARED_REUSE_ENV, framework.SHARED_REUSE_SOURCES_ENV):
            os.environ.pop(k, None)
        self._orig_urlopen = framework.urllib.request.urlopen
        self._orig_validate = framework.validate_url
        # 固定 fixture 域名不依赖真实 DNS（确定性测试）
        framework.validate_url = lambda url: (True, "ok")
        framework.reset_run_caches()

    def tearDown(self):
        framework.urllib.request.urlopen = self._orig_urlopen
        framework.validate_url = self._orig_validate
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        framework.reset_run_caches()

    def enable(self, sources=None):
        os.environ[framework.SHARED_REUSE_ENV] = "1"
        if sources is not None:
            os.environ[framework.SHARED_REUSE_SOURCES_ENV] = sources


# ══════════════════════════════════════════════════════════════════
# §B1 有效请求身份
# ══════════════════════════════════════════════════════════════════
class TestRequestIdentity(_Base):
    def test_same_effective_request_same_key(self):
        a = framework.request_identity("https://x.example/feed/", "GET",
                                       {"User-Agent": framework.UA})
        b = framework.request_identity("https://x.example/feed/", "GET",
                                       {"user-agent": framework.UA})
        self.assertEqual(a, b)

    def test_different_url_different_key(self):
        a = framework.request_identity("https://x.example/feed/")
        b = framework.request_identity("https://x.example/feed/?country=ne")
        self.assertNotEqual(a, b)

    def test_different_method_different_key(self):
        self.assertNotEqual(framework.request_identity("https://x.example/", "GET"),
                            framework.request_identity("https://x.example/", "POST"))

    def test_different_auth_context_different_key(self):
        self.assertNotEqual(
            framework.request_identity("https://x.example/", auth_context="token-a"),
            framework.request_identity("https://x.example/", auth_context="token-b"))

    def test_sensitive_header_change_different_key_and_not_leaked(self):
        k1 = framework.request_identity("https://x.example/", headers={"Authorization": "Bearer AAA"})
        k2 = framework.request_identity("https://x.example/", headers={"Authorization": "Bearer BBB"})
        self.assertNotEqual(k1, k2)
        self.assertNotIn("AAA", k1)
        self.assertNotIn("aaaa", k1.lower())


# ══════════════════════════════════════════════════════════════════
# §B7 特性开关
# ══════════════════════════════════════════════════════════════════
class TestFeatureFlag(_Base):
    def test_default_disabled(self):
        self.assertFalse(framework.shared_reuse_enabled("pan_allafrica"))
        t = _Transport()
        framework.urllib.request.urlopen = t
        framework.fetch_page("https://feed.example/a", reuse=True, source_id="s1")
        framework.fetch_page("https://feed.example/a", reuse=True, source_id="s2")
        self.assertEqual(len(t.calls), 2)
        self.assertEqual(framework.get_request_stats()["cache_hits"], 0)
        self.assertEqual(framework.get_request_stats()["bypass_flag_disabled"], 2)

    def test_enabled_no_allowlist_reuses(self):
        self.enable()
        t = _Transport()
        framework.urllib.request.urlopen = t
        a = framework.fetch_page("https://feed.example/a", reuse=True, source_id="s1")
        b = framework.fetch_page("https://feed.example/a", reuse=True, source_id="s2")
        self.assertEqual(len(t.calls), 1)
        self.assertEqual(a[0], b[0])
        st = framework.get_request_stats()
        self.assertEqual(st["cache_hits"], 1)
        self.assertEqual(st["physical_network_requests"], 1)

    def test_allowlist_restricts(self):
        self.enable(sources="s1")
        t = _Transport()
        framework.urllib.request.urlopen = t
        framework.fetch_page("https://feed.example/a", reuse=True, source_id="s1")
        framework.fetch_page("https://feed.example/a", reuse=True, source_id="s2")
        self.assertEqual(len(t.calls), 2)
        self.assertEqual(framework.get_request_stats()["bypass_not_allowlisted"], 1)

    def test_different_url_no_reuse(self):
        self.enable()
        t = _Transport()
        framework.urllib.request.urlopen = t
        framework.fetch_page("https://feed.example/a", reuse=True, source_id="s1")
        framework.fetch_page("https://feed.example/b", reuse=True, source_id="s2")
        self.assertEqual(len(t.calls), 2)
        self.assertEqual(framework.get_request_stats()["cache_hits"], 0)


# ══════════════════════════════════════════════════════════════════
# §B3 缓存行为
# ══════════════════════════════════════════════════════════════════
class TestCacheBehavior(_Base):
    def test_failure_not_cached(self):
        self.enable()
        t = _Transport(fail_urls={"https://feed.example/bad"})
        framework.urllib.request.urlopen = t
        framework.fetch_page("https://feed.example/bad", reuse=True, source_id="s1")
        framework.fetch_page("https://feed.example/bad", reuse=True, source_id="s2")
        # MAX_RETRIES(2)+1 = 3 次物理尝试 × 2 次调用
        self.assertEqual(framework.get_request_stats()["cache_hits"], 0)
        self.assertEqual(framework.get_request_stats()["cache_misses"], 2)

    def test_reset_between_runs(self):
        self.enable()
        t = _Transport()
        framework.urllib.request.urlopen = t
        framework.fetch_page("https://feed.example/a", reuse=True, source_id="s1")
        framework.reset_run_caches()
        self.assertEqual(framework.get_request_stats()["cache_hits"], 0)
        framework.fetch_page("https://feed.example/a", reuse=True, source_id="s2")
        self.assertEqual(len(t.calls), 2)

    def test_bounded_eviction(self):
        self.enable()
        saved = framework.SHARED_REUSE_MAX_ENTRIES
        framework.SHARED_REUSE_MAX_ENTRIES = 2
        try:
            t = _Transport()
            framework.urllib.request.urlopen = t
            for i in range(4):
                framework.fetch_page("https://feed.example/%d" % i, reuse=True, source_id="s")
            st = framework.get_request_stats()
            self.assertLessEqual(st["cache_entries"], 2)
            self.assertGreaterEqual(st["evictions"], 2)
        finally:
            framework.SHARED_REUSE_MAX_ENTRIES = saved


# ══════════════════════════════════════════════════════════════════
# §B4 OLD vs NEW 等价性（固定 fixture）
# ══════════════════════════════════════════════════════════════════
def _src(sid, country, feed="https://shared.example/feed/", max_items=10):
    return {
        "source_id": sid, "source_name": sid, "discovery_type": "rss",
        "feed_url": feed, "base_url": "https://shared.example/",
        "listing_urls": [], "max_items": max_items, "language": "fr",
        "country_scope": [country],
    }


class TestEquivalence(_Base):
    def _run(self, reuse_on):
        if reuse_on:
            self.enable()
        else:
            os.environ.pop(framework.SHARED_REUSE_ENV, None)
        framework.reset_run_caches()
        t = _Transport()
        framework.urllib.request.urlopen = t
        disc = ArticleDiscoverer(registry=None)
        out = {}
        # 同一 feed 被 3 个不同 source_id 执行（模拟 BBC / RFI / AlJazeera 共享 feed）
        for sid, country in (("s_chad", "乍得"), ("s_niger", "尼日尔"), ("s_pan", "非洲")):
            arts, errs = disc.discover(_src(sid, country))
            out[sid] = {
                "urls": sorted(a["url"] for a in arts),
                "count": len(arts),
                "errors": errs,
                "discovered": [dict(a) for a in arts],
            }
        stats = framework.get_request_stats()
        return out, len(t.calls), stats

    def test_url_set_and_counts_identical(self):
        old, old_calls, _ = self._run(reuse_on=False)
        new, new_calls, new_stats = self._run(reuse_on=True)
        self.assertEqual(set(old), set(new))
        for sid in old:
            self.assertEqual(old[sid]["urls"], new[sid]["urls"], f"URL set differs for {sid}")
            self.assertEqual(old[sid]["count"], new[sid]["count"])
            self.assertEqual(old[sid]["errors"], new[sid]["errors"])
        # 物理请求：3 次 → 1 次
        self.assertEqual(old_calls, 3)
        self.assertEqual(new_calls, 1)
        self.assertEqual(new_stats["cache_hits"], 2)

    def test_article_payload_identical(self):
        old, _, _ = self._run(reuse_on=False)
        new, _, _ = self._run(reuse_on=True)
        for sid in old:
            self.assertEqual(old[sid]["discovered"], new[sid]["discovered"],
                             f"discovered payload differs for {sid}")

    def test_country_assignment_identical(self):
        """国家归属由**每个国家管线独立**执行，复用不得改变判定结果。"""
        from country_runner import identify_country
        old, _, _ = self._run(reuse_on=False)
        new, _, _ = self._run(reuse_on=True)
        cfgs = [{"country": "乍得"}, {"country": "尼日尔"}, {"country": "尼日利亚"}]
        for sid in old:
            for cfg in cfgs:
                for o, n in zip(old[sid]["discovered"], new[sid]["discovered"]):
                    text_o = (o["title"] + " " + o.get("summary", ""))
                    text_n = (n["title"] + " " + n.get("summary", ""))
                    self.assertEqual(identify_country(text_o, cfg), identify_country(text_n, cfg))


# ══════════════════════════════════════════════════════════════════
# §A4 指标命名（sources.json 快照 + 别名契约）
# ══════════════════════════════════════════════════════════════════
class TestMetricNamingAndRegistry(_Base):
    def test_registry_counts_unchanged(self):
        doc = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
        srcs = doc["sources"]
        self.assertEqual(len(srcs), 153, "LOGICAL_SOURCES must stay 153")
        enabled = [s for s in srcs if s.get("legacy_payload", {}).get("enabled", s.get("enabled"))]
        self.assertEqual(len(enabled), 151, "ENABLED must stay 151")

    def test_fixed_feeds_are_absolute_https(self):
        doc = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
        by_id = {s["source_id"]: s for s in doc["sources"]}
        for sid in ("ben_webtv", "nga_nrc"):
            fu = by_id[sid]["legacy_payload"]["feed_url"]
            self.assertTrue(fu.startswith("https://"), f"{sid} feed_url must be absolute https: {fu}")
            self.assertTrue(fu.endswith("/"), f"{sid} feed_url should use canonical trailing slash: {fu}")
        self.assertEqual(by_id["ben_webtv"]["legacy_payload"]["feed_url"],
                         "https://beninwebtv.com/feed/")
        self.assertEqual(by_id["nga_nrc"]["legacy_payload"]["feed_url"],
                         "https://nrc.gov.ng/feed/")

    def test_metric_alias_contract_present_in_source(self):
        """旧名语义不变、新名补齐、别名显式声明（静态契约检查）。"""
        src = (ROOT / "scripts" / "stage3_collect_v2.py").read_text(encoding="utf-8")
        for key in ("execution_rows_configured", "execution_rows_enumerated",
                    "execution_rows_skipped_wall_clock", "execution_rows_actually_attempted",
                    "successful_source_executions", "physical_network_requests",
                    "metrics_alias", "PHASE_TELEMETRY_AVAILABLE"):
            self.assertIn(key, src, f"missing metric key: {key}")
        # 旧字段仍必须写出
        self.assertIn('"attempted_sources": len(per_source)', src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
