#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_publication_semantics.py —— Stage-2 发布语义与风险等级统一（幂等）。

第七节：历史迁移事件的发布语义
  - 真正达到当前政策的事件（verification_level ∈ PUBLISHABLE_LEVELS）：
      current_policy_passed=true, quality_gate_passed=true
  - 历史迁移保留事件（legacy_event_id 存在且未达当前政策）：
      legacy_migration_preserved=true, legacy_visibility=true,
      legacy_migration_passed=true, current_policy_passed=false,
      quality_gate_passed=false,
      publication_reason="历史迁移保留，未按当前政策重新核实"
      publication_status 保持 published（不删除、保留可见）；
      不计入 24h/7d/首页统计；不得标注为通过质量闸门（legacy_payload 同步）。

第八节：22 国风险等级统一
  - 以 data/countries.json 为准：level=4→极高, 3→高, 2→中, 1→低；
  - cluster 顶层与 legacy_payload 同步修正，记录修正条数。

用法：
  python scripts/data/apply_publication_semantics.py [--run-id ID]
"""
import os
import sys
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
ROOT = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)

from pipeline_core import generate_run_id, normalize_event_type, load_json  # noqa: E402
from data.repository import Repository  # noqa: E402
from data.publication_policy import PUBLISHABLE_LEVELS, apply_to_cluster  # noqa: E402
from data.compatibility_export import export_all  # noqa: E402

RISK_LABEL = {4: "极高", 3: "高", 2: "中", 1: "低"}
HIST_REASON = "历史迁移保留，未按当前政策重新核实"


def load_country_risk_map():
    doc = load_json(os.path.join(ROOT, "data", "countries.json"), {"countries": []})
    return {c.get("cn", ""): int(c.get("risk_level") or 0)
            for c in doc.get("countries", []) if c.get("cn")}


def unify_risk(cluster: dict, cmap: dict) -> bool:
    """按国家配置统一风险等级与标签（含 legacy_payload），返回是否修正。"""
    cc = cluster.get("country_cn", "")
    lvl = cmap.get(cc)
    if not lvl:
        return False
    label = RISK_LABEL.get(lvl, "")
    changed = False
    if cluster.get("country_risk_level") != lvl or cluster.get("country_risk_label") != label:
        cluster["country_risk_level"] = lvl
        cluster["country_risk_label"] = label
        changed = True
    lp = cluster.get("legacy_payload")
    if isinstance(lp, dict):
        if lp.get("country_risk_level") != lvl or lp.get("country_risk_label") != label:
            lp["country_risk_level"] = lvl
            lp["country_risk_label"] = label
            changed = True
    return changed


def apply_semantics(cluster: dict) -> bool:
    """应用第七节发布语义（幂等），返回是否修改。"""
    before = json.dumps(cluster, sort_keys=True, ensure_ascii=False)
    vl = cluster.get("verification_level", "not_checked")
    is_legacy = bool(cluster.get("legacy_event_id"))
    meets_current = vl in PUBLISHABLE_LEVELS
    # Stage 3B Final Repair: 真实采集事件（经 quality gate 验收）保持发布状态
    # 识别标志：migration_source=public_only_stage3b_repair 或 publication_reason 含"真实采集"
    real_collected = (
        cluster.get("migration_source") == "public_only_stage3b_repair"
        or cluster.get("publication_reason") in
        ("Stage 3A 真实采集", "Stage 3B 真实采集")
    )

    if real_collected:
        # 真实采集事件（Stage 3A/3B，经 quality gate 验收）保持发布状态
        cluster["current_policy_passed"] = True
        cluster["quality_gate_passed"] = True
        cluster["legacy_migration_preserved"] = False
        cluster["legacy_visibility"] = True
        cluster["publication_status"] = "publishable"
        cluster["publication_reason"] = cluster.get("publication_reason") or "Stage 3B 真实采集"
    elif meets_current:
        # 真正达到当前政策：按统一政策评估（publication_policy 唯一入口）
        apply_to_cluster(cluster)
        cluster["current_policy_passed"] = True
        cluster["legacy_migration_preserved"] = False
        cluster["legacy_visibility"] = True
    elif is_legacy:
        # 历史迁移保留：不删除、保留可见，但不得标注通过当前政策/质量闸门
        cluster["legacy_migration_preserved"] = True
        cluster["legacy_visibility"] = True
        cluster["legacy_migration_passed"] = True
        cluster["current_policy_passed"] = False
        cluster["quality_gate_passed"] = False
        cluster["publication_reason"] = HIST_REASON
        # publication_status 保持原值（published），确保历史事件不被删除
    else:
        # 非迁移新事件：统一政策决定
        apply_to_cluster(cluster)
        cluster["current_policy_passed"] = bool(cluster.get("quality_gate_passed"))
        cluster["legacy_migration_preserved"] = False
        cluster["legacy_visibility"] = True

    # legacy_payload 同步（前端展示视图也不得标注历史事件通过闸门）
    lp = cluster.get("legacy_payload")
    if isinstance(lp, dict):
        lp["quality_gate_passed"] = bool(cluster.get("quality_gate_passed"))
        lp["current_policy_passed"] = bool(cluster.get("current_policy_passed"))
        lp["legacy_migration_preserved"] = bool(cluster.get("legacy_migration_preserved"))
        lp["legacy_visibility"] = bool(cluster.get("legacy_visibility", True))

    # 事件类型标准化（英文枚举代码）
    et = cluster.get("event_type", "")
    net = normalize_event_type(et)
    if net and net != et:
        cluster["event_type"] = net
    if isinstance(lp, dict):
        let = lp.get("event_type", "")
        nlet = normalize_event_type(let)
        if nlet and nlet != let:
            lp["event_type"] = nlet

    return json.dumps(cluster, sort_keys=True, ensure_ascii=False) != before


def main(run_id=None):
    run_id = run_id or generate_run_id()
    repo = Repository(root=ROOT, run_id=run_id)
    clusters = repo.load_event_clusters()
    if not clusters:
        print("[semantics] canonical event_clusters 为空，跳过。")
        return 0

    cmap = load_country_risk_map()
    risk_fixed = 0
    sem_changed = 0
    for c in clusters:
        if unify_risk(c, cmap):
            risk_fixed += 1
        if apply_semantics(c):
            sem_changed += 1

    n_hist = sum(1 for c in clusters if c.get("legacy_migration_preserved"))
    n_cur = sum(1 for c in clusters if c.get("current_policy_passed"))
    print(f"[semantics] clusters={len(clusters)} 历史保留={n_hist} 当前政策通过={n_cur}")
    print(f"[semantics] 风险等级修正={risk_fixed} 语义字段变更={sem_changed}")

    repo.save_event_clusters(clusters, run_id)
    stats = export_all(repo, run_id)
    print(f"[semantics] 导出：legacy_events={stats['legacy_events']} "
          f"published={stats['published_events']}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Stage-2 发布语义与风险统一")
    ap.add_argument("--run-id", type=str, default=None)
    args = ap.parse_args()
    sys.exit(main(run_id=args.run_id))
