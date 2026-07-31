"""ASIP Stage 2.5A — AI Provider 抽象与任务契约包。

统一入口：
- get_provider(name=None, config=None) -> 获取当前/指定 Provider（业务代码只经此入口）
- load_runtime_config(path=None) -> 运行配置（含安全默认值）
- new_ai_task(...) / validate_ai_task(...) / validate_ai_result(...) -> 契约工具
- generate_ai_task_id / generate_ai_cache_key -> 确定性幂等标识

本包在 Stage 2.5A 不调用任何 AI 模型、不访问任何外部网络。
"""

from .exceptions import (
    AIContractError,
    ProviderError,
    ProviderNotConfigured,
    TaskValidationError,
)
from .contracts import (
    SCHEMA_VERSION,
    TASK_TYPES,
    TASK_STATUSES,
    RESULT_STATUSES,
    PRIORITIES,
    PROVIDER_NAMES,
    validate_ai_task,
    validate_ai_result,
    new_ai_task,
    load_json_schema,
)
from .identifiers import generate_ai_task_id, generate_ai_cache_key
from .config import (
    DEFAULT_RUNTIME,
    VALID_RUNTIMES,
    VALID_PROVIDERS,
    PAID_PROVIDERS,
    load_runtime_config,
    validate_runtime_config,
    get_api_key,
)
from .provider import BaseAIProvider
from .registry import (
    get_provider,
    list_providers,
    register_provider,
    resolve_provider_name,
)
from .workbuddy_queue_provider import WorkbuddyQueueProvider, count_queued, count_failed
from .disabled_provider import DisabledProvider

__all__ = [
    "AIContractError",
    "ProviderError",
    "ProviderNotConfigured",
    "TaskValidationError",
    "SCHEMA_VERSION",
    "TASK_TYPES",
    "TASK_STATUSES",
    "RESULT_STATUSES",
    "PRIORITIES",
    "PROVIDER_NAMES",
    "validate_ai_task",
    "validate_ai_result",
    "new_ai_task",
    "load_json_schema",
    "generate_ai_task_id",
    "generate_ai_cache_key",
    "DEFAULT_RUNTIME",
    "VALID_RUNTIMES",
    "VALID_PROVIDERS",
    "PAID_PROVIDERS",
    "load_runtime_config",
    "validate_runtime_config",
    "get_api_key",
    "BaseAIProvider",
    "get_provider",
    "list_providers",
    "register_provider",
    "resolve_provider_name",
    "WorkbuddyQueueProvider",
    "DisabledProvider",
    "count_queued",
    "count_failed",
]
