#!/usr/bin/env python3
"""ASIP Stage 2.5D/E — Disabled Provider

No AI processing allowed. For safety-off mode.
"""

from .base import BaseProvider, ProviderConfig


class DisabledProvider(BaseProvider):
    """AI 处理完全禁用。"""

    def __init__(self, config=None):
        super().__init__(config or ProviderConfig("disabled"))

    def validate_config(self):
        return False, "AI processing is disabled"

    def process_binding(self, binding, budget):
        raise RuntimeError("AI processing disabled")

    def parse_response(self, raw):
        raise RuntimeError("AI processing disabled")

    def normalize_usage(self, raw_usage):
        return {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0}

    def healthcheck(self):
        return False, "disabled"

    def __repr__(self):
        return "DisabledProvider"
