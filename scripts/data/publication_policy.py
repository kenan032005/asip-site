#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publication_policy.py —— ASIP Stage-2 统一发布政策

唯一发布决策入口（规范第十三节）。所有脚本不得复制发布规则。

当前第二阶段暂用确定性规则：
- cross_verified            → publishable, gate=True
- direct_official_source    → publishable, gate=True（必须显示“直接机构单一来源”）
- high_reliability_single_source → verification_pending（本阶段不自动公开）
- single_source             → verification_pending
- conflicting_reports       → verification_pending
- insufficient_information  → verification_pending
- not_checked               → verification_pending
- 明显无关/国家错误/链接缺失 → quarantined（由调用方按 reason 触发）
"""

# verification_level → 中文标签
VERIFICATION_LABEL_CN = {
    "cross_verified": "多源交叉核实",
    "direct_official_source": "直接机构通报",
    "high_reliability_single_source": "高可靠单一来源",
    "single_source": "单一来源",
    "conflicting_reports": "不同来源说法不一",
    "insufficient_information": "信息有限",
    "not_checked": "尚未核实",
}

# verification_level → 确定性分数
VERIFICATION_SCORE = {
    "cross_verified": 100,
    "direct_official_source": 90,
    "high_reliability_single_source": 70,
    "single_source": 50,
    "conflicting_reports": 40,
    "insufficient_information": 20,
    "not_checked": 0,
}


def evaluate(verification_level: str, *, event: dict = None, force_quarantine: bool = False,
             quarantine_reason: str = "") -> dict:
    """返回统一的发布决策 dict。

    返回字段：
    - publication_status
    - quality_gate_passed
    - publication_reason
    - verification_level
    - verification_score
    - verification_label_cn
    """
    vl = str(verification_level or "not_checked")
    score = VERIFICATION_SCORE.get(vl, 0)
    label = VERIFICATION_LABEL_CN.get(vl, "尚未核实")

    # 强制隔离（明显无关/国家错误/链接缺失）
    if force_quarantine:
        return {
            "publication_status": "quarantined",
            "quality_gate_passed": False,
            "publication_reason": quarantine_reason or "强制隔离：明显无关/国家错误/链接缺失",
            "verification_level": vl,
            "verification_score": score,
            "verification_label_cn": label,
        }

    if vl == "cross_verified":
        return {
            "publication_status": "publishable",
            "quality_gate_passed": True,
            "publication_reason": "多源交叉核实，达到发布门槛",
            "verification_level": vl,
            "verification_score": score,
            "verification_label_cn": label,
        }

    if vl == "direct_official_source":
        return {
            "publication_status": "publishable",
            "quality_gate_passed": True,
            "publication_reason": "直接机构单一来源，达到发布门槛",
            "verification_level": vl,
            "verification_score": score,
            "verification_label_cn": label,
        }

    if vl == "high_reliability_single_source":
        return {
            "publication_status": "verification_pending",
            "quality_gate_passed": False,
            "publication_reason": "高可靠单一来源，本阶段暂不自动公开",
            "verification_level": vl,
            "verification_score": score,
            "verification_label_cn": label,
        }

    if vl == "single_source":
        return {
            "publication_status": "verification_pending",
            "quality_gate_passed": False,
            "publication_reason": "单一来源，待自动/人工核实",
            "verification_level": vl,
            "verification_score": score,
            "verification_label_cn": label,
        }

    if vl == "conflicting_reports":
        return {
            "publication_status": "verification_pending",
            "quality_gate_passed": False,
            "publication_reason": "不同来源说法不一，待核实",
            "verification_level": vl,
            "verification_score": score,
            "verification_label_cn": label,
        }

    if vl == "insufficient_information":
        return {
            "publication_status": "verification_pending",
            "quality_gate_passed": False,
            "publication_reason": "信息有限，暂不公开",
            "verification_level": vl,
            "verification_score": score,
            "verification_label_cn": label,
        }

    # not_checked 及其它
    return {
        "publication_status": "verification_pending",
        "quality_gate_passed": False,
        "publication_reason": "尚未核实，暂不公开",
        "verification_level": vl,
        "verification_score": score,
        "verification_label_cn": label,
    }


def apply_to_cluster(cluster: dict) -> dict:
    """就地把发布政策结论写回 Event Cluster。返回 cluster。"""
    decision = evaluate(
        cluster.get("verification_level", "not_checked"),
        event=cluster,
        force_quarantine=(cluster.get("publication_status") == "quarantined"),
        quarantine_reason=cluster.get("publication_reason", ""),
    )
    cluster["publication_status"] = decision["publication_status"]
    cluster["quality_gate_passed"] = decision["quality_gate_passed"]
    cluster["publication_reason"] = decision["publication_reason"]
    cluster["verification_score"] = decision["verification_score"]
    cluster["verification_label_cn"] = decision["verification_label_cn"]
    return cluster


# 当前发布门槛：允许进入 published 的 verification_level
PUBLISHABLE_LEVELS = {"cross_verified", "direct_official_source"}


def is_publishable(cluster: dict) -> bool:
    """依据发布政策判断是否可公开（第二阶段沿用既有门槛）。"""
    if cluster.get("publication_status") in ("published", "publishable"):
        return True
    # 已正式发布且能通过迁移验证的历史事件，沿用既有 published 标记
    if cluster.get("legacy_publication_status") == "published":
        return True
    return False
