#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 8C Package 1 — Deterministic Attribution Safety Layer.

纯确定性（non-AI、fail-closed、可审计）归因安全层。AI_CALLS = 0。

定位：
  AI structured output → Attribution Safety Layer → existing publication /
  report eligibility gates → Public / Report Input

设计约束（Stage8C Package 1 规格 §一-§十五）：
  - 不调用任何 LLM / 不联网。
  - 输入 marker 是事实约束（canonical/qualification input 中的
    alleged/claimed/suspected/unconfirmed/conflicting/single_source 及等价 marker）。
  - 四类安全规则（A alleged/claimed、B suspected/unconfirmed、
    C conflicting、D single_source）。
  - Validator first：只验证、不修复，输出可审计 evidence。
  - Deterministic correction：仅在 input fact ↔ output field 存在确定映射时
    允许；只补充证据状态/不确定性限定；不得增加新事实、不得改数字/实体/
    日期/地点/来源。
  - Fail-closed：无法确定映射 → AUTO_CORRECTION=false →
    ATTRIBUTION_SAFETY_GATE=FAIL → publication/report-input 均不可用。
  - Correction 后必须重新验证（POST_CORRECTION_ATTRIBUTION_GATE）。
  - 保留 original_ai_output / corrected_output / corrections[]（每条含
    fact_id/marker/field/before/after/rule_id）。
  - Telemetry：按 Social / Disease 分列 attribution_gate_checked /
    attribution_gate_pass / attribution_auto_corrected / attribution_hold。

用法（库）：
  from scripts.ai.safety.attribution_safety import run_attribution_safety
  result = run_attribution_safety(input_payload, ai_output_parsed, task_type)

用法（CLI）：
  python scripts/ai/safety/attribution_safety.py --input in.json --output out.json
      --task-type stage4_event_enrichment
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SAFETY_VERSION = "stage8c-v1"

# ────────────────────────────────────────────────────────────────────────────
# §三 四类保留规则（语义等价词典 + 通用归因正则）
# ────────────────────────────────────────────────────────────────────────────
# A. alleged / claimed —— 必须直接保留"据称/声称/被指"或严格语义等价
ALLEGED_OUT_KW = ("据称", "声称", "被指", "指控", "指称",
                  "alleged", "claimed", "reportedly", "according to")
# B. suspected / unconfirmed —— 必须保留"疑似/可能/尚未证实/未获确认/待确认/有待核实"
UNCONFIRMED_OUT_KW = ("疑似", "可能", "尚未证实", "未获确认", "待确认", "有待核实",
                      "未证实", "未经核实", "尚未核实", "尚未确认", "尚未公布",
                      "suspected", "unconfirmed", "未完全确认", "未获证实")
# C. conflicting —— 必须保留"说法不一/信息存在冲突/不同来源存在差异/尚无法确认"
CONFLICTING_OUT_KW = ("说法不一", "信息存在冲突", "不同来源存在差异", "尚无法确认",
                      "存在冲突", "相互矛盾", "conflicting", "说法不一致")
# D. single_source —— 必须保留"据<来源>报道/单一来源/目前仅一个来源/尚缺乏交叉验证"
SINGLE_SOURCE_OUT_KW = ("单一来源", "仅一个来源", "只有一个来源", "单一信源",
                        "目前仅一个来源", "仅此一个来源", "仅有单一来源",
                        "仅一个来源报道", "缺乏交叉验证", "尚缺乏交叉验证",
                        "单一来源支持", "single source", "single_source",
                        "仅有一个来源", "仅一个来源（")
# 通用来源归因正则：据<来源>报道/消息/信息/称/表示；<来源>通讯社/新闻社…报道
_SRC_RE = re.compile(
    r"据[\u4e00-\u9fffA-Za-z0-9·()（）]{1,28}(?:报道|消息|信息|称|表示|转述|通报)",
    re.I)
_SRC_RE2 = re.compile(
    r"[\u4e00-\u9fffA-Za-z0-9·()（）]{1,24}(?:通讯社|新闻社|新闻机构)"
    r"[\u4e00-\u9fff]{0,6}(?:报道|消息|称|通报)", re.I)

# §六 确定性修正固定句（只允许这些模板，不生成自由文本）
_TMPL_SINGLE_SOURCE = "据{src}报道，目前仅获单一来源支持，尚缺乏交叉验证。"
_TMPL_SINGLE_SOURCE_NOSRC = "目前仅获单一来源支持，尚缺乏交叉验证。"
_TMPL_CONFLICTING = "相关信息存在冲突，尚无法确认。"
_TMPL_UNCONFIRMED = "相关情况尚未证实。"
_TMPL_ALLEGED = "据称，尚未获得独立证实。"

# 数字句"不确定性限定"词（§十三：禁止 suspected→confirmed 数字污染）。
# 数字陈述句若含以下任一 → 视为已保留不确定性；否则判定为确定化断言。
_NUM_UNCERT_KW = ("疑似", "可能", "尚未", "未证实", "未确认", "未核实", "未经",
                  "未获", "据", "约", "左右", "估计", "预计", "初步", "媒体",
                  "转述", "通报", "称", "待", "存疑", "待核")
_SENT_SPLIT = re.compile(r"(?<=[。！？!?；;])")

# 数字中文化等价（用于 50000 ↔ 5万 锚定；仅只读，不用于改写数字）
_CN_NUM_UNIT = {"万": 10000, "亿": 100000000, "千": 1000}

# ────────────────────────────────────────────────────────────────────────────
# Marker 提取（input payload → markers[]，结构化优先 + 文本补充）
# ────────────────────────────────────────────────────────────────────────────

def _walk_strings(node, out):
    """递归收集 payload 内全部字符串（用于文本级 marker 检测）。"""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str):
                out.append(k)
            _walk_strings(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_strings(v, out)
    elif isinstance(node, str):
        out.append(node)


def _src_name_from_input(payload):
    """从 input 解析可信来源名（source_links[].source_name / primary_source /
    source_groups 等）。返回 (ok, name)。"""
    names = []
    sl = payload.get("source_links") if isinstance(payload, dict) else None
    if isinstance(sl, list):
        for s in sl:
            if isinstance(s, dict) and s.get("source_name"):
                names.append(str(s["source_name"]))
    ps = payload.get("primary_source") if isinstance(payload, dict) else None
    if ps and isinstance(ps, str) and ps.strip() and ps.strip() not in ("None", "null"):
        names.append(ps.strip())
    sg = payload.get("source_groups") if isinstance(payload, dict) else None
    if isinstance(sg, list) and not names:
        for g in sg:
            if isinstance(g, str) and g.strip():
                names.append(g.strip())
    if not names:
        return False, ""
    # 优先取最短且非占位符的名称（避免长描述污染）
    cleaned = [n for n in names if n and n.lower() not in ("none", "null", "n/a")]
    if not cleaned:
        return False, ""
    cleaned.sort(key=len)
    return True, cleaned[0]


def extract_markers(input_payload):
    """确定性提取 input marker。返回 markers: list[dict]。

    每条：{class: str, evidence_path: str, source_text: str,
           source_kind: "structured"|"text", anchor: "event"|"numeric"|None}
    """
    markers = []
    inp = input_payload or {}
    txts = []
    _walk_strings(inp, txts)
    joined = "\n".join(txts)

    def add(cls, path, src, kind, anchor):
        markers.append({"class": cls, "evidence_path": path,
                        "source_text": str(src)[:120], "source_kind": kind,
                        "anchor": anchor})

    # ── D. single_source ──
    if isinstance(inp, dict):
        if inp.get("independent_source_count") == 1:
            add("single_source", "independent_source_count", "independent_source_count=1",
                "structured", "event")
        if str(inp.get("verification_level", "")).lower() == "single_source":
            add("single_source", "verification_level", "verification_level=single_source",
                "structured", "event")
        legacy = inp.get("legacy_payload")
        if isinstance(legacy, dict):
            conf = str(legacy.get("confidence", "") or "")
            if "单一来源" in conf or "single source" in conf.lower():
                add("single_source", "legacy_payload.confidence", conf,
                    "structured", "event")
    for kw in ("单一来源", "single source", "single_source", "仅一个来源", "只有一个来源"):
        if kw in joined:
            add("single_source", "<text>", kw, "text", "event")
            break

    # ── C. conflicting ──
    if isinstance(inp, dict):
        cfs = inp.get("conflicting_fields")
        if isinstance(cfs, list) and cfs:
            add("conflicting", "conflicting_fields",
                "conflicting_fields=%s" % json.dumps(cfs, ensure_ascii=False)[:80],
                "structured", "event")
        elif "conflicting_fields" in inp:
            # 键存在（含空）：S8 multi-country 场景，按 marker 处理（§十）
            add("conflicting", "conflicting_fields", "conflicting_fields key present",
                "structured", "event")
        legacy = inp.get("legacy_payload")
        if isinstance(legacy, dict):
            ltxt = json.dumps(legacy, ensure_ascii=False)
            if re.search(r"conflict|矛盾|冲突", ltxt, re.I):
                add("conflicting", "legacy_payload", "legacy conflict indicator",
                    "structured", "event")
    for kw in ("conflicting", "说法不一", "存在冲突", "相互矛盾", "说法不一致"):
        if kw in joined:
            add("conflicting", "<text>", kw, "text", "event")
            break

    # ── B. suspected / unconfirmed ──
    if isinstance(inp, dict):
        for f in ("suspected_cases", "probable_cases"):
            if inp.get(f) is not None:
                add("unconfirmed", f, "%s=%s" % (f, inp.get(f)), "structured", "numeric")
        cct = str(inp.get("case_count_type", "") or "")
        if cct.lower() in ("suspected", "unknown"):
            add("unconfirmed", "case_count_type", "case_count_type=%s" % cct,
                "structured", "numeric")
        vs = str(inp.get("verification_status", "") or "").lower()
        if any(w in vs for w in ("unconfirm", "suspect", "pending", "not_checked")):
            add("unconfirmed", "verification_status", "verification_status=%s" % vs,
                "structured", "event")
        unc = inp.get("uncertainties")
        if isinstance(unc, list) and unc:
            add("unconfirmed", "uncertainties", json.dumps(unc, ensure_ascii=False)[:120],
                "structured", "event")
        vc = inp.get("verification_confidence")
        if isinstance(vc, (int, float)) and vc < 80:
            add("unconfirmed", "verification_confidence", "verification_confidence=%s" % vc,
                "structured", "event")
    for kw in ("suspected", "疑似", "unconfirmed", "尚未证实", "未获确认",
               "待确认", "有待核实", "未确认"):
        if kw in joined:
            add("unconfirmed", "<text>", kw, "text", "event")
            break

    # ── A. alleged / claimed ──
    for kw in ("alleged", "claimed", "reportedly", "指控", "声称", "据称",
               "被指", "aurait", "selon", "according to"):
        if kw in joined:
            add("alleged_claimed", "<text>", kw, "text", "event")
            break
    # 结构化兜底：标题含指称语义
    if isinstance(inp, dict):
        tl = str(inp.get("title_original") or inp.get("title_cn") or "")
        if re.search(r"alleg|claim|reportedly|据称|指控|声称|被指|aurait", tl, re.I):
            add("alleged_claimed", "title", tl[:80], "structured", "event")

    # 去重（同 class 同 anchor 只保留最强证据）
    seen = set()
    dedup = []
    for m in markers:
        key = (m["class"], m["anchor"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(m)
    return dedup


# ────────────────────────────────────────────────────────────────────────────
# Validator（只验证；§四）
# ────────────────────────────────────────────────────────────────────────────

def _has_pattern(text, kw_tuple, regexes=()):
    t = text or ""
    for kw in kw_tuple:
        if kw in t:
            return kw
    for rx in regexes:
        m = rx.search(t)
        if m:
            return m.group(0)[:40]
    return None


def _output_text_fields(output):
    """返回 (all_text, field_hits)：输出全文本（json.dumps）与字段级命中映射。"""
    out = output or {}
    all_text = json.dumps(out, ensure_ascii=False)

    # 字段级命中：用于 matched_output_field 审计
    def collect(node, path, hits):
        if isinstance(node, dict):
            for k, v in node.items():
                collect(v, "%s.%s" % (path, k) if path else k, hits)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                collect(v, "%s[%d]" % (path, i) if path else "[%d]" % i, hits)
        elif isinstance(node, str):
            hits.append((path, node))
    field_texts = []
    collect(out, "", field_texts)
    return all_text, field_texts


def _match_field(hits, pattern):
    """返回第一个包含 pattern 的字段路径；无 → None。"""
    for path, txt in hits:
        if pattern and pattern in txt:
            return path
    return None


_CLASS_PATTERNS = {
    "alleged_claimed": (ALLEGED_OUT_KW, ()),
    "unconfirmed": (UNCONFIRMED_OUT_KW, ()),
    "conflicting": (CONFLICTING_OUT_KW, ()),
    "single_source": (SINGLE_SOURCE_OUT_KW, (_SRC_RE, _SRC_RE2)),
}


def _cn_number_form(n):
    """数字的中文单位形式（50000 → '5万'），用于输出锚定；无则 None。"""
    for unit, mult in _CN_NUM_UNIT.items():
        if n % mult == 0 and n // mult > 0:
            return "%d%s" % (n // mult, unit)
    return None


def _numeric_fields_of(payload):
    """input 中非 null 的数值字段列表 [(field, int)]。"""
    out = []
    if not isinstance(payload, dict):
        return out
    for f in ("suspected_cases", "probable_cases", "total_cases",
              "confirmed_cases", "deaths", "recoveries"):
        v = payload.get(f)
        if isinstance(v, (int, float)) and v is not None:
            out.append((f, int(v)))
    return out


def _split_sentences(text):
    parts = _SENT_SPLIT.split(text or "")
    return [p.strip() for p in parts if p and p.strip()]


def _find_numeric_assertions(output, input_payload):
    """数字级检查：输出中陈述 input 数字的句子若无不确定性限定 → 返回失败列表。

    返回 list[ {field, sentence, number_desc, failure_reason} ]。

    §七（Repair）：仅扫描 user-facing natural language 字段
    （id/url/日期/enum/数字 raw 字段不参与数字句判定）。
    """
    nums = _numeric_fields_of(input_payload)
    if not nums:
        return []
    # 需要 unconfirmed marker 存在才检查（数字可信度语境）
    # ——由调用方先确认 marker；此处只做数字句定位与判定。
    failures = []
    # 遍历输出文本字段，定位含 input 数字的句子
    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, "%s.%s" % (path, k) if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, "%s[%d]" % (path, i) if path else "[%d]" % i)
        elif isinstance(node, str):
            # §七：非 user-facing 字段（id/url/日期/enum/数字 raw）跳过
            if not _leaf_is_user_facing(path):
                return
            for sent in _split_sentences(node):
                for f, n in nums:
                    if str(n) in sent:
                        if not any(kw in sent for kw in _NUM_UNCERT_KW):
                            failures.append({
                                "field": path or "text",
                                "sentence": sent,
                                "number_desc": "%s=%d" % (f, n),
                                "failure_reason":
                                    "numeric_assertion_without_uncertainty_qualifier",
                            })
                        break  # 该句判定一次
                    cn = _cn_number_form(n)
                    if cn and cn in sent:
                        if not any(kw in sent for kw in _NUM_UNCERT_KW):
                            failures.append({
                                "field": path or "text",
                                "sentence": sent,
                                "number_desc": "%s=%d(%s)" % (f, n, cn),
                                "failure_reason":
                                    "numeric_assertion_without_uncertainty_qualifier",
                            })
                        break
    walk(output, "")
    return failures


def validate_attribution(input_payload, output, markers=None):
    """Validator（§四/§八）。只判定，不修改。

    返回 dict：
      status: "PASS"|"FAIL"
      checks: list[ {input_marker, matched_output_field, matched_semantic_pattern,
                     failure_reason} ]
      numeric_failures: list[ {field, sentence, number_desc, failure_reason} ]
      gate: "PASS"|"FAIL"
    """
    markers = markers if markers is not None else extract_markers(input_payload)
    if not markers:
        return {"status": "PASS", "checks": [], "numeric_failures": [],
                "gate": "PASS"}

    all_text, field_texts = _output_text_fields(output)
    checks = []
    ok = True
    for m in markers:
        cls = m["class"]
        kw_tuple, regexes = _CLASS_PATTERNS[cls]
        hit = _has_pattern(all_text, kw_tuple, regexes)
        if hit:
            checks.append({
                "input_marker": m,
                "matched_output_field": _match_field(field_texts, hit),
                "matched_semantic_pattern": hit,
                "failure_reason": None,
            })
        else:
            ok = False
            checks.append({
                "input_marker": m,
                "matched_output_field": None,
                "matched_semantic_pattern": None,
                "failure_reason": "no %s preservation pattern found in output" % cls,
            })
    # §十三 数字级检查：unconfirmed marker 存在且 input 含数字 → 数字句确定性
    numeric_failures = []
    if any(m["class"] == "unconfirmed" for m in markers):
        numeric_failures = _find_numeric_assertions(output, input_payload)
        if numeric_failures:
            ok = False
    return {"status": "PASS" if ok else "FAIL",
            "checks": checks,
            "numeric_failures": numeric_failures,
            "gate": "PASS" if ok else "FAIL"}


# ────────────────────────────────────────────────────────────────────────────
# Deterministic Correction（§五-§八）
# ────────────────────────────────────────────────────────────────────────────

# §七（Repair）：Safety correction 只允许作用于 USER-FACING NATURAL LANGUAGE
# 字段。以真实 schema 字段为准：
#   enrichment: title_zh / summary_zh / key_facts[].fact / uncertainties[]
#   disease   : title_zh / summary_zh / key_changes[].description / uncertainties[]
#   report    : headline_zh / fact_summary / assessment / outlook
# 禁止修改：*_id / event_id / disease_event_id / source_id / source_refs / url /
#   timestamps / 日期 metadata / country_iso3 / enum 字段 / 数字 raw 字段。
_USER_FACING_LEAF_FIELDS = (
    "title_zh", "summary_zh", "summary", "summary_cn", "fact_summary",
    "headline_zh", "assessment", "outlook", "what_happened",
    "fact", "description", "text", "body_extracted", "uncertainties")
_FORBIDDEN_LEAF_HINTS = (
    "_id", "url", "iso3", "code", "timestamp", "time", "date", "week_start",
    "week_end", "period", "count", "cases", "deaths", "recoveries", "status",
    "type", "location", "lat", "long", "score", "confidence")


def _leaf_is_user_facing(field_path):
    """字段路径叶子是否属于 user-facing 自然语言 allowlist（§七 Repair）。"""
    leaf = (field_path or "").split(".")[-1]
    leaf = re.sub(r"\[\d+\]", "", leaf)
    if leaf in _USER_FACING_LEAF_FIELDS:
        return True
    if any(h in leaf for h in _FORBIDDEN_LEAF_HINTS):
        return False
    return False


def _fact_mapping_confirmed(input_payload, n):
    """§八（Repair）Fact-Aware：数字 n 必须可映射到 input 的
    unconfirmed/suspected 数字事实字段（或 uncertainties 提及），才允许 B2 修正。
    返回 (ok, field)。"""
    if not isinstance(input_payload, dict):
        return False, None
    for f in ("suspected_cases", "probable_cases", "total_cases",
              "confirmed_cases", "deaths", "recoveries"):
        v = input_payload.get(f)
        if isinstance(v, (int, float)) and int(v) == n:
            return True, f
    unc = input_payload.get("uncertainties")
    if isinstance(unc, list):
        for u in unc:
            if str(n) in str(u):
                return True, "uncertainties"
    return False, None


def _numeric_anchor_ok(input_payload, output):
    """数字级锚定：unconfirmed 数字 marker 的数字是否在输出出现。
    支持中文单位（50000 ↔ 5万）。返回 (ok, number_desc)。"""
    if not isinstance(input_payload, dict):
        return False, None
    nums = []
    for f in ("suspected_cases", "probable_cases", "total_cases", "confirmed_cases",
              "deaths", "recoveries"):
        v = input_payload.get(f)
        if isinstance(v, (int, float)) and v is not None:
            nums.append((f, int(v)))
    if not nums:
        return False, None
    all_text = json.dumps(output, ensure_ascii=False)
    for f, n in nums:
        if str(n) in all_text:
            return True, "%s=%d" % (f, n)
        # 中文单位形式：50000 → 5万 / 5 万
        for unit, mult in _CN_NUM_UNIT.items():
            if n % mult == 0:
                cn = "%d%s" % (n // mult, unit)
                if cn in all_text:
                    return True, "%s=%d(%s)" % (f, n, cn)
    return False, None


def _deterministic_correction(input_payload, output, markers, failed_checks,
                              numeric_failures):
    """仅在映射 100% 确定时修正。返回 (corrections, corrected_output, ok)。

    修正只做两类确定性补充：
      - uncertainties 数组追加固定限定句（事件级 marker）
      - 数字句就地插入"相关数字尚未证实"（§十三 数字污染，B2）
    不改数字/实体/日期/地点/来源；不生成自由文本。
    """
    if not isinstance(output, dict):
        return [], output, False
    out = json.loads(json.dumps(output))  # deep copy
    corrections = []

    # 锚定检查：事件级字段存在（summary_zh / uncertainties 任一可写）
    has_event_field = any(k in out for k in ("summary_zh", "uncertainties", "title_zh"))
    num_ok, num_desc = _numeric_anchor_ok(input_payload, out)
    if not has_event_field:
        return [], out, False

    # ── 数字句就地修正（SAFETY-CORR-B2）：数字被确定化 → 句尾插入限定 ──
    # §七（Repair）：仅 user-facing 自然语言字段可修；id/url/日期/enum/数字
    # raw 字段不可变。§八（Repair）：数字必须能映射 input unconfirmed 事实。
    for nf in numeric_failures:
        field_path = nf["field"]
        sent = nf["sentence"]
        # §七：allowlist 边界
        if not _leaf_is_user_facing(field_path):
            continue  # 非 user-facing 字段（如 *_id）→ 不修正（由 validator 另行判定）
        # §八：fact-aware——数字必须映射 input unconfirmed 数字事实
        num_val = None
        nd = nf.get("number_desc") or ""
        mnum = re.search(r"(\d+)", nd)
        if mnum:
            num_val = int(mnum.group(1))
        if num_val is not None:
            fm_ok, _fm_field = _fact_mapping_confirmed(input_payload, num_val)
            if not fm_ok:
                # 无法确认自然语言句 ↔ unconfirmed 事实映射 → 不自动修（HOLD 交由上层）
                continue
        parts = [p for p in field_path.split(".") if p] if field_path else []
        if not parts:
            return [], out, False

        def get_path(node, path):
            cur = node
            for p0 in path:
                if "[" in p0:
                    base, rest = p0.split("[", 1)
                    i = int(rest.rstrip("]"))
                    cur = cur[base][i]
                else:
                    cur = cur[p0]
            return cur

        def set_path(node, path, value):
            if not path:
                return value
            p0 = path[0]
            if "[" in p0:
                base, rest = p0.split("[", 1)
                i = int(rest.rstrip("]"))
                node[base][i] = set_path(node[base][i], path[1:], value)
            else:
                node[p0] = set_path(node[p0], path[1:], value)
            return node

        try:
            target = get_path(out, parts)
        except (KeyError, IndexError, TypeError):
            # 路径解析失败 → 无法 100% 锚定 → fail-closed（不猜测）
            return [], out, False
        if not isinstance(target, str) or sent not in target:
            return [], out, False
        before = target
        fixed = _insert_sentence_qualifier(target, sent, "，相关数字尚未证实")
        out = set_path(out, parts, fixed)
        corrections.append({
            "fact_id": nf["number_desc"],
            "marker": "unconfirmed",
            "field": field_path,
            "before": before,
            "after": fixed,
            "rule_id": "SAFETY-CORR-B2",
            "numeric_anchor": num_desc,
        })

    # ── 事件级 marker → uncertainties 追加固定句 ──
    for c in failed_checks:
        m = c["input_marker"]
        cls = m["class"]
        rule_id = None
        text = None
        if cls == "single_source":
            ok_src, name = _src_name_from_input(input_payload)
            if ok_src and len(name) <= 40:
                text = _TMPL_SINGLE_SOURCE.format(src=name)
                rule_id = "SAFETY-CORR-D1"
            else:
                text = _TMPL_SINGLE_SOURCE_NOSRC
                rule_id = "SAFETY-CORR-D1N"
        elif cls == "conflicting":
            text = _TMPL_CONFLICTING
            rule_id = "SAFETY-CORR-C1"
        elif cls == "unconfirmed":
            text = _TMPL_UNCONFIRMED
            rule_id = "SAFETY-CORR-B1"
        elif cls == "alleged_claimed":
            text = _TMPL_ALLEGED
            rule_id = "SAFETY-CORR-A1"
        if text is None:
            return [], out, False

        before = json.dumps(out.get("uncertainties"), ensure_ascii=False)
        unc = out.get("uncertainties")
        if not isinstance(unc, list):
            unc = []
        if text not in unc:  # 去重：同一限定句不重复追加
            unc.append(text)
        out["uncertainties"] = unc
        after = json.dumps(out.get("uncertainties"), ensure_ascii=False)
        corrections.append({
            "fact_id": m.get("evidence_path"),
            "marker": cls,
            "field": "uncertainties",
            "before": before,
            "after": after,
            "rule_id": rule_id,
            "numeric_anchor": num_desc,
        })
    return corrections, out, True


def _insert_sentence_qualifier(text, sentence, qualifier):
    """在目标句句尾标点前插入限定词（不改句子内容/数字/实体）。
    qualifier 不含句尾标点；原句尾标点保留，无标点则补句号。"""
    if sentence not in text:
        return text
    idx = text.index(sentence)
    end = idx + len(sentence)
    core = sentence.rstrip("。！？!?；;")
    tail = sentence[len(core):]
    if not tail:
        tail = "。"
    new_sent = core + qualifier + tail
    return text[:idx] + new_sent + text[end:]


# ────────────────────────────────────────────────────────────────────────────
# 顶层入口（§四-§九）
# ────────────────────────────────────────────────────────────────────────────

def run_attribution_safety(input_payload, ai_output, task_type=None,
                           telemetry=None):
    """执行完整 Safety Layer 流程。

    参数：
      input_payload : canonical/qualification input（dict）
      ai_output     : AI structured output（dict，已 parse）
      task_type     : "stage4_event_enrichment"|"disease_summary"|...（用于 telemetry 分组）
      telemetry     : 可选 dict，就地累加计数器

    返回 dict（§九 审计 + §十二 gates）：
      safety_version, input_markers, validator (pre), corrections,
      corrected_output, post_validator, attribution_safety_status,
      publication_eligible, report_input_eligible, manual_review_required,
      original_ai_output, telemetry
    """
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    group = "disease" if (task_type or "").startswith("disease") else "social"
    t = telemetry.setdefault(group, {})
    for _k in ("attribution_gate_checked", "attribution_gate_pass",
               "attribution_auto_corrected", "attribution_hold"):
        t.setdefault(_k, 0)
    t["attribution_gate_checked"] = t["attribution_gate_checked"] + 1

    markers = extract_markers(input_payload)
    pre = validate_attribution(input_payload, ai_output, markers)

    result = {
        "safety_version": SAFETY_VERSION,
        "task_type": task_type,
        "input_markers": markers,
        "validator_pre_correction": pre,
        "corrections": [],
        "corrected_output": ai_output,
        "validator_post_correction": None,
        "original_ai_output": ai_output,
        "attribution_safety_status": None,
        "attribution_safety_gate": None,
        "publication_eligible": None,
        "report_input_eligible": None,
        "manual_review_required": None,
        "telemetry": {},
    }

    if pre["status"] == "PASS":
        result["attribution_safety_status"] = "PASS"
        result["attribution_safety_gate"] = "PASS"
        result["publication_eligible"] = True
        result["report_input_eligible"] = True
        result["manual_review_required"] = False
        t["attribution_gate_pass"] = t.get("attribution_gate_pass", 0) + 1
        t["attribution_auto_corrected"] = t.get("attribution_auto_corrected", 0) + 0
        t["attribution_hold"] = t.get("attribution_hold", 0) + 0
        result["telemetry"] = dict(telemetry)
        return result

    # FAIL → 尝试确定性修正（§五-§八）
    failed = [c for c in pre["checks"] if c["failure_reason"]]
    corrections, corrected, mapped = _deterministic_correction(
        input_payload, ai_output, markers, failed, pre.get("numeric_failures") or [])
    if not mapped:
        # §七 fail-closed：无法 100% 确定映射 → HOLD
        result["attribution_safety_status"] = "FAIL"
        result["attribution_safety_gate"] = "FAIL"
        result["publication_eligible"] = False
        result["report_input_eligible"] = False
        result["manual_review_required"] = True
        t["attribution_hold"] = t.get("attribution_hold", 0) + 1
        result["telemetry"] = dict(telemetry)
        return result

    # 有映射 → 应用修正并重新验证（§八）
    result["corrections"] = corrections
    result["corrected_output"] = corrected
    if corrections:
        t["attribution_auto_corrected"] = t.get("attribution_auto_corrected", 0) + 1
    post = validate_attribution(input_payload, corrected, markers)
    result["validator_post_correction"] = post
    if post["status"] == "PASS":
        result["attribution_safety_status"] = "PASS"
        result["attribution_safety_gate"] = "PASS"
        result["publication_eligible"] = True
        result["report_input_eligible"] = True
        result["manual_review_required"] = False
        t["attribution_gate_pass"] = t.get("attribution_gate_pass", 0) + 1
    else:
        result["attribution_safety_status"] = "FAIL"
        result["attribution_safety_gate"] = "FAIL"
        result["publication_eligible"] = False
        result["report_input_eligible"] = False
        result["manual_review_required"] = True
        t["attribution_hold"] = t.get("attribution_hold", 0) + 1
    result["telemetry"] = dict(telemetry)
    return result


# ────────────────────────────────────────────────────────────────────────────
# §十二 Publication / Report-input Integration（硬门组件）
# ────────────────────────────────────────────────────────────────────────────

def attribution_safety_gate(input_payload, ai_output, task_type=None):
    """§十二 硬门：attribution_safety_gate = PASS 才允许 Public admission 与
    Report input eligibility。

    纯确定性、可审计；FAIL 或 UNKNOWN → 必须 hold，不得公开。
    供 enrichment writeback / promote / report input 组装前调用。
    """
    res = run_attribution_safety(input_payload, ai_output, task_type)
    return {
        "attribution_safety_gate": res["attribution_safety_gate"],
        "publication_eligible": res["publication_eligible"],
        "report_input_eligible": res["report_input_eligible"],
        "manual_review_required": res["manual_review_required"],
        "corrections": res["corrections"],
        "validator_pre_correction": res["validator_pre_correction"],
        "validator_post_correction": res["validator_post_correction"],
    }


# ────────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────────

def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Attribution Safety Layer (deterministic)")
    ap.add_argument("--input", required=True, help="input payload JSON 文件")
    ap.add_argument("--output", required=True, help="AI structured output JSON 文件")
    ap.add_argument("--task-type", default="stage4_event_enrichment")
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args(argv)
    inp = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out = json.loads(Path(args.output).read_text(encoding="utf-8"))
    res = run_attribution_safety(inp, out, args.task_type)
    print(json.dumps(res, ensure_ascii=False,
                     indent=2 if args.pretty else None))
    return 0 if res["attribution_safety_gate"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
