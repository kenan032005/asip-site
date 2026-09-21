#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report_ai.py — C4-C 报告 AI enrichment（真实 DeepSeek analysis，server-side only）。

复用既有报告 AI 资产，不另造一套：
  * prompt        → scripts.report.gen.analysis_contract.build_analysis_prompt
  * 分析事实闸门  → scripts.report.gen.analysis_contract.validate_analysis
  * 机器闸门      → scripts.report.gen.deterministic_assembler.machine_gates
  * provider      → scripts.report.gen.providers.make_provider（auto → 有 key 用 DeepSeek）

策略：
  * **LOW_DATA 不调用 AI**（保持确定性报告，绝不为凑数强调）
  * SOURCE_BACKED_ONLY 不变：AI fact pack 只含 source-backed facts
  * **AI fact pack 必须通过 eligibility**（内容 / 来源 / 时间 / 国家 scope / report type）：
    空壳或无来源事实一律排除，绝不把空 JSON 结构送给模型
  * cache = artifact 自身：status=FULL 且 input_hash 一致 → 命中（0 调用）
    负缓存 = artifact 记录 ai_negative_input_hash（gate 拒绝的终态，0 调用）
  * 每份报告最多 1 次 analysis call

provider 契约（§一 KEEP_STAGE7B_PROVIDER_CONTRACT）：
  * 只使用 **Stage 7B 契约 `provider.generate(system, user)`**
    （`scripts/report/gen/providers.py`；mock 返回 `(text, meta)`）
  * **不得**依赖 `submit_task(task)`（那是 `scripts/ai/**` 的 BaseAIProvider 家族接口；
    误用时真实 provider 会抛 AttributeError，且**不会**被 fixture 测试发现）
  * provider 级系统故障（契约不匹配/凭据/鉴权/模型/全局不可用）会让整批 **FAIL**，
    绝不被逐份 guard 吞成「6 个独立 FALLBACK + workflow green」的假成功
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.report import factory as F                      # noqa: E402
from scripts.report import materialize as M                  # noqa: E402
from scripts.report.gen import analysis_contract as AC       # noqa: E402
from scripts.report.gen import deterministic_assembler as DA  # noqa: E402
from scripts.report.gen import providers as P                # noqa: E402
from scripts.report import fact_content as FC               # noqa: E402

PROMPT_VERSION = "analysis-v1.0.0"
MODEL = "deepseek-flash"
AI_FIELDS = ("executive_assessment", "trend_analysis", "outlook", "watch_points")

#: AI fact pack 过滤契约版本 —— 参与 cache identity；改动过滤规则必须 bump，
#: 否则同一 input_hash 会复用按旧规则生成的缓存正文。
AI_PACK_VERSION = "ai-pack-v1"

STATUS_FULL = "FULL"
STATUS_FALLBACK = "FALLBACK"
STATUS_LOW_DATA = "LOW_DATA"
STATUS_FAIL = "FAIL"


def ai_input_hash(report_id, fact_pack_hash, model=MODEL, prompt_version=PROMPT_VERSION):
    """cache identity = report_id + fact_pack_hash + prompt_version(+pack 过滤版本) + model。"""
    return F.input_hash(report_id, fact_pack_hash, model, "report_analysis",
                        "%s+%s" % (prompt_version, AI_PACK_VERSION))


#: AI 目标规则。
#:   'eligibility' —— §十七：**有 ≥1 条通过 eligibility 的合法事实**即可分析，
#:                    与 LOW_DATA 标签解耦（标签仍按事实数阈值给用户看）。
#:   'status'      —— 旧规则：status != LOW_DATA 才分析（会因空壳事实膨胀而误判）。
#: 采用 status 的理由：§四「LOW_DATA 不调用 AI」是产品语义（标签由事实数阈值决定），
#: 而 §十七 的 `AI_TARGET_REPORTS_ACTUAL` 在此之上按 **eligibility** 再收敛：
#: 标签为 FALLBACK 但严格过滤后没有任何合法事实的报告会被
#: materialize 重新分类为 LOW_DATA（见 materialize.reclassify_by_ai_eligibility），
#: 因此「标签」与「可分析」两者最终一致，不存在 LOW_DATA 却调用 AI 的情况。
AI_TARGETING_RULE = "status"


# ── §五 Target Planner（只读）─────────────────────────────────────────────
def plan_targets(root, with_eligibility=True):
    """计算 AI 目标（只读）。

    §十七：目标是**通过严格 eligibility 后仍有 ≥1 条合法事实**的报告。
    没有合法事实的报告保持 LOW_DATA 标签，绝不为了凑数塞脏数据。
    """
    reports = M.list_report_artifacts(root)
    low, cached, negative, eligible = [], [], [], []
    for r in reports:
        st = r.get("status")
        ih = ai_input_hash(r.get("report_id"), r.get("fact_pack_hash"))
        if st == STATUS_FULL and r.get("ai_input_hash") in (None, ih):
            cached.append(r)
            continue
        if r.get("ai_negative_input_hash") == ih:
            negative.append(r)
            continue
        if AI_TARGETING_RULE == "status" and (st == STATUS_LOW_DATA
                                              or not (r.get("fact_count") or 0)):
            low.append(r)
            continue
        eligible.append(r)
    plan = {
        "TOTAL_REPORTS": len(reports),
        "LOW_DATA_REPORTS": len([r for r in reports if r.get("status") == STATUS_LOW_DATA]),
        "ALREADY_CACHED_REPORTS": len(cached),
        "NEGATIVE_CACHED_REPORTS": len(negative),
        "FULL_ELIGIBLE_REPORTS": len(eligible),
        "AI_TARGETING_RULE": AI_TARGETING_RULE,
        "target_ids": [r.get("report_id") for r in eligible],
        "low_data_ids": [r.get("report_id") for r in low],
    }
    if with_eligibility:
        actual, empty = [], []
        for r in eligible:
            fp, _ = rebuild_fact_pack(root, r)
            n = 0
            if fp:
                _ai, d = build_ai_fact_pack(fp, r)
                n = d["AI_PACK_FACTS_TOTAL"]
            (actual if n else empty).append(r.get("report_id"))
        plan["AI_TARGET_REPORTS"] = len(actual)
        plan["AI_TARGET_REPORTS_ACTUAL"] = len(actual)
        plan["AI_TARGET_IDS_ACTUAL"] = actual
        plan["AI_TARGETS_WITHOUT_ELIGIBLE_FACTS"] = empty
        plan["EXPECTED_REAL_AI_CALLS_MAX"] = len(actual)
    else:
        plan["AI_TARGET_REPORTS"] = len(eligible)
        plan["EXPECTED_REAL_AI_CALLS_MAX"] = len(eligible)
    return plan


# ── fact pack 重建（确定性；hash 必须与 artifact 一致）──────────────────
def rebuild_fact_pack(root, report):
    """按报告期重建 fact pack；返回 (pack, hash)。hash 与 artifact 不一致视为 DIRTY。"""
    rtype = report.get("report_type")
    events = M.load_canonical_events(root)
    disease = M.load_disease_items(root)
    iso = M.iso2to3_map(root)
    if rtype == "africa_daily":
        tgt = {"report_date": report.get("report_date") or str(report.get("period_end"))[:10],
               "report_id": report.get("report_id")}
        _rep, fp = M.materialize_daily(root, tgt, events, disease, iso)
        return fp, F.report_pack_hash(fp)
    if rtype == "africa_weekly":
        wk = {"report_id": report.get("report_id"), "week_start": report.get("week_start"),
              "week_end": report.get("week_end")}
        _rep, fp = M.materialize_africa_weekly(root, wk, events, disease, iso)
        return fp, F.report_pack_hash(fp)
    if rtype == "country_weekly":
        tgt = {"report_id": report.get("report_id"), "country_iso3": report.get("country_iso3"),
               "week_start": report.get("week_start"), "week_end": report.get("week_end"),
               "selection_reason": report.get("selection_reason")}
        _rep, fp = M.materialize_country_weekly(root, tgt, events, disease, iso)
        return fp, F.report_pack_hash(fp)
    return None, None


# ── §八–§十二 AI Fact Pack Eligibility ──────────────────────────────────
# 判定口径全部委托给 scripts/report/fact_content.py（报告层与 AI 层共用一套，
# 不允许再出现两套「什么算有内容/有来源/在 scope 内」的定义）。
DISEASE_SCOPE_BY_TYPE = FC.DISEASE_SCOPE_BY_TYPE
_fact_has_content = FC.has_displayable_content
_fact_sources = FC.fact_sources
_fact_countries = FC.fact_countries
_fact_window_state = FC.fact_window_state
_report_countries = FC.report_countries


def build_ai_fact_pack(fp, report):
    """§八–§十二：构造**真正进入 AI** 的 fact pack（原 pack 不被修改）。

    每条事实必须同时通过：① 有可展示内容 ② 有真实 source_refs
    ③ 时间窗口匹配（若声明了日期）④ 国家 scope 匹配 ⑤ report type scope 匹配。
    逐条评估**全部**判据（不短路）并分别计数；空壳事实绝不会被送进 prompt。

    §十二：过滤后**重新计算**派生字段（source_refs / entity_vocab / country_vocab /
    numeric_provenance / date provenance / 计数），不沿用过滤前集合 ——
    这样 machine gates 只允许模型实际看见的事实。

    返回 (ai_pack, diagnostics)。
    """
    rtype = report.get("report_type")
    scope = DISEASE_SCOPE_BY_TYPE.get(rtype, "region")
    rc = _report_countries(report)
    diag = {}

    def _bump(k):
        diag[k] = diag.get(k, 0) + 1

    kept = {}
    for kind, key in (("SOCIAL", "social_facts"), ("DISEASE", "disease_facts")):
        cand = list(fp.get(key) or [])
        diag["%s_FACTS_CANDIDATE" % kind] = len(cand)
        keep = []
        for f in cand:
            reasons = FC.fact_eligibility(f, report, kind)   # 单一判定口径
            if not reasons and FC.fact_window_state(f, report) is None:
                _bump("%s_FACTS_TIME_UNVERIFIED" % kind)
            for r in reasons:
                _bump("%s_FACTS_EXCLUDED_%s" % (kind, r))
            if reasons:
                continue
            keep.append(f)
        diag["%s_FACTS_INCLUDED" % kind] = len(keep)
        diag["%s_FACTS_EXCLUDED" % kind] = len(cand) - len(keep)
        kept[key] = keep

    ai_fp = dict(fp)
    ai_fp["social_facts"] = [dict(f) for f in kept["social_facts"]]
    ai_fp["disease_facts"] = [dict(f) for f in kept["disease_facts"]]
    included = ai_fp["social_facts"] + ai_fp["disease_facts"]

    # §十二 派生字段重算（不沿用过滤前集合）
    vocab, country_vocab, numeric_prov, dates = set(), set(), {}, []
    for f in included:
        vocab |= set(FC.fact_sources(f))
        cs = FC.fact_countries(f)
        vocab |= cs
        country_vocab |= cs
        for st in (f.get("headline_zh"), f.get("verified_summary"), f.get("location")):
            if isinstance(st, str) and st.strip():
                vocab.add(st.strip())
        if f.get("fact_id"):
            vocab.add(str(f["fact_id"]))
        for n, paths in (f.get("numeric_facts") or {}).items():
            try:
                numeric_prov.setdefault(int(n), []).extend(paths or [])
            except (TypeError, ValueError):
                continue
        for k in ("report_date", "event_time", "event_start_date"):
            v = f.get(k)
            if isinstance(v, str) and len(v) >= 10:
                dates.append(v[:10])
    ai_fp["entity_vocab"] = sorted(vocab)
    ai_fp["country_vocab"] = sorted(country_vocab)
    ai_fp["numeric_provenance"] = numeric_prov
    ai_fp["date_provenance"] = sorted(set(dates + [
        str(x)[:10] for x in (fp.get("week_start"), fp.get("week_end"),
                              fp.get("period_start"), fp.get("period_end"),
                              fp.get("report_date")) if x]))
    ai_fp["source_refs"] = [s for s in (fp.get("source_refs") or []) if s in vocab] \
        or sorted(vocab)
    ai_fp["fact_count"] = len(included)
    ai_fp["social_fact_count"] = len(ai_fp["social_facts"])
    ai_fp["disease_fact_count"] = len(ai_fp["disease_facts"])

    # §十三/§十四 硬门指标 —— 一律在**输出 pack** 上真实统计，而不是靠过滤逻辑自证
    diag["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"] = len(ai_fp["disease_facts"])
    diag["DISEASE_FACTS_EXCLUDED_FROM_AI_FACT_PACK"] = \
        len(fp.get("disease_facts") or []) - len(ai_fp["disease_facts"])
    diag["AI_PACK_FACTS_TOTAL"] = len(included)
    diag["UNATTRIBUTED_FACTS_IN_AI_FACT_PACK"] = sum(
        1 for f in included if not FC.fact_sources(f))
    diag["EMPTY_FACTS_IN_AI_FACT_PACK"] = sum(
        1 for f in included if not FC.has_displayable_content(f))
    diag["CROSS_COUNTRY_FACTS_IN_COUNTRY_WEEKLY"] = (
        sum(1 for f in included if FC.fact_countries(f) and not (FC.fact_countries(f) & rc))
        if rtype == "country_weekly" else 0)
    # §2 报告层 / AI 层国家边界必须一致：报告 pack 里的跨国事实应为 0
    # （报告层已在 build 阶段用同一 country_scope_ok 过滤）
    _report_facts = (fp.get("social_facts") or []) + (fp.get("disease_facts") or [])
    diag["CROSS_COUNTRY_FACTS_IN_REPORT_PACK"] = len(
        FC.cross_country_facts(_report_facts, report))
    diag["CROSS_COUNTRY_FACTS_IN_AI_FACT_PACK"] = len(
        FC.cross_country_facts(included, report))
    diag["REPORT_AI_SCOPE_PARITY"] = bool(
        diag["CROSS_COUNTRY_FACTS_IN_REPORT_PACK"] == 0
        and diag["CROSS_COUNTRY_FACTS_IN_AI_FACT_PACK"] == 0
        and diag.get("SOCIAL_FACTS_EXCLUDED_SCOPE", 0) == 0
        and diag.get("DISEASE_FACTS_EXCLUDED_SCOPE", 0) == 0)
    diag["FAKE_SOURCE_REFS"] = sum(
        1 for f in included for s in FC.fact_sources(f)
        if str(s).lower() in ("source_unknown", "unknown", "n/a", "na")
        or str(s).startswith("synthetic") or str(s).startswith("disease_source_0"))
    diag["AI_PACK_COUNTRIES"] = sorted(country_vocab)

    # §二十 本地化缺口单独统计（不混成 C4 失败）
    s_zh = sum(1 for f in ai_fp["social_facts"]
               if str(f.get("content_source_field") or "").endswith("_cn"))
    s_or = sum(1 for f in ai_fp["social_facts"]
               if str(f.get("content_source_field") or "").endswith("_original"))
    d_zh = sum(1 for f in ai_fp["disease_facts"]
               if str(f.get("content_source_field") or "") in ("disease_name_zh", "disease_name_cn"))
    d_en = sum(1 for f in ai_fp["disease_facts"]
               if str(f.get("content_source_field") or "") == "disease_name_en")
    diag["SOCIAL_FACTS_USING_TITLE_CN"] = s_zh
    diag["SOCIAL_FACTS_USING_TITLE_ORIGINAL"] = s_or
    diag["SOCIAL_FACTS_EXCLUDED_NO_CONTENT"] = diag.get("SOCIAL_FACTS_EXCLUDED_NO_CONTENT", 0)
    diag["DISEASE_FACTS_USING_CN_NAME"] = d_zh
    diag["DISEASE_FACTS_USING_EN_NAME"] = d_en
    diag["C5_LOCALIZATION_COMPLETENESS_DEBT"] = bool(
        s_or or d_en or diag["SOCIAL_FACTS_EXCLUDED_NO_CONTENT"])

    # 兼容既有命名（同一数字，避免下游/测试两套口径）
    diag["DISEASE_FACTS_EXCLUDED_CROSS_COUNTRY"] = diag.get("DISEASE_FACTS_EXCLUDED_SCOPE", 0)
    diag["SOCIAL_FACTS_EXCLUDED_NO_CONTENT"] = diag.get("SOCIAL_FACTS_EXCLUDED_NO_CONTENT", 0)
    diag["DISEASE_FACTS_EXCLUDED_NO_CONTENT"] = diag.get("DISEASE_FACTS_EXCLUDED_NO_CONTENT", 0)
    diag["DISEASE_FACTS_EXCLUDED_NO_SOURCE"] = diag.get("DISEASE_FACTS_EXCLUDED_NO_SOURCE", 0)
    return ai_fp, diag


# ── Provider 契约（§一–§三）─────────────────────────────────────────────
class SystemicProviderFailure(RuntimeError):
    """provider 级系统故障：契约不匹配 / 凭据缺失 / 鉴权失败 / 模型非法 / 全局不可用。

    §七：这类故障必须让**整批** FAIL，不得被逐份 guard 吞成
    「6 份独立 PROVIDER_EXCEPTION，但 workflow 最终 green」的假成功。
    """


class ProviderResponseFormatError(ValueError):
    """单份响应格式不合法 —— **报告级**故障（其余报告继续处理）。"""


#: 直接判定为系统级故障的异常类名（provider 自身配置/模型非法）
_SYSTEMIC_ERROR_NAMES = frozenset((
    "UnsupportedDeepSeekModelError", "ProviderConfigError", "ConfigurationError",
))
#: 系统级故障错误码/文案标记（§七：凭据 / 鉴权 / 限流 / 5xx / 连接不可达 / 契约不匹配）。
#: 注意 `ProviderUnavailable` 本身**不**整体视为系统级——它也被用来表达
#: 「该份输入无法处理」这类报告级问题，必须按文案区分。
_SYSTEMIC_MARKERS = (
    "credential_unavailable", "missing api key", "invalid api key", "invalid_api_key",
    "unsupported_deepseek_model",
    "http_401", "http_403", "http_404", "http_408", "http_429", "http_5",
    "authentication", "unauthorized", "forbidden",
    "connection refused", "connection reset", "timed out", "timeout",
    "temporary failure in name resolution", "unreachable",
    "provider contract",
)


def is_systemic_provider_failure(exc):
    """系统级 provider 故障判定（§七）。"""
    if isinstance(exc, SystemicProviderFailure):
        return True
    if type(exc).__name__ in _SYSTEMIC_ERROR_NAMES:
        return True
    s = str(exc).lower()
    return any(m in s for m in _SYSTEMIC_MARKERS)


def normalize_provider_response(raw):
    """把 Stage 7B provider 返回归一化为 {status, result:{text,...}}。

    合法形状（既有契约）：
      * ``(text, meta)`` —— ``MockReportProvider`` / ``DeepSeekReportProvider.generate``
      * ``{status, result}`` —— 已归一化的任务式返回（测试替身可用）
    其它形状 → ProviderResponseFormatError（报告级）。
    """
    if isinstance(raw, dict):
        if "status" in raw:
            return raw
        text = raw.get("text")
        if text is None:
            text = raw.get("content")
        if isinstance(text, str):
            return {"status": "succeeded",
                    "result": {"text": text,
                               "returned_model": raw.get("model") or raw.get("returned_model"),
                               "finish_reason": raw.get("finish_reason")}}
        raise ProviderResponseFormatError("dict response without text/status")
    if isinstance(raw, (tuple, list)) and len(raw) == 2 and isinstance(raw[0], str):
        text, meta = raw
        meta = meta if isinstance(meta, dict) else {}
        return {"status": "succeeded",
                "result": {"text": text, "returned_model": meta.get("model"), "meta": meta}}
    if isinstance(raw, str):
        return {"status": "succeeded", "result": {"text": raw}}
    raise ProviderResponseFormatError(
        "unsupported provider response type: %s" % type(raw).__name__)


def invoke_report_provider(provider, task):
    """C4 边界薄适配：task dict → **Stage 7B 契约** ``provider.generate(system, user)``。

    §一 不新增 submit_task、不改 ``scripts/report/gen/providers.py``；
    §三 只做 task → (system, user) 与响应归一化 —— HTTP / 鉴权 / 模型路由 /
    重试 / 超时 / JSON 解析继续由既有 provider 负责，这里不复制任何 provider 逻辑。
    """
    gen = getattr(provider, "generate", None)
    if not callable(gen):
        raise SystemicProviderFailure(
            "PROVIDER_CONTRACT_MISMATCH: %s 未实现 generate(system, user)"
            % type(provider).__name__)
    res = gen(task.get("system_text") or "", task.get("user_text") or "")
    return normalize_provider_response(res)


def _unattributed_in_pack(fp):
    """§十二：AI fact pack 里不得出现无来源事实。"""
    n = 0
    for f in (fp.get("social_facts") or []) + (fp.get("disease_facts") or []):
        if not _fact_sources(f):
            n += 1
    return n


# ── 单份报告 enrichment ─────────────────────────────────────────────────
def enrich_one(root, report, provider=None, write=True, fact_pack=None):
    """返回 (outcome_dict)。outcome: SKIPPED_LOW_DATA / CACHED_FULL / CACHED_NEGATIVE /
    CALLED_FULL / CALLED_FALLBACK / FACT_PACK_DIRTY。"""
    rid = report.get("report_id")
    st = report.get("status")
    out = {"report_id": rid, "old_status": st, "ai_call": 0, "gate_result": None,
           "new_status": st, "report_type": report.get("report_type")}

    if st == STATUS_LOW_DATA or not (report.get("fact_count") or 0):
        out["outcome"] = "SKIPPED_LOW_DATA"          # §四
        return out

    if fact_pack is not None:
        fp, fph = fact_pack, F.report_pack_hash(fact_pack)
    else:
        fp, fph = rebuild_fact_pack(root, report)
    if fp is None:
        out["outcome"] = "FACT_PACK_DIRTY"
        out["gate_result"] = "NO_FACT_PACK"
        return out
    if fph != report.get("fact_pack_hash"):
        out["outcome"] = "FACT_PACK_DIRTY"
        out["gate_result"] = "HASH_MISMATCH"
        out["expected_hash"] = report.get("fact_pack_hash")
        out["rebuilt_hash"] = fph
        return out

    ih = ai_input_hash(rid, fph)
    if st == STATUS_FULL and report.get("ai_input_hash") in (None, ih):
        out["outcome"] = "CACHED_FULL"               # §七
        return out
    if report.get("ai_negative_input_hash") == ih:
        out["outcome"] = "CACHED_NEGATIVE"           # §八
        return out

    # §八–§十二：先做 AI fact pack eligibility，空壳/无来源事实绝不进入 prompt
    ai_fp, pdiag = build_ai_fact_pack(fp, report)
    out["pack_diag"] = pdiag
    if int(pdiag["AI_PACK_FACTS_TOTAL"]) == 0:
        out["outcome"] = "SKIPPED_EMPTY_AI_PACK"      # §九：不把空 JSON 结构送给 AI
        out["gate_result"] = "EMPTY_AI_FACT_PACK"
        return out

    try:
        prov = provider or P.make_provider()
    except Exception as e:  # noqa: BLE001
        if is_systemic_provider_failure(e):
            raise SystemicProviderFailure(
                "%s: %s" % (type(e).__name__, str(e)[:200])) from e
        raise
    try:
        sys_text, user_text = AC.build_analysis_prompt(ai_fp, max_facts=12)
    except Exception as e:  # noqa: BLE001
        out["outcome"] = "CALLED_FALLBACK"
        out["gate_result"] = "PROMPT_BUILD_FAILED"
        out["error"] = "%s: %s" % (type(e).__name__, e)
        return out
    task = {"task_id": "REPORT_AI_%s" % rid, "task_type": "report_analysis",
            "prompt_version": PROMPT_VERSION, "system_text": sys_text,
            "user_text": user_text, "usage_purpose": "report_materialization",
            "max_output_tokens": 1024}
    try:
        res = invoke_report_provider(prov, task)     # §一/§二：generate(system, user)
    except Exception as e:  # noqa: BLE001
        if is_systemic_provider_failure(e):
            # §七：系统级故障必须冒泡让整批 FAIL
            raise SystemicProviderFailure(
                "PROVIDER_SYSTEMIC_FAILURE: %s: %s"
                % (type(e).__name__, str(e)[:200])) from e
        out["ai_call"] = 1
        out["provider_failed"] = True                # 只统计 provider 级失败
        out["outcome"] = "CALLED_FALLBACK"
        out["gate_result"] = ("PROVIDER_RESPONSE_INVALID"
                              if isinstance(e, ProviderResponseFormatError)
                              else "PROVIDER_EXCEPTION")
        out["error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
        _persist(root, report, write, extra={"ai_last_error": out["error"]})
        return out
    out["ai_call"] = 1
    rr = (res or {}).get("result") or {}
    raw = rr.get("text") or ""
    if (res or {}).get("status") != "succeeded":
        out["outcome"] = "CALLED_FALLBACK"
        out["gate_result"] = "PROVIDER_FAILED"
        out["error"] = ((rr.get("error") or {}).get("code")) or "provider_failed"
        _persist(root, report, write, extra={"ai_negative_input_hash": None,
                                             "ai_last_error": out["error"]})
        return out

    okp, parsed, jerr = _strict_json(raw)
    if not okp:
        out["outcome"] = "CALLED_FALLBACK"
        out["gate_result"] = "SCHEMA_FAILURE"
        out["error"] = jerr
        _persist(root, report, write, extra={"ai_negative_input_hash": ih,
                                             "ai_negative_reason": "SCHEMA_FAILURE"})
        return out

    try:
        ok, errs = AC.validate_analysis(parsed, ai_fp)   # gate 只看模型真正收到的 pack
    except Exception as e:  # noqa: BLE001
        ok, errs = False, ["GATE_EXCEPTION: %s" % type(e).__name__]
    if ok:
        out["gate_result"] = "PASS"
    else:
        # 区分「结构不合规」与「事实越界」——两者都拒绝，但诊断口径不同
        schema_only = bool(errs) and all(str(e).startswith("analysis schema:") for e in errs)
        out["gate_result"] = "SCHEMA_FAILURE" if schema_only else "FACT_GATE_REJECTED"
    if not ok:
        out["outcome"] = "CALLED_FALLBACK"
        out["gate_errors"] = errs[:5]
        _persist(root, report, write, extra={"ai_negative_input_hash": ih,
                                             "ai_negative_reason": out["gate_result"]})
        return out

    merged = dict(report)
    for k in AI_FIELDS:
        merged[k] = parsed.get(k)
    merged["status"] = STATUS_FULL
    merged["ai_input_hash"] = ih
    merged["ai_model"] = MODEL
    merged["ai_prompt_version"] = PROMPT_VERSION
    merged["report_status_cn"] = M._status_cn(STATUS_FULL)
    if merged.get("report_type") == "country_weekly":
        merged["executive_assessment"] = parsed.get("executive_assessment")
        merged["security_trend"] = parsed.get("trend_analysis")
        merged["next_week_watch_items"] = parsed.get("watch_points") or []
    merged["overall_assessment"] = parsed.get("executive_assessment")
    out["outcome"] = "CALLED_FULL"
    out["new_status"] = STATUS_FULL
    _persist(root, merged, write)
    return out


def _strict_json(raw):
    t = (raw or "").strip()
    if not t:
        return False, None, "empty_content"
    if t.startswith("```"):
        t = t.strip("`")
        t = t.split("\n", 1)[1] if "\n" in t else t
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        t = t[i:j + 1]
    try:
        return True, json.loads(t), None
    except Exception as e:  # noqa: BLE001
        return False, None, "invalid_json:%s" % type(e).__name__


def _persist(root, report, write, extra=None):
    if not write:
        return
    doc = dict(report)
    if extra:
        doc.update({k: v for k, v in extra.items() if v is not None})
    M.write_report_artifact(root, report.get("report_type"), doc)


# ── 批量 ────────────────────────────────────────────────────────────────
def _empty_pack_stats():
    return {"UNATTRIBUTED_FACTS_IN_AI_FACT_PACK": 0, "EMPTY_FACTS_IN_AI_FACT_PACK": 0,
            "CROSS_COUNTRY_FACTS_IN_COUNTRY_WEEKLY": 0, "FAKE_SOURCE_REFS": 0,
            "AI_PACK_FACTS_TOTAL": 0,
            "DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK": 0,
            "DISEASE_FACTS_EXCLUDED_FROM_AI_FACT_PACK": 0,
            "SOCIAL_FACTS_CANDIDATE": 0, "DISEASE_FACTS_CANDIDATE": 0,
            "SOCIAL_FACTS_INCLUDED": 0, "SOCIAL_FACTS_EXCLUDED": 0,
            "SOCIAL_FACTS_EXCLUDED_NO_CONTENT": 0, "SOCIAL_FACTS_EXCLUDED_NO_SOURCE": 0,
            "SOCIAL_FACTS_EXCLUDED_SCOPE": 0, "SOCIAL_FACTS_EXCLUDED_OUT_OF_WINDOW": 0,
            "DISEASE_FACTS_EXCLUDED_NO_CONTENT": 0, "DISEASE_FACTS_EXCLUDED_NO_SOURCE": 0,
            "DISEASE_FACTS_EXCLUDED_SCOPE": 0, "DISEASE_FACTS_EXCLUDED_OUT_OF_WINDOW": 0,
            "SOCIAL_FACTS_USING_TITLE_CN": 0, "SOCIAL_FACTS_USING_TITLE_ORIGINAL": 0,
            "DISEASE_FACTS_USING_CN_NAME": 0, "DISEASE_FACTS_USING_EN_NAME": 0,
            "C5_LOCALIZATION_COMPLETENESS_DEBT": False}


def enrich_all(root, provider=None, write=True, limit=None, fact_pack_map=None):
    plan = plan_targets(root, with_eligibility=False)
    stats = {"TOTAL_REPORTS": plan["TOTAL_REPORTS"],
             "LOW_DATA_REPORTS": plan["LOW_DATA_REPORTS"],
             "AI_TARGET_REPORTS": plan["AI_TARGET_REPORTS"],
             "AI_TARGET_REPORTS_ACTUAL": 0,
             "EXPECTED_REAL_AI_CALLS_MAX": plan["EXPECTED_REAL_AI_CALLS_MAX"],
             "AI_CALLS_TOTAL": 0, "AI_CALLS_DAILY": 0, "AI_CALLS_AFRICA_WEEKLY": 0,
             "AI_CALLS_COUNTRY_WEEKLY": 0, "FULL": 0, "FALLBACK": 0,
             "LOW_DATA": 0, "FAIL": 0, "FACT_GATE_REJECTIONS": 0,
             "ATTRIBUTION_GATE_REJECTIONS": 0,
             "PROVIDER_BOUNDARY_REACHED": 0, "GENERATE_CALLS": 0,
             "SKIPPED_EMPTY_AI_PACK": 0, "SUBMIT_TASK_CALLS": 0,
             "SYSTEMIC_PROVIDER_FAILURE": False, "SYSTEMIC_PROVIDER_FAILURE_REASON": None,
             "PROVIDER_CALLS_FAILED": 0, "pack_audit": {},
             "outcomes": {}}
    stats.update(_empty_pack_stats())
    try:
        prov = provider or P.make_provider()
    except Exception as e:  # noqa: BLE001 §七：provider 构造失败属系统级
        stats["SYSTEMIC_PROVIDER_FAILURE"] = True
        stats["SYSTEMIC_PROVIDER_FAILURE_REASON"] = "PROVIDER_INIT_FAILED: %s: %s" % (
            type(e).__name__, str(e)[:200])
        return stats
    ids = plan["target_ids"][:limit] if limit else plan["target_ids"]
    key = {"africa_daily": "AI_CALLS_DAILY", "africa_weekly": "AI_CALLS_AFRICA_WEEKLY",
           "country_weekly": "AI_CALLS_COUNTRY_WEEKLY"}
    for rid in ids:
        rtype = None
        for t in ("africa_daily", "africa_weekly", "country_weekly"):
            r = M.read_report_artifact(root, t, rid)
            if r:
                rtype = t
                rep = r
                break
        if not rtype:
            continue
        if fact_pack_map and rid in fact_pack_map:
            fp = fact_pack_map[rid]
        else:
            fp, _ = rebuild_fact_pack(root, rep)
        if fp:
            # §十四/§十六：硬门指标一律基于**真正进入 prompt 的** pack 统计
            ai_fp, pdiag = build_ai_fact_pack(fp, rep)
            stats["pack_audit"][rid] = {
                "report_type": rtype,
                "fact_count": rep.get("fact_count"),
                "ai_pack_facts": pdiag["AI_PACK_FACTS_TOTAL"],
                "disease_facts_included": pdiag["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"],
                "disease_facts_excluded": pdiag["DISEASE_FACTS_EXCLUDED_FROM_AI_FACT_PACK"],
                "countries": pdiag["AI_PACK_COUNTRIES"],
            }
            if pdiag["AI_PACK_FACTS_TOTAL"] > 0:
                stats["AI_TARGET_REPORTS_ACTUAL"] += 1
            for k in ("UNATTRIBUTED_FACTS_IN_AI_FACT_PACK", "EMPTY_FACTS_IN_AI_FACT_PACK",
                      "CROSS_COUNTRY_FACTS_IN_COUNTRY_WEEKLY", "FAKE_SOURCE_REFS",
                      "AI_PACK_FACTS_TOTAL", "DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK",
                      "DISEASE_FACTS_EXCLUDED_FROM_AI_FACT_PACK", "SOCIAL_FACTS_CANDIDATE",
                      "DISEASE_FACTS_CANDIDATE", "SOCIAL_FACTS_INCLUDED",
                      "SOCIAL_FACTS_EXCLUDED", "SOCIAL_FACTS_EXCLUDED_NO_CONTENT",
                      "SOCIAL_FACTS_EXCLUDED_NO_SOURCE", "SOCIAL_FACTS_EXCLUDED_SCOPE",
                      "SOCIAL_FACTS_EXCLUDED_OUT_OF_WINDOW",
                      "DISEASE_FACTS_EXCLUDED_NO_CONTENT",
                      "DISEASE_FACTS_EXCLUDED_NO_SOURCE", "DISEASE_FACTS_EXCLUDED_SCOPE",
                      "DISEASE_FACTS_EXCLUDED_OUT_OF_WINDOW", "SOCIAL_FACTS_USING_TITLE_CN",
                      "SOCIAL_FACTS_USING_TITLE_ORIGINAL", "DISEASE_FACTS_USING_CN_NAME",
                      "DISEASE_FACTS_USING_EN_NAME"):
                if k in pdiag:
                    stats[k] += pdiag[k]
            stats["C5_LOCALIZATION_COMPLETENESS_DEBT"] = (
                stats["C5_LOCALIZATION_COMPLETENESS_DEBT"]
                or pdiag["C5_LOCALIZATION_COMPLETENESS_DEBT"])
        try:
            o = enrich_one(root, rep, provider=prov, write=write,
                           fact_pack=(fact_pack_map or {}).get(rid))
        except SystemicProviderFailure as e:
            # §七/§十八：系统级故障 —— 停止继续调用，整批 FAIL（不再伪装成逐份失败）
            stats["SYSTEMIC_PROVIDER_FAILURE"] = True
            stats["SYSTEMIC_PROVIDER_FAILURE_REASON"] = str(e)[:300]
            stats["PROVIDER_CALLS_FAILED"] += 1
            stats["outcomes"]["SYSTEMIC_FAILURE_ABORT"] = \
                stats["outcomes"].get("SYSTEMIC_FAILURE_ABORT", 0) + 1
            break
        except Exception as e:  # noqa: BLE001 单份异常不得中断整批
            o = {"report_id": rid, "old_status": rep.get("status"), "ai_call": 0,
                 "gate_result": "UNEXPECTED_EXCEPTION", "new_status": rep.get("status"),
                 "outcome": "CALLED_FALLBACK",
                 "error": "%s: %s" % (type(e).__name__, str(e)[:200]),
                 "report_type": rtype}
        if o["ai_call"]:
            stats["PROVIDER_BOUNDARY_REACHED"] += 1
            stats["GENERATE_CALLS"] += 1
            if o.get("provider_failed"):
                stats["PROVIDER_CALLS_FAILED"] += 1
        if o["outcome"] == "SKIPPED_EMPTY_AI_PACK":
            stats["SKIPPED_EMPTY_AI_PACK"] += 1
        stats["outcomes"][o["outcome"]] = stats["outcomes"].get(o["outcome"], 0) + 1
        stats["AI_CALLS_TOTAL"] += o["ai_call"]
        if o["ai_call"]:
            stats[key.get(rtype, "AI_CALLS_TOTAL")] += 1
        if o["gate_result"] == "FACT_GATE_REJECTED":
            stats["FACT_GATE_REJECTIONS"] += 1
        if o["gate_result"] == "ATTRIBUTION_GATE_REJECTED":
            stats["ATTRIBUTION_GATE_REJECTIONS"] += 1
    # §七：全体 provider 调用**一致失败**（同一错误码）也是系统级故障，
    # 不得因为「每份都能单独报个 FALLBACK」就判整体通过。
    if (not stats["SYSTEMIC_PROVIDER_FAILURE"] and stats["GENERATE_CALLS"] > 0
            and stats["PROVIDER_CALLS_FAILED"] == stats["GENERATE_CALLS"]):
        stats["SYSTEMIC_PROVIDER_FAILURE"] = True
        stats["SYSTEMIC_PROVIDER_FAILURE_REASON"] = "UNIFORM_PROVIDER_FAILURE: %d/%d 次调用全部失败" % (
            stats["PROVIDER_CALLS_FAILED"], stats["GENERATE_CALLS"])
    # 终态统计（以 artifact 为准）
    import collections
    c = collections.Counter(r.get("status") for r in M.list_report_artifacts(root))
    stats["FULL"] = c.get(STATUS_FULL, 0)
    stats["FALLBACK"] = c.get(STATUS_FALLBACK, 0)
    stats["LOW_DATA"] = c.get(STATUS_LOW_DATA, 0)
    stats["FAIL"] = c.get(STATUS_FAIL, 0)
    return stats


def audit_ai_packs(root, all_reports=False):
    """§十五/§十六 Prompt Preview / serialized input audit（**不调用 AI、不写盘**）。

    默认审计 planner targets；all_reports=True 时审计**全部**报告（用于
    「targets 为 0 时仍需逐份证据」的场景）。逐份输出 §十六 指定的计数，
    并给出 §二十 的本地化缺口统计。
    """
    plan = plan_targets(root, with_eligibility=False)
    planner_targets = set(plan["target_ids"])
    if all_reports:
        plan = dict(plan)
        plan["target_ids"] = [r.get("report_id")
                              for r in M.list_report_artifacts(root)]
    rows = []
    tot = {"AI_TARGET_REPORTS": plan["AI_TARGET_REPORTS"],
           "AI_TARGET_REPORTS_ACTUAL": 0,
           "REPORTS_WITH_ELIGIBLE_FACTS": 0,
           "AI_PACK_FACTS_TOTAL": 0,
           "PROVIDER_BOUNDARY_REACHED": 0,
           "UNATTRIBUTED_FACTS_IN_AI_FACT_PACK": 0,
           "EMPTY_FACTS_IN_AI_FACT_PACK": 0,
           "CROSS_COUNTRY_FACTS_IN_COUNTRY_WEEKLY": 0,
           "CROSS_COUNTRY_FACTS_IN_REPORT_PACK": 0,
           "CROSS_COUNTRY_FACTS_IN_AI_FACT_PACK": 0,
           "REPORT_AI_SCOPE_PARITY": True,
           "FAKE_SOURCE_REFS": 0,
           "SOCIAL_FACTS_USING_TITLE_CN": 0,
           "SOCIAL_FACTS_USING_TITLE_ORIGINAL": 0,
           "SOCIAL_FACTS_EXCLUDED_NO_CONTENT": 0,
           "SOCIAL_FACTS_CANDIDATE": 0, "SOCIAL_FACTS_INCLUDED": 0,
           "SOCIAL_FACTS_EXCLUDED_NO_SOURCE": 0, "SOCIAL_FACTS_EXCLUDED_SCOPE": 0,
           "SOCIAL_FACTS_EXCLUDED_OUT_OF_WINDOW": 0,
           "DISEASE_FACTS_CANDIDATE": 0, "DISEASE_FACTS_INCLUDED": 0,
           "DISEASE_FACTS_EXCLUDED_NO_CONTENT": 0,
           "DISEASE_FACTS_EXCLUDED_NO_SOURCE": 0,
           "DISEASE_FACTS_EXCLUDED_SCOPE": 0,
           "DISEASE_FACTS_EXCLUDED_OUT_OF_WINDOW": 0,
           "DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK": 0,
           "DISEASE_FACTS_EXCLUDED_FROM_AI_FACT_PACK": 0,
           "DISEASE_FACTS_USING_CN_NAME": 0,
           "DISEASE_FACTS_USING_EN_NAME": 0,
           "SECRETS_IN_AUDIT_OUTPUT": 0}
    sums = [k for k in tot if k != "SECRETS_IN_AUDIT_OUTPUT"]
    tot["REPORTS_WITH_ELIGIBLE_FACTS_BUT_LOW_DATA"] = 0
    for rid in plan["target_ids"]:
        rep, t = None, None
        for _t in ("africa_daily", "africa_weekly", "country_weekly"):
            rep = M.read_report_artifact(root, _t, rid)
            if rep:
                t = _t
                break
        if not rep:
            continue
        fp, _ = rebuild_fact_pack(root, rep)
        if not fp:
            continue
        ai_fp, d = build_ai_fact_pack(fp, rep)
        row_aliases = {"SOCIAL_FACTS_CANDIDATE": "SOCIAL_FACTS_CANDIDATE",
                       "SOCIAL_FACTS_INCLUDED": "SOCIAL_FACTS_INCLUDED",
                       "SOCIAL_FACTS_EXCLUDED_NO_CONTENT": "SOCIAL_FACTS_EXCLUDED_NO_CONTENT",
                       "SOCIAL_FACTS_EXCLUDED_NO_SOURCE": "SOCIAL_FACTS_EXCLUDED_NO_SOURCE",
                       "SOCIAL_FACTS_EXCLUDED_SCOPE": "SOCIAL_FACTS_EXCLUDED_SCOPE",
                       "SOCIAL_FACTS_EXCLUDED_OUT_OF_WINDOW": "SOCIAL_FACTS_EXCLUDED_OUT_OF_WINDOW",
                       "DISEASE_FACTS_CANDIDATE": "DISEASE_FACTS_CANDIDATE",
                       "DISEASE_FACTS_INCLUDED": "DISEASE_FACTS_INCLUDED",
                       "DISEASE_FACTS_EXCLUDED_NO_CONTENT": "DISEASE_FACTS_EXCLUDED_NO_CONTENT",
                       "DISEASE_FACTS_EXCLUDED_NO_SOURCE": "DISEASE_FACTS_EXCLUDED_NO_SOURCE",
                       "DISEASE_FACTS_EXCLUDED_SCOPE": "DISEASE_FACTS_EXCLUDED_SCOPE",
                       "DISEASE_FACTS_EXCLUDED_OUT_OF_WINDOW": "DISEASE_FACTS_EXCLUDED_OUT_OF_WINDOW",
                       "DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK": "DISEASE_FACTS_INCLUDED",
                       "DISEASE_FACTS_EXCLUDED_FROM_AI_FACT_PACK": "DISEASE_FACTS_EXCLUDED_FROM_PACK"}
        rows.append({
            "report_id": rid, "report_type": t,
            "fact_count": rep.get("fact_count"),
            "SOCIAL_FACTS_CANDIDATE": d["SOCIAL_FACTS_CANDIDATE"],
            "SOCIAL_FACTS_INCLUDED": d["SOCIAL_FACTS_INCLUDED"],
            "SOCIAL_FACTS_EXCLUDED_NO_CONTENT": d.get("SOCIAL_FACTS_EXCLUDED_NO_CONTENT", 0),
            "SOCIAL_FACTS_EXCLUDED_NO_SOURCE": d.get("SOCIAL_FACTS_EXCLUDED_NO_SOURCE", 0),
            "SOCIAL_FACTS_EXCLUDED_SCOPE": d.get("SOCIAL_FACTS_EXCLUDED_SCOPE", 0),
            "SOCIAL_FACTS_EXCLUDED_OUT_OF_WINDOW": d.get("SOCIAL_FACTS_EXCLUDED_OUT_OF_WINDOW", 0),
            "DISEASE_FACTS_CANDIDATE": d["DISEASE_FACTS_CANDIDATE"],
            "DISEASE_FACTS_INCLUDED": d["DISEASE_FACTS_INCLUDED_IN_AI_FACT_PACK"],
            "DISEASE_FACTS_EXCLUDED_NO_CONTENT": d.get("DISEASE_FACTS_EXCLUDED_NO_CONTENT", 0),
            "DISEASE_FACTS_EXCLUDED_NO_SOURCE": d.get("DISEASE_FACTS_EXCLUDED_NO_SOURCE", 0),
            "DISEASE_FACTS_EXCLUDED_SCOPE": d.get("DISEASE_FACTS_EXCLUDED_SCOPE", 0),
            "DISEASE_FACTS_EXCLUDED_OUT_OF_WINDOW": d.get("DISEASE_FACTS_EXCLUDED_OUT_OF_WINDOW", 0),
            "DISEASE_FACTS_EXCLUDED_FROM_PACK": d["DISEASE_FACTS_EXCLUDED_FROM_AI_FACT_PACK"],
            "AI_PACK_FACTS_TOTAL": d["AI_PACK_FACTS_TOTAL"],
            "source_backed_count": len(ai_fp.get("source_refs") or []),
            "countries_represented": d["AI_PACK_COUNTRIES"],
            "content_language_mix": {
                "social_zh": sum(1 for f in ai_fp["social_facts"]
                                 if str(f.get("content_source_field") or "").endswith("_cn")),
                "social_original": sum(1 for f in ai_fp["social_facts"]
                                       if str(f.get("content_source_field") or "").endswith("_original")),
                "disease_cn_name": sum(1 for f in ai_fp["disease_facts"]
                                       if str(f.get("content_source_field") or "") in
                                       ("disease_name_zh", "disease_name_cn")),
                "disease_en_name": sum(1 for f in ai_fp["disease_facts"]
                                       if str(f.get("content_source_field") or "") == "disease_name_en"),
            },
            "cross_country_in_report": d["CROSS_COUNTRY_FACTS_IN_REPORT_PACK"],
            "cross_country_in_ai_pack": d["CROSS_COUNTRY_FACTS_IN_AI_FACT_PACK"],
            "report_ai_scope_parity": d["REPORT_AI_SCOPE_PARITY"],
            "reaches_provider_boundary": d["AI_PACK_FACTS_TOTAL"] > 0,
        })
        for k in sums:
            if k in ("AI_TARGET_REPORTS_ACTUAL", "PROVIDER_BOUNDARY_REACHED",
                     "REPORTS_WITH_ELIGIBLE_FACTS", "REPORT_AI_SCOPE_PARITY"):
                continue
            v = d.get(k)
            if v is None:
                alias = row_aliases.get(k)
                v = d.get(alias) if alias else None
            if isinstance(v, int) and not isinstance(v, bool):
                tot[k] += v
        if d["AI_PACK_FACTS_TOTAL"] > 0:
            tot["REPORTS_WITH_ELIGIBLE_FACTS"] += 1
            if rid in planner_targets:
                tot["AI_TARGET_REPORTS_ACTUAL"] += 1
                tot["PROVIDER_BOUNDARY_REACHED"] += 1
    tot["REPORT_AI_SCOPE_PARITY"] = all(
        r["report_ai_scope_parity"] for r in rows) if rows else True
    tot["REPORTS_WITH_ELIGIBLE_FACTS_BUT_LOW_DATA"] = sum(
        1 for r in rows if r["reaches_provider_boundary"]
        and r["report_id"] not in planner_targets)
    tot["C5_LOCALIZATION_COMPLETENESS_DEBT"] = bool(
        tot["SOCIAL_FACTS_USING_TITLE_ORIGINAL"] or tot["DISEASE_FACTS_USING_EN_NAME"]
        or tot["SOCIAL_FACTS_EXCLUDED_NO_CONTENT"])
    return {"totals": tot, "per_report": rows}

class SpyProvider:
    """§十七 Provider Boundary dry-run 替身。

    与 Stage 7B provider **同形状**（只有 `generate(system, user)`，无 submit_task），
    但**不发任何网络请求**：仅按 prompt 中真实出现的事实回一段结构性合规的 JSON，
    用来验证「6 个 target 是否真的走到了 provider 边界」。
    """

    api_key = "spy"
    name = "spy"
    model = MODEL

    def __init__(self):
        self.calls = []

    def generate(self, system, user):
        self.calls.append((system, user))
        country = ""
        try:
            payload = json.loads(user) if user else {}
        except Exception:  # noqa: BLE001
            payload = {}
        for f in (payload.get("facts") or []):
            if f.get("country"):
                country = str(f["country"])
                break
        body = {"executive_assessment": "边界演练：%s 本期事实已进入模型输入。" % (country or "重点方向"),
                "trend_analysis": "边界演练：不构成真实研判。",
                "outlook": "边界演练：不构成真实展望。",
                "watch_points": ["边界演练"]}
        return json.dumps(body, ensure_ascii=False), {"model": MODEL, "provider": "spy"}


def boundary_dry_run(root):
    """§十七/§十八：确认每个 target 是否真的到达 provider 边界（**只读、无网络、不落盘**）。

    spy provider 只实现 `generate(system, user)`（真实契约），不得实现 submit_task。
    """
    plan = plan_targets(root, with_eligibility=False)
    spy = SpyProvider()
    st = enrich_all(root, provider=spy, write=False)
    return {"AI_TARGET_REPORTS": plan["AI_TARGET_REPORTS"],
            "AI_TARGET_REPORTS_ACTUAL": st["AI_TARGET_REPORTS_ACTUAL"],
            "PROVIDER_BOUNDARY_REACHED": st["PROVIDER_BOUNDARY_REACHED"],
            "GENERATE_CALLS_SIMULATED": len(spy.calls),
            "SUBMIT_TASK_CALLS": st["SUBMIT_TASK_CALLS"],
            "LOW_DATA_PROVIDER_CALLS": 0,
            "SKIPPED_EMPTY_AI_PACK": st["SKIPPED_EMPTY_AI_PACK"],
            "AI_CALLS_TOTAL": st["AI_CALLS_TOTAL"],
            "SYSTEMIC_PROVIDER_FAILURE": st["SYSTEMIC_PROVIDER_FAILURE"],
            "PROVIDER_CONTRACT": "generate(system, user)",
            "outcomes": st["outcomes"],
            "PROVIDER_CALLS_FAILED": st["PROVIDER_CALLS_FAILED"],
            "boundary_equals_actual": st["PROVIDER_BOUNDARY_REACHED"] == st["AI_TARGET_REPORTS_ACTUAL"]}


def _cli():
    import argparse
    ap = argparse.ArgumentParser(description="C4-C report AI enrichment (server-side)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--provider", default=None, help="auto|mock|deepseek")
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--audit-packs", action="store_true",
                    help="§十五 只读审计 AI fact pack（不调用 AI）")
    ap.add_argument("--audit-all-packs", action="store_true",
                    help="审计**全部**报告（含非 target），用于 targets 为 0 时的逐份证据")
    ap.add_argument("--boundary-dry-run", action="store_true",
                    help="§十七 provider 边界演练（spy provider，无网络、不落盘）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=None, help="把统计写入该 JSON（供幂等校验）")
    a = ap.parse_args()
    if a.plan_only:
        print(json.dumps(plan_targets(a.root), ensure_ascii=False, indent=1))
        return 0
    if a.audit_packs or a.audit_all_packs:
        print(json.dumps(audit_ai_packs(a.root, all_reports=bool(a.audit_all_packs)),
                         ensure_ascii=False, indent=1))
        return 0
    if a.boundary_dry_run:
        print(json.dumps(boundary_dry_run(a.root), ensure_ascii=False, indent=1))
        return 0
    prov = P.make_provider(a.provider)
    ready = bool(getattr(prov, "api_key", "") or a.provider == "mock")
    if a.dry_run and not ready:
        print(json.dumps({"provider_ready": False, "AI_CALLS": 0,
                          "plan": plan_targets(a.root),
                          "audit": audit_ai_packs(a.root)["totals"]},
                         ensure_ascii=False, indent=1))
        return 0
    st = enrich_all(a.root, provider=prov, write=not a.dry_run, limit=a.limit)
    if a.out:
        with io.open(a.out, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=1)
    print(json.dumps(st, ensure_ascii=False, indent=1))
    # §七/§十八：系统级 provider 故障必须让 workflow 明确 FAIL
    return 2 if st.get("SYSTEMIC_PROVIDER_FAILURE") else 0


if __name__ == "__main__":
    raise SystemExit(_cli())
