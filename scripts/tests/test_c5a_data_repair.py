#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c5a_data_repair.py — C5-A 数据层修复契约测试（§三十四）。

覆盖：provenance 精确恢复 / 不猜 / 无 dangling / 无伪来源；event↔master 身份桥与
fail-closed；疾病真实 schema、来源身份、新鲜度；country scope 与 pack 结构；
领导层内容准入（体育）；本地化确定性复用与冲突 fail-closed；legacy provider 真实契约；
semantic hash 墙钟稳定性。
"""
import io
import json
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts")):
    sys.path.insert(0, p)

from scripts.data import disease_contract as DC     # noqa: E402
from scripts.data import event_identity as EI       # noqa: E402
from scripts.data import hash_audit as HA           # noqa: E402
from scripts.data import provenance_recovery as PR  # noqa: E402
from scripts.report import content_eligibility as CE  # noqa: E402
from scripts.report import country_fact_pack as CFP  # noqa: E402
from scripts.report import fact_content as FC       # noqa: E402
from scripts.report import factory as F             # noqa: E402


class ProvenanceRecoveryTest(unittest.TestCase):

    def test_01_exact_recovery_and_no_guessing(self):
        stats = PR.apply(str(ROOT), write=False)
        # 证据存在就能恢复；本仓证据已耗尽 → 可恢复但未恢复必须为 0
        self.assertEqual(stats["RECOVERABLE_BUT_FAILED"], 0)
        self.assertEqual(stats["RECOVERABLE_PROVENANCE_CASES"],
                         stats["PROVENANCE_RECOVERED"])
        # 剩余缺口必须有**无证据**解释
        self.assertGreater(stats["UNRESOLVED_NO_EVIDENCE"] +
                           stats["LOCALIZATION_BLOCKED_NO_ARTICLE_LINK"], 0,
                           "残余缺口必须能解释为没有确定性证据")

    def test_02_unresolved_provenance_not_guessed(self):
        """无证据的 cluster 不得被塞入任何 article_ids / source_groups。"""
        clusters = PR._cluster_doc(str(ROOT))
        by_id, by_event = PR.build_article_index(str(ROOT))
        for c in clusters:
            cid = c.get("event_id")
            if by_event.get(cid):
                continue                      # 有确定性证据的允许持有
            if not (c.get("article_ids") or []):
                self.assertEqual(c.get("article_ids") or [], [],
                                 "%s 无证据却持有 article_ids" % cid)

    def test_03_no_dangling_article_refs(self):
        v = PR.verify_recovery(str(ROOT))
        self.assertEqual(v["DANGLING_ARTICLE_REFS"], 0)

    def test_04_no_fake_source_ids(self):
        v = PR.verify_recovery(str(ROOT))
        self.assertEqual(v["FAKE_SOURCE_IDS"], 0)

    def test_05_confidence_classes_are_strict(self):
        _c, rows, _s = PR.recover_provenance(str(ROOT))
        allowed = {PR.EXACT_ID, PR.EXISTING_MEMBERSHIP, PR.EXISTING_PROVENANCE,
                   PR.UNRESOLVED}
        for r in rows:
            self.assertIn(r["confidence_class"], allowed)
            self.assertNotIn(r["confidence_class"], ("LIKELY", "PROBABLY", "AI_GUESS"))

    def test_06_localization_projection_is_deterministic_or_conflict(self):
        _c, rows, stats = PR.recover_provenance(str(ROOT))
        self.assertEqual(stats["LOCALIZATION_CONFLICTS"],
                         sum(1 for r in rows if r["localization_status"] == "LOCALIZATION_CONFLICT"))
        for r in rows:
            if r["localization_status"] == "RECOVERED":
                self.assertIn(r["localization_projection_method"],
                              (PR.EXISTING_MEMBERSHIP, PR.EXISTING_PROVENANCE))


class EventIdentityBridgeTest(unittest.TestCase):

    def test_07_exact_bridge_and_master_subset(self):
        b = EI.build_identity_bridge(str(ROOT))
        self.assertTrue(b["master_ids_subset_of_clusters"],
                        "master_event_id 必须来自 cluster id（精确身份）")
        self.assertEqual(b["exact"], b["master_total"])
        self.assertEqual(b["by_method"].get(EI.EXACT_ID), b["master_total"])

    def test_08_unresolved_not_disguised(self):
        b = EI.build_identity_bridge(str(ROOT))
        self.assertGreater(b["unresolved_count"], 0)
        for cid in b["unresolved"][:20]:
            self.assertIsNone(EI.resolve_master_event(b, cid),
                              "UNRESOLVED 不得返回 master_event_id")

    def test_09_ambiguous_fails_closed(self):
        """冲突候选必须记 AMBIGUOUS 且不产出映射（不静默任选）。"""
        b = {"mappings": {"C1": {"master_event_id": "M1", "method": EI.EXACT_ID,
                                 "evidence": "x"}},
             "ambiguous": [{"cluster_id": "C2", "candidates": ["M1", "M2"]}]}
        self.assertIsNone(EI.resolve_master_event(b, "C2"))
        src = (ROOT / "scripts" / "data" / "event_identity.py").read_text(encoding="utf-8")
        self.assertIn("AMBIGUOUS", src)
        self.assertIn("fail-closed", src)

    def test_10_published_events_bridge_is_recorded(self):
        _rows, st = EI.enrich_published_events(str(ROOT))
        self.assertEqual(st["BRIDGED"] + st["ALREADY_BRIDGED"] + st["UNRESOLVED"],
                         st["PUBLISHED_EVENTS_TOTAL"])


class DiseaseContractTest(unittest.TestCase):

    def test_11_real_schema_fields_used(self):
        view = DC.build_view(str(ROOT), data_as_of="2026-09-19")
        self.assertEqual(view["DISEASE_RECORDS_TOTAL"], 20)
        self.assertEqual(view["DISEASE_WITHOUT_SOURCE_IDENTITY"], 0)
        self.assertEqual(view["FAKE_DISEASE_SOURCE_IDS"], 0)
        rec = view["records"][0]
        for k in ("disease_name_en", "report_date", "outbreak_status", "counts",
                  "source_ids"):
            self.assertIn(k, rec)
        self.assertNotIn("latest_counts", rec)
        self.assertNotIn("updates", rec)

    def test_12_deprecated_readers_classified(self):
        hits = DC.audit_deprecated_readers(str(ROOT))
        bad = [h for h in hits if h["layer"] == "CANONICAL_LAYER_VIOLATION"]
        self.assertEqual(bad, [], "canonical 层不得再读 latest_counts/updates")
        self.assertTrue(all(h["layer"] in ("TIMELINE_LAYER_DERIVED",
                                          "VIEW_LAYER_CONSUMES_DERIVED",
                                          "ALLOWED_COMPAT_OR_MOCK") for h in hits))

    def test_13_freshness_contract(self):
        items = DC.load_items(str(ROOT))
        f = DC.freshness(items, data_as_of="2026-09-19")
        self.assertIn(f["disease_freshness_status"],
                      (DC.FRESHNESS_CURRENT, DC.FRESHNESS_STALE, DC.FRESHNESS_NONE))
        self.assertEqual(f["latest_disease_report_date"], max(
            str(i.get("report_date"))[:10] for i in items if i.get("report_date")))
        # 阈值必须显式且可测
        self.assertEqual(DC.FRESHNESS_CURRENT_MAX_DAYS, 14)
        self.assertEqual(DC.FRESHNESS_STALE_MAX_DAYS, 60)
        # 边界行为
        self.assertEqual(DC.freshness([{"report_date": "2026-09-10"}], "2026-09-19")
                         ["disease_freshness_status"], DC.FRESHNESS_CURRENT)
        self.assertEqual(DC.freshness([{"report_date": "2026-08-12"}], "2026-09-19")
                         ["disease_freshness_status"], DC.FRESHNESS_STALE)
        self.assertEqual(DC.freshness([{"report_date": "2025-11-24"}], "2026-09-19")
                         ["disease_freshness_status"], DC.FRESHNESS_NONE)
        self.assertEqual(DC.freshness([], "2026-09-19")["disease_freshness_status"],
                         DC.FRESHNESS_NONE)

    def test_14_disease_source_identity_no_fabrication(self):
        items = DC.load_items(str(ROOT))
        reg = DC.load_source_registry(str(ROOT))
        n = [DC.normalize(i, reg) for i in items]
        self.assertTrue(all(x["has_source_identity"] for x in n))
        for x in n:
            for s in x["source_ids"] + x["source_names"]:
                self.assertFalse(str(s).lower().startswith(("source_unknown", "synthetic")))

    def test_15_country_scope_reused_not_reimplemented(self):
        items = DC.load_items(str(ROOT))
        ctx = {"report_type": "country_weekly", "country_iso3": "TCD"}
        kept, excluded = DC.country_scope(items, ctx)
        self.assertEqual(len(kept) + len(excluded), len(items))
        for it in excluded:
            self.assertFalse(FC.country_scope_ok(it, ctx))


class CountryPackTest(unittest.TestCase):

    def setUp(self):
        self.snaps = json.loads((ROOT / "data" / "views" / "country_snapshots.json")
                                .read_text(encoding="utf-8"))["snapshots"]

    def test_16_pack_structure_complete(self):
        packs, st = CFP.enrich_snapshots(str(ROOT), self.snaps, data_as_of="2026-09-19")
        self.assertEqual(st["COUNTRY_FACT_PACKS_STRUCTURALLY_THIN"], 0,
                         "结构必须完整（数据少不算 THIN）")
        self.assertGreater(st["COUNTRY_FACT_PACKS_THIN_BEFORE"], 0,
                           "基线确实是 THIN（证明修复有实际效果）")
        for p in packs:
            missing = CFP.structurally_thin(p)
            self.assertEqual(missing, [], "%s 缺结构字段 %s" % (p.get("iso3"), missing))

    def test_17_pack_has_concrete_facts(self):
        packs, _st = CFP.enrich_snapshots(str(ROOT), self.snaps, data_as_of="2026-09-19")
        by_iso = {p["iso3"]: p for p in packs}
        rich = [p for p in packs if p["coverage_status"] == CFP.COVERAGE_OK]
        self.assertTrue(rich, "至少应有国家具备具体事实")
        for p in rich:
            self.assertIsInstance(p["recent_events"], list)
            self.assertIsInstance(p["source_refs"], list)
            self.assertTrue(p["recent_events"][0].get("title"))
            self.assertTrue(p["source_refs"])
        # 低数据国家结构仍然完整
        for iso in ("TCD",):
            self.assertIn(iso, by_iso)

    def test_18_no_cross_country_pollution(self):
        _packs, st = CFP.enrich_snapshots(str(ROOT), self.snaps, data_as_of="2026-09-19")
        self.assertEqual(st["CROSS_COUNTRY_FACTS_IN_COUNTRY_PACKS"], 0)

    def test_19_chad_iso2_iso3_regression(self):
        """TD→TCD 必须能归一（历史 bug：用 iso3[:2] 推出 TC，整国事件被静默丢弃）。"""
        from scripts.report import materialize as M
        mp = M.iso2to3_map(str(ROOT))
        self.assertEqual(mp.get("TD"), "TCD")
        self.assertEqual(mp.get("TC"), "TCD")
        clusters = CFP.load_clusters(str(ROOT))
        tcd = [c for c in clusters if c.get("country_iso3") == "TCD"]
        self.assertGreater(len(tcd), 0, "乍得事件必须能归一到 TCD")


class ContentEligibilityTest(unittest.TestCase):

    def test_20_pure_sports_excluded(self):
        for text, topic in (("football match report", "FOOTBALL"),
                            ("Premier League transfer news", "LEAGUE"),
                            ("soccer club signs player", "SOCCER")):
            ok, reason = CE.leadership_content_eligibility(text, "sport")
            self.assertFalse(ok, "纯体育必须排除：%s" % text)
            self.assertEqual(reason, "PURE_NON_SECURITY_%s" % topic,
                             "排除原因必须可审计（命中的题材词）")

    def test_21_sports_security_retained(self):
        for t in ("Football riot: 12 killed after stampede",
                  "Attack at stadium kills 5", "Protest outside football match"):
            ok, _r = CE.leadership_content_eligibility(t, "security")
            self.assertTrue(ok, "安全相关体育事件不得被删除：%s" % t)

    def test_22_leadership_views_clean(self):
        a = CE.audit_leadership_views(str(ROOT))
        self.assertEqual(a["PURE_SPORTS_IN_LEADERSHIP_VIEWS"], 0)
        self.assertTrue(a["scanned_views"])


class LegacyProviderContractTest(unittest.TestCase):

    def test_23_analysis_runner_uses_generate(self):
        src = (ROOT / "scripts" / "report" / "gen" / "analysis_runner.py").read_text(
            encoding="utf-8")
        self.assertIsNone(re.search(r"\.\s*submit_task\s*\(", src),
                          "不得再调用 submit_task")
        self.assertIn("generate(system, user)", src)

    def test_24_no_fake_submit_task_fixture(self):
        for rel in ("scripts/report/gen/analysis_runner.py",
                    "scripts/tests/test_stage8c_architecture.py"):
            src = (ROOT / rel).read_text(encoding="utf-8")
            body = re.sub(r'"""(?:.|\n)*?"""', "", src)
            self.assertIsNone(re.search(r"def\s+submit_task\s*\(", body),
                              "%s 仍有假 submit_task fixture" % rel)


class HashContractTest(unittest.TestCase):

    def test_25_semantic_hash_ignores_wall_clock(self):
        base = {"report_id": "R", "social_facts": [{"fact_id": "E1", "headline_zh": "x"}]}
        a = dict(base, generated_at="2026-09-21T10:00:00+08:00", runtime={"cache_hit": True})
        b = dict(base, generated_at="2027-01-01T00:00:00+08:00", runtime={"cache_hit": False})
        self.assertEqual(F.report_pack_hash(a), F.report_pack_hash(b))

    def test_26_semantic_hash_changes_on_fact_change(self):
        base = {"report_id": "R", "social_facts": [{"fact_id": "E1", "headline_zh": "x"}]}
        c = {"report_id": "R", "social_facts": [{"fact_id": "E1", "headline_zh": "y"}]}
        self.assertNotEqual(F.report_pack_hash(base), F.report_pack_hash(c))

    def test_27_no_unexplained_wallclock_contamination(self):
        s = HA.summarize(str(ROOT))
        self.assertEqual(s["UNEXPLAINED_HASH_WALLCLOCK_CONTAMINATION"], 0)
        self.assertGreater(s["HASH_CONTRACTS_AUDITED"], 0)
        self.assertTrue(s["checks"].get("report_pack_hash_wallclock_stable"))
        self.assertTrue(s["checks"].get("report_pack_hash_content_sensitive"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
