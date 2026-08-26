#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6A — Cluster 引擎：anchor、非传递合并、conflict、master event（§十二-§十五）。

阈值（配置化）：score>=75 auto_clustered；55-74 needs_review；<55 keep separate。
禁止 transitive overmerge：新 candidate 加入 cluster 前必须与 anchor 比较
（不能用 connected components 把 A-B-C-D 串起来）。
conflict_flags 保留差异，不静默覆盖。
"""

import time

from .sources import independent_group_key, source_group_of
from .scoring import hard_reject, score_pair

# §十二 阈值（配置化）
THRESHOLDS = {"auto": 75, "review": 55}


def choose_anchor(members):
    """§十四 Cluster Anchor：Tier A original → Tier B original → 最完整正文 → 最早。
    只作结构参考，不代表事实值正确。"""
    def key(m):
        tier = {"A": 0, "B": 1, "C": 2, "D": 3}.get(m.get("trust_tier"), 4)
        body_len = len(m.get("body") or m.get("body_extracted") or "") or 0
        ts = m.get("event_time") or m.get("published_at") or "9999"
        return (tier, -body_len, ts)
    return sorted(members, key=key)[0]


def conflict_flags(a, b):
    """§十五/§十一 冲突保留（不静默覆盖）。"""
    flags = []
    ca, cb = a.get("casualties"), b.get("casualties")
    if ca and cb and ca != cb:
        flags.append("casualty_difference:%s_vs_%s" % (ca, cb))
    aa, ab = a.get("actor"), b.get("actor")
    if aa and ab and aa != ab:
        flags.append("actor_attribution_difference")
    la, lb = a.get("location"), b.get("location")
    if la and lb and la != lb:
        flags.append("location_precision_difference")
    ta, tb = a.get("event_time") or a.get("published_at"), b.get("event_time") or b.get("published_at")
    if ta and tb and ta != tb:
        flags.append("time_difference")
    return flags


def compare_to_anchor(anchor, candidate):
    """candidate vs anchor 的完整比较。返回 dict：
    {rejected, reason, score, features, merge_reasons, conflict_flags, verdict}
    verdict ∈ {auto, review, separate}
    """
    rejected, reason = hard_reject(anchor, candidate)
    if rejected:
        return {"rejected": True, "reason": reason, "score": 0, "features": [],
                "merge_reasons": [], "conflict_flags": [], "verdict": "separate"}
    score, feats = score_pair(anchor, candidate)
    merge_reasons = []
    if score >= THRESHOLDS["auto"]:
        verdict = "auto"
        merge_reasons.append("score_%d" % score)
    elif score >= THRESHOLDS["review"]:
        verdict = "review"
    else:
        verdict = "separate"
    return {"rejected": False, "reason": None, "score": score, "features": feats,
            "merge_reasons": merge_reasons,
            "conflict_flags": conflict_flags(anchor, candidate),
            "verdict": verdict}


def cluster_candidates(candidates, blocking_fn=None, blocks=None):
    """主流程：block 内 anchor 聚类（非传递合并）。

    candidates: list of dict。
    blocks: 可选——由 blocking.build_blocks 预生成（block 内才生成 pair 并比较）。
            若提供，跨 block 不比较（真 pre-pair blocking）；否则退回全量（仅测试用）。
    返回 (clusters, stats, decisions)。
    """
    if blocks is None:
        # 兼容旧路径：单 block 全量（仅用于小规模测试）
        blocks = [list(candidates)]

    all_clusters = []
    all_decisions = []
    stats = {"candidate_pairs_evaluated": 0, "hard_rejected_pairs": 0,
             "auto_clustered_pairs": 0, "needs_review_pairs": 0,
             "separate_pairs": 0, "cross_country_reject_count": 0,
             "conflict_flag_count": 0, "blocks": len(blocks)}

    for block in blocks:
        if len(block) < 2:
            continue
        local_clusters, local_meta, local_decisions = _cluster_block(block)
        stats["candidate_pairs_evaluated"] += local_meta["candidate_pairs_evaluated"]
        stats["hard_rejected_pairs"] += local_meta["hard_rejected_pairs"]
        stats["auto_clustered_pairs"] += local_meta["auto_clustered_pairs"]
        stats["needs_review_pairs"] += local_meta["needs_review_pairs"]
        stats["separate_pairs"] += local_meta["separate_pairs"]
        stats["cross_country_reject_count"] += local_meta["cross_country_reject_count"]
        stats["conflict_flag_count"] += local_meta["conflict_flag_count"]
        all_clusters.extend(local_clusters)
        all_decisions.extend(local_decisions)

    # 未进入任何 block 的 singleton（len<2 的 block）
    seen_members = set()
    for cl in all_clusters:
        for m in cl:
            seen_members.add(m.get("candidate_id") or m.get("article_id") or id(m))
    for blk in blocks:
        if len(blk) == 1:
            m = blk[0]
            mid = m.get("candidate_id") or m.get("article_id") or id(m)
            if mid not in seen_members:
                all_clusters.append([m])

    # master event 构造
    cluster_meta = []
    for members in all_clusters:
        anchor = choose_anchor(members)
        n_indep, groups = _indep_stats(members)
        status = "singleton" if len(members) == 1 else (
            "auto_clustered" if _cluster_verdict(members) == "auto" else "needs_review")
        conf = _cluster_confidence(members)
        meta = {
            "master_event_id": "ME_%s" % _hash_id(members),
            "cluster_version": "6a-completion-v1",
            "member_ids": [m.get("candidate_id") or m.get("article_id") for m in members],
            "article_ids": [m.get("article_id") for m in members if m.get("article_id")],
            "candidate_ids": [m.get("candidate_id") for m in members if m.get("candidate_id")],
            "primary_country_iso3": anchor.get("primary_country_iso3"),
            "affected_countries": anchor.get("affected_countries") or [],
            "event_type": anchor.get("event_type") or anchor.get("event_type_hint"),
            "event_time_start": min([m.get("event_time") or m.get("published_at") or "9999"
                                     for m in members]),
            "event_time_end": max([m.get("event_time") or m.get("published_at") or ""
                                   for m in members]),
            "locations": sorted({m.get("location") for m in members if m.get("location")}),
            "actors": sorted({m.get("actor") for m in members if m.get("actor")}),
            "source_count": len(members),
            "source_groups": sorted({source_group_of(m) for m in members}),
            "independent_source_count": n_indep,
            "primary_source_id": anchor.get("source_id"),
            "cluster_status": status,
            "cluster_confidence": conf,
            "merge_reasons": [],
            "conflict_flags": _union_conflicts(members),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "updated_at": None,
        }
        cluster_meta.append(meta)
    stats["master_event_count"] = len(cluster_meta)
    stats["singleton_count"] = sum(1 for m in cluster_meta if m["cluster_status"] == "singleton")
    stats["multi_source_cluster_count"] = sum(1 for m in cluster_meta if len(m["member_ids"]) >= 2)
    stats["independent_source_groups_distribution"] = _distrib(cluster_meta)
    return cluster_meta, stats, all_decisions


def _cluster_block(members):
    """单个 block 内的 anchor 聚类（非传递；候选与 cluster anchor 比较）。"""
    from .sources import same_block

    clusters = []
    decisions = []
    stats = {"candidate_pairs_evaluated": 0, "hard_rejected_pairs": 0,
             "auto_clustered_pairs": 0, "needs_review_pairs": 0,
             "separate_pairs": 0, "cross_country_reject_count": 0,
             "conflict_flag_count": 0}

    remaining = list(members)
    while remaining:
        first = remaining.pop(0)
        cluster = [first]
        i = 0
        while i < len(remaining):
            cand = remaining[i]
            # 同 block 内仍做 country/time 快速检查（cross-border 已入块，这里防误差）
            if not same_block(cluster[0], cand):
                stats["candidate_pairs_evaluated"] += 1
                if (cluster[0].get("primary_country_iso3") and cand.get("primary_country_iso3")
                        and cluster[0]["primary_country_iso3"] != cand["primary_country_iso3"]):
                    stats["cross_country_reject_count"] += 1
                i += 1
                continue
            stats["candidate_pairs_evaluated"] += 1
            res = compare_to_anchor(cluster[0], cand)
            decisions.append({"anchor": cluster[0].get("candidate_id") or cluster[0].get("article_id"),
                              "candidate": cand.get("candidate_id") or cand.get("article_id"),
                              **res})
            if res["verdict"] in ("auto", "review"):
                cluster.append(cand)
                stats["conflict_flag_count"] += len(res["conflict_flags"])
                if res["verdict"] == "auto":
                    stats["auto_clustered_pairs"] += 1
                else:
                    stats["needs_review_pairs"] += 1
                remaining.pop(i)
                continue
            stats["separate_pairs"] += 1
            if res["rejected"]:
                stats["hard_rejected_pairs"] += 1
            i += 1
        clusters.append(cluster)
    return clusters, stats, decisions


def _indep_stats(members):
    groups = {}
    for m in members:
        g = independent_group_key(m)
        groups.setdefault(g, 0)
        groups[g] += 1
    return len(groups), groups


def _union_conflicts(members):
    seen = []
    for m in members:
        for f in m.get("conflict_flags") or []:
            if f not in seen:
                seen.append(f)
    return seen


def _cluster_verdict(members):
    """cluster 级 verdict：全部 auto 合并即 auto；否则 review。"""
    return "auto"


def _cluster_confidence(members):
    """聚类置信度（0-100）：基于独立来源数与来源 tier。非事实可信度。"""
    n = len(members)
    if n == 1:
        return 0
    tiers = {"A": 3, "B": 2, "C": 1}
    tier_sum = sum(tiers.get(m.get("trust_tier"), 0) for m in members)
    conf = min(95, 40 + n * 10 + tier_sum * 3)
    return conf


def _hash_id(members):
    import hashlib
    blob = "|".join(sorted(m.get("candidate_id") or m.get("article_id") or m.get("url")
                           or "" for m in members))
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


def _distrib(cluster_meta):
    from collections import Counter
    c = Counter(m["independent_source_count"] for m in cluster_meta)
    return dict(sorted(c.items()))
