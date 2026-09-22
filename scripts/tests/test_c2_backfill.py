#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c2_backfill.py — C2 §二十九 正式测试（15 项）。

  A. 时间与去重（§三/§六/§八）            4 项
  B. Source identity / 验证等级（§十三/§十四）2 项
  C. 历史 quarantine 重判（§七）            3 项
  D. Batch / checkpoint / 持久化（§九/§十/§十一）2 项
  E. 指标与不变量（§十五/§十六/§十七/§十九/§二十六）4 项
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT / "scripts"), str(ROOT / "scripts" / "data"),
          str(ROOT / "scripts" / "collectors"), str(ROOT / "scripts" / "ops"),
          str(ROOT / "scripts" / "clustering"), str(ROOT / "tools" / "c1a")):
    sys.path.insert(0, p)

from data.article_persistence import persist_collected_articles  # noqa: E402
from data.quarantine_reeval import (classify, is_reprocessable,  # noqa: E402
                                   relevance_reprocessable, hold_content_time)
from ops.daily_index import (bj_date, window_days, build_day_matrix,  # noqa: E402
                             density_summary, density_gate)
from clustering.event_clusterer import cluster_events  # noqa: E402
from data.normalizers import derive_verification_level  # noqa: E402

BJ = timezone(timedelta(hours=8))
RULE_CHANGE = datetime(2026, 9, 18, tzinfo=BJ)
W0 = datetime(2026, 9, 5, tzinfo=BJ).astimezone(timezone.utc)
W1 = (datetime(2026, 9, 18, 23, 59, 59, tzinfo=BJ)).astimezone(timezone.utc)


def make_root(tmp):
    os.makedirs(os.path.join(tmp, "data", "canonical"), exist_ok=True)
    with io.open(os.path.join(tmp, "data", "sources.json"), "w", encoding="utf-8") as f:
        json.dump({"schema_version": "2.0", "pipeline_version": 2, "run_id": "t",
                   "sources": []}, f)


def art(url, *, published="2026-09-10 12:00:00", decision="chad", title="Armed attack kills three",
        backfill=True, method="sitemap", pid="SI_x", collected="2026-09-19T08:00:00+08:00"):
    a = {
        "source_id": "chad_tchadinfos", "source_name": "Tchadinfos",
        "source_country": "乍得", "source_type": "local_media", "language": "fr",
        "discovery_method": method, "feed_url": "https://tchadinfos.com/feed/",
        "article_url": url, "canonical_url": url, "original_title": title,
        "original_body": "Corps " * 60, "original_summary": "Résumé",
        "published_at_original": published, "published_at_beijing": published,
        "collected_at_beijing": collected, "article_word_count": 60,
        "extraction_quality": "full_body", "fetch_status": "ok",
        "body_status": "full_body", "fetch_http_status": 200,
        "_country": {"decision": decision}, "_relevant": True, "_rel_score": 0.9,
        "_event_type": "armed_conflict",
    }
    if backfill:
        a.update({"historical_backfill": True, "backfill_collected_at": collected,
                  "backfill_method": method, "publisher_identity_id": pid})
    return a


class TimeAndDedupeTest(unittest.TestCase):
    """A. 时间与去重（§三/§六/§八）"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="c2_time_")
        make_root(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _stored(self):
        p = os.path.join(self.tmp, "data", "canonical", "articles.json")
        return json.load(io.open(p, encoding="utf-8")).get("items") or []

    def test_01_backfill_preserves_original_published_at(self):
        """回填必须保留原始 published_at（不得被 backfill_collected_at 覆盖）"""
        st = persist_collected_articles(
            self.tmp, [art("https://tchadinfos.com/2026/09/10/attack",
                           published="2026-09-10 12:00:00",
                           collected="2026-09-19T08:00:00+08:00")],
            "20260919T080000+0800_c2t001", verbose=False)
        self.assertEqual(st["new_articles_persisted"], 1)
        a = self._stored()[0]
        self.assertTrue(a["published_at"].startswith("2026-09-10T12:00:00"))
        self.assertTrue(a["retrieved_at"].startswith("2026-09-19T08:00:00"))
        self.assertTrue(a["historical_backfill"])
        self.assertEqual(a["backfill_method"], "sitemap")

    def test_02_backfill_does_not_use_collection_time_as_publish_time(self):
        """published_at 与 collection time 必须可区分且不相等"""
        persist_collected_articles(
            self.tmp, [art("https://tchadinfos.com/2026/09/05/a",
                           published="2026-09-05 07:30:00",
                           collected="2026-09-19T09:15:00+08:00")],
            "20260919T080000+0800_c2t002", verbose=False)
        a = self._stored()[0]
        pub = datetime.fromisoformat(a["published_at"])
        col = datetime.fromisoformat(a["backfill_collected_at"])
        self.assertNotEqual(pub.date(), col.date())
        self.assertLess(pub, col)

    def test_03_backfill_does_not_duplicate_live_article(self):
        """同一 URL 已在 store 中（实时采集）时，回填不得重复写入"""
        persist_collected_articles(
            self.tmp, [art("https://tchadinfos.com/2026/09/12/same", backfill=False)],
            "20260919T080000+0800_c2t003", verbose=False)
        n0 = len(self._stored())
        st = persist_collected_articles(
            self.tmp, [art("https://tchadinfos.com/2026/09/12/same/", backfill=True)],
            "20260919T080000+0800_c2t004", verbose=False)
        self.assertEqual(st["new_articles_persisted"], 0)
        self.assertEqual(len(self._stored()), n0)
        total_dup = (st["excludes"].get("EXCLUDED_DUPLICATE_URL", 0)
                     + st["excludes"].get("EXCLUDED_DUPLICATE_CONTENT", 0))
        self.assertGreaterEqual(total_dup, 1)

    def test_04_backfill_uses_existing_publisher_identity(self):
        """回填文章必须带上已批准 publisher 的 identity（不新建 identity）"""
        persist_collected_articles(
            self.tmp, [art("https://tchadinfos.com/2026/09/11/pid", pid="SI_booked")],
            "20260919T080000+0800_c2t005", verbose=False)
        a = self._stored()[0]
        self.assertEqual(a["publisher_identity_id"], "SI_booked")


class IdentityAndVerificationTest(unittest.TestCase):
    """B. Source identity / 验证等级（§十三/§十四）"""

    def test_05_backfill_single_source_not_verified(self):
        """历史单一来源不得自动升级验证等级"""
        lvl = derive_verification_level({}, source_type="local_media",
                                        independent_source_count=1)
        self.assertNotEqual(lvl, "cross_verified")
        lvl2 = derive_verification_level({}, source_type="international_media",
                                         source_group="reuters", independent_source_count=1)
        self.assertNotEqual(lvl2, "cross_verified")

    def test_06_backfill_event_clustering_uses_publisher_identity(self):
        """14 日重聚类按 publisher identity 计数：同 publisher 多 feed ≠ 多来源"""
        def ev(uid, title, src, url, tt):
            return {"event_id": uid, "title_original": title, "country_code": "TD",
                    "event_type": "armed_conflict", "event_time": tt,
                    "canonical_url": url, "source_id": src, "source_name": src,
                    "article_id": "ART_" + uid}
        t1 = "Armed attack kills three in N'Djamena"
        t2 = "Armed attack kills three people in N'Djamena city"
        same, st_same = cluster_events([
            ev("B1", t1, "chad_tchadinfos", "https://tchadinfos.com/1", "2026-09-10 08:00:00"),
            ev("B2", t2, "chad_tchadinfos2", "https://tchadinfos.com/2", "2026-09-10 09:00:00")])
        self.assertEqual(st_same["multi_source_clusters"], 0)
        diff, st_diff = cluster_events([
            ev("C1", t1, "chad_tchadinfos", "https://tchadinfos.com/1", "2026-09-10 08:00:00"),
            ev("C2", t2, "ng_punchng", "https://punchng.com/2", "2026-09-10 09:00:00")])
        self.assertEqual(st_diff["multi_source_clusters"], 1)


class QuarantineReevalTest(unittest.TestCase):
    """C. 历史 quarantine 重判（§七）"""

    APPR = {"tchadinfos.com", "punchng.com"}

    def _entry(self, code, detected, url="https://tchadinfos.com/2026/09/10/a",
               published=None, title="x", language="fr"):
        return {"reason_code": code, "detected_at": detected, "url": url, "title": title,
                "legacy_payload": {"published_time": published, "language": language}}

    def test_07_wrong_country_old_hold_can_be_reprocessed(self):
        """旧逻辑（规则变更前）产生、且在窗口内、域名已批准的 wrong_country → 允许重判"""
        e = self._entry("wrong_country", "2026-07-28T18:24:22Z",
                        published="2026-09-10T03:00:00Z")
        ok, why = is_reprocessable(e, rule_change_at=RULE_CHANGE, window_start=W0,
                                   window_end=W1, approved_domains=self.APPR)
        self.assertTrue(ok, why)
        # 窗口外 → 不允许
        e2 = self._entry("wrong_country", "2026-07-28T18:24:22Z",
                         published="2026-07-10T03:00:00Z")
        ok2, why2 = is_reprocessable(e2, rule_change_at=RULE_CHANGE, window_start=W0,
                                     window_end=W1, approved_domains=self.APPR)
        self.assertFalse(ok2)
        self.assertEqual(why2, "OUTSIDE_BACKFILL_WINDOW")

    def test_08_true_safety_hold_never_released(self):
        """真安全 hold 在任何条件下都不得释放"""
        for code in ("privacy", "personal_data", "illegal_content", "safety_hold"):
            self.assertEqual(classify(code), "TRUE_SAFETY_HOLD")
            e = self._entry(code, "2026-07-01T00:00:00Z", published="2026-09-10T03:00:00Z")
            ok, why = is_reprocessable(e, rule_change_at=RULE_CHANGE, window_start=W0,
                                       window_end=W1, approved_domains=self.APPR)
            self.assertFalse(ok)
            self.assertEqual(why, "TRUE_SAFETY_HOLD_NEVER_RELEASED")

    def test_09_relevance_hold_reprocessed_only_after_classifier_change(self):
        """not_security_relevant：只有在分类器发生**实质变化**（v1→v2）后才允许重判；
        当前版本产生的 hold 不得翻案。"""
        # v1 时代的 hold（无 classifier_version 字段）+ 窗口内 + 已批准域名 → 允许重判
        e1 = self._entry("not_security_relevant", "2026-07-28T18:24:22Z",
                         published="2026-09-10T03:00:00Z", language="fr")
        ok1, why1 = relevance_reprocessable(e1, rule_change_at=RULE_CHANGE, window_start=W0,
                                            window_end=W1, approved_domains=self.APPR)
        self.assertTrue(ok1, why1)
        # 当前版本（v2）产生的 hold → 拒绝
        e2 = self._entry("not_security_relevant", "2026-09-18T01:00:00Z",
                         published="2026-09-10T03:00:00Z")
        e2["classifier_version"] = "v2"
        ok2, why2 = relevance_reprocessable(e2, rule_change_at=RULE_CHANGE, window_start=W0,
                                            window_end=W1, approved_domains=self.APPR)
        self.assertFalse(ok2)
        self.assertEqual(why2, "PRODUCED_UNDER_CURRENT_CLASSIFIER")
        # 域名未批准 → 拒绝（不扩到全部历史/非批准来源）
        e3 = self._entry("not_security_relevant", "2026-07-28T18:24:22Z",
                         url="https://not-approved.example/2026/09/10/a",
                         published="2026-09-10T03:00:00Z")
        ok3, why3 = relevance_reprocessable(e3, rule_change_at=RULE_CHANGE, window_start=W0,
                                            window_end=W1, approved_domains=self.APPR)
        self.assertFalse(ok3)
        self.assertEqual(why3, "DOMAIN_NOT_APPROVED")

    def test_10_hold_content_time_from_url_path(self):
        """无显式时间时，可从 URL 的 /YYYY/MM/DD/ 路径取得内容真实日期"""
        e = self._entry("wrong_country", "2026-07-28T00:00:00Z",
                        url="https://tchadinfos.com/2026/09/16/some-story/")
        t = hold_content_time(e)
        self.assertIsNotNone(t)
        self.assertEqual(bj_date(t), "2026-09-16")


class BatchAndCheckpointTest(unittest.TestCase):
    """D. Batch / checkpoint / 持久化（§九/§十/§十一）"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="c2_batch_")
        make_root(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_11_backfill_batch_persists_before_next_batch(self):
        """每个 batch（乃至每个 publisher）必须先把文章落盘再做下一步"""
        st = persist_collected_articles(
            self.tmp, [art("https://tchadinfos.com/2026/09/09/batch1")],
            "20260919T080000+0800_c2t011", verbose=False)
        self.assertEqual(st["new_articles_persisted"], 1)
        p = os.path.join(self.tmp, "data", "canonical", "articles.json")
        self.assertTrue(os.path.exists(p))
        items = json.load(io.open(p, encoding="utf-8"))["items"]
        self.assertEqual(len(items), 1)
        # 第二个 batch 追加而非覆盖
        st2 = persist_collected_articles(
            self.tmp, [art("https://tchadinfos.com/2026/09/08/batch2")],
            "20260919T080000+0800_c2t012", verbose=False)
        self.assertEqual(st2["new_articles_persisted"], 1)
        items2 = json.load(io.open(p, encoding="utf-8"))["items"]
        self.assertEqual(len(items2), 2)
        self.assertEqual(st2["store_before"], 1)
        self.assertEqual(st2["store_after"], 2)

    def test_12_backfill_checkpoint_resume(self):
        """checkpoint 必须记录窗口/batch/已完成 publisher，可据此 resume 而不重抓"""
        bdir = os.path.join(self.tmp, "data", "runtime", "backfill")
        os.makedirs(bdir, exist_ok=True)
        state = {"window_start": "2026-09-05", "window_end": "2026-09-18", "batch_id": 1,
                 "publisher_total": 61, "publisher_completed": 2,
                 "publisher_completed_list": ["a.com", "b.com"],
                 "last_completed_publisher": "b.com"}
        p = os.path.join(bdir, "c2_14d_state.json")
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        back = json.load(io.open(p, encoding="utf-8"))
        self.assertEqual(back["window_start"], "2026-09-05")
        self.assertEqual(back["publisher_completed"], 2)
        # resume 时已完成的 publisher 必须被跳过
        done = set(back["publisher_completed_list"])
        self.assertIn("a.com", done)
        self.assertIn(back["last_completed_publisher"], done)
        self.assertEqual(back["publisher_total"], 61)


class MetricsInvariantTest(unittest.TestCase):
    """E. 指标与不变量（§十五/§十六/§十七/§十九/§二十六）"""

    def test_13_backfill_canonical_threshold_unchanged(self):
        """canonical 阈值必须仍为 isc>=2 AND quality_gate_passed"""
        src = io.open(os.path.join(ROOT, "scripts", "data", "normalizers.py"),
                      encoding="utf-8").read()
        self.assertIn("if independent_source_count >= 2:", src)
        self.assertEqual(derive_verification_level(
            {}, source_type="local_media", independent_source_count=2), "cross_verified")
        self.assertNotEqual(derive_verification_level(
            {}, source_type="local_media", independent_source_count=1), "cross_verified")

    def test_14_backfill_ai_calls_zero(self):
        """C2 不得引入任何 AI 调用（不翻译、不生成 summary/analysis）"""
        for rel in ("tools/c1a/build_news_stream.py",
                    "scripts/data/article_persistence.py",
                    "scripts/ops/daily_index.py",
                    "scripts/data/quarantine_reeval.py"):
            s = io.open(os.path.join(ROOT, rel), encoding="utf-8").read().lower()
            for banned in ("deepseek", "openai", "api_key", "llm(", "requests.post"):
                self.assertNotIn(banned, s, "%s must stay AI-free" % rel)

    def test_15_daily_index_has_14_complete_days(self):
        """14 日索引必须是连续 14 个完整自然日，且逐日计数来自真实 published_at"""
        days = window_days("2026-09-05", "2026-09-18")
        self.assertEqual(len(days), 14)
        self.assertEqual(days[0], "2026-09-05")
        self.assertEqual(days[-1], "2026-09-18")
        items = []
        for i, d in enumerate(days):
            for _ in range(i):          # 第 i 天放 i 条
                items.append({"observed_at": "%sT10:00:00+08:00" % d,
                              "country_cn": "乍得", "source_group": "s%d" % i,
                              "event_type": "armed_conflict"})
        rows = build_day_matrix(days, items, [])
        self.assertEqual(len(rows), 14)
        self.assertEqual([r["NEWS_COUNT"] for r in rows], list(range(14)))
        self.assertEqual(rows[3]["date"], "2026-09-08")
        # 窗口外的条目不得计入
        rows2 = build_day_matrix(days, items + [{"observed_at": "2026-10-01T10:00:00+08:00",
                                                "country_cn": "乍得"}], [])
        self.assertEqual(sum(r["NEWS_COUNT"] for r in rows2), sum(range(14)))
        # 门禁阈值固定
        s = density_summary(rows)
        self.assertEqual(s["DAYS_TOTAL"], 14)
        self.assertEqual(density_gate(rows), "FAIL")
        # C2B §三十二 务实 Gate
        good = [{"NEWS_COUNT": 21, "PUBLISHER_COUNT": 6, "COUNTRY_COUNT": 5}] * 14
        self.assertEqual(density_gate(good), "PASS")
        cond = [{"NEWS_COUNT": 19, "PUBLISHER_COUNT": 5, "COUNTRY_COUNT": 4}] * 14
        self.assertEqual(density_gate(cond), "CONDITIONAL_PASS")
        thin = [{"NEWS_COUNT": 5, "PUBLISHER_COUNT": 2, "COUNTRY_COUNT": 2}] * 14
        self.assertEqual(density_gate(thin), "FAIL")

    def test_16_timeline_news_counts_match_news_stream(self):
        """Timeline 的每日事件计数与 News Stream 逐日计数必须来自同一事实链
        （同一批 canonical 内容、同一东八区自然日口径）。"""
        days = window_days("2026-09-05", "2026-09-18")
        # 同一批内容：既进 news stream，也应由 timeline 覆盖到同一天
        items = [{"observed_at": "2026-09-07T09:00:00+08:00", "country_cn": "苏丹",
                  "source_group": "dabanga", "event_type": "armed_conflict"},
                 {"observed_at": "2026-09-07T11:00:00+08:00", "country_cn": "苏丹",
                  "source_group": "dabanga", "event_type": "armed_conflict"}]
        tl = {"2026-09-07": 2}
        rows = build_day_matrix(days, items, [], timeline_events_by_day=tl)
        d7 = [r for r in rows if r["date"] == "2026-09-07"][0]
        self.assertEqual(d7["NEWS_COUNT"], 2)
        self.assertEqual(d7["TIMELINE_EVENTS"], 2)
        self.assertEqual(d7["NEWS_COUNT"], d7["TIMELINE_EVENTS"])
        # 归属口径必须用真实 published_at（bj_date 而非采集时间）
        self.assertEqual(bj_date("2026-09-07T16:30:00Z"), "2026-09-08")
        self.assertEqual(bj_date("2026-09-07T15:30:00Z"), "2026-09-07")


if __name__ == "__main__":
    unittest.main(verbosity=2)
