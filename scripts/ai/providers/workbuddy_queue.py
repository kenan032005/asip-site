#!/usr/bin/env python3
"""ASIP Stage 2.5D/E — WorkBuddy Queue Provider

Default provider: handoff to WorkBuddy for local processing.
Never calls external APIs directly. Never falls back to paid providers.
"""

from .base import BaseProvider, ProviderConfig


class WorkBuddyQueueProvider(BaseProvider):
    """WorkBuddy Queue 交付模式。"""

    def __init__(self, config=None):
        super().__init__(config or ProviderConfig("workbuddy_queue"))

    def validate_config(self):
        return True, ""

    def process_binding(self, binding, budget):
        """WorkBuddy Queue 不直接处理，返回占位 result。"""
        return {
            "task_id": binding.get("task_id", ""),
            "schema_version": "1.0",
            "status": "pending",
            "provider": "workbuddy_queue",
            "model": "workbuddy_internal",
            "started_at": "",
            "completed_at": "",
            "result": {},
            "error": None,
            "usage": {"input_tokens": 0, "output_tokens": 0,
                      "estimated_cost_usd": 0},
        }

    def parse_response(self, raw):
        return raw

    def normalize_usage(self, raw_usage):
        return {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0}

    def healthcheck(self):
        return True, "workbuddy_queue"

    def __repr__(self):
        return "WorkBuddyQueueProvider"
