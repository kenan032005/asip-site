"""ASIP Stage 2.5A — AI 任务 / 结果契约常量与校验（零依赖）。

不依赖任何外部 JSON Schema 库；校验逻辑自包含，便于测试与离线运行。
"""

import os

# 契约版本
SCHEMA_VERSION = "1.0"

# 预留任务类型（仅为契约，本阶段不真正处理）
TASK_TYPES = [
    "article_analysis",
    "source_comparison",
    "event_synthesis",
    "daily_security_brief",
    "trend_forecast",
    "disease_risk_analysis",
]

# 任务状态枚举
TASK_STATUSES = [
    "queued",
    "processing",
    "completed",
    "failed",
    "waiting_retry",
    "permanently_failed",
    "cancelled",
]

# 结果状态枚举
RESULT_STATUSES = [
    "success",
    "failed",
    "refused",
    "invalid_output",
]

# 优先级
PRIORITIES = ["low", "normal", "high", "critical"]

# Provider 名称
PROVIDER_NAMES = ["workbuddy_queue", "openai_api", "generic_api", "disabled"]

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schemas")


def load_json_schema(name):
    """加载 schemas/<name> 返回 dict；缺失返回 None（不抛错）。"""
    path = os.path.join(SCHEMA_DIR, name)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return __import__("json").load(f)


def validate_ai_task(task):
    """校验 AI 任务 dict。返回错误字符串列表，空列表表示通过。"""
    errors = []
    if not isinstance(task, dict):
        return ["task must be an object"]
    s = SCHEMA_VERSION

    def need(key, allowed=None, typ=None):
        v = task.get(key)
        if v is None:
            errors.append(f"missing field: {key}")
            return
        if typ and not isinstance(v, typ):
            errors.append(f"field {key} must be {typ.__name__}")
        if allowed and v not in allowed:
            errors.append(f"field {key}={v!r} not in {allowed}")

    need("task_id", typ=str)
    if task.get("task_id") and not (
        isinstance(task.get("task_id"), str)
        and task["task_id"].startswith("AIT_")
        and len(task["task_id"]) == 28
    ):
        errors.append("task_id format must be AIT_<24 hex>")
    need("schema_version", typ=str)
    if task.get("schema_version") and task["schema_version"] != s:
        errors.append(f"schema_version must be {s}")
    need("task_type", allowed=TASK_TYPES)
    need("status", allowed=TASK_STATUSES)
    need("priority", allowed=PRIORITIES)
    if "input_ref" in task and not isinstance(task["input_ref"], dict):
        errors.append("input_ref must be an object")
    need("content_hash", typ=str)
    need("prompt_version", typ=str)
    need("output_schema_version", typ=str)
    need("provider_requested", allowed=PROVIDER_NAMES)
    need("created_at", typ=str)
    need("retry_count", typ=int)
    need("max_retries", typ=int)
    if isinstance(task.get("retry_count"), int) and isinstance(task.get("max_retries"), int):
        if task["retry_count"] > task["max_retries"]:
            errors.append("retry_count must not exceed max_retries")
    return errors


def validate_ai_result(result):
    """校验 AI 结果 dict。返回错误字符串列表，空列表表示通过。"""
    errors = []
    if not isinstance(result, dict):
        return ["result must be an object"]
    need = lambda k, allowed=None, typ=None: (
        errors.append(f"missing field: {k}") if result.get(k) is None
        else (errors.append(f"field {k} must be {typ.__name__}") if (typ and not isinstance(result.get(k), typ)) else
              (errors.append(f"field {k}={result.get(k)!r} not in {allowed}") if (allowed and result.get(k) not in allowed) else None))
    )
    need("task_id", typ=str)
    need("schema_version", typ=str)
    need("status", allowed=RESULT_STATUSES)
    need("provider", allowed=PROVIDER_NAMES + ["none"])
    need("model", typ=str)
    err = result.get("error")
    if err is not None and not isinstance(err, dict):
        errors.append("error must be object or null")
    usage = result.get("usage")
    if usage is not None:
        if not isinstance(usage, dict):
            errors.append("usage must be object or null")
        else:
            for k in ("input_tokens", "output_tokens"):
                if k in usage and not isinstance(usage[k], int):
                    errors.append(f"usage.{k} must be int")
            if "estimated_cost_usd" in usage and not isinstance(usage["estimated_cost_usd"], (int, float)):
                errors.append("usage.estimated_cost_usd must be number")
    return errors


def new_ai_task(task_type, input_ref, content_hash, prompt_version,
                output_schema_version, provider_requested="workbuddy_queue",
                priority="normal", created_at=None, max_retries=2):
    """便捷构造一个通过契约校验的 AI 任务。task_id / cache_key 确定性生成。"""
    from .identifiers import generate_ai_task_id, generate_ai_cache_key
    from datetime import datetime, timezone
    if created_at is None:
        created_at = datetime.now(timezone.utc).isoformat()
    task = {
        "task_id": generate_ai_task_id(
            task_type, input_ref, content_hash, prompt_version, output_schema_version
        ),
        "schema_version": SCHEMA_VERSION,
        "task_type": task_type,
        "status": "queued",
        "priority": priority,
        "input_ref": input_ref if isinstance(input_ref, dict) else {},
        "content_hash": content_hash,
        "prompt_version": prompt_version,
        "output_schema_version": output_schema_version,
        "provider_requested": provider_requested,
        "created_at": created_at,
        "retry_count": 0,
        "max_retries": max_retries,
    }
    task["cache_key"] = generate_ai_cache_key(
        task_type, input_ref, content_hash, prompt_version, output_schema_version
    )
    return task
