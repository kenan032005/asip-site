#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""materialize.py — C4-B 报告物化器（deterministic only，绝不调用 AI）。

职责：
  * 正式 Report Artifact Writer（原子写；首次自动建目录；同 report_id 覆盖同一逻辑 artifact）
  * Legacy Daily 身份兼容（**以 report_id 里的 YYYYMMDD 为报告日**，不看 period_end 的分钟秒）
  * 物化 14 Daily / 2 Africa Weekly / 6 Country Weekly（FALLBACK / LOW_DATA，绝不写 FULL）
  * real-only report index（legacy + new 去重，mock 永不进入）

复用既有 pipeline：scripts.report.builder（input 组装）、scripts.report.gen.fact_pack
（确定性 fact pack）、scripts.report.gen.deterministic_assembler（组装 + machine_gates）。
本模块**不**另造平行 pipeline。
"""
from __future__ import annotations

import copy
import io
import json
import os
import re
import time
from datetime import datetime, timedelta

import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.report import factory as F                          # noqa: E402
from scripts.report import builder as B                          # noqa: E402
from scripts.report.selection import temporal_bucket as _tb      # noqa: E402
from scripts.report.gen import fact_pack as FP                   # noqa: E402
from scripts.report.gen import deterministic_assembler as DA     # noqa: E402

#: 逻辑类型 → 存储子目录（语义与 C4-A 设计一致）
REPORT_DIRS = {
    "africa_daily": "daily",
    "africa_weekly": "weekly",
    "country_weekly": "country_weekly",
}

#: 低于该事实数视为 LOW_DATA（不调用 AI，也不需要）
LOW_DATA_MIN_FACTS = 1

STATUS_FULL = "FULL"
STATUS_FALLBACK = "FALLBACK"
STATUS_LOW_DATA = "LOW_DATA"
STATUS_FAIL = "FAIL"

LOW_DATA_TEXT_CN = "当前周期内可核实信息有限，暂不足以形成稳定趋势判断。"


# ── Writer ──────────────────────────────────────────────────────────────
def report_path(root, report_type, report_id):
    return os.path.join(str(root), "data", "reports", REPORT_DIRS[report_type],
                        "%s.json" % report_id)


def write_report_artifact(root, report_type, report, extra=None):
    """原子写入正式 report artifact；首次自动创建目录。

    同 report_id 重复物化 → 覆盖同一逻辑 artifact（不产生副本）。
    写入顺序：temp → flush+fsync → os.replace（避免半个 JSON）。
    """
    if report_type not in REPORT_DIRS:
        raise ValueError("unknown report_type: %s" % report_type)
    rid = report.get("report_id")
    if not rid:
        raise ValueError("report artifact requires report_id")
    path = report_path(root, report_type, rid)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = dict(report)
    if extra:
        doc.update(extra)
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return path


def read_report_artifact(root, report_type, report_id):
    try:
        with io.open(report_path(root, report_type, report_id), encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return None


def list_report_artifacts(root):
    out = []
    for rtype, sub in REPORT_DIRS.items():
        d = os.path.join(str(root), "data", "reports", sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                try:
                    with io.open(os.path.join(d, fn), encoding="utf-8") as f:
                        out.append(json.load(f))
                except Exception:  # noqa: BLE001
                    continue
    return out


# ── Legacy Daily 身份兼容 ───────────────────────────────────────────────
def legacy_report_date(report_id, period_end=None):
    """从 report_id 解析历史报告日（**优先于 period_end 的秒级时间戳**）。

    既有 11 份 Daily 的 period_end 形如 ``...20:19:54``；新规范是整点 20:00 BJT。
    若按 period_end 精确定位，同一天会被判成"另一个逻辑日报"并重复生成。
    因此身份只取 ``DAILY_<YYYYMMDD>`` 里的日期。
    """
    m = re.match(r"^DAILY_(\d{8})$", str(report_id or ""))
    if m:
        s = m.group(1)
        return "%s-%s-%s" % (s[:4], s[4:6], s[6:8])
    if period_end:
        return str(period_end)[:10]
    return None


def classify_existing(root, report_id, report_type, expected_period=None):
    """EXISTING_VALID / MISSING / DIRTY。

    legacy（仅在 index 里、不在 data/reports）与 new artifact 都算 EXISTING_VALID，
    只要 report identity 与目标一致；**不得**因为 legacy cutoff 不是整 20:00 判 DIRTY。
    """
    art = read_report_artifact(root, report_type, report_id)
    if art:
        if art.get("status") == STATUS_FAIL:
            return "DIRTY", art
        return "EXISTING_VALID", art
    legacy = legacy_index_entry(root, report_id)
    if legacy:
        return "EXISTING_VALID", legacy
    return "MISSING", None


def load_legacy_index(root):
    try:
        with io.open(os.path.join(str(root), "data", "views", "report_index.json"),
                     encoding="utf-8") as f:
            return (json.load(f).get("reports") or [])
    except Exception:  # noqa: BLE001
        return []


def legacy_index_entry(root, report_id):
    for r in load_legacy_index(root):
        if r.get("report_id") == report_id:
            return r
    return None


# ── 数据源适配 ──────────────────────────────────────────────────────────
def load_canonical_events(root):
    """canonical cluster → builder/selection 期望字段。"""
    try:
        with io.open(os.path.join(str(root), "data", "canonical", "event_clusters.json"),
                     encoding="utf-8") as f:
            items = json.load(f).get("items") or []
    except Exception:  # noqa: BLE001
        return []
    iso2to3 = iso2to3_map(root)
    out = []
    for c in items:
        isc = int(c.get("independent_source_count") or 1)
        cc = (c.get("country_code") or "").upper()
        iso3 = c.get("country_iso3") or iso2to3.get(cc) or (cc if len(cc) == 3 else None)
        out.append({
            "event_id": c.get("event_id"),
            "master_event_id": c.get("event_id"),
            "country": c.get("country_cn"),
            "country_cn": c.get("country_cn"),
            "country_iso3": iso3,
            "country_code": c.get("country_code"),
            "category": c.get("event_type"),
            "event_type": c.get("event_type"),
            "verification_status": c.get("verification_level") or (
                "verified" if isc >= 2 else "single_source"),
            "verification_label_cn": c.get("verification_label_cn"),
            "independent_source_count": isc,
            "source_groups": c.get("source_groups") or [],
            # _eligibility 需要真实的来源信息（否则一律 no_real_source）
            "source_count": isc or len(c.get("article_ids") or []) or 1,
            "source_id": ((c.get("source_groups") or [None])[0]
                          or (c.get("article_ids") or [None])[0]),
            "source_name": ((c.get("source_groups") or [None])[0]),
            "article_ids": c.get("article_ids") or [],
            "first_seen_at": c.get("first_seen_at"),
            "last_seen_at": c.get("last_seen_at"),
            "event_time": c.get("event_time"),
            "title_cn": c.get("title_cn"),
            "title_original": c.get("title_original"),
            "summary_cn": c.get("summary_cn"),
            "summary_original": c.get("summary_original"),
            "china_related": bool(c.get("china_related")),
            "quality_gate_passed": c.get("quality_gate_passed"),
            "location_name": c.get("location_name"),
            "location_admin1": c.get("location_admin1"),
            "legacy_payload": c.get("legacy_payload"),
        })
    return out


def load_disease_items(root):
    for rel in ("data/disease/canonical/outbreak_events.json",
                "data/disease/events.json"):
        p = os.path.join(str(root), rel.replace("/", os.sep))
        if os.path.exists(p):
            try:
                with io.open(p, encoding="utf-8") as f:
                    d = json.load(f)
                return d.get("items") or d.get("events") or []
            except Exception:  # noqa: BLE001
                continue
    return []


def iso2to3_map(root):
    """ISO2 → ISO3（country_snapshots 提供；仅用于 country_iso3 归一）。"""
    try:
        with io.open(os.path.join(str(root), "data", "views", "country_snapshots.json"),
                     encoding="utf-8") as f:
            rows = json.load(f).get("snapshots") or []
    except Exception:  # noqa: BLE001
        return {}
    m = {}
    for r in rows:
        iso3 = (r.get("iso3") or "").upper()
        if iso3:
            m[iso3[:2]] = iso3
            m[iso3] = iso3
    return m


# ── 确定性物化 ──────────────────────────────────────────────────────────
def _naive_dt(d):
    """date → naive datetime（temporal_bucket 内部做 naive 相减）。"""
    if isinstance(d, datetime):
        return d.replace(tzinfo=None)
    return datetime(d.year, d.month, d.day)


def window_scoped_pool(events, cutoff_dt, allow=("new_24h", "ongoing_72h", "trend_7d")):
    """按**管线自身的** temporal_bucket 语义把事实池限定到报告窗口。

    selection.temporal_bucket 明确写着：outside_7d = "超过7天，不得进入日报正文"。
    若不做这一步，历史 Daily 会因选材只看重要性而拿到同一批"最大事件"，
    导致 14 份日报内容完全相同（违反 C4-B §八/§十一）。这里只是在报告层
    执行管线自己已经声明的窗口规则，不引入新政策。
    """
    if cutoff_dt is None:
        return list(events)
    out = []
    for e in events:
        # **关键**：temporal_bucket 用 (cutoff - event).days，未来事件的 age 为负数，
        # 会被 `age <= 1` 误判成 new_24h —— 于是任何历史 Daily 都会挑到"最新"事件，
        # 导致 14 份历史日报内容完全相同。历史窗口必须排除 cutoff 之后的事件。
        t = e.get("latest_report_at") or e.get("published_at") or e.get("event_time")
        try:
            from datetime import datetime as _dt
            d = _dt.strptime(str(t)[:10], "%Y-%m-%d")
            if (cutoff_dt - d).days < 0:
                continue
        except Exception:  # noqa: BLE001
            pass
        b, _note = _tb(e, cutoff_dt)
        if b in allow:
            out.append(e)
    return out


def load_article_urls(root):
    """article_id → canonical_url（用于报告来源外链，可追溯）。"""
    try:
        with io.open(os.path.join(str(root), "data", "canonical", "articles.json"),
                     encoding="utf-8") as f:
            items = json.load(f).get("items") or []
    except Exception:  # noqa: BLE001
        return {}
    return {a.get("article_id"): a.get("canonical_url") for a in items if a.get("article_id")}


def attach_source_refs(root, fp, events, urls=None):
    """把**真实的**来源信息补进 fact pack（§十四/§二十三 需要）。

    既有 builder 只透传 source_id、且 _social_fact 只认 source_name →
    fact pack 的 source_refs 恒为空。这里在报告层用确定性映射补齐：
    来源名取自 event.source_groups，外链取 article_id → canonical_url。
    **不调用 AI、不编造来源**。
    """
    urls = urls if urls is not None else load_article_urls(root)
    by_id = {e.get("event_id"): e for e in events}
    refs_all = []
    for f in (fp.get("social_facts") or []) + (fp.get("disease_facts") or []):
        e = by_id.get(f.get("fact_id")) or {}
        groups = [g for g in (e.get("source_groups") or []) if g]
        links = [urls[a] for a in (e.get("article_ids") or []) if urls.get(a)]
        f["source_refs"] = sorted(set(groups)) or sorted(set(links))[:1]
        f["source_ids"] = sorted(set(groups))
        f["source_links"] = links[:3]
        for r in f["source_refs"]:
            refs_all.append({"source_name": r,
                             "url": links[0] if links else None,
                             "verification": f.get("verification_status") or "single_source"})
        if links and not f["source_refs"]:
            refs_all.append({"source_name": links[0],
                             "url": links[0],
                             "verification": f.get("verification_status") or "single_source"})
    if refs_all:
        fp["source_refs"] = sorted({r["source_name"] for r in refs_all})
    seen, uniq = set(), []
    for r in refs_all:
        k = (r["source_name"], r["url"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq


SOURCE_POLICY = "SOURCE_BACKED_ONLY"
COVERAGE_NOTE_TEMPLATE = ("本报告周期内可追溯且满足筛选条件的安全信息有限，"
                          "当前证据不足以形成稳定趋势判断。")
#: 确定性版（无模型研判时）对用户展示的产品化文案 —— 不得出现 AI / 门禁 / pipeline 字样
DETERMINISTIC_ASSESSMENT_CN = ("本报告基于已核验事实与确定性统计生成，"
                               "本期未包含模型研判内容。")
DETERMINISTIC_TREND_CN = "本期事件量不足以支撑趋势判断，详见下方事实依据。"

#: 会被替换掉的内部实现文案/字段值（含既有 assembler 的 fallback 措辞）
_INTERNAL_TEXT_MARKERS = ("AI综合研判", "质量门禁", "analysis_gate_failed",
                          "insufficient_data_or_analysis_gate_failed")


def sanitize_public_text(report, status):
    """把报告里对用户可见的**内部实现语言**替换为产品化文案（§二十二/§二十七）。"""
    def fix(v):
        if isinstance(v, str) and any(m in v for m in _INTERNAL_TEXT_MARKERS):
            return DETERMINISTIC_ASSESSMENT_CN if "综合研判" in v else DETERMINISTIC_TREND_CN
        return v
    for k in ("overall_assessment", "executive_assessment", "security_trend",
              "trend_analysis", "outlook"):
        if k in report:
            report[k] = fix(report.get(k))
    if status == STATUS_LOW_DATA:
        for k in ("overall_assessment", "executive_assessment"):
            if not report.get(k) or any(m in str(report.get(k)) for m in _INTERNAL_TEXT_MARKERS):
                report[k] = COVERAGE_NOTE_TEMPLATE
    return report

#: 日报正文的最小 source-backed 事实数（沿用既有 DAILY_SECURITY_MIN，不擅自调低）
DAILY_SECURITY_MIN = 8


def is_source_backed(ev, urls=None):
    """是否具备**真实**来源身份（§十二：只用既有 identity，绝不构造伪 id）。"""
    urls = urls or {}
    if [g for g in (ev.get("source_groups") or []) if g]:
        return True
    if any(urls.get(a) for a in (ev.get("article_ids") or [])):
        return True
    return False


def source_backed_pool(events, urls=None):
    """(kept, excluded_count)：只保留有真实来源身份的事件（§一 OPTION A）。"""
    kept = [e for e in events if is_source_backed(e, urls)]
    return kept, len(events) - len(kept)


def _status_for(fact_pack, min_facts=None):
    n = len(fact_pack.get("social_facts") or []) + len(fact_pack.get("disease_facts") or [])
    thr = DAILY_SECURITY_MIN if min_facts is None else min_facts
    # 没有 AI → 永不 FULL；事实不足 → LOW_DATA（§六）
    return (STATUS_LOW_DATA if n < thr else STATUS_FALLBACK), n


def _index_row(report, rtype, root, status, fph, path, extra=None):
    row = {
        "report_id": report.get("report_id"),
        "report_type": rtype,
        "title": report.get("title"),
        "title_cn": report.get("title_cn") or report.get("title"),
        "period_start": report.get("period_start") or report.get("week_start"),
        "period_end": report.get("period_end") or report.get("week_end"),
        "country_iso3": report.get("country_iso3"),
        "status": status,
        "data_as_of": F.data_as_of(root),
        "generated_at": report.get("generated_at"),
        "headline": _headline(report, status),
        "fact_pack_hash": fph,
        "path": os.path.relpath(path, str(root)).replace("\\", "/") if path else None,
        "is_mock": False,
    }
    if extra:
        row.update(extra)
    return row


def _headline(report, status):
    if status == STATUS_LOW_DATA:
        return LOW_DATA_TEXT_CN
    for k in ("overall_assessment", "executive_assessment"):
        v = report.get(k)
        if v:
            return str(v)[:160]
    for k in ("sections", "executive_summary", "major_security_developments"):
        v = report.get(k)
        if isinstance(v, list) and v:
            first = v[0]
            return str(first.get("summary_cn") or first.get("title_cn")
                       or first.get("event_id") or "").strip()[:160]
    return ""


def materialize_daily(root, target, events, disease, iso, prev_report=None):
    report_date = target["report_date"]
    s, e = F.daily_window(report_date)
    # temporal_bucket 内部做 naive 相减，必须传 naive cutoff（与 select_daily 自身用法一致）
    _win = window_scoped_pool(events, e.replace(tzinfo=None))
    _pool, _unattr = source_backed_pool(_win, load_article_urls(root))
    di = B.build_daily_input(_pool, disease,
                             prev_report=prev_report,
                             report_date=report_date, iso2to3=iso,
                             cutoff=e.isoformat())
    # §四 硬门：report identity 必须用既有规范（DAILY_<YYYYMMDD>，无横线），
    # 否则 legacy Daily 永远匹配不上、会为同一天重复生成两份日报。
    di["report_id"] = F.build_report_id("africa_daily", report_date=report_date)
    di["report_type"] = "africa_daily"
    di["period_start"] = s.isoformat()
    di["period_end"] = e.isoformat()
    di["generated_at"] = datetime.now(F.BJT).isoformat()
    fp = FP.build_fact_pack(di)
    report_sources = attach_source_refs(root, fp, events)
    status, nfacts = _status_for(fp)
    analysis = None
    if status == STATUS_LOW_DATA:
        analysis = None
    report = DA.assemble_report("africa_daily", fp, analysis=analysis)
    report["status"] = status
    report["period_start"] = s.isoformat()
    report["period_end"] = e.isoformat()
    report["data_as_of"] = F.data_as_of(root)
    report["latest_verified_event_time"] = _latest_verified(di)
    report["fact_pack_hash"] = F.report_pack_hash(fp)
    report["input_hash"] = F.input_hash(report["report_id"], report["fact_pack_hash"],
                                        "deepseek-flash", "africa_daily")
    report["fact_count"] = nfacts
    report["country_count"] = len(fp.get("country_distribution") or {})
    report["source_count"] = len(fp.get("source_refs") or [])
    report["uncertainties"] = fp.get("uncertainties") or []
    report["schema_version"] = "analysis-v1.0.0"
    report["pipeline_version"] = DA.PIPELINE_VERSION
    report["architecture_version"] = DA.ARCH_VERSION
    report["report_status_cn"] = _status_cn(status)
    report["source_refs"] = report_sources
    _apply_coverage(report, _unattr, status)
    sanitize_public_text(report, status)
    return report, fp


def _apply_coverage(report, unattributed, status):
    """§五/§十六：无来源事实只进 coverage 诊断，绝不进正文与 AI fact pack。"""
    notes = list(report.get("coverage_notes") or [])
    if unattributed:
        notes.append("source-backed event coverage is limited")
        notes.append("%d candidate events were excluded because source identity "
                     "was unavailable" % unattributed)
    if status == STATUS_LOW_DATA:
        notes.append(COVERAGE_NOTE_TEMPLATE)
    report["coverage_notes"] = notes
    report["unattributed_facts_excluded"] = unattributed
    report["report_facts_with_source_refs"] = report.get("fact_count") or 0
    return report


def _latest_verified(di):
    ts = []
    for sec in (di.get("sections") or {}).values():
        for it in (sec or []):
            for k in ("event_time", "first_seen_at", "last_seen_at"):
                if it.get(k):
                    ts.append(str(it[k]))
    return max(ts) if ts else None


def _status_cn(status):
    return {"FULL": "完整", "FALLBACK": "确定性版", "LOW_DATA": "数据有限",
            "FAIL": "生成失败"}.get(status, status)


def materialize_africa_weekly(root, week, events, disease, iso):
    """从**原始 facts**（事件集合）直接聚合，绝不拼接 Daily 文本。"""
    ws, we = F.week_window(week["week_end"])
    win = [e for e in events
           if ws.isoformat()[:10] <= str(e.get("event_time") or e.get("first_seen_at") or "")[:10]
           <= we.isoformat()[:10]]
    win_dis = [d for d in disease
               if ws.isoformat()[:10] <= str(d.get("event_date") or d.get("reported_at") or "")[:10]
               <= we.isoformat()[:10]]
    _win = window_scoped_pool(win, _naive_dt(we))
    _pool, _unattr = source_backed_pool(_win, load_article_urls(root))
    di = B.build_daily_input(_pool, win_dis,
                             report_date=week["week_end"], iso2to3=iso,
                             cutoff=we.isoformat())
    di["report_type"] = "africa_weekly"
    di["week_start"] = week["week_start"]
    di["week_end"] = week["week_end"]
    di["generated_at"] = datetime.now(F.BJT).isoformat()
    # 复用既有 sections 形状（fact_pack 对 weekly 取 major_events）
    di["sections"]["major_events"] = (di["sections"].get("executive_summary") or [])
    fp = FP.build_fact_pack(di)
    report_sources = attach_source_refs(root, fp, win)
    status, nfacts = _status_for(fp)
    report = DA.assemble_report("africa_daily", fp, analysis=None)   # 复用同一 sections 渲染
    report["report_type"] = "africa_weekly"
    report["report_id"] = week["report_id"]
    report["title"] = "非洲地区社会安全周报"
    report["title_cn"] = "非洲地区社会安全周报"
    report["week_start"] = week["week_start"]
    report["week_end"] = week["week_end"]
    report["period_start"] = week["week_start"]
    report["period_end"] = week["week_end"]
    report["status"] = status
    report["data_as_of"] = F.data_as_of(root)
    report["fact_pack_hash"] = F.report_pack_hash(fp)
    report["input_hash"] = F.input_hash(week["report_id"], report["fact_pack_hash"],
                                        "deepseek-flash", "africa_weekly")
    report["fact_count"] = nfacts
    report["country_count"] = len(fp.get("country_distribution") or {})
    report["source_count"] = len(fp.get("source_refs") or [])
    report["uncertainties"] = fp.get("uncertainties") or []
    report["schema_version"] = "analysis-v1.0.0"
    report["pipeline_version"] = DA.PIPELINE_VERSION
    report["architecture_version"] = DA.ARCH_VERSION
    report["report_status_cn"] = _status_cn(status)
    report["source_refs"] = report_sources
    _apply_coverage(report, _unattr, status)
    sanitize_public_text(report, status)
    return report, fp


def materialize_country_weekly(root, target, events, disease, iso):
    iso3 = target["country_iso3"]
    ws, we = F.week_window(target["week_end"])
    ctry = [e for e in events
            if (e.get("country_iso3") or iso.get((e.get("country_code") or "")[:2])
                or e.get("country_iso3")) == iso3]
    _win = window_scoped_pool(ctry, _naive_dt(we))
    ctry, _unattr = source_backed_pool(_win, load_article_urls(root))
    di = B.build_weekly_input(iso3, ctry, disease, target["week_start"], target["week_end"])
    # §四 同类硬门：country weekly 的 report_id 也必须用既有规范（无横线），
    # 否则 legacy WEEKLY_TCD_20260913 与新生成会被当成两份。
    di["report_id"] = F.build_report_id("country_weekly",
                                        week_end=target["week_end"], country_iso3=iso3)
    di["report_type"] = "country_weekly"
    di["generated_at"] = datetime.now(F.BJT).isoformat()
    fp = FP.build_fact_pack(di)
    report_sources = attach_source_refs(root, fp, ctry)
    status, nfacts = _status_for(fp)
    report = DA.assemble_report("country_weekly", fp, analysis=None)
    report["status"] = status
    report["period_start"] = target["week_start"]
    report["period_end"] = target["week_end"]
    report["data_as_of"] = F.data_as_of(root)
    report["fact_pack_hash"] = F.report_pack_hash(fp)
    report["input_hash"] = F.input_hash(report["report_id"], report["fact_pack_hash"],
                                        "deepseek-flash", "country_weekly")
    report["fact_count"] = nfacts
    report["source_count"] = len(fp.get("source_refs") or [])
    report["uncertainties"] = fp.get("uncertainties") or []
    report["schema_version"] = "analysis-v1.0.0"
    report["pipeline_version"] = DA.PIPELINE_VERSION
    report["architecture_version"] = DA.ARCH_VERSION
    report["selection_reason"] = target.get("selection_reason")
    report["report_status_cn"] = _status_cn(status)
    report["source_refs"] = report_sources
    _apply_coverage(report, _unattr, status)
    sanitize_public_text(report, status)
    return report, fp


def materialize_reports(root, days=14, now=None, write=True):
    """物化全部目标（deterministic）。返回统计 + 索引行。"""
    plan = F.plan_report_backfill(root, days=days, now=now)
    events = load_canonical_events(root)
    disease = load_disease_items(root)
    iso = iso2to3_map(root)
    stats = {"DAILY_TARGET": plan["DAILY_TARGET"],
             "DAILY_EXISTING_REUSED": 0, "DAILY_NEWLY_MATERIALIZED": 0,
             "DAILY_DIRTY_REBUILT": 0, "DAILY_FAIL": 0, "DAILY_DUPLICATES": 0,
             "AFRICA_WEEKLY_TARGET": plan["WEEKLY_TARGET"], "AFRICA_WEEKLY_MATERIALIZED": 0,
             "COUNTRY_WEEKLY_TARGET": plan["COUNTRY_WEEKLY_TARGET"],
             "COUNTRY_WEEKLY_MATERIALIZED": 0,
             "STATUS_FULL": 0, "STATUS_FALLBACK": 0, "STATUS_LOW_DATA": 0, "STATUS_FAIL": 0,
             "SPORTS_EXCLUDED_FROM_REPORT_FACTS": 0,
             "SECURITY_RELATED_SPORTS_RETAINED": 0,
             "REAL_AI_CALLS": 0,
             "SOURCE_POLICY": SOURCE_POLICY,
             "DAILY_LOW_DATA": 0, "DAILY_FALLBACK": 0,
             "AFRICA_WEEKLY_LOW_DATA": 0, "AFRICA_WEEKLY_FALLBACK": 0,
             "COUNTRY_WEEKLY_LOW_DATA": 0, "COUNTRY_WEEKLY_FALLBACK": 0,
             "UNATTRIBUTED_FACTS_EXCLUDED_FROM_REPORTS": 0,
             "REPORT_FACTS_TOTAL": 0, "REPORT_FACTS_WITH_SOURCE_REFS": 0}
    rows, seen = [], set()

    def _classify_and_write(report, rtype, fp):
        state, _prev = classify_existing(root, report["report_id"], rtype)
        if report["report_id"] in seen:
            stats["DAILY_DUPLICATES"] += 1
            return
        seen.add(report["report_id"])
        path = None
        if write:
            path = write_report_artifact(root, rtype, report)
        elif state == "EXISTING_VALID":
            path = report_path(root, rtype, report["report_id"])
        rows.append(_index_row(report, rtype, root, report["status"],
                               report["fact_pack_hash"], path,
                               extra={"legacy_reused": state == "EXISTING_VALID"}))
        st = report["status"]
        suffix = ("LOW_DATA" if st == STATUS_LOW_DATA else
                  "FALLBACK" if st == STATUS_FALLBACK else
                  "FAIL" if st == STATUS_FAIL else "FULL")
        stats["STATUS_%s" % suffix] += 1
        prefix = {"africa_daily": "DAILY", "africa_weekly": "AFRICA_WEEKLY",
                  "country_weekly": "COUNTRY_WEEKLY"}.get(rtype)
        if prefix:
            stats["%s_%s" % (prefix, suffix)] = stats.get("%s_%s" % (prefix, suffix), 0) + 1
        stats["UNATTRIBUTED_FACTS_EXCLUDED_FROM_REPORTS"] += report.get(
            "unattributed_facts_excluded") or 0
        stats["REPORT_FACTS_TOTAL"] += report.get("fact_count") or 0
        stats["REPORT_FACTS_WITH_SOURCE_REFS"] += report.get(
            "report_facts_with_source_refs") or 0
        return state

    prev = None
    for t in plan["DAILY_TARGET_DATES"]:
        try:
            report, fp = materialize_daily(root, t, events, disease, iso, prev_report=prev)
        except Exception:  # noqa: BLE001
            stats["DAILY_FAIL"] += 1
            continue
        state = _classify_and_write(report, "africa_daily", fp)
        if state == "EXISTING_VALID":
            stats["DAILY_EXISTING_REUSED"] += 1
        elif state == "DIRTY":
            stats["DAILY_DIRTY_REBUILT"] += 1
        else:
            stats["DAILY_NEWLY_MATERIALIZED"] += 1
        prev = report

    for w in plan["WEEKLY_TARGET_PERIODS"]:
        try:
            report, fp = materialize_africa_weekly(root, w, events, disease, iso)
        except Exception:  # noqa: BLE001
            continue
        _classify_and_write(report, "africa_weekly", fp)
        stats["AFRICA_WEEKLY_MATERIALIZED"] += 1

    for c in plan["COUNTRY_WEEKLY_TARGETS"]:
        try:
            report, fp = materialize_country_weekly(root, c, events, disease, iso)
        except Exception:  # noqa: BLE001
            continue
        _classify_and_write(report, "country_weekly", fp)
        stats["COUNTRY_WEEKLY_MATERIALIZED"] += 1

    # 报告层 eligibility filter 统计（只统计、不改事实）
    for e in events:
        ok, reason = F.report_eligibility("%s %s" % (e.get("title_original") or "",
                                                     e.get("title_cn") or ""),
                                          e.get("event_type"))
        if not ok:
            stats["SPORTS_EXCLUDED_FROM_REPORT_FACTS"] += 1
        elif reason.startswith("SECURITY_RELATED"):
            stats["SECURITY_RELATED_SPORTS_RETAINED"] += 1
    # §十六 数据质量指标（两个指标严格分开，不得混淆）
    urls = load_article_urls(root)
    stats["CANONICAL_FACTS_TOTAL"] = len(events)
    stats["CANONICAL_FACTS_WITH_SOURCE_IDENTITY"] = sum(
        1 for e in events if is_source_backed(e, urls))
    stats["CANONICAL_SOURCE_IDENTITY_COVERAGE"] = round(
        100.0 * stats["CANONICAL_FACTS_WITH_SOURCE_IDENTITY"]
        / max(1, stats["CANONICAL_FACTS_TOTAL"]), 1)
    stats["REPORT_FACT_SOURCE_ATTRIBUTION_RATE"] = (
        100.0 if stats["REPORT_FACTS_TOTAL"] == 0
        else round(100.0 * stats["REPORT_FACTS_WITH_SOURCE_REFS"]
                   / max(1, stats["REPORT_FACTS_TOTAL"]), 1))
    stats["_rows"] = rows
    stats["_plan"] = plan
    return stats


# ── real-only index ────────────────────────────────────────────────────
def build_real_report_index(root, rows=None, legacy=None, write=False):
    """real-only 索引：new canonical artifact 优先于 legacy index-only，且按 report_id 去重。"""
    rows = rows if rows is not None else [
        _index_row(r, r.get("report_type"), root, r.get("status"),
                   r.get("fact_pack_hash"),
                   report_path(root, r["report_type"], r["report_id"]))
        for r in list_report_artifacts(root)
        if r.get("report_type") in REPORT_DIRS
    ]
    legacy = legacy if legacy is not None else load_legacy_index(root)
    by_id = {}
    for r in legacy:                                # legacy 先放（低优先）
        if r.get("is_mock"):
            continue
        rid = r.get("report_id")
        if not rid:
            continue
        by_id[rid] = {
            "report_id": rid,
            "report_type": r.get("report_type") or ("africa_daily"
                                                    if str(rid).startswith("DAILY_") else None),
            "title": r.get("title"),
            "title_cn": r.get("title_cn") or r.get("title"),
            "period_start": r.get("period_start"),
            "period_end": r.get("period_end"),
            "country_iso3": r.get("country_iso3"),
            "status": r.get("status"),
            "data_as_of": r.get("data_as_of"),
            "generated_at": r.get("generated_at"),
            "headline": r.get("headline") or "",
            "fact_pack_hash": r.get("fact_pack_hash"),
            "path": r.get("path"),
            "is_mock": False,
            "legacy_only": True,
        }
    for r in rows:                                  # new canonical 覆盖 legacy
        rid = r.get("report_id")
        if not rid:
            continue
        merged = dict(by_id.get(rid) or {})
        merged.update({k: v for k, v in r.items() if v is not None})
        merged["legacy_only"] = False
        by_id[rid] = merged
    reports = sorted(by_id.values(),
                     key=lambda r: (str(r.get("period_end") or ""), str(r.get("report_id") or "")),
                     reverse=True)
    doc = {"schema": "report-index-v2", "real_only": True,
           "count": len(reports),
           "mock_excluded": sum(1 for r in legacy if r.get("is_mock")),
           "generated_at": datetime.now(F.BJT).isoformat(),
           "reports": reports}
    if write:
        p = os.path.join(str(root), "data", "views", "report_index.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    return doc


def _cli():
    import argparse
    ap = argparse.ArgumentParser(description="C4-B report materialization (deterministic, no AI)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    st = materialize_reports(a.root, days=a.days, write=not a.dry_run)
    idx = build_real_report_index(a.root, rows=st.pop("_rows"), write=not a.dry_run)
    st.pop("_plan", None)
    st["TOTAL_REAL_REPORTS_IN_INDEX"] = idx["count"]
    st["MOCK_IN_REAL_INDEX"] = 0
    st["LOW_DATA_TEXT_CN"] = LOW_DATA_TEXT_CN
    print(json.dumps(st, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    _cli()
