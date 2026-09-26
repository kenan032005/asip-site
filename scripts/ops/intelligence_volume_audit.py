"""C8-1 PHASE 1-3：24h 情报量漏斗审计（只读诊断，不修改任何采集行为）。

数据来源（全部为既有运行时工件，不新建 truth store）：
  data/runtime/ops/collection_summary.json      —— 最近一轮采集汇总 + failure_reasons
  data/runtime/ops/collection_source_stats.json —— 118 个源的逐源台账
  data/runtime/ops/collection_rotation.json     —— 轮换偏移
  data/runtime/ops/source_health.json           —— 源健康（last_fetch/candidate_count/parser_failures）
  data/runtime/ops/time_contract.json           —— data_as_of
  data/sources.json                             —— 源配置（tier/role/country/enabled）
  data/views/news_stream.json                   —— C1A 情报流（信号层）

输出：
  data/runtime/ops/intelligence_volume_audit.json
  reports/ops/C8_1_24H_VOLUME_AUDIT.md
  （可选 stdout 摘要）

口径说明（诚实标注）：
  · 逐源台账为**最近一轮**采集；24h 视窗指标由 news_stream 的 last_seen_at 派生。
  · "публиш/published"= 通过采集侧闸门并写入 Article Store 的条数（单轮）。
"""
import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BJT = timezone(timedelta(hours=8))
OPS = Path("data") / "runtime" / "ops"
OUT_JSON = OPS / "intelligence_volume_audit.json"
OUT_MD = Path("reports") / "ops" / "C8_1_24H_VOLUME_AUDIT.md"

# 与 collectors/failure_reasons.py 的 14 类对齐（此处按审计所需归并，不新增枚举）
LOSS_KEYS = ["HTTP_403", "HTTP_404", "HTTP_429", "TIMEOUT", "PARSE_ERROR", "RSS_EMPTY",
             "NO_ITEMS", "DATE_PARSE_FAIL", "OUTSIDE_24H", "COUNTRY_UNRESOLVED", "NOT_AFRICA",
             "SECURITY_FILTER_REJECT", "DUPLICATE_EXACT", "DUPLICATE_CLUSTER",
             "LOCALIZATION_PENDING", "PUBLICATION_FILTER", "OTHER"]


def load(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def parse_t(s):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def classify(ok_http, discovered, published, reason):
    if not ok_http:
        r = (reason or "").upper()
        if "403" in r or "BLOCKED" in r or "ACCESS" in r:
            return "ACCESS_LIMITED"
        return "BROKEN"
    if published >= 3 or discovered >= 15:
        return "HIGH_YIELD"
    if published >= 1 or discovered >= 5:
        return "MEDIUM_YIELD"
    if discovered >= 1:
        return "LOW_YIELD"
    return "ZERO_YIELD"


def audit(root):
    root = Path(root)
    cs = load(root / OPS / "collection_summary.json", {}) or {}
    ss = load(root / OPS / "collection_source_stats.json", {}) or {}
    rot = load(root / OPS / "collection_rotation.json", {}) or {}
    health = load(root / OPS / "source_health.json", {}) or {}
    tc = load(root / OPS / "time_contract.json", {}) or {}
    conf = (load(root / "data" / "sources.json", {}) or {}).get("sources") or []
    ns = load(root / "data" / "views" / "news_stream.json", {}) or {}
    feed = ns.get("items") or []
    ev = load(root / "data" / "public" / "published_events.json", {}) or {}
    events = ev.get("items") or []
    hv = load(root / "data" / "views" / "homepage_intelligence.json", {}) or {}

    now = datetime.now(timezone.utc)
    h24, d7 = now - timedelta(hours=24), now - timedelta(days=7)

    cfg_ids = {str(s.get("source_id")) for s in conf}
    enabled = [s for s in conf if str(s.get("enabled")).lower() in ("true", "1", "yes")]
    enabled_ids = {str(s.get("source_id")) for s in enabled}
    rows = ss.get("per_source") or []
    by_id = {str(r.get("source_id")): r for r in rows}
    health_by_id = {str(r.get("source_id")): r for r in (health.get("sources") or [])}
    tier_of = {str(s.get("source_id")): (s.get("source_reliability_tier") or "") for s in conf}
    role_of = {str(s.get("source_id")): (s.get("source_group") or "") for s in conf}
    scope_of = {str(s.get("source_id")): (s.get("country_scope") or "") for s in conf}

    attempted = [r for r in rows]
    http_ok = [r for r in rows if str(r.get("status") or "") == "success" and not r.get("error")]
    productive = [r for r in rows if int(r.get("published") or 0) > 0 or int(r.get("discovered") or 0) > 0]
    zero_out = [r for r in rows if int(r.get("discovered") or 0) == 0]
    failed = [r for r in rows if str(r.get("status") or "") != "success"]

    # ── 24h 视窗（信号层）──
    in24, in7 = [], []
    no_time = 0
    for it in feed:
        t = parse_t(it.get("last_seen_at") or it.get("observed_at"))
        if not t:
            no_time += 1
            continue
        if t >= d7:
            in7.append(it)
        if t >= h24:
            in24.append(it)

    by_verif = Counter(str(x.get("verification_status") or x.get("verification_level") or "") for x in in24)
    by_country24 = Counter(str(x.get("country_cn") or "未识别") for x in in24)
    multi24 = len([x for x in in24 if int(x.get("independent_source_count") or 0) >= 2])
    localized24 = len([x for x in in24 if str(x.get("title_cn") or "").strip() and str(x.get("summary_cn") or "").strip()])
    pub_items = load(root / "data" / "public" / "intelligence_items.json", {}) or {}
    pub_ids = {str(x.get("item_id")) for x in (pub_items.get("items") or [])}
    public_eligible = len([x for x in in7 if str(x.get("news_id")) in pub_ids or str(x.get("src_id")) in pub_ids])

    dedup = hv.get("dedup") or {}
    homepage_24h = ((hv.get("metrics") or {}).get("signals_24h", 0)
                    + (hv.get("metrics") or {}).get("verified_events_24h", 0))

    # ── PHASE 2：丢失原因 ──
    reasons = Counter()
    for k, v in (cs.get("failure_reasons") or {}).items():
        kk = str(k).upper()
        if "429" in kk:
            reasons["HTTP_429"] += int(v)
        elif "WALL_CLOCK" in kk:
            reasons["OTHER"] += int(v)          # 预算截断：源未跑，归 OTHER 并在下文明示
        elif "RSS_EMPTY" in kk:
            reasons["RSS_EMPTY"] += int(v)
        elif "NO_RESULT" in kk or "NO_ITEMS" in kk:
            reasons["NO_ITEMS"] += int(v)
        elif "OK_PRODUCTIVE" in kk:
            pass
        else:
            reasons["OTHER"] += int(v)
    for r in rows:
        if int(r.get("duplicates") or 0):
            reasons["DUPLICATE_EXACT"] += int(r.get("duplicates") or 0)
        if int(r.get("extraction_failed") or 0):
            reasons["PARSE_ERROR"] += int(r.get("extraction_failed") or 0)
        if int(r.get("quarantined") or 0):
            reasons["SECURITY_FILTER_REJECT"] += int(r.get("quarantined") or 0)
        fr = str(r.get("failure_reason") or "").upper()
        for key in ("HTTP_403", "HTTP_404", "HTTP_429", "TIMEOUT", "PARSE_ERROR", "RSS_EMPTY", "NO_ITEMS"):
            if key in fr:
                reasons[key] += 0  # 已在 failure_reasons 汇总，避免重复计数
    rejects = (ns.get("counts") or {}).get("rejects_by_code") or {}
    if rejects.get("REJ_NO_TIME"):
        reasons["DATE_PARSE_FAIL"] += int(rejects["REJ_NO_TIME"])
    if no_time:
        reasons["DATE_PARSE_FAIL"] += no_time
    reasons["COUNTRY_UNRESOLVED"] += len([x for x in in7 if not str(x.get("country_cn") or "").strip()])

    # ── PHASE 3：逐源台账 ──
    per_source = []
    for r in rows:
        sid = str(r.get("source_id"))
        h = health_by_id.get(sid) or {}
        per_source.append({
            "source_id": sid, "source_name": r.get("source_name"),
            "tier": tier_of.get(sid, ""), "role": role_of.get(sid, ""),
            "scope": scope_of.get(sid, r.get("country") or ""),
            "method": r.get("method"), "attempts_24h": 1,
            "http_success": str(r.get("status")) == "success",
            "items_discovered": int(r.get("discovered") or 0),
            "items_fetched": int(r.get("fetched") or 0),
            "security_accepted": int(r.get("published") or 0),
            "quarantined": int(r.get("quarantined") or 0),
            "duplicates": int(r.get("duplicates") or 0),
            "errors": int(r.get("errors") or 0),
            "runtime_s": r.get("duration_s"),
            "last_fetch": h.get("last_fetch"), "parser_failures": h.get("parser_failures"),
            "empty_anomaly": h.get("empty_anomaly"),
            "failure_reason": r.get("failure_reason") or r.get("error") or "",
            "yield_class": classify(str(r.get("status")) == "success",
                                    int(r.get("discovered") or 0), int(r.get("published") or 0),
                                    r.get("failure_reason") or r.get("error")),
        })
    per_source.sort(key=lambda x: (-x["security_accepted"], -x["items_discovered"], str(x["source_id"])))
    yc = Counter(p["yield_class"] for p in per_source)

    doc = {
        "schema": "intelligence-volume-audit-v1",
        "generated_at": now.isoformat(timespec="seconds"),
        "data_as_of": tc.get("data_as_of") or tc.get("processed_through"),
        "collection_run": {"run_id": cs.get("collector_run_id"), "started_at": cs.get("started_at"),
                           "generated_at": cs.get("collector_generated_at"),
                           "wall_clock_limit_s": cs.get("wall_clock_limit"),
                           "skipped_wall_clock": cs.get("skipped_wall_clock")},
        "funnel": {
            "CONFIGURED_SOURCES": len(conf), "ENABLED_SOURCES": len(enabled),
            "SOURCES_ATTEMPTED_24H": len(attempted), "SOURCES_HTTP_OK": len(http_ok),
            "SOURCES_PRODUCTIVE": len(productive), "SOURCES_ZERO_OUTPUT": len(zero_out),
            "SOURCES_FAILED": len(failed),
            "SOURCES_BLOCKED_BY_EXTERNAL": cs.get("sources_blocked_by_external"),
            "SOURCES_NO_OUTPUT_NOT_BLOCKED": cs.get("sources_no_output_not_blocked"),
            "RAW_ITEMS_DISCOVERED": cs.get("articles_discovered"),
            "RAW_ITEMS_FETCHED": sum(int(r.get("fetched") or 0) for r in rows),
            "DUPLICATES_AT_COLLECT": cs.get("duplicates"),
            "QUARANTINED_AT_COLLECT": cs.get("quarantined"),
            "ARTICLES_PERSISTED_NEW": cs.get("articles_persisted_new"),
            "ARTICLES_PERSISTED_TOTAL": cs.get("articles_persisted_total"),
            "ARTICLES_EXCLUDED_TOTAL": cs.get("articles_excluded_total"),
            "ITEMS_WITH_VALID_TIME_7D": len(in7), "ITEMS_WITH_NO_TIME": no_time,
            "ITEMS_IN_24H_WINDOW": len(in24),
            "MULTI_SOURCE_ITEMS_24H": multi24,
            "SINGLE_SOURCE_ITEMS_24H": len(in24) - multi24,
            "LOCALIZED_ITEMS_24H": localized24,
            "PUBLIC_ELIGIBLE_SIGNALS": public_eligible,
            "CLUSTER_INPUT_ITEMS": len(in7),
            "UNIQUE_DEVELOPMENTS": dedup.get("deduped_developments"),
            "VERIFIED_MULTI_SOURCE_EVENTS_24H": len([e for e in events
                                                     if int(e.get("independent_source_count") or 0) >= 2
                                                     and (parse_t(e.get("published_time")) or now - timedelta(days=99)) >= h24]),
            "HOMEPAGE_24H_VISIBLE": homepage_24h,
        },
        "loss_reasons": {k: reasons.get(k, 0) for k in LOSS_KEYS},
        "loss_reasons_note": {
            "OTHER_includes": "WALL_CLOCK_LIMIT_REACHED（预算截断：源未执行）与未归类的运行期错误",
            "WALL_CLOCK_LIMIT_REACHED": (cs.get("failure_reasons") or {}).get("WALL_CLOCK_LIMIT_REACHED"),
            "HTTP_429": (cs.get("failure_reasons") or {}).get("HTTP_429"),
            "QUERY_NO_RESULT": (cs.get("failure_reasons") or {}).get("QUERY_NO_RESULT"),
            "OK_PRODUCTIVE": (cs.get("failure_reasons") or {}).get("OK_PRODUCTIVE"),
        },
        "country": {"ACTIVE_COUNTRIES_24H": len([c for c in by_country24 if c != "未识别"]),
                    "ACTIVE_COUNTRIES_7D": len({str(x.get("country_cn") or "") for x in in7} - {""}),
                    "COUNTRY_UNRESOLVED_24H": by_country24.get("未识别", 0),
                    "top_24h": by_country24.most_common(10)},
        "verification_split_24h": dict(by_verif),
        "yield_classes": dict(yc),
        "per_source": per_source,
        "blocked_on": {"RELIEFWEB_STATUS": "PENDING_APPROVED_APPNAME",
                       "ACLED": "CREDENTIAL_REQUIRED", "REUTERS": "metadata_only_via_gdelt",
                       "AP": "verification_only"},
        "rotation": rot,
    }
    return doc


def render_md(doc):
    f = doc["funnel"]
    lr = doc["loss_reasons"]
    lines = [
        "# C8-1 · 24h 情报量漏斗审计",
        "",
        "生成时间：%s ｜ data_as_of：%s ｜ 采集轮：%s" % (doc["generated_at"], doc["data_as_of"],
                                                  (doc["collection_run"] or {}).get("run_id")),
        "",
        "> 口径：逐源台账为**最近一轮**采集；24h 视窗指标由 `news_stream.last_seen_at` 派生。",
        "",
        "## 1. 漏斗（PHASE 1）",
        "",
        "| 阶段 | 计数 |",
        "|---|---|",
    ]
    for k in ("CONFIGURED_SOURCES", "ENABLED_SOURCES", "SOURCES_ATTEMPTED_24H", "SOURCES_HTTP_OK",
              "SOURCES_PRODUCTIVE", "SOURCES_ZERO_OUTPUT", "SOURCES_FAILED",
              "SOURCES_BLOCKED_BY_EXTERNAL", "SOURCES_NO_OUTPUT_NOT_BLOCKED",
              "RAW_ITEMS_DISCOVERED", "RAW_ITEMS_FETCHED", "DUPLICATES_AT_COLLECT",
              "QUARANTINED_AT_COLLECT", "ARTICLES_PERSISTED_NEW", "ITEMS_WITH_VALID_TIME_7D",
              "ITEMS_WITH_NO_TIME", "ITEMS_IN_24H_WINDOW", "MULTI_SOURCE_ITEMS_24H",
              "SINGLE_SOURCE_ITEMS_24H", "LOCALIZED_ITEMS_24H", "PUBLIC_ELIGIBLE_SIGNALS",
              "UNIQUE_DEVELOPMENTS", "VERIFIED_MULTI_SOURCE_EVENTS_24H", "HOMEPAGE_24H_VISIBLE"):
        lines.append("| %s | %s |" % (k, f.get(k)))
    lines += ["", "## 2. 信息消失点（PHASE 2）", "", "| 原因 | 计数 |", "|---|---|"]
    for k in LOSS_KEYS:
        if lr.get(k):
            lines.append("| %s | %d |" % (k, lr[k]))
    lines += ["", "运行期原因明细：", "",
              "- WALL_CLOCK_LIMIT_REACHED = %s（预算截断，源未执行）" % doc["loss_reasons_note"]["WALL_CLOCK_LIMIT_REACHED"],
              "- HTTP_429 = %s" % doc["loss_reasons_note"]["HTTP_429"],
              "- QUERY_NO_RESULT = %s" % doc["loss_reasons_note"]["QUERY_NO_RESULT"],
              "- OK_PRODUCTIVE = %s" % doc["loss_reasons_note"]["OK_PRODUCTIVE"],
              "", "## 3. 产出分类（PHASE 3 汇总）", "", "| 分类 | 源数 |", "|---|---|"]
    for k, v in sorted(doc["yield_classes"].items(), key=lambda kv: -kv[1]):
        lines.append("| %s | %d |" % (k, v))
    lines += ["", "### 高产源（按已接受条数）", "",
              "| source_id | name | tier | scope | discovered | accepted | quarantined | dup | class |",
              "|---|---|---|---|---|---|---|---|---|"]
    for p in doc["per_source"][:18]:
        lines.append("| %s | %s | %s | %s | %d | %d | %d | %d | %s |" % (
            p["source_id"], p["source_name"], p["tier"], p["scope"], p["items_discovered"],
            p["security_accepted"], p["quarantined"], p["duplicates"], p["yield_class"]))
    lines += ["", "### 零产出 / 失败源（前 18）", "",
              "| source_id | name | status | reason | class |", "|---|---|---|---|---|"]
    zs = [p for p in doc["per_source"] if p["yield_class"] in ("ZERO_YIELD", "BROKEN", "ACCESS_LIMITED")]
    for p in zs[:18]:
        lines.append("| %s | %s | %s | %s | %s |" % (p["source_id"], p["source_name"],
                                                     "http_ok" if p["http_success"] else "fail",
                                                     str(p["failure_reason"])[:60], p["yield_class"]))
    lines += ["", "## 4. 24h 国家覆盖（PHASE 17 基线）", "",
              "- ACTIVE_COUNTRIES_24H = %s ｜ ACTIVE_COUNTRIES_7D = %s ｜ COUNTRY_UNRESOLVED_24H = %s" % (
                  doc["country"]["ACTIVE_COUNTRIES_24H"], doc["country"]["ACTIVE_COUNTRIES_7D"],
                  doc["country"]["COUNTRY_UNRESOLVED_24H"]),
              "- 24h 前十国家：%s" % ", ".join("%s=%d" % (a, b) for a, b in doc["country"]["top_24h"]),
              "", "## 5. 阻塞项（不计入 C8-1 失败）", ""]
    for k, v in doc["blocked_on"].items():
        lines.append("- %s = %s" % (k, v))
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="C8-1 24h 情报量审计（只读）")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root)
    doc = audit(root)
    print(json.dumps({"funnel": doc["funnel"], "yield_classes": doc["yield_classes"],
                      "loss_reasons_top": sorted(doc["loss_reasons"].items(),
                                                 key=lambda kv: -kv[1])[:6]},
                     ensure_ascii=False, indent=1)[:2600])
    if args.apply:
        p = root / OUT_JSON
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        m = root / OUT_MD
        m.parent.mkdir(parents=True, exist_ok=True)
        m.write_text(render_md(doc), encoding="utf-8")
        print("written: %s / %s" % (OUT_JSON, OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
