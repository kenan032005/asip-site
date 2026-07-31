#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASIP Stage 2.5B-2B-P — 跨会话交接准备端 验收测试（TDD 红→绿）。

覆盖（对应 Stage 2.5B-2B-P 规范八）：
  C1   prepare 生成 2 个 synthetic=true 的虚构 article_analysis 任务（queue=2）
  C2   prepare 不执行 claim（无 batches/manifest/lease）
  C3   prepare 不生成 AI 结果（completed=0，无任何 results*.json）
  C4   HANDOFF_READY.json 结构正确（契约字段 + producer_session_id 格式 +
       producer_processed_results=false + expected_model 非空且非 hy3）；
       HANDOFF_READY.md 含 10 条交接指引且不含中文摘要/AI 结果
  C5   任务正文与哈希一致：queue 任务 content_hash == HANDOFF_READY 中的哈希
       == sha256(source_text)
  C6   inspect 初始状态正确（queue=2 / processing=0 / completed=0 / leases=0 /
       无 results / 哈希一致 / producer_processed_results=false），CLI 退出码=0
  C7   不使用生产 data/ai（默认 ai_root 位于 .workbuddy_runtime，生产 queue=0）
  C8   消费端能够 claim（从 HANDOFF_READY 读取 provider/model 后 claim 成功）
  C9   consumer 与 producer session ID 不同
  C10  合法结果能够 ingest（accepted=2，provider/model 与交接契约一致）
  C11  重复 ingest 幂等（accepted=0，全部 idempotent_success）
  C12  verify 检查最终状态（queue=0 / processing=0 / completed=2 / leases=0）
  C13  verify 检查 task_id 不变（completed 文件名 == HANDOFF_READY.task_ids）
  C14  verify 检查安全语义（TCD 已确认伤亡 / NER 虚构伤亡 => verify ok=false）
  C15  外部网络调用为 0（静态扫描 cross_session_handoff_demo.py 无网络库）
  C16  .workbuddy_runtime 被 Git 忽略（git check-ignore 生效）
  C17  Stage 2.5B-2A 全部回归通过（subprocess 运行 2.5B-2A 测试套件）

自动测试只使用确定性模拟结果，不冒充真实跨会话模型处理证据。
真实模型处理证据由接收端任务（全新的 WorkBuddy 会话）单独记录。
"""

import os
import re
import sys
import json
import shutil
import subprocess
import tempfile
import hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ai"))

from ai.contracts import validate_ai_result  # noqa: E402
from ai.workbuddy_worker import (  # noqa: E402
    claim_batch, ingest_results, status_summary, AI_ROOT as PROD_AI_ROOT,
)

try:  # TDD 红阶段模块尚不存在时，全部用例报失败而不是崩溃
    import cross_session_handoff_demo as CSH  # noqa: E402
except Exception as _e:  # pragma: no cover
    CSH = None
    _CSH_IMPORT_ERR = str(_e)

PY = sys.executable
DEMO = os.path.join(SCRIPTS, "ai", "cross_session_handoff_demo.py")
WORKER = os.path.join(SCRIPTS, "ai", "workbuddy_worker.py")
T25A = os.path.join(SCRIPTS, "tests", "test_stage25b2a_manual_handoff.py")

# 安全语义分类（与 2.5B-2A 一致）
SECURITY_EVENT_TYPES = {
    "armed_incident", "security_incident", "shooting_incident",
    "violent_incident", "explosion_incident",
}
TRANSPORT_EVENT_TYPES = {
    "transport_disruption", "road_closure", "traffic_disruption",
    "infrastructure_disruption",
}


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _mk_root():
    return tempfile.mkdtemp(prefix="s25b2b_")


def _read_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_result_file(ai_root, batch_id, worker_id, results,
                       fname="results.submit.json"):
    payload = {"batch_id": batch_id, "worker_id": worker_id,
               "completed_at": "2026-07-31T06:00:05+00:00",
               "results": results}
    p = os.path.join(ai_root, "batches", batch_id, fname)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return p


def _mk_result(task_id, country_iso3, lang, event_type, summary_zh,
               key_facts, uncertainties, provider="workbuddy_queue",
               model="deepseek-v4-flash"):
    return {
        "task_id": task_id,
        "schema_version": "1.0",
        "status": "success",
        "provider": provider,
        "model": model,
        "started_at": "2026-07-31T06:00:00+00:00",
        "completed_at": "2026-07-31T06:00:05+00:00",
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


def _run_demo_cli(ai_root, *args):
    cmd = [PY, DEMO, "--ai-root", ai_root] + list(args)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


def _run_worker_cli(ai_root, *args):
    """通过标准 worker CLI 执行（M 系列测试专用，禁止绕过 CLI 直接调函数）。"""
    cmd = [PY, WORKER, "--ai-root", ai_root] + list(args)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


def _queue_tasks(ai_root):
    q = os.path.join(ai_root, "queue")
    out = []
    if os.path.isdir(q):
        for fn in sorted(os.listdir(q)):
            if fn.endswith(".json"):
                out.append(_read_json(os.path.join(q, fn)))
    return out


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

    if CSH is None:  # TDD 红：模块未实现
        for i in range(1, 18):
            check("C%d" % i, False, "cross_session_handoff_demo missing: %s"
                  % _CSH_IMPORT_ERR)
        print("\nRESULT: PASS=%d FAIL=%d" % (0, fails))
        sys.exit(1)

    # ═══ C1: prepare 生成 2 个合成任务 ═══
    print("\n=== C1: prepare creates 2 synthetic tasks ===")
    r1 = _mk_root(); roots.append(r1)
    info = CSH.prepare(r1)
    st = status_summary(r1)
    queue_tasks = _queue_tasks(r1)
    ok1 = (st.get("queue") == 2
           and all(t.get("synthetic") is True for t in queue_tasks)
           and all(t.get("task_type") == "article_analysis" for t in queue_tasks))
    check("C1", ok1, "queue=%s synthetic=%s" % (
        st.get("queue"), [t.get("synthetic") for t in queue_tasks]))

    # ═══ C2: prepare 不执行 claim ═══
    print("\n=== C2: prepare does not claim ===")
    batches = os.path.join(r1, "batches")
    leases = os.path.join(r1, "leases")
    ok2 = (not os.path.isdir(batches)
           or not [d for d in os.listdir(batches)
                   if os.path.isdir(os.path.join(batches, d))
                   and not d.startswith(".tmp_")])
    ok2 = ok2 and (not os.path.isdir(leases)
                   or not [f for f in os.listdir(leases) if f.endswith(".json")])
    ok2 = ok2 and st.get("processing") == 0
    check("C2", ok2, "batches=%s leases=%s processing=%s" % (
        os.path.isdir(batches), os.path.isdir(leases), st.get("processing")))

    # ═══ C3: prepare 不生成 AI 结果 ═══
    print("\n=== C3: prepare produces no results ===")
    comp = os.path.join(r1, "completed")
    comp_count = sum(1 for f in os.listdir(comp) if f.endswith(".json")) \
        if os.path.isdir(comp) else 0
    results_files = []
    for base, _, fns in os.walk(r1):
        for fn in fns:
            if fn.startswith("results") and fn.endswith(".json"):
                results_files.append(os.path.join(base, fn))
    ok3 = (comp_count == 0 and not results_files
           and st.get("completed") == 0)
    check("C3", ok3, "completed=%s results_files=%d" % (comp_count,
                                                        len(results_files)))

    # ═══ C4: HANDOFF_READY 契约结构 ═══
    print("\n=== C4: HANDOFF_READY contract structure ===")
    hj = os.path.join(r1, "HANDOFF_READY.json")
    hm = os.path.join(r1, "HANDOFF_READY.md")
    h = _read_json(hj)
    need_keys = {"handoff_version", "stage", "producer_session_id", "created_at",
                 "repo_commit", "ai_root_relative", "expected_task_count",
                 "task_ids", "task_content_hashes", "expected_provider",
                 "expected_model", "consumer_must_claim",
                 "producer_processed_results"}
    ok4a = need_keys <= set(h.keys())
    ok4b = bool(re.fullmatch(r"producer_[0-9a-f]{8}", h["producer_session_id"]))
    ok4c = h.get("producer_processed_results") is False
    ok4d = h.get("expected_provider") == "workbuddy_queue"
    ok4e = (isinstance(h.get("expected_model"), str)
            and len(h["expected_model"]) > 0
            and h["expected_model"] != "hy3")
    ok4f = h.get("expected_task_count") == 2 and len(h.get("task_ids")) == 2
    ok4g = (h.get("ai_root_relative", "").replace("\\", "/")
            == ".workbuddy_runtime/stage25b2b")
    md = open(hm, "r", encoding="utf-8").read() if os.path.exists(hm) else ""
    guide = ["WORKBUDDY_AI_WORKER.md", "claim", "ingest", "verify",
             "data/ai", "外部 API", "DeepSeek V4 Flash"]
    ok4h = os.path.exists(hm) and all(g in md for g in guide)
    # 交接文件不得预置结果数据（中文摘要 / results 数组 / 任务结果）
    ok4i = not ("summary_zh" in md
                or h.get("results") is not None
                or h.get("ai_results") is not None)
    check("C4", ok4a and ok4b and ok4c and ok4d and ok4e and ok4f and ok4g
          and ok4h and ok4i,
          "keys_ok=%s pid_ok=%s model=%r md_ok=%s no_results=%s" % (
              ok4a, ok4b, h.get("expected_model"), ok4h, ok4i))

    # ═══ C5: 任务正文与哈希一致 ═══
    print("\n=== C5: task content_hash matches source_text ===")
    hh = h["task_content_hashes"]
    ok5 = True
    detail = ""
    for t in queue_tasks:
        tid = t["task_id"]
        src = (t.get("input_ref") or {}).get("source_text") or ""
        calc = _sha256(src)
        if tid not in hh or hh[tid] != t.get("content_hash") or calc != hh[tid]:
            ok5 = False
            detail = "mismatch for %s" % tid
            break
        if (t.get("input_ref") or {}).get("synthetic") is not True:
            ok5 = False
            detail = "synthetic flag missing for %s" % tid
            break
    check("C5", ok5, detail or "all hashes match source_text")

    # ═══ C6: inspect 初始状态正确（CLI） ═══
    print("\n=== C6: inspect initial state (CLI) ===")
    rc6, out6, _ = _run_demo_cli(r1, "inspect")
    try:
        insp = json.loads(out6)
    except Exception:
        insp = {}
    ok6 = (rc6 == 0
           and insp.get("ok") is True
           and insp.get("checks", {}).get("queue") == 2
           and insp.get("checks", {}).get("processing") == 0
           and insp.get("checks", {}).get("completed") == 0
           and insp.get("checks", {}).get("leases") == 0
           and insp.get("checks", {}).get("results_files") == 0
           and insp.get("checks", {}).get("producer_processed_results") is False
           and insp.get("checks", {}).get("hashes_match") is True
           and insp.get("checks", {}).get("handoff_present") is True
           and insp.get("checks", {}).get("task_ids_match")
           == sorted(h["task_ids"]))
    check("C6", ok6, "rc=%s inspect=%s" % (rc6, out6[-300:]))

    # ═══ C7: 不使用生产 data/ai ═══
    print("\n=== C7: isolated from production data/ai ===")
    prod_q = os.path.join(PROD_AI_ROOT, "queue")
    prod_count = sum(1 for f in os.listdir(prod_q) if f.endswith(".json")) \
        if os.path.isdir(prod_q) else 0
    in_runtime = ".workbuddy_runtime" in CSH.DEFAULT_AI_ROOT.replace("\\", "/")
    ok7 = (prod_count == 0 and in_runtime)
    check("C7", ok7, "prod_queue=%s default_root_in_runtime=%s"
          % (prod_count, in_runtime))

    # ═══ C8–C13: 接收端链路（同一 root） ═══
    print("\n=== C8-C13: consumer chain ===")
    r8 = _mk_root(); roots.append(r8)
    p8 = CSH.prepare(r8)
    h8 = _read_json(os.path.join(r8, "HANDOFF_READY.json"))
    consumer_session = "consumer_%s" % _sha256("consumer")[:8]

    # C8: 消费端能够 claim（provider/model 取自交接契约）
    claim8 = claim_batch(r8, worker_id="workbuddy-consumer", batch_size=2,
                         lease_minutes=30,
                         expected_provider=h8["expected_provider"],
                         expected_model=h8["expected_model"])
    ok8 = (claim8.get("task_count") == 2
           and claim8.get("batch_id")
           and claim8.get("worker_id") == "workbuddy-consumer")
    manifest = _read_json(os.path.join(r8, "batches", claim8["batch_id"],
                                       "manifest.json"))
    ok8 = ok8 and manifest.get("expected_model") == h8["expected_model"]
    check("C8", ok8, "claimed=%s model=%s" % (claim8.get("task_count"),
                                              manifest.get("expected_model")))

    # C9: consumer 与 producer session ID 不同
    ok9 = (consumer_session != h8["producer_session_id"]
           and consumer_session.startswith("consumer_"))
    check("C9", ok9, "producer=%s consumer=%s" % (h8["producer_session_id"],
                                                  consumer_session))

    # C10: 合法结果能够 ingest
    exp_model = h8["expected_model"]
    results10 = []
    for t in claim8["tasks"]:
        tid = t["task_id"]
        iso3 = (t.get("input_ref") or {}).get("country_iso3")
        lang = (t.get("input_ref") or {}).get("source_language")
        if iso3 == "TCD":
            results10.append(_mk_result(
                tid, "TCD", lang, "security_incident",
                "乍得某虚构城镇发生短暂骚乱，当局实施夜间宵禁并在主要道路设置检查点；"
                "伤亡人数尚未获得官方确认。",
                ["夜间宵禁", "主要道路检查点", "官方未确认伤亡"],
                ["伤亡数字未得到官方确认"], provider="workbuddy_queue",
                model=exp_model))
        else:
            results10.append(_mk_result(
                tid, "NER", lang, "transport_disruption",
                "尼日尔某虚构地区道路阻断，安全部门引导车辆绕行，恢复时间尚未公布；"
                "官方未报告人员伤亡。",
                ["道路阻断", "车辆绕行", "恢复时间未公布"],
                ["官方未报告人员伤亡"], provider="workbuddy_queue",
                model=exp_model))
    rf10 = _write_result_file(r8, claim8["batch_id"], "workbuddy-consumer",
                              results10)
    rep10 = ingest_results(r8, claim8["batch_id"], rf10)
    ok10 = (rep10.get("accepted") == 2 and rep10.get("rejected") == 0
            and rep10.get("batch_complete") is True)
    # model 一致性：completed 结果中的 model == 交接契约 model
    comp_ids = set()
    for fn in os.listdir(os.path.join(r8, "completed")):
        if fn.endswith(".json"):
            cobj = _read_json(os.path.join(r8, "completed", fn))
            comp_ids.add(fn[:-5])
            if (cobj.get("ai_result") or {}).get("model") != exp_model:
                ok10 = False
    check("C10", ok10, "accepted=%s rejected=%s ids=%s" % (
        rep10.get("accepted"), rep10.get("rejected"), sorted(comp_ids)))

    # C11: 重复 ingest 幂等
    rep11 = ingest_results(r8, claim8["batch_id"], rf10)
    ok11 = (rep11.get("accepted") == 0
            and all(e.get("outcome") == "idempotent_success"
                    for e in rep11.get("tasks", [])))
    check("C11", ok11, "accepted=%s outcomes=%s" % (
        rep11.get("accepted"), [e.get("outcome") for e in rep11.get("tasks", [])]))

    # C12: verify 检查最终状态
    v12 = CSH.verify(r8, consumer_session_id=consumer_session)
    ok12 = (v12.get("ok") is True
            and v12.get("checks", {}).get("queue") == 0
            and v12.get("checks", {}).get("processing") == 0
            and v12.get("checks", {}).get("completed") == 2
            and v12.get("checks", {}).get("leases") == 0)
    check("C12", ok12, "verify=%s" % (json.dumps(v12, ensure_ascii=False)[-400:]))

    # C13: verify 检查 task_id 不变
    ok13 = (set(v12.get("checks", {}).get("completed_task_ids", []))
            == set(h8["task_ids"]))
    check("C13", ok13, "completed=%s expected=%s" % (
        v12.get("checks", {}).get("completed_task_ids"), h8["task_ids"]))

    # ═══ C14: verify 拒绝安全语义错误结果 ═══
    print("\n=== C14: verify rejects semantic violations ===")
    r14 = _mk_root(); roots.append(r14)
    p14 = CSH.prepare(r14)
    h14 = _read_json(os.path.join(r14, "HANDOFF_READY.json"))
    claim14 = claim_batch(r14, worker_id="workbuddy-consumer", batch_size=2,
                          lease_minutes=30,
                          expected_provider=h14["expected_provider"],
                          expected_model=h14["expected_model"])
    results14 = []
    for t in claim14["tasks"]:
        tid = t["task_id"]
        iso3 = (t.get("input_ref") or {}).get("country_iso3")
        lang = (t.get("input_ref") or {}).get("source_language")
        if iso3 == "TCD":
            # 坏结果：把未确认伤亡写成已确认
            results14.append(_mk_result(
                tid, "TCD", lang, "security_incident",
                "骚乱已造成至少 5 人死亡、多人受伤，宵禁生效。",
                ["夜间宵禁"], ["伤亡已确认"], provider="workbuddy_queue",
                model=h14["expected_model"]))
        else:
            # 坏结果：虚构伤亡
            results14.append(_mk_result(
                tid, "NER", lang, "transport_disruption",
                "阻断导致 3 人死亡，绕行路段拥堵。",
                ["道路阻断"], ["3 人死亡"], provider="workbuddy_queue",
                model=h14["expected_model"]))
    rf14 = _write_result_file(r14, claim14["batch_id"], "workbuddy-consumer",
                              results14)
    ingest_results(r14, claim14["batch_id"], rf14)
    v14 = CSH.verify(r14, consumer_session_id="consumer_%s" % _sha256("x")[:8])
    ok14 = (v14.get("ok") is False
            and any("semantics" in str(e) for e in v14.get("errors", [])))
    check("C14", ok14, "verify_ok=%s errors=%s" % (v14.get("ok"),
                                                   v14.get("errors")))

    # ═══ C15: 外部网络调用为 0（静态扫描） ═══
    print("\n=== C15: no external network calls in module ===")
    src = open(DEMO, "r", encoding="utf-8").read()
    banned = [r"\bimport\s+(requests|urllib|httpx|aiohttp|socket|http)\b",
              r"\bfrom\s+(requests|urllib|httpx|aiohttp|socket|http)\s+import",
              r"\burlopen\b", r"\bcurl\b", r"\bwget\b"]
    hits = [b for b in banned if re.search(b, src)]
    ok15 = not hits
    check("C15", ok15, "banned_network_imports=%s" % hits)

    # ═══ C16: runtime 目录被 Git 忽略 ═══
    print("\n=== C16: .workbuddy_runtime git-ignored ===")
    gi = os.path.join(ROOT, ".gitignore")
    gi_txt = open(gi, "r", encoding="utf-8").read()
    has_entry = ".workbuddy_runtime" in gi_txt
    check_proc = subprocess.run(
        ["git", "check-ignore", "-q", ".workbuddy_runtime/stage25b2b/x.json"],
        cwd=ROOT, capture_output=True)
    ok16 = has_entry and check_proc.returncode == 0
    check("C16", ok16, "gitignore_entry=%s check_ignore_rc=%s" % (
        has_entry, check_proc.returncode))

    # ═══ C17: Stage 2.5B-2A 全部回归 ═══
    print("\n=== C17: Stage 2.5B-2A regression ===")
    rc17, out17, err17 = -1, "", ""
    try:
        p17 = subprocess.run([PY, T25A], capture_output=True, text=True,
                             timeout=300)
        rc17, out17, err17 = p17.returncode, p17.stdout, p17.stderr
    except subprocess.TimeoutExpired:
        rc17 = -1
    ok17 = rc17 == 0 and "FAIL=0" in out17
    check("C17", ok17, "rc=%s tail=%s" % (rc17, (out17 + err17)[-200:]))

    # ══════════════════════════════════════════════════════════════════
    # M 系列（Microfix）：跨会话 Claim 模型传递（2.5B-2B-P Microfix）
    # 全部通过「标准 worker CLI」验证，禁止直接调用 claim_batch 代替。
    # ══════════════════════════════════════════════════════════════════

    def _claim_batch_dir(ai_root, claim_out):
        """从 CLI claim 的 JSON 输出提取批次目录。"""
        try:
            obj = json.loads(claim_out)
        except Exception:
            return None
        bid = (obj or {}).get("batch_id")
        if not bid:
            return None
        return os.path.join(ai_root, "batches", bid)

    # ═══ M1: claim CLI 接受 --expected-provider / --expected-model ═══
    print("\n=== M1: claim CLI accepts provider/model flags ===")
    m1 = _mk_root(); roots.append(m1)
    CSH.prepare(m1)
    rc_m1, out_m1, err_m1 = _run_worker_cli(
        m1, "claim", "--batch-size", "2",
        "--worker-id", "workbuddy-cross-session-test",
        "--lease-minutes", "30",
        "--expected-provider", "workbuddy_queue",
        "--expected-model", "deepseek-v4-flash",
        "--no-prompt-binding")
    ok_m1 = (rc_m1 == 0 and "batch_id" in out_m1)
    check("M1", ok_m1, "rc=%s err=%s" % (rc_m1, err_m1[-200:]))

    # ═══ M2: CLI claim 的 manifest 携带正确 provider/model ═══
    print("\n=== M2: manifest carries provider/model via CLI ===")
    bdir_m2 = _claim_batch_dir(m1, out_m1)
    ok_m2 = False
    if bdir_m2 and os.path.exists(os.path.join(bdir_m2, "manifest.json")):
        man_m2 = _read_json(os.path.join(bdir_m2, "manifest.json"))
        ok_m2 = (man_m2.get("expected_provider") == "workbuddy_queue"
                 and man_m2.get("expected_model") == "deepseek-v4-flash")
    check("M2", ok_m2, "manifest=%s" % (
        _read_json(os.path.join(bdir_m2, "manifest.json"))
        if bdir_m2 and os.path.exists(os.path.join(bdir_m2, "manifest.json"))
        else "missing"))

    # ═══ M3: results.template 与 manifest 一致 ═══
    print("\n=== M3: results.template matches manifest ===")
    ok_m3 = False
    if bdir_m2:
        tpl = _read_json(os.path.join(bdir_m2, "results.template.json"))
        man = _read_json(os.path.join(bdir_m2, "manifest.json"))
        ok_m3 = (len(tpl.get("results", [])) == 2
                 and all(r.get("provider") == man.get("expected_provider")
                         and r.get("model") == man.get("expected_model")
                         for r in tpl.get("results", [])))
    check("M3", ok_m3, "template_provider/model=%s/%s" % (
        tpl["results"][0].get("provider") if bdir_m2 and tpl.get("results") else "?",
        tpl["results"][0].get("model") if bdir_m2 and tpl.get("results") else "?"))

    # ═══ M4: WORKBUDDY_REQUEST.md 动态显示 DeepSeek V4 Flash ═══
    print("\n=== M4: REQUEST.md shows DeepSeek V4 Flash, no Hy3 ===")
    ok_m4 = False
    if bdir_m2:
        req = open(os.path.join(bdir_m2, "WORKBUDDY_REQUEST.md"),
                   "r", encoding="utf-8").read()
        ok_m4 = ("DeepSeek V4 Flash" in req
                 and "deepseek-v4-flash" in req
                 and "workbuddy_queue" in req
                 and "使用当前 WorkBuddy 内置 Hy3" not in req)
    check("M4", ok_m4, "req_ok=%s" % ok_m4)

    # ═══ M5: 未传 --expected-model 时保持安全默认 hy3 ═══
    print("\n=== M5: default expected_model stays hy3 ===")
    m5 = _mk_root(); roots.append(m5)
    CSH.prepare(m5)
    rc_m5, out_m5, _ = _run_worker_cli(
        m5, "claim", "--batch-size", "2",
        "--worker-id", "workbuddy-cross-session-test",
        "--lease-minutes", "30",
        "--expected-provider", "workbuddy_queue",
        "--no-prompt-binding")
    bdir_m5 = _claim_batch_dir(m5, out_m5)
    ok_m5 = False
    if rc_m5 == 0 and bdir_m5:
        man_m5 = _read_json(os.path.join(bdir_m5, "manifest.json"))
        ok_m5 = (man_m5.get("expected_provider") == "workbuddy_queue"
                 and man_m5.get("expected_model") == "hy3")
    check("M5", ok_m5, "rc=%s model=%s" % (
        rc_m5,
        _read_json(os.path.join(bdir_m5, "manifest.json")).get("expected_model")
        if bdir_m5 and os.path.exists(os.path.join(bdir_m5, "manifest.json"))
        else "?"))

    # ═══ M6: 非法 expected-model 必须失败并返回非零 ═══
    print("\n=== M6: invalid expected-model rejected (nonzero) ===")
    m6 = _mk_root(); roots.append(m6)
    CSH.prepare(m6)
    rc_m6, _, err_m6 = _run_worker_cli(
        m6, "claim", "--batch-size", "2",
        "--expected-provider", "workbuddy_queue",
        "--expected-model", "")
    bad_chars_rc, _, _ = _run_worker_cli(
        m6, "claim", "--batch-size", "2",
        "--expected-provider", "workbuddy_queue",
        "--expected-model", "bad model!")
    long_rc, _, _ = _run_worker_cli(
        m6, "claim", "--batch-size", "2",
        "--expected-provider", "workbuddy_queue",
        "--expected-model", "x" * 101)
    ok_m6 = (rc_m6 != 0 and "expected_model" in err_m6
             and bad_chars_rc != 0 and long_rc != 0)
    check("M6", ok_m6, "empty_rc=%s badchars_rc=%s long_rc=%s err=%s" % (
        rc_m6, bad_chars_rc, long_rc, err_m6[-200:]))

    # 清理临时目录
    for r in roots:
        if os.path.isdir(r):
            shutil.rmtree(r, ignore_errors=True)

    # ── 汇总 ──
    print("\n" + "=" * 64)
    print("RESULT: PASS=%d FAIL=%d" % (total - fails, fails))
    print("=" * 64)
    if fails:
        sys.exit(1)
    print("ALL STAGE 2.5B-2B-P CROSS-SESSION TESTS PASSED")


if __name__ == "__main__":
    main()
