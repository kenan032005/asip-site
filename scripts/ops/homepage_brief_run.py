#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C7-5 — 首页情报事实包 + 首页 AI 简报（一次结构化 AI 调用，含事实门）。

P1 事实包（确定性，REAL_AI_CALLS=0）：
   data/runtime/ops/homepage_intelligence_fact_pack.json
   输入：公开情报信号（news_stream）、已核实事件（published_events）、来源 tier/role、
        既有事件 AI 富集（canonical 字段）、当日 AI 研判（assessment）、executive_summary、
        疾病公开数据（public/disease_events）、国家监测数据（countries.json）
   窗口：主窗 24h；趋势上下文 7d。

P2 首页 AI 简报：scripts/ops/homepage_brief_run.py（本文件）
   - 一次调用产出全部首页分析内容（overall/sectors/top/china/health）
   - 节奏：**最多每 6 小时一次** 且 **仅当 input_hash 实质变化**
   - 产出 data/intelligence/ai/homepage/<YYYYMMDDhh>.json

P3 事实门（fail-closed）：国家存在 / 事件与信号 ID 存在 / 数字主张白名单 /
   引用可解析 / 枚举合法 / 结构合法 / China 影响与健康结论须有对应事实支撑。

用法：
  python scripts/ops/homepage_brief_run.py --fact-pack-only   # 只产事实包（无 AI）
  python scripts/ops/homepage_brief_run.py                  # 事实包 +（到期才）AI 简报
  python scripts/ops/homepage_brief_run.py --dry-run
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BJT = timezone(timedelta(hours=8))
PACK = Path("data") / "runtime" / "ops" / "homepage_intelligence_fact_pack.json"
OUT_DIR = Path("data") / "intelligence" / "ai" / "homepage"
#: 首页简报事实门版本。任何改动事实门校验语义（可引用数值集合、结构约束）都必须递增：
#: 节奏与缓存只以**同版本**的上一次尝试为准 —— 旧版本门产出的失败记录不会把新版本
#: 锁在 6h 窗口之外（与项目既有 CLASSIFIER_VERSION 约定一致）。
GATE_VERSION = 3
CADENCE_HOURS = 6

SECTORS = ["terrorism_conflict", "political_social", "crime_public_security",
           "military_border_maritime", "accident_disruption"]
CATEGORY_TO_SECTOR = {
    "armed_conflict": "terrorism_conflict", "terrorist_attack": "terrorism_conflict",
    "military_operation": "military_border_maritime",
    "civil_unrest": "political_social", "strike": "political_social",
    "political_crisis": "political_social",
    "kidnapping": "crime_public_security", "violent_crime": "crime_public_security",
    "banditry": "crime_public_security", "crime": "crime_public_security",
    "natural_disaster": "accident_disruption", "accident": "accident_disruption",
    "public_health": "accident_disruption", "infrastructure": "accident_disruption",
}

SYSTEM = (
    "你是 ASIP 平台的首席非洲安全分析师，为机构领导、安全负责人与企业决策者撰写首页情报简报。"
    "输入是结构化事实包，每条都带证据层级：\n"
    "  evidence_tier=multi_source_verified → 多源独立核实，可用『已核实』表述；\n"
    "  evidence_tier=single_source_published → 公开报道/单一来源，必须写成『公开报道显示』『单一来源消息，尚待核实』；\n"
    "  kind=news_signal → 文章级情报信号，同样不得写成已确立事实。\n"
    "写作硬性规则：\n"
    "1) 只使用事实包中的信息；禁止引入包外国家、事件、数字、来源；\n"
    "2) 严禁任何系统/工程语言：不得出现 事实包、Tier、tier、信源分级、管道、pipeline、"
    "input_hash、gate、run_id、采集器、窗口统计、条目计数式表述（如『N条情报信号』『N起已核实事件』）；"
    "只写事件、分析、趋势、风险与运营影响；\n"
    "3) 面向读者是执行层与业务决策者：先事实、再研判、最后前瞻；用谨慎情报语言，"
    "不得把预测写成既成事实；\n"
    "4) 中国影响：只有事实包中出现明确涉华证据时才可断言直接影响；否则必须说明未发现明确涉华重大事件，"
    "并可另行给出有事实支撑的区域性运营风险；\n"
    "5) 健康议题只能依据事实包 health 数据，禁止医学预测；起始时间不明时必须写"
    "『起始时间尚未从现有公开数据中确认』；\n"
    "6) 数字只能引用事实包 counts 中已有的计数，且必须以『N起 / N个国家 / N条 / N个信号』"
    "形式给出；不得对未计入 counts 的事物使用数字量词；\n"
    "7) 输出单个严格 JSON 对象，无解释文字、无 Markdown。")

USER_TMPL = """事实包（唯一信息来源）：

%s

请输出如下 JSON：
{{
 "overall_assessment": {{
   "summary_cn": "450–700 个汉字的非洲安全态势报告正文：A 事实态势（24h 主要地区/国家与安全事态、"
                 "升级或降级、有意义的运营动向）→ B 情报解读（含义、延续或转折、正在形成的模式、"
                 "有证据支撑的关联）→ C 前瞻判断（短期方向、24–72 小时关注、可能恶化或改善的因素）。"
                 "禁止系统语言与工程术语，禁止条目计数式表述",
   "risk_direction": "improving|stable|worsening",
   "confidence": "high|medium|low",
   "key_judgments": ["≤60字，3–5 条"],
   "watch_24_72h": ["≤50字，3–5 条"]
 }},
 "sectors": {{
   "terrorism_conflict": {{"assessment_cn": "300–500 字：近 7 日事实态势 + 解读 + 趋势判断 + 主要受影响国家/地区 + 显著变化 + 前瞻关注",
                          "changes_cn": "≤80字", "watch_cn": "≤80字", "trend": "up|flat|down", "confidence": "high|medium|low"}},
   "political_social": {{...}}, "crime_public_security": {{...}},
   "military_border_maritime": {{...}}, "accident_disruption": {{...}}
 }},
 "top_developments": [{{"fact_id": "<事实包中的 fact_id>",
                       "why_important_cn": "≤80字",
                       "analysis_cn": "100–200 字：解读该事件的含义、背景与可能走向",
                       "impact_cn": "≤80字：可能影响",
                       "watch_cn": "≤60字：后续关注"}}],
 "china_impact": {{"overall_level": "none|low|medium|high",
                   "summary_cn": "≤150字：总体影响研判结论",
                   "analysis_cn": "300–500 字（有证据支撑时）：按 人员安全 / 项目运营 / 交通物流 / 能源矿业基建暴露 / 政治社会扰动 展开",
                   "items": [{{"fact_id": "fact_id", "country": "国家中文名",
                              "sector": "personnel|energy|mining|infrastructure|transport|project_ops|political",
                              "impact_level": "low|medium|high", "impact_note": "≤80字"}}]}},
 "health_security": {{"summary_cn": "300–500 字（有数据支撑时），按 地区国别 / 疾病或卫生问题 / 起始时间 / "
                     "当前严重程度 / 趋势（worsening|stable|improving|unclear）/ 人员与运营影响 叙述；"
                     "起始时间不明时明确写『起始时间尚未从现有公开数据中确认』",
                     "issues": [{{"where": "国家/地区", "what": "疾病或卫生问题", "when": "起始时间或『待确认』",
                                 "severity_cn": "当前严重程度", "trend": "worsening|stable|improving|unclear",
                                 "impact_cn": "≤60字：人员/运营影响"}}],
                     "key_issues": ["≤50字"], "impact_cn": "≤80字", "trend": "worsening|stable|improving|unclear",
                     "confidence": "high|medium|low"}},
 "source_fact_refs": ["≥5 条真实 fact_id"]
}}
要求：top_developments 5–8 条且 fact_id 必须真实存在；sectors 无数据时 assessment_cn 填
"过去24小时未发现足够高质量公开信息形成明确判断"；china_impact.items 无证据时给空数组。
只输出 JSON。"""

NUM_UNITS = re.compile(r"(\d+)\s*(?:起|个国家|个事件|条|个信号)")
#: 正文（执行层报告）禁止出现的系统/工程语言（fail-closed）
BANNED_IN_PROSE = ("事实包", "Tier ", "TierA", "tier ", "A级", "C级", "信源分级",
                   "数据管道", "pipeline", "input_hash", "run_id", "采集器",
                   "gate", "GATE", "多源核实率", "投影")
#: 条目计数式表述（数字应留在指标条，不进正文）
SYSTEM_COUNT_PHRASES = re.compile(r"\d+\s*(?:条|起|个)\s*(?:情报信号|已核实事件|信号|事件)")


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def write_atomic(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def parse_time(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=BJT)
    except ValueError:
        return None


def tier_of(srcs, source_name):
    for s in srcs:
        if s.get("source_name") == source_name:
            return s.get("source_tier") or "C", s.get("source_role") or "local_signal"
    return "C", "local_signal"


def build_fact_pack(root, now):
    data = Path(root) / "data"
    srcs = (load_json(data / "sources.json", {}) or {}).get("sources") or []
    feed = (load_json(data / "views" / "news_stream.json", {}) or {}).get("items") or []
    pubs = (load_json(data / "public" / "published_events.json", {}) or {}).get("items") or []
    disease = (load_json(data / "public" / "disease_events.json", {}) or {}).get("items") or []
    countries = (load_json(data / "countries.json", {}) or {}).get("countries") \
        or (load_json(data / "countries.json", {}) or {}).get("items") or []
    exec_view = load_json(data / "views" / "executive_summary.json", {}) or {}

    h24, d7 = now - timedelta(hours=24), now - timedelta(days=7)
    sig24, sig7, ev24, ev7 = [], [], [], []
    for s in feed:
        if s.get("quarantined"):
            continue
        t = parse_time(s.get("last_seen_at") or s.get("observed_at"))
        if not t:
            continue
        if t >= d7:
            sig7.append((s, t))
            if t >= h24:
                sig24.append((s, t))
    for e in pubs:
        t = parse_time(e.get("published_time") or e.get("event_time"))
        if not t:
            continue
        if t >= d7:
            ev7.append((e, t))
            if t >= h24:
                ev24.append((e, t))

    facts = {}
    for s, t in sig7:
        fid = "news:%s" % hashlib.sha256(str(s.get("dedup_key") or s.get("news_id")
                                               or s.get("src_id") or "").encode()).hexdigest()[:16]
        tier, role = tier_of(srcs, str(s.get("source_name") or ""))
        facts[fid] = {"fact_id": fid, "level": "news_signal", "evidence_tier": "news_signal",
                      "source_count": int(s.get("independent_source_count") or 1),
                      "country": s.get("country_cn") or "未识别",
                      "title": (s.get("title_cn") or s.get("title_original") or "")[:140],
                      "category": s.get("event_type") or "other_security",
                      "source": s.get("source_name") or "", "source_tier": tier, "source_role": role,
                      "time": t.strftime("%Y-%m-%d %H:%M"),
                      "importance": s.get("importance") or "low",
                      "why_it_matters": (s.get("why_it_matters") or "")[:120]}
    for e, t in ev7:
        fid = str(e.get("event_id") or "")
        sf = ((e.get("source_links") or [{}])[0] or {})
        tier, role = tier_of(srcs, str(sf.get("source_name") or e.get("source_name") or ""))
        _isc = int(e.get("independent_source_count") or 0)
        _vtier = ("multi_source_verified" if _isc >= 2 else "single_source_published")
        facts[fid] = {"fact_id": fid, "level": "verified_event", "evidence_tier": _vtier,
                      "source_count": _isc or len(e.get("source_links") or []),
                      "country": e.get("country_cn") or "未识别",
                      "title": (e.get("title_cn") or e.get("title_original") or "")[:140],
                      "category": e.get("event_type") or "other_security",
                      "source": sf.get("source_name") or e.get("source_name") or "",
                      "source_tier": tier, "source_role": role,
                      "time": t.strftime("%Y-%m-%d %H:%M"),
                      "importance": "high",
                      "severity": e.get("event_severity") or "",
                      "source_count": int(e.get("independent_source_count") or 0)}

    def counter(rows, f):
        return [{"value": k, "count": v} for k, v in Counter(f(x) for x, _ in rows).most_common(12)]

    health = [{"disease": d.get("disease_name_zh") or d.get("disease_name_en"),
               "country_iso3": d.get("country_iso3"), "date": d.get("report_date"),
               "location": d.get("location_raw")} for d in disease][:12]

    # 24h 活跃国家（信号 ∪ 已核实事件），供首页关键计数使用
    c24 = sorted({s_.get("country_cn") for s_, _t in sig24 if s_.get("country_cn")} |
                 {e.get("country_cn") for e, _t in ev24 if e.get("country_cn")})

    tier_dist = Counter(f["source_tier"] for f in facts.values())
    pack = {
        "schema": "homepage-intelligence-fact-pack-v1",
        "generated_at": now.isoformat(timespec="seconds"),
        "windows": {"primary_hours": 24, "context_days": 7},
        "counts": {"signals_24h": len(sig24), "signals_7d": len(sig7),
                   "verified_events_24h": len(ev24), "verified_events_7d": len(ev7),
                   "multi_source_verified_events_7d": len([1 for e, _t in ev7
                                                           if int(e.get("independent_source_count") or 0) >= 2]),
                   "countries_with_activity_24h": len(c24),
                   "total_countries_monitored": len(countries)},
        "countries_24h": c24,
        "countries_7d": sorted({f["country"] for f in facts.values()} - {"未识别"}),
        "country_distribution_7d": counter(sig7, lambda x: x.get("country_cn") or "未识别"),
        "category_distribution_24h": counter(sig24, lambda x: x.get("event_type_cn")
                                             or x.get("event_type") or "其他"),
        "source_tier_distribution_7d": [{"value": k, "count": v} for k, v in tier_dist.most_common()],
        "top_verified_events": [f for f in facts.values() if f["level"] == "verified_event"][:6],
        "top_signals": sorted([f for f in facts.values() if f["level"] == "news_signal"],
                              key=lambda f: ({"high": 2, "medium": 1}.get(f["importance"], 0), f["time"]),
                              reverse=True)[:24],
        "health": health,
        "existing_assessment": (exec_view.get("assessment") or {}),
        "fact_count": len(facts),
        "facts": facts,
    }
    return pack


def _numeric_allowlist(pack):
    """事实包中**所有**可引用的数值（供数字主张校验）。

    规则不变：AI 引用的数字必须等于事实包算出的某个值；这里只是把"可引用数值"
    的集合补全为事实包里真正存在的全部计数 —— counts、三个分布的民族/类别/层级计数、
    以及各列表长度与事实总数。此前集合只含顶层 counts，导致 AI 引用事实包自带的
    分布计数（如「乍得 43 条」）时被误判为越界（生产实测连续 10 轮 FACT_GATE_FAIL：
    43条 / 14起 / 48起 / 125条 …）。
    """
    vals = set()

    def add(v):
        if isinstance(v, bool) or v is None:
            return
        if isinstance(v, int):
            vals.add(str(v))
        elif isinstance(v, str) and v.strip().isdigit():
            vals.add(v.strip())

    for v in (pack.get("counts") or {}).values():
        add(v)
    for key in ("country_distribution_7d", "category_distribution_24h",
                "source_tier_distribution_7d"):
        for row in (pack.get(key) or []):
            add((row or {}).get("count"))
    for key in ("countries_24h", "countries_7d", "top_verified_events", "top_signals", "health"):
        add(len(pack.get(key) or []))
    add(pack.get("fact_count"))
    return vals


def sanitize_china_impact(brief, pack):
    """C7-6R4 FIX C：涉华条目的证据稳定性（不放宽事实门）。

    规则（确定性、AI 之后、门之前）：
      1) 只保留 country 合法且 fact_refs 非空且**全部可在事实包中解析**的条目；
      2) 无支撑的条目直接**丢弃**（绝不发布不支持条目）；
      3）过滤后若已无任何受支撑条目 → items=[]，并把摘要改为诚实口径，
         同时清掉任何"直接涉及"式断言（保守，避免虚假涉华声称）。
    返回 (brief, dropped_count)。
    """
    ci = brief.get("china_impact") or {}
    if not isinstance(ci, dict):
        brief["china_impact"] = {"overall_level": "none", "summary_cn": "", "items": []}
        return brief, 0
    ids = set((pack.get("facts") or {}).keys())
    cset = {str(x) for x in (pack.get("countries_7d") or [])}
    cset |= {str(x) for x in (pack.get("countries_24h") or [])}
    kept, dropped = [], 0
    for it in (ci.get("items") or []):
        refs = [str(r) for r in (it.get("fact_refs") or [])]
        if str(it.get("country") or "") in cset and refs and all(r in ids for r in refs):
            kept.append(it)
        else:
            dropped += 1
    ci["items"] = kept
    if not kept:
        ci["overall_level"] = "none"
        ci["summary_cn"] = ("过去24小时未发现有充分公开证据支持的直接涉华重大安全事件。")
        if re.search(r"直接涉及|中资企业遭|中国公民遇袭|中企遭|中国企业遭", str(ci.get("analysis_cn") or "")):
            ci["analysis_cn"] = ""
    brief["china_impact"] = ci
    return brief, dropped


def fact_gate(brief, pack):
    errs = []
    oa = brief.get("overall_assessment") or {}
    for k in ("summary_cn", "risk_direction", "confidence", "key_judgments", "watch_24_72h"):
        if k not in oa:
            errs.append("overall_assessment 缺 %s" % k)
    if oa.get("risk_direction") not in ("improving", "stable", "worsening"):
        errs.append("risk_direction 非法")
    if oa.get("confidence") not in ("high", "medium", "low"):
        errs.append("confidence 非法")
    cjk = len(re.findall(r"[\u4e00-\u9fff]", str(oa.get("summary_cn") or "")))
    if not (300 <= cjk <= 1100):
        errs.append("summary_cn 汉字数 %d 越界（产品目标 450–700）" % cjk)
    body_txt = json.dumps(brief, ensure_ascii=False)
    for bad in BANNED_IN_PROSE:
        if bad in body_txt:
            errs.append("正文出现系统/工程语言：%s" % bad)
    for m in SYSTEM_COUNT_PHRASES.finditer(body_txt):
        errs.append("正文出现条目计数式表述：%s" % m.group(0))
    secs = brief.get("sectors") or {}
    for s in SECTORS:
        if s not in secs:
            errs.append("sectors 缺 %s" % s)
        elif (secs[s] or {}).get("trend") not in ("up", "flat", "down"):
            errs.append("sectors.%s.trend 非法" % s)
    ids = set(pack.get("facts") or {})
    cset = set(pack.get("countries_7d") or []) | {"未识别"}
    for t in (brief.get("top_developments") or []):
        if str(t.get("fact_id") or "") not in ids:
            errs.append("top_developments 引用不存在的 fact %r" % t.get("fact_id"))
    ci = brief.get("china_impact") or {}
    for it in (ci.get("items") or []):
        if str(it.get("country") or "") not in cset:
            errs.append("china_impact 引用未知国家 %r" % it.get("country"))
        for r in (it.get("fact_refs") or []):
            if str(r) not in ids:
                errs.append("china_impact.fact_refs 未解析 %r" % r)
        if not (it.get("fact_refs") or []):
            errs.append("china_impact 条目缺少支撑 fact_refs")
    if ci.get("overall_level") not in ("none", "low", "medium", "high"):
        errs.append("china_impact.overall_level 非法")
    hs = brief.get("health_security") or {}
    if not pack.get("health") and (hs.get("key_issues") or []):
        errs.append("health 数据为空但给出 key_issues")
    for r in (brief.get("source_fact_refs") or [])[:50]:
        if str(r) not in ids:
            errs.append("source_fact_refs 未解析 %r" % r)
    # 允许集合 = 事实包 counts 的**全部**计数 + 7 日国家数 + 事实总数。
    # 说明：放宽的是"AI 可以引用的计数白名单"（数字仍必须等于事实包算出的值），
    # 不是放宽反幻觉规则本身。此前该集合漏掉 countries_with_activity_24h /
    # total_countries_monitored，导致真实简报因「1个国家」被误判越界
    # （C7-5 生产实测 status=FACT_GATE_FAIL、gate_errors=["数字主张 1个国家 不在允许集合"]）。
    allowed = _numeric_allowlist(pack)
    for m in NUM_UNITS.finditer(str(oa.get("summary_cn") or "")):
        if m.group(1) not in allowed:
            errs.append("数字主张 %s 不在允许集合" % m.group(0))
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description="C7-5 首页事实包 + AI 简报")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--fact-pack-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="忽略 6h 节奏与 hash 缓存")
    args = ap.parse_args(argv)
    root = Path(args.root)
    now = datetime.now(BJT)

    pack = build_fact_pack(root, now)
    write_atomic(root / PACK, pack)
    stable = json.dumps({k: pack[k] for k in pack if k != "generated_at"},
                        ensure_ascii=False, sort_keys=True)
    ih = hashlib.sha256(stable.encode("utf-8")).hexdigest()

    if args.fact_pack_only:
        print(json.dumps({"mode": "fact-pack-only", "counts": pack["counts"],
                          "fact_count": pack["fact_count"], "input_hash": ih[:12],
                          "real_ai_calls": 0}, ensure_ascii=False, indent=1))
        return 0

    out_dir = root / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    latest = None
    try:
        cands = sorted(out_dir.glob("*.json"))
        if cands:
            latest = json.loads(cands[-1].read_text(encoding="utf-8"))
    except Exception:
        latest = None
    if latest and not args.force:
        prev_t = parse_time(latest.get("generated_time"))
        same_gate = latest.get("gate_version") == GATE_VERSION
        # 节奏（≤6h 一次）按"上一次**尝试**"计（不论成功/失败）：失败时若不计节奏，
        # 编排器每小时都会重试（生产实测 00–09 BJT 连续 10 次 AI 调用）。
        if same_gate and prev_t and (now - prev_t) < timedelta(hours=CADENCE_HOURS):
            print(json.dumps({"status": "skipped_cadence", "input_hash": ih[:12],
                              "prev_status": latest.get("status"),
                              "real_ai_calls": 0}, ensure_ascii=False))
            return 0
        if same_gate and latest.get("input_hash") == ih and latest.get("status") == "ok":
            print(json.dumps({"status": "skipped_same_input", "input_hash": ih[:12],
                              "real_ai_calls": 0}, ensure_ascii=False))
            return 0

    if args.dry_run:
        print(json.dumps({"mode": "dry-run", "counts": pack["counts"], "input_hash": ih[:12]},
                         ensure_ascii=False, indent=1))
        return 0

    try:
        for _p in (str(root), str(root / "scripts"), str(root / "scripts" / "data")):
            if _p not in sys.path:
                sys.path.insert(0, _p)
        from scripts.ai.safety import manual_trial as mt  # noqa: E402
        prov = mt._flash_provider()
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"status": "PROVIDER_IMPORT_FAIL", "error": str(e)[:200],
                          "real_ai_calls": 0}, ensure_ascii=False))
        return 0

    slim = {k: pack[k] for k in ("schema", "generated_at", "windows", "counts", "countries_24h",
                                 "countries_7d", "country_distribution_7d",
                                 "category_distribution_24h", "source_tier_distribution_7d",
                                 "top_verified_events", "top_signals", "health")}
    task = {"task_id": "homepage-brief-%s" % now.strftime("%Y%m%d%H"),
            "task_type": "homepage_brief", "system_text": SYSTEM,
            "user_text": USER_TMPL % json.dumps(slim, ensure_ascii=False, indent=1),
            "max_output_tokens": 6000}
    t0 = time.time()
    rec = prov.submit_task(task)
    calls = 1
    # provider 的用量在 rec["tokens"]（见 manual_trial 记录形状）；取不到时记 null，
    # 不写 0（0 会被误读成"零消耗"）。此前读顶层 total_tokens 恒为 0。
    usage = rec.get("tokens") or {}
    tokens = usage.get("total_tokens") if isinstance(usage.get("total_tokens"), int) else None
    base = {"generated_time": now.isoformat(timespec="seconds"),
            "input_hash": ih, "gate_version": GATE_VERSION,
            "counts": pack["counts"], "ai_calls": calls,
            "total_tokens": tokens, "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "runtime_s": round(time.time() - t0, 1),
            "provider": "deepseek", "model": rec.get("returned_model"),
            "provider_status": rec.get("provider_status"),
            "status": rec.get("status") or "failed"}
    if rec.get("status") != "succeeded":
        base["status"] = "AI_%s" % rec.get("status")
        write_atomic(out_dir / ("%s.json" % now.strftime("%Y%m%d%H")), base)
        print(json.dumps({"status": base["status"], "real_ai_calls": calls}, ensure_ascii=False))
        return 0
    text = (rec.get("result") or {}).get("text") or ""
    m, n = text.find("{"), text.rfind("}")
    brief = None
    if 0 <= m < n:
        try:
            brief = json.loads(text[m:n + 1])
        except ValueError:
            brief = None
    if not isinstance(brief, dict):
        base["status"] = "AI_JSON_INVALID"
        write_atomic(out_dir / ("%s.json" % now.strftime("%Y%m%d%H")), base)
        print(json.dumps({"status": base["status"], "real_ai_calls": calls}, ensure_ascii=False))
        return 0
    # C7-6R4 FIX C：先做涉华证据稳定性后处理（丢弃无支撑条目），再跑事实门。
    brief, dropped_cn = sanitize_china_impact(brief, pack)
    errs = fact_gate(brief, pack)
    base.update(brief)
    base["dropped_china_items"] = dropped_cn
    base["status"] = "ok" if not errs else "FACT_GATE_FAIL"
    base["gate_errors"] = errs
    write_atomic(out_dir / ("%s.json" % now.strftime("%Y%m%d%H")), base)
    print(json.dumps({"status": base["status"], "real_ai_calls": calls, "total_tokens": tokens,
                      "model": base["model"], "gate_errors": errs[:4]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
