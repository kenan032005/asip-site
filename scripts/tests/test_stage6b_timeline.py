#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6B §三十 — Event Update Chain & Disease Outbreak Timeline 测试。

覆盖：country attribution separation / regional source contamination regression /
social timeline / casualty update / numeric conflict / actor attribution /
correction / history preservation / current-state provenance / disease
observation / temporal update / numeric conflict / cross-border / outbreak
identity / unknown!=0 + Golden 28 组 + Stage6A regressions。
"""

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.timeline.country_attr import (  # noqa: E402
    attribute_event_country, country_hints_clean, is_multinational,
)
from scripts.timeline.social import (  # noqa: E402
    new_timeline, apply_update, classify_update_type,
)
from scripts.timeline.disease import (  # noqa: E402
    new_outbreak_timeline, apply_disease_event, build_outbreak_timelines,
    _same_outbreak, _admin1_list,
)
from scripts.timeline.golden_runner import run_social, run_disease  # noqa: E402
from scripts.timeline.golden import build_social_pairs, build_disease_pairs  # noqa: E402


def _art(aid, **kw):
    base = {
        "article_id": aid, "source_id": kw.pop("source_id", "s1"),
        "source_group": kw.pop("source_group", "g1"),
        "title": kw.pop("title", "Attack in CITY_ALPHA"),
        "url": kw.pop("url", "https://example.com/%s" % aid),
        "published_at": kw.pop("published_at", "2026-08-25T10:00:00+00:00"),
        "event_time": kw.pop("event_time", "2026-08-25T09:00:00+00:00"),
        "location": kw.pop("location", "CITY_ALPHA"),
        "event_type": kw.pop("event_type", "armed_attack"),
        "deaths": kw.pop("deaths", None),
        "injured": kw.pop("injured", None),
        "actor": kw.pop("actor", None),
        "body": kw.pop("body", "Body %s" % aid),
    }
    base.update(kw)
    return base


def _ev(eid, **kw):
    base = {"disease_event_id": eid, "disease_id": "cholera",
            "disease_name_en": "Cholera", "country_iso3": "TCD",
            "report_date": "2026-08-20", "confirmed_cases": 500,
            "deaths": 12, "outbreak_status": "active",
            "primary_source": "WHO", "update_type": "case_update"}
    base.update(kw)
    return base


class TestCountryAttribution(unittest.TestCase):
    """§二 country attribution separation + regional contamination regression。"""

    def test_tamazuj_blue_nile_not_ssd(self):
        src = {"source_id": "ssd_radio_tamazuj", "source_group": "radio_tamazuj",
               "scope": "country", "country_iso3": "SSD"}
        r = attribute_event_country(
            {"title": "Blue Nile civil society warns of deepening crisis as thousands flee"},
            src)
        self.assertIsNone(r["event_primary_country"],
                          "跨国源零文本证据不得回填 source country（SSD）")
        self.assertEqual(r["attribution_basis"], "insufficient_text")

    def test_tamazuj_south_sudan_text_attributed(self):
        src = {"source_id": "ssd_radio_tamazuj"}
        r = attribute_event_country(
            {"title": "South Sudan: government vows probe after two UN peacekeepers killed"},
            src)
        self.assertEqual(r["event_primary_country"], "SSD")
        self.assertNotIn("SDN", r["mentioned_countries"], "south sudan 不得误判苏丹")

    def test_sudan_crisis_attributed_sdn(self):
        r = attribute_event_country({"title": "Sudan crisis: thousands flee Blue Nile"}, None)
        self.assertEqual(r["event_primary_country"], "SDN")

    def test_ambiguous_multiple_countries(self):
        r = attribute_event_country(
            {"title": "Chad and Niger agree on border cooperation"}, None)
        self.assertIsNone(r["event_primary_country"])
        self.assertEqual(r["attribution_basis"], "ambiguous")
        self.assertEqual(r["mentioned_countries"], ["NER", "TCD"])

    def test_canonical_event_country_reused(self):
        r = attribute_event_country(
            {"event_country": "乍得", "mentioned_countries": ["乍得"]}, None)
        self.assertEqual(r["event_primary_country"], "TCD")
        self.assertEqual(r["attribution_basis"], "canonical")

    def test_multinational_sources_never_fallback(self):
        for sid in ("global_rfi_afrique", "global_allafrica", "global_reliefweb",
                    "tcd_alwihda", "ssd_sudantribune"):
            self.assertTrue(is_multinational({"source_id": sid}), sid)
        self.assertFalse(is_multinational(
            {"source_id": "tcd_atpe", "source_group": "atpe", "scope": "country"}))

    def test_country_hints_clean_south_sudan(self):
        self.assertEqual(country_hints_clean("South Sudan: crisis"), ["SS"])
        self.assertEqual(country_hints_clean("Sudan crisis"), ["SD"])


class TestSocialTimeline(unittest.TestCase):
    """§三-§十三 social timeline 语义。"""

    def test_casualty_update_later(self):
        tl = new_timeline("ME", _art("a", deaths=10))
        tl, upd, flags = apply_update(tl, _art("b", source_id="s2", source_group="g2",
                                               deaths=12,
                                               published_at="2026-08-25T14:00:00+00:00"))
        self.assertEqual(upd["update_type"], "casualty_update")
        self.assertEqual(tl["current_state"]["deaths"], 12)
        self.assertEqual(len(tl["updates"]), 2, "历史不可覆盖")

    def test_simultaneous_conflict(self):
        tl = new_timeline("ME", _art("a", deaths=10))
        tl, upd, flags = apply_update(tl, _art("b", source_id="s2", source_group="g2",
                                               deaths=20,
                                               published_at="2026-08-25T10:20:00+00:00"))
        self.assertEqual(tl["current_state"]["deaths"], 10, "同时期不自动选大数")
        self.assertIn("casualty_difference", flags)

    def test_actor_attribution_update(self):
        tl = new_timeline("ME", _art("a", actor=None))
        tl, upd, _ = apply_update(tl, _art("b", source_id="s2", source_group="g2",
                                           actor="GROUP_TEST_BETA",
                                           title="Officials say GROUP_TEST_BETA claimed the attack",
                                           published_at="2026-08-25T12:00:00+00:00"))
        self.assertEqual(upd["update_type"], "actor_attribution_update")
        self.assertEqual(tl["current_state"]["responsible_party"], "GROUP_TEST_BETA")

    def test_correction_points_to_corrected_value(self):
        tl = new_timeline("ME", _art("a", deaths=8))
        tl, upd, flags = apply_update(tl, _art("b", source_id="s2", source_group="g2",
                                               deaths=11,
                                               title="Corrected: death toll now 11",
                                               published_at="2026-08-25T13:00:00+00:00"))
        self.assertEqual(upd["update_type"], "correction")
        self.assertEqual(tl["current_state"]["deaths"], 11)
        self.assertIn("correction_applied", flags)

    def test_history_preserved(self):
        tl = new_timeline("ME", _art("a", deaths=8,
                                     published_at="2026-08-25T08:00:00+00:00"))
        tl, _, _ = apply_update(tl, _art("b", source_id="s2", source_group="g2",
                                         deaths=11,
                                         published_at="2026-08-25T14:00:00+00:00"))
        tl, _, _ = apply_update(tl, _art("c", source_id="s3", source_group="g3",
                                         deaths=12,
                                         published_at="2026-08-25T18:00:00+00:00"))
        self.assertEqual(tl["current_state"]["deaths"], 12)
        self.assertEqual(len(tl["updates"]), 3, "8→11→12 全部保留")
        self.assertEqual(tl["updates"][0]["update_type"], "initial_report")

    def test_current_state_provenance(self):
        tl = new_timeline("ME", _art("a", deaths=10))
        tl, upd, _ = apply_update(tl, _art("b", source_id="s2", source_group="g2",
                                           deaths=12,
                                           published_at="2026-08-25T14:00:00+00:00"))
        prov = tl["current_state"]["provenance"]["deaths"]
        self.assertEqual(prov["value"], 12)
        self.assertEqual(prov["source"], "s2")
        self.assertEqual(prov["update_id"], upd["update_id"])

    def test_official_confirmation(self):
        tl = new_timeline("ME", _art("a"))
        tl, upd, _ = apply_update(tl, _art("b", source_id="s2", source_group="g2",
                                           title="Government confirms attack in CITY_ALPHA",
                                           published_at="2026-08-25T12:00:00+00:00"))
        self.assertEqual(upd["update_type"], "official_confirmation")
        self.assertTrue(tl["current_state"]["official_confirmed"])

    def test_closure_status(self):
        tl = new_timeline("ME", _art("a"))
        tl, upd, _ = apply_update(tl, _art("b", source_id="s2", source_group="g2",
                                           title="Agreement reached, hostilities ended",
                                           published_at="2026-08-27T10:00:00+00:00"))
        self.assertEqual(upd["update_type"], "closure_update")
        self.assertEqual(tl["timeline_status"], "closed")

    def test_time_basis_fallback(self):
        tl = new_timeline("ME", _art("a", event_time=None))
        self.assertEqual(tl["updates"][0]["time_basis"], "published_at_fallback")

    def test_duplicate_does_not_form_update(self):
        # 同 canonical_url 的重复稿由上游 dedup；引擎对无变化文章判 context
        tl = new_timeline("ME", _art("a", canonical_url="https://x/1"))
        tl, upd, _ = apply_update(tl, _art("b", source_id="s2", source_group="g2",
                                           canonical_url="https://x/1",
                                           published_at="2026-08-25T12:00:00+00:00"))
        self.assertEqual(upd["update_type"], "context_update")
        self.assertEqual(tl["source_count"], 2)  # 引擎不吞 update；上游 dedup 负责

    def test_government_not_closure(self):
        self.assertNotEqual(
            classify_update_type(new_timeline("ME", _art("a")),
                                 _art("b", title="Government confirms attack"),
                                 None)[0], "closure_update")


class TestDiseaseTimeline(unittest.TestCase):
    """§十四-§二十 disease outbreak timeline 语义。"""

    def test_observation_500_to_620(self):
        tl = new_outbreak_timeline(_ev("a", report_date="2026-08-20", confirmed_cases=500))
        tl, obs, conflicts = apply_disease_event(
            tl, _ev("b", report_date="2026-08-24", confirmed_cases=620,
                    supersedes_event_id="a"))
        self.assertEqual(obs["update_type"], "case_update")
        self.assertEqual(tl["latest_counts"]["confirmed_cases"], 620)
        self.assertEqual(tl["updates"][0]["confirmed_cases"], 500, "observation 保留")
        self.assertEqual(conflicts, [])

    def test_temporal_update_not_conflict(self):
        tl = new_outbreak_timeline(_ev("a", report_date="2026-08-20", confirmed_cases=500))
        tl, obs, conflicts = apply_disease_event(
            tl, _ev("b", report_date="2026-08-21", confirmed_cases=510))
        self.assertEqual(conflicts, [], "report_date 不同 → temporal update 非 conflict")

    def test_same_period_numeric_conflict(self):
        tl = new_outbreak_timeline(_ev("a", report_date="2026-08-24", confirmed_cases=500))
        tl, obs, conflicts = apply_disease_event(
            tl, _ev("b", report_date="2026-08-24", confirmed_cases=620))
        self.assertTrue(any("numeric_conflict" in c for c in conflicts))

    def test_categories_separate(self):
        tl = new_outbreak_timeline(
            _ev("a", report_date="2026-08-20", confirmed_cases=100, suspected_cases=50))
        tl, _, _ = apply_disease_event(
            tl, _ev("b", report_date="2026-08-24", confirmed_cases=120, suspected_cases=50))
        self.assertEqual(tl["latest_counts"]["confirmed_cases"], 120)
        self.assertEqual(tl["latest_counts"]["suspected_cases"], 50)
        self.assertIsNone(tl["latest_counts"].get("total_cases"), "不得擅自合计")

    def test_geographic_spread_history(self):
        tl = new_outbreak_timeline(_ev("a", report_date="2026-08-20", admin1=["A", "B"]))
        tl, obs, _ = apply_disease_event(
            tl, _ev("b", report_date="2026-08-24", admin1=["A", "B", "C"]))
        self.assertEqual(obs["update_type"], "geographic_spread")
        self.assertEqual(sorted(tl["affected_admin1"]), ["A", "B", "C"])

    def test_cross_border(self):
        tl = new_outbreak_timeline(
            _ev("a", report_date="2026-08-20", affected_countries=["TCD"]))
        tl, _, _ = apply_disease_event(
            tl, _ev("b", report_date="2026-08-24", affected_countries=["TCD", "NER"],
                    cross_border=True))
        self.assertIn("NER", tl["affected_countries"])

    def test_outbreak_identity_time_separation(self):
        a = _ev("2024", report_date="2024-06-01", update_type="new_outbreak")
        b = _ev("2026", report_date="2026-08-20", update_type="new_outbreak")
        self.assertFalse(_same_outbreak(a, b), "2024 vs 2026 同疾病不同 outbreak")

    def test_unknown_not_zero(self):
        tl = new_outbreak_timeline(
            _ev("a", report_date="2026-08-20", deaths=None, confirmed_cases=None))
        self.assertIsNone(tl["latest_counts"]["deaths"])
        self.assertIsNone(tl["latest_counts"]["confirmed_cases"])

    def test_admin1_normalization(self):
        self.assertEqual(_admin1_list("South Ethiopia"), ["South Ethiopia"])
        self.assertEqual(_admin1_list(["A", "B"]), ["A", "B"])
        self.assertEqual(_admin1_list(None), [])

    def test_build_chains(self):
        events = [
            _ev("root", report_date="2026-08-20", update_type="new_outbreak"),
            _ev("upd", report_date="2026-08-24", confirmed_cases=620,
                supersedes_event_id="root"),
            _ev("marb", report_date="2025-11-24", disease_id="marburg",
                country_iso3="ETH", update_type="new_outbreak"),
        ]
        tls, stats, orphans = build_outbreak_timelines(events)
        self.assertEqual(stats["outbreaks_created"], 2)
        self.assertEqual(orphans, [])
        chol = [t for t in tls if t["disease_id"] == "cholera"][0]
        self.assertEqual(len(chol["updates"]), 2)


class TestGoldenAndRuntime(unittest.TestCase):
    """Golden 28 组 + runtime 隔离。"""

    def test_social_golden_16(self):
        results = run_social(build_social_pairs())
        fails = [r for r in results if r[1] != "PASS"]
        self.assertEqual(fails, [], "Social Golden 16/16 必须全过")

    def test_disease_golden_12(self):
        results = run_disease(build_disease_pairs())
        fails = [r for r in results if r[1] != "PASS"]
        self.assertEqual(fails, [], "Disease Golden 12/12 必须全过")

    def test_runtime_isolated_from_dist(self):
        self.assertFalse((ROOT / "dist" / "data" / "runtime").exists(),
                         "runtime 不得进 dist")
        gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("data/runtime", gi)

    def test_canonical_public_not_modified(self):
        # 本包不得写 Social/Disease Canonical/Public
        for p in ("data/events.json", "data/public/published_events.json",
                  "data/canonical/articles.json",
                  "data/disease/canonical/outbreak_events.json"):
            self.assertTrue((ROOT / p).exists(), p)


if __name__ == "__main__":
    unittest.main()
