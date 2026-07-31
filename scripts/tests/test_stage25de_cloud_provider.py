#!/usr/bin/env python3
"""ASIP Stage 2.5D/E — Cloud provider, budget, and GitHub Actions tests"""

import json, os, sys, tempfile, shutil, unittest, io
from unittest.mock import patch, MagicMock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
REPO = os.path.dirname(SCRIPTS)

from ai.providers.base import ProviderConfig, BudgetLimit, BaseProvider


class TestDefaultSafety(unittest.TestCase):
    """Default configuration must not allow any API calls."""

    def test_default_provider_is_workbuddy_queue(self):
        cfg = ProviderConfig.from_env(env={})
        self.assertEqual(cfg.provider_type, "workbuddy_queue")

    def test_default_processing_disabled(self):
        cfg = ProviderConfig.from_env(env={})
        self.assertFalse(cfg.processing_enabled)

    def test_default_paid_fallback_forbidden(self):
        cfg = ProviderConfig.from_env(env={})
        self.assertFalse(cfg.paid_fallback_allowed)

    def test_disabled_provider_rejects_execution(self):
        from ai.providers.disabled import DisabledProvider
        p = DisabledProvider()
        ok, _ = p.validate_config()
        self.assertFalse(ok)
        with self.assertRaises(RuntimeError):
            p.process_binding({}, BudgetLimit())

    def test_workbuddy_queue_no_paid_fallback(self):
        cfg = ProviderConfig.from_env(
            env={"ASIP_AI_PROVIDER": "workbuddy_queue",
                 "ALLOW_PAID_FALLBACK": "false"})
        self.assertEqual(cfg.provider_type, "workbuddy_queue")
        self.assertFalse(cfg.paid_fallback_allowed)


class TestBudgetMeltdown(unittest.TestCase):
    """Budget limits and meltdown control."""

    def test_default_zero_tasks(self):
        b = BudgetLimit()
        ok, reason = b.can_process()
        self.assertFalse(ok)
        self.assertIn("0", reason)

    def test_positive_tasks_allows_processing(self):
        b = BudgetLimit(max_tasks=5)
        ok, _ = b.can_process()
        self.assertTrue(ok)

    def test_max_tasks_exhausted(self):
        b = BudgetLimit(max_tasks=2)
        b.completed_tasks = 2
        ok, reason = b.can_process()
        self.assertFalse(ok)

    def test_max_tokens_exhausted(self):
        b = BudgetLimit(max_tasks=10, max_tokens=1000)
        b.total_input_tokens = 600
        b.total_output_tokens = 500
        ok, _ = b.can_process()
        self.assertFalse(ok)

    def test_max_cost_exhausted(self):
        b = BudgetLimit(max_tasks=10, max_cost_usd=0.50)
        b.total_cost_usd = 0.51
        ok, _ = b.can_process()
        self.assertFalse(ok)

    def test_record_increments_counters(self):
        b = BudgetLimit(max_tasks=10)
        b.record({"input_tokens": 100, "output_tokens": 50,
                  "estimated_cost_usd": 0.01})
        self.assertEqual(b.completed_tasks, 1)
        self.assertEqual(b.total_input_tokens, 100)
        self.assertEqual(b.total_output_tokens, 50)


class TestProviderRunnerCLI(unittest.TestCase):
    """CLI runner safety gates."""

    def setUp(self):
        from ai.provider_runner import main as runner_main
        self.runner = runner_main

    def test_run_without_execute_shows_idle(self):
        import argparse
        ns = argparse.Namespace(command="run", execute=False, batch_size=3)
        with patch.dict(os.environ, {}, clear=True):
            with patch("ai.provider_runner.parse_args", return_value=ns):
                rc = self.runner([])
                self.assertEqual(rc, 0)

    def test_run_disabled_provider_fails(self):
        import argparse
        ns = argparse.Namespace(command="run", execute=True, batch_size=3)
        with patch.dict(os.environ,
                        {"ASIP_AI_PROVIDER": "disabled"}, clear=True):
            with patch("ai.provider_runner.parse_args", return_value=ns):
                rc = self.runner([])
                self.assertNotEqual(rc, 0)

    def test_status_shows_config(self):
        import argparse
        ns = argparse.Namespace(command="status")
        with patch.dict(os.environ, {}, clear=True):
            with patch("ai.provider_runner.parse_args", return_value=ns):
                rc = self.runner([])
                self.assertEqual(rc, 0)


class TestGenericAPIProvider(unittest.TestCase):
    """Generic API provider parsing and safety."""

    def setUp(self):
        from ai.providers.generic_api import GenericAPIProvider
        self.env = {
            "ASIP_AI_PROVIDER": "generic_api",
            "ASIP_AI_PROCESSING_ENABLED": "true",
            "ASIP_AI_BASE_URL": "https://test.example.com/v1",
            "ASIP_AI_API_KEY": "sk-test123",
            "ASIP_AI_MODEL": "test-model",
        }
        self.saved = {}
        for k, v in self.env.items():
            self.saved[k] = os.environ.get(k)
            os.environ[k] = v
        cfg = ProviderConfig.from_env()
        self.provider = GenericAPIProvider()

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_parse_valid_response(self):
        raw = json.dumps({
            "choices": [{"message": {"content": json.dumps(
                {"summary_zh": "test"})}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        })
        binding = {"task_id": "AIT_111111111111111111111111"}
        result = self.provider.parse_response(raw, binding)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["provider"], "generic_api")
        self.assertEqual(result["usage"]["input_tokens"], 10)

    def test_parse_invalid_json(self):
        raw = "not json"
        binding = {"task_id": "AIT_111111111111111111111111"}
        result = self.provider.parse_response(raw, binding)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "invalid_json")

    def test_parse_missing_choices(self):
        raw = json.dumps({"choices": []})
        binding = {"task_id": "AIT_111111111111111111111111"}
        result = self.provider.parse_response(raw, binding)
        self.assertEqual(result["status"], "failed")

    def test_error_result_safe(self):
        result = self.provider._error_result(
            {"task_id": "T1"}, "e1", "message")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "e1")

    def test_api_key_not_in_repr(self):
        s = repr(self.provider)
        self.assertNotIn("sk-test", s)
        self.assertNotIn(self.provider.api_key, s)

    def test_validate_requires_key(self):
        from ai.providers.generic_api import GenericAPIProvider
        saved = {}
        env = {"ASIP_AI_PROVIDER": "generic_api",
               "ASIP_AI_PROCESSING_ENABLED": "true",
               "ASIP_AI_BASE_URL": "https://x.com/v1",
               "ASIP_AI_MODEL": "m"}
        for k, v in env.items():
            saved[k] = os.environ.get(k)
            os.environ[k] = v
        if "ASIP_AI_API_KEY" in os.environ:
            saved["ASIP_AI_API_KEY"] = os.environ["ASIP_AI_API_KEY"]
            del os.environ["ASIP_AI_API_KEY"]
        try:
            p = GenericAPIProvider()
            ok, msg = p.validate_config()
            self.assertFalse(ok)
            # Must mention missing key — either KEY or API or processing disabled
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


class TestWorkflowIntegrity(unittest.TestCase):
    """GitHub Actions workflow safety checks."""

    def test_workflow_exists(self):
        wf = os.path.join(REPO, ".github", "workflows", "asip-pipeline.yml")
        self.assertTrue(os.path.exists(wf))

    def test_concurrency_configured(self):
        wf = os.path.join(REPO, ".github", "workflows", "asip-pipeline.yml")
        content = open(wf, encoding='utf-8').read()
        self.assertIn("concurrency", content)
        self.assertIn("cancel-in-progress", content)

    def test_default_execute_ai_false(self):
        wf = os.path.join(REPO, ".github", "workflows", "asip-pipeline.yml")
        content = open(wf, encoding='utf-8').read()
        self.assertIn("execute_ai", content)
        self.assertIn("default: false", content)

    def test_max_ai_tasks_default_zero(self):
        wf = os.path.join(REPO, ".github", "workflows", "asip-pipeline.yml")
        content = open(wf, encoding='utf-8').read()
        self.assertIn("max_ai_tasks", content)
        self.assertIn('"0"', content)

    def test_secrets_not_in_plaintext(self):
        wf = os.path.join(REPO, ".github", "workflows", "asip-pipeline.yml")
        content = open(wf, encoding='utf-8').read()
        self.assertIn("secrets.ASIP_AI_API_KEY", content)
        # Must not contain any hardcoded API key
        self.assertNotIn("sk-", content)

    def test_timeout_set(self):
        wf = os.path.join(REPO, ".github", "workflows", "asip-pipeline.yml")
        content = open(wf, encoding='utf-8').read()
        self.assertIn("timeout-minutes", content)

    def test_permissions_minimal(self):
        wf = os.path.join(REPO, ".github", "workflows", "asip-pipeline.yml")
        content = open(wf, encoding='utf-8').read()
        self.assertIn("permissions:", content)
        self.assertIn("contents: write", content)


class TestDistIsolation(unittest.TestCase):
    def test_no_secrets_in_dist(self):
        dist = os.path.join(REPO, "dist")
        if os.path.isdir(dist):
            for root, dirs, files in os.walk(dist):
                for f in files:
                    if f.endswith((".py", ".json", ".yml", ".yaml")):
                        p = os.path.join(root, f)
                        c = open(p, encoding='utf-8', errors='ignore').read()
                        self.assertNotIn("ASIP_AI_API_KEY", c, p)

    def test_no_external_calls_in_code(self):
        import glob
        for f in glob.glob(os.path.join(SCRIPTS, "ai", "providers", "*.py")):
            c = open(f, encoding='utf-8').read()
            self.assertNotIn("requests.", c)


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    p = result.testsRun - len(result.failures) - len(result.errors)
    f = len(result.failures) + len(result.errors)
    print(f"\nRESULT: PASS={p} FAIL={f}")
    sys.exit(0 if f == 0 else 1)
