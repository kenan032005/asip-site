#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c3f_tag_trigger.py — C3F tag 触发的模式与默认运行模式契约。

用 GitHub 的 tag pattern 语义（glob，`*` 不跨 `/`）静态解析 workflow，
锁定：两个具名前缀可触发、无关 tag 不触发、tag 事件没有 inputs 时 mode 必须落到
c3f_incremental，且 tag 触发禁止 full。
"""
import fnmatch
import io
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WF = ROOT / ".github" / "workflows" / "asip-v11-c3-ai.yml"


def text():
    with io.open(WF, encoding="utf-8") as f:
        return f.read()


def tag_patterns():
    """从 on.push.tags 提取原始 pattern（indent 感知的逐行解析）。

    workflow 结构：
        on:                 (缩进 0)
          workflow_dispatch:
          push:             (缩进 2)
            tags:           (缩进 4)
              - "c3f-..."   (缩进 6)
        permissions:        (缩进 0 → on 块结束)
    """
    lines = text().splitlines()
    # 定位 on: 块
    start = None
    for i, ln in enumerate(lines):
        if ln.rstrip() == "on:":
            start = i + 1
            break
    if start is None:
        return []
    end = len(lines)
    for j in range(start, len(lines)):
        ln = lines[j]
        if ln.strip() and not ln.startswith(" "):
            end = j
            break
    body = lines[start:end]
    # 在 on: 块内定位 push: 与它的 tags:
    out, in_push = [], False
    for ln in body:
        stripped = ln.strip()
        if stripped == "push:":
            in_push = True
            continue
        if in_push:
            if stripped and (len(ln) - len(ln.lstrip())) <= 2 and stripped != "tags:":
                in_push = False          # 离开 push 块
                continue
            if stripped == "tags:":
                continue
            m = re.match(r'\s*-\s*"([^"]+)"\s*$', ln)
            if m:
                out.append(m.group(1))
    return out


def matches(pattern, tag):
    """GitHub tag filter 语义：glob；'*' 不匹配 '/'。"""
    return fnmatch.fnmatchcase(tag, pattern.replace("**", "*"))


class TagTriggerTest(unittest.TestCase):

    def test_01_patterns_are_explicit_not_wildcard(self):
        pats = tag_patterns()
        self.assertTrue(pats, "on.push.tags 不能为空")
        for p in pats:
            self.assertNotEqual(p.strip(), "*", "不得让任意 tag 触发真实 AI")
            self.assertIn("-real-ai-", p)

    def test_02_c3r2_pattern_still_matches(self):
        pats = tag_patterns()
        self.assertTrue(any(matches(p, "c3r2-real-ai-9") for p in pats),
                        "必须保留 c3r2-real-ai-* 兼容")

    def test_03_c3f_pattern_matches(self):
        pats = tag_patterns()
        for t in ("c3f-real-ai-1", "c3f-real-ai-2"):
            self.assertTrue(any(matches(p, t) for p in pats), "%s 必须能触发" % t)

    def test_04_unrelated_tag_does_not_match(self):
        pats = tag_patterns()
        for t in ("v1.0", "c3f-real-ai", "real-ai-1", "c3g-real-ai-1",
                  "release-2026", "main"):
            self.assertFalse(any(matches(p, t) for p in pats), "%s 不得触发" % t)


class ModeResolutionTest(unittest.TestCase):

    def test_05_tag_event_without_inputs_resolves_incremental(self):
        src = text()
        # 必须有显式解析步骤，且默认落到 c3f_incremental
        self.assertIn("RESOLVED_AI_MODE", src)
        self.assertIn('MODE="${RAW:-c3f_incremental}"', src)
        # 不得留下任何直接使用 inputs.mode 且无 c3f 兜底的调用
        self.assertNotIn("--mode \"${{ inputs.mode || 'full' }}\"", src)
        self.assertNotIn('--mode "${{ inputs.mode }}"', src)
        # 两处 c3_run 都必须用解析后的变量
        # 解析后的 mode 必须被真实调用方使用：两处 c3_run 调用 + 模式感知的输入审计
        self.assertGreaterEqual(src.count('--mode "$C3F_MODE"'), 2)
        self.assertIn("python -m scripts.ops.c3_input_audit --root . --mode \"$C3F_MODE\"", src)
        self.assertIn("--mode \"$C3F_MODE\"", src)

    def test_06_tag_trigger_refuses_full_mode(self):
        src = text()
        self.assertIn("FULL_MODE_REFUSED_FOR_TAG_TRIGGER", src)
        # 拒绝条件：非目标分支（即 tag 触发）且 mode=full
        self.assertIn('"${GITHUB_REF}" != "refs/heads/${TARGET_BRANCH}"', src)
        # 第二道阻断点：分支守卫里的 tag 前缀白名单必须与 on.push.tags 一致，
        # 否则 tag 虽能触发 workflow，却会在 guard 步骤被拒（c3f-real-ai-1 就是这样没跑起来）。
        pats = tag_patterns()
        for p in pats:
            self.assertIn(p, src, "guard 必须放行 on.push.tags 里的每个前缀: %s" % p)

    def test_07_incremental_mode_skips_event_and_country_loops(self):
        """c3f_incremental 在 runner 里必须显式跳过 event/country 且不做全量 localization。"""
        run = (ROOT / "scripts" / "ops" / "c3_run.py").read_text(encoding="utf-8")
        self.assertIn("incremental = (mode == \"c3f_incremental\")", run)
        self.assertIn("skip_analysis = incremental", run)
        self.assertIn("if skip_analysis:", run)
        self.assertIn('stats["event"] = {"full": 0, "fallback": 0, "low_data": 0,', run)
        self.assertIn("[] if skip_analysis else sorted(by_country.items())", run)
        # summary-only 目标集合（不是 needs_localization 全量）
        self.assertIn("L.needs_summary_only(i)", run)
        self.assertIn('if mode in ("summary_only", "c3f_incremental")', run)


if __name__ == "__main__":
    unittest.main(verbosity=2)
