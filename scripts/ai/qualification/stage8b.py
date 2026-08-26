#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8B — Production AI Qualification & Real Report Validation V1。

固定 20-case 资质集（qualification_version = stage8b-v1）：
  Social Event Enrichment ×8（S1-S8，§八）
  Disease AI Summary        ×4（D1-D4，§九）
  Africa Daily              ×3（RD1-RD3，§十）
  Country Weekly            ×3（RW1-RW3，§十一）
  Major Event Brief         ×2（RB1-RB2，§十二）

原则：
  - 统一接口 task_type/provider_name/model_name/prompt_version/
    input_payload/output_schema（§三），不绑定模型。
  - 严格 Response Gate（§十三）：strict JSON / schema；任何 markdown
    fence / reasoning wrapper / extra text → contract_failure。
  - 数字 Evidence Gate（§十七）、Attribution Gate（§十八）、
    Source Reference Gate（§十九）、Disease 类别分离 + unknown!=0（§九）。
  - Provider 角色（§二十六）：primary_candidate / secondary /
    not_qualified / provider_unresolved。
  - 产物（§二十五）：data/runtime/ai_qualification/stage8b/，不进
    dist/Public；绝不输出 API key（§三十一）。
  - 失败隔离（§三十四）：不改 Canonical/Public，不覆盖旧结果。
  - WorkBuddy Queue / Hy3 / 内嵌模型不得作为 Production Provider（§六）。

credential 缺失时如实记录 credential_unavailable，不调用 API、不伪造调用。

用法：
  python scripts/ai/qualification/stage8b.py [--provider glm47_flash|deepseek|all]
"""
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

QUALIFICATION_VERSION = "stage8b-v1"
ARTIFACT_DIR = ROOT / "data" / "runtime" / "ai_qualification" / "stage8b"

# 阈值（§十四/§十五）
SCHEMA_PASS_MIN = 19
STRICT_JSON_PASS_MIN = 19
REPORT_CASES_TOTAL = 8
REPORT_CASES_MIN_PASS = 7
INVALID_SHAPE_MAX_FOR_PRIMARY = 1   # ≥2 → 不得为唯一 Primary（可 Secondary）

# Provider 候选（§四/§五）
PROVIDER_CANDIDATES = ["glm47_flash", "deepseek"]
GLM_SECRET = "ASIP_GLM_API_KEY"
DS_SECRET = "ASIP_DEEPSEEK_API_KEY"

# ── 归因保留词（§十八；2026-08-26 扩展词典修复漏词）──
ATTR_SRC_KW = ("alleged", "claimed", "suspected", "reportedly", "unconfirmed",
               "single_source", "conflicting", "据称", "声称", "疑似", "被指",
               "尚未证实", "单一来源", "说法不一")
ATTR_OUT_KW = ("据称", "声称", "被指", "疑似", "可能", "据报道", "尚未证实",
               "单一来源", "说法不一", "存在冲突", "多家来源", "未证实",
               "alleged", "claimed", "suspected", "reportedly",
               "unconfirmed", "single source", "conflicting")

_NUM_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})*|\d+)(?![\w.])")

CASE_IDS = ["S%d" % i for i in range(1, 9)] + \
           ["D%d" % i for i in range(1, 5)] + \
           ["RD%d" % i for i in range(1, 4)] + \
           ["RW%d" % i for i in range(1, 4)] + \
           ["RB%d" % i for i in range(1, 3)]


def numbers_in(obj):
    out = set()
    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
        elif isinstance(node, (int, float)) and node is not None:
            out.add(int(node))
        elif isinstance(node, str):
            for m in _NUM_RE.finditer(node):
                out.add(int(m.group(0).replace(",", "")))
    walk(obj)
    return out


def strict_json_parse(text):
    """§十三：拒绝 markdown fence / 包裹 / 前后杂文。返回 (ok, parsed, err)。"""
    if not text or not isinstance(text, str):
        return False, None, "empty"
    t = text.strip()
    if "```" in t:
        return False, None, "markdown_fence"
    try:
        parsed = json.loads(t)
    except Exception as e:
        return False, None, "not_json:%s" % str(e)[:60]
    return True, parsed, None


def check_attribution(input_text, output_text):
    """输入含归因词而输出完全丢失 → 归因失败（§十八）。"""
    it = (input_text or "").lower()
    ot = (output_text or "").lower()
    if not any(k in it for k in ATTR_SRC_KW):
        return True, None
    if any(k in ot for k in ATTR_OUT_KW):
        return True, None
    return False, "attribution_lost"


def check_numeric_evidence(parsed, input_payload, fact_fields):
    """§十七：输出事实字段中的数字必须存在于 input（或为 null/无）。"""
    in_nums = numbers_in(input_payload)
    violations = []
    def walk_text(s, path):
        for m in _NUM_RE.finditer(s):
            n = int(m.group(0).replace(",", ""))
            if n not in in_nums:
                violations.append("%s: %s" % (path, n))
    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, "%s.%s" % (path, k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, "%s[%d]" % (path, i))
        elif isinstance(node, str):
            walk_text(node, path)
    walk(parsed, "out")
    return violations


def check_country(parsed, input_payload):
    """§八：enrichment country_iso3 必须与 input 一致或 None（源国不污染）。"""
    src_iso = None
    if isinstance(input_payload, dict):
        src_iso = (input_payload.get("country_iso3")
                   or input_payload.get("event_country")
                   or (input_payload.get("event") or {}).get("country_iso3"))
    if not src_iso:
        return True, None
    if isinstance(parsed, dict):
        out_iso = parsed.get("country_iso3")
        if out_iso and out_iso != src_iso:
            return False, "country_error: %s != %s" % (out_iso, src_iso)
    return True, None


def check_disease_identity(parsed, input_payload):
    """§九：disease identity 保留。

    修复（evaluator bug，2026-08-26）：Disease output contract 的身份字段是
    disease_event_id（非 disease_id）。不得要求模型输出 schema 不存在的字段。
    正确规则：
      1) 输入含 disease_event_id 且输出含 disease_event_id → 必须一致；
      2) 否则若输入含 disease_id，允许输出中出现 disease_id 或对应中文/英文名
         （disease_name_zh/name_en 任一命中即通过）；
      3) 输入无任何身份字段 → 不判。
    """
    if not isinstance(parsed, dict):
        return True, None
    problems = []
    src = input_payload if isinstance(input_payload, dict) else {}
    src_ev = src.get("event") or {}
    src_evid = src.get("disease_event_id") or src_ev.get("disease_event_id")
    out_evid = parsed.get("disease_event_id")
    if src_evid and out_evid:
        if str(src_evid) != str(out_evid):
            problems.append("disease_identity_error: %s != %s" % (out_evid, src_evid))
        return (len(problems) == 0), problems
    src_did = src.get("disease_id") or src_ev.get("disease_id")
    if src_did:
        blob = json.dumps(parsed, ensure_ascii=False).lower()
        names = [str(src_did).lower()]
        for k in ("disease_name_zh", "disease_name_en", "name_zh", "name_en"):
            v = src_ev.get(k) or src.get(k)
            if v:
                names.append(str(v).lower())
        if not any(n in blob for n in names if n):
            problems.append("disease_identity_error")
    return (len(problems) == 0), problems


def check_disease_numeric(parsed, input_payload):
    """§九/§十七：disease 输出数字必须来自 input；input null 处输出 0 → 失败。"""
    problems = []
    if not isinstance(parsed, dict):
        return True, None
    src = input_payload if isinstance(input_payload, dict) else {}
    src_ev = src.get("event") or {}
    in_nums = numbers_in(src)
    for k in ("confirmed_cases", "probable_cases", "suspected_cases", "deaths"):
        v = parsed.get(k)
        if v is None:
            continue
        if not isinstance(v, (int, float)):
            problems.append("disease_numeric_type:%s=%r" % (k, v))
            continue
        iv = int(v)
        if iv not in in_nums:
            problems.append("disease_numeric_gate_failure:%s=%s" % (k, iv))
        # input 为 null 而输出 0 → unknown 被写 0
        srcv = src_ev.get(k)
        if srcv is None and iv == 0:
            problems.append("disease_null_written_zero:%s" % k)
    return (len(problems) == 0), problems


def check_source_refs(parsed, input_payload):
    """§十九：report source_refs 必须 ⊆ input source_refs；不得虚构 URL。"""
    if not isinstance(parsed, dict):
        return True, None
    src_refs = []
    def collect(node, key):
        if isinstance(node, dict):
            if key in node and isinstance(node[key], list):
                src_refs.extend(node[key])
            for v in node.values():
                collect(v, key)
        elif isinstance(node, list):
            for v in node:
                collect(v, key)
    collect(input_payload, "source_refs")
    src_ids = set()
    src_urls = set()
    for r in src_refs:
        if isinstance(r, dict):
            if r.get("source_id"):
                src_ids.add(r["source_id"])
            if r.get("url"):
                src_urls.add(r["url"])
    problems = []
    for it in (parsed.get("source_refs") or []):
        if not isinstance(it, dict):
            continue
        if it.get("source_id") and it["source_id"] not in src_ids:
            problems.append("unsupported_source_reference:%s" % it["source_id"])
        if it.get("url") and it["url"] not in src_urls:
            problems.append("unsupported_source_url:%s" % it["url"][:60])
    return (len(problems) == 0), problems


def check_fact_analysis_separation(parsed):
    """§十/§三十七：FACT 字段不得含预测/评估化表述；assessment/outlook 与 fact 分离。"""
    pred_pats = ("未来", "预计将", "可能发生", "probability", "%%", "%", "87%",
                 "将发生", "必然", "risk of attack")
    problems = []
    def scan_fact(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("fact_summary", "what_happened", "confirmed_facts") or "fact" in k:
                    if isinstance(v, str):
                        for p in pred_pats:
                            if p in v:
                                problems.append("fact_prediction:%s" % path)
                scan_fact(v, "%s.%s" % (path, k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                scan_fact(v, "%s[%d]" % (path, i))
    scan_fact(parsed, "out")
    return (len(problems) == 0), problems


def credential_available(name):
    key = GLM_SECRET if name == "glm47_flash" else DS_SECRET
    return bool(os.environ.get(key, "").strip())


def _glm_task_builder(case):
    """构造 GLM provider submit_task 输入（对齐 glm_golden_set 模式）。"""
    if case["task_type"] == "stage4_event_enrichment":
        from scripts.ai.glm_golden_set import _glm_system_prompt, _schema_for
        sys_text = _glm_system_prompt()
        prompt_version = "stage4-enrichment-v1.0.0"
    elif case["task_type"] == "disease_summary":
        from scripts.ai.glm_golden_set import _disease_glm_system_prompt
        sys_text = _disease_glm_system_prompt()
        prompt_version = "disease-summary-v1.0.0"
    else:
        # §八/§九：报告类必须使用真实 Stage7B prompt（禁止 placeholder）
        if not case.get("system_prompt"):
            raise SystemExit(
                "QUALIFICATION_PROMPT_MISSING: %s 未配置真实 report prompt" % case["case_id"])
        sys_text = case["system_prompt"]
        prompt_version = case.get("prompt_version") or "v1.0.0"
    payload = case["input_payload"]
    return {
        "task_id": "S8B_%s" % case["case_id"],
        "task_type": case["task_type"],
        "prompt_version": prompt_version,
        "prompt_contract_hash": hashlib.sha256(sys_text.encode("utf-8")).hexdigest()[:16],
        "input_hash": "8b_" + hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12],
        "system_text": sys_text,
        "user_text": "INPUT:\n" + json.dumps(payload, ensure_ascii=False)[:6000],
        "usage_purpose": "production_qualification",
        "max_output_tokens": MAX_TOKEN_POLICY.get(case["task_type"], 2048),
    }


def classify_failure_stage(code):
    """§十三：失败阶段枚举（client_request_construction/http_request/
    provider_response/response_parse/schema_validation/quality_gate/unknown）。"""
    code = str(code or "")
    if code.startswith("http_") or code.startswith("transport_error"):
        return "http_request"
    if "model_mismatch" in code:
        return "provider_response"
    if code.startswith("retry_exhausted"):
        return "http_request"
    if code.startswith("provider_error"):
        return "provider_response"
    if code.startswith("invalid_response_shape") or code.startswith("not_json"):
        return "response_parse"
    if code.startswith("schema"):
        return "schema_validation"
    if code == "credential_unavailable" or code == "credential_missing":
        return "client_request_construction"
    return "unknown"


def run_case(case, provider_name):
    """执行单个 case。credential 缺失 → provider_unavailable（不调 API）。"""
    result = {
        "case_id": case["case_id"],
        "task_type": case["task_type"],
        "semantic": case.get("semantic"),
        "provider": provider_name,
        "credential_available": credential_available(provider_name),
        "requested_model": "deepseek-v4-flash" if provider_name == "deepseek"
                           else ("glm-4.7-flash" if provider_name == "glm47_flash"
                                 else None),
        "returned_model": None,
        "provider_status": "unavailable",
        "attempt_count": 0,
        "failure_stage": None,
        "strict_json_pass": False,
        "schema_pass": False,
        "contract_failure": None,
        "errors": [],
        "cached": False,
        "latency_ms": None,
        "tokens": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
    }
    if not credential_available(provider_name):
        result["provider_status"] = "blocked"
        result["contract_failure"] = "credential_unavailable"
        return result

    task = _glm_task_builder(case)
    if provider_name == "glm47_flash":
        from scripts.ai.registry import get_provider
        prov = get_provider("glm47_flash")
        res = prov.submit_task(task)
        status = (res or {}).get("status", "")
        raw_text = None
        meta = {}
        if status == "succeeded":
            rr = (res.get("result") or {})
            raw_text = rr.get("text") or rr.get("content") or ""
            meta = rr
        else:
            err = (res.get("result") or {}).get("error") or {}
            result["provider_status"] = status
            result["contract_failure"] = (err.get("code") if isinstance(err, dict) else None) or status
            result["failure_stage"] = classify_failure_stage(result["contract_failure"])
            return result
    else:
        # Stage 8B continuation：DeepSeek V4 Flash-only（§二-§四）
        from scripts.ai.providers.deepseek_v4_flash import (
            DeepSeekV4FlashProvider, ALLOWED_DEEPSEEK_MODELS)
        prov = DeepSeekV4FlashProvider()
        res = prov.submit_task(task)
        status = (res or {}).get("status", "")
        rr = (res.get("result") or {})
        result["returned_model"] = rr.get("returned_model")
        result["attempt_count"] = rr.get("attempt_count") or 0
        result["tokens"] = {
            "input_tokens": rr.get("input_tokens"),
            "output_tokens": rr.get("output_tokens"),
            "total_tokens": rr.get("total_tokens"),
        }
        if status != "succeeded":
            err = rr.get("error") or {}
            code = err.get("code") if isinstance(err, dict) else None
            result["provider_status"] = status
            result["contract_failure"] = code or status
            result["failure_stage"] = classify_failure_stage(code or status)
            if code == "model_mismatch":
                result["errors"].append(
                    "model_mismatch: returned=%s" % result["returned_model"])
            return result
        # §四：returned_model 明确返回非 flash → case FAIL
        if result["returned_model"] and result["returned_model"] not in ALLOWED_DEEPSEEK_MODELS:
            result["provider_status"] = "failed"
            result["contract_failure"] = "model_mismatch"
            result["failure_stage"] = "provider_response"
            result["errors"].append(
                "model_mismatch: returned=%s" % result["returned_model"])
            return result
        raw_text = rr.get("text") or ""

    result["provider_status"] = "succeeded"
    result["attempt_count"] = max(result["attempt_count"], 1)
    # §五-§七：provider response telemetry 透传（finish_reason/reasoning/content）
    for _tk in ("finish_reason", "reasoning_content_present",
                "reasoning_content_length_chars", "reasoning_tokens",
                "content_present", "content_length_chars"):
        result[_tk] = rr.get(_tk)
    ok_json, parsed, err = strict_json_parse(raw_text)
    result["strict_json_pass"] = ok_json
    if not ok_json:
        # §十：finish_reason 驱动分类（length→budget 不足 / content_filter /
        # stop+empty→anomaly），不得归为模型内容能力失败
        bf, bstage = classify_budget_failure(rr)
        if bf:
            result["contract_failure"] = bf
        else:
            result["contract_failure"] = "invalid_response_shape:%s" % (err or "?")
        result["failure_stage"] = bstage or "response_parse"
        return result
    result["raw_text_excerpt"] = raw_text[:400]  # artifact 审计用（不含 key）
    return _evaluate_case(case, parsed, result)


# ── §八/§九：确定性元数据 exact-copy（LLM 不得推导/计算/返回 null）──
EXACT_COPY_FIELDS = {
    "africa_daily": ("report_id", "report_type", "report_date",
                     "period_start", "period_end"),
    "country_weekly": ("report_id", "report_type", "country_iso3",
                       "week_start", "week_end"),
    "major_event_brief": ("brief_id", "report_type", "event_time", "country"),
}

# ── §二：AI content schema（envelope 迁回程序责任）──
AI_CONTENT_SCHEMA = {
    "africa_daily": "schemas/africa_daily_ai_content.schema.json",
    "country_weekly": "schemas/country_weekly_ai_content.schema.json",
    "major_event_brief": "schemas/major_event_brief_ai_content.schema.json",
}

# ── §九：max_tokens 策略（按 task type；Report 需同时容纳 low reasoning + 内容）──
# social/disease 无 thinking → 2048；daily/weekly/brief 显式 low thinking →
# 预算上调（上限，非目标消耗）。§五 禁止恢复无限制输出。
MAX_TOKEN_POLICY = {
    "stage4_event_enrichment": 2048,
    "disease_summary": 2048,
    "africa_daily": 8192,
    "country_weekly": 6144,
    "major_event_brief": 4096,
}


def classify_budget_failure(rr):
    """§十：finish_reason 驱动的失败分类（不含调 API）。

    返回 (contract_failure, failure_stage)：
    - finish_reason=length 且 content 空/截断 → OUTPUT_TOKEN_BUDGET_INSUFFICIENT
    - finish_reason=content_filter → CONTENT_FILTER_RESPONSE
    - finish_reason=stop 且 content 空 → EMPTY_CONTENT_ANOMALY
    - 其它 → (None, None)（保持既有 invalid_response_shape 分类）
    """
    rr = rr or {}
    fr = rr.get("finish_reason")
    content_present = rr.get("content_present", bool((rr.get("text") or "").strip()))
    if fr == "length" and not content_present:
        return ("output_token_budget_insufficient", "response_parse")
    if fr == "content_filter":
        return ("content_filter_response", "response_parse")
    if fr == "stop" and not content_present:
        return ("empty_content_anomaly", "response_parse")
    return (None, None)


def check_exact_copy(parsed, input_payload, task_type):
    """§八：output 确定性元数据必须与 input 逐字一致 → REPORT_METADATA_MISMATCH。"""
    fields = EXACT_COPY_FIELDS.get(task_type)
    if not fields or not isinstance(parsed, dict):
        return True, None
    src = input_payload if isinstance(input_payload, dict) else {}
    problems = []
    for f in fields:
        iv = src.get(f)
        ov = parsed.get(f)
        if iv is None:
            continue  # input 无此字段 → 不判（input gate 负责补齐）
        if ov is None:
            problems.append("REPORT_METADATA_MISMATCH:%s null（input=%r）" % (f, iv))
        elif str(iv) != str(ov):
            problems.append("REPORT_METADATA_MISMATCH:%s %r != %r" % (f, ov, iv))
    return (len(problems) == 0), problems


def _evaluate_case(case, parsed, result):
    """确定性 Gate：schema / 数字 / 归因 / 国家 / 疾病 / 来源 / FACT 分离 / exact-copy。

    §二/§三：报告类——AI raw 先过 AI content schema；再 assemble（envelope 由程序
    注入）；final report 过完整 output schema；exact-copy 针对 assembled final。
    """
    from scripts.ai.schema_validation import validate_against_schema
    from scripts.report.gen.assembler import assemble_report
    schema = case.get("schema")
    payload = case["input_payload"]

    if case["task_type"] in AI_CONTENT_SCHEMA:
        # 1) AI content payload schema（不含 envelope）
        ai_schema = load_schema(AI_CONTENT_SCHEMA[case["task_type"]])
        if ai_schema:
            errs = validate_against_schema(parsed, ai_schema)
            if errs:
                result["schema_pass"] = False
                result["contract_failure"] = "ai_content_schema_failure"
                result["errors"] = errs[:8]
                return result
        # 2) assembler：envelope（input 确定性值）+ AI content → final report
        final = assemble_report(case["task_type"], payload, parsed,
                                meta={"provider_name": "deepseek",
                                      "model_name": "deepseek-v4-flash",
                                      "prompt_version": case.get("prompt_version")})
        result["assembled_report"] = final
        if schema:
            errs = validate_against_schema(final, schema)
            if errs:
                result["schema_pass"] = False
                result["contract_failure"] = "schema_failure"
                result["errors"] = errs[:8]
                return result
        result["schema_pass"] = True
        parsed = final   # 后续 gate（数字/归因/来源/exact-copy）针对 final
    else:
        if schema:
            errs = validate_against_schema(parsed, schema)
            if errs:
                result["schema_pass"] = False
                result["contract_failure"] = "schema_failure"
                result["errors"] = errs[:8]
                return result
        result["schema_pass"] = True

    result["parsed"] = parsed
    errors = []
    # 数字 evidence（§十七）
    fact_fields = ("key_facts", "summary_zh", "fact_summary", "what_happened",
                   "confirmed_facts", "executive_summary", "latest_counts")
    nv = check_numeric_evidence(parsed, payload, fact_fields)
    for v in nv:
        errors.append("magnitude_error:" + v)
    # 归因（§十八）
    inp_txt = json.dumps(payload, ensure_ascii=False)
    out_txt = json.dumps(parsed, ensure_ascii=False)
    ok_a, aerr = check_attribution(inp_txt, out_txt)
    if not ok_a:
        errors.append(aerr)
    # 国家（§八）
    ok_c, cerr = check_country(parsed, payload)
    if not ok_c:
        errors.append(cerr)
    # 疾病（§九）
    if case["task_type"] == "disease_summary":
        ok_d, derrs = check_disease_identity(parsed, payload)
        for e in derrs:
            errors.append(e)
        ok_dn, dn = check_disease_numeric(parsed, payload)
        for e in dn:
            errors.append(e)
    # 来源（§十九，报告类）
    if case["task_type"] in ("africa_daily", "country_weekly", "major_event_brief"):
        ok_s, serrs = check_source_refs(parsed, payload)
        for e in serrs:
            errors.append(e)
        ok_f, ferr = check_fact_analysis_separation(parsed)
        for e in ferr:
            errors.append(e)
        # §八：确定性元数据 exact-copy（period/report_id/report_date 等）
        ok_m, merrs = check_exact_copy(parsed, payload, case["task_type"])
        for e in merrs:
            errors.append(e)
        for e in ferr:
            errors.append(e)
    # 主要造假启发（数字/国家不在 input → 标记人工复核）
    result["errors"] = errors
    result["core_failure"] = len(errors) > 0
    return result


# ── 20 个固定 case（§八-§十二）──
FIXTURE_DIR = ROOT / "data" / "qualification" / "stage8b"


def load_fixture_cases():
    """§六：报告 case 从 committed fixtures 构建（缺失/空 → 硬失败，禁止 {} 兜底）。"""
    man = load_json("data/qualification/stage8b/manifest.json")
    if not man or not man.get("cases"):
        raise SystemExit("QUALIFICATION_FIXTURE_MISSING: manifest.json 缺失或为空")
    cases = []
    for fc in man["cases"]:
        cid = fc["case_id"]
        path = FIXTURE_DIR / fc["fixture_path"]
        if not path.exists():
            raise SystemExit("QUALIFICATION_FIXTURE_MISSING: %s 缺失" % fc["fixture_path"])
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            raise SystemExit("QUALIFICATION_FIXTURE_INVALID_JSON: %s (%s)" % (cid, e))
        if not payload:
            raise SystemExit("QUALIFICATION_FIXTURE_EMPTY: %s" % cid)
        prompt_path = ROOT / fc["prompt_file"]
        if not prompt_path.exists():
            raise SystemExit("QUALIFICATION_PROMPT_MISSING: %s" % fc["prompt_file"])
        cases.append({
            "case_id": cid, "task_type": fc["task_type"],
            "semantic": "committed fixture (%s)" % fc["fixture_path"],
            "is_disease": False, "input_payload": payload,
            "schema": load_schema(fc["output_schema"]),
            "ai_content_schema": load_schema(AI_CONTENT_SCHEMA[fc["task_type"]]),
            "system_prompt": prompt_path.read_text(encoding="utf-8"),
            "prompt_version": fc.get("prompt_version") or "v1.0.1",
            "fixture_hash": fc.get("fixture_hash"),
        })
    return cases


def _fixture_metadata_ok(task_type, payload):
    """§十三：确定性元数据就绪——required metadata 必须为非空 string。"""
    if not isinstance(payload, dict):
        return False
    if task_type == "africa_daily":
        keys = ("period_start", "period_end", "report_id", "report_type",
                "report_date")
    elif task_type == "country_weekly":
        keys = ("week_start", "week_end", "country_iso3", "report_id",
                "report_type")
    else:
        keys = ("brief_id", "report_type", "event_time", "country")
    return all(isinstance(payload.get(k), str) and payload.get(k).strip()
               for k in keys)


def fixture_gate():
    """§七：REPORT_FIXTURE_GATE——8/8 存在/合法/非空/schema 有效/hash 匹配。"""
    from scripts.ai.schema_validation import validate_against_schema
    man = load_json("data/qualification/stage8b/manifest.json") or {}
    result = {"qualification_version": QUALIFICATION_VERSION,
              "report_fixtures_ready": False,
              "cases": []}
    if not man.get("cases"):
        result["error"] = "manifest missing"
        return result
    all_ok = True
    for fc in man["cases"]:
        cid = fc["case_id"]
        path = FIXTURE_DIR / fc["fixture_path"]
        entry = {"case_id": cid, "task_type": fc["task_type"],
                 "fixture_path": fc["fixture_path"],
                 "exists": path.exists(),
                 "json_valid": False, "nonempty": False,
                 "schema_valid": False, "hash_match": False,
                 "prompt_version": fc.get("prompt_version"),
                 "prompt_hash": fc.get("prompt_hash"),
                 "input_schema": fc.get("input_schema"),
                 "output_schema": fc.get("output_schema"),
                 "fixture_hash": fc.get("fixture_hash")}
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                entry["json_valid"] = True
                entry["nonempty"] = bool(payload)
                schema = load_schema(fc["input_schema"])
                if schema:
                    errs = validate_against_schema(payload, schema)
                    entry["schema_valid"] = not errs
                    if errs:
                        entry["schema_errors"] = errs[:5]
                import hashlib as _h
                cur = _h.sha256(
                    path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
                entry["hash_match"] = (cur == fc.get("fixture_hash"))
                # §十三：确定性元数据就绪（period/week 字段非 null string）
                entry["metadata_ready"] = _fixture_metadata_ok(fc["task_type"], payload)
            except Exception as e:
                entry["json_valid"] = False
                entry["error"] = str(e)[:100]
        entry["ok"] = all((entry["exists"], entry["json_valid"], entry["nonempty"],
                           entry["schema_valid"], entry["hash_match"],
                           entry.get("metadata_ready", False)))
        all_ok = all_ok and entry["ok"]
        result["cases"].append(entry)
    result["report_fixtures_ready"] = all_ok
    result["summary"] = {
        "report_fixture_count": len(result["cases"]),
        "fixture_schema_pass": sum(1 for c in result["cases"] if c["schema_valid"]),
        "fixture_nonempty": sum(1 for c in result["cases"] if c["nonempty"]),
        "fixture_hash_pass": sum(1 for c in result["cases"] if c["hash_match"]),
        "deterministic_metadata_ready": sum(
            1 for c in result["cases"] if c.get("metadata_ready")),
    }
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "fixture_gate_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def build_cases():
    from scripts.ai.glm_golden_set import build_security_samples, build_disease_samples
    sec = build_security_samples()
    dis = build_disease_samples()
    by_cat = {s["category"]: s for s in sec + dis}

    def enrich_task(cid, cat, semantic):
        s = by_cat[cat]
        return {"case_id": cid, "task_type": "stage4_event_enrichment",
                "semantic": semantic, "is_disease": False,
                "input_payload": s["event"], "schema": load_schema(
                    "schemas/ai_enrichment_payload.schema.json"),
                "system_prompt": None, "prompt_version": "stage4-enrichment-v1.0.0"}

    def disease_task(cid, cat, semantic):
        s = by_cat[cat]
        return {"case_id": cid, "task_type": "disease_summary",
                "semantic": semantic, "is_disease": True,
                "input_payload": s["event"], "schema": load_schema(
                    "schemas/disease_ai_summary.schema.json"),
                "system_prompt": None, "prompt_version": "disease-summary-v1.0.0"}

    cases = [
        enrich_task("S1", "disputed_allegation", "disputed allegation 归因保留"),
        enrich_task("S2", "casualty_uncertainty", "casualty uncertainty 伤亡不确定"),
        enrich_task("S3", "direct_security", "direct security event 直接安全事件"),
        enrich_task("S4", "economic_news", "economic/development 低安全相关性"),
        enrich_task("S5", "partial_body", "partial body 部分正文"),
        enrich_task("S6", "ordinary_security", "official confirmation guard（不得虚构官方确认）"),
        enrich_task("S7", "civil_unrest", "correction/update guard（不得虚构更新/更正）"),
        enrich_task("S8", "multi_country", "country ambiguity / contamination guard"),
        disease_task("D1", "disease_cholera", "cholera 高数字 NGA deaths=338"),
        disease_task("D2", "disease_mpox", "mpox suspected/deaths COD"),
        disease_task("D3", "disease_other_numbers", "marburg confirmed/deaths ETH"),
        disease_task("D4", "disease_cholera_tcd", "unknown/null values TCD"),
    ]
    # 报告类（§二-§九：committed fixtures + 真实 Stage7B prompt；缺失硬失败）
    for fc in load_fixture_cases():
        cases.append(fc)
    assert [c["case_id"] for c in cases] == CASE_IDS, "case set must be fixed"
    return cases


def report_case(cid, task_type, semantic, payload, schema_rel, prompt_version):
    return {"case_id": cid, "task_type": task_type, "semantic": semantic,
            "is_disease": False, "input_payload": payload,
            "schema": load_schema(schema_rel), "system_prompt": None,
            "prompt_version": prompt_version}


def load_schema(rel):
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_json(rel, default=None):
    p = ROOT / rel
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def _daily_variant(daily, kind):
    """从真实 daily input 派生两个契约场景（确定性，不改变规则）。"""
    if not daily:
        return {"report_id": "DAILY_DEV_%s" % kind, "report_type": "africa_daily",
                "sections": {}}
    import copy
    d = copy.deepcopy(daily)
    sec = d.get("sections") or {}
    if kind == "single_conflict":
        keep = []
        for k in ("major_security_developments", "terrorism_armed_violence",
                  "political_social_stability", "cross_border_regional"):
            for it in sec.get(k, []) or []:
                if it.get("single_source_warning") or it.get("conflicting"):
                    keep.append(it)
        d["sections"] = {"major_security_developments": keep[:6],
                         "public_health_disease": [],
                         "executive_summary": []}
        d["note"] = "D2: single-source/conflicting mix（真实筛选）"
    elif kind == "disease_security":
        dis = (sec.get("public_health_disease") or [])[:3]
        maj = (sec.get("major_security_developments") or [])[:3]
        d["sections"] = {"major_security_developments": maj,
                         "public_health_disease": dis,
                         "executive_summary": []}
        d["note"] = "D3: disease + major security mix（真实筛选）"
    return d


def _brief_input(security):
    """从真实 master_events / disease_outbreaks 构造 brief 结构化输入。"""
    me = load_json("data/runtime/frontend_preview_public/master_events.json") or {}
    do = load_json("data/runtime/frontend_preview_public/disease_outbreaks.json") or {}
    if security:
        e = (me.get("events") or [{}])[0]
        return {"brief_id": "BRF_QUAL_S", "event_id": e.get("master_event_id"),
                "master_event_id": e.get("master_event_id"),
                "country_iso3": e.get("country_iso3"), "country": e.get("country_cn"),
                "event_type": e.get("event_type"), "event_time": e.get("event_time"),
                "location": e.get("location"),
                "verification_status": e.get("verification_status"),
                "source_count": e.get("source_count"),
                "source_refs": [{"source_id": "src_qual_%s" % i} for i in range(1)],
                "facts": [{"fact": e.get("fact_summary") or ""}],
                "uncertainties": (e.get("uncertainties") or [])[:2],
                "label": "qualification_sample",
                "note": "真实 master event 结构化输入（无真实 brief candidate 时的资质样本）"}
    o = (do.get("outbreaks") or [{}])[0]
    return {"brief_id": "BRF_QUAL_D", "outbreak_id": o.get("outbreak_id"),
            "disease_id": o.get("disease_id"),
            "country_iso3": o.get("country_iso3"), "country": o.get("country_cn"),
            "event_type": "public_health", "event_time": o.get("latest_report_at"),
            "verification_status": o.get("verification_status"),
            "source_count": o.get("source_count"),
            "source_refs": [{"source_id": "src_qual_dis_%s" % i} for i in range(1)],
            "facts": [{"fact": "latest counts: %s" % json.dumps(o.get("latest_counts") or {}, ensure_ascii=False)}],
            "uncertainties": (o.get("uncertainties") or [])[:2],
            "label": "qualification_sample",
            "note": "真实 disease outbreak 结构化输入（资质样本）"}


def decide_role(results):
    """§十四/§十五/§二十六：provider 角色判定。"""
    ran = [r for r in results if r.get("provider_status") == "succeeded"]
    n = len(results)
    schema_pass = sum(1 for r in results if r.get("schema_pass"))
    strict_json_pass = sum(1 for r in results if r.get("strict_json_pass"))
    core_errors = sum(1 for r in results if r.get("core_failure"))
    invalid_shape = sum(1 for r in results if r.get("contract_failure")
                        and "invalid_response_shape" in str(r.get("contract_failure")))
    # 核心错误分项
    def count(prefix):
        return sum(1 for r in results for e in (r.get("errors") or [])
                   if str(e).startswith(prefix))
    counts = {
        "major_fabrication": count("magnitude_error"),
        "country_error": count("country_error"),
        "magnitude_error": count("magnitude_error"),
        "attribution_loss": count("attribution"),
        "disease_identity_error": count("disease_identity"),
        "disease_numeric_gate_failure": count("disease_numeric_gate_failure"),
        "unsupported_source_reference": count("unsupported_source"),
    }
    report_results = [r for r in results if r.get("task_type") in (
        "africa_daily", "country_weekly", "major_event_brief")]
    report_pass = sum(1 for r in report_results if r.get("provider_status") == "succeeded"
                      and r.get("schema_pass") and not r.get("core_failure"))

    primary_ok = (schema_pass >= SCHEMA_PASS_MIN
                  and strict_json_pass >= STRICT_JSON_PASS_MIN
                  and all(v == 0 for v in counts.values())
                  and report_pass >= REPORT_CASES_MIN_PASS
                  and len(report_results) == REPORT_CASES_TOTAL)
    if primary_ok:
        role = "primary_candidate"
    elif invalid_shape >= 2:
        role = "secondary"
    elif ran and (schema_pass >= 15 or strict_json_pass >= 15):
        role = "secondary"
    else:
        role = "not_qualified"
    return {
        "role": role,
        "reason": {
            "contract_reliability": {"schema_pass": schema_pass, "strict_json_pass": strict_json_pass,
                                     "invalid_response_shape": invalid_shape,
                                     "succeeded": len(ran), "total": n},
            "content_accuracy": counts,
            "numeric_integrity": counts["magnitude_error"],
            "attribution_integrity": counts["attribution_loss"],
            "report_quality": {"report_pass": report_pass, "report_total": len(report_results),
                               "min_required": REPORT_CASES_MIN_PASS},
            "transport_reliability": {"blocked_credential": n - len(ran),
                                      "invalid_response_shape": invalid_shape},
        },
        "primary_candidate": role == "primary_candidate",
    }


def write_artifacts(summary, results, telemetry, report_results):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "qualification_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    (ARTIFACT_DIR / "case_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    (ARTIFACT_DIR / "provider_telemetry.json").write_text(
        json.dumps(telemetry, ensure_ascii=False, indent=1), encoding="utf-8")
    (ARTIFACT_DIR / "report_quality_results.json").write_text(
        json.dumps(report_results, ensure_ascii=False, indent=1), encoding="utf-8")


def run(provider_name="all", limit=0):
    cases = build_cases()
    if limit:
        cases = cases[:limit]
    providers = PROVIDER_CANDIDATES if provider_name == "all" else [provider_name]
    all_results = []
    telemetry = {"qualification_version": QUALIFICATION_VERSION,
                 "providers": {p: {"credential_available": credential_available(p),
                                   "billing_mode": "free_currently" if p == "glm47_flash" else None}
                               for p in providers}}
    for prov in providers:
        for case in cases:
            t0 = time.time()
            r = run_case(case, prov)
            r["latency_ms"] = int((time.time() - t0) * 1000)
            all_results.append(r)
        time.sleep(0.2)
    # 每个 provider 单独汇总
    summary = {"qualification_version": QUALIFICATION_VERSION,
               "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
               "provider_results": {}}
    for prov in providers:
        pr = [r for r in all_results if r["provider"] == prov]
        decision = decide_role(pr)
        if not credential_available(prov):
            # §二/§五：credential 缺失 → PROVIDER_UNRESOLVED（无调用，非不合格）
            decision = {"role": "provider_unresolved",
                        "reason": {"contract_reliability": {
                            "credential_unavailable": True,
                            "succeeded": 0, "total": len(pr)},
                            "content_accuracy": {}, "numeric_integrity": None,
                            "attribution_integrity": None,
                            "report_quality": None, "transport_reliability": None},
                        "primary_candidate": False}
        summary["provider_results"][prov] = {
            "credential_available": credential_available(prov),
            "cases_total": len(pr),
            "cases_succeeded": sum(1 for r in pr if r["provider_status"] == "succeeded"),
            "role": decision["role"],
            "reason": decision["reason"],
        }
    report_results = [r for r in all_results if r.get("task_type") in (
        "africa_daily", "country_weekly", "major_event_brief")]
    write_artifacts(summary, all_results, telemetry, report_results)
    return summary, all_results


def run_smoke(provider_name="deepseek"):
    """§七：最小连接 smoke（仅 deepseek-v4-flash）。"""
    if provider_name == "deepseek":
        from scripts.ai.providers.deepseek_v4_flash import (
            DeepSeekV4FlashProvider, credential_available as ds_cred)
        if not ds_cred():
            return {"credential_available": False,
                    "result": "credential_injection_failed",
                    "requested_model": "deepseek-v4-flash",
                    "returned_model": None, "strict_json": False,
                    "http_status": None}
        prov = DeepSeekV4FlashProvider()
        return prov.smoke()
    return {"credential_available": credential_available(provider_name),
            "result": "not_supported", "strict_json": False}


def run_report_probe(provider_name="deepseek"):
    """§六：Report API Probe（RD1）——input → envelope → AI content → assembler → final。

    §七：exact_match 默认 null；只有真实比较后才 true/false（修复假阳性）。
    """
    cases = build_cases()
    rd1 = next(c for c in cases if c["case_id"] == "RD1")
    r = run_case(rd1, provider_name)
    per_ok = None   # §七：未真实比较 → null（不再默认 true）
    per_details = None
    if r.get("provider_status") == "succeeded" and r.get("assembled_report"):
        ok, errs = check_exact_copy(r["assembled_report"], rd1["input_payload"],
                                    "africa_daily")
        per_ok = ok
        per_details = errs or []
    tokens = r.get("tokens") or {}
    assembled = r.get("assembled_report")
    out = {
        "case_id": "RD1", "task_type": "africa_daily",
        "provider": provider_name,
        "credential_available": r.get("credential_available"),
        "requested_model": r.get("requested_model"),
        "returned_model": r.get("returned_model"),
        "provider_status": r.get("provider_status"),
        "contract_failure": r.get("contract_failure"),
        "failure_stage": r.get("failure_stage"),
        "attempt_count": r.get("attempt_count"),
        "latency_ms": r.get("latency_ms"),
        "strict_json_pass": r.get("strict_json_pass"),
        "schema_pass": r.get("schema_pass"),
        "period_start_exact_match": per_ok,   # null / true / false
        "period_end_exact_match": per_ok,
        "metadata_check": per_details,
        "input_tokens": tokens.get("input_tokens"),
        "output_tokens": tokens.get("output_tokens"),
        "total_tokens": tokens.get("total_tokens"),
        "errors": (r.get("errors") or [])[:5],
    }
    # §十二：同时保存 raw AI content 与 assembled report（区分模型/assembler 问题）
    raw = r.get("raw_text_excerpt")
    if raw:
        out["raw_ai_content_excerpt"] = raw[:600]
    if assembled:
        out["assembled_report"] = assembled
    print(json.dumps(out, ensure_ascii=False, indent=2))
    ok = (r.get("provider_status") == "succeeded" and r.get("strict_json_pass")
          and r.get("schema_pass") and per_ok is True
          and (r.get("returned_model") in (None, "deepseek-v4-flash")))
    out["report_probe"] = "PASS" if ok else "FAIL"
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "report_probe_result.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("REPORT_API_PROBE =", out["report_probe"])
    return 0 if ok else 1


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="all")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--smoke", action="store_true", help="只做 1 次最小连接 smoke")
    ap.add_argument("--report-probe", action="store_true",
                    help="只做 1 次 Report API Probe（RD1，deepseek-v4-flash）")
    ap.add_argument("--fixture-gate", action="store_true",
                    help="REPORT_FIXTURE_GATE：校验 8/8 committed fixtures")
    args = ap.parse_args(argv)
    if args.smoke:
        print(json.dumps(run_smoke(args.provider if args.provider != "all"
                                   else "deepseek"), ensure_ascii=False, indent=2))
        return 0
    if args.fixture_gate:
        g = fixture_gate()
        print(json.dumps(g, ensure_ascii=False, indent=1))
        return 0 if g.get("report_fixtures_ready") else 1
    if args.report_probe:
        return run_report_probe(args.provider if args.provider != "all"
                                else "deepseek")
    summary, results = run(args.provider, args.limit)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for r in results:
        print("  %s %s status=%s schema=%s strict_json=%s returned_model=%s" % (
            r["case_id"], r.get("semantic", "")[:30], r["provider_status"],
            r.get("schema_pass"), r.get("strict_json_pass"),
            r.get("returned_model")))
    return 0 if all(not s["credential_available"]
                    or s["role"] != "not_qualified" for s in
                    summary["provider_results"].values()) else 2


if __name__ == "__main__":
    sys.exit(main())
