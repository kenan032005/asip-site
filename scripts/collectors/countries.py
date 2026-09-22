#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""countries.py —— C1C：国家配置注册表（替代 chad/niger 硬编码）。

背景：
  采集主控 `stage3_collect_v2.py` 原先把「乍得/尼日尔」写死在 5 处
  （cfg_key 解析、decision→中文名、ISO2、国家清单×2），因此新增国别的直接来源
  即使配置正确也永远采不到。本模块把这些映射改为**由 config/countries/*.json
  自动派生**，使扩源在国别维度真正生效，且不改变任何既有判定语义。

约定（config/countries/<key>.json）：
  country     中文国名（与 sources.json 的 country_scope 一致）
  country_en  英文国名（decision 值即其小写）
  iso2        ISO-3166 alpha-2（写入 canonical event 的 country_code）
  keywords / locations / country_exclusions / source_languages …
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG_DIR = os.path.join(ROOT, "config", "countries")

_CACHE = {}


def load_all(force=False):
    """返回 {cfg_key: cfg}。"""
    global _CACHE
    if _CACHE and not force:
        return _CACHE
    out = {}
    if os.path.isdir(CFG_DIR):
        for fn in sorted(os.listdir(CFG_DIR)):
            if not fn.endswith(".json"):
                continue
            key = fn[:-5]
            try:
                with open(os.path.join(CFG_DIR, fn), "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                continue
            cfg.setdefault("cfg_key", key)
            out[key] = cfg
    _CACHE = out
    return out


def key_for(country_cn):
    """中文国名 → cfg_key（找不到返回 None，绝不猜）。"""
    for k, cfg in load_all().items():
        if cfg.get("country") == country_cn:
            return k
    return None


def cn_for_decision(decision):
    """identify_country 的 decision → 中文国名。

    "regional" 保留为区域（不做单国归属）；其余按 country_en 小写精确匹配。
    """
    if not decision:
        return None
    d = str(decision).strip().lower()
    if d in ("regional", "unclear", "exclude"):
        return None
    for cfg in load_all().values():
        if str(cfg.get("country_en", "")).lower() == d:
            return cfg.get("country")
    return None


def iso2_for(country_cn):
    """中文国名 → ISO2（缺失时返回空串，由调用方决定如何降级）。"""
    k = key_for(country_cn)
    if k:
        return str(load_all()[k].get("iso2") or "")
    return ""


def configured_countries():
    """全部已配置国家的中文名（顺序稳定）。"""
    return [cfg.get("country") for cfg in load_all().values() if cfg.get("country")]
