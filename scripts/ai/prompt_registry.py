#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 2.5C-1 — Prompt Registry

Loads and validates versioned prompt packages from prompts/ directory.
Resolves active/deprecated/disabled versions per registry.json.
"""

import os
import json
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
PROMPTS_DIR = os.path.join(REPO_ROOT, "prompts")
REGISTRY_PATH = os.path.join(PROMPTS_DIR, "registry.json")
PACKAGE_SCHEMA_PATH = os.path.join(REPO_ROOT, "schemas",
                                    "prompt_package.schema.json")
DEFAULT_SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"


class PromptRegistryError(Exception):
    """Prompt Registry 运行时错误。"""


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _validate_against_schema(instance, schema):
    """最小 Schema 校验（type, required, additionalProperties, enum, pattern, minLength, uniqueItems, items）。"""
    errors = []
    if not isinstance(instance, dict) or not isinstance(schema, dict):
        return ["invalid schema or instance"]
    # type
    typ = schema.get("type")
    if typ and typ != "object":
        return ["schema type must be object"]
    # additionalProperties
    if schema.get("additionalProperties") is False:
        for key in instance:
            if key not in schema.get("properties", {}):
                errors.append("unknown field: %s" % key)
    # required
    for req in schema.get("required", []):
        if req not in instance:
            errors.append("missing required field: %s" % req)
    # per-property checks
    for prop_name, prop_schema in schema.get("properties", {}).items():
        if prop_name not in instance:
            continue
        val = instance[prop_name]
        # enum
        if "enum" in prop_schema and val not in prop_schema["enum"]:
            errors.append("%s: value %r not in enum" % (prop_name, val))
        # pattern
        if "pattern" in prop_schema and isinstance(val, str):
            import re
            if not re.match(prop_schema["pattern"], val):
                errors.append("%s: value %r does not match pattern" % (prop_name, val))
        # minLength
        if "minLength" in prop_schema and isinstance(val, str):
            if len(val) < prop_schema["minLength"]:
                errors.append("%s: minLength %d required" % (prop_name, prop_schema["minLength"]))
        # type check
        ptype = prop_schema.get("type")
        if ptype == "string" and not isinstance(val, str):
            errors.append("%s: must be string" % prop_name)
        elif ptype == "integer" and not isinstance(val, int):
            errors.append("%s: must be integer" % prop_name)
        elif ptype == "number" and not isinstance(val, (int, float)):
            errors.append("%s: must be number" % prop_name)
        elif ptype == "boolean" and not isinstance(val, bool):
            errors.append("%s: must be boolean" % prop_name)
        elif ptype == "array" and not isinstance(val, list):
            errors.append("%s: must be array" % prop_name)
        elif ptype == "object" and not isinstance(val, dict):
            errors.append("%s: must be object" % prop_name)
        # uniqueItems
        if "uniqueItems" in prop_schema and isinstance(val, list):
            if len(val) != len(set(str(x) for x in val)):
                errors.append("%s: items must be unique" % prop_name)
        # nested items
        if isinstance(val, list) and "items" in prop_schema:
            item_schema = prop_schema["items"]
            for i, item in enumerate(val):
                if isinstance(item, dict) and isinstance(item_schema, dict):
                    nested = _validate_against_schema(item, item_schema)
                    for e in nested:
                        errors.append("%s[%d].%s" % (prop_name, i, e))
    return errors


def _validate_package(pkg, task_type, version_dir, strict_schema=True):
    """验证 package.json 符合契约（含 Schema 校验）。"""
    errors = []
    # 使用 prompt_package.schema.json 校验（仅当 strict_schema）
    if strict_schema and os.path.exists(PACKAGE_SCHEMA_PATH):
        pkg_schema = _load_json(PACKAGE_SCHEMA_PATH)
        schema_errs = _validate_against_schema(pkg, pkg_schema)
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
    # templates exist
    st = pkg.get("system_template")
    ut = pkg.get("user_template")
    if st:
        if not os.path.exists(os.path.join(version_dir, st)):
            errors.append("system_template not found: %s" % st)
    if ut:
        if not os.path.exists(os.path.join(version_dir, ut)):
            errors.append("user_template not found: %s" % ut)
    # output schema exists
    os_path = pkg.get("output_schema")
    if os_path:
        schema_path = os.path.join(REPO_ROOT, os_path)
        if not os.path.exists(schema_path):
            errors.append("output_schema not found: %s" % os_path)
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

    # system.md
    st = pkg.get("system_template")
    if st:
        with open(os.path.join(version_dir, st), "r", encoding="utf-8") as f:
            m.update(f.read().encode("utf-8"))
    # user.md
    ut = pkg.get("user_template")
    if ut:
        with open(os.path.join(version_dir, ut), "r", encoding="utf-8") as f:
            m.update(f.read().encode("utf-8"))
    # output schema (normalized)
    os_path = pkg.get("output_schema")
    if os_path:
        schema_path = os.path.join(REPO_ROOT, os_path)
        with open(schema_path, "r", encoding="utf-8") as f:
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
