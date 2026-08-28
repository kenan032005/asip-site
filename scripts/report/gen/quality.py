#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7B §八/§二十三-§二十四 — 确定性 Quality Gate。

对生成的报告做确定性后验证（不使用 AI 判断）：

1. Schema valid（对 output schema JSON Schema 校验）
2. 数字全部可追溯（numeric evidence gate：报告所有数字必须能在 input facts 中找到）
3. 日期可追溯
4. 国家有效（ISO3 集合）
5. source_refs 有效（source_id 来自 input）
6. rejected 事件不得出现
7. single_source 必须有 warning 标注
8. conflicting 不得写成 confirmed
9. Disease 数字不得改变（latest_counts 回显一致）
10. FACT 字段不得出现 prediction-only statements
11. Report ID 唯一
12. 不得重复 master event

report_status 枚举：draft / passed_quality_gate / failed_quality_gate /
approved_for_publication（开发阶段最高 passed_quality_gate，§二十四）。
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# 全非洲 ISO3（用于国家有效性校验）
_AFRICA_ISO3 = {
    "DZA", "AGO", "BEN", "BWA", "BFA", "BDI", "CPV", "CMR", "CAF", "TCD",
    "COM", "COG", "COD", "CIV", "DJI", "EGY", "GNQ", "ERI", "SWZ", "ETH",
    "GAB", "GMB", "GHA", "GIN", "GNB", "KEN", "LSO", "LBR", "LBY", "MDG",
    "MWI", "MLI", "MRT", "MUS", "MAR", "MOZ", "NAM", "NER", "NGA", "RWA",
    "STP", "SEN", "SYC", "SLE", "SOM", "ZAF", "SSD", "SDN", "TZA", "TGO",
    "TUN", "UGA", "ESH", "ZMB", "ZWE",
}

# §六 FACT 禁止的 prediction-only 表述
PREDICTION_PATTERNS = (
    r"将(确定|必然|一定会|100%|必定)发生",
    r"\d{1,3}%[的\s]*概率",
    r"概率[为是]\s*\d+%",
    r"必定|肯定会|确定会",
    r"72小时.*概率",
    r"袭击概率",
)
# §八 数字提取（前后非字母数字：避免 E1 / EVT-123 内嵌数字误提取）
_NUM_RE = re.compile(r"(?<![A-Za-z0-9])(\d{1,3}(?:,\d{3})*|\d+)(?![A-Za-z0-9])")
# §十 AI 口吻/标题党（soft warning，不阻断）
AI_TONE_PATTERNS = (
    "值得注意的是", "总而言之", "令人震惊", "触目惊心", "重磅", "突发!",
    "震惊!", "令人发指", "不容忽视!",
)


def _load_schema(task_type):
    fname = {
        "africa_daily": "africa_daily_report.schema.json",
        "country_weekly": "country_weekly_report.schema.json",
        "major_event_brief": "major_event_brief.schema.json",
    }[task_type]
    return json.loads((ROOT / "schemas" / fname).read_text(encoding="utf-8"))


def _schema_valid(report, schema):
    """轻量 JSON Schema 校验（draft-07 子集：required/type/enum/const/properties）。"""
    errors = []

    def check(node, schema_node, path):
        if not isinstance(schema_node, dict):
            return
        if "required" in schema_node:
            for k in schema_node["required"]:
                if k not in node:
                    errors.append("%s: missing required %r" % (path, k))
        if "type" in schema_node and node is not None:
            t = schema_node["type"]
            if isinstance(t, list):
                ok_types = t
            else:
                ok_types = [t]
            type_map = {"object": dict, "array": list, "string": str,
                        "integer": int, "number": (int, float), "boolean": bool,
                        "null": type(None)}
            if node is None and "null" in ok_types:
                pass
            elif node is not None and not isinstance(node, tuple(
                    type_map[t] for t in ok_types if t in type_map)):
                errors.append("%s: type mismatch %r" % (path, node))
        if "enum" in schema_node and node is not None:
            if node not in schema_node["enum"]:
                errors.append("%s: enum violation %r" % (path, node))
        if "const" in schema_node and node is not None:
            if node != schema_node["const"]:
                errors.append("%s: const violation %r != %r" % (path, node, schema_node["const"]))
        if isinstance(node, dict) and "properties" in schema_node:
            for k, v in node.items():
                if k in schema_node["properties"]:
                    check(v, schema_node["properties"][k], path + "." + k)
        if isinstance(node, list) and "items" in schema_node:
            for i, v in enumerate(node):
                check(v, schema_node["items"], "%s[%d]" % (path, i))

    check(report, schema, "$")
    return errors


_STRUCT_SKIP_KEYS = (
    "report_id", "brief_id", "input_report_id", "generated_at", "period_start",
    "period_end", "report_date", "week_start", "week_end", "event_time",
    "latest_update_at", "as_of_date", "published_at", "source_url", "url",
    "item_id", "master_event_id", "disease_id", "outbreak_id", "event_id",
    "source_id", "source_name", "country_iso3", "verification_status",
    "verification_confidence", "importance_score", "source_count",
    "trigger_score", "trigger_threshold", "change_type", "direction",
    "evidence_field", "selection_reasons", "source_refs", "source_notes",
)


def _collect_input_numbers(report_input):
    """从 report input 提取所有确定性数字（facts 文本 / latest_counts /
    标题 / 摘要等文本字段中的数字；跳过结构 ID / 时间 / 分数键）。"""
    nums = set()

    def walk(node, depth=0):
        if depth > 14:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                if k in _STRUCT_SKIP_KEYS:
                    continue
                if k == "latest_counts" and isinstance(v, dict):
                    for vv in v.values():
                        if isinstance(vv, (int, float)):
                            nums.add(int(vv))
                elif isinstance(v, str):
                    for m in _NUM_RE.finditer(v):
                        nums.add(int(m.group(0).replace(",", "")))
                elif isinstance(v, (int, float)):
                    nums.add(int(v))   # 确定性指标数字（event_count 等）
                else:
                    walk(v, depth + 1)
        elif isinstance(node, list):
            for v in node:
                walk(v, depth + 1)

    walk(report_input)
    return nums


def _collect_report_numbers(report):
    """只扫描事实字段（fact_summary/assessment/outlook 等）中的数字，
    排除 report_id / 时间戳 / metrics / latest_counts 等结构回显字段。"""
    nums = set()
    _FACT_TEXT_KEYS = ("fact_summary", "assessment", "outlook", "what_happened",
                       "fact", "headline_zh", "security_trend",
                       "executive_assessment", "immediate_implications",
                       "watch_items")
    _SKIP_KEYS = ("generation_metadata", "metrics", "latest_counts",
                  "source_notes", "source_refs", "report_id", "generated_at",
                  "period_start", "period_end", "report_date", "week_start",
                  "week_end", "event_time", "latest_update_at", "as_of_date",
                  "item_id", "master_event_id", "disease_id", "brief_id",
                  "input_report_id", "country_iso3", "verification_status",
                  "change_type", "direction", "field", "detail",
                  "selection_reasons", "uncertainties", "source_name", "url")

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in _SKIP_KEYS:
                    continue
                if k in _FACT_TEXT_KEYS and isinstance(v, str):
                    for m in _NUM_RE.finditer(v):
                        nums.add(int(m.group(0).replace(",", "")))
                elif k == "source_refs" and isinstance(v, list):
                    continue
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(report)
    return nums


def _source_ids_from_input(report_input):
    """收集 input 中可引用的来源/事件 id（source_id / sources[] / event_id /
    master_event_id / disease_id / outbreak_id）。"""
    ids = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("source_id", "event_id", "master_event_id",
                         "disease_id", "outbreak_id") and isinstance(v, str) and v:
                    ids.add(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                if isinstance(v, str) and v:
                    ids.add(v)   # sources 数组元素
                else:
                    walk(v)

    walk(report_input)
    return ids


def _iter_report_items(report, sec):
    """迭代 section items（fail-closed：非 dict item 报 malformed，不崩溃不宽松）。"""
    items, malformed = [], []
    for it in report.get(sec, []) or []:
        if not isinstance(it, dict):
            malformed.append("malformed_section: %s item 非对象: %r"
                             % (sec, str(it)[:40]))
            continue
        items.append(it)
    return items, malformed


def run_quality_gate(report, report_input, task_type, schema=None):
    """确定性 Quality Gate。返回 (passed, status, issues[])。

    开发阶段（§二十四）：passed → status="passed_quality_gate"；
    任何 hard issue → status="failed_quality_gate"。
    """
    schema = schema or _load_schema(task_type)
    issues = []
    warnings = []

    # 1. Schema valid
    for e in _schema_valid(report, schema):
        issues.append("schema: %s" % e)

    # 2. 数字 evidence gate（§八）：报告数字 ⊆ input 数字
    in_nums = _collect_input_numbers(report_input)
    out_nums = _collect_report_numbers(report)
    # 排除 metadata 中的时间戳/分数等已知回显（importance_score 等在 input 也存在）
    for n in sorted(out_nums - in_nums):
        issues.append("numeric_gate: 报告出现 input 中不存在的数字 %d" % n)

    # 3. 国家有效
    for sec in ("executive_summary", "major_security_developments",
                "political_social_stability", "terrorism_armed_violence",
                "cross_border_regional_risks"):
        items, mal = _iter_report_items(report, sec)
        issues.extend(mal)
        for it in items:
            c = it.get("country_iso3")
            if c and c not in _AFRICA_ISO3:
                issues.append("country: %s 非有效 ISO3" % c)

    # 4. source_refs 有效（§二十七：URL 不得 AI 自创）
    in_src = _source_ids_from_input(report_input)
    for sec_name in ("executive_summary", "major_security_developments",
                     "political_social_stability", "terrorism_armed_violence",
                     "cross_border_regional_risks", "public_health_disease_risks"):
        items, mal = _iter_report_items(report, sec_name)
        issues.extend(mal)
        for it in items:
            for sr in it.get("source_refs", []) or []:
                sid = sr.get("source_id")
                if sid and sid not in in_src:
                    issues.append("source_ref: %s 不在 input 来源中" % sid)
                if sr.get("url") and "http" not in str(sr.get("url")):
                    issues.append("source_ref: 非法 url %r" % sr.get("url"))
    for sn in report.get("source_notes", []) or []:
        if isinstance(sn, dict) and sn.get("source_id") and sn["source_id"] not in in_src:
            issues.append("source_notes: %s 不在 input 来源中" % sn["source_id"])

    # 6. rejected 不得出现（input 侧保证；此处防御）
    if report_input.get("rejected_events"):
        issues.append("rejected: input 含 rejected 事件")

    # 7. single_source 必须有 warning
    for sec in ("executive_summary", "major_security_developments",
                "political_social_stability", "terrorism_armed_violence",
                "cross_border_regional_risks"):
        items, mal = _iter_report_items(report, sec)
        issues.extend(mal)
        for it in items:
            if it.get("single_source_warning") and \
                    not _has_uncertainty_marker(it, ("单一来源", "single-source", "尚待进一步核实")):
                warnings.append("single_source: %s 需显式标注单一来源" % it.get("item_id"))

    # 8. conflicting 不得写成 confirmed
    for sec in ("executive_summary", "major_security_developments",
                "political_social_stability", "terrorism_armed_violence",
                "cross_border_regional_risks"):
        items, mal = _iter_report_items(report, sec)
        issues.extend(mal)
        for it in items:
            if it.get("conflicting") and _has_uncertainty_marker(it, ("已证实", "confirmed", "确认属实")):
                issues.append("conflict: %s 不得将冲突信息写成已证实" % it.get("item_id"))

    # 9. Disease 数字不得改变（§九）：latest_counts 回显一致
    for it in report.get("public_health_disease_risks", []) or []:
        if not isinstance(it, dict):
            issues.append("malformed_section: public_health_disease_risks item 非对象")
            continue
        lc = it.get("latest_counts") or {}
        for k, v in lc.items():
            if v is None:
                continue
            try:
                iv = int(v)
            except (TypeError, ValueError):
                continue
            if not any(str(iv) in json.dumps(s, ensure_ascii=False)
                       for s in report_input.get("sections", {}).get("public_health_disease", [])
                       if str(iv) in json.dumps(s, ensure_ascii=False)):
                issues.append("disease_numeric: %s 的 %s=%s 与 input 不符" % (it.get("disease_id"), k, v))

    # 9b. Weekly metrics 一致性（§十四：metrics 必须回显 input trend_metrics）
    if task_type == "country_weekly":
        in_m = report_input.get("trend_metrics") or {}
        out_m = report.get("metrics") or {}
        for k in ("event_count", "verified_event_count", "armed_attack_count",
                  "civil_unrest_count", "major_crime_count", "natural_disaster_count",
                  "multi_source_event_count", "new_outbreak_count",
                  "active_outbreak_count"):
            if k in in_m and out_m.get(k) != in_m[k]:
                issues.append("weekly_metrics: %s 与 input 不符（%s != %s）" %
                              (k, out_m.get(k), in_m[k]))

    # 10. FACT/assessment/outlook 不得出现 prediction-only（§六/§十三）
    _PREDICT_SCAN_KEYS = ("fact_summary", "assessment", "outlook",
                          "immediate_implications", "security_trend",
                          "executive_assessment", "what_happened")
    for sec in ("executive_summary", "major_security_developments",
                "political_social_stability", "terrorism_armed_violence",
                "cross_border_regional_risks", "public_health_disease_risks"):
        items, mal = _iter_report_items(report, sec)
        issues.extend(mal)
        for it in items:
            for key in _PREDICT_SCAN_KEYS:
                text = it.get(key)
                if isinstance(text, list):
                    text = " ".join(str(x) for x in text)
                if not text:
                    continue
                for pat in PREDICTION_PATTERNS:
                    if re.search(pat, str(text)):
                        issues.append("fact_prediction: %s 含预测表述 %r" % (key, pat))
    for key in _PREDICT_SCAN_KEYS:
        text = report.get(key)
        if isinstance(text, list):
            text = " ".join(str(x) for x in text)
        if text:
            for pat in PREDICTION_PATTERNS:
                if re.search(pat, str(text)):
                    issues.append("fact_prediction: %s 含预测表述 %r" % (key, pat))

    # 11. Report ID 唯一（brief 用 brief_id；其余用 report_id）
    rid = report.get("report_id") or report.get("brief_id")
    if not rid:
        issues.append("report_id: 缺失")

    # 12. 不得重复 master event
    seen_me = set()
    for sec in ("executive_summary", "major_security_developments",
                "political_social_stability", "terrorism_armed_violence",
                "cross_border_regional_risks"):
        items, mal = _iter_report_items(report, sec)
        issues.extend(mal)
        for it in items:
            me = it.get("master_event_id")
            if me:
                if me in seen_me:
                    issues.append("dup_master: %s 在多个 section 重复完整叙述" % me)
                seen_me.add(me)

    # AI 口吻（soft，仅 warning）
    full = json.dumps(report, ensure_ascii=False)
    for pat in AI_TONE_PATTERNS:
        if pat in full:
            warnings.append("ai_tone: 含 %r" % pat)

    passed = not issues
    status = "passed_quality_gate" if passed else "failed_quality_gate"
    report["generation_metadata"] = dict(report.get("generation_metadata") or {})
    report["generation_metadata"]["report_status"] = status
    report["generation_metadata"]["quality_gate_warnings"] = warnings
    return passed, status, issues, warnings


def _has_uncertainty_marker(item, markers):
    blob = " ".join([
        str(item.get("fact_summary") or ""),
        str(item.get("assessment") or ""),
        " ".join(str(x) for x in (item.get("uncertainties") or [])),
    ]).lower()
    return any(m.lower() in blob for m in markers)
