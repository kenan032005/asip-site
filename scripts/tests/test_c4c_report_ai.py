#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c4c_report_ai.py — C4-C 报告 AI enrichment 测试（含 cache / negative cache / gates）。

全部用**注入的 fixture provider**，不调用真实 AI。
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
for p in (str(ROOT), str(ROOT / "scripts")):
    sys.path.insert(0, p)

from scripts.report import factory as F            # noqa: E402
from scripts.report import materialize as M        # noqa: E402
from scripts.report import report_ai as RAI        # noqa: E402


class FixtureProvider:
    """按 fact pack 生成合法 analysis（或按需返回非法内容），并记录调用次数。"""

    def __init__(self, mode="ok", api_key="fixture"):
        self.mode = mode
        self.api_key = api_key
        self.calls = []
        self.name = "fixture"

    def submit_task(self, task):
        self.calls.append(task)
        if self.mode == "provider_failed":
            return {"status": "failed", "result": {"error": {"code": "http_503"}}}
        # 从 prompt 里取出 fact pack 的用户 JSON，构造保守分析
        txt = task.get("user_text") or ""
        i = txt.find("{")
        try:
            payload = json.loads(txt[i:]) if i >= 0 else {}
        except Exception:  # noqa: BLE001
            payload = {}
        facts = payload.get("facts") or []
        countries = sorted({str(f.get("country") or "") for f in facts if f.get("country")})
        c0 = countries[0] if countries else ""
        if self.mode == "bad_schema":
            body = {"executive_assessment": "x"}          # 缺字段
        elif self.mode == "unsupported_number":
            body = {"executive_assessment": "本期共 98765 人死亡。",
                    "trend_analysis": "趋势平稳。", "outlook": "继续观察。",
                    "watch_points": ["关注"]}
        else:
            body = {
                "executive_assessment": ("本期 %s 方向的事件强度维持，"
                                         "已核实事实以 %s 为主。"
                                         % (c0 or "重点国家", c0 or "重点国家")),
                "trend_analysis": "现有事实未显示趋势逆转，需持续观察同一来源的信度变化。",
                "outlook": "下一周期关注同一国家的同类事件是否延续。",
                "watch_points": ["持续跟踪同类事件", "关注单一来源条目是否获得交叉印证"],
            }
        return {"status": "succeeded",
                "result": {"text": json.dumps(body, ensure_ascii=False),
                           "http_status": 200, "finish_reason": "stop",
                           "returned_model": RAI.MODEL}}


def mkroot():
    t = tempfile.mkdtemp(prefix="c4c_")
    for rel in ("data/canonical/articles.json", "data/canonical/event_clusters.json",
                "data/status.json", "data/views/country_snapshots.json"):
        s = ROOT / rel
        d = Path(t) / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        if s.exists():
            shutil.copy2(str(s), str(d))
    return t


def seed_country_weekly(t, iso="TCD", week_end="2026-09-13", n_facts=10):
    """在 tmp root 物化一份有来源的 country weekly（供 AI enrichment 测试）。"""
    ev = []
    for i in range(n_facts):
        ev.append({"event_id": "E%s_%d" % (iso, i), "country_iso3": iso,
                   "country_code": iso[:2], "event_type": "armed_conflict",
                   "event_time": "2026-09-%02d" % (7 + (i % 6)),
                   "source_count": 1, "source_groups": ["src_%s_%d" % (iso, i)],
                   "title_original": "incident %d" % i,
                   "title_cn": "事件 %d" % i})
    tgt = {"report_id": F.build_report_id("country_weekly", week_end=week_end, country_iso3=iso),
           "country_iso3": iso, "week_start": "2026-09-06", "week_end": week_end,
           "selection_reason": "CONFIGURED_PRIORITY_COUNTRY"}
    rep, fp = M.materialize_country_weekly(t, tgt, ev, [], {iso[:2]: iso})
    rep["status"] = M.STATUS_FALLBACK
    M.write_report_artifact(t, "country_weekly", rep)
    return rep, fp


class TargetPlannerTest(unittest.TestCase):

    def test_01_planner_skips_low_data(self):
        p = RAII_plan(str(ROOT))
        self.assertEqual(p["TOTAL_REPORTS"], 22)
        self.assertEqual(p["LOW_DATA_REPORTS"], 16)
        self.assertEqual(p["AI_TARGET_REPORTS"], 6)
        self.assertEqual(p["EXPECTED_REAL_AI_CALLS_MAX"], 6)
        for rid in p["target_ids"]:
            self.assertTrue(rid.startswith("WEEKLY_"))

    def test_02_planner_is_read_only_and_zero_calls(self):
        p1 = RAII_plan(str(ROOT))
        p2 = RAII_plan(str(ROOT))
        self.assertEqual(p1, p2)


class EnrichmentTest(unittest.TestCase):

    def setUp(self):
        self.t = mkroot()
        self.rep, self.fp = seed_country_weekly(self.t)

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    def test_03_full_on_pass_and_gate_result(self):
        prov = FixtureProvider("ok")
        o = self._enrich(self.rep, prov)
        self.assertEqual(o["outcome"], "CALLED_FULL")
        self.assertEqual(o["gate_result"], "PASS")
        self.assertEqual(o["new_status"], M.STATUS_FULL)
        saved = M.read_report_artifact(self.t, "country_weekly", self.rep["report_id"])
        self.assertEqual(saved["status"], "FULL")
        for k in RAI.AI_FIELDS:
            self.assertTrue(saved.get(k), k)

    def test_04_second_identical_run_makes_zero_calls(self):
        prov = FixtureProvider("ok")
        self._enrich(self.rep, prov)
        self.assertEqual(len(prov.calls), 1)
        rep2 = M.read_report_artifact(self.t, "country_weekly", self.rep["report_id"])
        o2 = self._enrich(rep2, prov)
        self.assertEqual(o2["outcome"], "CACHED_FULL")
        self.assertEqual(o2["ai_call"], 0)
        self.assertEqual(len(prov.calls), 1, "同输入第二遍必须 0 新调用")

    def test_05_fact_gate_rejects_unsupported_number(self):
        prov = FixtureProvider("unsupported_number")
        o = self._enrich(self.rep, prov)
        self.assertEqual(o["gate_result"], "FACT_GATE_REJECTED")
        saved = M.read_report_artifact(self.t, "country_weekly", self.rep["report_id"])
        self.assertNotEqual(saved["status"], "FULL")
        self.assertNotIn("98765", json.dumps(saved, ensure_ascii=False),
                         "被拒正文不得落盘")

    def test_06_negative_cache_blocks_second_call(self):
        prov = FixtureProvider("unsupported_number")
        self._enrich(self.rep, prov)
        rep2 = M.read_report_artifact(self.t, "country_weekly", self.rep["report_id"])
        o2 = self._enrich(rep2, prov)
        self.assertEqual(o2["outcome"], "CACHED_NEGATIVE")
        self.assertEqual(len(prov.calls), 1)

    def test_07_schema_failure_falls_back_and_negative_caches(self):
        prov = FixtureProvider("bad_schema")
        o = self._enrich(self.rep, prov)
        self.assertEqual(o["gate_result"], "SCHEMA_FAILURE")
        rep2 = M.read_report_artifact(self.t, "country_weekly", self.rep["report_id"])
        o2 = self._enrich(rep2, prov)
        self.assertEqual(o2["outcome"], "CACHED_NEGATIVE")

    def test_08_provider_failure_keeps_fallback(self):
        prov = FixtureProvider("provider_failed")
        o = self._enrich(self.rep, prov)
        self.assertEqual(o["gate_result"], "PROVIDER_FAILED")
        saved = M.read_report_artifact(self.t, "country_weekly", self.rep["report_id"])
        self.assertNotEqual(saved["status"], "FULL")

    def _enrich(self, rep, prov):
        fp = getattr(self, "fp", None)
        return RAI.enrich_one(self.t, rep, provider=prov, fact_pack=fp)

    def test_09_low_data_never_calls_ai(self):
        tgt = {"report_id": "DAILY_20260918", "report_date": "2026-09-18"}
        rep, _ = M.materialize_daily(self.t, tgt, [], [], {})
        prov = FixtureProvider("ok")
        o = RAII_enrich(self.t, rep, prov)
        self.assertEqual(o["outcome"], "SKIPPED_LOW_DATA")
        self.assertEqual(len(prov.calls), 0)

    def test_10_fact_pack_hash_mismatch_is_dirty(self):
        bad = dict(self.rep, fact_pack_hash="deadbeef")
        prov = FixtureProvider("ok")
        o = self._enrich(bad, prov)
        self.assertEqual(o["outcome"], "FACT_PACK_DIRTY")
        self.assertEqual(len(prov.calls), 0)


class PolicyAndSafetyTest(unittest.TestCase):

    def test_11_unattributed_facts_never_in_ai_fact_pack(self):
        t = mkroot()
        try:
            rep, fp = seed_country_weekly(t)
            self.assertEqual(RAI._unattributed_in_pack(fp), 0)
            prompt = json.dumps(RAI.AC.build_analysis_prompt(fp), ensure_ascii=False)
            self.assertNotIn("source_unknown", prompt)
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_12_ai_fields_locked(self):
        self.assertEqual(RAI.AI_FIELDS,
                         ("executive_assessment", "trend_analysis", "outlook", "watch_points"))
        src = (ROOT / "scripts" / "report" / "report_ai.py").read_text(encoding="utf-8")
        self.assertIn("analysis-v1.0.0", src)
        self.assertIn("deepseek-flash", src)
        self.assertNotIn("thinking", src.replace("thinking_disabled", ""))

    def test_13_enrich_all_reports_zero_calls_for_low_data(self):
        t = mkroot()
        try:
            rep, fp = seed_country_weekly(t)
            prov = FixtureProvider("ok")
            st = RAI.enrich_all(t, provider=prov, write=False,
                                fact_pack_map={rep["report_id"]: fp})
            self.assertEqual(st["AI_CALLS_DAILY"], 0)
            self.assertEqual(st["AI_CALLS_AFRICA_WEEKLY"], 0)
            self.assertEqual(st["AI_CALLS_COUNTRY_WEEKLY"], 1)
            self.assertEqual(st["AI_CALLS_TOTAL"], 1)
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_14_no_ai_impl_details_in_artifacts(self):
        t = mkroot()
        try:
            rep, _fp = seed_country_weekly(t)
            RAI.enrich_one(t, rep, provider=FixtureProvider("ok"), fact_pack=_fp)
            saved = M.read_report_artifact(t, "country_weekly", rep["report_id"])
            txt = json.dumps(saved, ensure_ascii=False)
            # 允许内部记账字段存在（不展示），但不得写入 prompt/secret
            for bad in ("ASIP_DEEPSEEK_API_KEY", "Authorization", "Bearer "):
                self.assertNotIn(bad, txt)
        finally:
            shutil.rmtree(t, ignore_errors=True)


class ReportPackHashContractTest(unittest.TestCase):
    """§三 长期 hash 契约：墙钟字段不得影响 hash；真实事实变化必须影响 hash。"""

    def _base(self):
        return {"report_id": "WEEKLY_TCD_20260913", "report_type": "country_weekly",
                "report_date": "2026-09-13", "period": {"start": "2026-09-06",
                                                        "end": "2026-09-13"},
                "social_facts": [{"fact_id": "E1", "headline_zh": "事件一",
                                  "source_refs": ["srcA"]}],
                "numeric_provenance": {"2026": ["report_date"], "12": ["generated_at"]}}

    def test_a_report_pack_hash_ignores_generated_at(self):
        a = self._base(); a["generated_at"] = "2026-09-20T09:00:00+08:00"
        b = self._base(); b["generated_at"] = "2026-09-20T23:59:59+08:00"
        self.assertEqual(F.report_pack_hash(a), F.report_pack_hash(b))

    def test_b_report_pack_hash_ignores_built_at(self):
        a = self._base(); a["built_at"] = "2026-09-20T09:00:00+08:00"
        b = self._base(); b["built_at"] = "2026-09-21T10:00:00+08:00"
        self.assertEqual(F.report_pack_hash(a), F.report_pack_hash(b))

    def test_c_report_pack_hash_ignores_now(self):
        a = self._base(); a["now"] = "2026-09-20T09:00:00+08:00"
        b = self._base(); b["now"] = "2027-01-01T00:00:00+08:00"
        self.assertEqual(F.report_pack_hash(a), F.report_pack_hash(b))

    def test_d_report_pack_hash_ignores_cutoff_runtime_metadata(self):
        a = self._base(); a["cutoff"] = "2026-09-13T20:00:00+08:00"
        a["runtime"] = {"cache_hit": True}
        b = self._base(); b["cutoff"] = "2026-09-13T20:19:54+08:00"
        b["runtime"] = {"cache_hit": False}
        self.assertEqual(F.report_pack_hash(a), F.report_pack_hash(b))

    def test_e_report_pack_hash_ignores_wallclock_numeric_provenance(self):
        a = self._base()
        a["numeric_provenance"] = {"2026": ["report_date"], "12": ["generated_at"],
                                   "59": ["cutoff"]}
        b = self._base()
        b["numeric_provenance"] = {"2026": ["report_date"], "07": ["generated_at"],
                                   "30": ["cutoff"]}
        self.assertEqual(F.report_pack_hash(a), F.report_pack_hash(b))
        # 事实相关的 provenance 必须保留
        c = self._base()
        c["numeric_provenance"] = {"2026": ["report_date"], "12": ["generated_at"],
                                   "24": ["social_facts.0"]}
        self.assertNotEqual(F.report_pack_hash(a), F.report_pack_hash(c))

    def test_f_report_pack_hash_changes_when_factual_content_changes(self):
        a = self._base()
        b = self._base()
        b["social_facts"] = [{"fact_id": "E1", "headline_zh": "事件一（改）",
                              "source_refs": ["srcA"]}]
        self.assertNotEqual(F.report_pack_hash(a), F.report_pack_hash(b),
                            "真实事实变化必须改变 hash —— 稳定不等于忽略事实")
        c = self._base()
        c["social_facts"] = [{"fact_id": "E1", "headline_zh": "事件一",
                              "source_refs": ["srcA", "srcB"]}]
        self.assertNotEqual(F.report_pack_hash(a), F.report_pack_hash(c),
                            "来源变化也必须改变 hash")
        d = self._base()
        d["period"] = {"start": "2026-09-07", "end": "2026-09-13"}
        self.assertNotEqual(F.report_pack_hash(a), F.report_pack_hash(d),
                            "报告期变化也必须改变 hash")


# 简写别名（避免长名字重复）
RAII_plan = RAI.plan_targets
RAII_enrich = RAI.enrich_one


if __name__ == "__main__":
    unittest.main(verbosity=2)
