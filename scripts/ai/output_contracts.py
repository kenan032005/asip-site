#!/usr/bin/env python3
"""ASIP Stage 2.5C-1F — Output Contract Validator

Maps task_type + versions to output JSON Schema.
Distinguishes prompt_version from output_schema_version.
"""

import os
import json
from .prompt_registry import (
    get_prompt_package, resolve_confined_path,
    SCHEMAS_OUTPUT_DIR, REPO_ROOT, PromptRegistryError,
)
from .schema_validation import validate_against_schema

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))


class OutputContractError(Exception):
    """输出契约校验失败。"""


def get_output_schema(task_type, prompt_version=None,
                      output_schema_version=None):
    """返回 task_type 对应的输出 Schema dict。

    prompt_version: 精确加载该 Prompt Package（默认: active）
    output_schema_version: 指定输出 Schema 版本（默认: 使用 Package 绑定版本）

    两者都提供时必须与 Package 完全一致。
    """
    pkg = get_prompt_package(task_type, prompt_version)
    pkg_schema_version = pkg.get("output_schema_version", "1.0")

    if output_schema_version is None:
        effective = pkg_schema_version
    elif output_schema_version != pkg_schema_version:
        raise OutputContractError(
            "output_schema_version mismatch: requested %s, package binds %s"
            % (output_schema_version, pkg_schema_version))
    else:
        effective = output_schema_version

    schema_path = pkg.get("output_schema")
    if not schema_path:
        raise OutputContractError("no output_schema defined for %s" % task_type)

    full_path = resolve_confined_path(REPO_ROOT, schema_path,
                                      SCHEMAS_OUTPUT_DIR, must_exist=True)
    with open(str(full_path), "r", encoding="utf-8") as f:
        return json.load(f)


def validate_business_output(task_type, output,
                             prompt_version=None,
                             output_schema_version=None):
    """校验业务输出是否符合对应 Schema。

    Returns (ok: bool, errors: list).
    """
    try:
        schema = get_output_schema(task_type,
                                   prompt_version=prompt_version,
                                   output_schema_version=output_schema_version)
    except Exception as e:
        return (False, [str(e)])

    errors = validate_against_schema(output, schema)
    return (len(errors) == 0, errors)
