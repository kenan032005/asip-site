#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1 — 熔断 CLI（独立持久化）。

用法：
  python scripts/ops/breakerctl.py status
  python scripts/ops/breakerctl.py strike --reason state_push_failed
  python scripts/ops/breakerctl.py clear
  python scripts/ops/breakerctl.py publish --repo <owner/repo> [--branch ops-health]
  python scripts/ops/breakerctl.py fetch   --repo <owner/repo> [--branch ops-health]

为什么需要独立持久化：
  production-state 一旦写不进（本次故障），熔断标记若只放在该分支就永远读不到。
  因此熔断同时写本地文件，并通过 `publish` 推到**独立小分支** `ops-health`
  （单文件几百字节，不受 100MB 限制影响）；下一轮开始 `fetch` 回来即可生效。
"""
import argparse
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.ops import paid_gate  # noqa: E402

DEFAULT_BRANCH = "ops-health"
FILE_PATH = "breaker.json"


def _api(url, token, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer %s" % token,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def publish(repo, branch=DEFAULT_BRANCH, token=None):
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return {"ok": False, "error": "no_token"}
    doc = paid_gate.load_breaker()
    payload = {"message": "breaker: %s" % ("tripped" if doc.get("tripped") else "clear"),
               "content": base64.b64encode(json.dumps(doc, ensure_ascii=False, indent=1).encode()).decode(),
               "branch": branch}
    base = "https://api.github.com/repos/%s/contents/%s" % (repo, FILE_PATH)
    try:
        cur = _api(base + "?ref=" + branch, token)
        payload["sha"] = cur["sha"]
    except Exception:
        pass
    try:
        _api(base, token, method="PUT", body=payload)
        return {"ok": True, "branch": branch, "tripped": bool(doc.get("tripped"))}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:200]}


def fetch(repo, branch=DEFAULT_BRANCH, token=None):
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return {"ok": False, "error": "no_token"}
    try:
        doc = _api("https://api.github.com/repos/%s/contents/%s?ref=%s" % (repo, FILE_PATH, branch), token)
        remote = json.loads(base64.b64decode(doc["content"]).decode("utf-8"))
        local = paid_gate.load_breaker()
        # 远端更"新"（有 tripped 或 strikes 更大）→ 覆盖本地
        if remote.get("tripped") or int(remote.get("strikes") or 0) > int(local.get("strikes") or 0):
            paid_gate.save_breaker(remote)
            return {"ok": True, "applied": "remote", "remote": remote}
        return {"ok": True, "applied": "local_kept", "local": local}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:200]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "strike", "clear", "publish", "fetch"])
    ap.add_argument("--reason", default="manual")
    ap.add_argument("--ttl-hours", type=int, default=24)
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    ap.add_argument("--branch", default=DEFAULT_BRANCH)
    a = ap.parse_args(argv)
    if a.cmd == "status":
        print(json.dumps(paid_gate.load_breaker(), ensure_ascii=False, indent=1))
        print(json.dumps(paid_gate.pause_mode_summary(), ensure_ascii=False, indent=1))
    elif a.cmd == "strike":
        print(json.dumps(paid_gate.record_strike(a.reason, ttl_hours=a.ttl_hours), ensure_ascii=False, indent=1))
    elif a.cmd == "clear":
        print(json.dumps(paid_gate.clear_breaker(), ensure_ascii=False, indent=1))
    elif a.cmd == "publish":
        print(json.dumps(publish(a.repo, a.branch), ensure_ascii=False))
    else:
        print(json.dumps(fetch(a.repo, a.branch), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
