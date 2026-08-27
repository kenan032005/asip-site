#!/usr/bin/env python3
"""ASIP Stage 2.5C-1F — Unified JSON Schema Validator (Draft-07 subset)

Used by both prompt_registry and output_contracts.
Zero external dependencies, no network access.
"""

import re
import json


def validate_against_schema(instance, schema, path="$", resolve_refs=False):
    """Validate instance against JSON Schema Draft-07 subset.

    Returns list of error strings. Empty list = valid.

    Supports: type, required, properties, additionalProperties, items,
    enum, pattern, minLength, maxLength, minimum, maximum, uniqueItems,
    $ref（#/definitions/<name> 内部引用）。

    resolve_refs=False（默认）：$ref 不解析（历史宽松行为，Stage8B/8A 既有
    路径不变，避免暴露 fixture/视图数据的历史不合规）。
    resolve_refs=True：解析 $ref，items 类型/required 检查真正生效
    （Stage8C Package2 Repair：report final schema 验证缺口关闭，str[]
    等违规结构被正确拦截）。
    """
    errors = []
    _validate(instance, schema, path, errors, schema, resolve_refs)
    return errors


def _resolve_ref(schema, root):
    """解析 $ref（仅支持 #/definitions/<name> 内部引用）。循环安全。"""
    seen = 0
    while isinstance(schema, dict) and "$ref" in schema and seen < 8:
        ref = schema["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/definitions/"):
            break
        name = ref[len("#/definitions/"):]
        target = (root or {}).get("definitions", {}).get(name)
        if not isinstance(target, dict):
            break  # ref 目标缺失 → 保持原样（避免误伤）
        schema = target
        seen += 1
    return schema


def _validate(instance, schema, path, errors, root=None, resolve_refs=False):
    """Recursive validation."""
    if not isinstance(schema, dict):
        errors.append("%s: schema must be an object" % path)
        return
    # §：$ref 解析（resolve_refs=True 时；Stage8C Package2 Repair）
    if resolve_refs:
        schema = _resolve_ref(schema, root)

    # type check
    ptype = schema.get("type")
    if ptype:
        if not _type_match(instance, ptype):
            errors.append("%s: expected type %s, got %s" %
                          (path, ptype, _type_name(instance)))
            return  # Further checks pointless if type wrong

    # enum
    if "enum" in schema and instance not in schema["enum"]:
        errors.append("%s: value %s not in enum" % (path, _safe_repr(instance)))

    # string constraints
    if isinstance(instance, str):
        if "pattern" in schema:
            if not re.match(schema["pattern"], instance):
                errors.append("%s: does not match pattern" % path)
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append("%s: length %d < minLength %d" %
                          (path, len(instance), schema["minLength"]))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append("%s: length %d > maxLength %d" %
                          (path, len(instance), schema["maxLength"]))

    # numeric constraints
    if isinstance(instance, (int, float)):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append("%s: value %s < minimum %s" %
                          (path, instance, schema["minimum"]))
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append("%s: value %s > maximum %s" %
                          (path, instance, schema["maximum"]))

    # object constraints
    if isinstance(instance, dict) and schema.get("type") == "object":
        _validate_object(instance, schema, path, errors, root, resolve_refs)

    # array constraints
    if isinstance(instance, list) and schema.get("type") == "array":
        _validate_array(instance, schema, path, errors, root, resolve_refs)


def _validate_object(instance, schema, path, errors, root=None, resolve_refs=False):
    props = schema.get("properties", {})
    # additionalProperties
    ap = schema.get("additionalProperties")
    if ap is False:
        for key in instance:
            if key not in props:
                errors.append("%s.%s: unknown field" % (path, key))

    # required
    for req in schema.get("required", []):
        if req not in instance:
            errors.append("%s: missing required field %s" % (path, req))

    # per-property validation
    for prop_name, prop_schema in props.items():
        if prop_name not in instance:
            continue
        _validate(instance[prop_name], prop_schema,
                  "%s.%s" % (path, prop_name), errors, root, resolve_refs)


def _validate_array(instance, schema, path, errors, root=None, resolve_refs=False):
    items_schema = schema.get("items")
    if items_schema is None:
        return
    # uniqueItems
    if schema.get("uniqueItems") and isinstance(instance, list):
        strs = [json.dumps(x, ensure_ascii=False, sort_keys=True)
                for x in instance]
        if len(strs) != len(set(strs)):
            errors.append("%s: items must be unique" % path)

    if isinstance(items_schema, dict):
        if resolve_refs:
            items_schema = _resolve_ref(items_schema, root)
        for i, item in enumerate(instance):
            _validate(item, items_schema, "%s[%d]" % (path, i), errors, root, resolve_refs)
    elif isinstance(items_schema, list):
        for i, item in enumerate(instance):
            if i < len(items_schema):
                _validate(item, items_schema[i], "%s[%d]" % (path, i), errors, root, resolve_refs)


def _type_match(instance, expected):
    """Type matching with strict boolean handling."""
    if expected == "null":
        return instance is None
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    # type is array of types
    if isinstance(expected, list):
        return any(_type_match(instance, t) for t in expected)
    return False


def _type_name(instance):
    if instance is None:
        return "null"
    if isinstance(instance, bool):
        return "boolean"
    if isinstance(instance, int):
        return "integer"
    if isinstance(instance, float):
        return "number"
    if isinstance(instance, str):
        return "string"
    if isinstance(instance, list):
        return "array"
    if isinstance(instance, dict):
        return "object"
    return type(instance).__name__


def _safe_repr(val):
    """Safe repr, no paths or secrets."""
    if isinstance(val, str) and len(val) > 50:
        return repr(val[:50] + "...")
    return repr(val)
