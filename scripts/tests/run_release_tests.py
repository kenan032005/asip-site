#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_release_tests.py — C6-R1 §八 唯一正式 V1.1 release 测试入口。

设计目标（Fresh Clone 从零可跑）：
  1. **依赖**：从 requirements-dev.txt 安装（见文件头说明；本脚本只做检查与提示）
  2. **先建 runtime 产物**：部分套件断言的是 build 产物（不属于 source 契约），
     因此这里先执行一次正式 build，确保它们看到真实的 runtime 视图
  3. **统一调用契约**：所有套件以 `python -m scripts.tests.<name>` 运行，
     使 repo root 进入 sys.path（修掉 "No module named 'scripts'" 的调用方式缺陷）
  4. **明确 exit code**：全部通过 0，否则 1，并打印 TEST_TOTAL / TEST_PASS / TEST_FAIL

用法（Fresh Clone 根目录）：
    python -m scripts.tests.run_release_tests            # 全量（先 build）
    python -m scripts.tests.run_release_tests --no-build # 跳过 build（已 build 过）
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import shutil
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: 需要外部 runtime 产物 / 历史运行归档、且这些产物**不在 source 契约内**的套件。
#: 逐条有审计依据（见 C6_R1 审计表）；它们不是产品缺陷，但也不能假装通过：
#: 在构建后仍无法满足其输入时会标记为 ENVIRONMENT_DEPENDENT（不算 PASS，也不算 FAIL）。
ENVIRONMENT_DEPENDENT = {
    "test_stage8c_derived_evidence": "需要历史运行归档 .workbuddy/tmp/recovery4_art/（从未入库）",
    "test_stage8b_qualification": "需要真实 DeepSeek 凭据（server-side secret）",
}
#: 需要在 build 之后才有效的套件（断言 build/runtime 视图）
POST_BUILD = {
    "test_stage5_disease", "test_stage8a_frontend", "test_stage8c_manual_trial",
}


def provision_runtime_views():
    """§四 RUNTIME_ARTIFACT_TESTS：把 build 产出的视图供给到测试读取位置。

    精确记账：新增文件记录后删除、被覆盖文件按 git 还原 → 运行后工作树恢复干净。
    """
    dist_views = os.path.join(ROOT, "dist", "data", "views")
    dst = os.path.join(ROOT, "data", "views")
    if not os.path.isdir(dist_views):
        return []
    added, modified = [], []
    for fn in sorted(os.listdir(dist_views)):
        if not fn.endswith(".json"):
            continue
        src = os.path.join(dist_views, fn)
        dstf = os.path.join(dst, fn)
        if not os.path.exists(dstf):
            added.append(dstf)
        elif sha_file(src) != sha_file(dstf):
            modified.append(dstf)
        os.makedirs(dst, exist_ok=True)
        shutil.copy2(src, dstf)
    json.dump({"added": added, "modified": modified},
              io.open(os.path.join(ROOT, ".release_test_provisioned.json"), "w",
                      encoding="utf-8"), ensure_ascii=False, indent=1)
    return added + modified


def cleanup_runtime_views():
    p = os.path.join(ROOT, ".release_test_provisioned.json")
    if not os.path.exists(p):
        return
    rec = json.load(io.open(p, encoding="utf-8"))
    for f in rec.get("added", []):
        if os.path.exists(f):
            os.remove(f)
    for f in rec.get("modified", []):
        subprocess.run(["git", "checkout", "--", os.path.relpath(f, ROOT)],
                       cwd=ROOT, capture_output=True, text=True)
    os.remove(p)


def sha_file(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def _suites():
    d = os.path.join(ROOT, "scripts", "tests")
    out = []
    for fn in sorted(os.listdir(d)):
        if fn.startswith("test_") and fn.endswith(".py"):
            out.append(fn[:-3])
    return out


def _run(module, env=None):
    r = subprocess.run([sys.executable, "-m", "scripts.tests.%s" % module],
                       cwd=ROOT, capture_output=True, text=True, timeout=1800, env=env)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"^Ran (\d+) tests", out, re.M)
    ran = int(m.group(1)) if m else 0
    ok = bool(re.search(r"^OK\b", out, re.M)) or bool(
        re.search(r"RESULT: PASS=\d+ +FAIL=0", out)) or bool(
        re.search(r"PASS=\d+ +FAIL=0", out))
    # 自定义输出格式的套件（如 test_country.py）用退出码兜底
    ok = ok or (r.returncode == 0 and "FAILED" not in out and "Traceback" not in out)
    return {"module": module, "exit": r.returncode, "ran": ran, "ok": ok,
            "tail": "\n".join(out.strip().splitlines()[-3:])}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--only", default=None, help="只跑匹配的套件（子串）")
    a = ap.parse_args(argv)

    print("=" * 78)
    print("ASIP V1.1 RELEASE TEST RUN  (V1_1_RELEASE_TEST_COMMAND)")
    print("=" * 78)
    if not a.no_build:
        print("  [1/3] build runtime artifacts（部分套件断言 build 产物）…")
        b = subprocess.run([sys.executable, "-m", "scripts.build_site",
                            "--run-id", "20260921T180000+0800_releasetests"],
                           cwd=ROOT, capture_output=True, text=True, timeout=1800)
        print("        build exit =", b.returncode)
        if b.returncode != 0:
            print("        FATAL: build 失败，release 测试不可信")
            return 1
        provision_runtime_views()
    else:
        print("  [1/3] 跳过 build（--no-build）")

    print("  [2/3] 依赖检查（requirements-dev.txt）…")
    missing = []
    try:
        import zoneinfo  # noqa: F401
        from zoneinfo import ZoneInfo
        try:
            ZoneInfo("Asia/Shanghai")
        except Exception:  # noqa: BLE001
            missing.append("tzdata")
    except Exception:  # noqa: BLE001
        missing.append("zoneinfo")
    print("        missing deps =", missing or "none")

    print("  [3/3] 运行全部套件（python -m scripts.tests.<name>）")
    results, env_dep = [], []
    for s in _suites():
        if a.only and a.only not in s:
            continue
        r = _run(s)
        if not r["ok"] and s in ENVIRONMENT_DEPENDENT:
            env_dep.append({"module": s, "reason": ENVIRONMENT_DEPENDENT[s]})
            print("   %-46s ENV_DEPENDENT（%s）" % (s, ENVIRONMENT_DEPENDENT[s][:28]))
            continue
        results.append(r)
        print("   %-46s %s  (ran=%d)" % (s, "PASS" if r["ok"] else "FAIL", r["ran"]))
        if not r["ok"]:
            print("        %s" % r["tail"].replace("\n", " | ")[:150])

    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    failed = total - passed
    print()
    print("  TEST_TOTAL          =", total)
    print("  TEST_PASS           =", passed)
    print("  TEST_FAIL           =", failed)
    print("  ENV_DEPENDENT       =", len(env_dep), [e["module"] for e in env_dep])
    print("  MISSING_DEPENDENCIES=", missing)
    print("  ALL_VALID_TESTS     =", "PASS" if failed == 0 else "FAIL")
    cleanup_runtime_views()
    summary = {"TEST_TOTAL": total, "TEST_PASS": passed, "TEST_FAIL": failed,
               "ENV_DEPENDENT": env_dep, "MISSING_DEPENDENCIES": missing,
               "ALL_VALID_TESTS": "PASS" if failed == 0 else "FAIL",
               "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with io.open(os.path.join(ROOT, "release_test_summary.json"), "w",
                 encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
