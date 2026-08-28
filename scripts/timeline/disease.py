#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6B §十四-§二十 — Disease Outbreak Timeline 引擎。

- 数字 Observation（§十六）：每个报告是一个 observation（as_of_date=report_date），
  不得覆盖；latest_counts 是派生结果。
- temporal update ≠ conflict（§十七）：report_date/case_period_end 不同 → case_update；
  相同/高度重叠统计期 + 核心数字明显不一致 → numeric_conflict。
- 病例类别分离（§十八）：confirmed/probable/suspected/total_cases 分别保存，
  不得擅自合计。
- 地理扩散（§十九）：affected_admin1 历史值保留；cross_border/affected_countries。
- Outbreak Identity（§二十）：disease_id + country + time continuity + geographic
  overlap + official reference；同疾病不同时间（2024 vs 2026）可不同 outbreak。

不用 AI。纯确定性。基于现有 Disease Canonical 字段
（previous_event_id / supersedes_event_id / report_date / case_period_*）。
"""

import hashlib
import time

# Disease update 类型（§十五，复用 Disease 语义，非 Social enum）
DISEASE_UPDATE_TYPES = (
    "new_outbreak", "case_update", "mortality_update", "geographic_spread",
    "response_update", "status_change", "final_update",
)

# 核心数字字段（§十八 分别保存）
NUMERIC_FIELDS = ("confirmed_cases", "probable_cases", "suspected_cases",
                  "total_cases", "deaths", "recoveries")

# numeric_conflict 判定（§十七）：report_date 相同或 case_period_end 相同（重叠统计期）
CONFLICT_TOLERANCE_RATIO = 0.1   # 数字相对差 >10% 视为"明显不一致"


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _num(v):
    if v is None or v == "":
        return None
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _admin1_list(v):
    """admin1 规范化：canonical 可能为 str 或 list 或 None → list[str]。"""
    if v is None or v == "":
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [x for x in v if x]
    return [str(v)]


def _same_period(a, b):
    """§十七 相同/高度重叠统计期：report_date 相同或 case_period_end 相同。"""
    ra, rb = a.get("report_date"), b.get("report_date")
    if ra and rb and ra == rb:
        return True
    ea, eb = a.get("case_period_end"), b.get("case_period_end")
    if ea and eb and ea == eb:
        return True
    sa, sb = a.get("case_period_start"), b.get("case_period_start")
    if sa and sb and sa == sb and (ra and rb):
        return True
    return False


def _clearly_different(va, vb):
    """核心数字明显不一致（§十七）：两边都有值且相对差 > 容差。"""
    if va is None or vb is None:
        return False
    if va == 0 and vb == 0:
        return False
    if va == 0 or vb == 0:
        return True
    return abs(va - vb) / max(va, vb) > CONFLICT_TOLERANCE_RATIO


def classify_disease_update(prev_event, event):
    """判定 disease event 相对上一 observation 的 update_type（§十五）。

    优先继承 canonical 的 update_type（若为 new_outbreak/final_update 等强语义）；
    否则按字段变化推断。
    """
    ut = event.get("update_type")
    if ut in DISEASE_UPDATE_TYPES and prev_event is None:
        return "new_outbreak"
    if prev_event is None:
        return "new_outbreak"
    if ut == "final_update" or event.get("outbreak_status") == "ended":
        return "final_update"
    if ut in DISEASE_UPDATE_TYPES and ut not in ("new_outbreak",):
        return ut
    # 推断
    new_admin1 = set(_admin1_list(event.get("admin1"))) - set(_admin1_list(prev_event.get("admin1")))
    if new_admin1 or (event.get("affected_countries") and
                      event.get("affected_countries") != prev_event.get("affected_countries")):
        return "geographic_spread"
    if event.get("outbreak_status") and event.get("outbreak_status") != prev_event.get("outbreak_status"):
        return "status_change"
    nd = _num(event.get("deaths"))
    pd = _num(prev_event.get("deaths"))
    if nd is not None and pd is not None and nd != pd:
        return "mortality_update"
    for f in ("confirmed_cases", "total_cases", "probable_cases", "suspected_cases"):
        nv = _num(event.get(f))
        pv = _num(prev_event.get(f))
        if nv is not None and pv is not None and nv != pv:
            return "case_update"
    return "response_update" if ut == "response_update" else "case_update"


def _same_outbreak(a, b):
    """§二十 Outbreak Identity：disease_id + country + 时间连续性 + 地理重叠 + 官方引用。"""
    if a.get("disease_id") != b.get("disease_id"):
        return False
    ca, cb = a.get("country_iso3"), b.get("country_iso3")
    if ca and cb and ca != cb:
        ac = set(a.get("affected_countries") or [])
        bc = set(b.get("affected_countries") or [])
        if not (ac & bc) and not (a.get("cross_border") or b.get("cross_border")):
            return False
    # 时间连续性：两事件报告日期跨度超过 180 天 → 视为可能不同 outbreak（保守）
    # （同疾病不同年份如 2024 vs 2026 不得归并；同一年代较长暴发仍可连续）
    from datetime import datetime
    ra, rb = a.get("report_date") or a.get("event_start_date"), \
             b.get("report_date") or b.get("event_start_date")
    if ra and rb:
        try:
            da = datetime.strptime(str(ra)[:10], "%Y-%m-%d")
            db = datetime.strptime(str(rb)[:10], "%Y-%m-%d")
            if abs((db - da).days) > 180:
                return False
        except ValueError:
            pass
    # 地理重叠（§二十）
    aa = set(_admin1_list(a.get("admin1")))
    ba = set(_admin1_list(b.get("admin1")))
    if aa and ba and not (aa & ba):
        # 无 admin1 重叠但可能只是粒度不同：不强制分开（保守合并由 canonical 链决定）
        pass
    # 官方引用链（§二十）：显式 previous/supersedes 关系视为同一 outbreak
    if b.get("supersedes_event_id") == a.get("disease_event_id") or \
            b.get("previous_event_id") == a.get("disease_event_id"):
        return True
    if b.get("supersedes_event_id") or b.get("previous_event_id"):
        # 显式链到别的事件 → 尊重 canonical 决策
        return False
    return True


def new_outbreak_timeline(event):
    """从第一条 disease event 创建 outbreak timeline。"""
    obs = _mk_observation(event, "new_outbreak", None)
    timeline = {
        "outbreak_id": "OB_%s" % hashlib.sha1(
            ("%s|%s" % (event.get("disease_id"), event.get("country_iso3") or "region")).encode(
                "utf-8")).hexdigest()[:12],
        "disease_id": event.get("disease_id"),
        "country_iso3": event.get("country_iso3"),
        "affected_countries": event.get("affected_countries") or [],
        "first_reported_at": event.get("report_date"),
        "latest_report_at": event.get("report_date"),
        "outbreak_status": event.get("outbreak_status") or "unknown",
        "latest_counts": {
            "confirmed_cases": _num(event.get("confirmed_cases")),
            "probable_cases": _num(event.get("probable_cases")),
            "suspected_cases": _num(event.get("suspected_cases")),
            "total_cases": _num(event.get("total_cases")),
            "deaths": _num(event.get("deaths")),
            "as_of_date": event.get("report_date"),
        },
        "affected_admin1": _admin1_list(event.get("admin1")),
        "updates": [obs],
        "source_count": 1,
        "independent_source_count": 1,
        "verification_status": event.get("verification_status"),
        "numeric_conflicts": [],
        "uncertainties": event.get("uncertainties") or [],
        "created_at": _now(),
        "updated_at": None,
    }
    return timeline


def _mk_observation(event, utype, prev_obs):
    return {
        "update_id": "DU_%s" % hashlib.sha1(
            ("%s|%s|%s" % (event.get("disease_event_id") or "",
                           event.get("report_date") or "", utype)).encode(
                "utf-8")).hexdigest()[:14],
        "disease_event_id": event.get("disease_event_id"),
        "update_type": utype,
        "report_date": event.get("report_date"),
        "case_period_start": event.get("case_period_start"),
        "case_period_end": event.get("case_period_end"),
        "as_of_date": event.get("report_date"),
        "confirmed_cases": _num(event.get("confirmed_cases")),
        "probable_cases": _num(event.get("probable_cases")),
        "suspected_cases": _num(event.get("suspected_cases")),
        "total_cases": _num(event.get("total_cases")),
        "deaths": _num(event.get("deaths")),
        "recoveries": _num(event.get("recoveries")),
        "affected_admin1": _admin1_list(event.get("admin1")),
        "affected_countries": event.get("affected_countries") or [],
        "outbreak_status": event.get("outbreak_status"),
        "evidence": {
            "primary_source": event.get("primary_source"),
            "source_links": event.get("source_links") or [],
            "source_tier": event.get("source_tier"),
        },
        "uncertainties": event.get("uncertainties") or [],
        "created_at": _now(),
    }


def apply_disease_event(timeline, event):
    """向 outbreak timeline 追加一条 observation（§十六 不覆盖）。

    返回 (timeline, obs, numeric_conflicts)。
    """
    prev_obs = timeline["updates"][-1]
    utype = classify_disease_update(prev_obs, event)
    obs = _mk_observation(event, utype, prev_obs)
    conflicts = []

    # §十七 numeric_conflict：同统计期 + 核心数字明显不一致
    if _same_period(prev_obs, event):
        for f in ("confirmed_cases", "total_cases", "deaths"):
            nv = _num(event.get(f))
            pv = _num(prev_obs.get(f))
            if _clearly_different(nv, pv):
                msg = ("numeric_conflict:%s:%s:%s" % (
                    f, prev_obs.get("report_date"), event.get("report_date")))
                if msg not in timeline["numeric_conflicts"]:
                    timeline["numeric_conflicts"].append(msg)
                    conflicts.append(msg)

    # latest_counts 派生（§十六）：仅取最新 observation 的值（各字段独立）
    lc = timeline["latest_counts"]
    for f in NUMERIC_FIELDS:
        nv = _num(event.get(f))
        if nv is not None:
            lc[f] = nv
    if event.get("report_date"):
        lc["as_of_date"] = event.get("report_date")

    # §十九 geographic spread：admin1 历史值保留（并集），cross_border 扩展 affected
    new_admin1 = set(_admin1_list(event.get("admin1"))) - set(timeline["affected_admin1"])
    if new_admin1:
        timeline["affected_admin1"] = sorted(
            set(timeline["affected_admin1"]) | new_admin1)
        utype = "geographic_spread"
        obs["update_type"] = utype
    if event.get("affected_countries"):
        timeline["affected_countries"] = sorted(
            set(timeline["affected_countries"]) | set(event["affected_countries"]))

    # status（§十五/§十八）
    if event.get("outbreak_status"):
        timeline["outbreak_status"] = event["outbreak_status"]

    timeline["updates"].append(obs)
    timeline["latest_report_at"] = event.get("report_date") or timeline["latest_report_at"]
    timeline["source_count"] = len({u.get("disease_event_id") for u in timeline["updates"]})
    timeline["independent_source_count"] = len(
        {u.get("evidence", {}).get("primary_source") or "?" for u in timeline["updates"]})
    timeline["verification_status"] = event.get("verification_status") or timeline.get("verification_status")
    timeline["updated_at"] = _now()
    return timeline, obs, conflicts


def build_outbreak_timelines(events):
    """从 Disease Canonical 事件列表构造 outbreak timelines。

    events: list of disease canonical dict（含 disease_event_id/disease_id/
    country_iso3/report_date/previous_event_id/supersedes_event_id 等）。

    关联策略（§十三/§二十）：
    - 显式 supersedes/previous 链 → 同一 timeline；
    - 否则按 _same_outbreak（identity + 时间连续性 + 地理重叠）判断。

    返回 (timelines, stats, orphans)。
    """
    events = sorted(events, key=lambda e: str(e.get("report_date") or ""))
    stats = {"disease_events_processed": 0, "outbreaks_created": 0,
             "updates_created": 0, "case_updates": 0, "mortality_updates": 0,
             "geographic_spread": 0, "status_changes": 0, "numeric_conflicts": 0,
             "final_updates": 0}
    timelines = []
    by_id = {e.get("disease_event_id"): e for e in events}
    used = set()

    # 1. 显式链优先：找到每个链的根（supersedes 指向谁）
    def root_of(e):
        seen = set()
        cur = e
        while cur and cur.get("supersedes_event_id") in by_id and \
                cur.get("supersedes_event_id") not in seen:
            seen.add(cur.get("supersedes_event_id"))
            cur = by_id[cur["supersedes_event_id"]]
        return cur

    chains = {}
    for e in events:
        r = root_of(e)
        chains.setdefault(r.get("disease_event_id"), []).append(e)

    for root_id, members in chains.items():
        members = sorted(members, key=lambda m: str(m.get("report_date") or ""))
        tl = new_outbreak_timeline(members[0])
        stats["disease_events_processed"] += 1
        stats["outbreaks_created"] += 1
        stats["updates_created"] += 1
        used.add(members[0].get("disease_event_id"))
        for ev in members[1:]:
            tl, obs, conflicts = apply_disease_event(tl, ev)
            stats["disease_events_processed"] += 1
            stats["updates_created"] += 1
            stats["numeric_conflicts"] += len(conflicts)
            stats["case_updates"] += obs["update_type"] == "case_update"
            stats["mortality_updates"] += obs["update_type"] == "mortality_update"
            stats["geographic_spread"] += obs["update_type"] == "geographic_spread"
            stats["status_changes"] += obs["update_type"] == "status_change"
            stats["final_updates"] += obs["update_type"] == "final_update"
            used.add(ev.get("disease_event_id"))
        timelines.append(tl)

    # 2. 未入链事件：按 identity 归并（§二十）
    remaining = [e for e in events if e.get("disease_event_id") not in used]
    for e in remaining:
        placed = False
        for tl in timelines:
            if tl["disease_id"] == e.get("disease_id"):
                anchor = tl["updates"][0]
                if _same_outbreak(anchor, e):
                    tl, obs, conflicts = apply_disease_event(tl, e)
                    stats["disease_events_processed"] += 1
                    stats["updates_created"] += 1
                    stats["numeric_conflicts"] += len(conflicts)
                    stats["case_updates"] += obs["update_type"] == "case_update"
                    stats["mortality_updates"] += obs["update_type"] == "mortality_update"
                    stats["geographic_spread"] += obs["update_type"] == "geographic_spread"
                    stats["status_changes"] += obs["update_type"] == "status_change"
                    stats["final_updates"] += obs["update_type"] == "final_update"
                    used.add(e.get("disease_event_id"))
                    placed = True
                    break
        if not placed:
            tl = new_outbreak_timeline(e)
            timelines.append(tl)
            stats["disease_events_processed"] += 1
            stats["outbreaks_created"] += 1
            stats["updates_created"] += 1
            used.add(e.get("disease_event_id"))
    return timelines, stats, [e for e in events if e.get("disease_event_id") not in used]
