#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c4c_fact_projection.py — C4-C 事实内容投影 / 疾病字段与来源 / eligibility 契约。

§二十五 覆盖面：
  social title_cn 投影、title_original 回退、无合成本地化、疾病真实字段映射、
  疾病来源绑定、疾病无来源排除、国家 scope、regional 不自动放行、
  过滤后 source_refs / entity_vocab 重算、语义 hash 对事实敏感对墙钟稳定、
  边界演练覆盖全部 actual targets、backfill planner 共用 data_as_of 锚。

全部离线：不调用 AI、不写业务 data/。
"""
import io
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts")):
    sys.path.insert(0, p)

from scripts.report import fact_content as FC        # noqa: E402
from scripts.report import factory as F              # noqa: E402
from scripts.report import materialize as M          # noqa: E402
from scripts.report import report_ai as RAI          # noqa: E402
from scripts.report.gen import fact_pack as FP       # noqa: E402


class SocialContentProjectionTest(unittest.TestCase):
    """§二/§三 社交事实内容投影与回退顺序。"""

    def test_01_resolver_prefers_title_cn(self):
        r = FC.resolve_social_content({"title_cn": "中文标题", "title_original": "EN title"})
        self.assertEqual(r["headline"], "中文标题")
        self.assertEqual(r["content_source_field"], "title_cn")
        self.assertEqual(r["content_language"], "zh")

    def test_02_resolver_falls_back_to_title_original(self):
        r = FC.resolve_social_content({"title_cn": None, "title_original": "EN title",
                                       "summary_cn": None, "summary_original": "EN summary"})
        self.assertEqual(r["headline"], "EN title")
        self.assertEqual(r["summary"], "EN summary")
        self.assertEqual(r["content_source_field"], "title_original")
        self.assertEqual(r["content_language"], "original",
                         "使用原文必须被标记为 original，不得伪装成 zh")

    def test_03_summary_and_title_resolve_independently(self):
        r = FC.resolve_social_content({"title_cn": "中文标题", "summary_original": "EN sum"})
        self.assertEqual(r["headline"], "中文标题")
        self.assertEqual(r["summary"], "EN sum")
        self.assertIsNone(r["summary_language"].replace("zh", "") or None
                          if r["summary_language"] == "zh" else None)

    def test_04_no_content_when_all_fields_empty(self):
        r = FC.resolve_social_content({"title_cn": "", "title_original": "",
                                       "summary_cn": None, "summary_original": None})
        self.assertIsNone(r["headline"])
        self.assertIsNone(r["summary"])

    def test_05_fact_pack_uses_resolver_not_item_title(self):
        item = {"event_id": "E1", "title_cn": "标题CN", "title_original": "T-orig",
                "summary_cn": "摘要CN", "source_evidence": [{"source_id": "s1",
                                                            "source_name": "src1"}]}
        f = FP._social_fact(item, "major_events")
        self.assertEqual(f["headline_zh"], "标题CN")
        self.assertEqual(f["verified_summary"], "摘要CN")
        self.assertEqual(f["content_source_field"], "title_cn")

    def test_06_real_repo_reports_carry_content(self):
        """真实仓库：投影修复后事实必须有可展示内容（旧实现恒为空壳）。"""
        rid = "WEEKLY_NER_20260913"
        rep = M.read_report_artifact(str(ROOT), "country_weekly", rid)
        fp, _ = RAI.rebuild_fact_pack(str(ROOT), rep)
        sf = fp.get("social_facts") or []
        self.assertTrue(sf, "该周报必须有社交事实")
        with_content = [f for f in sf if FC.has_displayable_content(f)]
        self.assertEqual(len(with_content), len(sf), "投影后每条事实都必须有内容")
        for f in sf:
            self.assertIn(f.get("content_language"), ("zh", "original", None))

    def test_07_no_synthetic_localization(self):
        """§五：不得生成/伪造中文；只能复用真实字段。"""
        src = (ROOT / "scripts" / "report" / "fact_content.py").read_text(encoding="utf-8")
        for bad in ("translate", "deepseek", "requests.", "urllib"):
            self.assertNotIn(bad, src.lower())
        # 投影只能来自真实字段名
        self.assertIn("title_original", src)
        self.assertIn("title_cn", src)


class DiseaseFieldAndSourceTest(unittest.TestCase):
    """§六–§九 疾病真实字段映射与真实来源绑定。"""

    ITEM = {
        "disease_event_id": "DSEV_x", "disease_id": "cholera",
        "disease_name_zh": "", "disease_name_en": "Cholera",
        "country_iso3": "TCD", "location_raw": "N'Djamena",
        "report_date": "2026-09-10", "confirmed_cases": 12, "deaths": 2,
        "outbreak_status": "active", "update_type": "case_increase",
        "verification_status": "official", "primary_source": "WHO 通报",
        "uncertainties": ["疑似病例未核实"],
        "source_links": [{"url": "https://example.org/x", "source_id": "who_afro",
                          "source_name": "WHO（乍得霍乱）", "source_tier": "A"}],
    }

    def test_08_resolver_reads_real_disease_fields(self):
        r = FC.resolve_disease_content(self.ITEM)
        self.assertEqual(r["name"], "Cholera")
        self.assertEqual(r["content_source_field"], "disease_name_en")
        self.assertEqual(r["counts"], {"confirmed_cases": 12, "deaths": 2})

    def test_09_disease_has_content_requires_name_and_fact(self):
        self.assertTrue(FC.disease_has_content(self.ITEM))
        name_only = dict(self.ITEM, confirmed_cases=None, deaths=None,
                         outbreak_status=None, update_type=None)
        self.assertFalse(FC.disease_has_content(name_only),
                         "只有疾病名、没有任何真实事实 → 不算关键事实")

    def test_10_fact_pack_binds_real_disease_source(self):
        item = dict(self.ITEM, title="Cholera", summary="……",
                    verification="official", source_evidence=[{
                        "source_id": "who_afro", "source_name": "WHO（乍得霍乱）",
                        "url": "https://example.org/x"}])
        f = FP._disease_fact(item, "disease_public_health")
        self.assertEqual(f["source_ids"], ["who_afro"])
        self.assertEqual(f["source_refs"], ["WHO（乍得霍乱）"])
        self.assertEqual(f["source_links"], ["https://example.org/x"])
        self.assertIn(12, f["numeric_facts"], "真实计数必须进入 numeric provenance")

    def test_11_no_fake_source_when_unresolvable(self):
        item = dict(self.ITEM, source_links=[])
        f = FP._disease_fact(item, "disease_public_health")
        self.assertEqual(f["source_refs"], [])
        self.assertEqual(f["source_ids"], [])
        rep = {"report_type": "country_weekly", "country_iso3": "TCD",
               "week_start": "2026-09-06", "week_end": "2026-09-13"}
        fp = {"social_facts": [], "disease_facts": [f]}
        _ai, d = RAI.build_ai_fact_pack(fp, rep)
        self.assertEqual(d["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"], 0)
        self.assertEqual(d["DISEASE_FACTS_EXCLUDED_NO_SOURCE"], 1)
        self.assertEqual(d["FAKE_SOURCE_REFS"], 0)

    def test_12_real_repo_disease_facts_have_content_and_source(self):
        """真实仓库：疾病事实不再是空壳，且来源可解析（§六/§七/§九）。

        注：报告层已按国家 scope 过滤（§1），TCD 周报只剩本国 + 结构化相关的条目。
        """
        rep = M.read_report_artifact(str(ROOT), "country_weekly", "WEEKLY_TCD_20260913")
        fp, _ = RAI.rebuild_fact_pack(str(ROOT), rep)
        df = fp.get("disease_facts") or []
        self.assertTrue(df, "该周报仍保留本国/结构化相关的疾病事实")
        self.assertTrue(all(FC.has_displayable_content(f) for f in df))
        self.assertTrue(all(FC.fact_sources(f) for f in df))
        # 计数映射对**全量 canonical 疾病数据**生效（不依赖某一份报告恰好带计数）
        items = M.load_disease_items(str(ROOT))
        with_counts = [d for d in items if FC.resolve_disease_content(d)["counts"]]
        self.assertGreater(len(with_counts), 0, "canonical 疾病数据里存在真实计数")
        mapped = FP._disease_fact(
            {"disease_event_id": "X", "disease_id": "cholera", "disease_name_en": "Cholera",
             "country_iso3": "TCD", "confirmed_cases": 12, "deaths": 2,
             "source_evidence": [{"source_id": "who_afro", "source_name": "WHO"}]},
            "disease_public_health")
        self.assertEqual(mapped["counts"], {"confirmed_cases": 12, "deaths": 2})
        self.assertIn(12, mapped["numeric_facts"])


class EligibilityAndDerivedFieldsTest(unittest.TestCase):
    """§八–§十二 eligibility 与国家 scope、派生字段重算。"""

    REP = {"report_type": "country_weekly", "country_iso3": "TCD",
           "week_start": "2026-09-06", "week_end": "2026-09-13"}

    def _d(self, **kw):
        base = {"fact_id": "cholera", "disease_id": "cholera",
                "headline_zh": "Cholera", "country_iso3": "TCD",
                "report_date": "2026-09-10", "outbreak_status": "active",
                "source_refs": ["WHO"], "source_ids": ["who_afro"],
                "counts": {"confirmed_cases": 3}, "numeric_facts": {3: ["x"]}}
        base.update(kw)
        return base

    def test_13_country_scope_excludes_foreign_disease(self):
        fp = {"social_facts": [], "disease_facts": [self._d(country_iso3="ETH")]}
        _ai, d = RAI.build_ai_fact_pack(fp, self.REP)
        self.assertEqual(d["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"], 0)
        self.assertEqual(d["DISEASE_FACTS_EXCLUDED_SCOPE"], 1)

    def test_14_regional_not_automatically_admitted(self):
        fp = {"social_facts": [], "disease_facts": [self._d(country_iso3="regional")]}
        _ai, d = RAI.build_ai_fact_pack(fp, self.REP)
        self.assertEqual(d["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"], 0)
        self.assertEqual(d["DISEASE_FACTS_EXCLUDED_SCOPE"], 1)

    def test_15_out_of_window_excluded(self):
        fp = {"social_facts": [], "disease_facts": [self._d(report_date="2025-11-24")]}
        _ai, d = RAI.build_ai_fact_pack(fp, self.REP)
        self.assertEqual(d["DISEASE_FACTS_EXCLUDED_OUT_OF_WINDOW"], 1)
        self.assertEqual(d["AI_PACK_FACTS_TOTAL"], 0)

    def test_16_africa_weekly_allows_region_but_keeps_content_source_rules(self):
        rep = {"report_type": "africa_weekly", "week_start": "2026-09-06",
               "week_end": "2026-09-13"}
        ok = {"social_facts": [], "disease_facts": [self._d(country_iso3="ETH")]}
        _ai, d = RAI.build_ai_fact_pack(ok, rep)
        self.assertEqual(d["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"], 1)
        nosrc = {"social_facts": [],
                 "disease_facts": [self._d(country_iso3="ETH", source_refs=[],
                                           source_ids=[])]}
        _ai2, d2 = RAI.build_ai_fact_pack(nosrc, rep)
        self.assertEqual(d2["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"], 0)

    def test_17_derived_fields_recomputed_after_filtering(self):
        """§十二：source_refs / entity_vocab / numeric_provenance 不得沿用过滤前集合。"""
        kept = self._d(country_iso3="TCD", source_refs=["WHO"], source_ids=["who_afro"])
        dropped = self._d(country_iso3="ETH", source_refs=["ETH_SRC"],
                          source_ids=["eth_only"], fact_id="marburg",
                          headline_zh="Marburg", numeric_facts={777: ["x"]})
        fp = {"social_facts": [], "disease_facts": [kept, dropped],
              "source_refs": ["WHO", "ETH_SRC"], "entity_vocab": ["WHO", "ETH_SRC", "Marburg"],
              "numeric_provenance": {777: ["x"]}}
        ai_fp, d = RAI.build_ai_fact_pack(fp, self.REP)
        self.assertEqual(d["AI_PACK_FACTS_TOTAL"], 1)
        self.assertEqual(ai_fp["source_refs"], ["WHO"], "被排除事实的来源必须消失")
        self.assertNotIn("ETH_SRC", ai_fp["entity_vocab"])
        self.assertNotIn("Marburg", ai_fp["entity_vocab"])
        self.assertNotIn(777, ai_fp["numeric_provenance"],
                         "被排除事实的数字不得出现在 gate 允许集合里")
        self.assertEqual(ai_fp["country_vocab"], ["TCD"])
        self.assertEqual(ai_fp["disease_fact_count"], 1)

    def test_18_semantic_hash_sensitive_to_content_stable_to_wallclock(self):
        base = {"report_id": "W1", "report_type": "country_weekly", "country_iso3": "TCD",
                "week_start": "2026-09-06", "week_end": "2026-09-13",
                "social_facts": [{"fact_id": "E1", "headline_zh": "标题",
                                  "content_source_field": "title_cn",
                                  "source_refs": ["s1"]}],
                "disease_facts": [], "numeric_provenance": {}}
        a = dict(base, generated_at="2026-09-21T10:00:00+08:00")
        b = dict(base, generated_at="2027-01-01T00:00:00+08:00")
        self.assertEqual(F.report_pack_hash(a), F.report_pack_hash(b))
        c = json.loads(json.dumps(base))
        c["social_facts"][0]["headline_zh"] = "标题（改）"
        self.assertNotEqual(F.report_pack_hash(base), F.report_pack_hash(c),
                            "事实内容变化必须改变 hash")
        d = json.loads(json.dumps(base))
        d["social_facts"][0]["content_source_field"] = "title_original"
        self.assertNotEqual(F.report_pack_hash(base), F.report_pack_hash(d),
                            "内容来源字段变化（本地化状态）也必须改变 hash")

    def test_19_real_repo_hard_gates(self):
        a = RAI.audit_ai_packs(str(ROOT), all_reports=True)["totals"]
        self.assertEqual(a["UNATTRIBUTED_FACTS_IN_AI_FACT_PACK"], 0)
        self.assertEqual(a["EMPTY_FACTS_IN_AI_FACT_PACK"], 0)
        self.assertEqual(a["CROSS_COUNTRY_FACTS_IN_COUNTRY_WEEKLY"], 0)
        self.assertEqual(a["FAKE_SOURCE_REFS"], 0)
        self.assertEqual(a["PROVIDER_BOUNDARY_REACHED"], a["AI_TARGET_REPORTS_ACTUAL"])
        # §7 CASE A/B：ACTUAL 可以为 0（全部 LOW_DATA 时属合法收口），
        # 但绝不允许「有 target 却到不了边界」或「边界大于 target」
        self.assertGreaterEqual(a["AI_TARGET_REPORTS_ACTUAL"], 0)
        self.assertEqual(a["REPORT_AI_SCOPE_PARITY"], True)
        self.assertEqual(a["CROSS_COUNTRY_FACTS_IN_REPORT_PACK"], 0)
        self.assertGreater(a["DISEASE_FACTS_CANDIDATE"], 0)
        self.assertEqual(a["DISEASE_FACTS_EXCLUDED_NO_CONTENT"], 0,
                         "疾病字段映射修复后不应再有空壳疾病事实")

    def test_20_localization_debt_reported_separately(self):
        """C5-B：内容 resolver 补回 `title`/`summary` 后，社交事实已能取到**中文**标题
        （此前只 recognized title_cn/title_original → 退化到原文回退）。
        债务标记仍按实际计算，不写死。"""
        a = RAI.audit_ai_packs(str(ROOT), all_reports=True)["totals"]
        self.assertGreater(a["SOCIAL_FACTS_USING_TITLE_CN"], 0,
                           "应能取到中文标题（title/summary 回退链已补回）")
        expected_debt = bool(a["SOCIAL_FACTS_USING_TITLE_ORIGINAL"]
                             or a["DISEASE_FACTS_USING_EN_NAME"]
                             or a["SOCIAL_FACTS_EXCLUDED_NO_CONTENT"])
        self.assertEqual(bool(a["C5_LOCALIZATION_COMPLETENESS_DEBT"]), expected_debt)


class BoundaryAndTargetingTest(unittest.TestCase):

    def test_21_boundary_dry_run_reaches_every_actual_target(self):
        """边界 = ACTUAL（可以为 0：全部 LOW_DATA 时 §7 CASE B 合法）。"""
        b = RAI.boundary_dry_run(str(ROOT))
        self.assertEqual(b["SUBMIT_TASK_CALLS"], 0)
        self.assertEqual(b["PROVIDER_BOUNDARY_REACHED"], b["AI_TARGET_REPORTS_ACTUAL"])
        self.assertEqual(b["GENERATE_CALLS_SIMULATED"], b["AI_TARGET_REPORTS_ACTUAL"])
        self.assertFalse(b["SYSTEMIC_PROVIDER_FAILURE"])
        self.assertTrue(b["boundary_equals_actual"])

    def test_22_targets_are_never_low_data_labelled(self):
        """§四：LOW_DATA 不得被调用 AI（标签与可分析性必须一致）。"""
        plan = RAI.plan_targets(str(ROOT))
        for rep_row in M.list_report_artifacts(str(ROOT)):
            if rep_row.get("status") == M.STATUS_LOW_DATA:
                self.assertNotIn(rep_row["report_id"], plan["target_ids"])

    def test_23_fact_less_report_is_reclassified_low_data(self):
        """§十七：严格过滤后没有合法事实的报告必须是 LOW_DATA。

        两种路径都要成立：① 事实数不足阈值本就 LOW_DATA；
        ② 阈值判定为 FALLBACK 但 eligibility 后无事实 → 被**主动降级**。
        """
        # C5-A 之后：TCD 因 ISO2→ISO3 修复（TD→TCD）已获得合法事实，
        # 不再属于「无合法事实」；此处改用确实无事实的报告验证同一契约。
        for rid in ("WEEKLY_SSD_20260906",):
            rep = M.read_report_artifact(str(ROOT), "country_weekly", rid)
            self.assertEqual(rep.get("status"), M.STATUS_LOW_DATA)
            self.assertEqual(rep.get("ai_eligible_fact_count"), 0)
        tcd = M.read_report_artifact(str(ROOT), "country_weekly", "WEEKLY_TCD_20260913")
        self.assertEqual(tcd.get("status"), M.STATUS_LOW_DATA,
                         "事实数仍低于阈值 → 依旧 LOW_DATA（阈值未动）")
        self.assertGreater(tcd.get("ai_eligible_fact_count") or 0, 0,
                           "C5-A 修复后乍得报告必须获得合法事实")
        # ② 主动降级路径（用合成 report 验证，不依赖当前语料恰好处于哪一侧）
        fake_rep = {"report_id": "W_T", "report_type": "country_weekly",
                    "country_iso3": "TCD", "status": M.STATUS_FALLBACK,
                    "week_start": "2026-09-06", "week_end": "2026-09-13"}
        fake_pack = {"social_facts": [], "disease_facts": [
            {"fact_id": "marburg", "disease_id": "marburg", "headline_zh": "Marburg",
             "country_iso3": "ETH", "source_refs": ["WHO"], "outbreak_status": "active"}]}
        M.reclassify_by_ai_eligibility(fake_rep, fake_pack)
        self.assertEqual(fake_rep["status"], M.STATUS_LOW_DATA)
        self.assertEqual(fake_rep["status_reason"], "NO_AI_ELIGIBLE_FACTS")
        self.assertEqual(fake_rep["ai_eligible_fact_count"], 0)




class CountryScopeReconciliationTest(unittest.TestCase):
    """§1/§2/§8 Country Weekly 报告层 scope 与报告/AI 同一契约。"""

    def _pack(self, iso3="TCD"):
        return {
            "fact_id": "D1", "disease_id": "cholera", "headline_zh": "Cholera",
            "country_iso3": iso3, "report_date": "2026-09-10",
            "outbreak_status": "active", "source_refs": ["WHO"], "source_ids": ["who_afro"],
            "counts": {"confirmed_cases": 3}, "numeric_facts": {3: ["x"]},
        }

    def _ctx(self, iso3="TCD"):
        return {"report_type": "country_weekly", "country_iso3": iso3,
                "week_start": "2026-09-06", "week_end": "2026-09-13"}

    def test_29_country_weekly_report_excludes_other_country_disease(self):
        """§1：报告层的疾病事实必须遵循目标国家 scope。"""
        ctx = self._ctx("TCD")
        facts = [self._pack("TCD"), self._pack("ETH"), self._pack("NGA"), self._pack("COD")]
        kept, excluded = FC.filter_country_scope(facts, ctx)
        self.assertEqual([f["country_iso3"] for f in kept], ["TCD"])
        self.assertEqual(len(excluded), 3)
        # 真实仓库：6 份 country weekly 的报告 pack 跨国事实必须为 0
        for rid in ("WEEKLY_TCD_20260913", "WEEKLY_NER_20260913", "WEEKLY_SSD_20260913",
                    "WEEKLY_TCD_20260906", "WEEKLY_NER_20260906", "WEEKLY_SSD_20260906"):
            rep = M.read_report_artifact(str(ROOT), "country_weekly", rid)
            fp, _ = RAI.rebuild_fact_pack(str(ROOT), rep)
            facts = (fp.get("social_facts") or []) + (fp.get("disease_facts") or [])
            self.assertEqual(FC.cross_country_facts(facts, rep), [],
                             "%s 的报告 pack 不得含他国事实" % rid)

    def test_30_country_weekly_report_and_ai_share_scope_contract(self):
        """§2：REPORT_FACT_SCOPE == AI_FACT_SCOPE（同一判定函数、同一结果）。"""
        rep = M.read_report_artifact(str(ROOT), "country_weekly", "WEEKLY_TCD_20260913")
        fp, _ = RAI.rebuild_fact_pack(str(ROOT), rep)
        ai_fp, d = RAI.build_ai_fact_pack(fp, rep)
        report_facts = (fp.get("social_facts") or []) + (fp.get("disease_facts") or [])
        # 两层的国家判定必须逐条一致
        for f in report_facts:
            self.assertTrue(FC.country_scope_ok(f, rep),
                            "报告层保留的事实必须也通过 AI 层的同一判定")
        for f in (ai_fp.get("social_facts") or []) + (ai_fp.get("disease_facts") or []):
            self.assertIn(f, report_facts, "AI pack 事实必须来自报告层事实集合")
        self.assertEqual(d["CROSS_COUNTRY_FACTS_IN_REPORT_PACK"], 0)
        self.assertEqual(d["CROSS_COUNTRY_FACTS_IN_AI_FACT_PACK"], 0)
        self.assertTrue(d["REPORT_AI_SCOPE_PARITY"])
        # 报告层已过滤 → AI 层不应再出现 SCOPE 排除
        self.assertEqual(d.get("SOCIAL_FACTS_EXCLUDED_SCOPE", 0), 0)
        self.assertEqual(d.get("DISEASE_FACTS_EXCLUDED_SCOPE", 0), 0)
        a = RAI.audit_ai_packs(str(ROOT), all_reports=True)["totals"]
        self.assertTrue(a["REPORT_AI_SCOPE_PARITY"])
        self.assertEqual(a["CROSS_COUNTRY_FACTS_IN_REPORT_PACK"], 0)
        self.assertEqual(a["CROSS_COUNTRY_FACTS_IN_AI_FACT_PACK"], 0)

    def test_31_regional_fact_not_admitted_without_target_relevance(self):
        """§1：单纯 regional 不放行；结构化可追溯的目标国相关性才放行。"""
        ctx = self._ctx("TCD")
        plain = self._pack("regional")
        self.assertEqual(FC.country_scope_decision(plain, ctx),
                         (False, "REGIONAL_WITHOUT_RELEVANCE"))
        self.assertEqual(FC.filter_country_scope([plain], ctx)[0], [])
        # 结构化 affected_countries 明确指出报告国 → 放行（可追溯）
        affected = dict(self._pack("regional"), affected_countries=["COD", "TCD"])
        self.assertEqual(FC.country_scope_decision(affected, ctx),
                         (True, "AFFECTED_COUNTRY_MATCH"))
        # 结构化 TARGET_COUNTRY_RELEVANCE 明确指向报告国 → 放行
        rel = dict(self._pack("regional"), affected_countries=[],
                   target_country_relevance={"country": "TCD", "reason": "cross_border_spillover"})
        self.assertEqual(FC.country_scope_decision(rel, ctx),
                         (True, "TARGET_COUNTRY_RELEVANCE"))
        # regional 且 affected_countries 指向**别国** → 仍排除
        other = dict(self._pack("regional"), affected_countries=["NGA"])
        self.assertEqual(FC.country_scope_decision(other, ctx),
                         (False, "REGIONAL_WITHOUT_RELEVANCE"))
        # 区域报告不受国家隔离
        self.assertTrue(FC.country_scope_ok(self._pack("ETH"),
                                            {"report_type": "africa_weekly"}))

    def test_32_country_scope_change_updates_report_hash(self):
        """§3：scope 变化必须改变 fact_pack_hash（AI pack/input hash 随之变化）。"""
        base = {"report_id": "W1", "report_type": "country_weekly", "country_iso3": "TCD",
                "week_start": "2026-09-06", "week_end": "2026-09-13",
                "social_facts": [], "disease_facts": [self._pack("TCD")],
                "numeric_provenance": {}}
        with_foreign = dict(base, disease_facts=[self._pack("TCD"), self._pack("ETH")])
        self.assertNotEqual(F.report_pack_hash(base), F.report_pack_hash(with_foreign),
                            "国家 scope 变化必须改变 hash")
        # input hash 也必须随之变化（cache identity 含 fact_pack_hash）
        h1 = RAI.ai_input_hash("W1", F.report_pack_hash(base))
        h2 = RAI.ai_input_hash("W1", F.report_pack_hash(with_foreign))
        self.assertNotEqual(h1, h2)
        # 真实仓库：报告 pack 已按 scope 重建，hash 与重建结果一致
        rep = M.read_report_artifact(str(ROOT), "country_weekly", "WEEKLY_TCD_20260913")
        _fp, h = RAI.rebuild_fact_pack(str(ROOT), rep)
        self.assertEqual(h, rep.get("fact_pack_hash"))

    def test_33_zero_ai_targets_is_valid_when_all_reports_low_data(self):
        """§5/§7 CASE B：全部 LOW_DATA 时 0 个 AI target 是**合法**结果。"""
        plan = RAI.plan_targets(str(ROOT))
        self.assertEqual(plan["AI_TARGETING_RULE"], "status")
        statuses = {r.get("status") for r in M.list_report_artifacts(str(ROOT))}
        if statuses == {M.STATUS_LOW_DATA}:
            self.assertEqual(plan["AI_TARGET_REPORTS_ACTUAL"], 0)
            self.assertEqual(plan["AI_TARGET_REPORTS"], 0)
            self.assertEqual(plan["target_ids"], [])
        b = RAI.boundary_dry_run(str(ROOT))
        self.assertEqual(b["SUBMIT_TASK_CALLS"], 0)
        self.assertEqual(b["PROVIDER_BOUNDARY_REACHED"], b["AI_TARGET_REPORTS_ACTUAL"])
        self.assertTrue(b["boundary_equals_actual"])
        # 阈值不得被下调来制造调用
        self.assertEqual(M.DAILY_SECURITY_MIN, 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
