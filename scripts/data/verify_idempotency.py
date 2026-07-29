# -*- coding: utf-8 -*-
"""Stage 2B 幂等性验证脚本（独立运行，避免 shell 链断裂）。

流程：
  1. 从 pre-stage2 基线恢复 5 个旧数据池文件（git checkout）
  2. 删除 data/canonical 与 data/public（文件数少，安全）
  3. 执行 apply #1，记录 8 个关键文件 SHA-256 与计数
  4. 执行 apply #2，再次记录
  5. 对比：全部一致 -> IDEMPOTENT: PASS，否则 FAIL（退出码 1）

结果写入 data/canonical/idempotency_report.json 并打印。
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
# git 可执行文件：优先 GIT_EXE 环境变量，其次 PATH，最后常见便携版位置
import shutil as _sh
GIT = (os.environ.get("GIT_EXE") or _sh.which("git")
       or os.path.expanduser("~/.workbuddy/vendor/PortableGit/cmd/git.exe"))
PY = sys.executable

LEGACY_FILES = [
    "data/events.json",
    "data/raw_candidates.json",
    "data/pending_events.json",
    "data/quarantine_events.json",
    "data/sources.json",
]

CHECK_FILES = [
    "data/canonical/articles.json",
    "data/canonical/event_clusters.json",
    "data/canonical/quarantine.json",
    "data/sources.json",
    "data/events.json",
    "data/pending_events.json",
    "data/raw_candidates.json",
    "data/quarantine_events.json",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, **kw):
    print(">>", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", **kw)
    if r.stdout:
        print(r.stdout[-3000:])
    if r.returncode != 0:
        print("STDERR:", (r.stderr or "")[-2000:])
        raise SystemExit("command failed: %s" % cmd)
    return r


def counts():
    out = {}
    for name, key in [("articles", "items"), ("event_clusters", "items"),
                      ("quarantine", "items")]:
        p = os.path.join(ROOT, "data", "canonical", name + ".json")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            items = d.get("items") or []
            out[name] = len(items)
            ids = [it.get("article_id") or it.get("event_id") or it.get("quarantine_id") for it in items]
            out[name + "_unique_ids"] = len(set(ids))
    p = os.path.join(ROOT, "data", "public", "published_events.json")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        out["published_events"] = len(d.get("items") or d.get("events") or [])
    return out


def snapshot():
    return {f: sha256(os.path.join(ROOT, f)) for f in CHECK_FILES
            if os.path.exists(os.path.join(ROOT, f))}


def main():
    # 1. restore legacy baseline
    run([GIT, "checkout", "3c61e85", "--"] + LEGACY_FILES)
    # 2. move canonical/public aside (rename, avoid delete protection)
    import time
    stamp = time.strftime("%H%M%S")
    for d in ("data/canonical", "data/public"):
        p = os.path.join(ROOT, d)
        if os.path.isdir(p):
            dst = os.path.join(ROOT, "data", ".trash_%s_%s" % (os.path.basename(d), stamp))
            print("moving %s -> %s" % (d, dst))
            shutil.move(p, dst)

    # 3. apply #1
    print("\n===== APPLY 1 =====", flush=True)
    run([PY, os.path.join(HERE, "migrate_stage2.py"), "--apply"])
    s1 = snapshot()
    c1 = counts()

    # 4. apply #2
    print("\n===== APPLY 2 =====", flush=True)
    run([PY, os.path.join(HERE, "migrate_stage2.py"), "--apply"])
    s2 = snapshot()
    c2 = counts()

    # 5. compare
    same = True
    diffs = []
    for f in CHECK_FILES:
        h1, h2 = s1.get(f), s2.get(f)
        ok = h1 == h2 and h1 is not None
        if not ok:
            same = False
            diffs.append(f)
        print("%-42s %s" % (f, "SAME" if ok else "DIFF  %s vs %s" % (h1, h2)))
    if c1 != c2:
        same = False
        diffs.append("counts")

    report = {
        "apply1_counts": c1,
        "apply2_counts": c2,
        "hashes_apply1": s1,
        "hashes_apply2": s2,
        "identical": same,
        "diff_files": diffs,
    }
    outp = os.path.join(ROOT, "data", "canonical", "idempotency_report.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\ncounts apply1:", json.dumps(c1, ensure_ascii=False))
    print("counts apply2:", json.dumps(c2, ensure_ascii=False))
    print("\nIDEMPOTENT:", "PASS" if same else "FAIL")
    sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
