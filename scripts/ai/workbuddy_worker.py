#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 2.5B-1 — WorkBuddy AI 任务领取与交接协议控制器。

职责边界（对应规范五）：
- 只管理文件与状态：claim / lease / heartbeat / ingest / recover / release / status；
- 不直接调用任何 AI 模型（不提供 run-hy3 / call-model 等模型调用命令）；
- 不发起任何网络请求；
- WorkBuddy（内置 Hy3）通过批次目录中的 WORKBUDDY_REQUEST.md 接收任务，
  处理后把结果写入结果文件，再由本控制器 ingest 校验归档。

目录（位于 ai_root，默认 data/ai）：
  queue/ processing/ completed/ failed/ cache/ usage/   —— Stage 2.5A 已建立
  batches/<batch_id>/{manifest.json, WORKBUDDY_REQUEST.md, results.template.json}
  leases/<task_id>.json
  audit/audit_<YYYYMMDD>.jsonl
  locks/claim.lock（全局 claim 锁）
"""

import os
import sys
import json
import time
import argparse
import tempfile
from datetime import datetime, timedelta, timezone

# 允许两种运行方式：python scripts/ai/workbuddy_worker.py（脚本）或包内导入
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from ai.contracts import validate_ai_result  # noqa: E402
from ai.exceptions import TaskStateError  # noqa: E402
from ai.workbuddy_queue_provider import move_task, AI_ROOT  # noqa: E402

DEFAULT_LEASE_MINUTES = 30
MAX_EXTEND_MINUTES = 30
DEFAULT_BATCH_SIZE = 3
_PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}
_LOCK_STALE_SECONDS = 120
_LOCK_WAIT_SECONDS = 10


def _now():
    return datetime.now(timezone.utc)


def _now_iso():
    return _now().isoformat()


def _parse_iso(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def _ensure_dirs(ai_root):
    for d in ("queue", "processing", "completed", "failed", "cache", "usage",
              "batches", "leases", "audit", "locks"):
        os.makedirs(os.path.join(ai_root, d), exist_ok=True)


def _atomic_write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── 审计（合法 JSON Lines；不含密钥/本机路径/正文/Prompt/堆栈） ──

def audit(ai_root, event, **fields):
    _ensure_dirs(ai_root)
    rec = {"ts": _now_iso(), "event": event}
    for k, v in fields.items():
        if v is None:
            continue
        rec[k] = str(v)[:200]  # 只保留短摘要，绝不写入正文/堆栈/路径
    path = os.path.join(ai_root, "audit",
                        "audit_%s.jsonl" % _now().strftime("%Y%m%d"))
    line = json.dumps(rec, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ── 全局 claim 锁 ──

def _acquire_claim_lock(ai_root, wait=_LOCK_WAIT_SECONDS):
    _ensure_dirs(ai_root)
    lock = os.path.join(ai_root, "locks", "claim.lock")
    deadline = time.time() + wait
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json.dumps({"pid": os.getpid(), "at": _now_iso()}))
            return lock
        except FileExistsError:
            # 陈旧锁清理（进程崩溃残留）
            try:
                age = time.time() - os.path.getmtime(lock)
                if age > _LOCK_STALE_SECONDS:
                    os.remove(lock)
                    continue
            except OSError:
                pass
            if time.time() > deadline:
                raise TaskStateError("claim lock busy (timeout)")
            time.sleep(0.05)


def _release_claim_lock(lock):
    try:
        os.remove(lock)
    except OSError:
        pass


# ── 状态摘要 ──

def status_summary(ai_root=AI_ROOT):
    _ensure_dirs(ai_root)
    out = {}
    for st in ("queue", "processing", "completed", "failed"):
        d = os.path.join(ai_root, st)
        out[st] = sum(1 for f in os.listdir(d) if f.endswith(".json"))
    expired = 0
    now = _now()
    lease_dir = os.path.join(ai_root, "leases")
    for fn in os.listdir(lease_dir):
        if not fn.endswith(".json"):
            continue
        try:
            lease = _read_json(os.path.join(lease_dir, fn))
            exp = _parse_iso(lease.get("lease_expires_at"))
            if exp and exp < now:
                expired += 1
        except Exception:
            expired += 1  # 损坏 lease 视为异常
    out["leases"] = sum(1 for f in os.listdir(lease_dir) if f.endswith(".json"))
    out["expired_leases"] = expired
    out["batches"] = sum(1 for d in os.listdir(os.path.join(ai_root, "batches"))
                         if os.path.isdir(os.path.join(ai_root, "batches", d)))
    return out


# ── claim：领取批次 ──

def _list_queue_sorted(ai_root):
    qd = os.path.join(ai_root, "queue")
    tasks = []
    for fn in os.listdir(qd):
        if not fn.endswith(".json"):
            continue
        try:
            obj = _read_json(os.path.join(qd, fn))
        except Exception:
            continue
        tasks.append(obj)
    tasks.sort(key=lambda t: (
        _PRIORITY_ORDER.get(t.get("priority", "normal"), 2),
        str(t.get("created_at", "")),
        str(t.get("task_id", "")),
    ))
    return tasks


def _request_md(manifest):
    lines = [
        "# WORKBUDDY_REQUEST — AI 批次处理说明",
        "",
        "batch_id: `%s`" % manifest["batch_id"],
        "worker_id: `%s`" % manifest["worker_id"],
        "lease_expires_at: `%s`" % manifest["lease_expires_at"],
        "task_count: %d" % manifest["task_count"],
        "",
        "## 必须遵守的规则",
        "",
        "1. 只能处理本批次 manifest.json 中列出的任务，不得处理其他任务；",
        "2. 使用当前 WorkBuddy 内置 Hy3 模型处理，不调用外部 API；",
        "3. 不调用 OpenAI、Anthropic 或任何付费/外部模型接口；",
        "4. 不修改输入事实，不曲解原文含义；",
        "5. 不编造原文中不存在的数据、数字、地名或人名；",
        "6. 每个 task_id 必须且只能产生一个结果对象；",
        "7. 输出必须符合 schemas/ai_result.schema.json（schema_version=1.0）；",
        "8. 处理失败时返回标准 error（code + message），不得静默丢弃任务；",
        "9. 不得直接修改 Canonical、Public 数据或网页文件；",
        "10. 完成后将结果写入本批次目录的结果文件（可从 results.template.json 复制），",
        "    然后由控制器执行 ingest：",
        "    `python scripts/ai/workbuddy_worker.py ingest --batch-id %s --result-file <结果文件>`" % manifest["batch_id"],
        "",
        "## 计量说明",
        "",
        "- 当前 WorkBuddy 内置 Hy3 无可靠 Token 计费接口：",
        "  input_tokens=0 / output_tokens=0 / estimated_cost_usd=0，不得伪造用量。",
        "",
        "## 任务清单",
        "",
    ]
    for t in manifest["tasks"]:
        lines.append("- `%s` type=%s priority=%s attempt=%s" % (
            t.get("task_id"), t.get("task_type"),
            t.get("priority"), t.get("retry_count", 0)))
    return "\n".join(lines) + "\n"


def _results_template(manifest):
    return {
        "batch_id": manifest["batch_id"],
        "worker_id": manifest["worker_id"],
        "completed_at": "",
        "results": [
            {
                "task_id": t["task_id"],
                "schema_version": "1.0",
                "status": "",
                "provider": "workbuddy_queue",
                "model": "hy3",
                "started_at": "",
                "completed_at": "",
                "result": {},
                "error": None,
                "usage": {"input_tokens": 0, "output_tokens": 0,
                          "estimated_cost_usd": 0},
            }
            for t in manifest["tasks"]
        ],
    }


def claim_batch(ai_root=AI_ROOT, worker_id="workbuddy-local",
                batch_size=DEFAULT_BATCH_SIZE,
                lease_minutes=DEFAULT_LEASE_MINUTES, _fail_after=None):
    """领取一批任务：queue -> processing + lease + 批次清单。

    - 全局 claim 锁保证并发安全；
    - 中途失败回滚：已迁移任务返回 queue，已建 lease 删除，不留半成品批次；
    - 空队列正常返回 {"batch_id": None, "task_count": 0, "tasks": []}。
    """
    _ensure_dirs(ai_root)
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    lock = _acquire_claim_lock(ai_root)
    claimed = []       # [(task_dict_after_move)]
    lease_paths = []
    try:
        candidates = _list_queue_sorted(ai_root)[:batch_size]
        if not candidates:
            return {"batch_id": None, "worker_id": worker_id,
                    "task_count": 0, "tasks": []}

        now = _now()
        batch_id = "BATCH_" + now.strftime("%Y%m%dT%H%M%S") + "_" + os.urandom(3).hex()
        expires = (now + timedelta(minutes=lease_minutes)).isoformat()

        try:
            for i, task in enumerate(candidates):
                if _fail_after is not None and i >= _fail_after:
                    raise TaskStateError("injected failure for atomic-rollback test")
                tid = task["task_id"]
                moved = move_task(tid, "queue", "processing", ai_root=ai_root)
                claimed.append(moved)
                lease = {
                    "task_id": tid,
                    "batch_id": batch_id,
                    "worker_id": worker_id,
                    "claimed_at": now.isoformat(),
                    "lease_expires_at": expires,
                    "heartbeat_at": now.isoformat(),
                    "attempt_number": int(moved.get("retry_count", 0)) + 1,
                }
                lp = os.path.join(ai_root, "leases", "%s.json" % tid)
                _atomic_write_json(lp, lease)
                lease_paths.append(lp)
        except Exception:
            # 回滚：删 lease、任务返回 queue
            for lp in lease_paths:
                try:
                    os.remove(lp)
                except OSError:
                    pass
            for t in claimed:
                try:
                    move_task(t["task_id"], "processing", "queue", ai_root=ai_root)
                except Exception:
                    pass
            raise

        manifest = {
            "batch_id": batch_id,
            "worker_id": worker_id,
            "created_at": now.isoformat(),
            "lease_expires_at": expires,
            "task_count": len(claimed),
            "tasks": claimed,
        }
        bdir = os.path.join(ai_root, "batches", batch_id)
        os.makedirs(bdir, exist_ok=True)
        _atomic_write_json(os.path.join(bdir, "manifest.json"), manifest)
        with open(os.path.join(bdir, "WORKBUDDY_REQUEST.md"), "w",
                  encoding="utf-8") as f:
            f.write(_request_md(manifest))
        _atomic_write_json(os.path.join(bdir, "results.template.json"),
                           _results_template(manifest))
        for t in claimed:
            audit(ai_root, "task_claimed", task_id=t["task_id"],
                  batch_id=batch_id, worker_id=worker_id,
                  attempt=int(t.get("retry_count", 0)) + 1)
        return manifest
    finally:
        _release_claim_lock(lock)


# ── heartbeat：续约 ──

def heartbeat_batch(ai_root, batch_id, worker_id,
                    extend_minutes=DEFAULT_LEASE_MINUTES):
    """只允许原 worker 延长租约；单次延长不超过 30 分钟；
    已完成 / 已失败任务不能续约。"""
    _ensure_dirs(ai_root)
    extend_minutes = min(int(extend_minutes), MAX_EXTEND_MINUTES)
    report = {"batch_id": batch_id, "worker_id": worker_id,
              "extended": 0, "rejected": []}
    lease_dir = os.path.join(ai_root, "leases")
    now = _now()
    for fn in sorted(os.listdir(lease_dir)):
        if not fn.endswith(".json"):
            continue
        lp = os.path.join(lease_dir, fn)
        try:
            lease = _read_json(lp)
        except Exception:
            continue
        if lease.get("batch_id") != batch_id:
            continue
        tid = lease.get("task_id")
        if lease.get("worker_id") != worker_id:
            report["rejected"].append({"task_id": tid, "reason": "worker_mismatch"})
            continue
        if not os.path.exists(os.path.join(ai_root, "processing", "%s.json" % tid)):
            report["rejected"].append({"task_id": tid, "reason": "not_processing"})
            continue
        lease["heartbeat_at"] = now.isoformat()
        lease["lease_expires_at"] = (now + timedelta(minutes=extend_minutes)).isoformat()
        _atomic_write_json(lp, lease)
        report["extended"] += 1
        audit(ai_root, "lease_extended", task_id=tid, batch_id=batch_id,
              worker_id=worker_id)
    return report


# ── ingest：接收并校验结果 ──

def ingest_results(ai_root, batch_id, result_file, allow_expired=False):
    """校验批次结果并归档。

    - batch_id / worker_id / 租约 / manifest 归属 / 唯一性 / 契约校验；
    - success -> completed；failed/refused/invalid_output -> failed；
    - 无效结果不影响其他有效结果（任务保持 processing 并记录原因）；
    - 重复 ingest 幂等：已完成任务返回 idempotent_success，不重复写入。
    """
    _ensure_dirs(ai_root)
    report = {"batch_id": batch_id, "accepted": 0, "failed_tasks": 0,
              "rejected": 0, "tasks": []}

    man_path = os.path.join(ai_root, "batches", batch_id, "manifest.json")
    if not os.path.exists(man_path):
        report["error"] = "batch manifest not found: %s" % batch_id
        return report
    manifest = _read_json(man_path)
    manifest_ids = {t["task_id"] for t in manifest.get("tasks", [])}

    try:
        payload = _read_json(result_file)
    except Exception as e:
        report["error"] = "result file unreadable: %s" % type(e).__name__
        return report

    if payload.get("batch_id") != batch_id:
        report["error"] = "batch_id mismatch"
        return report
    if payload.get("worker_id") != manifest.get("worker_id"):
        report["error"] = "worker_id mismatch"
        audit(ai_root, "result_ingested", batch_id=batch_id,
              outcome="rejected_worker_mismatch")
        return report

    now = _now()
    seen = set()
    for res in payload.get("results", []):
        tid = res.get("task_id")
        entry = {"task_id": tid}
        report["tasks"].append(entry)

        if tid in seen:
            entry["outcome"] = "rejected_duplicate_in_file"
            report["rejected"] += 1
            continue
        seen.add(tid)

        if tid not in manifest_ids:
            entry["outcome"] = "rejected_not_in_manifest"
            report["rejected"] += 1
            continue

        comp_path = os.path.join(ai_root, "completed", "%s.json" % tid)
        fail_path = os.path.join(ai_root, "failed", "%s.json" % tid)
        if os.path.exists(comp_path):
            entry["outcome"] = "idempotent_success"
            continue
        if os.path.exists(fail_path):
            entry["outcome"] = "idempotent_failed"
            continue

        # 租约检查
        lp = os.path.join(ai_root, "leases", "%s.json" % tid)
        if os.path.exists(lp):
            lease = _read_json(lp)
            exp = _parse_iso(lease.get("lease_expires_at"))
            if exp and exp < now and not allow_expired:
                entry["outcome"] = "rejected_lease_expired"
                report["rejected"] += 1
                continue

        # 契约校验
        errors = validate_ai_result(res)
        if errors:
            entry["outcome"] = "rejected_invalid_result"
            entry["reasons"] = errors[:5]
            report["rejected"] += 1
            audit(ai_root, "result_ingested", task_id=tid, batch_id=batch_id,
                  outcome="invalid", reason="; ".join(errors[:2]))
            continue

        if not os.path.exists(os.path.join(ai_root, "processing", "%s.json" % tid)):
            entry["outcome"] = "rejected_not_processing"
            report["rejected"] += 1
            continue

        if res["status"] == "success":
            move_task(tid, "processing", "completed", ai_root=ai_root,
                      updates={"ai_result": res})
            entry["outcome"] = "completed"
            report["accepted"] += 1
            audit(ai_root, "result_ingested", task_id=tid, batch_id=batch_id,
                  outcome="success")
            audit(ai_root, "task_completed", task_id=tid, batch_id=batch_id)
        else:
            moved = move_task(tid, "processing", "failed", ai_root=ai_root,
                              updates={"ai_result": res})
            entry["outcome"] = "failed"
            report["failed_tasks"] += 1
            audit(ai_root, "result_ingested", task_id=tid, batch_id=batch_id,
                  outcome=res["status"])
            audit(ai_root, "task_failed", task_id=tid, batch_id=batch_id,
                  code=(res.get("error") or {}).get("code"),
                  retry_count=moved.get("retry_count"))
        try:
            os.remove(lp)
        except OSError:
            pass
    return report


# ── recover-expired：过期租约恢复 ──

def recover_expired(ai_root=AI_ROOT, dry_run=False):
    """扫描过期 lease：retry_count+1 后重新入队或永久失败；不产生新 task_id。"""
    _ensure_dirs(ai_root)
    now = _now()
    report = {"scanned": 0, "requeued": [], "permanently_failed": [],
              "skipped": [], "dry_run": bool(dry_run)}
    lease_dir = os.path.join(ai_root, "leases")
    for fn in sorted(os.listdir(lease_dir)):
        if not fn.endswith(".json"):
            continue
        lp = os.path.join(lease_dir, fn)
        try:
            lease = _read_json(lp)
        except Exception:
            report["skipped"].append({"lease": fn, "reason": "unreadable"})
            continue
        report["scanned"] += 1
        exp = _parse_iso(lease.get("lease_expires_at"))
        if exp is None or exp >= now:
            continue
        tid = lease.get("task_id")
        proc_path = os.path.join(ai_root, "processing", "%s.json" % tid)
        if not os.path.exists(proc_path):
            # 任务已不在 processing（已完成/失败）：仅清理 lease
            if not dry_run:
                try:
                    os.remove(lp)
                except OSError:
                    pass
            report["skipped"].append({"task_id": tid, "reason": "not_processing"})
            continue
        task = _read_json(proc_path)
        rc = int(task.get("retry_count", 0))
        mr = int(task.get("max_retries", 0))
        if rc < mr:
            if not dry_run:
                move_task(tid, "processing", "queue", ai_root=ai_root,
                          updates={"retry_count": rc + 1})
                try:
                    os.remove(lp)
                except OSError:
                    pass
                audit(ai_root, "task_requeued", task_id=tid,
                      batch_id=lease.get("batch_id"), retry_count=rc + 1)
            report["requeued"].append(tid)
        else:
            if not dry_run:
                move_task(tid, "processing", "failed", ai_root=ai_root)
                # move_task 会把 status 规范为 failed；永久失败需要再标记
                fp = os.path.join(ai_root, "failed", "%s.json" % tid)
                obj = _read_json(fp)
                obj["status"] = "permanently_failed"
                _atomic_write_json(fp, obj)
                try:
                    os.remove(lp)
                except OSError:
                    pass
                audit(ai_root, "task_permanently_failed", task_id=tid,
                      batch_id=lease.get("batch_id"), retry_count=rc)
            report["permanently_failed"].append(tid)
    return report


# ── release：归还批次 ──

def release_batch(ai_root, batch_id):
    """把批次中仍在 processing 的任务归还 queue（不增加 retry），删除对应 lease。"""
    _ensure_dirs(ai_root)
    report = {"batch_id": batch_id, "released": [], "skipped": []}
    lease_dir = os.path.join(ai_root, "leases")
    for fn in sorted(os.listdir(lease_dir)):
        if not fn.endswith(".json"):
            continue
        lp = os.path.join(lease_dir, fn)
        try:
            lease = _read_json(lp)
        except Exception:
            continue
        if lease.get("batch_id") != batch_id:
            continue
        tid = lease.get("task_id")
        if os.path.exists(os.path.join(ai_root, "processing", "%s.json" % tid)):
            move_task(tid, "processing", "queue", ai_root=ai_root)
            report["released"].append(tid)
        else:
            report["skipped"].append(tid)
        try:
            os.remove(lp)
        except OSError:
            pass
    audit(ai_root, "batch_released", batch_id=batch_id,
          released=len(report["released"]))
    return report


# ── CLI ──

def _print(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="ASIP Stage 2.5B-1 WorkBuddy worker controller "
                    "(file/state management only; never calls AI)")
    ap.add_argument("--ai-root", default=AI_ROOT,
                    help="AI root dir (default: data/ai)")
    # 子命令也可接受 --ai-root，支持 ``<cmd> --ai-root <dir>`` 调用顺序
    # 用 SUPPRESS 避免子解析器默认值覆盖顶层已解析的值
    pp = argparse.ArgumentParser(add_help=False)
    pp.add_argument("--ai-root", default=argparse.SUPPRESS,
                    help="AI root dir (default: data/ai)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", parents=[pp])

    c = sub.add_parser("claim", parents=[pp])
    c.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    c.add_argument("--worker-id", default="workbuddy-local")
    c.add_argument("--lease-minutes", type=int, default=DEFAULT_LEASE_MINUTES)

    i = sub.add_parser("ingest", parents=[pp])
    i.add_argument("--batch-id", required=True)
    i.add_argument("--result-file", required=True)
    i.add_argument("--allow-expired", action="store_true",
                   help="accept results for a just-expired lease")

    r = sub.add_parser("recover-expired", parents=[pp])
    r.add_argument("--dry-run", action="store_true")

    rel = sub.add_parser("release", parents=[pp])
    rel.add_argument("--batch-id", required=True)

    h = sub.add_parser("heartbeat", parents=[pp])
    h.add_argument("--batch-id", required=True)
    h.add_argument("--worker-id", required=True)
    h.add_argument("--extend-minutes", type=int, default=DEFAULT_LEASE_MINUTES)

    args = ap.parse_args(argv)
    root = args.ai_root

    if args.cmd == "status":
        _print(status_summary(root))
    elif args.cmd == "claim":
        _print(claim_batch(root, worker_id=args.worker_id,
                           batch_size=args.batch_size,
                           lease_minutes=args.lease_minutes))
    elif args.cmd == "ingest":
        _print(ingest_results(root, args.batch_id, args.result_file,
                              allow_expired=args.allow_expired))
    elif args.cmd == "recover-expired":
        _print(recover_expired(root, dry_run=args.dry_run))
    elif args.cmd == "release":
        _print(release_batch(root, args.batch_id))
    elif args.cmd == "heartbeat":
        _print(heartbeat_batch(root, args.batch_id, args.worker_id,
                               extend_minutes=args.extend_minutes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
