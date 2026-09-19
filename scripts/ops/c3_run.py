#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c3_run.py —— C3 增量流水线（§二十三–§二十六、§四十–§四十二）。

流程（每次 Collection 之后可自动执行）：
  1. 读 news stream 的 NEWS_ELIGIBLE → 找出 new / changed（缺中文或内容指纹变化）
  2. deterministic dedupe → localization cache 查表（news_id+content_hash+prompt_version+model）
  3. 批量（8–12/次）调用 provider → schema 校验 → numbers/dates 守恒闸门
  4. 写 localization artifact + 回写 article.title_cn/summary_cn（供 News Stream 展示）
  5. 对 new / materially changed 的 multi-source event 生成 event intelligence
  6. 对 fact pack hash 变化的 country 生成 country intelligence（不足则 LOW_DATA）
  7. homepage fact pack hash 变化且超过 cooldown 才重算
  8. 成本统计 / 幂等（相同输入第二次运行 AI_CALLS_NEW=0）

凭据缺失时（§三十七）：不调用 API、不伪造 AI 文本，全部落 FALLBACK，
最终状态 HOLD_AI_CREDENTIAL_RUNTIME_REQUIRED。
"""
import argparse
import hashlib
import io
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

# C3R2-IMPORT：仓库根目录**从本文件位置推导**，禁止硬编码开发机路径。
# 旧版本把开发机绝对路径写死，在 GitHub Actions 里 sys.path 全部指向不存在的目录，
# 于是 `import c3_localization` 直接 ModuleNotFoundError（CI Real run 1 的失败原因）。
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BJ = timezone(timedelta(hours=8))

# 本仓库需要路径可见的模块目录（data / collectors / clustering / ai.providers 目前不是包）。
# 全部由 ROOT 推导，跨机器一致；C3 自身模块改走下面的 package-qualified import。
for _d in ("", "scripts", "scripts/data", "scripts/ops", "scripts/ai",
           "scripts/ai/providers", "scripts/collectors", "scripts/clustering"):
    _p = os.path.join(ROOT, _d)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# C3 模块：package-qualified 优先（repo root 与 python -m 都稳定），
# 回退扁平导入以兼容既有的 `python scripts/ops/c3_run.py` 调用方式。
try:                                                    # noqa: E402
    from scripts.ai import c3_localization as L         # noqa: E402
    from scripts.ai import c3_analysis as A             # noqa: E402
    from scripts.ai import c3_artifacts as ART          # noqa: E402
except ImportError:                                     # pragma: no cover
    import c3_localization as L                         # noqa: E402
    import c3_analysis as A                             # noqa: E402
    import c3_artifacts as ART                          # noqa: E402


def rd(p, d=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return d


def dt(v):
    if not v:
        return None
    try:
        x = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _latest_reports(root, limit=8):
    """最近报告列表（确定性）：来自已提交的 report_index 视图；缺失则空。"""
    doc = rd(os.path.join(str(root), "data", "views", "report_index.json"), {}) or {}
    rows = doc.get("reports") or doc.get("items") or []
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        if r.get("status") and r.get("status") != "production":
            continue
        out.append({"title": r.get("title") or r.get("title_original") or "",
                    "date": r.get("report_date") or r.get("date") or ""})
    out.sort(key=lambda x: x.get("date") or "", reverse=True)
    return out[:limit]


def get_provider(mode):
    """mode: auto | mock_ok | mock_timeout | mock_429 | mock_500 | mock_invalid_json |
             mock_schema_fail | mock_injection"""
    if mode.startswith("stub"):
        behavior = mode.split(":", 1)[1] if ":" in mode else "ok"
        return L.StubProvider(behavior), "stub:%s" % behavior
    # C3 明确使用 DeepSeek V4 Flash（§三）；沿用本仓库既有做法直接构造 provider
    # （与 ai/qualification/report_trial.py 一致），不得自动回退其它付费模型。
    try:
        from scripts.ai.providers.deepseek_v4_flash import DeepSeekV4FlashProvider
    except ImportError:
        from ai.providers.deepseek_v4_flash import DeepSeekV4FlashProvider
    try:
        p = DeepSeekV4FlashProvider()
        return p, "deepseek_v4_flash"
    except Exception as e:  # noqa: BLE001
        return None, "unavailable:%s" % type(e).__name__


def provider_ready(provider):
    """凭据可用性检查（只读环境变量，绝不打印值）。"""
    if provider is None:
        return False, "provider_unavailable"
    if getattr(provider, "name", "") == "stub":
        return True, "stub"
    try:
        try:
            from scripts.ai.providers.deepseek_v4_flash import credential_available
        except ImportError:
            from ai.providers.deepseek_v4_flash import credential_available
        if not credential_available():
            return False, "credential_missing"
    except Exception:  # noqa: BLE001
        if not os.environ.get("ASIP_DEEPSEEK_API_KEY", "").strip():
            return False, "credential_missing"
    return True, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("ASIP_C3_ROOT", ROOT))
    ap.add_argument("--provider", default="auto")
    ap.add_argument("--window-start", default="2026-09-05")
    ap.add_argument("--window-end", default="2026-09-18")
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--mode", default="full",
                    choices=["full", "summary_only", "c3f_incremental"],
                    help="full=标题+摘要；summary_only=只补缺失摘要（不重写标题）；"
                         "c3f_incremental=先 full 再 summary_only，只处理 dirty 组件")
    ap.add_argument("--home-cooldown-hours", type=float, default=4.0)
    ap.add_argument("--force-home", action="store_true")
    ap.add_argument("--out", default=os.path.join(
        os.environ.get("ASIP_C3_OUT_DIR", os.getcwd()), "c3_run_report.json"))
    a = ap.parse_args()
    root = a.root

    news = rd(os.path.join(root, "data", "views", "news_stream.json"), {}) or {}
    items = news.get("items") or []
    articles = rd(os.path.join(root, "data", "canonical", "articles.json"), {}).get("items") or []
    clusters = rd(os.path.join(root, "data", "canonical", "event_clusters.json"),
                  {}).get("items") or []
    status_doc = rd(os.path.join(root, "data", "status.json"), {}) or {}
    data_as_of = status_doc.get("data_as_of")

    provider, pname = get_provider(a.provider)
    ready, why = provider_ready(provider)
    model = getattr(provider, "model", L.DEFAULT_MODEL) if ready else L.DEFAULT_MODEL

    stats = {
        "schema": "c3-run-v1",
        "generated_at_bj": datetime.now(BJ).strftime("%Y-%m-%d %H:%M:%S"),
        "provider_requested": a.provider, "provider_resolved": pname,
        "provider_ready": ready, "provider_block_reason": why,
        "model": model, "data_as_of": data_as_of,
        "ai_calls_total": 0, "ai_calls_localization": 0, "ai_calls_event": 0,
        "ai_calls_country": 0, "ai_calls_homepage": 0,
        "cache_hits": 0, "cache_misses": 0,
        "localization": {}, "event": {}, "country": {}, "homepage": {},
        "gates": {"localization_fact_gate": "PASS", "analysis_fact_gate": "PASS"},
        "errors": [],
    }

    # ── 1) Localization ──────────────────────────────────────────────
    mode = a.mode
    # C3F-R §三：c3f_incremental = 只补缺失摘要 + 仅当 fact pack hash 变化才重跑 Homepage，
    # 且**显式跳过** Event / Country 分析（它们的 fact pack 本轮未变，召回即违规）。
    incremental = (mode == "c3f_incremental")
    if mode in ("summary_only", "c3f_incremental"):
        targets = [i for i in items if L.needs_summary_only(i)]
    else:
        targets = [i for i in items if L.needs_localization(i)]
    summary_mode = mode in ("summary_only", "c3f_incremental")
    skip_analysis = incremental
    stats["localization"]["mode"] = mode
    stats["localization"]["target"] = len(targets)
    batches = L.build_batches(targets, a.batch_size)
    stats["localization"]["batches"] = len(batches)
    localized_full = localized_fallback = localized_failed = 0
    applied = {}
    for batch in batches:
        bkeys = [L.cache_key(i, model) for i in batch]
        cached = {}
        to_call = []
        for it, k in zip(batch, bkeys):
            rec = ART.read_artifact(root, "localization", k)
            # 缓存命中：input_hash 一致且不是「可重试的 provider 失败」。
            # C3F §四：summary-only 下"缺摘要"不再无条件重试——若该条目是**终态负缓存**
            # （gate 确定性拒绝），必须直接复用，否则 Run2 会对同一个 FALLBACK 再次调用 provider，
            # 破坏 SECOND_IDENTICAL_RUN_AI_CALLS = 0。
            _negative = rec and L.is_negative_cached(rec)
            if (rec and rec.get("input_hash") == L.content_hash(it)
                    and not rec.get("retryable")
                    and not (summary_mode and not (rec.get("summary_cn") or "").strip()
                             and not _negative)):
                cached[k] = rec
            else:
                to_call.append(it)
        stats["cache_hits"] += len(cached)
        stats["cache_misses"] += len(to_call)
        for k, rec in cached.items():
            _out = {"title_cn": rec.get("title_cn"), "summary_cn": rec.get("summary_cn")}
            for _idk in ("src_id", "news_id", "display_identity"):
                if rec.get(_idk):
                    applied[rec[_idk]] = _out
        if not ready:
            for it in to_call:
                k = L.cache_key(it, model)
                nid = it.get("news_id") or it.get("src_id")
                ART.write_artifact(root, "localization", k,
                                   {"news_id": nid, "src_id": it.get("src_id") or "",
                                    "display_identity": L.display_identity(it) or "",
                                    "title_cn": "", "summary_cn": "",
                                    "fallback_reason": why},
                                   schema_version=L.SCHEMA_VERSION, model=model,
                                   prompt_version=L.PROMPT_VERSION,
                                   input_hash=L.content_hash(it),
                                   status=L.STATUS_FALLBACK,
                                   source_fact_refs=[nid], data_as_of=data_as_of,
                                   # 凭据缺失不是内容问题：一旦补齐凭据应当自动重试
                                   extra={"retryable": True, "blocked_reason": why})
                # 凭据缺失 = provider 不可用（不是 fact gate 拒绝），指标必须如实归类
                localized_failed += 1
            continue
        if not to_call:
            continue          # 全部命中缓存：不得发起任何 API 调用
        if summary_mode:
            u = L.build_user_prompt_summary_only(to_call)
            task = {"task_id": "sum_%s" % hashlib.sha256(u.encode()).hexdigest()[:12],
                    "task_type": "stage4_event_enrichment",
                    "system_text": L.SYSTEM_PROMPT_SUMMARY_ONLY,
                    "user_text": u, "max_output_tokens": 2000}
            resp = provider.submit_task(task)
            res = (resp or {}).get("result") or {}
            if (resp or {}).get("status") != "succeeded":
                out_items, meta = [], {"ok": False, "status": (resp or {}).get("status"),
                                       "error": ((res.get("error") or {}).get("code")),
                                       "usage": {}, "returned_model": res.get("returned_model")}
            else:
                out_items, errs = L.parse_summary_only(res.get("text"))
                meta = {"ok": not errs, "status": "succeeded", "errors": errs,
                        "usage": {}, "returned_model": res.get("returned_model")}
        else:
            out_items, meta = L.localize_batch(provider, to_call, model=model)
        if meta.get("status") == "succeeded" or meta.get("ok"):
            stats["ai_calls_localization"] += 1
            stats["ai_calls_total"] += 1
        by_id = {str(x["news_id"]): x for x in out_items}
        for it in to_call:
            nid = str(it.get("news_id") or it.get("src_id"))
            k = L.cache_key(it, model)
            got = by_id.get(nid)
            if not got:
                st = L.STATUS_FAILED if meta.get("status") != "succeeded" else L.STATUS_FALLBACK
                if st == L.STATUS_FAILED:
                    localized_failed += 1
                else:
                    localized_fallback += 1
                ART.write_artifact(root, "localization", k,
                                   {"news_id": nid, "src_id": it.get("src_id") or "",
                                    "display_identity": L.display_identity(it) or "",
                                    "title_cn": "", "summary_cn": "",
                                    "fallback_reason": meta.get("error") or "no_output"},
                                   schema_version=L.SCHEMA_VERSION, model=model,
                                   prompt_version=L.PROMPT_VERSION,
                                   input_hash=L.content_hash(it), status=st,
                                   source_fact_refs=[nid], data_as_of=data_as_of,
                                   # provider 传输/HTTP 失败 → 下次可重试；
                                   # schema/gate 拒绝是确定性的，同一输入不重试（§十/§二十六/§三十八）
                                   extra={"retryable": st == L.STATUS_FAILED})
                continue
            ok, reasons = (L.summary_preservation_gate(it, got) if summary_mode
                           else L.preservation_gate(it, got))
            if not ok:
                stats["gates"]["localization_fact_gate"] = "FAIL"
                localized_fallback += 1
                ART.write_artifact(root, "localization", k,
                                   {"news_id": nid, "src_id": it.get("src_id") or "",
                                    "display_identity": L.display_identity(it) or "",
                                    "title_cn": "", "summary_cn": "",
                                    "fallback_reason": "PRESERVATION_GATE_FAIL",
                                    "gate_reasons": reasons},
                                   schema_version=L.SCHEMA_VERSION, model=model,
                                   prompt_version=L.PROMPT_VERSION,
                                   input_hash=L.content_hash(it),
                                   status=L.STATUS_FALLBACK,
                                   source_fact_refs=[nid], data_as_of=data_as_of,
                                   extra={"retryable": False})
                continue
            localized_full += 1
            if summary_mode:
                # C3F §十八：**只写 summary_cn**，绝不覆盖已验证的 title_cn
                _o = {"title_cn": it.get("title_cn") or "", "summary_cn": got["summary_cn"]}
                _patch = {"summary_cn": got["summary_cn"]}
            else:
                _o = {"title_cn": got["title_cn"], "summary_cn": got["summary_cn"]}
                _patch = {"title_cn": got["title_cn"], "summary_cn": got["summary_cn"]}
            applied[nid] = _o
            for _idk in ("src_id", "display_identity"):
                if it.get(_idk):
                    applied[str(it[_idk])] = _o
            ART.write_artifact(root, "localization", k,
                               dict({"news_id": nid, "src_id": it.get("src_id") or "",
                                     "display_identity": L.display_identity(it) or ""},
                                    **_patch),
                               schema_version=L.SCHEMA_VERSION, model=model,
                               prompt_version=L.PROMPT_VERSION,
                               input_hash=L.content_hash(it), status=L.STATUS_FULL,
                               source_fact_refs=[nid], data_as_of=data_as_of)
    stats["localization"].update({"full": localized_full, "fallback": localized_fallback,
                                  "failed": localized_failed, "applied": len(applied)})

    # ── 4) 回写 article.title_cn/summary_cn（供 News Stream 展示）──
    if applied:
        n_changed = 0
        for x in articles:
            nid = x.get("article_id")
            if nid in applied:
                t = applied[nid]["title_cn"]
                s = applied[nid]["summary_cn"]
                if t and x.get("title_cn") != t:
                    x["title_cn"] = t
                    n_changed += 1
                if s and x.get("summary_cn") != s:
                    x["summary_cn"] = s
        if n_changed:
            try:
                from data.repository import Repository
                from pathlib import Path
                Repository(root=Path(root)).save_articles(
                    articles, run_id="20260919T100000+0800_c3locl")
            except Exception as e:  # noqa: BLE001
                stats["errors"].append("article_writeback_failed:%s" % e)
        stats["localization"]["articles_updated"] = n_changed

    # ── 5) Event intelligence（只 multi-source）──────────────────────
    ev_full = ev_fb = ev_low = 0
    if skip_analysis:
        stats["event"] = {"full": 0, "fallback": 0, "low_data": 0,
                          "skipped": "c3f_incremental (fact pack unchanged)"}
        clusters = []          # 不进入 Event 分析循环
    for c in clusters:
        if not A.event_is_analyzable(c):
            continue
        pack = A.build_event_fact_pack(c)
        h = A.pack_hash(pack)
        eid = c.get("event_id")
        prev = ART.read_artifact(root, "event_analysis", eid)
        if prev and prev.get("input_hash") == h and not prev.get("retryable"):
            stats["cache_hits"] += 1
            ev_full += 1 if prev.get("status") == A.STATUS_FULL else 0
            ev_fb += 0 if prev.get("status") == A.STATUS_FULL else 1
            continue
        stats["cache_misses"] += 1
        if not ready:
            A_ = A.deterministic_fallback("event", pack)
            ART.write_artifact(root, "event_analysis", eid, A_,
                               schema_version=A.SCHEMA_VERSION, model=model,
                               prompt_version=A.PROMPT_VERSION, input_hash=h,
                               status=A.STATUS_FALLBACK, source_fact_refs=[eid],
                               data_as_of=data_as_of)
            ev_fb += 1
            continue
        task = {"task_id": "ev_%s" % h, "task_type": "stage4_event_enrichment",
                "system_text": A.SYSTEM_EVENT,
                "user_text": json.dumps(pack, ensure_ascii=False)[:6000],
                "max_output_tokens": 1200}
        resp = provider.submit_task(task)
        stats["ai_calls_event"] += 1
        stats["ai_calls_total"] += 1
        res = (resp or {}).get("result") or {}
        out, errs = (A.validate_analysis_shape(json.loads(res["text"]), A.EVENT_KEYS)
                     if resp.get("status") == "succeeded" and _json_ok(res.get("text"))
                     else ({}, ["SCHEMA_FAILURE:no_text"]))
        okg, greasons = (A.analysis_fact_gate(pack, out) if not errs else (False, errs))
        if errs or not okg:
            stats["gates"]["analysis_fact_gate"] = "FAIL"
            ART.write_artifact(root, "event_analysis", eid,
                               A.deterministic_fallback("event", pack),
                               schema_version=A.SCHEMA_VERSION, model=model,
                               prompt_version=A.PROMPT_VERSION, input_hash=h,
                               status=A.STATUS_FALLBACK, source_fact_refs=[eid],
                               data_as_of=data_as_of,
                               extra={"gate_reasons": greasons[:6]})
            ev_fb += 1
        else:
            ART.write_artifact(root, "event_analysis", eid, out,
                               schema_version=A.SCHEMA_VERSION, model=model,
                               prompt_version=A.PROMPT_VERSION, input_hash=h,
                               status=A.STATUS_FULL, source_fact_refs=[eid],
                               data_as_of=data_as_of)
            ev_full += 1
    stats["event"] = {"full": ev_full, "fallback": ev_fb, "low_data": ev_low}

    # ── 6) Country intelligence ─────────────────────────────────────
    c_full = c_fb = c_low = 0
    by_country = {}
    if skip_analysis:
        countries = []         # 不进入 Country 分析循环
    for i in items:
        cn = i.get("country_cn")
        if cn:
            by_country.setdefault(cn, []).append(i)
    for cn, rows in ([] if skip_analysis else sorted(by_country.items())):
        pack = A.build_country_fact_pack(cn, rows, data_as_of=data_as_of)
        low, why_low = A.country_is_low_data(pack)
        h = A.pack_hash(pack)
        prev = ART.read_artifact(root, "country_analysis", cn)
        if prev and prev.get("input_hash") == h and not prev.get("retryable"):
            stats["cache_hits"] += 1
            if prev.get("status") == A.STATUS_FULL:
                c_full += 1
            else:
                c_low += 1
            continue
        stats["cache_misses"] += 1
        if low:
            ART.write_artifact(root, "country_analysis", cn,
                               A.low_data_placeholder("country"),
                               schema_version=A.SCHEMA_VERSION, model=model,
                               prompt_version=A.COUNTRY_PROMPT_VERSION, input_hash=h,
                               status=A.STATUS_LOW_DATA, source_fact_refs=[cn],
                               data_as_of=data_as_of, extra={"low_data_reason": why_low})
            c_low += 1
            continue
        if not ready:
            ART.write_artifact(root, "country_analysis", cn,
                               A.deterministic_fallback("country", pack),
                               schema_version=A.SCHEMA_VERSION, model=model,
                               prompt_version=A.COUNTRY_PROMPT_VERSION, input_hash=h,
                               status=A.STATUS_FALLBACK, source_fact_refs=[cn],
                               data_as_of=data_as_of)
            c_fb += 1
            continue
        task = {"task_id": "ct_%s" % h, "task_type": "stage4_event_enrichment",
                "system_text": A.SYSTEM_COUNTRY,
                "user_text": json.dumps(pack, ensure_ascii=False)[:6000],
                "max_output_tokens": 1400}
        resp = provider.submit_task(task)
        stats["ai_calls_country"] += 1
        stats["ai_calls_total"] += 1
        res = (resp or {}).get("result") or {}
        out, errs = (A.validate_analysis_shape(json.loads(res["text"]), A.COUNTRY_KEYS)
                     if resp.get("status") == "succeeded" and _json_ok(res.get("text"))
                     else ({}, ["SCHEMA_FAILURE:no_text"]))
        okg, greasons = (A.analysis_fact_gate(pack, out) if not errs else (False, errs))
        if errs or not okg:
            stats["gates"]["analysis_fact_gate"] = "FAIL"
            ART.write_artifact(root, "country_analysis", cn,
                               A.deterministic_fallback("country", pack),
                               schema_version=A.SCHEMA_VERSION, model=model,
                               prompt_version=A.COUNTRY_PROMPT_VERSION, input_hash=h,
                               status=A.STATUS_FALLBACK, source_fact_refs=[cn],
                               data_as_of=data_as_of, extra={"gate_reasons": greasons[:6]})
            c_fb += 1
        else:
            ART.write_artifact(root, "country_analysis", cn, out,
                               schema_version=A.SCHEMA_VERSION, model=model,
                               prompt_version=A.COUNTRY_PROMPT_VERSION, input_hash=h,
                               status=A.STATUS_FULL, source_fact_refs=[cn],
                               data_as_of=data_as_of)
            c_full += 1
    stats["country"] = {"full": c_full, "fallback": c_fb, "low_data": c_low,
                        "countries": len(by_country),
                        **({"skipped": "c3f_incremental (fact pack unchanged)"}
                           if skip_analysis else {})}

    # ── 7) Homepage intelligence（fact pack hash + cooldown）─────────
    # C3R2：CI 环境没有 dist/，优先读 data/views/site_overview.json（随分支提交），
    # 再回退到 dist 版本；确保 Homepage Fact Pack 拿到真实 KPI 与国家风险事实。
    # C3F §五：Homepage Fact Pack 由**统一装配函数**生成，确保前端算出的
    # homepage_fact_pack_hash 与 AI artifact 记录的 fact_pack_hash 同源可比。
    hpack = A.build_homepage_fact_pack_from_views(root)
    hhash = A.pack_hash(A.stable_pack_projection(hpack))
    prev_h = ART.read_artifact(root, "homepage_analysis", "current")
    fresh_enough = False
    if prev_h and prev_h.get("generated_at"):
        try:
            age = (datetime.now(BJ)
                   - datetime.fromisoformat(prev_h["generated_at"])).total_seconds() / 3600.0
            fresh_enough = age < a.home_cooldown_hours
        except Exception:  # noqa: BLE001
            fresh_enough = False
    if prev_h and prev_h.get("input_hash") == hhash and fresh_enough and not a.force_home:
        stats["cache_hits"] += 1
        stats["homepage"] = {"status": prev_h.get("status"), "skipped": "unchanged+cooldown"}
    else:
        stats["cache_misses"] += 1
        if not ready:
            ART.write_artifact(root, "homepage_analysis", "current",
                               A.deterministic_fallback("homepage", hpack),
                               schema_version=A.SCHEMA_VERSION, model=model,
                               prompt_version=A.HOMEPAGE_PROMPT_VERSION, input_hash=hhash,
                               status=A.STATUS_FALLBACK, source_fact_refs=["homepage"],
                               data_as_of=data_as_of,
                               extra={"fact_pack_hash": hhash,
                                      "fact_pack_version": A.HOMEPAGE_FACT_PACK_VERSION})
            stats["homepage"] = {"status": A.STATUS_FALLBACK, "fact_pack_hash": hhash}
        else:
            task = {"task_id": "hp_%s" % hhash, "task_type": "stage4_event_enrichment",
                    "system_text": A.SYSTEM_HOMEPAGE,
                    "user_text": json.dumps(hpack, ensure_ascii=False)[:6000],
                    "max_output_tokens": 1600}
            resp = provider.submit_task(task)
            stats["ai_calls_homepage"] += 1
            stats["ai_calls_total"] += 1
            res = (resp or {}).get("result") or {}
            out, errs = (A.validate_analysis_shape(json.loads(res["text"]), A.COUNTRY_KEYS)
                         if resp.get("status") == "succeeded" and _json_ok(res.get("text"))
                         else ({}, ["SCHEMA_FAILURE:no_text"]))
            okg, greasons = (A.analysis_fact_gate(hpack, out) if not errs else (False, errs))
            if errs or not okg:
                stats["gates"]["analysis_fact_gate"] = "FAIL"
                ART.write_artifact(root, "homepage_analysis", "current",
                                   A.deterministic_fallback("homepage", hpack),
                                   schema_version=A.SCHEMA_VERSION, model=model,
                                   prompt_version=A.HOMEPAGE_PROMPT_VERSION,
                                   input_hash=hhash, status=A.STATUS_FALLBACK,
                                   source_fact_refs=["homepage"], data_as_of=data_as_of,
                                   extra={"gate_reasons": greasons[:6]})
                stats["homepage"] = {"status": A.STATUS_FALLBACK}
            else:
                ART.write_artifact(root, "homepage_analysis", "current", out,
                                   schema_version=A.SCHEMA_VERSION, model=model,
                                   prompt_version=A.HOMEPAGE_PROMPT_VERSION,
                                   input_hash=hhash, status=A.STATUS_FULL,
                                   source_fact_refs=["homepage"], data_as_of=data_as_of,
                                   extra={"fact_pack_hash": hhash,
                                          "fact_pack_version": A.HOMEPAGE_FACT_PACK_VERSION})
                stats["homepage"] = {"status": A.STATUS_FULL, "fact_pack_hash": hhash}

    # C3F §二十二：聚合口径——19 条被安全拦截是 PASS_WITH_FALLBACK，不是系统故障
    _acc = localized_full
    _rej = localized_fallback
    _pf = localized_failed
    _unsafe = 0
    stats["summary_only"] = {
        "target": len(targets) if summary_mode else 0,
        "full": localized_full if summary_mode else 0,
        "fallback": localized_fallback if summary_mode else 0,
        "failed": localized_failed if summary_mode else 0,
    }
    stats["localization_pipeline"] = {
        "status": L.pipeline_status(_acc, 0, _rej, _pf, _unsafe),
        "ITEMS_ACCEPTED": _acc, "ITEMS_PARTIAL": 0,
        "ITEMS_REJECTED_BY_GATE": _rej, "ITEMS_PROVIDER_FAILED": _pf,
        "UNSAFE_OUTPUT_PUBLISHED": _unsafe,
    }
    stats["gates"]["localization_pipeline_status"] = stats["localization_pipeline"]["status"]
    stats["gates"].pop("localization_fact_gate", None)
    stats["status"] = ("HOLD_AI_CREDENTIAL_RUNTIME_REQUIRED" if not ready
                       else "OK")
    stats["news_per_localization_call"] = (round(
        stats["localization"].get("target", 0) /
        max(1, stats["ai_calls_localization"]), 2))
    with io.open(a.out, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)
    ART.write_run_report(root, "c3_%s" % datetime.now(BJ).strftime("%Y%m%dT%H%M%S"), stats)
    print(json.dumps(stats, ensure_ascii=False, indent=1)[:3000])
    print("\nwrote ->", a.out)
    return 0


def _json_ok(text):
    try:
        json.loads(text)
        return True
    except Exception:  # noqa: BLE001
        return False


if __name__ == "__main__":
    raise SystemExit(main())
