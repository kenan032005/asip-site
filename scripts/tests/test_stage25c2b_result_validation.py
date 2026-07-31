#!/usr/bin/env python3
"""ASIP Stage 2.5C-2B — Core result validation tests"""

import json, os, sys, tempfile, shutil, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
REPO = os.path.dirname(SCRIPTS)

from ai.workbuddy_worker import claim_batch, ingest_results, _ensure_dirs
from ai.output_contracts import validate_business_output
from ai.task_prompt_binding import bind_task_to_prompt

def _write_json(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
def _read_json(p):
    with open(p, 'r', encoding='utf-8') as f: return json.load(f)
def _setup():
    r = tempfile.mkdtemp(prefix="c2b_")
    _ensure_dirs(r)
    return r

def _make_task(tid, ttype, input_ref, **kw):
    t = {"task_id": tid, "schema_version": "1.0", "task_type": ttype,
         "status": "queued", "priority": "high", "input_ref": input_ref,
         "content_hash": "abc", "prompt_version": "1.0.1",
         "output_schema_version": "1.1", "provider_requested": "workbuddy_queue",
         "created_at": "2026-08-01T00:00:00Z", "retry_count": 0,
         "max_retries": 1, "cache_key": "cache:" + tid, "synthetic": True}
    t.update(kw)
    return t

def _valid_aa():
    return {"summary_zh":"x","country_iso3":"NER","source_language":"en",
            "event_type":"road_closure","event_time":None,"locations":[],
            "actors":[],"key_facts":["f"],"source_claims":["c"],
            "casualties":{"confirmed":0,"reported":0,"unknown":True},
            "uncertainties":[],"china_relevance":"none","project_impact":"none",
            "security_relevance":0.5,"confidence":0.5,"synthetic":True}


class TestBinding(unittest.TestCase):
    """Task-to-prompt binding works end-to-end."""

    def test_bind_article_analysis(self):
        t = _make_task("AIT_111111111111111111111111", "article_analysis",
                       {"prompt_variables": {"source_text":"road","country_iso3":"NER","source_language":"en"}})
        b = bind_task_to_prompt(t)
        self.assertIn("system_text", b)
        self.assertIn("user_text", b)
        self.assertEqual(b["task_type"], "article_analysis")

    def test_prompt_binding_generates_files(self):
        root = _setup()
        try:
            tid = "AIT_111111111111111111111112"
            t = _make_task(tid, "article_analysis",
                           {"prompt_variables": {"source_text":"road","country_iso3":"NER","source_language":"en"}})
            _write_json(os.path.join(root, "queue", tid + ".json"), t)
            r = claim_batch(ai_root=root, batch_size=1, prompt_binding_enabled=True,
                            expected_model="deepseek-v4-flash")
            bid = r.get("batch_id")
            self.assertIsNotNone(bid, "claim should succeed: " + str(r.get("claim_error", "")))
            man = _read_json(os.path.join(root, "batches", bid, "manifest.json"))
            self.assertTrue(man.get("prompt_registry_validated"))
            pp = os.path.join(root, "batches", bid, "prompts", tid + ".prompt.json")
            self.assertTrue(os.path.exists(pp))
        finally:
            shutil.rmtree(root, ignore_errors=True)


class TestBusinessOutput(unittest.TestCase):
    """Business output schema validation."""

    def test_valid_output(self):
        ok, err = validate_business_output("article_analysis", _valid_aa(),
                                            prompt_version="1.0.1",
                                            output_schema_version="1.1")
        self.assertTrue(ok, msg=str(err))

    def test_invalid_output_missing_fields(self):
        ok, err = validate_business_output("article_analysis", {"summary_zh":"x"},
                                            prompt_version="1.0.1",
                                            output_schema_version="1.1")
        self.assertFalse(ok)

    def test_six_types_valid(self):
        examples = {
            "article_analysis": _valid_aa(),
            "source_comparison": {"compared_source_ids":["a"],"agreements":[],"conflicts":[],"unique_claims":[],"unresolved_facts":[],"source_quality_assessment":{},"recommended_fact_status":"unknown","confidence":0.5,"synthetic":True},
            "event_synthesis": {"event_summary_zh":"x","country_iso3":"NER","event_type":"road_closure","timeline":[],"confirmed_facts":["f"],"reported_claims":[],"contradictions":[],"unresolved_questions":[],"affected_locations":[],"potential_impacts":[],"confidence":0.5,"synthetic":True},
            "daily_security_brief": {"report_date":"2026-08-01","geographic_scope":"x","overall_assessment":"t","risk_direction":"stable","key_events":[],"risk_increases":[],"risk_decreases":[],"china_related_items":[],"project_operational_impacts":[],"management_attention":[],"information_gaps":[],"confidence":0.5,"synthetic":True},
            "trend_forecast": {"base_time":"2026-08-01T00:00Z","geographic_scope":"x","forecast_windows":[{"window":"24h","predictions":[{"prediction":"p","supporting_evidence":[],"probability":0.5,"uncertainty":"u"}]}],"likely_scenarios":[],"escalation_triggers":[],"deescalation_signals":[],"monitoring_priorities":[],"assumptions":[],"limitations":[],"confidence":0.5,"synthetic":True},
            "disease_risk_analysis": {"disease_name":"x","affected_countries":["NER"],"official_source_ids":["w"],"reporting_period":"2026","confirmed_case_data":{},"transmission_assessment":"l","cross_border_risk":"l","travel_impact":"n","project_site_impact":"n","medical_resource_impact":"n","recommended_precautions":[],"information_gaps":[],"confidence":0.5,"synthetic":True},
        }
        for tid, ex in examples.items():
            ok, err = validate_business_output(tid, ex, prompt_version="1.0.1", output_schema_version="1.1")
            self.assertTrue(ok, msg=tid + ": " + str(err[:3]))


class TestIsolation(unittest.TestCase):
    """Isolation checks."""

    def test_dist_no_prompts(self):
        self.assertFalse(os.path.isdir(os.path.join(REPO, "dist", "prompts")))

    def test_no_external_calls(self):
        c = open(os.path.join(SCRIPTS, "ai", "workbuddy_worker.py"), encoding='utf-8').read()
        self.assertNotIn("requests.", c)
        self.assertNotIn("openai", c)


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    p = result.testsRun - len(result.failures) - len(result.errors)
    f = len(result.failures) + len(result.errors)
    print(f"\nRESULT: PASS={p} FAIL={f}")
    sys.exit(0 if f == 0 else 1)
