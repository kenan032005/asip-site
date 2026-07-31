#!/usr/bin/env python3
"""ASIP Stage 2.5C-2A — AI Task to Prompt Binding

Binds AI Tasks to versioned Prompt Packages, extracts prompt variables
from input_ref, calls the secure renderer, and validates output schema.
"""

import json
import hashlib
import os

from .prompt_registry import (
    get_prompt_package, PromptRegistryError,
)
from .prompt_renderer import render_prompt, PromptRenderError
from .output_contracts import get_output_schema, OutputContractError
from .contracts import validate_ai_task

BINDING_VERSION = "1.0"

# ── Error codes ──
ERR = {
    "invalid_ai_task": "invalid_ai_task",
    "unknown_prompt_task_type": "unknown_prompt_task_type",
    "prompt_version_not_registered": "prompt_version_not_registered",
    "output_schema_version_mismatch": "output_schema_version_mismatch",
    "prompt_variables_missing": "prompt_variables_missing",
    "prompt_variables_invalid": "prompt_variables_invalid",
    "prompt_render_failed": "prompt_render_failed",
    "output_schema_binding_failed": "output_schema_binding_failed",
    "prompt_file_write_failed": "prompt_file_write_failed",
}


class BindingError(Exception):
    """Prompt 绑定失败。"""
    def __init__(self, code, task_id, detail=""):
        self.code = code
        self.task_id = task_id
        self.detail = detail
        msg = "[%s] task=%s: %s" % (code, task_id, detail)
        super().__init__(msg)


def _extract_prompt_variables(task):
    """从 task.input_ref 提取 Prompt 变量。

    支持两种模式：
    A. nested_prompt_variables: input_ref.prompt_variables 直接使用
    B. legacy_flat_allowlist: 从 input_ref 顶层按 required/optional 过滤
    """
    input_ref = task.get("input_ref") or {}
    pkg = get_prompt_package(task["task_type"], task.get("prompt_version"))
    required = set(pkg.get("required_variables", []))
    optional = set(pkg.get("optional_variables", []))
    all_vars = required | optional

    if "prompt_variables" in input_ref:
        # 新标准模式
        pv = input_ref["prompt_variables"]
        if not isinstance(pv, dict):
            raise BindingError(
                ERR["prompt_variables_invalid"], task["task_id"],
                "prompt_variables must be an object")
        variables = dict(pv)
        mode = "nested_prompt_variables"
    else:
        # 旧任务兼容模式
        variables = {}
        for k in all_vars:
            if k in input_ref:
                variables[k] = input_ref[k]
        mode = "legacy_flat_allowlist"

    # 验证 required 变量
    for rv in required:
        if rv not in variables:
            raise BindingError(
                ERR["prompt_variables_missing"], task["task_id"],
                "missing required variable: %s" % rv)

    return variables, mode


def bind_task_to_prompt(task):
    """将 AI Task 绑定到 Prompt Package。

    返回 Binding dict 或抛出 BindingError。
    """
    # 1. 校验 AI Task
    errs = validate_ai_task(task)
    if errs:
        raise BindingError(ERR["invalid_ai_task"], task.get("task_id", "?"),
                           "; ".join(errs))

    tid = task["task_id"]
    ttype = task["task_type"]
    pv = task.get("prompt_version")

    # 2. task_type 必须在 Registry 中
    try:
        pkg = get_prompt_package(ttype, pv)
    except PromptRegistryError as e:
        raise BindingError(ERR["prompt_version_not_registered"], tid, str(e))

    # 3. disabled 拒绝
    if pkg.get("status") == "disabled":
        raise BindingError(ERR["prompt_version_not_registered"], tid,
                           "prompt version is disabled")

    # 4. output_schema_version 必须与 Package 一致
    osv = task.get("output_schema_version")
    pkg_osv = pkg.get("output_schema_version")
    if osv and osv != pkg_osv:
        raise BindingError(
            ERR["output_schema_version_mismatch"], tid,
            "task=%s != pkg=%s" % (osv, pkg_osv))

    # 5. 提取 Prompt 变量
    variables, mapping_mode = _extract_prompt_variables(task)

    # 6. 调用 Renderer
    try:
        rendered = render_prompt(ttype, variables, version=pv)
    except PromptRenderError as e:
        raise BindingError(ERR["prompt_render_failed"], tid, str(e))

    # 7. 验证输出 Schema 可加载
    try:
        get_output_schema(ttype, prompt_version=pv,
                          output_schema_version=pkg_osv)
    except (OutputContractError, Exception) as e:
        raise BindingError(ERR["output_schema_binding_failed"], tid, str(e))

    # 8. 计算变量摘要（确定性，不含本机路径/时间/随机数）
    var_digest = _compute_variables_digest(variables)

    binding = {
        "binding_version": BINDING_VERSION,
        "task_id": tid,
        "task_type": ttype,
        "prompt_version": rendered["prompt_version"],
        "output_schema_version": rendered["output_schema_version"],
        "prompt_checksum": rendered["prompt_checksum"],
        "render_hash": rendered["render_hash"],
        "output_schema": pkg.get("output_schema", ""),
        "output_language": pkg.get("output_language", "zh-CN"),
        "legacy_safe_mode": rendered.get("legacy_safe_mode", False),
        "input_mapping_mode": mapping_mode,
        "prompt_variables_digest": var_digest,
        "system_text": rendered["system_text"],
        "user_text": rendered["user_text"],
    }
    return binding


def validate_task_prompt_binding(task):
    """快速校验 task 能否成功绑定（不返回绑定内容，仅校验）。"""
    bind_task_to_prompt(task)
    return True


def build_batch_prompt_files(tasks, batch_temp_dir):
    """为 batch 中所有任务生成 Prompt 文件。

    Args:
        tasks: list of task dicts
        batch_temp_dir: batch 临时目录

    Returns:
        (bindings: list, manifest_entries: list)

    Raises:
        BindingError: 任一任务绑定失败
    """
    prompts_dir = os.path.join(batch_temp_dir, "prompts")
    os.makedirs(prompts_dir, exist_ok=True)

    bindings = []
    manifest_entries = []

    for task in tasks:
        tid = task["task_id"]

        # 绑定
        binding = bind_task_to_prompt(task)

        # 安全文件名（仅 task_id）
        _validate_safe_filename(tid)
        prompt_filename = "prompts/%s.prompt.json" % tid
        prompt_path = os.path.join(batch_temp_dir, prompt_filename)

        # 写入
        try:
            os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
            with open(prompt_path, "w", encoding="utf-8") as f:
                json.dump(binding, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise BindingError(
                ERR["prompt_file_write_failed"], tid, str(e))

        bindings.append(binding)

        # manifest 条目（非敏感）
        entry = {
            "task_id": tid,
            "task_type": binding["task_type"],
            "prompt_version": binding["prompt_version"],
            "output_schema_version": binding["output_schema_version"],
            "prompt_checksum": binding["prompt_checksum"],
            "render_hash": binding["render_hash"],
            "prompt_variables_digest": binding["prompt_variables_digest"],
            "prompt_file": prompt_filename,
        }
        manifest_entries.append(entry)

    return bindings, manifest_entries


def _compute_variables_digest(variables):
    """计算 Prompt 变量的确定性 SHA-256 摘要。"""
    m = hashlib.sha256()
    for k in sorted(variables):
        m.update(k.encode("utf-8"))
        m.update(json.dumps(variables[k], ensure_ascii=False,
                            sort_keys=True).encode("utf-8"))
    return "sha256:" + m.hexdigest()


def _validate_safe_filename(tid):
    """确保 task_id 可用作安全文件名。"""
    if not tid or not isinstance(tid, str):
        raise BindingError("prompt_file_write_failed", "?",
                           "invalid task_id for filename")
    if ".." in tid or "/" in tid or "\\" in tid:
        raise BindingError("prompt_file_write_failed", tid,
                           "path traversal in task_id")
