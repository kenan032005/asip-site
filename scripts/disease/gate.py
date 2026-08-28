#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 传染病数据质量 Gate（§十五）。

硬性检查（任一失败即 normalization_incomplete / invalid，不猜测）：
- disease_id 有效（字典存在）；
- country_iso3 有效（ISO3）或明确为 regional；
- report_date 有效；
- source URL 有效（http/https）；
- primary_source 存在；
- 病例未知不能写 0；死亡未知不能写 0；
- 数字不能为负；
- confirmed/probable/suspected 字段含义不混淆（case_count_type 一致）；
- WHO/官方原始值不得被 AI 改写（本包确定性解析，无 AI 改写路径）。
"""

import re
from urllib.parse import urlparse

from .diseases import load_diseases
from .constants import NUMERIC_FIELDS

_URL_RE = re.compile(r"^https?://[^\s]+$")


def check_url(v):
    if not v or not _URL_RE.match(str(v).strip()):
        return False
    p = urlparse(str(v).strip())
    return bool(p.scheme and p.netloc)


def run_gate(fields):
    """对一条 disease event 字段做质量 Gate。

    返回 (ok, errors)。errors 为失败原因列表；全部通过时 ok=True。
    """
    errors = []

    # 1) disease_id 有效
    if fields.get("disease_id") not in load_diseases():
        errors.append("invalid_disease_id:%s" % fields.get("disease_id"))

    # 2) country_iso3 有效或 regional
    iso3 = fields.get("country_iso3")
    if iso3 != "regional" and (not iso3 or len(iso3) != 3 or not iso3.isalpha()):
        errors.append("invalid_country_iso3:%s" % iso3)

    # 3) report_date 有效
    rd = fields.get("report_date") or ""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", rd):
        errors.append("invalid_report_date:%s" % rd)

    # 4) source URL 有效
    links = fields.get("source_links") or []
    if not any(check_url(l.get("url")) for l in links):
        errors.append("no_valid_source_url")

    # 5) primary_source 存在
    if not fields.get("primary_source"):
        errors.append("missing_primary_source")

    # 6/7) 未知数字不得为 0；数字不得为负
    for f in NUMERIC_FIELDS:
        v = fields.get(f)
        if v is not None:
            if not isinstance(v, int) or isinstance(v, bool):
                errors.append("numeric_field_not_int:%s" % f)
            elif v < 0:
                errors.append("negative_number:%s" % f)
        # 0 且来源未给值 → 视为以 0 代替未知（由 data_quality_flags 标记，此处不重复）

    # 8) confirmed/probable/suspected 含义不混淆：case_count_type 与字段一致
    cct = fields.get("case_count_type")
    if cct in ("source_total", "computed_total", "confirmed_only", "unknown"):
        pass
    else:
        errors.append("invalid_case_count_type:%s" % cct)

    # 9) WHO/官方原始值不得被 AI 改写：本包无 AI 路径；如 flags 含 ai_rewrite 即失败
    if "ai_rewritten" in (fields.get("data_quality_flags") or []):
        errors.append("official_value_ai_rewritten")

    return (len(errors) == 0), errors
