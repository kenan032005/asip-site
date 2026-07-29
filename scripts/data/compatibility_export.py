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
    ev["event_id"] = cluster.get("legacy_event_id") or ev.get("event_id")
    return ev


def _legacy_pending_from_article(a: dict) -> dict:
    """忠实复现原始 pending 记录。"""
    return dict(a.get("legacy_payload", {}))


def _legacy_quarantine_from_record(q: dict) -> dict:
    """忠实复现原始 quarantine 记录。"""
    return dict(q.get("legacy_payload", {}))


def _published_from_cluster(cluster: dict, articles_by_id: dict) -> dict:
    source_links = []
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
    published = [ _published_from_cluster(c, articles_by_id) for c in clusters if _is_published(c) ]
    repo.save_published_events(published, run_id)

    # public current_metrics.json
    metrics = {
        "articles": len(articles),
        "event_clusters": len(clusters),
        "published_events": len(published),
        "quarantine": len(quarantine),
        "publishable_clusters": sum(1 for c in clusters if c.get("publication_status") in ("publishable", "published")),
    }
    repo.save_current_metrics(metrics, run_id)

    return {
        "legacy_events": len(legacy_events),
        "legacy_pending": len(pending),
        "legacy_raw": len(raw),
        "legacy_quarantine": len(quar),
        "published_events": len(published),
    }
