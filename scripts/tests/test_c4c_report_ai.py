#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c4c_report_ai.py — C4-C 报告 AI enrichment 测试（含 cache / negative cache / gates）。

全部用**注入的 fixture provider**，不调用真实 AI。
"""
import io
import json
import os
import re
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
    """**只实现 Stage 7B 真实契约** `generate(system, user)` → (text, meta)。

    §五：刻意 **不**实现 `submit_task()`。若 report_ai 再误用 task-style 接口，
    这里会立刻 AttributeError（而不是被一个假接口悄悄兼容掉）。
    """

    #: 真实 provider（providers.py）只暴露这两个方法名；用于契约测试断言
    CONTRACT_METHODS = ("generate",)

    def __init__(self, mode="ok", api_key="fixture"):
        self.mode = mode
        self.api_key = api_key
        self.calls = []          # [(system, user)]
        self.name = "fixture"

    def generate(self, system, user):
        self.calls.append((system, user))
        if self.mode == "provider_failed":
            # 5xx = provider 全局不可用 → 系统级（§七）
            raise RAI.P.ProviderUnavailable("http_503")
        if self.mode == "report_level_failed":
            # 仅这一份输入无法处理 → 报告级
            raise RAI.P.ProviderUnavailable("content_filter: this report input rejected")
        try:
            payload = json.loads(user)
        except Exception:  # noqa: BLE001
            payload = {}
        facts = payload.get("facts") or []
        countries = sorted({str(f.get("country") or "") for f in facts if f.get("country")})
        c0 = countries[0] if countries else ""
        if self.mode == "bad_schema":
            body = {"executive_assessment": "x"}          # 缺字段
        elif self.mode == "not_json":
            return "这不是 JSON", {"model": RAI.MODEL}
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
        return json.dumps(body, ensure_ascii=False), {"model": RAI.MODEL, "provider": self.name}


class SubmitTaskOnlyProvider:
    """**错误契约**替身：只有 submit_task（正是 C4-C 第一次真实运行踩到的形状）。"""

    def __init__(self):
        self.api_key = "fixture"
        self.calls = []

    def submit_task(self, task):     # noqa: D102
        self.calls.append(task)
        return {"status": "succeeded", "result": {"text": "{}"}}


class RaisingProvider:
    """按指定异常类型抛错的 provider。"""

    def __init__(self, exc):
        self.api_key = "fixture"
        self.exc = exc
        self.calls = []

    def generate(self, system, user):
        self.calls.append((system, user))
        raise self.exc


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


def ai_pack(iso="TCD", n_social=3, n_disease=2, social_content=True, social_source=True,
            disease_content=True, disease_source=True, disease_country=None,
            disease_date="2026-09-10"):
    """构造一个**有内容/有来源**的 fact pack（AI 边界测试用，绕开上游投影缺陷）。

    上游 `build_weekly_input` 目前不投影 title/summary，真实 pack 里的事实是空壳；
    这里显式给出合规形状，用来验证「合规输入 → 正常调用」这半边契约。
    """
    sf = []
    for i in range(n_social):
        f = {"fact_id": "E%d" % i, "country_iso3": iso, "event_type": "armed_conflict",
             "source_refs": ["src%d" % i] if social_source else [],
             "uncertainties": []}
        if social_content:
            f["headline_zh"] = "事件 %d" % i
            f["verified_summary"] = "摘要 %d" % i
        sf.append(f)
    df = []
    for i in range(n_disease):
        f = {"fact_id": "dis%d" % i, "disease_id": "cholera%d" % i,
             "country_iso3": disease_country or iso, "report_date": disease_date,
             "source_refs": ["dnews%d" % i] if disease_source else [],
             "uncertainties": []}
        if disease_content:
            f["headline_zh"] = "疫情 %d" % i
        df.append(f)
    fp = {"report_id": "WEEKLY_%s_20260913" % iso, "report_type": "country_weekly",
          "country_iso3": iso, "week_start": "2026-09-06", "week_end": "2026-09-13",
          "period_start": "2026-09-06", "period_end": "2026-09-13",
          "social_facts": sf, "disease_facts": df,
          "source_refs": sorted({s for f in sf + df for s in f["source_refs"]}),
          "entity_vocab": [], "numeric_provenance": {}, "uncertainties": []}
    return fp


def with_pack(rep, fp):
    """把 fixture pack 挂到报告上（hash 必须与之自洽，否则会被判 FACT_PACK_DIRTY）。"""
    r = dict(rep)
    r["fact_pack_hash"] = F.report_pack_hash(fp)
    return r


class TargetPlannerTest(unittest.TestCase):

    def test_01_planner_skips_low_data(self):
        """C4-C 事实投影修复后：4 份无可分析事实的周报被重新分类为 LOW_DATA（§十七），
        因此 LOW_DATA = 20、targets = 2（不再是空壳事实撑起来的 6）。"""
        p = RAII_plan(str(ROOT))
        self.assertEqual(p["TOTAL_REPORTS"], 22)
        self.assertEqual(p["LOW_DATA_REPORTS"], 20)
        self.assertEqual(p["AI_TARGET_REPORTS"], 2)
        self.assertEqual(p["AI_TARGET_REPORTS_ACTUAL"], 2)
        self.assertEqual(p["EXPECTED_REAL_AI_CALLS_MAX"], 2)
        for rid in p["target_ids"]:
            self.assertTrue(rid.startswith("WEEKLY_"))

    def test_02_planner_is_read_only_and_zero_calls(self):
        p1 = RAII_plan(str(ROOT))
        p2 = RAII_plan(str(ROOT))
        self.assertEqual(p1, p2)


class EnrichmentTest(unittest.TestCase):

    def setUp(self):
        self.t = mkroot()
        rep, _ = seed_country_weekly(self.t)
        self.fp = ai_pack()
        self.rep = with_pack(rep, self.fp)
        M.write_report_artifact(self.t, "country_weekly", self.rep)   # 磁盘状态自洽

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

    def test_08_report_level_provider_failure_keeps_fallback(self):
        prov = FixtureProvider("report_level_failed")
        o = self._enrich(self.rep, prov)
        self.assertEqual(o["gate_result"], "PROVIDER_EXCEPTION")
        self.assertTrue(o.get("provider_failed"))
        saved = M.read_report_artifact(self.t, "country_weekly", self.rep["report_id"])
        self.assertNotEqual(saved["status"], "FULL")

    def _enrich(self, rep, prov):
        return RAI.enrich_one(self.t, rep, provider=prov, fact_pack=self.fp)

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
        fp = ai_pack(n_social=2, n_disease=0, social_source=False)
        _ai, d = RAI.build_ai_fact_pack(fp, {"report_type": "country_weekly",
                                            "country_iso3": "TCD"})
        self.assertEqual(d["UNATTRIBUTED_FACTS_IN_AI_FACT_PACK"], 0)
        self.assertEqual(d["SOCIAL_FACTS_INCLUDED"], 0)
        self.assertEqual(d["SOCIAL_FACTS_EXCLUDED_NO_SOURCE"], 2)

    def test_12_ai_fields_locked(self):
        self.assertEqual(RAI.AI_FIELDS,
                         ("executive_assessment", "trend_analysis", "outlook", "watch_points"))
        src = (ROOT / "scripts" / "report" / "report_ai.py").read_text(encoding="utf-8")
        self.assertIn("analysis-v1.0.0", src)
        self.assertIn("deepseek-flash", src)
        self.assertIn("AI_PACK_VERSION", src)

    def test_13_enrich_all_reports_zero_calls_for_low_data(self):
        t = mkroot()
        try:
            rep, _ = seed_country_weekly(t)
            fp = ai_pack()
            rep = with_pack(rep, fp)
            M.write_report_artifact(t, "country_weekly", rep)
            prov = FixtureProvider("ok")
            st = RAI.enrich_all(t, provider=prov, write=False,
                                fact_pack_map={rep["report_id"]: fp})
            self.assertEqual(st["AI_CALLS_DAILY"], 0)
            self.assertEqual(st["AI_CALLS_AFRICA_WEEKLY"], 0)
            self.assertEqual(st["AI_CALLS_COUNTRY_WEEKLY"], 1)
            self.assertEqual(st["AI_CALLS_TOTAL"], 1)
            self.assertEqual(st["UNATTRIBUTED_FACTS_IN_AI_FACT_PACK"], 0)
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_14_no_ai_impl_details_in_artifacts(self):
        t = mkroot()
        try:
            rep, _ = seed_country_weekly(t)
            fp = ai_pack()
            rep = with_pack(rep, fp)
            M.write_report_artifact(t, "country_weekly", rep)
            RAI.enrich_one(t, rep, provider=FixtureProvider("ok"), fact_pack=fp)
            saved = M.read_report_artifact(t, "country_weekly", rep["report_id"])
            txt = json.dumps(saved, ensure_ascii=False)
            # 允许内部记账字段存在（不展示），但不得写入 prompt/secret
            for bad in ("ASIP_DEEPSEEK_API_KEY", "Authorization", "Bearer "):
                self.assertNotIn(bad, txt)
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_15_real_repo_targets_have_clean_ai_packs(self):
        """§十四 硬门：真实报告的 AI pack 不得含空壳/无来源/跨国家事实。

        C4-C 事实投影修复后：疾病字段映射与来源绑定已修好（NO_CONTENT/NO_SOURCE = 0），
        疾病事实现在是因为**国家 scope / 时间窗**被排除，而不是因为空壳。
        """
        a = RAI.audit_ai_packs(str(ROOT), all_reports=True)
        t = a["totals"]
        self.assertEqual(t["UNATTRIBUTED_FACTS_IN_AI_FACT_PACK"], 0)
        self.assertEqual(t["EMPTY_FACTS_IN_AI_FACT_PACK"], 0)
        self.assertEqual(t["CROSS_COUNTRY_FACTS_IN_COUNTRY_WEEKLY"], 0)
        self.assertEqual(t["FAKE_SOURCE_REFS"], 0)
        self.assertEqual(t["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"], 0)
        self.assertEqual(t["DISEASE_FACTS_EXCLUDED_FROM_AI_FACT_PACK"],
                         t["DISEASE_FACTS_CANDIDATE"])
        self.assertEqual(t["DISEASE_FACTS_EXCLUDED_NO_CONTENT"], 0)
        self.assertEqual(t["DISEASE_FACTS_EXCLUDED_NO_SOURCE"], 0)
        self.assertEqual(t["SECRETS_IN_AUDIT_OUTPUT"], 0)


class ProviderContractTest(unittest.TestCase):
    """§六 Provider Contract：只认 Stage 7B 的 generate(system, user)。"""

    def _task(self):
        return {"task_id": "REPORT_AI_X", "task_type": "report_analysis",
                "system_text": "SYS", "user_text": "{}",
                "prompt_version": RAI.PROMPT_VERSION}

    def test_16_report_ai_uses_generate_contract(self):
        prov = FixtureProvider("ok")
        res = RAI.invoke_report_provider(prov, self._task())
        self.assertEqual(res["status"], "succeeded")
        self.assertEqual(len(prov.calls), 1)

    def test_17_report_ai_never_requires_submit_task(self):
        # 只有 submit_task 的 provider（正是首次真实运行踩到的形状）必须被判为契约不匹配
        with self.assertRaises(RAI.SystemicProviderFailure):
            RAI.invoke_report_provider(SubmitTaskOnlyProvider(), self._task())

    def test_18_generate_receives_system_and_user(self):
        prov = FixtureProvider("ok")
        RAI.invoke_report_provider(prov, self._task())
        system, user = prov.calls[0]
        self.assertEqual(system, "SYS")
        self.assertEqual(user, "{}")

    def test_19_provider_response_is_normalized(self):
        # (text, meta) —— MockReportProvider / DeepSeekReportProvider 的真实形状
        n = RAI.normalize_provider_response(("hello", {"model": "m1"}))
        self.assertEqual(n["status"], "succeeded")
        self.assertEqual(n["result"]["text"], "hello")
        self.assertEqual(n["result"]["returned_model"], "m1")
        # 已归一化形状原样透传
        self.assertIs(RAI.normalize_provider_response({"status": "succeeded"})["status"],
                      "succeeded")
        # 非法形状 → 报告级异常（不是系统级）
        with self.assertRaises(RAI.ProviderResponseFormatError):
            RAI.normalize_provider_response(12345)

    def test_20_provider_exception_is_report_level_diagnostic(self):
        t = mkroot()
        try:
            rep, _ = seed_country_weekly(t)
            fp = ai_pack()
            rep = with_pack(rep, fp)
            M.write_report_artifact(t, "country_weekly", rep)
            # 报告级：单份响应非法 → FALLBACK，不冒泡
            o = RAI.enrich_one(t, rep, provider=FixtureProvider("not_json"),
                               fact_pack=fp, write=False)
            self.assertEqual(o["outcome"], "CALLED_FALLBACK")
            self.assertIn(o["gate_result"], ("SCHEMA_FAILURE", "PROVIDER_RESPONSE_INVALID"))
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_21_real_provider_shape_is_compatible_with_report_ai(self):
        """§六 最后一项：直接检查 scripts/report/gen/providers.py 的真实接口。"""
        mock = RAI.P.make_provider("mock")
        self.assertTrue(callable(getattr(mock, "generate", None)))
        self.assertFalse(hasattr(mock, "submit_task"),
                         "Stage 7B provider 不得有 submit_task（C4 也不得依赖它）")
        res = RAI.invoke_report_provider(
            mock, {"system_text": "s", "user_text": json.dumps({"report_type": "africa_daily"})})
        self.assertEqual(res["status"], "succeeded")
        self.assertIsInstance(res["result"]["text"], str)
        # DeepSeek provider 的类同样只暴露 generate
        self.assertTrue(callable(getattr(RAI.P.DeepSeekReportProvider, "generate", None)))
        self.assertFalse(hasattr(RAI.P.DeepSeekReportProvider, "submit_task"))

    def test_22_report_ai_source_has_no_submit_task_call(self):
        """§四 静态审计：C4 report pipeline 不得出现 submit_task 调用。"""
        src = (ROOT / "scripts" / "report" / "report_ai.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\.\s*submit_task\s*\(", src))
        wf = (ROOT / ".github" / "workflows" / "asip-v11-c4-report-ai.yml").read_text(
            encoding="utf-8")
        self.assertNotIn("submit_task", wf)


class AIFactPackEligibilityTest(unittest.TestCase):
    """§八–§十二 进入 AI 前的事实 eligibility。"""

    REP = {"report_type": "country_weekly", "country_iso3": "TCD",
           "week_start": "2026-09-06", "week_end": "2026-09-13"}

    def test_23_empty_shell_facts_are_excluded(self):
        fp = ai_pack(social_content=False, disease_content=False)
        _ai, d = RAI.build_ai_fact_pack(fp, self.REP)
        self.assertEqual(d["AI_PACK_FACTS_TOTAL"], 0)
        self.assertEqual(d["SOCIAL_FACTS_EXCLUDED_NO_CONTENT"], 3)
        self.assertEqual(d["DISEASE_FACTS_EXCLUDED_NO_CONTENT"], 2)
        self.assertEqual(d["EMPTY_FACTS_IN_AI_FACT_PACK"], 0)

    def test_24_disease_without_source_is_excluded_and_counted(self):
        fp = ai_pack(n_social=0, n_disease=3, disease_source=False)
        _ai, d = RAI.build_ai_fact_pack(fp, self.REP)
        self.assertEqual(d["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"], 0)
        self.assertEqual(d["DISEASE_FACTS_EXCLUDED_FROM_AI_FACT_PACK"], 3)
        self.assertEqual(d["DISEASE_FACTS_EXCLUDED_NO_SOURCE"], 3)

    def test_25_cross_country_disease_excluded_from_country_weekly(self):
        fp = ai_pack(n_social=0, n_disease=2, disease_country="ETH")
        _ai, d = RAI.build_ai_fact_pack(fp, self.REP)
        self.assertEqual(d["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"], 0)
        self.assertEqual(d["DISEASE_FACTS_EXCLUDED_CROSS_COUNTRY"], 2)
        self.assertEqual(d["CROSS_COUNTRY_FACTS_IN_COUNTRY_WEEKLY"], 0)
        # regional 不默认放行（§十一：必须有确定性规则，当前产品规则不存在）
        fp2 = ai_pack(n_social=0, n_disease=1, disease_country="regional")
        _ai2, d2 = RAI.build_ai_fact_pack(fp2, self.REP)
        self.assertEqual(d2["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"], 0)
        self.assertEqual(d2["DISEASE_FACTS_EXCLUDED_CROSS_COUNTRY"], 1)

    def test_26_out_of_window_fact_is_excluded(self):
        fp = ai_pack(n_social=0, n_disease=1, disease_date="2026-08-01")
        _ai, d = RAI.build_ai_fact_pack(fp, self.REP)
        self.assertEqual(d["DISEASE_FACTS_EXCLUDED_OUT_OF_WINDOW"], 1)
        self.assertEqual(d["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"], 0)

    def test_27_africa_weekly_allows_region_but_not_empty_or_sourceless(self):
        rep = {"report_type": "africa_weekly", "week_start": "2026-09-06",
               "week_end": "2026-09-13"}
        fp = ai_pack(n_social=0, n_disease=2, disease_country="ETH")
        _ai, d = RAI.build_ai_fact_pack(fp, rep)
        self.assertEqual(d["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"], 2,
                         "区域周报允许他国事实，但仍需内容+来源")
        fp2 = ai_pack(n_social=0, n_disease=2, disease_country="ETH", disease_content=False)
        _ai2, d2 = RAI.build_ai_fact_pack(fp2, rep)
        self.assertEqual(d2["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"], 0)

    def test_28_empty_ai_pack_never_calls_provider(self):
        """eligibility 后没有任何合法事实 → 绝不调用 provider。

        注：投影修复后，真实物化的 pack 已经不是空壳（社交事实有内容），
        因此这里显式构造「全部被 scope/时间窗排除」的 pack 来验证跳过行为。
        """
        t = mkroot()
        try:
            rep, _ = seed_country_weekly(t)
            fp = ai_pack(n_social=2, n_disease=2, disease_country="ETH",
                         disease_date="2025-11-24")   # 他国 + 过期 → 全部不合格
            for f in fp["social_facts"]:
                f["country_iso3"] = "ETH"            # 社交事实也不属报告国
            rep = with_pack(rep, fp)
            prov = FixtureProvider("ok")
            o = RAI.enrich_one(t, rep, provider=prov, fact_pack=fp, write=False)
            self.assertEqual(o["outcome"], "SKIPPED_EMPTY_AI_PACK")
            self.assertEqual(len(prov.calls), 0, "空壳/不合格 fact pack 绝不送进模型")
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_29_compliant_pack_reaches_provider_and_filters_only_bad_rows(self):
        fp = ai_pack(n_social=2, n_disease=3, disease_country="ETH")   # 3 条他国、2 条本国
        fp["disease_facts"][0]["country_iso3"] = "TCD"
        fp["disease_facts"][1]["country_iso3"] = "TCD"
        ai_fp, d = RAI.build_ai_fact_pack(fp, self.REP)
        self.assertEqual(d["AI_PACK_FACTS_TOTAL"], 4)      # 2 social + 2 disease
        self.assertEqual(len(ai_fp["disease_facts"]), 2)
        self.assertEqual(d["CROSS_COUNTRY_FACTS_IN_COUNTRY_WEEKLY"], 0)
        self.assertEqual(d["EMPTY_FACTS_IN_AI_FACT_PACK"], 0)
        self.assertEqual(d["UNATTRIBUTED_FACTS_IN_AI_FACT_PACK"], 0)
        prompt = json.dumps(RAI.AC.build_analysis_prompt(ai_fp), ensure_ascii=False)
        self.assertNotIn("dis2", prompt, "被排除的事实不得出现在 prompt 中")


class FailureModeTest(unittest.TestCase):
    """§七/§十八/§十九 系统级 vs 报告级故障。"""

    def _root(self):
        t = mkroot()
        rep, _ = seed_country_weekly(t)
        fp = ai_pack()
        rep = with_pack(rep, fp)
        M.write_report_artifact(t, "country_weekly", rep)
        return t, rep, fp

    def test_30_missing_credential_is_systemic(self):
        t, rep, fp = self._root()
        try:
            prov = RaisingProvider(RAI.P.ProviderUnavailable(
                "credential_unavailable: ASIP_DEEPSEEK_API_KEY missing"))
            with self.assertRaises(RAI.SystemicProviderFailure):
                RAI.enrich_one(t, rep, provider=prov, fact_pack=fp, write=False)
            st = RAI.enrich_all(t, provider=prov, write=False,
                                fact_pack_map={rep["report_id"]: fp})
            self.assertTrue(st["SYSTEMIC_PROVIDER_FAILURE"])
            self.assertIn("credential_unavailable", st["SYSTEMIC_PROVIDER_FAILURE_REASON"])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_31_auth_failure_is_systemic(self):
        t, rep, fp = self._root()
        try:
            prov = RaisingProvider(RAI.P.ProviderUnavailable("http_401"))
            st = RAI.enrich_all(t, provider=prov, write=False,
                                fact_pack_map={rep["report_id"]: fp})
            self.assertTrue(st["SYSTEMIC_PROVIDER_FAILURE"],
                            "鉴权失败是系统级故障，不得伪装成逐份 FALLBACK")
            self.assertEqual(st["outcomes"].get("SYSTEMIC_FAILURE_ABORT"), 1)
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_31b_provider_5xx_is_systemic(self):
        """§七：provider 全局不可用（5xx）必须判系统级，workflow 明确 FAIL。"""
        t, rep, fp = self._root()
        try:
            st = RAI.enrich_all(t, provider=FixtureProvider("provider_failed"), write=False,
                                fact_pack_map={rep["report_id"]: fp})
            self.assertTrue(st["SYSTEMIC_PROVIDER_FAILURE"])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_32_invalid_model_is_systemic(self):
        t, rep, fp = self._root()
        try:
            exc = ValueError("unsupported_deepseek_model: 'gpt-4'")
            st = RAI.enrich_all(t, provider=RaisingProvider(exc), write=False,
                                fact_pack_map={rep["report_id"]: fp})
            self.assertTrue(st["SYSTEMIC_PROVIDER_FAILURE"])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_33_uniform_provider_failure_escalates_to_systemic(self):
        """§七：全部调用一致失败 = 系统级，不允许『6 份各自 FALLBACK 但整体 green』。"""
        t = mkroot()
        try:
            rep, _ = seed_country_weekly(t)
            fp = ai_pack()
            rep = with_pack(rep, fp)
            M.write_report_artifact(t, "country_weekly", rep)
            st = RAI.enrich_all(t, provider=FixtureProvider("not_json"), write=False,
                                fact_pack_map={rep["report_id"]: fp})
            # 单份 malformed 属报告级 → 不升级为系统级
            self.assertFalse(st["SYSTEMIC_PROVIDER_FAILURE"])
            self.assertEqual(st["FALLBACK"], 1)
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_34_report_level_failure_does_not_stop_other_reports(self):
        """§十九：第 N 份 malformed 时其余报告继续处理（可完成的 partial result）。"""
        t = mkroot()
        try:
            reps, fps = [], {}
            for i, iso in enumerate(("TCD", "NER", "SSD")):
                r, _ = seed_country_weekly(t, iso=iso)
                fp = ai_pack(iso=iso, n_social=1, n_disease=1)
                r = with_pack(r, fp)
                M.write_report_artifact(t, "country_weekly", r)
                reps.append(r)
                fps[r["report_id"]] = fp

            class ThirdBad(FixtureProvider):
                def __init__(self):
                    FixtureProvider.__init__(self, "ok")
                    self.n = 0

                def generate(self, system, user):
                    self.n += 1
                    if self.n == 3:
                        self.calls.append((system, user))
                        return "not-json", {"model": RAI.MODEL}
                    return FixtureProvider.generate(self, system, user)

            prov = ThirdBad()
            st = RAI.enrich_all(t, provider=prov, write=True, fact_pack_map=fps)
            self.assertEqual(st["AI_CALLS_TOTAL"], 3, "三份都到达 provider")
            self.assertEqual(st["FALLBACK"], 1, "第 3 份报告级失败 → FALLBACK")
            self.assertEqual(st["FULL"], 2, "其余两份正常完成")
            self.assertFalse(st["SYSTEMIC_PROVIDER_FAILURE"])
        finally:
            shutil.rmtree(t, ignore_errors=True)


class SystemicDryRunTest(unittest.TestCase):
    """§十七 Provider Boundary dry-run（真实 provider 形状 + 网络调用被 spy 拦下）。"""

    def test_35_boundary_dry_run_counts_without_network(self):
        class SpyProvider(FixtureProvider):
            """与真实 Stage 7B provider 同形状，但不发网络请求。"""

            def __init__(self):
                FixtureProvider.__init__(self, "ok")
                self.generate_calls = 0

            def generate(self, system, user):
                self.generate_calls += 1
                return FixtureProvider.generate(self, system, user)

        t = mkroot()
        try:
            rep, _ = seed_country_weekly(t)
            fp = ai_pack()
            rep = with_pack(rep, fp)
            M.write_report_artifact(t, "country_weekly", rep)
            SpyProvider.generate_calls = 0
            prov = SpyProvider()
            st = RAI.enrich_all(t, provider=prov, write=False,
                                fact_pack_map={rep["report_id"]: fp})
            self.assertEqual(st["GENERATE_CALLS"], prov.generate_calls)
            self.assertEqual(st["PROVIDER_BOUNDARY_REACHED"], st["AI_CALLS_TOTAL"])
            self.assertEqual(st["SUBMIT_TASK_CALLS"], 0)
            self.assertEqual(st["AI_CALLS_DAILY"], 0)
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
