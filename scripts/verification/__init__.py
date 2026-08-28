#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 事件自动核实核心 V1。"""

from .engine import verify_event, is_article_url
from .source_tiers import classify_tier
from .independence import count_independent, is_duplicate
from .conflicts import detect_conflicts

__all__ = [
    "verify_event", "is_article_url",
    "classify_tier", "count_independent", "is_duplicate", "detect_conflicts",
]
