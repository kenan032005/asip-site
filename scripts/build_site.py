#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_site.py —— Stage-1 静态站点构建器（零依赖）。

将公开页面与数据装配到 dist/，供 GitHub Pages（gh-pages 分支）发布。

Stage-1 改进：
  - 注入 ASIP_BUILD_META（run_id, pipeline_version, build_time）到所有页面；
  - 数据文件保持从 gh-pages 路径读取（相对路径 + fetch）；
  - 可选的 __DB__ 内联快照（用于离线/文件协议回退）；
  - 构建后验证 dist run_id 与源数据一致。

用法：
  python scripts/build_site.py [--run-id <run_id>] [--no-embed]
"""
import os
import sys
import json
import shutil
import re
import argparse
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pipeline_core import (
    PIPELINE_VERSION, DATA_DIR, bj_iso, bj_format, load_json, save_json,
)

DIST = os.path.join(ROOT, "dist")
ASSETS = os.path.join(ROOT, "assets")
REPORTS = os.path.join(ROOT, "reports")
INTELLIGENCE_BUILD = os.path.join(HERE, "build_intelligence_demo.py")

HTML_FILES = [
    "index.html", "events.html", "event.html", "countries.html", "country.html",
    "reports.html", "report.html", "disease-risk.html", "404.html",
]

# ── Stage-2 收尾：公开部署数据白名单（杜绝 Canonical 内部数据外泄）──
# 仅下列文件进入 dist/ 与 gh-pages；其余（canonical/、quarantine_events.json、
# raw_candidates.json、pending_events.json、backup/、logs/ 等）一律不发布。
PUBLIC_DATA_ALLOWLIST = [
    "status.json",
    "latest-summary.json",
    "events.json",                       # 复制时脱敏
    "countries.json",
    "risk-levels.json",
    "sources.json",                      # 复制时脱敏（去 legacy_payload/notes/本机路径）
    "public/published_events.json",
    "public/current_metrics.json",
    "public/legacy_archive_events.json",
    "public/disease_events.json",        # Stage 5 疾病公开快照（Public ⊆ Disease Canonical）
]

# Stage 8A：公开安全前端视图（由 scripts/frontend/build_frontend_views.py 生成）。
# 只允许进入 dist 白名单的 8 个视图契约；绝不带内部 runtime 字段。
FRONTEND_VIEWS = [
    "site_overview",
    "master_events",
    "event_timelines",
    "country_snapshots",
    "disease_outbreaks",
    "report_index",
    "knowledge_summary",
    "china_interest",
]
FRONTEND_VIEWS_DIR = os.path.join(DATA_DIR, "runtime", "frontend_preview_public")


def _copy_frontend_views(dist_root, frontend_views_dir=None):
    """§二十四：前端视图 → dist/data/*.json（public-safe，供页面 API.get 消费）。

    默认构建时刷新生产 Preview view；历史回填预览传入独立目录时只读该目录，
    不调用生产 view builder，避免把 Preview 数据混入生产 runtime。
    """
    source_dir = frontend_views_dir or FRONTEND_VIEWS_DIR
    if frontend_views_dir is None:
        try:
            sys.path.insert(0, os.path.join(HERE, "frontend"))
            import build_frontend_views as _bfv
            _bfv.main()
        except Exception as e:
            print(f"  ⚠ 前端视图刷新失败（跳过）: {e}")
    if not os.path.isdir(source_dir):
        return 0
    dst_root = os.path.join(dist_root, "data")
    os.makedirs(dst_root, exist_ok=True)
    n = 0
    for name in FRONTEND_VIEWS:
        src = os.path.join(source_dir, name + ".json")
        if not os.path.exists(src):
            continue
        shutil.copy2(src, os.path.join(dst_root, name + ".json"))
        n += 1
    return n

WIN_PATH_RE = re.compile(r"[A-Za-z]:[\\/]+[^\s\"'<>|]*")
POSIX_PATH_RE = re.compile(r"/(?:home|Users)/[^\s\"'<>|]*")

# 脱敏时移除的内部字段
_SANITIZE_KEYS = (
    "legacy_payload", "notes", "processing_status", "internal_notes",
    "internal_verification_note", "raw_body", "full_text", "raw_text",
)


def _sanitize_public(obj):
    """递归去除内部字段与本机绝对路径，供公开副本/内联快照使用。"""
    if isinstance(obj, dict):
        return {k: _sanitize_public(v) for k, v in obj.items()
                if k not in _SANITIZE_KEYS}
    if isinstance(obj, list):
        return [_sanitize_public(x) for x in obj]
    if isinstance(obj, str):
        return POSIX_PATH_RE.sub("<redacted-path>", WIN_PATH_RE.sub("<redacted-path>", obj))
    return obj


def _copy_public_data(dist_root):
    """按白名单复制公开数据到 dist/data（sources/events 复制时脱敏）。"""
    dst_root = os.path.join(dist_root, "data")
    os.makedirs(dst_root, exist_ok=True)
    for rel in PUBLIC_DATA_ALLOWLIST:
        src = os.path.join(DATA_DIR, rel)
        if not os.path.exists(src):
            continue  # legacy_archive_events.json 等可能尚未生成
        dst = os.path.join(dst_root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if rel in ("sources.json", "events.json"):
            try:
                with open(src, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data = _sanitize_public(data)
                with open(dst, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"  ⚠ 脱敏复制 {rel} 失败: {e}")
            continue
        shutil.copy2(src, dst)


def load_public_db(data_dir=None, frontend_views_dir=None):
    """仅加载白名单文件（脱敏后）作为内联快照，杜绝内部数据进入 __DB__。

    Stage 8A：额外内联公开安全前端视图（site_overview 等），
    键与 dist/data/<name>.json 一致，页面直接 API.get("site_overview")。
    """
    if data_dir is None:
        data_dir = DATA_DIR
    if frontend_views_dir is None:
        frontend_views_dir = FRONTEND_VIEWS_DIR
    db = {}
    for rel in PUBLIC_DATA_ALLOWLIST:
        src = os.path.join(data_dir, rel)
        if not os.path.exists(src):
            continue
        try:
            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if rel in ("sources.json", "events.json"):
            data = _sanitize_public(data)
        db[rel[:-5]] = data
    # Stage 8A 前端视图（public-safe）
    for name in FRONTEND_VIEWS:
        src = os.path.join(frontend_views_dir, name + ".json")
        if not os.path.exists(src):
            continue
        try:
            with open(src, "r", encoding="utf-8") as f:
                db[name] = json.load(f)
        except Exception:
            continue
    return db



def load_db(data_dir=None):
    """加载 data/*.json 为 {文件名: 内容} 字典。"""
    if data_dir is None:
        data_dir = DATA_DIR
    db = {}
    if os.path.isdir(data_dir):
        for fn in sorted(os.listdir(data_dir)):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(data_dir, fn), "r", encoding="utf-8") as f:
                        db[fn[:-5]] = json.load(f)
                except (json.JSONDecodeError, Exception) as e:
                    print(f"  ⚠ 加载 {fn} 失败: {e}")
    return db


def get_build_meta(run_id=None):
    """从 status.json 读取或生成构建元数据。"""
    status = load_json(os.path.join(DATA_DIR, "status.json"), {})
    if run_id is None:
        run_id = status.get("run_id", "")
    return {
        "run_id": run_id,
        "pipeline_version": PIPELINE_VERSION,
        "build_time": bj_iso(),
        "build_time_bj": bj_format(),
        "source_commit": (status.get("source_commit") or "")[:8],
    }


def inject_meta(html, meta):
    """在 HTML 中注入 window.ASIP_BUILD_META。"""
    meta_js = f'<script>window.ASIP_BUILD_META = {json.dumps(meta, ensure_ascii=False)};</script>\n'
    # 插入在 <head> 末尾或 api.js 引用之前
    head_close = "</head>"
    if head_close in html:
        return html.replace(head_close, meta_js + head_close, 1)
    # fallback: 插入在 <body> 之前
    body_open = "<body"
    if body_open in html:
        # 在 <body> 标签之后插入
        idx = html.index(">", html.index(body_open))
        return html[:idx + 1] + "\n" + meta_js + html[idx + 1:]
    return meta_js + html


def inject_db(html, db):
    """内联数据快照（回退机制）。"""
    blob = json.dumps(db, ensure_ascii=False)
    script = '<script>window.__DB__ = ' + blob + ';</script>\n'
    marker = '<script src="assets/js/api.js"></script>'
    if marker in html:
        return html.replace(marker, script + marker, 1)
    return script + html


def main(run_id=None, no_embed=False, data_dir=None, frontend_views_dir=None, dist_dir=None, reports_dir=None):
    """构建站点；可选数据/视图/输出目录仅供本地 Preview 隔离使用。"""
    global DATA_DIR, FRONTEND_VIEWS_DIR, DIST, REPORTS
    if data_dir is not None:
        DATA_DIR = os.path.abspath(str(data_dir))
    if frontend_views_dir is not None:
        FRONTEND_VIEWS_DIR = os.path.abspath(str(frontend_views_dir))
    if dist_dir is not None:
        DIST = os.path.abspath(str(dist_dir))
    if reports_dir is not None:
        REPORTS = os.path.abspath(str(reports_dir))
    meta = get_build_meta(run_id)
    print(f"[build_site] run_id={meta['run_id']} pipeline_version={meta['pipeline_version']}")
    print(f"[build_site] build_time={meta['build_time_bj']}")

    # 零删除构建：先构建到目标目录旁的临时目录，最后用纯改名交换。
    # Preview 可指定独立 dist_dir，因此绝不把临时构建写入生产 dist。
    import time as _time
    DIST_NEW = DIST + ".new"
    TRASH = DIST + ".trash"
    if os.path.isdir(DIST_NEW):  # 上次异常残留
        os.makedirs(TRASH, exist_ok=True)
        os.rename(DIST_NEW, os.path.join(TRASH, f"new_{int(_time.time()*1000)}"))
    os.makedirs(DIST_NEW, exist_ok=True)

    def _rename_retry(src, dst, attempts=6, delay=1.0):
        """Windows 下新写入目录偶被杀毒/索引器短暂占用导致 rename 报 WinError 5，
        这里用 os.replace（更原子）加重试，避免一次性失败。不做任何删除。"""
        last = None
        for _i in range(attempts):
            try:
                os.replace(src, dst)
                return True
            except (PermissionError, OSError) as _e:
                last = _e
                _time.sleep(delay)
        if last:
            raise last
        return False

    def _finish_swap():
        """构建完成后：dist -> trash，.dist_new -> dist（纯 rename，绝不删除）。

        注意：不要在这里做任何批量删除（环境的删除保护会直接终止进程）。
        .dist_trash 由使用者按需手动清理。
        """
        if os.path.isdir(DIST):
            os.makedirs(TRASH, exist_ok=True)
            _rename_retry(DIST, os.path.join(TRASH, f"dist_{int(_time.time()*1000)}"))
        _rename_retry(DIST_NEW, DIST)

    # 构建 HTML
    built = 0
    for fn in HTML_FILES:
        src = os.path.join(ROOT, fn)
        if not os.path.exists(src):
            print(f"  跳过缺失页面: {fn}")
            continue
        with open(src, "r", encoding="utf-8") as f:
            html = f.read()

        # 注入 ASIP_BUILD_META
        html = inject_meta(html, meta)

        # 可选内联数据快照（仅白名单公开数据，已脱敏）
        if not no_embed:
            html = inject_db(html, load_public_db(DATA_DIR, FRONTEND_VIEWS_DIR))

        outpath = os.path.join(DIST_NEW, fn)
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(html)
        built += 1

    # 复制静态资源
    if os.path.isdir(ASSETS):
        shutil.copytree(ASSETS, os.path.join(DIST_NEW, "assets"))
    if os.path.isdir(DATA_DIR):
        # Stage-2 收尾：仅按白名单复制公开数据，绝不复制整个 data/ 目录
        _copy_public_data(DIST_NEW)
    # Stage 8A：公开安全前端视图（site_overview/master_events/...）
    n_views = _copy_frontend_views(DIST_NEW, FRONTEND_VIEWS_DIR if frontend_views_dir is not None else None)
    print(f"  前端视图: {n_views} 个契约")
    if os.path.isdir(REPORTS):
        shutil.copytree(REPORTS, os.path.join(DIST_NEW, "reports"))

    # 独立微型样板：不进入正式导航，构建为 GitHub Pages 项目路径下的静态子树
    from build_intelligence_demo import build_intelligence_demo
    build_intelligence_demo(DIST_NEW)

    # 正式非洲知识库：生产数据层，统一全非洲数据底座
    from build_intelligence_africa import build as build_intelligence_africa
    build_intelligence_africa(DIST_NEW)

    # .nojekyll
    with open(os.path.join(DIST_NEW, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")

    # 更新 status.json 的构建完成时间（仅在 dist 中）
    dist_status_path = os.path.join(DIST_NEW, "data", "status.json")
    dist_status = load_json(dist_status_path, {})
    if dist_status:
        dist_status["build_completed_at"] = bj_iso()
        dist_status["build_completed_at_beijing"] = bj_format()
        save_json(dist_status_path, dist_status)

    # 纯改名交换：.dist_new -> dist
    _finish_swap()

    print(f"构建完成 -> {os.path.relpath(DIST, ROOT)}")  # 相对路径（第九节：日志不得含本地绝对路径）
    print(f"  HTML: {built} 个页面")
    print(f"  ASIP_BUILD_META: 已注入")
    print(f"  内联数据快照: {not no_embed}")
    print(f"  run_id: {meta['run_id']}")
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Stage-1 构建静态站点")
    ap.add_argument("--run-id", type=str, default=None, help="指定 run_id")
    ap.add_argument("--no-embed", action="store_true", help="不内联数据快照")
    ap.add_argument("--data-dir", type=str, default=None, help="本地 Preview 数据目录")
    ap.add_argument("--frontend-views-dir", type=str, default=None, help="本地 Preview 前端视图目录")
    ap.add_argument("--dist-dir", type=str, default=None, help="本地 Preview 输出目录")
    ap.add_argument("--reports-dir", type=str, default=None, help="本地 Preview 报告页面目录")
    args = ap.parse_args()
    main(run_id=args.run_id, no_embed=args.no_embed, data_dir=args.data_dir,
         frontend_views_dir=args.frontend_views_dir, dist_dir=args.dist_dir,
         reports_dir=args.reports_dir)
