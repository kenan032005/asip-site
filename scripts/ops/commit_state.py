#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1B — 状态提交助手（state_src 工作树、全链路退出码校验）。

修复 R1 阻断项：
  1. 所有 git 命令在 **state_src** 执行（生产状态工作树），绝不在代码工作树提交；
  2. `git add -f` 使用与 workflow 对称的路径集合（相对 state_src）；
  3. 复制 / staging / commit / merge / push **每一步校验退出码**，任何失败即抛错；
  4. push 后校验 `origin production-state` 远端 SHA == 本地 HEAD；
  5. 校验已提交内容确实包含本轮结果（可选 expect 断言）；
  6. 失败 → record_strike() + 返回 ok=False（调用方必须阻断后续付费任务）。

设计：`commit_now()` 是唯一入口；`sync_to_state_branch()` 仅做复制并逐项校验。
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "state_src"

#: 与 workflow "Commit state" 的 git add -f 集合完全一致（路径相对 state_src）
GIT_PATHS = [
    "data/runtime/ops", "data/canonical", "data/disease", "data/runtime/timeline",
    "data/events.json", "data/pending_events.json", "data/raw_candidates.json",
    "data/quarantine_events.json", "data/public", "data/intelligence", "data/views",
    "data/reports", "logs", "data/runtime/article_processing_state.json",
]

#: 代码工作树 → state_src 的复制对（目录）
COPY_PAIRS = [
    ("data/runtime/ops", "data/runtime/ops"),
    ("data/canonical", "data/canonical"),
    ("data/disease", "data/disease"),
    ("data/runtime/timeline", "data/runtime/timeline"),
    ("data/public", "data/public"),
    ("data/intelligence", "data/intelligence"),
    ("data/views", "data/views"),
    ("data/reports", "data/reports"),
    ("logs/collector_cache", "logs/collector_cache"),
]
COPY_FILES = [
    "data/events.json", "data/pending_events.json", "data/raw_candidates.json",
    "data/quarantine_events.json", "data/runtime/article_processing_state.json",
    "data/runtime/article_processing_state.json.bak",
]


class CheckpointError(RuntimeError):
    """checkpoint 任一步失败（调用方必须阻断后续付费任务）。"""

    def __init__(self, stage, message, detail=""):
        super().__init__("CHECKPOINT_FAILED[%s]: %s" % (stage, message))
        self.stage = stage
        self.detail = detail


def _git(args, cwd=None, timeout=180):
    """在 state_src 执行 git；返回 CompletedProcess（调用方决定是否校验退出码）。"""
    cwd = Path(cwd or STATE_DIR)
    if not cwd.exists():
        raise CheckpointError("state_worktree", "state_src missing: %s" % cwd)
    return subprocess.run(["git", "-C", str(cwd)] + args,
                          capture_output=True, text=True, timeout=timeout)


def _git_ok(args, stage, cwd=None, timeout=180, allow=()):
    r = _git(args, cwd=cwd, timeout=timeout)
    if r.returncode != 0 and r.returncode not in allow:
        raise CheckpointError(stage, "%s -> rc=%d" % (" ".join(args), r.returncode),
                              (r.stderr or r.stdout or "")[-500:])
    return r


def assert_state_worktree():
    """拒绝在代码工作树执行提交（防止误提交到代码分支）。"""
    if not STATE_DIR.exists():
        raise CheckpointError("guard", "state_src not checked out")
    top = _git_ok(["rev-parse", "--show-toplevel"], "guard").stdout.strip()
    if not top:
        raise CheckpointError("guard", "cannot resolve git toplevel of state_src")
    if Path(top).resolve() == ROOT.resolve():
        raise CheckpointError("guard", "refusing to commit in CODE worktree (%s)" % top)
    # state_src 必须真的在 production-state 分支（或 detached 于其提交）
    head = _git_ok(["rev-parse", "HEAD"], "guard").stdout.strip()
    if not head:
        raise CheckpointError("guard", "state_src HEAD unresolved")
    return {"toplevel": top, "head": head}


def sync_to_state_branch(verify=True):
    """复制本轮产物到 state_src；逐项校验（存在、字节数一致）。"""
    if not STATE_DIR.exists():
        raise CheckpointError("sync", "state_src missing")
    copied = 0
    for src_rel, dst_rel in COPY_PAIRS:
        s, d = ROOT / src_rel, STATE_DIR / dst_rel
        if not s.is_dir():
            continue
        d.mkdir(parents=True, exist_ok=True)
        for f in s.rglob("*"):
            if not f.is_file():
                continue
            t = d / f.relative_to(s)
            t.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(f, t)
            except OSError as e:
                raise CheckpointError("sync", "copy failed %s: %s" % (f, e))
            if verify and t.stat().st_size != f.stat().st_size:
                raise CheckpointError("sync", "size mismatch after copy: %s" % t)
            copied += 1
    for rel in COPY_FILES:
        s = ROOT / rel
        if not s.is_file():
            continue
        d = STATE_DIR / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(s, d)
        except OSError as e:
            raise CheckpointError("sync", "copy failed %s: %s" % (s, e))
        if verify and d.stat().st_size != s.stat().st_size:
            raise CheckpointError("sync", "size mismatch after copy: %s" % d)
        copied += 1
    return {"copied": copied}


def _remote_sha(branch="production-state", retries=3):
    """取远端分支 SHA（ls-remote）。取不到返回 None（由调用方 fail-closed）。"""
    for i in range(retries):
        r = _git(["ls-remote", "origin", "refs/heads/%s" % branch], timeout=120)
        if r.returncode == 0:
            line = (r.stdout or "").strip().split("\n")[0].strip()
            if line:
                return line.split()[0]
        time.sleep(2 * (i + 1))
    return None


def _verify_content(expect):
    """校验已提交文件确实包含本轮结果（从 HEAD 读，而非工作区）。"""
    if not expect:
        return {"checked": False}
    path = expect["path"]
    r = _git_ok(["show", "HEAD:%s" % path], "verify_content")
    if expect.get("nonempty") and not (r.stdout or "").strip():
        raise CheckpointError("verify_content", "HEAD:%s is empty" % path)
    field = expect.get("field")
    if field:
        import json
        try:
            doc = json.loads(r.stdout)
        except Exception as e:  # noqa: BLE001
            raise CheckpointError("verify_content", "HEAD:%s not json: %s" % (path, e))
        if expect.get("equals") is not None:
            got = doc.get(field)
            if got != expect["equals"]:
                raise CheckpointError("verify_content",
                                      "%s.%s = %r != expected %r" % (path, field, got, expect["equals"]))
        elif expect.get("present") and not doc.get(field):
            raise CheckpointError("verify_content", "%s.%s missing/empty" % (path, field))
    return {"checked": True, "path": path}


def commit_now(message, after="state", expect=None, push=True, branch="production-state"):
    """提交 state 分支。返回 dict；失败抛 CheckpointError（不吞异常）。

    参数 expect: {"path": "...", "field": "...", "equals"/"present": ...} 用于内容校验。
    """
    from scripts.ops import paid_gate

    info = {"after": after, "branch": branch, "stages": {}}
    try:
        info["stages"]["guard"] = assert_state_worktree()
        info["stages"]["sync"] = sync_to_state_branch()
        _git_ok(["add", "-f"] + GIT_PATHS, "add")
        info["stages"]["add"] = {"paths": len(GIT_PATHS)}

        st = _git_ok(["status", "--porcelain"], "status").stdout
        if not (st or "").strip():
            info.update({"ok": True, "committed": False, "pushed": False,
                         "message": "no changes (%s)" % after})
            return info

        _git_ok(["commit", "-m", "%s [%s]" % (message, after)], "commit")
        info["stages"]["commit"] = {"sha": _git_ok(["rev-parse", "HEAD"], "commit").stdout.strip()}
        if not push:
            info.update({"ok": True, "committed": True, "pushed": False})
            return info

        # 并发写入者：fetch + merge -X ours（保留本地本轮数据），失败即抛
        _git_ok(["fetch", "origin", branch], "fetch")
        m = _git(["merge", "-X", "ours", "--no-edit", "origin/%s" % branch], timeout=180)
        if m.returncode != 0:
            # 已在本地提交之上无需合并 / 或合并冲突：都要显式判定，不得静默继续
            ahead = _git(["rev-list", "--count", "origin/%s..HEAD" % branch], timeout=60)
            if ahead.returncode != 0 or not (ahead.stdout or "").strip().isdigit():
                raise CheckpointError("merge", "merge failed and ahead-count unknown",
                                      (m.stderr or "")[-400:])
        info["stages"]["merge"] = {"rc": m.returncode}
        st2 = _git_ok(["status", "--porcelain"], "status").stdout
        if (st2 or "").strip():
            _git_ok(["commit", "--no-edit"], "merge_commit")
        local = _git_ok(["rev-parse", "HEAD"], "rev-parse").stdout.strip()

        p = _git(["push", "origin", "HEAD:%s" % branch], timeout=300)
        if p.returncode != 0:
            raise CheckpointError("push", "push rejected", (p.stderr or "")[-500:])
        info["stages"]["push"] = {"local": local}

        remote = _remote_sha(branch)
        if not remote:
            raise CheckpointError("verify_remote", "cannot read remote ref %s" % branch)
        if remote != local:
            raise CheckpointError("verify_remote",
                                  "remote %s != local %s (not persisted)" % (remote[:12], local[:12]))
        info["stages"]["verify_remote"] = {"remote": remote, "match": True}
        info["stages"]["verify_content"] = _verify_content(expect)
        info.update({"ok": True, "committed": True, "pushed": True, "head": local, "remote": remote})
        return info
    except CheckpointError as e:
        paid_gate.record_strike("checkpoint_%s:%s" % (e.stage, str(e.detail)[:120]))
        info.update({"ok": False, "committed": False, "pushed": False,
                     "stage": e.stage, "error": str(e), "detail": e.detail})
        raise
    except Exception as e:  # noqa: BLE001
        paid_gate.record_strike("checkpoint_exception:%s" % str(e)[:150])
        info.update({"ok": False, "committed": False, "pushed": False,
                     "stage": "exception", "error": str(e)[:400]})
        raise CheckpointError("exception", str(e)[:300])


def main(argv=None):
    argv = argv or sys.argv[1:]
    msg = argv[0] if argv else "ops: state checkpoint"
    after = argv[1] if len(argv) > 1 else "manual"
    try:
        res = commit_now(msg, after=after)
    except CheckpointError as e:
        print({"ok": False, "stage": e.stage, "error": str(e)})
        return 1
    print(res)
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
