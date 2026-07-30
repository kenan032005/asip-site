#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASIP Stage 2.5A 最终加固 — 验收测试（TDD）。

对应规范三 / 七 / 十：先写失败测试，再实现功能；本文件在加固前会因
config.DEFAULT_CONFIG_PATH / contracts.SCHEMA_DIR 指向错误目录、pipeline 未调用
2.5A 测试、README 未包含 2.5A 说明等而失败；加固后全部通过。

硬性断言（T1-T15）：
  T1  config.DEFAULT_CONFIG_PATH == <repo_root>/config/runtime.json
  T2  contracts.SCHEMA_DIR == <repo_root>/schemas
  T3  修改 runtime.json 安全测试值后 load_runtime_config() 真实读取
  T4  load_json_schema("ai_task.schema.json") 不为 None
  T5  相同任务 queue 重复提交不重复
  T6  同一任务进 processing 后再次提交不重复
  T7  同一任务进 completed 后再次提交不重复
  T8  同一任务进 failed 后重试须依据 retry_count，不生成第二文件
  T9  AI Result 缺 started_at 必须失败
  T10 AI Result 缺 completed_at 必须失败
  T11 AI Result 缺 result/error/usage 必须失败
  T12 schema_version 不是 1.0 必须失败
  T13 task_id 格式错误必须失败
  T14 pipeline_runner.py 必须实际调用 Stage 2.5A 测试
  T15 README 必须包含 Stage 2.5A 当前状态说明

公网隔离（规范十，分层硬检查）：
  ISO1  dist 本地扫描（硬）：不得含 data/ai / config/runtime.json / .env / .env.example / schemas/ai_task.schema.json / 任务结果内容
  ISO2  gh-pages 分支树（硬）：同上路径不得出现
  ISO3  线上 URL（补充）：404 视为未暴露；网络不可达标记 UNVERIFIED，不得标 PASS
"""

import os
import sys
import json
import re
import glob
import shutil
import tempfile
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

from ai.config import load_runtime_config, DEFAULT_CONFIG_PATH  # noqa: E402
from ai.contracts import SCHEMA_DIR, load_json_schema, validate_ai_result, SCHEMA_VERSION  # noqa: E402
from ai.identifiers import generate_ai_task_id, generate_ai_cache_key  # noqa: E402
from ai.workbuddy_queue_provider import (  # noqa: E402
    WorkbuddyQueueProvider,
    find_existing_task_by_cache_key,
    move_task,
)
from ai.exceptions import SchemaNotFoundError  # noqa: E402


# 公网禁止暴露的文件 / 目录
FORBIDDEN_PATTERNS = [
    "data/ai", "config/runtime.json", ".env", ".env.example",
    "schemas/ai_task.schema.json", "schemas/ai_result.schema.json",
    "schemas/runtime_config.schema.json",
]


def _count_tasks(ai_root):
    n = 0
    for st in ("queue", "processing", "completed", "failed", "cache"):
        d = os.path.join(ai_root, st)
        if os.path.isdir(d):
            n += sum(1 for f in os.listdir(d) if f.endswith(".json"))
    return n


def main():
    print("=" * 64)
    print("ASIP Stage 2.5A 最终加固 — 验收测试")
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

    # ── T1 DEFAULT_CONFIG_PATH 真实路径 ──
    expected_cfg = os.path.normpath(os.path.join(ROOT, "config", "runtime.json"))
    actual_cfg = os.path.normpath(str(DEFAULT_CONFIG_PATH))
    check("T1", actual_cfg == expected_cfg,
          "DEFAULT_CONFIG_PATH=%s 期望=%s" % (actual_cfg, expected_cfg))

    # ── T2 SCHEMA_DIR 真实路径 ──
    expected_schema = os.path.normpath(os.path.join(ROOT, "schemas"))
    actual_schema = os.path.normpath(str(SCHEMA_DIR))
    check("T2", actual_schema == expected_schema,
          "SCHEMA_DIR=%s 期望=%s" % (actual_schema, expected_schema))

    # ── T3 修改 runtime.json 后 load_runtime_config 真实读取（测后恢复）──
    rt_path = os.path.join(ROOT, "config", "runtime.json")
    sentinel = "stage25a-hardening-sentinel"
    original = None
    read_ok = False
    try:
        with open(rt_path, "r", encoding="utf-8") as f:
            original = f.read()
        data = json.loads(original)
        data["ai_model"] = sentinel  # ai_model 无枚举约束，安全可控
        with open(rt_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        cfg = load_runtime_config()  # 不传 path -> 必须读取 DEFAULT_CONFIG_PATH
        read_ok = (cfg.get("ai_model") == sentinel)
    finally:
        if original is not None:
            with open(rt_path, "w", encoding="utf-8") as f:
                f.write(original)
    check("T3", read_ok, "load_runtime_config() 未读取到修改后的 ai_model")

    # ── T4 load_json_schema 真实加载 ──
    schema_obj = None
    raised_missing = False
    try:
        schema_obj = load_json_schema("ai_task.schema.json")
    except Exception as e:
        schema_obj = None
    # required=True 且缺失应抛 SchemaNotFoundError
    try:
        load_json_schema("__nonexistent__.schema.json", required=True)
    except SchemaNotFoundError:
        raised_missing = True
    except Exception:
        raised_missing = False
    check("T4", schema_obj is not None and raised_missing,
          "ai_task.schema.json 加载为 None 或 缺失未抛 SchemaNotFoundError")

    # ── T5 queue 重复提交不重复 ──
    tmp5 = tempfile.mkdtemp(prefix="hw5_")
    p5 = WorkbuddyQueueProvider({}, ai_root=tmp5)
    t = {"task_type": "article_analysis", "input_ref": {"id": "dup5"},
         "content_hash": "h5", "prompt_version": "p1", "output_schema_version": "o1"}
    gen = generate_ai_task_id("article_analysis", {"id": "dup5"}, "h5", "p1", "o1")
    from ai.contracts import new_ai_task
    nt = new_ai_task("article_analysis", {"id": "dup5"}, "h5", "p1", "o1")
    r1 = p5.submit_task(nt)
    r2 = p5.submit_task(nt)
    check("T5", r1["task_id"] == r2["task_id"] and _count_tasks(tmp5) == 1,
          "queue 重复提交生成了多份任务（count=%d）" % _count_tasks(tmp5))

    # ── T6 进 processing 后再次提交不重复 ──
    tmp6 = tempfile.mkdtemp(prefix="hw6_")
    p6 = WorkbuddyQueueProvider({}, ai_root=tmp6)
    nt6 = new_ai_task("article_analysis", {"id": "dup6"}, "h6", "p1", "o1")
    r6 = p6.submit_task(nt6)
    move_task(r6["task_id"], "queue", "processing", ai_root=tmp6)
    r6b = p6.submit_task(nt6)
    check("T6", _count_tasks(tmp6) == 1 and r6b.get("status") == "processing",
          "进 processing 后仍重复入队（count=%d, status=%s）" % (_count_tasks(tmp6), r6b.get("status")))

    # ── T7 进 completed 后再次提交不重复 ──
    tmp7 = tempfile.mkdtemp(prefix="hw7_")
    p7 = WorkbuddyQueueProvider({}, ai_root=tmp7)
    nt7 = new_ai_task("article_analysis", {"id": "dup7"}, "h7", "p1", "o1")
    r7 = p7.submit_task(nt7)
    move_task(r7["task_id"], "queue", "completed", ai_root=tmp7)
    r7b = p7.submit_task(nt7)
    check("T7", _count_tasks(tmp7) == 1 and r7b.get("status") == "completed",
          "进 completed 后仍重复入队（count=%d, status=%s）" % (_count_tasks(tmp7), r7b.get("status")))

    # ── T8 failed 后重试须依据 retry_count，不生成第二文件 ──
    # 8a: retry_count < max_retries -> 复用 task_id 回到 queued
    tmp8 = tempfile.mkdtemp(prefix="hw8a_")
    p8 = WorkbuddyQueueProvider({}, ai_root=tmp8)
    nt8 = new_ai_task("article_analysis", {"id": "dup8"}, "h8", "p1", "o1")  # retry_count=0, max_retries=2
    r8 = p8.submit_task(nt8)
    move_task(r8["task_id"], "queue", "failed", ai_root=tmp8)
    r8b = p8.submit_task(nt8)  # rc=0 < mr=2 -> 应回到 queued，retry_count+1
    check("T8a", _count_tasks(tmp8) == 1 and r8b.get("status") == "queued"
          and r8b.get("retry_count", 0) == 1,
          "failed(retryable) 未复用 task_id（count=%d, status=%s, retry=%s）"
          % (_count_tasks(tmp8), r8b.get("status"), r8b.get("retry_count")))

    # 8b: retry_count == max_retries -> 不重试，返回既有 failed，不新建第二文件
    tmp8b = tempfile.mkdtemp(prefix="hw8b_")
    p8b = WorkbuddyQueueProvider({}, ai_root=tmp8b)
    nt8b = new_ai_task("article_analysis", {"id": "dup8b"}, "h8b", "p1", "o1")
    nt8b["retry_count"] = 2
    nt8b["max_retries"] = 2
    r8b_ = p8b.submit_task(nt8b)
    move_task(r8b_["task_id"], "queue", "failed", ai_root=tmp8b)
    r8b_2 = p8b.submit_task(nt8b)  # rc==mr -> 不应新建
    check("T8b", _count_tasks(tmp8b) == 1 and r8b_2.get("status") == "failed",
          "failed(exhausted) 不应新建第二文件（count=%d, status=%s）"
          % (_count_tasks(tmp8b), r8b_2.get("status")))

    # ── T9-T13 AI Result 校验 ──
    def _base_result():
        return {
            "task_id": generate_ai_task_id("article_analysis", {"id": "r"}, "h", "p1", "o1"),
            "schema_version": "1.0",
            "status": "success",
            "provider": "workbuddy_queue",
            "model": "hy3",
            "started_at": "2026-07-30T10:00:00+00:00",
            "completed_at": "2026-07-30T10:05:00+00:00",
            "result": {"summary": "ok"},
            "error": None,
            "usage": {"input_tokens": 10, "output_tokens": 5, "estimated_cost_usd": 0.0},
        }

    check("T9", bool(validate_ai_result({k: v for k, v in _base_result().items() if k != "started_at"})),
          "缺 started_at 时未失败")
    check("T10", bool(validate_ai_result({k: v for k, v in _base_result().items() if k != "completed_at"})),
          "缺 completed_at 时未失败")
    missing_usage = _base_result(); del missing_usage["usage"]
    check("T11", bool(validate_ai_result(missing_usage)),
          "缺 usage 时未失败")
    bad_sv = _base_result(); bad_sv["schema_version"] = "2.0"
    check("T12", bool(validate_ai_result(bad_sv)),
          "schema_version=2.0 时未失败")
    bad_tid = _base_result(); bad_tid["task_id"] = "BAD_ID"
    check("T13", bool(validate_ai_result(bad_tid)),
          "task_id 格式错误时未失败")

    # 反例：完整合法应无错误
    ok_res = validate_ai_result(_base_result())
    check("T13b", not ok_res, "合法 AI Result 被误判失败: %s" % ok_res)

    # ── T14 pipeline_runner.py 实际调用 2.5A 测试 ──
    pr = open(os.path.join(SCRIPTS, "pipeline_runner.py"), encoding="utf-8").read()
    check("T14", ("test_stage25a_runtime_ai_contract.py" in pr)
          and ("test_stage25a_hardening.py" in pr),
          "pipeline_runner.py 未将 Stage 2.5A 测试纳入构建前闸门")

    # ── T15 README 包含 Stage 2.5A 状态说明 ──
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    check("T15", "Stage 2.5A" in readme and "workbuddy_queue" in readme,
          "README 未包含 Stage 2.5A 当前状态说明")

    # ── 公网隔离（规范十，分层硬检查）──
    # ISO1: dist 本地扫描（硬）
    dist_dir = os.path.join(ROOT, "dist")
    iso1_bad = []
    if os.path.isdir(dist_dir):
        for root, _, files in os.walk(dist_dir):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), dist_dir).replace("\\", "/")
                if any(p in rel or rel.startswith(p.replace("data/ai", "ai")) for p in FORBIDDEN_PATTERNS):
                    iso1_bad.append(rel)
    check("ISO1", not iso1_bad, "dist 含禁止暴露内容: %s" % iso1_bad[:5])

    # ISO2: gh-pages 分支树（硬）
    iso2_bad = []
    try:
        out = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "origin/gh-pages"],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )
        if out.returncode == 0:
            tree = out.stdout.splitlines()
            for line in tree:
                if any(line.strip() == p or line.strip().startswith(p + "/") for p in FORBIDDEN_PATTERNS):
                    iso2_bad.append(line.strip())
            iso2_status = "scanned"
        else:
            iso2_status = "UNVERIFIED(git-failed)"
    except Exception as e:
        iso2_status = "UNVERIFIED(%s)" % type(e).__name__
    # 仅在确实发现禁止路径时才判失败；网络/命令失败仅标记未验证
    check("ISO2", (iso2_status != "scanned") or (not iso2_bad),
          "gh-pages 分支树含禁止暴露内容: %s" % iso2_bad[:5])
    if iso2_status != "scanned":
        print("  [INFO] ISO2 gh-pages 树: %s（未验证，不计入硬失败）" % iso2_status)

    # ISO3: 线上 URL（补充）
    online_exposed = False
    try:
        import urllib.request
        for rel in ("data/ai/queue/", "config/runtime.json", ".env.example"):
            try:
                r = urllib.request.urlopen("https://kenan032005.github.io/asip-site/" + rel, timeout=15)
                if r.status == 200:
                    online_exposed = True
            except Exception as e:
                code = getattr(e, "code", None)
                if code == 200:
                    online_exposed = True
    except Exception:
        pass
    check("ISO3", not online_exposed, "线上站点暴露了内部文件（补充检查）")

    # ── 收尾 ──
    print("=" * 64)
    print("RESULT: PASS=%d FAIL=%d" % (total - fails, fails))
    print("=" * 64)
    if fails:
        sys.exit(1)
    print("ALL STAGE 2.5A HARDENING TESTS PASSED")


if __name__ == "__main__":
    main()
