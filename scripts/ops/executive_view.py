#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP C7-1 — Executive Intelligence Dashboard 数据层（确定性，无 AI 调用）。

职责（单一）：
  只读既有四类数据源，组装 `data/views/executive_summary.json`（领导 30 秒视图的单一数据源）：
    - data/public/published_events.json   → 24h/7d 计数、活跃国家、top_events
    - data/canonical/articles.json        → latest_intelligence（最新安全相关情报）
    - data/canonical/event_clusters.json  → country_code → country_cn 映射、severity/source_count 补全
    - data/views/ai_intelligence.json     → 可选 ai_assessment 文字（原样引用，注明来源）

铁律：
  - **确定性**：全部文字由事实模板生成，无任何 AI 调用（REAL_AI_CALLS=0）；
  - **只读**：不改 canonical / public / 实体 / 关系 / 图谱 / 疾病；
  - 诚实态：无记录 ≠ 安全（LOW_DATA/无事件国家不显示积极信号）；
  - 时间语义：事件 `event_time` 为北京时间 naive 串（与采集侧一致），统一按 BJT 解析；
  - 默认 dry-run，`--apply` 才写盘；写盘前先过 schema 校验（自研 validate_instance）。

用法：
  python scripts/ops/executive_view.py                 # dry-run
  python scripts/ops/executive_view.py --apply         # 写 data/views/executive_summary.json
  python scripts/ops/executive_view.py --apply --now 2026-09-24T05:00:00+08:00
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BJT = timezone(timedelta(hours=8))
SCHEMA_NAME = "executive_summary.schema.json"
OUT_REL = Path("data") / "views" / "executive_summary.json"
SOURCES_USED = [
    "data/public/published_events.json",
    "data/canonical/articles.json",
    "data/canonical/event_clusters.json",
    "data/views/ai_intelligence.json",
]
SEVERITY_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}
HIGH_SEVERITY = {"high", "critical"}
TOP_EVENTS_MAX = 5
INTEL_MAX = 8
KEY_REGIONS_MAX = 5


def parse_time(s, assume_bj=True):
    """兼容 RFC3339 与采集侧 naive 'YYYY-MM-DD HH:MM:SS'（按北京时间解析）。"""
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=BJT)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=BJT) if assume_bj else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def items_of(doc, *keys):
    if not isinstance(doc, dict):
        return []
    for k in keys:
        v = doc.get(k)
        if isinstance(v, list):
            return v
    return []


def cn_map(clusters):
    """country_code/country -> country_cn（来自 canonical，确定性）。"""
    m = {}
    for c in clusters:
        code = str(c.get("country_code") or c.get("country") or "").strip()
        cn = str(c.get("country_cn") or "").strip()
        if code and cn:
            m[code] = cn
        prim = str(c.get("primary_country") or "").strip()
        if prim and cn:
            m[prim] = cn
    return m


def country_cn(raw, mapping):
    s = str(raw or "").strip()
    if not s:
        return "未识别"
    if s in mapping:
        return mapping[s]
    if any("\u4e00" <= ch <= "\u9fff" for ch in s):
        return s
    return s


def build(root, now):
    root = Path(root)
    data = root / "data"
    pub = load_json(data / "public" / "published_events.json", {})
    clusters = items_of(load_json(data / "canonical" / "event_clusters.json", {}), "items")
    articles = items_of(load_json(data / "canonical" / "articles.json", {}), "items")
    ai = load_json(data / "views" / "ai_intelligence.json", {})
    total_countries = len(items_of(load_json(data / "countries.json", {}), "countries", "items"))

    mapping = cn_map(clusters)
    pub_items = items_of(pub, "items", "events")
    h24, d7 = now - timedelta(hours=24), now - timedelta(days=7)

    ev_24, ev_7, c24, c7 = [], [], set(), set()
    for e in pub_items:
        t = parse_time(e.get("published_time") or e.get("event_time"))
        if t is None:
            continue
        if t >= h24:
            ev_24.append((e, t))
            c24.add(e.get("country_cn") or e.get("country"))
        if t >= d7:
            ev_7.append((e, t))
            c7.add(e.get("country_cn") or e.get("country"))
    ev_24.sort(key=lambda x: x[1], reverse=True)
    ev_7.sort(key=lambda x: x[1], reverse=True)

    # ---- key_regions：按 7d 事件量取 Top N，方向由 24h 占比确定性推导 ----
    by_c = {}
    for e, t in ev_7:
        k = e.get("country_cn") or e.get("country") or "未识别"
        d = by_c.setdefault(k, {"events_24h": 0, "events_7d": 0, "sev_high": 0})
        d["events_7d"] += 1
        if t >= h24:
            d["events_24h"] += 1
        if str(e.get("event_severity") or "").lower() in HIGH_SEVERITY:
            d["sev_high"] += 1
    key_regions = []
    for name, d in sorted(by_c.items(), key=lambda kv: (-kv[1]["events_7d"], kv[0]))[:KEY_REGIONS_MAX]:
        direction = "up" if d["events_24h"] >= 2 else ("flat" if d["events_24h"] == 1 else "down")
        note = "7日 %d 起，24h %d 起" % (d["events_7d"], d["events_24h"])
        if d["sev_high"]:
            note += "，含高严重度 %d 起" % d["sev_high"]
        key_regions.append({"country": name, "events_24h": d["events_24h"],
                            "events_7d": d["events_7d"], "direction": direction, "note": note})

    # ---- top_events：7d 内按 (severity, 来源数, 时间) 取 Top 5 ----
    def sev_rank(e):
        return SEVERITY_RANK.get(str(e.get("event_severity") or "").lower(), 0)

    cands = sorted(ev_7, key=lambda x: (sev_rank(x[0]), x[0].get("independent_source_count") or 0,
                                        x[1]), reverse=True)[:TOP_EVENTS_MAX]
    top_events = []
    for e, t in cands:
        title = str(e.get("title_cn") or "").strip() or str(e.get("title_original") or "").strip()
        summ = str(e.get("summary_cn") or "").strip() or str(e.get("summary_original") or "").strip()
        top_events.append({
            "country": e.get("country_cn") or e.get("country") or "未识别",
            "title": title[:120],
            "summary": summ[:180],
            "time": t.strftime("%Y-%m-%d %H:%M"),
            "source_count": int(e.get("independent_source_count") or 0),
            "event_id": e.get("event_id") or "",
            "severity": str(e.get("event_severity") or ""),
        })

    # ---- latest_intelligence：最新安全相关文章（文章层，事件层之外的体量来源）----
    arts = []
    for a in articles:
        if a.get("is_security_relevant") is not True:
            continue
        t = parse_time(a.get("published_at") or a.get("retrieved_at"))
        if t is None:
            continue
        arts.append((a, t))
    arts.sort(key=lambda x: x[1], reverse=True)
    latest = []
    for a, t in arts[:INTEL_MAX]:
        tcn = str(a.get("title_cn") or "").strip()
        latest.append({
            "title": (tcn or str(a.get("title_original") or "").strip())[:120],
            "country": country_cn(a.get("event_country") or a.get("detected_country"), mapping),
            "source": str(a.get("source_name") or "").strip() or "未知来源",
            "time": t.strftime("%Y-%m-%d %H:%M"),
            "security_category": str(a.get("event_type") or "").strip() or "未分类",
            "article_id": str(a.get("article_id") or "").strip(),
            "translated": bool(tcn),
        })

    # ---- 确定性评估文字（无 AI）----
    parts = ["过去24小时共记录 %d 起安全事件，涉及 %d 个国家；近7日 %d 起、%d 个国家。"
             % (len(ev_24), len(c24), len(ev_7), len(c7))]
    if key_regions:
        parts.append("事件量居前：%s。" % "、".join(
            "%s %d 起/7日" % (r["country"], r["events_7d"]) for r in key_regions[:3]))
    high24 = sum(1 for e, _ in ev_24 if str(e.get("event_severity") or "").lower() in HIGH_SEVERITY)
    if len(ev_24) == 0:
        parts.append("过去24小时无新增公开事件记录；无记录不等于无风险。")
    elif high24:
        parts.append("其中高严重度 %d 起，需重点关注。" % high24)
    else:
        parts.append("过去24小时无高严重度公开事件。")
    silent = max(0, total_countries - len(c7))
    if silent:
        parts.append("另有 %d 个在册国家近7日无公开事件记录（无记录不等于无风险）。" % silent)
    overall = "".join(parts)

    risk_direction = "worsening" if high24 else "stable"
    confidence = "medium" if (len(ev_24) >= 3 and len(c24) >= 2) else "low"

    ai_home = (ai.get("homepage") or {}) if isinstance(ai, dict) else {}
    ai_text = ""
    if str(ai_home.get("status") or "").lower() == "ok":
        ai_text = str(ai_home.get("executive_assessment") or "").strip()

    doc = {
        "schema": "executive-summary-v1",
        "generated_time": now.astimezone(BJT).isoformat(timespec="seconds"),
        "period": {
            "data_as_of": None,  # 本包不引入第二时间源；C7-3 将从 time_contract 注入
            "events_24h": len(ev_24),
            "events_7d": len(ev_7),
            "active_countries_24h": len(c24),
            "active_countries_7d": len(c7),
            "total_countries": total_countries,
            "articles_7d": sum(1 for _, t in arts if t >= d7),
        },
        "overall_assessment": overall,
        "risk_direction": risk_direction,
        "confidence": confidence,
        "key_regions": key_regions,
        "top_events": top_events,
        "latest_intelligence": latest,
        "sources_used": list(SOURCES_USED),
    }
    if ai_text:
        doc["ai_assessment"] = ai_text[:400]
    return doc


def validate_doc(doc, root=None):
    # schema 校验用的是**本仓库**的 schemas/ 与校验器，与数据 root 无关
    for _p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "scripts" / "data")):
        if _p not in sys.path:
            sys.path.insert(0, _p)
    from data.schema_validator import load_schema, validate_instance  # noqa: E402
    schema = load_schema(SCHEMA_NAME)
    return validate_instance(doc, schema)


def write_atomic(doc, path):
    import os
    import tempfile
    d = os.path.dirname(str(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".executive_summary.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description="ASIP C7-1 — Executive Intelligence 数据层（确定性）")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--apply", action="store_true", help="写盘（默认 dry-run）")
    ap.add_argument("--now", default=None, help="测试用 BJT now（ISO）")
    args = ap.parse_args(argv)

    now = datetime.fromisoformat(args.now).astimezone(BJT) if args.now else datetime.now(BJT)
    doc = build(args.root, now)
    errs = validate_doc(doc)
    out = {
        "mode": "apply" if args.apply else "dry-run",
        "out_path": str(Path(args.root) / OUT_REL),
        "real_ai_calls": 0,
        "schema_errors": len(errs),
        "schema_error_sample": errs[:3],
        "period": doc["period"],
        "risk_direction": doc["risk_direction"],
        "confidence": doc["confidence"],
        "key_regions": len(doc["key_regions"]),
        "top_events": len(doc["top_events"]),
        "latest_intelligence": len(doc["latest_intelligence"]),
        "overall_assessment": doc["overall_assessment"],
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if errs:
        print("  ✗ 阻断：schema 校验未通过，未写盘", file=sys.stderr)
        return 2
    if args.apply:
        write_atomic(doc, Path(args.root) / OUT_REL)
        out["written"] = True
        print(json.dumps({"written": True, "path": out["out_path"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
