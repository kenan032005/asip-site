#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7A §二十六 — Report Engine Golden Set fixtures。

Daily 15 / Weekly 10 / Brief 8。全部中性 fixture（ORG_TEST_ALPHA 等），
期望值明确（selected / suppressed / score / candidate_status）。
"""

CITY = "CITY_ALPHA"
GRP = "GROUP_TEST_BETA"


def _ev(eid, **kw):
    base = {
        "event_id": eid, "master_event_id": "ME_" + eid,
        "event_type": kw.pop("event_type", "armed_attack"),
        "country": kw.pop("country", "TCD"),
        "country_iso3": kw.pop("country_iso3", "TCD"),
        "title_original": kw.pop("title_original", "Attack in %s" % CITY),
        "verification_status": kw.pop("verification_status", "verified"),
        "source_count": kw.pop("source_count", 2),
        "source_id": kw.pop("source_id", "s1"),
        "source_name": kw.pop("source_name", "Source 1"),
        "published_at": kw.pop("published_at", "2026-08-25T10:00:00+00:00"),
        "deaths": kw.pop("deaths", None),
        "casualties": kw.pop("casualties", None),
        "injured": kw.pop("injured", None),
        "location": kw.pop("location", CITY),
        "category": kw.pop("category", None),
        "timeline_status": kw.pop("timeline_status", "ongoing"),
        "conflicting": kw.pop("conflicting", False),
        "single_source_warning": kw.pop("single_source_warning", False),
    }
    base.update(kw)
    return base


def build_daily_fixtures():
    """Daily selection fixtures（15 组，期望 selected/score/reasons）。"""
    f = []

    # D1 重大恐袭进入
    f.append(("d1_major_terror_enters",
              [_ev("t1", event_type="terrorist_attack", deaths=25,
                   event_severity="高")],
              {"selected": 1, "min_score": 40, "reasons_contains": "terrorism_armed_conflict"}))
    # D2 普通经济不进入（low-value 抑制）
    f.append(("d2_ordinary_economic_suppressed",
              [_ev("e1", event_type="other_security",
                   title_original="Business meeting on trade cooperation in CITY_ALPHA")],
              {"selected": 0, "suppressed": 1}))
    # D3 single-source 重大事件进入但带 warning
    f.append(("d3_single_source_major_with_warning",
              [_ev("s1", event_type="terrorist_attack", deaths=12,
                   verification_status="single_source", source_count=1,
                   single_source_warning=True)],
              {"selected": 1, "warning": True}))
    # D4 conflicting 重大事件进入
    f.append(("d4_conflicting_major_enters",
              [_ev("c1", event_type="armed_conflict", deaths=30,
                   verification_status="conflicting", conflicting=True)],
              {"selected": 1, "conflicting": True}))
    # D5 已报告无变化不重复（prev ids 含 → watch，不进 key changes）
    f.append(("d5_reported_no_change_not_repeated",
              [_ev("r1", event_type="armed_conflict", deaths=15,
                   verification_status="verified")],
              {"selected": 1, "prev_ids": ["ME_r1"], "watch": 1}))
    # D6 casualty update 进入 Key Changes
    f.append(("d6_casualty_update_key_change",
              [_ev("u1", event_type="armed_conflict", deaths=18,
                   change_type="casualty_increase")],
              {"selected": 1, "change_type": "casualty_increase"}))
    # D7 closed event 降级（closed → 不进 exec，可 watch）
    f.append(("d7_closed_downgraded",
              [_ev("z1", event_type="armed_conflict", deaths=12,
                   timeline_status="closed", change_type="closed")],
              {"selected": 1, "status": "closed"}))
    # D8 disease new outbreak 进入
    f.append(("d8_disease_new_outbreak_enters",
              [_ev("p1", event_type="public_health", is_disease=True,
                   disease_id="cholera", category="public_health")],
              {"selected_disease": 1}))
    # D9 普通 disease 无变化不进入（已报告 + 无 change → 抑制）
    f.append(("d9_disease_no_change_not_enters",
              [_ev("p2", event_type="public_health", is_disease=True,
                   disease_id="measles", category="public_health",
                   change_type=None, timeline_status="stable")],
              {"selected_disease": 0, "prev_ids": ["ME_p2"]}))
    # D10 cross-border 进入
    f.append(("d10_cross_border_enters",
              [_ev("x1", event_type="border_incident",
                   title_original="Cross-border clash at border town")],
              {"selected": 1, "reasons_contains": "cross_border"}))
    # D11 priority country 加权
    f.append(("d11_priority_country_weighted",
              [_ev("n1", event_type="armed_conflict", country_iso3="NER",
                   deaths=8)],
              {"selected": 1, "reasons_contains": "priority_country",
               "priority_countries": ["TCD", "NER", "SSD"]}))
    # D12 low-value meeting 抑制
    f.append(("d12_low_value_meeting_suppressed",
              [_ev("m1", event_type="other_security",
                   title_original="Ceremonial visit of minister to REGION_BETA")],
              {"selected": 0, "suppressed": 1}))
    # D13 correction 进入
    f.append(("d13_correction_enters",
              [_ev("k1", event_type="armed_conflict", deaths=9,
                   change_type="correction")],
              {"selected": 1, "change_type": "correction"}))
    # D14 official confirmation 进入
    f.append(("d14_official_confirmation_enters",
              [_ev("o1", event_type="terrorist_attack", deaths=14,
                   change_type="official_confirmation", official_declaration=True)],
              {"selected": 1, "change_type": "official_confirmation"}))
    # D15 duplicate/master 只算一次（同 master_event_id 两篇 → 1 条）
    f.append(("d15_duplicate_master_once",
              [_ev("m1", master_event_id="ME_dup", deaths=11),
               _ev("m2", master_event_id="ME_dup", deaths=11)],
              {"selected": 1}))
    return f


def build_weekly_fixtures():
    """Weekly fixtures（10 组，期望 metrics/comparison）。"""
    f = []

    # W1 一周多事件聚合
    f.append(("w1_multi_event_aggregation",
              [_ev("a", event_type="armed_attack", deaths=5),
               _ev("b", event_type="civil_unrest", injured=3),
               _ev("c", event_type="terrorist_attack", deaths=8)],
              {"event_count": 3, "armed_attack_count": 2, "civil_unrest_count": 1,
               "fatalities_known": 13}))
    # W2 重复文章不重复计（同 event_id 两篇）
    f.append(("w2_duplicate_not_double_counted",
              [_ev("a", event_type="armed_attack", deaths=5),
               _ev("a", event_type="armed_attack", deaths=5)],
              {"event_count": 1}))
    # W3 趋势上升（有上周数据）
    f.append(("w3_trend_up",
              [_ev("a", event_type="armed_attack")],
              {"comparison": {"event_count": "up"},
               "prev_metrics": {"event_count": 0}}))
    # W4 趋势下降
    f.append(("w4_trend_down",
              [_ev("a", event_type="armed_attack")],
              {"comparison": {"event_count": "down"},
               "prev_metrics": {"event_count": 5}}))
    # W5 无数据不编造（空列表）
    f.append(("w5_no_data_no_fabrication",
              [],
              {"event_count": 0, "fatalities_known": None, "assessment": "数据不足"}))
    # W6 疾病变化（new outbreak 计入）
    f.append(("w6_disease_change",
              [_ev("a", event_type="public_health", is_disease=True,
                   disease_id="cholera", report_date="2026-08-24",
                   outbreak_status="active")],
              {"new_outbreak_count": 1, "active_outbreak_count": 1,
               "disease_events": [{"outbreak_id": "OB_w6", "disease_id": "cholera",
                                   "report_date": "2026-08-24",
                                   "outbreak_status": "active",
                                   "updates": [{"report_date": "2026-08-24",
                                                "confirmed_cases": 100}]}]}))
    # W7 上周比较（prev_metrics 提供 → comparison 非空）
    f.append(("w7_prev_week_comparison",
              [_ev("a", event_type="armed_attack")],
              {"comparison_has_values": True,
               "prev_metrics": {"event_count": 1, "verified_event_count": 0,
                                "armed_attack_count": 1, "civil_unrest_count": 0,
                                "major_crime_count": 0, "natural_disaster_count": 0,
                                "multi_source_event_count": 0}}))
    # W8 fatalities unknown 不写 0
    f.append(("w8_fatalities_unknown_not_zero",
              [_ev("a", event_type="civil_unrest", deaths=None, injured=None)],
              {"fatalities_known": None, "injuries_known": None}))
    # W9 conflict 保留
    f.append(("w9_conflict_preserved",
              [_ev("a", event_type="armed_attack", deaths=10,
                   verification_status="conflicting", conflicting=True)],
              {"verified_event_count": 0, "event_count": 1}))
    # W10 来源统计（sections.sources 由 builder 层覆盖；metrics 层验证两源两事件）
    f.append(("w10_source_stats",
              [_ev("a", source_id="src_a"), _ev("b", source_id="src_b")],
              {"event_count": 2}))
    return f


def build_brief_fixtures():
    """Brief fixtures（8 组，期望 candidate_status/score）。"""
    f = []

    # B1 重大袭击触发（mass+terror+official+rapid = 70）
    f.append(("b1_mass_attack_triggers",
              [_ev("a", event_type="terrorist_attack", deaths=40,
                   event_severity="极高", official_emergency=True,
                   update_count=3)],
              {"status": "brief_candidate", "min_score": 70}))
    # B2 重大骚乱触发（mass+coup 权重+capital+rapid = 70）
    f.append(("b2_mass_protest_triggers",
              [_ev("b", event_type="mass_protest", deaths=15,
                   event_severity="高",
                   title_original="Mass protests in capital of REGION_BETA",
                   update_count=3)],
              {"status": "brief_candidate", "min_score": 70}))
    # B3 政变触发（severity 极高→mass + coup 权重 + capital + rapid = 70）
    f.append(("b3_coup_triggers",
              [_ev("c", event_type="coup_attempt", event_severity="极高",
                   title_original="Coup attempt in capital of REGION_BETA",
                   update_count=3)],
              {"status": "brief_candidate", "min_score": 70}))
    # B4 跨境触发（mass+cross_border+multi_country+rapid = 70）
    f.append(("b4_cross_border_triggers",
              [_ev("d", event_type="border_incident", deaths=12,
                   title_original="Cross-border conflict at border town",
                   affected_countries=["TCD", "NER"], update_count=3)],
              {"status": "brief_candidate", "min_score": 70}))
    # B5 疫情新暴发触发（mass+official+rapid+multi_country+cross_border = 80）
    f.append(("b5_disease_outbreak_triggers",
              [_ev("e", event_type="public_health", is_disease=True,
                   disease_id="marburg", category="public_health",
                   deaths=25, official_declaration=True, rapid_escalation=True,
                   affected_countries=["TCD", "NER"],
                   title_original="Marburg outbreak spreads across border")],
              {"status": "brief_candidate", "min_score": 70}))
    # B6 普通事件不触发
    f.append(("b6_ordinary_not_trigger",
              [_ev("f", event_type="other_security",
                   title_original="Business meeting in CITY_ALPHA")],
              {"status": "below_threshold"}))
    # B7 低伤亡单源不触发
    f.append(("b7_low_casualty_single_not_trigger",
              [_ev("g", event_type="armed_attack", deaths=2,
                   verification_status="single_source", source_count=1,
                   single_source_warning=True)],
              {"status": "below_threshold"}))
    # B8 conflicting 重大事件仍可 candidate（mass+terror+capital+rapid = 70）
    f.append(("b8_conflicting_major_candidate",
              [_ev("h", event_type="terrorist_attack", deaths=50,
                   verification_status="conflicting", conflicting=True,
                   event_severity="极高",
                   title_original="Attack in capital of REGION_BETA",
                   update_count=3)],
              {"status": "brief_candidate", "min_score": 70}))
    return f
