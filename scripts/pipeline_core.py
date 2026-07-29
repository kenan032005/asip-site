#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline_core.py —— ASIP Stage-1 主链路基础模块

提供：
1. 统一 run_id 生成与追踪
2. 北京时间辅助函数
3. pipeline_version=2 隔离规则
4. 结构化运行日志
5. 数据质量闸门检查
"""

import json
import os
import random
import string
from datetime import datetime, timedelta, timezone

# ── 基础配置 ──────────────────────────────────────────────
PIPELINE_VERSION = 2
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
TZ_BEIJING = timezone(timedelta(hours=8))

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
    "serious_crime": "���重刑事犯罪",
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

# ── 时间工具 ──────────────────────────────────────────────

def bj_now():
    """返回 naive 北京时间 datetime（无时区信息，方便与各种时间格式比较）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=8)


def bj_iso():
    """返回带时区的北京时间 ISO 8601 字符串。"""
    return (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()


def bj_format(dt=None):
    """返回北京时间格式化字符串 YYYY-MM-DD HH:MM:SS。"""
    if dt is None:
        dt = bj_now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def bj_24h_ago():
    """返回北京时间 24 小时前的 datetime。"""
    return bj_now() - timedelta(hours=24)


def bj_7d_ago():
    """返回北京时间 7 天前的 datetime。"""
    return bj_now() - timedelta(days=7)


def parse_time(s):
    """尝试多种格式解析时间字符串，返回 naive datetime 或 None。"""
    if not s:
        return None
    s = str(s).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
    ):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=timezone.utc).astimezone(TZ_BEIJING)
                dt = dt.replace(tzinfo=None)
            return dt
        except (ValueError, OverflowError):
            continue
    # ISO parsing
    try:
        from datetime import timezone as tz
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=timezone.utc).astimezone(TZ_BEIJING)
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        return None


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


# ── 结构化日志 ────────────────────────────────────────────

def create_run_log(run_id, trigger="manual"):
    """创建空运行日志骨架。"""
    return {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": run_id,
        "trigger": trigger,
        "started_at": bj_iso(),
        "steps": [],
        "main_commit": "",
        "gh_pages_commit": "",
        "online_run_id": "",
        "final_status": "running",
    }


def add_log_step(log, name, status, started_at="", completed_at="", details=None):
    """向运行日志追加一步。"""
    log.setdefault("steps", []).append({
        "name": name,
        "status": status,
        "started_at": started_at or bj_iso(),
        "completed_at": completed_at or bj_iso(),
        "details": details or {},
    })


def save_run_log(log, run_id):
    """保存运行日志到 logs/pipeline_<run_id>.json。"""
    log["completed_at"] = bj_iso()
    os.makedirs(LOGS_DIR, exist_ok=True)
    path = os.path.join(LOGS_DIR, f"pipeline_{run_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    return path


# ── pipeline_version=2 质量闸门 ────────────────────────────

def passes_stage1_gate(event):
    """
    判断一条事件是否通过 Stage 1 质量闸门。
    乍得/尼日尔必须满足：
      - pipeline_version == 2
      - quality_gate_passed is True (or absent — backward compat)
      - 未进入 quarantine
      - country 为乍得 or 尼日尔
    """
    # 不在 quarantine 中（由调用方在数据层过滤，这里只做字段检查）
    country = event.get("country", "")
    if country not in STAGE1_COUNTRIES:
        return False

    # pipeline_version 检查
    pv = event.get("pipeline_version", 0)
    if pv < 2:
        return False

    # quality_gate_passed（缺省视为 true — 兼容通过旧管道进入的新事件）
    if "quality_gate_passed" in event and not event.get("quality_gate_passed"):
        return False

    # publication_status 检查
    ps = event.get("publication_status", "")
    if ps in ("suppressed", "withdrawn", "quarantined"):
        return False

    # 基本字段完整性
    if not event.get("event_id") or not event.get("title_cn"):
        return False

    return True


def is_stage1_country(country_name):
    """判断是否为 Stage 1 目标国家（乍得/尼日尔）。"""
    return country_name in STAGE1_COUNTRIES


# ── 数据统计工具 ──────────────────────────────────────────

def count_events_24h(events, country=None):
    """统计北京时间最近 24 小时内的事件数。"""
    now = bj_now()
    cutoff = now - timedelta(hours=24)
    count = 0
    for e in events:
        if country is not None and e.get("country") != country:
            continue
        t = (e.get("published_time") or e.get("event_time") or e.get("created_at") or "")
        dt = parse_time(t)
        if dt and dt >= cutoff and dt <= now:
            count += 1
    return count


def count_events_7d(events, country=None):
    """统计北京时间最近 7 天内的事件数。"""
    now = bj_now()
    cutoff = now - timedelta(days=7)
    count = 0
    for e in events:
        if country is not None and e.get("country") != country:
            continue
        t = (e.get("published_time") or e.get("event_time") or e.get("created_at") or "")
        dt = parse_time(t)
        if dt and dt >= cutoff and dt <= now:
            count += 1
    return count


# ── JSON 安全读写 ─────────────────────────────────────────

def load_json(path, default=None):
    """安全读取 JSON 文件。"""
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return default


def save_json(path, data):
    """安全写入 JSON 文件。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 事件类型标准化 ────────────────────────────────────────

def normalize_event_type(raw_type):
    """
    将事件类型统一为英文枚举代码。
    输入：中文 or 英文 or None
    输出：英文代码（无法识别 → other_security）
    """
    if not raw_type:
        return "other_security"
    if raw_type in EVENT_TYPE_CN:
        return raw_type  # 已是英文代码
    if raw_type in EVENT_TYPE_EN:
        return EVENT_TYPE_EN[raw_type]
    # 模糊匹配
    for en, cn in EVENT_TYPE_CN.items():
        if cn == raw_type or raw_type in cn:
            return en
    return "other_security"


def event_type_cn(english_code):
    """英文代码 → 中文显示，未识别返回'其他安全事件'。"""
    return EVENT_TYPE_CN.get(english_code, "其他安全事件")
