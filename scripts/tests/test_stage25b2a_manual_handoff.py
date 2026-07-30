#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASIP Stage 2.5B-2A — 单会话 Hy3 手工交接验证验收测试（14 项）。

覆盖（对应规范三/四/五/六/七）：
  D1    prepare 在 queue 放入 2 个合成任务（synthetic=true），country_iso3=TCD/NER
  D2    批次 manifest 的 expected_provider=workbuddy_queue / expected_model=hy3 / task_count=2
  D3    批次目录含 manifest.json / WORKBUDDY_REQUEST.md / results.template.json
  D4    Hy3 形状结果（summary_zh/country_iso3/event_type/key_facts/uncertainties/synthetic）通过契约校验
  D5    真实 ingest 2 个合法结果 → accepted=2, batch_complete=True
  D6    幂等重 ingest → accepted=0（全部 idempotent_success），CLI 退出码=0
  D7    CLI status → 退出码=0
  D8    CLI 空队列 claim → 退出码=0
  D9    CLI 部分 ingest（1 接受 + 1 拒绝）→ 退出码=0
  D10   CLI 全部拒绝（accepted=0, rejected>0）→ 退出码≠0  （规范三：全拒=非0）
  D11   CLI 结构性错误（结果文件不存在）→ 退出码≠0
  D12   CLI 参数错误（claim --batch-size 0）→ 退出码≠0
  D13   非对象结果条目（字符串/数字）被优雅拒绝，不崩溃，计入 rejected
  D14   cleanup 删除整个运行时目录

注意：本测试全部使用独立临时 ai_root，绝不触碰生产 data/ai。
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ai"))  # 用于 import manual_handoff_demo

from ai.contracts import validate_ai_result  # noqa: E402
from ai.workbuddy_worker import (  # noqa: E402
    claim_batch, ingest_results,
)
from manual_handoff_demo import prepare, cleanup  # noqa: E402

PY = sys.executable
WORKER = os.path.join(SCRIPTS, "ai", "workbuddy_worker.py")


def _mk_root():
    return tempfile.mkdtemp(prefix="s25b2a_")


def _read_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_result_file(ai_root, batch_id, worker_id, results,
                       fname="results.submit.json"):
    payload = {"batch_id": batch_id, "worker_id": worker_id,
               "completed_at": "2026-07-31T05:00:05+00:00",
               "results": results}
    p = os.path.join(ai_root, "batches", batch_id, fname)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return p


def _mk_hy3_result(task_id, country_iso3, lang, event_type, summary_zh,
                   key_facts, uncertainties, provider="workbuddy_queue",
                   model="hy3"):
    return {
        "task_id": task_id,
        "schema_version": "1.0",
        "status": "success",
        "provider": provider,
        "model": model,
        "started_at": "2026-07-31T05:00:00+00:00",
        "completed_at": "2026-07-31T05:00:05+00:00",
        "result": {
            "summary_zh": summary_zh,
            "country_iso3": country_iso3,
            "lang": lang,
            "event_type": event_type,
            "key_facts": key_facts,
            "uncertainties": uncertainties,
            "synthetic": True,
        },
        "error": None,
        "usage": {"input_tokens": 0, "output_tokens": 0,
                  "estimated_cost_usd": 0},
    }


def _run_cli(ai_root, *args):
    cmd = [PY, WORKER, "--ai-root", ai_root] + list(args)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


def main():
    total, fails = 0, 0
    roots = []

    def check(name, ok, detail=""):
        nonlocal total, fails
        total += 1
        status = "PASS" if ok else "FAIL"
        print("  [%s] %s" % (status, name))
        if not ok:
            fails += 1
            print("       %s" % detail)

    # ═══ D1: prepare 2 个合成任务 ═══
    print("\n=== D1: prepare two synthetic tasks ===")
    r1 = _mk_root(); roots.append(r1)
    info = prepare(r1)
    iso3 = {t["country_iso3"] for t in info["tasks"]}
    ok1 = (info["batch_id"] is not None
           and len(info["tasks"]) == 2
           and iso3 == {"TCD", "NER"}
           and all(t["task_id"].startswith("AIT_") for t in info["tasks"]))
    check("D1", ok1,
          "batch_id=%s tasks=%d iso3=%s" % (info["batch_id"], len(info["tasks"]), iso3))

    # ═══ D2: manifest 字段 ═══
    print("\n=== D2: manifest expected_provider/model/count ===")
    manifest = _read_json(info["manifest_path"])
    ok2 = (manifest.get("expected_provider") == "workbuddy_queue"
           and manifest.get("expected_model") == "hy3"
           and manifest.get("task_count") == 2)
    check("D2", ok2,
          "provider=%s model=%s count=%s" % (
              manifest.get("expected_provider"),
              manifest.get("expected_model"),
              manifest.get("task_count")))

    # ═══ D3: 批次文件齐全 ═══
    print("\n=== D3: batch files exist ===")
    ok3 = (os.path.exists(info["manifest_path"])
           and os.path.exists(info["request_md_path"])
           and os.path.exists(info["template_path"]))
    check("D3", ok3, "manifest=%s request=%s template=%s" % (
        os.path.exists(info["manifest_path"]),
        os.path.exists(info["request_md_path"]),
        os.path.exists(info["template_path"])))

    # ═══ D4: Hy3 形状结果通过契约校验 ═══
    print("\n=== D4: Hy3 result shape valid ===")
    tid0 = info["tasks"][0]["task_id"]
    hy3 = _mk_hy3_result(
        tid0, "TCD", "fr", "social_security_forum",
        "乍得恩贾梅纳举行区域性社会保障论坛，多国代表讨论跨境养老金互认。",
        ["论坛于2026年虚构日期举行", "议题含跨境养老金互认"],
        ["具体参会名单未公开", "金额数据缺失"])
    errs = validate_ai_result(hy3)
    check("D4", errs == [], "errors=%s" % errs)

    # ═══ D5: 真实 ingest 2 个合法结果 ═══
    print("\n=== D5: ingest accepts two valid results ===")
    results = [
        _mk_hy3_result(
            info["tasks"][0]["task_id"], "TCD", "fr", "social_security_forum",
            "乍得恩贾梅纳举行区域性社会保障论坛，多国代表讨论跨境养老金互认。",
            ["论坛于2026年虚构日期举行", "议题含跨境养老金互认"],
            ["具体参会名单未公开", "金额数据缺失"]),
        _mk_hy3_result(
            info["tasks"][1]["task_id"], "NER", "en", "pension_workshop",
            "尼日尔尼亚美举办养老金体系能力建设 workshop，聚焦农村覆盖。",
            ["workshop 为虚构演练", "聚焦农村覆盖扩展"],
            ["实施时间表未定", "预算来源未说明"]),
    ]
    rf = _write_result_file(r1, info["batch_id"], info["worker_id"], results)
    rep5 = ingest_results(r1, info["batch_id"], rf)
    ok5 = (rep5.get("accepted") == 2
           and rep5.get("rejected") == 0
           and rep5.get("batch_complete") is True)
    check("D5", ok5, "accepted=%s rejected=%s complete=%s" % (
        rep5.get("accepted"), rep5.get("rejected"), rep5.get("batch_complete")))

    # ═══ D6: 幂等重 ingest ═══
    print("\n=== D6: idempotent re-ingest ===")
    rep6 = ingest_results(r1, info["batch_id"], rf)
    outcomes = [e.get("outcome", "") for e in rep6.get("tasks", [])]
    all_idem = all(o == "idempotent_success" for o in outcomes)
    # 同时验证 CLI 退出码=0
    rc6, _, _ = _run_cli(r1, "ingest", "--batch-id", info["batch_id"],
                         "--result-file", rf)
    ok6 = (rep6.get("accepted") == 0 and all_idem
           and rep6.get("error") in (None, "")
           and rc6 == 0)
    check("D6", ok6, "accepted=%s outcomes=%s cli_rc=%s" % (
        rep6.get("accepted"), outcomes, rc6))

    # ═══ D7: CLI status 退出码=0 ═══
    print("\n=== D7: CLI status exit 0 ===")
    r7 = _mk_root(); roots.append(r7)
    rc7, _, _ = _run_cli(r7, "status")
    check("D7", rc7 == 0, "rc=%s" % rc7)

    # ═══ D8: CLI 空队列 claim 退出码=0 ═══
    print("\n=== D8: CLI empty claim exit 0 ===")
    r8 = _mk_root(); roots.append(r8)
    rc8, out8, _ = _run_cli(r8, "claim", "--batch-size", "2")
    check("D8", rc8 == 0, "rc=%s" % rc8)

    # ═══ D9: CLI 部分 ingest 退出码=0 ═══
    print("\n=== D9: CLI partial ingest exit 0 ===")
    r9 = _mk_root(); roots.append(r9)
    inf9 = prepare(r9)
    res9 = [
        _mk_hy3_result(inf9["tasks"][0]["task_id"], "TCD", "fr",
                       "social_security_forum", "x", ["a"], ["b"]),
        # 第二个结果 provider 不匹配 → 被拒绝
        _mk_hy3_result(inf9["tasks"][1]["task_id"], "NER", "en",
                       "pension_workshop", "y", ["c"], ["d"],
                       **{"provider": "openai_api"}),
    ]
    rf9 = _write_result_file(r9, inf9["batch_id"], inf9["worker_id"], res9)
    rc9, _, _ = _run_cli(r9, "ingest", "--batch-id", inf9["batch_id"],
                         "--result-file", rf9)
    check("D9", rc9 == 0, "rc=%s" % rc9)

    # ═══ D10: CLI 全部拒绝 退出码≠0 ═══
    print("\n=== D10: CLI all-rejected exit nonzero ===")
    r10 = _mk_root(); roots.append(r10)
    inf10 = prepare(r10)
    res10 = [
        _mk_hy3_result(inf10["tasks"][0]["task_id"], "TCD", "fr",
                       "social_security_forum", "x", ["a"], ["b"],
                       **{"provider": "openai_api"}),
        _mk_hy3_result(inf10["tasks"][1]["task_id"], "NER", "en",
                       "pension_workshop", "y", ["c"], ["d"],
                       **{"provider": "openai_api"}),
    ]
    rf10 = _write_result_file(r10, inf10["batch_id"], inf10["worker_id"], res10)
    rc10, _, _ = _run_cli(r10, "ingest", "--batch-id", inf10["batch_id"],
                          "--result-file", rf10)
    check("D10", rc10 != 0, "rc=%s (expected nonzero)" % rc10)

    # ═══ D11: CLI 结构性错误 退出码≠0 ═══
    print("\n=== D11: CLI structural error exit nonzero ===")
    r11 = _mk_root(); roots.append(r11)
    inf11 = prepare(r11)
    rc11, _, _ = _run_cli(r11, "ingest", "--batch-id", inf11["batch_id"],
                         "--result-file", os.path.join(r11, "nope.json"))
    check("D11", rc11 != 0, "rc=%s (expected nonzero)" % rc11)

    # ═══ D12: CLI 参数错误 退出码≠0 ═══
    print("\n=== D12: CLI param error exit nonzero ===")
    r12 = _mk_root(); roots.append(r12)
    rc12, _, _ = _run_cli(r12, "claim", "--batch-size", "0")
    check("D12", rc12 != 0, "rc=%s (expected nonzero)" % rc12)

    # ═══ D13: 非对象结果优雅处理 ═══
    print("\n=== D13: non-object result handled ===")
    r13 = _mk_root(); roots.append(r13)
    inf13 = prepare(r13)
    res13 = [
        _mk_hy3_result(inf13["tasks"][0]["task_id"], "TCD", "fr",
                       "social_security_forum", "x", ["a"], ["b"]),
        "this-is-not-an-object",   # 非对象条目
        12345,                     # 数字条目
    ]
    rf13 = _write_result_file(r13, inf13["batch_id"], inf13["worker_id"], res13)
    crashed = False
    try:
        rep13 = ingest_results(r13, inf13["batch_id"], rf13)
    except Exception as e:
        rep13 = None
        crashed = True
    outcomes = [e.get("outcome", "") for e in (rep13 or {}).get("tasks", [])]
    rejected_types = sum(1 for o in outcomes if o == "rejected_invalid_result_type")
    accepted13 = (rep13 or {}).get("accepted", 0)
    ok13 = (not crashed
            and rejected_types == 2
            and accepted13 == 1)
    check("D13", ok13, "crashed=%s accepted=%s rejected_types=%s outcomes=%s" % (
        crashed, accepted13, rejected_types, outcomes))

    # ═══ D14: cleanup 删除运行时目录 ═══
    print("\n=== D14: cleanup removes runtime dir ===")
    r14 = _mk_root(); roots.append(r14)
    prepare(r14)
    ok14 = cleanup(r14) and not os.path.isdir(r14)
    check("D14", ok14, "removed=%s" % (not os.path.isdir(r14)))

    # 清理其余临时目录
    for r in roots:
        if os.path.isdir(r):
            shutil.rmtree(r, ignore_errors=True)

    # ── 汇总 ──
    print("\n" + "=" * 64)
    print("RESULT: PASS=%d FAIL=%d" % (total - fails, fails))
    print("=" * 64)
    if fails:
        sys.exit(1)
    print("ALL STAGE 2.5B-2A MANUAL HANDOFF TESTS PASSED")


if __name__ == "__main__":
    main()
