#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage8C Package2 — Report Evidence Recovery 执行模式（report-stage-only）。

只允许在 Derived Frozen Report Evidence Snapshot（§十三）全部通过后使用：

  - 输入 ONLY = 三份 hash 锁定的 derived report input
    （data/runtime/stage8c_trial2_recovery/derived/*_report_input.json）。
  - 不得读取最新 Canonical；不得执行 Social/Disease enrichment；
    不得重新 Safety 修正。
  - 只允许 3 次报告调用：Africa Daily=1 / TCD Weekly=1 / SSD Weekly=1。
  - 每次调用走冻结 generate_report()：Provider response → persist raw →
    JSON parse → AI content schema → assembler → final schema → machine gates；
    任何前置失败 raw 仍必须持久化（§十二）。

用法：
  python scripts/ai/safety/report_evidence_recovery.py --check
    # 离线 readiness 检查（不调用 AI；验证 hash/schema/counts/EXPECTED_API_CALLS）
  python scripts/ai/safety/report_evidence_recovery.py --run
    # 执行 3-call Evidence Run（仅由用户显式裁定后使用；本任务 AI_CALLS=0 不执行）

--run 硬约束：
  - 运行前 check_ready() 必须 True；
  - provider 调用计数必须恰为 3；任务类型仅 {africa_daily, country_weekly}；
  - telemetry 与 machine gate 结果写盘；任何失败 fail-closed 报告。
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.ai.safety import derive_frozen_report_evidence as dfe  # noqa: E402
from scripts.ai.safety import manual_trial as mt  # noqa: E402
from scripts.ai.schema_validation import validate_against_schema  # noqa: E402

DERIVED = dfe.OUT
MANIFEST = dfe.MANIFEST_PATH
EXPECTED_API_CALLS = 3
JOBS = [
    ("africa_daily", "africa_daily", "africa_daily_report_input.json",
     "config/prompts/africa_daily_report_v1.md", "africa_daily"),
    ("country_weekly", "tcd_weekly", "tcd_weekly_report_input.json",
     "config/prompts/country_weekly_report_v1.md", "tcd_weekly"),
    ("country_weekly", "ssd_weekly", "ssd_weekly_report_input.json",
     "config/prompts/country_weekly_report_v1.md", "ssd_weekly"),
]
SCHEMAS = {
    "africa_daily": "africa_daily_report_input.schema.json",
    "country_weekly": "country_weekly_report_input.schema.json",
}


def load_inputs(derived_dir=None):
    d = Path(derived_dir) if derived_dir else DERIVED
    out = {}
    for tt, _label, fname, _pf, key in JOBS:
        out[key] = json.loads((d / fname).read_text(encoding="utf-8"))
    return out


def check_ready(derived_dir=None, manifest_path=None):
    """离线 readiness 检查（AI_CALLS=0）。"""
    d = Path(derived_dir) if derived_dir else DERIVED
    mpath = Path(manifest_path) if manifest_path else MANIFEST
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    gates = {"manifest_exists": True, "hash_lock": True, "schema": True,
             "counts_closed": True, "expected_calls": True}
    issues = []

    # 1) 文件存在 + hash 锁定
    payload_bytes = {}
    for tt, _label, fname, _pf, key in JOBS:
        p = d / fname
        if not p.exists():
            gates["hash_lock"] = False
            issues.append("%s missing" % fname)
            continue
        data = p.read_bytes().replace(b"\r\n", b"\n")  # LF 归一化（冻结 hash 基于 LF）
        payload_bytes[key] = data
        sha = dfe.sha256_bytes(data)
        want = manifest["hashes"].get(
            {"africa_daily": "africa_daily_report_input_sha256",
             "tcd_weekly": "tcd_weekly_report_input_sha256",
             "ssd_weekly": "ssd_weekly_report_input_sha256"}[key])
        if sha != want:
            gates["hash_lock"] = False
            issues.append("%s hash mismatch: %s != %s" % (fname, sha[:16], want[:16]))
    if len(payload_bytes) != 3:
        gates["hash_lock"] = False

    # 2) 官方 input schema（resolve_refs=True）
    for key, obj in load_inputs(derived_dir).items():
        tt = "africa_daily" if key == "africa_daily" else "country_weekly"
        s = json.loads((ROOT / "schemas" / SCHEMAS[tt]).read_text(encoding="utf-8"))
        errs = validate_against_schema(obj, s, resolve_refs=True)
        if errs:
            gates["schema"] = False
            issues.append("%s schema: %s" % (key, errs[:2]))

    # 3) counts closure
    counts = manifest.get("counts") or {}
    gates["counts_closed"] = bool(counts.get("closure_ok"))

    # 4) 预期调用数
    gates["expected_calls"] = EXPECTED_API_CALLS == 3
    if not gates["expected_calls"]:
        issues.append("expected calls != 3")

    ready = all(gates.values())
    return {"ready": ready, "gates": gates, "issues": issues,
            "expected_api_calls": EXPECTED_API_CALLS,
            "aggregate_snapshot_sha256": manifest.get("hashes", {}).get(
                "aggregate_snapshot_sha256"),
            "reconstructable": manifest.get("report_input_snapshot_reconstructable")}


def run_evidence(provider=None, out_dir=None):
    """3-call Report Evidence Run（仅用户显式裁定后执行）。"""
    out = Path(out_dir) if out_dir else (ROOT / "data" / "runtime"
                                         / "stage8c_trial2_recovery" / "evidence_run")
    pre = check_ready()
    if not pre["ready"]:
        return {"status": "blocked_not_ready", "precheck": pre,
                "ai_calls": 0}
    from scripts.ai.safety.manual_trial import _flash_provider, generate_report
    prov = provider or _flash_provider()
    telemetry = {}
    results = {}
    out.mkdir(parents=True, exist_ok=True)
    for tt, label, fname, prompt_rel, key in JOBS:
        report_input = json.loads((DERIVED / fname).read_text(encoding="utf-8"))
        r = generate_report(prov, tt, report_input,
                            ROOT / prompt_rel, label, telemetry,
                            raw_path=out / ("%s_raw_response.json" % key))
        r["report_input"] = report_input
        results[key] = r
    total = sum(v.get("calls", 0) for v in telemetry.values())
    task_types = set()
    for v in telemetry:
        task_types.add(v)
    (out / "evidence_run_summary.json").write_text(
        json.dumps({"jobs": list(results.keys()), "ai_calls": total,
                    "task_types": sorted(task_types),
                    "expected_api_calls": EXPECTED_API_CALLS,
                    "machine_gates": {k: v.get("machine_gate_status")
                                      for k, v in results.items()},
                    "statuses": {k: v.get("status") for k, v in results.items()}},
                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"status": "completed", "ai_calls": total,
            "task_types": sorted(task_types),
            "expected_api_calls": EXPECTED_API_CALLS,
            "results": {k: v.get("status") for k, v in results.items()},
            "machine_gates": {k: v.get("machine_gate_status")
                              for k, v in results.items()}}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Report Evidence Recovery mode")
    ap.add_argument("--check", action="store_true", help="离线 readiness 检查（不调 AI）")
    ap.add_argument("--run", action="store_true", help="执行 3-call Evidence Run")
    args = ap.parse_args(argv)
    if args.run:
        res = run_evidence()
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0 if res.get("status") == "completed" and res["ai_calls"] == 3 else 1
    pre = check_ready()
    print("REPORT_EVIDENCE_RECOVERY_READY =", pre["ready"])
    print("EXPECTED_API_CALLS =", pre["expected_api_calls"])
    print("GATES =", json.dumps(pre["gates"], ensure_ascii=False))
    for i in pre["issues"]:
        print("ISSUE:", i)
    print("AGGREGATE_SNAPSHOT_SHA256 =", pre.get("aggregate_snapshot_sha256"))
    print("REPORT_INPUT_SNAPSHOT_RECONSTRUCTABLE =", pre.get("reconstructable"))
    return 0 if pre["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
