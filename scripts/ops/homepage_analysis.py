#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP V1.1 — Homepage Executive Intelligence AI 契约（capability 实现）。

§八/§九/§十九/§二十/§三十三：
- build_homepage_fact_pack()：确定性 Fact Pack（全部来自视图数据，LLM 不生成事实）。
- homepage_analysis_prompt()：homepage-analysis-v1 极简 schema（deepseek-v4-flash, thinking disabled）。
- boundary_gate()：高价值确定性 Guard（unsupported numbers / named refs / new events / attribution）。
- run()：执行一次 Homepage Analysis（最多 1 次调用；供未来 workflow 在 Social AI 后刷新 Brief）。

本模块不修改任何 Production schedule；仅提供能力函数与预览。
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

VIEWS = ROOT / "data" / "runtime" / "frontend_preview_public"

# 四类 Category（与前端 home-v11.js 保持一致）
CATEGORIES = {
    "conflict": ["terrorist_attack", "armed_conflict", "military_operation", "kidnapping",
                 "insurgent_activity", "cross_border_armed", "armed_activity"],
    "political": ["protest", "strike", "election", "political_crisis", "government_instability",
                  "civil_unrest", "coup_related"],
    "safety": ["major_crime", "natural_disaster", "major_accident", "humanitarian_incident",
               "border_incident", "civil_protection", "other_security"],
    "health": ["outbreak", "epidemic", "who_alert", "major_disease", "public_health_emergency"],
}


def _load(name, default=None):
    p = VIEWS / (name + ".json")
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def build_homepage_fact_pack(data_dir=None):
    """§八：确定性 Homepage Executive Fact Pack（LLM 不生成任何事实字段）。"""
    views = Path(data_dir) if data_dir else VIEWS
    def read_view(name, default):
        p = views / (name + ".json")
        if not p.exists():
            return default
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default

    ov = read_view("site_overview", {})
    me = read_view("master_events", {})
    cs = read_view("country_snapshots", {})
    dis = read_view("disease_outbreaks", {})
    ci = read_view("china_interest", {})
    ctx = read_view("context_signals", {})
    kpis = ov.get("kpis", {})
    events = me.get("events", [])
    snapshots = cs.get("snapshots", [])
    outbreaks = dis.get("outbreaks", [])
    china_rows = ci.get("rows", [])
    contexts = ctx.get("signals", [])

    def risk_of(s):
        return s.get("risk_level") if s.get("risk_level") is not None else s.get("baseline_risk_level")

    top_risk = sorted(snapshots, key=lambda s: -(risk_of(s) or 0))[:7]

    def _e(e):
        return {"event_id": e.get("master_event_id"), "headline_zh": e.get("headline_zh"),
                "country": e.get("country_cn"), "country_iso3": e.get("country_iso3"),
                "event_type": e.get("event_type"), "summary": (e.get("fact_summary") or "")[:120],
                "verification_status": e.get("verification_status"),
                "source_count": e.get("source_count"), "time": e.get("latest_update_at") or e.get("event_time")}

    return {
        "reporting_period": ov.get("latest_data_time_bj"),
        "verified_24h_events": kpis.get("events_24h"),
        "7d_events_total": sum(s.get("events_7d") or 0 for s in snapshots),
        "accepted_historical_facts": [_e(e) for e in events],
        "facts_24h": [_e(e) for e in events if e.get("event_date") == ov.get("latest_data_time_bj")],
        "metrics_7d": {"events_7d": kpis.get("events_7d"), "events_10d": kpis.get("events_10d")},
        "country_risk_levels": [{"cn": s.get("country_cn"), "iso3": s.get("country_iso3") or s.get("iso3"),
                                 "risk_level": risk_of(s)} for s in snapshots],
        "top_risk_countries": [{"cn": s.get("country_cn"), "iso3": s.get("country_iso3") or s.get("iso3"),
                                "risk_level": risk_of(s), "events_24h": s.get("events_24h"), "events_7d": s.get("events_7d")}
                               for s in top_risk],
        "disease_status": [{"disease": o.get("disease_name_cn") or o.get("disease_id"),
                            "country": o.get("country_cn") or o.get("country_iso3"),
                            "status": o.get("status"), "latest_counts": o.get("latest_counts"),
                            "as_of_date": (o.get("latest_counts") or {}).get("as_of_date")}
                           for o in outbreaks],
        "context_signals": [{"context_id": c.get("context_id"), "topic": c.get("topic") or c.get("headline_zh"),
                             "summary": c.get("summary_zh") or c.get("fact_summary_zh"), "time": c.get("event_date")}
                            for c in contexts],
        "china_interest_events": china_rows[:8],
        "top_security_events": [_e(e) for e in events[:8]],
        "category_events": {k: [_e(e) for e in events if e.get("event_type") in v][:3]
                            for k, v in CATEGORIES.items()},
        "verification_status": [{"headline": e.get("headline_zh"), "status": e.get("verification_status")}
                                for e in events[:8]],
        "uncertainties": [{"headline": e.get("headline_zh"), "uncertainties": e.get("uncertainties") or []}
                           for e in events[:5]],
        "source_coverage": {"events_with_sources": sum(1 for e in events if e.get("source_count")),
                            "total_events": len(events)},
    }


def homepage_analysis_prompt(fp):
    """§九：homepage-analysis-v1 极简 schema 提示。DeepSeek 只做归纳，不生成事实。"""
    fp_json = json.dumps(fp, ensure_ascii=False, indent=1)
    return (
        "你是 ASIP 平台的首席安全分析师。请基于以下【确定性事实包】撰写首页管理层简报。\n"
        "【硬性约束】\n"
        "- 不得生成任何新的事件、数字、日期、人员、组织、地点、风险等级、事件数量、来源引用或 ID。\n"
        "- 只允许归纳、总结、趋势解释、风险含义与 72 小时关注建议（关注对象只能来自事实包已有国家/主题）。\n"
        "- 关键判断最多 3 条。\n"
        "- 返回 JSON，格式严格如下：\n"
        '{"overall_assessment": "...", "key_judgements": ["...", "...", "..."], '
        '"china_implications": "...", "watch_next_72h": ["..."]}\n'
        "【事实包】\n" + fp_json
    )


# 高价值确定性 Guard（§三十三）
_NUM_RE = re.compile(r"\d+")
_KNOWN_FIELDS = None


def boundary_gate(text, fp):
    """检查 AI 输出是否越界：新数字/新事件/新实体引用/属性升级。"""
    issues = []
    known = json.dumps(fp, ensure_ascii=False)
    nums = set(_NUM_RE.findall(text))
    known_nums = set(_NUM_RE.findall(known))
    new_nums = [n for n in nums if len(n) >= 2 and n not in known_nums]
    if new_nums:
        issues.append("unsupported_numbers:%s" % ",".join(sorted(new_nums)[:5]))
    try:
        parsed = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        parsed = {}
    allowed_entities = set()
    for key in ("country_risk_levels", "top_risk_countries"):
        allowed_entities.update(str(x.get("cn")) for x in fp.get(key, []) if x.get("cn"))
        allowed_entities.update(str(x.get("iso3")) for x in fp.get(key, []) if x.get("iso3"))
    for key in ("accepted_historical_facts", "top_security_events"):
        allowed_entities.update(str(x.get("headline_zh")) for x in fp.get(key, []) if x.get("headline_zh"))
        allowed_entities.update(str(x.get("country")) for x in fp.get(key, []) if x.get("country"))
    for x in fp.get("disease_status", []):
        allowed_entities.update(str(x.get(k)) for k in ("disease", "country", "status") if x.get(k))
    for x in fp.get("context_signals", []):
        allowed_entities.update(str(x.get(k)) for k in ("topic", "summary") if x.get(k))
    output_text = json.dumps(parsed, ensure_ascii=False)
    # 只阻断明确的实体引入：AI 文本中出现新英文专名 token，且不属于事实包白名单。
    known_words = set(re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", known))
    output_words = set(re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", output_text))
    new_entities = sorted(x for x in output_words - known_words if x.lower() not in {"overall", "assessment", "key", "judgements", "china", "implications", "watch", "next"})
    if new_entities:
        issues.append("unsupported_named_entities:%s" % ",".join(new_entities[:5]))
    if any(marker in output_text for marker in ("新增事件", "发生了新的", "new event", "confirmed event")):
        issues.append("new_event_introduction")
    for w in ("确认发生", "已证实", "官方确认"):
        if w in output_text:
            issues.append("attribution_escalation:" + w)
    return (len(issues) == 0, issues)


def run(provider, data_dir=None, emit=lambda s: print(s)):
    """执行一次 Homepage Analysis（§三十二：单次调用预算）。"""
    fp = build_homepage_fact_pack(data_dir)
    prompt = homepage_analysis_prompt(fp)
    task = {"task_type": "homepage_analysis", "prompt": prompt,
            "schema": {"type": "object",
                       "properties": {
                           "overall_assessment": {"type": "string"},
                           "key_judgements": {"type": "array", "maxItems": 3,
                                              "items": {"type": "string"}},
                           "china_implications": {"type": "string"},
                           "watch_next_72h": {"type": "array", "items": {"type": "string"}}},
                       "required": ["overall_assessment", "key_judgements"]}}
    res = provider.submit_task(task)
    text = ""
    if res.get("status") == "succeeded":
        try:
            parsed = json.loads(res.get("result", {}).get("text", "{}"))
            ok, issues = boundary_gate(json.dumps(parsed, ensure_ascii=False), fp)
            if not ok:
                emit("HOMEPAGE_AI_BOUNDARY_ISSUES=%s" % ";".join(issues))
                return {"status": "held", "issues": issues, "fact_pack_hash":
                        hashlib.sha256(json.dumps(fp, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()}
            result = res.get("result") or {}
            usage = {"input_tokens": int(result.get("input_tokens") or 0),
                     "output_tokens": int(result.get("output_tokens") or 0),
                     "total_tokens": int(result.get("total_tokens") or 0)}
            return {"status": "ok", "analysis": parsed,
                    "fact_pack_hash": hashlib.sha256(json.dumps(fp, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
                    "usage": usage, "provider": result.get("provider") or "workbuddy_queue",
                    "model": result.get("returned_model") or "deepseek-v4-flash"}
        except Exception:
            return {"status": "fallback", "reason": "invalid_json"}
    return {"status": "fallback", "reason": res.get("status")}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Homepage Analysis capability (preview)")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--fake", action="store_true", help="fake provider（无 AI 调用）")
    args = ap.parse_args(argv)
    fp = build_homepage_fact_pack(args.data_dir)
    print(json.dumps({"fact_pack_keys": sorted(fp.keys()),
                      "events": len(fp["top_security_events"]),
                      "top_risk": len(fp["top_risk_countries"]),
                      "categories": {k: len(v) for k, v in fp["category_events"].items()}},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
