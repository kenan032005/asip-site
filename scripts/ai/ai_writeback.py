#!/usr/bin/env python3
"""ASIP Stage 2.5C-3 — Canonical Writeback

Transactional write of validated AI results to Article/EventCluster records.
Uses existing Repository as the single Canonical write path.
Never persists internal task fields into canonical records.
"""

import json
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from data.repository import Repository

# 禁止写入 Canonical 的内部字段
_INTERNAL_FIELDS = (
    "_task",
    "input_ref",
    "prompt_variables",
    "source_text",
    "source_a",
    "source_b",
    "articles",
    "events",
    "historical_events",
    "disease_reports",
    "system_text",
    "user_text",
    "prompt_file",
    "batch_manifest",
    "prompt_checksum_raw",
)


class WritebackError(Exception):
    """写回失败。"""
    def __init__(self, code, detail):
        self.code = code
        super().__init__("[%s] %s" % (code, detail))


# task_type → target_type 允许映射
_ALLOWED_MAP = {
    "article_analysis": "article",
    "event_synthesis": "event_cluster",
    "source_comparison": "event_cluster",
}


def _get_writeback_target(task):
    """从 task.input_ref.writeback 提取写回目标，或返回 None。"""
    wb = (task.get("input_ref") or {}).get("writeback")
    if not wb or not isinstance(wb, dict):
        return None
    return wb


def _validate_target(task, wb):
    """验证写回目标合法。"""
    ttype = wb.get("target_type")
    tid = wb.get("target_id")
    wb_task_type = task.get("task_type")

    if not ttype or not tid:
        raise WritebackError("invalid_writeback", "missing target_type or target_id")
    expected = _ALLOWED_MAP.get(wb_task_type)
    if not expected:
        raise WritebackError("no_writeback_policy",
                             "task_type %s has no writeback" % wb_task_type)
    if ttype != expected:
        raise WritebackError("target_type_mismatch",
                             "%s cannot write to %s" % (wb_task_type, ttype))


def _check_internal_fields(record):
    """递归检查记录中不得包含内部字段。返回违规字段列表。"""
    found = []
    if isinstance(record, dict):
        for k, v in record.items():
            if k in _INTERNAL_FIELDS:
                found.append(k)
            else:
                found.extend(_check_internal_fields(v))
    elif isinstance(record, list):
        for item in record:
            found.extend(_check_internal_fields(item))
    return found


def _make_provenance(task, provenance, cache_hit):
    """构建非敏感 AI 溯源。"""
    return {
        "task_id": task.get("task_id", ""),
        "task_type": task.get("task_type", ""),
        "content_hash": task.get("content_hash", ""),
        "prompt_version": task.get("prompt_version", ""),
        "output_schema_version": task.get("output_schema_version", ""),
        "prompt_checksum": provenance.get("prompt_checksum", ""),
        "render_hash": provenance.get("render_hash", ""),
        "prompt_variables_digest": provenance.get("prompt_variables_digest", ""),
        "provider": provenance.get("provider", ""),
        "model": provenance.get("model", ""),
        "batch_id": provenance.get("batch_id", ""),
        "cache_hit": cache_hit,
        "completed_at": provenance.get("completed_at", ""),
    }


def _write_article_analysis(repo, task, article, result, provenance, cache_hit):
    """article_analysis → Article 写回。"""
    article["summary_cn"] = result.get("summary_zh", "")
    article["event_type"] = result.get("event_type", "")
    article["relevance_score"] = result.get("security_relevance", 0.5)
    article["is_security_relevant"] = (
        result.get("security_relevance", 0) > 0.3)
    article["china_related"] = (
        result.get("china_relevance", "none") != "none")
    article["needs_translation"] = False

    article.setdefault("ai_enrichment", {})
    article["ai_enrichment"]["article_analysis"] = {
        "result": result,
        "provenance": _make_provenance(task, provenance, cache_hit),
    }
    _assert_clean(article, "article")

    articles = repo.load_articles()
    for i, a in enumerate(articles):
        if a.get("article_id") == article["article_id"]:
            articles[i] = article
            break
    repo.save_articles(articles)


def _write_event_synthesis(repo, task, event, result, provenance, cache_hit):
    """event_synthesis → EventCluster 写回。"""
    event["summary_cn"] = result.get("event_summary_zh", "")
    event["event_type"] = result.get("event_type", "")
    potential = result.get("potential_impacts", [])
    if potential:
        event["potential_impact"] = potential[0] if potential else ""

    event.setdefault("ai_enrichment", {})
    event["ai_enrichment"]["event_synthesis"] = {
        "result": result,
        "provenance": _make_provenance(task, provenance, cache_hit),
    }
    _assert_clean(event, "event_cluster")

    events = repo.load_event_clusters()
    for i, e in enumerate(events):
        if e.get("event_id") == event["event_id"]:
            events[i] = event
            break
    repo.save_event_clusters(events)


def _write_source_comparison(repo, task, event, result, provenance, cache_hit):
    """source_comparison → EventCluster 写回（不自动改变发布状态）。"""
    event.setdefault("ai_enrichment", {})
    event["ai_enrichment"]["source_comparison"] = {
        "result": result,
        "provenance": _make_provenance(task, provenance, cache_hit),
    }
    _assert_clean(event, "event_cluster")

    events = repo.load_event_clusters()
    for i, e in enumerate(events):
        if e.get("event_id") == event["event_id"]:
            events[i] = event
            break
    repo.save_event_clusters(events)


def _assert_clean(record, kind):
    """保存前断言记录不含内部字段，否则抛错（不允许半写）。"""
    found = _check_internal_fields(record)
    if found:
        raise WritebackError("canonical_internal_field_detected",
                             "%s contains internal fields: %s" % (
                                 kind, ",".join(sorted(set(found))[:5])))


_WRITERS = {
    ("article_analysis", "article"): _write_article_analysis,
    ("event_synthesis", "event_cluster"): _write_event_synthesis,
    ("source_comparison", "event_cluster"): _write_source_comparison,
}


def execute_writeback(task, result_obj, provenance, repo=None,
                      cache_hit=False):
    """执行 Canonical 写回。

    参数:
        task: 当前 AI Task
        result_obj: 已验证业务结果
        provenance: 非敏感 provenance dict
        repo: 可选 Repository（默认生产）
        cache_hit: 是否来自缓存命中

    返回 dict: {"written": True, "target_type": "...", "target_id": "..."}
    或忽略当无 writeback 目标时: {"written": False}
    """
    wb = _get_writeback_target(task)
    if not wb:
        return {"written": False}

    _validate_target(task, wb)

    if repo is None:
        repo = Repository()

    ttype = wb["target_type"]
    tid = wb["target_id"]

    if ttype == "article":
        article = repo.get_article(tid)
        if not article:
            raise WritebackError("article_not_found", tid)
        target = article
    elif ttype == "event_cluster":
        event = repo.get_event(tid)
        if not event:
            raise WritebackError("event_not_found", tid)
        target = event
    else:
        raise WritebackError("unknown_target_type", ttype)

    writer_key = (task.get("task_type"), ttype)
    writer = _WRITERS.get(writer_key)
    if not writer:
        raise WritebackError("no_writer", str(writer_key))

    writer(repo, task, target, result_obj, provenance, cache_hit)

    return {"written": True, "target_type": ttype, "target_id": tid}
