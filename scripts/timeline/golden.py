#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6B — Golden Set fixtures（§二十一 Social 16 组 / §二十二 Disease 12 组）。

全部中性 fixture（ORG_TEST_ALPHA / GROUP_TEST_BETA / CITY_ALPHA / REGION_BETA），
不涉及真实敏感组织。期望值明确（update_type / current_state / flags）。
"""

CITY = "CITY_ALPHA"
REGION = "REGION_BETA"
COUNTRY = "TCD"
GRP = "GROUP_TEST_BETA"
ORG = "ORG_TEST_ALPHA"


def _art(aid, **kw):
    base = {
        "article_id": aid, "source_id": kw.pop("source_id", "s1"),
        "source_group": kw.pop("source_group", "g1"),
        "trust_tier": kw.pop("trust_tier", "B"),
        "title": kw.pop("title", "Attack in %s" % CITY),
        "url": kw.pop("url", "https://example.com/%s" % aid),
        "canonical_url": kw.pop("canonical_url", None),
        "original_url": kw.pop("original_url", None),
        "original_publisher": kw.pop("original_publisher", None),
        "content_hash": kw.pop("content_hash", None),
        "published_at": kw.pop("published_at", "2026-08-25T10:00:00+00:00"),
        "event_time": kw.pop("event_time", "2026-08-25T09:00:00+00:00"),
        "primary_country_iso3": kw.pop("country", COUNTRY),
        "affected_countries": kw.pop("affected_countries", []),
        "location": kw.pop("location", CITY),
        "event_type": kw.pop("event_type", "armed_attack"),
        "actor": kw.pop("actor", None),
        "responsible_party": kw.pop("responsible_party", None),
        "target": kw.pop("target", None),
        "facility": kw.pop("facility", None),
        "deaths": kw.pop("deaths", None),
        "casualties": kw.pop("casualties", None),
        "injured": kw.pop("injured", None),
        "body": kw.pop("body", "Body text %s" % aid),
        "body_extracted": kw.pop("body_extracted", None),
        "event_status": kw.pop("event_status", None),
    }
    base.update(kw)
    return base


def build_social_pairs():
    """16 组 Social fixture。每组 (id, [articles 按时间序], expected)：
    expected = {update_types: [..], deaths: n|None, flags: [...], status: ...}"""
    pairs = []

    # S1 首报 10 死 → 后续 12 死（更晚）→ casualty_update
    pairs.append(("s1_initial_10_to_12",
                  [_art("a", deaths=10, published_at="2026-08-25T10:00:00+00:00"),
                   _art("b", source_id="s2", source_group="g2", deaths=12,
                        published_at="2026-08-25T14:00:00+00:00")],
                  {"update_types": ["initial_report", "casualty_update"],
                   "deaths": 12, "flags": []}))

    # S2 同时期 10 vs 20 → conflict，不自动选 20
    pairs.append(("s2_simultaneous_10_vs_20",
                  [_art("a", deaths=10, published_at="2026-08-25T10:00:00+00:00"),
                   _art("b", source_id="s2", source_group="g2", deaths=20,
                        published_at="2026-08-25T10:20:00+00:00")],
                  {"update_types": ["initial_report", "casualty_update"],
                   "deaths": 10, "flags": ["casualty_difference"]}))

    # S3 unknown actor → official attribution
    pairs.append(("s3_unknown_actor_to_official_attr",
                  [_art("a", actor=None, title="Attack in %s" % CITY),
                   _art("b", source_id="s2", source_group="g2", actor=GRP,
                        title="Officials say %s claimed the attack" % GRP,
                        published_at="2026-08-25T12:00:00+00:00")],
                  {"update_types": ["initial_report", "actor_attribution_update"],
                   "responsible_party": GRP, "flags": []}))

    # S4 allegation → confirmed later（attribution 升级 flag）
    pairs.append(("s4_allegation_to_confirmed",
                  [_art("a", actor=GRP, title="%s allegedly behind blast" % GRP),
                   _art("b", source_id="s2", source_group="g2", actor=GRP,
                        title="Authorities confirm %s responsible" % GRP,
                        published_at="2026-08-25T13:00:00+00:00")],
                  {"update_types": ["initial_report", "actor_attribution_update"],
                   "responsible_party": GRP, "flags": ["attribution_escalation"]}))

    # S5 location province → city precision（location_update）
    pairs.append(("s5_location_province_to_city",
                  [_art("a", location=REGION),
                   _art("b", source_id="s2", source_group="g2", location=CITY,
                        published_at="2026-08-25T11:00:00+00:00")],
                  {"update_types": ["initial_report", "location_update"],
                   "location": CITY, "flags": []}))

    # S6 local report → official confirmation
    pairs.append(("s6_local_to_official_confirmation",
                  [_art("a", source_id="s1"),
                   _art("b", source_id="s2", source_group="g2",
                        title="Government confirms attack in %s" % CITY,
                        published_at="2026-08-25T12:00:00+00:00")],
                  {"update_types": ["initial_report", "official_confirmation"],
                   "official_confirmed": True, "flags": []}))

    # S7 corrected casualty figure（correction → current_state 指向更正值）
    pairs.append(("s7_corrected_casualty",
                  [_art("a", deaths=8, published_at="2026-08-25T10:00:00+00:00"),
                   _art("b", source_id="s2", source_group="g2", deaths=11,
                        title="Corrected: death toll now 11",
                        published_at="2026-08-25T13:00:00+00:00")],
                  {"update_types": ["initial_report", "correction"],
                   "deaths": 11, "flags": ["correction_applied"]}))

    # S8 发布时间晚但 event_time 相同 → 非 update（context）
    pairs.append(("s8_late_publish_same_event_time",
                  [_art("a", published_at="2026-08-25T10:00:00+00:00",
                        event_time="2026-08-25T09:00:00+00:00"),
                   _art("b", source_id="s2", source_group="g2", deaths=None,
                        published_at="2026-08-26T10:00:00+00:00",
                        event_time="2026-08-25T09:00:00+00:00",
                        title="Recap: %s attack details" % CITY)],
                  {"update_types": ["initial_report", "context_update"],
                   "deaths": None, "flags": []}))

    # S9 published_at fallback（无 event_time）
    pairs.append(("s9_published_at_fallback",
                  [_art("a", event_time=None, published_at="2026-08-25T10:00:00+00:00"),
                   _art("b", source_id="s2", source_group="g2", deaths=12,
                        event_time=None, published_at="2026-08-25T14:00:00+00:00")],
                  {"update_types": ["initial_report", "casualty_update"],
                   "deaths": 12, "flags": [], "time_basis": "published_at_fallback"}))

    # S10 same event context article（补充背景 → context）
    pairs.append(("s10_context_article",
                  [_art("a"),
                   _art("b", source_id="s2", source_group="g2",
                        title="Background: tensions rise in %s" % REGION,
                        published_at="2026-08-25T15:00:00+00:00")],
                  {"update_types": ["initial_report", "context_update"], "flags": []}))

    # S11 new attack same actor next day different location → 不同事件（不并入）
    # （引擎侧：作为独立 master event 的 new timeline，此处验证同一 timeline 不吞并）
    pairs.append(("s11_new_attack_different_location",
                  [_art("a", actor=GRP, location=CITY),
                   _art("b", source_id="s2", source_group="g2", actor=GRP,
                        location="CITY_BETA", event_time="2026-08-26T09:00:00+00:00",
                        published_at="2026-08-26T10:00:00+00:00",
                        title="New attack in %s" % "CITY_BETA")],
                  {"update_types": ["initial_report", "location_update"],
                   "location": "CITY_BETA", "flags": []}))

    # S12 same country same type different target → 不同事件（loc 变化 → location_update）
    pairs.append(("s12_same_country_different_target",
                  [_art("a", target="target_x", location="site_x"),
                   _art("b", source_id="s2", source_group="g2", target="target_y",
                        location="site_y", published_at="2026-08-25T12:00:00+00:00")],
                  {"update_types": ["initial_report", "location_update"],
                   "location": "site_y", "flags": []}))

    # S13 closure update
    pairs.append(("s13_closure",
                  [_art("a"),
                   _art("b", source_id="s2", source_group="g2",
                        title="Agreement reached, hostilities ended",
                        published_at="2026-08-27T10:00:00+00:00")],
                  {"update_types": ["initial_report", "closure_update"],
                   "status": "closed", "flags": []}))

    # S14 stable 状态（无更新超过阈值 → stable）
    pairs.append(("s14_stable",
                  [_art("a", published_at="2026-08-20T10:00:00+00:00"),
                   _art("b", source_id="s2", source_group="g2",
                        title="Situation update in %s" % CITY,
                        published_at="2026-08-25T10:00:00+00:00")],
                  {"update_types": ["initial_report", "context_update"],
                   "status": "stable", "flags": []}))

    # S15 source duplicate 不得形成 update（同 canonical_url → runner 跳过）
    pairs.append(("s15_duplicate_no_update",
                  [_art("a", canonical_url="https://example.com/x/1"),
                   _art("b", source_id="s2", source_group="g2",
                        canonical_url="https://example.com/x/1",
                        published_at="2026-08-25T12:00:00+00:00")],
                  {"update_types": ["initial_report"],
                   "source_count": 1, "flags": []}))

    # S16 syndicated report 不算独立 confirmation（同 source_group 同内容 → context）
    pairs.append(("s16_syndicated_no_independent",
                  [_art("a", source_group="france24"),
                   _art("b", source_group="france24",
                        title="%s: attack in %s" % ("France24", CITY),
                        published_at="2026-08-25T12:00:00+00:00")],
                  {"update_types": ["initial_report", "context_update"],
                   "independent_source_count": 1, "flags": []}))

    return pairs


def build_disease_pairs():
    """12 组 Disease fixture。每组 (id, [events 按时间序], expected)：
    expected = {update_types: [..], latest: {...}, conflicts: n, admin1: [...]}"""
    def ev(eid, **kw):
        base = {"disease_event_id": eid, "disease_id": "cholera",
                "disease_name_en": "Cholera", "country_iso3": "TCD",
                "report_date": "2026-08-20", "confirmed_cases": 500,
                "deaths": 12, "outbreak_status": "active",
                "primary_source": "WHO", "update_type": "case_update"}
        base.update(kw)
        return base

    pairs = []

    # D1 500 → 620 cases later date → case_update
    pairs.append(("d1_cases_500_to_620",
                  [ev("d1a", report_date="2026-08-20", confirmed_cases=500),
                   ev("d1b", report_date="2026-08-24", confirmed_cases=620,
                      supersedes_event_id="d1a")],
                  {"update_types": ["new_outbreak", "case_update"],
                   "latest": {"confirmed_cases": 620}, "conflicts": 0}))

    # D2 12 → 15 deaths → mortality_update（canonical 标注 mortality_update）
    pairs.append(("d2_deaths_12_to_15",
                  [ev("d2a", report_date="2026-08-20", deaths=12),
                   ev("d2b", report_date="2026-08-24", deaths=15,
                      update_type="mortality_update", supersedes_event_id="d2a")],
                  {"update_types": ["new_outbreak", "mortality_update"],
                   "latest": {"deaths": 15}, "conflicts": 0}))

    # D3 confirmed 与 suspected 分别更新
    pairs.append(("d3_confirmed_suspected_separate",
                  [ev("d3a", report_date="2026-08-20", confirmed_cases=100, suspected_cases=50),
                   ev("d3b", report_date="2026-08-24", confirmed_cases=120, suspected_cases=50,
                      supersedes_event_id="d3a")],
                  {"update_types": ["new_outbreak", "case_update"],
                   "latest": {"confirmed_cases": 120, "suspected_cases": 50,
                              "total_cases": None}, "conflicts": 0}))

    # D4 同一统计期不同数字 → numeric_conflict
    pairs.append(("d4_same_period_conflict",
                  [ev("d4a", report_date="2026-08-24", confirmed_cases=500),
                   ev("d4b", report_date="2026-08-24", confirmed_cases=620,
                      supersedes_event_id="d4a")],
                  {"update_types": ["new_outbreak", "case_update"],
                   "conflicts": 1}))

    # D5 report date 不同 → temporal update（非 conflict）
    pairs.append(("d5_report_date_diff_temporal",
                  [ev("d5a", report_date="2026-08-20", confirmed_cases=500),
                   ev("d5b", report_date="2026-08-21", confirmed_cases=510,
                      supersedes_event_id="d5a")],
                  {"update_types": ["new_outbreak", "case_update"],
                   "conflicts": 0}))

    # D6 3 → 5 provinces spread
    pairs.append(("d6_spread_3_to_5",
                  [ev("d6a", report_date="2026-08-20", admin1=["A", "B", "C"]),
                   ev("d6b", report_date="2026-08-24", admin1=["A", "B", "C", "D", "E"],
                      supersedes_event_id="d6a")],
                  {"update_types": ["new_outbreak", "geographic_spread"],
                   "admin1": ["A", "B", "C", "D", "E"]}))

    # D7 new country cross-border（canonical 标注 geographic_spread）
    pairs.append(("d7_cross_border",
                  [ev("d7a", report_date="2026-08-20", country_iso3="TCD",
                      affected_countries=["TCD"]),
                   ev("d7b", report_date="2026-08-24", country_iso3="TCD",
                      affected_countries=["TCD", "NER"], cross_border=True,
                      update_type="geographic_spread", supersedes_event_id="d7a")],
                  {"update_types": ["new_outbreak", "geographic_spread"],
                   "affected_countries": ["NER", "TCD"]}))

    # D8 status active → declining → status_change（canonical 标注 status_change）
    pairs.append(("d8_status_change",
                  [ev("d8a", report_date="2026-08-20", outbreak_status="active"),
                   ev("d8b", report_date="2026-08-28", outbreak_status="declining",
                      update_type="status_change", supersedes_event_id="d8a")],
                  {"update_types": ["new_outbreak", "status_change"],
                   "outbreak_status": "declining"}))

    # D9 status contained（canonical 标注 status_change）
    pairs.append(("d9_contained",
                  [ev("d9a", report_date="2026-08-20", outbreak_status="active"),
                   ev("d9b", report_date="2026-09-01", outbreak_status="contained",
                      update_type="status_change", supersedes_event_id="d9a")],
                  {"update_types": ["new_outbreak", "status_change"],
                   "outbreak_status": "contained"}))

    # D10 final update
    pairs.append(("d10_final_update",
                  [ev("d10a", report_date="2026-08-20", outbreak_status="active"),
                   ev("d10b", report_date="2026-09-10", outbreak_status="ended",
                      update_type="final_update", supersedes_event_id="d10a")],
                  {"update_types": ["new_outbreak", "final_update"],
                   "outbreak_status": "ended"}))

    # D11 2024 vs 2026 同疾病不同 outbreak（identity 不合并）
    pairs.append(("d11_2024_vs_2026_outbreak",
                  [ev("d11a", report_date="2024-06-01", update_type="new_outbreak"),
                   ev("d11b", report_date="2026-08-20", update_type="new_outbreak",
                      supersedes_event_id=None)],
                  {"separate_outbreaks": 2}))

    # D12 null unknown 不得变 0
    pairs.append(("d12_null_not_zero",
                  [ev("d12a", report_date="2026-08-20", deaths=None, confirmed_cases=None)],
                  {"latest": {"deaths": None, "confirmed_cases": None}}))

    return pairs
