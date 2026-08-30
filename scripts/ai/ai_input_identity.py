#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Input Identity Contract（Stage8D P0-2 幂等修复）。

背景：Observation V2 实测 REPROCESSED_UNCHANGED_COUNT = 13 —— 同一 content 在
不同 cycle 被重复送进 deepseek 并重复计费。根因是生产 enrichment 路径
（scripts/ai/safety/manual_trial.enrich_and_safe）从未接入现有的
scripts/ai/ai_result_cache，且缺少"稳定输入身份"的定义。

本模块定义：
  ai_input_hash(...) —— 稳定身份哈希，只覆盖语义相关输入：
      · normalized fact payload（剔除易变字段）
      · task_type / analysis schema version（output_schema_version）
      · prompt_version（analysis contract）
      · model
      · 确定性上下文（country / 相关 deterministic context）
  明确排除（否则每轮都产生新 hash，幂等必然失效）：
      run_id / generated_at / retrieved_at / cutoff / build timestamp /
      enriched_at / processed_at / created_at / updated_at / ts / timestamp

契约版本变更（AI_IDENTITY_VERSION）会使所有历史缓存失效，属预期行为。
"""
from __future__ import annotations

import hashlib
import json

# 身份契约版本：变更即全量失效（用于"schema/contract 变了必须重算"场景）
AI_IDENTITY_VERSION = "ai-identity-v1"

#: 每轮变化但不改变语义的字段 —— 必须排除在身份哈希之外
VOLATILE_FIELDS = frozenset({
    "run_id", "generated_at", "retrieved_at", "fetched_at", "created_at",
    "updated_at", "processed_at", "enriched_at", "cutoff", "build_timestamp",
    "build_time", "ts", "timestamp", "last_seen_at", "imported_at",
    "snapshot_at", "collected_at", "published_at",
})

#: 允许进入身份哈希的确定性上下文字段（白名单，避免引入隐式易变字段）
CONTEXT_FIELDS = frozenset({
    "country_code", "country_iso3", "region", "disease", "category",
})


def normalize_payload(obj):
    """递归归一化：剔除易变字段、排序键、稳定序列化。"""
    if isinstance(obj, dict):
        return {k: normalize_payload(v)
                for k, v in sorted(obj.items())
                if k not in VOLATILE_FIELDS}
    if isinstance(obj, (list, tuple)):
        return [normalize_payload(x) for x in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def pick_context(payload, extra_context=None):
    """从 payload 与显式上下文中提取确定性上下文字段（白名单）。"""
    ctx = {}
    src = {}
    if isinstance(payload, dict):
        src.update(payload)
    if isinstance(extra_context, dict):
        src.update(extra_context)
    for k in sorted(CONTEXT_FIELDS):
        v = src.get(k)
        if v not in (None, "", []):
            ctx[k] = v
    return ctx


def ai_input_hash(payload, task_type=None, model=None, prompt_version=None,
                  output_schema_version=None, extra_context=None,
                  identity_version=None):
    """稳定 AI 输入身份哈希（同语义输入 → 同 hash，跨 cycle 不变）。

    identity_version=None → 取模块级 AI_IDENTITY_VERSION（调用时解析，
    便于 contract version 变更时全量失效）。
    """
    identity_version = identity_version or AI_IDENTITY_VERSION
    blob = {
        "identity_version": identity_version,
        "task_type": task_type or "",
        "model": model or "",
        "prompt_version": prompt_version or "",
        "output_schema_version": output_schema_version or "",
        "payload": normalize_payload(payload),
        "context": pick_context(payload, extra_context),
    }
    return hashlib.sha256(
        json.dumps(blob, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def build_cache_key(ai_hash, task_type=None, model=None, identity_version=None):
    """缓存键：仅由稳定身份构成（不含 run_id / 时间戳）。"""
    identity_version = identity_version or AI_IDENTITY_VERSION
    return "%s|%s|%s|%s" % (identity_version, task_type or "",
                            model or "", ai_hash)
