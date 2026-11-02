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
  data/runtime/ops/reports/daily_brief_<YYYYMMDD>.json      （既有 report.html 渲染契约）
  data/runtime/ops/reports/tcd_weekly_brief_<WEEKLY_BRIEF_...>.json
  并把当期报告 upsert 进 data/views/report_index.json 顶部（同一索引文件，不建第二套）

Phase 3 / I.4（国家级相关性闸门）：
  周报此前把**全非洲**（africa_weekly）产物直接命名成 tcd_weekly_brief_* 并写入公开
  索引 → 非乍得内容（莫桑比克矿用挖掘机运营新闻等）冒充"乍得周报"发布。
  现在：
    - 周报内容按乍得相关性过滤后才生成（发布物确实是乍得周报）；
    - 乍得相关性证据不足 → **暂缓**：不写发布文件、不进索引，原始证据留在
      data/runtime/ops/reports/deferred/（该目录不在发布路径内）；
    - 被暂缓的 report_id 记入索引 deferred_reports → 后续自动重建**不得**重新加入；
    - 合格日报与其他网站内容不受影响（日报永远发布）。
  真正的乍得周报由 scripts/report/materialize.py::materialize_country_weekly 产出
  （report_type=country_weekly → data/reports/country_weekly/WEEKLY_TCD_*.json），
  本模块不得与之抢同一命名空间。

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

# ── 国家级相关性闸门（ASIP-5 P0 Phase 3 · I.4）──────────────────────────
# 根因：africa_weekly（**全非洲**）产物此前被直接命名成 tcd_weekly_brief_* 并写入
# 公开索引 → 非乍得内容（莫桑比克矿用挖掘机运营新闻等）冒充"乍得周报"。
# 真正的乍得周报由 scripts/report/materialize.py::materialize_country_weekly
# 产出（report_type=country_weekly → data/reports/country_weekly/WEEKLY_TCD_*.json），
# 本模块不得与之抢同一命名空间。
#
# 修正后的契约：
#   1. 本模块的周报只在**内容确实是乍得范围**时才作为"乍得周报"发布；
#   2. 内容按乍得相关性过滤（过滤后才叫乍得周报），非乍得内容不得混入；
#   3. 乍得相关性证据不足 → **暂缓**（不写发布文件、不进索引），但原始证据保留；
#   4. 暂缓过的 report_id 记入索引的 deferred_reports，后续自动重建**不得**重新加入；
#   5. 合格日报与其他网站内容不受影响（日报永远发布）。
CHAD_TOKENS = ("乍得", "Tchad", "tchad", "TCD", "tcd")
CHAD_MIN_ITEMS = 3        # 绝对下限：乍得相关条目 < 3 → 无国家相关性证据
CHAD_MIN_SHARE = 0.30     # 相对下限：乍得相关占比 < 30% → 不足以称为"乍得周报"
DEFERRED_DIR = Path("deferred")   # 相对 BRIEF_DIR：暂缓证据的存放位置（不进发布路径）


def _item_text(it):
    """条目文本（用于国家相关性判定）。"""
    return " ".join(str(it.get(k) or "") for k in
                     ("country", "country_cn", "title_cn", "title_original",
                      "summary_cn", "headline_zh", "title_zh"))


def _is_chad_relevant(it):
    """条目是否与乍得存在国家层面关联（归属乍得，或正文明确指向乍得）。"""
    blob = _item_text(it)
    if not blob.strip():
        return False
    low = blob.lower()
    return any(tok in blob or tok in low for tok in CHAD_TOKENS)


def weekly_scope_gate(feed):
    """国家级相关性闸门。返回 (publishable, reason, stats)。

    publishable=False → 该周报**暂缓公开**（证据保留，不进索引、不写发布文件）。
    """
    n = len(feed or [])
    chad = [it for it in (feed or []) if _is_chad_relevant(it)]
    share = (float(len(chad)) / n) if n else 0.0
    stats = {"feed_items": n, "chad_relevant": len(chad), "chad_share": round(share, 3),
             "min_items": CHAD_MIN_ITEMS, "min_share": CHAD_MIN_SHARE}
    if n == 0:
        return False, "no_feed_items", stats
    if len(chad) < CHAD_MIN_ITEMS:
        return False, "insufficient_chad_items:%d<%d" % (len(chad), CHAD_MIN_ITEMS), stats
    if share < CHAD_MIN_SHARE:
        return False, "chad_share_too_low:%.3f<%.3f" % (share, CHAD_MIN_SHARE), stats
    return True, "chad_scope_ok", stats


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


def build_weekly(hv, now, feed=None):
    """周报（乍得范围）。

    feed：调用方**已按乍得相关性过滤**的条目；缺省时用全部情报流（仅供离线诊断，
    生产路径必须先过 weekly_scope_gate，否则内容非乍得范围）。
    """
    o = hv.get("overview") or {}
    secs = hv.get("sectors") or []
    china = hv.get("china_impact") or {}
    health = hv.get("health_security") or {}
    feed = hv.get("latest_intelligence") or [] if feed is None else feed
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
        # I.4：内容已按乍得相关性过滤 → 类型/标题必须与实际范围一致，
        # 不得再用 africa_weekly（全非洲）冒充乍得周报。
        "report_type": "country_weekly",
        "country_scope": "TCD",
        "title_cn": "乍得国家安全形势周报（当期情报简报）",
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


def _indexable(root, row, keep_paths):
    """发布契约过滤：索引只能引用"构建能发布到 dist 的产物"。

    build_site._copy_report_artifacts 的 canonical SOURCE 集合是树 data/reports/**；
    runtime-only 报告（只在 data/runtime/ops/reports/ 与 dist 里）不在该集合内，
    一旦被索引 → MISSING → REPORT_ARTIFACT_PUBLICATION=FAIL → 生产 deploy 卡在 Build site
    （生产实测：索引 29 行，其中 DAILY_20260908/23/24/25/26 缺失 → MISSING=5）。
    """
    path = str(row.get("path") or "")
    if not path:
        return False
    if path in keep_paths:                     # 本轮要落盘并发布的当期简报
        return True
    return (root / path).exists()              # 已在 canonical SOURCE 树中的产物


def upsert_index(root, d_doc, w_doc, d_name, w_name, deferred=None):
    """把当期日报 upsert 进公开索引（周报按国家级相关性闸门决定是否 upsert）。

    deferred：本次被暂缓的报告描述列表 [{"report_id","reason","scope_stats"}]。
    暂缓项：
      - 不进索引；
      - 已存在的旧行**必须移除**（不得因产物文件仍在树中而被重新带回）；
      - 记入索引的 deferred_reports（跨轮持久）→ 后续自动重建**不得**重新加入。
    """
    idx = load_json(root / RI, {}) or {}
    keep_paths = {"data/reports/daily/%s" % d_name}
    if w_doc is not None:
        keep_paths.add("data/reports/weekly/%s" % w_name)

    # 跨轮持久化的暂缓清单（既有 + 本次）
    prior = [x for x in (idx.get("deferred_reports") or []) if isinstance(x, dict)]
    prior_ids = {str(x.get("report_id")) for x in prior}
    cur = [dict(x) for x in (deferred or [])]
    cur_ids = {str(x.get("report_id")) for x in cur}
    merged = [x for x in prior if str(x.get("report_id")) not in cur_ids] + cur

    # 本轮要替换的 report_id（日报必替换；周报仅在发布时替换）
    _replace_ids = {str(d_doc["report_id"])}
    if w_doc is not None:
        _replace_ids.add(str(w_doc["report_id"]))
    rows = [r for r in (idx.get("reports") or [])
            if str(r.get("report_id")) not in _replace_ids]
    # 暂缓过的报告：无论产物文件是否仍在树中，都不得重新加入
    rows = [r for r in rows if str(r.get("report_id")) not in (prior_ids | cur_ids)]
    rows = [r for r in rows if _indexable(root, r, keep_paths)]

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
    rows = [row(d_doc, dpath)] + rows
    if w_doc is not None:
        wpath = "data/reports/weekly/%s" % w_name
        rows = [row(w_doc, wpath)] + rows
    rows.sort(key=lambda r: (str(r.get("period_end") or ""), str(r.get("report_id") or "")), reverse=True)
    idx = {"schema": "report-index-v2", "real_only": True, "count": len(rows),
           "generated_at": d_doc["generated_at"], "source": "c7-6_current_brief",
           "deferred_reports": merged, "reports": rows}
    write_atomic(root / RI, idx)
    return idx


def _defer_weekly(root, evidence_doc, wk_id, reason, scope_stats, now):
    """暂缓周报：保留原始证据 + 清理同名旧发布文件。

    - 证据写入 BRIEF_DIR/deferred/：该目录**不在**构建发布命名空间内
      （build_site._copy_production_reports 只取 BRIEF_DIR 顶层的
      daily_/tcd_weekly_/ssd_weekly_ 前缀文件，非递归）→ 证据不会变成公开报告；
    - 同名旧发布文件（上一轮误用 tcd_weekly 命名发布的产物）移入 deferred/，
      避免历史产物在后续自动重建时被再次发布。
    """
    ev = dict(evidence_doc or {})
    ev["deferred"] = True
    ev["deferred_reason"] = reason
    ev["scope_stats"] = scope_stats
    ev["deferred_at"] = now.isoformat(timespec="seconds")
    ddir = root / BRIEF_DIR / DEFERRED_DIR
    name = "tcd_weekly_brief_%s.json" % wk_id
    write_atomic(ddir / name, ev)
    stale = root / BRIEF_DIR / name
    if stale.exists():
        try:
            stale.replace(ddir / name)
        except OSError:
            pass
    return True


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

    # ── I.4：周报国家级相关性闸门 ──────────────────────────────────────
    iso = now.isocalendar()
    wk_id = "WEEKLY_BRIEF_%d%02d" % (iso[0], iso[1])
    raw_feed = hv.get("latest_intelligence") or []
    publishable, reason, scope_stats = weekly_scope_gate(raw_feed)
    # 通过闸门时，周报内容**只取乍得相关条目** → 发布物确实是"乍得周报"
    chad_feed = [it for it in raw_feed if _is_chad_relevant(it)] if publishable else []
    w_doc = build_weekly(hv, now, feed=chad_feed) if publishable else None
    w_name = ("tcd_weekly_brief_%s.json" % wk_id) if w_doc else None
    deferred = []
    if not publishable:
        deferred.append({"report_id": wk_id, "reason": reason,
                         "scope_stats": scope_stats,
                         "deferred_at": now.isoformat(timespec="seconds")})

    if args.apply:
        # 文件名前缀必须落在构建发布白名单内（daily_ / tcd_weekly_ / ssd_weekly_）；
        # dist 内的文件名由 report_id 别名决定，用户可见路径不受此前缀影响。
        d_name = "daily_brief_%s.json" % now.strftime("%Y%m%d")
        write_atomic(root / BRIEF_DIR / d_name, d_doc)
        if w_doc is not None:
            write_atomic(root / BRIEF_DIR / w_name, w_doc)
        else:
            # 暂缓：原始证据保留（deferred/ 不在发布路径内，构建/归档都不会带上它），
            # 并把同名旧发布文件移入 deferred/ → 历史产物不会被再次发布。
            _defer_weekly(root, build_weekly(hv, now, feed=raw_feed), wk_id,
                          reason, scope_stats, now)
        # 发布契约：先落盘 → 再写索引；索引路径 = canonical SOURCE 集合
        # data/reports/{daily,weekly}/<同名文件>（build_site._copy_report_artifacts 的比对基准），
        # 且 deploy 的 Load state 会把同一文件从 state 落到该树路径 → INDEX ⊆ SOURCE ∩ DIST。
        idx = upsert_index(root, d_doc, w_doc, d_name, w_name, deferred=deferred)
        print("  index rows = %d | daily = %s | weekly = %s%s" % (
            len(idx["reports"]), d_doc["report_id"],
            (w_doc["report_id"] if w_doc else wk_id),
            ("" if w_doc else " (DEFERRED: %s)" % reason)))
    print(json.dumps({
        "daily": d_doc["report_id"], "daily_sections": list(d_doc["sections"].keys()),
        "daily_items": sum(len(v) for v in d_doc["sections"].values()),
        "weekly": (w_doc["report_id"] if w_doc else wk_id),
        "weekly_published": bool(w_doc),
        "weekly_scope_gate": reason,
        "weekly_scope_stats": scope_stats,
        "weekly_items": (sum(len(v) for v in w_doc["sections"].values()) if w_doc else 0),
        "deferred_reports": [d.get("report_id") for d in deferred],
        "real_ai_calls": 0,
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
