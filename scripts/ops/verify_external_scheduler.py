#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""External Automated Wake-up 验证脚本（Stage8D §十八）。

用途：
  1) --check-only（默认，只读）：查询最近 orchestrator 运行，判定是否存在
     由 external_scheduler / github_native_schedule 触发的 automation run。
  2) --dispatch：向仓库发出一次 repository_dispatch
     （type=external_scheduler_wakeup，client_payload.trigger_source=external_scheduler），
     用于验证接收端是否配置正确。

安全：
  - 不在代码/workflow/仓库内存储任何 token；token 仅从环境变量读取。
  - 不写入 production-state / gh-pages。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com/repos/{repo}/{path}"
WORKFLOW = "asip-production-orchestrator.yml"


def _get(repo, path, token):
    req = urllib.request.Request(API.format(repo=repo, path=path))
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "asip-external-scheduler-verify")
    if token:
        req.add_header("Authorization", "Bearer %s" % token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _post(repo, path, token, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API.format(repo=repo, path=path), data=data,
                                 method="POST")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "asip-external-scheduler-verify")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer %s" % token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def check_only(repo, token, limit=20):
    doc = _get(repo, "actions/workflows/%s/runs?per_page=%d" % (WORKFLOW, limit),
               token)
    runs = doc.get("workflow_runs", [])
    print("RECENT_ORCHESTRATOR_RUNS = %d" % len(runs))
    auto = 0
    for r in runs:
        print("  %s | event=%s | %s | %s | %s" % (
            r.get("id"), r.get("event"), r.get("status"),
            r.get("conclusion"), r.get("created_at")))
        if r.get("event") in ("schedule", "repository_dispatch"):
            auto += 1
    ext = [r for r in runs if r.get("event") == "repository_dispatch"]
    print("SCHEDULE_RUNS = %d" % len(
        [r for r in runs if r.get("event") == "schedule"]))
    print("REPOSITORY_DISPATCH_RUNS = %d" % len(ext))
    print("EXTERNAL_SCHEDULER_CONFIGURED = %s" % (
        "true" if ext else "false"))
    return 0


def dispatch(repo, token):
    if not token:
        print("ERROR: 需要 token（--token-env 指定环境变量名，默认 ASIP_GH_TOKEN）",
              file=sys.stderr)
        return 2
    code = _post(repo, "dispatches", token, {
        "event_type": "external_scheduler_wakeup",
        "client_payload": {"trigger_source": "external_scheduler"}})
    print("DISPATCH_HTTP = %s（204 表示接收端接受）" % code)
    return 0 if code == 204 else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="External scheduler verifier")
    ap.add_argument("--repo", default="kenan032005/asip-site")
    ap.add_argument("--token-env", default="ASIP_GH_TOKEN",
                    help="存放 GitHub token 的环境变量名（不落盘、不入库）")
    ap.add_argument("--dispatch", action="store_true",
                    help="实际发起一次 repository_dispatch（默认只做只读检查）")
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args(argv)
    token = os.environ.get(args.token_env, "").strip()
    if args.dispatch:
        return dispatch(args.repo, token)
    return check_only(args.repo, token)


if __name__ == "__main__":
    sys.exit(main())
