#!/usr/bin/env python3
"""ASIP Stage 2.5C-1 — Output Contract Validator

Maps task_type to output JSON Schema and validates business output
using zero-dependency jsonschema-like checks or existing validator.
"""

import os
import json
from .prompt_registry import get_prompt_package, get_active_version, PromptRegistryError

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))


class OutputContractError(Exception):
    """输出契约校验失败。"""


def get_output_schema(task_type, version=None):
    """返回 task_type 对应的输出 Schema dict。

    version=None 时使用 active_version。
    不依赖在线 Schema 服务。
    """
    pkg = get_prompt_package(task_type, version)
    schema_path = pkg.get("output_schema")
    if not schema_path:
        raise OutputContractError("no output_schema defined for %s" % task_type)

    full_path = os.path.join(REPO_ROOT, schema_path)
    if not os.path.exists(full_path):
        raise OutputContractError("output schema not found: %s" % schema_path)

    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _validate_against_schema(instance, schema):
    """最小但严格的 JSON Schema Draft-07 子集校验器。
    
    不需要第三方库。只支持本阶段需要的校验规则。
    """
    errors = []

    if not isinstance(instance, dict):
        return ["output must be an object"]

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

    # properties
    for prop_name, prop_schema in schema.get("properties", {}).items():
        if prop_name not in instance:
            continue
        val = instance[prop_name]
        errors.extend(_check_property(prop_name, val, prop_schema))

    return errors


def _check_property(name, value, schema):
    errors = []
    ptype = schema.get("type")

    # type
    if ptype:
        if isinstance(ptype, list):
            if not any(_type_match(value, t) for t in ptype):
                errors.append("%s: type must be one of %s" % (name, ptype))
        else:
            if not _type_match(value, ptype):
                errors.append("%s: type must be %s" % (name, ptype))

    # enum
    if "enum" in schema and value not in schema["enum"]:
        errors.append("%s: value %r not in enum %s" % (name, value, schema["enum"]))

    # minimum / maximum (for number/integer)
    if isinstance(value, (int, float)):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append("%s: value %s < minimum %s" % (name, value, schema["minimum"]))
        if "maximum" in schema and value > schema["maximum"]:
            errors.append("%s: value %s > maximum %s" % (name, value, schema["maximum"]))

    # string minLength / maxLength
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append("%s: length %d < minLength %d" % (name, len(value), schema["minLength"]))
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append("%s: length %d > maxLength %d" % (name, len(value), schema["maxLength"]))

    # nested objects
    if isinstance(value, dict) and schema.get("type") == "object":
        ap = schema.get("additionalProperties")
        if ap is False:
            for k in value:
                if k not in schema.get("properties", {}):
                    errors.append("%s.%s: unknown field" % (name, k))
        for pk, ps in schema.get("properties", {}).items():
            if pk in value:
                errors.extend(_check_property("%s.%s" % (name, pk), value[pk], ps))
        for req in schema.get("required", []):
            if req not in value:
                errors.append("%s: missing required field %s" % (name, req))

    # arrays
    if isinstance(value, list) and schema.get("type") == "array":
        items_schema = schema.get("items")
        if items_schema:
            for i, item in enumerate(value):
                errors.extend(_check_property("%s[%d]" % (name, i), item, items_schema))

    return errors


def _type_match(value, expected_type):
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "null":
        return value is None
    return False


def validate_business_output(task_type, output, schema_version=None):
    """校验业务输出是否符合对应 Schema。
    
    Args:
        task_type: prompt task_type
        output: business output dict to validate
        schema_version: optional, passed to get_output_schema
    
    Returns:
        (ok: bool, errors: list)
    """
    try:
        schema = get_output_schema(task_type, schema_version)
    except Exception as e:
        return (False, [str(e)])

    errors = _validate_against_schema(output, schema)
    return (len(errors) == 0, errors)
