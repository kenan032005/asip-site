#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quarantine_reeval.py —— C2 §七：历史 quarantine 重新判定（确定性规则，供管线与测试共用）。

先把历史 hold 分成两类：
  TRUE_SAFETY_HOLD     —— 真安全/隐私/无效 → **永不释放**
  SEMANTIC_FILTER_HOLD —— 语义闸门（wrong_country / not_security_relevant /
                          insufficient_body / homepage_or_listing_page）

释放规则（三条全部满足才允许重新判定并释放）：
  A. reason_code == "wrong_country"
  B. 该 hold 产生于 country detection 规则发生变化**之前**（旧逻辑的 false negative）
  C. 内容真实发布时间落在回填窗口内

not_security_relevant 只在 relevance 规则发生**实质变化**时重判；本仓库中唯一实质变化
是 C1C 为莫桑比克补了葡语词表，因此只对葡语内容开放重判，其余保持原 hold。

本模块不读网络、不写文件，是纯函数；调用方负责取数与落盘。
"""
import re
from datetime import datetime, timezone

#: 真安全 hold（绝不放）
TRUE_SAFETY_CODES = frozenset({
    "privacy", "personal_data", "illegal_content", "safety_hold",
    "explicit_safety_hold", "malicious", "credential_leak", "csam", "violent_graphic",
})
#: 语义闸门 hold（可谈）
SEMANTIC_FILTER_CODES = frozenset({
    "wrong_country", "not_security_relevant", "insufficient_body",
    "homepage_or_listing_page",
})
#: 允许重新判定的唯一语义原因（本任务）
REPROCESSABLE_REASON = "wrong_country"


def classify(reason_code):
    c = reason_code or ""
    if c in TRUE_SAFETY_CODES:
        return "TRUE_SAFETY_HOLD"
    if c in SEMANTIC_FILTER_CODES:
        return "SEMANTIC_FILTER_HOLD"
    return "OTHER"


def _dt(v):
    if not v:
        return None
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def hold_content_time(entry):
    """hold 对应内容的真实时间：legacy_payload 的 published_time/event_time，
    或从 URL 的 /YYYY/MM/DD/ 路径推断（不少 publisher 的 permalink 带日期）。"""
    lp = entry.get("legacy_payload") or {}
    for k in ("published_time", "event_time"):
        d = _dt(lp.get(k))
        if d:
            return d
    url = entry.get("url") or lp.get("url") or lp.get("article_url") or ""
    m = re.search(r"/(20\d\d)/(\d{2})/(\d{2})/", url)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                            12, 0, tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def hold_domain(entry):
    import urllib.parse
    lp = entry.get("legacy_payload") or {}
    u = entry.get("url") or lp.get("url") or lp.get("article_url") or lp.get("source_url") or ""
    try:
        return urllib.parse.urlsplit(u).netloc.lower().replace("www.", "")
    except Exception:  # noqa: BLE001
        return ""


def is_reprocessable(entry, *, rule_change_at, window_start, window_end,
                     approved_domains, hold_time=None):
    """返回 (allowed: bool, reason: str)。三条全满足才 True。"""
    if classify(entry.get("reason_code")) == "TRUE_SAFETY_HOLD":
        return False, "TRUE_SAFETY_HOLD_NEVER_RELEASED"
    if entry.get("reason_code") != REPROCESSABLE_REASON:
        return False, "REASON_NOT_REPROCESSABLE:%s" % entry.get("reason_code")
    det = _dt(entry.get("detected_at"))
    if det is None or det >= rule_change_at:
        return False, "PRODUCED_UNDER_CURRENT_RULES"
    t = hold_time if hold_time is not None else hold_content_time(entry)
    if t is None:
        return False, "NO_CONTENT_TIME"
    if not (window_start <= t <= window_end):
        return False, "OUTSIDE_BACKFILL_WINDOW"
    if hold_domain(entry) not in approved_domains:
        return False, "DOMAIN_NOT_APPROVED"
    return True, "REPROCESS_ALLOWED"


def relevance_reprocessable(entry, *, rule_change_at, window_start, window_end,
                            approved_domains, hold_time=None):
    """not_security_relevant：只有葡语内容（葡语词表在本轮之前发生实质变化）才允许重判。"""
    if entry.get("reason_code") != "not_security_relevant":
        return False, "NOT_A_RELEVANCE_HOLD"
    det = _dt(entry.get("detected_at"))
    if det is None or det >= rule_change_at:
        return False, "PRODUCED_UNDER_CURRENT_RULES"
    blob = " ".join(str(entry.get(k) or "") for k in ("title", "url", "reason_cn"))
    lp = entry.get("legacy_payload") or {}
    blob += " " + " ".join(str(lp.get(k) or "") for k in ("title_original", "title_cn", "language"))
    if not re.search(r"\b(pt|portugu[eê]s|portuguese)\b", blob, re.I):
        return False, "NO_MATERIAL_RULE_CHANGE_FOR_THIS_LANGUAGE"
    t = hold_time if hold_time is not None else hold_content_time(entry)
    if t is None or not (window_start <= t <= window_end):
        return False, "OUTSIDE_BACKFILL_WINDOW"
    if hold_domain(entry) not in approved_domains:
        return False, "DOMAIN_NOT_APPROVED"
    return True, "REPROCESS_ALLOWED"
