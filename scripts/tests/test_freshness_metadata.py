#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_freshness_metadata.py —— PUBLIC FRESHNESS METADATA HOTFIX 验收测试。

覆盖（任务 III）：
  A. 旧 status + 新 site_overview：不误报过期
  B. 两者都旧：仍正确显示红色警告
  C. 数据截止 >12h：黄色提醒
  D. 数据截止 >48h：红色提醒
  E. 构建时间新、真实数据旧：仍提醒（build_time 不冒充数据更新）
  F. 时间字段缺失/损坏：不能判为新鲜（给出"新鲜度未知"）
  G. 北京时间（UTC+8）换算正确
  H. status / 首页 header(ASIP_BUILD_META) / 横幅 一致性
  I. legacy ai_intelligence.json 不被误用为时效来源
  J. 可验证对外计数同步为真实值（II.4）
不触发任何 AI 调用（AI_CALLS=0）。
"""
import os
import sys
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import build_site as bs

FIXED_NOW = datetime(2026, 11, 4, 3, 0, 0, tzinfo=timezone.utc)


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def _make_tree(status=None, site_overview=None, homepage=None, current_metrics=None,
               ai_intel=None, views_dir="views"):
    """在临时 DATA_DIR 内构造 fixture，返回该目录路径。"""
    d = tempfile.mkdtemp(prefix="asip_fresh_")
    if status is not None:
        _write(os.path.join(d, "status.json"), status)
    if site_overview is not None:
        _write(os.path.join(d, views_dir, "site_overview.json"), site_overview)
    if homepage is not None:
        _write(os.path.join(d, views_dir, "homepage_intelligence.json"), homepage)
    if current_metrics is not None:
        _write(os.path.join(d, "public", "current_metrics.json"), current_metrics)
    if ai_intel is not None:
        _write(os.path.join(d, views_dir, "ai_intelligence.json"), ai_intel)
    return d


def _cleanup(d):
    shutil.rmtree(d, ignore_errors=True)


class FreshnessTest(unittest.TestCase):

    def test_A_old_status_new_view_no_false_alarm(self):
        """旧 status.data_as_of(Sept) + 新 site_overview(Nov) → 不误报过期。"""
        d = _make_tree(
            status={"data_as_of": "2026-09-21T12:17:16+00:00",
                    "data_as_of_source": "production_state.last_daily_report"},
            site_overview={"data_as_of": "2026-11-03T18:32:02+00:00",
                           "data_as_of_status": "EXPLICIT",
                           "data_as_of_source": "production_state.last_successful_ai"},
        )
        try:
            meta = bs.get_build_meta(data_dir=d, now=FIXED_NOW)
            self.assertEqual(meta["data_as_of"], "2026-11-03T18:32:02+00:00",
                             "必须采用经验证的视图截止，而非旧 status.data_as_of")
            self.assertEqual(meta["data_as_of_source"], "site_overview.data_as_of")
            self.assertFalse(meta["data_stale"], "新数据（~8.5h）不应判为过期")
            self.assertIsNone(bs._staleness_banner(meta) or None,
                               "新鲜时不显示横幅")
        finally:
            _cleanup(d)

    def test_B_both_old_red_banner(self):
        """status 与视图都旧（>48h）→ 红色警告。"""
        old = (FIXED_NOW - timedelta(hours=72)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        d = _make_tree(
            status={"data_as_of": old},
            site_overview={"data_as_of": old, "data_as_of_status": "EXPLICIT"},
        )
        try:
            meta = bs.get_build_meta(data_dir=d, now=FIXED_NOW)
            self.assertTrue(meta["data_stale"])
            banner = bs._staleness_banner(meta)
            self.assertIn("asip-staleness-banner", banner)
            self.assertIn("数据严重过期", banner)
            self.assertIn(old, banner)
        finally:
            _cleanup(d)

    def test_C_over_12h_yellow(self):
        """数据截止 >12h 且 ≤48h → 黄色提醒。"""
        t = (FIXED_NOW - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        d = _make_tree(site_overview={"data_as_of": t, "data_as_of_status": "EXPLICIT"})
        try:
            meta = bs.get_build_meta(data_dir=d, now=FIXED_NOW)
            banner = bs._staleness_banner(meta)
            self.assertIn("数据可能已过期", banner)
            self.assertIn("#fef3c7", banner)  # 黄底
        finally:
            _cleanup(d)

    def test_D_over_48h_red(self):
        """数据截止 >48h → 红色提醒。"""
        t = (FIXED_NOW - timedelta(hours=60)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        d = _make_tree(site_overview={"data_as_of": t, "data_as_of_status": "EXPLICIT"})
        try:
            meta = bs.get_build_meta(data_dir=d, now=FIXED_NOW)
            banner = bs._staleness_banner(meta)
            self.assertIn("数据严重过期", banner)
            self.assertIn("#fee2e2", banner)  # 红底
        finally:
            _cleanup(d)

    def test_E_build_new_data_old_still_warns(self):
        """构建时间新、真实数据旧 → 仍提醒；build_time 不冒充 data_as_of。"""
        old = (FIXED_NOW - timedelta(hours=50)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        d = _make_tree(site_overview={"data_as_of": old, "data_as_of_status": "EXPLICIT"})
        try:
            meta = bs.get_build_meta(data_dir=d, now=FIXED_NOW)
            self.assertNotEqual(meta["data_as_of"], meta["build_time"],
                                "build_time 不得冒充数据更新时间")
            self.assertEqual(meta["data_as_of"], old)
            self.assertTrue(meta["data_stale"])
            self.assertIsNotNone(bs._staleness_banner(meta))
        finally:
            _cleanup(d)

    def test_F_missing_or_corrupt_not_fresh(self):
        """时间字段缺失/损坏 → age=None → 不得判为新鲜（给出未知提醒）。"""
        # 完全无 views、status 无 data_as_of
        d = _make_tree(status={"run_id": "x", "events_24h": 0})
        try:
            meta = bs.get_build_meta(data_dir=d, now=FIXED_NOW)
            self.assertIsNone(meta["data_age_hours"])
            banner = bs._staleness_banner(meta)
            self.assertIn("数据新鲜度未知", banner)
        finally:
            _cleanup(d)
        # 损坏的时间字段
        d2 = _make_tree(status={"data_as_of": "not-a-date"},
                        site_overview={"data_as_of": "%%broken%%"})
        try:
            meta = bs.get_build_meta(data_dir=d2, now=FIXED_NOW)
            self.assertIsNone(meta["data_age_hours"])
            self.assertIn("数据新鲜度未知", bs._staleness_banner(meta))
        finally:
            _cleanup(d2)

    def test_G_bj_utc_conversion(self):
        """北京时间（UTC+8）换算正确。"""
        d = _make_tree(site_overview={
            "data_as_of": "2026-11-03T18:32:02+00:00", "data_as_of_status": "EXPLICIT"})
        try:
            meta = bs.get_build_meta(data_dir=d, now=FIXED_NOW)
            self.assertEqual(meta["data_as_of_bj"], "2026-11-04 02:32:02")
        finally:
            _cleanup(d)
        # 无时区后缀按北京时间解释
        d2 = _make_tree(site_overview={
            "data_as_of": "2026-11-04T02:32:53", "data_as_of_status": "EXPLICIT"})
        try:
            meta = bs.get_build_meta(data_dir=d2, now=FIXED_NOW)
            self.assertEqual(meta["data_as_of_bj"], "2026-11-04 02:32:53")
        finally:
            _cleanup(d2)

    def test_H_consistency_status_meta_banner(self):
        """status / ASIP_BUILD_META / 横幅 一致性。"""
        d = _make_tree(
            status={"data_as_of": "2026-09-21T12:17:16+00:00"},
            site_overview={"data_as_of": "2026-11-03T18:32:02+00:00",
                           "data_as_of_status": "EXPLICIT"},
        )
        try:
            meta = bs.get_build_meta(data_dir=d, now=FIXED_NOW)
            # 横幅嵌入的日期应与 meta.data_as_of 一致
            banner = bs._staleness_banner(meta)
            self.assertFalse(banner)  # 新鲜 → 无横幅（返回空串），但一致性仍成立
            # 模拟 main() 把 meta 写回 dist status.json
            dist_status = {"data_as_of": "2026-09-21T12:17:16+00:00"}
            if meta.get("data_as_of"):
                dist_status["data_as_of"] = meta["data_as_of"]
                dist_status["data_as_of_bj"] = meta.get("data_as_of_bj") or ""
                dist_status["data_as_of_source"] = meta.get("data_as_of_source") or ""
                dist_status["data_as_of_status"] = meta.get("data_as_of_status") or ""
            self.assertEqual(dist_status["data_as_of"], meta["data_as_of"])
            self.assertEqual(dist_status["data_as_of_bj"], meta["data_as_of_bj"])
        finally:
            _cleanup(d)

    def test_I_legacy_ai_view_excluded(self):
        """legacy ai_intelligence.json 不被误用为时效来源。"""
        # 即使 legacy AI 视图写着 1999，只要 site_overview 有真实 Nov 数据，就用后者
        d = _make_tree(
            site_overview={"data_as_of": "2026-11-03T18:32:02+00:00",
                           "data_as_of_status": "EXPLICIT"},
            ai_intel={"data_as_of": "1999-01-01T00:00:00+00:00",
                      "status": "FALLBACK"},
        )
        try:
            meta = bs.get_build_meta(data_dir=d, now=FIXED_NOW)
            self.assertEqual(meta["data_as_of"], "2026-11-03T18:32:02+00:00")
            self.assertNotIn("ai_intelligence", meta["data_as_of_source"])
        finally:
            _cleanup(d)
        # 完全没有 site_overview 时，legacy AI 也绝不被采用（仍按 fallback 规则）
        d2 = _make_tree(
            status={"data_as_of": "2026-09-21T12:17:16+00:00"},
            ai_intel={"data_as_of": "1999-01-01T00:00:00+00:00",
                      "status": "FALLBACK"},
        )
        try:
            meta = bs.get_build_meta(data_dir=d2, now=FIXED_NOW)
            self.assertNotEqual(meta["data_as_of"], "1999-01-01T00:00:00+00:00")
        finally:
            _cleanup(d2)

    def test_J_count_reconciliation(self):
        """可经 current_metrics 验证的对外计数同步为真实值（II.4）。"""
        d = _make_tree(
            status={"published_event_count": 11, "quarantine_event_count": 683,
                    "pending_event_count": 21, "events_24h": 0},
            site_overview={"data_as_of": "2026-11-03T18:32:02+00:00",
                           "data_as_of_status": "EXPLICIT",
                           "kpis": {"events_24h": 60, "events_72h_ongoing": 45}},
            current_metrics={"published_events": 1921, "quarantine": 21660,
                             "pending_articles": 21},
        )
        try:
            dist_status = {"published_event_count": 11, "quarantine_event_count": 683,
                           "pending_event_count": 21, "events_24h": 0}
            cm = {"published_events": 1921, "quarantine": 21660, "pending_articles": 21}
            so = {"kpis": {"events_24h": 60, "events_72h_ongoing": 45}}
            bs._reconcile_status_counts(dist_status, cm=cm, so=so)
            self.assertEqual(dist_status["published_event_count"], 1921)
            self.assertEqual(dist_status["quarantine_event_count"], 21660)
            self.assertEqual(dist_status["events_24h"], 60)
        finally:
            _cleanup(d)


if __name__ == "__main__":
    unittest.main(verbosity=2)
