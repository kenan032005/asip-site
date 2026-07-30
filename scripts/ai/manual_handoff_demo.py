#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 2.5B-2A — 单会话 Hy3 手工交接演示。

演示「创建任务 → 领取 → 当前 WorkBuddy 内置 Hy3（免费）处理 → 写结果 →
ingest → 完成 → 幂等重ingest」整条链路。

约束（对应规范）：
- 不调用任何外部/付费模型（禁用 DeepSeek V4 Pro / ChatGPT 5.6）；
- 不发起任何网络请求；
- 所有状态仅存在于 .workbuddy_runtime/stage25b2a/（运行时目录，已 gitignore，绝不入库）；
- 合成任务标记 synthetic=true，绝不进入生产 data/ai。
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from ai.contracts import new_ai_task  # noqa: E402
from ai.workbuddy_queue_provider import WorkbuddyQueueProvider  # noqa: E402
from ai.workbuddy_worker import (  # noqa: E402
    claim_batch, ingest_results, status_summary,
)

# 运行时目录（与 data/ai 完全隔离；gitignore，绝不入库）
DEFAULT_AI_ROOT = os.path.join(
    os.path.dirname(_SCRIPTS), ".workbuddy_runtime", "stage25b2a"
)

EXPECTED_PROVIDER = "workbuddy_queue"
EXPECTED_MODEL = "hy3"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def prepare(ai_root=DEFAULT_AI_ROOT, worker_id="workbuddy-hy3-demo"):
    """在 queue 放入 2 个合成任务（synthetic=true），并 claim 出批次。

    返回信息字典，含 batch_id、tasks（task_id / task_type / country_iso3 / lang）、
    各批次文件路径，供 Hy3 生成结果时引用 task_id。
    """
    os.makedirs(ai_root, exist_ok=True)
    provider = WorkbuddyQueueProvider({}, ai_root=ai_root)
    # 2 个合成任务：乍得(法语,TCD) + 尼日尔(英语,NER)，纯虚构安全事件
    specs = [
        ("event_synthesis", {"country_iso3": "TCD", "lang": "fr",
                             "event": "social_security_forum"},
         "synthetic-tcd-forum-2026", "p1", "o1", "critical"),
        ("event_synthesis", {"country_iso3": "NER", "lang": "en",
                             "event": "pension_workshop"},
         "synthetic-ner-workshop-2026", "p2", "o2", "high"),
    ]
    for task_type, input_ref, ch, pv, osv, prio in specs:
        t = new_ai_task(task_type, input_ref, ch, pv, osv,
                        provider_requested=EXPECTED_PROVIDER,
                        priority=prio, max_retries=1)
        t["synthetic"] = True  # 标记合成，绝不进入生产数据
        provider.submit_task(t)
    claimed = claim_batch(ai_root, worker_id=worker_id, batch_size=2,
                          lease_minutes=30,
                          expected_provider=EXPECTED_PROVIDER,
                          expected_model=EXPECTED_MODEL)
    bdir = os.path.join(ai_root, "batches", claimed["batch_id"])
    return {
        "ai_root": ai_root,
        "batch_id": claimed["batch_id"],
        "worker_id": claimed["worker_id"],
        "tasks": [
            {
                "task_id": t["task_id"],
                "task_type": t["task_type"],
                "country_iso3": (t.get("input_ref") or {}).get("country_iso3"),
                "lang": (t.get("input_ref") or {}).get("lang"),
            }
            for t in claimed["tasks"]
        ],
        "manifest_path": os.path.join(bdir, "manifest.json"),
        "request_md_path": os.path.join(bdir, "WORKBUDDY_REQUEST.md"),
        "template_path": os.path.join(bdir, "results.template.json"),
    }


def verify(ai_root=DEFAULT_AI_ROOT, batch_id=None, info=None):
    """校验批次清单/模板/请求文件存在且字段正确。返回 (ok, detail)。"""
    if info is not None and info.get("batch_id"):
        bdir = os.path.join(ai_root, "batches", info["batch_id"])
    else:
        bpat = os.path.join(ai_root, "batches")
        if not os.path.isdir(bpat):
            return False, "no batches dir under %s" % ai_root
        subs = [d for d in os.listdir(bpat)
                if os.path.isdir(os.path.join(bpat, d))
                and not d.startswith(".tmp_")]
        if not subs:
            return False, "no batch found under %s" % ai_root
        bdir = os.path.join(bpat, sorted(subs)[-1])
    manifest = os.path.join(bdir, "manifest.json")
    req = os.path.join(bdir, "WORKBUDDY_REQUEST.md")
    tpl = os.path.join(bdir, "results.template.json")
    if not (os.path.exists(manifest) and os.path.exists(req) and os.path.exists(tpl)):
        return False, "missing batch files"
    try:
        m = json.load(open(manifest, encoding="utf-8"))
    except Exception as e:
        return False, "manifest unreadable: %s" % e
    if m.get("expected_provider") != EXPECTED_PROVIDER:
        return False, "expected_provider mismatch: %r" % m.get("expected_provider")
    if m.get("expected_model") != EXPECTED_MODEL:
        return False, "expected_model mismatch: %r" % m.get("expected_model")
    if m.get("task_count") != 2:
        return False, "task_count != 2: %r" % m.get("task_count")
    return True, "batch=%s tasks=%d" % (m.get("batch_id"), m.get("task_count"))


def cleanup(ai_root=DEFAULT_AI_ROOT):
    """删除整个运行时目录。"""
    if os.path.isdir(ai_root):
        shutil.rmtree(ai_root, ignore_errors=True)
    return not os.path.isdir(ai_root)


def run(ai_root=DEFAULT_AI_ROOT, result_file=None, worker_id="workbuddy-hy3-demo"):
    """完整演示：prepare → ingest(result_file) → 幂等重ingest → verify。

    假设 result_file 已由当前 Hy3 会话生成（含 2 个合法结果）。
    """
    info = prepare(ai_root=ai_root, worker_id=worker_id)
    if result_file is None:
        return {"ok": False, "stage": "prepare", "info": info,
                "note": "需先由 Hy3 生成结果文件"}
    rep1 = ingest_results(ai_root, info["batch_id"], result_file)
    rep2 = ingest_results(ai_root, info["batch_id"], result_file)  # 幂等
    ok, detail = verify(ai_root, info["batch_id"], info)
    return {
        "ok": ok and rep1.get("accepted", 0) == 2,
        "prepare": info,
        "ingest_first": rep1,
        "ingest_idempotent": rep2,
        "verify": {"ok": ok, "detail": detail},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="ASIP 2.5B-2A 单会话 Hy3 手工交接演示")
    ap.add_argument("--ai-root", default=DEFAULT_AI_ROOT)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare")
    sub.add_parser("verify")
    sub.add_parser("cleanup")
    r = sub.add_parser("run")
    r.add_argument("--result-file", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "prepare":
        info = prepare(ai_root=args.ai_root)
        print(json.dumps(info, ensure_ascii=False, indent=2))
    elif args.cmd == "verify":
        ok, detail = verify(ai_root=args.ai_root)
        print(json.dumps({"ok": ok, "detail": detail}, ensure_ascii=False, indent=2))
    elif args.cmd == "cleanup":
        ok = cleanup(ai_root=args.ai_root)
        print(json.dumps({"cleaned": ok}, ensure_ascii=False, indent=2))
    elif args.cmd == "run":
        out = run(ai_root=args.ai_root, result_file=args.result_file)
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
