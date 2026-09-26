"""C7-6 当期报告简报（确定性，无 AI 调用）。

背景（PHASE 10 真因）：
  编排器只跑 reports_run.py，从不调用 scripts/report/materialize.py → data/views/report_index.json
  永不刷新（线上索引冻结在 DAILY_20260922）；且 report factory 的事实闸门要求 source identity
  （覆盖率 26.7%），导致最近 14 份日报全部判 LOW_DATA，正文近乎空壳。

本模块按产品要求生成**当期**日报/周报，输入全部来自既有确定性+AI 产物（不新建 truth store）：
  data/views/homepage_intelligence.json（首页情报：总体态势/五领域/重点动态/涉华/健康）
  data/views/executive_summary.json · data/views/report_index.json（既有报告索引）
  data/public/intelligence_items.json（公开情报投影，含 detail_url）

输出：
  data/reports/brief/DAILY_BRIEF_<YYYYMMDD>.json     （既有 report.html 渲染契约）
  data/reports/brief/WEEKLY_BRIEF_<YYYYWW>.json
  并把当期两条 upsert 进 data/views/report_index.json 顶部（同一索引文件，不建第二套）

幂等：同一报告日/周重复运行内容一致（除 generated_at），因此不会重复生成或制造部署风暴。
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BJT = timezone(timedelta(hours=8))
HV = Path("data") / "views" / "homepage_intelligence.json"
EX = Path("data") / "views" / "executive_summary.json"
RI = Path("data") / "views" / "report_index.json"
# C7-6：简报写入 data/runtime/ops/reports/brief/ —— 该目录已被 deploy 的 Load state 覆盖
# （state_src/data/runtime/ops/reports → data/runtime/ops/reports），并由构建发布到
# dist/data/reports/brief/，与 report_index.path 一一对应。
BRIEF_DIR = Path("data") / "runtime" / "ops" / "reports"
INDEX_DIR = Path("data") / "reports" / "daily"


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def write_atomic(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, str(path))


def _hdr(name):
    return {"title_zh": "■ " + name, "headline_zh": name, "source_refs": ""}


def _dev_item(d, prefix=""):
    return {
        "title_zh": (prefix + d.get("title_cn") or "").strip(),
        "headline_zh": d.get("title_cn") or "",
        "detail_url": d.get("detail_url") or "",
        "country_cn": d.get("country") or "",
        "time": d.get("time") or "",
        "verification_label": d.get("verification_label") or "",
        "source_refs": " · ".join([s.get("name") or "" for s in (d.get("sources") or [])][:3])
                       or (d.get("source") or ""),
    }


def build_daily(hv, now):
    o = hv.get("overview") or {}
    m = hv.get("metrics") or {}
    secs = hv.get("sectors") or []
    china = hv.get("china_impact") or {}
    health = hv.get("health_security") or {}
    tops = hv.get("top_developments") or []
    feed = hv.get("latest_intelligence") or []
    date_key = now.strftime("%Y%m%d")
    period_end = now.replace(hour=20, minute=0, second=0, microsecond=0)
    period_start = period_end - timedelta(hours=24)

    sections = {}
    overall = [_hdr("一、过去24小时总体态势")]
    if o.get("summary_cn"):
        overall.append({"title_zh": o["summary_cn"], "headline_zh": "总体态势", "source_refs": ""})
    for k in (o.get("key_judgments") or []):
        overall.append({"title_zh": "关键判断：" + k, "headline_zh": "关键判断", "source_refs": ""})
    sections["overall_24h"] = overall

    dom = [_hdr("二、五大领域摘要")]
    for s in secs:
        dom.append({
            "title_zh": "%s：%s" % (s.get("title_cn"), (s.get("assessment_cn") or "数据不足，未形成判断")[:520]),
            "headline_zh": s.get("title_cn") or "",
            "trend": s.get("trend"), "confidence": s.get("confidence"),
            "source_refs": "近7日 已核实 %s · 情报信号 %s" % (s.get("verified_events_7d"), s.get("signals_7d")),
        })
    sections["sectors"] = dom

    ver = [_hdr("三、重点已核实事件")]
    ver += [_dev_item(d) for d in tops if d.get("kind") == "verified_event"][:8]
    if len(ver) == 1:
        ver.append({"title_zh": "本周期内无多源独立核实的重大事件。", "headline_zh": "", "source_refs": ""})
    sections["verified_events"] = ver

    sig = [_hdr("四、主要情报信号")]
    sig += [_dev_item(d) for d in tops if d.get("kind") != "verified_event"][:8]
    sig += [_dev_item(d) for d in feed if d.get("kind") != "verified_event"][:12]
    if len(sig) == 1:
        sig.append({"title_zh": "本周期内无可展示的情报信号。", "headline_zh": "", "source_refs": ""})
    sections["signals"] = sig

    cty = {}
    for d in feed:
        cty.setdefault(d.get("country") or "未识别", 0)
        cty[d.get("country") or "未识别"] += 1
    reg = [_hdr("五、重点区域")]
    reg += [{"title_zh": "%s：本周期公开条目 %d 条" % (k, v), "headline_zh": k, "source_refs": ""}
            for k, v in sorted(cty.items(), key=lambda kv: kv[1], reverse=True)[:8]]
    sections["regions"] = reg

    cn = [_hdr("六、对中国企业及人员影响")]
    cn.append({"title_zh": china.get("analysis_cn") or china.get("summary_cn") or
                           "过去24小时未发现明确直接涉及中国企业或人员的重大公开安全事件。",
               "headline_zh": "涉华影响研判", "source_refs": ""})
    for x in (china.get("direct_items") or [])[:6]:
        cn.append(_dev_item(x, "直接涉华："))
    for x in (china.get("regional_items") or [])[:6]:
        cn.append(_dev_item(x, "区域性运营风险："))
    sections["china_impact"] = cn

    hl = [_hdr("七、公共卫生关注")]
    hl.append({"title_zh": health.get("summary_cn") or "公共卫生数据暂不可用或不足，不作推断。",
               "headline_zh": "公共卫生", "source_refs": ""})
    for it in (health.get("items") or [])[:6]:
        hl.append({"title_zh": "%s（%s）%s" % (it.get("disease"), it.get("country_iso3"),
                                              ("· " + it.get("location")) if it.get("location") else ""),
                   "headline_zh": "传染病事件", "source_refs": str(it.get("as_of") or "")})
    sections["health_security"] = hl

    wt = [_hdr("八、未来24–72小时关注")]
    wt += [{"title_zh": x, "headline_zh": "关注", "source_refs": ""} for x in (o.get("watch_24_72h") or [])]
    sections["watch"] = wt

    evidence = [_hdr("九、证据与置信度说明")]
    evidence.append({"title_zh": "本报告由首页情报视图与当期 AI 研判汇总生成（确定性投影，未新增 AI 调用）。"
                                "已核实事件=多源独立核实；情报信号=公开报道/单一来源，尚未独立核实，两者不得混用。"
                                "研判置信度：%s。" % (o.get("confidence") or "低"),
                     "headline_zh": "证据说明", "source_refs": ""})
    sections["evidence"] = evidence

    return {
        "report_id": "DAILY_BRIEF_%s" % date_key,
        "report_type": "africa_daily",
        "title_cn": "非洲地区社会安全与综合形势日报（当期情报简报）",
        "report_date": now.strftime("%Y-%m-%d"),
        "period_start": period_start.isoformat(timespec="seconds"),
        "period_end": period_end.isoformat(timespec="seconds"),
        "generated_at": now.isoformat(timespec="seconds"),
        "report_timezone": "Asia/Shanghai",
        "status": "production",
        "is_mock": False,
        "data_as_of": hv.get("data_as_of") or "",
        "fact_count": m.get("signals_24h", 0) + m.get("verified_events_24h", 0),
        "source_count": len({x.get("source") for x in feed if x.get("source")}),
        "sections": sections,
        "analysis": {
            "executive_assessment": o.get("summary_cn") or "",
            "trend_analysis": "；".join((x.get("title_cn") or "") + "：" + (x.get("assessment_cn") or "")[:80]
                                       for x in secs[:5]),
            "watch_points": o.get("watch_24_72h") or [],
        },
        "overall_assessment": o.get("summary_cn") or "",
        "brief_kind": "daily",
    }


def build_weekly(hv, now):
    o = hv.get("overview") or {}
    secs = hv.get("sectors") or []
    china = hv.get("china_impact") or {}
    health = hv.get("health_security") or {}
    feed = hv.get("latest_intelligence") or []
    iso = now.isocalendar()
    wk = "%d%02d" % (iso[0], iso[1])
    period_end = now.replace(hour=20, minute=0, second=0, microsecond=0)
    period_start = period_end - timedelta(days=7)

    sections = {}
    sections["overall_week"] = [_hdr("一、一周总体安全态势"),
                                {"title_zh": o.get("summary_cn") or "本周公开信息不足以形成稳定研判。",
                                 "headline_zh": "总体态势", "source_refs": ""}]
    sections["sector_trends"] = [_hdr("二、五大领域趋势")] + [
        {"title_zh": "%s（趋势 %s）：%s" % (s.get("title_cn"), s.get("trend"),
                                          (s.get("assessment_cn") or "")[:420]),
         "headline_zh": s.get("title_cn") or "", "source_refs": ""} for s in secs]
    cty = {}
    for d in feed:
        k = d.get("country") or "未识别"
        cty[k] = cty.get(k, 0) + 1
    sections["regions"] = [_hdr("三、主要区域变化")] + [
        {"title_zh": "%s：本周公开条目 %d 条" % (k, v), "headline_zh": k, "source_refs": ""}
        for k, v in sorted(cty.items(), key=lambda kv: kv[1], reverse=True)[:10]]
    sections["major_events"] = [_hdr("四、重点事件")] + [
        _dev_item(d) for d in feed[:12]]
    sections["signals"] = [_hdr("五、高关注情报信号")] + [
        _dev_item(d) for d in feed if d.get("importance") == "high"][:10]
    sections["country_activity"] = [_hdr("六、国家活动变化")] + [
        {"title_zh": "%s：本周活动 %d 条（24h %s 条）" % (k, v, sum(
            1 for d in feed if (d.get("country") or "未识别") == k)), "headline_zh": k, "source_refs": ""}
        for k, v in sorted(cty.items(), key=lambda kv: kv[1], reverse=True)[:10]]
    sections["china_impact"] = [_hdr("七、中国企业/人员影响"),
                               {"title_zh": china.get("analysis_cn") or china.get("summary_cn") or
                                            "本周未发现明确直接涉及中国企业或人员的重大公开安全事件。",
                                "headline_zh": "涉华影响", "source_refs": ""}]
    sections["health"] = [_hdr("八、公共卫生安全"),
                          {"title_zh": health.get("summary_cn") or "公共卫生数据不足，不作推断。",
                           "headline_zh": "公共卫生", "source_refs": ""}]
    sections["next_week"] = [_hdr("九、下周重点关注")] + [
        {"title_zh": x, "headline_zh": "关注", "source_refs": ""} for x in (o.get("watch_24_72h") or [])]

    return {
        "report_id": "WEEKLY_BRIEF_%s" % wk,
        "report_type": "africa_weekly",
        "title_cn": "非洲地区安全形势周报（当期情报简报）",
        "report_date": now.strftime("%Y-%m-%d"),
        "period_start": period_start.isoformat(timespec="seconds"),
        "period_end": period_end.isoformat(timespec="seconds"),
        "generated_at": now.isoformat(timespec="seconds"),
        "report_timezone": "Asia/Shanghai",
        "status": "production",
        "is_mock": False,
        "data_as_of": hv.get("data_as_of") or "",
        "fact_count": len(feed),
        "source_count": len({x.get("source") for x in feed if x.get("source")}),
        "sections": sections,
        "analysis": {"executive_assessment": o.get("summary_cn") or "",
                     "trend_analysis": "；".join((s.get("title_cn") or "") + " 趋势 " + str(s.get("trend"))
                                                for s in secs),
                     "watch_points": o.get("watch_24_72h") or []},
        "overall_assessment": o.get("summary_cn") or "",
        "brief_kind": "weekly",
    }


def upsert_index(root, d_doc, w_doc, d_name, w_name):
    idx = load_json(root / RI, {}) or {}
    rows = [r for r in (idx.get("reports") or [])
            if str(r.get("report_id")) not in (d_doc["report_id"], w_doc["report_id"])]
    def row(doc, path):
        return {"report_id": doc["report_id"], "report_type": doc["report_type"],
                "title": doc["title_cn"], "title_cn": doc["title_cn"],
                "period_start": doc["period_start"], "period_end": doc["period_end"],
                "status": "production", "data_as_of": doc.get("data_as_of"),
                "generated_at": doc["generated_at"], "headline": doc["overall_assessment"][:150],
                "path": path, "is_mock": False, "legacy_only": False,
                "fact_count": doc.get("fact_count"), "source_count": doc.get("source_count")}
    # 与 dist 实际发布文件名严格一致：构建按前缀（daily_ / tcd_weekly_）原样复制，
    # report_id 别名并不保证生成 → 索引必须指向源名文件，才能满足
    # INDEX_REFERENCED_REPORTS == PUBLISHED_REPORT_FILES。
    dpath = "data/reports/daily/%s" % d_name
    wpath = "data/reports/weekly/%s" % w_name
    rows = [row(d_doc, dpath), row(w_doc, wpath)] + rows
    rows.sort(key=lambda r: (str(r.get("period_end") or ""), str(r.get("report_id") or "")), reverse=True)
    idx = {"schema": "report-index-v2", "real_only": True, "count": len(rows),
           "generated_at": d_doc["generated_at"], "source": "c7-6_current_brief",
           "reports": rows}
    write_atomic(root / RI, idx)
    return idx


def main(argv=None):
    ap = argparse.ArgumentParser(description="C7-6 当期报告简报（确定性）")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root)
    now = datetime.now(BJT)

    # 先刷新既有报告索引（materialize：确定性，无 AI）——修掉"索引永不刷新"的真实断点
    try:
        import sys as _sys
        if str(root) not in _sys.path:
            _sys.path.insert(0, str(root))
        from scripts.report import materialize as M  # noqa: E402
        st = M.materialize_reports(str(root), days=14, write=args.apply)
        M.build_real_report_index(str(root), rows=st.pop("_rows", []), write=args.apply)
        print("  materialize: TOTAL_REAL_REPORTS_IN_INDEX=%s" % st.get("TOTAL_REAL_REPORTS_IN_INDEX"))
    except Exception as e:  # noqa: BLE001
        print("  ⚠ materialize 跳过：%s" % str(e)[:160])

    hv = load_json(root / HV, {})
    if not hv:
        print(json.dumps({"status": "no_homepage_view", "written": 0}, ensure_ascii=False))
        return 0
    d_doc = build_daily(hv, now)
    w_doc = build_weekly(hv, now)
    if args.apply:
        # 文件名前缀必须落在构建发布白名单内（daily_ / tcd_weekly_ / ssd_weekly_）；
        # dist 内的文件名由 report_id 别名决定，用户可见路径不受此前缀影响。
        d_name = "daily_brief_%s.json" % now.strftime("%Y%m%d")
        w_name = "tcd_weekly_brief_%s.json" % w_doc["report_id"]
        write_atomic(root / BRIEF_DIR / d_name, d_doc)
        write_atomic(root / BRIEF_DIR / w_name, w_doc)
        # 发布契约：先落盘（daily_brief_* / tcd_weekly_brief_* → 构建白名单前缀）→ 再写索引，
        # 索引路径与 dist 实际发布名（<report_id>.json）一一对应，保证
        # INDEX_REFERENCED_REPORTS == PUBLISHED_REPORT_FILES。
        idx = upsert_index(root, d_doc, w_doc, d_name, w_name)
        print("  index rows = %d | daily = %s | weekly = %s" % (len(idx["reports"]),
                                                              d_doc["report_id"], w_doc["report_id"]))
    print(json.dumps({
        "daily": d_doc["report_id"], "daily_sections": list(d_doc["sections"].keys()),
        "daily_items": sum(len(v) for v in d_doc["sections"].values()),
        "weekly": w_doc["report_id"], "weekly_items": sum(len(v) for v in w_doc["sections"].values()),
        "real_ai_calls": 0,
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
