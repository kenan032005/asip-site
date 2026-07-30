"""ASIP Stage 2.5A — 运行配置加载与安全默认值。

关键约束（对应规范四、九、十一）：
- 默认 runtime_mode=workbuddy_local，ai_provider=workbuddy_queue；
- 默认 allow_paid_fallback=false、cloud_schedule_enabled=false、ai_processing_enabled=false；
- 缺失配置时采用上述安全默认值，绝不启动付费 API；
- 环境变量仅可覆盖「非敏感」配置；API Key 绝不写入 runtime.json；
- 未知 runtime 或 provider 一律报错；
- 检查付费 Provider 密钥只在「显式选择该付费 Provider」时发生，且缺失即失败关闭。
"""

import os
import json

# ── 安全默认值（缺失配置时的兜底）──
DEFAULT_RUNTIME = {
    "schema_version": "1.0",
    "runtime_mode": "workbuddy_local",
    "ai_provider": "workbuddy_queue",
    "ai_model": "hy3",
    "allow_paid_fallback": False,
    "cloud_schedule_enabled": False,
    "ai_processing_enabled": False,
}

# 受支持的枚举集合
VALID_RUNTIMES = {"workbuddy_local", "github_actions"}
VALID_PROVIDERS = {"workbuddy_queue", "openai_api", "generic_api", "disabled"}
PAID_PROVIDERS = {"openai_api", "generic_api"}

# 环境变量 -> 配置键（仅「非敏感」字段可被覆盖）
_ENV_MAP = {
    "ASIP_RUNTIME": "runtime_mode",
    "ASIP_AI_PROVIDER": "ai_provider",
    "ASIP_AI_MODEL": "ai_model",
    "ASIP_ALLOW_PAID_FALLBACK": ("allow_paid_fallback", bool),
    "ASIP_CLOUD_SCHEDULE_ENABLED": ("cloud_schedule_enabled", bool),
}

# 付费 Provider 对应的密钥环境变量（仅 env 读取，绝不入库）
_KEY_ENV = {
    "openai_api": "OPENAI_API_KEY",
    "generic_api": "GENERIC_AI_API_KEY",
}

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, "runtime.json")


def _coerce_bool(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def validate_runtime_config(cfg):
    """校验配置字典；非法 runtime / provider 抛 ValueError。"""
    if not isinstance(cfg, dict):
        raise ValueError("runtime config must be an object")
    mode = cfg.get("runtime_mode")
    if mode not in VALID_RUNTIMES:
        raise ValueError(
            f"unknown runtime_mode={mode!r}; allowed={sorted(VALID_RUNTIMES)}"
        )
    provider = cfg.get("ai_provider")
    if provider not in VALID_PROVIDERS:
        raise ValueError(
            f"unknown ai_provider={provider!r}; allowed={sorted(VALID_PROVIDERS)}"
        )
    # 安全兜底：绝不允许“默认开启付费回退”
    if cfg.get("allow_paid_fallback") is True and provider in PAID_PROVIDERS:
        # 仅是配置层面允许；真正调用仍受 get_provider 的显式选择 + 密钥检查约束
        pass
    return cfg


def load_runtime_config(path=None):
    """加载运行配置：文件 -> 安全默认值合并 -> 环境变量覆盖 -> 校验。

    返回 dict。任意异常（文件缺失/损坏/非法）都回退到安全默认值后再校验，
    保证 Stage 2 流水线在缺少 AI 配置时行为与之前完全一致。
    """
    cfg = dict(DEFAULT_RUNTIME)
    path = path or DEFAULT_CONFIG_PATH
    try:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                # 仅合并已知非敏感键，杜绝注入未知付费开关
                for k in DEFAULT_RUNTIME:
                    if k in data:
                        cfg[k] = data[k]
    except Exception:
        # 损坏或缺失 -> 使用安全默认值
        cfg = dict(DEFAULT_RUNTIME)

    # 环境变量覆盖（仅非敏感字段）
    for env, spec in _ENV_MAP.items():
        if env in os.environ:
            raw = os.environ[env]
            if isinstance(spec, tuple):
                key, typ = spec
                cfg[key] = _coerce_bool(raw) if typ is bool else raw
            else:
                cfg[spec] = raw

    validate_runtime_config(cfg)
    return cfg


def get_api_key(provider_name):
    """仅在「显式选择某付费 Provider」时调用；缺失返回 None（不抛错）。"""
    env = _KEY_ENV.get(provider_name)
    if not env:
        return None
    val = os.environ.get(env, "")
    return val or None


def provider_requires_key(provider_name):
    return provider_name in _KEY_ENV
