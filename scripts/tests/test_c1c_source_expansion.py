#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c1c_source_expansion.py — C1C §二十二 正式测试（10 项）。

  A. Source Admission（§十/§十一）        4 项
  B. Article / News Stream 链路（§十二/§十六）2 项
  C. Source Identity / Corroboration（§八/§十九）2 项
  D. GDELT 定位与阈值不变量（§十四/§十九） 2 项
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT / "scripts"), str(ROOT / "scripts" / "data"),
          str(ROOT / "scripts" / "collectors"), str(ROOT / "tools" / "c1a")):
    sys.path.insert(0, p)

from source_admission import (admit, build_record, direct_vs_gdelt_counts,  # noqa: E402
                              ENABLED, REJECTED, UNVERIFIABLE)
from data.source_identity import source_identity, independent_source_count  # noqa: E402
from country_runner import relevance_stage1  # noqa: E402


def pub(domain="premiumtimesng.com", name="Premium Times", country="尼日利亚",
        lang="en", stype="local_media", entries=15, age=3.0, latest="2026-09-18T14:19:43Z",
        url_ex=1.0, pub_ex=1.0, xml=True, hp=200, feed_status=200, samples=None,
        feed_error=None, best=True):
    bf = None
    if best:
        bf = {"feed_url": "https://%s/feed" % domain, "reachable": True,
              "http_status": feed_status, "xml_valid": xml, "entry_count": entries,
              "latest_entry": latest, "age_hours_of_latest": age,
              "url_extraction": url_ex, "published_extraction": pub_ex,
              "duplicate_ratio": 0.0, "fetch_error": feed_error,
              "sample_titles": samples or ["Armed attack kills three in Kaduna"]}
    return {"domain": domain, "source_name": name, "country": country, "language": lang,
            "source_type": stype, "homepage_status": hp, "homepage_error": None,
            "discovered_feeds": ["https://%s/feed" % domain],
            "validated_feeds": [bf] if bf else [], "best_feed": bf, "priority": "P1",
            "batch": "test"}


class AdmissionTest(unittest.TestCase):
    """A. Source Admission（§十/§十一）"""

    def test_01_new_source_requires_validation(self):
        """未经验证的候选不得 ENABLED（无 feed / 无发现证据）"""
        d, reasons, bf = admit(pub(best=False))
        self.assertEqual(d, REJECTED)
        self.assertTrue(any(r.startswith("NO_PARSABLE_FEED") for r in reasons))
        # 可达但解析不出条目
        p2 = pub(entries=0)
        d2, r2, _ = admit(p2)
        self.assertEqual(d2, REJECTED)

    def test_02_source_recent_content_required(self):
        """最新条目超出窗口（>30 天）必须 REJECTED，并给出具体原因"""
        d, reasons, _ = admit(pub(entries=10, age=24 * 40))
        self.assertEqual(d, REJECTED)
        self.assertTrue(any(r.startswith("NO_RECENT_CONTENT") for r in reasons), reasons)
        # 条目过少同样拒绝
        d2, r2, _ = admit(pub(entries=2, age=1.0))
        self.assertEqual(d2, REJECTED)
        self.assertTrue(any("entries=2" in r for r in r2), r2)

    def test_03_rejected_source_not_enabled(self):
        """REJECTED 候选不得产出 enabled 记录；环境不可验证必须单列"""
        bad = pub(domain="vanguardngr.com", name="Vanguard", best=False)
        bad["homepage_status"] = 403
        bad["homepage_error"] = "HTTP_403"
        d, reasons, bf = admit(bad)
        self.assertEqual(d, REJECTED)
        self.assertTrue(any("NOT_REACHABLE" in r for r in reasons), reasons)
        self.assertIsNone(bf)
        # 环境噪声 → 既不算通过也不算失败
        env = pub(domain="rfi.fr", best=False)
        env["homepage_error"] = UNVERIFIABLE
        d2, _, _ = admit(env)
        self.assertEqual(d2, UNVERIFIABLE)

    def test_04_enabled_record_is_schema_valid_and_has_identity(self):
        """ENABLED 记录必须 schema 合法，且带 publisher_identity_id"""
        from data.repository import SCHEMA_DIR
        from data.schema_validator import validate_instance, load_schema
        from data.source_rules import validate_source_business_rules
        d, reasons, bf = admit(pub())
        self.assertEqual(d, ENABLED, reasons)
        rec = build_record(pub(), bf)
        sch = load_schema("source.schema.json", SCHEMA_DIR)
        errs = validate_instance(rec, sch) + validate_source_business_rules(rec)
        self.assertEqual(errs, [], errs)
        self.assertTrue(rec["publisher_identity_id"].startswith("SI_"))
        self.assertEqual(rec["legacy_payload"]["collection_method"], "rss")
        self.assertTrue(rec["enabled"])


class DirectSourceChainTest(unittest.TestCase):
    """B. Article / News Stream 链路（§十二/§十六）"""

    def test_05_feed_does_not_ingest_sports_by_default(self):
        """综合媒体的体育/娱乐条目默认不得进 ASIP News（相关性门槛不降低）"""
        for t in ("Mozambique football team wins regional cup",
                  "Nigeria: Nollywood actress wins award",
                  "Kenya: fashion week opens in Nairobi",
                  "Sudan: music festival attracts thousands"):
            rel, score, matched, why = relevance_stage1(t)
            self.assertFalse(rel, "sports/entertainment must not be relevant: %s" % t)
        # 同一媒体同时含安全信号时仍判相关（不误伤）
        rel2, _, _, _ = relevance_stage1(
            "Kenya: protest in Nairobi turns violent, police fire tear gas")
        self.assertTrue(rel2)

    def test_06_direct_source_persists_articles(self):
        """直接来源的文章必须经 Article Corpus 持久化（不得只停留在 runner）"""
        from data.article_persistence import persist_collected_articles
        tmp = tempfile.mkdtemp(prefix="c1c_ds_")
        try:
            os.makedirs(os.path.join(tmp, "data", "canonical"), exist_ok=True)
            with io.open(os.path.join(tmp, "data", "sources.json"), "w",
                         encoding="utf-8") as f:
                json.dump({"schema_version": "2.0", "pipeline_version": 2,
                           "run_id": "t", "sources": []}, f)
            art = {
                "source_id": "ng_premiumtimes", "source_name": "Premium Times",
                "source_country": "尼日利亚", "source_type": "local_media",
                "language": "en", "discovery_method": "rss",
                "feed_url": "https://premiumtimesng.com/feed",
                "article_url": "https://premiumtimesng.com/x",
                "canonical_url": "https://premiumtimesng.com/x",
                "original_title": "Armed attack kills three in Kaduna",
                "original_body": "Corps " * 60, "original_summary": "Summary",
                "published_at_original": "2026-09-18 10:00:00",
                "published_at_beijing": "2026-09-18 10:00:00",
                "collected_at_beijing": "2026-09-18T20:00:00+08:00",
                "article_word_count": 60, "extraction_quality": "full_body",
                "fetch_status": "ok", "body_status": "full_body",
                "fetch_http_status": 200,
                "_country": {"decision": "nigeria"}, "_relevant": True, "_rel_score": 0.9,
                "_event_type": "armed_conflict",
            }
            st = persist_collected_articles(tmp, [art], "20260918T230001+0800_c1c001",
                                            verbose=False)
            self.assertEqual(st["new_articles_persisted"], 1, st)
            p = os.path.join(tmp, "data", "canonical", "articles.json")
            items = json.load(io.open(p, encoding="utf-8"))["items"]
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["source_id"], "ng_premiumtimes")
            # 采集器本地时间必须已归一为 RFC3339
            self.assertTrue(items[0]["published_at"].startswith("2026-09-18T10:00:00"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_07_direct_sources_feed_news_stream(self):
        """直接来源的条目必须能通过 News Admission Gate 进入 news stream"""
        import importlib.util as ilu
        bs = ROOT / "tools" / "c1a" / "build_news_stream.py"
        spec = ilu.spec_from_file_location("c1a_bs_test", str(bs))
        mod = ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        g = mod.Gate()
        cand = {"src_id": "ng_premiumtimes|https://premiumtimesng.com/x",
                "source_url": "https://premiumtimesng.com/x",
                "observed_at": "2026-09-18T14:19:43Z",
                "title_original": "Armed attack kills three in Kaduna",
                "title_cn": "", "country_iso2": "NG", "quarantined": False,
                "dedup_key": mod.sha1("u", mod.norm_url("https://premiumtimesng.com/x"))}
        out = g.admit(cand)
        self.assertIsNotNone(out, "direct source item must be admitted")
        # 重复条目必须被拦
        self.assertIsNone(g.admit(dict(cand)))
        self.assertEqual(g.rejects["REJ_DUPLICATE"], 1)
        # 缺时间/缺 URL 的条目必须被拦（不得绕过 gate）
        for bad in ({"src_id": "x", "source_url": "", "observed_at": "2026-09-18T00:00:00Z",
                     "title_original": "t", "country_iso2": "NG", "dedup_key": "d1"},
                    {"src_id": "y", "source_url": "https://a/b", "observed_at": "",
                     "title_original": "t", "country_iso2": "NG", "dedup_key": "d2"}):
            self.assertIsNone(g.admit(bad))


class IdentityAndGdeltTest(unittest.TestCase):
    """C/D. Source Identity、Corroboration 与 GDELT 定位（§八/§十四/§十九）"""

    def test_08_same_publisher_multiple_feeds_one_identity(self):
        """同一 publisher 的多个 feed：config 可多条，publisher_identity_id 必须相同"""
        a = pub(domain="punchng.com", name="Punch")
        b = pub(domain="punchng.com", name="Punch")
        ra = build_record(a, admit(a)[2])
        rb = build_record(b, admit(b)[2])
        self.assertEqual(ra["publisher_identity_id"], rb["publisher_identity_id"])
        ic = independent_source_count([
            {"source_id": ra["source_id"], "source_name": ra["source_name"],
             "article_url": "https://punchng.com/a"},
            {"source_id": rb["source_id"], "source_name": rb["source_name"],
             "article_url": "https://punchng.com/b"},
        ])
        self.assertEqual(ic["independent_source_count"], 1)

    def test_09_multisource_corroboration_uses_publisher_identity(self):
        """事件印证按 publisher identity 计数：同 publisher 多 feed 不算多来源"""
        from clustering.event_clusterer import cluster_events
        def ev(uid, title, src, url, tt):
            return {"event_id": uid, "title_original": title, "country_code": "NG",
                    "event_type": "armed_conflict", "event_time": tt,
                    "canonical_url": url, "source_id": src, "source_name": src,
                    "article_id": "ART_" + uid}
        t1 = "Armed attack kills three in Kaduna"
        t2 = "Armed attack kills three people in Kaduna state"
        # 同 publisher（同域名）两条 → independent_source_count 必须为 1
        same, st_same = cluster_events([
            ev("E1", t1, "ng_punch_a", "https://punchng.com/1", "2026-09-18 08:00:00"),
            ev("E2", t2, "ng_punch_b", "https://punchng.com/2", "2026-09-18 09:00:00")])
        self.assertEqual(st_same["multi_source_clusters"], 0)
        # 两家不同 publisher → isc=2
        diff, st_diff = cluster_events([
            ev("F1", t1, "ng_punch", "https://punchng.com/1", "2026-09-18 08:00:00"),
            ev("F2", t2, "ng_premiumtimes", "https://premiumtimesng.com/2",
               "2026-09-18 09:00:00")])
        self.assertEqual(st_diff["multi_source_clusters"], 1)
        m = [c for c in diff if (c.get("independent_source_count") or 0) >= 2]
        self.assertEqual(len(m[0]["article_ids"]), 2)

    def test_10_gdelt_not_counted_as_unique_publisher_configs(self):
        """68 个 GDELT config 不得当作 68 个独立 publisher"""
        srcs = []
        for dom in ("reuters.com", "news.cn", "apnews.com"):
            for cc, cn in (("chad", "乍得"), ("niger", "尼日尔")):
                srcs.append({
                    "source_id": "intl_%s_%s" % (dom.split(".")[0], cc),
                    "enabled": True,
                    "legacy_payload": {"collection_method": "gdelt_search",
                                       "query": "domain:%s %s" % (dom, cn)}})
        # 两个真正的直接来源
        srcs.append({"source_id": "ng_punch", "enabled": True,
                     "legacy_payload": {"collection_method": "rss",
                                        "feed_url": "https://punchng.com/feed/"}})
        srcs.append({"source_id": "so_hiiraan", "enabled": True,
                     "legacy_payload": {"collection_method": "rss",
                                        "feed_url": "https://hiiraan.com/news.xml"}})
        c = direct_vs_gdelt_counts(srcs)
        self.assertEqual(c["GDELT_CONFIG_COUNT"], 6)
        self.assertEqual(c["GDELT_DISTINCT_PUBLISHER_DOMAINS"], 3)
        self.assertEqual(c["DIRECT_SOURCE_COUNT"], 2)
        self.assertNotEqual(c["GDELT_CONFIG_COUNT"], c["GDELT_DISTINCT_PUBLISHER_DOMAINS"])

    def test_11_canonical_threshold_unchanged(self):
        """canonical 阈值必须仍为 independent_source_count>=2 + quality_gate_passed"""
        from data.normalizers import derive_verification_level
        self.assertNotEqual(derive_verification_level(
            {}, source_type="local_media", independent_source_count=1), "cross_verified")
        self.assertEqual(derive_verification_level(
            {}, source_type="local_media", independent_source_count=2), "cross_verified")
        # 扩源不得改变阈值常量本身
        import io as _io
        src = _io.open(os.path.join(ROOT, "scripts", "data", "normalizers.py"),
                       encoding="utf-8").read()
        self.assertIn("if independent_source_count >= 2:", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
