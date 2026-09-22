#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""time_contract.py —— C2B §三–§六：单一时间契约（Time Contract）真值源。

三个语义完全不同、**不得互相冒充**的时间：

  data_as_of                 系统已完整处理完毕的数据窗口截止时间
                              （来自处理状态，绝不使用视图构建时间/墙钟）
  latest_verified_event_time 当前 public/canonical truth 中最新已核实事件时间
  generated_at               本次 view/report 构建时间

另有：
  backfill_collected_at      历史回填的采集时间（C2 引入，绝不冒充 data_as_of）
  backfill_reference_date    回填窗口的参考日（必须显式记录来源）

解析顺序（确定性，逐级记录来源与状态）：
  1) data/runtime/ops/time_contract.json          → source="time_contract"
  2) data/runtime/ops/production_state.json       → source="production_state.<field>"
  3) data/canonical/event_clusters.json.updated_at→ source="canonical.updated_at"（FALLBACK）
  4) 都不存在                                     → data_as_of=None，
                                                     status="UNAVAILABLE_EXPLICIT_FALLBACK"

**绝不静默用墙钟冒充 data_as_of**：无法确定时返回 None + 显式状态，由调用方展示。
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: production_state 中可作为 processing cutoff 的字段（语义同上）
DATA_AS_OF_FIELDS = ("last_successful_collection", "last_daily_report",
                     "last_weekly_report", "last_disease_run", "last_successful_ai")

STATUS_EXPLICIT = "EXPLICIT"
STATUS_FALLBACK_CANONICAL = "FALLBACK_CANONICAL"
STATUS_UNAVAILABLE = "UNAVAILABLE_EXPLICIT_FALLBACK"


def contract_path(root=None):
    return Path(root or ROOT) / "data" / "runtime" / "ops" / "time_contract.json"


def _iso(dt):
    if dt is None:
        return None
    return dt.isoformat()


def _parse(v):
    if not v:
        return None
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def write_contract(root=None, *, run_id, processed_through, data_as_of=None,
                   latest_verified_event_time=None, source=None,
                   backfill_reference_date=None, backfill_reference_source=None,
                   extra=None):
    """采集/处理成功收尾时写入契约（唯一写入入口）。

    data_as_of 缺省等于 processed_through —— 语义是"完整处理到的窗口截止"。
    """
    root = Path(root or ROOT)
    p = contract_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = read_contract(root) or {}
    pdt = _parse(processed_through)
    doc.update({
        "schema": "time-contract-v1",
        "run_id": run_id,
        "processed_through": processed_through,
        "last_successful_collection_at": processed_through,
        "data_as_of": data_as_of or _iso(pdt) or processed_through,
        "data_as_of_source": source or "time_contract.processed_through",
        "latest_verified_event_time": (latest_verified_event_time
                                       if latest_verified_event_time is not None
                                       else doc.get("latest_verified_event_time")),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    if backfill_reference_date:
        doc["backfill_reference_date"] = backfill_reference_date
        doc["backfill_reference_source"] = backfill_reference_source
    if extra:
        doc.update(extra)
    tmp = str(p) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    os.replace(tmp, str(p))
    return doc


def read_contract(root=None):
    p = contract_path(root)
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return None


def resolve(root=None):
    """返回 (data_as_of_iso, source, status)；无法确定时 value=None 且 status 显式为 UNAVAILABLE。"""
    root = Path(root or ROOT)
    doc = read_contract(root) or {}
    if doc.get("data_as_of"):
        return doc["data_as_of"], doc.get("data_as_of_source") or "time_contract", STATUS_EXPLICIT
    # production_state
    try:
        st = json.loads((root / "data" / "runtime" / "ops"
                         / "production_state.json").read_text(encoding="utf-8"))
        best, src = None, None
        for f in DATA_AS_OF_FIELDS:
            dt = _parse(st.get(f))
            if dt and (best is None or dt > best):
                best, src = dt, "production_state.%s" % f
        if best:
            return _iso(best), src, STATUS_EXPLICIT
    except Exception:  # noqa: BLE001
        pass
    # canonical fallback
    try:
        can = json.loads((root / "data" / "canonical" / "event_clusters.json")
                         .read_text(encoding="utf-8"))
        dt = _parse(can.get("updated_at"))
        if dt:
            return _iso(dt), "canonical.updated_at", STATUS_FALLBACK_CANONICAL
    except Exception:  # noqa: BLE001
        pass
    return None, None, STATUS_UNAVAILABLE


def refresh_derived_snapshots(root=None, run_id=None):
    """把契约同步进遗留快照（data/status.json / data/public/current_metrics.json）。

    C2B §三/§六：这两块快照不会自己跟进处理进度（历史上曾停在 2026-08-02），
    会造成"同一系统多个互相冲突的时间真值"。此处统一从契约刷新，
    保持单一事实源；无法确定 data_as_of 时写 None + 显式状态，**不用墙钟冒充**。
    """
    root = Path(root or ROOT)
    iso, src, status = resolve(root)
    rid = run_id or (read_contract(root) or {}).get("run_id")
    touched = []
    sp = root / "data" / "status.json"
    if sp.exists():
        try:
            d = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            d = {}
        d["data_as_of"] = iso
        d["data_as_of_bj"] = iso
        d["data_as_of_status"] = status
        d["data_as_of_source"] = src
        if rid:
            d["run_id"] = rid
        d["data_updated_at"] = iso
        sp.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        touched.append("data/status.json")
    mp = root / "data" / "public" / "current_metrics.json"
    if mp.exists():
        try:
            d = json.loads(mp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            d = {}
        d["data_as_of"] = iso
        d["data_as_of_status"] = status
        d["data_as_of_source"] = src
        if rid:
            d["run_id"] = rid
        d["updated_at"] = iso
        mp.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        touched.append("data/public/current_metrics.json")
    # C3R2-PRE §二：public 派生快照必须与 canonical 真值的 run_id / data_as_of 一致。
    # published_events.json 也是派生公开视图，同样从唯一契约刷新。
    pp = root / "data" / "public" / "published_events.json"
    if pp.exists():
        try:
            d = json.loads(pp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            d = {}
        d["data_as_of"] = iso
        d["data_as_of_status"] = status
        d["data_as_of_source"] = src
        if rid:
            d["run_id"] = rid
        d["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        pp.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        touched.append("data/public/published_events.json")
    return {"data_as_of": iso, "source": src, "status": status, "touched": touched}


def generated_at():
    """视图构建时间（与 data_as_of 语义不同，禁止互相冒充）。"""
    return datetime.now(timezone.utc).isoformat()
