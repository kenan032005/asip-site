#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""factory.py — C4-A Report Factory 核心契约（窗口 / ID / 过滤 / hash / cache / gate / index / planner）。

设计原则：**复用既有报告 pipeline**（scripts/report/gen 的 fact_pack / deterministic_assembler /
machine_gates、scripts/report/selection 的 importance_score、scripts/report/weekly 的周指标），
本模块只补"报告工厂"缺失的那一层契约，不另造平行 pipeline。

已固化的口径（来自 repo 既有事实，不是自定）：
  * DAILY_WINDOW_TYPE = ROLLING_24H（period_end = 目标报告日 20:00 BJT；period_start = −24h）
  * REPORT_TIMEZONE   = Asia/Shanghai (UTC+8)
  * WEEK_IDENTITY     = SUNDAY_TO_SUNDAY，且为**闭区间**（weekly.py: ``week_start <= date <= week_end``）
  * PRIORITY_COUNTRY_POLICY = CONFIG_DRIVEN（config.PRIORITY_REPORT_COUNTRIES）
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from datetime import datetime, timedelta, timezone

BJT = timezone(timedelta(hours=8))

DAILY_WINDOW_TYPE = "ROLLING_24H"
DAILY_CUTOFF_HOUR_BJT = 20
REPORT_TIMEZONE = "Asia/Shanghai"
WEEK_IDENTITY = "SUNDAY_TO_SUNDAY"
WEEK_INTERVAL_INCLUSIVITY = "CLOSED"          # 两端都含（与 weekly.py 一致）
PRIORITY_COUNTRY_POLICY = "CONFIG_DRIVEN"

REPORT_TYPES = ("africa_daily", "africa_weekly", "country_weekly", "major_event_brief")
MAJOR_BRIEF_AUTO_PUBLICATION = False          # C4 不得改变

PIPELINE_VERSION = "v2"
ARCH_VERSION = "deterministic-facts-ai-analysis-v1"
PROMPT_VERSION = "analysis-v1.0.0"

REPORT_STATUSES = ("FULL", "FALLBACK", "LOW_DATA", "FAIL")
PUBLISHABLE_STATUSES = ("FULL", "FALLBACK", "LOW_DATA")   # 只有 FAIL 阻断物化

#: fact pack hash 必须剔除的墙钟/运行时字段（避免重演 C3 homepage hash 随墙钟漂移）
HASH_DROP_KEYS = ("generated_at", "cutoff", "runtime", "cache_hit", "built_at", "now")

#: AI 只允许产出的分析字段
AI_ALLOWED_FIELDS = ("executive_assessment", "trend_analysis", "outlook", "watch_points")


# ── 时间窗口 ────────────────────────────────────────────────────────────
def daily_window(report_date):
    """目标报告日的滚动 24h 窗口（cutoff = 当日 20:00 BJT）。

    period_end   = report_date 20:00 BJT
    period_start = period_end − 24h
    **generated_at 不参与**窗口计算。
    """
    if isinstance(report_date, str):
        report_date = datetime.strptime(report_date[:10], "%Y-%m-%d").date()
    end = datetime(report_date.year, report_date.month, report_date.day,
                   DAILY_CUTOFF_HOUR_BJT, 0, 0, tzinfo=BJT)
    return end - timedelta(hours=24), end


def week_window(week_end):
    """Sunday → Sunday **闭区间**周窗口（week_end 必须为周日）。

    与既有 weekly.py 的 ``week_start <= date <= week_end`` 语义一致。
    """
    if isinstance(week_end, str):
        week_end = datetime.strptime(week_end[:10], "%Y-%m-%d").date()
    if week_end.weekday() != 6:
        raise ValueError("week_end must be a Sunday (got %s)" % week_end)
    return week_end - timedelta(days=7), week_end


def last_complete_week_end(now=None):
    """最近一个**已完整结束**的周日（严格早于 now 的当天，避免拿未完成的周）。"""
    now = now or datetime.now(BJT)
    d = now.date()
    days_back = (d.weekday() + 1) % 7          # 到最近周日（含今天）的距离
    last_sun = d - timedelta(days=days_back)
    if last_sun == d and now.hour < DAILY_CUTOFF_HOUR_BJT:
        last_sun -= timedelta(days=7)          # 今天就是周日但还没到 cutoff → 用上一个
    return last_sun


def data_as_of(root):
    """canonical 数据边界（只读 data/status.json）。"""
    try:
        with io.open(os.path.join(str(root), "data", "status.json"), encoding="utf-8") as f:
            return json.load(f).get("data_as_of")
    except Exception:  # noqa: BLE001
        return None


# ── Report ID ───────────────────────────────────────────────────────────
def build_report_id(report_type, report_date=None, week_end=None, country_iso3=None):
    """稳定 report ID。相同 type/period/country 必须完全一致。

    沿用既有命名规范：
      DAILY_<YYYYMMDD>            （日期 = 该 20:00 BJT cutoff 所属报告日）
      WEEKLY_<ISO3>_<YYYYMMDD>    （country weekly，week_end 紧凑日期）
      AFRICA_WEEKLY_<YYYYMMDD>    （africa weekly 新注册）
      BRIEF_<...>
    """
    if report_type == "africa_daily":
        d = report_date
        if isinstance(d, str):
            d = d[:10].replace("-", "")
        else:
            d = d.strftime("%Y%m%d")
        return "DAILY_%s" % d
    if report_type == "country_weekly":
        if not country_iso3:
            raise ValueError("country_weekly requires country_iso3")
        w = week_end if isinstance(week_end, str) else week_end.strftime("%Y-%m-%d")
        return "WEEKLY_%s_%s" % (str(country_iso3).upper(), str(w)[:10].replace("-", ""))
    if report_type == "africa_weekly":
        w = week_end if isinstance(week_end, str) else week_end.strftime("%Y-%m-%d")
        return "AFRICA_WEEKLY_%s" % str(w)[:10].replace("-", "")
    if report_type == "major_event_brief":
        raise ValueError("major_event_brief id 由既有 brief.py 生成，C4 不接管")
    raise ValueError("unknown report_type: %s" % report_type)


# ── 报告可用性过滤（§十六）────────────────────────────────────────────
#: 纯体育/娱乐/生活方式的确定性特征词（**仅作用于 Report Fact Pack**，不改全站 relevance）
REPORT_EXCLUDED_TOPICS = (
    "sports", "体育", "football", "soccer", "futebol", "match", "league",
    "world cup", "olympic", "basketball", "tennis", "fifa", "afcon",
    "entertainment", "celebrity", "娱乐", "lifestyle", "生活方式",
    "football club", "friendly", "coupe du monde",
)
#: 安全相关豁免：命中即**不得**仅因 sports 关键词排除
REPORT_SECURITY_EXEMPT = (
    "riot", "stampede", "terror", "attack", "bomb", "killed", "death",
    "protest", "unrest", "clash", "crowd crush", "public order",
    "骚乱", "踩踏", "恐袭", "袭击", "死亡", "抗议", "冲突", "公共秩序",
)


def report_eligibility(text, event_type=None):
    """确定性报告可用性判定。返回 (eligible: bool, reason: str)。

    eligible=False 仅当"命中题材特征词"且"未命中安全豁免"。
    """
    blob = ("%s %s" % (text or "", event_type or "")).lower()
    topic = next((k for k in REPORT_EXCLUDED_TOPICS if k in blob), None)
    if not topic:
        return True, "ELIGIBLE"
    exempt = next((k for k in REPORT_SECURITY_EXEMPT if k in blob), None)
    if exempt:
        return True, "SECURITY_RELATED_%s" % exempt.upper().replace(" ", "_")
    return False, "PURE_NON_SECURITY_%s" % topic.upper().replace(" ", "_")


def filter_report_facts(items, text_key="title_original", type_key="event_type"):
    kept, excluded = [], []
    for it in items or []:
        ok, reason = report_eligibility(it.get(text_key), it.get(type_key))
        (kept if ok else excluded).append(dict(it, _eligibility=reason))
    return kept, excluded


# ── hash ────────────────────────────────────────────────────────────────
def stable_projection(obj):
    """剔除墙钟/运行时字段的稳定投影（用于 fact_pack_hash）。

    注意：这是 **Report Fact Pack** 的投影，与 C3 的 homepage 投影互不影响。
    """
    if isinstance(obj, dict):
        return {k: stable_projection(v) for k, v in sorted(obj.items())
                if k not in HASH_DROP_KEYS}
    if isinstance(obj, list):
        return [stable_projection(v) for v in obj]
    return obj


def _sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def fact_pack_hash(fact_pack):
    return _sha(stable_projection(fact_pack))


#: 报告 fact pack 里对墙钟敏感、**不得进入 hash** 的字段
REPORT_WALLCLOCK_KEYS = ("generated_at", "cutoff", "built_at", "now",
                         "runtime", "cache_hit", "built_at_utc", "collected_at")


def report_pack_projection(fact_pack):
    """报告 fact pack 的稳定投影。

    真实缺陷：build_fact_pack 会把 generated_at 这类墙钟字段写进 pack（并进入
    numeric_provenance），导致 fact_pack_hash 每次运行都不同 →
    报告 AI 的 cache/fact-pack 一致性判定永远不命中（CI 上表现为 0 调用、0 FULL，
    且**没有任何报错**）。因此 hash 必须基于剔除墙钟字段后的稳定投影。
    """
    import copy as _copy
    p = _copy.deepcopy(fact_pack)
    for k in REPORT_WALLCLOCK_KEYS:
        p.pop(k, None)
    npv = p.get("numeric_provenance")
    if isinstance(npv, dict):
        kept = {}
        for n, paths in npv.items():
            pp = [x for x in (paths or [])
                  if not any(str(x).startswith(w) for w in REPORT_WALLCLOCK_KEYS)]
            if pp:
                kept[n] = pp
        p["numeric_provenance"] = kept
    return p


def report_pack_hash(fact_pack):
    """报告 fact pack 的确定性 hash（墙钟无关）。"""
    return _sha(report_pack_projection(fact_pack))


def input_hash(report_id, fph, model, report_type, prompt_version=PROMPT_VERSION):
    """report input_hash：id + fact pack hash + prompt + model + type。"""
    return _sha({"report_id": report_id, "fact_pack_hash": fph, "model": model,
                 "report_type": report_type, "prompt_version": prompt_version})


# ── cache / negative cache ──────────────────────────────────────────────
class ReportCache:
    """AI 结果缓存 + **终态负缓存**（复用 C3 教训：被拒结果也必须成为终态）。"""

    def __init__(self, path):
        self.path = str(path)
        self.data = {}
        try:
            with io.open(self.path, encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:  # noqa: BLE001
            self.data = {}

    def get(self, ih):
        return self.data.get(ih)

    def put_full(self, ih, analysis, meta=None):
        self.data[ih] = {"kind": "FULL", "analysis": analysis, "meta": meta or {}}
        self._flush()

    def put_negative(self, ih, reason, extra=None):
        """只保存安全元信息，**绝不保存被拒正文 / raw response**。"""
        self.data[ih] = {"kind": "NEGATIVE", "reason": reason,
                         "input_hash": ih, **(extra or {})}
        self._flush()

    def is_negative(self, ih):
        r = self.data.get(ih)
        return bool(r and r.get("kind") == "NEGATIVE")

    def should_call(self, ih):
        """同 input_hash 已在缓存（无论 FULL / NEGATIVE）→ 不再调用 provider。"""
        return ih not in self.data

    def _flush(self):
        d = os.path.dirname(self.path)
        if d:
            os.makedirs(d, exist_ok=True)
        tmp = self.path + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(tmp, self.path)


# ── fact gate（分析层）──────────────────────────────────────────────────
def analysis_fact_gate(fact_pack, analysis):
    """AI 分析不得引入新的数字/国家/地点/风险等级。返回 (ok, reasons)。"""
    if not analysis:
        return False, ["NO_ANALYSIS"]
    blob = json.dumps(stable_projection(fact_pack), ensure_ascii=False)
    text = json.dumps({k: analysis.get(k) for k in AI_ALLOWED_FIELDS if k in analysis},
                      ensure_ascii=False)
    reasons = []
    import re
    for n in set(re.findall(r"\d+(?:[.,]\d+)?", blob)):
        if len(n.replace(".", "").replace(",", "")) >= 2 and n not in text:
            pass          # 允许漏提数字；只禁止"新增"
    for n in set(re.findall(r"\d+(?:[.,]\d+)?", text)):
        if len(n.replace(".", "").replace(",", "")) >= 2 and n not in blob:
            reasons.append("NEW_NUMBER:%s" % n)
    for iso in set(re.findall(r"\b[A-Z]{3}\b", text)):
        if iso not in blob and iso not in ("AI", "FULL", "JSON"):
            reasons.append("NEW_COUNTRY_TOKEN:%s" % iso)
    return (not reasons), reasons


# ── index ───────────────────────────────────────────────────────────────
def build_report_index(reports, real_only=True):
    """确定性索引（real_only=True → mock 永不进入正式索引）。"""
    rows = []
    for r in reports or []:
        if real_only and (r.get("is_mock") or r.get("mock")):
            continue
        rows.append({k: r.get(k) for k in (
            "report_id", "report_type", "title", "title_cn", "period_start", "period_end",
            "country_iso3", "status", "data_as_of", "generated_at", "headline",
            "path", "fact_pack_hash")})
    rows.sort(key=lambda r: (str(r.get("period_end") or ""), str(r.get("report_id") or "")),
              reverse=True)
    return {"schema": "report-index-v2", "real_only": bool(real_only),
            "count": len(rows), "reports": rows}


# ── backfill planner ────────────────────────────────────────────────────
def enabled_priority_countries(config=None):
    """启用权只来自 config.PRIORITY_REPORT_COUNTRIES（§七/§九）。"""
    if config is None:
        try:
            from scripts.report import config as C
        except Exception:  # noqa: BLE001
            try:
                from report import config as C       # type: ignore
            except Exception:  # noqa: BLE001
                return {}, {}
        config = C.PRIORITY_REPORT_COUNTRIES
    en = {k: v for k, v in config.items() if v}
    dis = {k: v for k, v in config.items() if not v}
    return en, dis


def plan_report_backfill(root, days=14, now=None):
    """规划目标报告集合（**不物化、不调用 AI**）。

    Daily：最近 14 个 20:00 BJT 滚动 24h 逻辑窗口
    Weekly：所有完整 Sunday→Sunday 周（闭区间）
    Country Weekly：完整周 × 当前 enabled priority countries（1 国 1 周最多 1 份）
    """
    now = now or datetime.now(BJT)
    as_of = data_as_of(root)
    end_date = now.date()
    if as_of:
        try:
            end_date = datetime.fromisoformat(str(as_of).replace("Z", "+00:00")).astimezone(BJT).date()
        except Exception:  # noqa: BLE001
            pass
    daily = []
    for i in range(days):
        d = end_date - timedelta(days=i)
        s, e = daily_window(d)
        daily.append({"report_id": build_report_id("africa_daily", report_date=d),
                      "report_type": "africa_daily",
                      "report_date": str(d), "period_start": s.isoformat(),
                      "period_end": e.isoformat()})
    daily = list(reversed(daily))

    weeks = []
    wk = last_complete_week_end(now)
    while wk >= end_date - timedelta(days=days):
        s, e = week_window(wk)
        weeks.append({"week_start": str(s), "week_end": str(e),
                      "report_id": build_report_id("africa_weekly", week_end=wk)})
        wk -= timedelta(days=7)
    weeks = list(reversed(weeks))

    en, dis = enabled_priority_countries()
    country = []
    for w in weeks:
        for iso in sorted(en):
            country.append({"report_id": build_report_id("country_weekly",
                                                         week_end=w["week_end"],
                                                         country_iso3=iso),
                            "report_type": "country_weekly", "country_iso3": iso,
                            "week_start": w["week_start"], "week_end": w["week_end"],
                            "selection_reason": "CONFIGURED_PRIORITY_COUNTRY"})
    seen, uniq = set(), []
    for c in country:                      # 1 country 1 week 最多 1 份（硬门）
        if c["report_id"] in seen:
            continue
        seen.add(c["report_id"])
        uniq.append(c)
    return {"DAILY_WINDOW_TYPE": DAILY_WINDOW_TYPE,
            "DAILY_CUTOFF_BJT": "20:00", "REPORT_TIMEZONE": REPORT_TIMEZONE,
            "WEEK_IDENTITY": WEEK_IDENTITY, "WEEK_INTERVAL_INCLUSIVITY": WEEK_INTERVAL_INCLUSIVITY,
            "PRIORITY_COUNTRY_POLICY": PRIORITY_COUNTRY_POLICY,
            "ENABLED_PRIORITY_COUNTRIES": sorted(en), "DISABLED_CONFIGURED_COUNTRIES": sorted(dis),
            "DAILY_TARGET": len(daily), "DAILY_TARGET_DATES": daily,
            "WEEKLY_TARGET": len(weeks), "WEEKLY_TARGET_PERIODS": weeks,
            "COUNTRY_WEEKLY_TARGET": len(uniq), "COUNTRY_WEEKLY_TARGETS": uniq,
            "TOTAL_REPORT_TARGET": len(daily) + len(weeks) + len(uniq),
            "data_as_of": as_of}


# ── report type registry（africa_weekly 正式注册，不另造 pipeline）──
def registered_report_types():
    """在既有 pipeline 内注册的 report types（africa_weekly 为本轮新增）。"""
    return {
        "africa_daily": {"builder": "scripts.report.builder.build_daily_input",
                         "schema": "africa_daily_report.schema.json"},
        "africa_weekly": {"builder": "scripts.report.builder.build_africa_weekly_input",
                          "schema": "africa_weekly_report.schema.json"},
        "country_weekly": {"builder": "scripts.report.builder.build_weekly_input",
                           "schema": "country_weekly_report.schema.json"},
        "major_event_brief": {"builder": "scripts.report.brief",
                              "schema": "major_event_brief.schema.json",
                              "auto_publication": MAJOR_BRIEF_AUTO_PUBLICATION},
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="C4-A Report Factory dry run（不调用 AI）")
    ap.add_argument("--root", default=".")
    ap.add_argument("--days", type=int, default=14)
    a = ap.parse_args()
    plan = plan_report_backfill(a.root, a.days)
    out = {k: v for k, v in plan.items()
           if not k.endswith("_DATES") and not k.endswith("_TARGETS")
           and not k.endswith("_PERIODS")}
    out["AI_CALLS"] = 0
    print(json.dumps(out, ensure_ascii=False, indent=1))
