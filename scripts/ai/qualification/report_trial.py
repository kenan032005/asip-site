#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8B — Real Report Development Trial（§十九-§二十三）。

仅使用 DeepSeek V4 Flash（Flash-only 硬门禁）生成：
  Africa Daily ×1（真实 daily_input/latest.json）
  TCD Weekly ×1 / SSD Weekly ×1（真实 weekly input）
  Major Event Brief ×1（无真实 trigger → qualification_sample 结构化输入）

每份走 Stage7B Deterministic Quality Gate（scripts/report/gen/quality.py），
状态最高 passed_quality_gate（不得 approved_for_publication）。
真实草稿回填 docs/stage8b-real-ai-review.md 供 ChatGPT + 用户人工验收。

credential 缺失 / provider 未达 Primary → 优雅跳过（REPORT_TRIAL_SKIPPED），
不改 Canonical/Public，不覆盖旧结果。

用法：
  python scripts/ai/qualification/report_trial.py [--provider deepseek]
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

ARTIFACT_DIR = ROOT / "data" / "runtime" / "ai_qualification" / "stage8b"
REVIEW = ROOT / "docs" / "stage8b-real-ai-review.md"
OUT_DIR = ARTIFACT_DIR / "report_trial"


def credential_ok():
    return bool(os.environ.get("ASIP_DEEPSEEK_API_KEY", "").strip())


def run_one(provider, task_type, payload, system_prompt, prompt_version,
            schema_rel, label):
    """单份报告：provider → strict JSON → quality gate → artifact。"""
    from scripts.ai.qualification.stage8b import strict_json_parse
    from scripts.ai.providers.deepseek_v4_flash import (
        DeepSeekV4FlashProvider, ALLOWED_DEEPSEEK_MODELS)
    import hashlib

    prov = DeepSeekV4FlashProvider()
    task = {
        "task_id": "TRIAL_%s" % label,
        "task_type": task_type,
        "prompt_version": prompt_version,
        "system_text": system_prompt,
        "user_text": "INPUT:\n" + json.dumps(payload, ensure_ascii=False)[:6000],
        "usage_purpose": "development_report_trial",
        "max_output_tokens": 4096,
    }
    res = prov.submit_task(task)
    if res.get("status") != "succeeded":
        return {"label": label, "status": "failed",
                "error": ((res.get("result") or {}).get("error") or {}).get("code"),
                "returned_model": (res.get("result") or {}).get("returned_model")}
    rr = res.get("result") or {}
    returned = rr.get("returned_model")
    if returned and returned not in ALLOWED_DEEPSEEK_MODELS:
        return {"label": label, "status": "failed",
                "error": "model_mismatch:%s" % returned,
                "returned_model": returned}
    raw = rr.get("text") or ""
    ok_json, parsed, jerr = strict_json_parse(raw)
    if not ok_json:
        return {"label": label, "status": "failed",
                "error": "invalid_response_shape:%s" % jerr,
                "returned_model": returned, "raw_excerpt": raw[:300]}

    # Stage7B Deterministic Quality Gate（§十五/§二十一）
    from scripts.report.gen.quality import run_quality_gate
    try:
        passed, qstatus, issues, warns = run_quality_gate(parsed, payload, task_type)
    except Exception as e:
        passed, qstatus, issues = False, "gate_error", [str(e)[:120]]
    record = {
        "label": label, "task_type": task_type, "prompt_version": prompt_version,
        "provider": "deepseek", "requested_model": "deepseek-v4-flash",
        "returned_model": returned,
        "input_hash": hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12],
        "generated_at": rr.get("generated_at") or __import__("time").strftime(
            "%Y-%m-%dT%H:%M:%S+08:00"),
        "quality_status": qstatus if passed else "failed_quality_gate",
        "quality_issues": (issues or [])[:10],
        "tokens": {"input_tokens": rr.get("input_tokens"),
                   "output_tokens": rr.get("output_tokens"),
                   "total_tokens": rr.get("total_tokens")},
        "report": parsed,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / ("%s.json" % label)).write_text(
        json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    return record


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="deepseek")
    args = ap.parse_args(argv)

    if not credential_ok():
        print("REPORT_TRIAL_SKIPPED credential_injection_failed")
        return 0

    from scripts.ai.qualification import stage8b as q

    # 输入：真实报告契约（与 20-case 同一来源）
    daily = q.load_json("data/runtime/reports/daily_input/latest.json") or {}
    weekly = {c: q.load_json("data/runtime/reports/weekly_input/%s.json" % c)
              for c in ("TCD", "SSD")}
    brief = q._brief_input(security=True)

    prompts = {
        "africa_daily": (ROOT / "config" / "prompts" / "africa_daily_report_v1.md"),
        "country_weekly": (ROOT / "config" / "prompts" / "country_weekly_report_v1.md"),
        "major_event_brief": (ROOT / "config" / "prompts" / "major_event_brief_v1.md"),
    }

    def sys_text(tt):
        p = prompts.get(tt)
        if p and p.exists():
            return p.read_text(encoding="utf-8")
        return "Generate the structured %s per contract. JSON only." % tt

    jobs = [
        ("africa_daily", daily, "africa-daily-v1.0.0", "schemas/africa_daily_report.schema.json", "daily"),
        ("country_weekly", weekly.get("TCD"), "country-weekly-v1.0.0", "schemas/country_weekly_report.schema.json", "weekly-tcd"),
        ("country_weekly", weekly.get("SSD"), "country-weekly-v1.0.0", "schemas/country_weekly_report.schema.json", "weekly-ssd"),
        ("major_event_brief", brief, "major-event-brief-v1.0.0", "schemas/major_event_brief.schema.json", "brief"),
    ]
    results = []
    for tt, payload, pv, schema_rel, label in jobs:
        if not payload:
            print("REPORT_TRIAL_SKIPPED missing input for %s" % label)
            continue
        r = run_one(args.provider, tt, payload, sys_text(tt), pv, schema_rel, label)
        results.append(r)
        print("  [trial] %-12s %s quality=%s returned_model=%s" % (
            label, r.get("status"), r.get("quality_status"), r.get("returned_model")))

    # 回填 review pack（真实草稿节）
    daily_r = next((r for r in results if r.get("label") == "daily"), None)
    append_review(daily_r, results)
    return 0


def append_review(daily, results):
    """§二十/§二十二：把真实模型草稿逐条写入 review pack。"""
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\n---\n", "## 真实 AI 草稿（DeepSeek V4 Flash，credential 注入后生成）\n"]
    if not daily or daily.get("status") != "ok":
        lines.append("> 本轮未生成真实草稿（provider 未达 Primary 或 credential 缺失）。\n")
        with open(REVIEW, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return
    rep = daily.get("report") or {}
    lines.append("### Africa Daily（真实模型草稿）\n")
    lines.append("| 项 | 值 |\n| --- | --- |")
    for k in ("provider", "requested_model", "returned_model", "prompt_version",
              "input_hash", "generated_at", "quality_status"):
        lines.append("| %s | %s |" % (k, daily.get(k)))
    lines.append("")
    for sec, title in (("executive_summary", "核心摘要"),
                       ("major_security_developments", "主要安全动态"),
                       ("terrorism_armed_violence", "恐怖主义与武装暴力"),
                       ("public_health_disease_risks", "公共卫生与疾病风险")):
        items = rep.get(sec) or []
        if not items:
            continue
        lines.append("#### %s\n" % title)
        for it in items:
            lines.append("- **%s**\n  - FACT: %s\n  - ASSESS: %s\n  - OUTLOOK: %s\n"
                         % (it.get("headline_zh") or it.get("item_id") or "?",
                            it.get("fact_summary"), it.get("assessment"),
                            it.get("outlook")))
    for r in results:
        if r.get("label") in ("weekly-tcd", "weekly-ssd", "brief") and r.get("status") == "ok":
            lines.append("### %s（真实模型草稿，quality=%s）\n" % (
                r["label"], r.get("quality_status")))
            lines.append("```json\n%s\n```\n" % json.dumps(
                r.get("report") or {}, ensure_ascii=False)[:4000])
    with open(REVIEW, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("REVIEW_PACK_UPDATED %s" % REVIEW)


if __name__ == "__main__":
    sys.exit(main())
