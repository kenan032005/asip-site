"""ASIP Stage 2.5A — AI 任务 / 结果契约常量与校验（零依赖）。

不依赖任何外部 JSON Schema 库；校验逻辑自包含，便于测试与离线运行。
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path

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

# 仓库根目录：scripts/ai/contracts.py -> parents[0]=scripts/ai, [1]=scripts, [2]=repo_root
REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "schemas"


def load_json_schema(name, required=False):
    """加载 schemas/<name> 返回 dict。

    required=True 且文件缺失时抛出 SchemaNotFoundError（指明缺失路径），
    绝不静默返回 None 后继续运行；任务提交 / 结果写入必须传 required=True。
    """
    path = SCHEMA_DIR / name
    if not path.exists():
        if required:
            from .exceptions import SchemaNotFoundError
            raise SchemaNotFoundError(name, str(path))
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
    """校验 AI 结果 dict（Stage 2.5A 强化契约）。返回错误字符串列表，空列表表示通过。

    强制字段：task_id / schema_version / status / provider / model /
    started_at / completed_at / result / error / usage。
    规则（对应规范六）：
    - schema_version 必须精确为 "1.0"；
    - task_id 必须符合 AIT_<24位十六进制>；
    - started_at / completed_at 必须为 ISO 时间，且 completed_at 不得早于 started_at；
    - status=success：result 必须为非空对象，error 必须为 null；
    - status=failed/refused/invalid_output：error 必须含 code 与 message；
    - usage 必须含 input_tokens / output_tokens / estimated_cost_usd，且均非负；
    - 不允许未知顶层字段。
    """
    errors = []
    if not isinstance(result, dict):
        return ["result must be an object"]

    ALLOWED = {
        "task_id", "schema_version", "status", "provider", "model",
        "started_at", "completed_at", "result", "error", "usage",
    }
    for k in result:
        if k not in ALLOWED:
            errors.append("unknown result field: %s" % k)

    REQUIRED = [
        "task_id", "schema_version", "status", "provider", "model",
        "started_at", "completed_at", "result", "error", "usage",
    ]
    for f in REQUIRED:
        # error 字段允许显式为 null（status=success 时必须为 null），
        # 因此对 error 只检查「键是否存在」，其余字段不允许为 None。
        if f == "error":
            if f not in result:
                errors.append("missing field: %s" % f)
        elif result.get(f) is None:
            errors.append("missing field: %s" % f)

    # task_id 格式
    tid = result.get("task_id")
    if tid is not None and not (isinstance(tid, str) and re.match(r"^AIT_[0-9a-f]{24}$", tid)):
        errors.append("task_id format must be AIT_<24 hex>")

    # schema_version 精确 1.0
    sv = result.get("schema_version")
    if sv is not None and sv != "1.0":
        errors.append("schema_version must be exactly 1.0")

    # provider / status 枚举
    if result.get("provider") not in PROVIDER_NAMES + ["none"]:
        errors.append("invalid provider: %r" % result.get("provider"))
    status = result.get("status")
    if status is not None and status not in RESULT_STATUSES:
        errors.append("invalid status: %r" % status)

    # 时间 ISO + completed_at >= started_at
    def _parse_iso(s):
        try:
            return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        except Exception:
            return None

    sa = _parse_iso(result["started_at"]) if result.get("started_at") else None
    ca = _parse_iso(result["completed_at"]) if result.get("completed_at") else None
    if result.get("started_at") and sa is None:
        errors.append("started_at is not a valid ISO datetime")
    if result.get("completed_at") and ca is None:
        errors.append("completed_at is not a valid ISO datetime")
    if sa and ca and ca < sa:
        errors.append("completed_at earlier than started_at")

    # error 结构
    err = result.get("error")
    if status in ("failed", "refused", "invalid_output"):
        if not isinstance(err, dict) or not err.get("code") or not err.get("message"):
            errors.append("error must contain code and message when status=%s" % status)
    if status == "success":
        if isinstance(err, dict):
            errors.append("error must be null when status=success")
        r = result.get("result")
        if not isinstance(r, dict) or len(r) == 0:
            errors.append("result must be a non-empty object when status=success")

    # usage 结构
    usage = result.get("usage")
    if isinstance(usage, dict):
        for k in ("input_tokens", "output_tokens"):
            v = usage.get(k)
            if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                errors.append("usage.%s must be a non-negative integer" % k)
        c = usage.get("estimated_cost_usd")
        if c is not None and (not isinstance(c, (int, float)) or isinstance(c, bool) or c < 0):
            errors.append("usage.estimated_cost_usd must be a non-negative number")
    elif usage is not None:
        errors.append("usage must be an object")

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
