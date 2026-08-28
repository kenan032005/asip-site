#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 疾病基础字典加载与别名归一化（§五）。"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DISEASES_PATH = ROOT / "data" / "reference" / "diseases.json"

_cache = None


def load_diseases():
    """加载疾病字典。返回 {disease_id: disease}。"""
    global _cache
    if _cache is None:
        d = json.loads(DISEASES_PATH.read_text(encoding="utf-8"))
        _cache = {x["disease_id"]: x for x in d.get("diseases", [])}
    return _cache


def _alias_index():
    idx = {}
    for did, d in load_diseases().items():
        for a in d.get("aliases", []):
            idx[a.strip().lower()] = did
    return idx


def resolve_disease_id(raw):
    """把来源中的疾病名/别名归一化为 disease_id。未命中返回 None。"""
    if not raw:
        return None
    r = str(raw).strip().lower()
    idx = _alias_index()
    if r in idx:
        return idx[r]
    # 宽松包含匹配（如 "Cholera outbreak" → cholera）
    for key, did in idx.items():
        if key and len(key) >= 3 and key in r:
            return did
    return None


def disease_name(disease_id, lang="zh"):
    d = load_diseases().get(disease_id)
    if not d:
        return disease_id
    return d.get("name_zh" if lang == "zh" else "name_en", disease_id)
