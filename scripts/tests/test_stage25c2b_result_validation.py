#!/usr/bin/env python3
"""ASIP Stage 2.5C-2B — Result validation and end-to-end tests"""

import json, os, sys, shutil, tempfile, unittest, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
REPO = os.path.dirname(SCRIPTS)

from ai.workbuddy_worker import claim_batch, ingest_results, _ensure_dirs
from ai.output_contracts import validate_business_output

def _write_json(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
def _read_json(p):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)
def _setup_root():
    r = tempfile.mkdtemp(prefix="asip_2b_")
    _ensure_dirs(r)
    for d in ("batches","leases","locks","audit"):
        os.makedirs(os.path.join(r, d), exist_ok=True)
    return r

def _make_task(tid, ttype, input_ref, **kw):
    t = {
        "task_id": tid, "schema_version": "1.0", "task_type": ttype,
        "status": "queued", "priority": "high", "input_ref": input_ref,
        "content_hash": "abc", "prompt_version": "1.0.1",
        "output_schema_version": "1.1", "provider_requested": "workbuddy_queue",
        "created_at": "2026-08-01T00:00:00Z", "retry_count": 0,
        "max_retries": 1, "cache_key": "cache:" + tid, "synthetic": True,
    }
    t.update(kw)
    return t

class TestClaimCLI(unittest.TestCase):
    """CLI claim generates prompt files."""

    def test_claim_generates_prompts(self):
        root = _setup_root()
        try:
            t = _make_task("AIT_aaaaaaaaaaaaaaaaaaaaaaaa", "article_analysis",
                           {"prompt_variables": {"source_text":"road","country_iso3":"NER","source_language":"en"}})
            _write_json(os.path.join(root, "queue", "AIT_d943465a0617f3df943f472c.json"), t)

            result = claim_batch(ai_root=root, batch_size=1,
                                 prompt_binding_enabled=True)
            bid = result.get("batch_id")
            self.assertIsNotNone(bid)

            man = _read_json(os.path.join(root, "batches", bid, "manifest.json"))
            self.assertTrue(man.get("prompt_registry_validated"))
            prompt_path = os.path.join(root, "batches", bid,
                                       "prompts", "AIT_d943465a0617f3df943f472c.prompt.json")
            self.assertTrue(os.path.exists(prompt_path))

            # Check WORKBUDDY_REQUEST has prompt_file references
            req = open(os.path.join(root, "batches", bid, "WORKBUDDY_REQUEST.md"),
                       encoding='utf-8').read()
            self.assertIn("prompt_file", req)
            # must NOT contain full prompt text
            self.assertNotIn("Core Safety Rules", req)
        finally:
            shutil.rmtree(root, ignore_errors=True)


class TestResultValidation(unittest.TestCase):
    """Dual-layer result validation."""

    def _full_claim(self, root):
        t = _make_task("AIT_91e7e433e34c3b8843334c14", "article_analysis",
                       {"prompt_variables": {"source_text":"road","country_iso3":"NER","source_language":"en"}})
        _write_json(os.path.join(root, "queue", "AIT_91e7e433e34c3b8843334c14.json"), t)
        r = claim_batch(ai_root=root, batch_size=1, prompt_binding_enabled=True)
        return r["batch_id"]

    def _make_result(self, bid, tid, status="success", result=None, provider="workbuddy_queue", model="deepseek-v4-flash"):
        res = {
            "batch_id": bid,
            "worker_id": "workbuddy-local",
            "results": [{
                "task_id": tid,
                "schema_version": "1.0",
                "status": status,
                "provider": provider,
                "model": model,
                "started_at": "2026-08-01T00:01:00Z",
                "completed_at": "2026-08-01T00:02:00Z",
                "usage": {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0},
            }]
        }
        if result is not None:
            res["results"][0]["result"] = result
        if status == "failed":
            res["results"][0]["error"] = {"code": "test_error", "message": "test"}
        return res

    def _valid_aa_output(self):
        return {"summary_zh":"x","country_iso3":"NER","source_language":"en",
                "event_type":"road_closure","event_time":None,"locations":[],
                "actors":[],"key_facts":["f"],"source_claims":["c"],
                "casualties":{"confirmed":0,"reported":0,"unknown":True},
                "uncertainties":[],"china_relevance":"none","project_impact":"none",
                "security_relevance":0.5,"confidence":0.5,"synthetic":True}

    def test_valid_result_completes(self):
        root = _setup_root()
        try:
            bid = self._full_claim(root)
            tid = "AIT_91e7e433e34c3b8843334c14"
            result_data = self._make_result(bid, tid, result=self._valid_aa_output())
            rf = os.path.join(root, "batches", bid, "result.json")
            _write_json(rf, result_data)

            rep = ingest_results(root, bid, rf)
            self.assertEqual(rep["accepted"], 1)
            self.assertIn(tid, rep["accepted_task_ids"])

            # Check provenance in completed
            comp = _read_json(os.path.join(root, "completed", tid + ".json"))
            self.assertIn("provenance", comp)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_invalid_business_output_rejected(self):
        root = _setup_root()
        try:
            bid = self._full_claim(root)
            tid = "AIT_91e7e433e34c3b8843334c14"
            bad_result = {"summary_zh":"missing fields"}
            result_data = self._make_result(bid, tid, result=bad_result)
            rf = os.path.join(root, "batches", bid, "result.json")
            _write_json(rf, result_data)

            rep = ingest_results(root, bid, rf)
            self.assertEqual(rep["accepted"], 0)
            self.assertIn(tid, rep["rejected_task_ids"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_provider_mismatch_rejected(self):
        root = _setup_root()
        try:
            bid = self._full_claim(root)
            tid = "AIT_91e7e433e34c3b8843334c14"
            result_data = self._make_result(bid, tid, provider="wrong_provider", result=self._valid_aa_output())
            rf = os.path.join(root, "batches", bid, "result.json")
            _write_json(rf, result_data)

            rep = ingest_results(root, bid, rf)
            self.assertEqual(rep["accepted"], 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_invalid_ai_result_rejected(self):
        root = _setup_root()
        try:
            bid = self._full_claim(root)
            tid = "AIT_91e7e433e34c3b8843334c14"
            bad = {"batch_id": bid, "worker_id": "workbuddy-local", "results": [{"task_id": tid}]}
            rf = os.path.join(root, "batches", bid, "result.json")
            _write_json(rf, bad)

            rep = ingest_results(root, bid, rf)
            self.assertEqual(rep["accepted"], 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_idempotent_reingest(self):
        root = _setup_root()
        try:
            bid = self._full_claim(root)
            tid = "AIT_91e7e433e34c3b8843334c14"
            result_data = self._make_result(bid, tid, result=self._valid_aa_output())
            rf = os.path.join(root, "batches", bid, "result.json")
            _write_json(rf, result_data)

            r1 = ingest_results(root, bid, rf)
            r2 = ingest_results(root, bid, rf)
            self.assertEqual(r1["accepted"], 1)
            # second ingest should be idempotent
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_dist_no_prompts(self):
        self.assertFalse(os.path.exists(os.path.join(REPO, "dist", "prompts")))

    def test_no_external_calls(self):
        for m in ["workbuddy_worker.py"]:
            c = open(os.path.join(SCRIPTS, "ai", m), encoding='utf-8').read()
            self.assertNotIn("requests.", c)
            self.assertNotIn("openai", c)
            self.assertNotIn("anthropic", c)


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    p = result.testsRun - len(result.failures) - len(result.errors)
    f = len(result.failures) + len(result.errors)
    print(f"\nRESULT: PASS={p} FAIL={f}")
    sys.exit(0 if f == 0 else 1)
