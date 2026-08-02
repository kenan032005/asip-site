#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 — Provider 接口（同步结构化输出）。

Stage 2.5 的 BaseAIProvider 是异步队列式（submit_task/get_task_status/load_result）。
Stage 4 事件增强需要「同步、结构化」输出。此处定义 Stage4Provider 抽象，
仅做向后兼容扩展：不修改 Stage 2.5 任何接口，只新增 Stage 4 专用基类。
"""

from abc import ABC, abstractmethod


class Stage4ProviderError(Exception):
    """Provider 调用错误基类。"""


class ProviderTimeout(Stage4ProviderError):
    """模拟/真实超时。"""


class ProviderAPIError(Stage4ProviderError):
    """API 层错误（重试性）。"""


class ProviderTerminalError(Stage4ProviderError):
    """Terminal 错误（不可重试）。"""


class Stage4Provider(ABC):
    """Stage 4 同步 Provider 接口。

    约定：
    - generate_structured() 返回 dict，包含 raw_text / parsed / error / usage / raw_response_hash
    - 失败抛出 ProviderTimeout / ProviderAPIError（可重试）或 ProviderTerminalError（不可重试）
    """

    provider_name = "base"
    model_name = "base-model"

    def __init__(self, timeout=30, max_retries=2):
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def retry_policy(self):
        return {
            "max_retries": self.max_retries,
            "backoff_seconds": 1,
            "retryable": (ProviderTimeout, ProviderAPIError),
        }

    @abstractmethod
    def generate_structured(self, prompt_text):
        """输入渲染后的 prompt 文本，返回统一结果 dict。

        返回结构（统一）：
        {
          "ok": bool,
          "raw_text": str,            # 原始响应（mock 为确定性字符串）
          "parsed": dict | None,      # 解析后的 JSON 对象
          "error": {"code": str, "message": str} | None,
          "token_usage": {"input_tokens": int, "output_tokens": int, "estimated_cost_usd": float},
          "raw_response_hash": str,   # raw_text 的 SHA-256
        }
        """
        raise NotImplementedError

    def normalize_usage(self, raw_usage=None):
        """把 provider 原始 usage 归一化；默认返回零计数。"""
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
        }
