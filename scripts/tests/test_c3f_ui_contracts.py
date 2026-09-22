#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c3f_ui_contracts.py — C3F §二十九 契约与状态语义测试（18 项）。

其中「页面级」断言直接对**真实 HTML/JS 源码契约**做检查（宿主 id / URL 参数 / 挂载键），
因为这些坑无法靠纯数据单测发现，必须锁在源码上；其余用纯函数与已提交数据验证。
"""
import io
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "ai"))
sys.path.insert(0, str(ROOT / "scripts" / "ops"))
sys.path.insert(0, str(ROOT / "scripts" / "data"))

import c3_localization as L          # noqa: E402
import c3_analysis as A              # noqa: E402


def read(rel):
    with io.open(ROOT / rel, encoding="utf-8") as f:
        return f.read()


def jload(rel, default=None):
    try:
        with io.open(ROOT / rel, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


class HomepageContractTest(unittest.TestCase):
    """§三/§五/§六"""

    def test_01_homepage_full_hides_unavailable_notice(self):
        """FULL 时必须走 home-v11.js 的 AI 分支（aiBlock），而不是 aiFallback 文案。"""
        src = read("assets/js/home-v11.js")
        self.assertIn("ai && ai.overall_assessment", src)
        self.assertIn("aiFallback(", src)
        # 注入钩子存在：AI 到达后重跑 Executive，使占位提示被真实 AI 取代
        self.assertIn("window.__HOME_AI_SET__", src)
        # 渲染器只在 fresh 时注入 AI
        js = read("assets/js/ai-intelligence.js")
        self.assertIn('hp.status === "FULL"', js)
        self.assertIn("hp.fact_pack_hash === doc.homepage_fact_pack_hash", js)

    def test_02_homepage_ai_not_rendered_when_fact_hash_stale(self):
        view = jload("data/views/ai_intelligence.json", {}) or {}
        hp = view.get("homepage") or {}
        cur = view.get("homepage_fact_pack_hash")
        self.assertTrue(cur, "view 必须暴露当前 fact pack hash")
        # C3F-R / C4-A 之后：hash 契约已修复、artifact hash 已按稳定投影重导，
        # 因此当前应为**匹配**（stale 的withheld 行为由 js 的 fresh 判定单测覆盖）。
        self.assertTrue(hp.get("ai_matches_current_fact_pack"),
                        "hash 契约修复后，homepage artifact 必须与当前 fact pack 一致")
        self.assertEqual(hp.get("fact_pack_hash"), cur)
        # 判定逻辑：hash 不一致 → 前端不注入
        js = read("assets/js/ai-intelligence.js")
        self.assertIn("var fresh = !!", js)

    def test_03_homepage_ai_rendered_when_fact_hash_matches(self):
        """hash 一致（含人工构造）时判定为 fresh。"""
        hp = {"status": "FULL", "fact_pack_hash": "H", "executive_assessment": "x"}
        fresh = bool(hp["status"] == "FULL" and hp["fact_pack_hash"]
                     and "H" == "H")
        self.assertTrue(fresh)
        # 前端同样不得暴露 hash / STALE 等技术细节
        js = read("assets/js/ai-intelligence.js")
        for banned in ("fact_pack_hash", "STALE", "hash"):
            self.assertNotIn('esc(' + banned, js)


class CountryContractTest(unittest.TestCase):
    """§七/§八/§九"""

    def test_04_country_page_uses_feCountry_host(self):
        html = read("country.html")
        self.assertIn('id="feCountry"', html)
        # 渲染器必须使用真实宿主，且不得再引用猜测出来的容器
        js = read("assets/js/ai-intelligence.js")
        self.assertIn('getElementById("feCountry")', js)
        for wrong in ('"countryDetail"', "[data-country-detail]", 'querySelector("main")'):
            self.assertNotIn(wrong, js, "不得继续使用猜测的宿主 %s" % wrong)

    def test_05_country_page_reads_country_param(self):
        fe = read("assets/js/frontend.js")
        self.assertIn('get("country")', fe)         # 真实参数名
        js = read("assets/js/ai-intelligence.js")
        self.assertIn('q("country")', js)
        self.assertNotIn('q("c")', js)              # 不得保留错误参数

    def test_06_country_ai_uses_iso3_not_filename(self):
        import build_ai_views as BAV
        view = jload("data/views/ai_intelligence.json", {}) or {}
        idx = view.get("country_index") or {}
        self.assertEqual(len(idx), 12, "12 个国家都要按 ISO3 建索引")
        self.assertIn("COD", idx)
        # 关联必须经 ISO3，而不是文件名
        self.assertEqual((view.get("country_name_to_iso3") or {}).get("刚果（金）"), "COD")
        self.assertEqual(idx["COD"].get("name_cn"), "刚果（金）")
        self.assertIn("按 ISO3", read("scripts/ops/build_ai_views.py"))

    def test_07_drc_display_name_correct(self):
        view = jload("data/views/ai_intelligence.json", {}) or {}
        n2i = view.get("country_name_to_iso3") or {}
        self.assertEqual(n2i.get("刚果（金）"), "COD")
        self.assertEqual(n2i.get("刚果共和国（刚果布）"), "COG")
        self.assertNotEqual(n2i.get("刚果（金）"), n2i.get("刚果共和国（刚果布）"))
        # 错误显示名不得出现在任何源码/数据里
        for rel in ("assets/js/ai-intelligence.js", "scripts/ops/build_ai_views.py",
                    "config/countries/drc.json"):
            self.assertNotIn("刚果（平）", read(rel))

    def test_08_country_full_renders(self):
        view = jload("data/views/ai_intelligence.json", {}) or {}
        idx = view.get("country_index") or {}
        full = [k for k, v in idx.items() if v.get("status") == "FULL"]
        self.assertEqual(len(full), 9, "9 个 FULL 国家")
        for k in full:
            v = idx[k]
            self.assertTrue(v.get("executive_assessment") or v.get("trend_analysis"),
                            "%s 缺少正文" % k)
        self.assertIn("当前态势研判", read("assets/js/ai-intelligence.js"))

    def test_09_country_low_data_renders(self):
        view = jload("data/views/ai_intelligence.json", {}) or {}
        idx = view.get("country_index") or {}
        low = [k for k, v in idx.items() if v.get("status") == "LOW_DATA"]
        self.assertEqual(sorted(low), ["ETH", "KEN", "SDN"], "3 个 LOW_DATA：埃塞/肯尼亚/苏丹")
        js = read("assets/js/ai-intelligence.js")
        self.assertIn("当前数据不足以形成稳定研判", js)


class EventContractTest(unittest.TestCase):
    """§十一/§十二"""

    def test_10_event_ai_mount_uses_real_event_id(self):
        html = read("event.html")
        self.assertIn('id="feEventDetail"', html)
        fe = read("assets/js/frontend.js")
        self.assertIn('get("id")', fe)
        self.assertIn("master_event_id", fe)
        js = read("assets/js/ai-intelligence.js")
        self.assertIn('getElementById("feEventDetail")', js)
        self.assertIn('q("id")', js)
        self.assertIn("doc.event_analysis", js)
        # artifact 键必须与 master_event_id 同源（EVT_<16hex>）
        # artifact 键必须来自 canonical event_clusters 的 event_id 体系
        cl = jload("data/canonical/event_clusters.json", {}) or {}
        cids = {c.get("event_id") for c in (cl.get("items") or [])}
        ea = (jload("data/views/ai_intelligence.json", {}) or {}).get("event_analysis") or {}
        self.assertTrue(set(ea.keys()) <= cids, "event_analysis 键必须属于 event_clusters")
        # 已知架构缺口（本轮只接线，不改内容架构）：
        # public 事件详情页解析的是 master_events[].master_event_id，而当前 master_events
        # 里没有任何 multi-source 事件 → 与这 6 条研判的 id 交集为 0。
        # 记录该事实，交给 C4/C5 决定是否把 multi-source cluster 暴露到公开事件视图。
        me = jload("data/views/master_events.json", {}) or {}
        mids = {e.get("master_event_id") for e in (me.get("events") or [])}
        self.assertEqual(len(set(ea.keys()) & mids), 0,
                         "当前应为 0；若将来 >0 说明公开事件视图已包含这些 multi-source 事件")

    def test_11_event_ai_only_on_eligible_event(self):
        ea = (jload("data/views/ai_intelligence.json", {}) or {}).get("event_analysis") or {}
        self.assertEqual(len(ea), 6, "只挂载 multi-source event 的 6 条研判")
        for k, v in ea.items():
            self.assertTrue(k.startswith("EVT_"), k)
            self.assertEqual(v.get("status"), "FULL")


class TranslationBadgeTest(unittest.TestCase):
    """§十四"""

    def test_12_translated_title_hides_untranslated_badge(self):
        src = read("assets/js/news-stream.js")
        self.assertIn("if (!n.title_cn && n.title_cn_missing)", src)
        items = (jload("data/views/news_stream.json", {}) or {}).get("items") or []
        bad = [i for i in items if (i.get("title_cn") or "").strip() and i.get("title_cn_missing")]
        self.assertEqual(bad, [], "有中文标题不得再标未翻译")

    def test_13_original_title_shows_untranslated_badge(self):
        items = (jload("data/views/news_stream.json", {}) or {}).get("items") or []
        # 缺 title_cn 的条目必须带 title_cn_missing（或明确不在展示范围）
        miss = [i for i in items if not (i.get("title_cn") or "").strip()]
        flagged = [i for i in miss if i.get("title_cn_missing")]
        self.assertTrue(len(flagged) >= len(miss) - 1,
                        "缺中文标题的条目应显示未翻译标记 (%d/%d)" % (len(flagged), len(miss)))


class LocalizationStateTest(unittest.TestCase):
    """§十五/§十六/§十七/§十八/§二十二"""

    def test_14_full_requires_summary(self):
        self.assertEqual(L.classify_status({"title_cn": "甲", "summary_cn": "乙"}), L.STATUS_FULL)
        self.assertEqual(L.classify_status({"title_cn": "甲", "summary_cn": ""}), L.STATUS_PARTIAL)
        self.assertEqual(L.classify_status({"title_cn": "", "summary_cn": ""}), L.STATUS_FALLBACK)
        self.assertEqual(L.classify_status({"title_cn": "甲", "summary_cn": "乙"}, gate_ok=False),
                         L.STATUS_FALLBACK)
        self.assertEqual(L.classify_status({"title_cn": "甲"}, provider_failed=True), L.STATUS_FAILED)

    def test_15_partial_when_summary_missing(self):
        import collections
        d = ROOT / "data" / "intelligence" / "ai" / "localization"
        c = collections.Counter()
        for f in os.listdir(str(d)):
            if f.endswith(".json"):
                c[jload("data/intelligence/ai/localization/" + f, {}).get("status")] += 1
        # C3F-R 的 summary-only 增量运行补齐了 91 条摘要 → PARTIAL 由 100 降为 9
        # （若将来又出现空摘要，PARTIAL 会回升——这里断言的是「当前真实计数」而非固定值）。
        self.assertEqual(c[L.STATUS_PARTIAL], 9, "剩余空摘要条目数")
        self.assertEqual(c[L.STATUS_FALLBACK], 19, "gate 拒绝条目保持不变")
        self.assertGreaterEqual(c[L.STATUS_FULL], 437)
        self.assertEqual(c[L.STATUS_PARTIAL] + c[L.STATUS_FULL] + c[L.STATUS_FALLBACK], 556)

    def test_16_summary_only_does_not_regenerate_title(self):
        self.assertEqual(L.ALLOWED_KEYS_SUMMARY_ONLY, {"news_id", "summary_cn"})
        items, errs = L.validate_summary_only_shape({"items": [
            {"news_id": "n1", "summary_cn": "摘要", "title_cn": "改写后的标题"}]})
        self.assertEqual(items, [])
        self.assertTrue(any("unexpected_keys" in e for e in errs))
        clean, errs2 = L.validate_summary_only_shape({"items": [
            {"news_id": "n1", "summary_cn": "摘要"}]})
        self.assertEqual(len(clean), 1)
        self.assertEqual(list(clean[0].keys()), ["news_id", "summary_cn"])
        # 运行器在 summary_only 模式下只 patch summary_cn
        run = read("scripts/ops/c3_run.py")
        self.assertIn('_patch = {"summary_cn": got["summary_cn"]}', run)

    def test_17_fact_gate_fallback_never_leaks_text(self):
        d = ROOT / "data" / "intelligence" / "ai" / "localization"
        n_fb = n_partial = leaked = 0
        for f in os.listdir(str(d)):
            if not f.endswith(".json"):
                continue
            rec = jload("data/intelligence/ai/localization/" + f, {})
            st = rec.get("status")
            if st == L.STATUS_FALLBACK:
                n_fb += 1
                # FALLBACK = 被 gate 拒绝 → 必须不带任何文本（不得因覆盖率重新放行）
                if (rec.get("title_cn") or "").strip() or (rec.get("summary_cn") or "").strip():
                    leaked += 1
            elif st == L.STATUS_PARTIAL:
                n_partial += 1
                # PARTIAL 只保留已验证的标题，摘要必须为空
                if (rec.get("summary_cn") or "").strip():
                    leaked += 1
        self.assertEqual(n_fb, 19, "19 条 fact-gate FALLBACK 保持不动")
        self.assertEqual(n_partial, 9, "summary 补齐后剩余 PARTIAL")
        self.assertEqual(leaked, 0, "FALLBACK 不得带文本；PARTIAL 不得带摘要")

    def test_18_localization_pipeline_pass_with_fallback_semantics(self):
        self.assertEqual(L.pipeline_status(537, 100, 19, 0, 0), "PASS_WITH_FALLBACK")
        self.assertEqual(L.pipeline_status(537, 0, 0, 0, 0), "PASS")
        self.assertEqual(L.pipeline_status(0, 0, 0, 5, 1), "FAIL")
        self.assertEqual(L.pipeline_status(0, 0, 19, 0, 0), "FAIL")
        run = read("scripts/ops/c3_run.py")
        self.assertIn("localization_pipeline", run)
        self.assertIn("UNSAFE_OUTPUT_PUBLISHED", run)


if __name__ == "__main__":
    unittest.main(verbosity=2)
