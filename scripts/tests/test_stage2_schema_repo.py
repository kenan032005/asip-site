#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_stage2_schema_repo.py —— Stage 2A 回归测试

覆盖：
- identifiers：ID 稳定性、URL 规范化、Reuters 转载去重、幂等
- normalizers：国家/语言/severity 映射；Reuters 单一来源不为官方通报；ReliefWeb NGO 不为联合国官方
- publication_policy：确定性发布规则
- schema_validator：5 份 schema 可加载；合法对象通过、非法对象失败
- repository：原子写入、自动备份、去重、变更计数、加载往返

退出码：FAIL>0 → 1；否则 0。
"""

import json
import sys
import os
import tempfile
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
sys.path.insert(0, str(SCRIPTS))

from data.identifiers import (
    article_id, event_id, content_hash, quarantine_id, normalize_url,
    is_article_id, is_event_id,
)
from data.normalizers import (
    normalize_country_code, normalize_language, normalize_event_severity,
    derive_verification_level, derive_needs_translation,
)
from data.publication_policy import evaluate, VERIFICATION_LABEL_CN
from data.repository import Repository
from data.schema_validator import validate_instance, load_schema

PASS = 0
FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  {extra}")


def section(title):
    print(f"\n=== {title} ===")


# ─────────────────────────────────────────────────────
section("identifiers：稳定性与规范化")
u1 = "https://www.reuters.com/article/abc?utm_source=news&fbclid=XYZ#frag"
u2 = "https://www.reuters.com/article/abc?fbclid=ZZZ"
check("normalize_url 剔除追踪参数与片段并小写域名",
      normalize_url(u1) == "https://reuters.com/article/abc", normalize_url(u1))
check("normalize_url 同路径不同追踪参数归一为同值",
      normalize_url(u1) == normalize_url(u2))
aid1 = article_id(canonical_url=u1)
aid2 = article_id(canonical_url=u2)
check("article_id 基于 canonical_url 稳定（幂等）", aid1 == aid2)
check("article_id 格式 ART_<16hex>", is_article_id(aid1), aid1)
# 无 canonical_url 时基于 source+time+title
aid3 = article_id(source_id="chad-tchadinfos", published_at="2026-07-28T16:40:18Z",
                  title="Mandoul conflit")
aid4 = article_id(source_id="chad-tchadinfos", published_at="2026-07-28T16:40:18Z",
                  title="Mandoul conflit")
check("article_id 无 url 时基于 source+time+title 且幂等", aid3 == aid4)
check("不同标题产生不同 article_id", aid3 != article_id(
    source_id="chad-tchadinfos", published_at="2026-07-28T16:40:18Z", title="Other"))
# Reuters 转载去重：同 canonical_url 必然同 ID
re1 = article_id(canonical_url="https://reuters.com/a/123?cmpid=app")
re2 = article_id(canonical_url="https://reuters.com/a/123")
check("同一 Reuters 文章（不同追踪参数）不产生多个 ID", re1 == re2)

eid1 = event_id("TD", "Mandoul", "armed_conflict", "2026-07-28", "customs clash")
eid2 = event_id("TD", "Mandoul", "armed_conflict", "2026-07-28", "customs clash")
eid3 = event_id("TD", "Mandoul", "armed_conflict", "2026-07-29", "customs clash")
check("event_id 基于指纹稳定（幂等）", eid1 == eid2)
check("event_id 不同日期产生不同 ID", eid1 != eid3)
check("event_id 格式 EVT_<16hex>", is_event_id(eid1), eid1)

ch1 = content_hash("Title", "Summary", u1)
ch2 = content_hash("Title", "Summary", u1)
check("content_hash 稳定", ch1 == ch2 and len(ch1) == 16)
check("content_hash 不同内容不同值",
      ch1 != content_hash("Other", "Summary", u1))

# ─────────────────────────────────────────────────────
section("normalizers：映射与来源/核实分离")
check("乍得→TD", normalize_country_code("乍得") == "TD")
check("尼日尔→NE", normalize_country_code("尼日尔") == "NE")
check("苏丹→SD", normalize_country_code("苏丹") == "SD")
check("ISO 原样返回", normalize_country_code("TD") == "TD")
check("语言 法文→fr", normalize_language("法文") == "fr")
check("语言 中文→zh", normalize_language("中文") == "zh")
check("severity 高→high", normalize_event_severity("高") == "high")
check("severity 中→medium", normalize_event_severity("中") == "medium")

# Reuters 单一来源不得为 direct_official_source
reuters_lvl = derive_verification_level(
    {"verification_status": "verified", "confidence": "已核实"},
    source_type="international_media", source_group="reuters",
    is_direct_origin=True, independent_source_count=1)
check("Reuters 单一来源 ≠ direct_official_source",
      reuters_lvl != "direct_official_source", reuters_lvl)
check("Reuters 单一来源 = 高可靠单一来源",
      reuters_lvl == "high_reliability_single_source", reuters_lvl)

# ReliefWeb 上的 NGO 报告不得为联合国官方通报
relief_ngo = derive_verification_level(
    {"verification_status": "partial"},
    source_type="aggregation_platform", source_group="reliefweb",
    is_direct_origin=False, independent_source_count=1,
    claim_origin_type="ngo_report")
check("ReliefWeb NGO 报告 ≠ direct_official_source",
      relief_ngo != "direct_official_source", relief_ngo)
check("ReliefWeb NGO 报告 = 信息有限/单一来源",
      relief_ngo in ("insufficient_information", "single_source"), relief_ngo)

# 真正直接机构声明
un = derive_verification_level(
    {"verification_status": "verified"},
    source_type="international_organization", source_group="un",
    is_direct_origin=True, independent_source_count=1,
    claim_origin_type="direct_international_organization_report")
check("直接机构声明 = direct_official_source",
      un == "direct_official_source", un)

# 多源交叉核实
cv = derive_verification_level(
    {"verification_status": "verified"}, source_group="xinhua",
    independent_source_count=2)
check("独立来源≥2 = cross_verified", cv == "cross_verified", cv)

check("needs_translation 空中文为真",
      derive_needs_translation({"title_cn": ""}) is True)
check("needs_translation 有中文为假",
      derive_needs_translation({"title_cn": "标题", "summary_cn": "摘要"}) is False)

# ─────────────────────────────────────────────────────
section("publication_policy：确定性规则")
d = evaluate("cross_verified")
check("cross_verified → publishable + gate",
      d["publication_status"] == "publishable" and d["quality_gate_passed"] is True)
d = evaluate("direct_official_source")
check("direct_official_source → publishable + gate",
      d["publication_status"] == "publishable" and d["quality_gate_passed"] is True)
check("direct_official_source 理由标注直接机构单一来源",
      "直接机构" in d["publication_reason"], d["publication_reason"])
d = evaluate("high_reliability_single_source")
check("high_reliability_single_source → verification_pending（不自动公开）",
      d["publication_status"] == "verification_pending")
d = evaluate("single_source")
check("single_source → verification_pending", d["publication_status"] == "verification_pending")
d = evaluate("insufficient_information")
check("insufficient_information → verification_pending",
      d["publication_status"] == "verification_pending")
d = evaluate("conflicting_reports")
check("conflicting_reports → verification_pending",
      d["publication_status"] == "verification_pending")
d = evaluate("not_checked")
check("not_checked → verification_pending", d["publication_status"] == "verification_pending")
d = evaluate("single_source", force_quarantine=True, quarantine_reason="国家错误")
check("force_quarantine → quarantined", d["publication_status"] == "quarantined")
check("verification_label_cn 映射齐全（7 项）",
      len(VERIFICATION_LABEL_CN) == 7 and VERIFICATION_LABEL_CN["cross_verified"] == "多源交叉核实")

# ─────────────────────────────────────────────────────
section("schema_validator：5 份 schema 加载与校验")
schemas = {
    "article": load_schema("article.schema.json"),
    "event_cluster": load_schema("event_cluster.schema.json"),
    "published_event": load_schema("published_event.schema.json"),
    "quarantine_record": load_schema("quarantine_record.schema.json"),
    "source": load_schema("source.schema.json"),
}
check("5 份 schema 均可加载为 dict", all(isinstance(v, dict) for v in schemas.values()))

valid_article = {
    "article_id": "ART_" + "a" * 16,
    "schema_version": "2.0", "pipeline_version": 2,
    "run_id": "20260729T231355+0800_j04bl1",
    "source_id": "reuters", "article_url": "https://reuters.com/a/1",
    "processing_status": "raw", "verification_queue_status": "not_required",
}
check("合法 Article 通过校验", validate_instance(valid_article, schemas["article"]) == [])
bad_article = dict(valid_article)
bad_article["article_id"] = "BADID"
bad_article["processing_status"] = "weird"
bad_article.pop("source_id")
errs = validate_instance(bad_article, schemas["article"])
check("非法 Article 被校验拒绝（id格式/枚举/必填）",
      any("pattern" in e or "枚举" in e or "缺少必填" in e for e in errs), str(errs))

valid_event = {
    "event_id": "EVT_" + "b" * 16, "schema_version": "2.0",
    "pipeline_version": 2, "run_id": "20260729T231355+0800_j04bl1",
    "country_code": "TD", "event_type": "armed_conflict",
    "event_severity": "high", "event_status": "ongoing",
    "verification_level": "cross_verified", "publication_status": "publishable",
}
check("合法 Event Cluster 通过校验", validate_instance(valid_event, schemas["event_cluster"]) == [])
bad_event = dict(valid_event)
bad_event["country_risk_level"] = 9
bad_event["event_severity"] = "huge"
errs = validate_instance(bad_event, schemas["event_cluster"])
check("非法 Event（risk越界/severity枚举）被拒绝",
      any("maximum" in e or "枚举" in e for e in errs), str(errs))

valid_pub = {
    "event_id": "EVT_" + "c" * 16, "country": "TD", "country_cn": "乍得",
    "country_risk_level": 4, "event_type": "armed_conflict",
    "event_severity": "high", "event_status": "ongoing", "title_cn": "标题",
    "verification_level": "cross_verified", "verification_label_cn": "多源交叉核实",
    "pipeline_version": 2, "schema_version": "2.0",
    "run_id": "20260729T231355+0800_j04bl1",
}
check("合法 Published Event 通过校验",
      validate_instance(valid_pub, schemas["published_event"]) == [])
# published 不得包含内部字段
leaky = dict(valid_pub)
leaky["internal_error_stack"] = "traceback..."
leaky["secret_key"] = "x"
check("Published Event 禁止额外内部字段（additionalProperties=false）",
      validate_instance(leaky, schemas["published_event"]) != [])

valid_q = {
    "quarantine_id": "Q_" + "d" * 16, "original_object_type": "event",
    "original_id": "EVT_" + "e" * 16, "reason_code": "wrong_country",
    "reason_cn": "国家错误", "detected_at": "2026-07-29T23:00:00+08:00",
    "detected_by": "pipeline", "restorable": True,
}
check("合法 Quarantine 通过校验", validate_instance(valid_q, schemas["quarantine_record"]) == [])

valid_src = {
    "source_id": "reuters", "source_group": "reuters", "source_name": "Reuters",
    "source_type": "international_media", "source_reliability_tier": "tier_1",
    "enabled": True, "tested": True,
}
check("合法 Source 通过校验", validate_instance(valid_src, schemas["source"]) == [])
bad_src = dict(valid_src)
bad_src["source_type"] = "government"
bad_src["source_reliability_tier"] = "tier_0"
errs = validate_instance(bad_src, schemas["source"])
check("Reuters 标为 government / tier_0 被拒绝",
      any("枚举" in e or "government" in e for e in errs), str(errs))

# ─────────────────────────────────────────────────────
section("repository：原子写入 / 备份 / 去重 / 计数")
tmp = tempfile.mkdtemp(prefix="asip_repo_test_")
try:
    repo = Repository(root=tmp, run_id="20260729T000000+0800_test01", make_backups=True)
    a1 = dict(valid_article)
    a2 = dict(valid_article); a2["article_id"] = "ART_" + "f" * 16
    log1 = repo.save_articles([a1, a2])
    check("首次保存：added=2", log1["added"] == 2, str(log1))
    apath = repo._canonical("articles.json")
    check("原子写入生成文件", apath.exists())
    # 备份存在
    bak = list((apath.parent / ".backups").glob("articles.json.*.bak")) if (apath.parent / ".backups").exists() else []
    # 首次保存前文件不存在，可能无备份；再次保存应有备份
    log2 = repo.save_articles([a1, a2])
    check("相同内容二次保存：skipped=2、added=0",
          log2["skipped"] == 2 and log2["added"] == 0, str(log2))
    check("加载往返一致（数量=2）", len(repo.load_articles()) == 2)
    # 修改一条
    a1m = dict(a1); a1m["summary_original"] = "changed"
    log3 = repo.save_articles([a1m, a2])
    check("修改一条：modified=1", log3["modified"] == 1, str(log3))
    # 非法条目计入 failed
    bad = {"article_id": "", "processing_status": "raw"}
    log4 = repo.save_articles([a1m, a2, bad])
    check("非法条目计入 failed", log4["failed"] >= 1, str(log4))
    check("非法条目不被写入（数量仍为2）", len(repo.load_articles()) == 2)
    # 备份目录已生成且为复制（非删除）
    bakdir = apath.parent / ".backups"
    check("备份目录存在（自动备份生效）", bakdir.exists())
    # export_legacy_views 在 2B 之前应抛出明确错误
    raised = False
    try:
        repo.export_legacy_views()
    except RuntimeError as e:
        raised = True
    check("export_legacy_views 在兼容导出构建前抛出明确错误", raised)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ─────────────────────────────────────────────────────
print(f"\n{'='*52}")
print(f"Stage 2A 测试结果：PASS={PASS}  FAIL={FAIL}")
print(f"{'='*52}")
sys.exit(1 if FAIL > 0 else 0)
