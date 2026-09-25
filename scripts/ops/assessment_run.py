#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP C7-3 — 每日安全态势研判（事实包 → 真实 AI → 事实门 → 研判工件）。

P4  事实包（确定性，REAL_AI_CALLS=0）：
    data/runtime/ops/reports/daily_assessment_fact_pack.json
    同时覆盖两类情报：VERIFIED EVENTS（公开已核实事件）与
    NEWS / INTELLIGENCE SIGNALS（文章级情报信号，允许单源）。
P5  每日一次真实 AI 研判：data/intelligence/ai/assessment/daily/<YYYYMMDD>.json
    同 input_hash 不重复调用（0 次重复 AI）。
P6  事实门（fail-closed）：结构 / 枚举 / 国家名 / fact 引用 / 数字主张
    全部机器校验；不过门 → 工件 status=FACT_GATE_FAIL（首页自动回落确定性摘要）。

铁律：AI 必须区分 VERIFIED EVENTS 与 NEWS SIGNALS，不得把单源信号写成既定事实。
用法：
  python scripts/ops/assessment_run.py --fact-pack-only   # 只产事实包（无 AI）
  python scripts/ops/assessment_run.py                    # 事实包 +（到期才）AI 研判
  python scripts/ops/assessment_run.py --dry-run          # 只输出计划
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BJT = timezone(timedelta(hours=8))
PACK = Path("data") / "runtime" / "ops" / "reports" / "daily_assessment_fact_pack.json"
ASSESS_DIR = Path("data") / "intelligence" / "ai" / "assessment" / "daily"
HIGH_SEV = {"high", "critical"}

SYSTEM = (
    "你是 ASIP 平台的首席安全分析师，为机构领导撰写每日非洲安全态势研判。"
    "你只会收到一份结构化事实包（fact pack），其中每个条目都标注了情报层级：\n"
    "  - VERIFIED EVENT：已通过多来源交叉核实的公开事件；\n"
    "  - NEWS SIGNAL：文章级情报信号，可能是单源，尚未核实。\n"
    "硬性规则：\n"
    "1) 只允许使用事实包中的信息，禁止引入任何包外事实、数字、国家或来源；\n"
    "2) 必须区分两类情报：NEWS SIGNAL 只能以『情报信号/单源消息，尚待核实』的"
    "口径表述，绝不能写成已确立的事实；\n"
    "3) 不做无依据的预测；watch_items 只列需要继续监测的事项；\n"
    "4) overall_assessment 为简洁的中文决策层摘要（150–350 个汉字）；\n"
    "5) 输出必须是单个严格 JSON 对象，不得包含任何解释文字或 Markdown。")

USER_TMPL = """事实包（JSON，唯一信息来源）如下：

%s

请输出一个 JSON 对象，字段如下：
{{
  "overall_assessment": "≤350个汉字的执行层中文摘要；必须先讲已核实事件，再讲情报信号（并明确标注哪些是单源信号）",
  "key_regions": [{{"country": "<国家中文名，必须来自事实包的 countries 列表>", "direction": "up|flat|down", "note": "≤60字"}}],
  "major_trends": ["≤80字", "..."],
  "risk_direction": "improving|stable|worsening",
  "watch_items": ["需要继续监测的具体事项，≤60字"],
  "confidence": "high|medium|low",
  "source_fact_refs": ["从事实包 facts 中原样引用的 fact id，≥3 条"]
}}
要求：key_regions 3–5 条；major_trends 3–5 条；watch_items 2–4 条；
source_fact_refs 必须真实存在于事实包。只输出 JSON。"""

NUM_UNITS = re.compile(r"(\d+)\s*(?:起|个国家|个事件|个来源|条)")


def parse_time(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=BJT)
    except ValueError:
        return None


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def write_atomic(path, obj):
    path = Path(path)
    import os
    import tempfile
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


def dist(rows, field, n=8):
    return [{"value": k, "count": v} for k, v in
            Counter(str(r.get(field) or "未分类") for r in rows).most_common(n)]


def build_fact_pack(root, now):
    data = Path(root) / "data"
    pub = (load_json(data / "public" / "published_events.json", {}) or {}).get("items") or []
    feed = (load_json(data / "views" / "news_stream.json", {}) or {}).get("items") or []
    countries = (load_json(data / "countries.json", {}) or {}).get("countries") \
        or (load_json(data / "countries.json", {}) or {}).get("items") or []
    prev = load_json(data / ASSESS_DIR.parent.parent / "ai" / "assessment" / "daily"
                     / "_latest_pointer.json", {}) or {}

    h24, d7 = now - timedelta(hours=24), now - timedelta(days=7)
    ev, sig = [], []
    for e in pub:
        t = parse_time(e.get("published_time") or e.get("event_time"))
        if t and t >= d7:
            ev.append((e, t))
    for s in feed:
        if s.get("quarantined"):
            continue
        t = parse_time(s.get("last_seen_at") or s.get("observed_at"))
        if t and t >= d7:
            sig.append((s, t))

    def metrics(rows):
        return {"count": len(rows),
                "active_countries": len({str(r.get("country_cn") or r.get("country_cn") or "未识别")
                                         for r, _ in rows})}
    ev24 = [(e, t) for e, t in ev if t >= h24]
    sg24 = [(s, t) for s, t in sig if t >= h24]

    facts, countries_set = [], set()
    for e, t in ev:
        fid = str(e.get("event_id") or "")
        countries_set.add(str(e.get("country_cn") or "未识别"))
        facts.append({"fact_id": fid, "level": "verified_event",
                      "country": e.get("country_cn") or "未识别",
                      "title": (e.get("title_cn") or e.get("title_original") or "")[:120],
                      "time": t.strftime("%Y-%m-%d %H:%M"),
                      "severity": e.get("event_severity") or "",
                      "source_count": int(e.get("independent_source_count") or 0)})
    for s, t in sig[:60]:
        fid = "news:%s" % hashlib.sha256(str(s.get("dedup_key") or s.get("news_id") or
                                              s.get("src_id") or "").encode()).hexdigest()[:16]
        countries_set.add(str(s.get("country_cn") or "未识别"))
        facts.append({"fact_id": fid, "level": "news_signal",
                      "country": s.get("country_cn") or "未识别",
                      "title": ((s.get("title_cn") or s.get("title_original") or ""))[:120],
                      "time": t.strftime("%Y-%m-%d %H:%M"),
                      "severity": "", "source_count": int(s.get("independent_source_count") or 0)})

    top_ev = [f for f in facts if f["level"] == "verified_event"][:5]
    top_sg = [f for f in facts if f["level"] == "news_signal"][:8]
    pack = {
        "schema": "daily-assessment-fact-pack-v1",
        "report_date": now.strftime("%Y-%m-%d"),
        "generated_at": now.isoformat(timespec="seconds"),
        "metrics": {
            "24h": {"verified_events": len(ev24), "news_signals": len(sg24),
                    "articles_24h": len(sg24), "active_countries": len(
                        {str(e.get("country_cn") or "未识别") for e, _ in ev24} |
                        {str(s.get("country_cn") or "未识别") for s, _ in sg24})},
            "7d": {"verified_events": len(ev), "news_signals": len(sig),
                   "articles_7d": len(sig),
                   "active_countries": len(countries_set),
                   "total_countries": len(countries)},
            "country_distribution_7d": [{"country": k, "count": v} for k, v in
                                         Counter(str(e.get("country_cn") or "未识别")
                                                 for e, _ in ev).most_common(10)],
            "category_distribution_7d": dist([e for e, _ in ev], "event_type"),
            "source_distribution_7d": dist([s for s, _ in sig], "source_name"),
        },
        "top_verified_events": top_ev,
        "top_intelligence_signals": top_sg,
        "countries": sorted(countries_set - {"未识别"}),
        "fact_count": len(facts),
        "previous_assessment_digest": prev.get("digest") or prev.get("input_hash") or None,
        "facts": facts,
    }
    return pack


def fact_gate(ass, pack):
    errs = []
    for k in ("overall_assessment", "key_regions", "major_trends", "risk_direction",
              "watch_items", "confidence", "source_fact_refs"):
        if k not in ass:
            errs.append("缺少字段 %s" % k)
    if errs:
        return errs
    if not isinstance(ass["key_regions"], list) or not (3 <= len(ass["key_regions"]) <= 5):
        errs.append("key_regions 必须 3–5 条")
    if not isinstance(ass["major_trends"], list) or not (2 <= len(ass["major_trends"]) <= 5):
        errs.append("major_trends 必须 2–5 条")
    if ass["risk_direction"] not in ("improving", "stable", "worsening"):
        errs.append("risk_direction 非法")
    if ass["confidence"] not in ("high", "medium", "low"):
        errs.append("confidence 非法")
    if not isinstance(ass["watch_items"], list) or not ass["watch_items"]:
        errs.append("watch_items 为空")
    cjk = len(re.findall(r"[\u4e00-\u9fff]", str(ass["overall_assessment"])))
    if not (60 <= cjk <= 500):
        errs.append("overall_assessment 汉字数 %d 超界" % cjk)
    okc = set(pack.get("countries") or [])
    for kr in ass["key_regions"]:
        if str(kr.get("country") or "") not in okc:
            errs.append("key_regions 引用未知国家 %r" % (kr.get("country"),))
    pack_ids = {f["fact_id"] for f in pack.get("facts") or []}
    for rid in (ass.get("source_fact_refs") or []):
        if str(rid) not in pack_ids:
            errs.append("source_fact_refs 引用不存在的 fact %r" % (rid,))
    allowed = {str(v) for blk in (pack.get("metrics") or {}).values()
               for v in ([blk] if isinstance(blk, int) else
                         ([blk["count"]] if isinstance(blk, dict) and "count" in blk else
                          [x.get("count") for x in blk] if isinstance(blk, list) else []))
               if isinstance(v, int)}
    allowed |= {pack.get("fact_count"), len(pack.get("countries") or [])}
    for m in NUM_UNITS.finditer(str(ass["overall_assessment"])):
        if m.group(1) not in {str(x) for x in allowed if x is not None}:
            errs.append("数字主张 %s 不在事实包允许集合" % m.group(0))
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description="ASIP C7-3 每日安全态势研判")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--fact-pack-only", action="store_true", help="只产事实包（无 AI）")
    ap.add_argument("--dry-run", action="store_true", help="只输出计划")
    ap.add_argument("--force", action="store_true", help="忽略同 hash 缓存")
    args = ap.parse_args(argv)

    root = Path(args.root)
    now = datetime.now(BJT)
    pack = build_fact_pack(root, now)
    write_atomic(root / PACK, pack)
    stable = json.dumps({k: pack[k] for k in pack if k not in ("generated_at",)},
                        ensure_ascii=False, sort_keys=True)
    input_hash = hashlib.sha256(stable.encode("utf-8")).hexdigest()
    date_key = now.strftime("%Y%m%d")

    if args.fact_pack_only:
        print(json.dumps({"mode": "fact-pack-only", "fact_count": pack["fact_count"],
                          "metrics": pack["metrics"], "input_hash": input_hash[:12],
                          "real_ai_calls": 0}, ensure_ascii=False, indent=1))
        return 0

    out_dir = root / ASSESS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / ("%s.json" % date_key)
    prev_art = load_json(out_path, {}) or {}
    if (not args.force and prev_art.get("status") == "ok"
            and prev_art.get("input_hash") == input_hash):
        print(json.dumps({"status": "skipped_same_input", "date": date_key,
                          "input_hash": input_hash[:12], "real_ai_calls": 0},
                         ensure_ascii=False))
        return 0

    plan = {"mode": "dry-run" if args.dry_run else "assess", "date": date_key,
            "fact_count": pack["fact_count"], "input_hash": input_hash[:12],
            "previous_status": prev_art.get("status") or "none"}
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=1))
        return 0

    try:
        # 与 enrichment_run 相同的双路径导入约定（scripts.ai 需要仓库根在路径上）
        for _p in (str(root), str(root / "scripts"), str(root / "scripts" / "data")):
            if _p not in sys.path:
                sys.path.insert(0, _p)
        from scripts.ai.safety import manual_trial as mt  # noqa: E402
        prov = mt._flash_provider()
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"status": "PROVIDER_IMPORT_FAIL", "error": str(e)[:200],
                          "real_ai_calls": 0}, ensure_ascii=False))
        return 0

    slim = {k: pack[k] for k in pack if k != "facts"}
    slim["facts"] = pack["facts"][:80]
    user = USER_TMPL % json.dumps(slim, ensure_ascii=False, indent=1)
    task = {"task_id": "daily-assessment-%s" % date_key,
            "task_type": "daily_assessment",
            "system_text": SYSTEM, "user_text": user, "max_output_tokens": 4000}
    rec = prov.submit_task(task)
    calls = 1
    tokens = rec.get("total_tokens") if isinstance(rec.get("total_tokens"), int) else 0
    base = {"date": date_key, "generated_time": now.isoformat(timespec="seconds"),
            "input_hash": input_hash, "fact_count": pack["fact_count"],
            "ai_calls": calls, "total_tokens": tokens,
            "provider": "deepseek", "model": rec.get("returned_model"),
            "provider_status": rec.get("provider_status"),
            "source_fact_refs": [], "key_regions": [], "major_trends": [],
            "watch_items": [], "overall_assessment": "", "risk_direction": "",
            "confidence": "", "status": rec.get("status") or "failed"}
    if rec.get("status") != "succeeded":
        base["status"] = "AI_%s" % rec.get("status")
        write_atomic(out_path, base)
        print(json.dumps({"status": base["status"], "real_ai_calls": calls},
                         ensure_ascii=False))
        return 0
    text = (rec.get("result") or {}).get("text") or ""
    m, n = text.find("{"), text.rfind("}")
    ass = None
    if 0 <= m < n:
        try:
            ass = json.loads(text[m:n + 1])
        except ValueError:
            ass = None
    if not isinstance(ass, dict):
        base["status"] = "AI_JSON_INVALID"
        write_atomic(out_path, base)
        print(json.dumps({"status": base["status"], "real_ai_calls": calls},
                         ensure_ascii=False))
        return 0
    for k in ("overall_assessment", "key_regions", "major_trends", "risk_direction",
              "watch_items", "confidence", "source_fact_refs"):
        if k in ass:
            base[k] = ass[k]
    errs = fact_gate(ass, pack)
    base["status"] = "ok" if not errs else "FACT_GATE_FAIL"
    base["gate_errors"] = errs
    write_atomic(out_path, base)
    print(json.dumps({"status": base["status"], "real_ai_calls": calls,
                      "total_tokens": tokens, "model": base["model"],
                      "gate_errors": errs[:4], "artifact": str(out_path)},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
