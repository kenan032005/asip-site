#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 传染病来源注册表加载与来源评估（§七/§八/§十三）。

官方源优先：WHO DON / WHO AFRO / Africa CDC / 国家卫生部 = Tier A；
UNICEF / OCHA / 其他 UN = Tier B；国际媒体 = 仅 supplementary/discovery；
NewsNow 类聚合 = 仅 lead discovery。
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "data" / "disease_sources.json"

_cache = None


def load_registry():
    global _cache
    if _cache is None:
        d = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        _cache = {s["source_id"]: s for s in d.get("sources", [])}
    return _cache


def source_meta(source_id):
    return load_registry().get(source_id)


def is_lead_only(source_id):
    s = source_meta(source_id)
    return bool(s and s.get("status") == "lead_only")


def disease_scope_of(source_id):
    s = source_meta(source_id)
    return set((s or {}).get("disease_scope") or [])
