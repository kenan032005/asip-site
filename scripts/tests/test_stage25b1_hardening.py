#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASIP Stage 2.5B-1H — Worker协议最终加固验收测试（TDD）。

在修改实现之前，本文件必然失败（ImportError / 断言失败）；实现加固后全部通过。

覆盖（对应规范三/四至十）：
  H1   租约缺失时 ingest 失败关闭
  H2   lease.batch_id 不匹配时拒绝
  H3   lease.worker_id 不匹配时拒绝
  H4   lease 文件损坏或不可解析时拒绝
  H5   已过期且未提供 allow_expired 时拒绝
  H6   --allow-expired 仅允许宽限期(10min)内的结果
  H7   超过宽限期的结果即使带 --allow-expired 也拒绝
  H8   provider 与 manifest.expected_provider 不一致时拒绝
  H9   model 与 manifest.expected_model 不一致时拒绝
  H10  结果文件缺少批次中的任务时明确报告
  H11  批次文件写入失败时 claim 完整回滚
  H12  audit 中的本机路径、用户名和疑似密钥被脱敏
  H13  lease_minutes 为 0 或负数时拒绝
  H14  heartbeat extend_minutes 为 0、负数或 >30 时拒绝
  H15  Stage 2.5B-1 原有 26 项测试继续通过
"""

import os, sys, json, time, glob, shutil, getpass, tempfile, subprocess
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

from pipeline_core import sanitize_log_value  # noqa: E402
from ai.contracts import new_ai_task  # noqa: E402
from ai.workbuddy_queue_provider import WorkbuddyQueueProvider, move_task  # noqa: E402
from ai.workbuddy_worker import (  # noqa: E402
    claim_batch, ingest_results, recover_expired,
    heartbeat_batch, release_batch, status_summary,
    DEFAULT_LEASE_MINUTES, audit, _now, _parse_iso, _read_json, _ensure_dirs,
)

PY = sys.executable


def _mk_root():
    return tempfile.mkdtemp(prefix="s25b1h_")


def _submit(provider, idx, priority="normal", created_at=None, max_retries=2):
    t = new_ai_task("article_analysis", {"id": "mock-h%d" % idx},
                    "h%d" % idx, "p1", "o1",
                    priority=priority, created_at=created_at, max_retries=max_retries)
    return provider.submit_task(t)


def _count(ai_root, state):
    d = os.path.join(ai_root, state)
    if not os.path.isdir(d):
        return 0
    return sum(1 for f in os.listdir(d) if f.endswith(".json"))


def _mk_result(task_id, status="success", **over):
    r = {
        "task_id": task_id, "schema_version": "1.0", "status": status,
        "provider": "workbuddy_queue", "model": "hy3",
        "started_at": "2026-07-31T04:00:00+00:00",
        "completed_at": "2026-07-31T04:00:05+00:00",
        "result": {"summary": "mock"} if status == "success" else {},
        "error": None if status == "success" else {"code": "E_MOCK", "message": "mock"},
        "usage": {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0},
    }
    r.update(over)
    return r


def _write_result_file(ai_root, batch_id, worker_id, results):
    payload = {"batch_id": batch_id, "worker_id": worker_id,
               "completed_at": datetime.now(timezone.utc).isoformat(),
               "results": results}
    p = os.path.join(ai_root, "batches", batch_id, "results.submit.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return p


class H:
    """Harness: 提交 n 个任务 → claim → 返回 root/harness。"""
    def __init__(self, count=3, priority="normal", worker_id="wh",
                 batch_size=None, lease_minutes=DEFAULT_LEASE_MINUTES):
        if batch_size is None:
            batch_size = count
        self.root = _mk_root()
        self.provider = WorkbuddyQueueProvider({}, ai_root=self.root)
        for i in range(count):
            _submit(self.provider, i, priority=priority)
        self.claimed = claim_batch(self.root, worker_id=worker_id,
                                   batch_size=batch_size,
                                   lease_minutes=lease_minutes)
        self.batch_id = self.claimed["batch_id"]
        self.manifest = _read_json(os.path.join(
            self.root, "batches", self.batch_id, "manifest.json"))
        self.tasks = self.claimed["tasks"]

    def ingest(self, results_list, allow_expired=False, result_file=None):
        if result_file is None:
            result_file = _write_result_file(
                self.root, self.batch_id, self.manifest["worker_id"], results_list)
        return ingest_results(self.root, self.batch_id, result_file,
                              allow_expired=allow_expired)

    def rm_lease(self, task_id):
        p = os.path.join(self.root, "leases", "%s.json" % task_id)
        if os.path.exists(p):
            os.remove(p)

    def set_lease(self, task_id, overrides):
        p = os.path.join(self.root, "leases", "%s.json" % task_id)
        d = _read_json(p)
        d.update(overrides)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f)

    def corrupt_lease(self, task_id):
        p = os.path.join(self.root, "leases", "%s.json" % task_id)
        with open(p, "w", encoding="utf-8") as f:
            f.write("{not valid json")

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


def main():
    total, fails = 0, 0

    def check(name, ok, detail=""):
        nonlocal total, fails
        total += 1
        status = "PASS" if ok else "FAIL"
        print("  [%s] %s" % (status, name))
        if not ok:
            fails += 1
            print("       %s" % detail)

    user = getpass.getuser()

    # ═══ H1: 租约缺失时 ingest 失败关闭 ═══
    print("\n=== H1: missing lease ===")
    h1 = H(1)
    tid1 = h1.tasks[0]["task_id"]
    h1.rm_lease(tid1)
    r = h1.ingest([_mk_result(tid1)])
    outcomes = [e.get("outcome", "") for e in r.get("tasks", [])]
    rejected = any("rejected" in o or o == "rejected_lease_missing" for o in outcomes)
    check("H1", rejected and r.get("accepted", 0) == 0,
          "missing lease rejected=%s accepted=%d outcomes=%s" % (
              rejected, r.get("accepted", 0), outcomes))
    h1.cleanup()

    # ═══ H2: lease.batch_id 不匹配 ═══
    print("\n=== H2: lease batch_id mismatch ===")
    h2 = H(1)
    tid2 = h2.tasks[0]["task_id"]
    h2.set_lease(tid2, {"batch_id": "BATCH_WRONG_XYZ"})
    r2 = h2.ingest([_mk_result(tid2)])
    rejected2 = [e for e in r2.get("tasks", []) if "rejected" in e.get("outcome", "")]
    check("H2", len(rejected2) >= 1 and r2.get("accepted", 0) == 0,
          "batch_id mismatch rejected=%d accepted=%d" % (
              len(rejected2), r2.get("accepted", 0)))
    h2.cleanup()

    # ═══ H3: lease.worker_id 不匹配 ═══
    print("\n=== H3: lease worker_id mismatch ===")
    h3 = H(1)
    tid3 = h3.tasks[0]["task_id"]
    h3.set_lease(tid3, {"worker_id": "attacker-w"})
    r3 = h3.ingest([_mk_result(tid3)])
    rejected3 = [e for e in r3.get("tasks", []) if "rejected" in e.get("outcome", "")]
    check("H3", len(rejected3) >= 1 and r3.get("accepted", 0) == 0,
          "worker_id mismatch rejected=%d accepted=%d" % (
              len(rejected3), r3.get("accepted", 0)))
    h3.cleanup()

    # ═══ H4: lease 损坏 ═══
    print("\n=== H4: corrupt lease ===")
    h4 = H(1)
    tid4 = h4.tasks[0]["task_id"]
    h4.corrupt_lease(tid4)
    r4 = h4.ingest([_mk_result(tid4)])
    rejected4 = [e for e in r4.get("tasks", []) if "rejected" in e.get("outcome", "")]
    check("H4", len(rejected4) >= 1 and r4.get("accepted", 0) == 0,
          "corrupt lease rejected=%d accepted=%d" % (
              len(rejected4), r4.get("accepted", 0)))
    h4.cleanup()

    # ═══ H5: 过期租约 + 无 allow_expired → 拒绝 ═══
    print("\n=== H5: expired lease without allow_expired ===")
    h5 = H(1)
    tid5 = h5.tasks[0]["task_id"]
    past = (_now() - timedelta(hours=2)).isoformat()
    h5.set_lease(tid5, {"lease_expires_at": past})
    r5 = h5.ingest([_mk_result(tid5)])
    rejected5 = [e for e in r5.get("tasks", []) if "rejected" in e.get("outcome", "")]
    check("H5", len(rejected5) >= 1 and r5.get("accepted", 0) == 0,
          "expired rejected=%d accepted=%d" % (len(rejected5), r5.get("accepted", 0)))
    h5.cleanup()

    # ═══ H6: allow_expired 在宽限期内 (5min) → 通过 ═══
    print("\n=== H6: allow_expired within grace (5 min ago) ===")
    h6 = H(1)
    tid6 = h6.tasks[0]["task_id"]
    recent = (_now() - timedelta(minutes=5)).isoformat()
    h6.set_lease(tid6, {"lease_expires_at": recent})
    r6 = h6.ingest([_mk_result(tid6)], allow_expired=True)
    check("H6", r6.get("accepted") == 1,
          "within grace accepted=%d" % r6.get("accepted"))
    h6.cleanup()

    # ═══ H7: allow_expired 超过宽限期 (15min) → 拒绝 ═══
    print("\n=== H7: allow_expired beyond grace (15 min) ===")
    h7 = H(1)
    tid7 = h7.tasks[0]["task_id"]
    far = (_now() - timedelta(minutes=15)).isoformat()
    h7.set_lease(tid7, {"lease_expires_at": far})
    r7 = h7.ingest([_mk_result(tid7)], allow_expired=True)
    rejected7 = [e for e in r7.get("tasks", []) if "rejected" in e.get("outcome", "")]
    check("H7", len(rejected7) >= 1 and r7.get("accepted", 0) == 0,
          "beyond grace rejected=%d accepted=%d" % (
              len(rejected7), r7.get("accepted", 0)))
    h7.cleanup()

    # ═══ H8: provider 不匹配 ═══
    print("\n=== H8: provider mismatch ===")
    h8 = H(1)
    tid8 = h8.tasks[0]["task_id"]
    r8 = h8.ingest([_mk_result(tid8, provider="openai")])
    rejected8 = [e for e in r8.get("tasks", []) if "rejected" in e.get("outcome", "")]
    check("H8", len(rejected8) >= 1 and r8.get("accepted", 0) == 0,
          "provider mismatch rejected=%d accepted=%d" % (
              len(rejected8), r8.get("accepted", 0)))
    h8.cleanup()

    # ═══ H9: model 不匹配 ═══
    print("\n=== H9: model mismatch ===")
    h9 = H(1)
    tid9 = h9.tasks[0]["task_id"]
    r9 = h9.ingest([_mk_result(tid9, model="gpt-4")])
    rejected9 = [e for e in r9.get("tasks", []) if "rejected" in e.get("outcome", "")]
    check("H9", len(rejected9) >= 1 and r9.get("accepted", 0) == 0,
          "model mismatch rejected=%d accepted=%d" % (
              len(rejected9), r9.get("accepted", 0)))
    h9.cleanup()

    # ═══ H10: missing_task_ids + batch_complete ═══
    print("\n=== H10: missing tasks report ===")
    h10 = H(3)
    tids = [t["task_id"] for t in h10.tasks]
    # 只提交 2/3
    r10 = h10.ingest([_mk_result(tids[0]), _mk_result(tids[1])])
    missing = r10.get("missing_task_ids", [])
    bc = r10.get("batch_complete", None)
    mc = r10.get("manifest_task_count", 0)
    sc = r10.get("submitted_result_count", 0)
    check("H10", mc == 3 and sc == 2
          and len(missing) == 1 and tids[2] in missing
          and bc is False,
          "manifest=%d submitted=%d missing=%s batch_complete=%s" % (mc, sc, missing, bc))
    h10.cleanup()

    # ═══ H11: 批次文件写入失败回滚 (3 种) ═══
    # 要求: claim_batch 支持 _fail_steps 参数注入故障点
    print("\n=== H11: batch write rollback ===")
    h11_ok = True
    h11_detail = ""
    for fail_step in ("manifest", "request_md", "template"):
        root11 = _mk_root()
        prov11 = WorkbuddyQueueProvider({}, ai_root=root11)
        for i in range(2):
            _submit(prov11, i)
        try:
            c = claim_batch(root11, worker_id="wh", batch_size=2,
                            lease_minutes=DEFAULT_LEASE_MINUTES,
                            _fail_steps={fail_step})
        except Exception:
            c = {"batch_id": None, "task_count": 0, "tasks": []}
        q = _count(root11, "queue")
        p = _count(root11, "processing")
        l = _count(root11, "leases")
        b = len(glob.glob(os.path.join(root11, "batches", "*")))
        ok = (c.get("batch_id") is None and q == 2
              and p == 0 and l == 0 and b == 0)
        if not ok:
            h11_ok = False
            h11_detail += "%s rollback failed (q=%d p=%d l=%d b=%d); " % (
                fail_step, q, p, l, b)
        shutil.rmtree(root11, ignore_errors=True)
    check("H11", h11_ok, h11_detail)

    # ═══ H12: audit 脱敏 ═══
    print("\n=== H12: audit sanitization ===")
    h12 = H(1)
    tid12 = h12.tasks[0]["task_id"]
    h12.ingest([_mk_result(tid12)])
    h12.ingest([_mk_result(tid12)])  # idempotent 触发更多审计事件
    bad = []
    markers = ["c:\\users", "/users/", "/home/", "kenan",
               "WorkBuddy", "Bearer ", "sk-", "api_key",
               "password", "secret", "token"]
    for f in glob.glob(os.path.join(h12.root, "audit", "audit_*.jsonl")):
        with open(f, encoding="utf-8", errors="ignore") as fh:
            for ln, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    bad.append("%s:%d not JSON" % (os.path.basename(f), ln))
                    continue
                s = json.dumps(obj, ensure_ascii=False).lower()
                for m in markers:
                    if m.lower() in s:
                        bad.append("%s:%d leak=%s" % (os.path.basename(f), ln, m))
    check("H12", len(bad) == 0, "audit leaks: %s" % (bad[:5] if bad else "(none)"))
    h12.cleanup()

    # ═══ H13: lease_minutes 边界 ═══
    print("\n=== H13: lease_minutes boundary ===")
    h13_ok = True
    h13_detail = ""
    for lm in (0, -1, -999):
        root13 = _mk_root()
        prov13 = WorkbuddyQueueProvider({}, ai_root=root13)
        _submit(prov13, 0)
        try:
            c = claim_batch(root13, worker_id="wh", batch_size=1, lease_minutes=lm)
            if c.get("batch_id") is not None:
                h13_ok = False
                h13_detail += "lease_minutes=%d accepted; " % lm
        except (ValueError, AssertionError):
            pass  # 正确拒绝
        except Exception as e:
            h13_ok = False
            h13_detail += "lease_minutes=%d threw %s; " % (lm, type(e).__name__)
        shutil.rmtree(root13, ignore_errors=True)
    check("H13", h13_ok, h13_detail)

    # ═══ H14: heartbeat extend_minutes 边界 ═══
    print("\n=== H14: heartbeat extend_minutes boundary ===")
    h14 = H(1)
    bid14 = h14.batch_id
    h14_ok = True
    h14_detail = ""
    for em in (0, -1, 31, 999):
        try:
            r = heartbeat_batch(h14.root, bid14, "wh", extend_minutes=em)
            extended = r.get("extended", 0)
            if extended > 0:
                h14_ok = False
                h14_detail += "extend_minutes=%d accepted (extended=%d); " % (em, extended)
        except (ValueError, AssertionError):
            pass  # 正确拒绝
        except Exception as e:
            h14_ok = False
            h14_detail += "extend_minutes=%d threw %s; " % (em, type(e).__name__)
    h14.cleanup()
    check("H14", h14_ok, h14_detail)

    # ═══ H15: 2.5B-1 回归 ═══
    print("\n=== H15: Stage 2.5B-1 regression ===")
    h15_ok = True
    h15_detail = ""
    tf = "test_stage25b1_worker_protocol.py"
    r = subprocess.run([PY, os.path.join(SCRIPTS, "tests", tf)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or "FAIL=0" not in r.stdout:
        h15_ok = False
        h15_detail = "%s rc=%d stdout_tail=%s" % (
            tf, r.returncode, (r.stdout + r.stderr)[-200:])
    check("H15", h15_ok, h15_detail)

    # ── 汇总 ──
    print("\n" + "=" * 64)
    print("RESULT: PASS=%d FAIL=%d" % (total - fails, fails))
    print("=" * 64)
    if fails:
        sys.exit(1)
    print("ALL STAGE 2.5B-1H HARDENING TESTS PASSED")


if __name__ == "__main__":
    main()
