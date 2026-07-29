#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
schema_validator.py —— 轻量 JSON Schema 校验器（零依赖）

仅实现本项目中用到的 draft-07 子集：
required / type / enum / const / pattern / minimum / maximum / format(uri,date-time) / items。

目的：在无法联网安装 jsonschema 的环境下，仍能按 schemas/*.json 执行结构化校验。
validate_stage2.py 与 2A 测试均依赖本模块。
"""

import re
from pathlib import Path

# date-time：允许带 Z 或 ±HH:MM 偏移
_ISO_DT = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)
# uri：宽松校验 scheme://host
_URI = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://\S+$")


def _check_type(value, typ):
    if typ == "object":
        return isinstance(value, dict)
    if typ == "array":
        return isinstance(value, list)
    if typ == "string":
        return isinstance(value, str)
    if typ == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if typ == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if typ == "boolean":
        return isinstance(value, bool)
    if typ == "null":
        return value is None
    return True


def validate_instance(obj, schema, path="$") -> list:
    """返回错误字符串列表（空表示通过）。"""
    errors = []

    if not isinstance(schema, dict):
        return errors

    # const
    if "const" in schema:
        if obj != schema["const"]:
            errors.append(f"{path}: 期望 const={schema['const']!r}，实际 {obj!r}")

    # type
    if "type" in schema:
        typ = schema["type"]
        if isinstance(typ, list):
            if not any(_check_type(obj, t) for t in typ):
                errors.append(f"{path}: 类型不符合任一 {typ}")
        else:
            if not _check_type(obj, typ):
                errors.append(f"{path}: 类型应为 {typ}，实际 {type(obj).__name__}")

    # enum
    if "enum" in schema and obj not in schema["enum"]:
        errors.append(f"{path}: 值 {obj!r} 不在枚举 {schema['enum']}")

    # pattern
    if "pattern" in schema and isinstance(obj, str):
        if not re.search(schema["pattern"], obj):
            errors.append(f"{path}: 值 {obj!r} 不匹配模式 {schema['pattern']}")

    # minimum / maximum
    if "minimum" in schema and isinstance(obj, (int, float)):
        if obj < schema["minimum"]:
            errors.append(f"{path}: {obj} < minimum {schema['minimum']}")
    if "maximum" in schema and isinstance(obj, (int, float)):
        if obj > schema["maximum"]:
            errors.append(f"{path}: {obj} > maximum {schema['maximum']}")

    # format
    if "format" in schema and isinstance(obj, str):
        fmt = schema["format"]
        if fmt == "date-time" and not _ISO_DT.match(obj):
            errors.append(f"{path}: 不是合法 date-time: {obj!r}")
        elif fmt == "uri" and not _URI.match(obj):
            errors.append(f"{path}: 不是合法 uri: {obj!r}")

    # required
    if "required" in schema and isinstance(obj, dict):
        for r in schema["required"]:
            if r not in obj:
                errors.append(f"{path}: 缺少必填字段 {r}")

    # properties
    if "properties" in schema and isinstance(obj, dict):
        for k, subschema in schema["properties"].items():
            if k in obj:
                errors.extend(validate_instance(obj[k], subschema, f"{path}.{k}"))

    # additionalProperties: false
    if schema.get("additionalProperties") is False and isinstance(obj, dict):
        allowed = set(schema.get("properties", {}).keys())
        for k in obj:
            if k not in allowed:
                errors.append(f"{path}.{k}: additionalProperties=false 不允许额外字段 {k!r}")

    # items
    if "items" in schema and isinstance(obj, list):
        for i, item in enumerate(obj):
            errors.extend(validate_instance(item, schema["items"], f"{path}[{i}]"))

    return errors


def load_schema(name: str, schema_dir: Path = None) -> dict:
    if schema_dir is None:
        schema_dir = Path(__file__).resolve().parent.parent.parent / "schemas"
    path = Path(schema_dir) / name
    import json
    return json.loads(path.read_text(encoding="utf-8"))
