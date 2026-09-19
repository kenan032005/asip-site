#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c3r_runtime.py — C3R §五/§六/§十七/§十九 测试。

  A. Country fact pack 三窗口（§五）            4 项
  B. live_published_events 身份与缓存（§六）    3 项
  C. 增量 A/B/C 与 dirty-only（§十七）          3 项
  D. finalize 幂等与 canonical 口径（§十九）    2 项
  E. UI 接线条件（§十四/§十五）                 2 项
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT / "scripts"), str(ROOT / "scripts" / "ai"),
          str(ROOT / "scripts" / "ops"), str(ROOT / "scripts" / "data"),
          str(ROOT / "scripts" / "collectors"), str(ROOT / "scripts" / "clustering")):
    sys.path.insert(0, p)

import c3_analysis as A            # noqa: E402
import c3_localization as L        # noqa: E402
import c3_artifacts as ART         # noqa: E402
import build_ai_views as BAV       # noqa: E402

BJ = timezone(timedelta(hours=8))
AS_OF = "2026-09-19T00:00:00+00:00"


def item(nid, hours_ago, **kw):
    t = datetime.fromisoformat(AS_OF) - timedelta(hours=hours_ago)
    d = {"news_id": nid, "src_id": kw.pop("src_id", ""),
         "observed_at": t.isoformat(), "source_group": kw.pop("source_group", "s1"),
         "source_name": "Src", "event_type": kw.pop("event_type", "armed_conflict"),
         "title_original": kw.pop("title_original", "Armed attack kills three"),
         "summary_original": "Three killed.", "country_cn": kw.pop("country_cn", "乍得"),
         "independent_source_count": kw.pop("independent_source_count", 1),
         "verification_level": "single_source", "origin": kw.pop("origin", "canonical_articles"),
         "title_cn": kw.pop("title_cn", None), "summary_cn": kw.pop("summary_cn", None)}
    d.update(kw)
    return d


class CountryFactPackWindowTest(unittest.TestCase):
    """A. §五"""

    def _pack(self):
        rows = [item("n1", 1), item("n2", 20), item("n3", 30), item("n4", 50),
                item("n5", 70), item("n6", 100), item("n7", 160), item("n8", 200)]
        return A.build_country_fact_pack("乍得", rows, data_as_of=AS_OF)

    def test_01_country_fact_pack_24h_filtered(self):
        p = self._pack()
        w = p["windows"]["24h"]
        self.assertEqual(w["news_count"], 2)                 # 1h, 20h
        self.assertEqual(sorted(w["fact_refs"]), ["n1", "n2"])
        self.assertEqual(w["latest"], (datetime.fromisoformat(AS_OF)
                                       - timedelta(hours=1)).isoformat())

    def test_02_country_fact_pack_72h_filtered(self):
        p = self._pack()
        w = p["windows"]["72h"]
        self.assertEqual(w["news_count"], 5)                 # 1,20,30,50,70
        self.assertEqual(sorted(w["fact_refs"]), ["n1", "n2", "n3", "n4", "n5"])

    def test_03_country_fact_pack_7d_filtered(self):
        p = self._pack()
        w = p["windows"]["7d"]
        self.assertEqual(w["news_count"], 7)                 # 排除 200h
        self.assertNotIn("n8", w["fact_refs"])
        self.assertEqual(p["reference_time"], AS_OF)

    def test_04_country_fact_pack_windows_nested(self):
        p = self._pack()
        self.assertTrue(A.windows_are_nested(p["windows"]))
        n24 = p["windows"]["24h"]["news_count"]
        n72 = p["windows"]["72h"]["news_count"]
        n7 = p["windows"]["7d"]["news_count"]
        self.assertLessEqual(n24, n72)
        self.assertLessEqual(n72, n7)
        # 三窗口不得再共用同一份 news set（C3 的原 bug）
        self.assertNotEqual(n24, n7)
        # 无 data_as_of 时退化到 items 内最新时间，仍保持嵌套
        p2 = A.build_country_fact_pack("乍得", [item("x", 1), item("y", 40), item("z", 200)],
                                       data_as_of=None)
        self.assertTrue(A.windows_are_nested(p2["windows"]))


class LiveEventIdentityTest(unittest.TestCase):
    """B. §六"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="c3r_live_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _live(self):
        return item("NEWS-abc123", 2, src_id="", origin="live_published_events")

    def test_05_live_event_without_article_can_cache_localization(self):
        it = self._live()
        ident = L.display_identity(it)
        self.assertEqual(ident, "NEWS-abc123")           # 无 Article → 用 news_id
        self.assertFalse(L.is_article_identity(ident))
        k = L.cache_key(it)
        ART.write_artifact(self.tmp, "localization", k,
                           {"news_id": "NEWS-abc123", "src_id": "",
                            "display_identity": ident,
                            "title_cn": "武装袭击致三人死亡", "summary_cn": "三人死亡。"},
                           schema_version=L.SCHEMA_VERSION, model=L.DEFAULT_MODEL,
                           prompt_version=L.PROMPT_VERSION, input_hash=L.content_hash(it),
                           status=L.STATUS_FULL, source_fact_refs=["NEWS-abc123"])
        rec = ART.read_artifact(self.tmp, "localization", k)
        self.assertEqual(rec["status"], L.STATUS_FULL)
        self.assertEqual(rec["display_identity"], "NEWS-abc123")
        idx = BAV.localization_index(self.tmp)
        self.assertIn("NEWS-abc123", idx)
        self.assertEqual(idx["NEWS-abc123"]["title_cn"], "武装袭击致三人死亡")

    def test_06_live_event_localization_survives_rebuild(self):
        it = self._live()
        ART.write_artifact(self.tmp, "localization", L.cache_key(it),
                           {"news_id": it["news_id"], "src_id": "", "display_identity": it["news_id"],
                            "title_cn": "中文标题", "summary_cn": "中文摘要"},
                           schema_version=L.SCHEMA_VERSION, model=L.DEFAULT_MODEL,
                           prompt_version=L.PROMPT_VERSION, input_hash=L.content_hash(it),
                           status=L.STATUS_FULL, source_fact_refs=[it["news_id"]])
        vd = os.path.join(self.tmp, "data", "views")
        os.makedirs(vd, exist_ok=True)
        stream = os.path.join(vd, "news_stream.json")
        with io.open(stream, "w", encoding="utf-8") as f:
            json.dump({"items": [
                {"news_id": "NEWS-abc123", "src_id": "", "origin": "live_published_events",
                 "title_original": "x", "title_cn": None, "summary_cn": None},
                {"news_id": "NEWS-withart", "src_id": "ART_1", "origin": "canonical_articles",
                 "title_original": "y", "title_cn": "已有中文", "summary_cn": "已有"},
            ]}, f, ensure_ascii=False)
        out = BAV.merge_into_news_stream(self.tmp, dist_path=os.path.join(self.tmp, "nodist"))
        self.assertEqual(out["merged"], 1)
        doc = json.load(io.open(stream, encoding="utf-8"))
        live = [i for i in doc["items"] if i["news_id"] == "NEWS-abc123"][0]
        art = [i for i in doc["items"] if i["news_id"] == "NEWS-withart"][0]
        self.assertEqual(live["title_cn"], "中文标题")      # artifact 补齐
        self.assertEqual(art["title_cn"], "已有中文")        # Article 优先，不被覆盖
        # 再次重建后依然能补齐（永久缓存，不依赖 Article）
        with io.open(stream, "w", encoding="utf-8") as f:
            json.dump({"items": [{"news_id": "NEWS-abc123", "src_id": "",
                                  "origin": "live_published_events", "title_cn": None}]},
                      f, ensure_ascii=False)
        BAV.merge_into_news_stream(self.tmp, dist_path=os.path.join(self.tmp, "nodist"))
        doc2 = json.load(io.open(stream, encoding="utf-8"))
        self.assertEqual(doc2["items"][0]["title_cn"], "中文标题")

    def test_07_live_event_localization_not_recalled_when_unchanged(self):
        it = self._live()
        k = L.cache_key(it)
        ART.write_artifact(self.tmp, "localization", k,
                           {"news_id": it["news_id"], "src_id": "",
                            "display_identity": it["news_id"], "title_cn": "t", "summary_cn": "s"},
                           schema_version=L.SCHEMA_VERSION, model=L.DEFAULT_MODEL,
                           prompt_version=L.PROMPT_VERSION, input_hash=L.content_hash(it),
                           status=L.STATUS_FULL, source_fact_refs=[it["news_id"]])
        rec = ART.read_artifact(self.tmp, "localization", k)
        # 未变化 → 命中缓存（不 retryable），因此不会再次调用
        self.assertEqual(rec["input_hash"], L.content_hash(it))
        self.assertFalse(rec.get("retryable"))
        # 内容变化 → 缓存键与指纹都变 → 必须重新处理
        it2 = dict(it, title_original="Armed attack kills three people")
        self.assertNotEqual(L.cache_key(it2), k)
        self.assertNotEqual(L.content_hash(it2), L.content_hash(it))


class IncrementalABC(unittest.TestCase):
    """C. §十七（Run A 增量 / Run B 幂等 / Run C dirty-only）"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="c3r_inc_")
        d = Path(self.tmp) / "data"
        for sub in ("canonical", "views"):
            (d / sub).mkdir(parents=True, exist_ok=True)
        (Path(self.tmp) / "dist" / "data").mkdir(parents=True, exist_ok=True)
        items = [item("NEWS-%d" % i, i, title_original="Armed attack kills %d" % (i + 1),
                      title_cn=None, summary_cn=None) for i in range(10)]
        self._w(d / "views" / "news_stream.json",
                {"counts": {"admitted": 10, "fresh_24h": 10, "fresh_7d": 10}, "items": items})
        self._w(d / "canonical" / "articles.json", {"items": []})
        self._w(d / "canonical" / "event_clusters.json", {"items": [
            {"event_id": "EVT_1", "independent_source_count": 2, "quality_gate_passed": True,
             "country_cn": "乍得", "event_time": "2026-09-18T10:00:00+08:00",
             "title_original": "Attack kills three"}]})
        self._w(d / "status.json", {"data_as_of": AS_OF})
        self._w(Path(self.tmp) / "dist" / "data" / "site_overview.json", {"countries": []})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def _w(p, o):
        os.makedirs(os.path.dirname(str(p)), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(o, f, ensure_ascii=False)

    def _run(self, provider="stub:ok"):
        out = os.path.join(self.tmp, "run.json")
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "ops" / "c3_run.py"),
                            "--root", self.tmp, "--provider", provider, "--out", out],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        return json.load(io.open(out, encoding="utf-8"))

    def test_08_run_a_incremental_picks_up_new_news(self):
        a = self._run()
        self.assertGreater(a["ai_calls_localization"], 0)
        self.assertEqual(a["localization"]["target"], 10)
        # 新增一条 → Run A' 只处理新增
        p = Path(self.tmp) / "data" / "views" / "news_stream.json"
        doc = json.load(io.open(p, encoding="utf-8"))
        doc["items"].append(item("NEWS-new", 1, title_original="Flood displaces 500 in Beira",
                                 title_cn=None, summary_cn=None))
        doc["counts"]["admitted"] = 11
        self._w(p, doc)
        b = self._run()
        self.assertGreater(b["ai_calls_localization"], 0)
        self.assertLessEqual(b["ai_calls_localization"], a["ai_calls_localization"])

    def test_09_run_b_identical_zero_new_calls(self):
        self._run()
        b = self._run()
        self.assertEqual(b["ai_calls_localization"], 0)
        self.assertEqual(b["ai_calls_total"], 0)

    def test_10_run_c_only_dirty_components_reprocessed(self):
        self._run()
        # 改变 home fact pack（新增一个国家）→ 只有 homepage 应为 dirty
        ov = Path(self.tmp) / "dist" / "data" / "site_overview.json"
        self._w(ov, {"countries": [{"country_cn": "乍得", "risk_level": 4}]})
        c = self._run()
        self.assertEqual(c["ai_calls_localization"], 0)      # 新闻未变
        self.assertGreaterEqual(c["ai_calls_homepage"], 0)   # 仅事实包变化者重算
        self.assertLessEqual(c["ai_calls_homepage"], 1)


class FinalizeIdempotencyTest(unittest.TestCase):
    """D. §十九"""

    def test_11_recluster_from_article_store_is_idempotent(self):
        from clustering.event_clusterer import cluster_events
        from countries import iso2_for
        arts = [{"article_id": "ART_%016x" % i, "published_at": "2026-09-1%dT10:00:00+08:00" % (i % 9 + 1),
                 "canonical_url": "https://x/%d" % i, "source_id": "s%d" % (i % 3),
                 "source_group": "g%d" % (i % 3), "event_country": "乍得",
                 "title_original": "Armed attack kills three in N'Djamena",
                 "summary_original": "Three killed."} for i in range(24)]
        ev = [{"event_id": "EVT_%016x" % i, "title_original": a["title_original"],
               "summary_original": a["summary_original"], "country_code": iso2_for("乍得"),
               "country_cn": "乍得", "event_type": "armed_conflict",
               "event_time": a["published_at"], "canonical_url": a["canonical_url"],
               "source_id": a["source_id"], "source_group": a["source_group"],
               "article_id": a["article_id"], "article_ids": [],
               "quality_gate_passed": True} for i, a in enumerate(arts)]
        c1, s1 = cluster_events(ev)
        ms1 = sum(1 for c in c1 if (c.get("independent_source_count") or 0) >= 2)
        # 再跑一次同样的 article 级输入 → 结果必须一致（幂等）
        c2, s2 = cluster_events(ev)
        ms2 = sum(1 for c in c2 if (c.get("independent_source_count") or 0) >= 2)
        self.assertEqual(ms1, ms2)
        self.assertEqual(s1.get("merged_pairs"), s2.get("merged_pairs"))
        # 反例：在**已合并**的 cluster 上二次聚类会退化（merged_pairs=0）
        c3, s3 = cluster_events(c1)
        self.assertEqual(s3.get("merged_pairs"), 0)

    def test_12_canonical_threshold_unchanged_and_count_recorded(self):
        src = io.open(ROOT / "scripts" / "data" / "normalizers.py", encoding="utf-8").read()
        self.assertIn("if independent_source_count >= 2:", src)
        pre = None
        pre_p = os.path.join(r"C:\Users\kenan\WorkBuddy\2026-09-12-05-20-26",
                             "c3_canonical_regression_preflight.json")
        if os.path.exists(pre_p):
            pre = json.load(io.open(pre_p, encoding="utf-8"))
        if pre:
            self.assertEqual(pre["canonical_regression"], False)
            self.assertEqual(pre["canonical_threshold_changed"], False)
            self.assertEqual(pre["numbers"]["recomputed_from_article_store"], 6)


class UIGatingTest(unittest.TestCase):
    """E. §十四/§十五：AI 文本只在合法状态出现"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="c3r_ui_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_13_homepage_ai_view_hides_non_full_payload(self):
        doc, _p = BAV.build(self.tmp)
        self.assertIsNone(doc.get("homepage"))
        ART.write_artifact(self.tmp, "homepage_analysis", "current",
                           A.deterministic_fallback("homepage", {}),
                           schema_version=A.SCHEMA_VERSION, model="m",
                           prompt_version=A.HOMEPAGE_PROMPT_VERSION, input_hash="h",
                           status=A.STATUS_FALLBACK, source_fact_refs=["homepage"])
        doc2, _ = BAV.build(self.tmp)
        self.assertEqual(doc2["homepage"]["status"], A.STATUS_FALLBACK)
        self.assertFalse((doc2["homepage"].get("executive_assessment") or "").strip())
        # 公开视图不得泄漏实现细节
        blob = json.dumps(doc2, ensure_ascii=False).lower()
        for banned in ("deepseek", "api_key", "prompt_version", "input_hash",
                       "gate_reasons", "token", "model"):
            self.assertNotIn(banned, blob)

    def test_14_country_ai_view_low_data_is_honest(self):
        ART.write_artifact(self.tmp, "country_analysis", "乍得",
                           A.low_data_placeholder("country"),
                           schema_version=A.SCHEMA_VERSION, model="m",
                           prompt_version=A.COUNTRY_PROMPT_VERSION, input_hash="h",
                           status=A.STATUS_LOW_DATA, source_fact_refs=["乍得"])
        doc, _ = BAV.build(self.tmp)
        c = doc["country_analysis"]["乍得"]
        self.assertEqual(c["status"], A.STATUS_LOW_DATA)
        self.assertIn("数据不足", c["executive_assessment"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
