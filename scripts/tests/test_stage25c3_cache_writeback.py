#!/usr/bin/env python3
"""ASIP Stage 2.5C-3 closeout — Cache-hit writeback, transaction order, canonical isolation"""

import json, os, sys, shutil, tempfile, copy, unittest
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
REPO = os.path.dirname(SCRIPTS)

from ai.workbuddy_worker import claim_batch, ingest_results, _ensure_dirs
from ai.ai_result_cache import write_cache_entry, check_cache_hit, set_ai_root
from ai.ai_writeback import _check_internal_fields, _INTERNAL_FIELDS

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

def _task(tid, tt="article_analysis", cache_key=None, writeback=None, **kw):
    ir = {"prompt_variables":{"source_text":"road","country_iso3":"NER","source_language":"en"}}
    if writeback:
        ir["writeback"] = writeback
    t = {"task_id":tid,"schema_version":"1.0","task_type":tt,
         "status":"queued","priority":"high","input_ref":ir,
         "content_hash":"abc","prompt_version":"1.0.1",
         "output_schema_version":"1.1","provider_requested":"workbuddy_queue",
         "created_at":"2026-08-01T00:00:00Z","retry_count":0,"max_retries":1,
         "cache_key":cache_key or ("cache:"+tid),"synthetic":True}
    t.update(kw)
    return t

def _result(bid, tid, status="success", output=None):
    r = {"task_id":tid,"schema_version":"1.0","status":status,
         "provider":"workbuddy_queue","model":"deepseek-v4-flash",
         "started_at":"2026-08-01T00:01:00Z","completed_at":"2026-08-01T00:02:00Z",
         "usage":{"input_tokens":0,"output_tokens":0,"estimated_cost_usd":0},
         "error":None if status=="success" else {"code":"e","message":"x"}}
    if output is not None: r["result"] = output
    return {"batch_id":bid,"worker_id":"workbuddy-local","results":[r]}

def _mk_canonical(tmp):
    os.makedirs(os.path.join(tmp,"data","canonical"), exist_ok=True)
    article = {"article_id":"ART_0123456789abcdef","schema_version":"2.0",
               "pipeline_version":2,"run_id":"20260101T000000+0800_abc123",
               "source_id":"S1","article_url":"http://a",
               "processing_status":"queued_for_verification","verification_queue_status":"waiting",
               "summary_cn":"","event_type":"None","relevance_score":0,
               "is_security_relevant":False,"china_related":False,
               "needs_translation":True,"content_hash":"0123456789abcdef",
               "published_at":"2026-01-01T00:00:00Z"}
    event = {"event_id":"EVT_0123456789abcdef","schema_version":"2.0",
             "pipeline_version":2,"run_id":"20260101T000000+0800_abc123",
             "country_code":"NER","event_severity":"medium",
             "event_status":"ongoing","event_type":"None","summary_cn":"",
             "potential_impact":"","article_ids":[],
             "verification_level":"not_checked","verification_score":0,
             "publication_status":"verification_pending","quality_gate_passed":False,
             "current_policy_passed":False,
             "created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z"}
    _write_json(os.path.join(tmp,"data","canonical","articles.json"), [article])
    _write_json(os.path.join(tmp,"data","canonical","event_clusters.json"), [event])
    return article, event

def _cache_result_into(root, task, prov, ts="2026-08-01T00:00:00Z"):
    set_ai_root(root)
    write_cache_entry(task, _VALID_AA, prov, ts)


class TestCacheHitWriteback(unittest.TestCase):
    """Cache hit must execute writeback before completed."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="chw_")
        _ensure_dirs(self.tmp)
        set_ai_root(self.tmp)
        self.article, self.event = _mk_canonical(self.tmp)

    def tearDown(self):
        set_ai_root(None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed_cache(self, tid="AIT_111111111111111111111201"):
        t = _task(tid)
        prov = {"prompt_checksum":"cs","render_hash":"rh",
                "prompt_variables_digest":"vd","provider":"workbuddy_queue",
                "model":"deepseek-v4-flash","batch_id":"B_orig","cache_hit":False}
        _cache_result_into(self.tmp, t, prov)
        return t

    def test_cache_hit_article_writeback(self):
        tid = "AIT_111111111111111111111201"
        self._seed_cache(tid)
        from data.repository import Repository
        repo = Repository(root=self.tmp, make_backups=False)
        # Queue task with writeback target
        t = _task(tid, writeback={"target_type":"article","target_id":"ART_0123456789abcdef"})
        _write_json(os.path.join(self.tmp,"queue",tid+".json"), t)
        cr = claim_batch(ai_root=self.tmp, batch_size=1, prompt_binding_enabled=True,
                         expected_model="deepseek-v4-flash",
                         _writeback_repo=repo)
        self.assertIsNone(cr.get("batch_id"))
        # Article updated
        art = repo.get_article("ART_0123456789abcdef")
        self.assertEqual(art["summary_cn"], "x")
        # No batch/lease/prompt
        batches = os.listdir(os.path.join(self.tmp,"batches")) if os.path.exists(
            os.path.join(self.tmp,"batches")) else []
        leases = os.listdir(os.path.join(self.tmp,"leases")) if os.path.exists(
            os.path.join(self.tmp,"leases")) else []
        self.assertEqual(len(batches), 0)
        self.assertEqual(len(leases), 0)
        # completed with cache.hit + provenance.cache_hit
        comp = _read_json(os.path.join(self.tmp,"completed",tid+".json"))
        self.assertTrue(comp["cache"]["hit"])
        self.assertFalse(comp["cache"]["model_call_performed"])
        self.assertTrue(comp["provenance"]["cache_hit"])

    def test_cache_hit_event_writeback_no_publish(self):
        tid = "AIT_111111111111111111111202"
        self._seed_cache(tid)
        # Create event_synthesis task targeting event
        from data.repository import Repository
        repo = Repository(root=self.tmp, make_backups=False)
        evt_result = {"event_summary_zh":"protest","country_iso3":"NER","event_type":"civil_unrest",
                      "potential_impacts":[],"timeline":[],"confirmed_facts":[],
                      "reported_claims":[],"contradictions":[],"unresolved_questions":[],
                      "affected_locations":[],"confidence":0.5,"synthetic":True}
        # Seed cache with event result (using same cache_key to hit)
        from ai.ai_result_cache import write_cache_entry as wce
        set_ai_root(self.tmp)
        t_evt = _task(tid, tt="event_synthesis", cache_key="ck:evt")
        prov = {"prompt_checksum":"cs","render_hash":"rh","prompt_variables_digest":"vd"}
        wce(t_evt, evt_result, prov, "2026-08-01T00:00:00Z")
        # Queue same task with writeback
        t2 = _task(tid, tt="event_synthesis", cache_key="ck:evt",
                   writeback={"target_type":"event_cluster","target_id":"EVT_0123456789abcdef"})
        _write_json(os.path.join(self.tmp,"queue",tid+".json"), t2)
        cr = claim_batch(ai_root=self.tmp, batch_size=1, prompt_binding_enabled=True,
                         expected_model="deepseek-v4-flash",
                         _writeback_repo=repo)
        self.assertIsNone(cr.get("batch_id"))
        ev = repo.get_event("EVT_0123456789abcdef")
        self.assertEqual(ev["summary_cn"], "protest")
        self.assertEqual(ev["publication_status"], "verification_pending")
        self.assertEqual(ev["verification_level"], "not_checked")

    def test_cache_hit_writeback_failure_keeps_queue(self):
        tid = "AIT_111111111111111111111203"
        self._seed_cache(tid)
        from data.repository import Repository
        repo = Repository(root=self.tmp, make_backups=False)
        # Target does not exist → writeback fails
        t = _task(tid, writeback={"target_type":"article","target_id":"ART_NOPE"})
        _write_json(os.path.join(self.tmp,"queue",tid+".json"), t)
        cr = claim_batch(ai_root=self.tmp, batch_size=1, prompt_binding_enabled=True,
                         expected_model="deepseek-v4-flash",
                         _writeback_repo=repo)
        self.assertTrue(cr.get("cache_hit_errors"))
        self.assertEqual(cr["cache_hit_errors"][0]["code"], "cache_hit_writeback_failed")
        # Queue unchanged
        from ai.workbuddy_worker import status_summary
        st = status_summary(self.tmp)
        self.assertEqual(st["queue"], 1)
        self.assertEqual(st["processing"], 0)
        self.assertEqual(st["completed"], 0)


class TestTransactionOrder(unittest.TestCase):
    """New-result writeback failure must not leave orphan cache."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="txn_")
        _ensure_dirs(self.tmp)
        set_ai_root(self.tmp)
        self.article, self.event = _mk_canonical(self.tmp)

    def tearDown(self):
        set_ai_root(None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _claim(self, tid, tt="article_analysis", writeback=None, cache_key=None):
        t = _task(tid, tt=tt, writeback=writeback, cache_key=cache_key)
        _write_json(os.path.join(self.tmp,"queue",tid+".json"), t)
        return claim_batch(ai_root=self.tmp, batch_size=1, prompt_binding_enabled=True,
                           expected_model="deepseek-v4-flash")

    def test_new_result_writeback_failure_no_cache(self):
        tid = "AIT_111111111111111111111301"
        from data.repository import Repository
        repo = Repository(root=self.tmp, make_backups=False)
        cr = self._claim(tid, writeback={"target_type":"article","target_id":"ART_MISSING"})
        bid = cr.get("batch_id")
        self.assertIsNotNone(bid)
        rd = _result(bid, tid, output=_VALID_AA)
        _write_json(os.path.join(self.tmp,"batches",bid,"result.json"), rd)
        rep = ingest_results(self.tmp, bid, os.path.join(self.tmp,"batches",bid,"result.json"),
                             _writeback_repo=repo)
        self.assertEqual(rep["accepted"], 0)
        # No cache created
        hit, _, _ = check_cache_hit(_task(tid, cache_key="cache:"+tid))
        self.assertFalse(hit)
        # Not completed
        self.assertFalse(os.path.exists(os.path.join(self.tmp,"completed",tid+".json")))

    def test_cache_write_failure_still_completes(self):
        tid = "AIT_111111111111111111111302"
        cr = self._claim(tid)  # no writeback
        bid = cr.get("batch_id")
        rd = _result(bid, tid, output=_VALID_AA)
        _write_json(os.path.join(self.tmp,"batches",bid,"result.json"), rd)
        # Mock cache write to fail
        with patch("ai.ai_result_cache.write_cache_entry",
                   side_effect=IOError("disk full")):
            rep = ingest_results(self.tmp, bid, os.path.join(self.tmp,"batches",bid,"result.json"))
        self.assertEqual(rep["accepted"], 1)
        comp = _read_json(os.path.join(self.tmp,"completed",tid+".json"))
        self.assertTrue(comp["cache"]["cache_write_failed"])

    def test_no_writeback_plain_completes(self):
        tid = "AIT_111111111111111111111303"
        cr = self._claim(tid)
        bid = cr.get("batch_id")
        rd = _result(bid, tid, output=_VALID_AA)
        _write_json(os.path.join(self.tmp,"batches",bid,"result.json"), rd)
        rep = ingest_results(self.tmp, bid, os.path.join(self.tmp,"batches",bid,"result.json"))
        self.assertEqual(rep["accepted"], 1)
        comp = _read_json(os.path.join(self.tmp,"completed",tid+".json"))
        self.assertIn("cache", comp)
        self.assertFalse(comp["cache"]["hit"])


class TestCanonicalIsolation(unittest.TestCase):
    """Canonical must never contain internal task fields."""

    def test_internal_fields_detected(self):
        bad = {"_task": {"x": 1}, "summary_cn": "ok"}
        found = _check_internal_fields(bad)
        self.assertIn("_task", found)

    def test_clean_record_passes(self):
        good = {"summary_cn": "x", "ai_enrichment": {"a": {"result": {}, "provenance": {"task_id":"t"}}}}
        found = _check_internal_fields(good)
        self.assertEqual(found, [])

    def test_provenance_clean(self):
        from ai.ai_writeback import _make_provenance
        prov = _make_provenance(
            {"task_id":"t","task_type":"article_analysis","content_hash":"c",
             "prompt_version":"1.0.1","output_schema_version":"1.1"},
            {"prompt_checksum":"cs","render_hash":"rh","prompt_variables_digest":"vd",
             "provider":"p","model":"m","batch_id":"b"},
            True)
        self.assertTrue(prov["cache_hit"])
        s = json.dumps(prov)
        self.assertNotIn("system_text", s)
        self.assertNotIn("source_text", s)


class TestPublicIsolation(unittest.TestCase):
    def test_dist_no_ai(self):
        self.assertFalse(os.path.isdir(os.path.join(REPO,"dist","data","ai")))

    def test_no_external_calls(self):
        for m in ["ai_result_cache.py","ai_writeback.py","workbuddy_worker.py"]:
            c = open(os.path.join(SCRIPTS,"ai",m),encoding='utf-8').read()
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
