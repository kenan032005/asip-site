"""ASIP Stage 2.5A — 禁用 / 占位 Provider（openai_api / generic_api / disabled）。

本阶段硬性约束（对应规范九、十一）：
- openai_api / generic_api 不得真正发出任何网络请求；
- 未配置（无密钥）且被显式选择时，必须失败关闭（ProviderNotConfigured）；
- disabled 模式只允许任务留在队列或暂停；
- 绝不安装 OpenAI SDK，绝不 import openai；
- 任何代码都不允许实现「Hy3 失败 -> 自动调用 OpenAI」的回退。
"""

from .provider import BaseAIProvider
from .exceptions import ProviderNotConfigured, ProviderError
from . import config as _config


class DisabledProvider(BaseAIProvider):
    """未来付费 / 禁用模式的占位实现：不执行、不联网、缺密钥即失败关闭。"""

    def __init__(self, runtime_config=None, name="disabled"):
        super().__init__(runtime_config or {}, name)
        self.reason = "provider disabled in Stage 2.5A; not implemented / not enabled"

    def validate_config(self):
        """若显式选择付费 Provider 但缺少密钥 -> 失败关闭。"""
        if self.name in _config.PAID_PROVIDERS:
            key = _config.get_api_key(self.name)
            if not key:
                raise ProviderNotConfigured(
                    f"{self.name} requires API key ({_config._KEY_ENV.get(self.name)}) "
                    f"but none is configured; failing closed."
                )
        return []

    def submit_task(self, task):
        raise ProviderError(
            f"Provider {self.name} cannot process tasks in Stage 2.5A: {self.reason}"
        )

    def get_task_status(self, task_id):
        return "unknown"

    def load_result(self, task_id):
        return None

    def health_check(self):
        enabled = self.name in _config.PAID_PROVIDERS and bool(
            _config.get_api_key(self.name)
        )
        return {
            "status": "disabled",
            "provider": self.name,
            "external_network": False,
            "key_configured": enabled,
            "note": self.reason,
        }
