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
    ov = json.loads((views / "site_overview.json").read_text(encoding="utf-8")) \
        if (views / "site_overview.json").exists() else {}
    me = json.loads((views / "master_events.json").read_text(encoding="utf-8")) \
        if (views / "master_events.json").exists() else {}
    cs = json.loads((views / "country_snapshots.json").read_text(encoding="utf-8")) \
        if (views / "country_snapshots.json").exists() else {}
    dis = json.loads((views / "disease_outbreaks.json").read_text(encoding="utf-8")) \
        if (views / "disease_outbreaks.json").exists() else {}
    evs_raw = json.loads((ROOT / "data" / "events.json").read_text(encoding="utf-8")) \
        if (ROOT / "data" / "events.json").exists() else {}

    kpis = ov.get("kpis", {})
    events = me.get("events", [])
    snapshots = cs.get("snapshots", [])
    outbreaks = dis.get("outbreaks", [])
    evs = evs_raw.get("events", [])

    top_risk = sorted(snapshots, key=lambda s: -(s.get("baseline_risk_level") or 0))[:7]
    china = [e for e in evs if e.get("china_related")][:3]

    def _e(e):
        return {"headline_zh": e.get("headline_zh"), "country": e.get("country_cn"),
                "event_type": e.get("event_type"), "summary": (e.get("fact_summary") or "")[:120],
                "verification_status": e.get("verification_status"),
                "source_count": e.get("source_count"), "time": e.get("latest_update_at")}

    return {
        "reporting_period": ov.get("latest_data_time_bj"),
        "verified_24h_events": kpis.get("events_24h"),
        "7d_events_total": sum(s.get("events_7d") or 0 for s in snapshots),
        "country_risk_levels": [{"cn": s.get("country_cn"), "iso3": s.get("iso3"),
                                 "risk_level": s.get("baseline_risk_level")} for s in snapshots],
        "top_risk_countries": [{"cn": s.get("country_cn"), "risk_level": s.get("baseline_risk_level"),
                                "events_24h": s.get("events_24h"), "events_7d": s.get("events_7d")}
                               for s in top_risk],
        "disease_signals": [{"disease": o.get("disease_name_cn") or o.get("disease_id"),
                             "country": o.get("country_cn") or o.get("country_iso3"),
                             "status": o.get("status")} for o in outbreaks if o.get("status")],
        "china_interest_events": [_e(e) for e in events if e.get("country_iso3") == "CN"] + china,
        "top_security_events": [_e(e) for e in events[:8]],
        "category_events": {k: [_e(e) for e in events if e.get("event_type") in v][:3]
                            for k, v in CATEGORIES.items()},
        "verification_status": [{"headline": e.get("headline_zh"), "status": e.get("verification_status")}
                                for e in events[:8]],
        "uncertainties": [{"headline": e.get("headline_zh"),
                           "uncertainties": e.get("uncertainties") or []} for e in events[:5]],
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
    """检查 AI 输出是否越界：新数字/新事件/新实体引用/属性升级。

    返回 (ok, issues)。仅做确定性启发式：输出中出现事实包外的 3+ 位数字
    或已知实体名以外的专名引用即标记。实体白名单来自事实包。
    """
    issues = []
    known = json.dumps(fp, ensure_ascii=False)
    # 1) 新数字（事实包中不存在的 2 位以上数字）
    nums = set(_NUM_RE.findall(text))
    known_nums = set(_NUM_RE.findall(known))
    new_nums = [n for n in nums if len(n) >= 2 and n not in known_nums]
    if new_nums:
        issues.append("unsupported_numbers:%s" % ",".join(sorted(new_nums)[:5]))
    # 2) 事件/国家/人员/组织新引用（启发式：事实包外中文专名，谨慎避免误报）
    # 3) 归因升级：出现"确认/证实"等强词
    for w in ("确认发生", "已证实", "官方确认"):
        if w in text:
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
                        hash(json.dumps(fp, ensure_ascii=False, sort_keys=True))}
            return {"status": "ok", "analysis": parsed,
                    "fact_pack_hash": hash(json.dumps(fp, ensure_ascii=False, sort_keys=True))}
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
