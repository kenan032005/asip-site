#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_no_local_paths.py —— ASIP 第二阶段收尾 第九节 路径扫描测试

扫描仓库工作区（main 提交内容）、dist/、data/public/ 中的文本文件，
禁止出现本地机器路径（如 C:\\Users\\<name>\\...、/Users/<name>/...、
/home/<name>/...）。

白名单：
- scripts/pipeline_core.py 中 redact_local_paths 的正则模式本身；
- 本测试文件自身的模式定义。

退出码：FAIL>0 → 1；否则 0。
"""

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

# 本地路径特征（不含正则元字符描述，仅匹配真实路径实例）
WIN_PAT = re.compile(r"[A-Za-z]:(?:\\\\|\\|/)+Users(?:\\\\|\\|/)+[A-Za-z0-9_.-]+")
POSIX_PAT = re.compile(r"/(?:home|Users)/[A-Za-z0-9_.-]+/")

# 允许包含"模式字符串"的文件（它们描述正则，不含真实用户名路径实例）
ALLOW_FILES = {
    "scripts/pipeline_core.py",
    "scripts/tests/test_no_local_paths.py",
}

# 允许的占位符（清洗后的产物）
PLACEHOLDERS = ("<repo>", "<local-path-redacted>")

TEXT_EXTS = {
    ".py", ".json", ".md", ".html", ".css", ".js", ".txt", ".yml",
    ".yaml", ".xml", ".csv", ".gitignore",
}

SKIP_DIRS = {".git", "__pycache__", "node_modules", "backup", ".workbuddy"}

PASS = 0
FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  {extra}")


def iter_text_files(base: Path, include_hidden=False):
    for dirpath, dirnames, filenames in os.walk(base):
        if include_hidden:
            # dist/ 会整体发布到 gh-pages，隐藏目录同样会被发布，必须一并扫描
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        else:
            # 跳过隐藏目录（.git、.backups、.trash_* 等本地产物，不属于 main 提交内容）
            dirnames[:] = [d for d in dirnames
                           if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() in TEXT_EXTS or fn == ".gitignore":
                yield p


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def scan(base: Path, label: str, include_hidden=False):
    """返回 [(相对路径, 命中片段)]"""
    hits = []
    if not base.exists():
        return hits, False
    for p in iter_text_files(base, include_hidden=include_hidden):
        r = rel(p)
        if r in ALLOW_FILES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pat in (WIN_PAT, POSIX_PAT):
            m = pat.search(text)
            if m:
                hits.append((r, m.group(0)[:80]))
                break
    return hits, True


def main():
    print("=== 第九节：本地路径扫描 ===")

    # 1) 仓库主工作区（排除 dist，dist 单独扫）
    repo_hits = []
    for p in iter_text_files(ROOT):
        r = rel(p)
        if r.startswith("dist/") or r in ALLOW_FILES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pat in (WIN_PAT, POSIX_PAT):
            m = pat.search(text)
            if m:
                repo_hits.append((r, m.group(0)[:80]))
                break
    check("仓库工作区无本地路径", not repo_hits,
          "; ".join(f"{f}: {s}" for f, s in repo_hits[:5]))

    # 2) dist/（若存在；发布内容，含隐藏目录一并扫描）
    dist_hits, dist_exists = scan(ROOT / "dist", "dist", include_hidden=True)
    if dist_exists:
        check("dist/ 无本地路径", not dist_hits,
              "; ".join(f"{f}: {s}" for f, s in dist_hits[:5]))
    else:
        print("  ⏭️ dist/ 不存在，跳过")

    # 3) data/public/
    pub_hits, pub_exists = scan(ROOT / "data" / "public", "public")
    check("data/public/ 存在", pub_exists)
    if pub_exists:
        check("data/public/ 无本地路径", not pub_hits,
              "; ".join(f"{f}: {s}" for f, s in pub_hits[:5]))

    # 4) migration_state.json 明确复查
    ms = ROOT / "data" / "canonical" / "migration_state.json"
    if ms.exists():
        t = ms.read_text(encoding="utf-8")
        check("migration_state.json 无本地路径",
              not WIN_PAT.search(t) and not POSIX_PAT.search(t))

    # 5) logs/ 明确复查
    logs_hits, logs_exists = scan(ROOT / "logs", "logs")
    if logs_exists:
        check("logs/ 无本地路径", not logs_hits,
              "; ".join(f"{f}: {s}" for f, s in logs_hits[:5]))

    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
