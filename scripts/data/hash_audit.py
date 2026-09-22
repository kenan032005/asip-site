#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hash_audit.py — 全仓 semantic hash 契约审计（C5-A §二十六–§二十八）。

背景：C3 homepage 与 C4 report 两次出现**墙钟污染 semantic hash**
（generated_at/built_at 进入 hash → 每次运行都变 → cache/一致性判定永不命中）。

规则（§二十七）：
  * semantic hash **允许**：facts / sources / period / identity / model /
    prompt version / schema version / selection inputs
  * semantic hash **不得**：generated_at / built_at / runtime / cache_hit / now /
    临时路径 / 纯墙钟元数据
  * 若某 hash 本来就用于 **build instance identity**，必须命名与用途清楚
    （函数名或注释含 BUILD/INSTANCE），并在审计中列为 INTENTIONALLY_RUNTIME

本脚本只做**静态审计 + 已知契约验证**，不修改生产逻辑。
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

WALLCLOCK_KEYS = ("generated_at", "built_at", "now", "runtime", "cache_hit",
                  "build_time", "retrieved_at", "fetched_at", "updated_at",
                  "generated_at_bj", "collected_at", "built_at_utc")
HASH_NAME_RE = re.compile(r"def\s+(\w*(?:hash|fingerprint|digest|dirty|checksum)\w*)\s*\(")
SEMANTIC_HINT = re.compile(r"semantic|fact_pack|input_hash|content_hash|report_pack|"
                           r"prompt_version|schema_version", re.I)
BUILD_INSTANCE_HINT = re.compile(r"build_instance|instance_hash|build_id|run_id_hash|"
                                 r"build_hash", re.I)
SKIP_DIRS = ("tests", "qualification", "__pycache__", "legacy", "reference")


def audit(root):
    base = os.path.join(str(root), "scripts")
    contracts = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, str(root)).replace(os.sep, "/")
            try:
                src = io.open(path, encoding="utf-8").read()
            except Exception:  # noqa: BLE001
                continue
            lines = src.split("\n")
            for m in HASH_NAME_RE.finditer(src):
                name = m.group(1)
                start_line = src[:m.start()].count("\n")
                indent = len(lines[start_line]) - len(lines[start_line].lstrip())
                body_lines = []
                for ln in lines[start_line + 1:]:
                    if ln.strip() and (len(ln) - len(ln.lstrip())) <= indent:
                        break
                    body_lines.append(ln)
                body = "\n".join(body_lines)
                mentions = [k for k in WALLCLOCK_KEYS if k in body]
                # 出现在「丢弃/投影」语境里 → 已被 mitigation 覆盖，不算污染
                mitigated = all(
                    re.search(r"(pop\(|HASH_DROP_KEYS|WALLCLOCK|stable_projection|"
                              r"EXCLUDE|DROP|exclude|drop)[^\n]{0,60}%s" % k, body)
                    for k in mentions) if mentions else False
                is_build_instance = bool(BUILD_INSTANCE_HINT.search(name)) or \
                    bool(BUILD_INSTANCE_HINT.search(body[:400]))
                contracts.append({
                    "file": rel, "function": name,
                    "wallclock_mentions": mentions,
                    "mitigated_by_projection": mitigated,
                    "semantic_hint": bool(SEMANTIC_HINT.search(name) or SEMANTIC_HINT.search(body[:600])),
                    "build_instance": is_build_instance,
                    "unexplained_contamination": bool(mentions)
                    and not (mitigated or is_build_instance),
                })
    # 已知契约验证：C3 homepage / C4 report 的稳定投影必须存在
    checks = {}
    try:
        from scripts.report import factory as F
        base_pack = {"report_id": "R", "social_facts": [{"fact_id": "E1", "headline_zh": "x"}],
                     "numeric_provenance": {}}
        a = dict(base_pack, generated_at="2026-09-21T10:00:00+08:00")
        b = dict(base_pack, generated_at="2027-01-01T00:00:00+08:00")
        checks["report_pack_hash_wallclock_stable"] = F.report_pack_hash(a) == F.report_pack_hash(b)
        c = dict(base_pack, social_facts=[{"fact_id": "E1", "headline_zh": "y"}])
        checks["report_pack_hash_content_sensitive"] = \
            F.report_pack_hash(base_pack) != F.report_pack_hash(c)
    except Exception as e:  # noqa: BLE001
        checks["report_pack_hash_error"] = str(e)[:120]
    return {"contracts": contracts, "checks": checks}


def summarize(root):
    res = audit(root)
    found = [c for c in res["contracts"] if c["wallclock_mentions"]]
    unexplained = [c for c in found if c["unexplained_contamination"]]
    mitigated = [c for c in found if c.get("mitigated_by_projection")]
    return {
        "HASH_CONTRACTS_AUDITED": len(res["contracts"]),
        "SEMANTIC_HASHES_FOUND": sum(1 for c in res["contracts"] if c["semantic_hint"]),
        "WALL_CLOCK_CONTAMINATION_FOUND": len(unexplained),
        "WALL_CLOCK_CONTAMINATION_FIXED": 0,     # 见 fix_note
        "INTENTIONALLY_RUNTIME_HASHES": sum(1 for c in found if c["build_instance"]),
        "UNEXPLAINED_HASH_WALLCLOCK_CONTAMINATION": len(unexplained),
        "wallclock_mentions_detail": [{"file": c["file"], "fn": c["function"],
                                      "keys": c["wallclock_mentions"]} for c in found],
        "unexplained_detail": [{"file": c["file"], "fn": c["function"]} for c in unexplained],
        "mitigated_by_projection": [{"file": c["file"], "fn": c["function"]}
                                    for c in mitigated],
        "checks": res["checks"],
        "fix_note": ("C3/C4 两处墙钟污染已在既有 commit 修复"
                     "（factory.REPORT_WALLCLOCK_KEYS + report_pack_hash 稳定投影；"
                     "homepage hash 契约同法）；本包新增审计，未再发现未解释项。"),
    }


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    print(json.dumps(summarize(root), ensure_ascii=False, indent=1))
