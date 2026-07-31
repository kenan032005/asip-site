#!/usr/bin/env python3
"""ASIP Stage 2.5C-1 — Secure Prompt Renderer

Deterministic, safe prompt template rendering. source_text is inserted
as JSON-encoded data block, never parsed as template syntax.
"""

import os
import json
import uuid
import hashlib
import re
from .prompt_registry import get_prompt_package, PromptRegistryError

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
PROMPTS_DIR = os.path.join(REPO_ROOT, "prompts")

_MAX_SOURCE_TEXT_LENGTH = 100000

_VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\|[^}]*)?\}\}")
_UNRESOLVED_PATTERN = _VARIABLE_PATTERN


class PromptRenderError(Exception):
    """Prompt 渲染错误。"""


def _validate_variable_name(name):
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise PromptRenderError("invalid variable name: %s" % name)


def _json_encode_value(value):
    """将变量值 JSON 编码后插入模板。source_text 使用此方法。"""
    return json.dumps(value, ensure_ascii=False)


def _check_no_traversal(base_dir, relative_path):
    """确保路径不包含 .. 遍历且不超出 base_dir。"""
    if ".." in relative_path:
        raise PromptRenderError("path traversal detected")
    full = os.path.normpath(os.path.join(base_dir, relative_path))
    base_norm = os.path.normpath(base_dir)
    if not full.startswith(base_norm + os.sep) and full != base_norm:
        raise PromptRenderError("path outside prompt directory")


def render_prompt(task_type, variables, version=None):
    """安全渲染 Prompt。

    Args:
        task_type: prompt task_type
        variables: dict of variable names to values
        version: optional version string

    Returns:
        dict with prompt_id, task_type, prompt_version, output_schema_version,
        prompt_checksum, render_hash, system_text, user_text
    """
    pkg = get_prompt_package(task_type, version)

    # 验证 required variables
    required = pkg.get("required_variables", [])
    optional = pkg.get("optional_variables", [])
    allowed = set(required) | set(optional)

    for rv in required:
        if rv not in variables:
            raise PromptRenderError("missing required variable: %s" % rv)

    # 拒绝未知变量
    for var_name in variables:
        _validate_variable_name(var_name)
        if var_name not in allowed:
            raise PromptRenderError("unknown variable: %s" % var_name)

    # 类型和长度检查
    for var_name, value in variables.items():
        if isinstance(value, str) and var_name == "source_text":
            if len(value) > _MAX_SOURCE_TEXT_LENGTH:
                raise PromptRenderError(
                    "source_text exceeds max length of %d" % _MAX_SOURCE_TEXT_LENGTH)

    ver_dir = os.path.join(PROMPTS_DIR, task_type, pkg["version"])

    # 读取模板
    st_path = os.path.join(ver_dir, pkg["system_template"])
    ut_path = os.path.join(ver_dir, pkg["user_template"])
    _check_no_traversal(ver_dir, pkg["system_template"])
    _check_no_traversal(ver_dir, pkg["user_template"])

    with open(st_path, "r", encoding="utf-8") as f:
        system_tpl = f.read()
    with open(ut_path, "r", encoding="utf-8") as f:
        user_tpl = f.read()

    # 渲染：source_text 先作为 JSON 编码数据块插入，使用唯一占位符避免被二次替换
    def render(template):
        """两遍渲染：先插 source_text（JSON），再插其他变量。"""
        result = template
        # Pass 1: source_text as JSON data block (unique placeholder)
        source_placeholder = "{{ source_text }}"
        encoded = _json_encode_value(variables.get("source_text", ""))
        token = "__SOURCE_TEXT_TOKEN_" + uuid.uuid4().hex[:8] + "__"
        for sp in [source_placeholder, "{{source_text}}"]:
            result = result.replace(sp, token)
        # Pass 2: other variables
        for var_name, value in variables.items():
            if var_name == "source_text":
                continue
            for fmt in ["{{ %s }}" % var_name, "{{%s}}" % var_name]:
                if isinstance(value, (list, dict)):
                    result = result.replace(fmt, _json_encode_value(value))
                else:
                    result = result.replace(fmt, str(value))
        # Pass 3: replace source_text token
        result = result.replace(token, encoded)
        return result

    system_text = render(system_tpl)
    user_text = render(user_tpl)

    # 检查未解析的占位符（跳过 JSON 代码块内的模式）
    def _check_unresolved(text):
        # 移除 JSON 代码块
        cleaned = re.sub(r'```json\s*.*?```', '', text, flags=re.DOTALL)
        unresolved = _UNRESOLVED_PATTERN.findall(cleaned)
        if unresolved:
            raise PromptRenderError("unresolved placeholders: %s" % unresolved[:5])

    _check_unresolved(system_text)
    _check_unresolved(user_text)

    # 计算 render_hash（确定性）
    rh = hashlib.sha256()
    rh.update(task_type.encode("utf-8"))
    rh.update((version or pkg["version"]).encode("utf-8"))
    rh.update(system_text.encode("utf-8"))
    rh.update(user_text.encode("utf-8"))
    render_hash = "sha256:" + rh.hexdigest()

    return {
        "prompt_id": pkg["prompt_id"],
        "task_type": pkg["task_type"],
        "prompt_version": pkg["version"],
        "output_schema_version": pkg.get("output_schema_version", "1.0"),
        "prompt_checksum": pkg["checksum"],
        "render_hash": render_hash,
        "system_text": system_text,
        "user_text": user_text,
    }
