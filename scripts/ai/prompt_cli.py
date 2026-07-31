#!/usr/bin/env python3
"""ASIP Stage 2.5C-1 — Prompt CLI

Commands: validate, list, show, render, checksum
"""

import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from ai.prompt_registry import (
    validate_all, list_prompts, get_prompt_package,
    get_package_checksum, PromptRegistryError,
)
from ai.prompt_renderer import render_prompt, PromptRenderError


def cmd_validate(args):
    ok, errors = validate_all()
    if not ok:
        for e in errors:
            print("FAIL:", e)
        return 1
    print("OK: %d task types validated" % len(list_prompts()))
    return 0


def cmd_list(args):
    prompts = list_prompts()
    for p in prompts:
        print(json.dumps(p, ensure_ascii=False, indent=2))
    return 0


def cmd_show(args):
    pkg = get_prompt_package(args.task_type, args.version)
    # 不输出隐藏密钥或内部路径
    safe_keys = ["prompt_id", "task_type", "version", "status",
                 "required_variables", "optional_variables",
                 "output_schema", "output_schema_version",
                 "output_language", "description", "checksum"]
    out = {k: pkg[k] for k in safe_keys if k in pkg}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_render(args):
    if not args.variables_file:
        sys.stderr.write("error: --variables-file required for render\n")
        return 2
    with open(args.variables_file, "r", encoding="utf-8") as f:
        variables = json.load(f)

    result = render_prompt(
        args.task_type, variables,
        version=args.version)

    if args.output:
        # 安全检查：仅允许写入指定文件
        out_path = os.path.abspath(args.output)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("Rendered to:", out_path)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_checksum(args):
    cs = get_package_checksum(args.task_type, args.version)
    print("Suggested checksum:", cs)
    print("(not auto-applied; update package.json manually)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="ASIP Stage 2.5C-1 Prompt CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate")

    sub.add_parser("list")

    s = sub.add_parser("show")
    s.add_argument("--task-type", required=True)
    s.add_argument("--version", default=None)

    r = sub.add_parser("render")
    r.add_argument("--task-type", required=True)
    r.add_argument("--version", default=None)
    r.add_argument("--variables-file", default=None)
    r.add_argument("--output", default=None)

    c = sub.add_parser("checksum")
    c.add_argument("--task-type", required=True)
    c.add_argument("--version", default="1.0.0")

    try:
        args = ap.parse_args(argv)
        if args.cmd == "validate":
            return cmd_validate(args)
        elif args.cmd == "list":
            return cmd_list(args)
        elif args.cmd == "show":
            return cmd_show(args)
        elif args.cmd == "render":
            return cmd_render(args)
        elif args.cmd == "checksum":
            return cmd_checksum(args)
        return 0
    except SystemExit:
        raise
    except (PromptRegistryError, PromptRenderError) as e:
        sys.stderr.write("error: %s\n" % e)
        return 1
    except Exception as e:
        sys.stderr.write("error: %s\n" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
