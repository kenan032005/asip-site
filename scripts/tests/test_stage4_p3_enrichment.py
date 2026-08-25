#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 第三执行包 — 工程验证测试（§十 本轮相关，不依赖内容执行）。

覆盖：
- P1 Prompt v1.1：config/prompts/stage4_event_enrichment_v1_1.md 版本=1.1.0，
  三类新规则（数字与单位 / 指控声称 / security_relevance 分级）齐全；v1 未变（1.0.0）。
- P2 Bug 修复回归：
  * enqueue_event 索引条目含 event_id（write_handoff 不再输出 event=None）；
  * _load_canonical_eligible 读取 data/canonical/quarantine.json（含 legacy id 映射）。
- P3 active 结果选择：prompt_version=1.1.0 + succeeded + 排除 DeepSeek 试跑结果。
- P4 Public 注入（apply_enrichment 纯函数）：
  字段注入白名单 / 无结果回退 / review_before_activation 跳过 / orphan 阻断 /
  Public⊆Canonical 校验。
- P5 前端 fallback：common.js / index.html / country.html / event.html
  含 title_zh→title_cn→title_original fallback 链；详情页保留原文标题/AI 标识。
- P6 AI runtime isolation：build_site 白名单不含 data/ai；.gitignore 覆盖 data/ai。
"""

import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "ai"))

from ai.prompt_contract import load_prompt_contract
from ai.hy3_stage4_provider import Hy3Stage4Provider
from ai.enrichment_eligibility import eligibility_status
from stage4_apply_enrichment import (
    apply_enrichment, select_active_result, REVIEW_BEFORE_ACTIVATION,
    AI_SEMANTIC_FIELDS, AI_META_FIELDS,
)

V1_PATH = os.path.join(ROOT, "config", "prompts", "stage4_event_enrichment_v1.md")
V11_PATH = os.path.join(ROOT, "config", "prompts", "stage4_event_enrichment_v1_1.md")


def mk_result(event_id, model="hy3-real", pv="1.1.0", status="succeeded", **kw):
    r = {
        "result_id": "r_" + event_id[-6:],
        "event_id": event_id,
        "ai_provider": "hy3",
        "ai_model": model,
        "prompt_version": pv,
        "processed_at": "2026-08-25T12:00:00+08:00",
        "processing_status": status,
        "title_zh": "中文标题" + event_id[-2:],
        "summary_zh": "中文摘要：" + event_id[-4:],
        "event_type": "other_security",
        "security_relevance": "indirect",
        "classification_confidence": 70,
        "location": {"country_iso3": "TCD", "admin1": None, "city": None,
                     "site": None, "raw_text": ""},
        "key_facts": [{"fact": "事实一", "evidence_field": "body_extracted",
                       "evidence_excerpt": "excerpt"}],
        "uncertainties": ["unverified"],
    }
    r.update(kw)
    return r


class TestPromptV11(unittest.TestCase):
    """P1：Prompt v1.1 存在、版本正确、三类规则齐全、v1 未变。"""

    def test_v11_exists_and_version(self):
        self.assertTrue(os.path.exists(V11_PATH), "v1.1 prompt 文件缺失")
        pc = load_prompt_contract(V11_PATH)
        self.assertEqual(pc.version, "1.1.0")

    def test_v11_three_new_rules(self):
        with open(V11_PATH, encoding="utf-8") as f:
            t = f.read()
        self.assertIn("数字与单位", t)
        self.assertIn("million", t)
        self.assertIn("milliard", t)
        self.assertIn("1,2 million", t)
        self.assertIn("120 millions", t)
        self.assertIn("239 milliards", t)
        self.assertIn("指控、声称和未经证实的信息", t)
        self.assertIn("accuse", t)
        self.assertIn("aurait", t)
        self.assertIn("non confirmé", t)
        self.assertIn("security_relevance", t)
        self.assertIn("经济新闻", t)
        self.assertIn("农业物资", t)
        self.assertIn("就业数据", t)
        self.assertIn("普通政府会见", t)

    def test_v11_attribution_not_escalated(self):
        with open(V11_PATH, encoding="utf-8") as f:
            t = f.read()
        # 不得把"指称……参与"强化为"……策划"的规则必须存在
        self.assertIn("不得把", t)
        self.assertIn("强化为", t)

    def test_v1_unchanged(self):
        pc1 = load_prompt_contract(V1_PATH)
        self.assertEqual(pc1.version, "1.0.0")

    def test_v11_render_works(self):
        pc = load_prompt_contract(V11_PATH)
        ev = {"event_id": "EVT_1234567890abcdef", "canonical_run_id": "r",
              "primary_country": "乍得", "country_iso3": "TCD",
              "original_title": "T", "source_language": "fr",
              "event_time": "2026-08-01T00:00:00+08:00",
              "canonical_url": "https://example.com/a",
              "body_extracted": "word " * 40}
        r = pc.render(ev)
        self.assertIn("EVT_1234567890abcdef", r)
        self.assertIn("TCD", r)


class TestBugFixes(unittest.TestCase):
    """P2：write_handoff event_id 与 _load_canonical_eligible quarantine 路径。"""

    def test_index_entry_has_event_id(self):
        root = tempfile.mkdtemp()
        try:
            pc = load_prompt_contract(V11_PATH)
            prov = Hy3Stage4Provider(ai_root=root, mode="produce")
            ev = {"event_id": "EVT_1234567890abcdef", "primary_country": "乍得",
                  "country_code": "TD", "country_iso3": "TCD",
                  "canonical_url": "https://example.com/2026/08/01/x",
                  "body_status": "full_body", "body_extracted": "word " * 40,
                  "article_word_count": 40,
                  "event_time": "2026-08-01T09:00:00+08:00",
                  "original_title": "Attack",
                  "canonical_run_id": "20260802T084000+0800_x"}
            prov.enqueue_event(ev, pc)
            entry = prov._index["EVT_1234567890abcdef"]
            self.assertEqual(entry["event_id"], "EVT_1234567890abcdef")
            # write_handoff 任务清单不再出现 event=None
            md = prov.write_handoff([entry]).read_text(encoding="utf-8")
            self.assertIn("event=EVT_1234567890abcdef", md)
            self.assertNotIn("event=None", md)
        finally:
            import shutil
            shutil.rmtree(root, ignore_errors=True)

    def test_load_canonical_eligible_quarantine_path(self):
        from ai.hy3_stage4_provider import _load_canonical_eligible
        eligible = _load_canonical_eligible()
        # 隔离判定真正生效（数量以最新 Canonical 数据为准，不断言旧数据固定值）
        self.assertGreater(len(eligible), 0)
        # 已知被隔离（legacy original_id 命中）的事件不得出现
        with open(os.path.join(ROOT, "data", "canonical",
                               "event_clusters.json"), encoding="utf-8") as f:
            d = json.load(f)
        with open(os.path.join(ROOT, "data", "canonical",
                               "quarantine.json"), encoding="utf-8") as f:
            q = json.load(f)
        qids = {it.get("original_id") for it in q.get("items", [])
                if it.get("original_object_type") == "event" and it.get("original_id")}
        for ev in eligible:
            self.assertNotIn(ev.get("event_id"), qids)
            self.assertNotIn(ev.get("legacy_event_id"), qids,
                             "legacy 格式隔离 id 必须已映射到 event_id 并排除")


class TestActiveSelection(unittest.TestCase):
    """P3：active Hy3 结果选择。"""

    def test_selects_v11_succeeded_non_deepseek(self):
        recs = [
            mk_result("EVT_1111111111111111", model="deepseek-v4-flash",
                      pv="1.0.0", title_zh="DeepSeek 结果"),
            mk_result("EVT_1111111111111111", model="hy3-real", pv="1.1.0",
                      title_zh="Hy3 结果"),
        ]
        act = select_active_result(recs, "1.1.0", {"deepseek-v4-flash"})
        self.assertIsNotNone(act)
        self.assertEqual(act["title_zh"], "Hy3 结果")
        self.assertEqual(act["ai_model"], "hy3-real")

    def test_deepseek_not_active(self):
        recs = [mk_result("EVT_1111111111111111", model="deepseek-v4-flash",
                          pv="1.0.0")]
        self.assertIsNone(select_active_result(recs, "1.1.0", {"deepseek-v4-flash"}))

    def test_non_succeeded_not_active(self):
        recs = [mk_result("EVT_1111111111111111", model="hy3-real", pv="1.1.0",
                          status="failed_terminal")]
        self.assertIsNone(select_active_result(recs, "1.1.0", {"deepseek-v4-flash"}))


class TestPublicApply(unittest.TestCase):
    """P4：apply_enrichment 纯函数。"""

    def test_inject_fields(self):
        pub = [{"event_id": "EVT_1111111111111111", "title_cn": "旧中文"}]
        res = [mk_result("EVT_1111111111111111")]
        out, stats = apply_enrichment(pub, res, {"EVT_1111111111111111"})
        self.assertEqual(stats["injected"], 1)
        o = out[0]
        for f in AI_SEMANTIC_FIELDS:
            self.assertIn(f, o, f)
        for dst in AI_META_FIELDS:
            self.assertIn(dst, o, dst)
        self.assertEqual(o["title_zh"], "中文标题11")
        self.assertEqual(o["ai_model"], "hy3-real")
        self.assertEqual(o["ai_prompt_version"], "1.1.0")
        # 原有字段保留
        self.assertEqual(o["title_cn"], "旧中文")

    def test_no_active_result_fallback(self):
        pub = [{"event_id": "EVT_1111111111111111", "title_cn": "旧中文"}]
        out, stats = apply_enrichment(pub, [], {"EVT_1111111111111111"})
        self.assertEqual(stats["no_active_result"], 1)
        self.assertEqual(out[0]["title_cn"], "旧中文")
        self.assertNotIn("title_zh", out[0])

    def test_rba_skipped(self):
        eid = list(REVIEW_BEFORE_ACTIVATION)[0]
        pub = [{"event_id": eid, "title_cn": "旧"}]
        res = [mk_result(eid, title_zh="不应注入")]
        out, stats = apply_enrichment(pub, res, {eid})
        self.assertEqual(stats["rba_skipped"], 1)
        self.assertNotIn("title_zh", out[0])

    def test_orphan_flagged(self):
        pub = [{"event_id": "EVT_9999999999999999"}]
        out, stats = apply_enrichment(pub, [], {"EVT_1111111111111111"})
        self.assertEqual(stats["orphan_skipped"], 1)
        self.assertIn("EVT_9999999999999999", stats["not_in_canonical"])

    def test_public_subset_canonical_real_data(self):
        with open(os.path.join(ROOT, "data", "public",
                               "published_events.json"), encoding="utf-8") as f:
            pub = json.load(f)
        with open(os.path.join(ROOT, "data", "canonical",
                               "event_clusters.json"), encoding="utf-8") as f:
            canon = json.load(f)
        cids = {e.get("event_id") for e in canon.get("items", [])}
        for it in pub.get("items", []):
            self.assertIn(it.get("event_id"), cids,
                          "Public⊆Canonical 被破坏: %s" % it.get("event_id"))


class TestFrontendFallback(unittest.TestCase):
    """P5：前端 title_zh fallback 链与详情页 AI 标识。"""

    def _check(self, rel):
        p = os.path.join(ROOT, rel)
        self.assertTrue(os.path.exists(p), rel)
        with open(p, encoding="utf-8") as f:
            return f.read()

    def test_common_js_fallback(self):
        t = self._check(os.path.join("assets", "js", "common.js"))
        self.assertIn("title_zh || ev.title_cn || ev.title_original", t)
        self.assertIn("summary_zh || ev.summary_cn", t)

    def test_index_fallback(self):
        t = self._check("index.html")
        self.assertIn("title_zh || e.title_cn || e.title_original", t)

    def test_country_fallback(self):
        t = self._check("country.html")
        self.assertIn("title_zh || e.title_cn || e.title_original", t)

    def test_event_detail(self):
        t = self._check("event.html")
        # 详情页：fallback 链 + 原文标题保留 + AI 标识低调显示
        self.assertIn("title_zh || e.title_cn || e.title_original", t)
        self.assertIn('kv("原文标题", esc(e.title_original))', t)
        self.assertIn("ai_model", t)
        self.assertIn("ai_processed_at", t)

    def test_events_page_uses_event_card(self):
        t = self._check("events.html")
        self.assertIn("eventCard", t)


class TestAIRuntimeIsolation(unittest.TestCase):
    """P6：AI runtime 不外泄（dist 白名单 + gitignore）。"""

    def test_build_site_allowlist_no_ai(self):
        bs = open(os.path.join(ROOT, "scripts", "build_site.py"), encoding="utf-8").read()
        m = re.search(r"PUBLIC_DATA_ALLOWLIST\s*=\s*\[([\s\S]*?)\]", bs)
        self.assertIsNotNone(m)
        self.assertNotIn("data/ai", m.group(1))
        self.assertNotIn("ai/", m.group(1))

    def test_gitignore_covers_data_ai(self):
        gi = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
        self.assertIn("data/ai/", gi)

    def test_no_ai_runtime_in_dist_allowlist_files(self):
        # dist 构建白名单不得包含 queue/completed/enrichment_results
        bs = open(os.path.join(ROOT, "scripts", "build_site.py"), encoding="utf-8").read()
        for bad in ("enrichment_results", "hy3_prompts", "HY3_STAGE4_HANDOFF"):
            self.assertNotIn(bad, bs, "白名单不得包含 AI runtime 文件: %s" % bad)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    print("RESULT: PASS=%d FAIL=%d" % (n_run - n_fail, n_fail))
    sys.exit(1 if n_fail else 0)
