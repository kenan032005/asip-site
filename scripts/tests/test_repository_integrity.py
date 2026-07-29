#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_repository_integrity.py —— ASIP 第二阶段收尾 Commit 1 测试

覆盖：
- 第三节：Repository 保存前强制调用 Schema；非法 schema_version / 缺失必填 /
  非法枚举 / 非法 URL 均阻断；100 条中 1 条非法 → 整个保存失败且原文件字节不变。
- 第四节：link_article_to_event 事务式双向关联；Event 不写 linked_event_id；
  磁盘回读一致；第二次关联不改变文件内容；任一侧不存在则两文件均不变。
- 第五节：validate_source_business_rules（Reuters / Xinhua / ReliefWeb）且
  save_sources 拒绝违反业务规则的来源；仅测试业务约束时不被其他非法字段假通过。

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

from data.repository import Repository, RepositorySchemaError
from data.source_rules import validate_source_business_rules
from pipeline_core import generate_run_id

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


RID = generate_run_id()


def valid_article(i):
    return {
        "article_id": "ART_" + f"{i:016x}",
        "schema_version": "2.0", "pipeline_version": 2, "run_id": RID,
        "source_id": "reuters", "article_url": "https://reuters.com/a/%d" % i,
        "processing_status": "raw", "verification_queue_status": "not_required",
    }


def valid_event(eid="EVT_" + "b" * 16):
    return {
        "event_id": eid, "schema_version": "2.0", "pipeline_version": 2, "run_id": RID,
        "country_code": "TD", "country_cn": "乍得", "country_risk_level": 4,
        "country_risk_label": "极高", "event_type": "armed_conflict",
        "event_severity": "high", "event_status": "ongoing",
        "verification_level": "cross_verified", "publication_status": "publishable",
        "quality_gate_passed": True, "article_ids": [],
    }


# ─────────────────────────────────────────────────────
section("第三节：Repository 保存前强制 Schema 校验（整体失败）")
tmp = tempfile.mkdtemp(prefix="asip_repo_int_")
try:
    repo = Repository(root=tmp, run_id=RID)
    apath = repo._canonical("articles.json")

    # 非法 schema_version
    a = valid_article(1); a["schema_version"] = "1.0"
    raised = False
    try:
        repo.save_articles([a])
    except RepositorySchemaError:
        raised = True
    check("非法 schema_version 阻断整个保存", raised)

    # 缺失必填字段（source_id）
    a = valid_article(2); a.pop("source_id")
    raised = False
    try:
        repo.save_articles([a])
    except RepositorySchemaError:
        raised = True
    check("缺失必填字段（source_id）阻断整个保存", raised)

    # 非法枚举（processing_status）
    a = valid_article(3); a["processing_status"] = "weird"
    raised = False
    try:
        repo.save_articles([a])
    except RepositorySchemaError:
        raised = True
    check("非法 publication_status 枚举阻断整个保存", raised)

    # 非法 URL
    a = valid_article(4); a["article_url"] = "not-a-url"
    raised = False
    try:
        repo.save_articles([a])
    except RepositorySchemaError:
        raised = True
    check("非法 URL（article_url）阻断整个保存", raised)

    # 100 条中 1 条非法 → 整个保存失败 + 原文件字节不变
    arts = [valid_article(i) for i in range(100)]
    arts[50]["processing_status"] = "bogus_enum"
    # 先写一个基线（99 合法）以验证“原文件不变”
    base = [valid_article(i) for i in range(99)]
    repo.save_articles(base)
    before = apath.read_bytes()
    raised = False
    try:
        repo.save_articles(arts)
    except RepositorySchemaError:
        raised = True
    check("100 条中 1 条非法 → 整个保存失败", raised)
    check("保存失败后原文件哈希不变（数量仍为99）",
          apath.read_bytes() == before and len(repo.load_articles()) == 99)

    # 全合法 → 成功
    ok = repo.save_articles([valid_article(1000), valid_article(1001)])
    check("全合法记录保存成功（added=2）", ok["added"] == 2, str(ok))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ─────────────────────────────────────────────────────
section("第四节：link_article_to_event 事务式双向关联")
tmp = tempfile.mkdtemp(prefix="asip_link_")
try:
    repo = Repository(root=tmp, run_id=RID)
    a = valid_article(7)
    e = valid_event()
    repo.save_articles([a])
    repo.save_event_clusters([e])
    aid = a["article_id"]; eid = e["event_id"]

    ok = repo.link_article_to_event(eid, aid)
    check("link 返回 True（已写入）", ok)

    # 重新加载（模拟重启 Repository）
    repo2 = Repository(root=tmp, run_id=RID)
    ra = repo2.get_article(aid)
    re = repo2.get_event(eid)
    check("磁盘回读：Article 仍指向 Event", ra.get("linked_event_id") == eid)
    check("磁盘回读：Article processing_status=linked_to_event",
          ra.get("processing_status") == "linked_to_event")
    check("磁盘回读：Event 仍包含 Article", aid in (re.get("article_ids") or []))
    check("Event 不得写入 linked_event_id", "linked_event_id" not in re)

    # 第二次关联不改变文件内容
    apath = repo2._canonical("articles.json")
    epath = repo2._canonical("event_clusters.json")
    a_before = apath.read_bytes(); e_before = epath.read_bytes()
    ok2 = repo2.link_article_to_event(eid, aid)
    check("第二次关联返回 False（幂等，不写文件）", ok2 is False)
    check("第二次关联后 Article 文件字节不变", apath.read_bytes() == a_before)
    check("第二次关联后 Event 文件字节不变", epath.read_bytes() == e_before)

    # 任一侧不存在 → 两文件均不变
    a_before = apath.read_bytes(); e_before = epath.read_bytes()
    no_art = repo2.link_article_to_event(eid, "ART_" + "0" * 16)
    no_evt = repo2.link_article_to_event("EVT_" + "0" * 16, aid)
    check("Article 不存在 → 返回 False 且两文件不变",
          no_art is False and apath.read_bytes() == a_before and epath.read_bytes() == e_before)
    check("Event 不存在 → 返回 False 且两文件不变",
          no_evt is False and apath.read_bytes() == a_before and epath.read_bytes() == e_before)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ─────────────────────────────────────────────────────
section("第五节：来源业务约束（validate_source_business_rules）")
reuters_ok = {
    "source_id": "intl_reuters", "source_group": "reuters", "source_name": "Reuters",
    "source_type": "international_media", "source_reliability_tier": "tier_1",
    "is_direct_origin": True, "is_republication_platform": False,
    "claim_origin_type": "unknown", "enabled": True, "tested": True,
}
check("Reuters 合规通过", validate_source_business_rules(reuters_ok) == [])

reuters_bad = dict(reuters_ok); reuters_bad["source_type"] = "government"
check("Reuters 标为 government 被拒", validate_source_business_rules(reuters_bad) != [])

reuters_bad2 = dict(reuters_ok); reuters_bad2["claim_origin_type"] = "direct_government_statement"
check("Reuters 标为官方直接声明被拒", validate_source_business_rules(reuters_bad2) != [])

xinhua_ok = {
    "source_id": "intl_xinhua", "source_group": "xinhua", "source_name": "新华社",
    "source_type": "state_media", "source_reliability_tier": "tier_1",
    "is_direct_origin": False, "is_republication_platform": False,
    "claim_origin_type": "media_reporting", "enabled": True, "tested": True,
}
check("Xinhua 合规通过（claim=media_reporting）", validate_source_business_rules(xinhua_ok) == [])

xinhua_bad = dict(xinhua_ok); xinhua_bad["claim_origin_type"] = "direct_government_statement"
check("Xinhua 不得因国家通讯社身份自动视为政府直接声明",
      validate_source_business_rules(xinhua_bad) != [])
xinhua_unknown = dict(xinhua_ok); xinhua_unknown["claim_origin_type"] = "unknown"
check("Xinhua claim=unknown 视为尚未补全但不阻断",
      validate_source_business_rules(xinhua_unknown) == [])

relief_ok = {
    "source_id": "un_reliefweb", "source_group": "reliefweb", "source_name": "ReliefWeb",
    "source_type": "aggregation_platform", "source_reliability_tier": "tier_2",
    "is_direct_origin": False, "is_republication_platform": True,
    "claim_origin_type": "unknown", "enabled": True, "tested": True,
}
check("ReliefWeb 合规通过", validate_source_business_rules(relief_ok) == [])

relief_bad = dict(relief_ok); relief_bad["is_direct_origin"] = True
check("ReliefWeb 不得 is_direct_origin", validate_source_business_rules(relief_bad) != [])
relief_bad2 = dict(relief_ok); relief_bad2["claim_origin_type"] = "media_reporting"
check("ReliefWeb 平台 claim 必须为 unknown（依据原始机构）",
      validate_source_business_rules(relief_bad2) != [])

# save_sources 拒绝违反业务规则的来源（整体失败）
tmp = tempfile.mkdtemp(prefix="asip_srcrule_")
try:
    repo = Repository(root=tmp, run_id=RID)
    bad_src = dict(reuters_ok); bad_src["source_type"] = "government"
    raised = False
    try:
        repo.save_sources([bad_src])
    except RepositorySchemaError:
        raised = True
    check("save_sources 拒绝违反业务规则的来源", raised)
    # 合规来源可正常保存
    ok_save = repo.save_sources([reuters_ok, xinhua_ok, relief_ok])
    check("合规来源保存成功", ok_save["skipped"] == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ─────────────────────────────────────────────────────
print(f"\n{'='*52}")
print(f"Commit 1 完整性测试：PASS={PASS}  FAIL={FAIL}")
print(f"{'='*52}")
sys.exit(1 if FAIL > 0 else 0)
