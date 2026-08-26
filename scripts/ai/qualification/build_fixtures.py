#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8B — Committed Qualification Fixture Builder（§二-§五）。

从 Stage7A/7B 已生成的真实报告输入契约，生成 sanitized 冻结快照，
提交进 git（data/qualification/stage8b/），使 Actions checkout 中
报告 case 测试真实输入（不再依赖 gitignored data/runtime）。

来源（真实，不修改业务事实）：
  RD1  daily_input/latest.json（真实 Africa Daily input）
  RD2  single-source/conflicting mix（真实筛选派生）
  RD3  disease + major security mix（真实筛选派生）
  RW1  weekly_input/TCD.json（真实）
  RW2  weekly_input/SSD.json（真实）
  RW3  weekly_input/NER.json（真实 low-data）
  RB1  major security brief（真实 master event 结构化输入）
  RB2  major disease/cross-border brief（真实 outbreak 结构化输入）

规则：
  - 保留原 Input Schema / facts / analysis_inputs / uncertainties /
    source_evidence / metrics / verification / disease counts / timeline changes。
  - sanitize：剔除 internal debug / score / review_pair / candidate /
    runtime paths / 密钥；输出 fixture_safety_scan。
  - manifest.json：case_id/task_type/fixture_path/input_schema_version/
    source_snapshot_date/sanitized/fixture_hash + prompt 路由 + output schema。

用法：
  python scripts/ai/qualification/build_fixtures.py
"""
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "qualification" / "stage8b"
QUALIFICATION_VERSION = "stage8b-v1"
SNAPSHOT_DATE = "2026-08-26"

# Prompt 路由（§八/§九）：真实 Stage7B 报告 prompt + 对应 schema
PROMPT_ROUTE = {
    "africa_daily": {
        "prompt_file": "config/prompts/africa_daily_report_v1.md",
        "prompt_version": "v1.0.3",
        "input_schema": "schemas/africa_daily_report_input.schema.json",
        "output_schema": "schemas/africa_daily_report.schema.json",
        "input_schema_version": "stage7a-v1",
    },
    "country_weekly": {
        "prompt_file": "config/prompts/country_weekly_report_v1.md",
        "prompt_version": "v1.0.3",
        "input_schema": "schemas/country_weekly_report_input.schema.json",
        "output_schema": "schemas/country_weekly_report.schema.json",
        "input_schema_version": "stage7a-v1",
    },
    "major_event_brief": {
        "prompt_file": "config/prompts/major_event_brief_v1.md",
        "prompt_version": "v1.0.4",
        "input_schema": "schemas/major_event_brief_input.schema.json",
        "output_schema": "schemas/major_event_brief.schema.json",
        "input_schema_version": "stage7b-v1",
    },
}

_SECRET_RE = re.compile(
    r"ASIP_GLM_API_KEY|ASIP_DEEPSEEK_API_KEY|sk-[A-Za-z0-9]{16,}|"
    r"Bearer\s+[A-Za-z0-9._-]{16,}|GITHUB_TOKEN|GH_TOKEN|client_secret", re.I)
_INTERNAL_KEY_HINT = ("debug", "review_pair", "internal", "raw", "telemetry",
                      "prompt_cache", "runtime_path")
# sanitize 豁免：schema 必需字段（不得被内部关键词规则误删）
_SANITIZE_EXEMPT = {"trigger_score", "candidate_status", "trigger_reasons",
                    "source_count", "independent_source_count", "source_evidence"}


def sanitize(obj):
    """剔除内部字段 + 任何 /data/runtime 路径引用（豁免 schema 必需字段）。"""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            kl = k.lower()
            if k in _SANITIZE_EXEMPT:
                out[k] = sanitize(v)
                continue
            if any(h in kl for h in _INTERNAL_KEY_HINT):
                continue
            out[k] = sanitize(v)
        return out
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    if isinstance(obj, str):
        s = obj
        if "/data/runtime/" in s or "data\\runtime\\" in s:
            s = re.sub(r"(?:/|\\)data(?:/|\\)runtime(?:/|\\)[A-Za-z0-9_./\\-]*", "[runtime-path-redacted]", s)
        return s
    return obj


def load_json(rel):
    p = ROOT / rel
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit("fixture source missing: %s (%s)" % (rel, e))


def daily_variant(daily, kind):
    import copy
    d = copy.deepcopy(daily)
    sec = d.get("sections") or {}
    # 保留全部 section 键（schema 必需），无关键置空
    all_keys = list(sec.keys())
    if kind == "single_conflict":
        keep = []
        for k in ("major_security_developments", "terrorism_armed_violence",
                  "political_social_stability", "cross_border_regional"):
            for it in sec.get(k, []) or []:
                if it.get("single_source_warning") or it.get("conflicting"):
                    keep.append(it)
        d["sections"] = {k: (keep[:6] if k == "major_security_developments" else [])
                         for k in all_keys}
        d["sections"]["public_health_disease"] = []
        d["sections"]["executive_summary"] = []
        d["note"] = "RD2: single-source/conflicting mix（真实筛选）"
    elif kind == "disease_security":
        dis = (sec.get("public_health_disease") or [])[:3]
        maj = (sec.get("major_security_developments") or [])[:3]
        d["sections"] = {k: [] for k in all_keys}
        d["sections"]["major_security_developments"] = maj
        d["sections"]["public_health_disease"] = dis
        d["sections"]["executive_summary"] = []
        d["note"] = "RD3: disease + major security mix（真实筛选）"
    return d


def brief_input(security):
    me = load_json("data/runtime/frontend_preview_public/master_events.json") or {}
    do = load_json("data/runtime/frontend_preview_public/disease_outbreaks.json") or {}
    if security:
        e = (me.get("events") or [{}])[0]
        loc = e.get("location")
        if isinstance(loc, list):
            loc = ", ".join(str(x) for x in loc)[:200] or None
        return {
            "brief_id": "BRF_QUAL_S", "report_type": "major_event_brief",
            "trigger_score": 0, "trigger_reasons": [],
            "candidate_status": "below_threshold",
            "event_id": e.get("master_event_id"),
            "master_event_id": e.get("master_event_id"),
            "country_iso3": e.get("country_iso3"), "country": e.get("country_cn"),
            "event_type": e.get("event_type") or "other_security",
            "event_time": e.get("event_time"),
            "location": loc,
            "verification_status": e.get("verification_status"),
            "source_count": e.get("source_count"),
            "facts": [{"fact": e.get("fact_summary") or ""}],
            "uncertainties": (e.get("uncertainties") or [])[:2],
            "label": "qualification_sample",
            "note": "真实 master event 结构化输入（无真实 brief candidate 时的资质样本）"}
    o = (do.get("outbreaks") or [{}])[0]
    return {
        "brief_id": "BRF_QUAL_D", "report_type": "major_event_brief",
        "trigger_score": 0, "trigger_reasons": [],
        "candidate_status": "below_threshold",
        "event_id": o.get("outbreak_id"),
        "outbreak_id": o.get("outbreak_id"),
        "disease_id": o.get("disease_id"),
        "country_iso3": o.get("country_iso3"),
        "country": o.get("country_cn") or (o.get("country_iso3") or "regional"),
        "event_type": "public_health",
        "event_time": o.get("latest_report_at"),
        "verification_status": o.get("verification_status"),
        "source_count": o.get("source_count"),
        "facts": [{"fact": "latest counts: %s" % json.dumps(o.get("latest_counts") or {}, ensure_ascii=False)}],
        "uncertainties": (o.get("uncertainties") or [])[:2],
        "label": "qualification_sample",
        "note": "真实 disease outbreak 结构化输入（资质样本）"}


def daily_period(daily):
    """§四：Daily period 确定性生成（北京时间 ISO8601，LLM 不推导）。

    Stage7B §二 temporal 语义证据（cutoff 相对滚动窗）：
      - cutoff = 报告生成时刻（builder.py: cutoff 默认 now +08:00）
      - new_24h（≤~1 天）为主报告窗；ongoing_72h 仅 developing 条件；
        trend_7d 仅 watch。
    → 主日报时间窗 = cutoff - 24h → cutoff（选项 B）。
    72h/7d 属 watch context，不得混入 period_start/period_end。

    实现：
      period_start = cutoff - 24 hours（保持 +08:00 时区）
      period_end   = cutoff
    """
    from datetime import datetime, timedelta
    cutoff = (daily.get("cutoff") or "").strip()
    if not cutoff:
        return None, None
    try:
        dt = datetime.fromisoformat(cutoff)
        ps = (dt - timedelta(hours=24)).isoformat(timespec="seconds")
        return ps, cutoff
    except Exception:
        return None, None


def main():
    daily = load_json("data/runtime/reports/daily_input/latest.json")
    weekly = {c: load_json("data/runtime/reports/weekly_input/%s.json" % c)
              for c in ("TCD", "SSD", "NER")}

    def rd_daily(kind):
        d = daily_variant(daily, kind)
        ps, pe = daily_period(d)
        d["period_start"] = ps
        d["period_end"] = pe
        return d

    cases = [
        ("RD1", "africa_daily", rd_daily("normal"), "daily/RD1.json"),
        ("RD2", "africa_daily", rd_daily("single_conflict"), "daily/RD2.json"),
        ("RD3", "africa_daily", rd_daily("disease_security"), "daily/RD3.json"),
        ("RW1", "country_weekly", weekly["TCD"], "weekly/RW1.json"),
        ("RW2", "country_weekly", weekly["SSD"], "weekly/RW2.json"),
        ("RW3", "country_weekly", weekly["NER"], "weekly/RW3.json"),
        ("RB1", "major_event_brief", brief_input(security=True), "brief/RB1.json"),
        ("RB2", "major_event_brief", brief_input(security=False), "brief/RB2.json"),
    ]
    manifest = {"qualification_version": QUALIFICATION_VERSION,
                "source_snapshot_date": SNAPSHOT_DATE,
                "cases": []}
    safety = []
    for cid, task_type, payload, rel in cases:
        clean = sanitize(payload)
        text = json.dumps(clean, ensure_ascii=False, indent=1)
        # 安全扫描
        if _SECRET_RE.search(text):
            safety.append("%s: SECRET pattern" % cid)
        if "/data/runtime/" in text or "data\\runtime\\" in text:
            safety.append("%s: runtime path residue" % cid)
        route = PROMPT_ROUTE[task_type]
        fp = OUT / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(text, encoding="utf-8")
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        prompt_path = ROOT / route["prompt_file"]
        prompt_hash = hashlib.sha256(
            prompt_path.read_text(encoding="utf-8").encode()).hexdigest()[:16] \
            if prompt_path.exists() else None
        manifest["cases"].append({
            "case_id": cid, "task_type": task_type, "fixture_path": rel,
            "input_schema_version": route["input_schema_version"],
            "input_schema": route["input_schema"],
            "output_schema": route["output_schema"],
            "ai_content_schema": "schemas/%s_ai_content.schema.json" % task_type,
            "prompt_file": route["prompt_file"],
            "prompt_version": route["prompt_version"],
            "prompt_hash": prompt_hash,
            "sanitized": True, "fixture_hash": h,
            "source_snapshot_date": SNAPSHOT_DATE,
        })
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print("fixtures written:", len(cases), "to", OUT)
    print("safety issues:", safety or "NONE")
    # schema 自检
    from scripts.ai.schema_validation import validate_against_schema
    for cid, task_type, payload, rel in cases:
        route = PROMPT_ROUTE[task_type]
        schema = json.loads((ROOT / route["input_schema"]).read_text(encoding="utf-8"))
        errs = validate_against_schema(sanitize(payload), schema)
        print("  schema %-5s %s %s" % (cid, "PASS" if not errs else "FAIL", errs[:2]))
    return 0 if not safety else 2


if __name__ == "__main__":
    sys.exit(main())
