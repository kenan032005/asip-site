#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C8-4D1 STEP0/STEP1 回归测试。

§STEP0  PHASE 遥测：显式入参（write_stats(..., phase_stats=...)）、由真实
        source-country 执行行派生、相位耗时只用逐行实测值、相位跳过与
        per_source 墙钟跳过必须对账。
§STEP1  缓存新鲜度上限：长采集周期内同一共享响应不得无限期复用。
"""
import os
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "scripts" / "collectors")):
    if p not in sys.path:
        sys.path.insert(0, p)

import framework  # noqa: E402
import stage3_collect_v2 as s3  # noqa: E402


def _row(sid, country, phase, status="success", duration=1.0):
    row = {
        "source_id": sid, "source_name": sid, "country": country, "method": "rss",
        "discovered": 3, "fetched": 3, "full_body": 3, "partial_body": 0,
        "summary_only": 0, "extraction_failed": 0, "published": 1,
        "quarantined": 0, "duplicates": 0, "errors": 0,
        "status": status, "error": "", "duration_s": duration,
    }
    if phase is not None:
        row["phase"] = phase
    return row


class _StatsHarness(unittest.TestCase):
    """把 stats 落盘与 time_contract 隔离到临时目录，测试不污染仓库数据。"""

    def setUp(self):
        self._saved_stats_path = s3.STATS_PATH
        self._tmp = tempfile.mkdtemp(prefix="c84d1_")
        s3.STATS_PATH = os.path.join(self._tmp, "stats.json")
        self._saved_tc = sys.modules.get("ops.time_contract")
        stub = types.ModuleType("ops.time_contract")
        stub.write_contract = lambda **kw: {"data_as_of": "TEST", "status": "TEST", "touched": []}
        stub.refresh_derived_snapshots = lambda **kw: {"data_as_of": "TEST", "status": "TEST", "touched": []}
        sys.modules["ops.time_contract"] = stub

    def tearDown(self):
        s3.STATS_PATH = self._saved_stats_path
        if self._saved_tc is not None:
            sys.modules["ops.time_contract"] = self._saved_tc
        else:
            sys.modules.pop("ops.time_contract", None)


class TestPhaseTelemetryFromRows(_StatsHarness):
    def test_fields_derived_from_source_country_rows(self):
        rows = [
            _row("n1", "尼日尔", 0, duration=2.5),
            _row("n2", "尼日尔", 0, status="skipped_wall_clock", duration=0.0),
            _row("c1", "乍得", 1, duration=1.5),
            _row("x1", "马里", 3, duration=0.7),
        ]
        t = s3.write_stats(rows, "T_PHASE", configured_sources=153,
                           phase_stats={"unenumerated": 2})
        self.assertIs(t["PHASE_TELEMETRY_AVAILABLE"], True)
        self.assertEqual(t["PHASE_TELEMETRY_BASIS"], "measured_source_country_rows")
        self.assertEqual(t["PHASE_ELAPSED_BASIS"], "measured_row_durations")
        # 相位 0：2 枚举行 / 1 实际尝试 / 1 墙钟跳过 / 实测 2.5s
        self.assertEqual(t["PHASE0_ENUMERATED"], 2)
        self.assertEqual(t["PHASE0_ATTEMPTED"], 1)
        self.assertEqual(t["PHASE0_EXECUTIONS"], 1)
        self.assertEqual(t["PHASE0_SKIPPED_WALL_CLOCK"], 1)
        self.assertEqual(t["PHASE0_ELAPSED_SECONDS"], 2.5)
        self.assertEqual(t["PHASE1_ELAPSED_SECONDS"], 1.5)
        self.assertEqual(t["PHASE3_ELAPSED_SECONDS"], 0.7)
        self.assertEqual(t["PHASE2_ENUMERATED"], 0)
        # 15 个字段全部存在且为数值
        for p in range(5):
            for suffix in ("EXECUTIONS", "SKIPPED_WALL_CLOCK", "ELAPSED_SECONDS"):
                k = "PHASE%d_%s" % (p, suffix)
                self.assertIsInstance(t[k], (int, float), "%s must be numeric" % k)
        # 对账
        self.assertEqual(t["PHASE_SKIPPED_TOTAL"], 1)
        self.assertIs(t["PHASE_SKIP_RECONCILED"], True)
        self.assertEqual(t["PHASE_UNENUMERATED_KEYS"], 2)

    def test_explicit_arg_without_stamps_uses_declared_fallback(self):
        rows = [_row("a", "乍得", None), _row("b", "尼日尔", None)]
        ps = {p: {"executions": 0, "skipped": 0, "elapsed": 0.0} for p in range(5)}
        ps[1]["executions"] = 2
        t = s3.write_stats(rows, "T_FALLBACK", configured_sources=153, phase_stats=ps)
        self.assertIs(t["PHASE_TELEMETRY_AVAILABLE"], True)
        self.assertEqual(t["PHASE_TELEMETRY_BASIS"], "aggregate_fallback")
        self.assertEqual(t["PHASE1_EXECUTIONS"], 2)
        # 不得把估算耗时当精确值上报
        self.assertEqual(t["PHASE1_ELAPSED_SECONDS"], "UNKNOWN")
        self.assertEqual(t["PHASE_ELAPSED_BASIS"], "UNKNOWN")

    def test_missing_telemetry_is_unknown_not_zero(self):
        t = s3.write_stats([_row("a", "乍得", None)], "T_NONE", configured_sources=153)
        self.assertIs(t["PHASE_TELEMETRY_AVAILABLE"], False)
        for p in range(5):
            self.assertEqual(t["PHASE%d_EXECUTIONS" % p], "UNKNOWN")
            self.assertEqual(t["PHASE%d_SKIPPED_WALL_CLOCK" % p], "UNKNOWN")
            self.assertEqual(t["PHASE%d_ELAPSED_SECONDS" % p], "UNKNOWN")

    def test_skip_mismatch_is_flagged(self):
        """相位缺失但行标为墙钟跳过 → 对账必须显式失败，不静默通过。"""
        rows = [_row("n1", "尼日尔", 0),
                _row("weird", "尼日尔", 9, status="skipped_wall_clock")]
        t = s3.write_stats(rows, "T_MISMATCH", configured_sources=153,
                           phase_stats={"unenumerated": 0})
        self.assertEqual(t["PHASE_SKIPPED_TOTAL"], 0)
        self.assertIs(t["PHASE_SKIP_RECONCILED"], False)


class TestCacheFreshness(unittest.TestCase):
    def setUp(self):
        self._saved_env = {k: os.environ.get(k) for k in (
            framework.SHARED_REUSE_ENV, framework.SHARED_REUSE_SOURCES_ENV)}
        os.environ[framework.SHARED_REUSE_ENV] = "1"
        self._orig_urlopen = framework.urllib.request.urlopen
        self._orig_validate = framework.validate_url
        framework.validate_url = lambda url: (True, "ok")
        framework.reset_run_caches()
        self.calls = []

        def _fake(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            self.calls.append(url)

            class _H:
                def get_content_charset(self):
                    return "utf-8"

                def get(self, k, d=None):
                    return d

            class _R:
                status = 200
                headers = _H()

                def read(self, n=-1):
                    return b"<rss><channel><title>t</title></channel></rss>"

                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

            return _R()

        framework.urllib.request.urlopen = _fake

    def tearDown(self):
        framework.urllib.request.urlopen = self._orig_urlopen
        framework.validate_url = self._orig_validate
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        framework.reset_run_caches()

    def test_expired_entry_refetches(self):
        saved_ttl = framework.SHARED_REUSE_TTL_SECONDS
        framework.SHARED_REUSE_TTL_SECONDS = 0.05
        try:
            framework.fetch_page("https://feed.example/a", reuse=True, source_id="s1")
            time.sleep(0.12)
            framework.fetch_page("https://feed.example/a", reuse=True, source_id="s2")
            st = framework.get_request_stats()
            self.assertEqual(len(self.calls), 2, "expired entry must be refetched")
            self.assertEqual(st["cache_hits"], 0)
            self.assertGreaterEqual(st["cache_expired"], 1)
            self.assertEqual(st["ttl_seconds"], 0.05)
        finally:
            framework.SHARED_REUSE_TTL_SECONDS = saved_ttl

    def test_fresh_entry_reused_within_ttl(self):
        framework.fetch_page("https://feed.example/a", reuse=True, source_id="s1")
        framework.fetch_page("https://feed.example/a", reuse=True, source_id="s2")
        st = framework.get_request_stats()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(st["cache_expired"], 0)
        self.assertEqual(st["cache_hits"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
