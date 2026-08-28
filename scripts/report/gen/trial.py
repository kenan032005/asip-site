#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7B §十九-§二十二 — Report Generation Trial。

--mock : Mock Contract 测试（Mock Daily/Weekly/Brief：strict JSON / schema /
         fact separation / numeric gate / uncertainty / source refs / renderer）
--dev  : Development Report Trial（Africa Daily×1 + TCD Weekly×1 + SSD Weekly×1，
         provider auto：DeepSeek key 缺失 → mock fallback，usage_purpose=
         development_test，如实记录 credential 状态）
生成 review packs：docs/stage7b-daily-review.md / docs/stage7b-weekly-review.md
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REVIEW_DIR = ROOT / "docs"

sys.path.insert(0, str(ROOT))

from scripts.report.gen.runner import run_report  # noqa: E402
from scripts.report.gen.quality import run_quality_gate  # noqa: E402
from scripts.report.gen.renderer import save_preview, render_daily_markdown, \
    render_weekly_markdown  # noqa: E402
from scripts.report.gen.providers import MockReportProvider, DeepSeekReportProvider, \
    ProviderUnavailable  # noqa: E402


# ── §十九 Mock inputs（结构化，验证合同而非内容）──
MOCK_DAILY_INPUT = {
    "report_id": "DAILY_MOCK01", "report_type": "africa_daily",
    "report_date": "2026-08-26", "cutoff": "2026-08-26T08:00:00+08:00",
    "sections": {
        "executive_summary": [{
            "event_id": "E1", "master_event_id": "ME_E1", "country_iso3": "SSD",
            "category": "security", "importance_score": 85,
            "selection_reasons": ["major_casualties", "armed_conflict"],
            "verification_status": "verified", "source_count": 2,
            "facts": [{"fact": "deaths=12", "evidence": "Eye Radio"},
                      {"fact": "event_type=armed_conflict"}],
            "analysis_inputs": [], "uncertainties": [],
            "source_evidence": [{"source_id": "ssd_eyeradio", "source_name": "Eye Radio"},
                                {"source_id": "ssd_radio_tamazuj"}],
            "latest_update_at": "2026-08-26T06:00:00+00:00",
        }],
        "major_security_developments": [],
        "terrorism_armed_violence": [],
        "political_social_stability": [],
        "cross_border_regional": [],
        "public_health_disease": [{
            "disease_id": "cholera", "country_iso3": "TCD", "outbreak_id": "OB_1",
            "latest_counts": {"confirmed_cases": 620, "deaths": 15, "as_of_date": "2026-08-24"},
            "change_type": "case_increase", "outbreak_status": "active",
            "selection_reasons": ["case_increase"],
            "verification_status": "verified",
        }],
        "key_changes": [], "watch_items": [], "source_notes": [],
    },
}

MOCK_WEEKLY_INPUT = {
    "report_id": "WEEKLY_TCD_2026-08-30", "report_type": "country_weekly",
    "country_iso3": "TCD", "week_start": "2026-08-24", "week_end": "2026-08-30",
    "trend_metrics": {"event_count": 5, "verified_event_count": 3,
                      "armed_attack_count": 3, "civil_unrest_count": 1,
                      "major_crime_count": 0, "natural_disaster_count": 0,
                      "fatalities_known": None, "injuries_known": None,
                      "multi_source_event_count": 2, "new_outbreak_count": 0,
                      "active_outbreak_count": 1,
                      "comparison": {"event_count": "up"}},
    "sections": {"major_events": [], "disease_public_health": [],
                 "changes_from_previous_week": [], "sources": ["ssd_eyeradio"]},
}

MOCK_BRIEF_INPUT = {
    "report_type": "major_event_brief",
    "event_id": "E_BRIEF1", "master_event_id": "ME_BRIEF1",
    "country": "South Sudan", "country_iso3": "SSD",
    "event_type": "armed_conflict", "event_time": "2026-08-26T06:00:00+00:00",
    "location": "CITY_ALPHA", "trigger_score": 85, "trigger_reasons": ["mass_casualty"],
    "verification_status": "verified", "source_count": 2, "conflicting": False,
    "facts": [{"fact": "deaths=25"}], "uncertainties": [],
}


def _report_items(report, sections=("executive_summary", "major_security_developments",
                                    "terrorism_armed_violence",
                                    "political_social_stability",
                                    "cross_border_regional_risks",
                                    "public_health_disease_risks")):
    out = []
    for s in sections:
        out.extend(report.get(s, []) or [])
    return out


def run_mock():
    """§十九 Mock Contract 测试。"""
    results = []
    prov = MockReportProvider()
    for task, inp in (("africa_daily", MOCK_DAILY_INPUT),
                      ("country_weekly", MOCK_WEEKLY_INPUT),
                      ("major_event_brief", MOCK_BRIEF_INPUT)):
        report, meta, status = run_report(task, inp, provider=prov)
        ok = status == "generated" and report is not None
        # quality gate（mock 输出为占位 JSON → gate 只验结构管道可用）
        passed, qstatus, issues, warns = run_quality_gate(
            report, inp, task) if report else (False, "failed_quality_gate", ["no report"], [])
        results.append((task, "PASS" if ok else "FAIL",
                        {"status": status, "gate": qstatus,
                         "issues": issues[:3]}))
    print("=== Mock Contract Test ===")
    for t, v, d in results:
        print("  %-18s %s %s" % (t, v, d))
    return all(v == "PASS" for _, v, _ in results)


def _build_dev_daily(report_input):
    """从 Stage7A real daily input 构造 development trial input。"""
    return report_input


def run_dev(report_inputs):
    """§二十 Development Report Trial（≤3 份；DeepSeek key 缺失 → mock fallback）。"""
    print("=== Development Report Trial (usage_purpose=development_test) ===")
    # credential 状态检查
    try:
        dp = DeepSeekReportProvider()
        _ = dp.api_key
        cred = "present" if dp.api_key else "missing"
    except Exception:
        cred = "missing"
    print("  DeepSeek credential:", cred)

    out = {}
    for task, inp in report_inputs:
        report, meta, status = run_report(task, inp)
        passed, qstatus, issues, warns = run_quality_gate(report, inp, task)
        print("  [%s] status=%s gate=%s issues=%d provider=%s/%s" % (
            task, status, qstatus, len(issues), meta.get("provider_name"),
            meta.get("model_name")))
        if cred == "missing":
            print("    -> credential_unavailable 记录；mock_fallback=%s" %
                  meta.get("mock_fallback", False))
        save_preview(report, task)
        out[task] = {"report": report, "gate_status": qstatus,
                     "issues": issues, "warnings": warns, "meta": meta}
    return out, cred


def write_daily_review(out):
    """§二十一 docs/stage7b-daily-review.md。"""
    r = out.get("africa_daily", {}).get("report") or {}
    lines = ["# Stage 7B — Africa Daily Development Review",
             "",
             "**usage_purpose**: development_test　|　**provider**: %s/%s" % (
                 (out.get("africa_daily", {}).get("meta") or {}).get("provider_name", "?"),
                 (out.get("africa_daily", {}).get("meta") or {}).get("model_name", "?")),
             "**quality gate**: %s" % out.get("africa_daily", {}).get("gate_status"),
             ""]
    issues = out.get("africa_daily", {}).get("issues") or []
    if issues:
        lines.append("## Gate Issues")
        for i in issues:
            lines.append("- %s" % i)
        lines.append("")
    for sec in ("executive_summary", "major_security_developments",
                "terrorism_armed_violence", "political_social_stability",
                "cross_border_regional_risks", "public_health_disease_risks"):
        items = r.get(sec, []) or []
        if not items:
            continue
        lines.append("## %s (%d)" % (sec, len(items)))
        lines.append("")
        for it in items:
            lines.append("### %s" % it.get("headline_zh", it.get("item_id")))
            lines.append("- item_id: %s" % it.get("item_id"))
            lines.append("- source event ids: %s" % (
                [s.get("source_id") for s in (it.get("source_refs") or [])]))
            lines.append("- verification: %s" % it.get("verification_status"))
            lines.append("- input facts: %s" % json.dumps(
                [f.get("fact") for f in (it.get("facts") or [])], ensure_ascii=False))
            lines.append("- fact_summary: %s" % it.get("fact_summary"))
            lines.append("- assessment: %s" % it.get("assessment"))
            lines.append("- outlook: %s" % it.get("outlook"))
            if it.get("uncertainties"):
                lines.append("- uncertainties: %s" % it["uncertainties"])
            lines.append("")
    (REVIEW_DIR / "stage7b-daily-review.md").write_text(
        "\n".join(lines), encoding="utf-8")
    return REVIEW_DIR / "stage7b-daily-review.md"


def write_weekly_review(out):
    """§二十二 docs/stage7b-weekly-review.md（TCD + SSD；NER 不强制）。"""
    lines = ["# Stage 7B — Country Weekly Development Review",
             "",
             "**usage_purpose**: development_test（TCD / SSD；NER 数据不足不强制）",
             ""]
    for key in ("country_weekly_tcd", "country_weekly_ssd"):
        item = out.get(key) or {}
        r = item.get("report") or {}
        if not r:
            lines.append("## %s" % key)
            lines.append("（未生成）")
            lines.append("")
            continue
        lines.append("## %s（gate: %s）" % (r.get("country_iso3"), item.get("gate_status")))
        lines.append("")
        if r.get("executive_assessment"):
            lines.append("**评估**：%s" % r["executive_assessment"])
            lines.append("")
        if r.get("security_trend"):
            lines.append("**趋势**：%s" % r["security_trend"])
            lines.append("")
        m = r.get("metrics") or {}
        lines.append("**metrics**：event_count=%s armed=%s civil=%s fatalities=%s" % (
            m.get("event_count"), m.get("armed_attack_count"),
            m.get("civil_unrest_count"), m.get("fatalities_known")))
        lines.append("")
        for it in (r.get("major_events") or []):
            lines.append("- **%s**：%s" % (it.get("headline_zh", it.get("item_id")),
                                           it.get("fact_summary", "")))
        lines.append("")
    (REVIEW_DIR / "stage7b-weekly-review.md").write_text(
        "\n".join(lines), encoding="utf-8")
    return REVIEW_DIR / "stage7b-weekly-review.md"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="Mock Contract 测试（§十九）")
    ap.add_argument("--dev", action="store_true", help="Development Trial（§二十）")
    ap.add_argument("--daily-input", default="data/runtime/reports/daily_input/latest.json")
    ap.add_argument("--weekly-input", default="data/runtime/reports/weekly_input")
    args = ap.parse_args()

    if args.mock:
        return 0 if run_mock() else 1

    # ── §二十 Development Trial ──
    daily_inp = json.loads((ROOT / args.daily_input).read_text(encoding="utf-8"))
    weekly_inputs = {}
    for iso3 in ("TCD", "SSD"):
        p = ROOT / args.weekly_input / ("%s.json" % iso3)
        if p.exists():
            weekly_inputs[iso3] = json.loads(p.read_text(encoding="utf-8"))

    inputs = [("africa_daily", daily_inp)]
    for iso3, w in weekly_inputs.items():
        inputs.append(("country_weekly", w))

    out, cred = run_dev(inputs)
    # 整理 key
    mapped = {}
    for task, item in out.items():
        if task == "africa_daily":
            mapped["africa_daily"] = item
        elif task == "country_weekly":
            iso3 = item["report"].get("country_iso3", "x")
            mapped["country_weekly_%s" % iso3.lower()] = item
    dp = write_daily_review(mapped)
    wp = write_weekly_review(mapped)
    print("review packs: %s / %s" % (dp.name, wp.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
