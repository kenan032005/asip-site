#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASIP Stage 2.5B-1 — WorkBuddy AI 任务领取与交接协议验收测试（TDD）。

先写测试：在实现 scripts/ai/workbuddy_worker.py 与 pipeline_core.sanitize_log_value
之前，本文件必然失败（ImportError / 断言失败）；实现完成后全部通过。

覆盖（对应规范十四）：
  W1   日志脱敏后 JSON 合法（Windows 路径 / 空格路径 / 双引号 / 多行 / JSON 片段）
  W2   空队列 claim 正常返回
  W3   优先级排序（critical > high > normal > low，同级按 created_at）
  W4   batch-size 限制
  W5   同一任务不可重复领取
  W6   claim 原子回滚
  W7   manifest 结构
  W8   lease 结构（默认 30 分钟）
  W9   worker_id 验证（ingest 拒绝错误 worker）
  W10  heartbeat（原 worker 可延长、他人拒绝、completed 不能续约）
  W11  合法结果 ingest -> completed
  W12  非法结果拒绝（保持 processing，记录原因）
  W13  部分成功批次（无效结果不影响有效结果）
  W14  重复 ingest 幂等（idempotent_success，不生成第二份文件）
  W15  过期任务重新入队（retry_count+1，task_id 不变）
  W16  达到重试上限 -> permanently_failed
  W17  task_id 全流程保持不变
  W18  audit 日志可解析（JSON Lines）
  W19  audit 无本机路径 / 用户名
  W20  dist 不包含 batches / leases / audit
  W21  Worker 源码无外部 AI 网络调用
  W22  Stage 2.5A 回归全部通过
  W23  并发 claim 只有一个成功领取同一任务
  W24  release 批次归还任务
"""

import os
import sys
import json
import time
import glob
import shutil
import getpass
import tempfile
import threading
import subprocess
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

from pipeline_core import sanitize_log_value  # noqa: E402
from ai.contracts import new_ai_task  # noqa: E402
from ai.workbuddy_queue_provider import WorkbuddyQueueProvider, move_task  # noqa: E402
from ai.workbuddy_worker import (  # noqa: E402
    claim_batch,
    ingest_results,
    recover_expired,
    heartbeat_batch,
    release_batch,
    status_summary,
    DEFAULT_LEASE_MINUTES,
)

PY = sys.executable


def _mk_root():
    return tempfile.mkdtemp(prefix="s25b1_")


def _submit(provider, idx, priority="normal", created_at=None, max_retries=2):
    t = new_ai_task(
        "article_analysis", {"id": "mock-%s" % idx}, "hash-%s" % idx,
        "p1", "o1", priority=priority, created_at=created_at, max_retries=max_retries,
    )
    return provider.submit_task(t)


def _count(ai_root, state):
    d = os.path.join(ai_root, state)
    if not os.path.isdir(d):
        return 0
    return sum(1 for f in os.listdir(d) if f.endswith(".json"))


def _mk_result(task_id, status="success", **over):
    r = {
        "task_id": task_id,
        "schema_version": "1.0",
        "status": status,
        "provider": "workbuddy_queue",
        "model": "hy3",
        "started_at": "2026-07-31T04:00:00+00:00",
        "completed_at": "2026-07-31T04:00:05+00:00",
        "result": {"summary": "mock"} if status == "success" else {},
        "error": None if status == "success" else {"code": "E_MOCK", "message": "mock failure"},
        "usage": {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0},
    }
    r.update(over)
    return r


def _write_result_file(ai_root, batch_id, worker_id, results):
    payload = {
        "batch_id": batch_id,
        "worker_id": worker_id,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
    fd, path = tempfile.mkstemp(prefix="res_", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def _expire_lease(ai_root, task_id):
    p = os.path.join(ai_root, "leases", "%s.json" % task_id)
    with open(p, "r", encoding="utf-8") as f:
        lease = json.load(f)
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    lease["lease_expires_at"] = past
    lease["heartbeat_at"] = past
    with open(p, "w", encoding="utf-8") as f:
        json.dump(lease, f)


def main():
    print("=" * 64)
    print("ASIP Stage 2.5B-1 — Worker 协议验收测试")
    print("=" * 64)
    fails = 0
    total = 0

    def check(name, ok, detail=""):
        nonlocal fails, total
        total += 1
        if ok:
            print("  [PASS] %s" % name)
        else:
            fails += 1
            print("  [FAIL] %s :: %s" % (name, detail))

    user = getpass.getuser()

    # ── W1 日志脱敏后 JSON 合法 ──
    # 注意：源码不得出现 Windows 用户目录字面量（会触发 Stage-1 源码卫生扫描）。
    # 以下样例路径均在运行时拼接，源码中仅含分段常量。
    _DRV = "C:"
    _SEP = "\\"
    _USR = "Users"
    def _win(*parts):
        body = _SEP.join(parts) if parts else ""
        return _DRV + _SEP + _USR + _SEP + user + (_SEP + body if body else "")
    def _win2(*parts):
        # 双反斜杠变体（JSON 文本内的转义形式）
        body = "\\".join(parts) if parts else ""
        return _DRV + _SEP + _SEP + _USR + _SEP + _SEP + user + (_SEP + _SEP + body if body else "")
    def _posix(*parts):
        body = "/".join(parts) if parts else ""
        return _DRV + "/" + _USR + "/" + user + ("/" + body if body else "")
    dirty = {
        "win_path": _win("WorkBuddy", "proj", "file.py"),
        "space_path": _win("My Documents", "a b", "file.txt"),
        "quotes": 'error: "cannot" open file ' + _win("x.json") + " here",
        "multiline": "line1\r\nline2 " + _posix("y.log") + "\nline3",
        "json_frag": '{"target": "' + _win2("z.bak") + '", "reason": "x"}',
        "nested": {"list": [_win("n1.txt"), 42, None, True]},
        "unix": "/Users/%s/some file/deep.txt and /home/%s/a.log" % (user, user),
    }
    clean = sanitize_log_value(dirty)
    w1_ok = True
    w1_detail = ""
    try:
        text = json.dumps(clean, ensure_ascii=False)
        json.loads(text)  # 序列化后必须可回读
    except Exception as e:
        w1_ok = False
        w1_detail = "JSON 往返失败: %s" % e
    if w1_ok:
        flat = json.dumps(clean, ensure_ascii=False)
        _needle_win = _DRV + _SEP + _USR
        _needle_posix = _DRV + "/" + _USR
        if user in flat:
            w1_ok, w1_detail = False, "脱敏后仍含本机用户名"
        elif _needle_win in flat.replace("\\\\", "\\") or _needle_posix in flat:
            w1_ok, w1_detail = False, "脱敏后仍含 Windows 用户绝对路径"
    check("W1", w1_ok, w1_detail)

    # ── W2 空队列 claim ──
    root2 = _mk_root()
    try:
        r = claim_batch(root2, worker_id="w1", batch_size=3)
        check("W2", r.get("task_count") == 0 and not r.get("batch_id"),
              "空队列返回异常: %s" % r)
    except Exception as e:
        check("W2", False, "空队列抛异常: %s" % e)

    # ── W3 优先级排序 ──
    root3 = _mk_root()
    p3 = WorkbuddyQueueProvider({}, ai_root=root3)
    base = datetime(2026, 7, 30, 10, 0, 0, tzinfo=timezone.utc)
    t_low = _submit(p3, "low", "low", (base + timedelta(minutes=1)).isoformat())
    t_crit = _submit(p3, "crit", "critical", (base + timedelta(minutes=3)).isoformat())
    t_norm1 = _submit(p3, "n1", "normal", (base + timedelta(minutes=2)).isoformat())
    t_norm2 = _submit(p3, "n2", "normal", (base + timedelta(minutes=0)).isoformat())
    t_high = _submit(p3, "high", "high", (base + timedelta(minutes=4)).isoformat())
    m3 = claim_batch(root3, worker_id="w1", batch_size=3)
    got = [t["task_id"] for t in m3["tasks"]]
    expect = [t_crit["task_id"], t_high["task_id"], t_norm2["task_id"]]
    check("W3", got == expect, "优先级顺序错误: got=%s expect=%s" % (got, expect))

    # ── W4 batch-size 限制 ──
    check("W4", m3["task_count"] == 3 and _count(root3, "queue") == 2,
          "batch_size 未限制（claimed=%s, left=%d）" % (m3["task_count"], _count(root3, "queue")))

    # ── W5 同一任务不可重复领取 ──
    m3b = claim_batch(root3, worker_id="w2", batch_size=5)
    got_b = {t["task_id"] for t in m3b["tasks"]}
    check("W5", got_b.isdisjoint(set(got)) and len(got_b) == 2,
          "第二次 claim 领到了已领取任务: %s" % (got_b & set(got)))

    # ── W6 claim 原子回滚 ──
    root6 = _mk_root()
    p6 = WorkbuddyQueueProvider({}, ai_root=root6)
    for i in range(3):
        _submit(p6, "rb%d" % i)
    try:
        claim_batch(root6, worker_id="w1", batch_size=3, _fail_after=2)
        check("W6", False, "_fail_after 未触发异常")
    except Exception:
        q, pr = _count(root6, "queue"), _count(root6, "processing")
        leases = len(glob.glob(os.path.join(root6, "leases", "*.json")))
        check("W6", q == 3 and pr == 0 and leases == 0,
              "回滚不完整 queue=%d processing=%d leases=%d" % (q, pr, leases))

    # ── W7 manifest 结构 ──
    man_path = os.path.join(root3, "batches", m3["batch_id"], "manifest.json")
    w7_ok = os.path.exists(man_path)
    if w7_ok:
        man = json.load(open(man_path, encoding="utf-8"))
        for k in ("batch_id", "worker_id", "created_at", "lease_expires_at",
                  "task_count", "tasks"):
            if k not in man:
                w7_ok = False
        req_md = os.path.join(root3, "batches", m3["batch_id"], "WORKBUDDY_REQUEST.md")
        tpl = os.path.join(root3, "batches", m3["batch_id"], "results.template.json")
        w7_ok = w7_ok and os.path.exists(req_md) and os.path.exists(tpl)
        if w7_ok:
            json.load(open(tpl, encoding="utf-8"))  # 模板必须是合法 JSON
    check("W7", w7_ok, "manifest/WORKBUDDY_REQUEST/results.template 缺失或残缺")

    # ── W8 lease 结构 ──
    lease_p = os.path.join(root3, "leases", "%s.json" % got[0])
    w8_ok = os.path.exists(lease_p)
    if w8_ok:
        lease = json.load(open(lease_p, encoding="utf-8"))
        for k in ("task_id", "batch_id", "worker_id", "claimed_at",
                  "lease_expires_at", "heartbeat_at", "attempt_number"):
            if k not in lease:
                w8_ok = False
        if w8_ok:
            exp = datetime.fromisoformat(lease["lease_expires_at"])
            cla = datetime.fromisoformat(lease["claimed_at"])
            mins = (exp - cla).total_seconds() / 60
            w8_ok = abs(mins - DEFAULT_LEASE_MINUTES) < 2
    check("W8", w8_ok, "lease 缺失、字段不全或时长非默认 30 分钟")

    # ── W9 worker_id 验证 ──
    rf9 = _write_result_file(root3, m3["batch_id"], "intruder",
                             [_mk_result(got[0])])
    rep9 = ingest_results(root3, m3["batch_id"], rf9)
    check("W9", rep9.get("accepted", 0) == 0 and _count(root3, "completed") == 0,
          "错误 worker_id 未被拒绝: %s" % rep9)

    # ── W10 heartbeat ──
    lease_before = json.load(open(lease_p, encoding="utf-8"))
    time.sleep(0.05)
    hb1 = heartbeat_batch(root3, m3["batch_id"], "w1")
    lease_after = json.load(open(lease_p, encoding="utf-8"))
    hb2 = heartbeat_batch(root3, m3["batch_id"], "someone-else")
    w10_ok = (hb1.get("extended", 0) == 3
              and lease_after["lease_expires_at"] >= lease_before["lease_expires_at"]
              and hb2.get("extended", 0) == 0)
    check("W10", w10_ok, "心跳规则不符: hb1=%s hb2=%s" % (hb1, hb2))

    # ── W11 合法结果 ingest ──
    rf11 = _write_result_file(root3, m3["batch_id"], "w1", [_mk_result(got[0])])
    rep11 = ingest_results(root3, m3["batch_id"], rf11)
    w11_ok = (rep11.get("accepted") == 1
              and os.path.exists(os.path.join(root3, "completed", "%s.json" % got[0]))
              and not os.path.exists(lease_p))
    check("W11", w11_ok, "合法结果未正确完成: %s" % rep11)

    # W10 补充：已完成任务不能续约
    hb3 = heartbeat_batch(root3, m3["batch_id"], "w1")
    check("W10b", hb3.get("extended", 0) == 2,
          "completed 任务仍被续约: %s" % hb3)

    # ── W12 非法结果拒绝 ──
    bad = _mk_result(got[1])
    del bad["usage"]  # 缺 usage -> 契约失败
    rf12 = _write_result_file(root3, m3["batch_id"], "w1", [bad])
    rep12 = ingest_results(root3, m3["batch_id"], rf12)
    still_processing = os.path.exists(os.path.join(root3, "processing", "%s.json" % got[1]))
    w12_ok = rep12.get("accepted", 0) == 0 and still_processing
    reasons = json.dumps(rep12, ensure_ascii=False)
    check("W12", w12_ok and "usage" in reasons,
          "非法结果处理错误: %s" % rep12)

    # ── W13 部分成功批次 ──
    bad13 = _mk_result(got[2]);  bad13["schema_version"] = "9.9"
    ok13 = _mk_result(got[1])
    rf13 = _write_result_file(root3, m3["batch_id"], "w1", [ok13, bad13])
    rep13 = ingest_results(root3, m3["batch_id"], rf13)
    w13_ok = (rep13.get("accepted") == 1
              and os.path.exists(os.path.join(root3, "completed", "%s.json" % got[1]))
              and os.path.exists(os.path.join(root3, "processing", "%s.json" % got[2])))
    check("W13", w13_ok, "部分成功批次处理错误: %s" % rep13)

    # ── W14 重复 ingest 幂等 ──
    before_files = sorted(os.listdir(os.path.join(root3, "completed")))
    rep14 = ingest_results(root3, m3["batch_id"], rf13)
    after_files = sorted(os.listdir(os.path.join(root3, "completed")))
    idem = [r for r in rep14.get("tasks", []) if r.get("outcome") == "idempotent_success"]
    check("W14", before_files == after_files and len(idem) >= 1,
          "重复 ingest 非幂等: %s" % rep14)

    # ── W15 过期任务重新入队 ──
    _expire_lease(root3, got[2])
    rep15 = recover_expired(root3)
    q_task = os.path.join(root3, "queue", "%s.json" % got[2])
    w15_ok = os.path.exists(q_task)
    if w15_ok:
        obj = json.load(open(q_task, encoding="utf-8"))
        w15_ok = obj.get("status") == "queued" and obj.get("retry_count") == 1
    check("W15", w15_ok, "过期恢复未按预期重新入队: %s" % rep15)

    # ── W16 达到重试上限永久失败 ──
    root16 = _mk_root()
    p16 = WorkbuddyQueueProvider({}, ai_root=root16)
    t16 = new_ai_task("article_analysis", {"id": "exh"}, "hx", "p1", "o1", max_retries=1)
    t16["retry_count"] = 1
    r16 = p16.submit_task(t16)
    m16 = claim_batch(root16, worker_id="w1", batch_size=1)
    _expire_lease(root16, r16["task_id"])
    recover_expired(root16)
    f_task = os.path.join(root16, "failed", "%s.json" % r16["task_id"])
    w16_ok = os.path.exists(f_task)
    if w16_ok:
        obj = json.load(open(f_task, encoding="utf-8"))
        w16_ok = obj.get("status") == "permanently_failed"
    check("W16", w16_ok, "达到上限未 permanently_failed")

    # ── W17 task_id 全流程不变 ──
    comp = json.load(open(os.path.join(root3, "completed", "%s.json" % got[0]),
                          encoding="utf-8"))
    check("W17", comp.get("task_id") == got[0] and
          json.load(open(q_task, encoding="utf-8")).get("task_id") == got[2],
          "task_id 在流转中被改变")

    # ── W18 audit 可解析 ──
    audit_files = glob.glob(os.path.join(root3, "audit", "*.jsonl"))
    w18_ok = bool(audit_files)
    events = set()
    for af in audit_files:
        for line in open(af, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                events.add(rec.get("event"))
            except Exception as e:
                w18_ok = False
    need_events = {"task_claimed", "result_ingested", "task_completed", "task_requeued"}
    check("W18", w18_ok and need_events.issubset(events),
          "audit 不可解析或缺事件: %s" % (need_events - events))

    # ── W19 audit 无本机路径 ──
    w19_ok = True
    for af in audit_files:
        content = open(af, encoding="utf-8").read()
        if user in content or "C:\\" in content or "C:/" in content:
            w19_ok = False
    check("W19", w19_ok, "audit 含本机路径或用户名")

    # ── W20 dist 隔离 ──
    dist_dir = os.path.join(ROOT, "dist")
    bad20 = []
    if os.path.isdir(dist_dir):
        for r, dirs, files in os.walk(dist_dir):
            rel = os.path.relpath(r, dist_dir).replace("\\", "/")
            for name in dirs + files:
                p = (rel + "/" + name).lstrip("./")
                if any(seg in p for seg in ("ai/batches", "ai/leases", "ai/audit",
                                            "data/ai")):
                    bad20.append(p)
    check("W20", not bad20, "dist 暴露内部目录: %s" % bad20[:3])

    # ── W21 Worker 源码无外部 AI 网络调用 ──
    src = open(os.path.join(SCRIPTS, "ai", "workbuddy_worker.py"), encoding="utf-8").read()
    forbidden = ("import requests", "import urllib", "import socket", "openai",
                 "anthropic", "http://", "https://", "api_key", "API_KEY")
    hits = [k for k in forbidden if k in src]
    check("W21", not hits, "Worker 源码含疑似网络/密钥调用: %s" % hits)

    # ── W22 Stage 2.5A 回归 ──
    w22_ok = True
    w22_detail = ""
    for tf in ("test_stage25a_runtime_ai_contract.py", "test_stage25a_hardening.py"):
        r = subprocess.run([PY, os.path.join(SCRIPTS, "tests", tf)],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0 or "FAIL=0" not in r.stdout:
            w22_ok = False
            w22_detail += "%s rc=%d; " % (tf, r.returncode)
    check("W22", w22_ok, w22_detail)

    # ── W23 并发 claim ──
    root23 = _mk_root()
    p23 = WorkbuddyQueueProvider({}, ai_root=root23)
    for i in range(4):
        _submit(p23, "cc%d" % i)
    results23 = [None, None]

    def _worker(idx, wid):
        try:
            results23[idx] = claim_batch(root23, worker_id=wid, batch_size=4)
        except Exception as e:
            results23[idx] = {"error": str(e), "tasks": [], "task_count": 0}

    th1 = threading.Thread(target=_worker, args=(0, "wA"))
    th2 = threading.Thread(target=_worker, args=(1, "wB"))
    th1.start(); th2.start(); th1.join(); th2.join()
    set_a = {t["task_id"] for t in results23[0].get("tasks", [])}
    set_b = {t["task_id"] for t in results23[1].get("tasks", [])}
    check("W23", set_a.isdisjoint(set_b) and len(set_a) + len(set_b) == 4,
          "并发 claim 冲突: A=%s B=%s" % (set_a, set_b))

    # ── W24 release 归还批次 ──
    root24 = _mk_root()
    p24 = WorkbuddyQueueProvider({}, ai_root=root24)
    for i in range(2):
        _submit(p24, "rel%d" % i)
    m24 = claim_batch(root24, worker_id="w1", batch_size=2)
    rep24 = release_batch(root24, m24["batch_id"])
    leases24 = len(glob.glob(os.path.join(root24, "leases", "*.json")))
    check("W24", _count(root24, "queue") == 2 and _count(root24, "processing") == 0
          and leases24 == 0, "release 未归还任务: %s" % rep24)

    # ── status 摘要冒烟 ──
    st = status_summary(root24)
    check("W25", st.get("queue") == 2 and st.get("processing") == 0
          and "expired_leases" in st, "status 摘要异常: %s" % st)

    # ── 清理临时目录 ──
    for d in (root2, root3, root6, root16, root23, root24):
        shutil.rmtree(d, ignore_errors=True)

    print("=" * 64)
    print("RESULT: PASS=%d FAIL=%d" % (total - fails, fails))
    print("=" * 64)
    if fails:
        sys.exit(1)
    print("ALL STAGE 2.5B-1 WORKER PROTOCOL TESTS PASSED")


if __name__ == "__main__":
    main()
