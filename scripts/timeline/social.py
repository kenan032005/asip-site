#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6B §三-§十三 — Social Event Timeline 引擎。

核心原则：
- 历史不可覆盖（§五）：8 → 11 → 12 全部保留在 updates[]，current_state 是派生层（§六）。
- 伤亡数字更新 vs conflict（§七）：后发（published_at 明显更晚）→ casualty_update；
  同时期且无法证明先后 → conflicting_values，不自动选大数。
- 时间语义（§八）：published_at / event_time / effective_at 分离；
  effective_at 缺省回退 published_at 并标注 time_basis=published_at_fallback。
- 责任方归因（§九）：actor_attribution_update + attribution_type
  （claimed/officially_attributed/reported/alleged/confirmed），官方指控不得自动转 confirmed。
- 官方确认（§十）：official_confirmation 不删首报。
- Correction（§十一）：保留被纠正历史，current_state 指向更正后值。
- 生命周期（§十二）：developing → ongoing → stable（阈值配置化）→ closed。
- Stage6A master_event 为父对象（§十三）：一篇新文章不创建新 timeline。

不用 AI。纯确定性。Stage5 verification 字段直接引用（§二十七）。
"""

import hashlib
import re
import time

# update_type 固定枚举（§四）
UPDATE_TYPES = (
    "initial_report", "casualty_update", "injury_update", "location_update",
    "actor_attribution_update", "official_confirmation", "status_update",
    "correction", "context_update", "closure_update",
)

# timeline_status（§十二）
TIMELINE_STATUSES = ("developing", "ongoing", "stable", "closed", "unknown")

# attribution_type（§九）
ATTRIBUTION_TYPES = ("claimed", "officially_attributed", "reported", "alleged", "confirmed")

# 配置化（§十二）：无重大更新超过该秒数 → stable（第一版保守：72h）
STABLE_AFTER_SECONDS = int(__import__("os").environ.get(
    "ASIP_TIMELINE_STABLE_AFTER_SECONDS", "259200"))  # 72h
# 同时期判定（§七）：发布时间差小于该秒数视为"基本相同"
SIMULTANEOUS_SECONDS = int(__import__("os").environ.get(
    "ASIP_TIMELINE_SIMULTANEOUS_SECONDS", "3600"))    # 1h

# 官方源特征：source_id 含官方标志 或 trust_tier=A 且 role=evidence 官方域
OFFICIAL_SOURCE_HINTS = ("gov", "presidence", "moh", "presidency", "op.gov")
# correction 信号词
CORRECTION_KW = ("correct", "corrig", "clarif", "retract", "previous figure was incorrect",
                 "更正", "修正", "澄清", "撤回")
# 归因信号词（§九）——只做关键词分类，不做事实裁决
ATTRIBUTION_KW = {
    "claimed": ("claim", "claims", "claimed", "声称", "宣称"),
    "officially_attributed": ("official", "government", "authorities", "官方", "政府", "当局"),
    "reported": ("report", "reports", "reported", "报道", "据报"),
    "alleged": ("allege", "alleged", "allegedly", "据称", "被指"),
    "confirmed": ("confirm", "confirmed", "证实", "确认"),
}
# 结束信号词（§十二 closure）
CLOSURE_KW = ("ended", "concluded", "over", "ceasefire reached", "agreement reached",
              "结束", "终止", "达成协议")


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _ts(dt):
    """ISO 时间串 → 可比较时间戳；解析失败返回 None。"""
    if not dt:
        return None
    s = str(dt).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
                "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            from datetime import datetime
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    try:
        from datetime import datetime
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _eff_time(article):
    """effective_at（§八）：event_time 优先；否则 published_at 回退并标注 basis。"""
    et = article.get("event_time") or article.get("event_time_candidate")
    if et:
        return et, "event_time"
    pt = article.get("published_at")
    if pt:
        return pt, "published_at_fallback"
    return None, "none"


def _attr_type(text):
    """关键词分类 attribution_type；无法判断 → None。"""
    t = (text or "").lower()
    for atype, kws in ATTRIBUTION_KW.items():
        if any(k in t for k in kws):
            return atype
    return None


def _is_correction(article):
    t = " ".join([str(article.get("title") or ""), str(article.get("body") or ""),
                  str(article.get("body_extracted") or "")]).lower()
    if any(k in t for k in ("更正", "修正", "澄清", "撤回")):
        return True
    return any(re.search(r"\b%s\b" % re.escape(k), t)
               for k in ("corrected", "corrige", "clarified", "retracted",
                         "previous figure was incorrect"))


def _is_closure(article):
    t = " ".join([str(article.get("title") or ""), str(article.get("body") or ""),
                  str(article.get("body_extracted") or "")]).lower()
    if any(k in t for k in ("结束", "终止", "达成协议")):
        return True
    return any(re.search(r"\b%s\b" % re.escape(k), t)
               for k in ("ended", "concluded", "over", "ceasefire reached",
                         "agreement reached"))


def _is_official(source, article):
    sid = (source or {}).get("source_id", "") or ""
    name = (source or {}).get("name", "") or ""
    t = " ".join([sid, name, str(article.get("title") or "")])
    if any(h in sid.lower() for h in OFFICIAL_SOURCE_HINTS):
        return True
    if re.search(r"\b(official|government|authorities|presidency|ministry)\b", t, re.I):
        return True
    return False


def _num(v):
    """宽容转数字；None/空/非数字 → None。"""
    if v is None or v == "":
        return None
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None


def classify_update_type(timeline, article, source=None):
    """判定 article 对 timeline 的 update_type（§四）。

    返回 (update_type, extra) —— extra 可含 attribution_type / official /
    correction / closure 等标记。
    """
    prev = timeline["current_state"]
    if not timeline["updates"]:
        return "initial_report", {}
    extra = {}

    # correction 优先（§十一）
    if _is_correction(article):
        return "correction", {}

    # closure（§十二）
    if _is_closure(article):
        return "closure_update", {}

    # actor attribution（§九）：responsible_party 变化、首次出现，
    # 或归因状态升级（alleged/claimed → confirmed）均计 actor_attribution_update
    new_party = article.get("responsible_party") or article.get("actor")
    old_party = prev.get("responsible_party")
    attr = _attr_type(" ".join([str(article.get("title") or ""),
                                str(article.get("body") or ""),
                                str(article.get("body_extracted") or "")]))
    prev_attr = (timeline["updates"][-1].get("attribution_type")
                 if timeline["updates"] else None)
    escalated = (attr in ("confirmed", "officially_attributed") and
                 prev_attr in ("claimed", "alleged"))
    if attr and (new_party != old_party or (new_party and not old_party) or escalated):
        extra["attribution_type"] = attr
        return "actor_attribution_update", extra

    # official confirmation（§十）：官方源/官方措辞且非首报
    if _is_official(source, article) and prev.get("official_confirmed") is not True:
        extra["official"] = True
        return "official_confirmation", extra

    # casualty / injury（§七）：数字出现或变化（首报无数字后报有数字也算）
    new_deaths = _num(article.get("deaths") or article.get("casualties"))
    old_deaths = prev.get("deaths")
    new_injured = _num(article.get("injured"))
    old_injured = prev.get("injured")
    if new_deaths is not None and new_deaths != old_deaths:
        return "casualty_update", {"field": "deaths"}
    if new_injured is not None and new_injured != old_injured:
        return "injury_update", {"field": "injured"}

    # location_update（§六/§十一 更精确地点）
    new_loc = article.get("location") or article.get("location_raw")
    old_loc = prev.get("location")
    if new_loc and old_loc and new_loc != old_loc:
        return "location_update", {}

    # status_update（§十二）
    new_status = article.get("event_status")
    old_status = prev.get("event_status")
    if new_status and old_status and new_status != old_status:
        return "status_update", {}

    # 其余补充背景
    return "context_update", {}


def _conflict_or_update(article, field, new_v, old_v, prev_update):
    """§七：后发 → update；同时期无法证明先后 → conflicting_values。"""
    pt = _ts(article.get("published_at"))
    if prev_update is None:
        return "update"
    prev_pt = _ts(prev_update.get("published_at"))
    if pt and prev_pt:
        diff = (pt - prev_pt).total_seconds()
        if diff >= SIMULTANEOUS_SECONDS:
            return "update"
        if diff < -SIMULTANEOUS_SECONDS:
            return "update"   # 更早报道也允许记录（时间线按 effective 排序）
    return "conflict"


def new_timeline(master_event_id, article, source=None, verification=None):
    """创建 timeline（首条 update = initial_report）。"""
    eff, basis = _eff_time(article)
    attr = _attr_type(" ".join([str(article.get("title") or ""),
                                str(article.get("body") or ""),
                                str(article.get("body_extracted") or "")]))
    first = {
        "update_id": "UP_%s" % hashlib.sha1(
            ("%s|%s|%s" % (master_event_id, article.get("article_id") or "",
                           article.get("published_at") or "")).encode("utf-8")).hexdigest()[:14],
        "master_event_id": master_event_id,
        "article_id": article.get("article_id") or article.get("candidate_id"),
        "source_id": (source or {}).get("source_id") or article.get("source_id"),
        "source_group": (source or {}).get("source_group") or article.get("source_group"),
        "published_at": article.get("published_at"),
        "event_time": article.get("event_time"),
        "effective_at": eff,
        "time_basis": basis,
        "update_type": "initial_report",
        "previous_update_id": None,
        "changed_fields": ["title", "country", "location", "event_type", "deaths", "injured"],
        "evidence": {"title": article.get("title"), "url": article.get("url")},
        "attribution_type": attr,
        "verification_status": (verification or {}).get("status"),
        "verification_confidence": (verification or {}).get("confidence"),
        "created_at": _now(),
    }
    timeline = {
        "timeline_id": "TL_%s" % hashlib.sha1(master_event_id.encode("utf-8")).hexdigest()[:12],
        "master_event_id": master_event_id,
        "timeline_status": "developing",
        "first_reported_at": article.get("published_at"),
        "latest_update_at": article.get("published_at"),
        "current_state": {
            "country": article.get("event_primary_country") or article.get("country_iso3"),
            "location": article.get("location") or article.get("location_raw"),
            "event_type": article.get("event_type"),
            "deaths": _num(article.get("deaths") or article.get("casualties")),
            "injured": _num(article.get("injured")),
            "responsible_party": article.get("responsible_party") or article.get("actor"),
            "event_status": article.get("event_status"),
            "official_confirmed": False,
            "last_updated": article.get("published_at"),
            "provenance": {
                "country": {"value": article.get("event_primary_country") or article.get("country_iso3"),
                            "source": article.get("source_id"), "update_id": first["update_id"],
                            "effective_at": eff},
                "location": {"value": article.get("location") or article.get("location_raw"),
                             "source": article.get("source_id"), "update_id": first["update_id"],
                             "effective_at": eff},
                "deaths": {"value": _num(article.get("deaths") or article.get("casualties")),
                           "source": article.get("source_id"), "update_id": first["update_id"],
                           "effective_at": eff},
                "injured": {"value": _num(article.get("injured")),
                            "source": article.get("source_id"), "update_id": first["update_id"],
                            "effective_at": eff},
                "responsible_party": {"value": article.get("responsible_party") or article.get("actor"),
                                      "source": article.get("source_id"),
                                      "update_id": first["update_id"], "effective_at": eff},
            },
        },
        "updates": [first],
        "source_count": 1,
        "independent_source_count": 1,
        "verification_status": (verification or {}).get("status"),
        "confidence": None,
        "conflict_flags": [],
        "uncertainties": article.get("uncertainties") or [],
        "created_at": _now(),
        "updated_at": None,
    }
    return timeline


def apply_update(timeline, article, source=None, verification=None):
    """向 timeline 追加一条 update（§五 历史不可覆盖；§六 current_state 派生）。

    返回 (timeline, update, conflict_flags)。
    """
    utype, extra = classify_update_type(timeline, article, source)
    eff, basis = _eff_time(article)
    prev_updates = timeline["updates"]
    prev_id = prev_updates[-1]["update_id"] if prev_updates else None

    upd = {
        "update_id": "UP_%s" % hashlib.sha1(
            ("%s|%s|%s" % (timeline["master_event_id"], article.get("article_id") or "",
                           article.get("published_at") or "")).encode("utf-8")).hexdigest()[:14],
        "master_event_id": timeline["master_event_id"],
        "article_id": article.get("article_id") or article.get("candidate_id"),
        "source_id": (source or {}).get("source_id") or article.get("source_id"),
        "source_group": (source or {}).get("source_group") or article.get("source_group"),
        "published_at": article.get("published_at"),
        "event_time": article.get("event_time"),
        "effective_at": eff,
        "time_basis": basis,
        "update_type": utype,
        "previous_update_id": prev_id,
        "changed_fields": [],
        "evidence": {"title": article.get("title"), "url": article.get("url")},
        "attribution_type": extra.get("attribution_type"),
        "verification_status": (verification or {}).get("status"),
        "verification_confidence": (verification or {}).get("confidence"),
        "created_at": _now(),
    }
    flags = []

    # ── current_state 派生（§六）：仅对核心字段更新 provenance ──
    st = timeline["current_state"]
    prov = st["provenance"]

    # deaths：update 或 conflict（§七）；correction（§十一）直接指向更正值
    new_deaths = _num(article.get("deaths") or article.get("casualties"))
    if new_deaths is not None and utype in ("casualty_update", "correction", "initial_report"):
        old = st.get("deaths")
        if old is not None and new_deaths != old:
            mode = ("update" if utype == "correction" else
                    _conflict_or_update(article, "deaths", new_deaths, old,
                                        prev_updates[-1] if prev_updates else None))
            if mode == "conflict":
                flags.append("casualty_difference")
                st.setdefault("conflicting_values", []).append(
                    {"value": new_deaths, "source": article.get("source_id"),
                     "published_at": article.get("published_at")})
            else:
                st["deaths"] = new_deaths
                prov["deaths"] = {"value": new_deaths, "source": article.get("source_id"),
                                  "update_id": upd["update_id"], "effective_at": eff}
                upd["changed_fields"].append("deaths")
        elif old is None:
            st["deaths"] = new_deaths
            prov["deaths"] = {"value": new_deaths, "source": article.get("source_id"),
                              "update_id": upd["update_id"], "effective_at": eff}
            upd["changed_fields"].append("deaths")

    # injured
    new_inj = _num(article.get("injured"))
    if new_inj is not None and utype in ("injury_update", "initial_report"):
        old = st.get("injured")
        if old is not None and new_inj != old:
            mode = _conflict_or_update(article, "injured", new_inj, old,
                                       prev_updates[-1] if prev_updates else None)
            if mode == "conflict":
                flags.append("injury_difference")
            else:
                st["injured"] = new_inj
                prov["injured"] = {"value": new_inj, "source": article.get("source_id"),
                                   "update_id": upd["update_id"], "effective_at": eff}
                upd["changed_fields"].append("injured")
        elif old is None:
            st["injured"] = new_inj
            prov["injured"] = {"value": new_inj, "source": article.get("source_id"),
                               "update_id": upd["update_id"], "effective_at": eff}
            upd["changed_fields"].append("injured")

    # location（§六）：更精确/变化 → location_update；alias 变化不强制 conflict
    new_loc = article.get("location") or article.get("location_raw")
    if new_loc and st.get("location") and new_loc != st.get("location"):
        st["location"] = new_loc
        prov["location"] = {"value": new_loc, "source": article.get("source_id"),
                            "update_id": upd["update_id"], "effective_at": eff}
        upd["changed_fields"].append("location")

    # responsible_party（§九）：unknown → 首次出现 actor 也更新
    new_party = article.get("responsible_party") or article.get("actor")
    if new_party and new_party != st.get("responsible_party"):
        st["responsible_party"] = new_party
        prov["responsible_party"] = {"value": new_party, "source": article.get("source_id"),
                                     "update_id": upd["update_id"], "effective_at": eff}
        upd["changed_fields"].append("responsible_party")
    # 归因升级 flag（§九）：alleged/claimed → confirmed/officially_attributed，
    # 与 party 是否变化无关（同 party 升级同样标记）
    if extra.get("attribution_type") in ("confirmed", "officially_attributed") and \
            prev_updates and prev_updates[-1].get("attribution_type") in ("claimed", "alleged"):
        flags.append("attribution_escalation")

    # official confirmation（§十）
    if extra.get("official"):
        st["official_confirmed"] = True
        upd["changed_fields"].append("official_confirmed")

    # event_status（§十二）
    new_status = article.get("event_status")
    if new_status and st.get("event_status") and new_status != st.get("event_status"):
        st["event_status"] = new_status
        prov["event_status"] = {"value": new_status, "source": article.get("source_id"),
                                "update_id": upd["update_id"], "effective_at": eff}
        upd["changed_fields"].append("event_status")

    # closure（§十二）
    if utype == "closure_update":
        st["event_status"] = "closed"
        prov["event_status"] = {"value": "closed", "source": article.get("source_id"),
                                "update_id": upd["update_id"], "effective_at": eff}
        upd["changed_fields"].append("event_status")

    # correction（§十一）：保留历史，current_state 已由上方正常更新指向新值
    if utype == "correction":
        upd["changed_fields"].append("correction_applied")
        flags.append("correction_applied")

    # ── timeline 状态推进（§十二）：closure → closed；长间隔 → stable；其余 ongoing ──
    st_ts = _ts(timeline["latest_update_at"])
    new_ts = _ts(article.get("published_at"))
    if utype == "closure_update":
        timeline["timeline_status"] = "closed"
    elif utype == "initial_report":
        timeline["timeline_status"] = "developing"
    else:
        if st_ts and new_ts and (new_ts - st_ts).total_seconds() > STABLE_AFTER_SECONDS:
            timeline["timeline_status"] = "stable"
        else:
            timeline["timeline_status"] = "ongoing"

    # ── timeline 级字段 ──
    timeline["updates"].append(upd)
    timeline["latest_update_at"] = article.get("published_at") or timeline["latest_update_at"]
    timeline["source_count"] = len({u["source_id"] for u in timeline["updates"] if u["source_id"]})
    timeline["independent_source_count"] = len(
        {u["source_group"] for u in timeline["updates"] if u["source_group"]})
    timeline["verification_status"] = (verification or {}).get("status") or timeline.get("verification_status")
    timeline["confidence"] = (verification or {}).get("confidence") or timeline.get("confidence")
    timeline["updated_at"] = _now()
    for f in flags:
        if f not in timeline["conflict_flags"]:
            timeline["conflict_flags"].append(f)
    if not upd["changed_fields"]:
        upd["changed_fields"] = ["context"]
    return timeline, upd, flags


def build_social_timelines(master_events, articles_map, source_map=None, verification_map=None):
    """从 Stage6A master events + articles 构造 timelines。

    master_events: list of master event dict（含 member_ids）。
    articles_map: {article_id: article}。
    source_map: {source_id: registry dict}（可选）。
    verification_map: {article_id: verification dict}（可选）。

    返回 (timelines, stats, updates_created)。
    """
    source_map = source_map or {}
    verification_map = verification_map or {}
    timelines = []
    stats = {"master_events_processed": 0, "timelines_created": 0,
             "updates_created": 0, "casualty_updates": 0, "actor_updates": 0,
             "official_confirmations": 0, "corrections": 0, "conflicts": 0,
             "closed_timelines": 0}
    for me in master_events:
        mids = me.get("member_ids") or []
        arts = [articles_map.get(m) for m in mids if articles_map.get(m)]
        if not arts:
            continue
        stats["master_events_processed"] += 1
        # 按 published_at 排序（§十三：同一 timeline 内按时间演进）
        arts.sort(key=lambda a: str(a.get("published_at") or ""))
        first = arts[0]
        # 若 member_ids 为空用 candidate_id
        src = source_map.get(first.get("source_id") or "", None)
        tl = new_timeline(me.get("master_event_id") or me.get("timeline_id"),
                          first, source=src,
                          verification=verification_map.get(first.get("article_id")))
        timelines.append(tl)
        stats["updates_created"] += 1
        for a in arts[1:]:
            src2 = source_map.get(a.get("source_id") or "", None)
            tl, upd, flags = apply_update(
                tl, a, source=src2,
                verification=verification_map.get(a.get("article_id")))
            stats["updates_created"] += 1
            if upd["update_type"] == "casualty_update":
                stats["casualty_updates"] += 1
            elif upd["update_type"] == "actor_attribution_update":
                stats["actor_updates"] += 1
            elif upd["update_type"] == "official_confirmation":
                stats["official_confirmations"] += 1
            elif upd["update_type"] == "correction":
                stats["corrections"] += 1
            stats["conflicts"] += len(flags)
            if tl["timeline_status"] == "closed":
                stats["closed_timelines"] += 1
        if tl["timeline_status"] == "closed":
            stats["closed_timelines"] += 1
    stats["timelines_created"] = len(timelines)
    return timelines, stats
