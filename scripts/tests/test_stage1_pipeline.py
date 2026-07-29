#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第一阶段收尾整改回归测试。

运行：python scripts/tests/test_stage1_pipeline.py
输出与 test_country.py 一致的 PASS/FAIL 汇总，FAIL>0 时退出码非零。

覆盖项（对应第一阶段验收清单）：
- run_id 格式与时间真实性
- 真实时区（ZoneInfo Asia/Shanghai / UTC，禁止 utc+8h 手工换算漂移）
- 日报目标日期（22:00 窗口边界）
- parse_time 尊重原始时区偏移
- 统一公开统计（pv2 闸门 / 隔离 / 窗口）
- Stage1 质量闸门（国家范围）
- 信息源真实统计（杜绝 enabled=success）
- 运行锁（互斥 / 重入 / 释放）
- 校验失败返回非零退出码
- 源码无本机绝对路径
- status.json 元数据健康
"""
import os
import re
import sys
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import pipeline_core as pc  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  PASS  %s" % name)
    else:
        FAIL += 1
        print("  FAIL  %s" % name)


# ── 1. run_id 格式与真实性 ──────────────────────────────
print("== run_id ==")
rid = pc.generate_run_id()
check("run_id 格式 YYYYMMDDTHHMMSS+0800_xxxxxx",
      re.fullmatch(r"\d{8}T\d{6}\+0800_[a-z0-9]{6}", rid) is not None)
try:
    rid_dt = datetime.strptime(rid[:15], "%Y%m%dT%H%M%S")
    drift = abs((rid_dt - pc.bj_now()).total_seconds())
except Exception:
    drift = 99999
check("run_id 时间戳与真实北京时间偏差 < 120s", drift < 120)
check("两次生成的 run_id 不重复", pc.generate_run_id() != rid)

# ── 2. 真实时区 ────────────────────────────────────────
print("== 真实时区 ==")
check("bj_iso 带 +08:00 后缀", pc.bj_iso().endswith("+08:00"))
check("utc_iso 带 +00:00 后缀", pc.utc_iso().endswith("+00:00"))
diff_h = (pc.bj_now() - pc.utc_now()).total_seconds() / 3600
check("bj_now 与 utc_now 差 8 小时（ZoneInfo 换算）", abs(diff_h - 8) < 0.02)
ref = datetime.now(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
check("bj_now 与 ZoneInfo(Asia/Shanghai) 一致", abs((pc.bj_now() - ref).total_seconds()) < 5)

# ── 3. parse_time 尊重原始偏移 ──────────────────────────
print("== parse_time ==")
t = pc.parse_time("2026-07-29T00:00:00Z")
check("Z 后缀按 UTC 换算为北京 08:00", t is not None and t.hour == 8)
t = pc.parse_time("2026-07-29T12:00:00+03:00")
check("+03:00 偏移换算为北京 17:00", t is not None and t.hour == 17)
t = pc.parse_time("2026-07-29T15:30:00")
check("naive 时间视为北京墙钟不再偏移", t is not None and t.hour == 15 and t.minute == 30)
check("空/垃圾输入返回 None", pc.parse_time("") is None and pc.parse_time("not-a-time") is None)

# ── 4. 日报窗口目标日期（22:00 边界）────────────────────
print("== 日报目标日期 ==")
d = pc.get_latest_completed_report_date(datetime(2026, 7, 29, 21, 59))
check("21:59 → 目标为前一天", d == datetime(2026, 7, 28).date())
d = pc.get_latest_completed_report_date(datetime(2026, 7, 29, 22, 0))
check("22:00 → 目标为当天", d == datetime(2026, 7, 29).date())
d = pc.get_latest_completed_report_date(datetime(2026, 7, 30, 0, 5))
check("次日 00:05 → 目标为前一天", d == datetime(2026, 7, 29).date())

# ── 5. 统一公开统计与 pv2 闸门 ──────────────────────────
print("== 公开统计 / 质量闸门 ==")
now = pc.bj_now()
fresh = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
old3d = (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")


def ev(**kw):
    base = {"pipeline_version": 2, "event_id": "e1", "title_cn": "测试事件",
            "country": "乍得", "published_time": fresh, "quality_gate_passed": True}
    base.update(kw)
    return base


stats = pc.calculate_public_statistics([ev()], now=now)
check("pv2 有效事件计入 24h", stats["events_24h"] == 1 and stats["chad_events_24h"] == 1)
stats = pc.calculate_public_statistics([ev(pipeline_version=1)], now=now)
check("pv<2 旧数据不计入统计", stats["events_24h"] == 0 and stats["current_event_count"] == 0)
stats = pc.calculate_public_statistics([ev(publication_status="quarantined")], now=now)
check("quarantined 事件被隔离", stats["current_event_count"] == 0)
stats = pc.calculate_public_statistics([ev(quality_gate_passed=False)], now=now)
check("闸门未通过事件不计入", stats["current_event_count"] == 0)
stats = pc.calculate_public_statistics([ev(published_time=old3d, country="尼日尔")], now=now)
check("3 天前事件计 7d 不计 24h", stats["events_24h"] == 0 and stats["niger_events_7d"] == 1)
stats = pc.calculate_public_statistics([ev(title_cn="")], now=now)
check("缺 title_cn 字段不完整事件剔除", stats["current_event_count"] == 0)
check("Stage1 闸门拒绝范围外国家", not pc.passes_stage1_gate(ev(country="尼日利亚")))
check("Stage1 闸门放行乍得有效事件", pc.passes_stage1_gate(ev()))

# ── 6. 信息源真实统计 ──────────────────────────────────
print("== 信息源统计 ==")
srcs = [
    {"enabled": True, "status": "active", "last_test_at": "2026-07-29T10:00:00+08:00",
     "articles_detected_last_run": 5, "relevant_articles_last_run": 1},
    {"enabled": True, "status": "failed", "last_test_at": "2026-07-29T10:00:00+08:00"},
    {"enabled": True},  # enabled 但从未测试
    {"enabled": False, "status": "paused"},
]
ss = pc.compute_source_statistics(srcs)
check("enabled != request_success（杜绝 enabled=success）",
      ss["source_enabled_count"] == 3 and ss["source_request_success_count_last_run"] == 1)
check("failed 源如实计数", ss["source_failed_count_last_run"] == 1)
check("有产出源仅按真实抓取计数", ss["source_with_articles_count_last_run"] == 1
      and ss["source_with_relevant_articles_count_last_run"] == 1)

# ── 7. 运行锁 ──────────────────────────────────────────
print("== 运行锁 ==")
_orig_lock = pc.LOCK_FILE
tmp_lock = Path(tempfile.mkdtemp()) / "test.pipeline.lock"
pc.LOCK_FILE = tmp_lock
try:
    check("首次获取锁成功", pc.acquire_lock("run_A") is True)
    check("他人持锁时获取失败", pc.acquire_lock("run_B") is False)
    check("同 run_id 重入允许", pc.acquire_lock("run_A") is True)
    pc.release_lock("run_A")
    released = (not tmp_lock.exists()) or json.loads(
        tmp_lock.read_text(encoding="utf-8")).get("released") is True
    check("释放后锁文件删除或标记 released", released)
    check("释放后可重新获取", pc.acquire_lock("run_C") is True)
    pc.release_lock("run_C")
finally:
    pc.LOCK_FILE = _orig_lock

# ── 8. 校验失败必须返回非零 ─────────────────────────────
print("== 校验退出码 ==")
import validate_pipeline  # noqa: E402
rc = validate_pipeline.main(run_id="20990101T000000+0800_zzzzzz",
                            dist_dir=os.path.join(ROOT, "__no_such_dist__"),
                            stage="dist")
check("dist 缺失/run_id 不符时校验返回非零", rc != 0)

# ── 9. 源码无本机绝对路径 ──────────────────────────────
print("== 绝对路径扫描 ==")
needle_a = "C:" + "\\" + "Users"
needle_b = "C:" + "/Users"
offenders = []
scan_dirs = [os.path.join(ROOT, "scripts")]
scan_files = [p for d in scan_dirs for p in Path(d).rglob("*.py")]
scan_files += list(Path(ROOT).glob("*.html")) + list(Path(ROOT).glob("*.md"))
for p in scan_files:
    if p.resolve() == Path(__file__).resolve():
        continue
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if needle_a in txt or needle_b in txt:
        offenders.append(str(p.relative_to(ROOT)))
check("scripts/*.py 与根 HTML/MD 无本机绝对路径 %s" % (offenders or ""), not offenders)

# ── 10. status.json 元数据健康 ─────────────────────────
print("== status.json ==")
status_path = os.path.join(ROOT, "data", "status.json")
try:
    st = json.load(open(status_path, encoding="utf-8"))
except Exception:
    st = {}
check("status.json 存在且可解析", bool(st))
check("status.json pipeline_version == 2", st.get("pipeline_version") == 2)
check("status.json run_id 格式合法",
      re.fullmatch(r"\d{8}T\d{6}\+0800_[a-z0-9]{6}", str(st.get("run_id", ""))) is not None)
check("status.json 不含自引用 gh_pages_commit", "gh_pages_commit" not in st)

# ── 汇总 ───────────────────────────────────────────────
print()
print("PASS=%d FAIL=%d" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
