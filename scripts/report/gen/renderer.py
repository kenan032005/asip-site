#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7B §二十六 — 确定性 Renderer（JSON report → HTML/Markdown preview）。

AI 只返回结构化 JSON；本模块负责标题、板块、来源、warning、时间、格式。
不生成生产网页（preview 用），输出到 data/runtime/report_preview/。
"""

import html
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PREVIEW_DIR = ROOT / "data" / "runtime" / "report_preview"

_SECTION_TITLES = {
    "executive_summary": "一、核心摘要",
    "major_security_developments": "二、主要安全动态",
    "political_social_stability": "三、政治与社会稳定",
    "terrorism_armed_violence": "四、恐怖主义与武装暴力",
    "cross_border_regional_risks": "五、跨境与地区风险",
    "public_health_disease_risks": "六、公共卫生与疾病风险",
    "key_changes": "七、较上期主要变化",
    "watch_items": "八、关注事项",
}


def _esc(s):
    return html.escape(str(s or ""))


def render_daily_markdown(report):
    """日报 → Markdown preview。"""
    md = ["# %s" % report.get("title", "非洲社会安全与综合形势日报"),
          "",
          "报告期：%s ～ %s　|　生成：%s" % (
              report.get("period_start"), report.get("period_end"),
              report.get("generated_at")),
          "状态：%s" % (report.get("generation_metadata") or {}).get("report_status", "draft"),
          ""]
    for sec, title in _SECTION_TITLES.items():
        items = report.get(sec, []) or []
        if not items:
            continue
        md.append("## %s" % title)
        md.append("")
        for it in items:
            md.append("### %s" % it.get("headline_zh", it.get("item_id", "")))
            md.append("")
            md.append("**事实**：%s" % it.get("fact_summary", ""))
            if it.get("assessment"):
                md.append("")
                md.append("**判断**：%s" % it["assessment"])
            if it.get("outlook"):
                md.append("")
                md.append("**展望**：%s" % it["outlook"])
            tags = []
            if it.get("single_source_warning"):
                tags.append("⚠ 单一来源")
            if it.get("conflicting"):
                tags.append("⚠ 来源冲突")
            if tags:
                md.append("")
                md.append("> %s" % " ".join(tags))
            if it.get("uncertainties"):
                md.append("")
                md.append("> 不确定：%s" % "；".join(it["uncertainties"]))
            refs = it.get("source_refs") or []
            if refs:
                md.append("")
                md.append("来源：%s" % ", ".join(
                    r.get("source_name") or r.get("source_id") for r in refs))
            md.append("")
    if report.get("overall_assessment"):
        md.append("## 整体评估")
        md.append("")
        md.append(report["overall_assessment"])
        md.append("")
    if report.get("source_notes"):
        md.append("## 来源说明")
        md.append("")
        for sn in report["source_notes"]:
            md.append("- %s%s" % (sn.get("source_name") or sn.get("source_id"),
                                  (" (%s)" % sn["url"]) if sn.get("url") else ""))
    return "\n".join(md)


def render_weekly_markdown(report):
    md = ["# %s" % report.get("title", "重点国家周报"),
          "",
          "国家：%s　|　周：%s ～ %s" % (report.get("country_iso3"),
                                         report.get("week_start"),
                                         report.get("week_end")),
          ""]
    if report.get("executive_assessment"):
        md.append("## 本周评估")
        md.append("")
        md.append(report["executive_assessment"])
        md.append("")
    if report.get("security_trend"):
        md.append("## 安全趋势")
        md.append("")
        md.append(report["security_trend"])
        md.append("")
    for sec, title in (("major_events", "主要事件"),
                       ("terrorism_armed_violence", "恐怖主义与武装暴力"),
                       ("disease_public_health", "公共卫生与疾病")):
        items = report.get(sec, []) or []
        if not items:
            continue
        md.append("## %s" % title)
        md.append("")
        for it in items:
            md.append("- **%s**：%s" % (it.get("headline_zh", it.get("item_id")),
                                        it.get("fact_summary", "")))
        md.append("")
    if report.get("week_over_week_changes"):
        md.append("## 环比变化")
        md.append("")
        for c in report["week_over_week_changes"]:
            md.append("- %s：%s" % (c.get("field"), c.get("direction")))
        md.append("")
    return "\n".join(md)


def render_brief_markdown(report):
    md = ["# %s" % report.get("title", "重大事件简报"),
          "",
          "时间：%s　|　国家：%s%s" % (
              report.get("event_time"), report.get("country"),
              ("（%s）" % report["country_iso3"]) if report.get("country_iso3") else ""),
          ""]
    if report.get("what_happened"):
        md.append("## 事件经过")
        md.append("")
        md.append(report["what_happened"])
        md.append("")
    md.append("## 已确认事实")
    md.append("")
    for f in report.get("confirmed_facts", []) or []:
        md.append("- %s" % f.get("fact"))
    md.append("")
    if report.get("uncertainties"):
        md.append("## 不确定性")
        md.append("")
        for u in report["uncertainties"]:
            md.append("- %s" % u)
        md.append("")
    if report.get("immediate_implications"):
        md.append("## 即时影响")
        md.append("")
        for i in report["immediate_implications"]:
            md.append("- %s" % i)
        md.append("")
    return "\n".join(md)


def render_to_html(md, title):
    return """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>%s</title>
<style>
body{max-width:860px;margin:24px auto;padding:0 20px;font-family:"Microsoft YaHei",sans-serif;
line-height:1.7;color:#1f2937;background:#fff}
h1{border-bottom:2px solid #2563eb;padding-bottom:8px;color:#1e3a8a}
h2{color:#1e3a8a;margin-top:28px}
h3{color:#374151;margin-bottom:4px}
blockquote{color:#92400e;background:#fef3c7;border-left:4px solid #f59e0b;margin:8px 0;padding:6px 12px}
</style></head><body>
%s
</body></html>""" % (title, md.replace("\n\n", "</p><p>").replace("\n", "<br>").replace("<p></p>", ""))


def save_preview(report, task_type, subdir="latest"):
    """JSON report → preview 文件（内部 runtime，不进 dist）。"""
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    rid = report.get("report_id", "report_%d" % int(time.time()))
    if task_type == "africa_daily":
        md = render_daily_markdown(report)
    elif task_type == "country_weekly":
        md = render_weekly_markdown(report)
    else:
        md = render_brief_markdown(report)
    d = PREVIEW_DIR / task_type
    d.mkdir(parents=True, exist_ok=True)
    (d / ("%s.md" % rid)).write_text(md, encoding="utf-8")
    (d / ("%s.html" % rid)).write_text(
        render_to_html(md, report.get("title", rid)), encoding="utf-8")
    (d / ("%s.json" % rid)).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return d / ("%s.md" % rid)
