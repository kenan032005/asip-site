#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1B — 熔断 CLI（独立持久化 + 分支自举 + 可达性 fail-closed + 解除审计）。

为什么独立持久化：production-state 一旦写不进（本次故障），熔断标记若只放在该分支
永远读不到。因此熔断写本地文件，并推到**独立小分支** `ops-health`（几百字节，
不受 100MB 限制）；每轮开始时 `fetch` 回来，跨 runner 生效。

R1B 修复：
  * `ops-health` **不假设已存在**：首次 publish 自动创建分支（先取默认分支 HEAD 建 ref）；
  * `fetch` 失败/远端不可验证 → 记录 `breaker_remote.json(reachable=false)`，
    付费门禁据此 **fail-closed 暂停**；
  * `clear` 必须带 `--by/--reason`，写入状态文件与 `breaker_audit.jsonl`（可审计）。

用法：
  python scripts/ops/breakerctl.py status
  python scripts/ops/breakerctl.py strike --reason state_push_failed [--ttl-hours 24]
  python scripts/ops/breakerctl.py clear --by kenan --reason "storage migrated"
  python scripts/ops/breakerctl.py publish --repo owner/repo [--branch ops-health]
  python scripts/ops/breakerctl.py fetch   --repo owner/repo [--branch ops-health]
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.ops import paid_gate  # noqa: E402

DEFAULT_BRANCH = "ops-health"
FILE_PATH = "breaker.json"
API = "https://api.github.com"


class RemoteError(RuntimeError):
    pass


def _token(explicit=None):
    return explicit or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def _api(url, token, method="GET", body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer %s" % token,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return (json.loads(raw) if raw else {}), r.status
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, 404
        raise RemoteError("HTTP %s: %s" % (e.code, str(e)[:200]))
    except Exception as e:  # noqa: BLE001
        raise RemoteError(str(e)[:200])


def default_branch(repo, token):
    doc, _ = _api("%s/repos/%s" % (API, repo), token)
    return (doc or {}).get("default_branch") or "main"


def branch_exists(repo, branch, token):
    doc, status = _api("%s/repos/%s/git/ref/heads/%s" % (API, repo, branch), token)
    if status == 404:
        return False
    if not doc or "object" not in (doc or {}):
        raise RemoteError("unexpected ref response for %s" % branch)
    return True


def ensure_branch(repo, branch=DEFAULT_BRANCH, token=None, base=None):
    """确保分支存在：不存在则从 base（默认分支 HEAD）创建。返回 {"created":bool,"sha":...}。"""
    token = _token(token)
    if not token:
        raise RemoteError("no_token")
    if branch_exists(repo, branch, token):
        doc, _ = _api("%s/repos/%s/git/ref/heads/%s" % (API, repo, branch), token)
        return {"created": False, "sha": doc["object"]["sha"], "branch": branch}
    base = base or default_branch(repo, token)
    doc, status = _api("%s/repos/%s/git/ref/heads/%s" % (API, repo, base), token)
    if status == 404 or not doc:
        raise RemoteError("base branch %s not found" % base)
    sha = doc["object"]["sha"]
    _api("%s/repos/%s/git/refs" % (API, repo), token, method="POST",
         body={"ref": "refs/heads/%s" % branch, "sha": sha})
    return {"created": True, "sha": sha, "branch": branch, "from": base}


def publish(repo, branch=DEFAULT_BRANCH, token=None, doc=None):
    token = _token(token)
    if not token:
        paid_gate.save_remote_status(False, "no_token")
        return {"ok": False, "error": "no_token"}
    try:
        boot = ensure_branch(repo, branch, token)
    except RemoteError as e:
        paid_gate.save_remote_status(False, "bootstrap_failed:%s" % e)
        return {"ok": False, "error": "bootstrap_failed: %s" % e}
    doc = doc if doc is not None else paid_gate.load_breaker()
    payload = {"message": "breaker: %s%s" % ("tripped" if doc.get("tripped") else "clear",
                                             " (auto-bootstrap)" if boot["created"] else ""),
               "content": base64.b64encode(json.dumps(doc, ensure_ascii=False, indent=1).encode()).decode(),
               "branch": branch}
    base = "%s/repos/%s/contents/%s" % (API, repo, FILE_PATH)
    try:
        cur, status = _api(base + "?ref=" + branch, token)
        if status != 404 and cur and cur.get("sha"):
            payload["sha"] = cur["sha"]
        _api(base, token, method="PUT", body=payload)
        paid_gate.save_remote_status(True, "published:%s" % branch)
        return {"ok": True, "branch": branch, "bootstrapped": boot["created"],
                "tripped": bool(doc.get("tripped"))}
    except RemoteError as e:
        paid_gate.save_remote_status(False, "publish_failed:%s" % e)
        return {"ok": False, "error": str(e)[:200]}


def fetch(repo, branch=DEFAULT_BRANCH, token=None):
    token = _token(token)
    if not token:
        paid_gate.save_remote_status(False, "no_token")
        return {"ok": False, "error": "no_token"}
    try:
        doc, status = _api("%s/repos/%s/contents/%s?ref=%s" % (API, repo, FILE_PATH, branch), token)
        if status == 404 or not doc or "content" not in (doc or {}):
            # 分支/文件尚不存在：不是错误，但"远端状态不可验证" → 由调用方决定是否暂停
            paid_gate.save_remote_status(False, "breaker_file_absent:%s" % branch)
            return {"ok": False, "error": "breaker_file_absent", "bootstrap_required": True}
        remote = json.loads(base64.b64decode(doc["content"]).decode("utf-8"))
    except RemoteError as e:
        paid_gate.save_remote_status(False, "fetch_failed:%s" % e)
        return {"ok": False, "error": str(e)[:200]}
    local = paid_gate.load_breaker()
    paid_gate.save_remote_status(True, "fetched:%s" % branch)
    if remote.get("tripped") or int(remote.get("strikes") or 0) > int(local.get("strikes") or 0):
        paid_gate.save_breaker(remote)
        return {"ok": True, "applied": "remote", "remote_tripped": bool(remote.get("tripped"))}
    return {"ok": True, "applied": "local_kept", "local_tripped": bool(local.get("tripped"))}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "strike", "clear", "publish", "fetch", "bootstrap"])
    ap.add_argument("--reason", default="manual")
    ap.add_argument("--by", default=os.environ.get("GITHUB_ACTOR") or "manual")
    ap.add_argument("--ttl-hours", type=int, default=24)
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    ap.add_argument("--branch", default=DEFAULT_BRANCH)
    a = ap.parse_args(argv)
    if a.cmd == "status":
        print(json.dumps(paid_gate.load_breaker(), ensure_ascii=False, indent=1))
        print(json.dumps(paid_gate.pause_mode_summary(), ensure_ascii=False, indent=1))
    elif a.cmd == "strike":
        doc = paid_gate.record_strike(a.reason, ttl_hours=a.ttl_hours)
        out = {"breaker": doc}
        if a.repo:
            out["publish"] = publish(a.repo, a.branch)
        print(json.dumps(out, ensure_ascii=False, indent=1))
    elif a.cmd == "clear":
        if not a.reason or a.reason == "manual":
            print(json.dumps({"ok": False, "error": "clear requires explicit --reason (audit)"},
                             ensure_ascii=False))
            return 2
        doc = paid_gate.clear_breaker(by=a.by, reason=a.reason)
        out = {"breaker": doc}
        if a.repo:
            out["publish"] = publish(a.repo, a.branch, doc=doc)
        print(json.dumps(out, ensure_ascii=False, indent=1))
    elif a.cmd == "publish":
        print(json.dumps(publish(a.repo, a.branch), ensure_ascii=False))
    elif a.cmd == "bootstrap":
        try:
            print(json.dumps(ensure_branch(a.repo, a.branch), ensure_ascii=False))
        except RemoteError as e:
            print(json.dumps({"ok": False, "error": str(e)[:200]}, ensure_ascii=False))
            return 1
    else:
        print(json.dumps(fetch(a.repo, a.branch), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
