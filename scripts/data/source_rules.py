#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
source_rules.py —— ASIP Stage-2 来源业务约束（统一函数）

落实第二阶段收尾整改第五节：
- Reuters：source_group=reuters、source_type=international_media、
  source_reliability_tier=tier_1、is_direct_origin=true、is_republication_platform=false；
  不得标记为 government / official / direct_official_source。
- Xinhua：source_group=xinhua、source_type=state_media、
  默认 claim_origin_type=media_reporting；不能仅因国家通讯社身份自动视为政府直接声明。
- ReliefWeb：source_group=reliefweb、source_type=aggregation_platform、
  is_direct_origin=false、is_republication_platform=true；
  Article 的 claim_origin_type 必须依据原始发布机构，而非 reliefweb.int 域名
  （故平台来源记录的 claim_origin_type 必须为 unknown）。

用于：来源迁移、Repository 保存、validate_stage2、新 Article 生成。
validate_source_business_rules(source) 返回错误字符串列表（空=通过）。
"""

# 直接机构声明类（一旦标记即视为“官方直接声明”，来源业务约束需禁止的情形）
DIRECT_STATEMENTS = {
    "direct_government_statement",
    "direct_military_statement",
    "direct_international_organization_report",
    "direct_humanitarian_report",
}


def _grp(source):
    return (str(source.get("source_group", "")) + " " + str(source.get("source_id", ""))).lower()


def _name(source):
    return str(source.get("source_name", "") or "")


def validate_source_business_rules(source: dict) -> list:
    """返回违反业务约束的错误列表；空列表表示通过。

    source 期望含：source_id / source_group / source_name / source_type /
    source_reliability_tier / is_direct_origin / is_republication_platform / claim_origin_type
    """
    errs = []
    if not isinstance(source, dict):
        return ["source 不是对象"]
    g = _grp(source)
    name = _name(source)
    sid = source.get("source_id", "")
    st = source.get("source_type", "")
    tier = source.get("source_reliability_tier", "")
    direct = source.get("is_direct_origin", False)
    repub = source.get("is_republication_platform", False)
    claim = source.get("claim_origin_type", "")

    # ── Reuters ──
    if "reuters" in g:
        if st != "international_media":
            errs.append(f"{sid}: Reuters 必须 source_type=international_media，实际 {st!r}")
        if tier != "tier_1":
            errs.append(f"{sid}: Reuters 必须 source_reliability_tier=tier_1，实际 {tier!r}")
        if direct is not True:
            errs.append(f"{sid}: Reuters 必须 is_direct_origin=true（高可靠直接来源）")
        if repub is not False:
            errs.append(f"{sid}: Reuters 不得 is_republication_platform=true（转载≠官方）")
        if st == "government":
            errs.append(f"{sid}: Reuters 不得标记为 government（媒体≠政府）")
        if claim in DIRECT_STATEMENTS:
            errs.append(f"{sid}: Reuters 单一媒体不得标记 claim_origin_type 为官方直接声明（{claim}）")

    # ── Xinhua ──
    if g in ("xinhua", "xinhuanet") or "新华" in name:
        if st != "state_media":
            errs.append(f"{sid}: 新华社必须 source_type=state_media，实际 {st!r}")
        if claim in DIRECT_STATEMENTS:
            errs.append(f"{sid}: 新华社不得仅因国家通讯社身份自动视为政府直接声明（claim={claim}）")
        # 默认 media_reporting；unknown 视为尚未补全但不阻断（非官方直接声明即可）
        if claim not in ("media_reporting", "unknown", ""):
            errs.append(f"{sid}: 新华社 claim_origin_type 应为 media_reporting 或 unknown，实际 {claim!r}")

    # ── ReliefWeb ──
    if "reliefweb" in g:
        if st != "aggregation_platform":
            errs.append(f"{sid}: ReliefWeb 必须 source_type=aggregation_platform，实际 {st!r}")
        if direct is not False:
            errs.append(f"{sid}: ReliefWeb 不得 is_direct_origin=true（平台≠直接来源）")
        if repub is not True:
            errs.append(f"{sid}: ReliefWeb 必须 is_republication_platform=true（聚合转载平台）")
        if claim != "unknown":
            errs.append(
                f"{sid}: ReliefWeb 平台来源 claim_origin_type 必须为 unknown"
                f"（须依据原始发布机构，而非 reliefweb.int 域名），实际 {claim!r}"
            )

    return errs
