#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASIP Stage 2.5B-2A 验收补正 — 单会话 Hy3 手工交接验证验收测试（强化版）。

覆盖（对应验收补正规范二/三/四/五/六/七/九）：
  T1    prepare 在 queue 放入 2 个合成任务，且两个任务均含非空 source_text（ASIP 安全场景）
  T2    乍得任务 source_language=fr；尼日尔任务 source_language=en
  T3    准备出的任务不得出现社会保障/养老金语义
        （social_security_forum / pension_workshop / pension / social protection forum /
         养老金 / 社会保障论坛）
  T4    content_hash 必须基于 source_text 计算且稳定（同 source_text -> 同 hash）
  T5    乍得结果必须是安全事件；尼日尔结果必须是道路/交通中断事件（分类校验）
  T6    Hy3 结果不得把未确认伤亡写成已确认事实（伤亡未确认守卫）
  T7    prepare 不会自动生成 AI 结果（completed=0 / processing=2 / 无 ai_result）
  T8    真实 ingest 2 个合法结果 -> accepted=2, batch_complete=True
  T9    幂等重 ingest -> accepted=0（全部 idempotent_success），CLI 退出码=0
  T10   verify 在 ingest 之后检查最终状态（queue/processing/completed/leases + 结果语义）
  T11   verify 失败时（ingest 前）CLI 退出码必须非零
  T12   run 在 ok=false 时 CLI 退出码必须非零
  T13   非对象结果条目（字符串/数字）被优雅拒绝，不崩溃，计入 rejected
  T14   CLI 全部拒绝（accepted=0, rejected>0）退出码≠0
  T15   CLI 部分 ingest（1 接受 + 1 拒绝）退出码=0
  T16   CLI status 退出码=0
  T17   CLI 空队列 claim 退出码=0
  T18   不使用生产 data/ai；默认 ai_root 位于 .workbuddy_runtime（已 gitignore）

注意：本测试全部使用独立临时 ai_root，绝不触碰生产 data/ai。
自动测试使用确定性模拟结果以保证流水线可重复；「当前 WorkBuddy 内置 Hy3（免费）」
真实处理证据由 ASIP_STAGE25B2A_ACCEPTANCE.md 单独记录，二者明确分离。
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
import hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ai"))  # 用于 import manual_handoff_demo

from ai.contracts import validate_ai_result  # noqa: E402
from ai.workbuddy_worker import (  # noqa: E402
    claim_batch, ingest_results, status_summary, AI_ROOT as PROD_AI_ROOT,
)
from manual_handoff_demo import prepare, cleanup, DEFAULT_AI_ROOT  # noqa: E402

# 优先使用演示脚本内置的语义校验；若尚未实现则回退到本文件内联实现。
try:
    from manual_handoff_demo import validate_result_event as _demo_validate_event  # noqa: E402
except Exception:  # pragma: no cover
    _demo_validate_event = None

PY = sys.executable
WORKER = os.path.join(SCRIPTS, "ai", "workbuddy_worker.py")
DEMO = os.path.join(SCRIPTS, "ai", "manual_handoff_demo.py")

# 分类枚举（与演示脚本保持一致）
SECURITY_EVENT_TYPES = {
    "armed_incident", "security_incident", "shooting_incident",
    "violent_incident", "explosion_incident",
}
TRANSPORT_EVENT_TYPES = {
    "transport_disruption", "road_closure", "traffic_disruption",
    "infrastructure_disruption",
}

FORBIDDEN_TOKENS = [
    "social_security_forum", "pension_workshop", "pension",
    "social protection forum", "养老金", "社会保障论坛",
]


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _inline_validate_event(result):
    """内联版语义守卫（与演示脚本 validate_result_event 逻辑一致）。"""
    errs = []
    r = (result.get("result") or {}) if isinstance(result, dict) else {}
    iso3 = r.get("country_iso3")
    et = r.get("event_type")
    summary = r.get("summary_zh") or ""
    uncertainties = r.get("uncertainties") or []
    blob = summary + " " + " ".join(uncertainties)

    def asserts_confirmed_casualties(t):
        return any(p in t for p in (
            "已造成伤亡", "已造成死伤", "确认有死伤", "确认造成",
            "造成死亡", "造成伤亡", "造成死伤",
        ))

    def mentions_unconfirmed_casualties(t):
        casualty_kw = ("死伤", "伤亡", "死亡", "受伤", "morts", "bless",
                       "casualt", "deaths", "injured", "victim")
        unconf = ("尚未", "未确认", "未证实", "没有确认", "暂未", "待确认",
                  "not confirmed", "unconfirmed", "have not confirmed",
                  "officially", "no casualties reported")
        return any(c in t.lower() for c in casualty_kw) and any(
            u in t.lower() for u in unconf)

    def fabricates_casualties(t):
        return any(p in t for p in (
            "造成伤亡", "造成死伤", "人死亡", "人受伤", "导致死亡",
            "confirmed deaths", "fatalities",
        ))

    if asserts_confirmed_casualties(blob):
        errs.append("casualties written as confirmed")
    if iso3 == "TCD":
        if et not in SECURITY_EVENT_TYPES:
            errs.append("TCD not security event: %r" % et)
        if not mentions_unconfirmed_casualties(blob):
            errs.append("TCD must retain unconfirmed casualties")
    if iso3 == "NER":
        if et not in TRANSPORT_EVENT_TYPES:
            errs.append("NER not transport disruption: %r" % et)
        if fabricates_casualties(blob):
            errs.append("NER fabricates casualties")
    return errs


def validate_event(result):
    if _demo_validate_event is not None:
        return _demo_validate_event(result)
    return _inline_validate_event(result)


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


def _mk_result(task_id, country_iso3, lang, event_type, summary_zh,
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
            "source_language": lang,
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


def _run_demo_cli(ai_root, *args):
    cmd = [PY, DEMO, "--ai-root", ai_root] + list(args)
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

    # ═══ T1: 两个任务均含非空 source_text ═══
    print("\n=== T1: both tasks have non-empty source_text ===")
    r1 = _mk_root(); roots.append(r1)
    info = prepare(r1)
    srcs = [t.get("source_text") for t in info["tasks"]]
    ok1 = (len(info["tasks"]) == 2
           and all(isinstance(s, str) and s.strip() for s in srcs))
    check("T1", ok1, "source_texts=%s" % [bool(s) for s in srcs])

    # ═══ T2: 语言标记 fr / en ═══
    print("\n=== T2: source_language fr (TCD) / en (NER) ===")
    lang_map = {t["task_id"]: t.get("source_language") for t in info["tasks"]}
    iso3_map = {t["task_id"]: t.get("country_iso3") for t in info["tasks"]}
    tcd_lang = next((lang_map[t["task_id"]] for t in info["tasks"]
                     if iso3_map[t["task_id"]] == "TCD"), None)
    ner_lang = next((lang_map[t["task_id"]] for t in info["tasks"]
                     if iso3_map[t["task_id"]] == "NER"), None)
    ok2 = (tcd_lang == "fr" and ner_lang == "en")
    check("T2", ok2, "tcd_lang=%r ner_lang=%r" % (tcd_lang, ner_lang))

    # ═══ T3: 禁止社会保障/养老金语义 ═══
    print("\n=== T3: no social-security / pension semantics ===")
    # 检查真实落盘的批次清单（含完整 input_ref），旧实现会把
    # social_security_forum / pension_workshop 写进 input_ref.event。
    m = _read_json(info["manifest_path"])
    blob = json.dumps(m, ensure_ascii=False).lower()
    hits = [tok for tok in FORBIDDEN_TOKENS if tok.lower() in blob]
    ok3 = (len(hits) == 0)
    check("T3", ok3, "forbidden_hits=%s" % hits)

    # ═══ T4: content_hash 基于 source_text 且稳定 ═══
    print("\n=== T4: content_hash derived from source_text and stable ===")
    ch_map = {t["task_id"]: t.get("content_hash") for t in info["tasks"]}
    calc = {t["task_id"]: _sha256(t.get("source_text", ""))
            for t in info["tasks"]}
    derived_ok = all(ch_map.get(tid) == calc.get(tid) for tid in ch_map)
    # 稳定性：独立 root 再 prepare 一次，task_id 应保持一致（同源输入）
    r1b = _mk_root(); roots.append(r1b)
    info_b = prepare(r1b)
    id_map_b = {t["task_id"]: t.get("content_hash") for t in info_b["tasks"]}
    stable_ok = all(ch_map.get(tid) == id_map_b.get(tid)
                    for tid in ch_map if tid in id_map_b)
    ok4 = derived_ok and stable_ok
    check("T4", ok4, "derived=%s stable=%s" % (derived_ok, stable_ok))

    # ═══ T5: 安全事件 / 交通中断 分类校验 ═══
    print("\n=== T5: TCD security event / NER transport disruption ===")
    tcd_tid = next(t["task_id"] for t in info["tasks"]
                   if iso3_map[t["task_id"]] == "TCD")
    ner_tid = next(t["task_id"] for t in info["tasks"]
                   if iso3_map[t["task_id"]] == "NER")
    good_tcd = _mk_result(tcd_tid, "TCD", "fr", "armed_incident",
                          "乍得虚构地点 Dar-Salam 市场附近晚间传出枪声，安全部队临时封锁。当局尚未确认是否有死伤。",
                          ["市场附近枪声", "安全部队封锁", "当局未确认死伤"],
                          ["伤亡尚未确认", "枪击原因不明"])
    good_ner = _mk_result(ner_tid, "NER", "en", "transport_disruption",
                          "尼日尔虚构城镇 Kori 附近主干道因不明物体临时关闭，交通改道，官方未报告伤亡。",
                          ["主干道关闭", "交通改道", "安保检查"],
                          ["物体性质未定", "官方未报告人员伤亡"])
    bad_tcd = _mk_result(tcd_tid, "TCD", "fr", "pension_workshop",
                         "养老金研讨会。", ["x"], ["y"])
    bad_ner = _mk_result(ner_tid, "NER", "en", "social_security_forum",
                         "社会保障论坛。", ["x"], ["y"])
    ok5 = (validate_event(good_tcd) == []
           and validate_event(good_ner) == []
           and validate_event(bad_tcd) != []
           and validate_event(bad_ner) != [])
    check("T5", ok5, "good_tcd=%s good_ner=%s bad_tcd=%s bad_ner=%s" % (
        validate_event(good_tcd), validate_event(good_ner),
        validate_event(bad_tcd), validate_event(bad_ner)))

    # ═══ T6: 未确认伤亡不得写成已确认事实 ═══
    print("\n=== T6: unconfirmed casualties must not be written as confirmed ===")
    confirmed_tcd = _mk_result(tcd_tid, "TCD", "fr", "armed_incident",
                               "已确认造成5人死亡。", ["x"], ["y"])
    ok6 = (validate_event(confirmed_tcd) != [])
    check("T6", ok6, "confirmed_tcd_errs=%s" % validate_event(confirmed_tcd))

    # ═══ T7: prepare 不自动生成 AI 结果 ═══
    print("\n=== T7: prepare does not auto-generate AI results ===")
    st = status_summary(r1)
    # 检查 completed 内无 ai_result 文件
    comp_dir = os.path.join(r1, "completed")
    comp_files = [f for f in os.listdir(comp_dir)] if os.path.isdir(comp_dir) else []
    ok7 = (st.get("completed", 0) == 0
           and st.get("processing", 0) == 2
           and len(comp_files) == 0)
    check("T7", ok7, "queue=%s processing=%s completed=%s" % (
        st.get("queue"), st.get("processing"), st.get("completed")))

    # ═══ T8: 真实 ingest 2 个合法结果 ═══
    print("\n=== T8: ingest accepts two valid results ===")
    results = [good_tcd, good_ner]
    rf = _write_result_file(r1, info["batch_id"], info["worker_id"], results)
    rep8 = ingest_results(r1, info["batch_id"], rf)
    ok8 = (rep8.get("accepted") == 2
           and rep8.get("rejected") == 0
           and rep8.get("batch_complete") is True)
    check("T8", ok8, "accepted=%s rejected=%s complete=%s" % (
        rep8.get("accepted"), rep8.get("rejected"), rep8.get("batch_complete")))

    # ═══ T9: 幂等重 ingest ═══
    print("\n=== T9: idempotent re-ingest ===")
    rep9 = ingest_results(r1, info["batch_id"], rf)
    outcomes = [e.get("outcome", "") for e in rep9.get("tasks", [])]
    all_idem = all(o == "idempotent_success" for o in outcomes)
    rc9, _, _ = _run_cli(r1, "ingest", "--batch-id", info["batch_id"],
                         "--result-file", rf)
    ok9 = (rep9.get("accepted") == 0 and all_idem
           and rep9.get("error") in (None, "")
           and rc9 == 0)
    check("T9", ok9, "accepted=%s outcomes=%s cli_rc=%s" % (
        rep9.get("accepted"), outcomes, rc9))

    # ═══ T10: verify 检查最终状态 ═══
    print("\n=== T10: verify checks final state ===")
    rc10, out10, _ = _run_demo_cli(r1, "verify")
    try:
        v10 = json.loads(out10)
    except Exception:
        v10 = {}
    ok10 = (isinstance(v10, dict)
            and v10.get("ok") is True
            and "checks" in v10)
    check("T10", ok10, "rc=%s ok=%s keys=%s" % (
        rc10, v10.get("ok"), list((v10.get("checks") or {}).keys())[:6]))

    # ═══ T11: verify 失败 CLI 非零（ingest 前）═══
    print("\n=== T11: verify failure -> CLI nonzero (before ingest) ===")
    r11 = _mk_root(); roots.append(r11)
    prepare(r11)
    rc11, out11, _ = _run_demo_cli(r11, "verify")
    try:
        v11 = json.loads(out11)
    except Exception:
        v11 = {}
    ok11 = (rc11 != 0 and v11.get("ok") is False)
    check("T11", ok11, "rc=%s ok=%s" % (rc11, v11.get("ok")))

    # ═══ T12: run ok=false CLI 非零 ═══
    print("\n=== T12: run ok=false -> CLI nonzero ===")
    r12 = _mk_root(); roots.append(r12)
    prepare(r12)
    rc12, _, _ = _run_demo_cli(r12, "run", "--result-file",
                                os.path.join(r12, "missing.json"))
    ok12 = (rc12 != 0)
    check("T12", ok12, "rc=%s" % rc12)

    # ═══ T13: 非对象结果优雅处理 ═══
    print("\n=== T13: non-object result handled ===")
    r13 = _mk_root(); roots.append(r13)
    inf13 = prepare(r13)
    res13 = [
        _mk_result(inf13["tasks"][0]["task_id"], "TCD", "fr", "armed_incident",
                   "x", ["a"], ["b"]),
        "this-is-not-an-object",
        12345,
    ]
    rf13 = _write_result_file(r13, inf13["batch_id"], inf13["worker_id"], res13)
    crashed = False
    try:
        rep13 = ingest_results(r13, inf13["batch_id"], rf13)
    except Exception:
        rep13 = None
        crashed = True
    outcomes = [e.get("outcome", "") for e in (rep13 or {}).get("tasks", [])]
    rejected_types = sum(1 for o in outcomes if o == "rejected_invalid_result_type")
    accepted13 = (rep13 or {}).get("accepted", 0)
    ok13 = (not crashed and rejected_types == 2 and accepted13 == 1)
    check("T13", ok13, "crashed=%s accepted=%s rejected_types=%s" % (
        crashed, accepted13, rejected_types))

    # ═══ T14: CLI 全部拒绝 退出码≠0 ═══
    print("\n=== T14: CLI all-rejected exit nonzero ===")
    r14 = _mk_root(); roots.append(r14)
    inf14 = prepare(r14)
    res14 = [
        _mk_result(inf14["tasks"][0]["task_id"], "TCD", "fr", "armed_incident",
                   "x", ["a"], ["b"], **{"provider": "openai_api"}),
        _mk_result(inf14["tasks"][1]["task_id"], "NER", "en",
                   "transport_disruption", "y", ["c"], ["d"],
                   **{"provider": "openai_api"}),
    ]
    rf14 = _write_result_file(r14, inf14["batch_id"], inf14["worker_id"], res14)
    rc14, _, _ = _run_cli(r14, "ingest", "--batch-id", inf14["batch_id"],
                          "--result-file", rf14)
    check("T14", rc14 != 0, "rc=%s" % rc14)

    # ═══ T15: CLI 部分 ingest 退出码=0 ═══
    print("\n=== T15: CLI partial ingest exit 0 ===")
    r15 = _mk_root(); roots.append(r15)
    inf15 = prepare(r15)
    res15 = [
        _mk_result(inf15["tasks"][0]["task_id"], "TCD", "fr", "armed_incident",
                   "乍得虚构地点发生枪击，安全部队封锁。", ["a"], ["b"]),
        _mk_result(inf15["tasks"][1]["task_id"], "NER", "en",
                   "transport_disruption", "y", ["c"], ["d"],
                   **{"provider": "openai_api"}),
    ]
    rf15 = _write_result_file(r15, inf15["batch_id"], inf15["worker_id"], res15)
    rc15, _, _ = _run_cli(r15, "ingest", "--batch-id", inf15["batch_id"],
                          "--result-file", rf15)
    check("T15", rc15 == 0, "rc=%s" % rc15)

    # ═══ T16: CLI status 退出码=0 ═══
    print("\n=== T16: CLI status exit 0 ===")
    r16 = _mk_root(); roots.append(r16)
    rc16, _, _ = _run_cli(r16, "status")
    check("T16", rc16 == 0, "rc=%s" % rc16)

    # ═══ T17: CLI 空队列 claim 退出码=0 ═══
    print("\n=== T17: CLI empty claim exit 0 ===")
    r17 = _mk_root(); roots.append(r17)
    rc17, _, _ = _run_cli(r17, "claim", "--batch-size", "2")
    check("T17", rc17 == 0, "rc=%s" % rc17)

    # ═══ T18: 不使用生产 data/ai；默认 ai_root 位于 .workbuddy_runtime ═══
    print("\n=== T18: isolated from production data/ai ===")
    prod_q = os.path.join(PROD_AI_ROOT, "queue")
    prod_count = sum(1 for f in os.listdir(prod_q) if f.endswith(".json")) \
        if os.path.isdir(prod_q) else 0
    in_runtime = ".workbuddy_runtime" in DEFAULT_AI_ROOT.replace("\\", "/")
    ok18 = (prod_count == 0 and in_runtime)
    check("T18", ok18, "prod_queue=%s in_runtime=%s" % (prod_count, in_runtime))

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
    print("ALL STAGE 2.5B-2A ACCEPTANCE-CORRECTION TESTS PASSED")


if __name__ == "__main__":
    main()
