#!/usr/bin/env python3
"""ASIP Stage 2.5C-2A — Prompt binding tests"""

import json, os, sys, shutil, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
REPO = os.path.dirname(SCRIPTS)

from ai.task_prompt_binding import (
    bind_task_to_prompt, build_batch_prompt_files,
    BindingError, ERR,
)
from ai.workbuddy_worker import claim_batch, _ensure_dirs
from ai.workbuddy_queue_provider import _ensure_ai_dirs

def _make_task(task_id, task_type, prompt_version="1.0.1",
               output_schema_version="1.1", input_ref=None,
               cache_key=None, **kw):
    t = {
        "task_id": task_id,
        "schema_version": "1.0",
        "task_type": task_type,
        "status": "queued",
        "priority": "high",
        "input_ref": input_ref or {},
        "content_hash": "abc123",
        "prompt_version": prompt_version,
        "output_schema_version": output_schema_version,
        "provider_requested": "workbuddy_queue",
        "created_at": "2026-07-31T00:00:00Z",
        "retry_count": 0,
        "max_retries": 1,
        "cache_key": cache_key or ("cache:" + task_id),
        "synthetic": True,
    }
    t.update(kw)
    return t

def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _setup_temp_ai_root():
    root = tempfile.mkdtemp(prefix="asip_c2a_")
    _ensure_ai_dirs(root)
    for d in ("batches","leases","locks","audit"):
        os.makedirs(os.path.join(root,d), exist_ok=True)
    return root


class TestBinding(unittest.TestCase):
    """B1-B7: Task-to-prompt binding tests."""

    def test_article_analysis_binds(self):
        """B3: article_analysis binds successfully."""
        task = _make_task("AIT_000000000000000000000001", "article_analysis",
                          input_ref={"prompt_variables": {
                              "source_text":"road closed","country_iso3":"NER",
                              "source_language":"en"}})
        b = bind_task_to_prompt(task)
        self.assertEqual(b["task_type"], "article_analysis")
        self.assertEqual(b["input_mapping_mode"], "nested_prompt_variables")

    def test_all_six_types_bind(self):
        """B4: All 6 task types bind."""
        cases = {
            "article_analysis": {"prompt_variables":{"source_text":"x","country_iso3":"NER","source_language":"en"}},
            "source_comparison": {"prompt_variables":{"source_a":"a","source_b":"b","country_iso3":"NER"}},
            "event_synthesis": {"prompt_variables":{"articles":"[]","country_iso3":"NER"}},
            "daily_security_brief": {"prompt_variables":{"report_date":"2026-08-01","events":"[]","geographic_scope":"x"}},
            "trend_forecast": {"prompt_variables":{"historical_events":"[]","geographic_scope":"x"}},
            "disease_risk_analysis": {"prompt_variables":{"disease_reports":"[]","country_iso3":"NER"}},
        }
        for tid, pv in cases.items():
            task = _make_task("AIT_" + "0"*22 + tid[:2], tid, input_ref=pv)
            b = bind_task_to_prompt(task)
            self.assertIsNotNone(b["system_text"], tid)

    def test_nested_mode(self):
        """B5: nested_prompt_variables mode."""
        task = _make_task("AIT_000000000000000000000011", "article_analysis",
                          input_ref={
                              "prompt_variables": {"source_text":"x","country_iso3":"NER","source_language":"en"},
                              "source_refs": ["extra"],
                              "metadata": {"scenario_id": "test"}
                          })
        b = bind_task_to_prompt(task)
        self.assertEqual(b["input_mapping_mode"], "nested_prompt_variables")
        # extra metadata must not enter prompt
        self.assertNotIn("scenario_id", b["user_text"])

    def test_legacy_mode(self):
        """B6: legacy_flat_allowlist mode."""
        task = _make_task("AIT_000000000000000000000012", "article_analysis",
                          input_ref={
                              "source_text": "legacy_data",
                              "country_iso3": "NER",
                              "source_language": "en",
                              "scenario_id": "old_test",
                          })
        b = bind_task_to_prompt(task)
        self.assertEqual(b["input_mapping_mode"], "legacy_flat_allowlist")
        self.assertIn("legacy_data", b["user_text"])

    def test_missing_required_fails(self):
        """B8: Missing required variable fails."""
        task = _make_task("AIT_000000000000000000000013", "article_analysis",
                          input_ref={"prompt_variables": {"country_iso3":"NER"}})
        with self.assertRaises(BindingError):
            bind_task_to_prompt(task)

    def test_unknown_version_fails(self):
        """B9: Unregistered prompt_version fails."""
        task = _make_task("AIT_000000000000000000000014", "article_analysis",
                          prompt_version="99.99.99",
                          input_ref={"prompt_variables":{"source_text":"x","country_iso3":"NER","source_language":"en"}})
        with self.assertRaises(BindingError):
            bind_task_to_prompt(task)

    def test_schema_version_mismatch(self):
        """B10: output_schema_version mismatch fails."""
        task = _make_task("AIT_000000000000000000000015", "article_analysis",
                          output_schema_version="9.9",
                          input_ref={"prompt_variables":{"source_text":"x","country_iso3":"NER","source_language":"en"}})
        with self.assertRaises(BindingError):
            bind_task_to_prompt(task)

    def test_checksum_matches_renderer(self):
        """B12: prompt_checksum matches Renderer."""
        task = _make_task("AIT_000000000000000000000016", "article_analysis",
                          input_ref={"prompt_variables":{"source_text":"match test","country_iso3":"NER","source_language":"en"}})
        b = bind_task_to_prompt(task)
        from ai.prompt_renderer import render_prompt
        r = render_prompt("article_analysis", {"source_text":"match test","country_iso3":"NER","source_language":"en"})
        self.assertEqual(b["prompt_checksum"], r["prompt_checksum"])

    def test_render_hash_stable(self):
        """B13: render_hash is stable."""
        task = _make_task("AIT_000000000000000000000017", "article_analysis",
                          input_ref={"prompt_variables":{"source_text":"hash test","country_iso3":"NER","source_language":"en"}})
        b1 = bind_task_to_prompt(task)
        b2 = bind_task_to_prompt(task)
        self.assertEqual(b1["render_hash"], b2["render_hash"])

    def test_variables_digest_stable(self):
        """B14: variables_digest is stable."""
        task = _make_task("AIT_000000000000000000000018", "article_analysis",
                          input_ref={"prompt_variables":{"source_text":"digest","country_iso3":"NER","source_language":"en"}})
        b1 = bind_task_to_prompt(task)
        b2 = bind_task_to_prompt(task)
        self.assertEqual(b1["prompt_variables_digest"], b2["prompt_variables_digest"])

    def test_no_absolute_paths_in_binding(self):
        """B22: Binding contains no absolute paths."""
        task = _make_task("AIT_000000000000000000000019", "article_analysis",
                          input_ref={"prompt_variables":{"source_text":"x","country_iso3":"NER","source_language":"en"}})
        b = bind_task_to_prompt(task)
        binding_str = json.dumps(b)
        self.assertNotIn(REPO.replace("\\","\\\\"), binding_str)


class TestClaimPrecheck(unittest.TestCase):
    """B15-B17: Claim pre-check with prompt binding."""

    def test_claim_fails_on_bad_task(self):
        """B16-B17: Claim fails on invalid prompt task, queue unchanged."""
        root = _setup_temp_ai_root()
        try:
            bad_task = _make_task("AIT_000000000000000000000020", "article_analysis",
                                  prompt_version="99.99.99",
                                  input_ref={"prompt_variables":{"source_text":"x","country_iso3":"NER","source_language":"en"}})
            _write_json(os.path.join(root, "queue", "AIT_000000000000000000000020.json"), bad_task)

            result = claim_batch(ai_root=root, batch_size=1,
                                 expected_provider="workbuddy_queue",
                                 expected_model="deepseek-v4-flash",
                                 prompt_binding_enabled=True)
            self.assertIsNone(result.get("batch_id"))
            if "claim_error" in result:
                self.assertIn("prompt", result["claim_error"]["code"])

            from ai.workbuddy_worker import status_summary
            st = status_summary(root)
            self.assertEqual(st["queue"], 1)
            self.assertEqual(st["processing"], 0)
            self.assertEqual(st["leases"], 0)
            self.assertEqual(st["batches"], 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_valid_claim_generates_prompts(self):
        """B18: Valid claim generates prompt files and manifest entries."""
        root = _setup_temp_ai_root()
        try:
            task = _make_task("AIT_000000000000000000000021", "article_analysis",
                              input_ref={"prompt_variables":{"source_text":"road","country_iso3":"NER","source_language":"en"}})
            _write_json(os.path.join(root, "queue", "AIT_000000000000000000000021.json"), task)

            result = claim_batch(ai_root=root, batch_size=1,
                                 expected_provider="workbuddy_queue",
                                 expected_model="deepseek-v4-flash",
                                 prompt_binding_enabled=True)
            self.assertIsNotNone(result.get("batch_id"))
            bid = result["batch_id"]

            # Check prompt file exists
            prompt_path = os.path.join(root, "batches", bid,
                                       "prompts", "AIT_000000000000000000000021.prompt.json")
            self.assertTrue(os.path.exists(prompt_path))

            # Check manifest has prompt metadata
            manifest_path = os.path.join(root, "batches", bid, "manifest.json")
            with open(manifest_path, encoding='utf-8') as f:
                manifest = json.load(f)
            self.assertTrue(manifest.get("prompt_registry_validated"))
            self.assertIn("tasks", manifest)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    failed = len(result.failures) + len(result.errors)
    print(f"\nRESULT: PASS={passed} FAIL={failed}")
    sys.exit(0 if failed == 0 else 1)
