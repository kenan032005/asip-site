#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compatibility_export.py —— ASIP Stage-2 兼容导出（规范数据 → 遗留视图，单向）

规范数据为唯一来源；本模块单向生成遗留文件，确保前端与日报脚本在过渡期正常运行：
- data/events.json          （来自 canonical event_clusters，event_id 保留 legacy_event_id）
- data/pending_events.json  （来自 canonical articles，processing_status=queued_for_verification）
- data/raw_candidates.json  （来自 canonical articles，processing_status∈{raw,normalized}）
- data/quarantine_events.json（来自 canonical quarantine）
- data/public/published_events.json（来自 event_clusters 中达到发布门槛者，公开模型不含内部字段）
- data/public/current_metrics.json

遗留文件顶层新增：generated_from_canonical / do_not_edit_manually / schema_version / run_id。
"""

import json
from pathlib import Path

from pipeline_core import EVENT_TYPE_CN, normalize_event_type

SEVERITY_CN = {"low": "低", "medium": "中", "high": "高", "critical": "极高"}


def _legacy_event_from_cluster(cluster: dict) -> dict:
    """忠实复现原始遗留事件（来自 legacy_payload），仅保证 event_id 稳定。

    不向遗留对象注入规范字段，确保「规范→遗留→规范」往返幂等（二次迁移内容一致）。
    前端显示所需字段均包含在 legacy_payload 中。
    """
    ev = dict(cluster.get("legacy_payload", {}))
    ev["event_id"] = cluster.get("legacy_event_id") or ev.get("event_id") or cluster.get("event_id")
    return ev


def _legacy_pending_from_article(a: dict) -> dict:
    """忠实复现原始 pending 记录。"""
    return dict(a.get("legacy_payload", {}))


def _legacy_quarantine_from_record(q: dict) -> dict:
    """忠实复现原始 quarantine 记录。"""
    return dict(q.get("legacy_payload", {}))


def _published_from_cluster(cluster: dict, articles_by_id: dict) -> dict:
    # Stage 3B Final Repair: 支持内联 source_links（采集器直写的集群格式）
    # 优先使用 cluster 内联的 source_links，回退到 article_ids 查找
    source_links = list(cluster.get("source_links", []))
    if not source_links:
        for aid in cluster.get("article_ids", []):
            art = articles_by_id.get(aid)
            if art:
                source_links.append({
                    "url": art.get("canonical_url") or art.get("article_url", ""),
                    "source_name": art.get("source_name", ""),
                    "source_group": art.get("source_group", ""),
                    "language": art.get("language", ""),
                })
    return {
        "event_id": cluster.get("event_id"),
        "country": cluster.get("country_code", ""),
        "country_cn": cluster.get("country_cn", ""),
        "country_risk_level": cluster.get("country_risk_level", 4),
        "country_risk_label": cluster.get("country_risk_label", "极高"),
        "event_type": cluster.get("event_type", ""),
        "event_severity": cluster.get("event_severity", ""),
        "event_status": cluster.get("event_status", ""),
        "title_cn": cluster.get("title_cn", ""),
        "title_original": cluster.get("title_original", ""),
        "summary_cn": cluster.get("summary_cn", ""),
        "summary_original": cluster.get("summary_original", ""),
        "event_time": cluster.get("event_time", ""),
        "published_time": cluster.get("event_time", ""),
        "location": cluster.get("location_name", ""),
        "china_related": cluster.get("china_related", False),
        "verification_level": cluster.get("verification_level", ""),
        "verification_label_cn": cluster.get("verification_label_cn", ""),
        "independent_source_count": cluster.get("independent_source_count", 0),
        "source_links": source_links,
        "potential_impact": cluster.get("potential_impact", ""),
        "progress": cluster.get("current_progress", ""),
        # Stage-2 最终收尾：发布语义标记
        "current_policy_passed": bool(cluster.get("current_policy_passed", False)),
        "quality_gate_passed": bool(cluster.get("quality_gate_passed", False)),
        "legacy_migration_preserved": bool(cluster.get("legacy_migration_preserved", False)),
        "legacy_visibility": bool(cluster.get("legacy_visibility", True)),
        "publication_reason": cluster.get("publication_reason", ""),
        # Stage 3B Final Repair §4: 正文追溯与质量字段
        "body_extracted": cluster.get("body_extracted", ""),
        "body_status": cluster.get("body_status", ""),
        "article_word_count": cluster.get("article_word_count", 0),
        "extraction_method": cluster.get("extraction_method", ""),
        "extraction_quality_score": cluster.get("extraction_quality_score", 0),
        "extraction_quality_reasons": cluster.get("extraction_quality_reasons", []),
        "canonical_url": cluster.get("canonical_url", ""),
        "discovery_method": cluster.get("discovery_method", ""),
        "fetch_http_status": cluster.get("fetch_http_status", 0),
        "pipeline_version": 2,
        "schema_version": "2.0",
        "run_id": cluster.get("run_id", ""),
    }


def _is_published(cluster: dict) -> bool:
    if cluster.get("publication_status") in ("publishable", "published"):
        return True
    # 历史已正式发布的事件（沿用既有发布标记）
    if cluster.get("legacy_publication_status") in ("verified", "已核实"):
        return True
    return False


def export_all(repo, run_id: str = ""):
    """生成全部兼容与公开文件。返回统计 dict。"""
    articles = repo.load_articles()
    clusters = repo.load_event_clusters()
    quarantine = repo.load_quarantine()
    articles_by_id = {a["article_id"]: a for a in articles if a.get("article_id")}

    # legacy events.json
    legacy_events = [_legacy_event_from_cluster(c) for c in clusters]
    env_events = {
        "generated_from_canonical": True, "do_not_edit_manually": True,
        "schema_version": "2.0", "pipeline_version": 2, "run_id": run_id,
        "version": "2.0", "updated_at": "", "is_demo": False,
        "note": "由 canonical event_clusters 单向生成；请勿手工编辑",
        "events": legacy_events,
    }
    repo.write_if_changed(repo._data("events.json"), env_events)

    # legacy pending_events.json
    pending = [ _legacy_pending_from_article(a) for a in articles
                if a.get("processing_status") == "queued_for_verification" ]
    env_pending = {
        "generated_from_canonical": True, "do_not_edit_manually": True,
        "schema_version": "2.0", "pipeline_version": 2, "run_id": run_id,
        "updated_at": "", "items": pending,
    }
    repo.write_if_changed(repo._data("pending_events.json"), env_pending)

    # legacy raw_candidates.json
    raw = [ _legacy_pending_from_article(a) for a in articles
            if a.get("processing_status") in ("raw", "normalized") ]
    env_raw = {
        "generated_from_canonical": True, "do_not_edit_manually": True,
        "schema_version": "2.0", "pipeline_version": 2, "run_id": run_id,
        "updated_at": "", "items": raw,
    }
    repo.write_if_changed(repo._data("raw_candidates.json"), env_raw)

    # legacy quarantine_events.json
    quar = [ _legacy_quarantine_from_record(q) for q in quarantine ]
    env_quar = {
        "generated_from_canonical": True, "do_not_edit_manually": True,
        "schema_version": "2.0", "pipeline_version": 2, "run_id": run_id,
        "updated_at": "", "items": quar,
    }
    repo.write_if_changed(repo._data("quarantine_events.json"), env_quar)

    # public published_events.json
    # ① canonical 中已隔离（quarantine original_id 命中）的 cluster 不导出；
    # ② 合并保留现有 public 中 Stage 3A/3B 真实采集事件（不经 canonical 直接发布）；
    # ③ Stage 3B Final Repair §2: 已进入 quarantine 的事件不得同时存在于 public。
    real_reasons = ("Stage 3A 真实采集", "Stage 3B 真实采集")
    quar_ids = {q.get("original_id") for q in quarantine if q.get("original_id")}
    quar_event_ids = {q.get("original_id") for q in quarantine
                      if (q.get("original_id") or "").startswith("EVT_")}
    published = [_published_from_cluster(c, articles_by_id)
                 for c in clusters if _is_published(c)
                 and c.get("event_id") not in quar_ids
                 and c.get("legacy_event_id") not in quar_ids]
    try:
        existing_items = repo.load_published_events()
        # 当前 canonical 全部 event_id（含 legacy_event_id），用于过滤已移除事件
        canonical_ev_ids = {c.get("event_id") for c in clusters if c.get("event_id")}
        canonical_legacy_ids = {c.get("legacy_event_id") for c in clusters if c.get("legacy_event_id")}
        real_events = []
        for e in existing_items:
            if e.get("publication_reason") not in real_reasons:
                continue
            eid = e.get("event_id")
            if eid in quar_event_ids:
                continue  # 已隔离，不得保留在 public
            # Stage 3B Final Repair §4: 事件已从 canonical 移除（如非文章页误判）
            # 不得继续保留在 public（public 必须是 canonical 子集）
            if eid not in canonical_ev_ids and eid not in canonical_legacy_ids:
                continue
            sl = e.get("source_links") or []
            url = (sl[0].get("url", "") if sl else "").strip().rstrip("/")
            if url and url.lower() in {x.strip().rstrip("/").lower() for x in quar_ids}:
                continue  # 来源 URL 已隔离
            real_events.append(e)
        if real_events:
            # 按 event_id 去重合并（真实采集事件保留在 canonical 事件之后）
            published_ids = {p.get("event_id") for p in published}
            published = published + [e for e in real_events
                                     if e.get("event_id") not in published_ids]
    except Exception as _e:
        print(f"  ⚠ 合并真实采集事件失败（继续）: {_e}")
    repo.save_published_events(published, run_id)

    # public current_metrics.json
    # publishable_clusters/current_policy_passed_events 需与 published_events 口径一致：
    # canonical 通过政策事件 + 不在 canonical 的真实采集事件（避免双重计数）
    canon_policy_ids = {c.get("event_id") for c in clusters
                        if c.get("current_policy_passed") is True}
    # 仅统计"真实采集但不在 canonical 政策集合中"的事件（合并保留的旧 public 事件）
    n_real_extra = sum(1 for e in published
                       if e.get("publication_reason") in real_reasons
                       and e.get("event_id") not in canon_policy_ids)
    n_canon_cur = len(canon_policy_ids)
    n_total_publishable = n_canon_cur + n_real_extra
    metrics = {
        "articles": len(articles),
        "event_clusters": len(clusters),
        "published_events": len(published),
        "quarantine": len(quarantine),
        # Stage-2 收尾：publishable_clusters 只统计真正通过当前发布政策的事件
        # （current_policy_passed=true + 不在 canonical 的 Stage 3A/3B 真实采集），
        # 不得把历史迁移可见事件计入，也不得双重计数。
        "publishable_clusters": n_total_publishable,
        # Stage-2 最终收尾：供 build_summary 使用（不再读遗留事件池）
        "pending_articles": len(pending),
        "current_policy_passed_events": n_total_publishable,
        "legacy_migration_preserved_events": sum(1 for c in clusters if c.get("legacy_migration_preserved") is True),
    }
    repo.save_current_metrics(metrics, run_id)

    return {
        "legacy_events": len(legacy_events),
        "legacy_pending": len(pending),
        "legacy_raw": len(raw),
        "legacy_quarantine": len(quar),
        "published_events": len(published),
    }
