#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 8C Package3 — Production Report runner（§八/§九/§十/§十七）。

三份正式报告状态：FULL / FALLBACK / LOW_DATA（Fact Gate PASS 为前提）。
  - Africa Daily：每天最多 1 份（生产日期 20:00 北京，由 workflow 调度）。
  - Country Weekly：每 enabled country 每周最多 1 份。
  - Major Brief：condition-triggered；V1 不自动公开（MAJOR_BRIEF_AUTO_PUBLICATION=false）。

输入：
  --source derived  : 冻结 Derived Report Input（shadow 验证，0 AI 可选）
  --source canonical: 当前 canonical eligible facts（生产；经 manual_trial.build_inputs）

AI Analysis：deepseek-v4-flash（thinking disabled）；PASS→FULL；任一失败→FALLBACK；
fact_count=0 → LOW_DATA_NO_AI（不调用 AI）。
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.safety import manual_trial as mt  # noqa: E402
from scripts.report.gen import analysis_contract as ac  # noqa: E402
from scripts.report.gen import deterministic_assembler as da  # noqa: E402
from scripts.report.gen.fact_pack import build_fact_pack, pack_hash  # noqa: E402
from scripts.report.gen import analysis_runner as ar  # noqa: E402
from scripts.ops import production_state as ps  # noqa: E402

DERIVED = ROOT / "data" / "runtime" / "stage8c_trial2_recovery" / "derived"
# cold start（§二十八）：data/runtime 为 gitignored；缺失时用 git tracked 的
# evidence/ 副本（字节一致，冻结 hash 不变）
DERIVED_EVIDENCE = ROOT / "evidence" / "stage8c_trial2_recovery" / "derived"
REPORTS_OUT = ps.OPS_DIR / "reports"
SCHEMAS = {
    "africa_daily": "africa_daily_report.schema.json",
    "country_weekly": "country_weekly_report.schema.json",
}
LOW_DATA_NO_AI = True


def _derived_dir():
    if (DERIVED / "africa_daily_report_input.json").exists():
        return DERIVED
    return DERIVED_EVIDENCE


def load_input(mode, source, country=None):
    """加载 report input。derived→冻结 snapshot；canonical→当前 eligible facts。"""
    if source == "derived":
        fname = {"daily": "africa_daily_report_input.json",
                 "tcd_weekly": "tcd_weekly_report_input.json",
                 "ssd_weekly": "ssd_weekly_report_input.json"}[mode]
        return json.loads((_derived_dir() / fname).read_text(encoding="utf-8"))
    # canonical：复用冻结的 trial input builder（committed canonical → report input）
    inputs = mt.build_inputs()
    if mode == "daily":
        return inputs["daily_input"]
    return {"tcd_weekly": inputs["weekly_tcd_input"],
            "ssd_weekly": inputs["weekly_ssd_input"]}[mode]


def generate_report(mode, input_obj, provider, telemetry, emit):
    """生成一份报告：Fact Pack → optional AI Analysis → Assembler → Gates。"""
    fp = build_fact_pack(input_obj)
    fh = pack_hash(fp)
    analysis, ares = None, None
    if fp["fact_count"] == 0 and LOW_DATA_NO_AI:
        ares = {"status": "LOW_DATA_NO_AI", "stage": "no_ai",
                "schema_ok": False, "boundary_ok": False, "errors": ["low_data_no_ai"]}
        emit("[%s] LOW_DATA_NO_AI fact_count=0" % mode)
    elif provider is None:
        ares = {"status": "FAIL", "stage": "no_provider",
                "schema_ok": False, "boundary_ok": False, "errors": ["ai_disabled"]}
        emit("[%s] AI_DISABLED -> fallback" % mode)
    else:
        analysis, ares = ar.analyze(provider, fp, telemetry, mode)
        emit("[%s] analysis status=%s stage=%s" % (mode, ares.get("status"),
                                                   ares.get("stage")))
    rtype = "africa_daily" if mode == "daily" else "country_weekly"
    report = da.assemble_report(rtype, fp, analysis, ares)
    schema = json.loads((ROOT / "schemas" / SCHEMAS[rtype]).read_text(encoding="utf-8"))
    gates = da.machine_gates(report, fp,
                             None if analysis is None else ares,
                             final_schema=schema)
    return {"mode": mode, "fact_pack": fp, "fact_pack_hash": fh,
            "analysis": analysis, "analysis_result": ares,
            "report": report, "gates": gates}


def classify(report_res):
    """FULL / FALLBACK / LOW_DATA / HOLD（§ 正式三种状态 + HOLD）。

    HOLD 条件（fail-closed）：FACT_GATE 非 PASS，或 FINAL_SCHEMA_GATE 非 PASS
    （schema 不合规产物不得作为正常报告进入 Public）。
    """
    g = report_res["gates"]
    if g.get("FACT_GATE") != "PASS":
        return "HOLD"
    if g.get("FINAL_SCHEMA_GATE") != "PASS":
        return "HOLD"
    ares = report_res["analysis_result"]
    if ares and ares.get("status") == "LOW_DATA_NO_AI":
        return "LOW_DATA"
    if report_res["analysis"] is not None and ares.get("status") == "PASS":
        return "FULL"
    return "FALLBACK"


def run(mode, source, provider=None, state=None, ops_run=None, out_dir=None,
        emit=lambda s: print(s), allow_ai=True):
    state = state or ps.load_state()
    out = Path(out_dir) if out_dir else REPORTS_OUT
    out.mkdir(parents=True, exist_ok=True)
    prov = provider if provider is not None else (mt._flash_provider() if allow_ai
                                                  else None)
    telemetry = {}
    results = {}
    modes = [mode] if mode != "all" else ["daily", "tcd_weekly", "ssd_weekly"]
    for m in modes:
        ri = load_input(m, source)
        rr = generate_report(m, ri, prov, telemetry, emit)
        results[m] = rr
        cls = classify(rr)
        if ops_run is not None:
            key = "reports_%s" % {"FULL": "full", "FALLBACK": "fallback",
                                  "LOW_DATA": "low_data", "HOLD": "hold"}[cls]
            ops_run[key] = ops_run.get(key, 0) + 1
        (out / ("%s_%s.json" % (m, cls.lower()))).write_text(
            json.dumps(rr["report"], ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8")
        (out / ("%s_fact_pack.json" % m)).write_text(
            json.dumps(rr["fact_pack"], ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8")
        (out / ("%s_gates.json" % m)).write_text(
            json.dumps(rr["gates"], ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8")
        emit("[%s] status=%s gates_fact=%s final=%s" % (
            m, cls, rr["gates"].get("FACT_GATE"), rr["gates"].get("FINAL_SCHEMA_GATE")))
        # state 幂等记录
        ps.mark_processed(state, "reports", "%s:%s:%s" % (
            m, source, ri.get("report_date") or ri.get("week_end") or "unknown"),
            {"classification": cls, "fact_pack_hash": rr["fact_pack_hash"]})
    # AI usage
    for k, v in telemetry.items():
        if k == "report_analysis":
            ps.add_ai_usage(state, "daily_analysis" if mode == "daily"
                            else "weekly_analysis", v)
    summary = {"mode": mode, "source": source,
               "results": {m: {"classification": classify(rr),
                               "fact_count": rr["fact_pack"]["fact_count"],
                               "fact_pack_hash": rr["fact_pack_hash"]}
                           for m, rr in results.items()},
               "analysis_api_calls": sum(v.get("calls", 0)
                                         for v in telemetry.values())}
    (out / "reports_run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description="Production report runner")
    ap.add_argument("--mode", choices=["daily", "tcd_weekly", "ssd_weekly", "all"],
                    default="all")
    ap.add_argument("--source", choices=["derived", "canonical"], default="derived")
    ap.add_argument("--no-ai", action="store_true", help="不调用 AI（全部走 FALLBACK/LOW_DATA）")
    args = ap.parse_args(argv)
    state = ps.load_state()
    s = run(args.mode, args.source, state=state, allow_ai=not args.no_ai)
    ps.save_state(state)
    print(json.dumps(s, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
