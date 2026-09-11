#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V2 backfill import tests: deterministic mapping, dedupe, clustering and HOLD."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ops import backfill_import as bi  # noqa: E402


def _bundle(social=None, health=None, contexts=None, observations=None):
    social = social or []
    health = health or []
    contexts = contexts or []
    observations = observations or []
    return {
        "manifest": {
            "batch_id": bi.BATCH_ID,
            "window_bjt": {"start": bi.WINDOW_START, "end": bi.WINDOW_END},
        },
        "social": social,
        "health": health,
        "contexts": contexts,
        "observations": observations,
    }


def _source(url, name="Test Source"):
    return [{"url": url, "source_name": name, "published_date": "2026-08-20"}]


def _social(**kw):
    base = {
        "record_id": "S0",
        "record_type": "event",
        "headline_en": "Synthetic protest in Zambia",
        "headline_zh": "赞比亚示威事件",
        "fact_summary_en": "A synthetic test event summary.",
        "fact_summary_zh": "合成测试事件摘要。",
        "country_iso3": "ZMB",
        "country_name_zh": "赞比亚",
        "category": "political_social_stability",
        "event_date": "2026-08-20",
        "event_date_basis": "reported_date",
        "verification_status": "multi_source",
        "importance_score_editorial": 70,
        "sources": _source("https://unit.test/source-0"),
        "uncertainties": ["synthetic uncertainty"],
    }
    base.update(kw)
    return base


def _health(**kw):
    base = {
        "record_id": "D0",
        "record_type": "disease_update",
        "cluster_key": "COD_EBOLA_TEST_2026",
        "disease": "Ebola",
        "disease_zh": "埃博拉",
        "country_iso3": "COD",
        "country_name_zh": "刚果（金）",
        "event_date": "2026-08-20",
        "verification_status": "official_confirmed",
        "sources": _source("https://unit.test/health-0", "WHO"),
    }
    base.update(kw)
    return base


class TestBackfillImportV2(unittest.TestCase):
    def test_empty_bundle_contract(self):
        report = bi.run_bundle(_bundle())
        self.assertEqual(report["results"]["social"]["input"], 0)
        self.assertEqual(report["results"]["health"]["input"], 0)
        self.assertEqual(report["contract_issues"], [])

    def test_social_new_update_duplicate_and_hold(self):
        rows = [
            _social(record_id="S1", cluster_key="ZMB_ELECTION_TEST", headline_en="Protest in Zambia", fact_summary_en="Post-election protest in Lusaka.", sources=_source("https://unit.test/s1"), china_interest="indirect"),
            _social(record_id="S2", headline_en="Protest in Zambia", fact_summary_en="Post-election protest in Lusaka.", sources=_source("https://unit.test/s2")),
            _social(record_id="S3", record_type="event_update", cluster_key="ZMB_ELECTION_TEST", headline_en="Zambia post-election update", fact_summary_en="Follow-up violence in Kitwe.", event_date="2026-08-21", sources=_source("https://unit.test/s3")),
            _social(record_id="S4", verification_status="disputed_claim", country_iso3="TCD", headline_en="Disputed claim", fact_summary_en="Alleged strike.", category="armed_conflict_terrorism", sources=_source("https://unit.test/s4")),
            _social(record_id="S5", country_iso3="MLI", headline_en="No source", fact_summary_en="Missing url.", sources=[]),
        ]
        report = bi.run_bundle(_bundle(social=rows))
        s = report["results"]["social"]
        self.assertEqual(s["input"], 5)
        self.assertEqual(s["new"], 1)
        self.assertEqual(s["update"], 1)
        self.assertEqual(s["duplicate"], 1)
        self.assertEqual(s["held"], 2)
        self.assertEqual(report["results"]["china"]["indirect"], 1)
        self.assertEqual(len(report["preview"]["master_events"]), 1)
        self.assertEqual(len(report["preview"]["timeline_updates"]), 1)

    def test_disease_cluster_single_entity(self):
        rows = [
            _health(record_id="D1", sources=_source("https://unit.test/d1", "WHO")),
            _health(record_id="D2", event_date="2026-08-24", sources=_source("https://unit.test/d2", "WHO")),
        ]
        report = bi.run_bundle(_bundle(health=rows))
        d = report["results"]["health"]
        self.assertEqual(d["input"], 2)
        self.assertEqual(d["new"], 1)
        self.assertEqual(d["update"], 1)
        self.assertEqual(d["held"], 0)
        self.assertEqual(len(report["preview"]["disease_entities"]), 1)
        self.assertEqual(len(report["preview"]["disease_timeline_updates"]), 1)

    def test_health_context_does_not_create_outbreak(self):
        row = _health(record_id="HC1", record_type="public_health_policy")
        report = bi.run_bundle(_bundle(health=[row]))
        self.assertEqual(report["results"]["health"]["input"], 1)
        self.assertEqual(report["results"]["health"]["context"], 1)
        self.assertEqual(report["results"]["health"]["new"], 0)
        self.assertEqual(len(report["preview"]["disease_entities"]), 0)

    def test_regional_health_mapping(self):
        row = _health(record_id="D3", cluster_key="AFR_POLIO_TEST", disease="Poliovirus type 2", country_iso3="MULTI", country_name_en="Burundi, Ghana, Uganda", sources=_source("https://unit.test/polio", "WHO"))
        report = bi.run_bundle(_bundle(health=[row]))
        self.assertEqual(report["results"]["health"]["held"], 0)
        ent = report["preview"]["disease_entities"][0]
        self.assertEqual(ent["country_iso3"], "AFR")
        self.assertTrue(ent["regional"])
        self.assertEqual(len(ent["affected_countries"]), 3)

    def test_disease_status_and_latest_structured_stats(self):
        rows = [
            _health(record_id="COD1", cluster_key="COD_EBOLA", event_date="2026-08-18",
                    headline_en="Sustained transmission in DRC", fact_summary_en="Sustained transmission continues."),
            _health(record_id="COD2", cluster_key="COD_EBOLA", event_date="2026-08-24",
                    headline_en="DRC records more than 5,200 cases", fact_summary_en="WHO reported more than 5,200 cases."),
            _health(record_id="GNB1", cluster_key="GNB_MPOX", country_iso3="GNB", country_name_zh="几内亚比绍",
                    disease="Mpox", event_date="2026-08-27", headline_en="Active community transmission",
                    fact_summary_en="58 suspected mpox cases by August 23, including 10 laboratory-confirmed cases and no deaths."),
            _health(record_id="UGA1", cluster_key="UGA_EBOLA", country_iso3="UGA", country_name_zh="乌干达",
                    event_date="2026-08-27", severity="resolved_signal",
                    headline_en="Uganda ends outbreak", fact_summary_en="The outbreak ended after 42 days without a new confirmed case."),
            _health(record_id="POL1", cluster_key="AFR_POLIO", country_iso3="MULTI",
                    country_name_en="Burundi, Ghana, Guinea-Bissau, Republic of the Congo and Uganda",
                    country_name_zh="五国", disease="Poliovirus type 2 outbreaks", event_date="2026-08-19",
                    severity="resolved_signal", headline_en="Five countries ended type 2 polio outbreaks",
                    fact_summary_en="Transmission was interrupted in five countries."),
            _health(record_id="SSD1", cluster_key="SSD_PREP", country_iso3="SSD", country_name_zh="南苏丹",
                    record_type="disease_preparedness_update", disease="Ebola preparedness", event_date="2026-08-27",
                    headline_en="Ebola preparedness at border", fact_summary_en="Preparedness and screening were strengthened."),
        ]
        report = bi.run_bundle(_bundle(health=rows))
        by_cluster = {d["cluster_key"]: d for d in report["preview"]["disease_entities"]}
        self.assertEqual(by_cluster["COD_EBOLA"]["outbreak_status"], "ACTIVE")
        self.assertEqual(by_cluster["GNB_MPOX"]["latest_counts"], {
            "confirmed": 10, "suspected": 58, "deaths": 0, "recovered": None, "as_of_date": "2026-08-23"
        })
        self.assertEqual(by_cluster["GNB_MPOX"]["outbreak_status"], "ACTIVE")
        self.assertEqual(by_cluster["UGA_EBOLA"]["outbreak_status"], "RESOLVED")
        self.assertEqual(by_cluster["AFR_POLIO"]["outbreak_status"], "RESOLVED")
        self.assertEqual(by_cluster["SSD_PREP"]["outbreak_status"], "PREPAREDNESS")
        self.assertEqual(by_cluster["GNB_MPOX"]["report_date"], "2026-08-27")

    def test_active_outbreak_and_signal_counts(self):
        rows = [
            _health(record_id="A1", cluster_key="ACTIVE", headline_en="Active transmission"),
            _health(record_id="R1", cluster_key="RESOLVED", severity="resolved_signal", headline_en="Outbreak ended"),
            _health(record_id="P1", cluster_key="PREP", record_type="disease_preparedness_update", headline_en="Preparedness mission"),
        ]
        report = bi.run_bundle(_bundle(health=rows))
        views = bi.build_views(report)
        self.assertEqual(views["site_overview"]["kpis"]["active_outbreaks"], 1)
        self.assertEqual(views["site_overview"]["kpis"]["disease_active_signal_count"], 2)
        self.assertEqual(views["disease_outbreaks"]["outbreaks"][0]["latest_report_at"], "2026-08-20")


if __name__ == "__main__":
    unittest.main()
