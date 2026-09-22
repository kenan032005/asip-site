#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_c3_import_wiring.py — C3R2 §九 导入接线测试（7 项）。

模拟 GitHub Actions 的干净环境：**不设置 PYTHONPATH**、不预置 scripts/ 路径、
working directory = repo root，用与 workflow 相同的调用形式执行。
不调用真实 DeepSeek（provider=auto 在无凭据时短路；另有 mock 断言）。
"""
import importlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

C3_MODULES = ("scripts.ai.c3_localization", "scripts.ai.c3_analysis",
              "scripts.ai.c3_artifacts", "scripts.ops.c3_run",
              "scripts.ops.build_ai_views")


def _clean_env():
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)          # 与 GitHub Actions 一致：不靠 PYTHONPATH
    env.pop("ASIP_DEEPSEEK_API_KEY", None)   # 保证不触发真实 AI
    return env


def _run(args, timeout=180):
    return subprocess.run([sys.executable] + args, cwd=str(ROOT), env=_clean_env(),
                          capture_output=True, text=True, timeout=timeout)


class ImportWiringTest(unittest.TestCase):
    """§七/§九：干净环境下 5 个模块都必须可导入"""

    def _import_in_subprocess(self, module):
        code = ("import importlib, sys\n"
                "sys.path = [p for p in sys.path if 'scripts' not in p]\n"
                "importlib.import_module(%r)\n"
                "print('OK')\n" % module)
        r = _run(["-c", code])
        return r

    def test_01_c3_runner_imports_from_repo_root(self):
        r = self._import_in_subprocess("scripts.ops.c3_run")
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        self.assertNotIn("ModuleNotFoundError", r.stderr)
        self.assertIn("OK", r.stdout)

    def test_02_c3_localization_imports_cleanly(self):
        r = self._import_in_subprocess("scripts.ai.c3_localization")
        self.assertEqual(r.returncode, 0, r.stderr[-600:])

    def test_03_c3_analysis_imports_cleanly(self):
        r = self._import_in_subprocess("scripts.ai.c3_analysis")
        self.assertEqual(r.returncode, 0, r.stderr[-600:])

    def test_04_c3_artifacts_imports_cleanly(self):
        r = self._import_in_subprocess("scripts.ai.c3_artifacts")
        self.assertEqual(r.returncode, 0, r.stderr[-600:])

    def test_05_build_ai_views_imports_cleanly(self):
        r = self._import_in_subprocess("scripts.ops.build_ai_views")
        self.assertEqual(r.returncode, 0, r.stderr[-600:])


class EntrypointTest(unittest.TestCase):
    """§五/§九"""

    def test_06_c3_module_entrypoint(self):
        """python -m scripts.ops.c3_run 必须可用（不需要任何 sys.path 魔法）"""
        r = _run(["-m", "scripts.ops.c3_run", "--help"])
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        self.assertIn("--root", r.stdout)
        r2 = _run(["-m", "scripts.ops.build_ai_views", "--help"])
        self.assertEqual(r2.returncode, 0, r2.stderr[-600:])

    def test_07_c3_runner_entrypoint_matches_github_actions(self):
        """与 workflow 完全相同的调用形式：从 repo root 用脚本路径执行，
        并且必须能真正走到 Localization 阶段（不是 import 就挂）。"""
        tmp = tempfile.mkdtemp(prefix="c3wiring_")
        for rel in ("data/canonical/articles.json", "data/canonical/event_clusters.json",
                    "data/views/news_stream.json", "data/status.json",
                    "data/sources.json", "data/views/country_snapshots.json",
                    "data/views/site_overview.json", "data/views/report_index.json",
                    "data/views/china_interest.json"):
            s = ROOT / rel
            d = Path(tmp) / rel
            d.parent.mkdir(parents=True, exist_ok=True)
            if s.exists():
                d.write_bytes(s.read_bytes())
        out = os.path.join(tmp, "run_probe.json")
        r = _run(["scripts/ops/c3_run.py", "--root", tmp, "--provider", "auto",
                  "--window-start", "2026-09-05", "--window-end", "2026-09-18",
                  "--batch-size", "10", "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertNotIn("ModuleNotFoundError", r.stderr)
        doc = json.loads(Path(out).read_text(encoding="utf-8"))
        # 进入 Localization 阶段（无凭据时为 0 次真实调用，但目标必须被扫出来）
        self.assertGreater(doc["localization"]["target"], 0)
        self.assertEqual(doc["ai_calls_total"], 0, "本地测试不得发生真实 AI 调用")
        self.assertFalse(doc["provider_ready"])          # 无 key → 明确 blocked
        # 硬编码开发机路径必须已移除
        src = (ROOT / "scripts" / "ops" / "c3_run.py").read_text(encoding="utf-8")
        self.assertNotIn('r"C://Users', src)
        self.assertIn("os.path.abspath(__file__)", src)


class NoHackGuardTest(unittest.TestCase):
    """§三：不得以"仅为 CI 凑通"的方式引入不可移植路径"""

    def test_08_no_hardcoded_machine_paths_in_c3_modules(self):
        for rel in ("scripts/ops/c3_run.py", "scripts/ops/build_ai_views.py",
                    "scripts/ai/c3_localization.py", "scripts/ai/c3_analysis.py",
                    "scripts/ai/c3_artifacts.py"):
            src = (ROOT / rel).read_text(encoding="utf-8")
            for bad in ('r"C://Users', '"/Users/', "'/Users/", 'r"C:/Users'):
                self.assertNotIn(bad, src, "%s contains a hardcoded machine path" % rel)

    def test_09_no_real_ai_calls_in_this_suite(self):
        """本套件全程不设 ASIP_DEEPSEEK_API_KEY，且只用 auto（无凭据短路）。"""
        self.assertNotIn("ASIP_DEEPSEEK_API_KEY", os.environ)
        r = _run(["-c", "import os; print('KEY=%s' % bool(os.environ.get('ASIP_DEEPSEEK_API_KEY')))"])
        self.assertIn("KEY=False", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
