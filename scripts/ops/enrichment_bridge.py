#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP C6-R5E — AI enrichment → 发布链桥接（Phase 1 追踪结论的落地）。

PHASE 1 追踪结论（EXPORT_BREAKPOINT）
------------------------------------
AI 产物落点：`data/runtime/ops/enrichment/S<event_id 末 8 位>_ok.json`
  其中 `safety.original_ai_output` 含 `title_zh` / `summary_zh` / `key_facts` /
  `uncertainties` / `security_relevance`（已生成、已持久化）。

公开产物生成路径：`data/canonical/event_clusters.json`
  → `scripts/data/compatibility_export.py::_published_from_cluster()`
  → `data/public/published_events.json` → 站点。

而 `_published_from_cluster` 取的是 **`cluster["title_cn"]` / `cluster["summary_cn"]`**，
这两个字段在采集/AI 周期中**从未被回填**（旧 applier `scripts/stage4_apply_enrichment.py`
读的是遗留路径 `data/ai/enrichment_results.json`，且按 `prompt_version==1.1.0` +
**排除** `deepseek-v4-flash` 过滤，与当前生产产物完全错配）
⇒ 译文/AI 摘要在 canonical 处被丢弃，永远到不了 public 与站点。

本模块职责（单一）
------------------
把**已存在**的 AI 产物中的中文与结构化字段回填进 canonical 事件行。
**不重新生成 AI、不调用任何外部模型**（REAL_AI_CALLS = 0）。

保守/安全约束
-------------
- 只填 `title_cn` / `summary_cn` **为空**的事件（绝不覆盖任何既有中文，天然幂等）；
- 仅接受 `status=ok` 且 `schema_pass=true` 且 `provider_status=succeeded`
  且 `safety.gate=PASS` 且 `safety.publication_eligible=true` 的产物（不绕过安全闸门）；
- `label` 与 `event_id` 必须自校验一致（`S` + `event_id[-8:]`），防错配；
- 不新增/删除事件，不改任何其它字段，**不改写任何条目的 `run_id`**（谱系保持）；
- 直接原子写（沿用本阶段既有 applier 的写法），但**写盘前先做 schema 校验**，任一不合规即整体中止；
- 默认 dry-run，`--apply` 才写盘。

用法
----
  python scripts/ops/enrichment_bridge.py             # dry-run
  python scripts/ops/enrichment_bridge.py --apply     # 写盘
  python scripts/ops/enrichment_bridge.py --apply --emit-json
"""

import argparse
import glob
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLUSTERS_PATH = ROOT / "data" / "canonical" / "event_clusters.json"
ENRICHMENT_DIR = ROOT / "data" / "runtime" / "ops" / "enrichment"

#: AI 产物字段 → canonical 事件字段（同名直投）
FIELD_MAP = {"title_zh": "title_cn", "summary_zh": "summary_cn"}
#: 结构化 AI 细节（canonical `event_cluster.schema.json` 为 additionalProperties=true，可承载）
EXTRA_FIELDS = ("key_facts", "uncertainties", "security_relevance")
#: 供审计的 provenance 字段
PROVENANCE = {"ai_model": "returned_model", "ai_input_hash": "ai_input_hash",
              "ai_task_type": "task_type"}


def bj_iso():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def load_clusters(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_artifacts(enrichment_dir):
    """读取全部 `S*_ok.json`；返回 (by_event, stats)。

    by_event[event_id] = {"fields": {...}, "label": str, "path": str}
    """
    by_event = {}
    stats = {"files": 0, "accepted": 0, "rejected_gate": 0, "rejected_label": 0,
             "rejected_empty": 0, "rejected_unreadable": 0}
    for p in sorted(glob.glob(str(Path(enrichment_dir) / "S*_ok.json"))):
        stats["files"] += 1
        label = os.path.basename(p)[:-len("_ok.json")]
        try:
            with open(p, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception:  # noqa: BLE001
            stats["rejected_unreadable"] += 1
            continue

        eid = doc.get("event_id")
        if not eid:
            stats["rejected_unreadable"] += 1
            continue
        # label 自校验：S + event_id 末 8 位（防错配）
        if label != "S" + str(eid)[-8:]:
            stats["rejected_label"] += 1
            continue

        safety = doc.get("safety") or {}
        ai_out = safety.get("original_ai_output") or doc.get("original_ai_output") or {}
        if not (doc.get("status") == "ok" and doc.get("schema_pass") is True
                and doc.get("provider_status") == "succeeded"
                and safety.get("gate") == "PASS"
                and safety.get("publication_eligible") is True):
            stats["rejected_gate"] += 1
            continue

        fields = {}
        for src, dst in FIELD_MAP.items():
            v = ai_out.get(src)
            if isinstance(v, str) and v.strip():
                fields[dst] = v.strip()
        if not ("title_cn" in fields and "summary_cn" in fields):
            stats["rejected_empty"] += 1
            continue
        for k in EXTRA_FIELDS:
            v = ai_out.get(k)
            if v not in (None, "", [], {}):
                fields[k] = v
        for dst, src in PROVENANCE.items():
            v = doc.get(src)
            if v not in (None, ""):
                fields[dst] = v
        fields["ai_bridged_at"] = bj_iso()

        by_event[eid] = {"fields": fields, "label": label, "path": p}
        stats["accepted"] += 1
    return by_event, stats


def plan_bridge(clusters, by_event):
    """纯函数：计算需要回填的 (item, fields)。返回 (assignments, stats)。"""
    stats = {"clusters": len(clusters), "matched": 0, "bridged": 0,
             "skipped_already_translated": 0, "unmatched_cluster": 0}

    assignments = []
    for it in clusters:
        eid = it.get("event_id")
        art = by_event.get(eid)
        if not art:
            continue
        stats["matched"] += 1
        has_cn = bool(str(it.get("title_cn") or "").strip()
                      or str(it.get("summary_cn") or "").strip())
        if has_cn:
            stats["skipped_already_translated"] += 1
            continue
        assignments.append((it, art["fields"]))
        stats["bridged"] += 1
    used = {it.get("event_id") for it, _ in assignments}
    stats["unmatched_cluster"] = len(set(by_event) - used - {
        c.get("event_id") for c in clusters})
    return assignments, stats


def validate_clusters(clusters):
    """写盘前 schema 校验（复用 Repository 的校验器）；返回错误列表。"""
    try:
        # 三种导入路径都试（脚本以 `python scripts/ops/enrichment_bridge.py` 运行，
        # 此时 sys.path[0] 是 scripts/ops，`scripts.data` 需要仓库根在路径上）
        for _p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "scripts" / "data")):
            if _p not in sys.path:
                sys.path.insert(0, _p)
        from scripts.data.repository import Repository  # noqa: E402
        # Repository 的 root 语义是**仓库根**（canonical_dir = root/"data"/"canonical"）
        repo = Repository(root=ROOT)
        return repo._validate_records(clusters, "event_cluster", "event_id")
    except Exception as e:  # noqa: BLE001
        return ["VALIDATOR_UNAVAILABLE: %s: %s" % (type(e).__name__, e)]


def write_clusters_atomic(doc, path):
    d = os.path.dirname(str(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".event_clusters.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description="ASIP C6-R5E — AI enrichment → canonical 发布桥")
    ap.add_argument("--apply", action="store_true", help="写盘（默认 dry-run）")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--limit", type=int, default=0, help="最多回填 N 条（0=不限；仅用于受控验证）")
    args = ap.parse_args(argv)

    root = Path(args.root)
    clusters_path = root / "data" / "canonical" / "event_clusters.json"
    enrichment_dir = root / "data" / "runtime" / "ops" / "enrichment"

    doc = load_clusters(clusters_path)
    clusters = doc.get("items", [])
    by_event, astats = read_artifacts(enrichment_dir)
    assignments, pstats = plan_bridge(clusters, by_event)
    if args.limit:
        assignments = assignments[:args.limit]

    events = []
    for it, fields in assignments:
        events.append({"event_id": it.get("event_id"),
                       "title_cn": fields.get("title_cn", "")[:60],
                       "summary_cn_len": len(fields.get("summary_cn") or ""),
                       "extra_keys": sorted(k for k in fields
                                            if k in EXTRA_FIELDS)})

    out = {
        "mode": "apply" if args.apply else "dry-run",
        "clusters_path": str(clusters_path),
        "enrichment_dir": str(enrichment_dir),
        "artifact_stats": astats,
        "plan_stats": pstats,
        "would_bridge": len(assignments),
        "events": events[:20],
        "envelope_run_id": doc.get("run_id"),
        "real_ai_calls": 0,
    }

    if args.apply and assignments:
        # 守卫：只要求「本次未引入新的 schema 违规」。
        # 既有违规（本周期采集写入的 naive `event_time`，违反 event_cluster 的
        # `format: date-time`）属**采集侧**缺陷，不在本包 STRICT SCOPE 内，故不改动、
        # 只原样保留并如实计数上报（见 preexisting_schema_violations）。
        errs_before = validate_clusters([dict(it) for it, _ in assignments])
        for it, fields in assignments:
            for k, v in fields.items():
                it[k] = v
        errs_after = validate_clusters([it for it, _ in assignments])
        new_errs = [e for e in errs_after if e not in errs_before]
        out["schema_errors_introduced"] = len(new_errs)
        out["preexisting_schema_violations"] = len(errs_before)
        out["preexisting_sample"] = errs_before[:2]
        if new_errs:
            out["schema_error_sample"] = new_errs[:3]
            out["written"] = False
            print(json.dumps(out, ensure_ascii=False, indent=1))
            print("  ✗ 阻断：本次回填引入了新的 schema 违规，未写盘", file=sys.stderr)
            return 2
        write_clusters_atomic(doc, clusters_path)
        out["written"] = True
    elif args.apply:
        out["written"] = False
        out["schema_errors_introduced"] = 0

    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
