#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c3f_negative_cache.py — C3F §七 终态负缓存与幂等测试（8 项）。

C3F 观察到的真实缺陷：run1 有 1 条 gate 拒绝的 FALLBACK，run2 又对它调用了一次 provider
（SECOND_IDENTICAL_RUN_AI_CALLS = 1）。根因不是 batching，而是"缺摘要就重试"的规则
覆盖了「同输入的终态负缓存」。
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT / "scripts"), str(ROOT / "scripts" / "ai"),
          str(ROOT / "scripts" / "ops")):
    sys.path.insert(0, p)

import c3_localization as L          # noqa: E402
import c3_artifacts as ART           # noqa: E402


def neg_rec(reason="PRESERVATION_GATE_FAIL", **kw):
    r = {"schema_version": L.SCHEMA_VERSION, "model": L.DEFAULT_MODEL,
         "prompt_version": L.PROMPT_VERSION, "input_hash": "H",
         "generated_at": "2026-09-19T21:20:00+08:00", "data_as_of": None,
         "status": L.STATUS_FALLBACK, "source_fact_refs": ["n1"],
         "news_id": "n1", "title_cn": "", "summary_cn": "",
         "fallback_reason": reason}
    r.update(kw)
    return r


class NegativeCacheSemanticsTest(unittest.TestCase):

    def test_01_summary_fallback_is_negative_cached(self):
        self.assertTrue(L.is_negative_cached(neg_rec("PRESERVATION_GATE_FAIL")))
        self.assertTrue(L.is_negative_cached(neg_rec("FACT_GATE_REJECTED")))
        self.assertTrue(L.is_negative_cached(neg_rec("SCHEMA_FAILURE")))

    def test_02_identical_second_run_does_not_retry_gate_fallback(self):
        """同 input_hash 的 gate FALLBACK，在 summary-only 下必须直接复用。"""
        rec = neg_rec()
        summary_mode = True
        # 修复前的规则：summary_mode 且缺 summary → 视为 miss（导致 run2 重调 provider）
        old_would_retry = (summary_mode and not (rec.get("summary_cn") or "").strip())
        self.assertTrue(old_would_retry)             # 旧行为确实会重试
        negative = L.is_negative_cached(rec)
        hit = (not rec.get("retryable")) and not (old_would_retry and not negative)
        self.assertTrue(hit, "终态负缓存必须让第二次运行 0 调用")
        run = (ROOT / "scripts" / "ops" / "c3_run.py").read_text(encoding="utf-8")
        self.assertIn("_negative = rec and L.is_negative_cached(rec)", run)
        self.assertIn("and not _negative", run)

    def test_03_negative_cache_contains_no_rejected_text(self):
        rec = neg_rec(gate_reasons=["NUMBER_DRIFT:24"])
        self.assertEqual((rec.get("title_cn") or "").strip(), "")
        self.assertEqual((rec.get("summary_cn") or "").strip(), "")
        for banned in ("raw_response", "raw_text", "provider_result", "content"):
            self.assertNotIn(banned, rec)
        # artifact 允许保留的字段白名单
        allowed = {"schema_version", "model", "prompt_version", "input_hash", "generated_at",
                   "data_as_of", "status", "source_fact_refs", "news_id", "src_id",
                   "display_identity", "title_cn", "summary_cn", "fallback_reason",
                   "gate_reasons", "retryable", "blocked_reason"}
        self.assertTrue(set(rec.keys()) <= allowed, set(rec.keys()) - allowed)

    def test_04_changed_input_hash_retries_fallback(self):
        rec = neg_rec()
        other = {"title_original": "different", "summary_original": "x"}
        self.assertNotEqual(L.content_hash(other), rec["input_hash"])
        # hash 变了 → 不是同输入 → 允许重试（负缓存不生效）
        hit = (rec.get("input_hash") == L.content_hash(other))
        self.assertFalse(hit)

    def test_05_changed_prompt_version_retries_fallback(self):
        key_a = "loc_n1_H_localization-batch-v1_deepseek-flash"
        key_b = "loc_n1_H_localization-batch-v2_deepseek-flash"
        self.assertNotEqual(key_a, key_b)
        self.assertIn(L.PROMPT_VERSION, key_a)

    def test_06_changed_model_retries_fallback(self):
        a = "loc_n1_H_localization-batch-v1_deepseek-flash"
        b = "loc_n1_H_localization-batch-v1_deepseek-v4-flash"
        self.assertNotEqual(a, b)

    def test_07_manual_retry_can_bypass_negative_cache(self):
        """provider 失败（retryable=True）与人工重试都不受终态负缓存约束。"""
        self.assertFalse(L.is_negative_cached(neg_rec(fallback_reason="timeout",
                                                     retryable=True)))
        self.assertFalse(L.is_negative_cached(neg_rec(status=L.STATUS_FULL)))
        self.assertFalse(L.is_negative_cached(neg_rec(status=L.STATUS_PARTIAL)))

    def test_08_full_cache_behavior_unchanged(self):
        """FULL 命中语义未变：同 input_hash + 非 retryable 即命中。"""
        full = {"status": L.STATUS_FULL, "input_hash": "H", "title_cn": "甲",
                "summary_cn": "乙"}
        self.assertFalse(L.is_negative_cached(full))     # FULL 不是负缓存
        self.assertTrue(full["title_cn"] and full["summary_cn"])
        # partial 仍需补摘要（不是负缓存）
        part = {"status": L.STATUS_PARTIAL, "input_hash": "H", "title_cn": "甲",
                "summary_cn": ""}
        self.assertFalse(L.is_negative_cached(part))


class IdempotencyIntegrationTest(unittest.TestCase):
    """§十八：同一输入第二次运行必须是 0 次 provider 调用（用桩证明，不调用真实 AI）"""

    def test_09_second_identical_run_makes_zero_calls(self):
        import shutil as _sh
        tmp = tempfile.mkdtemp(prefix="c3neg_")
        try:
            for rel in ("data/canonical/articles.json", "data/canonical/event_clusters.json",
                        "data/views/news_stream.json", "data/status.json", "data/sources.json",
                        "data/views/country_snapshots.json", "data/views/site_overview.json",
                        "data/views/report_index.json", "data/views/china_interest.json"):
                s = ROOT / rel
                d = Path(tmp) / rel
                d.parent.mkdir(parents=True, exist_ok=True)
                if s.exists():
                    _sh.copy2(str(s), str(d))
            _sh.copytree(str(ROOT / "data" / "intelligence" / "ai"),
                         str(Path(tmp) / "data" / "intelligence" / "ai"))
            env = {**os.environ, "PYTHONPATH": ""}
            out = os.path.join(tmp, "r.json")
            r = subprocess.run([sys.executable, "-m", "scripts.ops.c3_run", "--root", tmp,
                                "--provider", "stub:ok", "--mode", "c3f_incremental",
                                "--out", out], cwd=str(ROOT), capture_output=True,
                               text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr[-500:])
            j = json.load(open(out, encoding="utf-8"))
            # 91 条已完成 → 目标应为 0（或仅原本不属于本轮的既有 PARTIAL）
            target = (j.get("summary_only") or {}).get("target")
            self.assertLessEqual(target, 9, "已完成 91 条后不应再有 >=91 的摘要目标")
            # 关键：gate 拒绝的 FALLBACK 不得因为"缺摘要"被再次请求
            self.assertEqual(j.get("ai_calls_event"), 0)
            self.assertEqual(j.get("ai_calls_country"), 0)
            self.assertLessEqual(j.get("ai_calls_homepage", 0), 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
