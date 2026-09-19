#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c3_commit_guard.py —— C3 AI 产物 commit-back 的 **Unicode-safe** 白名单守卫。

背景（C3R2）：真实 AI run 成功，但 commit-back 被拒：
`git diff --cached --name-only` 默认对非 ASCII 路径做 quoted/octal 转义
（`data/intelligence/ai/country_analysis/\344\270\255\346\226\207.json`），
于是合法的中文 country_analysis 路径匹配不上白名单 → OUT-OF-WHITELIST。

修法：**用 NUL 分隔的原始路径**（`git diff --cached --name-only -z`），
逐条按原始字节字符串匹配，不解析任何 Git 引号形式。
`core.quotePath=false` 只作为辅助（便于人读日志），不作为判定依据。

白名单范围**保持不变**（不得扩大）：只允许 C3 既定合法产物。
"""
import argparse
import os
import subprocess
import sys

#: 允许 commit-back 的路径前缀（与 workflow 既有白名单一致，不得放宽）
WHITELIST_PREFIXES = (
    "data/intelligence/ai/localization/",
    "data/intelligence/ai/event_analysis/",
    "data/intelligence/ai/country_analysis/",
    "data/intelligence/ai/homepage_analysis/",
    "data/intelligence/ai/runs/",
    "data/views/ai_intelligence.json",
    "data/canonical/articles.json",
    "data/views/news_stream.json",
)

#: 明确禁止（即使落在白名单目录内也不允许）
FORBIDDEN_SUBSTRINGS = ("raw_response", "prompt_debug", "debug", ".env", "secret",
                        "credential", "authorization")
FORBIDDEN_SUFFIXES = (".zip", ".pem", ".key", ".log", ".bak", ".tmp")
FORBIDDEN_EXACT = ("c3_run_report_run1.json", "c3_run_report_run2.json",
                   "c3_run_report_ci.json", "run1.json", "run2.json",
                   "staged.txt", "staged_paths.txt")


def is_whitelisted(path):
    """path 必须是 POSIX 风格、未转义的**原始**仓库相对路径。"""
    p = str(path)
    if p.startswith("/") or p.startswith("./") or "\\" in p:
        p = p.replace("\\", "/")
        if p.startswith("/"):
            return False
        if p.startswith("./"):
            p = p[2:]
    base = p.rsplit("/", 1)[-1]
    if base in FORBIDDEN_EXACT:
        return False
    low = p.lower()
    if any(s in low for s in FORBIDDEN_SUBSTRINGS):
        return False
    if low.endswith(FORBIDDEN_SUFFIXES):
        return False
    return any(p == w or p.startswith(w) for w in WHITELIST_PREFIXES)


def check(paths):
    """返回 (ok, allowed, rejected)。paths 为**原始**路径列表。"""
    allowed, rejected = [], []
    for p in paths:
        p = p.strip("\n")
        if not p:
            continue
        if is_whitelisted(p):
            allowed.append(p)
        else:
            rejected.append(p)
    return (not rejected), allowed, rejected


def staged_paths(root="."):
    """NUL 分隔读取 staged 原始路径（不经过 Git 的引号/octal 转义）。"""
    r = subprocess.run(["git", "diff", "--cached", "--name-only", "-z", "--no-renames"],
                       cwd=root, capture_output=True)
    out = r.stdout.decode("utf-8", "surrogateescape")
    return [p for p in out.split("\0") if p]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--paths", nargs="*", help="直接给出路径做判定（不读 git）")
    ap.add_argument("--list-only", action="store_true", help="只打印，不因越界返回非零")
    a = ap.parse_args()

    paths = a.paths if a.paths else staged_paths(a.root)
    ok, allowed, rejected = check(paths)

    print("STAGED_TOTAL = %d" % len(paths))
    print("ALLOWED      = %d" % len(allowed))
    print("REJECTED     = %d" % len(rejected))
    for p in rejected:
        print("OUT-OF-WHITELIST: %s" % p)
    # 便于人读：同时用 quotePath=false 的形式打印一遍（仅展示，不参与判定）
    for p in allowed[:5]:
        sys.stdout.write("  allowed: %s\n" % p)
    print("OUT_OF_WHITELIST_COUNT = %d" % len(rejected))
    print("UNICODE_COMMIT_GUARD = %s" % ("PASS" if ok else "FAIL"))
    if a.list_only:
        return 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
