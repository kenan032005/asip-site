#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c2b_time_and_relevance.py — C2B §三十五（时间契约）+ §三十六（Relevance V2）。

时间契约 5 项 + Relevance V2 12 项，共 17 项。
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT / "scripts"), str(ROOT / "scripts" / "data"),
          str(ROOT / "scripts" / "collectors"), str(ROOT / "scripts" / "ops"),
          str(ROOT / "scripts" / "frontend")):
    sys.path.insert(0, p)

from ops import time_contract as tc          # noqa: E402
from country_runner import (relevance_stage1, relevance_detail, CLASSIFIER_VERSION,  # noqa: E402
                            EXCLUDE_SPORTS)
from data.quarantine_reeval import (relevance_reprocessable,  # noqa: E402
                                    is_reprocessable, classify)
from relevance_lexicon_v2 import (stats as lex_stats, flat_strong,  # noqa: E402
                                  ARABIC_RELEVANCE_SUPPORT, LEXICON, NEGATIVE_TERMS)

BJ = timezone(timedelta(hours=8))
RULE_CHANGE = datetime(2026, 9, 18, tzinfo=BJ)
W0 = datetime(2026, 9, 5, tzinfo=BJ).astimezone(timezone.utc)
W1 = (datetime(2026, 9, 18, 23, 59, 59, tzinfo=BJ)).astimezone(timezone.utc)


class TimeContractTest(unittest.TestCase):
    """§三十五 时间契约"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="c2b_tc_"))
        (self.tmp / "data" / "runtime" / "ops").mkdir(parents=True)
        (self.tmp / "data" / "canonical").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_01_data_as_of_not_null_after_successful_collection(self):
        """一次成功采集收尾后，契约必须写入非空 data_as_of 与 run_id"""
        doc = tc.write_contract(root=self.tmp, run_id="20260919T090000+0800_c2ba01",
                                processed_through="2026-09-19T09:05:00Z")
        self.assertIsNotNone(doc["data_as_of"])
        self.assertEqual(doc["run_id"], "20260919T090000+0800_c2ba01")
        iso, src, status = tc.resolve(self.tmp)
        self.assertIsNotNone(iso)
        self.assertEqual(status, tc.STATUS_EXPLICIT)
        self.assertEqual(src, "time_contract.processed_through")

    def test_02_data_as_of_uses_processed_window(self):
        """data_as_of 必须等于 processed_through（处理窗口截止），不是写文件的时间"""
        tc.write_contract(root=self.tmp, run_id="r1",
                          processed_through="2026-09-18T12:19:58Z")
        iso, src, status = tc.resolve(self.tmp)
        self.assertEqual(iso, "2026-09-18T12:19:58+00:00")
        doc = tc.read_contract(self.tmp)
        self.assertEqual(doc["last_successful_collection_at"], "2026-09-18T12:19:58Z")
        self.assertEqual(doc["processed_through"], "2026-09-18T12:19:58Z")

    def test_03_generated_at_not_used_as_data_as_of(self):
        """generated_at（构建时间）不得被当成 data_as_of；两者自始至终是两个字段"""
        doc = tc.write_contract(root=self.tmp, run_id="r2",
                                processed_through="2026-09-10T00:00:00Z")
        gen = tc.generated_at()
        self.assertNotEqual(gen, doc["data_as_of"])
        self.assertNotIn("generated_at", doc)
        iso, _src, _st = tc.resolve(self.tmp)
        self.assertEqual(iso, "2026-09-10T00:00:00+00:00")   # 不受调用时刻影响
        # 无法确定时必须是显式状态，而不是墙钟兜底
        empty = Path(tempfile.mkdtemp(prefix="c2b_tc_empty_"))
        try:
            iso2, src2, st2 = tc.resolve(empty)
            self.assertIsNone(iso2)
            self.assertEqual(st2, tc.STATUS_UNAVAILABLE)
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_04_backfill_reference_date_explicit(self):
        """历史回填的参考日必须显式记录来源，不得冒充 data_as_of"""
        doc = tc.write_contract(root=self.tmp, run_id="r3",
                                processed_through="2026-09-19T01:00:00Z",
                                backfill_reference_date="2026-09-18",
                                backfill_reference_source="wall_clock_asia_shanghai")
        self.assertEqual(doc["backfill_reference_date"], "2026-09-18")
        self.assertEqual(doc["backfill_reference_source"], "wall_clock_asia_shanghai")
        # 回填参考日与 data_as_of 是两个不同字段，不得混用
        self.assertNotEqual(doc["backfill_reference_date"], doc["data_as_of"][:10])

    def test_05_homepage_uses_data_as_of_contract(self):
        """前端时间契约必须读统一契约，并显式带 data_as_of_status"""
        import build_frontend_views as bfv
        tc.write_contract(root=self.tmp, run_id="r4",
                          processed_through="2026-09-11T06:00:00Z")
        out = bfv._time_contract(_dt("2026-09-11T06:00:00Z"), None,
                                 "2026-09-19T09:00:00Z",
                                 extra="time_contract[EXPLICIT]")
        self.assertEqual(out["data_as_of_status"], "EXPLICIT")
        self.assertEqual(out["data_as_of"], "2026-09-11T06:00:00+00:00")
        # 不可用状态必须显式暴露，而不是悄悄用生成时间
        out2 = bfv._time_contract(None, None, "2026-09-19T09:00:00Z",
                                  extra="UNAVAILABLE_EXPLICIT_FALLBACK")
        self.assertEqual(out2["data_as_of_status"], "UNAVAILABLE_EXPLICIT_FALLBACK")
        self.assertIsNone(out2["data_as_of"])
        # status 字段只能来自固定枚举，避免下游误读
        for st in (out["data_as_of_status"], out2["data_as_of_status"]):
            self.assertIn(st, ("EXPLICIT", "FALLBACK_CANONICAL",
                               "UNAVAILABLE_EXPLICIT_FALLBACK"))


def _dt(s):
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


class RelevanceV2Test(unittest.TestCase):
    """§三十六 Relevance Classifier V2"""

    def test_06_murder_is_security_relevant(self):
        for t in ("Mutilated corpse of woman found in Jos wildlife forest reserve",
                  "Police probe murder of two traders in Kano",
                  "Meurtre d'un commerçant à N'Djamena",
                  "Homicídio de dois comerciantes em Nampula"):
            self.assertTrue(relevance_stage1(t)[0] is True, t)

    def test_07_kidnapping_is_security_relevant(self):
        for t in ("Child kidnapping ring busted in Nairobi",
                  "Gunmen abduct 12 villagers in northern Nigeria",
                  "Enlèvement de trois humanitaires au Niger",
                  "Sequestro de dois professores em Cabo Delgado"):
            self.assertTrue(relevance_stage1(t)[0] is True, t)

    def test_08_drug_trafficking_is_security_relevant(self):
        for t in ("Court jails South African woman 25 years in Abuja for importing heroin",
                  "Cocaine seizure at Lagos port, two arrests",
                  "Saisie record de stupéfiants à Agadez",
                  "Apreensão de cocaína no porto de Maputo"):
            self.assertTrue(relevance_stage1(t)[0] is True, t)

    def test_09_armed_robbery_is_security_relevant(self):
        for t in ("Armed robbery suspects arrested in Lagos",
                  "Bandits raid market in Zamfara, two killed",
                  "Braquage à main armée dans une station-service",
                  "Assalto armado a um banco em Beira"):
            self.assertTrue(relevance_stage1(t)[0] is True, t)

    def test_10_violent_protest_is_security_relevant(self):
        for t in ("Violent protest erupts in Khartoum over fuel prices",
                  "Manifestations violentes à Niamey, plusieurs blessés",
                  "Protestos violentos em Maputo após detenções"):
            self.assertTrue(relevance_stage1(t)[0] is True, t)

    def test_11_disaster_is_security_relevant(self):
        for t in ("Flood displaces thousands in Cabo Delgado",
                  "Inondations meurtrières dans le Logone Oriental",
                  "Deslizamento mata onze pessoas em Sofala",
                  "Cholera outbreak spreads in three provinces"):
            self.assertTrue(relevance_stage1(t)[0] is True, t)

    def test_12_sports_attack_phrase_not_security_event(self):
        """§十四：体育语境里的 attack/shoot/defeat 不得进入安全 News"""
        for t in ("Nigeria attacks down the wing as Super Eagles press",
                  "England 0-3 Nigeria: Falconets cruise into World Cup quarter-finals",
                  "The striker shot wide after beating the offside trap",
                  "Team defeats rivals in the group stage fixture"):
            rel = relevance_stage1(t)[0]
            self.assertIsNot(rel, True, "must not be admitted: %s" % t)

    def test_13_entertainment_not_security_event(self):
        for t in ("Nollywood actress wins award at film festival",
                  "Cantor angolano lança novo álbum em Luanda",
                  "Fashion week opens in Nairobi with new designers",
                  "Dangote Petroleum Refinery IPO opens for subscription"):
            self.assertIsNot(relevance_stage1(t)[0], True, t)

    def test_14_french_security_terms(self):
        for t in ("Attaque armée dans la région du Lac Tchad",
                  "Embuscade contre un convoi militaire près d'Abala",
                  "Vingt-sept morts dans une inondation au Soudan"):
            self.assertTrue(relevance_stage1(t)[0] is True, t)

    def test_15_portuguese_security_terms(self):
        for t in ("Ataque armado deixa cinco mortos em Cabo Delgado",
                  "Tiroteio em Maputo faz três feridos",
                  "Cheias provocam deslocados em Sofala"):
            self.assertTrue(relevance_stage1(t)[0] is True, t)

    def test_16_old_relevance_hold_can_be_reprocessed_after_v2(self):
        """§十九：v1 产生的 relevance hold 可用 V2 重判；v2 产生的不行"""
        e = {"reason_code": "not_security_relevant", "detected_at": "2026-09-16T02:00:00Z",
             "url": "https://tchadinfos.com/2026/09/11/x", "title": "Corps retrouvé à Moundou"}
        ok, why = relevance_reprocessable(e, rule_change_at=RULE_CHANGE, window_start=W0,
                                          window_end=W1, approved_domains={"tchadinfos.com"},
                                          current_version="v2")
        self.assertTrue(ok, why)
        e2 = dict(e)
        e2["classifier_version"] = "v2"
        ok2, why2 = relevance_reprocessable(e2, rule_change_at=RULE_CHANGE, window_start=W0,
                                            window_end=W1,
                                            approved_domains={"tchadinfos.com"},
                                            current_version="v2")
        self.assertFalse(ok2)
        self.assertEqual(why2, "PRODUCED_UNDER_CURRENT_CLASSIFIER")

    def test_17_true_safety_hold_never_released(self):
        for code in ("privacy", "personal_data", "illegal_content", "safety_hold"):
            self.assertEqual(classify(code), "TRUE_SAFETY_HOLD")
            ok, why = is_reprocessable({"reason_code": code, "detected_at": "2026-07-01T00:00:00Z",
                                        "url": "https://tchadinfos.com/2026/09/11/x",
                                        "legacy_payload": {"published_time": "2026-09-11T03:00:00Z"}},
                                       rule_change_at=RULE_CHANGE, window_start=W0,
                                       window_end=W1, approved_domains={"tchadinfos.com"})
            self.assertFalse(ok)
            self.assertEqual(why, "TRUE_SAFETY_HOLD_NEVER_RELEASED")
        # V2 词表不得用于释放任何真安全 hold
        self.assertNotIn("safety_hold", (flat_strong() or [""]))
        self.assertNotIn("privacy", NEGATIVE_TERMS.get("sports", []))


class LexiconV2InvariantTest(unittest.TestCase):
    """V2 词表自身的不变量（§九/§十三/§十四）"""

    def test_18_lexicon_covers_required_categories_and_languages(self):
        need_cats = {"ARMED_CONFLICT", "TERRORISM_SECURITY", "CRIME_PUBLIC_SAFETY",
                     "CIVIL_UNREST", "POLITICAL_STABILITY", "DISASTER_EMERGENCY",
                     "BORDER_MIGRATION", "PUBLIC_HEALTH"}
        self.assertTrue(need_cats.issubset(set(LEXICON.keys())))
        for cat in need_cats:
            for lang in ("en", "fr", "pt"):
                self.assertTrue(LEXICON[cat].get(lang), "%s/%s empty" % (cat, lang))
        s = lex_stats()
        self.assertEqual(s["version"], CLASSIFIER_VERSION)
        self.assertGreater(s["strong_terms_total"], 200)
        # §十三：阿拉伯语在缺乏可靠分词前显式 DEFERRED
        self.assertEqual(ARABIC_RELEVANCE_SUPPORT, "DEFERRED")
        self.assertEqual(s["arabic_relevance_support"], "DEFERRED")

    def test_19_threshold_unchanged_and_version_marked(self):
        """门槛语义未变：仍要求至少一个“强信号”，弱信号单独出现不足以判定"""
        self.assertEqual(CLASSIFIER_VERSION, "v2")
        rel, score, matched, reason = relevance_stage1("Police patrol in the city centre")
        self.assertIsNot(rel, True)          # 只有弱信号 → 不判相关
        detail = relevance_detail("Armed robbery suspects arrested in Lagos")
        self.assertEqual(detail["classifier_version"], "v2")
        self.assertTrue(detail["relevant"] is True)
        self.assertIn("CRIME_PUBLIC_SAFETY", detail["categories"])
        # 体育短语已在排除族里（结构性防误判）
        self.assertIn("down the wing", EXCLUDE_SPORTS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
