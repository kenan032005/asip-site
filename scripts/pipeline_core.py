#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline_core.py —— ASIP Stage-1 主链路基础模块（零依赖，跨平台）

提供：
1. 统一 run_id 生成与追踪
2. 真实时区处理（ZoneInfo: Asia/Shanghai / UTC）
3. pipeline_version=2 质量闸门
4. 统一公开统计函数 calculate_public_statistics
5. 信息源真实运行统计 compute_source_statistics
6. 日报目标日期计算 get_latest_completed_report_date
7. 运行锁 acquire_lock / release_lock（避免并发覆盖）
8. 线上轮询验证 online_verify（失败返回 False，由调用方转非零退出码）
9. 结构化运行日志
"""

import json
import os
import sys
import random
import string
import time
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── 真实时区（ZoneInfo，禁用 fake-UTC+8 写法）──────────────
try:
    from zoneinfo import ZoneInfo
    TZ_BEIJING = ZoneInfo("Asia/Shanghai")
    TZ_UTC = ZoneInfo("UTC")
except Exception:  # 极端兜底：仅在 ZoneInfo 完全不可用时
    TZ_BEIJING = timezone(timedelta(hours=8))
    TZ_UTC = timezone.utc

# ── 基础配置 ──────────────────────────────────────────────
PIPELINE_VERSION = 2
_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent
DATA_DIR = ROOT / "data"
LOGS_DIR = ROOT / "logs"
REPORTS_DIR = ROOT / "reports"
LOCK_FILE = DATA_DIR / ".pipeline.lock"
MAX_LOCK_AGE_MIN = 240  # 锁最长存活时间，超时视为陈旧可抢占

# Stage 1 目标国家
STAGE1_COUNTRIES = ("乍得", "尼日尔")

# 统一的英文事件类型代码 → 中文显示映射
EVENT_TYPE_CN = {
    "armed_conflict": "武装冲突",
    "terrorist_attack": "恐怖袭击",
    "military_operation": "军事行动",
    "political_crisis": "政治危机",
    "election_security": "选举安全",
    "protest": "抗议示威",
    "strike": "罢工",
    "civil_unrest": "社会动荡",
    "kidnapping": "绑架劫持",
    "serious_crime": "严重刑事犯罪",
    "communal_conflict": "社区及部族冲突",
    "border_security": "边境安全",
    "transport_disruption": "交通中断",
    "infrastructure_security": "基础设施安全",
    "natural_disaster": "自然灾害",
    "public_health": "传染病及公共卫生",
    "china_related": "涉华安全事件",
    "foreign_national_security": "外籍人员安全",
    "policy_security": "安全政策法规",
    "other_security": "其他安全事件",
}

# 中文事件类型 → 英文代码（兼容旧数据）
EVENT_TYPE_EN = {v: k for k, v in EVENT_TYPE_CN.items()}

# 国家固定风险等级（Stage 1 必须纠正）
FIXED_RISK_LEVELS = {
    "乍得": {"country_risk_level": 4, "country_risk_label": "极高"},
    "尼日尔": {"country_risk_level": 4, "country_risk_label": "极高"},
}


# ── 时间工具（真实时区）──────────────────────────────────

def bj_now():
    """返回 naive 北京时间 datetime（墙钟时间与北京时间一致，由 ZoneInfo 正确换算后剥离时区）。

    注意：剥离时区仅为兼容既有「naive 时间比较」逻辑；所有对外 ISO 字符串
    必须使用 bj_iso()/utc_iso()，确保后缀时区正确。
    """
    return datetime.now(TZ_UTC).astimezone(TZ_BEIJING).replace(tzinfo=None)


def bj_iso():
    """返回带正确时区的北京时间 ISO 8601 字符串（形如 2026-07-29T22:00:00+08:00）。"""
    return datetime.now(TZ_BEIJING).isoformat()


def utc_now():
    """返回 naive UTC datetime。"""
    return datetime.now(TZ_UTC).replace(tzinfo=None)


def utc_iso():
    """返回带正确时区的 UTC ISO 字符串（形如 2026-07-29T14:00:00+00:00）。"""
    return datetime.now(TZ_UTC).isoformat()


def bj_format(dt=None):
    """返回北京时间格式化字符串 YYYY-MM-DD HH:MM:SS。"""
    if dt is None:
        dt = bj_now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def bj_24h_ago():
    return bj_now() - timedelta(hours=24)


def bj_7d_ago():
    return bj_now() - timedelta(days=7)


def parse_time(s):
    """解析时间字符串为 naive 北京时间 datetime；无法解析返回 None。

    规则：
    - 带有时区偏移（含 Z）→ 正确 astimezone 到北京，**绝不覆盖已有偏移为 UTC**。
    - 纯 naive ISO/常见格式 → 直接返回（假定已是北京时间墙钟）。
    """
    if not s:
        return None
    s = str(s).strip()
    # 先尝试 ISO（含偏移 / Z）
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            # 尊重原始偏移，正确换算到北京后剥离
            return dt.astimezone(TZ_BEIJING).replace(tzinfo=None)
        return dt  # naive：假定已是北京时间
    except (ValueError, TypeError):
        pass
    # 常见格式兜底
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
    ):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is not None:
                return dt.astimezone(TZ_BEIJING).replace(tzinfo=None)
            return dt
        except ValueError:
            continue
    return None


def get_latest_completed_report_date(now_bj=None):
    """根据北京时间返回「已结束完整统计窗口」的最新日报目标日期。

    - 当前北京时间 < 22:00 → 目标为前一天（其窗口 [前前日22:00, 前日22:00] 已结束）
    - 当前北京时间 >= 22:00 → 目标为当天（其窗口 [前日22:00, 当日22:00] 刚结束）
    """
    now = now_bj or bj_now()
    if now.hour < 22:
        return (now - timedelta(days=1)).date()
    return now.date()


# ── run_id 生成 ───────────────────────────────────────────

def generate_run_id():
    """生成唯一运行标识。格式: YYYYMMDDTHHMMSS+0800_XXXXXX"""
    ts = bj_now().strftime("%Y%m%dT%H%M%S")
    suffix = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    return f"{ts}+0800_{suffix}"


def create_pipeline_meta(run_id):
    """创建统一 pipeline 元数据结构。"""
    return {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": run_id,
        "run_started_at": bj_iso(),
        "data_generated_at": "",
        "build_started_at": "",
        "build_completed_at": "",
        "deploy_started_at": "",
        "deploy_completed_at": "",
        "source_commit": "",
        "deployment_commit": "",
    }


# ── 运行锁（防并发覆盖）──────────────────────────────────

def acquire_lock(run_id, max_age_min=MAX_LOCK_AGE_MIN):
    """尝试获取运行锁。成功返回 True，已被其他活动运行持有则返回 False。

    注：锁"释放"以内容 released=True 或文件不存在为准（删除可能被环境
    的批量删除保护拦截，因此覆写与删除双轨）。
    """
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if LOCK_FILE.exists():
            try:
                raw = LOCK_FILE.read_text(encoding="utf-8").strip()
                info = json.loads(raw) if raw else {}
                if not info.get("released"):
                    started = parse_time(info.get("started_at", ""))
                    age = (bj_now() - started).total_seconds() / 60 if started else 9999
                    if age < max_age_min:
                        # 锁仍新鲜：若 run_id 相同（自身重入）则允许，否则拒绝
                        if info.get("run_id") == run_id:
                            return True
                        return False
                # 已释放或陈旧：直接覆写抢占（不依赖删除）
            except Exception:
                pass
        LOCK_FILE.write_text(
            json.dumps({
                "run_id": run_id,
                "pid": os.getpid(),
                "started_at": bj_iso(),
                "host": os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME", "unknown")),
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except Exception:
        # 锁机制失败不应阻断主流程
        return True


def release_lock(run_id=None):
    """释放运行锁。优先删除；删除被拦截时覆写 released=True（写不受删除保护限制）。"""
    try:
        if not LOCK_FILE.exists():
            return
        if run_id is not None:
            try:
                info = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
                if info.get("run_id") != run_id:
                    return
            except Exception:
                pass
        try:
            LOCK_FILE.unlink()
        except Exception:
            LOCK_FILE.write_text(
                json.dumps({"released": True, "run_id": run_id or "", "released_at": bj_iso()}),
                encoding="utf-8",
            )
    except Exception:
        pass


# ── 结构化日志 ────────────────────────────────────────────

def create_run_log(run_id, trigger="manual"):
    return {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": run_id,
        "trigger": trigger,
        "started_at": bj_iso(),
        "steps": [],
        "main_commit": "",
        "gh_pages_commit": "",
        "online_run_id": "",
        "online_verified_at": "",
        "final_status": "running",
    }


def add_log_step(log, name, status, started_at="", completed_at="", details=None):
    log.setdefault("steps", []).append({
        "name": name,
        "status": status,
        "started_at": started_at or bj_iso(),
        "completed_at": completed_at or bj_iso(),
        "details": details or {},
    })


def save_run_log(log, run_id):
    log["completed_at"] = bj_iso()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    path = LOGS_DIR / f"pipeline_{run_id}.json"
    path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


# ── pipeline_version=2 质量闸门 ────────────────────────────

def _is_current_event(event):
    """事件是否属于「当前有效」集合：pv2 + 闸门通过 + 未隔离 + 字段完整。"""
    if event.get("pipeline_version", 0) < 2:
        return False
    if "quality_gate_passed" in event and not event.get("quality_gate_passed"):
        return False
    ps = event.get("publication_status", "")
    if ps in ("suppressed", "withdrawn", "quarantined"):
        return False
    if not event.get("event_id") or not event.get("title_cn"):
        return False
    return True


def passes_stage1_gate(event):
    """Stage 1 质量闸门：仅乍得/尼日尔 + 当前有效。"""
    if event.get("country") not in STAGE1_COUNTRIES:
        return False
    return _is_current_event(event)


def is_stage1_country(country_name):
    return country_name in STAGE1_COUNTRIES


# ── 统一公开统计（status 与 summary 共用）─────────────────

def calculate_public_statistics(events, now=None):
    """统一统计函数。events 为事件列表。

    仅统计 pipeline_version>=2 且通过闸门且未隔离的「当前有效」事件，
    杜绝旧 pipeline 数据混入首页与统计。
    """
    now = now or bj_now()
    cut24 = now - timedelta(hours=24)
    cut7 = now - timedelta(days=7)

    current = [e for e in events if _is_current_event(e)]

    def in_window(e, cutoff):
        t = e.get("published_time") or e.get("event_time") or e.get("created_at") or ""
        dt = parse_time(t)
        return dt is not None and cutoff <= dt <= now

    events_24h = sum(1 for e in current if in_window(e, cut24))
    events_7d = sum(1 for e in current if in_window(e, cut7))
    chad_24h = sum(1 for e in current if e.get("country") == "乍得" and in_window(e, cut24))
    niger_24h = sum(1 for e in current if e.get("country") == "尼日尔" and in_window(e, cut24))
    chad_7d = sum(1 for e in current if e.get("country") == "乍得" and in_window(e, cut7))
    niger_7d = sum(1 for e in current if e.get("country") == "尼日尔" and in_window(e, cut7))

    return {
        "events_24h": events_24h,
        "events_7d": events_7d,
        "chad_events_24h": chad_24h,
        "niger_events_24h": niger_24h,
        "chad_events_7d": chad_7d,
        "niger_events_7d": niger_7d,
        "current_event_count": len(current),
        "published_event_count": len(events),
    }


# ── 信息源真实运行统计 ───────────────────────────────────

def compute_source_statistics(sources):
    """从 sources.json 计算真实运行统计，杜绝「enabled=success」。"""
    sources = sources or []
    configured = len(sources)
    enabled = sum(1 for s in sources if s.get("enabled"))
    tested = sum(1 for s in sources if s.get("tested") or s.get("last_test_at"))
    # 本轮请求成功：实际执行过测试且未处于失败/错误态
    request_success = sum(
        1 for s in sources
        if (s.get("status") in ("active", "degraded")) and s.get("last_test_at")
    )
    with_articles = sum(1 for s in sources if (s.get("articles_detected_last_run") or 0) > 0)
    with_relevant = sum(1 for s in sources if (s.get("relevant_articles_last_run") or 0) > 0)
    failed = sum(1 for s in sources if s.get("status") in ("failed", "error"))
    degraded = sum(1 for s in sources if s.get("status") == "degraded")
    blocked = sum(1 for s in sources if s.get("status") == "paused")
    requires_api = sum(1 for s in sources if s.get("requires_api"))
    # rate_limited：degraded 且备注/失败原因含 429 / rate / 限流
    rate_limited = 0
    for s in sources:
        note = " ".join(str(s.get(k, "")) for k in ("notes", "failure_reason", "last_error")).lower()
        if s.get("status") == "degraded" and ("429" in note or "rate" in note or "限流" in note or "throttl" in note):
            rate_limited += 1

    return {
        "source_configured_count": configured,
        "source_enabled_count": enabled,
        "source_tested_count": tested,
        "source_request_success_count_last_run": request_success,
        "source_with_articles_count_last_run": with_articles,
        "source_with_relevant_articles_count_last_run": with_relevant,
        "source_failed_count_last_run": failed,
        "source_degraded_count": degraded,
        "source_rate_limited_count_last_run": rate_limited,
        "source_blocked_count": blocked,
        "source_requires_api_count": requires_api,
    }


# ── 数据统计工具（供兼容）─────────────────────────────────

def count_events_24h(events, country=None):
    return calculate_public_statistics(events).get("events_24h")


def count_events_7d(events, country=None):
    return calculate_public_statistics(events).get("events_7d")


# ── JSON 安全读写 ─────────────────────────────────────────

def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception):
        return default


def save_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 事件类型标准化 ────────────────────────────────────────

def normalize_event_type(raw_type):
    """统一为英文枚举代码。"""
    if not raw_type:
        return "other_security"
    if raw_type in EVENT_TYPE_CN:
        return raw_type
    if raw_type in EVENT_TYPE_EN:
        return EVENT_TYPE_EN[raw_type]
    for en, cn in EVENT_TYPE_CN.items():
        if cn == raw_type or raw_type in cn:
            return en
    return "other_security"


def event_type_cn(english_code):
    return EVENT_TYPE_CN.get(english_code, "其他安全事件")


# ── 线上轮询验证 ──────────────────────────────────────────

def online_verify(run_id, base_url="https://kenan032005.github.io/asip-site",
                  timeout=300, poll=15, initial=15):
    """轮询线上 status.json，验证 run_id 一致。返回 (ok:bool, detail:dict)。"""
    import urllib.request
    url = f"{base_url.rstrip('/')}/data/status.json"
    deadline = time.time() + timeout
    time.sleep(initial)
    last = {}
    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                f"{url}?run_id={run_id}&t={int(time.time()*1000)}",
                headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"},
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
            online_rid = data.get("run_id", "")
            pv = data.get("pipeline_version")
            last = {
                "online_run_id": online_rid,
                "pipeline_version": pv,
                "last_updated_beijing": data.get("last_updated_beijing"),
                "events_24h": data.get("events_24h"),
                "http": r.status,
            }
            if online_rid == run_id and pv == PIPELINE_VERSION:
                last["verified_at"] = bj_iso()
                return True, last
        except Exception as e:
            last = {"error": str(e)}
        time.sleep(poll)
    return False, last


if __name__ == "__main__":
    # 简单自检
    print("bj_iso :", bj_iso())
    print("utc_iso:", utc_iso())
    print("bj_now :", bj_format())
    print("run_id :", generate_run_id())
    print("report_date(<22h):", get_latest_completed_report_date(
        datetime(2026, 7, 29, 4, 0, tzinfo=TZ_BEIJING).replace(tzinfo=None)))
    print("report_date(>=22h):", get_latest_completed_report_date(
        datetime(2026, 7, 29, 23, 30, tzinfo=TZ_BEIJING).replace(tzinfo=None)))
