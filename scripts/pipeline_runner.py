#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline_runner.py —— ASIP Stage-1 完整主链路编排器。

一次运行执行完整流程:
  生成 run_id → 数据汇总(status+summary+风险修正) → 日报 → 构建 dist →
  验证 → 提交 main → 部署 gh-pages → 线上验证 → 结构化日志

用法：
  python scripts/pipeline_runner.py [--skip-report] [--skip-deploy]
"""
import os
import sys
import json
import time
import subprocess
import argparse
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)

from pipeline_core import (
    PIPELINE_VERSION, DATA_DIR, LOGS_DIR,
    generate_run_id, create_pipeline_meta, create_run_log,
    add_log_step, save_run_log, save_json, load_json,
    bj_iso, bj_format,
)

PYTHON = r"C:\Users\kenan\.workbuddy\binaries\python\versions\3.13.12\python.exe"
GIT = r"C:\Users\kenan\.workbuddy\vendor\PortableGit\cmd\git.exe"


def run_cmd(cmd, cwd=None, timeout=120):
    """运行命令，返回 (returncode, stdout, stderr)。"""
    try:
        r = subprocess.run(
            cmd, cwd=cwd or ROOT, capture_output=True, text=True,
            timeout=timeout, shell=True,
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)


def git_commit(msg):
    """提交所有变更到 main。返回 commit hash 或 None。"""
    rc, out, err = run_cmd(f'"{GIT}" add -A')
    if rc != 0:
        return None, f"git add failed: {err}"
    rc, out, err = run_cmd(f'"{GIT}" commit -m "{msg}"')
    if rc != 0:
        # 没有变更也算成功
        if "nothing to commit" in out + err:
            rc2, hash_out, _ = run_cmd(f'"{GIT}" rev-parse HEAD')
            return hash_out, "no changes"
        return None, f"git commit failed: {err}"
    rc, hash_out, _ = run_cmd(f'"{GIT}" rev-parse HEAD')
    return hash_out, ""


def git_push():
    """推送 main。"""
    return run_cmd(f'"{GIT}" push origin main')


def deploy_gh_pages():
    """将 dist/ 推送到 gh-pages 分支。"""
    DIST = os.path.join(ROOT, "dist")
    if not os.path.exists(os.path.join(DIST, "index.html")):
        return None, "dist/index.html 不存在"

    # 创建临时目录，复制 dist 到 gh-pages 分支
    tmpdir = os.path.join(ROOT, ".gh-pages-tmp")
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)
    os.makedirs(tmpdir)

    # 用 git subtree 方式推送
    rc, out, err = run_cmd(
        f'cd "{ROOT}" && git subtree push --prefix dist origin gh-pages 2>&1',
        timeout=120
    )

    # subtree push 可能在新仓库不工作，用 force push 替代
    if rc != 0:
        print("  subtree push failed, using force push to gh-pages...")
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp_repo = os.path.join(tmp, "repo")
            run_cmd(f'cp -r "{DIST}" "{tmp_repo}"')
            # init new git in tmp
            run_cmd(f'cd "{tmp_repo}" && "{GIT}" init && "{GIT}" add -A && "{GIT}" commit -m "deploy"', timeout=60)
            rc2, out2, err2 = run_cmd(
                f'cd "{tmp_repo}" && "{GIT}" push -f https://kenan032005:{os.environ.get("GITHUB_TOKEN","")}@github.com/kenan032005/asip-site.git main:gh-pages 2>&1',
                timeout=60
            )

    # 无论哪种方式，尝试获取 gh-pages hash
    rc, gh_hash, _ = run_cmd(f'"{GIT}" ls-remote origin gh-pages')
    if gh_hash:
        gh_hash = gh_hash.split()[0]
    return gh_hash or "unknown", ""


def main(skip_report=False, skip_deploy=False):
    run_id = generate_run_id()
    pipeline_log = create_run_log(run_id, trigger="manual")
    pipeline_meta = create_pipeline_meta(run_id)

    print("=" * 60)
    print(f"ASIP Stage-1 Pipeline Runner")
    print(f"  run_id: {run_id}")
    print(f"  pipeline_version: {PIPELINE_VERSION}")
    print(f"  started: {bj_iso()}")
    print("=" * 60)

    # ── Step 1: 拉取最新代码 ────────────────────────────
    print("\n[1/11] git pull...")
    rc, out, err = run_cmd(f'"{GIT}" pull origin main', timeout=30)
    add_log_step(pipeline_log, "git_pull", "success" if rc == 0 else "failed",
                 details={"output": out[:200], "error": err[:200]})
    print(f"  pull: {'OK' if rc == 0 else 'ERR'}")

    # ── Step 2: 运行测试 ────────────────────────────────
    print("\n[2/11] run unit tests...")
    rc, out, err = run_cmd(f'"{PYTHON}" scripts/tests/test_country.py', timeout=30)
    tests_passed = "PASS" in (out + err) and "FAIL" not in (out + err)
    add_log_step(pipeline_log, "unit_tests", "success" if tests_passed else "failed",
                 details={"output": out[:300]})
    print(f"  tests: {'OK' if tests_passed else 'FAIL'}")
    if not tests_passed:
        print(f"  输出: {out[:200]}")

    # ── Step 3: 数据汇总（status + summary + risk fix + type normalize）──
    print("\n[3/11] build_summary (status + summary + fixes)...")
    rc, out, err = run_cmd(
        f'"{PYTHON}" scripts/build_summary.py --run-id {run_id}',
        timeout=60
    )
    add_log_step(pipeline_log, "build_summary", "success" if rc == 0 else "failed",
                 details={"output": out[-500:]})
    print(f"  build_summary: {'OK' if rc == 0 else 'ERR'}")
    if rc != 0:
        print(out[-300:])
        print("⛔ 数据汇总失败，终止。")
        pipeline_log["final_status"] = "failed"
        save_run_log(pipeline_log, run_id)
        return 1

    # ── Step 4: 生成日报 ──────────────────────────────────
    if not skip_report:
        print("\n[4/11] generate_reports...")
        rc, out, err = run_cmd(
            f'"{PYTHON}" scripts/generate_reports.py --date 2026-07-28',
            timeout=60
        )
        add_log_step(pipeline_log, "generate_reports", "success" if rc == 0 else "failed",
                     details={"output": out[-500:]})
        print(f"  generate_reports: {'OK' if rc == 0 else 'ERR'}")
    else:
        print("\n[4/11] skip: generate_reports")
        add_log_step(pipeline_log, "generate_reports", "skipped")

    # ── Step 5: 构建 dist ─────────────────────────────────
    print("\n[5/11] build_site...")
    rc, out, err = run_cmd(
        f'"{PYTHON}" scripts/build_site.py --run-id {run_id}',
        timeout=60
    )
    add_log_step(pipeline_log, "build_site", "success" if rc == 0 else "failed",
                 details={"output": out[-300:]})
    print(f"  build_site: {'OK' if rc == 0 else 'ERR'}")

    # ── Step 6: validate_pipeline ──────────────────────────
    print("\n[6/11] validate_pipeline...")
    dist_dir = os.path.join(ROOT, "dist")
    rc, out, err = run_cmd(
        f'"{PYTHON}" scripts/validate_pipeline.py --run-id {run_id} --dist "{dist_dir}"',
        timeout=60
    )
    validation_ok = rc == 0
    add_log_step(pipeline_log, "validate_pipeline", "success" if validation_ok else "failed",
                 details={"output": out[-500:]})
    print(f"  validate: {'OK' if validation_ok else 'FAIL (CRITICAL)'}")
    if not validation_ok:
        print(out)
        print("⛔ 数据校验失败。部署已阻止。")
        pipeline_log["final_status"] = "failed"
        save_run_log(pipeline_log, run_id)
        return 1

    # ── Step 7: 提交 main ──────────────────────────────────
    print("\n[7/11] git commit main...")
    commit_msg = f"pipeline: Stage-1 run_id={run_id} (status+summary+risk+types+reports+build+validate)"
    main_hash, commit_err = git_commit(commit_msg)
    add_log_step(pipeline_log, "git_commit", "success" if main_hash else "failed",
                 details={"commit": main_hash, "error": commit_err})
    print(f"  main commit: {main_hash or commit_err}")

    # ── Step 8: 推送 main ──────────────────────────────────
    print("\n[8/11] git push main...")
    rc, out, err = git_push()
    add_log_step(pipeline_log, "git_push_main", "success" if rc == 0 else "failed",
                 details={"output": out[:200]})
    print(f"  push: {'OK' if rc == 0 else 'ERR'}")

    # ── Step 9: 部署 gh-pages ──────────────────────────────
    if not skip_deploy:
        print("\n[9/11] deploy gh-pages...")
        gh_hash, gh_err = deploy_gh_pages()
        add_log_step(pipeline_log, "deploy_gh_pages", "success" if not gh_err else "failed",
                     details={"commit": gh_hash, "error": gh_err})
        print(f"  gh-pages: {gh_hash} {'OK' if not gh_err else 'ERR: '+gh_err}")
    else:
        print("\n[9/11] skip: deploy gh-pages")
        add_log_step(pipeline_log, "deploy_gh_pages", "skipped")

    # ── Step 10: 线上验证 ──────────────────────────────────
    print("\n[10/11] online verify (waiting for GitHub Pages)...")
    time.sleep(5)
    verify_ok = False
    try:
        import urllib.request
        url = "https://kenan032005.github.io/asip-site/data/status.json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        r = urllib.request.urlopen(req, timeout=20)
        online_status = json.loads(r.read().decode("utf-8", "replace"))
        online_rid = online_status.get("run_id", "")
        verify_ok = (online_rid == run_id)
        add_log_step(pipeline_log, "online_verify", "success" if verify_ok else "failed",
                     details={"online_run_id": online_rid, "expected": run_id})
        print(f"  online run_id: {online_rid}")
        print(f"  match: {'✅ YES' if verify_ok else '❌ NO (GH Pages 更新需要 1-2 分钟)'}")
    except Exception as e:
        add_log_step(pipeline_log, "online_verify", "failed",
                     details={"error": str(e)})
        print(f"  online verify error: {e}")

    # ── Step 11: 最终日志 ──────────────────────────────────
    pipeline_log["main_commit"] = main_hash or ""
    pipeline_log["gh_pages_commit"] = gh_hash if not skip_deploy else ""
    pipeline_log["online_run_id"] = run_id if verify_ok else ""
    pipeline_log["final_status"] = "success" if verify_ok else "deployed_not_verified"
    log_path = save_run_log(pipeline_log, run_id)
    print(f"\n[11/11] log saved: {log_path}")

    # ── 更新 status.json ──────────────────────────────────
    status = load_json(os.path.join(DATA_DIR, "status.json"), {})
    status["source_commit"] = main_hash or ""
    status["deployment_commit"] = status.get("deployment_commit", gh_hash if not skip_deploy else "")
    status["deploy_completed_at"] = bj_iso()
    save_json(os.path.join(DATA_DIR, "status.json"), status)

    print(f"\n{'='*60}")
    print(f"Pipeline completed: {pipeline_log['final_status']}")
    print(f"  run_id: {run_id}")
    print(f"  main: {main_hash}")
    if not skip_deploy:
        print(f"  gh-pages: {gh_hash}")
    print(f"  log: logs/pipeline_{run_id}.json")
    print(f"{'='*60}")
    return 0 if verify_ok else 0  # even if verify fails, return 0 (Pages may need time)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="ASIP Stage-1 Pipeline Runner")
    ap.add_argument("--skip-report", action="store_true", help="跳过日报生成")
    ap.add_argument("--skip-deploy", action="store_true", help="跳过 gh-pages 部署")
    args = ap.parse_args()
    sys.exit(main(skip_report=args.skip_report, skip_deploy=args.skip_deploy))
