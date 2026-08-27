#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage8C Package2 — Deterministic Facts + AI Analysis 验证入口（§十二/§十三/§十四）。

离线构建 + 一次 Analysis Validation：
  - 输入 ONLY = 3 份 hash 锁定的 Derived Report Input（冻结 hash，不刷新 Canonical）。
  - 每份 → Deterministic Fact Pack → Fact Sections → Final skeleton（离线 schema 校验）。
  - Africa=1 call / TCD=1 call（deepseek-v4-flash, thinking disabled）。
  - SSD fact_count=0 → LOW_DATA_NO_AI=true → 不调用 AI（AI_CALLS=0），
    直接 deterministic low-data report。
  - AI 分析通过 guards → FULL；任一失败（provider/JSON/schema/number/named ref/
    attribution escalation）→ Deterministic Fallback（analysis_status=unavailable）。
  - Machine Gates（§十七）+ Human Review Pack v2（DETERMINISTIC FACTS 与 AI
    ANALYSIS 清晰分区，§十八）。

用法：
  python scripts/report/gen/analysis_runner.py --local-fake   # fake provider 离线验证
  python scripts/report/gen/analysis_runner.py --run          # 真实 2-call（仅用户裁定）
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.ai.safety import manual_trial as mt  # noqa: E402
from scripts.report.gen import analysis_contract as ac  # noqa: E402
from scripts.report.gen import deterministic_assembler as da  # noqa: E402
from scripts.report.gen.fact_pack import build_fact_pack, pack_hash  # noqa: E402

DERIVED = ROOT / "data" / "runtime" / "stage8c_trial2_recovery" / "derived"
OUT = ROOT / "data" / "runtime" / "stage8c_trial2_recovery" / "architecture_run"
RUN_ID = "33066148566"
EXPECTED_HASHES = {
    "africa_daily_report_input.json":
        "f51fe2f548eca356f37f35450360fbe0a15faf6b886c857d2107972557afcc49",
    "tcd_weekly_report_input.json":
        "89d1c42a79a174f775f4c3b80bc1c4264feea7b7629d4b83782c5ec8d429d948",
    "ssd_weekly_report_input.json":
        "1ff941f38e9fb0393dc683b1c82bb4bcc04b5bbc305d80de0d276cd08806f3e8",
}
EXPECTED_AGG = "efad13db07fb3a29015669bba17c49f38d5d5636fa40fc2f77f2f39e503a7caa"
JOBS = [
    ("africa_daily", "africa_daily", "africa_daily_report_input.json",
     "africa_daily_report.schema.json"),
    ("country_weekly", "tcd_weekly", "tcd_weekly_report_input.json",
     "country_weekly_report.schema.json"),
    ("country_weekly", "ssd_weekly", "ssd_weekly_report_input.json",
     "country_weekly_report.schema.json"),
]
LOW_DATA_NO_AI = True


def verify_hashes(derived_dir=None):
    d = Path(derived_dir) if derived_dir else DERIVED
    blob = b""
    for f, want in EXPECTED_HASHES.items():
        data = (d / f).read_bytes().replace(b"\r\n", b"\n")
        blob += data
        sha = hashlib.sha256(data).hexdigest()
        if sha != want:
            raise SystemExit("HASH_MISMATCH %s" % f)
    agg = hashlib.sha256(blob).hexdigest()
    if agg != EXPECTED_AGG:
        raise SystemExit("AGG_HASH_MISMATCH")
    return True


def call_analysis(prov, fact_pack, telemetry, label):
    """单次 Simple Analysis 调用（deepseek-v4-flash, thinking disabled）。"""
    sys_text, user_text = ac.build_analysis_prompt(fact_pack)
    task = {
        "task_id": "ANALYSIS_%s" % label,
        "task_type": "report_analysis",
        "prompt_version": "analysis-v1.0.0",
        "system_text": sys_text,
        "user_text": user_text,
        "usage_purpose": "development_test",
        "max_output_tokens": 1024,
    }
    t = telemetry.setdefault("report_analysis", {"calls": 0, "input_tokens": 0,
                                                 "output_tokens": 0, "total_tokens": 0,
                                                 "finish_reasons": [], "thinking": []})
    res = prov.submit_task(task)
    t["calls"] += 1
    rr = res.get("result") or {}
    t["input_tokens"] += rr.get("input_tokens") or 0
    t["output_tokens"] += rr.get("output_tokens") or 0
    t["total_tokens"] += rr.get("total_tokens") or 0
    t["finish_reasons"].append(rr.get("finish_reason"))
    t["thinking"].append(rr.get("thinking_requested"))
    raw = rr.get("text") or ""
    if res.get("status") != "succeeded":
        return None, {"stage": "provider_failed", "raw": raw,
                      "raw_content_length": len(raw)}
    ok, parsed, jerr = mt._strict_json_parse(raw)
    if not ok:
        return None, {"stage": "invalid_json", "raw": raw,
                      "raw_content_length": len(raw), "json_error": jerr}
    return parsed, {"stage": "parsed", "raw": raw, "raw_content_length": len(raw),
                    "parsed_ai_content": parsed}


def analyze(prov, fact_pack, telemetry, label):
    """执行分析 + guards。返回 (analysis, analysis_result)。"""
    parsed, meta = call_analysis(prov, fact_pack, telemetry, label)
    if parsed is None:
        return None, {"status": "FAIL", "stage": meta["stage"],
                      "schema_ok": False, "boundary_ok": False,
                      "errors": ["analysis %s" % meta["stage"]], "meta": meta}
    schema_ok, serr = _check_schema(parsed)
    if not schema_ok:
        return None, {"status": "FAIL", "stage": "analysis_schema",
                      "schema_ok": False, "boundary_ok": False,
                      "errors": serr, "meta": meta}
    boundary_ok, berr = ac.validate_analysis(parsed, fact_pack)
    if not boundary_ok:
        return None, {"status": "FAIL", "stage": "analysis_boundary",
                      "schema_ok": True, "boundary_ok": False,
                      "errors": berr, "meta": meta}
    return parsed, {"status": "PASS", "stage": "ok",
                    "schema_ok": True, "boundary_ok": True, "errors": [],
                    "meta": meta}


def _check_schema(parsed):
    if not isinstance(parsed, dict):
        return False, ["analysis not object"]
    errs = []
    for k in ("executive_assessment", "trend_analysis", "outlook"):
        if not isinstance(parsed.get(k), str) or not parsed[k].strip():
            errs.append("missing/empty %s" % k)
    wp = parsed.get("watch_points")
    if not isinstance(wp, list) or not all(isinstance(x, str) for x in wp):
        errs.append("watch_points must be string[]")
    return (not errs), errs


def build_pack_v2(records, telemetry, out):
    """Human Review Pack v2：DETERMINISTIC FACTS 与 AI ANALYSIS 分区（§十八）。"""
    md = ["# ASIP Stage 8C Package 2 — Deterministic Facts + AI Analysis",
          "",
          "> REPORT_ARCHITECTURE = DETERMINISTIC_FACTS_PLUS_AI_ANALYSIS",
          "> THIS IS A DERIVED EVIDENCE SNAPSHOT. NOT HISTORICAL RUN#4 REPORT INPUT.",
          "> DETERMINISTIC FACTS（程序事实）与 AI ANALYSIS（DeepSeek 分析）明确分区。",
          ""]
    for key, rec in records.items():
        md += ["## %s" % key.upper(),
               "### SNAPSHOT_METADATA",
               "```json\n%s\n```" % json.dumps({
                   "snapshot_type": "derived_report_evidence_snapshot",
                   "source_run": RUN_ID,
                   "historical_report_input_equivalence": False,
                   "reconstruction_claim": "none",
                   "report_generation_architecture": da.ARCH_VERSION,
                   "report_pipeline_version": da.PIPELINE_VERSION,
               }, ensure_ascii=False, indent=1),
               "### INPUT_SHA256", "```\n%s\n```" % rec["input_sha256"],
               "### FACT_PACK_HASH", "```\n%s\n```" % rec["fact_pack_hash"],
               "### [DETERMINISTIC] FACT_PACK",
               "```json\n%s\n```" % json.dumps(rec["fact_pack"], ensure_ascii=False,
                                               indent=1)[:60000],
               "### [DETERMINISTIC] FACT_SECTIONS",
               "```json\n%s\n```" % json.dumps(rec["fact_sections"], ensure_ascii=False,
                                               indent=1)[:40000],
               "### [DETERMINISTIC] METRICS / SOURCES / VERIFICATION / UNCERTAINTIES",
               "```json\n%s\n```" % json.dumps({
                   "trend_metrics": rec["fact_pack"].get("trend_metrics"),
                   "source_refs": rec["fact_pack"].get("source_refs"),
                   "verification": rec["fact_pack"].get("verification"),
                   "uncertainties": rec["fact_pack"].get("uncertainties"),
                   "country_distribution": rec["fact_pack"].get("country_distribution"),
               }, ensure_ascii=False, indent=1)[:20000]]
        if rec["analysis"] is not None:
            md += ["### [AI] RAW RESPONSE",
                   "```json\n%s\n```" % json.dumps(
                       rec["analysis_result"].get("meta", {}).get("raw", ""),
                       ensure_ascii=False)[:30000],
                   "### [AI] PARSED ANALYSIS",
                   "```json\n%s\n```" % json.dumps(rec["analysis"], ensure_ascii=False,
                                                   indent=1),
                   "### [AI] ANALYSIS GUARDS",
                   "```json\n%s\n```" % json.dumps(
                       {"schema_ok": rec["analysis_result"]["schema_ok"],
                        "boundary_ok": rec["analysis_result"]["boundary_ok"],
                        "errors": rec["analysis_result"]["errors"]},
                       ensure_ascii=False, indent=1)]
        else:
            md += ["### [FALLBACK] AI ANALYSIS",
                   "```json\n%s\n```" % json.dumps({
                       "analysis_status": "unavailable",
                       "stage": (rec.get("analysis_result") or {}).get("stage"),
                       "errors": (rec.get("analysis_result") or {}).get("errors") or [],
                       "fallback_text": da.FALLBACK_ASSESSMENT,
                   }, ensure_ascii=False, indent=1)]
        md += ["### FINAL REPORT",
               "```json\n%s\n```" % json.dumps(rec["report"], ensure_ascii=False,
                                               indent=1)[:60000],
               "### MACHINE GATES",
               "```json\n%s\n```" % json.dumps(rec["gates"], ensure_ascii=False,
                                               indent=1),
               ""]
    md += ["## TELEMETRY",
           "```json\n%s\n```" % json.dumps(telemetry, ensure_ascii=False, indent=1), ""]
    (out / "human_review_pack_v2.md").write_text("\n".join(md), encoding="utf-8")
    return out / "human_review_pack_v2.md"


def run_validation(provider=None, derived_dir=None, out_dir=None,
                   emit=lambda s: print(s)):
    d = Path(derived_dir) if derived_dir else DERIVED
    out = Path(out_dir) if out_dir else OUT
    out.mkdir(parents=True, exist_ok=True)
    verify_hashes(d)
    emit("DERIVED_SNAPSHOT_HASH_VERIFIED = True")
    prov = provider or mt._flash_provider()
    telemetry = {}
    records = {}
    analysis_calls = 0
    for tt, key, fname, schema_name in JOBS:
        ri = json.loads((d / fname).read_text(encoding="utf-8"))
        fp = build_fact_pack(ri)
        fh = pack_hash(fp)
        sections = da.render_fact_sections(fp)
        input_sha = hashlib.sha256(
            json.dumps(ri, ensure_ascii=False).encode("utf-8")).hexdigest()
        rec = {"key": key, "report_type": tt, "input_sha256": input_sha,
               "fact_pack": fp, "fact_pack_hash": fh,
               "fact_sections": sections, "analysis": None,
               "analysis_result": None, "report": None, "gates": None}
        # LOW_DATA_NO_AI（§十四）：fact_count==0 → 不调用 AI
        if fp["fact_count"] == 0 and LOW_DATA_NO_AI:
            rec["analysis_result"] = {"status": "LOW_DATA_NO_AI", "stage": "no_ai",
                                      "schema_ok": False, "boundary_ok": False,
                                      "errors": ["low_data_no_ai"]}
            emit("[%s] LOW_DATA_NO_AI fact_count=0 -> no AI call" % key)
        else:
            analysis, ares = analyze(prov, fp, telemetry, key)
            analysis_calls += 1 if telemetry.get("report_analysis", {}).get(
                "calls", 0) > 0 else 0
            rec["analysis"] = analysis
            rec["analysis_result"] = ares
            emit("[%s] analysis status=%s stage=%s errors=%s" % (
                key, ares.get("status"), ares.get("stage"),
                ares.get("errors") or []))
        # Assembler + Gates
        report = da.assemble_report(tt, fp, rec["analysis"], rec["analysis_result"])
        final_schema = json.loads((ROOT / "schemas" / schema_name)
                                  .read_text(encoding="utf-8"))
        gates = da.machine_gates(report, fp,
                                 None if rec["analysis"] is None
                                 else rec["analysis_result"],
                                 final_schema=final_schema)
        rec["report"] = report
        rec["gates"] = gates
        records[key] = rec
        (out / ("%s_fact_pack.json" % key)).write_text(
            json.dumps(fp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (out / ("%s_report.json" % key)).write_text(
            json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (out / ("%s_gates.json" % key)).write_text(
            json.dumps(gates, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    pack = build_pack_v2(records, telemetry, out)
    total_calls = sum(v.get("calls", 0) for v in telemetry.values())
    emit("ANALYSIS_API_CALLS = %d" % total_calls)
    for key, rec in records.items():
        g = rec["gates"]
        emit("[%s] FACT_GATE=%s FINAL_SCHEMA_GATE=%s issues=%s" % (
            key, g.get("FACT_GATE"), g.get("FINAL_SCHEMA_GATE"), g.get("issues")))
    summary = {
        "architecture": da.ARCH_VERSION,
        "pipeline_version": da.PIPELINE_VERSION,
        "low_data_no_ai": LOW_DATA_NO_AI,
        "analysis_api_calls": total_calls,
        "reports": {k: {"fact_count": rec["fact_pack"]["fact_count"],
                        "analysis_status": (rec["analysis_result"] or {}).get("status"),
                        "analysis_stage": (rec["analysis_result"] or {}).get("stage"),
                        "fact_pack_hash": rec["fact_pack_hash"],
                        "gates": rec["gates"],
                        "report_status": rec["gates"].get("FINAL_SCHEMA_GATE")}
                    for k, rec in records.items()},
        "human_review_pack_v2": str(pack),
    }
    (out / "architecture_run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic Facts + AI Analysis validation")
    ap.add_argument("--local-fake", action="store_true", help="fake provider 离线验证")
    ap.add_argument("--run", action="store_true", help="真实 2-call（仅用户裁定）")
    args = ap.parse_args(argv)
    if args.run:
        s = run_validation()
        print(json.dumps(s, ensure_ascii=False, indent=1))
        return 0
    # local-fake（默认）：注入非 JSON fake → 验证 fallback 路径
    class FakeProvider:
        def __init__(self, text):
            self.text = text
            self.calls = 0
            self.task_types = []
        def submit_task(self, task):
            self.calls += 1
            self.task_types.append(task.get("task_type"))
            return {"status": "succeeded", "result": {
                "returned_model": "deepseek-v4-flash", "text": self.text,
                "input_tokens": 10, "output_tokens": 20, "total_tokens": 30,
                "finish_reason": "stop", "thinking_requested": "disabled",
                "reasoning_tokens": None}}
    s = run_validation(provider=FakeProvider("not-json"))
    print("ANALYSIS_API_CALLS =", s["analysis_api_calls"])
    print(json.dumps({k: v["analysis_status"] for k, v in s["reports"].items()},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
