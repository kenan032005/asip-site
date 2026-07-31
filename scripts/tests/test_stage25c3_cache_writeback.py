#!/usr/bin/env python3
"""ASIP Stage 2.5C-3 — Cache and writeback tests"""

import json, os, sys, shutil, tempfile, copy, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
REPO = os.path.dirname(SCRIPTS)

from ai.workbuddy_worker import claim_batch, ingest_results, _ensure_dirs
from ai.ai_result_cache import write_cache_entry, get_cache_entry, check_cache_hit, set_ai_root

def _write_json(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
def _read_json(p):
    with open(p, 'r', encoding='utf-8') as f: return json.load(f)

_VALID_AA = {"summary_zh":"x","country_iso3":"NER","source_language":"en",
    "event_type":"road_closure","event_time":None,"locations":[],"actors":[],
    "key_facts":["f"],"source_claims":["c"],
    "casualties":{"confirmed":0,"reported":0,"unknown":True},
    "uncertainties":[],"china_relevance":"none","project_impact":"none",
    "security_relevance":0.5,"confidence":0.5,"synthetic":True}

def _task(tid, tt="article_analysis", cache_key=None, **kw):
    t = {"task_id":tid,"schema_version":"1.0","task_type":tt,
         "status":"queued","priority":"high",
         "input_ref":{"prompt_variables":{"source_text":"road","country_iso3":"NER","source_language":"en"}},
         "content_hash":"abc","prompt_version":"1.0.1",
         "output_schema_version":"1.1","provider_requested":"workbuddy_queue",
         "created_at":"2026-08-01T00:00:00Z","retry_count":0,"max_retries":1,
         "cache_key":cache_key or ("cache:"+tid),"synthetic":True}
    t.update(kw)
    return t


class TestCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="c3c_")
        set_ai_root(self.tmp)

    def tearDown(self):
        set_ai_root(None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_write_and_read_valid(self):
        t = _task("AIT_855316cd7bda03ad6642e267")
        prov = {"prompt_checksum":"cs","render_hash":"rh","prompt_variables_digest":"vd"}
        write_cache_entry(t, _VALID_AA, prov, "2026-08-01T00:00:00Z")
        hit, entry, reason = check_cache_hit(t)
        self.assertTrue(hit, reason)

    def test_content_hash_mismatch_miss(self):
        t = _task("AIT_d029a4917dcf788f598b0532")
        prov = {"prompt_checksum":"cs","render_hash":"rh","prompt_variables_digest":"vd"}
        write_cache_entry(t, _VALID_AA, prov, "2026-08-01T00:00:00Z")
        t_bad = copy.deepcopy(t)
        t_bad["content_hash"] = "changed"
        hit, _, reason = check_cache_hit(t_bad)
        self.assertFalse(hit)
        self.assertEqual(reason, "content_hash_changed")

    def test_corrupt_cache_miss(self):
        from ai.ai_result_cache import _cache_path
        t = _task("AIT_36f9621a7549c8aac00a3247", cache_key="ck:corrupt")
        path = _cache_path("ck:corrupt")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f: f.write("not json")
        hit, _, _ = check_cache_hit(t)
        self.assertFalse(hit)

    def test_cache_hit_in_claim(self):
        # Full claim → ingest → populate cache → re-claim hits cache
        t = _task("AIT_888b175a6f8fb2d74545d3f1", cache_key="ck:e2e")
        _ensure_dirs(self.tmp)
        _write_json(os.path.join(self.tmp,"queue","AIT_888b175a6f8fb2d74545d3f1.json"), t)
        cr = claim_batch(ai_root=self.tmp, batch_size=1, prompt_binding_enabled=True,
                         expected_model="deepseek-v4-flash")
        self.assertIsNotNone(cr.get("batch_id"), str(cr.get("claim_error","")))
        bid = cr["batch_id"]
        rd = {"batch_id":bid,"worker_id":"workbuddy-local","results":[{
            "task_id":"AIT_888b175a6f8fb2d74545d3f1","schema_version":"1.0",
            "status":"success","provider":"workbuddy_queue","model":"deepseek-v4-flash",
            "started_at":"2026-08-01T00:01:00Z","completed_at":"2026-08-01T00:02:00Z",
            "usage":{"input_tokens":0,"output_tokens":0,"estimated_cost_usd":0},
            "error":None,"result":_VALID_AA}]}
        _write_json(os.path.join(self.tmp,"batches",bid,"result.json"), rd)
        rep = ingest_results(self.tmp, bid, os.path.join(self.tmp,"batches",bid,"result.json"))
        self.assertEqual(rep["accepted"], 1)

        # Re-claim with same cache_key → cache hit
        t2 = copy.deepcopy(t)
        t2["task_id"] = "AIT_71f59f819e36786338ed8be2"
        _write_json(os.path.join(self.tmp,"queue","AIT_71f59f819e36786338ed8be2.json"), t2)
        cr2 = claim_batch(ai_root=self.tmp, batch_size=1, prompt_binding_enabled=True,
                          expected_model="deepseek-v4-flash")
        self.assertEqual(cr2.get("cache_hits", 0), 1)


class TestWriteback(unittest.TestCase):
    """W1-W5: Writeback policy and validation tests."""

    def test_writeback_policy_enriches_fields(self):
        from ai.ai_writeback import execute_writeback, _make_provenance
        prov = _make_provenance(
            {"task_id":"t1","task_type":"article_analysis","content_hash":"abc",
             "prompt_version":"1.0.1","output_schema_version":"1.1"},
            {"prompt_checksum":"cs","render_hash":"rh",
             "prompt_variables_digest":"vd","provider":"x","model":"y",
             "batch_id":"b"},
            False)
        self.assertIn("task_id", prov)
        self.assertIn("prompt_checksum", prov)
        self.assertNotIn("system_text", json.dumps(prov))
        self.assertEqual(prov["cache_hit"], False)

    def test_writeback_validation_rejects_bad_target(self):
        from ai.ai_writeback import _validate_target, WritebackError
        task = {"task_type":"article_analysis",
                "input_ref":{"writeback":{"target_type":"event_cluster",
                                          "target_id":"EVT_x"}}}
        with self.assertRaises(WritebackError):
            _validate_target(task, task["input_ref"]["writeback"])

    def test_no_writeback_skips(self):
        from ai.ai_writeback import execute_writeback
        task = {"task_type":"article_analysis","input_ref":{}}
        r = execute_writeback(task, {}, {})
        self.assertFalse(r["written"])

    def test_unknown_task_type_no_writeback(self):
        from ai.ai_writeback import _ALLOWED_MAP
        self.assertNotIn("daily_security_brief", _ALLOWED_MAP)
        self.assertNotIn("disease_risk_analysis", _ALLOWED_MAP)  


class TestIsolation(unittest.TestCase):
    def test_cache_not_in_dist(self):
        self.assertFalse(os.path.isdir(os.path.join(REPO,"dist","data","ai","cache")))

    def test_no_external_calls(self):
        for m in ["ai_result_cache.py","ai_writeback.py"]:
            c = open(os.path.join(SCRIPTS,"ai",m),encoding='utf-8').read()
            self.assertNotIn("requests.", c)

    def test_production_canonical_unchanged(self):
        pth = os.path.join(REPO,"data","canonical","articles.json")
        if os.path.exists(pth):
            for a in _read_json(pth):
                self.assertNotIn("ai_enrichment", a,
                                 "prod canonical modified by tests")


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    p = result.testsRun - len(result.failures) - len(result.errors)
    f = len(result.failures) + len(result.errors)
    print(f"\nRESULT: PASS={p} FAIL={f}")
    sys.exit(0 if f == 0 else 1)
