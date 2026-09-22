#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c3_artifacts.py —— C3 的 AI artifact 层（§三十一）。

目录约定（沿用既有 `data/intelligence/` 体系，不创造第二套 truth）：

    data/intelligence/ai/
        localization/      news_id -> {title_cn, summary_cn, status, ...}
        event_analysis/    event_id -> event-intelligence-v1
        country_analysis/  country -> country-intelligence-v1（含窗口 24h/72h/7d）
        homepage_analysis/ homepage-analysis-v1
        runs/              每次运行的统计与成本

每条记录至少包含：schema_version / model / prompt_version / input_hash /
generated_at / data_as_of / status / source_fact_refs。
"""
import hashlib
import io
import json
import os
import time
from datetime import datetime, timedelta, timezone

BJ = timezone(timedelta(hours=8))
REQUIRED_META = ("schema_version", "model", "prompt_version", "input_hash",
                 "generated_at", "data_as_of", "status", "source_fact_refs")

SECTIONS = ("localization", "event_analysis", "country_analysis",
            "homepage_analysis", "runs")


def ai_root(root):
    return os.path.join(str(root), "data", "intelligence", "ai")


def section_dir(root, section):
    if section not in SECTIONS:
        raise ValueError("unknown ai artifact section: %r" % section)
    d = os.path.join(ai_root(root), section)
    os.makedirs(d, exist_ok=True)
    return d


def sha256_text(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


def path_for(root, section, key):
    safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in str(key))[:120]
    return os.path.join(section_dir(root, section), safe + ".json")


def write_artifact(root, section, key, record, *, schema_version, model,
                   prompt_version, input_hash, status, source_fact_refs,
                   data_as_of=None, extra=None):
    """写入一条 AI artifact（强制补齐元数据契约）。"""
    rec = {
        "schema_version": schema_version,
        "model": model,
        "prompt_version": prompt_version,
        "input_hash": input_hash,
        "generated_at": datetime.now(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "data_as_of": data_as_of,
        "status": status,
        "source_fact_refs": list(source_fact_refs or []),
    }
    # payload（record）与 extra 都并入同一条记录；元数据缺失即报错
    if record:
        rec.update(record)
    if extra:
        rec.update(extra)
    missing = [k for k in REQUIRED_META if k not in rec]
    if missing:
        raise ValueError("artifact missing required metadata: %s" % missing)
    p = path_for(root, section, key)
    tmp = p + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
    return rec


def read_artifact(root, section, key):
    p = path_for(root, section, key)
    if not os.path.exists(p):
        return None
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def load_section(root, section):
    d = section_dir(root, section)
    out = {}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            out[fn[:-5]] = json.load(io.open(os.path.join(d, fn), encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
    return out


def write_run_report(root, run_id, doc):
    d = section_dir(root, "runs")
    p = os.path.join(d, "%s.json" % run_id)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    return p
