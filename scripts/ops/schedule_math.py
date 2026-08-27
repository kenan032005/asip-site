#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 8C Package3 — Schedule math（§五/§七/§八/§九/§二十六）。

北京时间 → UTC 转换与验证（GitHub Actions cron 为 UTC）：
  UTC = Beijing - 8h（跨日则前一天）。

生产 schedule（北京时间）：
  Social collection : 00:20 / 06:20 / 12:20 / 18:20（每 6h）
  Social AI         : 00:30 / 06:30 / 12:30 / 18:30
  Disease AI        : 01:30（每天一次）
  Africa Daily      : 20:00（每天）
  Country Weekly    : 周日 06:45
"""
from datetime import datetime, timedelta


def bj_to_utc(bj_hm, date=None):
    """'HH:MM' 北京时间 → UTC datetime。date 省略时为相对"今天/昨天"。
    返回 (utc_hour, utc_minute, day_offset)。"""
    hh, mm = int(bj_hm.split(":")[0]), int(bj_hm.split(":")[1])
    bj = datetime(2000, 1, 1, hh, mm) - timedelta(hours=8)  # UTC = BJ - 8h
    return bj.hour, bj.minute, -1 if bj.day != 1 else 0


def bj_to_utc_cron(bj_hm):
    """'HH:MM'（北京时间）→ 'MM HH'（UTC cron 分钟/小时）。day_offset 由 workflow 注释说明。"""
    h, m, off = bj_to_utc(bj_hm)
    return "%02d %02d" % (m, h), off


SCHEDULES = {
    "social_collection": ["00:20", "06:20", "12:20", "18:20"],
    "social_ai": ["00:30", "06:30", "12:30", "18:30"],
    "disease_ai": ["01:30"],
    "africa_daily": ["20:00"],
    "country_weekly": ["06:45"],  # 北京周日 06:45 → UTC 周六 22:45（cron DOW=6）
}


def render_cron_list(bj_times):
    """多个北京时间 → 单条 UTC cron 表达式（小时列表，分钟同）。
    例：00:20/06:20/12:20/18:20 → '20 16,22,4,10 * * *'（注意跨日语义）。
    """
    utc = [bj_to_utc(t)[:2] for t in bj_times]
    mins = sorted({m for _, m in utc})
    hrs = sorted({h for h, _ in utc})
    if len(mins) == 1 and len(hrs) > 1:
        return "%02d %s * * *" % (mins[0], ",".join(str(h) for h in hrs))
    # 逐条渲染
    return "; ".join("%02d %02d * * *" % (m, h) for h, m in sorted(utc))


def verify_schedule(bj_hm, expected_utc_hm):
    """验证北京时间→UTC 转换与预期一致（§三十 schedule math 测试）。"""
    h, m, off = bj_to_utc(bj_hm)
    return "%02d:%02d" % (h, m) == expected_utc_hm, (h, m, off)


# GitHub Actions cron DOW：0=Sunday, 1=Monday ... 6=Saturday（与 cron 标准一致）。
# Python weekday()：0=Monday ... 6=Sunday。转换：cron_dow = (py_dow + 1) % 7。
_CRON_DOW_NAME = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def verify_weekly_dow(bj_dow_py, bj_hm, cron_dow):
    """验证"北京 星期X HH:MM"换算为 UTC cron 的 DOW 是否一致（跨日语义）。

    bj_dow_py : Python weekday() 语义（0=Monday ... 6=Sunday）。
    cron_dow  : GitHub Actions cron 的 DOW（0=Sunday ... 6=Saturday）。
    内部用真实日期（2026-08-30 为周日）计算 UTC 日历日并换算 cron DOW。
    """
    base = datetime(2026, 8, 30)  # 周日（Python weekday=6），仅作锚点
    # 找到最近的、满足 bj_dow_py 的日期
    shift = (bj_dow_py - base.weekday()) % 7
    bj_day = base + timedelta(days=shift)
    hh, mm = int(bj_hm.split(":")[0]), int(bj_hm.split(":")[1])
    bj_dt = bj_day.replace(hour=hh, minute=mm)
    utc_dt = bj_dt - timedelta(hours=8)
    utc_cron_dow = (utc_dt.weekday() + 1) % 7
    expected_bj = utc_dt + timedelta(hours=8)
    ok = utc_cron_dow == cron_dow
    return ok, {
        "bj_dow": _CRON_DOW_NAME[(bj_dow_py + 1) % 7],
        "bj_time": bj_hm,
        "utc_datetime": utc_dt.strftime("%Y-%m-%d %H:%M UTC"),
        "utc_cron_dow": utc_cron_dow,
        "cron_dow": cron_dow,
        "cron_dow_name": _CRON_DOW_NAME[cron_dow],
        "roundtrip_bj": expected_bj.strftime("%Y-%m-%d %H:%M BJT"),
        "ok": ok,
    }


if __name__ == "__main__":
    for name, times in SCHEDULES.items():
        print("%-20s BJ=%s -> UTC cron: %s" % (name, times,
                                               render_cron_list(times)))
