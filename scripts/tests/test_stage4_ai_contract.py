#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 第一执行包 — 正式测试。

覆盖：Schema / Eligibility / Prompt 安全 / Provider(Mock) / Cache / Data isolation。
运行方式：python scripts/tests/test_stage4_ai_contract.py
"""

import os
import sys
import json
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "ai"))

from ai.schema_validation import validate_against_schema  # noqa: E402
from ai.stage4_provider import (  # noqa: E402
    ProviderTimeout, ProviderAPIError, ProviderTerminalError,
)
from ai.mock_provider import MockProvider  # noqa: E402
from ai.enrichment_eligibility import (  # noqa: E402
    eligibility_status, compute_input_hash, is_article_url,
)
from ai.enrichment_validator import (  # noqa: E402
    parse_json_response, validate_enrichment, EVENT_TYPES,
)
from ai.enrichment_processor import (  # noqa: E402
    EnrichmentProcessor, SUCCEEDED, FAILED_RETRYABLE, FAILED_TERMINAL,
    INVALID_MODEL_OUTPUT, SKIPPED_INELIGIBLE,
)

SCHEMA_PATH = os.path.join(ROOT, "schemas", "ai_enrichment.schema.json")
FIXTURES_DIR = os.path.join(HERE, "fixtures", "stage4_ai")


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_fixtures():
    out = []
    for fn in sorted(os.listdir(FIXTURES_DIR)):
        if fn == "index.json":
            continue
        with open(os.path.join(FIXTURES_DIR, fn), encoding="utf-8") as f:
            out.append(json.load(f))
    return out


def schema_validate(parsed):
    """供 processor 使用的 schema_validator（返回 (ok, errors)）。"""
    errs = validate_against_schema(parsed, load_schema())
    return (len(errs) == 0, errs)


def make_valid_record(event=None, overrides=None):
    eid = (event or {}).get("event_id") or "EVT_1234567890abcdef"
    iso = (event or {}).get("country_iso3") or "TCD"
    rec = {
        "event_id": eid,
        "canonical_run_id": "20260802T084000+0800_084349",
        "input_hash": "a" * 64,
        "source_language": "fr",
        "title_zh": "乍得萨拉马特省发生武装袭击",
        "summary_zh": "武装人员袭击了乍得萨拉马特省的一个安全哨所，造成多名人员伤亡。"
                      "袭击者使用自动武器后向边境方向逃离，当地政府已展开调查。",
        "event_type": "armed_conflict",
        "country_iso3": iso,
        "location": {"country_iso3": iso, "admin1": None, "city": None,
                     "site": None, "raw_text": ""},
        "key_facts": [
            {"fact": "袭击发生在萨拉马特省", "evidence_field": "body_extracted",
             "evidence_excerpt": "attacked a post in Salamat"},
        ],
        "uncertainties": [],
        "security_relevance": "direct",
        "classification_confidence": 75,
        "ai_provider": "mock",
        "ai_model": "mock-model-v1",
        "prompt_version": "1.0.0",
        "processed_at": "2026-08-02T12:00:00+08:00",
        "processing_status": "succeeded",
        "error_code": None,
        "raw_response_hash": "b" * 64,
    }
    if overrides:
        rec.update(overrides)
    return rec


# ══════════════════════════════════════════════════════════════
class TestSchema(unittest.TestCase):
    """§12 Schema：合法/缺字段/枚举/类型/越界。"""

    def test_01_valid_record_passes(self):
        rec = make_valid_record()
        self.assertEqual(validate_against_schema(rec, load_schema()), [])

    def test_02_missing_field_fails(self):
        rec = make_valid_record()
        del rec["summary_zh"]
        errs = validate_against_schema(rec, load_schema())
        self.assertGreater(len(errs), 0)
        self.assertTrue(any("summary_zh" in e for e in errs))

    def test_03_invalid_enum_fails(self):
        for field, bad in (("event_type", "terrorist_attack"),
                           ("security_relevance", "high"),
                           ("processing_status", "done")):
            rec = make_valid_record()
            rec[field] = bad
            errs = validate_against_schema(rec, load_schema())
            self.assertGreater(len(errs), 0, f"{field}={bad} 应失败")

    def test_04_wrong_type_fails(self):
        rec = make_valid_record()
        rec["classification_confidence"] = "75"
        errs = validate_against_schema(rec, load_schema())
        self.assertGreater(len(errs), 0)
        rec2 = make_valid_record()
        rec2["key_facts"] = "not-array"
        self.assertGreater(len(validate_against_schema(rec2, load_schema())), 0)

    def test_05_confidence_out_of_range_fails(self):
        for bad in (-1, 101):
            rec = make_valid_record()
            rec["classification_confidence"] = bad
            errs = validate_against_schema(rec, load_schema())
            self.assertGreater(len(errs), 0, f"confidence={bad} 应越界失败")
        # 语义校验同样拦截
        ok, errs, _ = validate_enrichment(
            make_valid_record(overrides={"classification_confidence": 120}),
            {"event_id": "EVT_1234567890abcdef", "country_iso3": "TCD"})
        self.assertFalse(ok)
        self.assertTrue(any("confidence" in e for e in errs))


# ══════════════════════════════════════════════════════════════
class TestEligibility(unittest.TestCase):
    """§12 Eligibility。"""

    def _mk(self, **kw):
        e = {
            "event_id": "EVT_1234567890abcdef",
            "primary_country": "乍得",
            "country_code": "TD",
            "country_iso3": "TCD",
            "canonical_url": "https://example.com/2026/08/01/security-report",
            "body_status": "full_body",
            "body_extracted": "Some body text " * 10,
            "article_word_count": 40,
        }
        e.update(kw)
        return e

    def test_06_full_body_eligible(self):
        st, r = eligibility_status(self._mk())
        self.assertEqual(st, "eligible", r)

    def test_07_partial_body_eligible_when_enough(self):
        st, r = eligibility_status(self._mk(body_status="partial_body", article_word_count=40))
        self.assertEqual(st, "eligible", r)

    def test_08_rss_summary_only_skipped(self):
        st, r = eligibility_status(self._mk(body_status="rss_summary_only"))
        self.assertEqual(st, SKIPPED_INELIGIBLE)
        self.assertIn("rss_summary_only", r)

    def test_09_listing_page_skipped(self):
        st, r = eligibility_status(self._mk(canonical_url="https://reliefweb.int/country/tcd"))
        self.assertEqual(st, SKIPPED_INELIGIBLE)
        self.assertIn("non_article_url", r)

    def test_10_quarantined_skipped(self):
        st, r = eligibility_status(self._mk(), quarantine_ids={"EVT_1234567890abcdef"})
        self.assertEqual(st, SKIPPED_INELIGIBLE)
        self.assertIn("quarantined", r)

    def test_11_insufficient_body_skipped(self):
        st, r = eligibility_status(self._mk(article_word_count=10))
        self.assertEqual(st, SKIPPED_INELIGIBLE)
        self.assertIn("insufficient_body", r)


# ══════════════════════════════════════════════════════════════
class TestPromptSafety(unittest.TestCase):
    """§12 Prompt 安全：注入不生效、国家不变、无额外文字。"""

    def test_12_injection_does_not_override(self):
        # 注入文本只是正文；处理结果 country 仍为 TCD、输出为 JSON
        fixture = [f for f in load_fixtures()
                   if f["scenario"] == "prompt_injection"][0]
        event = fixture["event"]
        prov = MockProvider()
        proc = EnrichmentProcessor(prov, schema_validator=schema_validate,
                                   ai_root=tempfile.mkdtemp())
        prompt = proc._render_prompt(event)
        self.assertIn("Ignore previous instructions", prompt)
        resp = prov.generate_structured(prompt)
        parsed = resp["parsed"]
        self.assertIsNotNone(parsed)
        ok, errs, _ = validate_enrichment(
            parsed, event, expected_run_id=event["canonical_run_id"])
        self.assertTrue(ok, errs)

    def test_13_country_not_changed(self):
        fixture = [f for f in load_fixtures()
                   if f["scenario"] == "multi_country_single_primary"][0]
        event = fixture["event"]
        prov = MockProvider()
        resp = prov.generate_structured(EnrichmentProcessor(prov)._render_prompt(event))
        self.assertEqual(resp["parsed"]["country_iso3"], "TCD")

    def test_14_no_extra_text_output(self):
        # Mock 输出必须是纯 JSON（无围栏/解释）
        prov = MockProvider()
        resp = prov.generate_structured('{"event_id": "EVT_1234567890abcdef", "country_iso3": "TCD", "original_title": "Test"}')
        raw = resp["raw_text"].strip()
        self.assertTrue(raw.startswith("{") and raw.endswith("}"))


# ══════════════════════════════════════════════════════════════
class TestProviderMock(unittest.TestCase):
    """§12 Provider：Mock 成功/超时/无效 JSON/Retryable/Terminal。"""

    def test_15_mock_success(self):
        prov = MockProvider()
        resp = prov.generate_structured('{"event_id": "EVT_1234567890abcdef", "country_iso3": "TCD", "original_title": "Attaque"}')
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["parsed"]["event_id"], "EVT_1234567890abcdef")
        self.assertEqual(resp["parsed"]["country_iso3"], "TCD")
        self.assertEqual(resp["parsed"]["ai_provider"], "mock")
        self.assertEqual(len(resp["raw_response_hash"]), 64)

    def test_16_mock_timeout(self):
        prov = MockProvider(behavior={"timeout": True})
        with self.assertRaises(ProviderTimeout):
            prov.generate_structured("x")

    def test_17_mock_invalid_json(self):
        prov = MockProvider(behavior={"invalid_json": True})
        resp = prov.generate_structured("x")
        self.assertFalse(resp["ok"])
        self.assertIsNone(resp["parsed"])

    def test_18_mock_retryable_error(self):
        prov = MockProvider(behavior={"api_error": True})
        with self.assertRaises(ProviderAPIError):
            prov.generate_structured("x")

    def test_19_mock_terminal_error(self):
        prov = MockProvider(behavior={"terminal_error": True})
        with self.assertRaises(ProviderTerminalError):
            prov.generate_structured("x")

    def test_20_processor_maps_errors_to_status(self):
        root = tempfile.mkdtemp()
        ev = {"event_id": "EVT_1234567890abcdef", "primary_country": "乍得",
              "country_code": "TD", "country_iso3": "TCD",
              "canonical_url": "https://example.com/2026/08/01/x",
              "body_status": "full_body", "body_extracted": "word " * 40,
              "article_word_count": 40, "event_time": "2026-08-01T09:00:00+08:00",
              "original_title": "Attack"}
        p = EnrichmentProcessor(MockProvider(behavior={"timeout": True}),
                                ai_root=root)
        summ = p.process_events([ev])
        self.assertEqual(summ["failed_retryable"], 1)
        p2 = EnrichmentProcessor(MockProvider(behavior={"terminal_error": True}),
                                 ai_root=root)
        summ2 = p2.process_events([ev])
        self.assertEqual(summ2["failed_terminal"], 1)
        p3 = EnrichmentProcessor(MockProvider(behavior={"invalid_json": True}),
                                 ai_root=root)
        summ3 = p3.process_events([ev])
        self.assertEqual(summ3["invalid_model_output"], 1)


# ══════════════════════════════════════════════════════════════
class TestCache(unittest.TestCase):
    """§12 Cache：命中/输入变化/Prompt 变化/模型变化/失败不覆盖成功。"""

    def _mk_event(self, title="Attack", body="word " * 40, eid="EVT_1234567890abcdef"):
        return {"event_id": eid, "primary_country": "乍得", "country_code": "TD",
                "country_iso3": "TCD",
                "canonical_url": f"https://example.com/2026/08/01/{eid[:8]}",
                "body_status": "full_body", "body_extracted": body,
                "article_word_count": 40, "event_time": "2026-08-01T09:00:00+08:00",
                "original_title": title, "canonical_run_id": "20260802T084000+0800_084349"}

    def test_21_same_input_cache_hit(self):
        root = tempfile.mkdtemp()
        ev = self._mk_event()
        p = EnrichmentProcessor(MockProvider(), ai_root=root,
                                schema_validator=schema_validate)
        s1 = p.process_events([ev])
        self.assertEqual(s1["succeeded"], 1)
        p2 = EnrichmentProcessor(MockProvider(), ai_root=root,
                                 schema_validator=schema_validate)
        s2 = p2.process_events([ev])
        self.assertEqual(s2["cache_hit"], 1)
        self.assertEqual(s2["succeeded"], 0)

    def test_22_input_change_reprocess(self):
        root = tempfile.mkdtemp()
        ev1 = self._mk_event(body="word " * 40)
        p = EnrichmentProcessor(MockProvider(), ai_root=root,
                                schema_validator=schema_validate)
        p.process_events([ev1])
        ev2 = self._mk_event(body="different body text " * 10)
        s = p.process_events([ev2])
        self.assertEqual(s["succeeded"], 1)  # 重新处理（新 hash）

    def test_23_prompt_change_reprocess(self):
        root = tempfile.mkdtemp()
        ev = self._mk_event()
        p1 = EnrichmentProcessor(MockProvider(), prompt_version="1.0.0",
                                 ai_root=root, schema_validator=schema_validate)
        p1.process_events([ev])
        p2 = EnrichmentProcessor(MockProvider(), prompt_version="1.1.0",
                                 ai_root=root, schema_validator=schema_validate)
        s = p2.process_events([ev])
        self.assertEqual(s["succeeded"], 1)  # prompt 变 → 重新处理

    def test_24_model_change_independent(self):
        root = tempfile.mkdtemp()
        ev = self._mk_event()
        p1 = EnrichmentProcessor(MockProvider(), ai_root=root,
                                 schema_validator=schema_validate)
        p1.process_events([ev])
        m2 = MockProvider()
        m2.model_name = "mock-model-v2"
        p2 = EnrichmentProcessor(m2, ai_root=root, schema_validator=schema_validate)
        s = p2.process_events([ev])
        self.assertEqual(s["succeeded"], 1)  # 模型变 → 独立结果

    def test_25_failure_does_not_overwrite_success(self):
        root = tempfile.mkdtemp()
        ev = self._mk_event()
        p1 = EnrichmentProcessor(MockProvider(), ai_root=root,
                                 schema_validator=schema_validate)
        s1 = p1.process_events([ev])
        self.assertEqual(s1["succeeded"], 1)
        # 相同 key 但 provider 失败：已有成功结果不得被覆盖
        p2 = EnrichmentProcessor(MockProvider(behavior={"timeout": True}),
                                 ai_root=root, schema_validator=schema_validate)
        s2 = p2.process_events([ev])
        self.assertEqual(s2["cache_hit"], 1)  # 命中成功缓存，不调用失败 provider
        state = json.load(open(os.path.join(root, "enrichment_state.json"),
                               encoding="utf-8"))
        rec = state["records"][ev["event_id"]]
        self.assertEqual(rec["status"], SUCCEEDED)


# ══════════════════════════════════════════════════════════════
class TestDataIsolation(unittest.TestCase):
    """§12 Data isolation：AI runtime 不进 dist、Canonical/Public 不被修改、无 Key。"""

    def test_26_ai_not_in_dist(self):
        dist = os.path.join(ROOT, "dist")
        if os.path.exists(dist):
            for root, dirs, files in os.walk(dist):
                self.assertNotIn("ai", dirs, "dist 中不得出现 data/ai")
                self.assertNotIn("runtime", dirs, "dist 中不得出现 data/runtime")

    def test_27_gitignore_covers_ai_runtime(self):
        gi = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
        for pat in ("data/ai/queue/*", "data/ai/cache/*", "data/runtime/"):
            self.assertIn(pat, gi, f".gitignore 缺少 {pat}")

    def test_28_canonical_public_untouched(self):
        # 处理器不写 canonical/public
        root = tempfile.mkdtemp()
        ev = self._mk_event()
        EnrichmentProcessor(MockProvider(), ai_root=root,
                            schema_validator=schema_validate).process_events([ev])
        can_path = os.path.join(ROOT, "data", "canonical", "event_clusters.json")
        pub_path = os.path.join(ROOT, "data", "public", "published_events.json")
        mtime_can = os.path.getmtime(can_path)
        mtime_pub = os.path.getmtime(pub_path)
        # 再次运行处理器（应只写 data/ai）
        EnrichmentProcessor(MockProvider(), ai_root=root,
                            schema_validator=schema_validate).process_events([ev])
        self.assertEqual(os.path.getmtime(can_path), mtime_can,
                         "Canonical 不应被修改")
        self.assertEqual(os.path.getmtime(pub_path), mtime_pub,
                         "Public 不应被修改")

    def _mk_event(self, title="Attack", body="word " * 40, eid="EVT_1234567890abcdef"):
        return {"event_id": eid, "primary_country": "乍得", "country_code": "TD",
                "country_iso3": "TCD",
                "canonical_url": f"https://example.com/2026/08/01/{eid[:8]}",
                "body_status": "full_body", "body_extracted": body,
                "article_word_count": 40, "event_time": "2026-08-01T09:00:00+08:00",
                "original_title": title, "canonical_run_id": "20260802T084000+0800_084349"}

    def test_29_no_api_key_in_repo(self):
        import re
        bad = []
        for root, dirs, files in os.walk(os.path.join(ROOT, "scripts")):
            if "__pycache__" in root:
                continue
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(root, fn)
                try:
                    t = open(p, encoding="utf-8").read()
                except Exception:
                    continue
                if re.search(r"sk-[A-Za-z0-9]{20,}|OPENAI_API_KEY\s*=\s*['\"][^'\"]+['\"]", t):
                    bad.append(fn)
        self.assertEqual(bad, [], f"仓库中发现疑似 API Key: {bad}")


# ══════════════════════════════════════════════════════════════
class TestFixturesAndPipeline(unittest.TestCase):
    """§11 fixtures 完整性 + 端到端流程。"""

    def test_30_fixture_count(self):
        fxs = load_fixtures()
        self.assertGreaterEqual(len(fxs), 15, f"fixtures 仅 {len(fxs)} 条，需 ≥15")
        idx = json.load(open(os.path.join(FIXTURES_DIR, "index.json"), encoding="utf-8"))
        self.assertEqual(idx["count"], len(fxs))

    def test_31_scenario_coverage(self):
        scenarios = {f["scenario"] for f in load_fixtures()}
        required = {"fr_armed_attack", "en_political_security", "ar_border_incident",
                    "clear_casualty_numbers", "uncertain_casualties", "multiple_locations",
                    "multi_country_single_primary", "names_and_institutions",
                    "dates_and_times", "partial_body", "insufficient_body",
                    "non_security_news", "template_noise", "prompt_injection",
                    "invalid_model_json", "rss_summary_only", "listing_page_url"}
        missing = required - scenarios
        self.assertEqual(missing, set(), f"缺少场景: {missing}")

    def test_32_end_to_end_success(self):
        root = tempfile.mkdtemp()
        fxs = load_fixtures()
        events = [f["event"] for f in fxs
                  if f["scenario"] in ("fr_armed_attack", "partial_body",
                                       "template_noise", "prompt_injection")]
        p = EnrichmentProcessor(MockProvider(), ai_root=root,
                                schema_validator=schema_validate,
                                run_id="20260802T084000+0800_084349")
        summ = p.process_events(events)
        self.assertEqual(summ["succeeded"], 4, summ)
        # 结果文件存在且含 4 条
        results = json.load(open(os.path.join(root, "enrichment_results.json"),
                                 encoding="utf-8"))
        self.assertEqual(len(results["items"]), 4)

    def test_33_schema_validator_on_mock_output(self):
        # Mock 输出通过 schema + 语义校验
        root = tempfile.mkdtemp()
        ev = {"event_id": "EVT_1234567890abcdef", "primary_country": "乍得",
              "country_code": "TD", "country_iso3": "TCD",
              "canonical_url": "https://example.com/2026/08/01/x",
              "body_status": "full_body", "body_extracted": "word " * 40,
              "article_word_count": 40, "event_time": "2026-08-01T09:00:00+08:00",
              "original_title": "Attaque armée au Tchad",
              "canonical_run_id": "20260802T084000+0800_084349"}
        p = EnrichmentProcessor(MockProvider(), ai_root=root,
                                schema_validator=schema_validate,
                                run_id="20260802T084000+0800_084349")
        p.process_events([ev])
        results = json.load(open(os.path.join(root, "enrichment_results.json"),
                                 encoding="utf-8"))
        rec = results["items"][0]
        self.assertEqual(rec["event_id"], ev["event_id"])
        self.assertEqual(rec["country_iso3"], "TCD")
        self.assertEqual(rec["ai_provider"], "mock")
        self.assertEqual(rec["processing_status"], "succeeded")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    print(f"RESULT: PASS={n_run - n_fail} FAIL={n_fail}")
    sys.exit(1 if n_fail else 0)
