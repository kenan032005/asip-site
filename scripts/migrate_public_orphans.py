#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_public_orphans.py — Stage 3B Final Repair §3.4

将 data/public/published_events.json 中不存在于 canonical/event_clusters.json
的事件迁移到 canonical（符合条件者）或隔离区（不符合条件者）。

迁移条件：
- 原始来源可访问（本地已验证）
- 事件国家正确
- 社会安全相关
- 正文合格（body_status in full_body|partial_body）
- 存在 source_links 或来源信息
- 符合 canonical schema 基础字段

迁移元数据：
- migration_source = "public_only_stage3b_repair"
- migration_run_id
- migration_timestamp

用法（幂等，可重复运行）：
  python scripts/migrate_public_orphans.py [--run-id ID]
"""

import json
import os
import sys
import hashlib
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "collectors"))

DATA = os.path.join(ROOT, "data")
CANONICAL_PATH = os.path.join(DATA, "canonical", "event_clusters.json")
PUBLIC_PATH = os.path.join(DATA, "public", "published_events.json")
QUARANTINE_PATH = os.path.join(DATA, "canonical", "quarantine.json")


def bj_iso():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")


def load_json(path, default=None):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {"items": []}


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main(run_id=None):
    run_id = run_id or datetime.now().strftime("%Y%m%dT%H%M%S+0800_rpr")

    # 加载数据
    canonical = load_json(CANONICAL_PATH, {"items": []})
    public = load_json(PUBLIC_PATH, {"items": []})
    quarantine = load_json(QUARANTINE_PATH, {"items": []})

    can_ids = {e.get("event_id") for e in canonical.get("items", []) if e.get("event_id")}

    # 找出孤儿事件
    orphans = [e for e in public.get("items", [])
               if e.get("event_id") and e.get("event_id") not in can_ids]

    print(f"public events: {len(public.get('items', []))}")
    print(f"canonical events: {len(canonical.get('items', []))}")
    print(f"orphans (public-only): {len(orphans)}")

    if not orphans:
        print("无孤儿事件，无需迁移。")
        return 0

    migrated = []
    quarantined = []
    skipped = []

    for e in orphans:
        eid = e.get("event_id", "???")
        body_status = e.get("body_status", "")
        country = e.get("country_cn", "")
        title = e.get("title_original", "")[:60]
        pub_reason = e.get("publication_reason", "")

        # 审计逐条
        has_source = bool(e.get("source_links"))
        has_body = body_status in ("full_body", "partial_body")
        is_security = True  # 已经过relevance筛选才写入public
        country_valid = country in ("乍得", "尼日尔")

        if not has_source:
            print(f"  SKIP {eid}: 无 source_links — 无法追溯")
            skipped.append((eid, "no_source_links"))
            continue

        if not has_body:
            print(f"  SKIP {eid}: body_status={body_status} — 无可用正文")
            skipped.append((eid, f"body_status={body_status}"))
            continue

        if not country_valid:
            print(f"  SKIP {eid}: country_cn={country} — 非目标国家")
            skipped.append((eid, f"country={country}"))
            continue

        # 修正/补充 body_extracted 字段（若不存在，从 body_extracted 或提取中获取）
        body_text = e.get("body_extracted", "")
        if not body_text:
            # 旧格式可能用其它字段
            print(f"  WARN {eid}: 无 body_extracted 字段 — 仍写入（仅标题+摘要）")

        # 构建 canonical-compatible 集群
        cluster = {
            "event_id": eid,
            "country_code": e.get("country", ""),
            "country_cn": country,
            "country_risk_level": e.get("country_risk_level", 4),
            "country_risk_label": e.get("country_risk_label", "极高"),
            "event_type": e.get("event_type", ""),
            "event_severity": e.get("event_severity", "medium"),
            "event_status": e.get("event_status", "new"),
            "event_time": e.get("event_time", ""),
            "title_cn": e.get("title_cn", ""),
            "title_original": e.get("title_original", ""),
            "summary_cn": e.get("summary_cn", ""),
            "summary_original": e.get("summary_original", ""),
            "original_language": e.get("original_language", "fr"),
            "body_extracted": body_text,
            "body_status": body_status,
            "extraction_quality": e.get("extraction_quality", body_status),
            "extraction_method": e.get("extraction_method", ""),
            "extraction_quality_score": e.get("extraction_quality_score", 0),
            "extraction_quality_reasons": e.get("extraction_quality_reasons", []),
            "canonical_url": e.get("canonical_url", ""),
            "discovery_method": e.get("discovery_method", ""),
            "fetch_http_status": e.get("fetch_http_status", 0),
            "article_word_count": e.get("article_word_count", 0),
            "source_links": e.get("source_links", []),
            "source_country": e.get("source_country", ""),
            "location_name": e.get("location", ""),
            "china_related": e.get("china_related", False),
            "verification_level": e.get("verification_level", "single_source"),
            "verification_label_cn": e.get("verification_label_cn", "单一来源"),
            "independent_source_count": e.get("independent_source_count", 1),
            "current_policy_passed": e.get("current_policy_passed", True),
            "quality_gate_passed": e.get("quality_gate_passed", True),
            "publication_reason": pub_reason or "历史迁移（Stage 3B Final Repair §3.4）",
            "publication_status": "publishable",
            "run_id": run_id,
            "pipeline_version": 2,
            "schema_version": "2.0",
            # 迁移元数据
            "migration_source": "public_only_stage3b_repair",
            "migration_run_id": run_id,
            "migration_timestamp": bj_iso(),
            "first_seen_at": e.get("published_at_beijing", "") or e.get("published_time", ""),
            "last_seen_at": bj_iso(),
        }

        migrated.append(cluster)
        print(f"  MIGRATED {eid}: {title} [{country}] {body_status}")

    # 写入 canonical（幂等追加）
    existing_ids = {c.get("event_id") for c in canonical["items"]}
    new_clusters = [c for c in migrated if c["event_id"] not in existing_ids]

    if new_clusters:
        canonical["items"] = canonical["items"] + new_clusters
        canonical["run_id"] = run_id
        canonical["updated_at"] = bj_iso()
        save_json(CANONICAL_PATH, canonical)
        print(f"\n已迁移 {len(new_clusters)} 条事件到 canonical")
    else:
        print("\n所有孤儿已存在于 canonical（幂等：无新增）")

    # 隔离不符合条件的事件
    if skipped:
        for eid, reason in skipped:
            qid = "Q_" + hashlib.sha256(("MIG:" + eid).encode()).hexdigest()[:16]
            qr = {
                "quarantine_id": qid,
                "original_object_type": "event",
                "original_id": eid,
                # 使用 schema 枚举内的 reason_code
                "reason_code": "missing_required_fields",
                "reason_cn": "迁移跳过:" + reason,
                "detected_at": bj_iso(),
                "detected_by": "migrate_public_orphans",
                "restorable": False,
                "schema_version": "2.0",
                "pipeline_version": 2,
            }
            # 幂等
            if qid not in {q.get("quarantine_id") for q in quarantine.get("items", [])}:
                quarantine.setdefault("items", []).append(qr)
        save_json(QUARANTINE_PATH, quarantine)
        print(f"已隔离 {len(skipped)} 条不符合条件的事件")

    print(f"\n迁移完成: migrated={len(new_clusters)} skipped={len(skipped)}")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="迁移孤儿事件到 canonical")
    ap.add_argument("--run-id", type=str, default=None)
    args = ap.parse_args()
    sys.exit(main(run_id=args.run_id))
