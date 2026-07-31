#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 2.5C-1 — Prompt Registry

Loads and validates versioned prompt packages from prompts/ directory.
Resolves active/deprecated/disabled versions per registry.json.
"""

import os
import json
import hashlib
from pathlib import Path

from .schema_validation import validate_against_schema

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
PROMPTS_DIR = os.path.join(REPO_ROOT, "prompts")
REGISTRY_PATH = os.path.join(PROMPTS_DIR, "registry.json")
PACKAGE_SCHEMA_PATH = os.path.join(REPO_ROOT, "schemas",
                                    "prompt_package.schema.json")
SCHEMAS_OUTPUT_DIR = os.path.join(REPO_ROOT, "schemas", "ai_outputs")
DEFAULT_SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"


class PromptRegistryError(Exception):
    """Prompt Registry 运行时错误。"""


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_confined_path(base_dir, relative_path, allowed_root,
                          must_exist=True):
    """安全路径解析：拒绝绝对路径、盘符、UNC、..、符号链接逃逸。

    Returns resolved absolute Path or raises PromptRegistryError.
    """
    if not relative_path or not isinstance(relative_path, str):
        raise PromptRegistryError("empty or invalid path")
    if os.path.isabs(relative_path):
        raise PromptRegistryError("absolute path not allowed")
    # Windows drive letter
    if len(relative_path) >= 2 and relative_path[1] == ":":
        raise PromptRegistryError("drive letter path not allowed")
    # UNC
    if relative_path.startswith("\\\\") or relative_path.startswith("//"):
        raise PromptRegistryError("UNC path not allowed")
    # ..
    parts = Path(relative_path).parts
    if ".." in parts:
        raise PromptRegistryError("path traversal detected: ..")
    # resolve
    base = Path(base_dir).resolve()
    full = (base / relative_path).resolve()
    allowed = Path(allowed_root).resolve()
    if not str(full).startswith(str(allowed) + os.sep) and str(full) != str(allowed):
        raise PromptRegistryError("path outside allowed root")
    if must_exist and not full.exists():
        raise PromptRegistryError("file not found")
    return full


def _validate_package(pkg, task_type, version_dir, strict_schema=True,
                      _output_schema_root=None):
    """验证 package.json 符合契约（含 Schema 校验）。

    _output_schema_root: override for testing (default: SCHEMAS_OUTPUT_DIR)."""
    errors = []
    # 使用 prompt_package.schema.json 校验（仅当 strict_schema）
    if strict_schema and os.path.exists(PACKAGE_SCHEMA_PATH):
        pkg_schema = _load_json(PACKAGE_SCHEMA_PATH)
        schema_errs = validate_against_schema(pkg, pkg_schema)
        errors.extend(schema_errs)

    # prompt_id == task_type
    if pkg.get("prompt_id") != pkg.get("task_type"):
        errors.append("prompt_id must equal task_type")
    if pkg.get("task_type") != task_type:
        errors.append("task_type mismatch")
    # version matches directory
    if pkg.get("version") != os.path.basename(version_dir):
        errors.append("version must match directory name")
    # status enum
    if pkg.get("status") not in ("draft", "active", "deprecated", "disabled"):
        errors.append("invalid status: %s" % pkg.get("status"))
    # required_variables: all must be strings
    rv = pkg.get("required_variables") or []
    for i, v in enumerate(rv):
        if not isinstance(v, str):
            errors.append("required_variables[%d]: must be string, got %s" %
                          (i, type(v).__name__))
    ov = pkg.get("optional_variables") or []
    for i, v in enumerate(ov):
        if not isinstance(v, str):
            errors.append("optional_variables[%d]: must be string" % i)
    # untrusted_variables must be subset of required+optional
    ut = pkg.get("untrusted_variables") or []
    allowed_vars = set(rv) | set(ov)
    for i, v in enumerate(ut):
        if not isinstance(v, str):
            errors.append("untrusted_variables[%d]: must be string" % i)
        elif v not in allowed_vars:
            errors.append(
                "untrusted_variables[%d]: '%s' not in required/optional" % (i, v))
    # templates exist (safe path check — allowed_root=version_dir)
    st = pkg.get("system_template")
    ut_tmpl = pkg.get("user_template")
    if st:
        try:
            resolve_confined_path(version_dir, st, version_dir, must_exist=True)
        except PromptRegistryError as e:
            errors.append("system_template: %s" % e)
    if ut_tmpl:
        try:
            resolve_confined_path(version_dir, ut_tmpl, version_dir, must_exist=True)
        except PromptRegistryError as e:
            errors.append("user_template: %s" % e)
    # output schema exists (safe path — allowed_root=schemas/ai_outputs/)
    os_path = pkg.get("output_schema")
    if os_path:
        schema_root = _output_schema_root or SCHEMAS_OUTPUT_DIR
        try:
            resolve_confined_path(REPO_ROOT, os_path,
                                  schema_root, must_exist=True)
        except PromptRegistryError as e:
            errors.append("output_schema: %s" % e)
    # required_variables unique
    rv = pkg.get("required_variables") or []
    if len(set(rv)) != len(rv):
        errors.append("required_variables must be unique")
    ov = pkg.get("optional_variables") or []
    if len(set(ov)) != len(ov):
        errors.append("optional_variables must be unique")
    overlap = set(rv) & set(ov)
    if overlap:
        errors.append("variables overlap: %s" % overlap)
    # checksum format
    cs = pkg.get("checksum", "")
    if not cs.startswith("sha256:") or len(cs) != 71:
        errors.append("invalid checksum format")
    return errors


def compute_checksum(pkg, task_type, version_dir):
    """计算 package 的确定性 SHA-256 checksum。"""
    import re
    pkg_meta = {k: v for k, v in sorted(pkg.items()) if k != "checksum"}
    m = hashlib.sha256()
    for k in sorted(pkg_meta):
        m.update(k.encode("utf-8"))
        m.update(json.dumps(pkg_meta[k], ensure_ascii=False,
                            sort_keys=True).encode("utf-8"))

    # system.md (安全路径解析)
    st = pkg.get("system_template")
    if st:
        st_path = resolve_confined_path(version_dir, st, version_dir, must_exist=True)
        with open(str(st_path), "r", encoding="utf-8") as f:
            m.update(f.read().encode("utf-8"))
    # user.md
    ut = pkg.get("user_template")
    if ut:
        ut_path = resolve_confined_path(version_dir, ut, version_dir, must_exist=True)
        with open(str(ut_path), "r", encoding="utf-8") as f:
            m.update(f.read().encode("utf-8"))
    # output schema (normalized) — must be under schemas/ai_outputs/
    os_path = pkg.get("output_schema")
    if os_path:
        schema_path = resolve_confined_path(REPO_ROOT, os_path,
                                            SCHEMAS_OUTPUT_DIR, must_exist=True)
        with open(str(schema_path), "r", encoding="utf-8") as f:
            sc = json.load(f)
        m.update(json.dumps(sc, ensure_ascii=False,
                            sort_keys=True).encode("utf-8"))
    return "sha256:" + m.hexdigest()


def validate_version(tid, version="1.0.0", strict_schema=True):
    """校验指定版本的 prompt package 完整性（包括 checksum）。"""
    reg = load_registry()
    rt = reg.get("task_types", {}).get(tid)
    if not rt:
        raise PromptRegistryError("unknown task_type: %s" % tid)
    if version not in rt.get("versions", []):
        raise PromptRegistryError("version %s not registered for %s" % (version, tid))

    ver_dir = os.path.join(PROMPTS_DIR, tid, version)
    pkg_path = os.path.join(ver_dir, "package.json")
    if not os.path.exists(pkg_path):
        raise PromptRegistryError("package.json not found: %s" % pkg_path)

    pkg = _load_json(pkg_path)
    errors = _validate_package(pkg, tid, ver_dir, strict_schema=strict_schema)
    if errors:
        raise PromptRegistryError("package validation failed: %s" % "; ".join(errors))

    actual_cs = compute_checksum(pkg, tid, ver_dir)
    expected_cs = pkg.get("checksum", "")
    if actual_cs != expected_cs:
        raise PromptRegistryError(
            "checksum mismatch: computed=%s expected=%s" % (actual_cs, expected_cs))
    return pkg


def load_registry():
    """加载 prompts/registry.json。"""
    if not os.path.exists(REGISTRY_PATH):
        raise PromptRegistryError("registry.json not found")
    return _load_json(REGISTRY_PATH)


def get_prompt_package(task_type, version=None):
    """根据 task_type 和可选 version 解析 prompt package。

    - version=None: 加载 active_version
    - deprecated: 可加载但记录 deprecation
    - disabled: 拒绝
    - 未知 task_type 或 version: 失败
    """
    reg = load_registry()
    rt = reg.get("task_types", {}).get(task_type)
    if not rt:
        raise PromptRegistryError("unknown task_type: %s" % task_type)

    if version is None:
        version = rt.get("active_version")
        if not version:
            raise PromptRegistryError("no active_version for %s" % task_type)

    if version not in rt.get("versions", []):
        raise PromptRegistryError(
            "version %s not registered for %s" % (version, task_type))

    ver_dir = os.path.join(PROMPTS_DIR, task_type, version)
    pkg_path = os.path.join(ver_dir, "package.json")
    if not os.path.exists(pkg_path):
        raise PromptRegistryError("package.json not found")

    pkg = _load_json(pkg_path)
    status = pkg.get("status", "unknown")

    if status == "disabled":
        raise PromptRegistryError(
            "version %s of %s is disabled" % (version, task_type))

    if status == "draft":
        # draft 允许加载但发出提醒
        pass

    # 校验完整性（旧版本宽松 schema）
    is_active = (version == rt.get("active_version"))
    errors = _validate_package(pkg, task_type, ver_dir, strict_schema=is_active)
    if errors:
        raise PromptRegistryError("package validation failed: %s" % "; ".join(errors))

    # 验证 checksum
    actual_cs = compute_checksum(pkg, task_type, ver_dir)
    expected_cs = pkg.get("checksum", "")
    if actual_cs != expected_cs:
        raise PromptRegistryError(
            "checksum mismatch for %s/%s" % (task_type, version))

    return pkg


def validate_all():
    """验证 Registry 中所有注册版本的完整性。active 版本做完整校验。"""
    errors = []
    try:
        reg = load_registry()
    except Exception as e:
        return (False, [str(e)])

    for tid, rt in reg.get("task_types", {}).items():
        active_ver = rt.get("active_version")
        for version in rt.get("versions", []):
            try:
                pkg = get_prompt_package(tid, version)
                # checksum 始终验证
                ver_dir = os.path.join(PROMPTS_DIR, tid, version)
                actual_cs = compute_checksum(pkg, tid, ver_dir)
                if actual_cs != pkg.get("checksum", ""):
                    errors.append("%s/%s: checksum mismatch" % (tid, version))
            except Exception as e:
                errors.append("%s/%s: %s" % (tid, version, str(e)))

    return (len(errors) == 0, errors)


def get_active_version(task_type):
    """返回 task_type 的 active_version 字符串，失败抛异常。"""
    reg = load_registry()
    rt = reg.get("task_types", {}).get(task_type)
    if not rt:
        raise PromptRegistryError("unknown task_type: %s" % task_type)
    av = rt.get("active_version")
    if not av:
        raise PromptRegistryError("no active_version for %s" % task_type)
    return av


def list_prompts():
    """列出所有已注册 prompt 的摘要（不含敏感信息）。"""
    reg = load_registry()
    result = []
    for tid, rt in sorted(reg.get("task_types", {}).items()):
        entry = {
            "task_type": tid,
            "active_version": rt.get("active_version"),
            "versions": rt.get("versions", []),
        }
        av = rt.get("active_version")
        if av:
            try:
                pkg = _load_json(os.path.join(
                    PROMPTS_DIR, tid, av, "package.json"))
                entry["status"] = pkg.get("status")
                entry["description"] = pkg.get("description")
                entry["checksum"] = pkg.get("checksum")
                entry["required_variables"] = pkg.get("required_variables", [])
                entry["output_schema"] = pkg.get("output_schema")
            except Exception:
                entry["status"] = "error"
        result.append(entry)
    return result


def get_package_checksum(task_type, version="1.0.0"):
    """输出建议的 checksum（不修改文件）。"""
    ver_dir = os.path.join(PROMPTS_DIR, task_type, version)
    pkg_path = os.path.join(ver_dir, "package.json")
    if not os.path.exists(pkg_path):
        raise PromptRegistryError("package.json not found")
    pkg = _load_json(pkg_path)
    return compute_checksum(pkg, task_type, ver_dir)
