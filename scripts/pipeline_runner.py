#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline_runner.py —— ASIP Stage-1 完整主链路编排器（零依赖，跨平台）。

一次运行执行完整流程：
  git pull → 单元测试 → 数据汇总(status+summary+风险+类型) → [日报] →
  数据校验 → 提交 main → 构建 dist → dist 校验 → 部署 gh-pages → 线上验证 → 日志

用法：
  python scripts/pipeline_runner.py --mode {incremental|daily|full|validate-only} [--trigger {manual|scheduled|pre_daily}]

  --mode incremental : 每2小时增量（不生成日报）
  --mode daily       : 北京时间22:00 生成正式日报并部署
  --mode full        : 手动完整测试（含日报）
  --mode validate-only: 仅校验，不修改/不部署

设计原则：
  - 不硬编码本机绝对路径（使用 sys.executable / shutil.which / Path(__file__)）；
  - 部署失败 / 校验失败 → 返回非零，绝不输出“成功”；
  - 使用 deploy.token（gitignore，绝不入库）推送 gh-pages；
  - 线上验证采用轮询 + 防缓存，失败返回非零。
"""
import os
import sys
import json
import shutil
import tempfile
import subprocess
import argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from pipeline_core import (
    PIPELINE_VERSION, DATA_DIR, LOGS_DIR,
    generate_run_id, create_run_log, add_log_step, save_run_log,
    acquire_lock, release_lock, online_verify, bj_iso, bj_format, load_json, save_json,
)

# 跨平台：使用当前 Python 与 PATH 中的 git（禁止硬编码 Windows 绝对路径）
PYTHON = sys.executable
GIT = shutil.which("git") or "git"

DEPLOY_TOKEN_FILE = ROOT / "deploy.token"
REPO_URL = "https://github.com/kenan032005/asip-site.git"
REPO_PUSH_URL = "https://kenan032005:{token}@github.com/kenan032005/asip-site.git"
SITE_BASE = "https://kenan032005.github.io/asip-site"


def run_cmd(cmd, cwd=None, timeout=180):
    """运行命令（列表参数，shell=False），返回 (rc, stdout, stderr)。"""
    try:
        r = subprocess.run(
            cmd, cwd=str(cwd) if cwd else str(ROOT),
            capture_output=True, text=True, timeout=timeout, shell=False,
        )
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)


def git(args, timeout=120, cwd=None):
    return run_cmd([GIT] + args, cwd=cwd, timeout=timeout)


def git_rev_head():
    rc, out, _ = git(["rev-parse", "HEAD"])
    return out.strip() if rc == 0 else ""


def git_commit(msg):
    """提交所有变更到 main。返回 commit hash 或 None。"""
    rc, out, err = git(["add", "-A"])
    if rc != 0:
        return None, f"git add failed: {err}"
    rc, out, err = git(["commit", "-m", msg])
    if rc != 0:
        if "nothing to commit" in (out + err):
            return git_rev_head() or "", "no changes"
        return None, f"git commit failed: {err}"
    return git_rev_head() or "", ""


def read_deploy_token():
    if not DEPLOY_TOKEN_FILE.exists():
        return None
    return DEPLOY_TOKEN_FILE.read_text(encoding="utf-8").strip()


def update_status_source_commit(commit):
    """将 source_commit 写入源 data/status.json（构建前一次）。"""
    p = DATA_DIR / "status.json"
    if not p.exists():
        return
    try:
        st = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return
    if st.get("source_commit") != commit:
        st["source_commit"] = commit
        p.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def deploy_gh_pages(dist_dir, token, source_commit):
    """将 dist/ 强制推送到 gh-pages 分支。返回 (gh_pages_commit, error)。"""
    if not (Path(dist_dir) / "index.html").exists():
        return None, "dist/index.html 不存在"
    tmp = tempfile.mkdtemp(prefix="asip-gh-")
    try:
        dst = Path(tmp)
        # 复制 dist 内容（不使用 shell cp / rm）
        for item in Path(dist_dir).iterdir():
            if item.name in (".git",):
                continue
            tgt = dst / item.name
            if item.is_dir():
                shutil.copytree(item, tgt)
            else:
                shutil.copy2(item, tgt)
        (dst / ".nojekyll").write_text("", encoding="utf-8")

        rc, out, err = git(["init"], cwd=tmp)
        if rc != 0:
            return None, f"git init failed: {err}"
        git(["config", "user.email", "asip-bot@github.com"], cwd=tmp)
        git(["config", "user.name", "ASIP Pipeline"], cwd=tmp)
        git(["add", "-A"], cwd=tmp)
        rc, out, err = git(["commit", "-m", f"deploy: source {source_commit[:8]}"], cwd=tmp)
        if rc != 0:
            return None, f"commit failed: {err}"
        url = REPO_PUSH_URL.format(token=token)
        rc, out, err = git(["push", "-f", url, "HEAD:gh-pages"], cwd=tmp, timeout=180)
        if rc != 0:
            return None, f"push failed: {err}"
        # 获取真实 gh-pages commit
        rc, out, _ = git(["ls-remote", url, "gh-pages"], timeout=60)
        gh = out.split()[0] if out else None
        return (gh or "unknown"), ""
    except Exception as e:
        return None, str(e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_mode(mode, trigger):
    run_id = generate_run_id()
    log = create_run_log(run_id, trigger=trigger)
    started = bj_iso()

    print("=" * 64)
    print(f"ASIP Stage-1 Pipeline Runner")
    print(f"  run_id : {run_id}")
    print(f"  mode   : {mode}")
    print(f"  trigger: {trigger}")
    print(f"  started: {started}")
    print("=" * 64)

    # 0) 获取运行锁（防并发覆盖）
    if not acquire_lock(run_id):
        print("⛔ 另一 pipeline 正在运行，已放弃本次执行。")
        log["final_status"] = "skipped_locked"
        save_run_log(log, run_id)
        return 1
    try:
        # 1) git pull --rebase
        print("\n[1] git pull --rebase origin main ...")
        rc, out, err = git(["pull", "--rebase", "origin", "main"], timeout=60)
        add_log_step(log, "git_pull", "success" if rc == 0 else "failed",
                     details={"output": out[-200:], "error": err[-200:]})
        if rc != 0:
            print(f"  pull: ERR (继续，以本地为准) {err[-150:]}")

        # 2) 单元测试
        print("\n[2] unit tests ...")
        rc, out, err = run_cmd([PYTHON, str(HERE / "tests" / "test_country.py")], timeout=120)
        tests_ok = rc == 0 and "FAIL=0" in out  # 以测试脚本的结果行为准（rc=0 且 FAIL=0）
        add_log_step(log, "unit_tests", "success" if tests_ok else "failed",
                     details={"output": (out + err)[-400:]})
        print(f"  tests: {'OK' if tests_ok else 'FAIL'}")
        if not tests_ok:
            print((out + err)[-400:])

        # 3) 数据汇总（status + summary + 风险修正 + 类型标准化）
        print("\n[3] build_summary ...")
        rc, out, err = run_cmd([PYTHON, str(HERE / "build_summary.py"), "--run-id", run_id], timeout=120)
        add_log_step(log, "build_summary", "success" if rc == 0 else "failed", details={"output": out[-400:]})
        print(f"  build_summary: {'OK' if rc == 0 else 'ERR'}")
        if rc != 0:
            print(out[-300:])
            log["final_status"] = "failed"
            save_run_log(log, run_id)
            return 1

        # 4) 日报（daily / full 模式）
        if mode in ("daily", "full"):
            print("\n[4] generate_reports ...")
            rc, out, err = run_cmd([PYTHON, str(HERE / "generate_reports.py"), "--run-id", run_id], timeout=120)
            add_log_step(log, "generate_reports", "success" if rc == 0 else "failed", details={"output": out[-400:]})
            print(f"  generate_reports: {'OK' if rc == 0 else 'ERR'}")
            if rc != 0:
                print(out[-300:])
                log["final_status"] = "failed"
                save_run_log(log, run_id)
                return 1
        else:
            print("\n[4] skip generate_reports (incremental/validate-only)")

        # 5) 数据校验（源）
        print("\n[5] validate_pipeline (source) ...")
        rc, out, err = run_cmd([PYTHON, str(HERE / "validate_pipeline.py"), "--run-id", run_id,
                                "--stage", "source"], timeout=120)
        src_ok = rc == 0
        add_log_step(log, "validate_source", "success" if src_ok else "failed", details={"output": out[-600:]})
        print(f"  validate_source: {'OK' if src_ok else 'FAIL (CRITICAL)'}")
        if not src_ok:
            print(out)
            log["final_status"] = "failed"
            save_run_log(log, run_id)
            return 1

        # 6) 提交 main（数据）
        print("\n[6] git commit main (data) ...")
        data_hash, cerr = git_commit(f"data: Stage-1 run_id={run_id} (status+summary+risk+types)")
        add_log_step(log, "git_commit_data", "success" if data_hash else "failed",
                     details={"commit": data_hash, "error": cerr})
        print(f"  data commit: {data_hash or cerr}")

        # 7) 获取 source_commit 并写回 status.json（仅一次，构建前）
        source_commit = git_rev_head()
        update_status_source_commit(source_commit)
        # 再次提交以固化 source_commit
        final_data_hash, _ = git_commit(f"chore: set source_commit={source_commit[:8]} for run_id={run_id}")
        source_commit = final_data_hash or source_commit

        # 8) 构建 dist
        print("\n[8] build_site ...")
        rc, out, err = run_cmd([PYTHON, str(HERE / "build_site.py"), "--run-id", run_id], timeout=120)
        add_log_step(log, "build_site", "success" if rc == 0 else "failed",
                     details={"output": out[-300:], "error": err[-500:]})
        print(f"  build_site: {'OK' if rc == 0 else 'ERR'}")
        if rc != 0:
            print(out[-300:])
            print(err[-500:])
            log["final_status"] = "failed"
            save_run_log(log, run_id)
            return 1

        # 9) 校验 dist
        print("\n[9] validate_pipeline (dist) ...")
        rc, out, err = run_cmd([PYTHON, str(HERE / "validate_pipeline.py"), "--run-id", run_id,
                                "--dist", str(ROOT / "dist"), "--stage", "dist"], timeout=120)
        dist_ok = rc == 0
        add_log_step(log, "validate_dist", "success" if dist_ok else "failed", details={"output": out[-600:]})
        print(f"  validate_dist: {'OK' if dist_ok else 'FAIL (CRITICAL)'}")
        if not dist_ok:
            print(out)
            log["final_status"] = "failed"
            save_run_log(log, run_id)
            return 1

        if mode == "validate-only":
            print("\n[validate-only] 校验通过，不部署。")
            log["final_status"] = "success"
            log["main_commit"] = source_commit
            log_path = save_run_log(log, run_id)
            print(f"  log: {log_path}")
            return 0

        # 10) 推送 main
        print("\n[10] git push origin main ...")
        rc, out, err = git(["push", "origin", "main"], timeout=120)
        add_log_step(log, "git_push_main", "success" if rc == 0 else "failed", details={"output": out[-200:]})
        print(f"  push main: {'OK' if rc == 0 else 'ERR'}")
        if rc != 0:
            print(err[-200:])
            log["final_status"] = "failed"
            save_run_log(log, run_id)
            return 1

        # 11) 部署 gh-pages
        print("\n[11] deploy gh-pages ...")
        token = read_deploy_token()
        if not token:
            add_log_step(log, "deploy_gh_pages", "failed", details={"error": "缺少 deploy.token"})
            print("  ⛔ 缺少 deploy.token，无法部署。")
            log["final_status"] = "failed"
            save_run_log(log, run_id)
            return 1
        gh_hash, gh_err = deploy_gh_pages(ROOT / "dist", token, source_commit)
        add_log_step(log, "deploy_gh_pages", "success" if not gh_err else "failed",
                     details={"commit": gh_hash, "error": gh_err})
        print(f"  gh-pages: {gh_hash} {'OK' if not gh_err else 'ERR: '+gh_err}")
        if gh_err:
            log["final_status"] = "failed"
            save_run_log(log, run_id)
            return 1

        # 12) 线上轮询验证（失败返回非零）
        print("\n[12] online verify (polling up to 5 min) ...")
        ok_verify, detail = online_verify(run_id, base_url=SITE_BASE, timeout=300)
        add_log_step(log, "online_verify", "success" if ok_verify else "failed", details=detail)
        print(f"  online: {'✅ run_id 一致' if ok_verify else '❌ 不一致/超时'}")
        print(f"  detail: {json.dumps(detail, ensure_ascii=False)[:300]}")

        if not ok_verify:
            log["final_status"] = "failed"
            log["main_commit"] = source_commit
            log["gh_pages_commit"] = gh_hash or ""
            log["online_run_id"] = detail.get("online_run_id", "")
            save_run_log(log, run_id)
            print("\n⛔ 线上验证失败：保留上一版站点，返回非零退出码。")
            return 1

        # 13) 结构化日志（提交到 main）
        log["main_commit"] = source_commit
        log["gh_pages_commit"] = gh_hash or ""
        log["online_run_id"] = run_id
        log["online_verified_at"] = detail.get("verified_at", "")
        log["final_status"] = "success"
        log_path = save_run_log(log, run_id)
        # 提交日志（force-add，因 logs/ 可能被 gitignore）
        git(["add", "-f", str(Path(log_path).relative_to(ROOT))])
        git(["commit", "-m", f"logs: pipeline run_id={run_id} final_status=success"], timeout=60)
        git(["push", "origin", "main"], timeout=120)
        print(f"\n[done] log: {log_path}")
        print(f"  run_id={run_id} main={source_commit} gh-pages={gh_hash}")
        return 0
    finally:
        release_lock(run_id)


def main():
    ap = argparse.ArgumentParser(description="ASIP Stage-1 Pipeline Runner")
    ap.add_argument("--mode", choices=["incremental", "daily", "full", "validate-only"],
                    default="full", help="运行模式")
    ap.add_argument("--trigger", choices=["manual", "scheduled", "pre_daily"],
                    default="manual", help="触发来源（用于日志标记）")
    args = ap.parse_args()
    rc = run_mode(args.mode, args.trigger)
    print(f"\n{'='*64}\nPipeline exit code: {rc}\n{'='*64}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
