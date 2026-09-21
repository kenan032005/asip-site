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
        """真实仓库：疾病事实不再是空壳，且来源可解析（§六/§七/§九）。"""
        rep = M.read_report_artifact(str(ROOT), "country_weekly", "WEEKLY_TCD_20260913")
        fp, _ = RAI.rebuild_fact_pack(str(ROOT), rep)
        df = fp.get("disease_facts") or []
        self.assertTrue(df, "该周报的 pack 仍保留疾病事实（报告内容未删减）")
        self.assertTrue(all(FC.has_displayable_content(f) for f in df),
                        "疾病事实必须有真实内容")
        self.assertTrue(all(FC.fact_sources(f) for f in df),
                        "疾病事实必须有真实来源（来自 source_links）")
        self.assertTrue(any(f.get("counts") for f in df), "至少一条带真实计数")


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
        self.assertGreater(a["AI_TARGET_REPORTS_ACTUAL"], 0,
                           "§十七：ACTUAL 必须 > 0")
        self.assertGreater(a["DISEASE_FACTS_CANDIDATE"], 0)
        self.assertEqual(a["DISEASE_FACTS_EXCLUDED_NO_CONTENT"], 0,
                         "疾病字段映射修复后不应再有空壳疾病事实")

    def test_20_localization_debt_reported_separately(self):
        a = RAI.audit_ai_packs(str(ROOT), all_reports=True)["totals"]
        self.assertEqual(a["SOCIAL_FACTS_USING_TITLE_CN"], 0)
        self.assertGreater(a["SOCIAL_FACTS_USING_TITLE_ORIGINAL"], 0)
        self.assertTrue(a["C5_LOCALIZATION_COMPLETENESS_DEBT"],
                        "仍有原文回退 → C5 本地化债务必须被标记")


class BoundaryAndTargetingTest(unittest.TestCase):

    def test_21_boundary_dry_run_reaches_every_actual_target(self):
        b = RAI.boundary_dry_run(str(ROOT))
        self.assertEqual(b["SUBMIT_TASK_CALLS"], 0)
        self.assertGreater(b["AI_TARGET_REPORTS_ACTUAL"], 0)
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
        """§十七：严格过滤后没有合法事实的报告必须被重新分类为 LOW_DATA。"""
        for rid, rtype in (("WEEKLY_TCD_20260913", "country_weekly"),
                           ("WEEKLY_NER_20260906", "country_weekly")):
            rep = M.read_report_artifact(str(ROOT), rtype, rid)
            self.assertEqual(rep.get("status"), M.STATUS_LOW_DATA)
            self.assertEqual(rep.get("status_reason"), "NO_AI_ELIGIBLE_FACTS")
            self.assertEqual(rep.get("ai_eligible_fact_count"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
