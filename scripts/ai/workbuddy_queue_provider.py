"""ASIP Stage 2.5A — WorkBuddy Queue Provider（当前唯一启用 Provider）。

职责边界（对应规范八）：
1. 校验 AI Task 契约；
2. 生成稳定 task_id / cache_key；
3. 原子写入 data/ai/queue（绝不整体写入 data/）；
4. 相同 cache_key 不重复创建任务（幂等）；
5. 返回 queued 状态；
6. 不直接调用 Hy3；
7. 不假装已完成 AI 处理（结果需由 2.5B 的执行器产生）。

这是「任务交接层」：WorkBuddy 后续自动任务读取队列 -> 用 Hy3 处理 -> 写入 completed。
"""

import os
import json
import tempfile

from .contracts import validate_ai_task, SCHEMA_VERSION
from .identifiers import generate_ai_task_id, generate_ai_cache_key
from .exceptions import TaskValidationError
from .provider import BaseAIProvider

# data/ai 位于仓库根目录（scripts/ai -> scripts -> repo_root）
AI_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "ai",
)
QUEUE_DIR = os.path.join(AI_ROOT, "queue")
PROCESSING_DIR = os.path.join(AI_ROOT, "processing")
COMPLETED_DIR = os.path.join(AI_ROOT, "completed")
FAILED_DIR = os.path.join(AI_ROOT, "failed")
CACHE_DIR = os.path.join(AI_ROOT, "cache")
USAGE_DIR = os.path.join(AI_ROOT, "usage")


def _ensure_dirs():
    for d in (AI_ROOT, QUEUE_DIR, PROCESSING_DIR, COMPLETED_DIR, FAILED_DIR, CACHE_DIR, USAGE_DIR):
        os.makedirs(d, exist_ok=True)


def _path_for(task_id):
    return os.path.join(QUEUE_DIR, f"{task_id}.json")


def count_queued():
    if not os.path.isdir(QUEUE_DIR):
        return 0
    return sum(1 for f in os.listdir(QUEUE_DIR) if f.endswith(".json"))


def count_failed():
    if not os.path.isdir(FAILED_DIR):
        return 0
    return sum(1 for f in os.listdir(FAILED_DIR) if f.endswith(".json"))


class WorkbuddyQueueProvider(BaseAIProvider):
    name = "workbuddy_queue"

    def __init__(self, config=None, name="workbuddy_queue", ai_root=None):
        super().__init__(config or {}, name)
        self.ai_root = ai_root or AI_ROOT
        self._dirs = {
            "queue": os.path.join(self.ai_root, "queue"),
            "processing": os.path.join(self.ai_root, "processing"),
            "completed": os.path.join(self.ai_root, "completed"),
            "failed": os.path.join(self.ai_root, "failed"),
            "cache": os.path.join(self.ai_root, "cache"),
            "usage": os.path.join(self.ai_root, "usage"),
        }

    # ── 内部工具 ──
    def _ensure(self):
        for d in self._dirs.values():
            os.makedirs(d, exist_ok=True)

    def _queue_path(self, task_id):
        return os.path.join(self._dirs["queue"], f"{task_id}.json")

    def _atomic_write(self, path, obj):
        """先写临时文件再 os.replace，保证原子性；不触发任何网络。"""
        self._ensure()
        d = os.path.dirname(path)
        fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass

    # ── 接口实现 ──
    def validate_config(self):
        # 队列 Provider 不需要任何外部密钥或网络配置
        return []

    def submit_task(self, task):
        errors = validate_ai_task(task)
        if errors:
            raise TaskValidationError(errors)

        task_type = task["task_type"]
        input_ref = task.get("input_ref") or {}
        content_hash = task.get("content_hash")
        prompt_version = task.get("prompt_version")
        output_schema_version = task.get("output_schema_version")

        task_id = task.get("task_id") or generate_ai_task_id(
            task_type, input_ref, content_hash, prompt_version, output_schema_version
        )
        cache_key = generate_ai_cache_key(
            task_type, input_ref, content_hash, prompt_version, output_schema_version
        )

        # 幂等：相同 cache_key 已存在 -> 不重复入队，返回既有任务
        existing = self._find_by_cache_key(cache_key)
        if existing is not None:
            return existing

        enriched = dict(task)
        enriched["task_id"] = task_id
        enriched["cache_key"] = cache_key
        enriched["status"] = "queued"
        # 即使请求了付费 Provider，队列阶段也不执行；保持请求声明但不调用
        enriched.setdefault("provider_requested", "workbuddy_queue")
        self._atomic_write(self._queue_path(task_id), enriched)
        return enriched

    def _find_by_cache_key(self, cache_key):
        if not os.path.isdir(self._dirs["queue"]):
            return None
        for fn in os.listdir(self._dirs["queue"]):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(self._dirs["queue"], fn), "r", encoding="utf-8") as f:
                    obj = json.load(f)
            except Exception:
                continue
            if obj.get("cache_key") == cache_key:
                return obj
        return None

    def get_task_status(self, task_id):
        for name, d in (
            ("completed", self._dirs["completed"]),
            ("failed", self._dirs["failed"]),
            ("processing", self._dirs["processing"]),
            ("queued", self._dirs["queue"]),
        ):
            p = os.path.join(d, f"{task_id}.json")
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        return json.load(f).get("status", name)
                except Exception:
                    return name
        return "unknown"

    def load_result(self, task_id):
        p = os.path.join(self._dirs["completed"], f"{task_id}.json")
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def health_check(self):
        self._ensure()
        return {
            "status": "ok",
            "provider": self.name,
            "mode": "queue_only",
            "external_network": False,  # 队列层绝不发起外部网络请求
            "ai_processing_enabled": bool(self.config.get("ai_processing_enabled", False)),
        }
