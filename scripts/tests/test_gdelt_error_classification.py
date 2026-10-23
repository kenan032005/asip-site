#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_gdelt_error_classification.py — C8-4E W1：GDELT 五类错误分类测试。

分组：
  A. 限流器响应体分类（classify_body / fetch）   8 项
  B. 采集器错误映射（_fetch_group / run）          4 项
  C. 失败原因分类（failure_reasons）               6 项
  D. 安全约束（不泄漏原始响应体）                 2 项

五类区分（用户规格）：
  1. HTTP_429 / GDELT_RATE_LIMITED
  2. HTTP 200 + 非 JSON 响应
  3. JSON 格式损坏或结构异常
  4. 合法 JSON 但 articles=[]（唯一记 QUERY_NO_RESULT 的情况）
  5. 网络异常、超时及其它 HTTP 错误
"""
import json
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "collectors"))

from gdelt_rate_limiter import (  # noqa: E402
    GdeltSharedRateLimiter, classify_body,
    BODY_JSON_OK, BODY_JSON_STRUCTURE, BODY_JSON_CORRUPT, BODY_NON_JSON, BODY_EMPTY,
    ERR_GDELT_NON_JSON, ERR_GDELT_JSON_INVALID)
import gdelt_search_collector as gsc  # noqa: E402
from failure_reasons import (  # noqa: E402
    classify_source_failure, QUERY_NO_RESULT, HTTP_429, HTTP_403, TIMEOUT,
    GDELT_NON_JSON_RESPONSE, GDELT_JSON_INVALID)

URL = "https://api.gdeltproject.org/api/v2/doc/doc?q=x"
ADVISORY = ("Please limit requests to one every 5 seconds or contact "
            "kalev.leetaru5@gmail.com for larger queries. All high-traffic users "
            "should switch to our ngrams dataset: https://blog.gdeltproject.org/...")
SECRET_BODY = "internal-note SECRET_TOKEN_123 do-not-log"


class _FakeHeaders:
    """够用的 headers 桩：限流器只调用 get_content_charset()。"""

    def get_content_charset(self):
        return "utf-8"


class _FakeResp:
    def __init__(self, body, status=200):
        self._b = body.encode("utf-8") if isinstance(body, str) else body
        self.status = status
        self.headers = _FakeHeaders()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_error(code):
    return urllib.error.HTTPError(URL, code, "err", {}, None)


def _limiter(max_attempts=2):
    """零间隔 + 假时钟：测试不产生真实等待、不发起真实请求。"""
    return GdeltSharedRateLimiter(min_interval=0.0, max_interval=0.0, max_attempts=max_attempts,
                                  budget=10, timeout=5, allow_network=True,
                                  clock=lambda: 0.0, sleeper=lambda s: None)


class TestA_LimiterBodyClassification(unittest.TestCase):
    """A. 限流器：五类响应体分类"""

    def test_a1_200_valid_json_with_articles(self):
        body = json.dumps({"articles": [{"title": "t", "url": "https://a.example/x"}]})
        with mock.patch("urllib.request.urlopen", return_value=_FakeResp(body)):
            text, err, meta = _limiter().fetch(URL)
        self.assertIsNotNone(text)
        self.assertIsNone(err)
        self.assertEqual(meta["body_class"], BODY_JSON_OK)
        self.assertEqual(meta["status"], 200)
        self.assertEqual(len(json.loads(text)["articles"]), 1)

    def test_a2_200_valid_json_empty_articles_is_legit_empty(self):
        body = json.dumps({"articles": []})
        with mock.patch("urllib.request.urlopen", return_value=_FakeResp(body)):
            text, err, meta = _limiter().fetch(URL)
        self.assertIsNotNone(text)          # 合法空结果：保留文本，由下游记 QUERY_NO_RESULT
        self.assertIsNone(err)
        self.assertEqual(meta["body_class"], BODY_JSON_OK)

    def test_a3_200_non_json_text(self):
        with mock.patch("urllib.request.urlopen", return_value=_FakeResp(ADVISORY)):
            text, err, meta = _limiter().fetch(URL)
        self.assertIsNone(text)
        self.assertIsNotNone(err)
        self.assertTrue(err.startswith(ERR_GDELT_NON_JSON + "("), err)
        self.assertEqual(meta["body_class"], BODY_NON_JSON)
        self.assertNotIn("Please limit", err)   # 不输出原文
        self.assertNotIn("kalev", err)

    def test_a3b_200_empty_body(self):
        with mock.patch("urllib.request.urlopen", return_value=_FakeResp("")):
            text, err, meta = _limiter().fetch(URL)
        self.assertIsNone(text)
        self.assertTrue(err.startswith(ERR_GDELT_NON_JSON + "("), err)
        self.assertEqual(meta["body_class"], BODY_EMPTY)

    def test_a4_http_429(self):
        with mock.patch("urllib.request.urlopen", side_effect=_http_error(429)):
            text, err, meta = _limiter().fetch(URL)
        self.assertIsNone(text)
        self.assertTrue(meta["rate_limited"])
        self.assertEqual(meta["status"], 429)
        self.assertIn("429", str(err))

    def test_a5_http_403(self):
        with mock.patch("urllib.request.urlopen", side_effect=_http_error(403)):
            text, err, meta = _limiter().fetch(URL)
        self.assertIsNone(text)
        self.assertFalse(meta["rate_limited"])
        self.assertEqual(meta["status"], 403)
        self.assertIn("403", str(err))

    def test_a6_connection_timeout(self):
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            text, err, meta = _limiter().fetch(URL)
        self.assertIsNone(text)
        self.assertEqual(meta["status"], "TimeoutError")
        self.assertIn("TimeoutError", str(err))

    def test_a7_json_structure_abnormal(self):
        for bad in ('{"foo": 1}', '[1, 2, 3]', '{"articles": "not-a-list"}', '{"articles":'):
            with mock.patch("urllib.request.urlopen", return_value=_FakeResp(bad)):
                text, err, meta = _limiter().fetch(URL)
            self.assertIsNone(text, bad)
            self.assertTrue(err.startswith(ERR_GDELT_JSON_INVALID + "("), (bad, err))
            self.assertIn(meta["body_class"], (BODY_JSON_STRUCTURE, BODY_JSON_CORRUPT), bad)

    def test_a8_classify_body_unit(self):
        c, _d, e = classify_body('{"articles": []}')
        self.assertEqual((c, e), (BODY_JSON_OK, None))
        c, _d, e = classify_body(ADVISORY)
        self.assertEqual(c, BODY_NON_JSON)
        self.assertTrue(e.startswith(ERR_GDELT_NON_JSON + "("))
        c, _d, e = classify_body(None)
        self.assertEqual((c, e), (None, None))
        c, _d, e = classify_body('{"articles": [{"title": "x"}]}')
        self.assertEqual((c, e), (BODY_JSON_OK, None))


class TestB_CollectorMapping(unittest.TestCase):
    """B. 采集器：错误码透传"""

    def setUp(self):
        gsc._CACHE.clear()

    def _group(self, ret):
        with mock.patch.object(gsc, "fetch_gdelt", return_value=ret):
            return gsc._fetch_group({"source_id": "intl_reuters_chad", "country": "",
                                     "query": "domain:reuters.com Chad"}, "Chad", "72h")

    def test_b1_non_json_maps_to_error_code(self):
        e = self._group((None, "GDELT_NON_JSON_RESPONSE(body_len=347, advisory_like=True)",
                         {"rate_limited": False, "status": 200, "body_class": "non_json"}))
        self.assertTrue(e["error"].startswith("gdelt fetch: GDELT_NON_JSON_RESPONSE"), e["error"])
        self.assertFalse(e["rate_limited"])
        self.assertNotIn("Please limit", e["error"])

    def test_b2_legit_empty_has_no_error(self):
        e = self._group((json.dumps({"articles": []}), None,
                         {"rate_limited": False, "status": 200, "body_class": "json_ok"}))
        self.assertIsNone(e["error"])
        self.assertEqual(e["articles"], [])

    def test_b3_429_maps_to_rate_limited(self):
        e = self._group((None, "HTTP 429",
                         {"rate_limited": True, "status": 429, "body_class": None}))
        self.assertTrue(e["rate_limited"])
        self.assertIn("GDELT_RATE_LIMITED", e["error"])

    def test_b4_run_surfaces_error_without_body(self):
        src = {"source_id": "intl_reuters_chad", "language": "en",
               "query": "domain:reuters.com Chad"}
        with mock.patch.object(gsc, "fetch_gdelt",
                               return_value=(None, "GDELT_JSON_INVALID(body_len=12, parse_error=JSONDecodeError)",
                                             {"rate_limited": False, "status": 200,
                                              "body_class": "json_corrupt"})):
            col = gsc.GdeltSearchCollector(src)
            arts = col.run()
        self.assertEqual(arts, [])
        self.assertTrue(any("GDELT_JSON_INVALID" in e for e in col.errors), col.errors)
        self.assertFalse(any("body:" in e for e in col.errors))


class TestC_FailureReasonMapping(unittest.TestCase):
    """C. failure_reasons：五类归因"""

    def test_c1_non_json_response(self):
        code, _ev = classify_source_failure(
            {"discovered": 0, "method": "gdelt_search"},
            ["intl_reuters_chad: gdelt fetch: GDELT_NON_JSON_RESPONSE(body_len=347, advisory_like=True)"])
        self.assertEqual(code, GDELT_NON_JSON_RESPONSE)

    def test_c2_json_invalid(self):
        code, _ev = classify_source_failure(
            {"discovered": 0, "method": "gdelt_search"},
            ["intl_ap_chad: gdelt fetch: GDELT_JSON_INVALID(body_len=12, parse_error=JSONDecodeError)"])
        self.assertEqual(code, GDELT_JSON_INVALID)

    def test_c3_legit_empty_only_is_query_no_result(self):
        code, _ev = classify_source_failure(
            {"discovered": 0, "method": "gdelt_search"}, [])
        self.assertEqual(code, QUERY_NO_RESULT)

    def test_c4_429_and_403(self):
        code, _ = classify_source_failure({"discovered": 0, "method": "gdelt_search"},
                                          ["gdelt fetch: GDELT_RATE_LIMITED(HTTP 429) ... 429"])
        self.assertEqual(code, HTTP_429)
        code, _ = classify_source_failure({"discovered": 0, "method": "gdelt_search"},
                                          ["intl_x: gdelt fetch: HTTP 403"])
        self.assertEqual(code, HTTP_403)

    def test_c5_timeout(self):
        code, _ = classify_source_failure({"discovered": 0, "method": "gdelt_search"},
                                          ["intl_x: gdelt fetch: TimeoutError: timed out"])
        self.assertEqual(code, TIMEOUT)

    def test_c6_legacy_advisory_body_still_classified(self):
        # 旧实现把限流建议原文写进 error；新规则应将其归入非 JSON 类
        code, _ = classify_source_failure(
            {"discovered": 0, "method": "gdelt_search"},
            ["gdelt json: Expecting value / body: Please limit requests to one every 5 seconds ..."])
        self.assertEqual(code, GDELT_NON_JSON_RESPONSE)


class TestD_NoSensitiveLeak(unittest.TestCase):
    """D. 安全约束：不泄漏原始响应体"""

    def test_d1_secret_body_not_in_error(self):
        with mock.patch("urllib.request.urlopen", return_value=_FakeResp(SECRET_BODY)):
            text, err, meta = _limiter().fetch(URL)
        blob = json.dumps({"text": text, "err": err, "meta": meta}, ensure_ascii=False)
        self.assertNotIn("SECRET_TOKEN_123", blob)
        self.assertNotIn("do-not-log", blob)

    def test_d2_collector_error_has_no_raw_body(self):
        gsc._CACHE.clear()
        with mock.patch.object(gsc, "fetch_gdelt",
                               return_value=(None, "GDELT_NON_JSON_RESPONSE(body_len=%d, advisory_like=True)" % len(SECRET_BODY),
                                             {"rate_limited": False, "status": 200,
                                              "body_class": "non_json"})):
            e = gsc._fetch_group({"source_id": "intl_reuters_chad", "country": "",
                                  "query": "domain:reuters.com Chad"}, "Chad", "72h")
        self.assertNotIn("SECRET_TOKEN_123", e["error"])
        self.assertNotIn("body:", e["error"])


class TestE_RequestCounting(unittest.TestCase):
    """E. 逻辑查询数 vs 物理 HTTP 尝试数（C8-4E W2 STEP3：重试不得遗漏在物理计数之外）"""

    def test_e1_success_is_one_query_one_attempt(self):
        body = json.dumps({"articles": [{"title": "t", "url": "https://a.example/x"}]})
        with mock.patch("urllib.request.urlopen", return_value=_FakeResp(body)) as m:
            lim = _limiter()
            lim.fetch(URL)
            st = lim.stats()
        self.assertEqual(st["logical_queries"], 1)
        self.assertEqual(st["physical_http_attempts"], 1)
        self.assertEqual(st["actual_http_requests"], 1)
        self.assertEqual(m.call_count, 1)

    def test_e2_429_retries_counted_as_physical_attempts(self):
        with mock.patch("urllib.request.urlopen", side_effect=_http_error(429)) as m:
            lim = _limiter(max_attempts=3)
            lim.fetch(URL)
            st = lim.stats()
        self.assertEqual(st["logical_queries"], 1)          # 一次逻辑查询
        self.assertEqual(st["physical_http_attempts"], 3)   # 3 次物理尝试（含 2 次重试）
        self.assertEqual(st["actual_http_requests"], 3)
        self.assertEqual(m.call_count, 3)
        self.assertGreaterEqual(st["backoff_events"], 1)

    def test_e3_cache_hit_adds_no_query_no_attempt(self):
        body = json.dumps({"articles": []})
        with mock.patch("urllib.request.urlopen", return_value=_FakeResp(body)) as m:
            lim = _limiter()
            lim.fetch(URL)
            lim.fetch(URL)          # 同签名：缓存命中
            st = lim.stats()
        self.assertEqual(st["logical_queries"], 1)
        self.assertEqual(st["physical_http_attempts"], 1)
        self.assertEqual(st["cache_hits"], 1)
        self.assertEqual(m.call_count, 1)

    def test_e4_retry_then_success_counts_two_attempts(self):
        calls = {"n": 0}

        def flaky(*a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                raise _http_error(429)
            return _FakeResp(json.dumps({"articles": [{"title": "t", "url": "https://a.example/x"}]}))

        with mock.patch("urllib.request.urlopen", side_effect=flaky) as m:
            lim = _limiter(max_attempts=3)
            text, err, meta = lim.fetch(URL)
            st = lim.stats()
        self.assertIsNotNone(text)
        self.assertIsNone(err)
        self.assertEqual(st["logical_queries"], 1)
        self.assertEqual(st["physical_http_attempts"], 2)   # 1 次 429 + 1 次成功
        self.assertEqual(m.call_count, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
