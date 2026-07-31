#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline_runner.py —— ASIP Stage-2 完整主链路编排器（零依赖，跨平台）。

一次运行执行完整流程（canonical-first）：
  锁 → git pull --rebase（失败即中止）→ run_id → 单元测试（Stage1+Stage2，
  失败即中止）→ canonical 发布语义与风险统一（publication_policy →
  public → legacy 单向导出）→ build_summary（读 public）→ [日报] →
  预构建 dist → validate_stage2（42 项）→ validate_pipeline(source) → 提交 main →
  注入 source_commit 重建 dist → validate_pipeline(dist) → 推送 main → 部署 gh-pages →
  线上轮询验证 run_id → 结构化日志（本地路径已脱敏）

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

# 第二阶段纪律：git pull --rebase 失败必须中止本次运行（禁止基于过期本地状态继续发布）
PULL_FAILURE_BLOCKS = True

DEPLOY_TOKEN_FILE = ROOT / "deploy.token"
REPO_URL = "https://github.com/kenan032005/asip-site.git"
REPO_PUSH_URL = "https://kenan032005:{token}@github.com/kenan032005/asip-site.git"
SITE_BASE = "https://kenan032005.github.io/asip-site"


def _kill_tree(pid):
    """跨平台强杀整个进程树（Windows 下孙进程会占用管道导致挂死）。"""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True, timeout=15)
        else:
            os.kill(pid, 9)
    except Exception:
        pass


def run_cmd(cmd, cwd=None, timeout=180, env_extra=None):
    """运行命令（列表参数，shell=False），返回 (rc, stdout, stderr)。

    超时处理：先 taskkill /T 杀整个进程树，再回收管道——避免 Windows 下
    subprocess.run(timeout) 因孙进程持有管道句柄而无限挂起。
    """
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    try:
        p = subprocess.Popen(
            cmd, cwd=str(cwd) if cwd else str(ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, shell=False, env=env,
        )
        try:
            out, err = p.communicate(timeout=timeout)
            return p.returncode, (out or "").strip(), (err or "").strip()
        except subprocess.TimeoutExpired:
            _kill_tree(p.pid)
            try:
                out, err = p.communicate(timeout=10)
            except Exception:
                out, err = "", ""
            return -1, (out or "").strip(), "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)


# git 一律禁用交互式凭据/终端提示，避免无终端环境挂起
GIT_ENV = {
    "GIT_TERMINAL_PROMPT": "0",
    "GCM_INTERACTIVE": "Never",
    "GIT_ASKPASS": "echo",
}


def git(args, timeout=120, cwd=None, env_extra=None):
    env = dict(GIT_ENV)
    if env_extra:
        env.update(env_extra)
    return run_cmd([GIT] + args, cwd=cwd, timeout=timeout, env_extra=env)


def git_rev_head():
    rc, out, _ = git(["rev-parse", "HEAD"])
    return out.strip() if rc == 0 else ""


def git_commit(msg):
    """提交所有变更到 main。返回 commit hash 或 None。"""
    rc, out, err = git(["add", "-A"])
    if rc != 0:
        return None, f"git add failed: {err}"
    # 第二阶段纪律：绝不将 .workbuddy（智能体自动化噪声）纳入项目提交
    git(["reset", "-q", "--", ".workbuddy"])
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
    """将 dist/ 强制推送到 gh-pages 分支。返回 (gh_pages_commit, error)。

    实现：在主仓库内用 git plumbing（临时索引 + write-tree + commit-tree）
    合成 gh-pages 提交。与 main 共享对象库 → push 只传增量，慢网络也能完成。
    不再使用独立 git init 临时仓库（那会每次全量推送数百对象）。
    """
    dist = Path(dist_dir)
    if not (dist / "index.html").exists():
        return None, "dist/index.html 不存在"
    try:
        # 1) 用临时索引把 dist/ 内容做成一棵树
        tmp_index = str(ROOT / ".git" / f"gh-index-{os.getpid()}")
        env = {"GIT_INDEX_FILE": tmp_index}
        rc, out, err = git(["--git-dir", str(ROOT / ".git"), "--work-tree", str(dist),
                            "add", "-A", "."], cwd=dist, env_extra=env)
        if rc != 0:
            return None, f"index add failed: {err}"
        rc, tree, err = git(["write-tree"], env_extra=env)
        if rc != 0 or not tree:
            return None, f"write-tree failed: {err}"

        # 2) 以远端 gh-pages 为父提交（存在则续链，不存在则孤儿链）
        parent = ""
        rc, out, _ = git(["rev-parse", "--verify", "-q", "refs/remotes/origin/gh-pages"])
        if rc == 0 and out:
            parent = out.strip()

        msg = f"deploy: source {source_commit[:8]}"
        args = ["commit-tree", tree, "-m", msg]
        if parent:
            args = ["commit-tree", tree, "-p", parent, "-m", msg]
        commit_env = {
            "GIT_AUTHOR_NAME": "ASIP Pipeline", "GIT_AUTHOR_EMAIL": "asip-bot@github.com",
            "GIT_COMMITTER_NAME": "ASIP Pipeline", "GIT_COMMITTER_EMAIL": "asip-bot@github.com",
        }
        rc, new_commit, err = git(args, env_extra=commit_env)
        if rc != 0 or not new_commit:
            return None, f"commit-tree failed: {err}"
        new_commit = new_commit.strip()

        # 3) 推送该提交到 gh-pages（增量对象，网络负担最小）
        url = REPO_PUSH_URL.format(token=token)
        rc, out, err = git(["push", "-f", url, f"{new_commit}:refs/heads/gh-pages"], timeout=420)
        if rc != 0:
            return None, f"push failed: {err}"
        # 更新本地远端跟踪引用，便于下次续链
        git(["update-ref", "refs/remotes/origin/gh-pages", new_commit])
        return new_commit, ""
    except Exception as e:
        return None, str(e)


def _check_ai_runtime_and_schema():
    """结构性校验：runtime.json 处于安全默认且三份 AI Schema 存在。返回 (cfg_ok, schema_ok)。"""
    try:
        import json as _json
        cfg_path = ROOT / "config" / "runtime.json"
        if not cfg_path.exists():
            return False, False
        cfg = _json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg_ok = (
            cfg.get("runtime_mode") == "workbuddy_local"
            and cfg.get("ai_provider") == "workbuddy_queue"
            and cfg.get("ai_processing_enabled") is False
            and cfg.get("allow_paid_fallback") is False
        )
        schema_ok = True
        for s in ("runtime_config.schema.json", "ai_task.schema.json", "ai_result.schema.json"):
            if not (ROOT / "schemas" / s).exists():
                schema_ok = False
        return cfg_ok, schema_ok
    except Exception:
        return False, False


def run_mode(mode, trigger):
    run_id = generate_run_id()
    log = create_run_log(run_id, trigger=trigger)
    started = bj_iso()

    print("=" * 64)
    print(f"ASIP Stage-2 Pipeline Runner")
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
        # 1) git pull --rebase（失败即中止，禁止基于过期本地状态发布）
        print("\n[1] git pull --rebase origin main ...")
        rc, out, err = git(["pull", "--rebase", "origin", "main"], timeout=150)
        add_log_step(log, "git_pull", "success" if rc == 0 else "failed",
                     details={"output": out[-200:], "error": err[-200:]})
        if rc != 0 and PULL_FAILURE_BLOCKS:
            print(f"  ⛔ pull 失败，中止本次运行: {err[-200:]}")
            log["final_status"] = "failed"
            save_run_log(log, run_id)
            return 1

        # 2) 单元测试（Stage-1 + Stage-2，全部通过才继续）
        print("\n[2] unit tests (stage1 + stage2) ...")
        tests_ok = True
        tests_out = ""
        worker_proto_ok = True
        for test_file in ("test_country.py", "test_stage1_pipeline.py",
                          "test_stage2_schema_repo.py",
                          "test_repository_integrity.py",
                          "test_no_local_paths.py",
                          "test_stage2_closeout.py",
                          "test_stage2_frontend_final.py",
                          "test_stage25a_runtime_ai_contract.py",
                          "test_stage25a_hardening.py",
                          "test_stage25b1_worker_protocol.py",
                          "test_stage25b1_hardening.py",
                          "test_stage25b2a_manual_handoff.py",
                          "test_stage25b2b_cross_session.py",
                          "test_stage25b2b_recovery.py"):
            rc, out, err = run_cmd([PYTHON, str(HERE / "tests" / test_file)], timeout=180)
            ok = rc == 0 and "FAIL=0" in out  # 以测试脚本的结果行为准（rc=0 且 FAIL=0）
            tests_ok = tests_ok and ok
            if test_file == "test_stage25b1_worker_protocol.py":
                worker_proto_ok = ok
            tests_out += f"[{test_file}] rc={rc} " + (out + err)[-200:] + "\n"
        add_log_step(log, "unit_tests", "success" if tests_ok else "failed",
                     details={"output": tests_out[-1200:]})
        print(f"  tests: {'OK' if tests_ok else 'FAIL'}")

        # 2.5A) 运行配置与 AI Schema 校验（结构性闸门，独立于单测脚本）
        cfg_ok, schema_ok = _check_ai_runtime_and_schema()
        add_log_step(log, "ai_runtime_config_valid", "success" if cfg_ok else "failed",
                     details={"expected": "workbuddy_local / workbuddy_queue / ai_processing_enabled=false / allow_paid_fallback=false"})
        add_log_step(log, "ai_schema_valid", "success" if schema_ok else "failed",
                     details={"schemas": ["runtime_config", "ai_task", "ai_result"]})
        if not cfg_ok or not schema_ok:
            tests_ok = False

        # 2.5B-1) 非敏感 AI Worker 协议指标（Stage 2.5B-1 新增）
        # 仅记录队列深度/处理中/过期租约计数与协议测试通过与否，不含任何密钥/路径/正文。
        try:
            from ai.workbuddy_worker import status_summary, AI_ROOT as _AI_ROOT
            _st = status_summary(_AI_ROOT)
            log["ai_worker_protocol_valid"] = bool(worker_proto_ok)
            log["ai_queue_depth"] = int(_st.get("queue", 0))
            log["ai_processing_count"] = int(_st.get("processing", 0))
            log["ai_expired_lease_count"] = int(_st.get("expired_leases", 0))
        except Exception as _e:
            log["ai_worker_protocol_valid"] = bool(worker_proto_ok)
            log["ai_queue_depth"] = -1
            log["ai_processing_count"] = -1
            log["ai_expired_lease_count"] = -1
            log["ai_worker_metrics_error"] = "<redacted:%s>" % type(_e).__name__

        if not tests_ok:
            print(tests_out[-600:])
            log["final_status"] = "failed"
            save_run_log(log, run_id)
            return 1

        # 2.5) canonical 发布语义 + 风险统一 + public/legacy 单向导出
        print("\n[2.5] apply_publication_semantics (canonical -> public -> legacy) ...")
        rc, out, err = run_cmd([PYTHON, str(HERE / "data" / "apply_publication_semantics.py"),
                                "--run-id", run_id], timeout=180)
        add_log_step(log, "publication_semantics", "success" if rc == 0 else "failed",
                     details={"output": out[-400:], "error": err[-300:]})
        print(f"  semantics+export: {'OK' if rc == 0 else 'ERR'}")
        if rc != 0:
            print((out + err)[-400:])
            log["final_status"] = "failed"
            save_run_log(log, run_id)
            return 1

        # 3) 数据汇总（读取 public/published_events.json）
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

        # 4.5) 预构建 dist（在 Stage-2 校验前构建，使 dist 携带本 run_id，S42 可一致）
        print("\n[4.5] build_site (pre-validate) ...")
        rc, out, err = run_cmd([PYTHON, str(HERE / "build_site.py"), "--run-id", run_id], timeout=120)
        add_log_step(log, "build_site_pre", "success" if rc == 0 else "failed",
                     details={"output": out[-300:], "error": err[-500:]})
        print(f"  build_site(pre): {'OK' if rc == 0 else 'ERR'}")
        if rc != 0:
            print(out[-300:])
            print(err[-500:])
            log["final_status"] = "failed"
            save_run_log(log, run_id)
            return 1

        # 4.6) Stage-2 规范数据层校验（42 项，失败即中止；此时 dist 已构建，run_id 与源一致）
        print("\n[4.6] validate_stage2 (42 checks) ...")
        rc, out, err = run_cmd([PYTHON, str(HERE / "data" / "validate_stage2.py")], timeout=180)
        s2_ok = rc == 0
        add_log_step(log, "validate_stage2", "success" if s2_ok else "failed",
                     details={"output": out[-800:]})
        print(f"  validate_stage2: {'OK' if s2_ok else 'FAIL (CRITICAL)'}")
        if not s2_ok:
            print(out[-1000:])
            log["final_status"] = "failed"
            save_run_log(log, run_id)
            return 1

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
        data_hash, cerr = git_commit(f"data: Stage-2 run_id={run_id} (canonical->public->legacy+summary)")
        add_log_step(log, "git_commit_data", "success" if data_hash else "failed",
                     details={"commit": data_hash, "error": cerr})
        print(f"  data commit: {data_hash or cerr}")

        # 7) 获取 source_commit 并写回 status.json（仅一次，构建前）
        source_commit = git_rev_head()
        update_status_source_commit(source_commit)
        # 再次提交以固化 source_commit
        final_data_hash, _ = git_commit(f"chore: set source_commit={source_commit[:8]} for run_id={run_id}")
        source_commit = final_data_hash or source_commit

        # 8) 用 source_commit 重建 dist（注入 commit 哈希；run_id 不变，仍为本次 run_id）
        print("\n[8] build_site (final) ...")
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
        rc, out, err = git(["push", "origin", "main"], timeout=420)
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
        if not gh_err:
            # Section 九：记录部署完成时间与部署 commit（deployment_commit）
            log["deploy_completed_at"] = bj_iso()
            log["deployment_commit"] = gh_hash or ""
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
        git(["push", "origin", "main"], timeout=420)
        print(f"\n[done] log: {log_path}")
        print(f"  run_id={run_id} main={source_commit} gh-pages={gh_hash}")
        return 0
    finally:
        release_lock(run_id)


def main():
    ap = argparse.ArgumentParser(description="ASIP Stage-2 Pipeline Runner")
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
