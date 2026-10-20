#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C8-4D2 — 来源注册表不变量回归（Part B/C 修复的守护测试）。

覆盖本轮实际修过/验证过的缺陷类别：
  R1  相对路径 feed_url（ben_webtv 类）不得出现在启用源中
  R2  rss/atom 源必须有非空绝对 feed_url；html_listing 源必须有非空 listing_urls
  R3  发现方式必须是采集器支持集合内的值
  R4  源数不变量（153 逻辑 / 151 启用）—— 防止顺手加源
  R5  本轮三处修复的目标形态（VOA ×2 失效 URL、ACSS 空 feed → html_listing）
  R6  http:// 明文 feed 只允许出现在既有豁免集中（不得新增）
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "data" / "sources.json"

SUPPORTED_METHODS = {"rss", "atom", "gdelt_search", "reliefweb_api", "html_listing"}
#: 既有明文 http 源（历史上游仅提供 http，且已实测 301/200）：不得新增
HTTP_ALLOWLIST = {"niger_garde_nationale", "nga_transport_moh"}  # 既有上游仅提供 http（已实测），不得新增


class TestSourceRegistryInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(SOURCES.read_text(encoding="utf-8"))
        cls.srcs = cls.doc["sources"]
        cls.enabled = [s for s in cls.srcs
                       if s.get("legacy_payload", {}).get("enabled", s.get("enabled"))]

    def test_counts_unchanged(self):
        self.assertEqual(len(self.srcs), 153)
        self.assertEqual(len(self.enabled), 151)

    def test_no_relative_feed_url(self):
        for s in self.enabled:
            fu = (s.get("legacy_payload", {}).get("feed_url") or "").strip()
            if fu:
                self.assertTrue(fu.startswith(("http://", "https://")),
                                f"{s['source_id']} 相对/非法 feed_url: {fu}")

    def test_rss_requires_absolute_feed_url(self):
        for s in self.enabled:
            lp = s.get("legacy_payload", {})
            if (lp.get("collection_method") or "") in ("rss", "atom"):
                fu = (lp.get("feed_url") or "").strip()
                self.assertTrue(fu, f"{s['source_id']} rss 源缺少 feed_url")
                self.assertTrue(fu.startswith(("http://", "https://")), s["source_id"])

    def test_html_listing_requires_listing_urls(self):
        for s in self.enabled:
            lp = s.get("legacy_payload", {})
            if (lp.get("collection_method") or "") == "html_listing":
                urls = s.get("listing_urls") or lp.get("category_urls") or []
                self.assertTrue(urls, f"{s['source_id']} html_listing 源缺少 listing_urls")
                for u in urls:
                    self.assertTrue(str(u).startswith(("http://", "https://")), u)

    def test_supported_discovery_methods(self):
        for s in self.enabled:
            m = (s.get("legacy_payload", {}).get("collection_method") or "html_listing")
            self.assertIn(m, SUPPORTED_METHODS, f"{s['source_id']}: {m}")

    def test_no_new_plain_http_feed(self):
        for s in self.enabled:
            fu = (s.get("legacy_payload", {}).get("feed_url") or "").strip()
            if fu.startswith("http://"):
                self.assertIn(s["source_id"], HTTP_ALLOWLIST,
                              f"{s['source_id']} 新增明文 http feed: {fu}")

    def test_repaired_targets(self):
        by = {s["source_id"]: s for s in self.srcs}
        self.assertEqual(by["pan_voa_africa"]["legacy_payload"]["feed_url"],
                         "https://www.voaafrica.com/api/")
        self.assertEqual(by["pan_voa_afrique"]["legacy_payload"]["feed_url"],
                         "https://www.voaafrique.com/api/")
        for sid in ("pan_voa_africa", "pan_voa_afrique"):
            self.assertNotIn("zrqiteukiq", by[sid]["legacy_payload"]["feed_url"],
                             "失效 token 端点不得回归")
        acss = by["specialist_acss"]
        self.assertEqual(acss["legacy_payload"]["collection_method"], "html_listing")
        self.assertEqual(acss["legacy_payload"]["feed_url"], "")
        self.assertEqual(acss["listing_urls"], ["https://africacenter.org/"])

    def test_no_new_source_added_this_package(self):
        """Africa CDC 等技术门槛未过项不得被顺手加入（源数是结果，不是目标）。"""
        ids = {s["source_id"] for s in self.srcs}
        for forbidden in ("pan_africacdc", "intl_africacdc", "un_africacdc"):
            self.assertNotIn(forbidden, ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
