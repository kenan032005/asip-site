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
import hashlib
import shutil
from pathlib import Path
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
# 只允许进入 dist 白名单的 7 个视图契约；绝不带内部 runtime 字段。
FRONTEND_VIEWS = [
    "site_overview",
    "china_interest",          # V1.1 homepage China Exposure view
    "master_events",
    "event_timelines",
    "country_snapshots",
    "disease_outbreaks",
    "report_index",
    "knowledge_summary",
    "ai_intelligence",        # C5-A：Homepage 会请求该视图，此前未发布 → 404
    "executive_summary",      # C7-1：领导 30 秒仪表盘单一数据源（确定性，无 AI 生成）
    "homepage_intelligence",  # C7-5：MESIP 风格首页情报视图（8 板块 + 地图 + 情报流）
]
FRONTEND_VIEWS_DIR = os.path.join(DATA_DIR, "runtime", "frontend_preview_public")


def _copy_frontend_views(dist_root):
    """§二十四：前端视图 → dist/data/*.json（public-safe，供页面 API.get 消费）。

    先刷新视图（确定性构建器，无 AI），再把 7 个契约复制进公开构建。
    生成失败时静默跳过（页面留空态，不影响站点构建）。
    """
    try:
        sys.path.insert(0, os.path.join(HERE, "frontend"))
        import build_frontend_views as _bfv
        _bfv.main()
    except Exception as e:
        print(f"  ⚠ 前端视图刷新失败（跳过）: {e}")
    if not os.path.isdir(FRONTEND_VIEWS_DIR):
        return 0
    dst_root = os.path.join(dist_root, "data")
    os.makedirs(dst_root, exist_ok=True)
    n = 0
    for name in FRONTEND_VIEWS:
        src = os.path.join(FRONTEND_VIEWS_DIR, name + ".json")
        if not os.path.exists(src):
            # C5-A：部分视图（如 ai_intelligence）由 ops 构建器直接写入
            # data/views/，未进入 frontend_preview_public → Homepage 请求 404。
            # 回退到 data/views/ 作为第二来源，保证发布完整。
            alt = os.path.join(DATA_DIR, "views", name + ".json")
            if os.path.exists(alt):
                src = alt
            else:
                continue
        shutil.copy2(src, os.path.join(dst_root, name + ".json"))
        # C5-B：页面 JS 探测的是 data/views/<name>.json（如 ai-intelligence.js），
        # 因此同时镜像一份到 data/views/，避免每次请求都 404（控制台噪声 + 模块静默空态）。
        vdir = os.path.join(dst_root, "views")
        os.makedirs(vdir, exist_ok=True)
        shutil.copy2(src, os.path.join(vdir, name + ".json"))
        n += 1
    return n

def _build_and_copy_c1a_views(dist_root):
    """C1A build integration（§二/§七）：生成 news-stream-v1 视图并发布公开视图。

    步骤：
      1. tools/c1a/build_views.build_c1a_views(...) 用仓库数据生成
         data/views/{news_stream,source_yield_report,c1a_gate_audit}.json；
      2. 把公开安全的 news_stream.json 复制进 dist/data/views/（页面按
         data/views/news_stream.json 直接 fetch，不进 __DB__ 内联快照，
         避免 ~1MB 视图膨胀每个页面）。

    失败不阻断站点构建（视图属展示层），但显式打印 C1A_VIEWS_OK=False。
    返回发布到 dist 的视图数。
    """
    try:
        sys.path.insert(0, os.path.join(ROOT, "tools", "c1a"))
        import build_views as _c1av
        ok, st = _c1av.build_c1a_views(root=ROOT, internal_dir=DATA_DIR,
                                       out_root=ROOT, verbose=True)
        print(f"  C1A_VIEWS_OK = {'TRUE' if ok else 'FALSE'}")
        if not ok:
            return 0
        return _c1av.copy_public_c1a_views(dist_root, root=ROOT)
    except Exception as e:
        print(f"  ⚠ C1A 视图集成失败（站点构建继续）: {e}")
        print("  C1A_VIEWS_OK = FALSE")
        return 0


# 负向后顾 (?<![A-Za-z])：URL scheme 的末字母 + 冒号（"https:" 的 "s:"）不得
# 被当作 Windows 盘符，否则整条 URL 被抹成 http<redacted-path>。
# 真实 Windows 绝对路径（C:\... / D:/...）前置字符为串首/空白/引号/等号，不受影响。
WIN_PATH_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]+[^\s\"'<>|]*")
# 同理：URL 路径段可能含 /home/ 或 /Users/（如 https://ex.com/home/index），
# 只在串首或"非路径字符"之后才认定为 Linux 本机绝对路径。
POSIX_PATH_RE = re.compile(r"(?<![A-Za-z0-9/._:\-])/(?:home|Users)/[^\s\"'<>|]*")

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


def _compliant_run_id():
    """返回符合 schema 约束的 run_id（^\d{8}T\d{6}\+0800_[a-z0-9]{6}$）。

    compatibility export 的信封 run_id 受 schema 约束；GitHub run_id 为纯数字、
    不满足该 pattern，会让 published_events 等保存整批中止（fail-fast）,
    进而 canonical 新 cluster 无法同步到 legacy 视图（V17 阻断）。
    优先沿用 canonical 中已存在的生产 run_id（真实来源），否则按当前 BJT 生成。
    """
    pat = re.compile(r"^\d{8}T\d{6}\+0800_[a-z0-9]{6}$")
    try:
        canon = load_json(os.path.join(DATA_DIR, "canonical", "event_clusters.json"), {}) or {}
        rid = canon.get("run_id")
        if isinstance(rid, str) and pat.match(rid):
            return rid
    except Exception:
        pass
    import hashlib
    from datetime import timezone
    now_bj = datetime.now(timezone(timedelta(hours=8)))
    stamp = now_bj.strftime("%Y%m%dT%H%M%S+0800")
    suffix = hashlib.md5(stamp.encode("utf-8")).hexdigest()[:6]
    return "%s_%s" % (stamp, suffix)


def _sync_legacy_from_canonical(run_id=None):
    """V17 Compatibility：canonical truth → legacy view（单向重建）。

    deploy 环境中 data/events.json 是 repo 静态文件，而 data/canonical/ 被
    production-state 覆盖；canonical 新增 cluster 时两者集合不一致，V17
    fail-closed 阻断部署。本步骤在 build 前用 compatibility export 重建
    legacy 视图（events/pending/quarantine/public published），保证
    canonical → compatibility export → legacy view 恒同步。
    不修改 canonical 本身；write_if_changed 保证幂等。
    """
    canon = os.path.join(DATA_DIR, "canonical", "event_clusters.json")
    if not os.path.exists(canon):
        return False
    try:
        # scripts.* 包导入需要仓库根在 sys.path（脚本模式下 sys.path[0]=scripts/）
        sys.path.insert(0, str(Path(HERE).parent))
        from scripts.data.repository import Repository
        from scripts.data.compatibility_export import export_all
        # Repository 内部按 root/data/<name> 解析，root 必须是仓库根
        repo = Repository(root=Path(ROOT))
        # C6-R2.6 merge fix：沿用本次 build 的 run_id（此前自生成新 id → 四方 run_id 不一致，
        # 触发 validate_stage2 S42）。无 run_id 时回退原行为。
        export_all(repo, run_id=run_id or _compliant_run_id())
        print("  legacy views rebuilt from canonical (V17 sync)")
        return True
    except Exception as e:
        print(f"  ⚠ canonical→legacy sync failed (keep as-is): {e}")
        return False


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


#: dist 内报告索引的可能位置（前端 report-views.js 依次探测这两条路径）
REPORT_INDEX_CANDIDATES = ("data/report_index.json", "data/views/report_index.json")


def verify_report_publication(dist_root, data_dir=None, raise_on_fail=True):
    """构建后硬校验：dist/data/reports 必须**精确反映本次构建结果**。

    覆盖 §2（与构建产物一致、不依赖人工同步）、§4（新增/修改/删除都要同步）、
    §5（report_index ↔ artifact 双向一致）。

    返回统计字典；不一致时打印明细并（默认）抛错，让构建**明确失败**，
    而不是把上一轮的 dist 当成新构建结果继续用。
    """
    data_dir = data_dir or DATA_DIR
    src_root = os.path.join(data_dir, "reports")
    dst_root = os.path.join(dist_root, "data", "reports")
    res = {"SOURCE_REPORT_COUNT": 0, "DIST_REPORT_COUNT": 0, "REPORT_INDEX_COUNT": 0,
           "MISSING_REPORT_ARTIFACTS": 0, "STALE_REPORT_ARTIFACTS": 0,
           "MISMATCHED_REPORT_ARTIFACTS": 0, "MOCK_IN_DIST_REPORT_INDEX": 0,
           "REPORT_INDEX_FILE": None}

    def _rel(root):
        out = {}
        if not os.path.isdir(root):
            return out
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                out[os.path.relpath(p, root).replace(os.sep, "/")] = p
        return out

    src, dst = _rel(src_root), _rel(dst_root)
    # index 的 path 字段相对 dist 根（data/reports/xxx）；统一到同一基准再比较
    dst_rel_root = {("data/reports/" + k): v for k, v in dst.items()}
    res["SOURCE_REPORT_COUNT"] = len(src)
    res["DIST_REPORT_COUNT"] = len(dst)
    missing = sorted(set(src) - set(dst))
    extra = sorted(set(dst) - set(src))
    mismatched = [r for r in sorted(set(src) & set(dst)) if _sha256(src[r]) != _sha256(dst[r])]

    index_file = None
    for rel in REPORT_INDEX_CANDIDATES:
        cand = os.path.join(dist_root, rel)
        if os.path.exists(cand):
            index_file = cand
            break
    idx = load_json(index_file, {}) if index_file else {}
    res["REPORT_INDEX_FILE"] = os.path.relpath(index_file, dist_root).replace(os.sep, "/") \
        if index_file else None
    rows = idx.get("reports") or []
    res["REPORT_INDEX_COUNT"] = idx.get("count") or len(rows)
    res["MOCK_IN_DIST_REPORT_INDEX"] = sum(1 for r in rows if r.get("is_mock"))
    indexed = {str(r.get("path") or "").replace(os.sep, "/") for r in rows}
    not_in_dist = sorted(p for p in indexed if p not in dst_rel_root)
    res["MISSING_REPORT_ARTIFACTS"] = len(not_in_dist) + len(missing)
    res["STALE_REPORT_ARTIFACTS"] = len(extra)
    res["MISMATCHED_REPORT_ARTIFACTS"] = len(mismatched)

    ok = (not missing and not extra and not mismatched and not not_in_dist
          and res["MOCK_IN_DIST_REPORT_INDEX"] == 0)
    res["REPORT_ARTIFACT_PUBLICATION"] = "PASS" if ok else "FAIL"
    print("  REPORT_ARTIFACT_PUBLICATION = %s" % res["REPORT_ARTIFACT_PUBLICATION"])
    print("    SOURCE_REPORT_COUNT=%d DIST_REPORT_COUNT=%d INDEX_COUNT=%d INDEX_FILE=%s"
          % (res["SOURCE_REPORT_COUNT"], res["DIST_REPORT_COUNT"],
             res["REPORT_INDEX_COUNT"], res["REPORT_INDEX_FILE"]))
    print("    MISSING=%d STALE=%d MISMATCHED=%d MOCK_IN_INDEX=%d"
          % (res["MISSING_REPORT_ARTIFACTS"], res["STALE_REPORT_ARTIFACTS"],
             res["MISMATCHED_REPORT_ARTIFACTS"], res["MOCK_IN_DIST_REPORT_INDEX"]))
    if not ok:
        for label, items in (("MISSING", missing + not_in_dist), ("STALE", extra),
                             ("MISMATCHED", mismatched)):
            for it in items[:5]:
                print("      %s: %s" % (label, it))
        if raise_on_fail:
            raise RuntimeError(
                "report artifact publication verification failed "
                "(dist/data/reports 与本次构建不一致 —— 不要手工同步，先查构建日志)")
    return res


def _copy_production_reports(dist_root):
    """Production report outputs → dist/reports/{daily,weekly}/。

    source = data/runtime/ops/reports/（deploy 环境由 state 拷贝）；
    report_index.json 的 path 字段与此处发布路径一一对应。
    gates/fact_pack/run_summary 为运行内部产物，不进公开归档。
    """
    src_dir = os.path.join(DATA_DIR, "runtime", "ops", "reports")
    if not os.path.isdir(src_dir):
        return 0
    n = 0
    for sub, prefixes in (("daily", ("daily_",)),
                          ("weekly", ("tcd_weekly_", "ssd_weekly_"))):
        dst_dir = os.path.join(dist_root, "reports", sub)
        os.makedirs(dst_dir, exist_ok=True)
        for fn in os.listdir(src_dir):
            if not fn.endswith(".json"):
                continue
            if not fn.startswith(prefixes):
                continue
            if fn.endswith(("_gates.json", "_fact_pack.json")):
                continue
            if fn == "reports_run_summary.json":
                continue
            src = os.path.join(src_dir, fn)
            shutil.copy2(src, os.path.join(dst_dir, fn))
            n += 1
            # report_index 的 path 以 report_id 命名（DAILY_YYYYMMDD / WEEKLY_<ISO>_<date>）；
            # 生成确定性别名文件，保证 index path 与归档一一对应可解析。
            try:
                doc = json.loads(open(src, encoding="utf-8").read())
                rid = doc.get("report_id")
                if rid and not any(x in str(rid).upper()
                                   for x in ("MANUAL_TRIAL", "_DEV", "TRIAL")):
                    shutil.copy2(src, os.path.join(dst_dir, "%s.json" % rid))
                    n += 1
            except Exception:
                pass
    return n


def _copy_report_artifacts(dist_root):
    """C4-B：正式 report artifacts → dist/data/reports/{daily,weekly,country_weekly}/。

    report_index 的 path 字段即 data/reports/... → 与公开路径一一对应可解析。
    """
    src_root = os.path.join(DATA_DIR, "reports")
    if not os.path.isdir(src_root):
        return 0
    n = 0
    for sub in ("daily", "weekly", "country_weekly"):
        src_dir = os.path.join(src_root, sub)
        if not os.path.isdir(src_dir):
            continue
        dst_dir = os.path.join(dist_root, "data", "reports", sub)
        os.makedirs(dst_dir, exist_ok=True)
        for fn in os.listdir(src_dir):
            if fn.endswith(".json"):
                shutil.copy2(os.path.join(src_dir, fn), os.path.join(dst_dir, fn))
                n += 1
    return n


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


def load_public_db(data_dir=None):
    """仅加载白名单文件（脱敏后）作为内联快照，杜绝内部数据进入 __DB__。

    Stage 8A：额外内联 7 个公开安全前端视图（site_overview 等），
    键与 dist/data/<name>.json 一致，页面直接 API.get("site_overview")。
    """
    if data_dir is None:
        data_dir = DATA_DIR
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
        src = os.path.join(FRONTEND_VIEWS_DIR, name + ".json")
        if not os.path.exists(src):
            # C5-A：部分视图（如 ai_intelligence）由 ops 构建器直接写入
            # data/views/，未进入 frontend_preview_public → Homepage 请求 404。
            # 回退到 data/views/ 作为第二来源，保证发布完整。
            alt = os.path.join(DATA_DIR, "views", name + ".json")
            if os.path.exists(alt):
                src = alt
            else:
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


def _parse_ts(s):
    """解析 ISO 时间戳为 UTC datetime；失败返回 None。

    无时区后缀的按北京时间（UTC+8）解释——站点全局约定「所有时间均为北京时间」。
    例：'2026-11-04T02:32:53'（无后缀）→ 视为北京时间 → UTC 2026-11-03T18:32:53Z。
    """
    if not s or not isinstance(s, str):
        return None
    try:
        t = s.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _bj_str_from_utc(utc_dt):
    """UTC datetime → 北京时间字符串 YYYY-MM-DD HH:MM:SS。"""
    if utc_dt is None:
        return ""
    return utc_dt.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")


def get_build_meta(run_id=None, data_dir=None, now=None):
    """派生公开数据时效性元数据。

    ROOT CAUSE 修复（PUBLIC FRESHNESS METADATA HOTFIX）：
      旧实现无条件优先 status.json.data_as_of，而该值常被历史兼容产物
      legacy ai_intelligence.json 污染（来源 production_state.last_daily_report，
      实为旧 AI 快照），导致线上误报「数据严重过期」。

    修复：data_as_of 优先取自**经当前生产视图验证**的截止时间
      （site_overview / homepage_intelligence / current_metrics），
      仅在真实视图均无截止时间时，才谨慎回退 status.json 并标注 FALLBACK_UNVERIFIED。
      绝不读取 legacy ai_intelligence.json 作为时效来源。

    严格区分四类时间语义（II.3）：
      - collection_as_of：采集成功时间
      - analysis_as_of  ：AI 分析有效时间
      - data_as_of      ：当前公开视图实际截止时间（对外公开时效真值）
      - build_time      ：网页构建时间（绝不冒充数据更新时间）
    """
    base = data_dir or DATA_DIR
    status = load_json(os.path.join(base, "status.json"), {})
    if run_id is None:
        run_id = status.get("run_id", "")

    # ── 经当前生产视图验证的截止时间候选（最新优先）──
    # 仅读取「当前公开视图」；绝不读取 legacy ai_intelligence.json（避免旧 AI 冒充最新）。
    # ── 视图读取：优先采用「本次构建已重建」的前端公开视图
    #    （data/runtime/frontend_preview_public），其 data_as_of 由 build_frontend_views
    #    从 production-state canonical 解析，是本次生产数据的真实截止时间；
    #    仅当重建产物缺失时才回退到提交态种子 views/（及 public/）。
    #    这是 P0-FRESHNESS 修复的核心：get_build_meta 必须在视图重建之后读取，
    #    否则会读到提交态陈旧种子（data_as_of=2026-09-21），导致误报。 ──
    def _load_view(name, sub="views"):
        fpv = os.path.join(base, "runtime", "frontend_preview_public", name + ".json")
        if os.path.exists(fpv):
            try:
                return load_json(fpv, {}) or {}
            except Exception:
                pass
        p = os.path.join(base, sub, name + ".json")
        try:
            return load_json(p, {}) or {}
        except Exception:
            return {}
    so = _load_view("site_overview")
    hi = _load_view("homepage_intelligence")
    cm = _load_view("current_metrics", sub="public")

    candidates = []  # (utc_dt, source_label, status_flag, original_str)
    if so.get("data_as_of"):
        candidates.append((_parse_ts(so.get("data_as_of")),
                          "site_overview.data_as_of", so.get("data_as_of_status") or "EXPLICIT",
                          so.get("data_as_of")))
    if hi.get("data_as_of"):
        candidates.append((_parse_ts(hi.get("data_as_of")),
                          "homepage_intelligence.data_as_of", "EXPLICIT",
                          hi.get("data_as_of")))
    if so.get("generated_at"):
        candidates.append((_parse_ts(so.get("generated_at")),
                          "site_overview.generated_at", "DERIVED", so.get("generated_at")))
    if cm.get("updated_at"):
        candidates.append((_parse_ts(cm.get("updated_at")),
                          "current_metrics.updated_at", "DERIVED", cm.get("updated_at")))

    data_as_of = ""
    data_as_of_bj = ""
    data_as_of_source = ""
    data_as_of_status = ""
    # 优先采用 site_overview（显式 UTC、状态 EXPLICIT，最权威）；否则取验证候选中最新者。
    if so.get("data_as_of") and _parse_ts(so.get("data_as_of")) is not None:
        top = (so.get("data_as_of"), "site_overview.data_as_of",
               so.get("data_as_of_status") or "EXPLICIT")
        data_as_of, data_as_of_source, data_as_of_status = top
        data_as_of_bj = _bj_str_from_utc(_parse_ts(data_as_of))
    elif candidates:
        verified = [c for c in candidates if c[0] is not None]
        verified.sort(key=lambda c: c[0], reverse=True)
        if verified:
            top = verified[0]
            data_as_of, data_as_of_source, data_as_of_status = top[3], top[1], top[2]
            data_as_of_bj = _bj_str_from_utc(top[0])

    # ── 回退：真实生产视图均无截止时间时，才谨慎使用 status.json（明确标注未验证）──
    # 不默认新鲜：缺失/解析失败 → data_as_of 仍可能为空，banner 必须给出「新鲜度未知」提醒。
    if not data_as_of:
        fb = status.get("data_as_of") or status.get("data_generated_at") or ""
        if fb and _parse_ts(fb) is not None:
            data_as_of = fb
            data_as_of_bj = _bj_str_from_utc(_parse_ts(fb))
            data_as_of_source = ("status.data_as_of" if status.get("data_as_of")
                                 else "status.data_generated_at") + ".fallback"
            data_as_of_status = "FALLBACK_UNVERIFIED"

    # ── 四个语义化时间字段（区分采集/分析/公开截止/构建；build_time 不冒充数据更新）──
    collection_as_of = so.get("latest_verified_event_time") or status.get("data_generated_at") or ""
    ai_gen = (hi.get("ai") or {}).get("generated_time") or so.get("data_as_of") or ""
    analysis_as_of = ai_gen
    build_time = bj_iso()

    # ── 时效年龄：以 data_as_of 真实截止时间计算，绝不用 build_time 冒充 ──
    ref_now = now if now is not None else datetime.now(timezone.utc)
    ref = _parse_ts(data_as_of) if data_as_of else None
    age_hours = None
    if ref is not None:
        age_hours = round((ref_now - ref).total_seconds() / 3600, 1)

    return {
        "run_id": run_id,
        "pipeline_version": PIPELINE_VERSION,
        "build_time": build_time,
        "build_time_bj": bj_format(),
        "source_commit": (status.get("source_commit") or "")[:8],
        "collection_as_of": collection_as_of,
        "analysis_as_of": analysis_as_of,
        "data_as_of": data_as_of,
        "data_as_of_bj": data_as_of_bj,
        "data_as_of_source": data_as_of_source,
        "data_as_of_status": data_as_of_status,
        "data_age_hours": age_hours,
        "data_stale": bool(age_hours is not None and age_hours > 12),
    }


def _staleness_banner(meta):
    """公开数据时效提醒（>12h 黄色 / >48h 红色）。

    规则（II.5 / II.6）：
      - 真实数据超过阈值必须显示警告（红/黄），不得删除或永久隐藏；
      - 缺失/解析失败时 age=None，**不得默认判为新鲜**——给出「新鲜度未知」黄色提醒；
      - 仅在能确认数据截止时间且距今 ≤12h 时才不显示横幅。
    """
    age = meta.get("data_age_hours")
    as_of = meta.get("data_as_of") or "未知"
    if age is None:
        # 无法判定新鲜度：不得默认新鲜，给出黄色「新鲜度未知」提醒。
        return ('<div id="asip-staleness-banner" role="status" style="position:sticky;top:0;z-index:9999;'
                'background:#fef3c7;color:#b45309;border-bottom:1px solid #b45309;padding:8px 12px;'
                'font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;text-align:center;">'
                '数据新鲜度未知：未能确认数据截止时间（最后已知 %s），请谨慎引用。</div>\n' % as_of)
    if age <= 12:
        return ""
    if age <= 48:
        color, bg, label = "#b45309", "#fef3c7", "数据可能已过期"
    else:
        color, bg, label = "#b91c1c", "#fee2e2", "数据严重过期"
    return ('<div id="asip-staleness-banner" role="status" style="position:sticky;top:0;z-index:9999;'
            'background:%s;color:%s;border-bottom:1px solid %s;padding:8px 12px;'
            'font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;text-align:center;">'
            '%s：数据截至 %s（距今 %.1f 小时），请谨慎引用。</div>\n'
            % (bg, color, color, label, as_of, age))


# 移除模板中可能已静态烘焙的旧时效横幅（避免新旧叠加）
_BANNER_RE = re.compile(r'<div id="asip-staleness-banner".*?</div>\s*', re.DOTALL)


def inject_meta(html, meta):
    """在 HTML 中注入 window.ASIP_BUILD_META（并抑制 favicon 404），并按真实时效刷新横幅。

    若模板已静态烘焙旧横幅，先移除再按本次构建的真实 data_as_of 注入
    （fresh 时不注入横幅，保持页面干净；stale 时注入红/黄警告）。
    """
    meta_js = f'<script>window.ASIP_BUILD_META = {json.dumps(meta, ensure_ascii=False)};</script>\n'
    # C5-B：站点未提供 favicon，浏览器默认请求 /favicon.ico → 每次加载一条
    # 控制台 404。用 data: 空图标显式声明，消除该噪声（不引入新资源）。
    if 'rel="icon"' not in html:
        meta_js = '<link rel="icon" href="data:,">' + chr(10) + meta_js
    banner = _staleness_banner(meta)
    # 先移除模板中可能已静态烘焙的旧横幅（避免新旧叠加 / 误报残留）
    html = _BANNER_RE.sub("", html)
    head_close = "</head>"
    if head_close in html:
        out = html.replace(head_close, meta_js + head_close, 1)
        if banner and "<body" in out:
            idx = out.index(">", out.index("<body"))
            out = out[:idx + 1] + "\n" + banner + out[idx + 1:]
        return out
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


def _reconcile_status_counts(dist_status, cm=None, so=None):
    """II.4：把可经 current_metrics / site_overview 直接验证的对外计数同步为真实值，
    不再输出过时数量作为当前值。仅覆盖「来源存在且类型正确」的字段；其余保持不变
    （不臆造、不删除），对无法证实的字段保留原值（或置 unknown）。"""
    if cm is None:
        try:
            cm = load_json(os.path.join(DATA_DIR, "public", "current_metrics.json"), {}) or {}
        except Exception:
            cm = {}
    if so is None:
        # 优先采用本次重建的前端视图（frontend_preview_public），与 get_build_meta 一致；
        # 仅当重建产物缺失时回退提交态种子 views/site_overview.json。
        _fpv = os.path.join(DATA_DIR, "runtime", "frontend_preview_public", "site_overview.json")
        try:
            so = load_json(_fpv, {}) or {}
        except Exception:
            so = {}
        if not so:
            try:
                so = load_json(os.path.join(DATA_DIR, "views", "site_overview.json"), {}) or {}
            except Exception:
                so = {}
    # 直接等价于 current_metrics 的对外计数
    mapping = [
        ("published_event_count", cm.get("published_events")),
        ("quarantine_event_count", cm.get("quarantine")),
        ("pending_event_count", cm.get("pending_articles")),
        ("current_event_count", cm.get("current_policy_passed_events")),
    ]
    for dst, val in mapping:
        if isinstance(val, int):
            dist_status[dst] = val
    # 来自 site_overview.kpis 的近窗计数
    kpis = (so.get("kpis") or {}) if isinstance(so, dict) else {}
    if isinstance(kpis.get("events_24h"), int):
        dist_status["events_24h"] = kpis["events_24h"]
    if isinstance(kpis.get("events_7d"), int):
        dist_status["events_7d"] = kpis["events_7d"]


def main(run_id=None, no_embed=False):
    # P0-FRESHNESS：在派生时效性元数据之前，先重建前端公开视图
    # （build_frontend_views 将 site_overview.data_as_of 从 production-state
    #  canonical 解析后写入 data/runtime/frontend_preview_public/）。
    # 这样 get_build_meta 读取的是「本次重建后的真实生产截止时间」，
    # 而非提交态陈旧种子（data_as_of=2026-09-21），从根本上消除误报。
    try:
        sys.path.insert(0, os.path.join(HERE, "frontend"))
        import build_frontend_views as _bfv_pre
        _bfv_pre.main()
        print("  [freshness] 前端视图已预重建（供时效性元数据派生）")
    except Exception as _e:
        print(f"  [freshness] 前端视图预重建跳过（回退提交态种子）: {_e}")
    meta = get_build_meta(run_id)
    print(f"[build_site] run_id={meta['run_id']} pipeline_version={meta['pipeline_version']}")
    print(f"[build_site] build_time={meta['build_time_bj']}")

    # 零删除构建：先构建到 .dist_new，最后用纯改名交换（rename 不受
    # 环境批量删除保护限制）。旧 dist 改名入 .dist_trash，尽力清理。
    import time as _time
    DIST_NEW = os.path.join(ROOT, ".dist_new")
    TRASH = os.path.join(ROOT, ".dist_trash")
    if os.path.isdir(DIST_NEW):  # 上次异常残留
        print("  WARNING: PREVIOUS_BUILD_INCOMPLETE —— 发现 .dist_new 残留（上次构建未完成交换，"
              "通常因为 dist 被占用，例如本地预览服务）。已移入 .dist_trash。")
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
            html = inject_db(html, load_public_db(DATA_DIR))

        outpath = os.path.join(DIST_NEW, fn)
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(html)
        built += 1

    # 复制静态资源
    if os.path.isdir(ASSETS):
        shutil.copytree(ASSETS, os.path.join(DIST_NEW, "assets"))
    # V17 Compatibility：canonical → legacy 视图同步（必须在复制公开数据之前）
    _sync_legacy_from_canonical(meta["run_id"])
    if os.path.isdir(DATA_DIR):
        # Stage-2 收尾：仅按白名单复制公开数据，绝不复制整个 data/ 目录
        _copy_public_data(DIST_NEW)
    # Stage 8A：公开安全前端视图（site_overview/master_events/...）
    # 先从 canonical + 持久 admission 重建 timelines（确定性，无 AI），
    # 保证 master_events/disease_outbreaks/event_timelines 反映生产真值。
    try:
        sys.path.insert(0, str(Path(HERE).parent))
        from scripts.ops import timeline_run as _timeline_run
        _tl = _timeline_run.build_timelines(data_dir=DATA_DIR)
        print(f"  timelines rebuilt: social={_tl['social']} disease={_tl['disease']}")
    except Exception as e:
        print(f"  timeline rebuild failed (use state artifacts): {e}")
    n_views = _copy_frontend_views(DIST_NEW)
    print(f"  前端视图: {n_views} 个契约")
    # C1A build integration（§二）：用仓库自身数据重新生成 news-stream-v1 视图，
    # 不依赖手工复制 / preview 目录。必须在 _copy_frontend_views 之后（
    # master_events / site_overview 需要是本次构建的新鲜产物）。
    n_c1a = _build_and_copy_c1a_views(DIST_NEW)
    print(f"  C1A 视图: {n_c1a} 个公开视图")
    if os.path.isdir(REPORTS):
        shutil.copytree(REPORTS, os.path.join(DIST_NEW, "reports"))
    # Production report outputs → 公开归档
    n_prod_reports = _copy_production_reports(DIST_NEW)
    n_prod_reports = _copy_report_artifacts(DIST_NEW)
    print(f"  生产报告归档: {n_prod_reports} 个文件")

    # 独立微型样板：不进入正式导航，构建为 GitHub Pages 项目路径下的静态子树
    from build_intelligence_demo import build_intelligence_demo
    build_intelligence_demo(DIST_NEW)

    # 正式非洲知识库：生产数据层，统一全非洲数据底座
    from build_intelligence_africa import build as build_intelligence_africa
    build_intelligence_africa(DIST_NEW)

    # .nojekyll
    with open(os.path.join(DIST_NEW, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")

    # 更新 status.json 的构建完成时间 + 时效性元数据协调（仅在 dist 中）
    dist_status_path = os.path.join(DIST_NEW, "data", "status.json")
    dist_status = load_json(dist_status_path, {})
    if dist_status:
        dist_status["build_completed_at"] = bj_iso()
        dist_status["build_completed_at_beijing"] = bj_format()
        # P0-FRESHNESS：用经当前生产视图验证的截止时间覆盖 status.json 中可能
        # 被 legacy ai_intelligence.json 污染的 data_as_of（II.4：与本次生产数据一致）。
        # 保留来源与状态语义（data_as_of_source / data_as_of_status）。
        if meta.get("data_as_of"):
            dist_status["data_as_of"] = meta["data_as_of"]
            dist_status["data_as_of_bj"] = meta.get("data_as_of_bj") or ""
            dist_status["data_as_of_source"] = meta.get("data_as_of_source") or ""
            dist_status["data_as_of_status"] = meta.get("data_as_of_status") or ""
            dist_status["data_updated_at"] = meta["data_as_of"]
        # 语义化时间字段（区分采集/分析/公开截止/构建；build_time 不冒充数据更新）
        dist_status["collection_as_of"] = meta.get("collection_as_of") or ""
        dist_status["analysis_as_of"] = meta.get("analysis_as_of") or ""
        # 页脚 last_updated_beijing 与公开时效真值一致（避免仍显示陈旧时间）
        if meta.get("data_as_of_bj"):
            dist_status["last_updated_beijing"] = meta["data_as_of_bj"]
        # II.4：把可验证的对外计数同步为真实值
        _reconcile_status_counts(dist_status)
        save_json(dist_status_path, dist_status)

    # 纯改名交换：.dist_new -> dist
    try:
        _finish_swap()
    except Exception as e:  # noqa: BLE001
        print("  FATAL: DIST_SWAP_FAILED —— 无法把 .dist_new 交换为 dist：%s" % e)
        print("         最常见原因：有进程以 dist 为工作目录（本地预览服务 / 编辑器索引）。")
        print("         本次构建**未发布**，dist 保持原样；.dist_new 已保留供排查。")
        raise

    # 构建后硬校验：dist/data/reports 必须精确反映本次构建（§2/§4/§5）
    verify_report_publication(DIST)

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
    args = ap.parse_args()
    main(run_id=args.run_id, no_embed=args.no_embed)
