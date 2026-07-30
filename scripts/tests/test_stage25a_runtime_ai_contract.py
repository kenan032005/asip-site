#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASIP Stage 2.5A — 运行配置与 AI 接口契约 验收测试（TDD）。

对应规范三 / 十三：先写失败测试，再实现功能；本文件在实现前会因
scripts/ai 不存在而 ImportError 失败，实现后全部通过。

硬性断言（至少 15 项）：
  T1  runtime.json 通过 Schema
  T2  默认 runtime 为 workbuddy_local
  T3  默认 Provider 为 workbuddy_queue
  T4  paid fallback 默认为 false
  T5  cloud schedule 默认为 false
  T6  workbuddy_queue 只写队列，不调用外部网络
  T7  相同任务重复提交不会重复入队（幂等）
  T8  task_id 稳定
  T9  cache_key 稳定
  T10 prompt 版本变化会产生新缓存键
  T11 openai_api 未启用时不会检查或调用 Key
  T12 明确选择 openai_api 但无 Key 时失败关闭
  T13 未知 Provider 失败
  T14 dist / gh-pages 构建内容不包含 data/ai
  T15 Stage 2 全部回归测试仍通过

仓库安全扫描：
  S1  不存在真实 API Key
  S2  不存在自动付费 fallback
  S3  不存在直接调用 Hy3 的 Python 代码
  S4  不存在直接调用 OpenAI API 的生产代码
"""

import os
import sys
import json
import re
import glob
import tempfile
import subprocess
import unittest.mock as mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import ai  # noqa: E402
from ai.config import (  # noqa: E402
    load_runtime_config,
    get_api_key,
    DEFAULT_RUNTIME,
    VALID_PROVIDERS,
    PAID_PROVIDERS,
)
from ai.identifiers import generate_ai_task_id, generate_ai_cache_key  # noqa: E402
from ai.contracts import (  # noqa: E402
    validate_ai_task,
    validate_ai_result,
    new_ai_task,
)
from ai.registry import get_provider, list_providers  # noqa: E402
from ai.workbuddy_queue_provider import WorkbuddyQueueProvider, count_queued, count_failed  # noqa: E402
from ai.disabled_provider import DisabledProvider  # noqa: E402
from ai.exceptions import ProviderNotConfigured  # noqa: E402


def _check_schema(obj, schema):
    """极简 JSON Schema 校验（type/required/enum/additionalProperties）。"""
    errs = []
    if schema.get("type") == "object":
        if not isinstance(obj, dict):
            return ["not an object"]
        for r in schema.get("required", []):
            if r not in obj:
                errs.append("missing required: %s" % r)
        props = schema.get("properties", {})
        for k, v in obj.items():
            if k not in props:
                if schema.get("additionalProperties") is False:
                    errs.append("additional property not allowed: %s" % k)
                continue
            spec = props[k]
            t = spec.get("type")
            if t == "string" and not isinstance(v, str):
                errs.append("%s must be string" % k)
            if t == "boolean" and not isinstance(v, bool):
                errs.append("%s must be boolean" % k)
            if "enum" in spec and v not in spec["enum"]:
                errs.append("%s=%r not in enum" % (k, v))
    return errs


def main():
    print("=" * 64)
    print("ASIP Stage 2.5A — Runtime & AI Contract 验收测试")
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

    # ── T1 runtime.json 通过 Schema ──
    runtime_path = os.path.join(ROOT, "config", "runtime.json")
    schema_path = os.path.join(ROOT, "schemas", "runtime_config.schema.json")
    runtime_cfg = json.load(open(runtime_path, encoding="utf-8"))
    schema = json.load(open(schema_path, encoding="utf-8"))
    errs = _check_schema(runtime_cfg, schema)
    check("T1", not errs, "runtime.json 未通过 Schema: %s" % errs)

    # ── T2 / T3 / T4 / T5 默认值 ──
    cfg = load_runtime_config(runtime_path)
    check("T2", cfg["runtime_mode"] == "workbuddy_local", "runtime_mode=%r" % cfg["runtime_mode"])
    check("T3", cfg["ai_provider"] == "workbuddy_queue", "ai_provider=%r" % cfg["ai_provider"])
    check("T4", cfg["allow_paid_fallback"] is False, "allow_paid_fallback=%r" % cfg["allow_paid_fallback"])
    check("T5", cfg["cloud_schedule_enabled"] is False, "cloud_schedule_enabled=%r" % cfg["cloud_schedule_enabled"])

    # ── T6 workbuddy_queue 只写队列，不调用外部网络 ──
    tmp = tempfile.mkdtemp(prefix="ai_test_")
    with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network called!")) as m_net, \
         mock.patch("socket.create_connection", side_effect=AssertionError("network called!")) as m_sock:
        prov = WorkbuddyQueueProvider({}, ai_root=tmp)
        task = new_ai_task("article_analysis", {"id": "x"}, "h123", "p1", "o1")
        res = prov.submit_task(task)
        prov.health_check()
        prov.get_task_status(res["task_id"])
        prov.load_result(res["task_id"])
        check(
            "T6",
            (not m_net.called) and (not m_sock.called) and res.get("status") == "queued",
            "队列 Provider 不应发起任何外部网络请求",
        )

    # ── T7 幂等：相同任务重复提交不重复入队 ──
    tmp2 = tempfile.mkdtemp(prefix="ai_idem_")
    prov2 = WorkbuddyQueueProvider({}, ai_root=tmp2)
    t = new_ai_task("article_analysis", {"id": "dup"}, "h123", "p1", "o1")
    r1 = prov2.submit_task(t)
    r2 = prov2.submit_task(t)
    qfiles = [f for f in os.listdir(prov2._dirs["queue"]) if f.endswith(".json")]
    check(
        "T7",
        r1["task_id"] == r2["task_id"] and len(qfiles) == 1 and r1["status"] == "queued",
        "相同 cache_key 不应重复入队（files=%d）" % len(qfiles),
    )

    # ── T8 / T9 task_id / cache_key 稳定 ──
    id_a = generate_ai_task_id("article_analysis", {"id": "a"}, "h", "p1", "o1")
    id_b = generate_ai_task_id("article_analysis", {"id": "a"}, "h", "p1", "o1")
    check("T8", id_a == id_b and id_a.startswith("AIT_") and len(id_a) == 28, "task_id 不稳定: %r" % id_a)
    ck_a = generate_ai_cache_key("article_analysis", {"id": "a"}, "h", "p1", "o1")
    ck_b = generate_ai_cache_key("article_analysis", {"id": "a"}, "h", "p1", "o1")
    check("T9", ck_a == ck_b and ck_a.startswith("cache:"), "cache_key 不稳定: %r" % ck_a)

    # ── T10 prompt 版本变化产生新缓存键 ──
    ck_base = generate_ai_cache_key("article_analysis", {"id": "a"}, "h", "p1", "o1")
    ck_newp = generate_ai_cache_key("article_analysis", {"id": "a"}, "h", "p2", "o1")
    check("T10", ck_base != ck_newp, "prompt_version 变化未产生新 cache_key")

    # ── T11 openai_api 未启用时不会检查或调用 Key ──
    with mock.patch.object(ai.config, "get_api_key", side_effect=AssertionError("key accessed!")) as mk:
        p = get_provider()  # 默认 workbuddy_queue
        check(
            "T11",
            (not mk.called) and isinstance(p, WorkbuddyQueueProvider),
            "默认未启用付费 Provider 时不应触碰 API Key",
        )

    # ── T12 明确选择 openai_api 但无 Key -> 失败关闭 ──
    # 注意：Windows 上 mock.patch.dict(os.environ) 在 __exit__ 恢复巨变量时会抛
    # "environment variable is longer than 32767 characters"，故此处手动仅操作相关键。
    _oai = os.environ.pop("OPENAI_API_KEY", None)
    _gen = os.environ.pop("GENERIC_AI_API_KEY", None)
    try:
        raised = False
        try:
            get_provider("openai_api")
        except ProviderNotConfigured:
            raised = True
        check("T12", raised, "显式选择 openai_api 且无 Key 时未失败关闭")
    finally:
        # 仅恢复我们操作过的两个键，绝不触碰其它（可能超长的）环境变量
        if _oai is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = _oai
        if _gen is None:
            os.environ.pop("GENERIC_AI_API_KEY", None)
        else:
            os.environ["GENERIC_AI_API_KEY"] = _gen

    # ── T13 未知 Provider 失败 ──
    raised = False
    try:
        get_provider("not_a_real_provider")
    except Exception:
        raised = True
    check("T13", raised, "未知 Provider 未报错")

    # ── T14 dist / gh-pages 构建内容不包含 data/ai ──
    bsrc = open(os.path.join(SCRIPTS, "build_site.py"), encoding="utf-8").read()
    m = re.search(r"PUBLIC_DATA_ALLOWLIST\s*=\s*\[([\s\S]*?)\]", bsrc)
    allow = re.findall(r"[\"']([^\"']+)[\"']", m.group(1)) if m else []
    bad_allow = [p for p in allow if "ai" in p.lower()]
    check("T14a", not bad_allow, "build_site 白名单含 data/ai: %s" % bad_allow)

    dist_dir = os.path.join(ROOT, "dist")
    found_in_dist = []
    if os.path.isdir(dist_dir):
        for root, _, files in os.walk(dist_dir):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), dist_dir).replace("\\", "/")
                if "data/ai" in rel or rel.startswith("ai/"):
                    found_in_dist.append(rel)
    check("T14b", not found_in_dist, "dist 含 data/ai: %s" % found_in_dist[:5])

    # 线上 gh-pages 不应暴露 data/ai（尽力验证：仅当返回 200 才算失败）
    gh_status = None
    try:
        import urllib.request
        try:
            r = urllib.request.urlopen(
                "https://kenan032005.github.io/asip-site/data/ai/queue/", timeout=15
            )
            gh_status = r.status
        except Exception as e:
            gh_status = getattr(e, "code", "ERR")
    except Exception:
        gh_status = "SKIP"
    check("T14c", gh_status in (404, 403, 400, "SKIP", "ERR"), "线上 gh-pages 暴露了 data/ai (HTTP %s)" % gh_status)

    # ── T15 Stage 2 全部回归测试仍通过 ──
    regress = [
        "scripts/tests/test_stage2_frontend_final.py",
        "scripts/tests/test_stage2_closeout.py",
        "scripts/tests/test_stage2_schema_repo.py",
        "scripts/data/validate_stage2.py",
        "scripts/validate_pipeline.py",
    ]
    regress_ok = True
    for rel in regress:
        try:
            out = subprocess.run(
                [sys.executable, rel], cwd=ROOT, capture_output=True, text=True, timeout=240
            )
            ok = out.returncode == 0
        except Exception as e:
            ok = False
            out = type("O", (), {"stdout": str(e), "stderr": ""})()
        if not ok:
            regress_ok = False
            print("    [regress FAIL] %s rc=%s" % (rel, getattr(out, "returncode", "?")))
            tail = (out.stdout or "")[-300:]
            print("    " + tail.replace("\n", "\n    "))
    check("T15", regress_ok, "Stage 2 回归套件未全部通过")

    # ── S1 不存在真实 API Key ──
    key_patterns = [
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(OPENAI_API_KEY|GENERIC_AI_API_KEY)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{12,}"),
        re.compile(r"[\"']?api_?key[\"']?\s*[:=]\s*[\"'](sk-|AKIA|[A-Za-z0-9]{24,})"),
    ]
    key_viol = []
    for f in glob.glob(os.path.join(ROOT, "**"), recursive=True):
        if not f.endswith((".py", ".json", ".md", ".example", ".yaml", ".yml")):
            continue
        rp = f.replace("\\", "/")
        if ".git" in rp or "/dist/" in rp or "__pycache__" in rp or "data/ai" in rp:
            continue
        try:
            t = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for pat in key_patterns:
            mm = pat.search(t)
            if mm:
                key_viol.append((rp, mm.group(0)[:14]))
                break
    check("S1", not key_viol, "发现疑似真实密钥: %s" % key_viol[:5])

    # ── S2 不存在自动付费 fallback ──
    reg_src = open(os.path.join(SCRIPTS, "ai", "registry.py"), encoding="utf-8").read()
    cfg_src = open(os.path.join(SCRIPTS, "ai", "config.py"), encoding="utf-8").read()
    danger_assign = re.search(r"ai_provider\"?\s*[:=]\s*[\"'](openai_api|generic_api)[\"']", reg_src)
    paid_in_cfg_default = ('"ai_provider": "openai_api"' in cfg_src) or ('"ai_provider": "generic_api"' in cfg_src)
    check("S2", (not danger_assign) and (not paid_in_cfg_default),
          "存在自动切换到付费 Provider 的逻辑 (assign=%s, cfg_default=%s)" % (bool(danger_assign), paid_in_cfg_default))

    # ── S3 不存在直接调用 Hy3 的 Python 代码 ──
    hy3_viol = []
    for f in glob.glob(os.path.join(SCRIPTS, "**", "*.py"), recursive=True):
        if "tests" in f.replace("\\", "/"):
            continue
        t = open(f, encoding="utf-8", errors="ignore").read()
        if re.search(r"^\s*(import|from)\s+hy3", t, re.M) or re.search(r"\bhy3\.\w", t) or re.search(r"Hy3\(", t):
            hy3_viol.append(f.replace("\\", "/"))
    check("S3", not hy3_viol, "发现直接调用 Hy3 的代码: %s" % hy3_viol)

    # ── S4 不存在直接调用 OpenAI API 的生产代码 ──
    oai_viol = []
    for f in glob.glob(os.path.join(SCRIPTS, "ai", "*.py")):
        t = open(f, encoding="utf-8", errors="ignore").read()
        if re.search(r"^\s*(import|from)\s+openai", t, re.M) or re.search(r"\bOpenAI\(", t) or re.search(r"\bopenai\.\w", t):
            oai_viol.append(os.path.basename(f))
    check("S4", not oai_viol, "scripts/ai 直接调用 OpenAI API: %s" % oai_viol)

    # ── 收尾 ──
    print("=" * 64)
    print("RESULT: PASS=%d FAIL=%d" % (total - fails, fails))
    print("=" * 64)
    if fails:
        sys.exit(1)
    print("ALL STAGE 2.5A CONTRACT TESTS PASSED")


if __name__ == "__main__":
    main()
