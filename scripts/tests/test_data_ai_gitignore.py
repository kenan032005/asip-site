#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A 包附加断言：data/ai/ 必须被 .gitignore 忽略，确保 Stage 4 AI 运行时缓存
（enrichment 结果、idempotency 等）绝不入库、不进 dist。

对应约束：ASIP Stage 4 第二执行包阻断报告「附带风险项」+ 用户裁定
「在解除阻断的执行包中一并补 .gitignore 规则并加测试断言」。
"""
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


class TestDataAiGitignore(unittest.TestCase):
    def test_data_ai_in_gitignore(self):
        gi = os.path.join(ROOT, ".gitignore")
        self.assertTrue(os.path.exists(gi), ".gitignore 必须存在")
        lines = [ln.strip() for ln in open(gi, encoding="utf-8")]
        self.assertIn("data/ai/", lines,
                      "data/ai/ 必须出现在 .gitignore，防止 Stage 4 运行时缓存入库")

    def test_data_ai_not_tracked(self):
        # 若 data/ai 目录已存在，git 不应跟踪其下任何文件
        ai_dir = os.path.join(ROOT, "data", "ai")
        if not os.path.isdir(ai_dir):
            self.skipTest("data/ai 尚不存在（Trial 运行前正常）")
        out = os.popen(f'cd "{ROOT}" && git status --porcelain data/ai 2>/dev/null').read()
        self.assertEqual(out.strip(), "",
                         "data/ai 下不应出现已跟踪/待提交文件")


if __name__ == "__main__":
    unittest.main()
