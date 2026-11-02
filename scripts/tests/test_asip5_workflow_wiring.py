#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 — GitHub Actions 接线最小测试（不依赖 PyYAML，纯文本断言）。"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CANDIDATES = [ROOT / ".github" / "workflows" / "asip-production-orchestrator.yml",
              ROOT / "release" / "patched" / "asip-production-orchestrator.yml"]


def _path():
    for p in CANDIDATES:
        if p.exists():
            return p
    return None


class TestOrchestratorWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = _path()
        if p is None:
            raise unittest.SkipTest("orchestrator workflow not present in this branch")
        cls.path = p
        cls.text = p.read_text(encoding="utf-8").replace("\r\n", "\n")

    def _step_block(self, name_prefix):
        """取某步骤到下一个同级步骤之间的文本。"""
        i = self.text.index("- name: " + name_prefix)
        j = self.text.find("\n      - name:", i + 10)
        return self.text[i:j if j > 0 else len(self.text)]

    def test_job_level_gate_skips_automatic_when_locked(self):
        m = re.search(r"\n    if: >-\n((?:      .*\n)+)", self.text)
        self.assertIsNotNone(m, "job 级 if 必须存在")
        cond = " ".join(m.group(1).split())
        self.assertIn("github.event_name == 'workflow_dispatch'", cond)
        self.assertIn("vars.ASIP_ALLOW_AUTOMATIC_RUNS == '1'", cond,
                      "自动触发必须在 Job 层 skip，绝不进入步骤解析空 orch.json")

    def test_dispatch_defaults_to_shadow_not_production(self):
        m = re.search(r"ASIP_RUN_MODE: (.+)", self.text)
        self.assertIsNotNone(m)
        expr = m.group(1)
        self.assertIn("github.event_name == 'workflow_dispatch'", expr)
        self.assertIn("'shadow'", expr, "人工 dispatch 缺 run_mode 必须默认 shadow")
        self.assertIn("|| 'production'", expr)

    def test_empty_orch_json_gets_placeholder(self):
        blk = self._step_block("Run due-task")
        self.assertIn("/tmp/orch_state_failure", blk)
        self.assertIn('"mode":"noop"', blk, "早退路径必须补最小 JSON")

    def test_final_checkpoint_skipped_for_shadow_and_noop(self):
        blk = self._step_block("Commit state")
        self.assertIn("steps.orch.outputs.run_mode != 'shadow'", blk)
        self.assertIn("steps.orch.outputs.executed_count != '0'", blk)

    def test_strike_only_on_state_failure_marker(self):
        blk = self._step_block("Trip breaker")
        self.assertIn("failure()", blk)
        self.assertIn("/tmp/orch_state_failure", blk,
                      "未授权/非法模式等拒绝路径不得造成误熔断")

    def test_pins_are_exact_and_uniform(self):
        wf_dir = self.path.parent
        pins = {}
        for f in sorted(wf_dir.glob("asip-production-*.yml")):
            t = f.read_text(encoding="utf-8").replace("\r\n", "\n")
            found = set(re.findall(r"ref://s*([0-9a-f]{7,40})//b", t))
            if found:
                pins[f.name] = found
        if not pins:
            self.skipTest("no code pins in this tree")
        allsha = {s for v in pins.values() for s in v}
        self.assertEqual(len(allsha), 1, "pin 必须一致：%s" % pins)
        self.assertTrue(all(len(s) == 40 for s in allsha), "pin 必须是完整 40 位 SHA")


if __name__ == "__main__":
    unittest.main(verbosity=2)
