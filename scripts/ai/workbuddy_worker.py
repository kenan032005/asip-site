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
import re
import json
import shutil
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
from pipeline_core import sanitize_log_value  # noqa: E402   # 2.5B-1H: 审计脱敏

DEFAULT_LEASE_MINUTES = 30
MAX_EXTEND_MINUTES = 30
DEFAULT_BATCH_SIZE = 3
MIN_BATCH_SIZE = 1
MAX_BATCH_SIZE = 20
MIN_LEASE_MINUTES = 1
EXPIRED_GRACE_SECONDS = 600  # 10 minutes
_PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}
_LOCK_STALE_SECONDS = 120
_LOCK_WAIT_SECONDS = 10
_WORKER_ID_RE = re.compile(r'^[a-zA-Z0-9._-]{1,100}$')


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
        # 2.5B-1H：先脱敏（去除本机路径/用户名/密钥），再截断，最后写入
        try:
            clean = sanitize_log_value(v)
            rec[k] = str(clean)[:200]
        except Exception:
            rec[k] = "<redacted>"
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
    corrupt = 0
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
            corrupt += 1  # 2.5B-1H：损坏 lease 标记为 corrupt 而非自动计为过期
    out["leases"] = sum(1 for f in os.listdir(lease_dir) if f.endswith(".json"))
    out["expired_leases"] = expired
    out["corrupt_leases"] = corrupt
    out["batches"] = sum(1 for d in os.listdir(os.path.join(ai_root, "batches"))
                         if os.path.isdir(os.path.join(ai_root, "batches", d)))
    return out


# ── 2.5B-1H: 统一租约校验 ──

def validate_active_lease(ai_root, task_id, batch_id, worker_id,
                          now=None, allow_expired=False,
                          grace_seconds=EXPIRED_GRACE_SECONDS):
    """验证 task_id 的属性/有效/未过期租约。

    返回 (ok, rejection_outcome, reasons)：
      - ok: bool — 是否通过所有检查
      - rejection_outcome: str — 拒绝原因标签（ok 时为 ""）
      - reasons: list — 拒绝原因短摘要（ok 时为 []）

    规则（规范四）：
      1. 租约文件必须存在；
      2. 必须是合法 JSON；
      3. lease.task_id == task_id；
      4. lease.batch_id == batch_id；
      5. lease.worker_id == worker_id；
      6. 未过期才正常接收；
      7. allow_expired 时仅允许过期不超过 grace_seconds；
      8. 超过宽限期必须拒绝。

    不检查 task 是否在 processing/completed/failed — 由调用方处理幂等。
    """
    if now is None:
        now = _now()
    lp = os.path.join(ai_root, "leases", "%s.json" % task_id)

    # 1. 租约文件必须存在
    if not os.path.exists(lp):
        return (False, "rejected_lease_missing",
                ["no lease file found for %s" % task_id])

    # 2. 必须是合法 JSON
    try:
        lease = _read_json(lp)
    except Exception as e:
        return (False, "rejected_lease_corrupt",
                ["lease file corrupt: %s" % type(e).__name__])

    # 3. lease.task_id == task_id
    ltid = lease.get("task_id")
    if ltid != task_id:
        return (False, "rejected_lease_task_mismatch",
                ["lease task_id %s != result %s" % (ltid, task_id)])

    # 4. lease.batch_id == batch_id
    lbid = lease.get("batch_id")
    if lbid != batch_id:
        return (False, "rejected_lease_batch_mismatch",
                ["lease batch %s != request %s" % (lbid, batch_id)])

    # 5. lease.worker_id == worker_id
    lwid = lease.get("worker_id")
    if lwid != worker_id:
        return (False, "rejected_lease_worker_mismatch",
                ["lease worker %s != request %s" % (lwid, worker_id)])

    # 6. 租约过期检查
    exp = _parse_iso(lease.get("lease_expires_at"))
    if exp is None:
        return (False, "rejected_lease_invalid_expiry",
                ["lease has no valid lease_expires_at"])

    if exp < now:
        if not allow_expired:
            return (False, "rejected_lease_expired",
                    ["lease expired at %s" % str(exp)])
        # allow_expired: 仅允许宽限期内的
        age = (now - exp).total_seconds()
        if age > grace_seconds:
            return (False, "rejected_lease_expired_beyond_grace",
                    ["lease expired %d s ago (grace=%d s)" % (int(age), grace_seconds)])

    return (True, "", [])


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
    exp_prov = manifest.get("expected_provider", "workbuddy_queue")
    exp_model = manifest.get("expected_model", "hy3")
    return {
        "batch_id": manifest["batch_id"],
        "worker_id": manifest["worker_id"],
        "completed_at": "",
        "results": [
            {
                "task_id": t["task_id"],
                "schema_version": "1.0",
                "status": "",
                "provider": exp_prov,
                "model": exp_model,
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
                lease_minutes=DEFAULT_LEASE_MINUTES,
                expected_provider="workbuddy_queue",
                expected_model="hy3",
                _fail_after=None, _fail_steps=None):
    """领取一批任务：queue -> processing + lease + 批次清单。

    - 全局 claim 锁保证并发安全；
    - 批次文件写入使用临时目录 + 原子 rename（事务性）；
    - _fail_steps 仅测试用：注入指定步骤故障以验证回滚；
    - 空队列正常返回 {"batch_id": None, "task_count": 0, "tasks": []}。
    """
    _fail_steps = _fail_steps or set()
    _ensure_dirs(ai_root)

    # 2.5B-1H 参数边界校验
    if not isinstance(batch_size, int) or batch_size < MIN_BATCH_SIZE or batch_size > MAX_BATCH_SIZE:
        raise ValueError("batch_size must be %d–%d, got %s" % (MIN_BATCH_SIZE, MAX_BATCH_SIZE, batch_size))
    if not isinstance(lease_minutes, int) or lease_minutes < MIN_LEASE_MINUTES or lease_minutes > DEFAULT_LEASE_MINUTES:
        raise ValueError("lease_minutes must be %d–%d, got %s" % (MIN_LEASE_MINUTES, DEFAULT_LEASE_MINUTES, lease_minutes))
    if not worker_id or not isinstance(worker_id, str) or not _WORKER_ID_RE.match(worker_id):
        raise ValueError("worker_id must be 1–100 chars [a-zA-Z0-9._-], got %r" % (worker_id[:120] if worker_id else worker_id))

    lock = _acquire_claim_lock(ai_root)
    claimed = []
    lease_paths = []
    temp_bdir = None
    try:
        candidates = _list_queue_sorted(ai_root)[:batch_size]
        if not candidates:
            return {"batch_id": None, "worker_id": worker_id,
                    "task_count": 0, "tasks": []}

        now = _now()
        batch_id = "BATCH_" + now.strftime("%Y%m%dT%H%M%S") + "_" + os.urandom(3).hex()
        expires = (now + timedelta(minutes=lease_minutes)).isoformat()

        # Phase 1: 领取并迁移任务
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
            _rollback_claim(claimed, lease_paths, ai_root)
            raise

        # Phase 2: 构建 manifest
        manifest = {
            "batch_id": batch_id,
            "worker_id": worker_id,
            "created_at": now.isoformat(),
            "lease_expires_at": expires,
            "task_count": len(claimed),
            "expected_provider": expected_provider,
            "expected_model": expected_model,
            "tasks": claimed,
        }

        # Phase 3: 写入批次文件（临时目录 → 原子 rename）
        bdir = os.path.join(ai_root, "batches", batch_id)
        temp_bdir = os.path.join(ai_root, "batches", ".tmp_" + batch_id)
        os.makedirs(temp_bdir, exist_ok=True)
        try:
            if "manifest" in _fail_steps:
                raise TaskStateError("injected failure: manifest write")

            _atomic_write_json(os.path.join(temp_bdir, "manifest.json"), manifest)

            if "request_md" in _fail_steps:
                raise TaskStateError("injected failure: WORKBUDDY_REQUEST write")

            with open(os.path.join(temp_bdir, "WORKBUDDY_REQUEST.md"), "w",
                      encoding="utf-8") as f:
                f.write(_request_md(manifest))

            if "template" in _fail_steps:
                raise TaskStateError("injected failure: results template write")

            _atomic_write_json(os.path.join(temp_bdir, "results.template.json"),
                               _results_template(manifest))

            # 验证三个文件均存在
            for fname in ("manifest.json", "WORKBUDDY_REQUEST.md", "results.template.json"):
                if not os.path.exists(os.path.join(temp_bdir, fname)):
                    raise TaskStateError("batch file missing after write: %s" % fname)

            # 原子 rename
            os.rename(temp_bdir, bdir)
            temp_bdir = None  # rename 成功，不再执行 finally 清理
        except Exception:
            # 批次文件写入失败 → 回滚所有已建立状态
            _rollback_claim(claimed, lease_paths, ai_root)
            if temp_bdir and os.path.isdir(temp_bdir):
                shutil.rmtree(temp_bdir, ignore_errors=True)
            raise

        # Phase 4: 审计
        for t in claimed:
            audit(ai_root, "task_claimed", task_id=t["task_id"],
                  batch_id=batch_id, worker_id=worker_id,
                  attempt=int(t.get("retry_count", 0)) + 1)
        return manifest
    finally:
        _release_claim_lock(lock)
        if temp_bdir and os.path.isdir(temp_bdir):
            shutil.rmtree(temp_bdir, ignore_errors=True)


def _rollback_claim(claimed, lease_paths, ai_root):
    """claim 中途失败时回滚：删 lease、任务返回 queue。"""
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


# ── heartbeat：续约 ──

def heartbeat_batch(ai_root, batch_id, worker_id,
                    extend_minutes=DEFAULT_LEASE_MINUTES):
    """只允许原 worker 延长租约；单次延长 1–30 分钟；
    已完成/已失败/过期超宽限期的任务不能续约；非法值明确报错。"""
    _ensure_dirs(ai_root)

    # 2.5B-1H：明确拒绝非法值，不得静默 clamp
    try:
        em = int(extend_minutes)
    except (TypeError, ValueError):
        raise ValueError("extend_minutes must be an integer, got %r" % extend_minutes)
    if em < 1 or em > MAX_EXTEND_MINUTES:
        raise ValueError("extend_minutes must be 1–%d, got %d" % (MAX_EXTEND_MINUTES, em))

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
        # 2.5B-1H：检查任务是否仍在 processing
        if not os.path.exists(os.path.join(ai_root, "processing", "%s.json" % tid)):
            report["rejected"].append({"task_id": tid, "reason": "not_processing"})
            continue
        # 2.5B-1H：过期超过宽限期的租约不得续约
        exp = _parse_iso(lease.get("lease_expires_at"))
        if exp is not None and exp < now:
            age = (now - exp).total_seconds()
            if age > EXPIRED_GRACE_SECONDS:
                report["rejected"].append({"task_id": tid,
                    "reason": "lease_expired_beyond_grace"})
                continue
        lease["heartbeat_at"] = now.isoformat()
        lease["lease_expires_at"] = (now + timedelta(minutes=em)).isoformat()
        _atomic_write_json(lp, lease)
        report["extended"] += 1
        audit(ai_root, "lease_extended", task_id=tid, batch_id=batch_id,
              worker_id=worker_id)
    return report


# ── ingest：接收并校验结果 ──

def ingest_results(ai_root, batch_id, result_file, allow_expired=False):
    """校验批次结果并归档（2.5B-1H 加固版）。

    - 统一租约校验（validate_active_lease）；
    - provider/model 与 manifest.expected_* 匹配检查；
    - 批次完整性报告（missing_task_ids / batch_complete）；
    - success -> completed；failed/refused/invalid_output -> failed；
    - 无效结果不影响同批其他有效结果；
    - 重复 ingest 幂等。
    """
    _ensure_dirs(ai_root)
    report = {
        "batch_id": batch_id,
        "accepted": 0,
        "failed_tasks": 0,
        "rejected": 0,
        "tasks": [],
        "manifest_task_count": 0,
        "submitted_result_count": 0,
        "accepted_task_ids": [],
        "rejected_task_ids": [],
        "missing_task_ids": [],
        "batch_complete": True,
    }

    man_path = os.path.join(ai_root, "batches", batch_id, "manifest.json")
    if not os.path.exists(man_path):
        report["error"] = "batch manifest not found: %s" % batch_id
        return report
    manifest = _read_json(man_path)
    manifest_ids = {t["task_id"] for t in manifest.get("tasks", [])}
    manifest_worker = manifest.get("worker_id", "")
    exp_provider = manifest.get("expected_provider", "workbuddy_queue")
    exp_model = manifest.get("expected_model", "hy3")
    report["manifest_task_count"] = len(manifest_ids)

    try:
        payload = _read_json(result_file)
    except Exception as e:
        report["error"] = "result file unreadable: %s" % type(e).__name__
        return report

    if payload.get("batch_id") != batch_id:
        report["error"] = "batch_id mismatch"
        return report
    if payload.get("worker_id") != manifest_worker:
        report["error"] = "worker_id mismatch"
        audit(ai_root, "result_ingested", batch_id=batch_id,
              outcome="rejected_worker_mismatch")
        return report

    results = payload.get("results")
    if not isinstance(results, list):
        report["error"] = "results field must be an array"
        return report

    now = _now()
    seen = set()
    for res in results:
        # 2.5B-2A：非对象结果条目（字符串/数字/None 等）必须被优雅拒绝，
        # 不得抛出 AttributeError 中断同批其他结果的处理。
        if not isinstance(res, dict):
            entry = {"task_id": None,
                     "outcome": "rejected_invalid_result_type",
                     "reasons": ["result entry is not an object: %s"
                                 % type(res).__name__]}
            report["tasks"].append(entry)
            report["rejected"] += 1
            report["rejected_task_ids"].append(None)
            audit(ai_root, "result_ingested", batch_id=batch_id,
                  outcome="invalid_result_type",
                  reason=type(res).__name__)
            continue
        tid = res.get("task_id")
        entry = {"task_id": tid}
        report["tasks"].append(entry)

        if tid in seen:
            entry["outcome"] = "rejected_duplicate_in_file"
            report["rejected"] += 1
            report["rejected_task_ids"].append(tid)
            continue
        seen.add(tid)

        if tid not in manifest_ids:
            entry["outcome"] = "rejected_not_in_manifest"
            entry["reasons"] = ["task_id not found in manifest %s" % batch_id]
            report["rejected"] += 1
            report["rejected_task_ids"].append(tid)
            continue

        # 幂等检查
        comp_path = os.path.join(ai_root, "completed", "%s.json" % tid)
        fail_path = os.path.join(ai_root, "failed", "%s.json" % tid)
        if os.path.exists(comp_path):
            entry["outcome"] = "idempotent_success"
            continue
        if os.path.exists(fail_path):
            entry["outcome"] = "idempotent_failed"
            continue

        # 2.5B-1H：统一租约校验
        v_ok, v_reject, v_reasons = validate_active_lease(
            ai_root, tid, batch_id, manifest_worker,
            now=now, allow_expired=allow_expired)
        if not v_ok:
            entry["outcome"] = v_reject
            entry["reasons"] = v_reasons
            report["rejected"] += 1
            report["rejected_task_ids"].append(tid)
            audit(ai_root, "result_ingested", task_id=tid, batch_id=batch_id,
                  outcome=v_reject, reason=v_reasons[0] if v_reasons else "")
            continue

        # 2.5B-1H: provider 匹配检查
        if res.get("provider") != exp_provider:
            entry["outcome"] = "rejected_provider_mismatch"
            entry["reasons"] = ["expected provider=%s, got %s" % (
                exp_provider, res.get("provider"))]
            report["rejected"] += 1
            report["rejected_task_ids"].append(tid)
            audit(ai_root, "result_ingested", task_id=tid, batch_id=batch_id,
                  outcome="provider_mismatch",
                  reason="expected %s got %s" % (exp_provider, res.get("provider")))
            continue

        # 2.5B-1H: model 匹配检查
        if res.get("model") != exp_model:
            entry["outcome"] = "rejected_model_mismatch"
            entry["reasons"] = ["expected model=%s, got %s" % (
                exp_model, res.get("model"))]
            report["rejected"] += 1
            report["rejected_task_ids"].append(tid)
            audit(ai_root, "result_ingested", task_id=tid, batch_id=batch_id,
                  outcome="model_mismatch",
                  reason="expected %s got %s" % (exp_model, res.get("model")))
            continue

        # 契约校验
        errors = validate_ai_result(res)
        if errors:
            entry["outcome"] = "rejected_invalid_result"
            entry["reasons"] = errors[:5]
            report["rejected"] += 1
            report["rejected_task_ids"].append(tid)
            audit(ai_root, "result_ingested", task_id=tid, batch_id=batch_id,
                  outcome="invalid", reason="; ".join(errors[:2]))
            continue

        if not os.path.exists(os.path.join(ai_root, "processing", "%s.json" % tid)):
            entry["outcome"] = "rejected_not_processing"
            entry["reasons"] = ["task not in processing"]
            report["rejected"] += 1
            report["rejected_task_ids"].append(tid)
            continue

        if res["status"] == "success":
            move_task(tid, "processing", "completed", ai_root=ai_root,
                      updates={"ai_result": res})
            entry["outcome"] = "completed"
            report["accepted"] += 1
            report["accepted_task_ids"].append(tid)
            audit(ai_root, "result_ingested", task_id=tid, batch_id=batch_id,
                  outcome="success")
            audit(ai_root, "task_completed", task_id=tid, batch_id=batch_id)
        else:
            moved = move_task(tid, "processing", "failed", ai_root=ai_root,
                              updates={"ai_result": res})
            entry["outcome"] = "failed"
            report["failed_tasks"] += 1
            report["accepted_task_ids"].append(tid)  # 也算处理完成
            audit(ai_root, "result_ingested", task_id=tid, batch_id=batch_id,
                  outcome=res["status"])
            audit(ai_root, "task_failed", task_id=tid, batch_id=batch_id,
                  code=(res.get("error") or {}).get("code"),
                  retry_count=moved.get("retry_count"))
        # 清理租约
        lp = os.path.join(ai_root, "leases", "%s.json" % tid)
        try:
            os.remove(lp)
        except OSError:
            pass

    # 2.5B-1H：计算批次完整性
    processed_ids = set(report["accepted_task_ids"]).union(
        {t for t in manifest_ids
         if os.path.exists(os.path.join(ai_root, "completed", "%s.json" % t))}
    ).union(
        {t for t in manifest_ids
         if os.path.exists(os.path.join(ai_root, "failed", "%s.json" % t))}
    )
    report["missing_task_ids"] = sorted(list(manifest_ids - processed_ids - seen))
    report["submitted_result_count"] = len(results)
    report["batch_complete"] = (
        len(report["missing_task_ids"]) == 0
        and len(manifest_ids) == len(processed_ids)
    )
    return report


# ── recover-expired：过期租约恢复 ──

def recover_expired(ai_root=AI_ROOT, dry_run=False):
    """扫描过期 lease：retry_count+1 后重新入队或永久失败；不产生新 task_id。"""
    _ensure_dirs(ai_root)
    now = _now()
    report = {"scanned": 0, "requeued": [], "permanently_failed": [],
              "skipped": [], "corrupt_lease": [], "dry_run": bool(dry_run)}
    lease_dir = os.path.join(ai_root, "leases")
    for fn in sorted(os.listdir(lease_dir)):
        if not fn.endswith(".json"):
            continue
        lp = os.path.join(lease_dir, fn)
        try:
            lease = _read_json(lp)
        except Exception:
            # 2.5B-1H：损坏租约 → 标记 corrupt_lease，不删任务，不自动入队
            report["corrupt_lease"].append({"lease": fn, "reason": "unreadable"})
            audit(ai_root, "corrupt_lease_detected", lease_file=fn,
                  reason="unreadable")
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

    try:
        args = ap.parse_args(argv)
        root = args.ai_root

        if args.cmd == "status":
            _print(status_summary(root))
            return 0
        elif args.cmd == "claim":
            _print(claim_batch(root, worker_id=args.worker_id,
                               batch_size=args.batch_size,
                               lease_minutes=args.lease_minutes))
            return 0
        elif args.cmd == "ingest":
            rep = ingest_results(root, args.batch_id, args.result_file,
                                allow_expired=args.allow_expired)
            _print(rep)
            # 2.5B-2A：CLI 退出码语义
            #  - 结构性错误（manifest/结果文件缺失、worker 不匹配等）→ 非0
            #  - 全部被拒（accepted=0 且 rejected>0）→ 非0
            #  - 部分接受 / 全部幂等（accepted=0 但 rejected=0，无错误）→ 0
            if rep.get("error"):
                return 1
            if rep.get("accepted", 0) == 0 and rep.get("rejected", 0) > 0:
                return 1
            return 0
        elif args.cmd == "recover-expired":
            _print(recover_expired(root, dry_run=args.dry_run))
            return 0
        elif args.cmd == "release":
            _print(release_batch(root, args.batch_id))
            return 0
        elif args.cmd == "heartbeat":
            _print(heartbeat_batch(root, args.batch_id, args.worker_id,
                                   extend_minutes=args.extend_minutes))
            return 0
        return 0
    except SystemExit:
        # argparse 参数错误（如缺 --batch-id）已自带非零退出码，直接上抛
        raise
    except Exception as e:
        sys.stderr.write("error: %s\n" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
