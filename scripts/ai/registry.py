"""ASIP Stage 2.5A — Provider Registry（唯一入口）。

业务代码务必通过 get_provider() 获取 Provider，禁止直接实例化或调用任何
Hy3 / OpenAI / 中转 API。

安全要点（对应规范七、九、十一）：
- 未知 Provider 名称 -> ValueError（失败关闭）；
- 默认仅 workbuddy_queue；
- 付费 Provider（openai_api / generic_api）仅当「显式按名请求」且「已配置密钥」时才
  可被获取，且本阶段仍返回禁用实现（不联网）；缺密钥则 ProviderNotConfigured；
- allow_paid_fallback=false 时，任何代码路径都不会自动选择付费 Provider。
"""

from . import config as _config
from .provider import BaseAIProvider
from .workbuddy_queue_provider import WorkbuddyQueueProvider
from .disabled_provider import DisabledProvider
from .mock_provider import MockProvider
from .exceptions import ProviderNotConfigured

_REGISTRY = {}


def register_provider(name, cls):
    """注册一个 Provider 类。"""
    if not (isinstance(cls, type) and issubclass(cls, BaseAIProvider)):
        raise TypeError(f"{cls} 不是 BaseAIProvider 子类")
    _REGISTRY[name] = cls


# 内置注册
register_provider("workbuddy_queue", WorkbuddyQueueProvider)
register_provider("openai_api", DisabledProvider)
register_provider("generic_api", DisabledProvider)
register_provider("disabled", DisabledProvider)
# Stage 4：Mock Provider（离线确定性，不联网、免 Key，兼容 BaseAIProvider 接口）
register_provider("mock", MockProvider)
# Stage 4：Mock Provider（离线确定性，不联网、免 Key，兼容 BaseAIProvider 接口）
register_provider("mock", MockProvider)


def list_providers():
    """返回所有已注册 Provider 名称。"""
    return sorted(_REGISTRY.keys())


def resolve_provider_name(config=None):
    """解析当前应选用的 Provider 名称（永不自动选择付费 Provider）。"""
    cfg = config or _config.load_runtime_config()
    name = cfg.get("ai_provider")
    if name not in _config.VALID_PROVIDERS:
        raise ValueError(f"unknown ai_provider={name!r}")
    # 即使是付费名称，也只接受「显式配置」；自动回退永远不成立
    return name


def get_provider(name=None, config=None):
    """获取 Provider 实例（唯一入口）。

    name 省略时取 config.ai_provider（默认 workbuddy_queue）。
    显式选择付费 Provider 但缺密钥 -> ProviderNotConfigured（失败关闭）。
    """
    cfg = config or _config.load_runtime_config()
    name = name or cfg.get("ai_provider")

    if name not in _config.VALID_PROVIDERS:
        raise ValueError(
            f"unknown ai_provider={name!r}; allowed={sorted(_config.VALID_PROVIDERS)}"
        )

    if name == "workbuddy_queue":
        return WorkbuddyQueueProvider(cfg, name)

    if name == "mock":
        # Stage 4：离线确定性 Provider（不联网、免 Key）
        return MockProvider()

    if name in ("openai_api", "generic_api", "disabled"):
        provider = DisabledProvider(cfg, name)
        # 仅当显式选择付费 Provider 时才校验密钥；缺密钥 -> 失败关闭
        provider.validate_config()
        return provider

    raise ValueError(f"unhandled provider name: {name!r}")
