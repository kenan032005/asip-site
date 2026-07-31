#!/usr/bin/env python3
"""ASIP Stage 2.5D/E — AI Provider Base Class

All providers implement this interface. Default: workbuddy_queue.
Supports: workbuddy_queue, generic_api, openai_api, disabled.
"""

from abc import ABC, abstractmethod


class ProviderConfig:
    """Provider configuration from environment."""
    def __init__(self, provider_type="workbuddy_queue"):
        self.provider_type = provider_type
        self.processing_enabled = False
        self.paid_fallback_allowed = False

    @classmethod
    def from_env(cls, env=None):
        import os
        e = env or os.environ
        cfg = cls(provider_type=e.get("ASIP_AI_PROVIDER", "workbuddy_queue"))
        cfg.processing_enabled = e.get(
            "ASIP_AI_PROCESSING_ENABLED", "false").lower() == "true"
        cfg.paid_fallback_allowed = e.get(
            "ALLOW_PAID_FALLBACK", "false").lower() == "true"
        return cfg


class BudgetLimit:
    """Budget tracking and meltdown control."""
    def __init__(self, max_tasks=0, max_tokens=0, max_cost_usd=0,
                 max_retries=1):
        self.max_tasks = max_tasks
        self.max_tokens = max_tokens
        self.max_cost_usd = max_cost_usd
        self.max_retries = max_retries
        self.completed_tasks = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0

    @classmethod
    def from_env(cls, env=None):
        import os
        e = env or os.environ
        return cls(
            max_tasks=int(e.get("ASIP_AI_MAX_TASKS_PER_RUN", "0")),
            max_tokens=int(e.get("ASIP_AI_MAX_TOTAL_TOKENS_PER_RUN", "0")),
            max_cost_usd=float(e.get("ASIP_AI_MAX_ESTIMATED_COST_USD", "0")),
            max_retries=int(e.get("ASIP_AI_MAX_RETRIES_PER_TASK", "1")),
        )

    def can_process(self):
        if self.max_tasks <= 0:
            return False, "max_tasks_per_run is 0"
        if self.completed_tasks >= self.max_tasks:
            return False, "max_tasks_per_run reached"
        if self.max_tokens > 0 and (
                self.total_input_tokens + self.total_output_tokens
                >= self.max_tokens):
            return False, "max_total_tokens reached"
        if self.max_cost_usd > 0 and self.total_cost_usd >= self.max_cost_usd:
            return False, "max_cost exceeded"
        return True, ""

    def record(self, usage):
        self.completed_tasks += 1
        self.total_input_tokens += usage.get("input_tokens", 0)
        self.total_output_tokens += usage.get("output_tokens", 0)
        self.total_cost_usd += usage.get("estimated_cost_usd", 0)


class BaseProvider(ABC):
    """Abstract AI Provider."""

    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    def validate_config(self):
        """验证配置合法。返回 (True, '') 或 (False, error_msg)。"""
        ...

    @abstractmethod
    def process_binding(self, binding, budget: BudgetLimit):
        """处理一个 Prompt Binding，返回标准化 AI Result dict。

        binding: task_prompt_binding.py 的 bind_task_to_prompt 输出
        budget: BudgetLimit 实例（用于累计用量）
        """
        ...

    @abstractmethod
    def parse_response(self, raw):
        """解析原始 API 响应为标准化 AI Result。"""
        ...

    @abstractmethod
    def normalize_usage(self, raw_usage):
        """标准化 API 用量为 {input_tokens, output_tokens, estimated_cost_usd}。"""
        ...

    def healthcheck(self):
        """快速可用性检查。返回 (True, '') 或 (False, reason)。"""
        return self.validate_config()
