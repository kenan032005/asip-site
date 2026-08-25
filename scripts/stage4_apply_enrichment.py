#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 第三执行包 — 将 active Hy3 enrichment 注入 Public（§七）。

职责（单一）：
- 从 data/ai/enrichment_results.json 选取每个事件的「active Hy3 正式结果」；
- 按 event_id 匹配，把 AI 字段补充进 data/public/published_events.json 的条目；
- 保持 Public ⊆ Canonical（不新增、不删除事件）；
- review_before_activation 事件一律不注入；
- DeepSeek 试跑结果（prompt 1.0.0 / model=deepseek-v4-flash）不得作为 active。

字段注入（§七 白名单）：
  title_zh / summary_zh / event_type / security_relevance / classification_confidence
  / location / key_facts / uncertainties
  ai_result_id / ai_model / ai_prompt_version / ai_processed_at

安全约束：
- 不修改 Canonical；
- 不读取/复制 Prompt 全文、API Key、完整 AI 原始响应；
- 默认 dry-run（--apply 才写盘）。

用法：
  python scripts/stage4_apply_enrichment.py [--apply] [--active-prompt-version 1.1.0]
                                            [--exclude-models deepseek-v4-flash]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_RESULTS = os.path.join(ROOT, "data", "ai", "enrichment_results.json")
PUBLIC_EVENTS = os.path.join(ROOT, "data", "public", "published_events.json")
CANONICAL = os.path.join(ROOT, "data", "canonical", "event_clusters.json")

# 本包明确保持 review_before_activation 的事件（§四/§七：不发布其 AI 结果）
REVIEW_BEFORE_ACTIVATION = {
    "EVT_2520e85f1185795d",  # primary_country_body_mismatch（利比亚正文/TCD 标注）
}

# 注入到 Public 的 AI 字段（§七 白名单）
AI_SEMANTIC_FIELDS = [
    "title_zh", "summary_zh", "event_type", "security_relevance",
    "classification_confidence", "location", "key_facts", "uncertainties",
]
AI_META_FIELDS = {
    "ai_result_id": "result_id",
    "ai_model": "ai_model",
    "ai_prompt_version": "prompt_version",
    "ai_processed_at": "processed_at",
}


def bj_now():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")


def select_active_result(records, active_prompt_version, exclude_models):
    """从某 event 的所有 enrichment record 中选 active（Hy3 正式结果）。

    规则：processing_status=succeeded 且 prompt_version=active_prompt_version
    且 ai_model 不在 exclude_models 中的最新一条（processed_at 排序）。
    返回 record 或 None。
    """
    cands = [r for r in records
             if r.get("processing_status") == "succeeded"
             and r.get("prompt_version") == active_prompt_version
             and r.get("ai_model") not in (exclude_models or set())]
    if not cands:
        return None
    cands.sort(key=lambda r: r.get("processed_at") or "", reverse=True)
    return cands[0]


def apply_enrichment(public_items, results_items, canonical_ids,
                     active_prompt_version="1.1.0",
                     exclude_models=None,
                     review_before_activation=None):
    """纯函数：把 active enrichment 注入 public_items（返回新列表 + stats）。

    public_items: list[dict]（Published 事件，可修改副本）
    results_items: list[dict]（enrichment_results.json items）
    canonical_ids: set[str]（canonical 中全部 event_id，用于 Public⊆Canonical 校验）
    """
    exclude_models = set(exclude_models or ["deepseek-v4-flash"])
    rba = set(review_before_activation or REVIEW_BEFORE_ACTIVATION)

    # 按 event_id 分组 results
    by_event = {}
    for rec in results_items:
        by_event.setdefault(rec.get("event_id"), []).append(rec)

    new_items = []
    stats = {"total": len(public_items), "injected": 0, "no_active_result": 0,
             "rba_skipped": 0, "orphan_skipped": 0, "not_in_canonical": []}

    for it in public_items:
        eid = it.get("event_id")
        if eid not in canonical_ids:
            stats["orphan_skipped"] += 1
            stats["not_in_canonical"].append(eid)
            new_items.append(dict(it))
            continue
        if eid in rba:
            stats["rba_skipped"] += 1
            new_items.append(dict(it))
            continue
        active = select_active_result(by_event.get(eid, []),
                                      active_prompt_version, exclude_models)
        if active is None:
            stats["no_active_result"] += 1
            new_items.append(dict(it))
            continue

        out = dict(it)
        for f in AI_SEMANTIC_FIELDS:
            if f in active:
                out[f] = active[f]
        for dst, src in AI_META_FIELDS.items():
            if src in active:
                out[dst] = active[src]
        new_items.append(out)
        stats["injected"] += 1
    return new_items, stats


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("  ⚠ 读取 %s 失败: %s" % (path, e))
        return default


def main(argv=None):
    ap = argparse.ArgumentParser(description="ASIP Stage 4 — 注入 active Hy3 enrichment 到 Public")
    ap.add_argument("--apply", action="store_true", help="写盘（默认 dry-run）")
    ap.add_argument("--active-prompt-version", default="1.1.0")
    ap.add_argument("--exclude-models", default="deepseek-v4-flash",
                    help="逗号分隔，不作为 active 的模型标识（DeepSeek 试跑对照）")
    args = ap.parse_args(argv)

    results = load_json(AI_RESULTS, {"items": []})
    pub = load_json(PUBLIC_EVENTS, {"items": []})
    canon = load_json(CANONICAL, {"items": []})

    canonical_ids = {e.get("event_id") for e in canon.get("items", [])}
    exclude = {m.strip() for m in (args.exclude_models or "").split(",") if m.strip()}

    new_items, stats = apply_enrichment(
        pub.get("items", []), results.get("items", []), canonical_ids,
        active_prompt_version=args.active_prompt_version,
        exclude_models=exclude,
    )

    # Public ⊆ Canonical 校验
    orphan_check = [it.get("event_id") for it in new_items
                    if it.get("event_id") not in canonical_ids]

    print(json.dumps({
        "mode": "apply" if args.apply else "dry-run",
        "active_prompt_version": args.active_prompt_version,
        "exclude_models": sorted(exclude),
        "stats": stats,
        "public_total_after": len(new_items),
        "public_orphan_count": len(orphan_check),
        "public_orphans": orphan_check,
    }, ensure_ascii=False, indent=2))

    if orphan_check:
        print("  ✗ 阻断：Public 存在不在 Canonical 的孤儿事件，未写盘")
        return 2

    if args.apply:
        pub["items"] = new_items
        pub["updated_at"] = bj_now()
        tmp = PUBLIC_EVENTS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(pub, f, ensure_ascii=False, indent=2)
        os.replace(tmp, PUBLIC_EVENTS)
        print("  已写盘: %s" % PUBLIC_EVENTS)
    else:
        print("  dry-run：未写盘（加 --apply 生效）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
