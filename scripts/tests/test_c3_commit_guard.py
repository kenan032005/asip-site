#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c3_commit_guard.py — C3R2 §四 commit guard 测试。

覆盖：中文/含括号路径必须被接受；白名单外必须 fail-closed；
logs / .env / secret / debug / 报告文件必须被拒；
并且**必须通过真实 git NUL 分隔读取**验证（复现 CI 的转义场景）。
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "ops"))

import importlib.util
spec = importlib.util.spec_from_file_location(
    "c3_commit_guard", str(ROOT / "scripts" / "ops" / "c3_commit_guard.py"))
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

CN_COUNTRIES = ("尼日利亚", "刚果（金）", "莫桑比克", "乍得", "苏丹")


class WhitelistPathTest(unittest.TestCase):
    """§四"""

    def test_01_commit_guard_accepts_unicode_country_analysis_path(self):
        for c in CN_COUNTRIES:
            p = "data/intelligence/ai/country_analysis/%s.json" % c
            self.assertTrue(G.is_whitelisted(p), p)
        # 真实 CI 产物里括号被 path_for 消毒后的文件名也必须接受
        self.assertTrue(G.is_whitelisted(
            "data/intelligence/ai/country_analysis/刚果_金_.json"))

    def test_02_commit_guard_accepts_ascii_ai_path(self):
        for p in ("data/intelligence/ai/localization/loc_x_deepseek-flash.json",
                  "data/intelligence/ai/event_analysis/EVT_abc.json",
                  "data/intelligence/ai/homepage_analysis/current.json",
                  "data/intelligence/ai/runs/ci_status.json",
                  "data/views/ai_intelligence.json",
                  "data/canonical/articles.json",
                  "data/views/news_stream.json"):
            self.assertTrue(G.is_whitelisted(p), p)

    def test_03_commit_guard_rejects_outside_ai_whitelist(self):
        for p in ("data/events.json", "data/canonical/quarantine.json",
                  "data/views/c1a_gate_audit.json", "scripts/ops/c3_run.py",
                  "index.html", "data/public/published_events.json",
                  "data/runtime/ops/time_contract.json",
                  "data/intelligence/ai/../ai/../../events.json"):
            self.assertFalse(G.is_whitelisted(p), p)

    def test_04_commit_guard_handles_spaces_and_unicode_without_quote_confusion(self):
        """含空格/中文/括号的路径不得被 Git 引号形式影响判定。"""
        cases = [
            "data/intelligence/ai/country_analysis/刚果（金）.json",
            "data/intelligence/ai/country_analysis/尼日利亚.json",
            "data/intelligence/ai/localization/loc_南非 报道_x.json",
        ]
        for p in cases:
            self.assertTrue(G.is_whitelisted(p), p)
        # Git 的 quoted 形式（带双引号 + octal 转义）**不是**原始路径，
        # 一旦被当成路径传入就必须判越界（这正是修复前的 bug）
        quoted = '"data/intelligence/ai/country_analysis/\\344\\270\\255.json"'
        self.assertFalse(G.is_whitelisted(quoted))
        ok, allowed, rejected = G.check(cases + [quoted])
        self.assertEqual(len(allowed), 3)
        self.assertEqual(len(rejected), 1)

    def test_05_commit_guard_does_not_accept_logs(self):
        for p in ("logs/run.log", "data/intelligence/ai/runs/a.log",
                  "data/intelligence/ai/localization/x.bak",
                  "c3_run_report_run1.json", "staged_paths.txt"):
            self.assertFalse(G.is_whitelisted(p), p)

    def test_06_commit_guard_does_not_accept_env_or_secret_files(self):
        for p in (".env", "config/.env", "data/intelligence/ai/localization/.env",
                  "secrets.json", "data/intelligence/ai/runs/credential.json",
                  "data/intelligence/ai/localization/raw_response_x.json",
                  "data/intelligence/ai/localization/prompt_debug_x.json",
                  "artifacts/asip-v11-c3r2-real-ai.zip"):
            self.assertFalse(G.is_whitelisted(p), p)


class RealGitStagingTest(unittest.TestCase):
    """用真实 git 仓库复现 CI 的「quoted path」场景（§二 的核心修复点）"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="c3guard_")
        subprocess.run(["git", "init", "-q"], cwd=self.tmp, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=self.tmp, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.tmp, check=True)

    def _write(self, rel, text="{}"):
        p = Path(self.tmp) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def test_07_staged_paths_reads_raw_unicode_names(self):
        """NUL 分隔读取必须返回**原始**中文路径，而不是 octal 转义形式。"""
        for c in CN_COUNTRIES:
            self._write("data/intelligence/ai/country_analysis/%s.json" % c)
        self._write("data/views/ai_intelligence.json")
        subprocess.run(["git", "add", "-A"], cwd=self.tmp, check=True)

        raw = G.staged_paths(self.tmp)
        self.assertEqual(len(raw), len(CN_COUNTRIES) + 1)
        for c in CN_COUNTRIES:
            self.assertIn("data/intelligence/ai/country_analysis/%s.json" % c, raw)
        # 不得出现任何反斜杠转义残留
        self.assertFalse([p for p in raw if "\\" in p])

        ok, allowed, rejected = G.check(raw)
        self.assertTrue(ok, "rejected=%s" % rejected)
        self.assertEqual(len(allowed), len(raw))
        self.assertEqual(rejected, [])

        # 对照：默认（非 -z）输出确实会被 Git 转义 —— 说明为什么必须用 -z
        r = subprocess.run(["git", "diff", "--cached", "--name-only"],
                           cwd=self.tmp, capture_output=True, text=True)
        self.assertIn("\\3", r.stdout)   # octal escape 出现在默认输出里

    def test_08_real_staging_still_fails_closed_outside_whitelist(self):
        self._write("data/intelligence/ai/country_analysis/尼日利亚.json")
        self._write("data/events.json")                    # 白名单外
        self._write("logs/x.log")                          # 禁止项
        subprocess.run(["git", "add", "-A"], cwd=self.tmp, check=True)
        raw = G.staged_paths(self.tmp)
        ok, allowed, rejected = G.check(raw)
        self.assertFalse(ok)
        self.assertEqual(len(allowed), 1)
        self.assertEqual(sorted(rejected),
                         ["data/events.json", "logs/x.log"])

    def test_09_guard_cli_exit_codes(self):
        self._write("data/intelligence/ai/country_analysis/莫桑比克.json")
        subprocess.run(["git", "add", "-A"], cwd=self.tmp, check=True)
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "ops" / "c3_commit_guard.py"),
                            "--root", self.tmp], capture_output=True, text=True,
                           encoding="utf-8", errors="ignore")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("UNICODE_COMMIT_GUARD = PASS", r.stdout)
        self.assertIn("OUT_OF_WHITELIST_COUNT = 0", r.stdout)

        self._write("data/events.json")
        subprocess.run(["git", "add", "-A"], cwd=self.tmp, check=True)
        r2 = subprocess.run([sys.executable, str(ROOT / "scripts" / "ops" / "c3_commit_guard.py"),
                             "--root", self.tmp], capture_output=True, text=True,
                            encoding="utf-8", errors="ignore")
        self.assertEqual(r2.returncode, 1)
        self.assertIn("UNICODE_COMMIT_GUARD = FAIL", r2.stdout)
        self.assertIn("OUT_OF_WHITELIST_COUNT = 1", r2.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
