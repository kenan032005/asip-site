#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 传染病 Canonical 存储（§九）。

- 独立保存于 data/disease/canonical/outbreak_events.json；
- 不写入 data/canonical/event_clusters.json（社安与疾病分层）；
- source record 可追溯、数字来源明确；
- 同一疾病/国家的后续更新通过 previous_event_id 关联；
- 不覆盖历史值；新通报可 supersede 旧通报（旧记录保留）；
- 原始来源 URL 保留。
"""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_PATH = ROOT / "data" / "disease" / "canonical" / "outbreak_events.json"


def _bj_now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def load_canonical(path=None):
    p = Path(path) if path else CANONICAL_PATH
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"items": [], "schema_version": "1.0.0", "pipeline_version": "disease-v1"}


def make_event_id(seed):
    return "DSEV_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def find_previous_for(disease_id, country_iso3, report_date, items, admin1=None):
    """查找同疾病+国家（且同 admin1 粒度）的上一事件（report_date 更早的最近一条）。

    粒度规则：仅当两边 admin1 都为空或相等时才视为同源（national 与州级不关联）。
    返回更早事件或 None。
    """
    best = None
    a1 = (admin1 or "").strip()
    for it in items:
        if it.get("disease_id") != disease_id:
            continue
        if it.get("country_iso3") != country_iso3:
            continue
        it_a1 = (it.get("admin1") or "").strip()
        if a1 != it_a1:
            continue  # 粒度不同（national vs 州级）不同源
        d = it.get("report_date") or ""
        if report_date and d and d < report_date:
            if best is None or d > (best.get("report_date") or ""):
                best = it
    return best


def upsert(record, path=None, link_previous=True, supersede=True):
    """写入一条 disease event 到 canonical。

    - 幂等：disease_event_id 已存在则更新该条（不重复追加）；
    - link_previous：同疾病+国家+admin1 存在更早事件 → 设 previous_event_id
      （指向更早通报），并标记旧事件 supersedes_event_id（历史保留）；
    - 历史记录永不删除、不被覆盖。
    """
    doc = load_canonical(path)
    items = doc["items"]
    eid = record["disease_event_id"]
    now = _bj_now()

    rec = dict(record)
    rec["created_at"] = rec.get("created_at") or now
    rec["updated_at"] = now

    if link_previous and not rec.get("previous_event_id"):
        prev = find_previous_for(rec.get("disease_id"), rec.get("country_iso3"),
                                 rec.get("report_date"), items,
                                 admin1=rec.get("admin1"))
        if prev and prev["disease_event_id"] != eid:
            rec["previous_event_id"] = prev["disease_event_id"]
            if supersede:
                for it in items:
                    if it["disease_event_id"] == prev["disease_event_id"]:
                        it["supersedes_event_id"] = eid
                        it["updated_at"] = now
                        break

    idx = None
    for i, it in enumerate(items):
        if it["disease_event_id"] == eid:
            idx = i
            break
    if idx is None:
        items.append(rec)
    else:
        items[idx] = rec

    _atomic_write(Path(path) if path else CANONICAL_PATH, doc)
    return rec
