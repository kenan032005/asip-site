#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_legacy.py — Stage 3A 历史公开事件审计 + 清洗。

对 published_events.json 中所有非 Stage 3A 采集事件（legacy）逐条审计，
分类为：
  valid_legacy              有效历史事件（国家正确、来源真实）
  invalid_test_or_placeholder 测试/占位/演示数据
  country_scope_mismatch    国家范围不符（非乍得/尼日尔）
  duplicate                 重复
  invalid_source            来源无效
  invalid_time              时间无效/未来
  missing_traceability      缺少可追溯字段
  other                     其他

不合格数据移出 published_events，进入隔离区（data/canonical/quarantine.json），
保留隔离原因。valid_legacy 保留在 published_events。

用法：
  python scripts/audit_legacy.py            # 审计并清洗
  python scripts/audit_legacy.py --dry      # 仅审计预览，不写文件
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(ROOT, "data")
PUBLIC_DIR = os.path.join(DATA_DIR, "public")
PUBLISHED_PATH = os.path.join(PUBLIC_DIR, "published_events.json")
QUARANTINE_PATH = os.path.join(DATA_DIR, "canonical", "quarantine.json")

# 平台允许的国家
VALID_COUNTRIES_CN = {"乍得", "尼日尔"}

# 测试/占位数据标记
TEST_MARKERS = ["测试", "placeholder", "占位", "demo event", "test event",
                "示例", "mock", "synthetic", "fixture", "lorem"]


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def classify_legacy(item):
    """审计单条 legacy 事件，返回 (分类, 原因)。"""
    eid = item.get("event_id", "?")
    country = item.get("country_cn") or item.get("country") or ""
    title = (item.get("title_cn") or "") + " " + (item.get("title_original") or "")
    url = ""
    links = item.get("source_links") or []
    if links:
        url = links[0].get("url", "")
    pub_time = item.get("published_time") or item.get("event_time") or ""
    run_id = item.get("run_id") or ""
    legacy_flag = item.get("legacy_migration_preserved") is True
    reason = item.get("publication_reason") or ""

    # 1. 测试/占位数据
    tl = title.lower()
    if any(m in tl for m in TEST_MARKERS):
        return "invalid_test_or_placeholder", "title_contains_test_marker"

    # 2. 国家范围不符
    if country not in VALID_COUNTRIES_CN:
        return "country_scope_mismatch", f"国家={country}，不在平台范围(乍得/尼日尔)"

    # 3. 时间无效/未来
    if pub_time:
        try:
            dt = datetime.fromisoformat(pub_time.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt > datetime.now(timezone.utc) + __import__("datetime").timedelta(hours=1):
                return "invalid_time", f"未来时间 {pub_time}"
        except (ValueError, TypeError):
            return "invalid_time", f"时间格式无效 {pub_time}"

    # 4. 来源无效
    if not url or not url.startswith("http"):
        return "invalid_source", f"URL 无效: {url}"

    # 5. 缺少可追溯字段
    missing = []
    if not title.strip():
        missing.append("title")
    if not run_id:
        missing.append("run_id")
    if not pub_time:
        missing.append("published_time")
    if not links:
        missing.append("source_links")
    if missing:
        return "missing_traceability", "缺少: " + ",".join(missing)

    # 6. 非平台当前政策的 legacy 标记 —— 保留但标注
    return "valid_legacy", reason or "legacy"


def main():
    ap = argparse.ArgumentParser(description="Stage 3A legacy 审计")
    ap.add_argument("--dry", action="store_true", help="仅审计，不写文件")
    args = ap.parse_args()

    pub = load_json(PUBLISHED_PATH, {"items": []})
    items = pub.get("items", [])

    legacy = [i for i in items if i.get("publication_reason") != "Stage 3A 真实采集"]
    stage3 = [i for i in items if i.get("publication_reason") == "Stage 3A 真实采集"]

    print(f"审计开始: 总数={len(items)} (legacy={len(legacy)}, stage3a={len(stage3)})")
    print("=" * 70)

    results = {}
    quarantine_entries = []
    valid_legacy = []
    for item in legacy:
        cat, why = classify_legacy(item)
        results[cat] = results.get(cat, 0) + 1
        eid = item.get("event_id", "?")
        if cat == "valid_legacy":
            valid_legacy.append(item)
            print(f"  [KEEP] {cat}: {eid} {item.get('title_cn') or item.get('title_original','')[:40]}")
        else:
            print(f"  [MOVE] {cat}: {eid} ({why})")
            quarantine_entries.append({
                "candidate_id": eid,
                "original_event_id": eid,
                "title": item.get("title_cn") or item.get("title_original", ""),
                "url": (item.get("source_links") or [{}])[0].get("url", ""),
                "source": (item.get("source_links") or [{}])[0].get("source_name", ""),
                "country": item.get("country_cn", ""),
                "reason": cat,
                "reason_detail": why,
                "collected_at": item.get("collected_at_beijing") or item.get("published_time", ""),
                "original_payload": item,
            })

    print("=" * 70)
    print("审计统计:")
    for cat in sorted(results, key=lambda c: -results[c]):
        print(f"  {cat:32s}: {results[cat]}")
    print(f"  有效保留(valid_legacy): {len(valid_legacy)}")

    if args.dry:
        print("\n[--dry] 未写入任何文件。")
        return 0

    # 重建 published_events: valid_legacy + stage3a
    new_items = valid_legacy + stage3
    pub["items"] = new_items
    save_json(PUBLISHED_PATH, pub)
    print(f"\npublished_events: {len(items)} → {len(new_items)}")

    # 追加隔离
    if quarantine_entries:
        q = load_json(QUARANTINE_PATH, {"items": []})
        existing_ids = {e.get("candidate_id") or e.get("original_event_id") for e in q.get("items", [])}
        new_q = [e for e in quarantine_entries if e["candidate_id"] not in existing_ids]
        q["items"] = q.get("items", []) + new_q
        save_json(QUARANTINE_PATH, q)
        print(f"隔离区: +{len(new_q)} (总计 {len(q['items'])})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
