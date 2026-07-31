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
import time
import tempfile

from .contracts import validate_ai_task, SCHEMA_VERSION
from .identifiers import generate_ai_task_id, generate_ai_cache_key
from .exceptions import TaskValidationError, TaskStateError
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


def _ensure_ai_dirs(ai_root):
    """确保给定 ai_root 下的全部状态目录存在（用于模块级函数，不受实例 ai_root 限制）。"""
    for st in ("queue", "processing", "completed", "failed", "cache", "usage"):
        os.makedirs(os.path.join(ai_root, st), exist_ok=True)


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


def find_existing_task_by_cache_key(cache_key, ai_root=AI_ROOT):
    """按 completed -> processing -> queue -> failed -> cache 顺序查找同一 cache_key 的任务。

    这是「全状态幂等」的核心：任一状态目录中已存在同一 cache_key 的任务，
    都视为同一权威任务，不再重复入队。返回 (state, task_dict) 或 None。
    同一 task_id 在同一时刻只能有一个权威状态文件。
    """
    _ensure_ai_dirs(ai_root)
    order = ("completed", "processing", "queue", "failed", "cache")
    for state in order:
        d = os.path.join(ai_root, state)
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(d, fn), "r", encoding="utf-8") as f:
                    obj = json.load(f)
            except Exception:
                continue
            if obj.get("cache_key") == cache_key:
                return (state, obj)
    return None


# 状态目录名 -> 任务 status 的规范映射（目录叫 queue，任务 status 叫 queued）
_STATE_STATUS = {
    "queue": "queued",
    "processing": "processing",
    "completed": "completed",
    "failed": "failed",
    "cache": "cache",
}


def _status_for_state(state):
    return _STATE_STATUS.get(state, state)


def move_task(task_id, from_state, to_state, ai_root=AI_ROOT, updates=None,
              max_retries=5, retry_delay=0.2):
    """原子移动任务状态（为 2.5B 提前建立的最小公共工具，不实现 AI 执行器）。

    流程：读源 -> 校验 -> 写临时 -> os.replace 目标 -> 确认目标成功 -> 删除源。
    - Windows 文件锁时有限次数重试；
    - 失败则源文件保持不变（一致性优先）；
    - 移动后任务内 status 必须与 to_state 一致；
    - 不允许同一任务同时存在于 from_state 与 to_state 两端。
    返回移动后的任务 dict。
    """
    src = os.path.join(ai_root, from_state, "%s.json" % task_id)
    dst = os.path.join(ai_root, to_state, "%s.json" % task_id)
    if not os.path.exists(src):
        raise TaskStateError("source task not found: %s/%s" % (from_state, task_id))
    try:
        with open(src, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception as e:
        raise TaskStateError("failed to read source %s: %s" % (src, e))
    # 一致性校验：源 status 须与 from_state 对应的规范 status 一致
    # （目录名 queue 对应任务 status=queued；cache 为缓存态，不参与状态机）
    if from_state != "cache" and obj.get("status") != _status_for_state(from_state):
        raise TaskStateError(
            "source status %r != from_state %r (task_id=%s)"
            % (obj.get("status"), from_state, task_id)
        )
    new_obj = dict(obj)
    if updates:
        new_obj.update(updates)
    new_obj["status"] = _status_for_state(to_state)

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    last_err = None
    for _ in range(max_retries):
        try:
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dst), suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(new_obj, f, ensure_ascii=False, indent=2)
                os.replace(tmp, dst)
            finally:
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
            break
        except (OSError, PermissionError) as e:
            last_err = e
            time.sleep(retry_delay)
    else:
        raise TaskStateError("atomic write failed after %d attempts: %s" % (max_retries, last_err))

    if not os.path.exists(dst):
        raise TaskStateError("target not written; source left intact")

    # 确认目标写入成功后再删源；删源失败则回滚目标，保证不出现双份
    for _ in range(max_retries):
        try:
            os.remove(src)
            break
        except (OSError, PermissionError) as e:
            last_err = e
            time.sleep(retry_delay)
    else:
        try:
            os.remove(dst)
        except OSError:
            pass
        raise TaskStateError("failed to remove source after move: %s" % last_err)
    return new_obj


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

        cache_key = generate_ai_cache_key(
            task_type, input_ref, content_hash, prompt_version, output_schema_version
        )

        # 全状态幂等：任一状态目录已存在同一 cache_key -> 不重复创建
        found = find_existing_task_by_cache_key(cache_key, self.ai_root)
        if found is not None:
            state, existing = found
            if state == "failed":
                rc = int(existing.get("retry_count", 0))
                mr = int(existing.get("max_retries", 0))
                if rc < mr:
                    # 仍可重试：复用同一 task_id，状态改回 queued（重试计数 +1），不新建文件
                    return self._requeue_failed(existing)
                # 达到上限：返回既有档案，绝不创建第二个相同 task_id 文件
                return existing
            # completed / processing / queue / cache：直接返回既有任务，不重复入队
            return existing

        task_id = task.get("task_id") or generate_ai_task_id(
            task_type, input_ref, content_hash, prompt_version, output_schema_version
        )
        enriched = dict(task)
        enriched["task_id"] = task_id
        enriched["cache_key"] = cache_key
        enriched["status"] = "queued"
        # 即使请求了付费 Provider，队列阶段也不执行；保持请求声明但不调用
        enriched.setdefault("provider_requested", "workbuddy_queue")
        self._atomic_write(self._queue_path(task_id), enriched)
        return enriched

    def _requeue_failed(self, existing):
        """复用同一 task_id，将 failed 任务改回 queued（retry_count +1）。"""
        task_id = existing["task_id"]
        new_retry = int(existing.get("retry_count", 0)) + 1
        return move_task(
            task_id, "failed", "queue", ai_root=self.ai_root,
            updates={
                "status": "queued",
                "retry_count": new_retry,
                "cache_key": existing.get("cache_key"),
            },
        )

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
