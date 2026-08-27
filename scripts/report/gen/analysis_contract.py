#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage8C Package2 — Simple Analysis Contract + Machine Guards（§五/§六/§七）。

DeepSeek 只负责分析（executive_assessment / trend_analysis / outlook /
watch_points），绝不生成 facts / numbers / ids / source refs / verification /
importance / selection reasons / metrics / envelope。

ANALYSIS_SCHEMA（短、扁平、无嵌套复杂对象）：
  {
    "executive_assessment": "string",
    "trend_analysis": "string",
    "outlook": "string",
    "watch_points": ["string"]
  }

Machine Guards（高价值确定性检查，不过度设计）：
  A. 数字：分析中数字必须来自 Fact Pack 或合法 metadata/date，否则
     ANALYSIS_UNSUPPORTED_NUMBER → FAIL。
  B. 具体事件：不得新增 Fact Pack 不存在的具体事件陈述（实体边界检查）。
  C. 实体：organization/person/location 必须在 Fact Pack/source context 可找到。
  D. 归因：不得把 suspected/unconfirmed/conflicting/single_source 升级为确定事实。
"""
import json
import re

ANALYSIS_SCHEMA = {
    "type": "object",
    "required": ["executive_assessment", "trend_analysis", "outlook",
                 "watch_points"],
    "properties": {
        "executive_assessment": {"type": "string"},
        "trend_analysis": {"type": "string"},
        "outlook": {"type": "string"},
        "watch_points": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": True,  # 允许分析方附加小字段；核心 4 字段强制
}

_PROMPT_SYSTEM = (
    "你是 ASIP 平台的社会安全情报分析模块。你的唯一任务：基于给定的确定性事实包"
    "（Fact Pack）撰写简短的研判分析。\n"
    "硬性规则：\n"
    "1. 只使用 Fact Pack 中提供的字段。\n"
    "2. 不得引入 Fact Pack 中不存在的事件、人物、组织、地点、数字、日期或任何"
    "事实性主张（Do not introduce any event, person, organization, location, "
    "number, date or factual claim that is not present in the supplied facts.）。\n"
    "3. 不得改写事实数据库（Do not rewrite the fact database.）。\n"
    "4. 只生成分析（Generate analysis only.）。\n"
    "5. 不得输出 Markdown 代码块（Do not output markdown fences.）。\n"
    "6. 只返回一个 JSON 对象，字段：executive_assessment（string）、"
    "trend_analysis（string）、outlook（string）、watch_points（string 数组）。\n"
)

# 归因升级词（Fact Pack 有 single_source/conflicting/uncertainty 时检测）
_ESCALATION = ("已证实", "已确认", "已确证", "确凿", "实锤", "confirmed",
               "verified fact", "确认为事实", "已核实为", "无争议", "铁证")

# 实体后缀：中文专有名词启发（用于实体边界检查）
_ENTITY_SUFFIX = ("组织", "机构", "公司", "通讯社", "大学", "医院", "部队", "委员会",
                  "卫生部", "外交部", "军队", "央行", "联合会", "基金会", "政府",
                  "省", "市", "县", "区", "州", "镇", "地区", "流域", "湖", "河",
                  "半岛", "海湾", "城", "警察", "民兵", "叛军", "武装")
_EN_WORD_RE = re.compile(r"[A-Z][A-Za-z]{2,}(?:\s+[A-Z][A-Za-z]{2,})*")

# 泛化词停用（不是具体专有名词，不触发实体边界检查）
_GENERIC_TERMS = frozenset((
    "该地区", "本地区", "当地", "本周该地区", "上述事件", "这些事件", "相关机构",
    "有关部门", "相关国家", "受影响地区", "周边地区", "其他地区", "有关方面",
    "相关方面", "多国", "多地区", "灾区", "疫区", "该国", "此地区", "各相关方",
    "重点地区", "高风险地区", "多个地区", "边境地区", "偏远地区", "中心城市",
    "北部地区", "南部地区", "东部地区", "西部地区", "该省", "该市", "该县", "该区",
))


def build_analysis_prompt(fact_pack, max_facts=12):
    """构造 analysis prompt（§十五：只输入 Fact Pack 中真正需要的字段）。"""
    facts = []
    for f in fact_pack.get("social_facts", [])[:max_facts]:
        facts.append({
            "fact_id": f.get("fact_id"),
            "headline": f.get("headline_zh"),
            "verified_summary": f.get("verified_summary"),
            "country": f.get("country_iso3") or f.get("country"),
            "category": f.get("category"),
            "importance": f.get("importance_score"),
            "verification_status": f.get("verification_status"),
            "single_source": f.get("single_source_warning"),
            "conflicting": f.get("conflicting"),
            "uncertainties": (f.get("uncertainties") or [])[:3],
            "source_name": (f.get("source_refs") or [None])[0],
        })
    for f in fact_pack.get("disease_facts", [])[:max_facts]:
        facts.append({
            "fact_id": f.get("fact_id"),
            "headline": f.get("headline_zh"),
            "verified_summary": f.get("verified_summary"),
            "country": f.get("country_iso3"),
            "category": "public_health",
            "verification_status": f.get("verification_status"),
            "uncertainties": (f.get("uncertainties") or [])[:3],
            "source_name": (f.get("source_refs") or [None])[0],
        })
    user = {
        "instruction": "Use ONLY the supplied Fact Pack. Do not introduce any "
                       "event, person, organization, location, number, date or "
                       "factual claim not present in the supplied facts. "
                       "Do not rewrite the fact database. Generate analysis only.",
        "report_type": fact_pack.get("report_type"),
        "period": fact_pack.get("period"),
        "fact_count": fact_pack.get("fact_count"),
        "facts": facts,
        "trend_metrics": {k: v for k, v in (fact_pack.get("trend_metrics") or {}).items()
                          if isinstance(v, (int, float, str)) or v is None},
        "source_refs": fact_pack.get("source_refs"),
        "country_distribution": fact_pack.get("country_distribution"),
    }
    return _PROMPT_SYSTEM, "INPUT:\n" + json.dumps(user, ensure_ascii=False, indent=1)


def _collect_pack_numbers(fact_pack):
    """Fact Pack 全部合法数字（facts + metadata/date + trend metrics）。"""
    nums = set()
    for v, paths in (fact_pack.get("numeric_provenance") or {}).items():
        try:
            nums.add(int(str(v).replace(",", "")))
        except (TypeError, ValueError):
            continue
    for f in fact_pack.get("social_facts", []) + fact_pack.get("disease_facts", []):
        for n in (f.get("numeric_facts") or {}):
            try:
                nums.add(int(n))
            except (TypeError, ValueError):
                continue
    return nums


def _analysis_numbers(text):
    out = []
    for m in re.findall(r"(?<![\w.])(\d{1,3}(?:,\d{3})*|\d+)(?![\w.])", str(text or "")):
        try:
            out.append(int(m.replace(",", "")))
        except ValueError:
            continue
    return out


def _entity_tokens(text):
    """中文实体候选（带地理/机构后缀）与英文专有名词候选；排除泛化词。"""
    toks = set()
    for m in re.finditer(r"[\u4e00-\u9fff]{2,10}(?:%s)" % "|".join(_ENTITY_SUFFIX), text):
        tok = m.group(0)
        if tok not in _GENERIC_TERMS:
            toks.add(tok)
    for m in _EN_WORD_RE.finditer(text):
        toks.add(m.group(0))
    return toks


def validate_analysis(parsed, fact_pack):
    """Machine Guards（§六 A-D）。返回 (ok, errors[])。"""
    errors = []
    if not isinstance(parsed, dict):
        return False, ["analysis not object"]
    # schema（扁平 4 字段）
    for k in ("executive_assessment", "trend_analysis", "outlook"):
        if not isinstance(parsed.get(k), str) or not parsed[k].strip():
            errors.append("analysis schema: %s missing/empty" % k)
    wp = parsed.get("watch_points")
    if not isinstance(wp, list) or not all(isinstance(x, str) for x in wp):
        errors.append("analysis schema: watch_points must be string[]")
    if errors:
        return False, errors

    blob = " ".join([str(parsed.get("executive_assessment") or ""),
                     str(parsed.get("trend_analysis") or ""),
                     str(parsed.get("outlook") or ""),
                     " ".join(wp or [])])
    # A. 数字边界
    pack_nums = _collect_pack_numbers(fact_pack)
    for n in _analysis_numbers(blob):
        if n not in pack_nums:
            errors.append("ANALYSIS_UNSUPPORTED_NUMBER %d" % n)
    # C. 实体边界（具体专有名词必须在 Fact Pack/source context 可找到）
    vocab = set(fact_pack.get("entity_vocab") or [])
    vocab |= set(fact_pack.get("source_refs") or [])
    for f in fact_pack.get("social_facts", []) + fact_pack.get("disease_facts", []):
        vocab.add(str(f.get("headline_zh") or ""))
        vocab.add(str(f.get("verified_summary") or ""))
    vocab_txt = " ".join(vocab)
    for tok in _entity_tokens(blob):
        if tok and tok not in vocab_txt:
            errors.append("ANALYSIS_UNSUPPORTED_NAMED_REFERENCE %s" % tok)
    # D. 归因升级（Fact Pack 有不确定标记时）
    has_uncertain = (fact_pack.get("verification", {}).get("single_source_count", 0) > 0 or
                     fact_pack.get("verification", {}).get("conflicting_count", 0) > 0 or
                     bool(fact_pack.get("uncertainties")))
    if has_uncertain:
        for w in _ESCALATION:
            if w in blob:
                errors.append("ANALYSIS_ATTRIBUTION_ESCALATION %s" % w)
    return (not errors), errors
