#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 传染病数据链 V1：常量与枚举（§六/§十/§十三）。"""

# outbreak_status（§六，事件状态，非医学风险评分）
OUTBREAK_ACTIVE = "active"
OUTBREAK_MONITORING = "monitoring"
OUTBREAK_DECLINING = "declining"
OUTBREAK_CONTAINED = "contained"
OUTBREAK_ENDED = "ended"
OUTBREAK_UNKNOWN = "unknown"
OUTBREAK_STATUS_ENUM = {
    OUTBREAK_ACTIVE, OUTBREAK_MONITORING, OUTBREAK_DECLINING,
    OUTBREAK_CONTAINED, OUTBREAK_ENDED, OUTBREAK_UNKNOWN,
}

# update_type（§六）
UPDATE_NEW_OUTBREAK = "new_outbreak"
UPDATE_CASE_UPDATE = "case_update"
UPDATE_GEOGRAPHIC_SPREAD = "geographic_spread"
UPDATE_MORTALITY_UPDATE = "mortality_update"
UPDATE_RESPONSE_UPDATE = "response_update"
UPDATE_STATUS_CHANGE = "status_change"
UPDATE_FINAL_UPDATE = "final_update"
UPDATE_TYPE_ENUM = {
    UPDATE_NEW_OUTBREAK, UPDATE_CASE_UPDATE, UPDATE_GEOGRAPHIC_SPREAD,
    UPDATE_MORTALITY_UPDATE, UPDATE_RESPONSE_UPDATE, UPDATE_STATUS_CHANGE,
    UPDATE_FINAL_UPDATE,
}

# 疾病核实状态（§十三：与社安核实不同，数字差异→data_difference，时间差异→temporal_update）
VERIFY_OFFICIAL = "official"           # 官方来源直接确认
VERIFY_CORROBORATED = "corroborated"   # ≥2 独立来源一致（含非官方）
VERIFY_SINGLE_SOURCE = "single_source" # 单一来源
VERIFY_DATA_DIFFERENCE = "data_difference"   # 数字不同但非时间差异（不自动判错）
VERIFY_TEMPORAL_UPDATE = "temporal_update"   # 不同报告时间的数字更新
VERIFY_UNVERIFIED = "unverified"
VERIFY_STATUS_ENUM = {
    VERIFY_OFFICIAL, VERIFY_CORROBORATED, VERIFY_SINGLE_SOURCE,
    VERIFY_DATA_DIFFERENCE, VERIFY_TEMPORAL_UPDATE, VERIFY_UNVERIFIED,
}

# 病例统计类型（§十）
CASE_COUNT_SOURCE_TOTAL = "source_total"    # 来源明确提供的总数
CASE_COUNT_COMPUTED_TOTAL = "computed_total"  # 由来源记录显式计算（如 confirmed+suspected），需明确记录
CASE_COUNT_CONFIRMED_ONLY = "confirmed_only"
CASE_COUNT_UNKNOWN = "unknown"

# 来源层级（官方源优先，§七/§十三）
TIER_OFFICIAL = "A"       # WHO / Africa CDC / 国家卫生部 / 疾控机构
TIER_UN_AGENCY = "B"      # UNICEF / OCHA / 其他 UN
TIER_INTERNATIONAL_MEDIA = "B2"  # Reuters/AP/BBC/RFI 等（supplementary/discovery）
TIER_LOCAL = "C"
TIER_AGGREGATOR = "D"     # NewsNow 类，仅 lead discovery

# 数字字段（§十五：未知必须 null，不得用 0 代替）
NUMERIC_FIELDS = (
    "confirmed_cases", "probable_cases", "suspected_cases",
    "total_cases", "deaths", "recoveries",
)

RULES_VERSION = "1.0.0"
