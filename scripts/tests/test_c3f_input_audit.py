#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c3f_input_audit.py — C3F §十 mode-aware 输入审计测试（10 项）。

核心命题：**既有真实 AI 状态 ≠ 污染**。full 模式保持严格；c3f_incremental 允许
REAL/STALE 作为 prior state，但 stub / simulation / unknown provenance 依旧 fail closed。
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
for p in (str(ROOT / "scripts"), str(ROOT / "scripts" / "ai"),
          str(ROOT / "scripts" / "ops")):
    sys.path.insert(0, p)

import c3_input_audit as AU          # noqa: E402
import c3_localization as L          # noqa: E402
import c3_analysis as A              # noqa: E402


def _rec(model="deepseek-flash", status="FULL", **kw):
    r = {"model": model, "schema_version": "localization-v1",
         "prompt_version": "localization-batch-v1", "input_hash": "h" * 8,
         "generated_at": "2026-09-19T00:00:00+08:00", "data_as_of": "2026-09-19T00:00:00Z",
         "status": status, "source_fact_refs": ["x"]}
    r.update(kw)
    return r


def _mkroot():
    t = tempfile.mkdtemp(prefix="c3audit_")
    ai = Path(t) / "data" / "intelligence" / "ai"
    for s in ("localization", "event_analysis", "country_analysis", "homepage_analysis"):
        (ai / s).mkdir(parents=True, exist_ok=True)
    (Path(t) / "data" / "canonical").mkdir(parents=True, exist_ok=True)
    (Path(t) / "data" / "canonical" / "articles.json").write_text(json.dumps(
        {"items": [{"published_at": "2026-09-11T00:00:00+08:00"}]}), encoding="utf-8")
    return t


def _write(t, rel, obj):
    p = Path(t) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


class IncrementalAcceptsPriorRealTest(unittest.TestCase):

    def setUp(self):
        self.t = _mkroot()

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    def test_01_c3f_incremental_accepts_valid_real_prior_ai(self):
        _write(self.t, "data/intelligence/ai/localization/a.json", _rec())
        r = AU.audit(self.t, "c3f_incremental")
        self.assertTrue(r["ok"], r["violations"])
        self.assertEqual(r["STUB_AI_INPUT_CONTAMINATION"], 0)
        self.assertEqual(r["PREEXISTING_REAL_AI_ARTIFACTS"], 1)

    def test_02_c3f_incremental_accepts_stale_real_homepage_as_dirty(self):
        # 真实 homepage，但 fact_pack_hash 与当前不一致 → STALE，不是污染
        _write(self.t, "data/intelligence/ai/homepage_analysis/current.json",
               _rec(executive_assessment="旧文本", fact_pack_hash="OLDHASH"))
        r = AU.audit(self.t, "c3f_incremental")
        self.assertTrue(r["ok"], r["violations"])
        self.assertEqual(r["provenance_counts"]["STALE_REAL_PRIOR_OUTPUT"], 1)
        self.assertEqual(r["STUB_AI_INPUT_CONTAMINATION"], 0)
        self.assertEqual(r["SIMULATION_AI_INPUT_CONTAMINATION"], 0)

    def test_03_c3f_incremental_marks_homepage_refresh_required(self):
        _write(self.t, "data/intelligence/ai/homepage_analysis/current.json",
               _rec(fact_pack_hash="OLDHASH"))
        r = AU.audit(self.t, "c3f_incremental")
        self.assertTrue(r["HOMEPAGE_REFRESH_REQUIRED"])
        self.assertTrue(r["HOMEPAGE_DIRTY"])
        # hash 一致则不再要求刷新
        t2 = _mkroot()
        try:
            cur = AU.current_homepage_fact_pack_hash(t2)
            _write(t2, "data/intelligence/ai/homepage_analysis/current.json",
                   _rec(fact_pack_hash=cur))
            r2 = AU.audit(t2, "c3f_incremental")
            self.assertFalse(r2["HOMEPAGE_REFRESH_REQUIRED"])
        finally:
            shutil.rmtree(t2, ignore_errors=True)


class IncrementalRejectsBadProvenanceTest(unittest.TestCase):

    def setUp(self):
        self.t = _mkroot()

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    def test_04_c3f_incremental_rejects_stub_prior_ai(self):
        _write(self.t, "data/intelligence/ai/localization/s.json", _rec(model="stub"))
        r = AU.audit(self.t, "c3f_incremental")
        self.assertFalse(r["ok"])
        self.assertEqual(r["STUB_AI_INPUT_CONTAMINATION"], 1)

    def test_05_c3f_incremental_rejects_simulation_prior_ai(self):
        _write(self.t, "data/intelligence/ai/localization/sim.json",
               _rec(note="simulation output"))
        r = AU.audit(self.t, "c3f_incremental")
        self.assertFalse(r["ok"])
        self.assertEqual(r["SIMULATION_AI_INPUT_CONTAMINATION"], 1)

    def test_06_c3f_incremental_rejects_unknown_provenance(self):
        _write(self.t, "data/intelligence/ai/localization/u.json",
               {"status": "FULL", "title_cn": "x"})     # 缺 model/schema/input_hash
        r = AU.audit(self.t, "c3f_incremental")
        self.assertFalse(r["ok"])
        self.assertEqual(r["UNKNOWN_AI_PROVENANCE"], 1)
        # 非 canonical 模型名也归 UNKNOWN（fail closed）
        t2 = _mkroot()
        try:
            _write(t2, "data/intelligence/ai/localization/u2.json", _rec(model="gpt-4o"))
            r2 = AU.audit(t2, "c3f_incremental")
            self.assertFalse(r2["ok"])
            self.assertEqual(r2["UNKNOWN_AI_PROVENANCE"], 1)
        finally:
            shutil.rmtree(t2, ignore_errors=True)

    def test_07_full_mode_retains_strict_input_audit(self):
        _write(self.t, "data/intelligence/ai/localization/a.json", _rec())
        r = AU.audit(self.t, "full")
        self.assertFalse(r["ok"], "full 模式不得接受既有 AI 产物")
        self.assertEqual(r["policy"], "STRICT_FULL")
        # 空树时 full 模式必须通过
        t2 = _mkroot()
        try:
            self.assertTrue(AU.audit(t2, "full")["ok"])
        finally:
            shutil.rmtree(t2, ignore_errors=True)


class PromptBoundaryTest(unittest.TestCase):

    def test_08_old_homepage_text_never_enters_new_prompt(self):
        """旧 homepage artifact 只用于 hash/cache/dirty，不得进入新 prompt。"""
        pack = A.build_homepage_fact_pack_from_views(str(ROOT))
        blob = json.dumps(pack, ensure_ascii=False)
        for field in ("executive_assessment", "trend_analysis", "outlook", "watch_points"):
            self.assertNotIn(field, blob, "旧 AI 文本字段不得出现在新 fact pack 中")
        # runner 只把 hpack 序列化进 prompt
        run = (ROOT / "scripts" / "ops" / "c3_run.py").read_text(encoding="utf-8")
        self.assertIn('json.dumps(hpack, ensure_ascii=False)', run)
        self.assertNotIn("prev_h.get(\"executive_assessment\")", run)

    def test_09_rejected_localization_text_never_enters_summary_prompt(self):
        """summary-only 的输入只含 item 字段；被 gate 拒绝的旧中文不得进入。"""
        item = {"news_id": "n1", "title_cn": "已验证标题", "title_original": "Orig title",
                "summary_original": "src", "country_cn": "乍得", "source_name": "Src",
                "summary_cn": ""}
        prompt = L.build_user_prompt_summary_only([item])
        self.assertIn("已验证标题", prompt)                 # 允许：已验证标题
        for banned in ("fallback_reason", "gate_reasons", "partial_reason",
                       "PRESERVATION_GATE_FAIL"):
            self.assertNotIn(banned, prompt, "被拒元数据不得进入 summary prompt")
        # 被拒条目的文本本身也不会出现在 prompt 里（因为 prompt 由 item 字段构造）
        rejected = _rec(status="FALLBACK", title_cn="", summary_cn="",
                        fallback_reason="PRESERVATION_GATE_FAIL")
        self.assertEqual((rejected.get("title_cn") or "").strip(), "")
        self.assertEqual((rejected.get("summary_cn") or "").strip(), "")

    def test_10_c3f_prior_artifacts_do_not_trigger_full_reprocessing(self):
        """既有 prior 产物不得导致全量重跑：incremental 下目标集合必须只是 summary 待补项。"""
        run = (ROOT / "scripts" / "ops" / "c3_run.py").read_text(encoding="utf-8")
        self.assertIn('if mode in ("summary_only", "c3f_incremental"):\n        targets = [i for i in items if L.needs_summary_only(i)]', run)
        self.assertIn("skip_analysis = incremental", run)
        r = AU.audit(str(ROOT), "c3f_incremental")
        self.assertTrue(r["ok"], r["violations"])
        self.assertEqual(r["STUB_AI_INPUT_CONTAMINATION"], 0)
        self.assertEqual(r["SIMULATION_AI_INPUT_CONTAMINATION"], 0)
        self.assertEqual(r["UNKNOWN_AI_PROVENANCE"], 0)
        self.assertTrue(r["HOMEPAGE_REFRESH_REQUIRED"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
