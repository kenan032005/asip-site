#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6A — Golden Set（§十六）：24 对中性 fixture。

不使用真实敏感组织背景；实体用 ORG_TEST_ALPHA / GROUP_TEST_BETA /
CITY_ALPHA / REGION_BETA。
期望值：duplicate / same_event / different_event / needs_review。
"""

import hashlib
import json

# 中性实体
ORG = "ORG_TEST_ALPHA"
GRP = "GROUP_TEST_BETA"
CITY = "CITY_ALPHA"
REGION = "REGION_BETA"
COUNTRY = "XAA"


def _art(cid, **kw):
    base = {
        "candidate_id": cid, "article_id": "A_" + cid,
        "source_id": kw.get("source_id", "src_x"),
        "source_group": kw.get("source_group", "src_x"),
        "trust_tier": kw.get("trust_tier", "B"),
        "title": kw.get("title", "Event in " + CITY),
        "url": kw.get("url", "https://example.com/%s" % cid),
        "canonical_url": kw.get("canonical_url"),
        "original_url": kw.get("original_url"),
        "original_publisher": kw.get("original_publisher"),
        "content_hash": kw.get("content_hash"),
        "published_at": kw.get("published_at", "2026-08-25T10:00:00+00:00"),
        "event_time": kw.get("event_time", "2026-08-25T09:00:00+00:00"),
        "primary_country_iso3": kw.get("country", COUNTRY),
        "affected_countries": kw.get("affected_countries", []),
        "location": kw.get("location", CITY),
        "event_type": kw.get("event_type", "armed_attack"),
        "actor": kw.get("actor"),
        "target": kw.get("target"),
        "facility": kw.get("facility"),
        "casualties": kw.get("casualties"),
        "numeric_facts": kw.get("numeric_facts", []),
        "body": kw.get("body", "Body text " + cid),
        "body_extracted": kw.get("body_extracted"),
    }
    # 透传额外字段（original_event_ref 等）
    base.update({k: v for k, v in kw.items() if k not in base})
    return base


def build_fixture_pairs():
    """返回 [(pair_id, article_a, article_b, expected)]，expected ∈
    {duplicate, same_event, different_event, needs_review}。"""
    T1 = "2026-08-25T09:00:00+00:00"
    T2 = "2026-08-25T10:30:00+00:00"
    T_LATER = "2026-08-30T09:00:00+00:00"   # >72h
    pairs = []

    # ── SAME_EVENT (1-9) ──
    pairs.append(("s1_independent_same_city_day",
                  _art("s1a", source_group="src_a", title="Attack in %s kills 10" % CITY, casualties=10),
                  _art("s1b", source_group="src_b", title="Deadly attack in %s" % CITY, casualties=10),
                  "same_event"))
    pairs.append(("s2_casualty_10_vs_12",
                  _art("s2a", source_group="src_a", title="%s attack: 10 dead" % CITY, casualties=10),
                  _art("s2b", source_group="src_b", title="%s attack death toll rises to 12" % CITY, casualties=12),
                  "same_event"))  # 数值差异 → conflict_flag 非 reject
    pairs.append(("s3_national_vs_city_location",
                  _art("s3a", source_group="src_a", title="Attack in %s, %s" % (CITY, REGION), location=REGION),
                  _art("s3b", source_group="src_b", title="Attack in %s" % CITY, location=REGION + "/" + CITY),
                  "same_event"))  # 上级区域 vs 城市级（la in lb）
    pairs.append(("s4_fr_en_different_title",
                  _art("s4a", source_group="src_a", language_hint=None, title="Attaque meurtrière à %s" % CITY),
                  _art("s4b", source_group="src_b", title="Deadly attack in %s" % CITY),
                  "same_event"))
    pairs.append(("s5_official_plus_media",
                  _art("s5a", source_group="gov", trust_tier="A", title="Official statement on %s incident" % CITY),
                  _art("s5b", source_group="media_x", title="%s incident reported by witnesses" % CITY),
                  "same_event"))
    pairs.append(("s6_same_event_different_pubtime",
                  _art("s6a", source_group="src_a", title="%s blast reported" % CITY, published_at=T1),
                  _art("s6b", source_group="src_b", title="%s blast details emerge" % CITY, published_at="2026-08-25T18:00:00+00:00"),
                  "same_event"))
    pairs.append(("s7_same_facility",
                  _art("s7a", source_group="src_a", title="Incident at %s facility" % ORG, facility=ORG),
                  _art("s7b", source_group="src_b", title="Explosion near %s facility" % ORG, facility=ORG),
                  "same_event"))
    pairs.append(("s8_same_distinct_number",
                  _art("s8a", source_group="src_a", title="%s: 47 injured" % CITY, numeric_facts=[47]),
                  _art("s8b", source_group="src_b", title="47 injured in %s" % CITY, numeric_facts=[47]),
                  "same_event"))
    pairs.append(("s9_partial_vs_full_body",
                  _art("s9a", source_group="src_a", title="%s security incident" % CITY,
                       body="Brief report on the incident in " + CITY),
                  _art("s9b", source_group="src_b", title="%s security incident" % CITY,
                       body="Full report: the incident in " + CITY + " involved "
                            + ORG + " with casualties in the morning hours."),
                  "same_event"))

    # ── DUPLICATE (10-14) ──
    pairs.append(("d10_same_canonical_url",
                  _art("d10a", source_group="src_a", title="T", url="https://x.com/a",
                       canonical_url="https://x.com/article/1"),
                  _art("d10b", source_group="src_a", title="T2", url="https://x.com/b",
                       canonical_url="https://x.com/article/1"),
                  "duplicate"))
    pairs.append(("d11_utm_variants",
                  _art("d11a", source_group="src_a", title="T", url="https://x.com/a?utm_source=x"),
                  _art("d11b", source_group="src_a", title="T", url="https://x.com/a?utm_source=y&fbclid=z"),
                  "duplicate"))
    pairs.append(("d12_same_content_hash",
                  _art("d12a", source_group="src_a", title="T", content_hash="abc123"),
                  _art("d12b", source_group="src_a", title="T", content_hash="abc123"),
                  "duplicate"))
    pairs.append(("d13_allafrica_repost",
                  _art("d13a", source_group="allafrica", title="T", url="https://allafrica.com/r",
                       original_url="https://rfi.fr/r1", original_publisher="RFI"),
                  _art("d13b", source_group="rfi", title="T", url="https://rfi.fr/r1"),
                  "duplicate"))
    pairs.append(("d14_f24_en_fr",
                  _art("d14a", source_group="france24", title="Event in Africa", url="https://france24.com/en/a", content_hash="f24same"),
                  _art("d14b", source_group="france24", title="Événement en Afrique", url="https://france24.com/fr/a", content_hash="f24same"),
                  "duplicate"))  # 同 source_group + 同 content_hash → 同源转载

    # ── DIFFERENT_EVENT (15-21) ──
    pairs.append(("e15_same_actor_diff_city",
                  _art("e15a", source_group="src_a", title="%s attack" % CITY, location=CITY, actor=GRP),
                  _art("e15b", source_group="src_b", title="%s attack" % "CITY_BETA", location="CITY_BETA", actor=GRP),
                  "different_event"))  # R3/R5
    pairs.append(("e16_same_city_gt72h",
                  _art("e16a", source_group="src_a", title="%s incident" % CITY, event_time=T1),
                  _art("e16b", source_group="src_b", title="%s incident" % CITY, event_time=T_LATER),
                  "different_event"))  # R2
    pairs.append(("e17_same_country_day_diff_type",
                  _art("e17a", source_group="src_a", title="%s attack" % CITY, event_type="armed_attack"),
                  _art("e17b", source_group="src_b", title="%s economic forum" % CITY, event_type="economic"),
                  "different_event"))  # R4
    pairs.append(("e18_same_actor_same_day_diff_target",
                  _art("e18a", source_group="src_a", title="%s targeted" % ORG, actor=GRP, target=ORG),
                  _art("e18b", source_group="src_b", title="second location hit", actor=GRP, target="SITE_BETA"),
                  "different_event"))  # R5
    pairs.append(("e19_similar_title_diff_location",
                  _art("e19a", source_group="src_a", title="Attack in %s leaves casualties" % CITY, location=CITY),
                  _art("e19b", source_group="src_b", title="Attack in %s leaves casualties" % "CITY_BETA", location="CITY_BETA"),
                  "different_event"))  # R3 高标题相似不合并
    pairs.append(("e20_same_casualty_diff_country",
                  _art("e20a", source_group="src_a", title="%s: 10 dead" % CITY, country=COUNTRY, casualties=10),
                  _art("e20b", source_group="src_b", title="10 dead in %s" % "CITY_BETA", country="YBB", casualties=10, location="CITY_BETA"),
                  "different_event"))  # R1
    pairs.append(("e21_same_place_day_distinct_event",
                  _art("e21a", source_group="src_a", title="%s: armed attack" % CITY, event_type="armed_attack"),
                  _art("e21b", source_group="src_b", title="%s: fuel price protest" % CITY, event_type="civil_unrest"),
                  "different_event"))  # R4 同地点同日不同事件

    # ── NEEDS_REVIEW (22-24) ──
    pairs.append(("r22_country_date_only",
                  _art("r22a", source_group="src_a", title="Security situation in %s" % COUNTRY, location=REGION, event_type=None),
                  _art("r22b", source_group="src_b", title="Security situation in %s reported" % COUNTRY, location=REGION, event_type=None),
                  "needs_review"))
    pairs.append(("r23_location_unknown_actor_type",
                  _art("r23a", source_group="src_a", title="%s claims attack" % GRP, location=None, actor=GRP, original_event_ref="EVT_REF_77"),
                  _art("r23b", source_group="src_b", title="Attack claimed by %s" % GRP, location=None, actor=GRP, original_event_ref="EVT_REF_77"),
                  "needs_review"))
    pairs.append(("r24_casualty_approx_insufficient",
                  _art("r24a", source_group="src_a", title="Incident in %s: 47 injured" % REGION, location=REGION, casualties=10, numeric_facts=[47]),
                  _art("r24b", source_group="src_b", title="%s incident: 47 wounded" % REGION, location=None, casualties=12, numeric_facts=[47]),
                  "needs_review"))
    return pairs


def main():
    pairs = build_fixture_pairs()
    print("fixture pairs: %d" % len(pairs))
    from collections import Counter
    print(Counter(p[3] for p in pairs))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
