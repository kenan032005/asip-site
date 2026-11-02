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


def assert_state_worktree(expected_branch="production-state",
                          expected_remote_substr=None,
                          expected_base_sha=None):
    """拒绝在代码工作树提交；并核对 state_src 的仓库、分支与基线。

    R1C：仅"不是代码树"不够 —— 还必须确认目标远端是本仓库、当前分支是 state 分支、
    且当前提交包含预期基线（防止把别人的 state 仓库/错误分支写坏）。
    """
    if not STATE_DIR.exists():
        raise CheckpointError("guard", "state_src not checked out")
    top = _git_ok(["rev-parse", "--show-toplevel"], "guard").stdout.strip()
    if not top:
        raise CheckpointError("guard", "cannot resolve git toplevel of state_src")
    if Path(top).resolve() == ROOT.resolve():
        raise CheckpointError("guard", "refusing to commit in CODE worktree (%s)" % top)

    remote = _git_ok(["remote", "get-url", "origin"], "guard").stdout.strip()
    if not remote:
        raise CheckpointError("guard", "state_src has no origin remote")
    want = expected_remote_substr or os.environ.get("ASIP_EXPECT_REPO_SUBSTR") or ""
    if want and want not in remote:
        raise CheckpointError("guard", "origin %r does not contain expected %r" % (remote, want))

    br = _git(["symbolic-ref", "--short", "HEAD"], timeout=60)
    branch = (br.stdout or "").strip()
    head = _git_ok(["rev-parse", "HEAD"], "guard").stdout.strip()
    if not head:
        raise CheckpointError("guard", "state_src HEAD unresolved")
    if expected_branch:
        if branch != expected_branch:
            raise CheckpointError("guard", "state_src on branch %r, expected %r"
                                  % (branch or "(detached)", expected_branch))
    if expected_base_sha:
        anc = _git(["merge-base", "--is-ancestor", expected_base_sha, head], timeout=60)
        if anc.returncode != 0:
            raise CheckpointError("guard", "expected base %s is not an ancestor of HEAD %s"
                                  % (expected_base_sha[:10], head[:10]))
    return {"toplevel": top, "head": head, "branch": branch, "remote": remote}


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
    """校验已提交文件确实包含本轮结果（从 HEAD 读，而非工作区）。

    R1C：必须显式 checked=True 才算完成；expect 缺失时由调用方 require_expect 拒绝。
    """
    if not expect:
        return {"checked": False}
    path = expect["path"]
    r = _git_ok(["show", "HEAD:%s" % path], "verify_content")
    if expect.get("nonempty") and not (r.stdout or "").strip():
        raise CheckpointError("verify_content", "HEAD:%s is empty" % path)
    for f in (expect.get("fields_present") or []):
        import json as _json
        try:
            doc2 = _json.loads(r.stdout) if "doc" not in dir() else doc
        except Exception as e:  # noqa: BLE001
            raise CheckpointError("verify_content", "HEAD:%s not json: %s" % (path, e))
        if not doc2.get(f):
            raise CheckpointError("verify_content", "%s.%s missing/empty" % (path, f))

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


def commit_now(message, after="state", expect=None, push=True, branch="production-state",
               require_expect=False, guard_extra=None):
    """提交 state 分支。返回 dict；失败抛 CheckpointError（不吞异常）。

    参数 expect: {"path","field","equals"/"present","fields_present":[...]}；
    require_expect=True 时缺少 expect 或内容未校验通过 → 拒绝（不得误报成功）。
    guard_extra: 传给 assert_state_worktree 的额外断言（expected_remote_substr / base）。
    """
    from scripts.ops import paid_gate

    info = {"after": after, "branch": branch, "stages": {}}
    try:
        if require_expect and not expect:
            raise CheckpointError("expect_required",
                                  "commit_now(require_expect=True) 必须显式传 expect")
        info["stages"]["guard"] = assert_state_worktree(**(guard_extra or {}))
        info["stages"]["sync"] = sync_to_state_branch()
        _git_ok(["add", "-f"] + GIT_PATHS, "add")
        info["stages"]["add"] = {"paths": len(GIT_PATHS)}

        st = _git_ok(["status", "--porcelain"], "status").stdout
        if not (st or "").strip():
            info.update({"ok": True, "committed": False, "pushed": False,
                         "content_verified": False,
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
        vc = _verify_content(expect)
        # 有 expect 就必须真的校验过；无 expect 时如实标注未校验（不得冒充已校验）
        if expect and not vc.get("checked"):
            raise CheckpointError("verify_content", "content verification not performed")
        info["stages"]["verify_content"] = vc
        info["content_verified"] = bool(vc.get("checked"))
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
    """CLI：commit_state.py "<message>" [after] [--require-expect] [--expect-path P]
    [--expect-field F] [--expect-equals V] [--expect-fields a,b] [--branch B] [--no-push]
    [--collection]（--collection 等价于 --require-expect + 采集场景字段）"""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("message", nargs="?", default="ops: state checkpoint")
    ap.add_argument("after", nargs="?", default="manual")
    ap.add_argument("--require-expect", action="store_true")
    ap.add_argument("--expect-path", default=None)
    ap.add_argument("--expect-field", default=None)
    ap.add_argument("--expect-equals", default=None)
    ap.add_argument("--expect-fields", default="")
    ap.add_argument("--branch", default="production-state")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--collection", action="store_true")
    a = ap.parse_args(argv)

    expect = None
    if a.collection:
        expect = {"path": "data/runtime/ops/production_state.json",
                  "fields_present": ["last_successful_collection", "processed_hashes"]}
    elif a.expect_path:
        expect = {"path": a.expect_path}
        if a.expect_field:
            expect["field"] = a.expect_field
        if a.expect_equals is not None:
            expect["equals"] = a.expect_equals
        if a.expect_fields:
            expect["fields_present"] = [x for x in a.expect_fields.split(",") if x]
    try:
        res = commit_now(a.message, after=a.after, expect=expect, push=not a.no_push,
                         branch=a.branch,
                         require_expect=(a.require_expect or a.collection),
                         guard_extra={"expected_remote_substr":
                                      os.environ.get("ASIP_EXPECT_REPO_SUBSTR", "asip-site")})
    except CheckpointError as e:
        print(json.dumps({"ok": False, "stage": e.stage, "error": str(e)}, ensure_ascii=False))
        return 1
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
